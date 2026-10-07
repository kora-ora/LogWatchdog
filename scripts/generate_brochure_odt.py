#!/usr/bin/env python3
"""
Script สำหรับสร้างแผ่นพับขนาด A4 แนวนอน (A4 Landscape Tri-Fold Brochure / Pamphlet)
สำหรับโครงงาน LogWatchdog: ระบบตรวจจับและระบุสาเหตุความผิดปกติใน System Logs
ด้วยสถาปัตยกรรม Hybrid Dual-Engine (Isolation Forest + DeepLog LSTM) พร้อมกลไก Cascaded Synergy

การแสดงผลตัวอักษร:
- ใช้ฟอนต์ TH SarabunPSK มาตรฐานราชการและวิชาการไทย ปราศจากกล่องข้อความสี่เหลี่ยม (Tofu-free)
- ใช้สัญลักษณ์ Typography สากล (◆, ▶, ●, ✓) แทนการใช้ Emoji เพื่อความคมชัดระดับวารสารวิชาการ
- ขนาดและระยะขอบคำนวณอย่างแม่นยำให้จบใน 2 หน้า A4 แนวนอน (หน้า 1 ด้านนอก, หน้า 2 ด้านใน) พับ 3 ตอนได้สมบูรณ์แบบ
"""

import os
import subprocess
import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls

def set_cell_background(cell, fill_hex):
    """กำหนดสีพื้นหลังของเซลล์"""
    tcPr = cell._tc.get_or_add_tcPr()
    shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{fill_hex}"/>')
    tcPr.append(shd)

def set_cell_margins(cell, top=20, bottom=20, left=50, right=50):
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

def add_run_psk(p, text, size_pt=11.0, bold=False, italic=False, color=RGBColor(0x2D, 0x37, 0x48)):
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
    p.paragraph_format.space_after = Pt(2.5)
    p.paragraph_format.line_spacing = 1.05

    prefix = f"{icon} " if icon else ""
    add_run_psk(p, prefix + title_th, size_pt=13.0, bold=True, color=RGBColor(0xFF, 0xFF, 0xFF))

    if title_en:
        p.add_run("\n")
        add_run_psk(p, title_en, size_pt=9.5, italic=True, color=RGBColor(0xCB, 0xD5, 0xE1))
    return p

def add_p_card(cell, bold_title, lines, left_color="2B6CB0", bg_color="F8FAFC", title_rgb=RGBColor(0x1A, 0x36, 0x5D), space_after=Pt(1.5)):
    """สร้างกล่องการ์ดข้อความ (Card Box) ที่มีแถบสีเด่นด้านซ้ายและพื้นหลังสีนวล"""
    p = cell.add_paragraph()
    pPr = p._p.get_or_add_pPr()
    pBdr = parse_xml(r"""
        <w:pBdr %s>
            <w:left w:val="single" w:sz="18" w:space="5" w:color="%s"/>
            <w:top w:val="none"/><w:right w:val="none"/><w:bottom w:val="none"/>
        </w:pBdr>
    """ % (nsdecls("w"), left_color))
    shd = parse_xml(r"""<w:shd %s w:fill="%s"/>""" % (nsdecls("w"), bg_color))
    pPr.append(pBdr)
    pPr.append(shd)
    p.paragraph_format.space_before = Pt(1)
    p.paragraph_format.space_after = space_after
    p.paragraph_format.line_spacing = 1.05
    p.paragraph_format.left_indent = Inches(0.06)

    if bold_title:
        add_run_psk(p, bold_title + "\n", size_pt=11.5, bold=True, color=title_rgb)

    for idx, line in enumerate(lines):
        add_run_psk(p, line, size_pt=10.5, color=RGBColor(0x2D, 0x37, 0x48))
        if idx < len(lines) - 1:
            p.add_run("\n")
    return p

