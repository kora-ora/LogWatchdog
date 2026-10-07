#!/usr/bin/env python3
"""
สคริปต์สำหรับสร้างแผ่นพับขนาด A4 แนวนอน (A4 Landscape Tri-Fold Brochure / Pamphlet)
สำหรับโครงงาน LogWatchdog: ระบบตรวจจับและระบุสาเหตุความผิดปกติใน System Logs
ด้วยสถาปัตยกรรม Hybrid Dual-Engine (Isolation Forest + DeepLog LSTM) พร้อมกลไก Cascaded Synergy

การออกแบบตามหลักวิชาการและประชาสัมพันธ์:
1. เป้าหมาย: เข้าใจใน 30 วินาที ว่าระบบแก้ปัญหาอะไร
2. สารหลัก: "LogWatchdog จับทั้ง Log ที่มี Error และ Log ที่ลำดับขั้นตอนผิด แล้วชี้บรรทัดต้นเหตุให้ทันที"
3. ผัง 6 แผง Tri-Fold (หน้านอก: แผงพับเข้า | ปกหลัง | ปกหน้า, หน้าใน: ปัญหา -> วิธีแก้ -> ผลลัพธ์)
4. รูปภาพประกอบความละเอียดสูง (300 DPI) ลดความหนาแน่นของข้อความ
5. ฟอนต์ TH SarabunPSK มาตรฐานราชการ คมชัด ไม่มีกล่องสี่เหลี่ยม (Tofu-free)
6. ตัวเลขถูกต้องสอดคล้องกับ Benchmark จริง 100% (37 Unit tests, FP iForest 178, FP Hybrid 286 ลด 46.9%)
"""

import os
import subprocess
import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls

ASSETS_DIR = "/home/kora/Project/AI Project/assets/brochure"

def set_cell_background(cell, fill_hex):
    """กำหนดสีพื้นหลังของเซลล์"""
    tcPr = cell._tc.get_or_add_tcPr()
    shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{fill_hex}"/>')
    tcPr.append(shd)

def set_cell_margins(cell, top=15, bottom=15, left=45, right=45):
    """กำหนดระยะขอบภายในเซลล์ (dxa: 1 pt = 20 dxa)"""
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = parse_xml(
        f'<w:tcMar {nsdecls("w")}>'
        f'<w:top w:w="{top}" w:type="dxa"/>'
        f'<w:bottom w:w="{bottom}" w:type="dxa"/>'
        f'<w:left w:w="{left}" w:type="dxa"/>'
        f'<w:right w:w="{right}" w:type="dxa"/>'
        f'</w:tcMar>'
    )
    tcPr.append(tcMar)

def set_table_borders(table, color="CBD5E1", sz="4", val="single"):
    """กำหนดเส้นขอบตาราง"""
    tblPr = table._tbl.tblPr
    borders = parse_xml(
        f'<w:tblBorders {nsdecls("w")}>'
        f'<w:top w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>'
        f'<w:bottom w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>'
        f'<w:left w:val="none"/><w:right w:val="none"/>'
        f'<w:insideH w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>'
        f'<w:insideV w:val="none"/>'
        f'</w:tblBorders>'
    )
    tblPr.append(borders)

def add_run_psk(p, text, size_pt=10.5, bold=False, italic=False, color=RGBColor(0x2D, 0x37, 0x48)):
    """เพิ่มข้อความด้วยฟอนต์ TH SarabunPSK อย่างถูกต้องสมบูรณ์"""
    r = p.add_run(text)
    r.font.name = "TH SarabunPSK"
    r.font.size = Pt(size_pt)
    r.bold = bold
    r.italic = italic
    r.font.color.rgb = color
    rPr = r._r.get_or_add_rPr()
    rFonts = parse_xml(r"""<w:rFonts %s w:ascii="TH SarabunPSK" w:hAnsi="TH SarabunPSK" w:cs="TH SarabunPSK"/>""" % nsdecls("w"))
    rPr.append(rFonts)
    return r

