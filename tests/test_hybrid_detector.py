import os
import sys
import pytest
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.models.isolation_forest import IsolationForestModel
from src.models.deeplog_lstm import DeepLogLSTMModel
from src.models.hybrid_detector import HybridLogDetector


@pytest.fixture
def mock_submodels():
    # Setup simple iForest
    X_train = np.array([
        [1, 2, 3],
        [1, 2, 3],
        [1, 2, 3],
        [1, 2, 3]
    ])
    iforest = IsolationForestModel(n_estimators=10, contamination=0.1, random_state=42)
    iforest.fit(X_train)

    # Setup simple DeepLog
    deeplog = DeepLogLSTMModel(
        vocab_size=10,
        window_size=3,
        hidden_dim=16,
        embedding_dim=16,
        num_layers=1,
        epochs=10,
        lr=0.01,
        top_k=1
    )
    X_seq = np.array([[1, 2, 3]])
    y_seq = np.array([4])
    deeplog.fit(X_seq, y_seq)

    return iforest, deeplog


def test_hybrid_detector_initialization(mock_submodels):
    iforest, deeplog = mock_submodels
    detector_or = HybridLogDetector(iforest, deeplog, strategy="or")
    detector_and = HybridLogDetector(iforest, deeplog, strategy="and")

    assert detector_or.strategy == "or"
    assert detector_and.strategy == "and"

    with pytest.raises(ValueError):
        HybridLogDetector(iforest, deeplog, strategy="invalid_strategy")


def test_hybrid_detector_or_voting_behavior(mock_submodels):
    iforest, deeplog = mock_submodels
    detector = HybridLogDetector(iforest, deeplog, strategy="or")

    # Case 1: normal count, normal sequence
    # Normal sequence [1, 2, 3, 4]
    res1 = detector.predict_session(np.array([1, 2, 3]), [1, 2, 3, 4])
    assert "prediction" in res1
    assert "triggered_by" in res1

    # Case 2: normal count, anomalous sequence [1, 2, 3, 9] (DeepLog flags)
    res2 = detector.predict_session(np.array([1, 2, 3]), [1, 2, 3, 9])
    assert res2["deeplog_pred"] == 1
    assert res2["prediction"] == 1
    assert "DeepLog LSTM" in res2["triggered_by"][0]


def test_hybrid_detector_synergy_behavior(mock_submodels):
    iforest, deeplog = mock_submodels
    detector = HybridLogDetector(iforest, deeplog, strategy="synergy")

    # Case 1: normal count, normal sequence
    res1 = detector.predict_session(np.array([1, 2, 3]), [1, 2, 3, 4])
    assert "prediction" in res1
    assert res1["prediction"] == 0

    # Case 2: predict batch
    cv_matrix = np.array([[1, 2, 3], [1, 2, 3]])
    seqs = [[1, 2, 3, 4], [1, 2, 3, 9]]
    batch_res = detector.predict_batch(cv_matrix, seqs)
    assert len(batch_res) == 2
    assert "prediction" in batch_res[0]
    assert "prediction" in batch_res[1]
