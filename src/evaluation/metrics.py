from typing import Any, Dict, List, Union
import numpy as np


def calculate_metrics(
    y_true: Union[List[int], np.ndarray],
    y_pred: Union[List[int], np.ndarray]
) -> Dict[str, Any]:
    """
    คำนวณมาตรวัดความแม่นยำมาตรฐานสำหรับ Binary Classification (0 = Normal, 1 = Anomaly):
    - TP (True Positive): Anomaly จริง และ AI ทายว่า Anomaly
    - FP (False Positive): ของจริงปกติ แต่ AI ร้องเตือน Anomaly (False Alarm)
    - TN (True Negative): ของจริงปกติ และ AI ทายว่าปกติ
    - FN (False Negative): Anomaly จริง แต่ AI ปล่อยผ่าน (Missed Alarm)
    
    Metrics:
    - Accuracy: (TP + TN) / Total
    - Precision: TP / (TP + FP)
    - Recall (Sensitivity): TP / (TP + FN)
    - Specificity: TN / (TN + FP)
    - F1-Score: 2 * (Precision * Recall) / (Precision + Recall)
    """
    y_t = np.array(y_true, dtype=int)
    y_p = np.array(y_pred, dtype=int)

    if len(y_t) != len(y_p):
        raise ValueError(f"ความยาว y_true ({len(y_t)}) และ y_pred ({len(y_p)}) ต้องเท่ากัน")

    tp = int(np.sum((y_t == 1) & (y_p == 1)))
    fp = int(np.sum((y_t == 0) & (y_p == 1)))
    tn = int(np.sum((y_t == 0) & (y_p == 0)))
    fn = int(np.sum((y_t == 1) & (y_p == 0)))
    total = len(y_t)

    accuracy = (tp + tn) / total if total > 0 else 0.0
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    specificity = tn / (tn + fp) if (tn + fp) > 0 else 0.0
    f1_score = (
        (2 * precision * recall) / (precision + recall)
        if (precision + recall) > 0
        else 0.0
    )

    return {
        "total_samples": total,
        "tp": tp,
        "fp": fp,
        "tn": tn,
        "fn": fn,
        "accuracy": round(float(accuracy), 4),
        "precision": round(float(precision), 4),
        "recall": round(float(recall), 4),
        "specificity": round(float(specificity), 4),
        "f1_score": round(float(f1_score), 4),
    }


def format_classification_report(
    metrics: Dict[str, Any],
    model_name: str = "Anomaly Detection Model"
) -> str:
    """
    แปลงค่ามาตรวัดเป็นตาราง Markdown / Text ที่สวยงามสำหรับรายงานผล
    """
    report = f"""
============================================================
📊 รายงานการประเมินผลประสิทธิภาพ (Evaluation Report): {model_name}
============================================================
จำนวนตัวอย่างทดสอบทั้งหมด: {metrics['total_samples']} Sessions

[ 📈 มาตรวัดความแม่นยำหลัก (Core Metrics) ]
• Accuracy (ความถูกต้องโดยรวม):     {metrics['accuracy'] * 100:.2f}%
• Precision (ความแม่นยำในการเตือน):  {metrics['precision'] * 100:.2f}% (False Alarm = {metrics['fp']})
• Recall (อัตราการตรวจจับได้ครบ):     {metrics['recall'] * 100:.2f}% (หลุดรอด = {metrics['fn']})
• F1-Score (คะแนนเฉลี่ยฮาร์มอนิก):    {metrics['f1_score'] * 100:.2f}%
• Specificity (ความแม่นกับเคสปกติ):  {metrics['specificity'] * 100:.2f}%

[ 🧮 ตาราง Confusion Matrix ]
                +-------------------+-------------------+
                | ทายว่าปกติ (Pred 0)| ทายว่า Anomaly (1) |
+---------------+-------------------+-------------------+
| ของจริงปกติ (0) | TN = {metrics['tn']:<12} | FP = {metrics['fp']:<12} |
+---------------+-------------------+-------------------+
| ของจริงผิดปกติ(1)| FN = {metrics['fn']:<12} | TP = {metrics['tp']:<12} |
+---------------+-------------------+-------------------+
============================================================
"""
    return report.strip()
