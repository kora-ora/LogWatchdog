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

    def __init__(self, vocab_size: int, embedding_dim: int = 64, hidden_dim: int = 64, num_layers: int = 2):
        super().__init__()
        self.embedding = nn.Embedding(num_embeddings=vocab_size, embedding_dim=embedding_dim)
        self.lstm = nn.LSTM(
            input_size=embedding_dim,
            hidden_size=hidden_dim,
            num_layers=num_layers,
            batch_first=True
        )
        self.fc = nn.Linear(hidden_dim, vocab_size)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x shape: (batch_size, window_size)
        embedded = self.embedding(x)  # (batch_size, window_size, embedding_dim)
        lstm_out, _ = self.lstm(embedded)  # (batch_size, window_size, hidden_dim)
        # ดึง Hidden state ตัวสุดท้ายของ window มาทำนายคำตอบ
        last_hidden = lstm_out[:, -1, :]  # (batch_size, hidden_dim)
        logits = self.fc(last_hidden)  # (batch_size, vocab_size)
        return logits


class DeepLogLSTMModel(BaseAnomalyModel):
    """
    🧱 [Lego Brick 4: DeepLog Sequential Model Implementation]
    โมเดลตรวจจับลำดับเวลาผิดปกติ (Sequential Anomaly) ด้วยสถาปัตยกรรม DeepLog (LSTM)
    
    หลักการทำงาน:
    1. ตอนเทรน (fit): ให้ LSTM เรียนรู้การเดา Event ถัดไป (Next-Event Prediction) จาก Log ปกติ
    2. ตอนทำนาย (predict): ตรวจสอบว่า Event ที่เกิดขึ้นจริง อยู่ในกลุ่มตัวเก็ง Top-K หรือไม่
       - ถ้าไม่อยู่ใน Top-K -> ฟันธงทันทีว่าลำดับขั้นตอนผิดเพี้ยน (Sequential Anomaly)!
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
        device: str = "cpu"
    ):
        self.vocab_size = vocab_size
        self.window_size = window_size
        self.top_k = top_k
        self.lr = lr
        self.epochs = epochs
        self.batch_size = batch_size
        self.device = torch.device(device)

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
        """
        ฝึกสอนโมเดล LSTM ด้วยชุดคู่ข้อมูล (X, y) จาก SequenceExtractor
        :param X: numpy array หรือ torch.Tensor ของหน้าต่างในอดีต (N, window_size)
        :param y: numpy array หรือ torch.Tensor ของ Event เป้าหมายถัดไป (N,)
        """
        if y is None or len(X) == 0:
            return self

        # บันทึกรายชื่อ Event ID ทั้งหมดที่พบใน Normal Data
        self.normal_vocab = set(np.array(X).flatten().tolist())
        self.normal_vocab.update(np.array(y).flatten().tolist())

        X_tensor = torch.tensor(X, dtype=torch.long)
        y_tensor = torch.tensor(y, dtype=torch.long)

        dataset = TensorDataset(X_tensor, y_tensor)
        loader = DataLoader(dataset, batch_size=self.batch_size, shuffle=True)

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
        """
        ตรวจจับว่า Sequence ใน 1 Session นี้มีความผิดปกติหรือไม่
        :param sequence: ลำดับ Event ID เช่น [1, 2, 3, 3, 4, 5]
        :return: 0 (Normal) หรือ 1 (Anomaly)
        """
        if not sequence:
            return 0

        # กฎข้อที่ 1 ของ DeepLog: ถ้ามี Event ที่ไม่เคยพบใน Normal Data เลย ถือเป็น Anomaly ทันที!
        if any(e not in self.normal_vocab for e in sequence):
            return 1

        # เตรียม sequence สำหรับ Sliding Window (ถ้าสั้นกว่า window_size ให้เติม padding 0)
        seq = sequence
        if len(seq) <= self.window_size:
            seq = [0] * (self.window_size - len(seq) + 1) + seq

        self.net.eval()
        with torch.no_grad():
            for i in range(len(seq) - self.window_size):
                window = seq[i : i + self.window_size]
                actual_next = seq[i + self.window_size]

                window_tensor = torch.tensor([window], dtype=torch.long).to(self.device)
                logits = self.net(window_tensor)
                
                # หา Top-K ตัวเก็งที่โมเดลเดาว่ามีความน่าจะเป็นสูงสุด
                topk_candidates = torch.topk(logits, k=min(self.top_k, self.vocab_size), dim=-1).indices[0].tolist()

                # กฎข้อที่ 2 ของ DeepLog: ถ้า Event ถัดไปที่เกิดจริง ไม่อยู่ใน Top-K -> Anomaly!
                if actual_next not in topk_candidates:
                    return 1  # Anomaly detected!

        return 0  # Normal

    def predict(self, session_sequences: Union[Dict[str, List[int]], Any]) -> np.ndarray:
        """
        ทำนายผลสำหรับทุก Session
        :param session_sequences: Dict ของ {session_id: [event_ids]}
        :return: numpy array ของ 0 (Normal) และ 1 (Anomaly)
        """
        if isinstance(session_sequences, dict):
            predictions = [self.predict_session(seq) for seq in session_sequences.values()]
            return np.array(predictions, dtype=int)
        
        # กรณีส่งมาเป็น Array/Matrix คู่ X
        self.net.eval()
        with torch.no_grad():
            X_tensor = torch.tensor(session_sequences, dtype=torch.long).to(self.device)
            logits = self.net(X_tensor)
            topk = torch.topk(logits, k=min(self.top_k, self.vocab_size), dim=-1).indices.cpu().numpy()
            return topk
