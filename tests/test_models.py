import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
import numpy as np
import pandas as pd
from src.models.isolation_forest import IsolationForestModel
from src.ingestion.hdfs_loader import HDFSLogLoader
from src.parsers.drain_parser import DrainParser
from src.features.count_vector import CountVectorBuilder


def test_isolation_forest_basic_flow():
    """ทดสอบการ fit และ predict บนข้อมูลตัวเลขจำลอง"""
    # สร้างข้อมูลจำลอง: 10 แถวปกติ, 1 แถวผิดปกติ
    X_train = np.array([
        [1, 2, 1, 0],
        [1, 2, 1, 0],
        [1, 2, 1, 0],
        [1, 2, 1, 0],
        [1, 2, 1, 0],
        [1, 2, 1, 0],
        [1, 2, 1, 0],
        [1, 2, 1, 0],
        [1, 2, 1, 0],
        [0, 0, 0, 50],  # ผิดปกติชัดเจน
    ])

    model = IsolationForestModel(contamination=0.1, random_state=42)
    try:
        model.fit(X_train)
        preds = model.predict(X_train)
        
        assert isinstance(preds, np.ndarray), "ผลลัพธ์ predict ต้องเป็น numpy array"
        assert len(preds) == len(X_train), "จำนวนผลทำนายต้องเท่ากับจำนวนแถว"
        # แถวสุดท้ายที่มี 50 ควรถูกมองเป็น Anomaly (1)
        assert preds[-1] == 1, "แถวที่ผิดปกติ [0, 0, 0, 50] ควรได้ label 1 (Anomaly)"
        # แถวแรกควรเป็น Normal (0)
        assert preds[0] == 0, "แถวปกติควรได้ label 0 (Normal)"
    except NotImplementedError:
        pytest.skip("IsolationForestModel ยังไม่ได้ถูกเขียน (รอให้คุณลงมือเขียน)")


def test_end_to_end_full_pipeline():
    """
    ทดสอบการต่อประสานครบ 4 บล็อก (End-to-End Pipeline):
    Block 1 (Loader) -> Block 2 (Parser) -> Block 3 (Feature) -> Block 4 (Model)
    """
    loader = HDFSLogLoader("data/raw/hdfs_sample.log")
    parser = DrainParser()
    builder = CountVectorBuilder()

    # 1. รัน Data Pipeline
    events = []
    for line in loader.load():
        block_id = HDFSLogLoader.extract_block_id(line)
        parsed = parser.parse_line(line)
        events.append({"session_id": block_id, "template_id": parsed["template_id"]})

    feature_matrix = builder.fit_transform(events)

    # 2. รัน Model Block
    model = IsolationForestModel(contamination=0.4, random_state=42)
    try:
        model.fit(feature_matrix)
        preds = model.predict(feature_matrix)
        
        assert len(preds) == len(feature_matrix)
        # ตรวจสอบว่าใน 5 sessions มีทั้ง normal (0) และ anomaly (1)
        assert 1 in preds, "ต้องสามารถตรวจจับ Anomaly ได้อย่างน้อย 1 รายการ"
    except NotImplementedError:
        pytest.skip("IsolationForestModel ยังไม่ได้ถูกเขียน (รอให้คุณลงมือเขียน)")


if __name__ == "__main__":
    print("=== ทดสอบ Full Pipeline (Block 1 -> 2 -> 3 -> 4) ===\n")
    loader = HDFSLogLoader("data/raw/hdfs_sample.log")
    parser = DrainParser()
    builder = CountVectorBuilder()

    events = []
    for line in loader.load():
        block_id = HDFSLogLoader.extract_block_id(line)
        parsed = parser.parse_line(line)
        events.append({"session_id": block_id, "template_id": parsed["template_id"]})

    feature_matrix = builder.fit_transform(events)

    model = IsolationForestModel(contamination=0.4, random_state=42)
    model.fit(feature_matrix)
    preds = model.predict(feature_matrix)
    scores = model.score_samples(feature_matrix)

    result_df = pd.DataFrame({
        "Anomaly_Prediction": ["🚨 ANOMALY" if p == 1 else "✅ NORMAL" for p in preds],
        "Anomaly_Score": scores
    }, index=feature_matrix.index)

    print("📊 ผลการทำนายของ AI (Isolation Forest):\n")
    print(result_df)
