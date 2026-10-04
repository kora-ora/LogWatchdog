# คู่มือและแผนงานพัฒนา AI-based Log Anomaly Detection สำหรับ CI/CD Pipeline

> [!NOTE] ภาพรวมโปรเจกต์
> โปรเจกต์พัฒนาระบบตรวจจับความผิดปกติของ Log (Log Anomaly Detection) อัตโนมัติด้วย AI และ Machine Learning สำหรับกระบวนการ CI/CD (เช่น GitHub Actions) โดยพัฒนาด้วยสถาปัตยกรรมแบบ **ตัวต่อเลโก้ (Lego Modular Architecture)** เพื่อให้สามารถแยกชิ้นส่วนพัฒนาและสลับเปลี่ยนอัลกอริทึมได้อย่างอิสระ
> 
> 📖 **ผังสถาปัตยกรรมระบบฉบับเต็ม:** [SYSTEM_ARCHITECTURE.md](SYSTEM_ARCHITECTURE.md) (รองรับการเปิดอ่านและเรนเดอร์กราฟิกใน Obsidian)

---

## 1. สถานะความคืบหน้าของโปรเจกต์ (Project Progress Tracker)

> [!IMPORTANT] สรุปสถานะภาพรวมของโปรเจกต์ (Overall Progress: ~75% - 80%)
> • **Phase 0 (Setup & Architecture):** 100% ✅ (เสร็จสมบูรณ์)
> • **Phase 1 (Baseline Isolation Forest):** 100% ✅ (เสร็จสมบูรณ์)
> • **Phase 2 (DeepLog LSTM & Real GHA Production Evaluation):** 85% 🔄 (แกนหลัก AI และการทดสอบกับ Real Logs เสร็จสิ้น)
> • **Phase 3 (Root Cause Analysis & Explainability):** 0% ⏳ (ขั้นตอนถัดไป: ชี้เป้าบรรทัด Log ที่เป็นต้นตอ)

```mermaid
flowchart LR
    P0["✅ Phase 0\nProject Setup\n& Architecture\n(100%)"] --> P1["✅ Phase 1\nBaseline System\n(Isolation Forest)\n(100%)"]
    P1 --> P2["🔄 Phase 2\nAdvanced CI/CD\n(DeepLog + Real GHA)\n(85%)"]
    P2 --> P3["⏳ Phase 3\nRoot Cause Analysis\n& Explainers\n(รอพัฒนา)"]
    P3 --> P4["⏳ Phase 4\nAlerting & CI/CD\nAction Integration\n(รอพัฒนา)"]
```

- [x] **Phase 0: ออกแบบระบบและจัดวางโครงสร้าง (100%)**
  - [x] ออกแบบผังสถาปัตยกรรมระบบ End-to-End และสถาปัตยกรรมเลโก้ ([SYSTEM_ARCHITECTURE.md](SYSTEM_ARCHITECTURE.md))
  - [x] จัดวางโครงสร้างโฟลเดอร์แบบ Modular (`src/ingestion`, `src/parsers`, `src/features`, `src/models`, `src/explainers`)
  - [x] สร้างชุดข้อมูลตัวอย่าง ([hdfs_sample.log](data/raw/hdfs_sample.log), [cicd_sample.log](data/raw/cicd_sample.log), [hdfs_labels_sample.csv](data/raw/hdfs_labels_sample.csv))
  - [x] เตรียม dependencies และ environment config ([requirements.txt](requirements.txt))
- [x] **Phase 1: พัฒนาระบบรากฐาน (Baseline System) (100%)**
  - [x] **Block 1 (Ingestion):** พัฒนา `HDFSLogLoader` และทดสอบด้วย `pytest`
  - [x] **Block 2 (Parser):** เชื่อมต่อ `DrainParser` สกัด Log Template และ Event ID
  - [x] **Block 3 (Feature):** สร้าง `CountVectorBuilder` นับความถี่ Template ต่อ Block ID
  - [x] **Block 4 (Model):** พัฒนาและเทรน `IsolationForestModel` (Unsupervised Detection)
  - [x] **Block 5 (Evaluation):** ตรวจสอบความถูกต้องร่วมกับ Ground Truth Labels
