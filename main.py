"""
=============================================================================
🚀 Master Production Pipeline: AI Log Anomaly Detection on Real GitHub Actions
=============================================================================
ไฟล์นี้เป็นจุดเริ่มรันระบบ (Master Entry Point) โดยใช้ข้อมูล Production Log จริง
จาก GitHub Actions Runner (45,234 บรรทัดจาก D2KLab/gha-dataset / PyTables)
ร่วมกับระบบ Regex Masking และโมเดล DeepLog LSTM แบบ Zero-Leakage 100%

ขั้นตอนการทำงาน:
1. Ingestion: โหลด Production Logs จาก data/raw/real_gha/
2. Masked Parsing: แปลงข้อความ Log ดิบเป็น Template ด้วย DrainParser + Regex Masking
3. Feature Extraction: สกัดลำดับเหตุการณ์ด้วย SequenceExtractor (Sliding Window w=3)
4. Deep Learning: เทรนโมเดล DeepLog LSTM บนรอบปกติจริง (Ubuntu, macOS, Windows)
5. Evaluation: ประเมินผลบนรอบปกติใหม่ (Unseen Python 3.11) และรอบที่ล้มเหลวจริง (Real Anomalies)
=============================================================================
"""

import glob
import os
import sys
import pandas as pd

# นำเข้า Lego Bricks จาก src/
from src.parsers.drain_parser import DrainParser
from src.features.sequence_extractor import SequenceExtractor
from src.models.deeplog_lstm import DeepLogLSTMModel
from src.evaluation.metrics import calculate_metrics, format_classification_report


