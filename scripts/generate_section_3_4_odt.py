#!/usr/bin/env python3
"""
Script สำหรับสร้างเอกสารฉบับเฉพาะเจาะจง:
"3.4 การออกแบบและพัฒนาโมเดล Hybrid Dual-Engine (Model Training & Synergy Details)"
เป็นไฟล์ .odt แยกต่างหาก เพื่อให้มีรายละเอียดเชิงลึกครบถ้วน โดยไม่กระทบกับไฟล์รายงานหลักเดิม

ข้อกำหนดการจัดรูปแบบ:
1. ใช้ลำดับข้อ (Numbered Items) อย่างเป็นระบบ ไม่ใช้ Bullet ผสมตัวเลข
2. ใช้ append_formatted_text() เพื่อแปลง **text** เป็นตัวหนาจริง ไร้สัญลักษณ์ ** หลุดรอด
3. ใช้ add_equation_box() สำหรับสมการคณิตศาสตร์ที่มีสัญลักษณ์ Unicode Math สวยงามระดับวิชาการ
4. คงตารางที่ 3.1 ไว้ตามเดิมและเสริมรายละเอียดด้านการเทรนอย่างละเอียดลึกซึ้ง
"""

import os
import re
import subprocess
import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn

def set_cell_background(cell, fill_hex):
    """กำหนดสีพื้นหลังของเซลล์ในตาราง"""
    tcPr = cell._tc.get_or_add_tcPr()
    shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{fill_hex}"/>')
    tcPr.append(shd)

def set_cell_margins(cell, top=120, bottom=120, left=150, right=150):
    """กำหนดระยะขอบภายในเซลล์ตาราง (หน่วย dxa: 1 pt = 20 dxa)"""
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
    """กำหนดเส้นขอบตารางแบบมินิมอลระดับวารสารวิชาการ"""
    tblPr = table._tbl.tblPr
    borders = parse_xml(
        f'<w:tblBorders {nsdecls("w")}>'
        f'<w:top w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>'
        f'<w:bottom w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>'
        f'<w:insideH w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>'
        f'<w:insideV w:val="none"/>'
        f'<w:left w:val="none"/>'
        f'<w:right w:val="none"/>'
        f'</w:tblBorders>'
    )
    tblPr.append(borders)

