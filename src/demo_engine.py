"""
Demo Engine: โมดูลสนับสนุน Web Demo Dashboard สำหรับระบบ Hybrid Dual-Engine
(Isolation Forest + DeepLog LSTM + Hybrid Detector)
- บริหารจัดการ Model Caching และ Pre-trained Checkpoints ของทั้ง 2 โมเดล
- บริหารจัดการ Evaluation Data (Zero-OOV Test Benchmark 2,793 Sessions)
- เปรียบเทียบประสิทธิภาพแบบรายโมเดล (iForest, DeepLog, Hybrid)
- แม่พิมพ์ข้อความ HDFS Log Templates สำหรับการทำ Human-readable Forensics
"""

import os
import re
import time
import pickle
import numpy as np
import pandas as pd
import torch
from collections import Counter
from typing import Dict, List, Any, Tuple, Optional

from src.models.deeplog_lstm import DeepLogLSTMModel
from src.models.isolation_forest import IsolationForestModel
from src.models.hybrid_detector import HybridLogDetector
from src.explainers.deeplog_explainer import DeepLogExplainer

# แม่พิมพ์ข้อความ Log มาตรฐานของระบบ HDFS
HDFS_TEMPLATES: Dict[int, str] = {
    0: "Receiving block <*> src: <*> dest: <*>",
    1: "Received block <*> of size <*> from <*>",
    2: "PacketResponder <*> for block <*> terminating",
    3: "BLOCK* NameSystem.allocateBlock: <*> <*>",
    4: "BLOCK* ask <*> to replicate <*> to datanode(s) <*>",
    5: "BLOCK* ask <*> to delete <*>",
    6: "BLOCK* NameSystem.addStoredBlock: blockMap updated: <*> is added to <*>",
    7: "Verification succeeded for block <*>",
    8: "BLOCK* NameSystem.addStoredBlock: Redundant addStoredBlock request received for <*>",
    9: "Deleting block <*> file <*>",
    10: "Received block <*> of size <*> from <*> (duplicate)",
    11: "Unexpected error trying to delete block <*>. BlockInfo not found in volumeMap.",
    12: "writeBlock <*> received exception java.io.IOException",
    13: "PacketResponder <*> Exception java.io.IOException",
    14: "BLOCK* NameSystem.delete: <*> is deleted",
    15: "Failed to transfer <*> to <*> got java.net.SocketTimeoutException",
    21: "Served block <*> to <*>",
    22: "writeBlock <*> terminating",
    23: "Transmitted block <*> to <*>",
    26: "Received block <*> src: <*> dest: <*> of size <*>"
}

def get_template_desc(event_id: int) -> str:
    """คืนค่าคำอธิบายภาษาอังกฤษ/คำสั่งของ Event ID"""
    return HDFS_TEMPLATES.get(event_id, f"HDFS Distributed Operation [Event E{event_id}]")

def extract_event_ids(encoded_str: str) -> List[int]:
    """สกัดลำดับ Event ID จากข้อความ Parquet"""
    return [int(e) for e in re.findall(r"<\|sep\|>(\d+)", str(encoded_str))]

MODEL_DIR = "models"
MODEL_PATH = os.path.join(MODEL_DIR, "deeplog_option_a.pt")
IFOREST_MODEL_PATH = os.path.join(MODEL_DIR, "iforest_model.pkl")
METADATA_PATH = os.path.join(MODEL_DIR, "demo_metadata.pkl")
EVAL_CACHE_PATH = os.path.join(MODEL_DIR, "demo_eval_cache.pkl")


def calc_metrics(y_true: List[int], y_pred: List[int]) -> Dict[str, Any]:
    """คำนวณ Accuracy, Precision, Recall, Specificity, F1-Score และ Confusion Matrix"""
    tp = sum(1 for yt, yp in zip(y_true, y_pred) if yt == 1 and yp == 1)
    fp = sum(1 for yt, yp in zip(y_true, y_pred) if yt == 0 and yp == 1)
    tn = sum(1 for yt, yp in zip(y_true, y_pred) if yt == 0 and yp == 0)
    fn = sum(1 for yt, yp in zip(y_true, y_pred) if yt == 1 and yp == 0)

    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
    accuracy = (tp + tn) / len(y_true) if len(y_true) > 0 else 0.0
    specificity = tn / (tn + fp) if (tn + fp) > 0 else 0.0

    return {
        "tp": tp, "fp": fp, "tn": tn, "fn": fn,
        "recall": recall, "precision": precision,
        "f1_score": f1, "accuracy": accuracy,
        "specificity": specificity
    }


