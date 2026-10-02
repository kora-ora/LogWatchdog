from typing import List, Dict, Any, Tuple, Optional
from collections import defaultdict
import numpy as np
from src.features.base import BaseFeatureExtractor


class SequenceExtractor(BaseFeatureExtractor):
    """
    🧱 [Lego Brick 3: Sequential Feature Extractor]
    สกัดลำดับ Event ตามเวลาในแต่ละ Session และตัดแบ่งเป็น Sliding Window
    สำหรับสอนโมเดล Deep Learning (DeepLog / LSTM) ให้ทำนาย Next-Event
    """

    def __init__(self, window_size: int = 3, pad_token: int = 0):
        """
        :param window_size: ขนาดของหน้าต่างลำดับเหตุการณ์ในอดีต (Default: 3)
        :param pad_token: ค่าตัวเลขที่ใช้เติมกรณีลำดับสั้นกว่า window_size (Default: 0)
        """
        self.window_size = window_size
        self.pad_token = pad_token #หากภายใน window จำนวนค่าข้อมูลไม่ครบ เช่น window = 3 = [e1,e2,...] ตรง ... ให้ใส่ 0 แทน 
        self.vocab: set = set()

    def extract_session_sequences(
        self, parsed_events: List[Dict[str, Any]]
    ) -> Dict[str, List[int]]:
        """
        จัดกลุ่ม Event ID เรียงตามลำดับเวลาในแต่ละ Session
        :return: Dict เช่น {'blk_1': [1, 2, 3, 1], 'blk_2': [1, 4]}
        """
        session_sequences = defaultdict(list)
        for event in parsed_events:
            session_id = event.get("session_id", "unknown")
            template_id = event.get("template_id")
            if template_id is not None:
                session_sequences[session_id].append(template_id)
                self.vocab.add(template_id)
        return dict(session_sequences)

    def fit_transform(self, parsed_events: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        แปลงข้อมูล Event ดิบให้เป็นชุดคู่ข้อมูล (X, y) ด้วยเทคนิค Sliding Window
        
        :param parsed_events: รายการ Dict จาก Block 2 ที่มี session_id และ template_id
        :return: Dict ที่ประกอบด้วย:
                 - 'X': numpy array มิติ (N, window_size) -> ลำดับเหตุการณ์ในอดีต
                 - 'y': numpy array มิติ (N,) -> เหตุการณ์เป้าหมายถัดไป
                 - 'session_sequences': ลำดับ Event ดิบแยกตาม Session
                 - 'vocab_size': จำนวน Event ID สูงสุดที่พบ + 1 (สำหรับกำหนดขนาด Embedding/Softmax)
        """
        if not parsed_events:
            return {
                "X": np.empty((0, self.window_size), dtype=int),
                "y": np.empty((0,), dtype=int),
                "session_sequences": {},
                "vocab_size": 0,
            }

        session_sequences = self.extract_session_sequences(parsed_events)

        X_list = []
        y_list = []

        for session_id, seq in session_sequences.items():
            if len(seq) == 0:
                continue

            # ถ้าลำดับสั้นกว่า window_size ให้เติม padding ด้านหน้า
            if len(seq) <= self.window_size:
                padded = [self.pad_token] * (self.window_size - len(seq) + 1) + seq
                for i in range(len(padded) - self.window_size):
                    X_list.append(padded[i : i + self.window_size])
                    y_list.append(padded[i + self.window_size])
            else:
                # ทำ Sliding Window ปกติ
                for i in range(len(seq) - self.window_size):
                    X_list.append(seq[i : i + self.window_size])
                    y_list.append(seq[i + self.window_size])

        X = np.array(X_list, dtype=int) if X_list else np.empty((0, self.window_size), dtype=int)
        y = np.array(y_list, dtype=int) if y_list else np.empty((0,), dtype=int)

        max_vocab_id = max(self.vocab) if self.vocab else 0
        vocab_size = max_vocab_id + 1  # เผื่อ index 0 สำหรับ pad_token

        return {
            "X": X,
            "y": y,
            "session_sequences": session_sequences,
            "vocab_size": vocab_size,
        }