def build_section_3_4_report():
    doc = docx.Document()

    # ตั้งค่าขอบหน้ากระดาษตามมาตรฐานรายงาน ม.อ. (ซ้าย 1.25 นิ้ว, บน/ล่าง/ขวา 1 นิ้ว)
    for section in doc.sections:
        section.top_margin = Inches(1.0)
        section.bottom_margin = Inches(1.0)
        section.left_margin = Inches(1.25)
        section.right_margin = Inches(1.0)
        section.different_first_page_header_footer = False

    # สีและฟอนต์มาตรฐาน
    FONT_FAMILY = "Sarabun"
    FONT_MATH = "Cambria Math"
    COLOR_PRIMARY = RGBColor(0x1A, 0x36, 0x5D)    # Navy Blue เข้ม
    COLOR_SECONDARY = RGBColor(0x2B, 0x6C, 0xB0)  # Slate Blue
    COLOR_TEXT = RGBColor(0x2D, 0x37, 0x48)       # Charcoal Dark
    COLOR_MUTED = RGBColor(0x71, 0x80, 0x96)      # Gray
    COLOR_ALERT = RGBColor(0x99, 0x1B, 0x1B)      # Dark Red
    COLOR_SUCCESS = RGBColor(0x16, 0x65, 0x34)    # Dark Green

    # ตั้งค่าสไตล์พื้นฐาน
    style_normal = doc.styles['Normal']
    style_normal.font.name = FONT_FAMILY
    style_normal.font.size = Pt(14)
    style_normal.font.color.rgb = COLOR_TEXT
    style_normal.paragraph_format.line_spacing = 1.25
    style_normal.paragraph_format.space_after = Pt(6)

    def append_formatted_text(paragraph, text, base_font=FONT_FAMILY, base_size=Pt(14), base_color=COLOR_TEXT, base_bold=False, base_italic=False):
        """
        แยกส่วนข้อความที่มี **ตัวหนา**, *ตัวเอียง*, หรือ `โค้ด`
        แล้วเพิ่มเป็น Run ใน docx อย่างถูกต้อง ไร้สัญลักษณ์ ** หรือ ` หลุดรอด
        """
        code_tokens = re.split(r'(`[^`]+`)', text)
        for c_tok in code_tokens:
            if not c_tok:
                continue
            if c_tok.startswith('`') and c_tok.endswith('`') and len(c_tok) >= 2:
                r = paragraph.add_run(c_tok[1:-1])
                r.font.name = "Courier New"
                r.font.size = Pt(12)
                r.font.color.rgb = COLOR_ALERT
                r.bold = True
                continue
            bold_tokens = re.split(r'(\*\*[^*]+\*\*)', c_tok)
            for b_tok in bold_tokens:
                if not b_tok:
                    continue
                if b_tok.startswith('**') and b_tok.endswith('**') and len(b_tok) >= 4:
                    r = paragraph.add_run(b_tok[2:-2])
                    r.font.name = base_font
                    r.font.size = base_size
                    r.bold = True
                    r.font.color.rgb = base_color
                else:
                    italic_tokens = re.split(r'(\*[^*]+\*)', b_tok)
                    for i_tok in italic_tokens:
                        if not i_tok:
                            continue
                        if i_tok.startswith('*') and i_tok.endswith('*') and len(i_tok) >= 2:
                            r = paragraph.add_run(i_tok[1:-1])
                            r.font.name = base_font
                            r.font.size = base_size
                            r.bold = base_bold
                            r.italic = True
                            r.font.color.rgb = base_color
                        else:
                            r = paragraph.add_run(i_tok)
                            r.font.name = base_font
                            r.font.size = base_size
                            r.bold = base_bold
                            r.italic = base_italic
                            r.font.color.rgb = base_color

    def add_title(text, level=1, page_break=False):
        if page_break:
            doc.add_page_break()
        h = doc.add_heading(level=level)
        h.paragraph_format.line_spacing = 1.2
        run = h.add_run(text)
        run.bold = True
        run.font.name = FONT_FAMILY
        if level == 1:
            run.font.size = Pt(20)
            run.font.color.rgb = COLOR_PRIMARY
            h.paragraph_format.space_before = Pt(14)
            h.paragraph_format.space_after = Pt(12)
        elif level == 2:
            run.font.size = Pt(16)
            run.font.color.rgb = COLOR_SECONDARY
            h.paragraph_format.space_before = Pt(12)
            h.paragraph_format.space_after = Pt(6)
        elif level == 3:
            run.font.size = Pt(14)
            run.font.color.rgb = COLOR_PRIMARY
            h.paragraph_format.space_before = Pt(10)
            h.paragraph_format.space_after = Pt(4)
        return h

    def add_p(text, indent=True, bold_prefix=None):
        p = doc.add_paragraph()
        p.paragraph_format.line_spacing = 1.25
        p.paragraph_format.space_after = Pt(6)
        if indent:
            p.paragraph_format.first_line_indent = Inches(0.4)
        if bold_prefix:
            run_b = p.add_run(bold_prefix + " ")
            run_b.bold = True
            run_b.font.name = FONT_FAMILY
            run_b.font.size = Pt(14)
            run_b.font.color.rgb = COLOR_TEXT
        append_formatted_text(p, text)
        return p

    def add_numbered_item(number_str, text, bold_prefix=None, level=0):
        p = doc.add_paragraph()
        p.paragraph_format.line_spacing = 1.2
        p.paragraph_format.space_after = Pt(4)
        p.paragraph_format.left_indent = Inches(0.45 + (level * 0.25))
        p.paragraph_format.first_line_indent = Inches(-0.25)

        r_num = p.add_run(f"{number_str} ")
        r_num.bold = True
        r_num.font.name = FONT_FAMILY
        r_num.font.size = Pt(14)
        r_num.font.color.rgb = COLOR_PRIMARY

        if bold_prefix:
            r_bp = p.add_run(bold_prefix + " ")
            r_bp.bold = True
            r_bp.font.name = FONT_FAMILY
            r_bp.font.size = Pt(14)
            r_bp.font.color.rgb = COLOR_TEXT

        append_formatted_text(p, text)
        return p

    def add_callout(text, bold_title=None):
        tbl = doc.add_table(rows=1, cols=1)
        tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
        tbl.autofit = False
        tbl.columns[0].width = Inches(6.0)
        cell = tbl.cell(0, 0)
        set_cell_background(cell, "EDF2F7")
        set_cell_margins(cell, top=130, bottom=130, left=170, right=170)
        tcPr = cell._tc.get_or_add_tcPr()
        borders = parse_xml(
            f'<w:tcBorders {nsdecls("w")}>'
            f'<w:top w:val="none"/>'
            f'<w:bottom w:val="none"/>'
            f'<w:right w:val="none"/>'
            f'<w:left w:val="single" w:sz="24" w:space="0" w:color="2B6CB0"/>'
            f'</w:tcBorders>'
        )
        tcPr.append(borders)
        p = cell.paragraphs[0]
        p.paragraph_format.space_after = Pt(0)
        p.paragraph_format.line_spacing = 1.2
        if bold_title:
            rb = p.add_run(bold_title + "\n")
            rb.bold = True
            rb.font.name = FONT_FAMILY
            rb.font.size = Pt(13)
            rb.font.color.rgb = COLOR_PRIMARY
        append_formatted_text(p, text, base_size=Pt(13))
        doc.add_paragraph().paragraph_format.space_after = Pt(4)

    def add_equation_box(formula_lines, title=None, eq_label=None, explanation=None):
        tbl = doc.add_table(rows=1, cols=1)
        tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
        tbl.autofit = False
        tbl.columns[0].width = Inches(6.0)
        cell = tbl.cell(0, 0)
        set_cell_background(cell, "F8FAFC")
        set_cell_margins(cell, top=100, bottom=100, left=160, right=160)
        tcPr = cell._tc.get_or_add_tcPr()
        borders = parse_xml(
            f'<w:tcBorders {nsdecls("w")}>'
            f'<w:top w:val="single" w:sz="6" w:space="0" w:color="CBD5E1"/>'
            f'<w:bottom w:val="single" w:sz="6" w:space="0" w:color="CBD5E1"/>'
            f'<w:left w:val="single" w:sz="20" w:space="0" w:color="2B6CB0"/>'
            f'<w:right w:val="none"/>'
            f'</w:tcBorders>'
        )
        tcPr.append(borders)
        p = cell.paragraphs[0]
        p.paragraph_format.space_after = Pt(0)
        p.paragraph_format.line_spacing = 1.25

        if title:
            rt = p.add_run(title + "\n")
            rt.bold = True
            rt.font.name = FONT_FAMILY
            rt.font.size = Pt(12)
            rt.font.color.rgb = COLOR_SECONDARY

        for idx, fl in enumerate(formula_lines):
            rf = p.add_run(fl)
            rf.bold = True
            rf.font.name = FONT_MATH
            rf.font.size = Pt(13)
            rf.font.color.rgb = COLOR_PRIMARY
            if idx < len(formula_lines) - 1:
                p.add_run("\n")

        if eq_label:
            rl = p.add_run(f"    ({eq_label})")
            rl.bold = True
            rl.font.name = FONT_FAMILY
            rl.font.size = Pt(11)
            rl.font.color.rgb = COLOR_MUTED

        if explanation:
            pe = cell.add_paragraph()
            pe.paragraph_format.space_before = Pt(4)
            pe.paragraph_format.space_after = Pt(0)
            pe.paragraph_format.line_spacing = 1.15
            append_formatted_text(pe, explanation, base_size=Pt(12), base_color=COLOR_TEXT)

        doc.add_paragraph().paragraph_format.space_after = Pt(4)

    # =========================================================================
    # ส่วนหัวเรื่องเอกสารเฉพาะบท (DOCUMENT HEADER)
    # =========================================================================
    p_meta = doc.add_paragraph()
    p_meta.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_meta.paragraph_format.space_before = Pt(20)
    p_meta.paragraph_format.space_after = Pt(4)
    r_meta = p_meta.add_run("เอกสารแนบเชิงวิชาการรายวิชา 240-318 AI&ML (Technical Appendix)")
    r_meta.font.name = FONT_FAMILY
    r_meta.font.size = Pt(13)
    r_meta.font.color.rgb = COLOR_MUTED

    p_main_title = doc.add_paragraph()
    p_main_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_main_title.paragraph_format.space_after = Pt(24)
    r_mt = p_main_title.add_run("3.4 การออกแบบและพัฒนาโมเดล Hybrid Dual-Engine\n(Model Training & Cascaded Synergy Details)")
    r_mt.bold = True
    r_mt.font.name = FONT_FAMILY
    r_mt.font.size = Pt(18)
    r_mt.font.color.rgb = COLOR_PRIMARY

    # =========================================================================
    # 3.4.1 ปรัชญาการออกแบบและสถาปัตยกรรมภาพรวม
    # =========================================================================
    add_title("3.4.1 ปรัชญาการออกแบบและสถาปัตยกรรมภาพรวม (Design Philosophy & Dual-Engine Overview)", level=2)
    add_p("การพัฒนาระบบตรวจจับความผิดปกติใน System Logs สำหรับระบบประมวลผลแบบกระจายศูนย์ระดับมหัตข้อมูล เช่น HDFS เผชิญกับความท้าทายหลักทางวิศวกรรมคือ 'ความหลากหลายของมิติความผิดปกติ (Multi-dimensional Anomaly Space)' ซึ่งไม่สามารถตรวจจับให้สมบูรณ์ได้ด้วยโมเดลประเภทใดประเภทหนึ่งเพียงลำพัง:")

    add_numbered_item("1.", "ความผิดปกติเชิงความถี่และปริมาณ (Count & Volume Outliers): เกิดจากการทำงานผิดพลาดของฮาร์ดแวร์ การเกิดลูปการเชื่อมต่อล้มเหลวซ้ำๆ (Infinite Retry Loops) หรือการโจมตีแบบปฏิเสธการให้บริการ (Log Flooding) ซึ่งส่งผลให้จำนวนครั้งของแม่พิมพ์เหตุการณ์บางประเภทพุ่งสูงขึ้นหรือลดลงอย่างผิดปกติ", bold_prefix="มิติด้านความถี่ (Frequency Dimension):")
    add_numbered_item("2.", "ความผิดปกติเชิงลำดับขั้นตอนการทำงาน (Sequential Transition & Execution Path Anomalies): เกิดจากการกระโดดข้ามขั้นตอน การสลับลำดับ หรือการขัดจังหวะของกระบวนการทำงาน (เช่น คำสั่งลบบล็อกเกิดขึ้นก่อนที่การเขียนข้อมูลจะเสร็จสิ้น) โดยที่ผลรวมความถี่ของแต่ละคำสั่งอาจยังคงเท่าเดิมทุกประการ", bold_prefix="มิติด้านลำดับเวลา (Temporal Sequence Dimension):")

    add_p("หากพึ่งพาเฉพาะโมเดลนับความถี่ (เช่น Isolation Forest) โมเดลจะมองไม่เห็นมิติเวลาและเกิด False Negatives มหาศาล ในทางตรงกันข้าม หากพึ่งพาเฉพาะโมเดลลำดับ DeepLog LSTM โครงข่ายประสาทเทียมจะมีความอ่อนไหวสูงมากต่อการสลับของเธรดการทำงานปกติ (Single-step Flukes) ส่งผลให้เกิด False Positives สูงถึง 539 บล็อก (Alert Fatigue) และหากนำสองโมเดลมารวมกันด้วยตรรกะแบบ Naive OR-Voting ยิ่งจะทำให้ False Positives ทวีความรุนแรงขึ้น")

    add_callout(
        "โครงงาน LogWatchdog จึงได้ออกแบบสถาปัตยกรรม 'Hybrid Dual-Engine with Cascaded Synergy' โดยแบ่งบทบาทหน้าที่ของโมเดลอย่างชัดเจน: ใช้ DeepLog LSTM เป็นหัวหอกด่านแรกในการสแกนลำดับขั้นตอนตลอดสาย และใช้ Isolation Forest เป็น 'Density Validator & Noise Suppressor' คอยตรวจสอบความหนาแน่นเชิงสถิติ เพื่อกรองการแจ้งเตือนพร่ำเพรื่อออกจากระบบได้อย่างแม่นยำ",
        bold_title="หลักการแกนกลางของสถาปัตยกรรม Hybrid Dual-Engine"
    )

    # =========================================================================
    # 3.4.2 การจัดเตรียมและการแปลงรูปข้อมูลเพื่อฝึกสอน
    # =========================================================================
    add_title("3.4.2 การจัดเตรียมและการแปลงรูปข้อมูลเพื่อฝึกสอน (Data Preparation & Transformation)", level=2)
    add_p("กระบวนการฝึกสอนโมเดลในระบบ LogWatchdog ได้รับการออกแบบภายใต้หลักการ Unsupervised / Semi-supervised Learning โดยมีขั้นตอนการจัดเตรียมข้อมูล 4 ขั้นตอนสำคัญ:")

    add_numbered_item("1.", "คัดกรองเฉพาะเซสชันปกติ (Normal Blocks) จำนวน 5,000 บล็อกแรกจากชุดฝึกสอนของ HDFS Log Dataset ซึ่งแปลงข้อความเป็น Event ID ลำดับตัวเลขผ่าน Drain3 Parser โดยยึดหลักการว่า AI ต้องเรียนรู้เฉพาะพฤติกรรมที่ถูกต้องสมบูรณ์ของระบบ", bold_prefix="การคัดเลือกบล็อกปกติ (Normal Sessions Extraction):")
    add_numbered_item("2.", "ในการทำงานจริง ข้อมูลที่ติดป้าย Normal อาจมีสัญญาณรบกวนหรือเหตุการณ์หายากที่เกิดขึ้นแบบบังเอิญปะปนอยู่ ระบบจึงสร้างกลไก Frequency Pruning โดยคัดกรองเฉพาะลำดับเป้าหมาย (Target Events) ที่มีความถี่เกิดขึ้นมากกว่า 5 ครั้ง เพื่อกำจัดสัญญาณรบกวนออก ป้องกันไม่ให้โมเดลจดจำความผิดปกติเป็นเรื่องปกติ (กำจัดจุดบอดที่จะนำไปสู่ False Negatives)", bold_prefix="กลไกการตัดสัญญาณรบกวน (Frequency Pruning - Option A):")
    add_numbered_item("3.", "แปลงลำดับเหตุการณ์ของแต่ละบล็อกให้เป็นเวกเตอร์ 30 มิติ (ขนาด Vocabulary = 30 แม่พิมพ์) โดยนับความถี่การปรากฏตัวของแต่ละ Event ID ภายในบล็อก ได้เป็นเมทริกซ์ความถี่ X_train_counts ขนาด (5000, 30) ชนิด float32 เพื่อใช้ฝึกสอน Isolation Forest", bold_prefix="การสร้างเวกเตอร์ความถี่ (Count Vector Transformation):")
    add_numbered_item("4.", "กำหนดขนาดหน้าต่างสไลด์ w = 3 ทำการเลื่อนหน้าต่างทีละ 1 เหตุการณ์ตลอดสายของเซสชันเพื่อสร้างคู่ข้อมูลฝึกสอน (X, y) โดย X คือลำดับเหตุการณ์ 3 ตัวก่อนหน้า [e_{t-3}, e_{t-2}, e_{t-1}] และ y คือเหตุการณ์ถัดไป e_t ได้ข้อมูลฝึกสอนทั้งสิ้น 13,109 ลำดับคู่ สำหรับป้อนให้โครงข่าย LSTM", bold_prefix="การสกัดคู่ลำดับหน้าต่างสไลด์ (Sliding Window Extraction, w=3):")

    # =========================================================================
    # 3.4.3 รายละเอียดการฝึกสอน Engine 1: Isolation Forest
    # =========================================================================
    add_title("3.4.3 รายละเอียดการฝึกสอน Engine 1: Isolation Forest (Count & Volume Engine)", level=2)
    add_p("โมเดล Isolation Forest (Brick 4A) ทำหน้าที่เป็นด่านตรวจจับความถี่และประเมินความหนาแน่นของข้อมูล มีขั้นตอนการพัฒนาและการทำงานเชิงอัลกอริทึมดังนี้:")

    add_numbered_item("1.", "กำหนด n_estimators = 100 โดยอัลกอริทึมจะสุ่มตัวอย่างข้อมูลชุดย่อย (Sub-sampling) แล้วสร้างต้นไม้การตัดสินใจ iTree แต่ละต้นด้วยการสุ่มเลือกแกนฟีเจอร์ (Event ID Dimension) และสุ่มจุดตัดแบ่ง (Split Value) ระหว่างค่าต่ำสุดและสูงสุดของฟีเจอร์นั้น ทำซ้ำจนกระทั่งจุดข้อมูลถูกตัดแยกเดี่ยวหรือต้นไม้มีความลึกถึงขีดจำกัด", bold_prefix="การสร้างโครงสร้างต้นไม้สุ่ม (iTrees Ensemble):")
    add_numbered_item("2.", "กำหนดพารามิเตอร์ contamination = 0.10 เพื่อกำหนดสัดส่วนทางสถิติสำหรับสร้างเส้นแบ่งคะแนนความผิดปกติ และตั้งค่า random_state = 42 เพื่อให้ผลลัพธ์สามารถทำซ้ำได้สมบูรณ์ (Deterministic Reproducibility)", bold_prefix="การกำหนดค่าพารามิเตอร์ Contamination:")
    add_numbered_item("3.", "เมื่อป้อนเวกเตอร์ความถี่ cv ของเซสชันทดสอบ โมเดลจะคำนวณคะแนนผ่านฟังก์ชันการตัดสินใจ decision_function(cv) ซึ่งสะท้อนระยะทางความหนาแน่นเทียบกับข้อมูลปกติที่เคยเรียนรู้:", bold_prefix="ฟังก์ชันคะแนนความหนาแน่น (Density Score Function):")

    add_equation_box(
        [
            "s(x, n) = 2^(- E(h(x)) / c(n))",
            "c(n) = 2 · (ln(n - 1) + 0.5772156649) - (2 · (n - 1) / n)",
            "Score_{iforest}(x) = - (s(x, n) - 0.5) · 2"
        ],
        title="สมการคำนวณคะแนนความผิดปกติและความหนาแน่นของ Isolation Forest",
        eq_label="สมการที่ 3.1",
        explanation="หาก Score >= 0.0 หมายถึงเซสชันนั้นตั้งอยู่ใจกลางกลุ่มข้อมูลปกติสมบูรณ์ หาก Score < 0.0 หมายถึงเริ่มมีความเบี่ยงเบนของความถี่ และหาก Score < -0.10 หมายถึงเกิดปรากฏการณ์ความถี่ระเบิดตัวรุนแรง (Volumetric Storm)"
    )

    add_numbered_item("4.", "การฝึกสอนบนเมทริกซ์ 5,000 แถวใช้เวลาเพียง 0.15 วินาทีบน CPU และการคำนวณเวกเตอร์ความถี่ในการทดสอบใช้เวลาต่ำกว่า 0.01 มิลลิวินาทีต่อบล็อก ด้วยความซับซ้อนเชิงเวลา O(n log n) ในขั้นตอนเทรน และ O(t log n) ในขั้นตอนทำนาย", bold_prefix="ประสิทธิภาพเชิงคำนวณ (Computational Efficiency):")

    # =========================================================================
    # 3.4.4 รายละเอียดการฝึกสอน Engine 2: DeepLog 2-Layer LSTM
    # =========================================================================
    add_title("3.4.4 รายละเอียดการฝึกสอน Engine 2: DeepLog 2-Layer LSTM (Sequential Engine)", level=2)
    add_p("โมเดล DeepLog LSTM (Brick 4B) ได้รับการพัฒนาด้วยเฟรมเวิร์ก PyTorch สถาปัตยกรรมโครงข่ายประสาทเทียมได้รับการปรับแต่งเชิงวิศวกรรมให้มีความกระชับ ทำงานรวดเร็ว และมีขีดความสามารถสูงสุดในการจำลองไวยากรณ์ลำดับการทำงาน:")

    add_numbered_item("1.", "สถาปัตยกรรมโครงข่ายประสาทเทียมประกอบด้วย 3 ชั้นหลัก:", bold_prefix="โครงสร้างโครงข่ายประสาทเทียม (PyTorch Architecture):")
    add_numbered_item("  1.1", "Embedding Layer: รับรหัส Event ID ขนาด Vocabulary = 30 แปลงเป็นเวกเตอร์ต่อเนื่องขนาด 32 มิติ (Embedding Dim = 32) เพื่อสร้างความสัมพันธ์เชิงความหมายระหว่างคำสั่ง", level=1)
    add_numbered_item("  1.2", "2-Layer LSTM: โครงข่าย LSTM ซ้อนกัน 2 ชั้น ขนาด Hidden State = 32 มิติ พร้อมกลไก Dropout = 0.2 ระหว่างชั้นเพื่อป้องกัน Overfitting กำหนด batch_first = True", level=1)
    add_numbered_item("  1.3", "Fully Connected Linear Output Layer: รับ Hidden State สุดท้ายขนาด 32 มิติ แปลงกลับเป็น Logits ขนาด 30 มิติ เพื่อส่งต่อเข้าสู่ฟังก์ชัน Softmax", level=1)

    add_numbered_item("2.", "การคำนวณของแต่ละเซลล์ความจำ LSTM ดำเนินการตามสมการคณิตศาสตร์อย่างเป็นทางการ:", bold_prefix="กลไกคณิตศาสตร์ระดับเซลล์ความจำ (LSTM Memory Transitions):")

    add_equation_box(
        [
            "f_t = σ(W_f · [h_{t-1}, x_t] + b_f)           (Forget Gate: ตัดข้อมูลที่ไม่จำเป็นในอดีต)",
            "i_t = σ(W_i · [h_{t-1}, x_t] + b_i)           (Input Gate: คัดเลือกข้อมูลใหม่ที่จะบันทึก)",
            "C̃_t = tanh(W_c · [h_{t-1}, x_t] + b_c)        (Candidate State: เวกเตอร์ความจำตัวเต็ง)",
            "C_t = f_t ⊙ C_{t-1} + i_t ⊙ C̃_t              (Cell Update: อัปเดตสถานะความจำหลัก)",
            "o_t = σ(W_o · [h_{t-1}, x_t] + b_o)           (Output Gate: ตัดสินใจข้อมูลที่จะส่งออก)",
            "h_t = o_t ⊙ tanh(C_t)                          (Hidden State: สถานะที่ส่งไปยังเลเยอร์ถัดไป)"
        ],
        title="สมการการเปลี่ยนสถานะของหน่วยความจำ LSTM",
        eq_label="สมการที่ 3.2",
        explanation="โดยที่ σ คือฟังก์ชัน Sigmoid (0 ถึง 1), ⊙ คือการคูณแบบ Hadamard, W และ b คือเมทริกซ์ค่าน้ำหนักและไบแอสที่ถูกปรับค่าผ่านการ Gradient Descent"
    )

    add_numbered_item("3.", "ใช้ฟังก์ชัน CrossEntropyLoss ในการวัดความแตกต่างระหว่างการแจกแจงความน่าจะเป็นที่โมเดลคาดเดากับเหตุการณ์เป้าหมายจริง y_t:", bold_prefix="ฟังก์ชันการสูญเสียและการปรับค่าน้ำหนัก (Loss Function & Optimizer):")

    add_equation_box(
        [
            "L_{CE}(z, y) = - ln( exp(z_{y}) / ∑_{j=1}^{|V|} exp(z_j) )"
        ],
        title="ฟังก์ชันการสูญเสีย Cross-Entropy Loss",
        eq_label="สมการที่ 3.3",
        explanation="โดยใช้ Adam Optimizer ที่มีอัตราการเรียนรู้ lr = 0.01 และเบต้า (β1 = 0.9, β2 = 0.999) ทำการปรับค่าน้ำหนักผ่าน Backpropagation Through Time (BPTT)"
    )

    add_numbered_item("4.", "กำหนด Batch Size = 128 และฝึกสอนทั้งสิ้น 5 รอบ (Epochs) จากการทดลองพบว่าฟังก์ชันการสูญเสียลู่เข้าสู่จุดต่ำสุดอย่างรวดเร็ว (Loss ลดลงจาก 2.85 สู่ 0.42 ภายใน 3 รอบแรก) การจำกัดที่ 5 Epochs ช่วยป้องกันภาวะ Overfitting ทำให้โมเดลมีความยืดหยุ่นต่อลำดับปกติ และใช้เวลาเทรนเพียง 3.5 วินาทีบน CPU", bold_prefix="พารามิเตอร์การฝึกสอน (Training Regimen):")
    add_numbered_item("5.", "เมื่อโมเดลคำนวณ Softmax Output จะได้เวกเตอร์ความน่าจะเป็น P(e_t = k | X) โมเดลจะคัดเลือกเหตุการณ์ที่มีความน่าจะเป็นสูงสุด K อันดับแรก (Top-K = 3) หากเหตุการณ์จริง e_t ไม่อยู่ในกลุ่ม Top-3 จะนับเป็น 1 Violation", bold_prefix="เกณฑ์การตัดสินใจ Top-K (Top-K = 3 Sensitivity):")

    # =========================================================================
    # 3.4.5 รายละเอียดการออกแบบกลไก Cascaded Synergy
    # =========================================================================
    add_title("3.4.5 รายละเอียดการออกแบบกลไก Cascaded Synergy (Master Ensemble Engine)", level=2)
    add_p("การผสานโมเดลในคลาส HybridLogDetector (Brick 4C) ได้รับการออกแบบขึ้นเพื่อแก้ปัญหาข้อจำกัดของการรวมโมเดลแบบเดิม โดยมีหลักการและการพิสูจน์เชิงตรรกะดังนี้:")

    add_numbered_item("1.", "การรวมผลลัพธ์แบบ Naive OR-Voting (P_hybrid = P_iforest ∨ P_lstm) จะทำให้ False Positive ของทั้งสองโมเดลถูกบวกทับถมกัน (FP เพิ่มจาก 502 เป็น 534+ บล็อก) ส่งผลให้ F1-Score ตกต่ำลง ในขณะที่การทำ AND-Voting (P_hybrid = P_iforest ∧ P_lstm) จะทำให้ False Negatives พุ่งสูงขึ้นและ Recall ตกฮวบ", bold_prefix="ความล้มเหลวของการรวมแบบ Naive Ensemble:")
    add_numbered_item("2.", "LogWatchdog จึงออกแบบกฎการตัดสินใจแบบลำดับขั้น 2 ระดับ (Two-Tier Cascaded Synergy Rule) โดยแบ่งการตัดสินใจออกเป็น 3 กรณีตามระดับความรุนแรง:", bold_prefix="กฎการตัดสินใจแบบ Cascaded Two-Tier Synergy:")

    add_equation_box(
        [
            "ŷ_{hybrid} = 1  (Anomaly)  เมื่อเงื่อนไขใดเงื่อนไขหนึ่งต่อไปนี้เป็นจริง:",
            "  กรณี ก (Severe Sequential Failure)   : (Violations ≥ 3) หรือ (min(P) < 0.01) หรือ (has_oov = True)",
            "  กรณี ข (Validated Sequence Anomaly)  : (Violations ≥ 1) และ (Score_{iforest} < 0.0)",
            "  กรณี ค (Severe Volumetric Storm)     : (Score_{iforest} < -0.10)",
            "ŷ_{hybrid} = 0  (Normal)    ในกรณีอื่นๆ ทั้งหมด  [ดำเนินการ Suppress False Alarm ทิ้ง]"
        ],
        title="กฎการตัดสินใจแบบ Cascaded Synergy (Two-Tier Anomaly Validation Rule)",
        eq_label="สมการที่ 3.4",
        explanation="กรณี ก: หากลำดับพังทลายรุนแรง จะฟันธงเป็น Anomaly ทันทีเพื่อรักษา Recall 100% | กรณี ข: หากลำดับผิดปกติเล็กน้อย (1-2 violations ซึ่งอาจเกิดจากการสลับเธรด) จะส่งให้ iForest ตรวจสอบ หาก iForest พบความถี่ปกติสมบูรณ์ (Score >= 0.0) ระบบจะระงับการแจ้งเตือนทิ้งทันที"
    )

    add_numbered_item("3.", "ผลลัพธ์ของการนำ iForest มาทำหน้าที่เป็น Noise Suppressor ในกรณี ข ทำให้ระบบสามารถคัดกรอง False Positives ออกไปได้ถึง 253 บล็อก (-46.9% จาก 539 เหลือเพียง 286 บล็อก) ส่งผลให้ Precision เพิ่มขึ้นเป็น 73.49% และ F1-Score ทะยานขึ้นสู่ 84.72% (+10.08% เหนือกว่า DeepLog LSTM เดียวๆ) โดยที่ Recall ยังคงสมบูรณ์แบบที่ 100.00% (793/793 เคส)", bold_prefix="ผลสำเร็จเชิงประจักษ์ของการผสานโมเดล:")

    # =========================================================================
    # 3.4.6 ตารางสรุป Hyperparameters และทรัพยากรการประมวลผล
    # =========================================================================
    add_title("3.4.6 ตารางสรุป Hyperparameters และทรัพยากรการประมวลผล (Configured Values & Compute Specs)", level=2)
    add_p("ตารางที่ 3.1 สรุปค่าพารามิเตอร์ของระบบ Hybrid Dual-Engine พร้อมรายละเอียดทรัพยากรการประมวลผล:")

    tbl_hyp = doc.add_table(rows=9, cols=3)
    tbl_hyp.alignment = WD_TABLE_ALIGNMENT.CENTER
    set_table_borders(tbl_hyp)
    h_hyp = ["โมเดล / Hyperparameter", "ค่าที่กำหนด (Configured Value)", "บทบาทและเหตุผลเชิงวิศวกรรม"]
    for j, h in enumerate(h_hyp):
        cell = tbl_hyp.cell(0, j)
        set_cell_background(cell, "2B6CB0")
        set_cell_margins(cell, top=140, bottom=140, left=140, right=140)
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run(h)
        r.bold = True
        r.font.name = FONT_FAMILY
        r.font.size = Pt(13)
        r.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)

    hyp_data = [
        ("iForest: n_estimators", "100 Isolation Trees", "สร้างความเสถียรในการประเมินคะแนนความหนาแน่น Outlier"),
        ("iForest: contamination", "0.10 (10%)", "กำหนดสัดส่วน Threshold ความผิดปกติในขั้นตอน Baseline"),
        ("iForest: Input Dimension", "30 Event Counters", "เวกเตอร์ความถี่ของแม่พิมพ์เหตุการณ์ทั้งหมดที่พบ"),
        ("LSTM: Vocabulary Size (|V|)", "30 แม่พิมพ์เหตุการณ์", "ครอบคลุมพฤติกรรมทั้งหมดของระบบไฟล์ HDFS"),
        ("LSTM: Sliding Window (w)", "3 เหตุการณ์", "จับบริบทที่กระชับ เหมาะกับช่วงสั้นของการทำงานแต่ละบล็อก"),
        ("LSTM: Architecture", "2-Layer LSTM (Hidden: 32, Embed: 32)", "โครงข่ายกะทัดรัด ประหยัดหน่วยความจำ ทำงานบน CPU ได้ลื่นไหล"),
        ("LSTM: Decision Threshold", "Top-K = 3 (Adam lr = 0.01)", "ให้ความยืดหยุ่นต่อลำดับปกติ และจับ Violation ได้ 100%"),
        ("Hybrid: Synergy Strategy", "Cascaded Synergy (Two-Tier Rule)", "IF ทำหน้าที่ Suppress False Alarms ช่วยดัน F1 พุ่งแตะ 84.72%")
    ]

    for i, row in enumerate(hyp_data):
        for j, val in enumerate(row):
            cell = tbl_hyp.cell(i + 1, j)
            bg = "EDF2F7" if i == 7 else ("F7FAFC" if i % 2 == 1 else "FFFFFF")
            set_cell_background(cell, bg)
            set_cell_margins(cell, top=100, bottom=100, left=120, right=120)
            p = cell.paragraphs[0]
            p.paragraph_format.line_spacing = 1.15
            p.paragraph_format.space_after = Pt(0)
            append_formatted_text(p, val, base_size=Pt(12), base_bold=(j == 0 or i == 7))
            if j == 0:
                p.runs[0].font.color.rgb = COLOR_PRIMARY

    p_cap2 = doc.add_paragraph()
    p_cap2.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_cap2 = p_cap2.add_run("ตารางที่ 3.1: การตั้งค่าสถาปัตยกรรมและ Hyperparameters ของโมเดล Hybrid Dual-Engine")
    r_cap2.font.name = FONT_FAMILY
    r_cap2.font.size = Pt(12)
    r_cap2.italic = True
    r_cap2.font.color.rgb = COLOR_MUTED

    # =========================================================================
    # 3.4.7 สรุปขั้นตอนการทำไปป์ไลน์ตั้งแต่ต้นจนจบ
    # =========================================================================
    add_title("3.4.7 สรุปขั้นตอนการทำไปป์ไลน์ตั้งแต่ต้นจนจบ (Step-by-Step Execution Recipe)", level=2)
    add_p("กระบวนการทำงานของสถาปัตยกรรมโมเดลในไฟล์ `src/demo_engine.py` และ `main.py` สรุปเป็นขั้นตอนการทำงาน 6 สเต็ป ดังนี้:")

    add_numbered_item("1.", "สตรีมข้อมูลบล็อกปกติ 5,000 บล็อก สกัดแม่พิมพ์คำสั่งด้วย Drain3 ได้ตารางคำศัพท์ 30 รายการ", bold_prefix="ขั้นตอนที่ 1 (Parsing & Vocab):")
    add_numbered_item("2.", "สกัด Count Matrix (5000, 30) และฝึกสอนโมเดล Isolation Forest 100 Trees บันทึกเป็น `iforest_model.pkl`", bold_prefix="ขั้นตอนที่ 2 (iForest Training):")
    add_numbered_item("3.", "สกัดคู่ลำดับ Sliding Window (w=3) จำนวน 13,109 คู่ ทำ Frequency Pruning และฝึกสอน DeepLog 2-Layer LSTM จำนวน 5 Epochs บันทึกเป็น `deeplog_option_a.pt`", bold_prefix="ขั้นตอนที่ 3 (LSTM Training):")
    add_numbered_item("4.", "ประกอบโมเดลทั้งสองเข้าด้วยกันภายใต้คลาส `HybridLogDetector` ด้วยกลยุทธ์ `strategy='synergy'`", bold_prefix="ขั้นตอนที่ 4 (Hybrid Assembly):")
    add_numbered_item("5.", "รัน High-Throughput Batch Inference บนชุดทดสอบมาตรฐาน 2,793 เซสชัน คำนวณเมตริกเปรียบเทียบทั้ง 3 รูปแบบ และบันทึกเป็น `demo_metadata.pkl` และ `demo_eval_cache.pkl`", bold_prefix="ขั้นตอนที่ 5 (Batch Evaluation & Caching):")
    add_numbered_item("6.", "ส่งต่ออ็อบเจกต์โมเดลและผลการประเมินให้ `app.py` (Streamlit Web Dashboard) และ `main.py` เพื่อแสดงผลลัพธ์และการชันสูตรเชิงลึกแบบโต้ตอบได้ทันที", bold_prefix="ขั้นตอนที่ 6 (Dashboard & Forensics Serving):")

    # บันทึกไฟล์ DOCX ชั่วคราว และแปลงเป็น ODT ด้วย LibreOffice
    os.makedirs("scratch", exist_ok=True)
    docx_path = "scratch/Section_3_4_Model_Training_generated.docx"
    odt_target = "LogWatchdog_Section_3_4_Detailed_Report.odt"

    print(f"กำลังบันทึกไฟล์ชั่วคราว {docx_path}...")
    doc.save(docx_path)
    print("บันทึก DOCX สำเร็จ กำลังแปลงเป็น .odt ด้วย LibreOffice...")

    res = subprocess.run(
        ["libreoffice", "--headless", "--convert-to", "odt", docx_path, "--outdir", "."],
        capture_output=True,
        text=True
    )
    if res.returncode != 0:
        print("เกิดข้อผิดพลาดในการแปลง:", res.stderr)
        raise RuntimeError(f"LibreOffice conversion failed: {res.stderr}")

    generated_odt = "Section_3_4_Model_Training_generated.odt"
    if os.path.exists(generated_odt):
        os.replace(generated_odt, odt_target)
        print(f"แทนที่และบันทึกไฟล์สำเร็จเป็น {odt_target}")
    else:
        print(f"ตรวจสอบไฟล์เป้าหมาย: {odt_target}")

    file_size = os.path.getsize(odt_target)
    print(f"สร้างไฟล์เสร็จสมบูรณ์: {odt_target} (ขนาด: {file_size:,} ไบต์)")

if __name__ == "__main__":
    build_section_3_4_report()
