"""T057 — Integration test: benchmark runner produces valid BenchmarkResult."""

import pytest

pytestmark = pytest.mark.integration


@pytest.mark.skip(reason="Requires network access and full pipeline")
def test_two_object_subset_produces_valid_benchmark_result(tmp_path, monkeypatch):
    """2-object subset → BenchmarkResult schema validates; JSON written to history."""
    import json

    monkeypatch.setattr("src.benchmark.runner._HISTORY_DIR", tmp_path)

    from src.benchmark.runner import run_benchmark
    from src.schemas.benchmark import GoldenDataset, GoldenObject

    dataset = GoldenDataset(
        dataset_version="test-v1",
        source_table="Test Dataset",
        objects=[
            GoldenObject(target_id="KIC-11442793", ground_truth="planet_candidate"),
            GoldenObject(target_id="KIC-3861595", ground_truth="false_positive"),
        ]
        + [GoldenObject(target_id=f"KIC-{i}", ground_truth="planet_candidate") for i in range(38)],
    )

    result = run_benchmark(dataset)

    assert result.run_id is not None
    assert result.dataset_version == "test-v1"
    assert len(result.per_object_results) > 0

    # Check JSON was written
    history_files = list(tmp_path.glob("*.json"))
    assert len(history_files) == 1

    data = json.loads(history_files[0].read_text())
    assert data["run_id"] == result.run_id
