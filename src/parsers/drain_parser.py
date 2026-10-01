from typing import Dict, Any
from drain3 import TemplateMiner  # สังเกตตัว T และ M ตัวใหญ่ (เป็น Class)
from src.parsers.base import BaseLogParser


class DrainParser(BaseLogParser):
    """
    🧱 [Lego Brick 2: Drain3 Parser Implementation]
    แปลง Log ดิบให้เป็น Template และ Event ID โดยใช้อัลกอริทึม Drain3
    """

    def __init__(self):
        # สร้างตัวขุด Template เตรียมไว้ใช้งาน
        self.miner = TemplateMiner()

    def parse_line(self, line: str) -> Dict[str, Any]:
        # 1. ส่งข้อความเข้าไปให้ miner ประมวลผล
        result = self.miner.add_log_message(line)

        # 2. คืนค่าออกมาเป็น Dictionary
        return {
            "raw_line": line,
            "template_id": result["cluster_id"],      # รหัส Event ID (เช่น 1, 2, 3)
            "template_str": result["template_mined"],  # ข้อความ template (เช่น "Receiving block <*>")
        }
