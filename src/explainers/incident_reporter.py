import os
import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional, List


class IncidentReporter:
    """
    🧱 [Lego Brick 5 Extension: Standardized Incident Reporter]
    สร้างและส่งออกรายงานการชันสูตรปัญหา (Incident Diagnostic Report)
    ตามมาตรฐาน AIOps และ SRE Industry Standards ใน 2 รูปแบบ:
    1. Machine-Readable JSON: สำหรับต่อยอด Webhook, REST API, PagerDuty, SIEM
    2. Human-Readable Markdown: สำหรับวิศวกรอ่านบน GitHub Step Summary, Obsidian หรือ VS Code
    """

    def __init__(self, output_dir: str = "reports/incidents"):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    def build_incident_payload(
        self,
        diagnosis: Dict[str, Any],
        pipeline_name: str = "CI/CD Anomaly Detection Pipeline",
        detector_name: str = "DeepLog 2-Layer LSTM"
    ) -> Dict[str, Any]:
        """
        แปลงผลลัพธ์การวินิจฉัยจาก DeepLogExplainer ให้เป็นโครงสร้างมาตรฐาน (AIOps 6-Pillar Schema)
        """
        session_id = diagnosis.get("session_id", "unknown_session")
        now_iso = datetime.now(timezone.utc).isoformat()
        incident_uuid = f"INC-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"

        is_anomaly = diagnosis.get("is_anomaly", False)
        a_type = diagnosis.get("anomaly_type", "NORMAL")
        sev = diagnosis.get("severity", "LOW" if not is_anomaly else "HIGH")

        # สกัดบริบท Log Context Window
        raw_context = diagnosis.get("context_lines", [])
        context_window = [
            {
                "line_number": c.get("line_number", 0),
                "raw_line": c.get("raw_line", "").strip(),
                "is_culprit": c.get("is_culprit", False)
            }
            for c in raw_context
        ]

        # สกัดหลักฐานเชิงสถิติ (Evidence & Context)
        evidence = {
            "detection_mechanism": diagnosis.get("detection_mechanism", "DeepLog LSTM"),
            "expected_top_candidates": diagnosis.get("expected_events", []),
            "actual_encountered": diagnosis.get("actual_event", {
                "template_id": diagnosis.get("culprit_template_id", None),
                "template_str": diagnosis.get("culprit_template_str", None)
            }),
            "context_window": context_window
        }

        payload = {
            "incident_id": incident_uuid,
            "metadata": {
                "timestamp_utc": now_iso,
                "pipeline_name": pipeline_name,
                "session_id": session_id,
                "detector": detector_name,
                "schema_version": "1.0.0"
            },
            "verdict": {
                "is_anomaly": is_anomaly,
                "severity": sev,
                "anomaly_type": a_type,
                "confidence_score": 0.95 if is_anomaly else 0.05
            },
            "root_cause_localization": {
                "culprit_line_number": diagnosis.get("culprit_line_number", None),
                "culprit_message": diagnosis.get("culprit_raw_line", None),
                "template_id": diagnosis.get("culprit_template_id", None),
                "template_str": diagnosis.get("culprit_template_str", None),
                "diagnosis_summary": diagnosis.get("root_cause", "No anomaly detected.")
            },
            "evidence_and_context": evidence
        }
        return payload

    def export_json(self, payload: Dict[str, Any], filepath: str) -> str:
        """บันทึกข้อมูลเป็นไฟล์ JSON (Machine-Readable)"""
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
        return filepath

    def export_markdown(self, payload: Dict[str, Any], filepath: str) -> str:
        """แปลงเป็นไฟล์ Markdown สวยงามตามมาตรฐาน GitHub Step Summary / Obsidian"""
        meta = payload["metadata"]
        verdict = payload["verdict"]
        rc = payload["root_cause_localization"]
        evidence = payload["evidence_and_context"]

        sev_badge = "🔴 CRITICAL" if verdict["severity"] == "CRITICAL" else "🟠 HIGH" if verdict["severity"] == "HIGH" else "🟢 NORMAL"

        md_content = f"""# 🚨 Incident Diagnostic Report: `{payload['incident_id']}`

> **Severity:** `{sev_badge}` &nbsp;|&nbsp; **Detector:** `{meta['detector']}` &nbsp;|&nbsp; **Session:** `{meta['session_id']}`
> **Timestamp (UTC):** `{meta['timestamp_utc']}`

---

## 1. 📌 สรุปผลการตรวจจับ (Executive Summary)
* **สถานะการตรวจจับ:** `{'🚨 ANOMALY DETECTED' if verdict['is_anomaly'] else '✅ NORMAL'}`
* **ประเภทความผิดปกติ (Anomaly Type):** `{verdict['anomaly_type']}`
* **กลไกที่ตรวจพบ (Detection Mechanism):** `{evidence.get('detection_mechanism', 'DeepLog LSTM')}`
* **คะแนนความเชื่อมั่น (Confidence Score):** `{verdict['confidence_score'] * 100:.1f}%`

---

## 2. 🔍 การชี้เป้าพิกัดและบริบทของปัญหา (Log Forensics & Culprit Localization)
* **พิกัดบรรทัดเกิดเหตุ (Culprit Line):** บรรทัดที่ `{rc['culprit_line_number']}`
* **ข้อความใน Log:** 
  ```log
  {rc['culprit_message']}
  ```
* **Log Template ที่สกัดได้:** `Event {rc['template_id']}` $\\to$ `{rc['template_str']}`
* **ข้อมูลทางเทคนิค (Technical Reason):**
  > {rc['diagnosis_summary']}

### 📄 บริบทแวดล้อม ณ จุดเกิดเหตุ (Log Context Window):
```log
"""
        for ctx in evidence.get("context_window", []):
            marker = "👉 [CULPRIT]" if ctx.get("is_culprit") else "   "
            line_no = ctx.get("line_number", "N/A")
            text = ctx.get("raw_line", "")
            md_content += f"{marker} [Line {line_no:>4}]: {text}\n"

        md_content += "```\n"

        # แสดงส่วนสถิติลำดับขั้นตอนเฉพาะเมื่อโมเดลมีค่าคำนวณจริงจาก LSTM (Sequential Violation)
        expected_list = evidence.get("expected_top_candidates", [])
        if expected_list:
            md_content += """
---

## 3. 📊 สถิติลำดับขั้นตอน (Expected vs Actual Transitions)
"""
            for exp in expected_list:
                md_content += f"- **Event {exp.get('template_id')}:** `{exp.get('template_str')}` *(ความน่าจะเป็น: {exp.get('probability')}%)*\n"
            act = evidence.get("actual_encountered", {})
            if act:
                md_content += f"\n👉 **สิ่งที่เกิดขึ้นจริง:** Event {act.get('template_id')}: `{act.get('template_str')}` *(ความน่าจะเป็น: {act.get('probability', 0.0)}%)*\n"

        md_content += f"""
---
*Report generated automatically by AI Log Anomaly Detection System (Schema v{meta['schema_version']})*
"""
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(md_content.strip() + "\n")
        return filepath

    def save_incident(
        self,
        diagnosis: Dict[str, Any],
        pipeline_name: str = "CI/CD Anomaly Detection Pipeline"
    ) -> Dict[str, str]:
        """
        บันทึกทั้ง JSON และ Markdown พร้อมกัน
        :return: Dict เก็บ path ของไฟล์ json และ md ที่สร้างขึ้น
        """
        payload = self.build_incident_payload(diagnosis, pipeline_name=pipeline_name)
        session_id = payload["metadata"]["session_id"]
        safe_session_id = "".join([c if c.isalnum() or c in "._-" else "_" for c in session_id])

        json_path = os.path.join(self.output_dir, f"{safe_session_id}.json")
        md_path = os.path.join(self.output_dir, f"{safe_session_id}.md")

        self.export_json(payload, json_path)
        self.export_markdown(payload, md_path)

        return {
            "incident_id": payload["incident_id"],
            "json_path": json_path,
            "md_path": md_path
        }