- [x] **Phase 2: ยกระดับสู่ระบบจริง (Advanced CI/CD Sequential AI) (~85%)**
  - [x] **Sequential Feature Extractor:** สร้าง `SequenceExtractor` ทำ Sliding Window ($w=3$)
  - [x] **Sequential Model (DeepLog):** พัฒนา `DeepLogLSTMModel` (PyTorch 2-Layer LSTM + Adam + Top-$K$)
  - [x] **Zero-Leakage Pipeline:** อัปเกรดโหมด Read-Only Inference (`miner.match()`) ใน `DrainParser` เพื่อป้องกัน Data Leakage
  - [x] **Production Regex Masking:** เพิ่มตัวกรอง Timestamp, Version, Path, Hex, Marker ใน `DrainParser`
  - [x] **Real-world GitHub Actions Dataset:** ดาวน์โหลดและทดสอบกับ Log จริง 45,234 บรรทัดจาก `D2KLab/gha-dataset`
  - [x] **Master Production Pipeline:** พัฒนา [`main.py`](main.py) รัน End-to-End บน Production Logs โดยตรง (ได้ F1 = 85.71%)
  - [x] **Evaluation Metrics Module:** พัฒนา `src/evaluation/metrics.py` คำนวณ Accuracy, Precision, Recall, F1-Score
- [ ] **Phase 3: วิเคราะห์ต้นตอความผิดปกติและการรายงานผล (Root Cause & Explainability) (0%)**
  - [ ] **Root Cause Localization (Block 5 Explainer):** พัฒนา `BaseExplainer` และ `DeepLogExplainer` เพื่อชี้เป้าบรรทัด Log ที่เป็นต้นเหตุ
  - [ ] **Anomaly Summary Report:** สรุปว่าเกิดจาก Step ไหน ข้ามขั้นตอนอะไร หรือเกิด Error ข้อความใด
- [ ] **Phase 4: บูรณาการและระบบแจ้งเตือน (Production Readiness & Alerts) (0%)**
  - [ ] **Alerting Hook:** ส่งการแจ้งเตือนเมื่อพบ Anomaly (เช่น Slack / Webhook / Console Summary)
  - [ ] **Optional Edge Model:** พัฒนา `FlyBrainModel` (Fruit Fly Olfactory Circuit) สำหรับ Edge Computing

---

## 2. คลังความรู้และโมเดลที่ใช้งานในโปรเจกต์ (Core Models & Concepts)

| โมเดล / อัลกอริทึม | ประเภท Anomaly ที่ตรวจจับ | กลไกการทำงาน | จุดเด่น |
| :--- | :--- | :--- | :--- |
| **Isolation Forest** | Frequency / Count Anomaly | สุ่มตัดแบ่งข้อมูล (Tree Partitioning) ข้อมูลที่ผิดปกติจะถูกแยกเดี่ยวได้เร็วกว่าปกติ | ทำงานเร็วมาก ไม่ต้องใช้ GPU เหมาะเป็น Baseline |
| **DeepLog (LSTM)** | Sequential Anomaly | โครงข่ายประสาทเทียมจำลอง "ระบบเดาคำถัดไป" เรียนรู้ลำดับขั้นตอนปกติ หากเจอลำดับผิดคิวจะแจ้งเตือน | จับปัญหาขั้นตอนสลับที่หรือข้ามขั้นตอนได้ดีเยี่ยม |
| **FlyBrain Circuit** *(ทางเลือก)* | Novelty / Out-of-Distribution | จำลองวงจรเห็ดสมองแมลงวัน (Mushroom Body: Kenyon Cells + APL) ผ่าน Sparse Random Projection | เบามาก ระดับ $O(1)$ ไม่ต้องใช้ Backpropagation |

---

## 3. สรุปโครงสร้างระบบแบบเลโก้ (Lego Modular Architecture)

แต่ละบล็อกทำงานเป็นอิสระและเชื่อมต่อกันผ่าน Interface มาตรฐาน:

