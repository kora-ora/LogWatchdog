"""
Unit tests for Demo Engine (src/demo_engine.py)
"""

import pytest
import numpy as np
import pandas as pd
from src.demo_engine import (
    get_template_desc,
    extract_event_ids,
    calc_metrics,
    get_trigger_source_desc,
    inspect_showcase_forensics,
    DEMO_SHOWCASE_CASES,
    HDFS_TEMPLATES
)
from src.models.deeplog_lstm import DeepLogLSTMModel
from src.models.isolation_forest import IsolationForestModel
from src.models.hybrid_detector import HybridLogDetector


def test_extract_event_ids():
    encoded_str = "<|sep|>0 /10.251.67.211<|sep|>6 <|sep|>14 "
    events = extract_event_ids(encoded_str)
    assert events == [0, 6, 14]


def test_extract_event_ids_empty():
    assert extract_event_ids("") == []


def test_get_template_desc_known():
    desc = get_template_desc(14)
    assert "delete" in desc.lower()


def test_get_template_desc_unknown():
    desc = get_template_desc(9999)
    assert "Event E9999" in desc


def test_calc_metrics():
    y_true = [1, 1, 0, 0]
    y_pred = [1, 0, 1, 0]
    m = calc_metrics(y_true, y_pred)
    assert m["tp"] == 1
    assert m["fn"] == 1
    assert m["fp"] == 1
    assert m["tn"] == 1
    assert m["recall"] == 0.5
    assert m["precision"] == 0.5


def test_get_trigger_source_desc():
    assert "Both" in get_trigger_source_desc(1, 1)
    assert "DeepLog" in get_trigger_source_desc(0, 1)
    assert "Isolation Forest" in get_trigger_source_desc(1, 0)
    assert "Healthy" in get_trigger_source_desc(0, 0)


def test_inspect_showcase_forensics():
    # Setup miniature models
    deeplog = DeepLogLSTMModel(
        vocab_size=15,
        window_size=3,
        hidden_dim=8,
        embedding_dim=8,
        num_layers=1,
        epochs=1,
        lr=0.01,
        top_k=2
    )
    X_seq = np.array([[0, 0, 0], [0, 0, 6]])
    y_seq = np.array([6, 2])
    deeplog.fit(X_seq, y_seq)

    X_train_counts = np.array([
        [3, 0, 1, 0, 0, 0, 1],
        [3, 0, 1, 0, 0, 0, 1]
    ])
    iforest = IsolationForestModel(n_estimators=10, contamination=0.1, random_state=42)
    iforest.fit(X_train_counts)

    case = DEMO_SHOWCASE_CASES[0]
    res = inspect_showcase_forensics(case, deeplog, iforest)

    assert "iforest_pred" in res
    assert "lstm_pred" in res
    assert "hybrid_pred" in res
    assert "triggered_source" in res
    assert "diagnosis" in res
    assert res["actual_label"] == "Normal"
