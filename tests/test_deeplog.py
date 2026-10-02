import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
import numpy as np
import torch
import pandas as pd
from src.models.deeplog_lstm import DeepLogLSTMModel, DeepLogNetwork
from src.features.sequence_extractor import SequenceExtractor
from src.ingestion.hdfs_loader import HDFSLogLoader
from src.parsers.drain_parser import DrainParser


def test_deeplog_network_forward():
    """ทดสอบ Forward Pass ของโครงข่าย LSTM"""
    vocab_size = 15
    batch_size = 4
    window_size = 3
    net = DeepLogNetwork(vocab_size=vocab_size, hidden_dim=32, num_layers=1)

    dummy_input = torch.randint(0, vocab_size, (batch_size, window_size))
    logits = net(dummy_input)

    assert logits.shape == (batch_size, vocab_size), "Output ต้องมีขนาด (batch_size, vocab_size)"


def test_deeplog_model_fit_and_predict():
    """ทดสอบการเรียนรู้ลำดับซ้ำๆ ของโมเดล DeepLog"""
    # จำลองลำดับปกติ: 1 -> 2 -> 3 -> 4
    X = np.array([
        [1, 2, 3],
        [1, 2, 3],
        [1, 2, 3],
    ])
    y = np.array([4, 4, 4])

    model = DeepLogLSTMModel(vocab_size=10, window_size=3, epochs=20, lr=0.05, top_k=1)
    model.fit(X, y)

    # ทดสอบว่าโมเดลเดาว่าหลัง [1, 2, 3] คือ 4 หรือไม่
    normal_seq = [1, 2, 3, 4]
    assert model.predict_session(normal_seq) == 0, "ลำดับปกติที่สอนไป ต้องทำนายได้ 0 (Normal)"

    # ทดสอบกรณีลำดับผิดคิว: 1 -> 2 -> 3 -> 9 (ผิดเพี้ยนไปจากที่เรียน)
    anomaly_seq = [1, 2, 3, 9]
    assert model.predict_session(anomaly_seq) == 1, "ลำดับที่ผิดคิว ต้องทำนายได้ 1 (Anomaly)"


def test_end_to_end_deeplog_pipeline():
    """
    ทดสอบการไหลของระบบ DeepLog แบบครบวงจร (Block 1 -> 2 -> 3 -> 4):
    HDFSLogLoader -> DrainParser -> SequenceExtractor -> DeepLogLSTMModel
    """
    loader = HDFSLogLoader("data/raw/hdfs_sample.log")
    parser = DrainParser()
    extractor = SequenceExtractor(window_size=3)

    events = []
    for line in loader.load():
        block_id = HDFSLogLoader.extract_block_id(line)
        parsed = parser.parse_line(line)
        events.append({"session_id": block_id, "template_id": parsed["template_id"]})

    seq_data = extractor.fit_transform(events)
    session_sequences = seq_data["session_sequences"]

    # คัดเลือกเฉพาะ Session ปกติมาสอนโมเดล (Self-Supervised บน Normal Logs)
    normal_block_ids = ["blk_-1608999687919862906", "blk_750348333428938754", "blk_3587508140051195832"]
    normal_events = [e for e in events if e["session_id"] in normal_block_ids]
    
    normal_seq_data = extractor.fit_transform(normal_events)

    model = DeepLogLSTMModel(
        vocab_size=seq_data["vocab_size"] + 2,
        window_size=3,
        hidden_dim=32,
        epochs=30,
        top_k=2
    )
    model.fit(normal_seq_data["X"], normal_seq_data["y"])

    # ทดสอบทำนายทุก Session
    predictions = {b_id: model.predict_session(seq) for b_id, seq in session_sequences.items()}

    assert predictions["blk_-1608999687919862906"] == 0, "blk_-1608 ต้องเป็น Normal"
    assert len(predictions) == 5, "ต้องทำนายครบ 5 Session"


if __name__ == "__main__":
    print("=== ทดสอบ Full DeepLog Pipeline (LSTM Neural Network) ===\n")
    loader = HDFSLogLoader("data/raw/hdfs_sample.log")
    parser = DrainParser()
    extractor = SequenceExtractor(window_size=3)

    events = []
    for line in loader.load():
        block_id = HDFSLogLoader.extract_block_id(line)
        parsed = parser.parse_line(line)
        events.append({"session_id": block_id, "template_id": parsed["template_id"]})

    seq_data = extractor.fit_transform(events)
    session_sequences = seq_data["session_sequences"]

    # 1. เทรน DeepLog ด้วย Normal Logs เท่านั้น
    normal_block_ids = ["blk_-1608999687919862906", "blk_750348333428938754", "blk_3587508140051195832"]
    normal_events = [e for e in events if e["session_id"] in normal_block_ids]
    normal_seq_data = extractor.fit_transform(normal_events)

    print("🧠 กำลังฝึกสอนโมเดล DeepLog (LSTM) ด้วย Normal Sequence...")
    model = DeepLogLSTMModel(
        vocab_size=seq_data["vocab_size"] + 2,
        window_size=3,
        hidden_dim=32,
        epochs=40,
        top_k=2
    )
    model.fit(normal_seq_data["X"], normal_seq_data["y"])
    print("✅ ฝึกสอนเสร็จสิ้น!\n")

    # 2. ทำนายผลและเทียบกับ Ground Truth
    labels_df = pd.read_csv("data/raw/hdfs_labels_sample.csv").set_index("BlockId")

    results = []
    for b_id, seq in session_sequences.items():
        pred = model.predict_session(seq)
        actual = labels_df.loc[b_id, "Label"] if b_id in labels_df.index else "Unknown"
        results.append({
            "Session / Block ID": b_id,
            "Event Sequence": str(seq),
            "Ground Truth": actual,
            "DeepLog (LSTM)": "🚨 ANOMALY" if pred == 1 else "✅ NORMAL"
        })

    result_df = pd.DataFrame(results).set_index("Session / Block ID")
    print("📊 ผลการตรวจจับของ DeepLog (LSTM) เปรียบเทียบกับเฉลยจริง:\n")
    print(result_df.to_string())
