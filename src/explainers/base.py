from abc import ABC, abstractmethod
from typing import Any, Dict

class BaseExplainer(ABC):
    """
    [Block 5 - Foundational Interface]
    สัญญามาตรฐานสำหรับชิ้นส่วนวิเคราะห์สาเหตุเชิงลึก (Root Cause Analysis & Alerts)
    """

    @abstractmethod
    def explain(self, anomaly_result: Any, raw_logs: Any) -> Dict[str, Any]:
        """
        วิเคราะห์ชี้เป้าบรรทัด Log ต้นตอ พร้อมสร้างสรุปสาเหตุความผิดปกติ
        """
        pass
