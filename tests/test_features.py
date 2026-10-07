import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
import pandas as pd
from src.features.count_vector import CountVectorBuilder
from src.ingestion.hdfs_loader import HDFSLogLoader
from src.parsers.drain_parser import DrainParser


def test_count_vector_builder_basic():
    """ทดสอบการสร้าง Count Vector พื้นฐาน"""
    mock_events = [
        {"session_id": "blk_1", "template_id": 1},
        {"session_id": "blk_1", "template_id": 1},
        {"session_id": "blk_1", "template_id": 2},
        {"session_id": "blk_2", "template_id": 3},
    ]

    builder = CountVectorBuilder()
    df = builder.fit_transform(mock_events)

    assert isinstance(df, pd.DataFrame), "ผลลัพธ์ต้องเป็น pandas DataFrame"
    assert df.shape == (2, 3), "ต้องมี 2 แถว (blk_1, blk_2) และ 3 คอลัมน์ (E1, E2, E3)"
    assert list(df.columns) == ["E1", "E2", "E3"]
    assert df.loc["blk_1", "E1"] == 2, "blk_1 ต้องมี E1 เกิดขึ้น 2 ครั้ง"
    assert df.loc["blk_1", "E3"] == 0, "blk_1 ไม่เคยมี E3 ต้องเติมค่าเป็น 0"
    assert df.loc["blk_2", "E3"] == 1, "blk_2 ต้องมี E3 เกิดขึ้น 1 ครั้ง"


def test_empty_events_returns_empty_df():
    """ทดสอบกรณีไม่มีข้อมูล Event เข้ามา"""
    builder = CountVectorBuilder()
    df = builder.fit_transform([])
    assert df.empty, "ถ้าไม่มีข้อมูลต้องคืน DataFrame ว่าง"


def test_end_to_end_block1_block2_block3():
    """
    ทดสอบการไหลของข้อมูลต่อกัน 3 บล็อก (Block 1 + Block 2 + Block 3):
    HDFSLogLoader -> DrainParser -> CountVectorBuilder
    """
    loader = HDFSLogLoader("data/raw/synthetic/hdfs_sample.log")
    parser = DrainParser()
    builder = CountVectorBuilder()

    parsed_events = []
    for line in loader.load():
        # Block 1: ดึง Session ID (Block ID)
        block_id = HDFSLogLoader.extract_block_id(line)
        
        # Block 2: Parse หา Event ID
        parsed = parser.parse_line(line)
        
        parsed_events.append({
            "session_id": block_id,
            "template_id": parsed["template_id"],
            "raw_line": parsed["raw_line"]
        })

    # Block 3: แปลงเป็น Feature Matrix
    feature_matrix = builder.fit_transform(parsed_events)

    assert not feature_matrix.empty, "Feature Matrix ต้องไม่ว่างเปล่า"
    assert feature_matrix.shape[0] == 5, f"ใน hdfs_sample.log ต้องมี 5 Block ID (ได้ {feature_matrix.shape[0]})"
    assert "blk_-1608999687919862906" in feature_matrix.index
    assert "blk_999999999999999999" in feature_matrix.index


if __name__ == "__main__":
    print("=== ทดสอบการต่อประสาน Block 1 -> Block 2 -> Block 3 ===\n")
    
    loader = HDFSLogLoader("data/raw/synthetic/hdfs_sample.log")
    parser = DrainParser()
    builder = CountVectorBuilder()

    parsed_events = []
    for line in loader.load():
        block_id = HDFSLogLoader.extract_block_id(line)
        parsed = parser.parse_line(line)
        parsed_events.append({
            "session_id": block_id,
            "template_id": parsed["template_id"]
        })

    feature_matrix = builder.fit_transform(parsed_events)
    
    print("📊 ตาราง Feature Matrix (Count Vector) ที่ได้:\n")
    print(feature_matrix)
    print("\n" + "="*60)
    print(f"ขนาดตาราง (Shape)   : {feature_matrix.shape[0]} Sessions x {feature_matrix.shape[1]} Features")
    print(f"รายชื่อ Feature Columns: {builder.get_feature_names()}")
    print("="*60)
