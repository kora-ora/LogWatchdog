from typing import Any, Dict, Optional, Union
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from src.models.base import BaseAnomalyModel


class IsolationForestModel(BaseAnomalyModel):
    """
    🧱 [Lego Brick 4: Isolation Forest Implementation]
    โมเดลตรวจจับความผิดปกติแบบ Unsupervised โดยใช้อัลกอริทึม Isolation Forest
    
    หลักการทำงาน:
    - โมเดลจะสุ่มสร้างต้นไม้ตัดสินใจ (Isolation Trees) เพื่อตัดแบ่งข้อมูล
    - จุดข้อมูลที่ 'ปกติ' (อยู่รวมกลุ่มกันแน่น) จะต้องใช้การตัดหลายครั้งกว่าจะแยกเดี่ยวได้
    - จุดข้อมูลที่ 'ผิดปกติ' (Outlier) จะถูกตัดแยกเดี่ยวได้เร็วมาก (Path Length สั้น)
    """

    def __init__(
        self,
        n_estimators: int = 100,
        contamination: Union[str, float] = "auto",
        random_state: int = 42
    ):
        """
        :param n_estimators: จำนวนต้นไม้ในป่า (Default: 100)
        :param contamination: สัดส่วนความผิดปกติที่คาดว่าจะพบในข้อมูล เช่น 0.1 หรือ 'auto'
        :param random_state: กำหนด seed เพื่อให้ผลลัพธ์คงที่ทุกครั้งที่รัน
        """
        self.n_estimators = n_estimators
        self.contamination = contamination
        self.random_state = random_state

        # 1. สร้างตัวโมเดลของ scikit-learn เตรียมไว้ใน self.model
        self.model = IsolationForest(
            n_estimators=self.n_estimators,
            contamination=self.contamination,
            random_state=self.random_state
        )

    def fit(self, X: Any, y: Any = None) -> "IsolationForestModel":
        self.model.fit(X) #train model 
        return self #ส่ง model ที่ train ออกไปให้ใข้งาน ตามวิธีการเขียน class
        
    def predict(self, X: Any) -> np.ndarray:
        raw_preds = self.model.predict(X) # ได้ค่าระหว่า -1 เป็นเท็จ และ 0 เป็นจริง
        return np.where(raw_preds == -1,1,0) #np.where( เงื่อนไข , ค่าถ้าเงื่อนไขเป็นจริง , ค่าถ้าเงื่อนไขเป็นเท็จ )

    def score_samples(self, X: Any) -> np.ndarray:
        return self.model.decision_function(X)
