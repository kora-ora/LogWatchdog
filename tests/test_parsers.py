import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
from src.parsers.drain_parser import DrainParser
from src.ingestion.hdfs_loader import HDFSLogLoader


def test_drain_parser_returns_dict_structure():
    """ทดสอบว่า DrainParser คืนค่า Dictionary ที่มี key ครบถ้วนตามสัญญา"""
    parser = DrainParser()
    sample_line = "081109 203615 148 INFO dfs.DataNode$DataXceiver: Receiving block blk_-1608999687919862906 src: /10.250.19.102:54106 dest: /10.250.19.102:50010"
    
    result = parser.parse_line(sample_line)
    
    assert isinstance(result, dict), "ผลลัพธ์ต้องเป็น Dictionary"
    assert "raw_line" in result, "ต้องมี key 'raw_line'"
    assert "template_id" in result, "ต้องมี key 'template_id'"
    assert "template_str" in result, "ต้องมี key 'template_str'"
    assert result["template_id"] >= 1, "Template ID ต้องเป็นจำนวนเต็มบวก"


def test_drain_parser_groups_similar_logs():
    """ทดสอบว่า Log ที่โครงสร้างเหมือนกันแต่ตัวแปรต่างกัน ต้องได้ template_id เดียวกัน"""
    parser = DrainParser()
    line1 = "Receiving block blk_111 src: /10.250.19.102:54106 dest: /10.250.19.102:50010"
    line2 = "Receiving block blk_222 src: /10.250.10.6:41121 dest: /10.250.10.6:50010"
    
    res1 = parser.parse_line(line1)
    res2 = parser.parse_line(line2)
    
    assert res1["template_id"] == res2["template_id"], (
        f"Log คล้ายกันต้องได้ template_id เดียวกัน! (ได้ {res1['template_id']} กับ {res2['template_id']})"
    )


def test_drain_parser_separates_different_logs():
    """ทดสอบว่า Log ที่ต่างกันอย่างสิ้นเชิง ต้องได้ template_id คนละตัว"""
    parser = DrainParser()
    line1 = "Receiving block blk_111 src: /10.250.19.102:54106 dest: /10.250.19.102:50010"
    line2 = "PacketResponder blk_111 2 terminating"
    
    res1 = parser.parse_line(line1)
    res2 = parser.parse_line(line2)
    
    assert res1["template_id"] != res2["template_id"], (
        f"Log ต่างประเภทกันต้องได้ template_id คนละตัว! (ได้ {res1['template_id']} กับ {res2['template_id']})"
    )


def test_integration_block1_and_block2():
    """ทดสอบการเชื่อมต่อจริงระหว่าง Block 1 (Loader) และ Block 2 (Parser)"""
    loader = HDFSLogLoader("data/raw/hdfs_sample.log")
    parser = DrainParser()
    
    total_parsed = 0
    unique_templates = set()
    
    for line in loader.load():
        parsed = parser.parse_line(line)
        total_parsed += 1
        unique_templates.add(parsed["template_id"])
        
    assert total_parsed > 0, "ต้อง parse ข้อความได้สำเร็จ"
    assert len(unique_templates) > 1, "ใน sample log ต้องพบ template มากกว่า 1 ชนิด"


if __name__ == "__main__":
    # สามารถสั่งรันไฟล์นี้โดยตรงได้ด้วย python3 tests/test_parsers.py
    print("=== เริ่มการทดสอบ Block 2: DrainParser ===\n")
    loader = HDFSLogLoader("data/raw/hdfs_sample.log")
    parser = DrainParser()
    
    for i, line in enumerate(loader.load()):
        parsed = parser.parse_line(line)
        if i < 4:
            print(f"[Line {i+1}]")
            print(f"  Raw     : {parsed['raw_line'][:60]}...")
            print(f"  Event ID: {parsed['template_id']}")
            print(f"  Template: {parsed['template_str']}")
            print()
            
    print("✅ การทดสอบเบื้องต้นผ่านเรียบร้อยดี!")
