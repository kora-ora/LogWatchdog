import os
import json
import tempfile
import pytest

from src.explainers.incident_reporter import IncidentReporter


@pytest.fixture
def sample_diagnosis():
    return {
        "session_id": "test_run_101.txt",
        "is_anomaly": True,
        "anomaly_type": "Sequential Violation / Step Skipping",
        "severity": "CRITICAL",
        "culprit_line_number": 42,
        "culprit_raw_line": "Deploy to prod without test",
        "culprit_template_id": 9,
        "culprit_template_str": "[Step: Deploy] Deploy app",
        "root_cause": "Expected step test but skipped directly to deploy",
        "remediation_hint": "Check workflow yaml configuration",
        "expected_events": [
            {"template_id": 4, "template_str": "[Step: Test] Pytest", "probability": 92.5}
        ],
        "actual_event": {
            "template_id": 9,
            "template_str": "[Step: Deploy] Deploy app",
            "probability": 0.05
        },
        "context_lines": [
            {"line_number": 40, "raw_line": "Build image", "is_culprit": False},
            {"line_number": 41, "raw_line": "Build success", "is_culprit": False},
            {"line_number": 42, "raw_line": "Deploy to prod without test", "is_culprit": True}
        ]
    }


def test_incident_reporter_payload_schema(sample_diagnosis):
    reporter = IncidentReporter(output_dir="/tmp/test_reports")
    payload = reporter.build_incident_payload(sample_diagnosis)

    # ตรวจสอบว่ามีเสาหลักสำคัญของ Schema ครบถ้วน
    assert "incident_id" in payload
    assert payload["incident_id"].startswith("INC-")
    assert "metadata" in payload
    assert "verdict" in payload
    assert "root_cause_localization" in payload
    assert "evidence_and_context" in payload

    assert payload["verdict"]["severity"] == "CRITICAL"
    assert payload["root_cause_localization"]["culprit_line_number"] == 42


def test_incident_reporter_file_exports(sample_diagnosis):
    with tempfile.TemporaryDirectory() as tmp_dir:
        reporter = IncidentReporter(output_dir=tmp_dir)
        paths = reporter.save_incident(sample_diagnosis)

        json_path = paths["json_path"]
        md_path = paths["md_path"]

        # ตรวจสอบไฟล์ JSON
        assert os.path.exists(json_path)
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            assert data["metadata"]["session_id"] == "test_run_101.txt"
            assert data["root_cause_localization"]["culprit_line_number"] == 42

        # ตรวจสอบไฟล์ Markdown
        assert os.path.exists(md_path)
        with open(md_path, "r", encoding="utf-8") as f:
            content = f.read()
            assert "Incident Diagnostic Report" in content
            assert "Line   42" in content
            assert "[CULPRIT]" in content
            assert "CRITICAL" in content
