import os
import sys
import re
import time
import numpy as np
import pandas as pd
from collections import defaultdict
from typing import Dict, List, Any

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.parsers.drain_parser import DrainParser
from src.features.count_vector import CountVectorBuilder
from src.features.sequence_extractor import SequenceExtractor
from src.models.isolation_forest import IsolationForestModel
from src.models.deeplog_lstm import DeepLogLSTMModel
from src.evaluation.metrics import calculate_metrics, format_classification_report


def run_loghub_hdfs_benchmark():
    print("=" * 80)
    print("🏛️ LOGHUB HDFS BENCHMARK (Real Production Distributed Cluster)")
    print("=" * 80)

    log_path = "data/raw/loghub_hdfs/HDFS_100k.log"
    label_path = "data/raw/loghub_hdfs/anomaly_label.csv"

    if not os.path.exists(log_path) or not os.path.exists(label_path):
        print(f"❌ Error: Required files not found in data/raw/loghub_hdfs/")
        return

    # 1. โหลด Ground Truth Labels
    print("\n[สเต็ปที่ 1] 📥 โหลด Ground-Truth Labels จากวิศวกรระบบ Hadoop...")
    labels_df = pd.read_csv(label_path).set_index("BlockId")

    # 2. แยก Block และสตรีม Log
    print("[สเต็ปที่ 2] 🧱 สกัด Block ID และแปลงข้อความด้วย DrainParser (Train Mode)...")
    pattern = re.compile(r"blk_-?\d+")
    parser = DrainParser()

    block_events = defaultdict(list)
    line_count = 0
    t0 = time.time()

    with open(log_path, "r", errors="ignore") as f:
        for line_no, line in enumerate(f, start=1):
            clean = line.strip()
            if not clean:
                continue
            line_count += 1
            m = pattern.search(clean)
            if m:
                bid = m.group()
                # Parse line to template
                p = parser.parse_line(clean, update_model=True)
                block_events[bid].append({
                    "line_number": line_no,
                    "raw_line": clean,
                    "template_id": p["template_id"]
                })

    t_parse = time.time() - t0
    print(f"   -> ประมวลผล Log ทั้งหมด {line_count:,} บรรทัด ในเวลา {t_parse:.2f} วินาที")
    print(f"   -> สกัดได้ {len(block_events):,} Block Sessions (พบ {len(parser.miner.drain.id_to_cluster):,} Unique Templates)")

    # 3. จัดการแบ่ง Train / Test Set อย่างเคร่งครัด
    normal_blocks = [b for b in block_events if labels_df.loc[b, "Label"] == "Normal"]
    anomaly_blocks = [b for b in block_events if labels_df.loc[b, "Label"] == "Anomaly"]

    TRAIN_NORMAL_COUNT = 5000
    train_block_ids = normal_blocks[:TRAIN_NORMAL_COUNT]
    test_normal_block_ids = normal_blocks[TRAIN_NORMAL_COUNT:]
    test_anomaly_block_ids = anomaly_blocks

    test_block_ids = test_normal_block_ids + test_anomaly_block_ids

    train_lines = sum(len(block_events[b]) for b in train_block_ids)
    test_lines = sum(len(block_events[b]) for b in test_block_ids)

    print("\n" + "-" * 80)
    print("📏 ขนาดและสัดส่วนของข้อมูล (Dataset Size & Train/Test Split):")
    print("-" * 80)
    print(f"• [ชุดฝึกสอน - Training Set] (Normal 100%):")
    print(f"   - จำนวน Block Sessions: {len(train_block_ids):,} Blocks (ปกติทั้งหมด)")
    print(f"   - ปริมาณ Log lines:     {train_lines:,} บรรทัด")
    print(f"• [ชุดทดสอบ - Testing Set] (ข้อสอบท้าทายความจริง):")
    print(f"   - จำนวน Block Sessions: {len(test_block_ids):,} Blocks")
    print(f"      ├─ Normal Blocks:    {len(test_normal_block_ids):,} Blocks")
    print(f"      └─ Real Anomalies:   {len(test_anomaly_block_ids):,} Blocks (Anomaly Rate: {len(test_anomaly_block_ids)/len(test_block_ids)*100:.2f}%)")
    print(f"   - ปริมาณ Log lines:     {test_lines:,} บรรทัด")
    print("-" * 80)

    # 4. สกัด Features สำหรับ Train
    print("\n[สเต็ปที่ 3] ⚙️ สกัด Features สำหรับ Isolation Forest และ DeepLog...")
    train_flat_events = []
    for bid in train_block_ids:
        for ev in block_events[bid]:
            train_flat_events.append({"session_id": bid, "template_id": ev["template_id"]})

    # 4A. iForest Feature: CountVector
    count_builder = CountVectorBuilder()
    df_train_counts = count_builder.fit_transform(train_flat_events)

    # 4B. DeepLog Feature: SequenceExtractor (Sliding Window w=3)
    seq_extractor = SequenceExtractor(window_size=3)
    train_seq_data = seq_extractor.fit_transform(train_flat_events)
    train_vocab_size = train_seq_data["vocab_size"]

    # 5. ฝึกสอนโมเดลทั้งสองตัว
    print(f"\n[สเต็ปที่ 4] 🌲 ฝึกสอน Isolation Forest บน {len(train_block_ids):,} Normal Blocks...")
    t0_if = time.time()
    iforest = IsolationForestModel(n_estimators=100, contamination=0.01, random_state=42)
    iforest.fit(df_train_counts.values)
    print(f"   -> iForest ฝึกสอนเสร็จสิ้นใน {time.time() - t0_if:.2f} วินาที")

    print(f"\n[สเต็ปที่ 5] 🤖 ฝึกสอน DeepLog LSTM บน {len(train_seq_data['X']):,} Sequential Pairs...")
    t0_lstm = time.time()
    deeplog = DeepLogLSTMModel(
        vocab_size=train_vocab_size + 2,
        window_size=3,
        hidden_dim=32,
        embedding_dim=32,
        num_layers=2,
        epochs=5,
        lr=0.01,
        top_k=5
    )
    deeplog.fit(train_seq_data["X"], train_seq_data["y"])
    print(f"   -> DeepLog LSTM ฝึกสอนเสร็จสิ้นใน {time.time() - t0_lstm:.2f} วินาที")

    # 6. เตรียม Test Data
    print(f"\n[สเต็ปที่ 6] 🎯 ทดสอบบน {len(test_block_ids):,} Test Blocks (Normal {len(test_normal_block_ids)} + Anomaly {len(test_anomaly_block_ids)})...")
    test_flat_events = []
    test_sessions_seq = {}
    y_true = []

    for bid in test_block_ids:
        seq = [ev["template_id"] for ev in block_events[bid]]
        test_sessions_seq[bid] = seq
        for ev in block_events[bid]:
            test_flat_events.append({"session_id": bid, "template_id": ev["template_id"]})
        y_true.append(1 if labels_df.loc[bid, "Label"] == "Anomaly" else 0)

    # 6A. ทำนายด้วย Isolation Forest
    df_test_counts = count_builder.transform(test_flat_events)
    df_test_counts = df_test_counts.reindex(test_block_ids).fillna(0)
    preds_iforest = iforest.predict(df_test_counts.values)

    # 6B. ทำนายด้วย DeepLog LSTM
    preds_deeplog = []
    for bid in test_block_ids:
        preds_deeplog.append(deeplog.predict_session(test_sessions_seq[bid]))
    preds_deeplog = np.array(preds_deeplog)

    # 6C. Ensemble Strategies
    preds_or = np.where((preds_deeplog == 1) | (preds_iforest == 1), 1, 0)
    preds_and = np.where((preds_deeplog == 1) & (preds_iforest == 1), 1, 0)

    # 7. คำนวณและเปรียบเทียบ Metrics
    m_iforest = calculate_metrics(y_true, preds_iforest)
    m_deeplog = calculate_metrics(y_true, preds_deeplog)
    m_or = calculate_metrics(y_true, preds_or)
    m_and = calculate_metrics(y_true, preds_and)

    summary = [
        {
            "Model / Strategy": "1. Isolation Forest (Count Vector)",
            "Accuracy": f"{m_iforest['accuracy']*100:.2f}%",
            "Precision": f"{m_iforest['precision']*100:.2f}%",
            "Recall": f"{m_iforest['recall']*100:.2f}%",
            "F1-Score": f"{m_iforest['f1_score']*100:.2f}%",
            "FP (False Alarms)": m_iforest["fp"],
            "FN (Missed)": m_iforest["fn"]
        },
        {
            "Model / Strategy": "2. DeepLog LSTM (Sequential)",
            "Accuracy": f"{m_deeplog['accuracy']*100:.2f}%",
            "Precision": f"{m_deeplog['precision']*100:.2f}%",
            "Recall": f"{m_deeplog['recall']*100:.2f}%",
            "F1-Score": f"{m_deeplog['f1_score']*100:.2f}%",
            "FP (False Alarms)": m_deeplog["fp"],
            "FN (Missed)": m_deeplog["fn"]
        },
        {
            "Model / Strategy": "3. Ensemble (Union / OR-Voting)",
            "Accuracy": f"{m_or['accuracy']*100:.2f}%",
            "Precision": f"{m_or['precision']*100:.2f}%",
            "Recall": f"{m_or['recall']*100:.2f}%",
            "F1-Score": f"{m_or['f1_score']*100:.2f}%",
            "FP (False Alarms)": m_or["fp"],
            "FN (Missed)": m_or["fn"]
        },
        {
            "Model / Strategy": "4. Ensemble (Intersect / AND-Voting)",
            "Accuracy": f"{m_and['accuracy']*100:.2f}%",
            "Precision": f"{m_and['precision']*100:.2f}%",
            "Recall": f"{m_and['recall']*100:.2f}%",
            "F1-Score": f"{m_and['f1_score']*100:.2f}%",
            "FP (False Alarms)": m_and["fp"],
            "FN (Missed)": m_and["fn"]
        },
    ]

    print("\n" + "=" * 80)
    print("🏆 FINAL COMPARATIVE BENCHMARK RESULTS ON LOGHUB HDFS")
    print("=" * 80)
    df_summary = pd.DataFrame(summary).set_index("Model / Strategy")
    print(df_summary.to_string())
    print("=" * 80)


if __name__ == "__main__":
    run_loghub_hdfs_benchmark()