def run_production_pipeline():
    print("\n" + "=" * 75)
    print("🚀 เริ่มต้นระบบ AI Log Anomaly Detection บน Production Log (GitHub Actions)")
    print("=" * 75)

    real_dir = "data/raw/real_gha"
    if not os.path.exists(real_dir):
        print(f"❌ ไม่พบโฟลเดอร์ {real_dir}")
        return

    # -------------------------------------------------------------------------
    # สเต็ปที่ 1: เตรียมชุดข้อมูล Production (แยก Train / Test แบบ Stratified)
    # -------------------------------------------------------------------------
    print("\n[สเต็ปที่ 1] 📥 จัดเตรียมชุดข้อมูลจริงจาก GitHub Actions Runner...")
    
    test_files = sorted(glob.glob(f"{real_dir}/*Test*.txt"))
    ubuntu_files = [f for f in test_files if "ubuntu" in f]
    macos_files = [f for f in test_files if "macos" in f]
    windows_files = [f for f in test_files if "windows" in f]

    # Training Set (รอบปกติจริง): Python 3.8, 3.9, 3.10 รวม 9 Jobs จาก 3 OS
    train_files = ubuntu_files[:3] + macos_files[:3] + windows_files[:3]

    # Test Set (ข้อสอบจริงที่ไม่เคยเห็น): Python 3.11 บน 3 OS (3 Jobs) + Job ที่ล้มเหลวจริง (3 Jobs)
    unseen_normal_files = [ubuntu_files[3], macos_files[3], windows_files[3]]
    anomaly_files = [
        f"{real_dir}/1_Build source distribution.txt",    # Job แท้งตั้งแต่ 8 บรรทัดแรก
        f"{real_dir}/5_Twine check.txt",                 # Job โดน Abort หลัง prepare
        f"{real_dir}/3_build_wheels_windows.txt"         # Build matrix failure (35 บรรทัด)
    ]

    print(f"   -> [Training Set]  รอบปกติใช้สอนโมเดล: {len(train_files)} Jobs (Python 3.8 - 3.10 บน Ubuntu, macOS, Windows)")
    print(f"   -> [Test Set]      ข้อสอบ Unseen ท้าทาย AI: {len(unseen_normal_files) + len(anomaly_files)} Jobs")
    print(f"      • Unseen Normal: 3 Jobs ({[os.path.basename(f) for f in unseen_normal_files]})")
    print(f"      • Real Anomalies: 3 Jobs ({[os.path.basename(f) for f in anomaly_files]})")

    # -------------------------------------------------------------------------
    # สเต็ปที่ 2: แปลงข้อความด้วย DrainParser + Regex Masking (Train Mode)
    # -------------------------------------------------------------------------
    print("\n[สเต็ปที่ 2] 🧱 ขุดแม่พิมพ์ Log Template ด้วย DrainParser + Regex Masking...")
    parser = DrainParser()

    train_events = []
    total_train_lines = 0

    for f in train_files:
        sid = os.path.basename(f)
        with open(f, "r", errors="ignore") as fp:
            for line in fp:
                clean = line.strip()
                if not clean:
                    continue
                total_train_lines += 1
                parsed = parser.parse_line(clean, update_model=True)  # Train: สร้าง/อัปเดตแม่พิมพ์
                train_events.append({"session_id": sid, "template_id": parsed["template_id"]})

    print(f"   -> ขุด Template สำเร็จจาก {total_train_lines:,} บรรทัดจริง")

    # -------------------------------------------------------------------------
    # สเต็ปที่ 3: สกัดลำดับเหตุการณ์ด้วย SequenceExtractor (Sliding Window w=3)
    # -------------------------------------------------------------------------
    print("\n[สเต็ปที่ 3] ⚙️ สกัดลำดับเวลาด้วย SequenceExtractor (Sliding Window w=3)...")
    extractor = SequenceExtractor(window_size=3)
    train_seq_data = extractor.fit_transform(train_events)
    train_vocab_size = train_seq_data["vocab_size"]
    UNKNOWN_TOKEN = train_vocab_size  # รหัสตัวเลขสำหรับเหตุการณ์แปลกปลอม

    print(f"   -> ขนาด Vocabulary แม่พิมพ์ที่พบใน Train: {train_vocab_size} templates")
    print(f"   -> คู่ข้อมูล X, y สำหรับฝึกสอน: X={train_seq_data['X'].shape}, y={train_seq_data['y'].shape}")

    # เตรียม Test Set ในโหมด Read-Only (ห้ามดัดแปลง Prefix Tree)
    test_sessions = {}
    test_labels = {}

    for f in unseen_normal_files:
        sid = os.path.basename(f)
        seq = []
        with open(f, "r", errors="ignore") as fp:
            for line in fp:
                clean = line.strip()
                if not clean:
                    continue
                parsed = parser.parse_line(clean, update_model=False)  # Test: Read-Only
                tid = UNKNOWN_TOKEN if parsed["is_unseen"] else parsed["template_id"]
                seq.append(tid)
        test_sessions[sid] = seq
        test_labels[sid] = 0

    for f in anomaly_files:
        sid = os.path.basename(f)
        seq = []
        with open(f, "r", errors="ignore") as fp:
            for line in fp:
                clean = line.strip()
                if not clean:
                    continue
                parsed = parser.parse_line(clean, update_model=False)  # Test: Read-Only
                tid = UNKNOWN_TOKEN if parsed["is_unseen"] else parsed["template_id"]
                seq.append(tid)
        test_sessions[sid] = seq
        test_labels[sid] = 1

    # -------------------------------------------------------------------------
    # สเต็ปที่ 4: ฝึกสอนโมเดล DeepLog LSTM
    # -------------------------------------------------------------------------
    print("\n[สเต็ปที่ 4] 🤖 ฝึกสอนโมเดล DeepLog LSTM บนรอบปกติของ GitHub Actions...")
    model = DeepLogLSTMModel(
        vocab_size=train_vocab_size + 2,
        window_size=3,
        hidden_dim=32,
        embedding_dim=32,
        num_layers=2,
        epochs=25,
        lr=0.01,
        top_k=5
    )
    print("   -> กำลังเทรนโมเดลผ่าน PyTorch (25 Epochs)...")
    model.fit(train_seq_data["X"], train_seq_data["y"])
    print("   -> ฝึกสอนเสร็จสิ้น!")

    # -------------------------------------------------------------------------
    # สเต็ปที่ 5: ทำนายผลและคำนวณ Metrics บน Production Test Set
    # -------------------------------------------------------------------------
    print("\n[สเต็ปที่ 5] 🎯 ประเมินผลบนข้อสอบจริง (Production Test Evaluation)...")
    y_true = []
    y_pred = []
    table_rows = []

    for sid, seq in test_sessions.items():
        actual = test_labels[sid]
        pred = model.predict_session(seq)
        y_true.append(actual)
        y_pred.append(pred)

        status = "✅ ถูกต้อง" if actual == pred else "❌ ผิดพลาด"
        table_rows.append({
            "Job / Session Name": sid,
            "Type": "Unseen Normal" if actual == 0 else "Real Anomaly",
            "Actual": "Anomaly" if actual == 1 else "Normal",
            "Prediction": "🚨 Anomaly" if pred == 1 else "✅ Normal",
            "Result": status
        })

    # แสดงตารางผลลัพธ์
    df_result = pd.DataFrame(table_rows).set_index("Job / Session Name")
    print("\n" + df_result.to_string())

    # แสดงรายงานมาตรวัดทางคณิตศาสตร์
    metrics = calculate_metrics(y_true, y_pred)
    print("\n" + format_classification_report(metrics, model_name="DeepLog LSTM (Production GHA)"))


if __name__ == "__main__":
    run_production_pipeline()
