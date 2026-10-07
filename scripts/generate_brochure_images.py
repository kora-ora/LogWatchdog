#!/usr/bin/env python3
"""
สคริปต์สร้างภาพประกอบและไดอะแกรมความละเอียดสูงสำหรับแผ่นพับ LogWatchdog A4 Tri-Fold
ใช้ฟอนต์ TH SarabunPSK เพื่อความคมชัดและความสอดคล้องกับเอกสารวิชาการ
"""

import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import matplotlib.font_manager as fm

ASSETS_DIR = "/home/kora/Project/AI Project/assets/brochure"
os.makedirs(ASSETS_DIR, exist_ok=True)

# ฟอนต์ TH SarabunPSK
FONT_REGULAR = "/home/kora/.local/share/fonts/t/THSarabun.ttf"
FONT_BOLD = "/home/kora/.local/share/fonts/t/THSarabun_Bold.ttf"

prop_reg = fm.FontProperties(fname=FONT_REGULAR)
prop_bold = fm.FontProperties(fname=FONT_BOLD)

def create_cover_badge():
    """0. ภาพโลโก้/กราฟิกปกหน้า (Cover Badge)"""
    fig, ax = plt.subplots(figsize=(6.6, 2.8), dpi=300)
    ax.set_facecolor('#0F172A')
    fig.patch.set_facecolor('#0F172A')
    ax.axis('off')

    # กรอบนอกแบบโมเดิร์น
    bg = patches.FancyBboxPatch((0.02, 0.05), 0.96, 0.90,
                                boxstyle="round,pad=0.02,rounding_size=0.04",
                                facecolor="#1E293B", edgecolor="#38BDF8", linewidth=1.8)
    ax.add_patch(bg)

    # วงแหวนเรดาร์จำลอง (Detection Radar)
    circle1 = plt.Circle((0.50, 0.52), 0.35, color="#0EA5E9", fill=False, linewidth=1.2, alpha=0.3)
    circle2 = plt.Circle((0.50, 0.52), 0.22, color="#38BDF8", fill=False, linewidth=1.2, alpha=0.5)
    circle3 = plt.Circle((0.50, 0.52), 0.08, color="#38BDF8", fill=True, alpha=0.8)
    ax.add_patch(circle1)
    ax.add_patch(circle2)
    ax.add_patch(circle3)

    # เส้นแกนสแกน
    ax.plot([0.15, 0.85], [0.52, 0.52], color="#38BDF8", linewidth=0.8, alpha=0.4, linestyle="--")
    ax.plot([0.50, 0.50], [0.17, 0.87], color="#38BDF8", linewidth=0.8, alpha=0.4, linestyle="--")

    # จุดตรวจจับ Anomaly (Red Pinpoint)
    anomaly_pt = plt.Circle((0.62, 0.65), 0.035, color="#EF4444", fill=True, alpha=0.95)
    ax.add_patch(anomaly_pt)
    ax.plot([0.50, 0.62], [0.52, 0.65], color="#EF4444", linewidth=1.5, alpha=0.8)
    ax.text(0.68, 0.67, "Culprit Line Detected!", ha='left', va='center',
            fontproperties=prop_bold, fontsize=10, color="#FCA5A5")

    # ข้อความบนและล่าง
    ax.text(0.50, 0.84, "LOGWATCHDOG DUAL-ENGINE RADAR", ha='center', va='center',
            fontproperties=prop_bold, fontsize=12.5, color="#F8FAFC")
    ax.text(0.50, 0.16, "Volumetric Count (iForest) + Sequential Syntax (DeepLog LSTM)", ha='center', va='center',
            fontproperties=prop_reg, fontsize=9.5, color="#94A3B8")

    plt.tight_layout()
    out_path = os.path.join(ASSETS_DIR, "cover_badge.png")
    plt.savefig(out_path, dpi=300, bbox_inches='tight', pad_inches=0.02)
    plt.close()
    print("Created:", out_path)


