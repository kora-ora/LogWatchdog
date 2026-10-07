# 🗂️ Data Provenance & Structure Guidelines

เอกสารฉบับนี้กำหนดการแบ่งแยกและแหล่งที่มาของชุดข้อมูลทั้งหมดในโปรเจกต์ เพื่อความโปร่งใส ปราศจากข้อมูลเท็จ (Zero-Deception / Absolute Authenticity):

---

## 1. 🧪 `data/raw/synthetic/` (Synthetic & Benchmark Mock Data)
* **สถานะ:** ข้อมูลสังเคราะห์ / จำลองขึ้นเพื่อการทดสอบทางทฤษฎีและ Unit Test
* **ไฟล์:**
  * `cicd_benchmark.log` และ `cicd_benchmark_labels.csv`: ออกแบบมาเพื่อทดสอบการจับเคส Step-Skipping / ลำดับข้ามขั้นตอน
  * `cicd_sample.log`: ไฟล์สั้นสำหรับ smoke test การโหลด CI/CD
  * `hdfs_sample.log` และ `hdfs_labels_sample.csv`: ตัวอย่างสั้นสำหรับ unit test ของ Block 1 - 3

---

## 2. 🐙 `data/raw/real_gha/` (Authentic CI/CD Production Logs)
* **สถานะ:** ข้อมูลจริง 100% จาก Production Runner ของ GitHub Actions
* **แหล่งที่มา:** บันทึกการรัน Test Matrix ของโปรเจกต์ `PyTables` บน Linux (Ubuntu), macOS และ Windows
* **ขนาด:** 45,234 บรรทัด รวม 15 Jobs
* **วัตถุประสงค์:** ใช้วัดผลการทำงานบน CI/CD Pipeline จริง

---

## 3. 🏛️ `data/raw/loghub_hdfs/` (Authentic Distributed System Benchmark)
* **สถานะ:** ข้อมูลจริง 100% มาตรฐานระดับโลก (LogHub Benchmark จาก The Chinese University of Hong Kong)
* **แหล่งที่มา:** บันทึกจริงจากคลัสเตอร์ Hadoop 200+ Nodes บน Amazon EC2
* **ไฟล์:**
  * `HDFS_100k.log`: ข้อความ Log ดิบ 100,000 บรรทัด ครอบคลุม 7,940 Block Sessions
  * `anomaly_label.csv`: เฉลย Ground-Truth จากวิศวกรระบบ Hadoop ตัวจริง (575,062 Blocks, โดยใน 100k log มี 313 Anomaly Blocks และ 7,627 Normal Blocks)
* **วัตถุประสงค์:** ใช้วัดประสิทธิภาพประชันระหว่าง Isolation Forest, DeepLog LSTM และ Hybrid Ensemble ในระดับ Benchmark สากล

---

## 4. 🔬 `data/raw/hdfs_full_parquet/` (Full HDFS Pre-Tokenized Benchmark)
* **สถานะ:** ข้อมูลจริง 100% จากชุดข้อมูลเต็มของ HDFS (11,175,629 บรรทัด, 575,062 Blocks) ที่ผ่านการ Pre-tokenize ด้วย Drain เป็น Parquet format
* **แหล่งที่มา:** Hugging Face Dataset: `honicky/hdfs-logs-encoded-blocks`
* **ไฟล์:**
  * `test-00000-of-00001.parquet` (16.58 MB): 57,507 Blocks (Normal: 55,845, Anomaly: 1,662)
  * `train-00000-of-00003.parquet` (44.18 MB): 153,350 Blocks (Normal: 148,833, Anomaly: 4,517)
  * `validation-00000-of-00001.parquet` (16.60 MB)
* **วัตถุประสงค์:** ใช้ทำ **Zero-OOV Sequence Benchmark** เพื่อพิสูจน์ขีดความสามารถการทำนายและตรวจจับลำดับขั้นตอน (Sequential Order Violations) ของ DeepLog LSTM ล้วนๆ โดยตัดอิทธิพลของ Rule-based OOV ออก 100%