```
[Brick 1: Ingestion]  ──(Iterator[RawLog])──>  [Brick 2: Parser]
                                                       │
                                                (Parsed Events)
                                                       ▼
[Brick 4: Anomaly Model]  <──(Feature Vectors)──  [Brick 3: Feature]
         │
  (Anomaly Result)
         ▼
[Brick 5: Explainer & Alert]  ──>  (Root Cause Report / Notification)
```

### รายละเอียด Standard Interface:
1. **`src/ingestion/` (Block 1):** `BaseLogLoader` $\rightarrow$ ส่งออกข้อความดิบทีละบรรทัด (`yield line`)
2. **`src/parsers/` (Block 2):** `BaseLogParser` $\rightarrow$ สกัด Template และ Event ID ด้วย Drain3
3. **`src/features/` (Block 3):** `BaseFeatureExtractor` $\rightarrow$ แปลงเป็นตารางความถี่ (Count Vector) หรือลำดับ (Sequence)
4. **`src/models/` (Block 4):** `BaseAnomalyModel` $\rightarrow$ เมธอด `fit(X)` และ `predict(X) -> Result`
5. **`src/explainers/` (Block 5):** `BaseExplainer` $\rightarrow$ เมธอด `explain(Result) -> Report` ระบุบรรทัดที่เป็นปัญหา

---

## 4. โครงสร้างโฟลเดอร์ไฟล์ในโปรเจกต์ (Project Directory Layout)

```text
AI Project/
├── data/
│   ├── raw/                           # ไฟล์ Log ดิบตัวอย่าง (HDFS, CI/CD, Labels)
│   └── processed/                     # ข้อมูลที่ผ่านการ parse หรือเตรียมพร้อมเทรน
├── src/
│   ├── ingestion/                     # 🧱 Block 1: ตัวอ่าน Log ดิบ (BaseLogLoader, HDFSLogLoader)
│   ├── parsers/                       # 🧱 Block 2: ตัวแปลง Template (BaseLogParser, Drain3)
│   ├── features/                      # 🧱 Block 3: ตัวสกัด Feature (BaseFeatureExtractor)
│   ├── models/                        # 🧱 Block 4: โมเดลตรวจจับ (BaseAnomalyModel)
│   └── explainers/                    # 🧱 Block 5: วิเคราะห์หาสาเหตุ (BaseExplainer)
├── tests/
│   └── test_ingestion.py              # ชุดทดสอบอัตโนมัติของ Block 1
├── requirements.txt                   # รายการไลบรารีที่จำเป็น
├── PROJECT_ROADMAP.md                 # แผนการพัฒนาและติดตามความคืบหน้า (เอกสารนี้)
├── SYSTEM_ARCHITECTURE.md             # ผังสถาปัตยกรรมระบบ Map of Content (เปิดใน Obsidian)
├── system_architecture/               # โฟลเดอร์แยกเอกสารสถาปัตยกรรมระบบ (01-06)
├── RESEARCH_AND_DATASET_REFERENCES.md # เอกสารอ้างอิงงานวิจัยและชุดข้อมูล
└── README.md                          # บทสรุปย่อของโปรเจกต์
```

---

## 5. แนะนำการติดตั้งสภาพแวดล้อม (Local Environment Setup)

โปรเจกต์นี้แนะนำให้รันบนคอมพิวเตอร์ของคุณเอง เนื่องจากชิ้นส่วนต่างๆ ประมวลผลบน Multi-core CPU ได้อย่างมีประสิทธิภาพ:

```bash
# 1. สร้าง Virtual Environment
python3 -m venv venv

# 2. เปิดใช้งาน venv
# สำหรับ Linux:
source venv/bin/activate
# สำหรับ Windows (PowerShell):
# .\venv\Scripts\Activate.ps1

# 3. ติดตั้ง Dependencies
pip install -r requirements.txt
```

---

*เอกสารฉบับนี้จะได้รับการอัปเดตอย่างต่อเนื่องตามความคืบหน้าของแต่ละบล็อกการพัฒนา*
