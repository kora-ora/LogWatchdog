from typing import Any, Dict, List, Optional, Union
import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset
from src.models.base import BaseAnomalyModel


class DeepLogNetwork(nn.Module):
    """
    โครงข่ายประสาทเทียม PyTorch สำหรับ DeepLog:
    Embedding -> LSTM Layers -> Linear (Output Logits)
    """

    def __init__(
        self,
        vocab_size: int,
        embedding_dim: int = 64,
        hidden_dim: int = 64,
        num_layers: int = 2
    ):
        super().__init__()
        self.embedding = nn.Embedding(num_embeddings=vocab_size, embedding_dim=embedding_dim) #ทำการ dense embedding เพื่อสร้าง Xt ขึ้นมา
        self.lstm = nn.LSTM(input_size=embedding_dim, hidden_size=hidden_dim, num_layers=num_layers, batch_first=True) #ตั้งค่า foget gate , input gate , output gate ภายในบรรทัดเดียว
        self.fc = nn.Linear(hidden_dim, vocab_size)# fully connect layer ใช้ในการแปลงกลับค่าจาก hiden layer(short term memory) จาก 64 มิติกลับเป็น event id ที่น่าจะเกิดขึ้นถัดไป

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        embedded = self.embedding(x)#แปลงข้อมูล tensor ขนาด batch size x window เป็น vector 64 มิติ   
        lstm_out, _ = self.lstm(embedded) #lstm_out คือ array ที่รวม short term memory ของแต่ละ event id ใน window size , _ คือ Long mem , Short mem ของ LSTM layer สุดท้าย
        last_hidden = lstm_out[:, -1, :]# เลือกหยิบเฉพาะ h3 (Short-term ล่าสุดหลังเห็นครบ 3 เหตุการณ์)
        logits = self.fc(last_hidden)#ส่งเข้า fully connect layer เพื่อแปลงกลับเป็น event id ที่น่าจะเกิดขึ้นถัดไป
        return logits

