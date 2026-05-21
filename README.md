
# Exoplanet Researcher — Independent Agentic Exoplanet Vetting

## Overview

Exoplanet Researcher is a lightweight, multi-agent pipeline built to automate the vetting of exoplanet candidates by cross-referencing quantitative photometric data with scientific literature. It eliminates manual verification bottlenecks, transforming raw transit observations and unstructured research into transparent, fully reproducible Vetting Reports backed by mathematical confidence scores.

---

## Architectural Blueprint

```
[CandidateTarget Input]
          │
          ▼
┌───────────────────┐  ──(MCP)──► [Local Astro MCP Tool Server]
│   ObserverNode    │  ◄────────  (Photometric Light Curves)
└─────────┬─────────┘
          │ (AnomalyRecords)
          ▼
┌───────────────────┐  ──(MCP)──► [Local Literature MCP Server]
│    ScholarNode    │  ◄────────  (ArXiv / ADS Metadata)
└─────────┬─────────┘
          │ (LiteratureSearchResult)
          ▼
┌───────────────────┐
│ DistillationNode  │ (Text Extraction & Citation Pinning)
└─────────┬─────────┘
          │ (DistillationOutput)
          ▼
┌───────────────────┐ ◄─────────────────────────┐
│  SynthesizerNode  │                          │
└─────────┬─────────┘                          │ [Self-Correction Loop]
          │ (Draft VettingReport)              │ (Max Retries Bound)
          ▼                                    │
┌───────────────────┐                          │
│   ValidatorNode   ├──────────────────────────┘
└─────────┬─────────┘ (Failed Physical Constraints)
          │
          ├─────────────────────────┐
          ▼ (Success)               ▼ (Failure)
  End[VettingReport]       End[ValidatorError]

```

The pipeline operates as a deterministic, type-safe state machine utilizing `pydantic_graph`. Context flows synchronously through mutable state variables, ensuring that downstream orchestration logic always consumes structurally validated data from prior nodes.

---

## The Spec-Driven Pattern

This project implements a strict Spec-Driven Development (SDD) workflow using **OpenSpec** to guarantee zero-maintenance stability and complete execution predictability.

* **Living Specifications via OpenSpec:** Rather than relying on unstructured prompts, feature requirements are managed through OpenSpec's delta specs. This ensures the system's "source of truth" documentation evolves bidirectionally with the codebase, trapping hallucinations at the planning stage before implementation begins.
* **Bypassing Framework Bloat (No LangChain/LangGraph):** This repository intentionally avoids the heavy, opaque abstraction layers of the LangChain ecosystem. By orchestrating a native `pydantic_graph` state machine, the control flow is explicitly driven by Python type hints rather than loose graph configurations, ensuring low memory overhead and immediate code scannability.
* **Instant Hallucination Trapping:** Rather than passing unstructured dictionaries or untyped JSON blobs between agent nodes, every system contract is a strict Pydantic `BaseModel`. LLM schema deviations are intercepted at the type level instantly, triggering localized inline self-correction retries inside the current execution span before corrupting downstream states.
* **Decoupled Capabilities via MCP:** All external tool logic (light curve processing, fitting equations, literature indexing) is completely isolated from agent reasoning layers via the open-source Model Context Protocol (MCP). This modular layout creates a zero-maintenance tool infrastructure that can be updated or swapped independently of the core LLM execution configuration.
* **Enterprise-Ready Telemetry (No Vendor Lock-In):** Instrumentation relies entirely on Pydantic Logfire, emitting standard OpenTelemetry spans. Every agent inference, prompt payload, and MCP invocation maps to a continuous `trace_id` out-of-the-box, demonstrating how to plug an AI application directly into existing production APM stacks (like Datadog, AWS CloudWatch, or X-Ray) without vendor lock-in.

---

## Quick Start (Zero-Configuration Cloud Run)

THIS OPERATION IS IN PROGRESS AND NOT CURRENTLY AVAILABLE

This project is fully optimized for **GitHub Codespaces**. Reviewers do not need to configure local Python environments, manage dependencies, or provide personal LLM API keys; the workspace automatically leverages your native `GITHUB_TOKEN` to securely authenticate against the GitHub Models marketplace for free.

1. Click the **Open in GitHub Codespaces** badge above to launch an isolated cloud workspace.
2. Once the terminal initializes in your browser, execute the pipeline script directly:

```bash
python src/main.py --target "KIC-10666592"

```

3. To view full-stack OpenTelemetry execution logs and state transitions immediately, review the auto-generated Logfire local session output linked in the terminal console.