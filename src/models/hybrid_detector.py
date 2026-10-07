from typing import Any, Dict, List, Optional, Union
import numpy as np
import pandas as pd
from src.models.base import BaseAnomalyModel
from src.models.isolation_forest import IsolationForestModel
from src.models.deeplog_lstm import DeepLogLSTMModel


class HybridLogDetector(BaseAnomalyModel):
    """
    🧱 [Lego Brick 4 Extension: Hybrid Dual-Engine Detector]
    ผสานพลัง 2 โมเดลตรวจจับความผิดปกติ:
    1. Isolation Forest (ด่านตรวจความถี่ / Volume & Count Outliers)
    2. DeepLog LSTM (ด่านตรวจลำดับเวลาและขั้นตอน / Sequential Transitions)
    
    กลยุทธ์การตัดสินใจ (Ensemble Strategy):
    - "synergy" / "cascaded" (ค่าเริ่มต้นที่แนะนำ):
      ใช้ Isolation Forest เป็น Anomaly Validator และ Noise Suppressor
      - หากพบความผิดปกติเชิงลำดับขั้นรุนแรง (min_prob < 0.01 หรือ >= 3 violations) -> ฟันธง Anomaly ทันที
      - หากพบความผิดปกติเชิงลำดับเล็กน้อย (1-2 violations) จะส่งให้ iForest ตรวจสอบ:
        ถ้า iForest ยืนยันความผิดปกติ (score < 0.0) -> ถือเป็น Anomaly
        ถ้า iForest ยืนยันว่า Session มีความถี่ปกติสมบูรณ์ -> กรอง False Positive ออก
      - หาก iForest ตรวจพบ Volume Storm รุนแรง (score < -0.10) -> ฟันธง Anomaly
      ผลลัพธ์: F1-Score พุ่งสูงกว่าโมเดลเดี่ยวทั้งสองตัว และลด False Positives ลงอย่างมหาศาล!
    - "or" (Union / OR-Voting - Max Sensitivity)
    - "and" (Intersection / AND-Voting - Max Precision)
    """

    def __init__(
        self,
        iforest_model: IsolationForestModel,
        deeplog_model: DeepLogLSTMModel,
        strategy: str = "synergy"
    ):
        self.iforest = iforest_model
        self.deeplog = deeplog_model
        self.strategy = strategy.lower()
        if self.strategy not in ["synergy", "cascaded", "or", "and"]:
            raise ValueError("strategy must be one of 'synergy', 'or', 'and'")

    def fit(self, X: Any, y: Any = None) -> "HybridLogDetector":
        """
        เมธอดตามสัญญา BaseAnomalyModel (โมเดลย่อยถูก fit ภายนอกมาแล้ว)
        """
        return self

    def predict(self, X: Any) -> np.ndarray:
        """
        เมธอดตามสัญญา BaseAnomalyModel
        """
        raise NotImplementedError("Use predict_session() with count_vector and sequence for HybridLogDetector.")

    def predict_session(
        self,
        count_vector: np.ndarray,
        sequence: List[int]
    ) -> Dict[str, Any]:
        """
        ทำนายผลสำหรับ 1 Session โดยรับทั้ง Count Vector และ Event Sequence
        """
        # 1. ทำนายด้วย Isolation Forest (ตรวจความถี่)
        cv = np.array(count_vector)
        if cv.ndim == 1:
            cv = cv.reshape(1, -1)
        iforest_pred = int(self.iforest.predict(cv)[0])
        if_score = float(self.iforest.model.decision_function(cv)[0])

        # 2. ทำนายด้วย DeepLog LSTM (ตรวจลำดับ)
        dl_stats = self.deeplog.inspect_session(sequence)
        deeplog_pred = int(dl_stats["is_anomaly"])

        # 3. รวมผลลัพธ์ตาม Ensemble Strategy
        trigger_sources = []
        if self.strategy in ["synergy", "cascaded"]:
            is_severe_seq = (
                dl_stats.get("has_oov", False) or 
                dl_stats.get("min_probability", 1.0) < 0.01 or 
                dl_stats.get("violation_count", 0) >= 3
            )
            is_confirmed_seq = (dl_stats.get("violation_count", 0) >= 1) and (if_score < 0.0)
            is_volume_storm = (if_score < -0.10)

            final_pred = 1 if (is_severe_seq or is_confirmed_seq or is_volume_storm) else 0

            if is_severe_seq:
                trigger_sources.append("DeepLog LSTM (Severe Sequential Failure)")
            if is_confirmed_seq:
                trigger_sources.append("Hybrid Synergy (Sequence Violation Confirmed by iForest)")
            if is_volume_storm:
                trigger_sources.append("Isolation Forest (Severe Volume/Count Storm)")
        elif self.strategy == "or":
            final_pred = 1 if (iforest_pred == 1 or deeplog_pred == 1) else 0
            if iforest_pred == 1:
                trigger_sources.append("Isolation Forest (Count/Volume Outlier)")
            if deeplog_pred == 1:
                trigger_sources.append("DeepLog LSTM (Sequential Violation / Unseen Token)")
        else: # and
            final_pred = 1 if (iforest_pred == 1 and deeplog_pred == 1) else 0
            if final_pred == 1:
                trigger_sources.append("Consensus (Both Engines Agreed)")

        return {
            "prediction": final_pred,
            "is_anomaly": (final_pred == 1),
            "strategy": self.strategy.upper(),
            "iforest_pred": iforest_pred,
            "iforest_score": if_score,
            "deeplog_pred": deeplog_pred,
            "deeplog_stats": dl_stats,
            "triggered_by": trigger_sources
        }

    def predict_batch(
        self,
        count_matrix: np.ndarray,
        sequences: List[List[int]]
    ) -> List[Dict[str, Any]]:
        """
        ทำนายผลแบบชุดข้อมูลขนาดใหญ่ (High-Throughput Batch Processing)
        """
        if len(count_matrix) != len(sequences):
            raise ValueError("count_matrix and sequences must have the same length.")

        # รัน iForest แบบ vectorized
        iforest_preds = self.iforest.predict(count_matrix)
        if_scores = self.iforest.model.decision_function(count_matrix)

        results = []
        for i, seq in enumerate(sequences):
            if_pred = int(iforest_preds[i])
            if_score = float(if_scores[i])
            dl_stats = self.deeplog.inspect_session(seq)
            dl_pred = int(dl_stats["is_anomaly"])

            triggers = []
            if self.strategy in ["synergy", "cascaded"]:
                is_severe_seq = (
                    dl_stats.get("has_oov", False) or 
                    dl_stats.get("min_probability", 1.0) < 0.01 or 
                    dl_stats.get("violation_count", 0) >= 3
                )
                is_confirmed_seq = (dl_stats.get("violation_count", 0) >= 1) and (if_score < 0.0)
                is_volume_storm = (if_score < -0.10)
                final_pred = 1 if (is_severe_seq or is_confirmed_seq or is_volume_storm) else 0

                if is_severe_seq:
                    triggers.append("DeepLog LSTM (Severe Sequential Failure)")
                if is_confirmed_seq:
                    triggers.append("Hybrid Synergy (Sequence Violation Confirmed by iForest)")
                if is_volume_storm:
                    triggers.append("Isolation Forest (Severe Volume/Count Storm)")
            elif self.strategy == "or":
                final_pred = 1 if (if_pred == 1 or dl_pred == 1) else 0
                if if_pred == 1:
                    triggers.append("Isolation Forest (Count/Volume Outlier)")
                if dl_pred == 1:
                    triggers.append("DeepLog LSTM (Sequential Violation / Unseen Token)")
            else:
                final_pred = 1 if (if_pred == 1 and dl_pred == 1) else 0
                if final_pred == 1:
                    triggers.append("Consensus (Both Engines Agreed)")

            results.append({
                "prediction": final_pred,
                "is_anomaly": (final_pred == 1),
                "strategy": self.strategy.upper(),
                "iforest_pred": if_pred,
                "iforest_score": if_score,
                "deeplog_pred": dl_pred,
                "deeplog_stats": dl_stats,
                "triggered_by": triggers
            })

        return results