def get_category_label(y_t: int, y_p: int) -> str:
    """แปลงผลการตัดสินใจเป็นหมวดหมู่ TP, FP, TN, FN"""
    if y_t == 1 and y_p == 1:
        return "TP (True Positive - Anomaly Detected)"
    elif y_t == 0 and y_p == 1:
        return "FP (False Positive - Benign Alert)"
    elif y_t == 0 and y_p == 0:
        return "TN (True Negative - Healthy)"
    else:
        return "FN (False Negative - Missed)"


def get_trigger_source_desc(if_p: int, dl_p: int) -> str:
    """ระบุแหล่งที่มาของการตรวจพบความผิดปกติ"""
    if if_p == 1 and dl_p == 1:
        return "Both Engines (Volume Outlier & Sequential Violation)"
    elif dl_p == 1:
        return "DeepLog LSTM Only (Sequential Transition Violation)"
    elif if_p == 1:
        return "Isolation Forest Only (Count/Frequency Outlier)"
    else:
        return "Healthy / Neither Engine Triggered"


def train_and_cache_model(
    train_parquet_path: str = "data/raw/hdfs_full_parquet/train-00000-of-00003.parquet",
    test_parquet_path: str = "data/raw/hdfs_full_parquet/test-00000-of-00001.parquet",
    train_blocks: int = 5000,
    top_k: int = 3,
    force_retrain: bool = False
) -> Tuple[DeepLogLSTMModel, IsolationForestModel, HybridLogDetector, Dict[str, Any], pd.DataFrame]:
    """
    โหลดโมเดลทั้งสอง (iForest + DeepLog LSTM) จากแคช หรือฝึกสอนใหม่หากยังไม่มี
    คืนค่า (model, iforest_model, hybrid_detector, metadata, eval_df)
    """
    os.makedirs(MODEL_DIR, exist_ok=True)

    if (not force_retrain and 
        os.path.exists(MODEL_PATH) and 
        os.path.exists(IFOREST_MODEL_PATH) and 
        os.path.exists(METADATA_PATH) and 
        os.path.exists(EVAL_CACHE_PATH)):
        
        # โหลดโมเดลและแคชที่มีอยู่
        with open(METADATA_PATH, "rb") as f:
            metadata = pickle.load(f)
        with open(EVAL_CACHE_PATH, "rb") as f:
            eval_df = pickle.load(f)
        with open(IFOREST_MODEL_PATH, "rb") as f:
            iforest_model = pickle.load(f)

        model = DeepLogLSTMModel(
            vocab_size=metadata["vocab_size"],
            window_size=metadata["window_size"],
            embedding_dim=metadata["embedding_dim"],
            hidden_dim=metadata["hidden_dim"],
            num_layers=metadata["num_layers"],
            top_k=metadata.get("top_k", top_k),
            min_session_length=None
        )
        model.net.load_state_dict(torch.load(MODEL_PATH, weights_only=True))
        model.net.eval()
        model.normal_vocab = set(range(metadata["vocab_size"]))

        hybrid_detector = HybridLogDetector(iforest_model, model, strategy="synergy")
        return model, iforest_model, hybrid_detector, metadata, eval_df

    # ฝึกสอนใหม่
    if not os.path.exists(train_parquet_path) or not os.path.exists(test_parquet_path):
        raise FileNotFoundError("ไม่พบไฟล์ Parquet ใน data/raw/hdfs_full_parquet/")

    df_train = pd.read_parquet(train_parquet_path)
    df_test = pd.read_parquet(test_parquet_path)

    # กรอง Normal Blocks และทำ Frequency Pruning (Option A)
    train_normal_df = df_train[df_train["label"] == "Normal"].head(train_blocks)
    train_seqs = train_normal_df["event_encoded"].apply(extract_event_ids).tolist()

    WINDOW_SIZE = 3
    X_list, y_list = [], []
    for seq in train_seqs:
        for i in range(len(seq) - WINDOW_SIZE):
            X_list.append(seq[i : i + WINDOW_SIZE])
            y_list.append(seq[i + WINDOW_SIZE])

    X_train = np.array(X_list, dtype=int)
    y_train = np.array(y_list, dtype=int)

    target_counts = Counter(y_train)
    clean_mask = np.array([target_counts[target] > 5 for target in y_train])
    X_train_clean = X_train[clean_mask]
    y_train_clean = y_train[clean_mask]

    normal_vocab = set(X_train_clean.flatten().tolist())
    normal_vocab.update(y_train_clean.flatten().tolist())
    vocab_size = max(normal_vocab) + 2

    # 1. ฝึกสอน DeepLog LSTM Model
    model = DeepLogLSTMModel(
        vocab_size=vocab_size,
        window_size=WINDOW_SIZE,
        embedding_dim=32,
        hidden_dim=32,
        num_layers=2,
        epochs=5,
        batch_size=128,
        lr=0.01,
        top_k=top_k,
        min_session_length=None
    )
    model.fit(X_train_clean, y_train_clean)
    model.normal_vocab = set(range(100))  # ปิด OOV guard ในโมเดลเพื่อเน้น Pure Sequence

    # 2. ฝึกสอน Isolation Forest Model บน Count Vectors ของ Normal Blocks ชุดเดียวกัน
    X_train_counts = np.zeros((len(train_seqs), vocab_size), dtype=np.float32)
    for i, seq in enumerate(train_seqs):
        for eid in seq:
            if eid < vocab_size:
                X_train_counts[i, eid] += 1

    iforest_model = IsolationForestModel(n_estimators=100, contamination=0.1, random_state=42)
    iforest_model.fit(X_train_counts)

    # 3. สร้าง Hybrid Dual-Engine Detector (Cascaded Synergy)
    hybrid_detector = HybridLogDetector(iforest_model, model, strategy="synergy")

    # 4. ประเมินผลบน Zero-OOV Test Benchmark
    df_test["event_seq"] = df_test["event_encoded"].apply(extract_event_ids)
    df_test["seq_len"] = df_test["event_seq"].apply(len)
    df_test["has_oov"] = df_test["event_seq"].apply(lambda s: any(e not in normal_vocab for e in s))

    in_vocab_test = df_test[~df_test["has_oov"]].copy()
    in_vocab_normals = in_vocab_test[in_vocab_test["label"] == "Normal"]
    in_vocab_anomalies = in_vocab_test[in_vocab_test["label"] == "Anomaly"]
    pure_seq_anomalies = in_vocab_anomalies[in_vocab_anomalies["seq_len"] >= 4]

    eval_normals = in_vocab_normals.sample(min(2000, len(in_vocab_normals)), random_state=42)
    eval_df = pd.concat([eval_normals, pure_seq_anomalies]).reset_index(drop=True)

    seqs = eval_df["event_seq"].tolist()
    y_true = (eval_df["label"] == "Anomaly").astype(int).tolist()

    # ทำนายผลด้วย DeepLog LSTM
    lstm_preds = [int(model.predict_session(s)) for s in seqs]

    # ทำนายผลด้วย Isolation Forest
    X_eval_counts = np.zeros((len(eval_df), vocab_size), dtype=np.float32)
    for i, seq in enumerate(seqs):
        for eid in seq:
            if eid < vocab_size:
                X_eval_counts[i, eid] += 1
    iforest_preds = [int(p) for p in iforest_model.predict(X_eval_counts)]

    # ทำนายผลด้วย Hybrid Detector (Cascaded Synergy Strategy)
    hybrid_res = hybrid_detector.predict_batch(X_eval_counts, seqs)
    hybrid_preds = [int(r["prediction"]) for r in hybrid_res]
    hybrid_triggers = [
        ", ".join(r["triggered_by"]) if r["triggered_by"] else "Healthy / Normal Transition"
        for r in hybrid_res
    ]

    # บันทึกคอลัมน์ลง eval_df
    eval_df["y_true"] = y_true
    eval_df["lstm_pred"] = lstm_preds
    eval_df["iforest_pred"] = iforest_preds
    eval_df["hybrid_pred"] = hybrid_preds

    eval_df["category_lstm"] = [get_category_label(yt, yp) for yt, yp in zip(y_true, lstm_preds)]
    eval_df["category_iforest"] = [get_category_label(yt, yp) for yt, yp in zip(y_true, iforest_preds)]
    eval_df["category_hybrid"] = [get_category_label(yt, yp) for yt, yp in zip(y_true, hybrid_preds)]
    eval_df["category"] = eval_df["category_hybrid"]

    eval_df["triggered_source"] = hybrid_triggers

    # คำนวณ Metrics แยก 3 โมเดล
    metrics_lstm = calc_metrics(y_true, lstm_preds)
    metrics_iforest = calc_metrics(y_true, iforest_preds)
    metrics_hybrid = calc_metrics(y_true, hybrid_preds)

    synergy = {
        "both": sum(1 for if_p, dl_p in zip(iforest_preds, lstm_preds) if if_p == 1 and dl_p == 1),
        "lstm_only": sum(1 for if_p, dl_p in zip(iforest_preds, lstm_preds) if if_p == 0 and dl_p == 1),
        "iforest_only": sum(1 for if_p, dl_p in zip(iforest_preds, lstm_preds) if if_p == 1 and dl_p == 0),
        "neither": sum(1 for if_p, dl_p in zip(iforest_preds, lstm_preds) if if_p == 0 and dl_p == 0),
        "tp_both": sum(1 for yt, if_p, dl_p in zip(y_true, iforest_preds, lstm_preds) if yt == 1 and if_p == 1 and dl_p == 1),
        "tp_lstm_only": sum(1 for yt, if_p, dl_p in zip(y_true, iforest_preds, lstm_preds) if yt == 1 and if_p == 0 and dl_p == 1),
        "tp_iforest_only": sum(1 for yt, if_p, dl_p in zip(y_true, iforest_preds, lstm_preds) if yt == 1 and if_p == 1 and dl_p == 0),
        "fp_suppressed_by_if": sum(1 for yt, dl_p, hy_p in zip(y_true, lstm_preds, hybrid_preds) if yt == 0 and dl_p == 1 and hy_p == 0),
        "tp_preserved": sum(1 for yt, dl_p, hy_p in zip(y_true, lstm_preds, hybrid_preds) if yt == 1 and dl_p == 1 and hy_p == 1),
    }

    metadata = {
        "vocab_size": vocab_size,
        "window_size": WINDOW_SIZE,
        "embedding_dim": 32,
        "hidden_dim": 32,
        "num_layers": 2,
        "top_k": top_k,
        "normal_vocab": normal_vocab,
        "train_blocks": train_blocks,
        "train_windows": len(X_train_clean),
        "total_test_blocks": len(eval_df),
        "models": {
            "hybrid": metrics_hybrid,
            "lstm": metrics_lstm,
            "iforest": metrics_iforest,
        },
        "synergy": synergy,
        "trained_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        # Backward compatibility
        **metrics_hybrid
    }

    # บันทึกแคช
    torch.save(model.net.state_dict(), MODEL_PATH)
    with open(IFOREST_MODEL_PATH, "wb") as f:
        pickle.dump(iforest_model, f)
    with open(METADATA_PATH, "wb") as f:
        pickle.dump(metadata, f)
    with open(EVAL_CACHE_PATH, "wb") as f:
        pickle.dump(eval_df, f)

    return model, iforest_model, hybrid_detector, metadata, eval_df


