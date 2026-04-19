"""T009 — Unit tests for BenchmarkResult schema."""

import pytest
from pydantic import ValidationError

from src.schemas.benchmark import BenchmarkResult, GoldenDataset, GoldenObject, ObjectResult


def _valid_object_result(**overrides) -> dict:
    base = {
        "target_id": "KIC-11442793",
        "ground_truth": "planet_candidate",
        "prediction": "planet_candidate",
    }
    base.update(overrides)
    return base


def _valid_benchmark(**overrides) -> dict:
    base = {
        "dataset_version": "2026-04-09-abc123",
        "true_positives": 15,
        "false_positives": 3,
        "true_negatives": 17,
        "false_negatives": 5,
        "precision": 0.833,
        "recall": 0.75,
        "f1": 0.789,
        "per_object_results": [ObjectResult(**_valid_object_result())],
    }
    base.update(overrides)
    return base


def test_valid_benchmark_result():
    r = BenchmarkResult(**_valid_benchmark())
    assert r.true_positives == 15
    assert r.run_id is not None  # auto-generated UUID


def test_negative_tp_raises():
    with pytest.raises(ValidationError):
        BenchmarkResult(**_valid_benchmark(true_positives=-1))


def test_negative_fp_raises():
    with pytest.raises(ValidationError):
        BenchmarkResult(**_valid_benchmark(false_positives=-1))


def test_negative_tn_raises():
    with pytest.raises(ValidationError):
        BenchmarkResult(**_valid_benchmark(true_negatives=-1))


def test_negative_fn_raises():
    with pytest.raises(ValidationError):
        BenchmarkResult(**_valid_benchmark(false_negatives=-1))


def test_f1_computed_from_known_values():
    """TP=10, FP=5, TN=15, FN=5 → precision=0.667, recall=0.667, F1≈0.667."""
    tp, fp, tn, fn = 10, 5, 15, 5
    precision = tp / (tp + fp)
    recall = tp / (tp + fn)
    f1 = 2 * precision * recall / (precision + recall)
    r = BenchmarkResult(
        **_valid_benchmark(
            true_positives=tp,
            false_positives=fp,
            true_negatives=tn,
            false_negatives=fn,
            precision=precision,
            recall=recall,
            f1=f1,
        )
    )
    assert abs(r.f1 - 0.6667) < 0.001


def test_zero_tp_fp_benchmark_accepted():
    """All correct (no false positives) is a valid result."""
    r = BenchmarkResult(
        **_valid_benchmark(false_positives=0, true_positives=20, false_negatives=0, precision=1.0, recall=1.0, f1=1.0)
    )
    assert r.f1 == 1.0


def test_empty_per_object_results_raises():
    with pytest.raises(ValidationError):
        BenchmarkResult(**_valid_benchmark(per_object_results=[]))


def test_golden_dataset_min_40_objects():
    objects = [GoldenObject(target_id=f"KIC-{i}", ground_truth="planet_candidate") for i in range(39)]
    with pytest.raises(ValidationError):
        GoldenDataset(dataset_version="v1", source_table="KOI table", objects=objects)


def test_golden_dataset_40_objects_accepted():
    objects = [GoldenObject(target_id=f"KIC-{i}", ground_truth="planet_candidate") for i in range(40)]
    ds = GoldenDataset(dataset_version="v1", source_table="KOI table", objects=objects)
    assert len(ds.objects) == 40
