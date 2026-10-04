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
    loader = CICDLogLoader("data/raw/cicd_benchmark.log")
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
    log_path = "data/raw/cicd_benchmark.log"
    label_path = "data/raw/cicd_benchmark_labels.csv"

    # 1. Ingestion
    loader = CICDLogLoader(log_path)
    parser = DrainParser()
    extractor = SequenceExtractor(window_size=3)

    events = []
    for line in loader.load():
        run_id = CICDLogLoader.extract_run_id(line)
        clean_msg = CICDLogLoader.extract_message(line)
        parsed = parser.parse_line(clean_msg)
        events.append({
            "session_id": run_id,
            "template_id": parsed["template_id"],
            "line": line
        })

    # 2. Extract sequences
    seq_data = extractor.fit_transform(events)
    session_sequences = seq_data["session_sequences"]
    vocab_size = seq_data["vocab_size"]

    # 3. แยกชุดฝึกสอนเฉพาะรอบปกติ (Run_101 ถึง Run_110)
    normal_run_ids = [f"Run_{i}" for i in range(101, 111)]
    normal_events = [e for e in events if e["session_id"] in normal_run_ids]
    normal_seq_data = extractor.fit_transform(normal_events)

    # 4. เทรน DeepLog ด้วย Normal Runs (ปรับ batch_size, epochs ตามขนาดข้อมูล)
    model = DeepLogLSTMModel(
        vocab_size=vocab_size + 2,
        window_size=3,
        hidden_dim=32,
        embedding_dim=32,
        num_layers=2,
        epochs=30,
        lr=0.02,
        top_k=2
    )
    model.fit(normal_seq_data["X"], normal_seq_data["y"])

    # 5. ทำนายทุก Session
    predictions = {}
    for r_id, seq in session_sequences.items():
        pred = model.predict_session(seq)
        predictions[r_id] = pred

    # 6. อ่าน Ground Truth
    labels_df = pd.read_csv(label_path).set_index("RunId")
    y_true = []
    y_pred = []

    for r_id in labels_df.index:
        if r_id in predictions:
            actual = 1 if labels_df.loc[r_id, "Label"] == "Anomaly" else 0
            predicted = predictions[r_id]
            y_true.append(actual)
            y_pred.append(predicted)

    # 7. คำนวณ Metrics
    metrics = calculate_metrics(y_true, y_pred)

    # ตรวจสอบว่าโมเดลตรวจจับ Anomaly ได้จริง และ F1 >= 0.80
    assert metrics["f1_score"] >= 0.80, f"F1-Score ต้องไม่ต่ำกว่า 0.80 (ได้ {metrics['f1_score']})"
    assert metrics["recall"] >= 0.80, f"Recall ต้องไม่ต่ำกว่า 0.80 (ได้ {metrics['recall']})"


if __name__ == "__main__":
    print("\n=======================================================")
    print("🚀 เริ่มการทดสอบ CI/CD Benchmark & Evaluation Run")
    print("=======================================================\n")

    log_path = "data/raw/cicd_benchmark.log"
    label_path = "data/raw/cicd_benchmark_labels.csv"

    loader = CICDLogLoader(log_path)
    parser = DrainParser()
    extractor = SequenceExtractor(window_size=3)

    events = []
    for line in loader.load():
        run_id = CICDLogLoader.extract_run_id(line)
        clean_msg = CICDLogLoader.extract_message(line)
        parsed = parser.parse_line(clean_msg)
        events.append({
            "session_id": run_id,
            "template_id": parsed["template_id"],
            "line": line
        })

    seq_data = extractor.fit_transform(events)
    session_sequences = seq_data["session_sequences"]
    vocab_size = seq_data["vocab_size"]

    print(f"📦 จำนวนบรรทัด Log ทั้งหมด: {len(events)} บรรทัด")
    print(f"🧩 ค้นพบ Log Template (Vocabulary Size): {vocab_size} templates")
    print(f"🔄 จำนวน CI/CD Runs: {len(session_sequences)} runs\n")

    # เทรนด้วย Normal Runs
    normal_run_ids = [f"Run_{i}" for i in range(101, 111)]
    normal_events = [e for e in events if e["session_id"] in normal_run_ids]
    normal_seq_data = extractor.fit_transform(normal_events)

    print("🧠 กำลังฝึกสอนโมเดล DeepLog LSTM บน Normal Runs (Run 101 - 110)...")
    model = DeepLogLSTMModel(
        vocab_size=vocab_size + 2,
        window_size=3,
        hidden_dim=32,
        embedding_dim=32,
        num_layers=2,
        epochs=35,
        lr=0.02,
        top_k=2
    )
    model.fit(normal_seq_data["X"], normal_seq_data["y"])
    print("✅ การฝึกสอนเสร็จสิ้น!\n")

    # ทดสอบทำนายผล
    labels_df = pd.read_csv(label_path).set_index("RunId")
    y_true = []
    y_pred = []
    table_rows = []

    for r_id in labels_df.index:
        if r_id in session_sequences:
            seq = session_sequences[r_id]
            pred = model.predict_session(seq)
            actual_label = labels_df.loc[r_id, "Label"]
            actual = 1 if actual_label == "Anomaly" else 0

            y_true.append(actual)
            y_pred.append(pred)

            status = "✅ ถูกต้อง" if actual == pred else "❌ พลาด"
            table_rows.append({
                "Run ID": r_id,
                "Ground Truth": actual_label,
                "Prediction": "🚨 Anomaly" if pred == 1 else "✅ Normal",
                "Status": status
            })

    # แสดงตารางผลลัพธ์
    df_result = pd.DataFrame(table_rows).set_index("Run ID")
    print("📋 ตารางเปรียบเทียบผลการทำนายรายรอบ (Run Comparison Table):")
    print(df_result.to_string())
    print()

    # คำนวณและแสดง Evaluation Report
    metrics = calculate_metrics(y_true, y_pred)
    report_text = format_classification_report(metrics, model_name="DeepLog 2-Layer LSTM")
    print(report_text)