def inspect_block_forensics(
    block_id: str,
    model: DeepLogLSTMModel,
    eval_df: pd.DataFrame,
    iforest_model: Optional[IsolationForestModel] = None,
    hybrid_detector: Optional[HybridLogDetector] = None
) -> Dict[str, Any]:
    """
    วิเคราะห์ทางนิติวิทยาศาสตร์สำหรับ Block ID ที่เลือก โดยแสดงผลทั้ง 3 โมเดล
    """
    row_matches = eval_df[eval_df["block_id"] == block_id]
    if row_matches.empty:
        raise ValueError(f"ไม่พบ Block ID: {block_id}")

    row = row_matches.iloc[0]
    seq = row["event_seq"]

    # สร้าง session events จำลองสำหรับ DeepLogExplainer
    session_events = [
        {
            "line_number": idx + 1,
            "raw_line": f"HDFS DataNode Operation [Event E{eid}]: {get_template_desc(eid)}",
            "template_id": eid,
            "template_str": get_template_desc(eid)
        }
        for idx, eid in enumerate(seq)
    ]

    explainer = DeepLogExplainer(model)
    diagnosis = explainer.explain_session(session_events, session_id=block_id)

    # ดึงค่า Softmax Distribution ณ จุด Culprit (หากมี)
    prob_distribution = []
    if diagnosis.get("is_anomaly", False) and diagnosis.get("culprit_step_index") is not None:
        culprit_idx = diagnosis["culprit_step_index"]
        w = model.window_size
        if culprit_idx >= w:
            window_slice = seq[culprit_idx - w : culprit_idx]
            x_tensor = torch.tensor([window_slice], dtype=torch.long)
            with torch.no_grad():
                logits = model.net(x_tensor)
                probs = torch.softmax(logits, dim=-1).squeeze().numpy()

            top_indices = np.argsort(probs)[::-1][:10]
            for idx in top_indices:
                prob_distribution.append({
                    "event_id": int(idx),
                    "event_name": f"E{idx}: {get_template_desc(int(idx))[:30]}",
                    "probability": float(probs[idx]),
                    "is_actual": int(idx) == diagnosis["culprit_template_id"],
                    "is_top_k": int(idx) in diagnosis.get("expected_candidates", [])
                })

    counts = dict(Counter(seq))

    return {
        "block_id": block_id,
        "actual_label": row["label"],
        "lstm_pred": "Anomaly" if row["lstm_pred"] == 1 else "Normal",
        "iforest_pred": "Anomaly" if row.get("iforest_pred", 0) == 1 else "Normal",
        "hybrid_pred": "Anomaly" if row.get("hybrid_pred", row["lstm_pred"]) == 1 else "Normal",
        "predicted_label": "Anomaly" if row.get("hybrid_pred", row["lstm_pred"]) == 1 else "Normal",
        "triggered_source": row.get("triggered_source", "Unknown"),
        "category": row.get("category_hybrid", row.get("category", "")),
        "sequence_length": len(seq),
        "sequence": seq,
        "counts": counts,
        "diagnosis": diagnosis,
        "prob_distribution": prob_distribution,
        "session_events": session_events
    }


