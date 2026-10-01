from abc import ABC, abstractmethod
from typing import Iterator, Dict, Any, Optional
import os


class LogIngestionError(Exception):
    """Exception พื้นฐานสำหรับข้อผิดพลาดในขั้นตอน Data Ingestion"""
    pass


class LogFileNotFoundError(LogIngestionError):
    """โยน Error เมื่อหาไฟล์ Log ไม่พบ"""
    pass


class EmptyLogError(LogIngestionError):
    """โยน Error เมื่อไฟล์ Log ว่างเปล่า"""
    pass


class BaseLogLoader(ABC):
    """
    🧱 [LEGO BRICK 1: Ingestion Interface]
    พิมพ์เขียวมาตรฐานสำหรับโมดูลอ่านข้อมูล Log ดิบ (Raw Logs)
    
    คุณสมบัติสำคัญ:
    - รองรับการอ่านแบบ Stream (Generator / yield) เพื่อไม่ให้เปลือง RAM
    - จัดการ Error เมื่อไฟล์ไม่ถูกต้อง
    - มีข้อต่อมาตรฐานที่ส่งต่อข้อความ String ให้ Block 2 (Parser) ใช้งานร่วมกันได้
    """

    def __init__(self, file_path: str):
        self.file_path = file_path
        self._validate_file_exists()

    def _validate_file_exists(self) -> None:
        """ตรวจสอบว่าไฟล์ปลายทางมีอยู่จริงหรือไม่"""
        if not os.path.exists(self.file_path):
            raise LogFileNotFoundError(f"ไม่พบไฟล์ที่ระบุ: {self.file_path}")

    @abstractmethod
    def load(self) -> Iterator[str]:
        """
        [Method หลักที่ต้องเขียน]
        อ่านข้อมูล Log และส่งออกเป็น Iterator/Generator ทีละบรรทัด (แนะนำให้ใช้ yield)
        
        :return: Generator ของ string แต่ละบรรทัด (ตัดช่องว่างหรือ newline ส่วนเกินแล้ว)
        """
        pass

    def count_lines(self) -> int:
        """นับจำนวนบรรทัดทั้งหมดใน Log (Utility Method)"""
        count = 0
        for _ in self.load():
            count += 1
        return count

    def get_metadata(self) -> Dict[str, Any]:
        """ดึงข้อมูลเบื้องต้นของไฟล์ Log เช่น ขนาดไฟล์ (Bytes)"""
        return {
            "file_path": self.file_path,
            "file_name": os.path.basename(self.file_path),
            "file_size_bytes": os.path.getsize(self.file_path) if os.path.exists(self.file_path) else 0,
        }
