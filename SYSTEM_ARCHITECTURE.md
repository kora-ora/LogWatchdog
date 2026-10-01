# สถาปัตยกรรมระบบ AI-based Log Anomaly Detection (System Architecture)

> [!NOTE] วัตถุประสงค์ของเอกสาร
> เอกสารฉบับนี้จัดทำขึ้นเพื่อแสดง **ลำดับและโครงสร้างการทำงานจริงของโปรเจกต์** ในรูปแบบผังสถาปัตยกรรมแบบบล็อกแนวตั้ง (Architectural Block Diagram Style คล้ายผังโครงสร้างของเปเปอร์ AI มาตรฐานระดับสากล) และแสดง **โครงสร้างแบบตัวต่อเลโก้ (Lego Modular Architecture)** เพื่อให้สามารถพัฒนาแยกส่วนและนำมาประกอบกันได้อย่างเป็นระเบียบ โดยรองรับการเปิดอ่านและเรนเดอร์กราฟิกผ่านโปรแกรม **Obsidian**

---

## 1. ผังสถาปัตยกรรมลำดับการทำงานของระบบ (End-to-End System Workflow)

ผังนี้แสดงการไหลของข้อมูลตั้งแต่ข้อมูลดิบด้านล่าง (Inputs) ผ่านชั้นการประมวลผลและการเลือกใช้โมเดลที่เหมาะสมที่สุดตามโจทย์ จนถึงผลลัพธ์การตรวจจับและชี้เป้าปัญหาด้านบน (Outputs):

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
            M3["FlyBrain Circuit\n(Sparse Coding / เหมาะกับ Novelty Detection)"]:::engineStyle
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
    ParsedTokens --> M3

    M1 --> ScoreCalc
    M2 --> ScoreCalc
    M3 --> ScoreCalc

    ScoreCalc --> DecisionCheck
    DecisionCheck -->|"ปกติ (No)"| NormalResult
    DecisionCheck -->|"ผิดปกติ (Yes)"| AnomalyAlert

    AnomalyAlert --> RootCause
    M2 -.->|"ส่งค่า Loss / Mismatch Step"| RootCause
```

---

## 2. สถาปัตยกรรมแบบตัวต่อเลโก้ (Lego Modular Architecture)

เพื่อให้การพัฒนาระบบสามารถทำแยกชิ้นส่วนกันได้อย่างอิสระ แต่ละส่วนจะมี **Standard Interface (ข้อต่อมาตรฐาน)** กำกับไว้ สามารถสลับเปลี่ยนอัลกอริทึมได้โดยไม่กระทบกับส่วนอื่นของระบบ:

```mermaid
flowchart LR
    classDef b1 fill:#e3f2fd,stroke:#1565c0,stroke-width:2px;
    classDef b2 fill:#fff3e0,stroke:#e65100,stroke-width:2px;
    classDef b3 fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px;
    classDef b4 fill:#fce4ec,stroke:#c2185b,stroke-width:2px;
    classDef b5 fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px;

    subgraph Brick1["🧱 Block 1: Ingestion"]
        L1["HDFSLoader"]
        L2["GitHubActionsLoader"]
        L3["MockLogGenerator"]
    end
    class Brick1 b1;

    subgraph Brick2["🧱 Block 2: Parser"]
        P1["Drain3Parser"]
        P2["RegexParser"]
    end
    class Brick2 b2;

    subgraph Brick3["🧱 Block 3: Feature Extractor"]
        F1["CountVectorBuilder"]
        F2["SequenceTokenizer"]
    end
    class Brick3 b3;

    subgraph Brick4["🧱 Block 4: Anomaly Model"]
        M1["IsolationForestModel"]
        M2["DeepLogLSTMModel"]
        M3["FlyBrainModel"]
    end
    class Brick4 b4;

    subgraph Brick5["🧱 Block 5: Explainer & Alert"]
        E1["RootCauseLocator"]
        E2["AlertDispatcher (Slack/PR)"]
    end
    class Brick5 b5;

    Brick1 == "Iterator[RawLog]" ==> Brick2
    Brick2 == "List[ParsedEvent]" ==> Brick3
    Brick3 == "Feature Tensors / Vectors" ==> Brick4
    Brick4 == "AnomalyResult" ==> Brick5
```

---

## 3. สรุปข้อต่อมาตรฐาน (Standard Interfaces สำหรับนักพัฒนา)

| เลโก้บล็อก             | ชื่อ Interface หลัก    | Method ที่ต้องมี                  | Output ที่ส่งต่อให้บล็อกถัดไป                 |
| :--------------------- | :--------------------- | :-------------------------------- | :-------------------------------------------- |
| **Block 1: Ingestion** | `BaseLogLoader`        | `load() -> Iterator[str]`         | ข้อความ Log ดิบทีละบรรทัด                     |
| **Block 2: Parser**    | `BaseLogParser`        | `parse(line: str) -> Event`       | รหัส Event ID และ Parameters                  |
| **Block 3: Feature**   | `BaseFeatureExtractor` | `fit_transform(events) -> Matrix` | Matrix ตัวเลข / ลำดับ Sequence สำหรับโมเดล    |
| **Block 4: Model**     | `BaseAnomalyModel`     | `fit(X)`, `predict(X) -> Result`  | คะแนนความผิดปกติ (Anomaly Score) และป้ายกำกับ |
| **Block 5: Explainer** | `BaseExplainer`        | `explain(Result) -> Report`       | บรรทัด Log ต้นเหตุ และคำอธิบายความผิดปกติ     |

> [!TIP] ประโยชน์ของการออกแบบลักษณะนี้
> 1. **เริ่มง่าย (Phase 1 Baseline):** สามารถเริ่มต้นด้วยการประกอบ `HDFSLoader` + `Drain3Parser` + `CountVectorBuilder` + `IsolationForestModel` เข้าด้วยกันเพื่อทำ Baseline ให้เสร็จอย่างรวดเร็ว
> 2. **ยกระดับง่าย (Phase 2 CI/CD):** เมื่อต้องการทำ Sequential Anomaly ก็เพียงแค่เปลี่ยนชิ้นส่วน `Feature` เป็น `SequenceTokenizer` และเปลี่ยน `Model` เป็น `DeepLogLSTMModel` โดยที่ส่วนอื่นยังคงใช้งานร่วมกันได้
> 3. **ทดลองสิ่งใหม่ได้อิสระ:** หากต้องการทดสอบอัลกอริทึมจำพวก Bio-inspired (เช่น สมองแมลงวัน) ก็เพียงแค่สร้าง Class `FlyBrainModel` มาเสียบใน Block 4 ได้ทันที