def add_p_banner(cell, title_th, title_en=None, icon=None, bg_color="1A365D"):
    """สร้างแถบหัวเรื่องประจำแผง (Panel Header Banner)"""
    p = cell.paragraphs[0] if len(cell.paragraphs) == 1 and cell.paragraphs[0].text == "" else cell.add_paragraph()
    pPr = p._p.get_or_add_pPr()
    shd = parse_xml(r"""<w:shd %s w:fill="%s"/>""" % (nsdecls("w"), bg_color))
    pPr.append(shd)
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after = Pt(2.0)
    p.paragraph_format.line_spacing = 1.05

    prefix = f"{icon} " if icon else ""
    add_run_psk(p, prefix + title_th, size_pt=12.5, bold=True, color=RGBColor(0xFF, 0xFF, 0xFF))
    if title_en:
        add_run_psk(p, f"\n{title_en}", size_pt=8.5, italic=True, color=RGBColor(0xE2, 0xE8, 0xF0))

def add_image_box(cell, image_filename, width_in=3.45, space_before=2.0, space_after=3.0):
    """เพิ่มรูปภาพประกอบลงในเซลล์ จัดกึ่งกลางพอดีขอบ"""
    img_path = os.path.join(ASSETS_DIR, image_filename)
    if not os.path.exists(img_path):
        return None
    p = cell.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(space_before)
    p.paragraph_format.space_after = Pt(space_after)
    p.paragraph_format.line_spacing = 1.0
    r = p.add_run()
    r.add_picture(img_path, width=Inches(width_in))
    return p

def add_styled_card_p(cell, title, items, border_color="2B6CB0", bg_fill="F8FAFC", space_before=2.5, space_after=3.0):
    """สร้างกล่องข้อความแบบกระชับ (Card) โดยใช้ Paragraph Border & Shading"""
    p = cell.add_paragraph()
    p.paragraph_format.space_before = Pt(space_before)
    p.paragraph_format.space_after = Pt(space_after)
    p.paragraph_format.line_spacing = 1.08
    pPr = p._p.get_or_add_pPr()

    # Border ด้านซ้าย หนา 18 (2.25 pt)
    pBdr = parse_xml(
        f'<w:pBdr {nsdecls("w")}>'
        f'<w:left w:val="single" w:sz="18" w:space="8" w:color="{border_color}"/>'
        f'<w:top w:val="none"/><w:right w:val="none"/><w:bottom w:val="none"/>'
        f'</w:pBdr>'
    )
    pPr.append(pBdr)

    # Shading สีพื้นหลัง
    if bg_fill:
        shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{bg_fill}"/>')
        pPr.append(shd)

    # Title
    if title:
        r_title = p.add_run(f"{title}\n")
        r_title.font.name = "TH SarabunPSK"
        r_title.font.size = Pt(11.0)
        r_title.bold = True
        r_title.font.color.rgb = RGBColor(0x1A, 0x36, 0x5D)
        rFonts = parse_xml(r"""<w:rFonts %s w:ascii="TH SarabunPSK" w:hAnsi="TH SarabunPSK" w:cs="TH SarabunPSK"/>""" % nsdecls("w"))
        r_title._r.get_or_add_rPr().append(rFonts)

    # Body lines
    for i, itm in enumerate(items):
        is_last = (i == len(items) - 1)
        suffix = "" if is_last else "\n"
        r_itm = p.add_run(f"{itm}{suffix}")
        r_itm.font.name = "TH SarabunPSK"
        r_itm.font.size = Pt(10.0)
        r_itm.font.color.rgb = RGBColor(0x2D, 0x37, 0x48)
        rFonts = parse_xml(r"""<w:rFonts %s w:ascii="TH SarabunPSK" w:hAnsi="TH SarabunPSK" w:cs="TH SarabunPSK"/>""" % nsdecls("w"))
        r_itm._r.get_or_add_rPr().append(rFonts)

