# 01. ผังสถาปัตยกรรมลำดับการทำงานของระบบ (End-to-End System Workflow)

> [!NOTE] นำทางด่วน (Navigation)
> 🏠 **กลับหน้าสารบัญหลัก:** [[SYSTEM_ARCHITECTURE]] | ➡️ **หัวข้อถัดไป:** [[02_lego_modular_architecture]]

---

## 📌 บทนำและภาพรวม

ผังสถาปัตยกรรมนี้แสดงการไหลของข้อมูลตั้งแต่ข้อมูลดิบด้านล่าง (**Layer 0: Input Sources**) ผ่านชั้นการประมวลผลและการเลือกใช้โมเดลที่เหมาะสมที่สุดตามโจทย์ (**Layer 1 - 4**) จนกระทั่งถึงผลลัพธ์การตรวจจับและชี้เป้าปัญหาด้านบน (**Layer 5: Outputs & Root Cause Localization**):

```mermaid
flowchart TD
    %% Styling Classes
    classDef inputStyle fill:#eceff1,stroke:#607d8b,stroke-width:2px,color:#263238;
    classDef parseStyle fill:#e3f2fd,stroke:#1976d2,stroke-width:2px,color:#0d47a1;
    classDef featureStyle fill:#fff3e0,stroke:#f57c00,stroke-width:2px,color:#e65100;
    classDef engineStyle fill:#ede7f6,stroke:#512da8,stroke-width:2px,color:#311b92;
    classDef decisionStyle fill:#e8f5e9,stroke:#388e3c,stroke-width:2px,color:#1b5e20;
    classDef outputAlert fill:#ffebee,stroke:#d32f2f,stroke-width:2px,color:#b71c1c;
    classDef outputNormal fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px,color:#1b5e20;
    classDef explainStyle fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px,color:#4a148c;

    %% 1. Raw Inputs Layer
    subgraph Layer0["📥 1. Input Sources (แหล่งข้อมูล Log ดิบ)"]
        RawHDFS["HDFS Benchmark Logs\n(ชุดข้อมูลทดสอบมาตรฐาน LogHub)"]:::inputStyle
        RawCICD["CI/CD Pipeline Logs\n(GitHub Actions: Build, Test, Deploy)"]:::inputStyle
    end

    %% 2. Preprocessing & Parsing Layer
    subgraph Layer1["⚙️ 2. Log Parsing & Structuring (แปลงข้อความเป็นโครงสร้าง)"]
        DrainParser["Drain3 Template Miner\n(แยก Log ดิบออกเป็น Template คงที่ และตัวแปรผัน)"]:::parseStyle
        ParsedTokens["Structured Event Stream\n[Event ID: E1, E14, E28, ...]"]:::parseStyle
    end

    %% 3. Feature Transformation Layer
    subgraph Layer2["📐 3. Feature Transformation (สกัดคุณลักษณะตามโจทย์)"]
        direction LR
        CountVec["Count Vector Extractor\n(นับความถี่ต่อ Session/Block)"]:::featureStyle
        SeqWindow["Sliding Window Tokenizer\n(จัดชุดลำดับเหตุการณ์ตามเวลา)"]:::featureStyle
    end

    %% 4. Modular Model Engine
    subgraph Layer3["🧠 4. Core Detection Engine (เลือกใช้โมเดลตามความเหมาะสม)"]
        direction TB
        subgraph ModelOptions["โมเดลที่เลือกใช้งานตามเป้าหมาย (Swappable Core)"]
            M1["Isolation Forest\n(เน้นเร็ว / เหมาะกับ Count Anomaly)"]:::engineStyle
            M2["DeepLog (LSTM)\n(เน้นลำดับเวลา / เหมาะกับ Sequential Anomaly)"]:::engineStyle
        end
    end

    %% 5. Decision & Evaluation Layer
    subgraph Layer4["⚖️ 5. Anomaly Decision & Scoring (ตัดสินผล)"]
        ScoreCalc["Anomaly Scoring & Threshold\n(คำนวณคะแนนความผิดปกติเทียบค่าเกณฑ์)"]:::decisionStyle
        DecisionCheck{"Score > Threshold\nหรือ Next-Event ผิดคิว?"}:::decisionStyle
    end

    %% 6. Outputs & Explainability
    subgraph Layer5["📢 6. Outputs & Action (ผลลัพธ์และการแจ้งเตือน)"]
        NormalResult["✅ Normal Status\n(ระบบทำงานตามปกติ ผ่านเข้าสู่สเต็ปถัดไป)"]:::outputNormal
        AnomalyAlert["🚨 Anomaly Detected\n(พบความผิดปกติ แจ้งเตือนทีม DevOps)"]:::outputAlert
        
        subgraph ExplainBox["🔍 Root Cause Localization"]
            RootCause["วิเคราะห์หาสาเหตุของปัญหา (Root Cause)\n- ชี้เป้าบรรทัด Log ที่ผิดปกติ\n- ระบุ Error Template (Timeout, OOM, IAM Denied)"]:::explainStyle
        end
    end

    %% Flow Connections
    RawHDFS --> DrainParser
    RawCICD --> DrainParser
    DrainParser --> ParsedTokens

    ParsedTokens -->|"ส่งต่อข้อมูลความถี่"| CountVec
    ParsedTokens -->|"ส่งต่อข้อมูลลำดับเวลา"| SeqWindow

    CountVec --> M1
    SeqWindow --> M2

    M1 --> ScoreCalc
    M2 --> ScoreCalc

    ScoreCalc --> DecisionCheck
    DecisionCheck -->|"ปกติ (No)"| NormalResult
    DecisionCheck -->|"ผิดปกติ (Yes)"| AnomalyAlert

    AnomalyAlert --> RootCause
    M2 -.->|"ส่งค่า Loss / Mismatch Step"| RootCause
```

