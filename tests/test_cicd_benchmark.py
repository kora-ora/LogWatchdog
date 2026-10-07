import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
import pandas as pd
import numpy as np

from src.ingestion.cicd_loader import CICDLogLoader
from src.parsers.drain_parser import DrainParser
from src.features.sequence_extractor import SequenceExtractor
from src.models.deeplog_lstm import DeepLogLSTMModel
from src.evaluation.metrics import calculate_metrics, format_classification_report


def test_cicd_loader():
    """ทดสอบการโหลด Log CI/CD และดึง Run ID"""
    loader = CICDLogLoader("data/raw/synthetic/cicd_benchmark.log")
    lines = list(loader.load())
    assert len(lines) > 50, "ควรมีบรรทัด Log ไม่ต่ำกว่า 50 บรรทัด"

    # ทดสอบดึง Run ID
    sample_line = lines[0]
    run_id = CICDLogLoader.extract_run_id(sample_line)
    assert run_id == "Run_101"


def test_calculate_metrics_math():
    """ทดสอบความถูกต้องของคณิตศาสตร์คำนวณ Precision, Recall, F1"""
    # จำลอง: 2 Normal (0), 2 Anomaly (1)
    y_true = [0, 0, 1, 1]
    y_pred = [0, 0, 1, 1]
    metrics = calculate_metrics(y_true, y_pred)

    assert metrics["accuracy"] == 1.0
    assert metrics["precision"] == 1.0
    assert metrics["recall"] == 1.0
    assert metrics["f1_score"] == 1.0
    assert metrics["tp"] == 2
    assert metrics["fp"] == 0
    assert metrics["tn"] == 2
    assert metrics["fn"] == 0


def test_end_to_end_cicd_benchmark_deeplog():
    """
    ทดสอบ End-to-End Pipeline บน CI/CD Benchmark จริง:
    CICDLogLoader -> DrainParser -> SequenceExtractor -> DeepLogLSTMModel -> Evaluation
    """
    log_path = "data/raw/synthetic/cicd_benchmark.log"
    label_path = "data/raw/synthetic/cicd_benchmark_labels.csv"

    loader = CICDLogLoader(log_path)
    all_lines = list(loader.load())

    # 1. Strict Session-Level Split (70% Normal Train, 30% Normal Test + All Anomaly Test)
    train_run_ids = set([f"Run_{i}" for i in range(101, 108)])
    test_run_ids = [f"Run_{i}" for i in range(108, 116)]

    train_lines = [l for l in all_lines if CICDLogLoader.extract_run_id(l) in train_run_ids]
    test_lines = [l for l in all_lines if CICDLogLoader.extract_run_id(l) in set(test_run_ids)]

    # 2. Strict Train Fitting: Parser และ Feature Extractor เรียนรู้เฉพาะจาก Train Set เท่านั้น
    parser = DrainParser()
    train_events = []
    for line in train_lines:
        run_id = CICDLogLoader.extract_run_id(line)
        clean_msg = CICDLogLoader.extract_message(line)
        parsed = parser.parse_line(clean_msg, update_model=True)
        train_events.append({
            "session_id": run_id,
            "template_id": parsed["template_id"],
            "line": line
        })

    extractor = SequenceExtractor(window_size=3)
    train_seq_data = extractor.fit_transform(train_events)
    train_vocab_size = train_seq_data["vocab_size"]
    UNKNOWN_TOKEN = train_vocab_size  # Token สำหรับ Event แปลกปลอมที่ไม่เคยเจอใน Train Set

    # 3. Read-Only Inference บน Test Set: ห้ามอัปเดต Parser ป้องกัน Data Leakage 100%
    test_session_sequences = {r_id: [] for r_id in test_run_ids}
    for line in test_lines:
        run_id = CICDLogLoader.extract_run_id(line)
        clean_msg = CICDLogLoader.extract_message(line)
        parsed = parser.parse_line(clean_msg, update_model=False)
        tid = UNKNOWN_TOKEN if parsed["is_unseen"] else parsed["template_id"]
        test_session_sequences[run_id].append(tid)

    # 4. เทรน DeepLog ด้วย Train Set และขนาด Vocab ที่มาจาก Train Set เท่านั้น
    model = DeepLogLSTMModel(
        vocab_size=train_vocab_size + 2,
        window_size=3,
        hidden_dim=32,
        embedding_dim=32,
        num_layers=2,
        epochs=35,
        lr=0.02,
        top_k=2
    )
    model.fit(train_seq_data["X"], train_seq_data["y"])

    # 5. ทำนายผลเฉพาะบน Test Set (Unseen Data)
    labels_df = pd.read_csv(label_path).set_index("RunId")
    y_true = []
    y_pred = []

    for r_id in test_run_ids:
        seq = test_session_sequences[r_id]
        pred = model.predict_session(seq)
        actual = 1 if labels_df.loc[r_id, "Label"] == "Anomaly" else 0
        y_true.append(actual)
        y_pred.append(pred)

    # 6. คำนวณ Metrics
    metrics = calculate_metrics(y_true, y_pred)

    # ตรวจสอบว่าโมเดลตรวจจับ Anomaly ได้จริง และ F1 >= 0.80
    assert metrics["f1_score"] >= 0.80, f"F1-Score ต้องไม่ต่ำกว่า 0.80 (ได้ {metrics['f1_score']})"
    assert metrics["recall"] >= 0.80, f"Recall ต้องไม่ต่ำกว่า 0.80 (ได้ {metrics['recall']})"