class DeepLogLSTMModel(BaseAnomalyModel):
    """
    🧱 [Lego Brick 4: DeepLog Sequential Model Implementation]
    โมเดลตรวจจับลำดับเวลาผิดปกติ (Sequential Anomaly) ด้วยสถาปัตยกรรม DeepLog (LSTM)
    """

    def __init__(
        self,
        vocab_size: int = 20,
        window_size: int = 3,
        embedding_dim: int = 64,
        hidden_dim: int = 64,
        num_layers: int = 2,
        top_k: int = 2,
        lr: float = 0.01,
        epochs: int = 30,
        batch_size: int = 16,
        min_session_length: Optional[int] = None,
        device: str = "cpu"
    ):
        self.vocab_size = vocab_size
        self.window_size = window_size
        self.top_k = top_k
        self.lr = lr
        self.epochs = epochs
        self.batch_size = batch_size
        self.min_session_length = min_session_length
        self.device = torch.device(device)

        # สร้างสมองกล DeepLogNetwork
        self.net = DeepLogNetwork(
            vocab_size=self.vocab_size,
            embedding_dim=embedding_dim,
            hidden_dim=hidden_dim,
            num_layers=num_layers
        ).to(self.device)

        self.criterion = nn.CrossEntropyLoss()
        self.optimizer = torch.optim.Adam(self.net.parameters(), lr=self.lr)
        self.normal_vocab = set()

    def fit(self, X: Any, y: Any = None) -> "DeepLogLSTMModel":
        if y is None or len(X) == 0:
            return self
    
        # 1. บันทึก event ID ทั้งหมดที่มีใน log เพื่อใช้ detect anomaly ตั้งแต่แรก เช่น ข้อมูลที่ส่งเข้ามา train มี evenid ที่ไม่เคยมีมาก่อน สามารถตีความเป็น anomaly ได้เลย
        self.normal_vocab = set(np.array(X).flatten().tolist())
        self.normal_vocab.update(np.array(y).flatten().tolist()) 

        # 2. เตรียม DataLoader
        #เตรียมข้อมูลให้ cpu ไปเทรนโดยให้ ข้อมูลที่ใช้เทรน 1 รอบ ตาม batch size = 16 แถว
        X_tensor = torch.tensor(X, dtype=torch.long)#
        y_tensor = torch.tensor(y, dtype=torch.long)
        dataset = TensorDataset(X_tensor, y_tensor)
        loader = DataLoader(dataset, batch_size=self.batch_size, shuffle=True)

        # 3. ลูปเทรน 
        #• Batch Size = 16: คือการทำโจทย์ทีละ 16 ข้อ แล้วตรวจคำตอบพร้อมปรับปรุงตัวเอง 1 ครั้ง
        #• 1 Epoch: คือการทำโจทย์ครบทั้ง 100 ข้อ จนจบเล่มบริบูรณ์ = 1 รอบ (1 Epoch)
        #• Epochs = 30: หมายถึง เราสั่งให้ AI นำหนังสือเล่มเดิมนี้มา ทบทวนซ้ำ 30 รอบ!

        self.net.train()
        for epoch in range(self.epochs):
            for batch_x, batch_y in loader:
                batch_x = batch_x.to(self.device)
                batch_y = batch_y.to(self.device)

                self.optimizer.zero_grad()
                logits = self.net(batch_x)
                loss = self.criterion(logits, batch_y)
                loss.backward()
                self.optimizer.step()

        return self


        
        

    def predict_session(self, sequence: List[int]) -> int:
        if not sequence:
                return 0

        # 1. เช็ก Event แปลกปลอม (Deterministic OOV Guard)
        if any(e not in self.normal_vocab for e in sequence):
            return 1

        # 2. เช็กเซสชันแท้งกลางคัน/สั้นกว่าเกณฑ์ปกติ (Incomplete Session Guard)
        if self.min_session_length is not None and len(sequence) < self.min_session_length:
            return 1

        # 3. จัดการความยาวสั้น ทำการ padding 
        seq = sequence
        if len(seq) <= self.window_size:
            seq = [0] * (self.window_size - len(seq) + 1) + seq

        # 3. โหมดทำนาย & 4. เลื่อนหน้าต่างเช็ก Top-K
        self.net.eval()
        with torch.no_grad():
            for i in range(len(seq) - self.window_size):
                window = seq[i : i + self.window_size]
                actual_next = seq[i + self.window_size]

                window_tensor = torch.tensor([window], dtype=torch.long).to(self.device)
                logits = self.net(window_tensor)

                topk_candidates = torch.topk(logits, k=min(self.top_k, self.vocab_size), dim=-1).indices[0].tolist()

                if actual_next not in topk_candidates:
                    return 1

        return 0

    def inspect_session(self, sequence: List[int]) -> Dict[str, Any]:
        """
        ตรวจสอบสถิติเชิงลึกของลำดับเหตุการณ์ใน Session:
        - is_anomaly: 1 หากพบ violation ใดๆ, 0 หากปกติ
        - violation_count: จำนวนจุดที่หลุดจาก Top-K
        - min_probability: ค่าความน่าจะเป็นต่ำสุดของเหตุการณ์ที่เกิดขึ้นจริง
        - has_oov: พบ Token แปลกปลอมหรือไม่
        """
        if not sequence:
            return {"is_anomaly": 0, "violation_count": 0, "min_probability": 1.0, "has_oov": False}

        has_oov = any(e not in self.normal_vocab for e in sequence)
        if has_oov:
            return {"is_anomaly": 1, "violation_count": 1, "min_probability": 0.0, "has_oov": True}

        seq = sequence
        if len(seq) <= self.window_size:
            seq = [0] * (self.window_size - len(seq) + 1) + seq

        self.net.eval()
        violation_count = 0
        min_p = 1.0
        with torch.no_grad():
            for i in range(len(seq) - self.window_size):
                window = seq[i : i + self.window_size]
                actual_next = seq[i + self.window_size]

                window_tensor = torch.tensor([window], dtype=torch.long).to(self.device)
                logits = self.net(window_tensor)
                probs = torch.softmax(logits, dim=-1).squeeze(0).cpu().numpy()
                topk_candidates = np.argsort(probs)[::-1][:min(self.top_k, self.vocab_size)].tolist()

                if actual_next not in topk_candidates:
                    violation_count += 1
                if actual_next < len(probs):
                    act_p = float(probs[actual_next])
                    if act_p < min_p:
                        min_p = act_p

        return {
            "is_anomaly": 1 if violation_count > 0 else 0,
            "violation_count": violation_count,
            "min_probability": min_p,
            "has_oov": False
        }



    def predict(self, session_sequences: Union[Dict[str, List[int]], Any]) -> np.ndarray:
        """Helper ทำนายผลทีละ session"""
        if isinstance(session_sequences, dict):
            predictions = [self.predict_session(seq) for seq in session_sequences.values()]
            return np.array(predictions, dtype=int)
        
        self.net.eval()
        with torch.no_grad():
            X_tensor = torch.tensor(session_sequences, dtype=torch.long).to(self.device)
            logits = self.net(X_tensor)
            topk = torch.topk(logits, k=min(self.top_k, self.vocab_size), dim=-1).indices.cpu().numpy()
            return topk