def create_kpi_card():
    """1. ภาพแสดงตัวเลขเด่น 3 ตัว (KPI Cards) สำหรับแผงพับเข้า (Flap)"""
    fig, ax = plt.subplots(figsize=(6.6, 2.2), dpi=300)
    ax.set_facecolor('#F8FAFC')
    fig.patch.set_facecolor('#F8FAFC')
    ax.axis('off')

    # กล่องพื้นหลังหลัก
    bg = patches.FancyBboxPatch((0.02, 0.05), 0.96, 0.90,
                                boxstyle="round,pad=0.02,rounding_size=0.03",
                                facecolor="#FFFFFF", edgecolor="#CBD5E1", linewidth=1.5)
    ax.add_patch(bg)

    # แบ่ง 3 คอลัมน์
    cols = [
        {"title": "RECALL", "val": "100.00%", "color": "#22543D", "sub": "ตรวจจับได้ครบทุกเคส\nไม่หลุดรอดแม้แต่เคสเดียว", "x": 0.18},
        {"title": "F1-SCORE", "val": "84.72%", "color": "#1A365D", "sub": "ประสิทธิภาพรวมสูงสุด\nเหนือกว่าโมเดลเดี่ยวทุกตัว", "x": 0.50},
        {"title": "FALSE ALARMS", "val": "-46.9%", "color": "#2B6CB0", "sub": "ตัดเสียงรบกวนพร่ำเพรื่อ\nจาก 539 เหลือ 286 ครั้ง", "x": 0.82}
    ]

    for col in cols:
        # Title
        ax.text(col["x"], 0.78, col["title"], ha='center', va='center',
                fontproperties=prop_bold, fontsize=11, color="#718096")
        # Big Value
        ax.text(col["x"], 0.52, col["val"], ha='center', va='center',
                fontproperties=prop_bold, fontsize=24, color=col["color"])
        # Subtitle
        ax.text(col["x"], 0.25, col["sub"], ha='center', va='center',
                fontproperties=prop_reg, fontsize=9.5, color="#4A5568", linespacing=1.1)

    # เส้นคั่นแนวตั้ง
    ax.plot([0.34, 0.34], [0.18, 0.82], color="#E2E8F0", linewidth=1.2)
    ax.plot([0.66, 0.66], [0.18, 0.82], color="#E2E8F0", linewidth=1.2)

    # หมายเหตุด้านล่าง
    ax.text(0.50, 0.09, "*ประเมินบนชุดทดสอบ In-Vocabulary (Zero-OOV) 2,793 เซสชัน (HDFS Benchmark)",
            ha='center', va='center', fontproperties=prop_reg, fontsize=8.5, color="#718096")

    plt.tight_layout()
    out_path = os.path.join(ASSETS_DIR, "kpi_metrics_card.png")
    plt.savefig(out_path, dpi=300, bbox_inches='tight', pad_inches=0.02)
    plt.close()
    print("Created:", out_path)


