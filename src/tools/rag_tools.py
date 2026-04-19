"""RAG tools: ArXiv search, ADS search, and iterative query builder."""

from __future__ import annotations

import os
import time

import requests

from src.errors import ArchiveConnectionError, ConfigError
from src.schemas.candidate import CandidateTarget
from src.schemas.tools import LiteraturePaper, LiteratureSearchResult

# ---------------------------------------------------------------------------
# ArXiv search tool (T028)
# ---------------------------------------------------------------------------

def search_arxiv(query: str, max_results: int = 10) -> list[LiteraturePaper]:
    """Search ArXiv for papers matching the query.

    Args:
        query: Search query string (e.g. "KIC 11442793 exoplanet").
        max_results: Maximum number of results to return.

    Returns:
        List of LiteraturePaper results.

    Raises:
        ValueError: If query is empty.
        ArchiveConnectionError: If ArXiv is unreachable.
    """
    if not query or not query.strip():
        raise ValueError("query must not be empty")

    try:
        import arxiv
    except ImportError as exc:
        raise ArchiveConnectionError("arxiv package not installed") from exc

    try:
        client = arxiv.Client()
        search = arxiv.Search(
            query=query,
            max_results=max_results,
            sort_by=arxiv.SortCriterion.Relevance,
        )
        results = list(client.results(search))
        return [
            LiteraturePaper(
                source_id=r.entry_id.split("/")[-1],
                abstract=r.summary,
                source_type="arxiv",
            )
            for r in results
        ]
    except Exception as exc:
        error_msg = str(exc).lower()
        if any(kw in error_msg for kw in ["connection", "timeout", "network"]):
            raise ArchiveConnectionError(str(exc)) from exc
        # Return empty on other errors (rate limits, etc.)
        return []


# ---------------------------------------------------------------------------
# ADS search tool (T029)
# ---------------------------------------------------------------------------

_ADS_API_BASE = "https://api.adsabs.harvard.edu/v1/search/query"


def search_ads(query: str, max_results: int = 10) -> list[LiteraturePaper]:
    """Search NASA ADS for papers matching the query.

    Args:
        query: Search query string.
        max_results: Maximum number of results to return.

    Returns:
        List of LiteraturePaper results.

    Raises:
        ConfigError: If ADS_API_TOKEN is not set.
        ValueError: If query is empty.
        ArchiveConnectionError: If ADS is unreachable.
    """
    if not query or not query.strip():
        raise ValueError("query must not be empty")

    token = os.environ.get("ADS_API_TOKEN")
    if not token:
        raise ConfigError(
            "ADS_API_TOKEN environment variable not set. "
            "Obtain a token from https://ui.adsabs.harvard.edu/user/settings/token"
        )

    headers = {"Authorization": f"Bearer {token}"}
    params = {
        "q": query,
        "fl": "bibcode,abstract",
        "rows": max_results,
        "sort": "score desc",
    }

    try:
        response = requests.get(_ADS_API_BASE, headers=headers, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        docs = data.get("response", {}).get("docs", [])
        return [
            LiteraturePaper(
                source_id=d["bibcode"],
                abstract=d.get("abstract", ""),
                source_type="ads",
            )
            for d in docs
            if "bibcode" in d
        ]
    except requests.exceptions.ConnectionError as exc:
        raise ArchiveConnectionError(str(exc)) from exc
    except requests.exceptions.Timeout as exc:
        raise ArchiveConnectionError(f"ADS request timed out: {exc}") from exc
    except requests.exceptions.RequestException as exc:
        raise ArchiveConnectionError(str(exc)) from exc


# ---------------------------------------------------------------------------
# Iterative query builder (T030)
# ---------------------------------------------------------------------------

def build_queries(
    candidate: CandidateTarget,
    anomaly_hints: list[str] | None = None,
) -> list[str]:
    """Generate ≥ 2 search query variants from a CandidateTarget.

    On empty results from the first query, subsequent queries broaden the search.

    Args:
        candidate: The candidate being vetted.
        anomaly_hints: Optional anomaly type strings to inject as hypothesis terms.

    Returns:
        List of query strings (at least 2).
    """
    base_id = candidate.target_id.replace("-", " ")
    catalog = candidate.catalog

    queries = [
        # Narrow: exact ID + exoplanet context
        f"{base_id} exoplanet transit photometry",
        # Broader: just the star ID
        f"{base_id} {catalog} stellar",
        # Even broader: catalog field + stellar type
        f"{catalog} exoplanet vetting",
    ]

    if anomaly_hints:
        for hint in anomaly_hints[:2]:
            # Translate anomaly type to search terms
            hypothesis_map = {
                "asymmetric_transit": "asymmetric transit dust disk comet",
                "aperiodicity": "stellar variability flares aperiodic signal",
                "flux_spike": "contamination eclipsing binary background star",
                "other": "false positive eclipsing binary",
            }
            search_term = hypothesis_map.get(hint, hint.replace("_", " "))
            queries.append(f"{base_id} {search_term}")

    return queries


def iterative_search(
    candidate: CandidateTarget,
    anomaly_hints: list[str] | None = None,
    max_iterations: int = 3,
) -> LiteratureSearchResult:
    """Run iterative ArXiv + ADS searches with query broadening.

    Args:
        candidate: The candidate being vetted.
        anomaly_hints: Anomaly types from Observer output.
        max_iterations: Maximum number of search rounds.

    Returns:
        LiteratureSearchResult with collected papers and issued queries.
    """
    queries = build_queries(candidate, anomaly_hints)
    all_results: list[LiteraturePaper] = []
    queries_issued: list[str] = []

    for i, query in enumerate(queries[:max_iterations]):
        queries_issued.append(query)

        # ArXiv search
        try:
            arxiv_results = search_arxiv(query, max_results=5)
            all_results.extend(arxiv_results)
        except (ArchiveConnectionError, Exception):
            pass

        # ADS search (skip if no token)
        try:
            ads_results = search_ads(query, max_results=5)
            all_results.extend(ads_results)
        except ConfigError:
            pass
        except (ArchiveConnectionError, Exception):
            pass

        # Stop early if we have enough results
        if len(all_results) >= 5:
            break

        # Brief pause to respect rate limits
        if i < len(queries) - 1:
            time.sleep(0.5)

    return LiteratureSearchResult(papers=all_results, queries_issued=queries_issued)