if __name__ == "__main__":
    print("\n=======================================================")
    print("🚀 เริ่มการทดสอบ CI/CD Benchmark & Evaluation Run (Strict Zero-Leakage)")
    print("=======================================================\n")

    log_path = "data/raw/synthetic/cicd_benchmark.log"
    label_path = "data/raw/synthetic/cicd_benchmark_labels.csv"

    loader = CICDLogLoader(log_path)
    all_lines = list(loader.load())

    # 1. กำหนด Train/Test Set ที่ระดับ Session (Run ID)
    train_run_ids = set([f"Run_{i}" for i in range(101, 108)])  # 70% Normal
    test_run_ids = [f"Run_{i}" for i in range(108, 116)]         # 30% Normal + All Anomaly

    train_lines = [l for l in all_lines if CICDLogLoader.extract_run_id(l) in train_run_ids]
    test_lines = [l for l in all_lines if CICDLogLoader.extract_run_id(l) in set(test_run_ids)]

    print(f"📦 จำนวนบรรทัด Log ทั้งหมด: {len(all_lines)} บรรทัด (Train: {len(train_lines)}, Test: {len(test_lines)})")
    print(f"🏋️ [Training Set]  ใช้สอนโมเดล (Normal Only): {len(train_run_ids)} runs ({sorted(list(train_run_ids))})")
    print(f"🎯 [Test Set]      ข้อสอบ Unseen (Normal + Anomaly): {len(test_run_ids)} runs ({test_run_ids})\n")

    # 2. Strict Train Fitting: Parser เรียนรู้เฉพาะ Training Data
    parser = DrainParser()
    train_events = []
    for line in train_lines:
        run_id = CICDLogLoader.extract_run_id(line)
        clean_msg = CICDLogLoader.extract_message(line)
        parsed = parser.parse_line(clean_msg, update_model=True)
        train_events.append({
            "session_id": run_id,
            "template_id": parsed["template_id"],
            "line": line
        })

    extractor = SequenceExtractor(window_size=3)
    train_seq_data = extractor.fit_transform(train_events)
    train_vocab_size = train_seq_data["vocab_size"]
    UNKNOWN_TOKEN = train_vocab_size

    print(f"🧩 ค้นพบ Log Template ใน Training Set เท่านั้น: {train_vocab_size} templates")
    print("🔒 โหมดป้องกัน Data Leakage: Drain3 จะไม่เรียนรู้หรือสร้าง Template จาก Test Set เด็ดขาด!\n")

    # 3. Read-Only Inference บน Test Set
    test_session_sequences = {r_id: [] for r_id in test_run_ids}
    for line in test_lines:
        run_id = CICDLogLoader.extract_run_id(line)
        clean_msg = CICDLogLoader.extract_message(line)
        parsed = parser.parse_line(clean_msg, update_model=False)
        tid = UNKNOWN_TOKEN if parsed["is_unseen"] else parsed["template_id"]
        test_session_sequences[run_id].append(tid)

    # 4. สร้างและเทรนโมเดล DeepLog LSTM
    print("🧠 กำลังฝึกสอนโมเดล DeepLog LSTM บน Training Set เท่านั้น...")
    model = DeepLogLSTMModel(
        vocab_size=train_vocab_size + 2,
        window_size=3,
        hidden_dim=32,
        embedding_dim=32,
        num_layers=2,
        epochs=35,
        lr=0.02,
        top_k=2
    )
    model.fit(train_seq_data["X"], train_seq_data["y"])
    print("✅ การฝึกสอนเสร็จสิ้น!\n")

    # 5. ทดสอบทำนายผลเฉพาะบน Test Set (Unseen Data)
    labels_df = pd.read_csv(label_path).set_index("RunId")
    y_true = []
    y_pred = []
    table_rows = []

    for r_id in test_run_ids:
        seq = test_session_sequences[r_id]
        pred = model.predict_session(seq)
        actual_label = labels_df.loc[r_id, "Label"]
        actual = 1 if actual_label == "Anomaly" else 0

        y_true.append(actual)
        y_pred.append(pred)

        status = "✅ ถูกต้อง" if actual == pred else "❌ พลาด"
        table_rows.append({
            "Run ID": r_id,
            "Set Type": "Unseen Normal" if actual == 0 else "Anomaly Case",
            "Ground Truth": actual_label,
            "Prediction": "🚨 Anomaly" if pred == 1 else "✅ Normal",
            "Status": status
        })

    # แสดงตารางผลลัพธ์
    df_result = pd.DataFrame(table_rows).set_index("Run ID")
    print("📋 ตารางผลการทดสอบบนข้อสอบที่ไม่เคยเห็นมาก่อน (Zero-Leakage Unseen Test Set):")
    print(df_result.to_string())
    print()

    # คำนวณและแสดง Evaluation Report
    metrics = calculate_metrics(y_true, y_pred)
    report_text = format_classification_report(metrics, model_name="Zero-Leakage DeepLog 2-Layer LSTM")
    print(report_text)
