from typing import Iterator
from src.ingestion.base import BaseLogLoader


class CICDLogLoader(BaseLogLoader):
    """
    🧱 [Lego Brick 1: CI/CD Implementation]
    ตัวอ่านชุดข้อมูล Log จาก CI/CD Pipeline (เช่น GitHub Actions, GitLab CI)
    
    ลักษณะของ CI/CD Log:
    - มักมี ISO Timestamp นำหน้า เช่น '2026-09-30T10:00:01Z'
    - มี Tag กำกับ Step หรือ Workflow เช่น '[Step: Install]', '[Workflow: ci-build]'
    """

    def __init__(self, file_path: str, encoding: str = "utf-8"):
        super().__init__(file_path)
        self.encoding = encoding

    def load(self) -> Iterator[str]:
        """
        TODO: เขียนโค้ดสำหรับอ่าน CI/CD Log ทีละบรรทัด
        (ใช้แนวคิดแบบ Generator เช่นเดียวกับ HDFSLogLoader)
        """
        # ========================================================
        # [พื้นที่สำหรับเขียนโค้ดเพิ่มเติมในอนาคต]
        # ========================================================
        with open(self.file_path, "r", encoding=self.encoding) as f:
            for line in f:
                cleaned = line.strip()
                if cleaned:
                    yield cleaned