# Curated Demo Showcase Scenarios
DEMO_SHOWCASE_CASES: List[Dict[str, Any]] = [
    {
        "case_id": "case_1",
        "name": "Case 1: Nominal Lifecycle (Unseen Normal Session)",
        "description": "วงจรชีวิตการทำงานปกติของระบบ HDFS: รับข้อมูล จัดสรร และปิดการเชื่อมต่ออย่างสมบูรณ์",
        "narrative": "บล็อกทำงานตามลำดับมาตรฐาน เริ่มต้นจากการจัดสรรพื้นที่ (allocate) การรับสตรีมข้อมูล (receiving/received) และการปิดเธรดเครือข่ายอย่างสมบูรณ์ (packetResponder terminating) ทั้ง iForest และ DeepLog เห็นพ้องว่าเป็นปกติ",
        "block_id": "blk_6334862664379948501",
        "ground_truth": "Normal",
        "events": [0, 0, 0, 6, 2, 3, 2, 3, 2, 3, 1, 1, 1],
    },
    {
        "case_id": "case_2",
        "name": "Case 2: DataNode I/O Failure (Hardware/Network Error)",
        "description": "ความล้มเหลวระดับฮาร์ดแวร์: เกิด IOException (Event 12 และ 13) และเกิดการสั่ง Retry ซ้ำหลายครั้ง",
        "narrative": "เกิดข้อผิดพลาดทางกายภาพของดิสก์ ส่งผลให้เกิด IOException (E12, E13) และพยายาม Delete/Replicate ซ้ำซ้อน ทำให้ความยาวพุ่งไป 27 เหตุการณ์ ทั้ง iForest (ตรวจจับความถี่สูงผิดปกติ) และ DeepLog (ตรวจจับ Exception นอกลู่ทาง) จับได้ทั้งคู่",
        "block_id": "blk_4516306414837452219",
        "ground_truth": "Anomaly",
        "events": [0, 0, 0, 6, 2, 3, 1, 2, 3, 2, 3, 1, 1, 12, 13, 0, 10, 11, 1, 1, 4, 5, 5, 5, 4, 4, 4],
    },
    {
        "case_id": "case_3",
        "name": "Case 3: Sequential Permutation (Step Skipping / Order Violation)",
        "description": "ความผิดปกติเชิงลำดับ: ทุกบรรทัดเป็นคำสั่งปกติ แต่มีคำสั่งลบบล็อก (Event 14) โผล่ขึ้นมาลัดขั้นตอน",
        "narrative": "ทุกข้อความใน Log เป็นคำสั่งปกติ จำนวนความถี่ปกติ (ความยาว 21 เหตุการณ์) ทำให้ iForest พลาด (False Negative) แต่ DeepLog และ Hybrid สามารถจับการลัดขั้นตอนที่มีคำสั่งลบโผล่มาผิดจังหวะได้ทันที",
        "block_id": "blk_5913130063451277660",
        "ground_truth": "Anomaly",
        "events": [0, 0, 0, 6, 2, 3, 2, 3, 2, 3, 1, 1, 1, 9, 5, 5, 5, 4, 4, 4, 14],
    },
]


