# AI-based Log Anomaly Detection สำหรับ CI/CD Pipeline

ระบบตรวจจับความผิดปกติของ Log (Log Anomaly Detection) อัตโนมัติด้วย AI/Machine Learning สำหรับงาน CI/CD Pipeline (เช่น GitHub Actions) โดยผสมผสานชุดข้อมูลมาตรฐานสากลจาก LogHub (HDFS) และชุดข้อมูลจำลองเสมือนจริง (Mock CI/CD Logs)

---

## สารบัญเอกสารสำคัญ
- 📖 [PROJECT_ROADMAP.md](PROJECT_ROADMAP.md) - **คู่มือและแผนงานพัฒนา:** อธิบายแนวคิดพื้นฐาน, สถานะความคืบหน้าของแต่ละบล็อก และวิธีติดตั้งสภาพแวดล้อม
- 📐 [SYSTEM_ARCHITECTURE.md](SYSTEM_ARCHITECTURE.md) - **ผังสถาปัตยกรรมระบบ:** แผนผังการทำงาน End-to-End และสถาปัตยกรรมตัวต่อเลโก้ (Lego Modular Architecture) สำหรับเปิดดูใน Obsidian

---

## ภาพรวมการดำเนินงาน

### Phase 1: สร้างระบบรากฐาน (Baseline)
- **Dataset:** HDFS จาก LogHub (มี Block ID และ Ground Truth Labels)
- **Parser:** Drain3 Algorithm (แปลง Raw text เป็น Template)
- **Feature:** Template Count Vector
- **Model:** Isolation Forest (Unsupervised) และ Logistic Regression (Supervised Baseline)
- **Evaluation:** Precision, Recall, F1-Score

### Phase 2: ยกระดับสู่ระบบจริง (Advanced CI/CD)
- **Dataset:** Mock GitHub Actions Logs (จำลอง Timeout, IAM Error, OOM)
- **Model:** DeepLog Architecture (LSTM Sequential Predictor)
- **Capabilities:** ตรวจจับลำดับเหตุการณ์ที่ผิดเพี้ยน (Sequential Anomaly) และชี้เป้าสาเหตุของปัญหา (Root Cause Analysis)
