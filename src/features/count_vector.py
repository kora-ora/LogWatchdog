from typing import List, Dict, Any, Optional
from collections import defaultdict, Counter
import pandas as pd
from src.features.base import BaseFeatureExtractor


class CountVectorBuilder(BaseFeatureExtractor):
    """
    🧱 [Lego Brick 3: Count Vector Implementation]
    รวมกลุ่ม Event ตาม Session (เช่น Block ID / Run ID) 
    และนับความถี่การเกิดของแต่ละ Event เพื่อสร้าง Feature Matrix สำหรับโมเดล AI
    """

    def __init__(self):
        # เก็บรายชื่อคอลัมน์ Event ID ทั้งหมดที่เคยพบในขั้นตอน fit
        self.feature_columns: List[str] = []

    def fit_transform(self, parsed_events: List[Dict[str, Any]]) -> pd.DataFrame:
        """
        เรียนรู้ Event ID ทั้งหมด และแปลงข้อมูล Event ให้กลายเป็น Feature Matrix (DataFrame)
        
        :param parsed_events: รายการ Dictionary ที่มี key 'session_id' และ 'template_id'
               ตัวอย่าง:
               [
                   {"session_id": "blk_-1608...", "template_id": 1},
                   {"session_id": "blk_-1608...", "template_id": 2},
                   {"session_id": "blk_9999...", "template_id": 6},
               ]
        :return: pandas.DataFrame
                 - Index: session_id
                 - Columns: 'E1', 'E2', 'E3', ... (Event IDs)
                 - Values: จำนวนครั้งที่เกิด Event นั้นใน Session (เติม 0 เมื่อไม่เกิด)
        """
        if not parsed_events:
            return pd.DataFrame()

        # 1. รวมกลุ่มและนับความถี่: {session_id: Counter({template_id: count})}
        session_event_counts = defaultdict(Counter)
        all_event_ids = set()

        for event in parsed_events:
            session_id = event.get("session_id", "unknown")
            template_id = event.get("template_id")
            
            if template_id is not None:
                session_event_counts[session_id][template_id] += 1
                all_event_ids.add(template_id)

        # 2. จัดเรียงชื่อคอลัมน์ Event ตามลำดับตัวเลข (E1, E2, E3, ...)
        sorted_event_ids = sorted(list(all_event_ids))
        self.feature_columns = [f"E{e_id}" for e_id in sorted_event_ids]

        # 3. สร้างตารางตัวเลข (Matrix)
        rows = []
        session_indices = []

        for session_id, event_counts in session_event_counts.items():
            row_data = [event_counts.get(e_id, 0) for e_id in sorted_event_ids]
            rows.append(row_data)
            session_indices.append(session_id)

        # 4. แปลงเป็น Pandas DataFrame
        df = pd.DataFrame(
            data=rows,
            index=session_indices,
            columns=self.feature_columns
        )
        df.index.name = "session_id"
        return df

    def get_feature_names(self) -> List[str]:
        """ดึงรายชื่อ Feature Columns ทั้งหมด"""
        return self.feature_columns