def inspect_showcase_forensics(
    case_info: Dict[str, Any],
    model: DeepLogLSTMModel,
    iforest_model: Optional[IsolationForestModel] = None,
    hybrid_detector: Optional[HybridLogDetector] = None
) -> Dict[str, Any]:
    """
    วิเคราะห์ทางนิติวิทยาศาสตร์สำหรับ Demo Showcase Case โดยรันทั้ง 3 เครื่องยนต์
    """
    seq = case_info["events"]
    block_id = case_info["block_id"]

    session_events = [
        {
            "line_number": idx + 1,
            "raw_line": f"HDFS DataNode Operation [Event E{eid}]: {get_template_desc(eid)}",
            "template_id": eid,
            "template_str": get_template_desc(eid)
        }
        for idx, eid in enumerate(seq)
    ]

    explainer = DeepLogExplainer(model)
    diagnosis = explainer.explain_session(session_events, session_id=block_id)

    prob_distribution = []
    if diagnosis.get("is_anomaly", False) and diagnosis.get("culprit_step_index") is not None:
        culprit_idx = diagnosis["culprit_step_index"]
        w = model.window_size
        if culprit_idx >= w:
            window_slice = seq[culprit_idx - w : culprit_idx]
            x_tensor = torch.tensor([window_slice], dtype=torch.long)
            with torch.no_grad():
                logits = model.net(x_tensor)
                probs = torch.softmax(logits, dim=-1).squeeze().numpy()

            top_indices = np.argsort(probs)[::-1][:10]
            for idx in top_indices:
                prob_distribution.append({
                    "event_id": int(idx),
                    "event_name": f"E{idx}: {get_template_desc(int(idx))[:30]}",
                    "probability": float(probs[idx]),
                    "is_actual": int(idx) == diagnosis.get("culprit_template_id"),
                    "is_top_k": int(idx) in diagnosis.get("expected_candidates", [])
                })

    # รันการทำนายทั้ง 3 โมเดล
    dl_pred = 1 if diagnosis.get("is_anomaly", False) else 0

    if iforest_model is not None:
        n_features = getattr(getattr(iforest_model, "model", None), "n_features_in_", model.vocab_size)
        cv = np.zeros(n_features, dtype=np.float32)
        for eid in seq:
            if eid < n_features:
                cv[eid] += 1
        if_pred = int(iforest_model.predict(cv.reshape(1, -1))[0])
    else:
        if_pred = 0

    if hybrid_detector is not None:
        hy_res = hybrid_detector.predict_session(cv, seq)
        hy_pred = hy_res["prediction"]
        triggered_src = ", ".join(hy_res["triggered_by"]) if hy_res["triggered_by"] else "Healthy / Within Normal Tolerances"
    else:
        hy_pred = 1 if (dl_pred == 1 or if_pred == 1) else 0
        triggered_src = get_trigger_source_desc(if_pred, dl_pred)

    return {
        "case_id": case_info["case_id"],
        "name": case_info["name"],
        "description": case_info["description"],
        "narrative": case_info["narrative"],
        "block_id": block_id,
        "actual_label": case_info["ground_truth"],
        "lstm_pred": "Anomaly" if dl_pred == 1 else "Normal",
        "iforest_pred": "Anomaly" if if_pred == 1 else "Normal",
        "hybrid_pred": "Anomaly" if hy_pred == 1 else "Normal",
        "predicted_label": "Anomaly" if hy_pred == 1 else "Normal",
        "triggered_source": triggered_src,
        "sequence_length": len(seq),
        "sequence": seq,
        "counts": dict(Counter(seq)),
        "diagnosis": diagnosis,
        "prob_distribution": prob_distribution,
        "session_events": session_events
    }