# ==============================================================================
# 1. หน้านอก (Outside Spread: แผงพับเข้า | ปกหลัง | ปกหน้า)
# ==============================================================================

def build_flap_panel(cell):
    """แผง 3: แผงพับเข้า (Flap) - สิ่งแรกที่เห็นเมื่อเปิดอ่าน จุดเด่นและตัวเลขใหญ่ 3 ตัว"""
    add_p_banner(cell, "จุดเด่นและตัวเลขสำคัญ", "Core Highlights & Benchmark Snapshot", icon="[ ◆ ]", bg_color="1A365D")

    # ภาพ KPI Metrics Cards (Recall 100%, F1 84.72%, FP -46.9%)
    add_image_box(cell, "kpi_metrics_card.png", width_in=3.45, space_before=2.0, space_after=2.5)

    # Card 1: ทำไมต้อง LogWatchdog?
    add_styled_card_p(
        cell,
        "◆ ทำไมต้องเลือกระบบ LogWatchdog?",
        [
            "• แก้ปัญหาคอขวด: ก้าวข้าม Regex ที่ตาบอดต่อลำดับเหตุการณ์",
            "• ผสาน 2 ขุมพลัง AI: จับทั้งความถี่ผิดปกติ (Count) และลำดับผิดพลาด (Sequence)",
            "• ตัดเสียงรบกวน 46.9%: กลไก Cascaded Synergy คัดกรอง False Alarm ทิ้ง",
            "• ชี้เป้าต้นเหตุทันที: สกัด 5 บรรทัดแวดล้อม ระบุ Culprit Line ตรงจุด"
        ],
        border_color="2B6CB0", bg_fill="F8FAFC", space_before=2.0, space_after=2.5
    )

    # Card 2: คุณค่าระดับวิศวกรรมระบบ (Engineering Values)
    add_styled_card_p(
        cell,
        "◆ ประสิทธิภาพเชิงวิศวกรรมระบบ",
        [
            "✓ วิเคราะห์ได้ระดับมิลลิวินาที/Session บน CPU ทั่วไป (ไม่ต้องพึ่งพา GPU)",
            "✓ ตัดปัญหา Alert Fatigue ช่วยให้วิศวกรโฟกัสเฉพาะปัญหาที่เกิดขึ้นจริง",
            "✓ Zero-Leakage Data Pipeline: รับประกันความถูกต้องตามระเบียบวิธีวิจัย",
            "✓ สกัดแม่พิมพ์ Log อัตโนมัติด้วย Drain3 ปรับตัวเข้ากับ Log รูปแบบใหม่ได้ทันที"
        ],
        border_color="276749", bg_fill="F0FFF4", space_before=2.0, space_after=1.0
    )