def create_problem_comparison():
    """2. ภาพเปรียบเทียบปัญหา: Regex Blindness vs LogWatchdog Dual-Engine"""
    fig, ax = plt.subplots(figsize=(6.6, 2.5), dpi=300)
    ax.set_facecolor('#FFFFFF')
    fig.patch.set_facecolor('#FFFFFF')
    ax.axis('off')

    # ฝั่งซ้าย: ข้อจำกัดแบบเดิม (Regex / Keyword Match)
    box_left = patches.FancyBboxPatch((0.02, 0.08), 0.46, 0.84,
                                      boxstyle="round,pad=0.02,rounding_size=0.03",
                                      facecolor="#FFF5F5", edgecolor="#FEB2B2", linewidth=1.5)
    ax.add_patch(box_left)
    ax.text(0.25, 0.82, "วิเคราะห์แบบเดิม (Regex / Keywords)", ha='center', va='center',
            fontproperties=prop_bold, fontsize=12, color="#9B2C2C")
    
    left_lines = [
        "1. Ingestion: Starting build process",
        "2. Step 1: Download repository",
        "4. Step 3: Deploy to production (ข้าม Step 2!)",
        "-------------------------------------------",
        "[X] ไม่มีคำว่า 'Error' หรือ 'Failed' ปรากฏ",
        "[X] Regex ตรวจไม่พบ (False Negative หลุดรอด)",
        "[X] มนุษย์ตรวจสอบไม่ไหวท่ามกลาง Log หลายล้านบรรทัด"
    ]
    y_pos = 0.67
    for line in left_lines:
        font_c = "#9B2C2C" if line.startswith("[X]") else "#4A5568"
        p_weight = prop_bold if line.startswith("[X]") else prop_reg
        ax.text(0.05, y_pos, line, ha='left', va='center',
                fontproperties=p_weight, fontsize=9.0, color=font_c)
        y_pos -= 0.085

    # ฝั่งขวา: พลังของ LogWatchdog Dual-Engine
    box_right = patches.FancyBboxPatch((0.52, 0.08), 0.46, 0.84,
                                       boxstyle="round,pad=0.02,rounding_size=0.03",
                                       facecolor="#F0FFF4", edgecolor="#9AE6B4", linewidth=1.5)
    ax.add_patch(box_right)
    ax.text(0.75, 0.82, "ระบบ LogWatchdog (Hybrid Dual-Engine)", ha='center', va='center',
            fontproperties=prop_bold, fontsize=12, color="#22543D")

    right_lines = [
        "Engine 1 (iForest): ตรวจจับความถี่และปริมาณ (Count)",
        "Engine 2 (DeepLog): ตรวจสอบไวยากรณ์ลำดับขั้นตอน",
        "Cascaded Synergy: ผสานพลังตัดเสียงรบกวน 46.9%",
        "-------------------------------------------",
        "[V] ตรวจจับลำดับที่ผิดปกติได้ทันที (Sequential Anomaly)",
        "[V] ชี้เป้าบรรทัดที่เกิดเหตุ (Culprit Line) แม่นยำ",
        "[V] สกัดบริบท 5 บรรทัด พร้อมคำนวณ Top-K Candidates"
    ]
    y_pos = 0.67
    for line in right_lines:
        font_c = "#22543D" if line.startswith("[V]") else "#2D3748"
        p_weight = prop_bold if line.startswith("[V]") else prop_reg
        ax.text(0.55, y_pos, line, ha='left', va='center',
                fontproperties=p_weight, fontsize=9.0, color=font_c)
        y_pos -= 0.085

    plt.tight_layout()
    out_path = os.path.join(ASSETS_DIR, "problem_comparison.png")
    plt.savefig(out_path, dpi=300, bbox_inches='tight', pad_inches=0.02)
    plt.close()
    print("Created:", out_path)


