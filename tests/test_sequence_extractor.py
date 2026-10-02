import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
import numpy as np
from src.features.sequence_extractor import SequenceExtractor
from src.ingestion.hdfs_loader import HDFSLogLoader
from src.parsers.drain_parser import DrainParser


def test_sequence_extractor_basic_sliding_window():
    """ทดสอบ Sliding Window ขั้นพื้นฐาน: [1, 2, 3, 4, 5] ด้วย window_size=3"""
    mock_events = [
        {"session_id": "blk_1", "template_id": 1},
        {"session_id": "blk_1", "template_id": 2},
        {"session_id": "blk_1", "template_id": 3},
        {"session_id": "blk_1", "template_id": 4},
        {"session_id": "blk_1", "template_id": 5},
    ]

    extractor = SequenceExtractor(window_size=3)
    result = extractor.fit_transform(mock_events)

    X = result["X"]
    y = result["y"]

    assert len(X) == 2, "ลำดับความยาว 5 หั่นด้วย window_size 3 ต้องได้ 2 คู่ข้อมูล"
    # คู่ที่ 1: [1, 2, 3] -> 4
    assert np.array_equal(X[0], [1, 2, 3])
    assert y[0] == 4
    # คู่ที่ 2: [2, 3, 4] -> 5
    assert np.array_equal(X[1], [2, 3, 4])
    assert y[1] == 5


def test_sequence_extractor_short_sequence_padding():
    """ทดสอบกรณี sequence สั้นกว่าหรือเท่ากับ window_size ต้องมีการเติม padding (0)"""
    mock_events = [
        {"session_id": "blk_short", "template_id": 1},
        {"session_id": "blk_short", "template_id": 2},
    ]

    extractor = SequenceExtractor(window_size=3, pad_token=0)
    result = extractor.fit_transform(mock_events)

    X = result["X"]
    y = result["y"]

    assert len(X) > 0, "ลำดับสั้นต้องถูกเติม padding เพื่อให้ดึงข้อมูลฝึกสอนได้"
    assert X.shape[1] == 3, "ขนาดของหน้าต่าง X ต้องคงที่เท่ากับ window_size (3)"


def test_integration_with_real_hdfs_logs():
    """ทดสอบการเชื่อมต่อ Block 1 (Loader) -> Block 2 (Parser) -> SequenceExtractor"""
    loader = HDFSLogLoader("data/raw/hdfs_sample.log")
    parser = DrainParser()
    extractor = SequenceExtractor(window_size=3)

    events = []
    for line in loader.load():
        block_id = HDFSLogLoader.extract_block_id(line)
        parsed = parser.parse_line(line)
        events.append({"session_id": block_id, "template_id": parsed["template_id"]})

    result = extractor.fit_transform(events)

    assert result["vocab_size"] > 0, "ต้องระบุขนาดคำศัพท์ (vocab_size) ได้"
    assert len(result["X"]) > 0, "ต้องสร้าง Training Pairs (X, y) จากไฟล์ HDFS ได้"
    assert len(result["session_sequences"]) == 5, "ต้องมีลำดับแยกตาม 5 Block ID"


if __name__ == "__main__":
    print("=== ทดสอบการสร้างลำดับเวลา (Sequence Extractor) ===\n")
    loader = HDFSLogLoader("data/raw/hdfs_sample.log")
    parser = DrainParser()
    extractor = SequenceExtractor(window_size=3)

    events = []
    for line in loader.load():
        block_id = HDFSLogLoader.extract_block_id(line)
        parsed = parser.parse_line(line)
        events.append({"session_id": block_id, "template_id": parsed["template_id"]})

    result = extractor.fit_transform(events)
    X = result["X"]
    y = result["y"]
    session_seqs = result["session_sequences"]

    print("📌 ลำดับ Event ID ดิบในแต่ละ Session (Block ID):")
    for session_id, seq in session_seqs.items():
        print(f"  - {session_id}: {seq}")

    print("\n" + "="*60)
    print("🤖 ตัวอย่างชุดข้อมูลสอน AI (Sliding Window: X -> y):")
    for i in range(min(6, len(X))):
        print(f"  ตัวอย่างที่ {i+1}: Input (X) = {X[i]}  -->  Target Next-Event (y) = {y[i]}")
    print("="*60)
    print(f"\nรวมทั้งหมด: {len(X)} คู่ข้อมูลสอน | Vocab Size: {result['vocab_size']}")