def build_back_cover_panel(cell):
    """แผง 2: ปกหลัง (Back Cover) - คณะผู้จัดทำ, ที่ปรึกษา, Tech Stack, CTA และการอ้างอิง"""
    add_p_banner(cell, "ข้อมูลโครงงานและคณะผู้จัดทำ", "Project Team & Academic Credits", icon="[ ◆ ]", bg_color="1A365D")

    # Card 1: คณะผู้พัฒนาและที่ปรึกษา
    add_styled_card_p(
        cell,
        "◆ คณะผู้จัดทำ & คณาจารย์ที่ปรึกษา",
        [
            "ผู้พัฒนา: นายกรวิชญ์ คงคล้าย (Korawit Kongkhlai)",
            "รหัสนักศึกษา: 6710110006  |  Section: 01",
            "สาขาวิชาวิศวกรรมคอมพิวเตอร์ ภาควิชาวิศวกรรมคอมพิวเตอร์",
            "คณะวิศวกรรมศาสตร์ มหาวิทยาลัยสงขลานครินทร์",
            "อาจารย์ที่ปรึกษา: ดร. อนันท์ ชยกสิริวงศ์, ดร. วรินทร โรจนกรินทร์",
            "รายวิชา 240-318 AI&ML (ปีการศึกษา 2569/1)"
        ],
        border_color="1A365D", bg_fill="F8FAFC", space_before=2.0, space_after=2.5
    )

    # Card 2: สถาปัตยกรรม & เทคโนโลยี (Tech Stack)
    add_styled_card_p(
        cell,
        "◆ สถาปัตยกรรมและเทคโนโลยีที่ใช้ (Tech Stack)",
        [
            "• Core AI: PyTorch (2-Layer LSTM) + Scikit-learn (Isolation Forest)",
            "• Log Parser: Drain3 Template Miner (LogHub Standard)",
            "• Interactive UI: Streamlit + Altair Data Visualization",
            "• Code Quality: Automated Unit Tests ผ่าน 37/37 ข้อ ครบ 100% (pytest)"
        ],
        border_color="2B6CB0", bg_fill="EBF8FF", space_before=2.0, space_after=2.5
    )

    # Card 3: การทดสอบและการเข้าถึง (CTA & Repository)
    add_styled_card_p(
        cell,
        "◆ การสาธิตระบบและซอร์สโค้ด (Demonstration & Code)",
        [
            "• ขอเชิญรับชม Live Demonstration ได้ที่บูธนำเสนอโครงงาน",
            "• ทดสอบผ่าน Web Dashboard ในเครื่อง: http://localhost:8501",
            "• Source Code & Documentation: github.com/kora-ora/LogWatchdog",
            "• เอกสารอ้างอิงหลัก: DeepLog (CCS'17), iForest (ICDM'08), LogHub (ICSE'19)"
        ],
        border_color="276749", bg_fill="F0FFF4", space_before=2.0, space_after=1.0
    )


def build_front_cover_panel(cell):
    """แผง 1: ปกหน้า (Front Cover) - ดึงความสนใจ สารหลัก 1 ประโยค และภาพเรดาร์"""
    # หัวเรื่องรายวิชาและสถาบัน
    p_inst = cell.paragraphs[0] if len(cell.paragraphs) == 1 and cell.paragraphs[0].text == "" else cell.add_paragraph()
    p_inst.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_inst.paragraph_format.space_before = Pt(0)
    p_inst.paragraph_format.space_after = Pt(2.0)
    add_run_psk(p_inst, "รายวิชา 240-318 AI&ML | สาขาวิชาวิศวกรรมคอมพิวเตอร์ ม.อ.", size_pt=9.5, bold=True, color=RGBColor(0x4A, 0x55, 0x68))

    # กล่องชื่อโครงการหลัก (Dark Hero Card)
    p_hero = cell.add_paragraph()
    p_hero.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_hero.paragraph_format.space_before = Pt(1.5)
    p_hero.paragraph_format.space_after = Pt(2.5)
    pPr_hero = p_hero._p.get_or_add_pPr()
    shd_hero = parse_xml(r"""<w:shd %s w:fill="0F172A"/>""" % nsdecls("w"))
    pPr_hero.append(shd_hero)
    add_run_psk(p_hero, "LogWatchdog\n", size_pt=22.0, bold=True, color=RGBColor(0xFF, 0xFF, 0xFF))
    add_run_psk(p_hero, "ระบบตรวจจับและระบุสาเหตุความผิดปกติใน System Logs\n", size_pt=10.5, bold=True, color=RGBColor(0x38, 0xBD, 0xF8))
    add_run_psk(p_hero, "Hybrid Dual-Engine: Isolation Forest + DeepLog LSTM", size_pt=8.5, italic=True, color=RGBColor(0x94, 0xA3, 0xB8))

    # สารหลัก (1 ประโยคเด่น)
    p_msg = cell.add_paragraph()
    p_msg.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_msg.paragraph_format.space_before = Pt(2.0)
    p_msg.paragraph_format.space_after = Pt(2.5)
    add_run_psk(p_msg, "“ ไม่ใช่แค่จับ Error แต่จับลำดับที่ผิด\nและบอกว่าผิดที่บรรทัดไหนทันที ”", size_pt=11.5, bold=True, color=RGBColor(0x1A, 0x36, 0x5D))

    # ภาพ Radar Graphic
    add_image_box(cell, "cover_badge.png", width_in=3.45, space_before=1.5, space_after=2.5)

    # จุดเด่นสำคัญระดับองค์กร (Core Values Card)
    add_styled_card_p(
        cell,
        "◆ จุดเด่นนวัตกรรมระดับองค์กร (Core Values)",
        [
            "✓ ตรวจจับได้ครบ 100% Recall: ครอบคลุมทั้ง Error ชัดเจนและลำดับแอบแฝง",
            "✓ ตัดการแจ้งเตือนพร่ำเพรื่อลง 46.9% ด้วยกลไก Cascaded Synergy",
            "✓ Root Cause Localization: ชี้เป้าบรรทัดปัญหาพร้อมบริบท 5 บรรทัด",
            "✓ Ultra-Lightweight: ประมวลผลระดับมิลลิวินาทีบน CPU โดยไม่ต้องใช้ GPU"
        ],
        border_color="276749", bg_fill="F0FFF4", space_before=1.5, space_after=2.0
    )

    # Footer สถาบัน
    p_ft = cell.add_paragraph()
    p_ft.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_ft.paragraph_format.space_before = Pt(1.5)
    p_ft.paragraph_format.space_after = Pt(0)
    add_run_psk(p_ft, "ภาควิชาวิศวกรรมคอมพิวเตอร์ คณะวิศวกรรมศาสตร์\nมหาวิทยาลัยสงขลานครินทร์ วิทยาเขตหาดใหญ่", size_pt=9.0, bold=False, color=RGBColor(0x71, 0x80, 0x96))