def create_pipeline_diagram():
    """3. ไดอะแกรมสถาปัตยกรรม 5 บล็อก (Pipeline) สำหรับแผง 5 (วิธีแก้)"""
    fig, ax = plt.subplots(figsize=(6.6, 2.7), dpi=300)
    ax.set_facecolor('#FFFFFF')
    fig.patch.set_facecolor('#FFFFFF')
    ax.axis('off')

    # Main Frame
    bg = patches.FancyBboxPatch((0.01, 0.02), 0.98, 0.96,
                                boxstyle="round,pad=0.02,rounding_size=0.03",
                                facecolor="#F8FAFC", edgecolor="#CBD5E1", linewidth=1.2)
    ax.add_patch(bg)

    # Header
    ax.text(0.50, 0.90, "5-Brick Modular Architecture & Cascaded Synergy",
            ha='center', va='center', fontproperties=prop_bold, fontsize=11.5, color="#1A365D")

    # Helper function for drawing blocks
    def draw_box(x, y, w, h, title, sub, bg_c="#FFFFFF", border_c="#CBD5E1", text_c="#1A365D"):
        patch = patches.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.015,rounding_size=0.02",
                                      facecolor=bg_c, edgecolor=border_c, linewidth=1.2)
        ax.add_patch(patch)
        ax.text(x + w/2, y + h*0.65, title, ha='center', va='center',
                fontproperties=prop_bold, fontsize=9.5, color=text_c)
        ax.text(x + w/2, y + h*0.30, sub, ha='center', va='center',
                fontproperties=prop_reg, fontsize=8.0, color="#4A5568")

    # Block 1: Ingestion
    draw_box(0.03, 0.45, 0.16, 0.32, "B1: Ingestion", "สตรีม & กรอง Log\nจับกลุ่มตาม ID")
    # Arrow 1
    ax.annotate('', xy=(0.23, 0.61), xytext=(0.19, 0.61),
                arrowprops=dict(arrowstyle="->", color="#718096", lw=1.5))

    # Block 2: Drain3
    draw_box(0.23, 0.45, 0.17, 0.32, "B2: Drain3", "สกัดแม่พิมพ์ข้อความ\nแมปสู่ Event ID")
    # Arrow 2
    ax.annotate('', xy=(0.44, 0.61), xytext=(0.40, 0.61),
                arrowprops=dict(arrowstyle="->", color="#718096", lw=1.5))

    # Block 3: Features & Dual Engine
    draw_box(0.44, 0.58, 0.25, 0.25, "Engine 1: iForest", "Count Vector (100 Trees)\nตรวจจับความถี่ & ปริมาณ",
             bg_c="#EBF8FF", border_c="#3182CE", text_c="#2B6CB0")
    
    draw_box(0.44, 0.26, 0.25, 0.25, "Engine 2: DeepLog", "2-Layer LSTM (Top-K=3)\nตรวจจับไวยากรณ์ลำดับ",
             bg_c="#EBF8FF", border_c="#3182CE", text_c="#2B6CB0")

    # Arrows splitting from Drain3 to iForest and DeepLog
    ax.annotate('', xy=(0.44, 0.70), xytext=(0.40, 0.61),
                arrowprops=dict(arrowstyle="->", color="#3182CE", lw=1.3))
    ax.annotate('', xy=(0.44, 0.38), xytext=(0.40, 0.61),
                arrowprops=dict(arrowstyle="->", color="#3182CE", lw=1.3))

    # Converging to Block 4: Cascaded Synergy
    draw_box(0.73, 0.38, 0.24, 0.38, "B4: Cascaded Synergy", "Two-Tier Decision Logic\n• Sequence Gate\n• Noise Suppressor (-47%)",
             bg_c="#FEFCBF", border_c="#D69E2E", text_c="#744210")

    ax.annotate('', xy=(0.73, 0.62), xytext=(0.69, 0.70),
                arrowprops=dict(arrowstyle="->", color="#D69E2E", lw=1.3))
    ax.annotate('', xy=(0.73, 0.48), xytext=(0.69, 0.38),
                arrowprops=dict(arrowstyle="->", color="#D69E2E", lw=1.3))

    # Footer banner
    ax.text(0.50, 0.12, "B5: DeepLogExplainer ชี้เป้า Culprit Line พร้อมสกัด 5 บรรทัดแวดล้อม และ Softmax ทันที",
            ha='center', va='center', fontproperties=prop_reg, fontsize=9.0, color="#2D3748")

    plt.tight_layout()
    out_path = os.path.join(ASSETS_DIR, "pipeline_diagram.png")
    plt.savefig(out_path, dpi=300, bbox_inches='tight', pad_inches=0.02)
    plt.close()
    print("Created:", out_path)


