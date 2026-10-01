from abc import ABC, abstractmethod
from typing import Any, List

class BaseFeatureExtractor(ABC):
    """
    [Block 3 - Foundational Interface]
    สัญญามาตรฐานสำหรับชิ้นส่วนแปลง Feature (เช่น Count Vector, Sliding Window)
    """

    @abstractmethod
    def fit_transform(self, parsed_events: List[Any]) -> Any:
        """
        แปลงข้อมูล Event ที่ผ่านการ Parse แล้ว ให้เป็น Matrix หรือ Tensor ตัวเลข
        """
        pass