# ==============================================================================
# 2. หน้าใน (Inside Spread: 4 ปัญหา -> 5 วิธีแก้ -> 6 ผลลัพธ์)
# ==============================================================================

def build_problem_panel(cell):
    """แผง 4: ปัญหาของการวิเคราะห์เดิม (The Problem & Pain Points) - ทำไมต้องมีระบบนี้"""
    add_p_banner(cell, "ปัญหาของการวิเคราะห์เดิม", "The Big Challenge & Pain Points", icon="[ ◆ ]", bg_color="9B2C2C")

    # Card 1: 4 อุปสรรควิกฤตของระบบ Log ในปัจจุบัน
    add_styled_card_p(
        cell,
        "◆ 4 อุปสรรควิกฤตของ System Logs ขนาดใหญ่",
        [
            "1. ข้อมูลมหาศาล (Massive Volume): คลัสเตอร์ผลิต Log หลายล้านบรรทัด/ชม. คนตรวจไม่ไหว",
            "2. Regex ล้มเหลว (Brittle): จับลำดับข้ามขั้นไม่ได้ หากไม่มีคำว่า 'Error' ปรากฏ",
            "3. แจ้งเตือนล้นเกิน (Alert Fatigue): โมเดลเดี่ยวเตือนพร่ำเพรื่อจนทีมงานเพิกเฉย",
            "4. ขาดการชี้เป้า (Black-box): โมเดลทั่วไปบอกแค่ผิดปกติ แต่ไม่บอกว่าผิดที่บรรทัดไหน"
        ],
        border_color="C53030", bg_fill="FFF5F5", space_before=2.0, space_after=2.5
    )

    # ภาพ Infographic: Regex Blindness vs LogWatchdog
    add_image_box(cell, "problem_comparison.png", width_in=3.45, space_before=1.5, space_after=2.5)

    # Card 2: มิติความผิดปกติที่ต้องตรวจจับพร้อมกัน
    add_styled_card_p(
        cell,
        "◆ สรุปแก่นปัญหา: มิติความผิดปกติ 2 ด้านที่ต้องตรวจคู่กัน",
        [
            "• มิติความถี่และปริมาณ (Count Outlier): Log บางประเภทพุ่งสูงหรือขาดหายผิดปกติ",
            "• มิติลำดับขั้นตอน (Sequential Violation): ขั้นตอนการทำงานสลับ ข้าม หรือไม่สมบูรณ์",
            "• ระบบ LogWatchdog จึงถูกออกแบบให้ครอบคลุมทั้ง 2 มิติอย่างสมบูรณ์แบบ"
        ],
        border_color="1A365D", bg_fill="F8FAFC", space_before=1.5, space_after=1.0
    )


