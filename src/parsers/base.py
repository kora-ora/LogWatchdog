from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

class BaseLogParser(ABC):
    """
    [Block 2 - Foundational Interface]
    สัญญามาตรฐานสำหรับชิ้นส่วน Log Parser (เช่น Drain3, Regex, LLM)
    แปลงข้อความ Log ดิบที่ไม่มีโครงสร้าง ให้กลายเป็น Structured Event Template
    """

    @abstractmethod
    def parse_line(self, line: str) -> Dict[str, Any]:     

        pass
