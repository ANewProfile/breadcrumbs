from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock
import pytest
from bson import ObjectId
from services.estimation import compute_subject_history, weighted_estimate

NOW = datetime(2026, 8, 1, tzinfo=timezone.utc)
USER_ID = ObjectId()


def history_entry(ratio: float, days_ago: int) -> dict:
    return {"ratio": ratio, "completed_at": NOW - timedelta(days=days_ago)}


def test_weighted_estimate_below_threshold_uses_raw_user_estimate():
    history = [history_entry(2.0, days_ago=i) for i in range(3)]  # only 3 samples
    estimate, learned = weighted_estimate(30, history)
    assert estimate == 30.0
    assert learned is False


def test_weighted_estimate_no_history():
    estimate, learned = weighted_estimate(30, [])
    assert estimate == 30.0
    assert learned is False


def test_weighted_estimate_uniform_ratio_blends_toward_that_ratio():
    # every past task in this subject ran exactly 1.5x its estimate
    history = [history_entry(1.5, days_ago=i) for i in range(5)]
    estimate, learned = weighted_estimate(100, history)
    assert learned is True
    # blended_ratio = 0.6*1.5 + 0.4*1.0 = 1.3 -> estimate = 130
    assert estimate == pytest.approx(130.0)


def test_weighted_estimate_no_deviation_leaves_estimate_unchanged():
    history = [history_entry(1.0, days_ago=i) for i in range(6)]
    estimate, learned = weighted_estimate(45, history)
    assert learned is True
    assert estimate == 45.0


def test_recent_deviation_outweighs_an_equally_sized_old_one():
    # Same multiset of ratios {2.0, 1.0, 1.0, 1.0, 1.0} in both cases — only the
    # chronological position of the outlier (2.0) differs.
    outlier_recent = [history_entry(2.0, days_ago=0)] + [
        history_entry(1.0, days_ago=i) for i in range(1, 5)
    ]
    outlier_old = [history_entry(1.0, days_ago=i) for i in range(0, 4)] + [
        history_entry(2.0, days_ago=100)
    ]

    estimate_recent, _ = weighted_estimate(100, outlier_recent)
    estimate_old, _ = weighted_estimate(100, outlier_old)

    # A plain unweighted average would give the identical result either way
    # (naive mean of {2,1,1,1,1} = 1.2 regardless of order). Recency weighting
    # should pull the "outlier recent" case higher and "outlier old" case lower.
    assert estimate_recent > estimate_old


def test_compute_subject_history_computes_ratio_and_filters_by_status():
    mock_collection = MagicMock()
    mock_collection.find.return_value = [
        {"estimated_minutes": 30, "actual_minutes": [45], "completed_at": NOW},
        {"estimated_minutes": 20, "actual_minutes": [10, 30], "completed_at": NOW},
    ]

    history = compute_subject_history(mock_collection, USER_ID, "Chemistry")

    mock_collection.find.assert_called_once_with(
        {"user_id": USER_ID, "subject": "Chemistry", "status": "done"},
        {"estimated_minutes": 1, "actual_minutes": 1, "completed_at": 1},
    )
    ratios = sorted(h["ratio"] for h in history)
    assert ratios == [0.5, 1.5, 1.5]


def test_compute_subject_history_skips_tasks_with_no_estimate():
    mock_collection = MagicMock()
    mock_collection.find.return_value = [
        {"estimated_minutes": 0, "actual_minutes": [20], "completed_at": NOW},
        {"actual_minutes": [20], "completed_at": NOW},
    ]

    history = compute_subject_history(mock_collection, USER_ID, "Chemistry")
    assert history == []


def test_compute_subject_history_handles_missing_completed_at():
    mock_collection = MagicMock()
    mock_collection.find.return_value = [
        {"estimated_minutes": 30, "actual_minutes": [30]},
    ]

    history = compute_subject_history(mock_collection, USER_ID, "Chemistry")
    assert len(history) == 1
    assert history[0]["ratio"] == 1.0
    assert history[0]["completed_at"] is not None
