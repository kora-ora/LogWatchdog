import pytest
import os
from src.ingestion.base import LogFileNotFoundError
from src.ingestion.hdfs_loader import HDFSLogLoader
from src.ingestion.cicd_loader import CICDLogLoader


def test_file_not_found_raises_error():
    """ทดสอบว่าเมื่อระบุพาธไฟล์ที่ไม่มีอยู่จริง ระบบต้องโยน LogFileNotFoundError"""
    with pytest.raises(LogFileNotFoundError):
        HDFSLogLoader("data/raw/non_existent_file.log")


def test_cicd_loader_loads_lines():
    """ทดสอบว่า CICDLogLoader สามารถอ่านไฟล์ได้ทีละบรรทัดและไม่มีบรรทัดว่าง"""
    sample_path = "data/raw/cicd_sample.log"
    if not os.path.exists(sample_path):
        pytest.skip("ไม่พบไฟล์ cicd_sample.log")
        
    loader = CICDLogLoader(sample_path)
    lines = list(loader.load())
    
    assert len(lines) > 0, "ต้องอ่านได้อย่างน้อย 1 บรรทัด"
    for line in lines:
        assert isinstance(line, str)
        assert len(line.strip()) > 0, "ต้องไม่มีบรรทัดว่างเปล่าหลุดออกมา"


def test_hdfs_loader_extract_block_id():
    """ทดสอบ Helper Method extract_block_id"""
    sample_line = "081109 203615 148 INFO dfs.DataNode: Receiving block blk_-1608999687919862906 src: /10.250.19.102"
    block_id = HDFSLogLoader.extract_block_id(sample_line)
    assert block_id == "blk_-1608999687919862906", f"Expected blk_-1608999687919862906, got {block_id}"


def test_hdfs_loader_when_implemented():
    """
    ทดสอบ HDFSLogLoader เมื่อคุณเขียนฟังก์ชัน load() เสร็จแล้ว
    (หากยังไม่เขียน จะ throw NotImplementedError ซึ่งถือว่าปกติในขั้นตอนนี้)
    """
    sample_path = "data/raw/hdfs_sample.log"
    if not os.path.exists(sample_path):
        pytest.skip("ไม่พบไฟล์ hdfs_sample.log")
        
    loader = HDFSLogLoader(sample_path)
    try:
        lines = list(loader.load())
        assert len(lines) > 0, "ต้องอ่านไฟล์ hdfs_sample.log ได้อย่างน้อย 1 บรรทัด"
        assert loader.count_lines() == len(lines)
    except NotImplementedError:
        pytest.skip("HDFSLogLoader.load() ยังไม่ได้ถูกเขียน (รอให้คุณลงมือเขียน)")
