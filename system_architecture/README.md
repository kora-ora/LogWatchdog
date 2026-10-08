# 📁 โฟลเดอร์สถาปัตยกรรมระบบ (System Architecture Directory)

โฟลเดอร์นี้รวบรวมเอกสารสถาปัตยกรรมระบบแบบแยกหัวข้อ เพื่อความสะดวกในการเปิดอ่านและจัดการผ่าน Obsidian Vault:

| หัวข้อ | ลิงก์เอกสาร | คำอธิบายย่อ |
| :--- | :--- | :--- |
| **01** | [[01_end_to_end_workflow\|01_end_to_end_workflow.md]] | ผังภาพรวมการทำงาน 6 เลเยอร์ ตั้งแต่ Input จนถึง Alert & Root Cause |
| **02** | [[02_lego_modular_architecture\|02_lego_modular_architecture.md]] | สถาปัตยกรรมตัวต่อเลโก้และข้อต่อมาตรฐาน (Standard Interfaces) |
| **03** | [[03_count_vector_transformation\|03_count_vector_transformation.md]] | การแปลงข้อมูล Log ดิบ สู่ตาราง Count Vector สำหรับ Isolation Forest |
| **04** | [[04_sequential_sliding_window\|04_sequential_sliding_window.md]] | การตัดหน้าต่าง Sliding Window สำหรับโมเดล DeepLog / LSTM |
| **05** | [[05_lstm_execution_flow\|05_lstm_execution_flow.md]] | แผนภาพจำลองกระบวนการทำงานระดับเซลล์ประสาท LSTM และโค้ด PyTorch |
| **06** | [[06_lstm_neural_network_internals\|06_lstm_neural_network_internals.md]] | การทำงานของ Neural Network ภายใน LSTM, 4 ประตู, และการเชื่อมต่อข้าม Layer |
| **07** | [[07_evaluation_methodology_and_data_leakage_audit\|07_evaluation_methodology_and_data_leakage_audit.md]] | ระเบียบวิธีทดสอบและตรวจสอบการป้องกัน Data Leakage แบบ Zero-Leakage |
| **08** | [[08_root_cause_localization_explainer\|08_root_cause_localization_explainer.md]] | การชี้เป้าบรรทัดต้นเหตุ Context Window และสร้างรายงาน Incident Diagnostic |
| **09** | [[09_hybrid_dual_engine_synergy\|09_hybrid_dual_engine_synergy.md]] | สถาปัตยกรรม Hybrid Dual-Engine และกลยุทธ์ Cascaded Synergy (ลด FP 46.9%) |

> 🏠 **กลับสู่หน้าหลัก:** [[SYSTEM_ARCHITECTURE]]
