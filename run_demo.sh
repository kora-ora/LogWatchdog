#!/bin/bash
# Script สำหรับเปิดรัน Web Demo Dashboard (Streamlit)
echo "กำลังเปิดระบบ AI Log Anomaly Detection Web Demo Dashboard..."
./venv/bin/streamlit run app.py --server.port 8501
