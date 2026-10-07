from abc import ABC, abstractmethod
from typing import Any, Dict

class BaseAnomalyModel(ABC):
    """
    [Block 4 - Foundational Interface]
    สัญญามาตรฐานสำหรับชิ้นส่วนโมเดลตรวจจับความผิดปกติ (เช่น Isolation Forest, DeepLog)
    """

    @abstractmethod
    def fit(self, X: Any, y: Any = None) -> "BaseAnomalyModel":
        """
        ฝึกสอนโมเดลด้วยข้อมูลปกติ (Unsupervised/Self-supervised) หรือข้อมูลที่มี Label
        """
        pass

    @abstractmethod
    def predict(self, X: Any) -> Any:
        """
        ทำนายผล: คืนค่าเป็น Label (Normal: 0, Anomaly: 1) หรือ Anomaly Score
        """
        pass