---

## 🔍 รายละเอียดของแต่ละเลเยอร์ (Layer Breakdown)

### Layer 0: แหล่งข้อมูล Log ดิบ (Input Sources)
- **HDFS Benchmark Logs:** ชุดข้อมูลทดสอบมาตรฐานระดับสากลจาก LogHub มีโครงสร้าง Block ID ชัดเจน เหมาะสำหรับการพัฒนา Baseline และการสอบทานความถูกต้องของโค้ด
- **CI/CD Pipeline Logs:** ข้อความ Log จริงจากการรัน CI/CD เช่น GitHub Actions (Build, Test, Deploy) ซึ่งมีทั้ง Log ปกติ และ Log ที่เกิดความผิดพลาด เช่น Network Timeout, Out-Of-Memory (OOM), หรือสิทธิ์ IAM ถูกปฏิเสธ

### Layer 1: การแปลง Log ดิบเป็นโครงสร้าง (Parsing & Structuring)
- **Drain3 Template Miner:** ใช้อัลกอริทึม Fixed-Depth Parse Tree เพื่อตัดตัวแปรผัน (IP, Block ID, Hex, Timestamp) ออก เหลือเพียง Template โครงสร้างข้อความคงที่
- **Structured Event Stream:** กำหนด Event ID เฉพาะตัว (เช่น $E1, E2, E3, \dots$) ทำให้ข้อความภาษามนุษย์ถูกแปลงเป็นรหัสตัวเลขเชิงโครงสร้าง

### Layer 2: การสกัดคุณลักษณะ (Feature Transformation)
- **Count Vector:** นับความถี่ของแต่ละ Event ID ที่เกิดขึ้นใน 1 Session / Block ID (เหมาะกับสถิติจำนวนครั้ง)
- **Sliding Window:** ตัดหน้าต่างลำดับเหตุการณ์ตามแกนเวลาด้วยขนาดคงที่ (เช่น $w=3$) เพื่อนำไปพยากรณ์เหตุการณ์ถัดไป ($X \to y$)

### Layer 3: แกนโมเดลตรวจจับแบบถอดเปลี่ยนได้ (Modular Core Detection Engine)
- **Isolation Forest:** โมเดล Unsupervised Tree สำหรับการตัดแยกจุดผิดปกติจาก Count Vector อย่างรวดเร็ว
- **DeepLog (LSTM):** นิวรอลเน็ตเวิร์ก 2 เลเยอร์ที่เรียนรู้ลำดับขั้นตอนการทำงานปกติ หากมี Event ผิดลำดับจะตรวจจับได้ทันที (Sequential Anomaly Predictor)

### Layer 4: การคำนวณคะแนนและตัดสินผล (Decision & Scoring)
- ประเมินคะแนน Anomaly Score หรือตรวจสอบว่า Target Event อยู่ในกลุ่ม Top-$K$ Candidates หรือไม่
- เปรียบเทียบกับค่า Threshold ที่กำหนดไว้เพื่อสรุปผลว่า ปกติ (Normal) หรือ ผิดปกติ (Anomaly)

### Layer 5: ผลลัพธ์และการชี้เป้าสาเหตุ (Outputs & Explainability)
- **Normal:** ปล่อยผ่านให้กระบวนการใน Pipeline ทำงานต่อ
- **Anomaly Alert:** ส่งสัญญาณแจ้งเตือนทีม DevOps
- **Root Cause Localization:** ดึงบรรทัด Log ต้นตอและถอดรหัส Template ที่เป็น Error ชี้เป้าให้ผู้พัฒนาแก้ไขได้ตรงจุดทันที

---

> [!TIP] หัวข้อถัดไป
> ไปทำความเข้าใจโครงสร้างการออกแบบแบบตัวต่อเลโก้และ Interface มาตรฐานได้ที่:
> ➡️ [[02_lego_modular_architecture]]