def create_forensics_preview():
    """4. ภาพจำลองการชี้เป้าสาเหตุ (Forensics & Culprit Line) สำหรับแผง 6 (ผลลัพธ์)"""
    fig, ax = plt.subplots(figsize=(6.6, 2.7), dpi=300)
    ax.set_facecolor('#FFFFFF')
    fig.patch.set_facecolor('#FFFFFF')
    ax.axis('off')

    # Card Container
    bg = patches.FancyBboxPatch((0.01, 0.02), 0.98, 0.96,
                                boxstyle="round,pad=0.02,rounding_size=0.03",
                                facecolor="#FFFFFF", edgecolor="#CBD5E1", linewidth=1.5)
    ax.add_patch(bg)

    # Title Banner
    banner = patches.FancyBboxPatch((0.03, 0.80), 0.94, 0.15,
                                    boxstyle="round,pad=0.01,rounding_size=0.02",
                                    facecolor="#1A202C", edgecolor="none")
    ax.add_patch(banner)
    ax.text(0.06, 0.88, "INCIDENT FORENSICS: blk_-1608999687919862906", ha='left', va='center',
            fontproperties=prop_bold, fontsize=10.5, color="#FFFFFF")
    ax.text(0.92, 0.88, "VERDICT: ANOMALY", ha='right', va='center',
            fontproperties=prop_bold, fontsize=10, color="#FC8181")

    # Context Window 5 Lines
    lines = [
        ("L1", "Receiving block blk_-1608... src: /10.250.19.102:54106 dest: /10.250.19.102:50010", False),
        ("L2", "PacketResponder 1 for block blk_-1608... terminating", False),
        ("L3", "writeBlock blk_-1608... received exception java.io.IOException [CULPRIT LINE]", True),
        ("L4", "PacketResponder 0 for block blk_-1608... terminating", False),
        ("L5", "10.250.19.102:50010:Exception in receiveBlock for block blk_-1608...", False)
    ]

    y_pos = 0.69
    for tag, txt, is_culprit in lines:
        if is_culprit:
            # Highlight box
            hl = patches.FancyBboxPatch((0.03, y_pos - 0.035), 0.94, 0.075,
                                        boxstyle="round,pad=0.005,rounding_size=0.01",
                                        facecolor="#FFF5F5", edgecolor="#E53E3E", linewidth=1.2)
            ax.add_patch(hl)
            ax.text(0.05, y_pos, f">> {tag}", ha='left', va='center',
                    fontproperties=prop_bold, fontsize=9.0, color="#C53030")
            ax.text(0.12, y_pos, txt, ha='left', va='center',
                    fontproperties=prop_bold, fontsize=8.5, color="#9B2C2C")
        else:
            ax.text(0.05, y_pos, f"   {tag}", ha='left', va='center',
                    fontproperties=prop_reg, fontsize=9.0, color="#718096")
            ax.text(0.12, y_pos, txt, ha='left', va='center',
                    fontproperties=prop_reg, fontsize=8.2, color="#4A5568")
        y_pos -= 0.082

    # Bottom analysis bar
    btm_box = patches.FancyBboxPatch((0.03, 0.06), 0.94, 0.17,
                                     boxstyle="round,pad=0.01,rounding_size=0.02",
                                     facecolor="#EDF2F7", edgecolor="#CBD5E1", linewidth=1.0)
    ax.add_patch(btm_box)
    ax.text(0.05, 0.16, "Root Cause Analysis: DeepLog คาดการณ์ Top-3 ลำดับที่ถูกต้องคือ [E5, E22, E11] (Prob > 99.4%)",
            ha='left', va='center', fontproperties=prop_bold, fontsize=8.8, color="#2D3748")
    ax.text(0.05, 0.09, "แต่เกิด Event 9 (IOException) กะทันหัน จึงตรวจจับความผิดปกติและชี้เป้าบรรทัดนี้ทันที",
            ha='left', va='center', fontproperties=prop_reg, fontsize=8.5, color="#4A5568")

    plt.tight_layout()
    out_path = os.path.join(ASSETS_DIR, "forensics_preview.png")
    plt.savefig(out_path, dpi=300, bbox_inches='tight', pad_inches=0.02)
    plt.close()
    print("Created:", out_path)

if __name__ == "__main__":
    create_cover_badge()
    create_kpi_card()
    create_problem_comparison()
    create_pipeline_diagram()
    create_forensics_preview()
    print("All brochure figures generated successfully!")
