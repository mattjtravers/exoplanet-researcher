"""Benchmark Runner — evaluate the full pipeline against the Golden Dataset."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from src.benchmark.metrics import compute_metrics
from src.errors import RegressionError
from src.schemas.benchmark import (
    BenchmarkResult,
    GoldenDataset,
    ObjectFailure,
    ObjectResult,
)

_HISTORY_DIR = Path("benchmarks") / "history"
_REGRESSION_THRESHOLD = 0.05  # 5 F1 percentage points


def check_regression(current_f1: float, prior_f1: float) -> None:
    """Raise RegressionError if current F1 regresses more than 5 points from prior.

    Args:
        current_f1: F1 score from the current run (0–1 scale).
        prior_f1: F1 score from the most recent prior run.

    Raises:
        RegressionError: If drop > 5 percentage points (i.e., 0.05 on 0–1 scale).
    """
    delta = prior_f1 - current_f1
    if delta > _REGRESSION_THRESHOLD:
        raise RegressionError(
            current_f1=current_f1,
            prior_f1=prior_f1,
            delta=delta,
        )


def load_prior_result() -> BenchmarkResult | None:
    """Load the most recent BenchmarkResult from history."""
    _HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    history_files = sorted(_HISTORY_DIR.glob("*.json"), reverse=True)
    if not history_files:
        return None
    try:
        data = json.loads(history_files[0].read_text())
        return BenchmarkResult(**data)
    except Exception:
        return None


def run_benchmark(dataset: GoldenDataset) -> BenchmarkResult:
    """Run the full pipeline against every object in the Golden Dataset.

    Args:
        dataset: The Golden Dataset to evaluate against.

    Returns:
        BenchmarkResult with confusion matrix and per-object results.
    """
    from src.dag.pipeline import run_pipeline

    per_object: list[ObjectResult] = []
    failures: list[ObjectFailure] = []

    for obj in dataset.objects:
        try:
            state = run_pipeline(target_id=obj.target_id, catalog="KIC")
            report = state.get("vetting_report")
            if report is None:
                raise RuntimeError("No vetting report produced")

            prediction = report.disposition
            confidence = report.consensus_confidence

            per_object.append(
                ObjectResult(
                    target_id=obj.target_id,
                    ground_truth=obj.ground_truth,
                    prediction=prediction,
                    confidence=confidence,
                )
            )
        except Exception as exc:
            failures.append(
                ObjectFailure(
                    target_id=obj.target_id,
                    error_type=type(exc).__name__,
                    error_message=str(exc),
                )
            )
            # Log but continue
            print(f"  [FAIL] {obj.target_id}: {type(exc).__name__}: {exc}", file=sys.stderr)

    # Compute metrics from successfully processed objects
    pred_pairs = [(r.prediction, r.ground_truth) for r in per_object]
    metrics = compute_metrics(pred_pairs)

    result = BenchmarkResult(
        dataset_version=dataset.dataset_version,
        true_positives=metrics["true_positives"],
        false_positives=metrics["false_positives"],
        true_negatives=metrics["true_negatives"],
        false_negatives=metrics["false_negatives"],
        precision=metrics["precision"],
        recall=metrics["recall"],
        f1=metrics["f1"],
        per_object_results=per_object if per_object else [
            ObjectResult(
                target_id=dataset.objects[0].target_id,
                ground_truth=dataset.objects[0].ground_truth,
                prediction="inconclusive",
            )
        ],
        failures=failures,
    )

    # Persist to history
    _HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    out_path = _HISTORY_DIR / f"{result.run_id}.json"
    out_path.write_text(json.dumps(result.model_dump(mode="json"), default=str))

    return result


def print_confusion_matrix(result: BenchmarkResult) -> None:
    """Print a formatted confusion matrix and F1 to stdout."""
    print("\n=== Benchmark Results ===")
    print(f"Dataset version: {result.dataset_version}")
    print(f"Run ID: {result.run_id}")
    print("\nConfusion Matrix:")
    print(f"  TP={result.true_positives}  FP={result.false_positives}")
    print(f"  FN={result.false_negatives}  TN={result.true_negatives}")
    print("\nMetrics:")
    print(f"  Precision: {result.precision:.4f}")
    print(f"  Recall:    {result.recall:.4f}")
    print(f"  F1:        {result.f1:.4f}")
    if result.failures:
        print(f"\nFailures: {len(result.failures)} object(s) did not complete")
    print("========================\n")


if __name__ == "__main__":
    from src.benchmark.dataset import download_koi_table, load_cached_dataset

    print("[XPI Benchmark] Loading Golden Dataset...")
    dataset = load_cached_dataset()
    if dataset is None:
        print("No cached dataset. Downloading...")
        dataset = download_koi_table()

    print(f"[XPI Benchmark] Running against {len(dataset.objects)} objects...")
    result = run_benchmark(dataset)
    print_confusion_matrix(result)

    # Regression check
    prior = load_prior_result()
    if prior and prior.run_id != result.run_id:
        try:
            check_regression(current_f1=result.f1, prior_f1=prior.f1)
            print(f"[XPI Benchmark] No regression detected (prior F1={prior.f1:.4f}).")
        except RegressionError as e:
            print(f"[XPI Benchmark] REGRESSION DETECTED: {e}", file=sys.stderr)
            sys.exit(1)
