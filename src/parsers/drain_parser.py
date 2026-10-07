from typing import Dict, Any, List, Optional
from drain3 import TemplateMiner
from drain3.template_miner_config import TemplateMinerConfig
from drain3.masking import MaskingInstruction
from src.parsers.base import BaseLogParser


class DrainParser(BaseLogParser):
    """
    🧱 [Lego Brick 2: Drain3 Parser Implementation]
    แปลง Log ดิบให้เป็น Template และ Event ID โดยใช้อัลกอริทึม Drain3
    พร้อมระบบ Regex Masking สำหรับแปลงตัวแปรผันแปร (Timestamp, IP, Paths, Versions, Numbers)
    """

    def __init__(
        self,
        masking_instructions: Optional[List[MaskingInstruction]] = None,
        sim_th: float = 0.7,
        depth: int = 5
    ):
        config = TemplateMinerConfig()
        config.profiling_enabled = False
        config.drain_sim_th = sim_th
        config.drain_depth = depth
        
        if masking_instructions is None:
            # ชุด Regex Masking มาตรฐานสำหรับ Production CI/CD & Distributed Systems (HDFS)
            config.masking_instructions = [
                MaskingInstruction(r"blk_-?\d+", "<BLOCK_ID>"),
                MaskingInstruction(r"(?:\d{1,3}\.){3}\d{1,3}(?::\d+)?", "<IP_PORT>"),
                MaskingInstruction(r"\d{4}-\d{2}-\d{2}T[0-9:.]+Z?", "<TIMESTAMP>"),
                MaskingInstruction(r"##\[\w+\]", "<MARKER>"),
                MaskingInstruction(r"(/[\w.-]+)+", "<PATH>"),
                MaskingInstruction(r"[a-zA-Z]:\\[\w.\\-]+", "<PATH>"),
                MaskingInstruction(r"\b[A-Za-z]{3}\s+\d{1,2}\s+\d{4}\b", "<DATE>"),
                MaskingInstruction(r"\b\d{1,2}:\d{2}:\d{2}\b", "<TIME>"),
                MaskingInstruction(r"\b\d+\.\d+(\.\d+)?\b", "<VERSION>"),
                MaskingInstruction(r"\b[0-9a-fA-F]{7,40}\b", "<HEX>"),
                MaskingInstruction(r"\b\d+\b", "<NUM>"),
            ]
        else:
            config.masking_instructions = masking_instructions

        self.miner = TemplateMiner(config=config)

    def parse_line(self, line: str, update_model: bool = True) -> Dict[str, Any]:
        """
        แปลง Log ดิบให้เป็น Template และ Event ID
        :param line: ข้อความ Log
        :param update_model: 
            - True (โหมด Train): ขุด Template ใหม่และอัปเดต Prefix Tree
            - False (โหมด Inference/Test): ค้นหา Template เดิมเท่านั้น (Read-Only) ป้องกัน Data Leakage
        """
        if update_model:
            result = self.miner.add_log_message(line)
            return {
                "raw_line": line,
                "template_id": result["cluster_id"],      # รหัส Event ID (เช่น 1, 2, 3)
                "template_str": result["template_mined"],  # ข้อความ template (เช่น "Receiving block <*>")
                "is_unseen": False,
            }
        else:
            match = self.miner.match(line)
            if match is not None:
                return {
                    "raw_line": line,
                    "template_id": match.cluster_id,
                    "template_str": match.get_template(),
                    "is_unseen": False,
                }
            else:
                return {
                    "raw_line": line,
                    "template_id": -1,  # รหัส Unseen / Out-of-Vocabulary
                    "template_str": "<UNKNOWN_UNSEEN_TEMPLATE>",
                    "is_unseen": True,
                }