def build_architecture_panel(cell):
    """แผง 5: สถาปัตยกรรม Hybrid Dual-Engine (AI Core & Pipeline) - ทำงานอย่างไร"""
    add_p_banner(cell, "สถาปัตยกรรม Hybrid Dual-Engine", "AI Core & Cascaded Synergy", icon="[ ◆ ]", bg_color="1A365D")

    # ภาพ Pipeline Diagram 5 บล็อก
    add_image_box(cell, "pipeline_diagram.png", width_in=3.45, space_before=2.0, space_after=2.5)

    # Card 1: 2 ขุมพลัง AI ที่เสริมจุดแข็งซึ่งกันและกัน
    add_styled_card_p(
        cell,
        "◆ สองขุมพลัง AI เสริมจุดแข็งซึ่งกันและกัน (Dual Engines)",
        [
            "• Engine 1: Isolation Forest (100 Trees, Contamination 0.10)",
            "  - วิเคราะห์ความถี่ด้วย Count Vector ตรวจจับเหตุการณ์ปริมาณผิดปกติ",
            "• Engine 2: DeepLog (2-Layer LSTM, Hidden 32, Top-K=3)",
            "  - ตรวจจับไวยากรณ์ลำดับการทำงานผ่าน Sliding Window (w=3)"
        ],
        border_color="2B6CB0", bg_fill="EBF8FF", space_before=1.5, space_after=2.5
    )

    # Card 2: กฎการตัดสินใจ Cascaded Synergy (ตัดเสียงรบกวน 46.9%)
    add_styled_card_p(
        cell,
        "◆ กลไก Cascaded Synergy (Two-Tier Decision Logic)",
        [
            "1. Sequence Gate: หาก LSTM ตรวจพบ 0 violations ➔ สรุป Normal ทันที",
            "2. Severity Rule: หาก LSTM พบผิดปกติรุนแรง (≥3) หรือ iForest ฟ้อง ➔ Anomaly",
            "3. Noise Suppressor: หาก LSTM พบ 1-2 violations แต่ความถี่ปกติสมบูรณ์",
            "   ➔ สรุป Normal (ตัด False Alarm จากการสลับเธรดทิ้งได้ถึง 46.9%!)"
        ],
        border_color="D69E2E", bg_fill="FEFCBF", space_before=1.5, space_after=1.0
    )


