from typing import Any, Dict, List, Optional
import torch
import torch.nn.functional as F
from src.explainers.base import BaseExplainer
from src.models.deeplog_lstm import DeepLogLSTMModel


class DeepLogExplainer(BaseExplainer):
    """
    🧱 [Lego Brick 5: DeepLog Explainer & Root Cause Localization]
    สืบสวนและชี้เป้าสาเหตุของความผิดปกติ (Root Cause Analysis) จากโมเดล DeepLog LSTM
    
    หน้าที่:
    1. ตรวจสอบว่าความผิดปกติเกิดจาก:
       - เคส A: ข้อความแปลกปลอม (Unseen Token / OOV)
       - เคส B: ลำดับขั้นตอนผิดคิว (Sequential Violation / Step Skipping)
    2. ชี้เป้าบรรทัดที่เกิดปัญหา (Line Number, Raw Message, Timestamp)
    3. ดึงบริบทแวดล้อม (Context Window: ก่อนหน้า, จุดเกิดเหตุ, ถัดไป)
    4. เปิดเผยสิ่งที่ AI คาดหวัง (Expected Candidates & Probabilities vs Reality)
    5. สรุปเป็นรายงานการชันสูตร (Incident Diagnostic Report) สำหรับวิศวกร
    """

    def __init__(self, model: DeepLogLSTMModel, template_vocab: Optional[Dict[int, str]] = None):
        """
        :param model: โมเดล DeepLogLSTMModel ที่ผ่านการฝึกสอนแล้ว
        :param template_vocab: พจนานุกรมแปล template_id -> ข้อความ template (สำหรับแสดงภาษาคน)
        """
        self.model = model
        self.template_vocab = template_vocab or {}

    def explain(self, anomaly_result: Any, raw_logs: Any) -> Dict[str, Any]:
        """
        เมธอดตามสัญญาของ BaseExplainer
        """
        if isinstance(raw_logs, list):
            return self.explain_session(raw_logs, session_id=str(anomaly_result))
        return {"status": "unsupported_input_format"}

    def explain_session(
        self,
        session_events: List[Dict[str, Any]],
        session_id: str = "Unknown_Session"
    ) -> Dict[str, Any]:
        """
        ชันสูตรเจาะลึก 1 Session ที่ถูกตัดสินว่าเป็น Anomaly
        
        :param session_events: รายการ Event ใน Session นั้น แต่ละตัวประกอบด้วย:
               - 'line_number': เลขบรรทัดในไฟล์ Log ดิบ
               - 'raw_line': ข้อความเต็มในไฟล์ Log
               - 'template_id': Event ID ตัวเลข
               - 'template_str' (optional): ข้อความ Template
        :param session_id: รหัส Session หรือ Run ID
        :return: Dict สรุปผลการวินิจฉัยเชิงลึก
        """
        if not session_events:
            return {
                "session_id": session_id,
                "is_anomaly": False,
                "culprit_step_index": None,
                "culprit_line_number": None,
                "culprit_template_id": None,
                "expected_candidates": [],
                "reason": "Empty session events"
            }

        # เก็บ Template String เข้าพจนานุกรมเพื่อใช้อ้างอิง
        for e in session_events:
            tid = e.get("template_id")
            tstr = e.get("template_str")
            if tid is not None and tstr and tid not in self.template_vocab:
                self.template_vocab[tid] = tstr

        # ---------------------------------------------------------------------
        # ด่านที่ 1: ตรวจสอบคำศัพท์แปลกปลอม (Unseen Token / Out-of-Vocabulary)
        # ---------------------------------------------------------------------
        for idx, event in enumerate(session_events):
            tid = event.get("template_id")
            if tid not in self.model.normal_vocab:
                # พบ Event แปลกปลอมที่ไม่เคยเห็นในรอบปกติ!
                return self._build_oov_report(
                    session_id=session_id,
                    culprit_index=idx,
                    session_events=session_events,
                    culprit_event=event
                )

        # ---------------------------------------------------------------------
        # ด่านที่ 1.5: ตรวจสอบเซสชันแท้งกลางคัน / สิ้นสุดก่อนกำหนด (Incomplete Session)
        # ---------------------------------------------------------------------
        min_len = getattr(self.model, "min_session_length", None)
        if min_len is not None and len(session_events) < min_len:
            return self._build_incomplete_report(
                session_id=session_id,
                session_events=session_events,
                min_expected_length=min_len
            )

        # ---------------------------------------------------------------------
        # ด่านที่ 2: ตรวจสอบการกระโดดข้ามขั้นตอน / ลำดับผิดคิว (Sequential Violation)
        # ---------------------------------------------------------------------
        seq = [e["template_id"] for e in session_events]
        w = self.model.window_size

        # จัดการ Session ที่สั้นกว่า window_size ด้วยการ Padding
        padded_events = list(session_events)
        if len(seq) <= w:
            pad_count = w - len(seq) + 1
            padded_seq = [0] * pad_count + seq
            pad_mock = [{"line_number": 0, "raw_line": "<PADDING>", "template_id": 0}] * pad_count
            padded_events = pad_mock + padded_events
        else:
            padded_seq = seq

        self.model.net.eval()
        with torch.no_grad():
            for i in range(len(padded_seq) - w):
                window = padded_seq[i : i + w]
                actual_next = padded_seq[i + w]
                culprit_event = padded_events[i + w]

                window_tensor = torch.tensor([window], dtype=torch.long).to(self.model.device)
                logits = self.model.net(window_tensor)
                probs = F.softmax(logits, dim=-1)[0]

                topk_result = torch.topk(
                    probs,
                    k=min(self.model.top_k, self.model.vocab_size),
                    dim=-1
                )
                topk_indices = topk_result.indices.cpu().numpy().tolist()
                topk_probs = topk_result.values.cpu().numpy().tolist()

                # ถ้าเหตุการณ์ถัดไปที่เกิดขึ้นจริง ไม่อยู่ในกลุ่มที่ AI คาดหวัง
                if actual_next not in topk_indices:
                    actual_prob = float(probs[actual_next].item()) if actual_next < len(probs) else 0.0
                    return self._build_sequential_report(
                        session_id=session_id,
                        culprit_index=i + w,
                        padded_events=padded_events,
                        culprit_event=culprit_event,
                        window=window,
                        expected_indices=topk_indices,
                        expected_probs=topk_probs,
                        actual_next=actual_next,
                        actual_prob=actual_prob
                    )

        # หากตรวจสอบครบแล้วไม่พบจุดผิดปกติ
        return {
            "session_id": session_id,
            "is_anomaly": False,
            "culprit_step_index": None,
            "culprit_line_number": None,
            "culprit_template_id": None,
            "expected_candidates": [],
            "message": "Session normal: no OOV and sequential transitions matched LSTM Top-K predictions"
        }

    def _extract_context(
        self,
        events: List[Dict[str, Any]],
        culprit_idx: int,
        context_window: int = 2
    ) -> List[Dict[str, Any]]:
        """ดึงบริบท Log 2 บรรทัดก่อนหน้า + จุดเกิดเหตุ + 2 บรรทัดถัดไป"""
        start = max(0, culprit_idx - context_window)
        end = min(len(events), culprit_idx + context_window + 1)
        context = []
        for i in range(start, end):
            item = dict(events[i])
            item["is_culprit"] = (i == culprit_idx)
            context.append(item)
        return context

    def _build_oov_report(
        self,
        session_id: str,
        culprit_index: int,
        session_events: List[Dict[str, Any]],
        culprit_event: Dict[str, Any]
    ) -> Dict[str, Any]:
        """สร้างรายงานสำหรับเคสคำศัพท์แปลกปลอม (Unseen Token)"""
        tid = culprit_event.get("template_id")
        tstr = culprit_event.get("template_str", self.template_vocab.get(tid, "<UNKNOWN_TEMPLATE>"))
        line_no = culprit_event.get("line_number", "N/A")
        raw = culprit_event.get("raw_line", "")
        context = self._extract_context(session_events, culprit_index)

        return {
            "session_id": session_id,
            "is_anomaly": True,
            "anomaly_type": "Unseen Event / Out-of-Vocabulary (OOV)",
            "detection_mechanism": "Template Dictionary Guard (Out-of-Vocabulary)",
            "severity": "HIGH",
            "culprit_step_index": culprit_index,
            "culprit_line_number": line_no,
            "culprit_raw_line": raw,
            "culprit_template_id": tid,
            "culprit_template_str": tstr,
            "root_cause": (
                f"ตรวจพบ Log Template ใหม่ (ID: {tid}) ที่ไม่เคยปรากฏในประวัติการฝึกสอนรอบปกติ "
                f"(Baseline Vocabulary มีขนาด {len(self.model.normal_vocab)} รูปแบบ)"
            ),
            "expected_events": [],
            "expected_candidates": [],
            "actual_event": None,
            "context_lines": context
        }

    def _build_incomplete_report(
        self,
        session_id: str,
        session_events: List[Dict[str, Any]],
        min_expected_length: int
    ) -> Dict[str, Any]:
        """สร้างรายงานกรณีเซสชันแท้งกลางคัน/สิ้นสุดก่อนกำหนด"""
        last_event = session_events[-1] if session_events else {}
        tid = last_event.get("template_id", 0)
        tstr = last_event.get("template_str", self.template_vocab.get(tid, "<UNKNOWN_TEMPLATE>"))
        line_no = last_event.get("line_number", "N/A")
        raw = last_event.get("raw_line", "")
        context = self._extract_context(session_events, len(session_events) - 1)

        return {
            "session_id": session_id,
            "is_anomaly": True,
            "anomaly_type": "Incomplete Session / Premature Termination",
            "detection_mechanism": f"Session Lifecycle Guard (Length < {min_expected_length})",
            "severity": "HIGH",
            "culprit_step_index": len(session_events) - 1,
            "culprit_line_number": line_no,
            "culprit_raw_line": raw,
            "culprit_template_id": tid,
            "culprit_template_str": tstr,
            "root_cause": (
                f"เซสชันสิ้นสุดการทำงานก่อนกำหนด (พบเพียง {len(session_events)} เหตุการณ์ "
                f"จากเกณฑ์ขั้นต่ำของระบบปกติ {min_expected_length} เหตุการณ์ โดยไม่มีขั้นตอนสิ้นสุด)"
            ),
            "expected_events": [],
            "expected_candidates": [],
            "actual_event": None,
            "context_lines": context
        }

    def _build_sequential_report(
        self,
        session_id: str,
        culprit_index: int,
        padded_events: List[Dict[str, Any]],
        culprit_event: Dict[str, Any],
        window: List[int],
        expected_indices: List[int],
        expected_probs: List[float],
        actual_next: int,
        actual_prob: float
    ) -> Dict[str, Any]:
        """สร้างรายงานสำหรับเคสข้ามขั้นตอน / ลำดับผิดปกติ (Sequential Violation)"""
        line_no = culprit_event.get("line_number", "N/A")
        raw = culprit_event.get("raw_line", "")
        context = self._extract_context(padded_events, culprit_index)

        expected_details = []
        for idx, prob in zip(expected_indices, expected_probs):
            t_str = self.template_vocab.get(idx, f"Event_{idx}")
            expected_details.append({
                "template_id": idx,
                "template_str": t_str,
                "probability": round(prob * 100, 2)
            })

        actual_str = self.template_vocab.get(actual_next, f"Event_{actual_next}")

        return {
            "session_id": session_id,
            "is_anomaly": True,
            "anomaly_type": "Sequential Violation / Step Skipping",
            "detection_mechanism": f"DeepLog LSTM Sequence Predictor (Top-{self.model.top_k})",
            "severity": "CRITICAL",
            "culprit_step_index": culprit_index,
            "culprit_line_number": line_no,
            "culprit_raw_line": raw,
            "culprit_template_id": actual_next,
            "culprit_template_str": actual_str,
            "previous_window": [
                {"template_id": tid, "template_str": self.template_vocab.get(tid, f"Event_{tid}")}
                for tid in window
            ],
            "expected_events": expected_details,
            "expected_candidates": expected_indices,
            "actual_probability": round(actual_prob * 100, 2),
            "actual_event": {
                "template_id": actual_next,
                "template_str": actual_str,
                "probability": round(actual_prob * 100, 2)
            },
            "root_cause": (
                f"ลำดับขั้นตอนผิดคิว: หลังจากผ่านลำดับเหตุการณ์ {window} โมเดลคาดหวัง Event "
                f"{[e['template_id'] for e in expected_details]} แต่พบ Event {actual_next} โผล่ขึ้นมาแทน "
                f"(ความน่าจะเป็นจากการคำนวณของโมเดล: {actual_prob * 100:.2f}%)"
            ),
            "context_lines": context
        }

    def format_incident_report(self, diagnosis: Dict[str, Any]) -> str:
        """
        แปลงข้อมูลการชันสูตรเป็นข้อความรายงานเชิงเทคนิคที่กระชับ ตรงตามข้อเท็จจริง
        """
        if not diagnosis.get("is_anomaly", False):
            return f"✅ [Incident Report: {diagnosis.get('session_id')}] - รอบการทำงานปกติดี ไม่พบสิ่งผิดปกติ"

        s_id = diagnosis["session_id"]
        a_type = diagnosis["anomaly_type"]
        mechanism = diagnosis.get("detection_mechanism", "DeepLog Detector")
        sev = diagnosis["severity"]
        line_no = diagnosis["culprit_line_number"]
        root_cause = diagnosis["root_cause"]

        report = f"""
================================================================================
🚨 [INCIDENT DIAGNOSTIC REPORT] • {s_id}
================================================================================
• ประเภทความผิดปกติ (Anomaly Type):     {a_type}
• กลไกการตรวจจับ (Detection Mechanism): {mechanism}
• ระดับความรุนแรง (Severity):           [{sev}]
• พิกัดบรรทัดต้นเหตุ (Culprit Line):     บรรทัดที่ {line_no}
• ข้อความใน Log (Message):              "{diagnosis['culprit_raw_line']}"
• รหัสแม่พิมพ์ (Template):               Event {diagnosis['culprit_template_id']} -> "{diagnosis['culprit_template_str']}"
• ข้อมูลทางเทคนิค (Technical Reason):    {root_cause}
"""
        # แสดงตารางความน่าจะเป็นเฉพาะเมื่อมีค่าคำนวณจริงจาก LSTM (Sequential Violation)
        if diagnosis.get("expected_events"):
            report += "\n📊 ความน่าจะเป็นของลำดับขั้นตอน (Expected vs Actual):\n"
            for exp in diagnosis["expected_events"]:
                report += f"  - [สิ่งที่ควรเกิด] Event {exp['template_id']}: \"{exp['template_str']}\" (P = {exp['probability']}%)\n"
            act = diagnosis.get("actual_event")
            if act:
                report += f"  👉 [ที่เกิดขึ้นจริง] Event {act['template_id']}: \"{act['template_str']}\" (P = {act['probability']}%)\n"

        # แสดง Context Window ของ Log
        report += "\n📄 บริบทแวดล้อมของ Log ณ จุดเกิดเหตุ (Log Context Window):\n"
        for ctx in diagnosis.get("context_lines", []):
            flag = "👉 [CULPRIT]" if ctx.get("is_culprit") else "   "
            l_num = ctx.get("line_number", "N/A")
            raw_text = ctx.get("raw_line", "").strip()
            report += f"  {flag} [Line {l_num:>4}]: {raw_text}\n"

        report += """================================================================================"""
        return report.strip()
