#!/usr/bin/env python3
"""
scripts/download_data.py
========================
ระบบดาวน์โหลดชุดข้อมูลอัตโนมัติสำหรับ LogWatchdog
(Automated Dataset Downloader for Cloned Repositories)

ดาวน์โหลดชุดข้อมูลมาตรฐาน HDFS Pre-tokenized Benchmark จาก Hugging Face Datasets
ไปยังโฟลเดอร์ data/raw/hdfs_full_parquet/ เพื่อให้ผู้ใช้งานที่ clone โปรเจกต์สามารถ
ฝึกสอนโมเดลหรือรัน Benchmark ได้ทันทีโดยไม่ต้องเก็บไฟล์ขนาดใหญ่ไว้บน Git
"""

import os
import sys
import time
import argparse
import urllib.request

HF_BASE_URL = "https://huggingface.co/datasets/honicky/hdfs-logs-encoded-blocks/resolve/main/data"

DATASETS = {
    "hdfs_test": {
        "filename": "test-00000-of-00001.parquet",
        "url": f"{HF_BASE_URL}/test-00000-of-00001.parquet",
        "expected_min_bytes": 17_000_000,
        "description": "HDFS Test Split (57,507 Blocks - ข้อสอบวัดผล)",
        "target_dir": "data/raw/hdfs_full_parquet"
    },
    "hdfs_train": {
        "filename": "train-00000-of-00003.parquet",
        "url": f"{HF_BASE_URL}/train-00000-of-00003.parquet",
        "expected_min_bytes": 45_000_000,
        "description": "HDFS Train Split Part 1 (153,350 Blocks - ชุดฝึกสอน AI)",
        "target_dir": "data/raw/hdfs_full_parquet"
    },
    "hdfs_val": {
        "filename": "validation-00000-of-00001.parquet",
        "url": f"{HF_BASE_URL}/validation-00000-of-00001.parquet",
        "expected_min_bytes": 17_000_000,
        "description": "HDFS Validation Split (57,506 Blocks - ชุดตรวจสอบ)",
        "target_dir": "data/raw/hdfs_full_parquet"
    }
}


def download_file(url: str, dest_path: str, description: str):
    """ดาวน์โหลดไฟล์พร้อมแสดง Progress Bar และความเร็ว"""
    print(f"\n📥 กำลังดาวน์โหลด: {description}")
    print(f"   URL: {url}")
    print(f"   ปลายทาง: {dest_path}")

    temp_path = dest_path + ".tmp"
    headers = {"User-Agent": "LogWatchdog-DatasetDownloader/1.0"}
    req = urllib.request.Request(url, headers=headers)

    start_time = time.time()
    try:
        with urllib.request.urlopen(req) as resp, open(temp_path, "wb") as out_file:
            total_size = int(resp.headers.get("Content-Length", 0))
            downloaded = 0
            chunk_size = 1024 * 1024  # 1 MB

            while True:
                chunk = resp.read(chunk_size)
                if not chunk:
                    break
                out_file.write(chunk)
                downloaded += len(chunk)
                elapsed = time.time() - start_time
                speed = downloaded / (elapsed + 1e-6) / (1024 * 1024)  # MB/s

                if total_size > 0:
                    percent = downloaded / total_size * 100
                    bar_len = 30
                    filled = int(bar_len * downloaded / total_size)
                    bar = "█" * filled + "░" * (bar_len - filled)
                    sys.stdout.write(
                        f"\r   [{bar}] {percent:5.1f}% | {downloaded / 1024 / 1024:6.1f} / {total_size / 1024 / 1024:6.1f} MB | {speed:5.1f} MB/s"
                    )
                else:
                    sys.stdout.write(f"\r   ดาวน์โหลดแล้ว {downloaded / 1024 / 1024:6.1f} MB | {speed:5.1f} MB/s")
                sys.stdout.flush()

        print()  # new line
        os.replace(temp_path, dest_path)
        total_time = time.time() - start_time
        print(f"   ✅ ดาวน์โหลดสำเร็จ! ขนาด: {os.path.getsize(dest_path) / 1024 / 1024:.2f} MB (ใช้เวลา {total_time:.1f} วินาที)")
    except Exception as e:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        print(f"\n   ❌ เกิดข้อผิดพลาดในการดาวน์โหลด: {e}")
        raise


def main():
    parser = argparse.ArgumentParser(
        description="LogWatchdog Automated Dataset Downloader (Hugging Face Datasets)"
    )
    parser.add_argument(
        "--dataset",
        choices=["hdfs", "all"],
        default="hdfs",
        help="ชุดข้อมูลที่ต้องการดาวน์โหลด: 'hdfs' (Train + Test Parquet - ค่าเริ่มต้น) หรือ 'all' (รวม Validation)"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="บังคับดาวน์โหลดใหม่แม้ว่าไฟล์จะมีอยู่แล้ว"
    )
    args = parser.parse_args()

    print("=" * 80)
    print("🐕 LogWatchdog: Automated Dataset Downloader")
    print("   แหล่งที่มา: Hugging Face Dataset (honicky/hdfs-logs-encoded-blocks)")
    print("=" * 80)

    keys_to_download = ["hdfs_test", "hdfs_train"]
    if args.dataset == "all":
        keys_to_download.append("hdfs_val")

    for key in keys_to_download:
        info = DATASETS[key]
        dest_dir = info["target_dir"]
        os.makedirs(dest_dir, exist_ok=True)
        dest_file = os.path.join(dest_dir, info["filename"])

        if os.path.exists(dest_file) and not args.force:
            size = os.path.getsize(dest_file)
            if size >= info["expected_min_bytes"]:
                print(f"⚡ ข้าม: {info['filename']} มีอยู่แล้ว ({size / 1024 / 1024:.2f} MB)")
                continue

        download_file(info["url"], dest_file, info["description"])

    print("\n" + "=" * 80)
    print("🎉 การเตรียมชุดข้อมูลเสร็จสมบูรณ์! คุณสามารถรันคำสั่งต่อไปนี้ได้ทันที:")
    print("   1. ทดสอบประเมินผล Master AI Pipeline:")
    print("      👉 python main.py")
    print("   2. บังคับฝึกสอนโมเดลใหม่ทั้งหมดจากข้อมูลดิบ:")
    print("      👉 python main.py --retrain")
    print("   3. เปิด Web Demo Dashboard:")
    print("      👉 streamlit run app.py")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