def build_results_panel(cell):
    """แผง 6: ผลการทดสอบเชิงประจักษ์ & แดชบอร์ด (Results & Forensic Web App) - พิสูจน์ว่าได้ผล"""
    add_p_banner(cell, "ผลการทดสอบเชิงประจักษ์ & แดชบอร์ด", "Empirical Evaluation & Incident Forensics", icon="[ ◆ ]", bg_color="1A365D")

    # ตารางเปรียบเทียบ 3 โมเดล (FP iForest = 178 ตามความจริง)
    p_tintro = cell.add_paragraph()
    p_tintro.paragraph_format.space_before = Pt(1.5)
    p_tintro.paragraph_format.space_after = Pt(1.5)
    add_run_psk(p_tintro, "Benchmark: ประเมินบนชุดทดสอบมาตรฐาน In-Vocabulary 2,793 เซสชัน:", size_pt=9.5, bold=True, color=RGBColor(0x1A, 0x36, 0x5D))

    table = cell.add_table(rows=4, cols=5)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    set_table_borders(table, color="CBD5E1", sz="4", val="single")

    col_widths = [Inches(0.95), Inches(0.60), Inches(0.60), Inches(0.60), Inches(0.70)]
    for row in table.rows:
        for idx, width in enumerate(col_widths):
            row.cells[idx].width = width

    # Header row
    hdr_titles = ["โมเดล", "Recall", "Prec.", "F1", "FP (ลวง)"]
    for idx, txt in enumerate(hdr_titles):
        c = table.rows[0].cells[idx]
        set_cell_background(c, "1A365D")
        set_cell_margins(c, top=8, bottom=8, left=15, right=15)
        p = c.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.space_after = Pt(0)
        add_run_psk(p, txt, size_pt=9.0, bold=True, color=RGBColor(0xFF, 0xFF, 0xFF))

    # Data rows
    row_data = [
        ("iForest", "28.25%", "55.72%", "37.49%", "178"),
        ("DeepLog", "100.00%", "59.53%", "74.64%", "539"),
        ("Hybrid (เรา)", "100.00%", "73.49%", "84.72%", "286 (-47%)")
    ]
    for r_idx, (m_name, rec, prec, f1, fp) in enumerate(row_data):
        row_cells = table.rows[r_idx + 1].cells
        bg_c = "EBF8FF" if r_idx == 2 else ("FFFFFF" if r_idx % 2 == 0 else "F8FAFC")
        txt_c = RGBColor(0x1A, 0x36, 0x5D) if r_idx == 2 else RGBColor(0x2D, 0x37, 0x48)
        is_b = (r_idx == 2)

        for c_idx, val in enumerate([m_name, rec, prec, f1, fp]):
            c = row_cells[c_idx]
            set_cell_background(c, bg_c)
            set_cell_margins(c, top=7, bottom=7, left=15, right=15)
            p = c.paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.space_before = Pt(0)
            p.paragraph_format.space_after = Pt(0)
            add_run_psk(p, val, size_pt=8.8, bold=is_b, color=txt_c)

    # ภาพจำลอง Forensics & Culprit Line
    add_image_box(cell, "forensics_preview.png", width_in=3.45, space_before=2.0, space_after=2.0)

    # Card: การชี้เป้าและการใช้งาน Streamlit
    add_styled_card_p(
        cell,
        "◆ นิติวิทยาศาสตร์ชี้เป้า (DeepLogExplainer) & Web App",
        [
            "• ชี้เป้า Culprit Line: สกัดบรรทัดที่เกิดปัญหาพร้อมบริบท 5 บรรทัด",
            "• แจกแจง Top-3 Softmax: แสดงสิ่งที่โมเดลคาดหวังเทียบกับเหตุการณ์จริง",
            "• Streamlit 3-Tab: Benchmark Table, Forensic Explorer, Sequence Playground",
            "• รันคำสั่งสาธิตง่ายๆ: ./run_demo.sh หรือ streamlit run app.py"
        ],
        border_color="276749", bg_fill="F0FFF4", space_before=1.5, space_after=1.0
    )


# ==============================================================================
# Master Document Generation & PDF Export
# ==============================================================================