def add_p(cell, text, bold_prefix=None, size=10.5, color=RGBColor(0x2D, 0x37, 0x48), space_after=Pt(2), line_spacing=1.05, align=WD_ALIGN_PARAGRAPH.LEFT):
    """เพิ่มย่อหน้าข้อความทั่วไปพร้อมการจัดช่องว่างและฟอนต์มาตรฐาน"""
    p = cell.add_paragraph()
    p.alignment = align
    p.paragraph_format.line_spacing = line_spacing
    p.paragraph_format.space_after = space_after
    if bold_prefix:
        add_run_psk(p, bold_prefix + " ", size_pt=size, bold=True, color=RGBColor(0x1A, 0x36, 0x5D))
    add_run_psk(p, text, size_pt=size, color=color)
    return p

def build_brochure():
    doc = docx.Document()
    sec = doc.sections[0]

    # ตั้งค่ากระดาษ A4 แนวนอน (Landscape: 11.69" x 8.27")
    sec.orientation = docx.enum.section.WD_ORIENT.LANDSCAPE
    sec.page_width = Inches(11.69)
    sec.page_height = Inches(8.27)

    # ขอบกระดาษปรับแต่งเพื่อให้พอดี 2 หน้า A4 พอดี
    sec.top_margin = Inches(0.24)
    sec.bottom_margin = Inches(0.24)
    sec.left_margin = Inches(0.28)
    sec.right_margin = Inches(0.28)

    COL_W = Inches(3.68)
    COLOR_PRIMARY = RGBColor(0x1A, 0x36, 0x5D)    # Deep Navy
    COLOR_SECONDARY = RGBColor(0x2B, 0x6C, 0xB0)  # Slate Blue
    COLOR_TEXT = RGBColor(0x2D, 0x37, 0x48)       # Charcoal
    COLOR_MUTED = RGBColor(0x64, 0x74, 0x8B)      # Slate Gray
    COLOR_SUCCESS = RGBColor(0x16, 0x65, 0x34)    # Forest Green
    COLOR_ALERT = RGBColor(0x99, 0x1B, 0x1B)      # Dark Red

    # =========================================================================
    # หน้า 1: ด้านนอก (OUTSIDE - 3 PANELS)
    # [Panel 3: Highlights] | [Panel 2: Back Cover] | [Panel 1: Front Cover]
    # =========================================================================
    tbl_out = doc.add_table(rows=1, cols=3)
    tbl_out.alignment = WD_TABLE_ALIGNMENT.CENTER
    tbl_out.autofit = False
    for col in tbl_out.columns:
        col.width = COL_W
    for c in tbl_out.rows[0].cells:
        set_cell_margins(c, top=20, bottom=20, left=45, right=45)

    p3_cell, p2_cell, p1_cell = tbl_out.rows[0].cells

    # -------------------------------------------------------------------------
    # PANEL 3 (ซ้ายของหน้า 1): ภาพรวมและจุดเด่นนวัตกรรม (Highlights)
    # -------------------------------------------------------------------------
    add_p_banner(p3_cell, "ภาพรวมและจุดเด่นนวัตกรรม", "Core Highlights & Value Proposition", icon="[●]", bg_color="1A365D")
    add_p(p3_cell, "ในระบบ Big Data การตรวจจับปัญหาจาก Log ด้วย Regex แบบเดิมจับลำดับที่ผิดปกติไม่ได้ ขณะที่โมเดลเดี่ยวก็แจ้งเตือนพร่ำเพรื่อ LogWatchdog จึงผสาน 2 ขุมพลัง AI เพื่อแก้ปัญหานี้โดยเฉพาะ",
          bold_prefix="ความจำเป็น:", size=10.0, space_after=Pt(2.5))

    add_p_card(p3_cell, "◆ 3 เสาหลักนวัตกรรมของ LogWatchdog", [
        "1. Dual-Perspective Engine: ตรวจจับทั้งมิติความถี่ (Count Outlier) และมิติลำดับเวลา (Sequential Workflow)",
        "2. Cascaded Noise Suppression: ใช้ Isolation Forest เป็นตัวกรองช่วยตัด False Alarm จากเธรดสลับ",
        "3. White-Box Explainability: เจาะจงบรรทัดต้นเหตุ (Culprit Line) ดึงบริบท 5 บรรทัดมาแสดงทันที"
    ], left_color="2B6CB0", bg_color="F1F5F9", title_rgb=COLOR_PRIMARY)

    add_p_card(p3_cell, "◆ บทพิสูจน์เชิงตัวเลข (Benchmark Snapshot)", [
        "✓ Recall: 100.00% (ตรวจจับความผิดปกติได้ครบทุกเคส)",
        "✓ Precision: 73.49% (สูงกว่า LSTM เดี่ยว +13.96%)",
        "✓ F1-Score: 84.72% (ยกระดับสูงสุดในทุกการทดสอบ)",
        "✓ False Alarms Cut: ลดลง 46.9% จาก 539 เหลือ 286"
    ], left_color="166534", bg_color="F0FDF4", title_rgb=COLOR_SUCCESS)

    add_p(p3_cell, "ลดระยะเวลากู้คืนระบบ (MTTR) เหลือไม่ถึง 1 วินาที และตัดปัญหา Alert Fatigue ได้อย่างเด็ดขาด พร้อมทำงานรวดเร็วบน CPU ทั่วไป",
          bold_prefix="คุณค่าเชิงวิศวกรรม:", size=10.0, space_after=Pt(0))

    # -------------------------------------------------------------------------
    # PANEL 2 (กลางของหน้า 1): แผงหลัง (Back Cover - ผู้จัดทำและที่ปรึกษา)
    # -------------------------------------------------------------------------
    add_p_banner(p2_cell, "ข้อมูลโครงงานและคณะผู้จัดทำ", "Project Team & Academic Credits", icon="[●]", bg_color="2B6CB0")

    add_p_card(p2_cell, "◆ ผู้พัฒนาโครงงาน (Developer)", [
        "นายกรวิชญ์ คงคล้าย (Korawit Kongkhlai)",
        "รหัสนักศึกษา: 6710110006  |  Section: 01",
        "สาขาวิชาวิศวกรรมคอมพิวเตอร์ ภาควิชาวิศวกรรมคอมพิวเตอร์",
        "คณะวิศวกรรมศาสตร์ มหาวิทยาลัยสงขลานครินทร์"
    ], left_color="2B6CB0", bg_color="F8FAFC")

    add_p_card(p2_cell, "◆ คณาจารย์ที่ปรึกษา (Advisors)", [
        "ดร. อนันท์ ชกสุริวงค์",
        "ดร. วรินทร โรจนกรินทร์",
        "รายวิชา 240-318 AI&ML (ปีการศึกษา 2569/1)"
    ], left_color="1A365D", bg_color="F8FAFC")

    add_p_card(p2_cell, "◆ สถาปัตยกรรมและเทคโนโลยี (Tech Stack)", [
        "• Core AI: PyTorch (LSTM) + Scikit-learn (iForest)",
        "• Log Parsing: Drain3 Template Miner (LogHub)",
        "• Dashboard: Streamlit + Altair Data Visualization",
        "• Quality: 37/37 Unit Tests ผ่าน 100% (pytest)"
    ], left_color="D97706", bg_color="FFFBEB", title_rgb=RGBColor(0xB4, 0x53, 0x09))

    add_p_card(p2_cell, "◆ ระบบทดสอบและสาธิตสด (Interactive Demo)", [
        "• Streamlit Web App: http://localhost:8501",
        "• รองรับ Live Inference จำลอง 3 เคสจริง",
        "• รายงาน Incident Report แบบ JSON / Markdown"
    ], left_color="166534", bg_color="F0FDF4", title_rgb=COLOR_SUCCESS)

    add_p(p2_cell, "อ้างอิง: DeepLog (ACM CCS 2017), Isolation Forest (IEEE ICDM 2008), LogHub Benchmark (ICSE 2019)",
          size=9.0, color=COLOR_MUTED, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=Pt(0))

    # -------------------------------------------------------------------------
    # PANEL 1 (ขวาของหน้า 1): หน้าปกหลัก (Front Cover)
    # -------------------------------------------------------------------------
    add_p(p1_cell, "รายวิชา 240-318 AI&ML | สาขาวิชาวิศวกรรมคอมพิวเตอร์ ม.อ.",
          size=9.5, color=COLOR_MUTED, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=Pt(4))

    # Front Cover Title Card
    p_cov = p1_cell.add_paragraph()
    pPr = p_cov._p.get_or_add_pPr()
    shd = parse_xml(r"""<w:shd %s w:fill="1A365D"/>""" % nsdecls("w"))
    pPr.append(shd)
    p_cov.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_cov.paragraph_format.space_before = Pt(2)
    p_cov.paragraph_format.space_after = Pt(4)
    p_cov.paragraph_format.line_spacing = 1.1

    add_run_psk(p_cov, "LogWatchdog\n", size_pt=22.0, bold=True, color=RGBColor(0xFF, 0xFF, 0xFF))
    add_run_psk(p_cov, "ระบบตรวจจับและระบุสาเหตุความผิดปกติใน System Logs\n", size_pt=12.5, bold=True, color=RGBColor(0x93, 0xC5, 0xFD))
    add_run_psk(p_cov, "Hybrid Dual-Engine Architecture (Isolation Forest + DeepLog LSTM) with Cascaded Synergy",
                size_pt=9.5, italic=True, color=RGBColor(0xCB, 0xD5, 0xE1))

    add_p(p1_cell, "ยกระดับการตรวจจับและสืบสวน Incident ในระบบกระจายศูนย์ (Big Data & Distributed Clusters) ก้าวข้ามขีดจำกัดของ Regex แบบเดิมด้วย AI สองขุมพลัง",
          size=10.0, color=COLOR_PRIMARY, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=Pt(3))

    add_p_card(p1_cell, "◆ จุดเด่นสำคัญระดับองค์กร (Core Values)", [
        "✓ Zero False Negatives: ตรวจจับได้ครบ 100.00% ไม่หลุดรอด",
        "✓ Cascaded Noise Filter: ตัดการแจ้งเตือนพร่ำเพรื่อลง 46.9%",
        "✓ Root Cause Localization: ชี้เป้าบรรทัดปัญหาพร้อมบริบท 5 บรรทัด",
        "✓ Ultra Lightweight: ทำงานระดับมิลลิวินาทีบน CPU มาตรฐาน"
    ], left_color="166534", bg_color="F0FDF4", title_rgb=COLOR_SUCCESS)

    add_p_card(p1_cell, "◆ เหมาะสำหรับผู้ใช้งาน (Target Users)", [
        "• วิศวกรดูแลระบบ (Site Reliability Engineers - SREs)",
        "• ทีม DevOps และ Cloud Infrastructure Engineers",
        "• ผู้ดูแลคลัสเตอร์ประมวลผลขนาดใหญ่ (HDFS, Kubernetes)"
    ], left_color="2B6CB0", bg_color="F8FAFC", title_rgb=COLOR_PRIMARY)

    add_p(p1_cell, "ภาควิชาวิศวกรรมคอมพิวเตอร์ คณะวิศวกรรมศาสตร์\nมหาวิทยาลัยสงขลานครินทร์ วิทยาเขตหาดใหญ่",
          size=9.5, color=COLOR_MUTED, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=Pt(0))

    # =========================================================================
    # หน้า 2: ด้านใน (INSIDE SPREAD - 3 PANELS เมื่อกางออกเต็ม)
    # [Panel 4: The Problem] | [Panel 5: AI Architecture] | [Panel 6: Results & Demo]
    # =========================================================================
    doc.add_page_break()

    tbl_in = doc.add_table(rows=1, cols=3)
    tbl_in.alignment = WD_TABLE_ALIGNMENT.CENTER
    tbl_in.autofit = False
    for col in tbl_in.columns:
        col.width = COL_W
    for c in tbl_in.rows[0].cells:
        set_cell_margins(c, top=20, bottom=20, left=45, right=45)

    p4_cell, p5_cell, p6_cell = tbl_in.rows[0].cells

    # -------------------------------------------------------------------------
    # PANEL 4 (ซ้ายของหน้า 2): ปัญหาและข้อจำกัดของการวิเคราะห์เดิม
    # -------------------------------------------------------------------------
    add_p_banner(p4_cell, "ปัญหาของการวิเคราะห์เดิม", "The Big Challenge & Pain Points", icon="[●]", bg_color="991B1B")
    add_p(p4_cell, "System Event Logs เป็นแหล่งความจริงเชิงประจักษ์ (Ground Truth) เพียงแหล่งเดียวในระบบคอมพิวเตอร์ แต่วิศวกรต้องเผชิญกับ 4 อุปสรรควิกฤต:",
          size=10.0, space_after=Pt(2.5))

    add_p_card(p4_cell, "1. ข้อมูลมหาศาล (Massive Volume)", [
        "คลัสเตอร์ Big Data ผลิต Log หลายล้านบรรทัด/ชม.",
        "การตรวจสอบด้วยสายตามนุษย์ (Manual) เป็นไปไม่ได้"
    ], left_color="991B1B", bg_color="FEF2F2", title_rgb=COLOR_ALERT)

    add_p_card(p4_cell, "2. Regex & Keyword ล้มเหลว (Brittle)", [
        "การค้นหาคำว่า 'Error' หรือ 'Failed' จับเคสสลับลำดับไม่ได้",
        "เช่น คำสั่งลบไฟล์เกิดขึ้นก่อนเขียนเสร็จ แม้คำสั่งจะถูก",
        "ตามไวยากรณ์และไม่มีคำว่า Error ปรากฏเลยก็ตาม"
    ], left_color="991B1B", bg_color="FEF2F2", title_rgb=COLOR_ALERT)

    add_p_card(p4_cell, "3. ภาวะแจ้งเตือนล้นเกิน (Alert Fatigue)", [
        "โมเดลทั่วไปแจ้งเตือนพร่ำเพรื่อเมื่อเธรดสลับที่เล็กน้อย",
        "ทำให้วิศวกรเกิดความล้าและมองข้ามวิกฤตจริงไป"
    ], left_color="D97706", bg_color="FFFBEB", title_rgb=RGBColor(0xB4, 0x53, 0x09))

    add_p_card(p4_cell, "4. ขาดการชี้เป้า (Black-box Invisibility)", [
        "โมเดลส่วนใหญ่บอกแค่ 'ผิดปกติ' แต่ไม่บอกบรรทัดไหน",
        "ทีมงานต้องเสียเวลาค้นหาต้นตอแบบสุ่ม (MTTR สูง)"
    ], left_color="718096", bg_color="F8FAFC", title_rgb=COLOR_PRIMARY)

    add_p(p4_cell, "ความผิดปกติในระบบมี 2 มิติที่ต้องตรวจจับพร้อมกัน: มิติความถี่ (Volumetric Outliers) และ มิติลำดับขั้นตอน (Sequential Path Permutations)",
          bold_prefix="สรุปปัญหา:", size=9.8, space_after=Pt(0))

    # -------------------------------------------------------------------------
    # PANEL 5 (กลางของหน้า 2): สถาปัตยกรรม Hybrid Dual-Engine
    # -------------------------------------------------------------------------
    add_p_banner(p5_cell, "สถาปัตยกรรม Hybrid Dual-Engine", "AI Core & Cascaded Synergy", icon="[●]", bg_color="1A365D")

    add_p_card(p5_cell, "◆ 5-Brick Modular Workflow", [
        "• B1 (Ingestion): สตรีม Log ดิบ กรองและจัดกลุ่มตาม Block ID",
        "• B2 (Drain3 Parser): สกัดแม่พิมพ์ข้อความ แมปสู่ Event ID",
        "• B3 (Features): สกัด Count Vector และ Sliding Window (w=3)",
        "• B4 (Hybrid Core): รวม 2 ขุมพลัง AI ผ่าน Cascaded Synergy",
        "• B5 (Explainer): ระบุ Culprit Line และดึงบริบท 5 บรรทัด"
    ], left_color="2B6CB0", bg_color="F8FAFC", title_rgb=COLOR_PRIMARY)

    add_p_card(p5_cell, "◆ 2 ขุมพลัง AI ที่ทำงานร่วมกัน", [
        "▶ Engine 1: Isolation Forest (100 iTrees, contamination 0.10)",
        "   ตรวจจับความผิดปกติเชิงความถี่และปริมาณ (Count Outlier)",
        "▶ Engine 2: DeepLog 2-Layer LSTM (Embed 32, Hidden 32)",
        "   ตรวจจับไวยากรณ์ลำดับการทำงานด้วยกฎ Top-K = 3"
    ], left_color="1A365D", bg_color="EDF2F7", title_rgb=COLOR_PRIMARY)

    add_p_card(p5_cell, "◆ กลไกตัดสินใจ Cascaded Synergy", [
        "1. Sequence Gate: หาก LSTM ปกติ (0 violations) ➜ สรุป Normal",
        "2. Severity Rule: หาก LSTM ผิดปกติรุนแรง (≥3 violations) หรือ iForest ฟ้องว่าความถี่ผิดปกติ ➜ สรุป Anomaly",
        "3. Noise Suppressor: หาก LSTM พบ 1-2 violations แต่ iForest ยืนยันความถี่ปกติสมบูรณ์ ➜ ปรับเป็น Normal (ตัด False Alarm ทิ้ง!)"
    ], left_color="166534", bg_color="F0FDF4", title_rgb=COLOR_SUCCESS)

    add_p(p5_cell, "กลไกนี้ทำให้ระบบคงค่า Recall 100.00% ไว้ได้ พร้อมลด False Alarm ลงได้ถึง 46.9%!",
          bold_prefix="ผลสำเร็จ:", size=10.0, color=COLOR_SUCCESS, space_after=Pt(0))

    # -------------------------------------------------------------------------
    # PANEL 6 (ขวาของหน้า 2): ผลการทดสอบเชิงประจักษ์ & แดชบอร์ด
    # -------------------------------------------------------------------------
    add_p_banner(p6_cell, "ผลการทดสอบเชิงประจักษ์ & แดชบอร์ด", "Empirical Evaluation & Web App", icon="[●]", bg_color="2B6CB0")

    add_p(p6_cell, "ประเมินผลบนชุดทดสอบมาตรฐาน HDFS 2,793 เซสชัน:",
          bold_prefix="Benchmark:", size=10.0, space_after=Pt(2))

    # Mini table
    tbl_res = p6_cell.add_table(rows=4, cols=5)
    tbl_res.alignment = WD_TABLE_ALIGNMENT.CENTER
    tbl_res.autofit = False
    set_table_borders(tbl_res, color="CBD5E1")

    headers = ["โมเดล", "Recall", "Prec.", "F1", "FP (ลวง)"]
    col_widths = [Inches(1.00), Inches(0.62), Inches(0.62), Inches(0.62), Inches(0.66)]

    for j, h in enumerate(headers):
        cell = tbl_res.cell(0, j)
        cell.width = col_widths[j]
        set_cell_background(cell, "1A365D")
        set_cell_margins(cell, top=20, bottom=20, left=20, right=20)
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_after = Pt(0)
        add_run_psk(p, h, size_pt=9.5, bold=True, color=RGBColor(0xFF, 0xFF, 0xFF))

    rows_data = [
        ("iForest", "28.25%", "55.72%", "37.49%", "179"),
        ("DeepLog", "100.00%", "59.53%", "74.64%", "539"),
        ("Hybrid (เรา)", "100.00%", "73.49%", "84.72%", "286 (-47%)")
    ]

    for i, row in enumerate(rows_data):
        for j, val in enumerate(row):
            cell = tbl_res.cell(i + 1, j)
            cell.width = col_widths[j]
            bg = "EDF2F7" if i == 2 else ("FFFFFF" if i == 0 else "F8FAFC")
            set_cell_background(cell, bg)
            set_cell_margins(cell, top=15, bottom=15, left=20, right=20)
            p = cell.paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER if j > 0 else WD_ALIGN_PARAGRAPH.LEFT
            p.paragraph_format.space_after = Pt(0)
            is_hybrid = (i == 2)
            c_rgb = COLOR_PRIMARY if is_hybrid else COLOR_TEXT
            add_run_psk(p, val, size_pt=9.5, bold=is_hybrid, color=c_rgb)

    p6_cell.add_paragraph().paragraph_format.space_after = Pt(2)

    add_p_card(p6_cell, "◆ นิติวิทยาศาสตร์ชี้เป้า (DeepLogExplainer)", [
        "• ระบุ Culprit Line แม่นยำ: เช่น writeBlock received exception",
        "• สกัด Context Window: แสดง 5 บรรทัดแวดล้อมก่อนและหลังจุดเกิดเหตุ",
        "• แจกแจง Probability Distribution: แสดง Top-K คาดการณ์ vs Actual"
    ], left_color="2B6CB0", bg_color="F8FAFC", title_rgb=COLOR_PRIMARY)

    add_p_card(p6_cell, "◆ Streamlit Web Application (4 แท็บพร้อมใช้งาน)", [
        "1. Model Comparison: ดูกราฟแท่งเปรียบเทียบ 3 โมเดลสด",
        "2. Forensics & Timeline: สืบสวนลำดับเหตุการณ์และชี้เป้าบรรทัดปัญหา",
        "3. Live Playground: จำลองเคส Nominal, Fault, Permutation",
        "4. Architecture Blueprint: แผนผัง Lego 5 บล็อกแบบ Interactive"
    ], left_color="166534", bg_color="F0FDF4", title_rgb=COLOR_SUCCESS)

    add_p(p6_cell, "พร้อมใช้งานผ่านคำสั่ง: ./run_demo.sh หรือ streamlit run app.py",
          size=9.2, color=COLOR_MUTED, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=Pt(0))

    # -------------------------------------------------------------------------
    # บันทึกไฟล์ DOCX ชั่วคราว และแปลงเป็น ODT และ PDF
    # -------------------------------------------------------------------------
    os.makedirs("scratch", exist_ok=True)
    docx_path = "scratch/LogWatchdog_Brochure_A4_generated.docx"
    odt_target = "LogWatchdog_Brochure_A4.odt"
    pdf_target = "LogWatchdog_Brochure_A4.pdf"

    print(f"กำลังบันทึกไฟล์ชั่วคราว {docx_path}...")
    doc.save(docx_path)
    print("บันทึก DOCX สำเร็จ กำลังแปลงเป็น .odt และ .pdf ด้วย LibreOffice...")

    res_odt = subprocess.run(
        ["libreoffice", "--headless", "--convert-to", "odt", docx_path, "--outdir", "."],
        capture_output=True,
        text=True
    )
    if res_odt.returncode != 0:
        print("เกิดข้อผิดพลาดในการแปลง ODT:", res_odt.stderr)
        raise RuntimeError(f"LibreOffice ODT conversion failed: {res_odt.stderr}")

    generated_odt = "LogWatchdog_Brochure_A4_generated.odt"
    if os.path.exists(generated_odt):
        os.replace(generated_odt, odt_target)
        print(f"บันทึกไฟล์แผ่นพับ ODT สำเร็จเป็น {odt_target}")

    res_pdf = subprocess.run(
        ["libreoffice", "--headless", "--convert-to", "pdf", odt_target, "--outdir", "."],
        capture_output=True,
        text=True
    )
    if res_pdf.returncode != 0:
        print("เกิดข้อผิดพลาดในการแปลง PDF:", res_pdf.stderr)
        raise RuntimeError(f"LibreOffice PDF conversion failed: {res_pdf.stderr}")

    file_size_odt = os.path.getsize(odt_target)
    file_size_pdf = os.path.getsize(pdf_target)
    print(f"สร้างไฟล์แผ่นพับเสร็จสมบูรณ์ทั้ง ODT และ PDF!")
    print(f" - ODT: {odt_target} (ขนาด: {file_size_odt:,} ไบต์)")
    print(f" - PDF: {pdf_target} (ขนาด: {file_size_pdf:,} ไบต์)")

if __name__ == "__main__":
    build_brochure()
