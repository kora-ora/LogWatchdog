import os
import sys
import pandas as pd

# เพิ่ม Root directory เข้า sys.path เพื่อให้ import src ได้
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.ingestion.cicd_loader import CICDLogLoader
from src.parsers.drain_parser import DrainParser


def display_drain_training_data():
    """
    ฟังก์ชันเปิดกล่องดำ (White-Box Inspection):
    แสดงข้อมูลที่ส่งเข้าฝึกสอน DrainParser และผลลัพธ์การขุด Template
    """
    log_path = "data/raw/synthetic/cicd_benchmark.log"
    loader = CICDLogLoader(log_path)
    parser = DrainParser()

    # 1. กำหนด Train Set (รอบปกติ Run 101 ถึง 107)
    train_run_ids = set([f"Run_{i}" for i in range(101, 108)])

    records = []
    line_number = 0

    for line in loader.load():
        run_id = CICDLogLoader.extract_run_id(line)
        
        # กรองเฉพาะบรรทัดที่อยู่ใน Training Set
        if run_id in train_run_ids:
            line_number += 1
            clean_msg = CICDLogLoader.extract_message(line)
            
            # ส่งเข้า Train DrainParser
            parsed = parser.parse_line(clean_msg, update_model=True)
            
            records.append({
                "Line#": line_number,
                "Run ID": run_id,
                "Raw Message (ข้อความสะอาด)": clean_msg,
                "Event ID": parsed["template_id"],
                "Mined Template (แม่พิมพ์ที่ขุดได้)": parsed["template_str"],
            })

    df = pd.DataFrame(records)

    # -------------------------------------------------------------
    # ตารางที่ 1: สรุปแม่พิมพ์ (Log Template Dictionary) ที่ Drain3 ขุดได้
    # -------------------------------------------------------------
    print("\n" + "=" * 90)
    print("📋 [ตารางที่ 1] พจนานุกรมแม่พิมพ์ (Drain3 Template Dictionary) ที่ได้จาก Training Set")
    print("=" * 90)
    
    template_summary = (
        df.groupby(["Event ID", "Mined Template (แม่พิมพ์ที่ขุดได้)"])
        .size()
        .reset_index(name="จำนวนครั้งที่พบ (Frequency)")
        .sort_values(by="Event ID")
    )
    pd.set_option("display.max_colwidth", None)
    pd.set_option("display.width", 1000)
    print(template_summary.to_string(index=False))

    # -------------------------------------------------------------
    # ตารางที่ 2: ตัวอย่างการจับคู่ทีละบรรทัด (Line-by-Line Mapping)
    # -------------------------------------------------------------
    print("\n" + "=" * 90)
    print("🔍 [ตารางที่ 2] ตัวอย่างบรรทัด Log จริงที่ใช้ Train และการแปลงเป็น Event ID (แสดงตัวอย่าง Run_101)")
    print("=" * 90)
    run101_df = df[df["Run ID"] == "Run_101"][["Line#", "Event ID", "Mined Template (แม่พิมพ์ที่ขุดได้)", "Raw Message (ข้อความสะอาด)"]]
    print(run101_df.to_string(index=False))

    print("\n" + "=" * 90)
    print(f"✅ รวมบรรทัดที่ใช้ Train ทั้งหมด: {len(df)} บรรทัด | ค้นพบ Template ทั้งหมด: {len(template_summary)} แบบ")
    print("=" * 90 + "\n")


if __name__ == "__main__":
    display_drain_training_data()
