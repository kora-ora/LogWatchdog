from typing import Iterator
import re
from src.ingestion.base import BaseLogLoader, EmptyLogError


class HDFSLogLoader(BaseLogLoader):
    """
    🧱 [Lego Brick 1: HDFS Implementation]
    ตัวอ่านชุดข้อมูล Log มาตรฐาน HDFS (Hadoop Distributed File System)
    
    ลักษณะของ HDFS Log:
    - มี Timestamp, Level, Component และข้อความ
    - จุดสำคัญที่สุดคือจะมี 'Block ID' กำกับ เช่น blk_-1608999687919862906
    
    ตัวอย่างบรรทัด Log:
    '081109 203615 148 INFO dfs.DataNode$DataXceiver: Receiving block blk_-1608999... src: /10.250.19.102...'
    """

    def __init__(self, file_path: str, encoding: str = "utf-8"):
        super().__init__(file_path)
        self.encoding = encoding

    def load(self) -> Iterator[str]:
        with open(self.file_path, "r", encoding=self.encoding) as f:
            for line in f:
                clean = line.strip() #ทำความสะอาดไม่ให้มี \n หรือ " " พื้นที่ว่างหน้าและหลังบรรทัด
                if clean : #ตรวจสอบว่าบรรทัดที่เข้ามามีข้อความหรือไม่ ถ้าไม่ทิ้งไม่ส่งออก
                    yield clean 
                

    @staticmethod
    def extract_block_id(line: str) -> str:
        """
        [Helper Function เพิ่มเติม]
        ดึง Block ID จากบรรทัด Log ของ HDFS (เช่น 'blk_-1608999687919862906')
        มีประโยชน์มากเมื่อนำไปจัดกลุ่ม Session ใน Block 3
        """
        match = re.search(r"(blk_-?\d+)", line)
        return match.group(1) if match else "unknown"
