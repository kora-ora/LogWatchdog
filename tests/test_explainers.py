import os
import sys
import pytest
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.models.deeplog_lstm import DeepLogLSTMModel
from src.explainers.deeplog_explainer import DeepLogExplainer


@pytest.fixture
def trained_model_and_vocab():
    """
    Fixture สร้างโมเดล DeepLog ที่เรียนรู้ลำดับขั้นตอนปกติ:
    Normal Sequence: [1, 2, 3, 4, 5]
    """
    vocab_size = 10
    model = DeepLogLSTMModel(
        vocab_size=vocab_size,
        window_size=3,
        hidden_dim=32,
        embedding_dim=32,
        num_layers=1,
        epochs=40,
        lr=0.03,
        top_k=1
    )

    # ข้อมูลเทรน: ลำดับ 1 -> 2 -> 3 -> 4 และ 2 -> 3 -> 4 -> 5
    X = np.array([
        [1, 2, 3],
        [2, 3, 4]
    ])
    y = np.array([4, 5])
    model.fit(X, y)

    template_vocab = {
        1: "[Step: Checkout] Git checkout",
        2: "[Step: Setup] Setup Python",
        3: "[Step: Install] Install dependencies",
        4: "[Step: Test] Run pytest",
        5: "[Step: Deploy] Deploy to server",
        9: "[Step: Deploy] Deploy directly without test",
        99: "[Error] Fatal kernel panic"
    }

    return model, template_vocab


def test_explainer_normal_session(trained_model_and_vocab):
    """ทดสอบว่าเคสปกติ Explainer ต้องตอบว่าไม่พบ Anomaly"""
    model, vocab = trained_model_and_vocab
    explainer = DeepLogExplainer(model, vocab)

    normal_events = [
        {"line_number": 1, "raw_line": "Checkout code", "template_id": 1, "template_str": vocab[1]},
        {"line_number": 2, "raw_line": "Setup Python", "template_id": 2, "template_str": vocab[2]},
        {"line_number": 3, "raw_line": "Install deps", "template_id": 3, "template_str": vocab[3]},
        {"line_number": 4, "raw_line": "Run pytest", "template_id": 4, "template_str": vocab[4]},
        {"line_number": 5, "raw_line": "Deploy app", "template_id": 5, "template_str": vocab[5]},
    ]

    report = explainer.explain_session(normal_events, session_id="Run_Normal")
    assert report["is_anomaly"] is False
    assert "Run_Normal" in explainer.format_incident_report(report)


def test_explainer_oov_anomaly_localization(trained_model_and_vocab):
    """ทดสอบการชี้เป้าเคสข้อความแปลกปลอม (OOV): ต้องบอกบรรทัดและข้อความที่เกิดเหตุได้ถูกต้อง"""
    model, vocab = trained_model_and_vocab
    explainer = DeepLogExplainer(model, vocab)

    # บรรทัดที่ 3 เกิด Fatal Error (Event ID 99 ซึ่งไม่เคยมีใน Train)
    anomaly_events = [
        {"line_number": 10, "raw_line": "Checkout code", "template_id": 1, "template_str": vocab[1]},
        {"line_number": 11, "raw_line": "Setup Python", "template_id": 2, "template_str": vocab[2]},
        {"line_number": 12, "raw_line": "FATAL: kernel panic out of memory", "template_id": 99, "template_str": vocab[99]},
        {"line_number": 13, "raw_line": "Install deps", "template_id": 3, "template_str": vocab[3]},
    ]

    report = explainer.explain_session(anomaly_events, session_id="Run_OOV_Test")
    assert report["is_anomaly"] is True
    assert report["anomaly_type"] == "Unseen Event / Out-of-Vocabulary (OOV)"
    assert report["culprit_line_number"] == 12
    assert "FATAL: kernel panic" in report["culprit_raw_line"]
    assert report["culprit_template_id"] == 99

    # ทดสอบการฟอร์แมตรายงาน
    formatted_text = explainer.format_incident_report(report)
    assert "INCIDENT DIAGNOSTIC REPORT" in formatted_text
    assert "บรรทัดที่ 12" in formatted_text
    assert "[CULPRIT]" in formatted_text


def test_explainer_sequential_violation_localization(trained_model_and_vocab):
    """ทดสอบการชี้เป้าเคสข้ามขั้นตอน (Step Skipping): ต้องชี้จุดผิดคิวและแสดงสิ่งที่ AI คาดหวัง"""
    model, vocab = trained_model_and_vocab
    explainer = DeepLogExplainer(model, vocab)

    # หลัง 1, 2, 3 ควรเป็น 4 (Test) แต่ดันกระโดดข้ามไป 5 (Deploy)
    # ทั้ง 1, 2, 3, 5 ล้วนเป็น Event ปกติใน normal_vocab แต่ลำดับผิดคิว
    anomaly_events = [
        {"line_number": 101, "raw_line": "Checkout code", "template_id": 1, "template_str": vocab[1]},
        {"line_number": 102, "raw_line": "Setup Python", "template_id": 2, "template_str": vocab[2]},
        {"line_number": 103, "raw_line": "Install deps", "template_id": 3, "template_str": vocab[3]},
        {"line_number": 104, "raw_line": "Deploy directly without test!", "template_id": 5, "template_str": vocab[5]},
    ]

    report = explainer.explain_session(anomaly_events, session_id="Run_Sequential_Skip")
    assert report["is_anomaly"] is True
    assert report["anomaly_type"] == "Sequential Violation / Step Skipping"
    assert report["culprit_line_number"] == 104
    assert report["culprit_template_id"] == 5
    assert len(report["expected_events"]) > 0

    # ตรวจสอบว่าใน expected events ต้องมี Event 4
    expected_ids = [e["template_id"] for e in report["expected_events"]]
    assert 4 in expected_ids

    # ทดสอบการเรนเดอร์รายงาน
    formatted_text = explainer.format_incident_report(report)
    assert "Sequential Violation / Step Skipping" in formatted_text
    assert "Expected vs Actual" in formatted_text
    assert "บรรทัดที่ 104" in formatted_text
