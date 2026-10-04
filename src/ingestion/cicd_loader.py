from typing import Iterator
import re
from src.ingestion.base import BaseLogLoader


class CICDLogLoader(BaseLogLoader):
    """
    🧱 [Lego Brick 1: CI/CD Implementation]
    ตัวอ่านและสกัด Log จากกระบวนการ CI/CD Pipeline (เช่น GitHub Actions)
    
    ลักษณะของ CI/CD Log:
    - มี Timestamp, Level ([INFO], [WARN], [ERROR])
    - มีระบุ Workflow, Step และ Run ID (เช่น 'Run_101' หรือ 'Run #101')
    """

    def __init__(self, file_path: str, encoding: str = "utf-8"):
        super().__init__(file_path)
        self.encoding = encoding

    def load(self) -> Iterator[str]:
        with open(self.file_path, "r", encoding=self.encoding) as f:
            for line in f:
                clean = line.strip()
                # ข้ามบรรทัดว่างและบรรทัดคอมเมนต์ (#)
                if clean and not clean.startswith("#"):
                    yield clean

    @staticmethod
    def extract_run_id(line: str) -> str:
        """
        [Helper Function]
        ดึง Run ID จากบรรทัด Log CI/CD เช่น:
        - '[Run: Run_101]' -> 'Run_101'
        - 'Job started: Run #101' -> 'Run_101'
        """
        match = re.search(r"\[Run:\s*([^\]]+)\]", line)
        if match:
            return match.group(1).strip()

        match_hash = re.search(r"Run\s*#(\d+)", line)
        if match_hash:
            return f"Run_{match_hash.group(1)}"

        return "unknown_run"

    @staticmethod
    def extract_message(line: str) -> str:
        """
        [Helper Function]
        ดึงเฉพาะเนื้อความจริงของ Log (Payload Message) โดยตัด Timestamp,
        Log Level และ Run ID ออก เพื่อให้ Drain3 ขุดหา Template ได้อย่างถูกต้อง
        """
        return re.sub(
            r"^\d{4}-\d{2}-\d{2}T\S+\s+\[\w+\]\s+(\[Run:\s*[^\]]+\]\s+)?",
            "",
            line
        ).strip()