def generate_brochure():
    print("Generating LogWatchdog A4 Landscape Tri-Fold Brochure...")

    doc = docx.Document()

    # ตั้งค่ากระดาษ A4 แนวนอน (Landscape: กว้าง 11.69 นิ้ว, สูง 8.27 นิ้ว)
    section = doc.sections[0]
    section.page_width = Inches(11.69)
    section.page_height = Inches(8.27)
    section.top_margin = Inches(0.24)
    section.bottom_margin = Inches(0.24)
    section.left_margin = Inches(0.28)
    section.right_margin = Inches(0.28)

    # ความกว้างแผง: (11.69 - 0.56) / 3 = 3.71 นิ้ว หักระยะห่างระหว่างคอลัมน์ เหลือ 3.65 นิ้ว
    COL_WIDTH = Inches(3.65)

    # -------------------------------------------------------------------------
    # หน้า 1: ด้านนอก (Outside Spread: แผงพับเข้า | ปกหลัง | ปกหน้า)
    # -------------------------------------------------------------------------
    table_outside = doc.add_table(rows=1, cols=3)
    table_outside.alignment = WD_TABLE_ALIGNMENT.CENTER
    set_table_borders(table_outside, color="E2E8F0", sz="2", val="single")

    row_out = table_outside.rows[0]
    for c in row_out.cells:
        c.width = COL_WIDTH
        set_cell_margins(c, top=10, bottom=10, left=35, right=35)

    print("Building Outside Spread (Flap, Back Cover, Front Cover)...")
    build_flap_panel(row_out.cells[0])
    build_back_cover_panel(row_out.cells[1])
    build_front_cover_panel(row_out.cells[2])

    # ขึ้นหน้าใหม่สำหรับหน้าใน
    doc.add_page_break()

    # -------------------------------------------------------------------------
    # หน้า 2: ด้านใน (Inside Spread: ปัญหา -> วิธีแก้ -> ผลลัพธ์)
    # -------------------------------------------------------------------------
    table_inside = doc.add_table(rows=1, cols=3)
    table_inside.alignment = WD_TABLE_ALIGNMENT.CENTER
    set_table_borders(table_inside, color="E2E8F0", sz="2", val="single")

    row_in = table_inside.rows[0]
    for c in row_in.cells:
        c.width = COL_WIDTH
        set_cell_margins(c, top=10, bottom=10, left=35, right=35)

    print("Building Inside Spread (Problem, AI Architecture, Empirical Results)...")
    build_problem_panel(row_in.cells[0])
    build_architecture_panel(row_in.cells[1])
    build_results_panel(row_in.cells[2])

    # บันทึกเป็นไฟล์ DOCX ชั่วคราว
    docx_path = "/home/kora/Project/AI Project/scratch/LogWatchdog_Brochure_A4.docx"
    os.makedirs(os.path.dirname(docx_path), exist_ok=True)
    doc.save(docx_path)
    print("Saved DOCX:", docx_path)

    # แปลงเป็น ODT และ PDF ด้วย LibreOffice Headless
    odt_target = "/home/kora/Project/AI Project/LogWatchdog_Brochure_A4.odt"
    pdf_target = "/home/kora/Project/AI Project/LogWatchdog_Brochure_A4.pdf"

    print("Converting to ODT via LibreOffice...")
    cmd_odt = [
        "libreoffice", "--headless", "--convert-to", "odt",
        docx_path, "--outdir", "/home/kora/Project/AI Project"
    ]
    subprocess.run(cmd_odt, check=True)

    print("Converting to PDF via LibreOffice...")
    cmd_pdf = [
        "libreoffice", "--headless", "--convert-to", "pdf",
        odt_target, "--outdir", "/home/kora/Project/AI Project"
    ]
    subprocess.run(cmd_pdf, check=True)

    print("Verifying PDF page count...")
    cmd_info = ["pdfinfo", pdf_target]
    res = subprocess.run(cmd_info, capture_output=True, text=True, check=True)
    for line in res.stdout.splitlines():
        if "Pages:" in line:
            print(f"=== {line.strip()} ===")

    print(f"\n[DONE] Brochure compiled successfully:")
    print(f"ODT: {odt_target} ({os.path.getsize(odt_target)} bytes)")
    print(f"PDF: {pdf_target} ({os.path.getsize(pdf_target)} bytes)")

if __name__ == "__main__":
    generate_brochure()
