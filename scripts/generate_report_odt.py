#!/usr/bin/env python3
"""
Script สำหรับสร้างรายงานโครงงานฉบับสมบูรณ์ (LogWatchdog Project Report)
เป็นไฟล์เอกสาร .odt (OpenDocument Text) สำหรับเปิดและแก้ไขใน LibreOffice Writer
ตามโครงร่างและข้อกำหนดของรายวิชา 240-318 AI&ML ภาควิชาวิศวกรรมคอมพิวเตอร์ ม.อ. หาดใหญ่

ปรับปรุงสถาปัตยกรรม:
1. ปรับสถาปัตยกรรมหลักสู่ Hybrid Dual-Engine (Isolation Forest + DeepLog LSTM) พร้อมกลไก Cascaded Synergy
2. ใช้ลำดับข้อที่เป็นระบบ (Numbered Items) แทนการใช้ Bullet ผสมตัวเลข
3. แก้ปัญหาการแสดงผลมาร์กดาวน์ **ตัวหนา** โดยแปลงเป็น Run.bold ใน docx โดยตรง ไร้สัญลักษณ์ ** หลุดรอด
4. ปรับสมการคณิตศาสตร์ทุกจุดให้แสดงผลด้วยสัญลักษณ์คณิตศาสตร์ที่ถูกต้องและเป็นระเบียบ สวยงามระดับวิชาการ
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

def build_report():
    doc = docx.Document()

    # ตั้งค่าขอบหน้ากระดาษตามมาตรฐานรายงาน ม.อ. (ซ้าย 1.25 นิ้ว, บน/ล่าง/ขวา 1 นิ้ว)
    for section in doc.sections:
        section.top_margin = Inches(1.0)
        section.bottom_margin = Inches(1.0)
        section.left_margin = Inches(1.25)
        section.right_margin = Inches(1.0)
        section.different_first_page_header_footer = True

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
        แล้วเพิ่มเป็น Run ใน docx อย่างถูกต้อง โดยไม่มีสัญลักษณ์ ** หรือ ` หลุดรอดเป็นข้อความดิบ
        """
        # ขั้นที่ 1: แยกด้วย inline code `...`
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
            # ขั้นที่ 2: แยกด้วย **bold**
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
                    # ขั้นที่ 3: แยกด้วย *italic* (หากมี)
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
            h.paragraph_format.space_before = Pt(10)
            h.paragraph_format.space_after = Pt(6)
        elif level == 3:
            run.font.size = Pt(14)
            run.font.color.rgb = COLOR_PRIMARY
            h.paragraph_format.space_before = Pt(8)
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
        """
        เพิ่มรายการแบบลำดับข้อ (Numbered Item) มีระยะเยื้องสวยงาม ไม่ใช้ Bullet
        """
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
        """
        แสดงบล็อกสมการคณิตศาสตร์อย่างเป็นทางการด้วย Typography ที่ประณีต
        """
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
    # หน้าปก (COVER PAGE)
    # =========================================================================
    p_cov_top = doc.add_paragraph()
    p_cov_top.paragraph_format.space_before = Pt(40)
    p_cov_top.paragraph_format.space_after = Pt(10)
    p_cov_top.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p_cov_top.add_run("รายงานโครงงานรายวิชา (Mini Project Report)")
    r.font.name = FONT_FAMILY
    r.font.size = Pt(16)
    r.font.color.rgb = COLOR_MUTED

    p_proj_th = doc.add_paragraph()
    p_proj_th.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_proj_th.paragraph_format.space_after = Pt(8)
    r = p_proj_th.add_run("LogWatchdog: ระบบตรวจจับและระบุสาเหตุความผิดปกติใน System Logs ด้วยสถาปัตยกรรม Hybrid Dual-Engine (Isolation Forest + DeepLog LSTM) พร้อมกลไก Cascaded Synergy")
    r.bold = True
    r.font.name = FONT_FAMILY
    r.font.size = Pt(17)
    r.font.color.rgb = COLOR_PRIMARY

    p_proj_en = doc.add_paragraph()
    p_proj_en.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_proj_en.paragraph_format.space_after = Pt(40)
    r = p_proj_en.add_run("LogWatchdog: Automated System Log Anomaly Detection and Root Cause Localization using Hybrid Dual-Engine Architecture (Isolation Forest + DeepLog LSTM) with Cascaded Synergy")
    r.italic = True
    r.font.name = FONT_FAMILY
    r.font.size = Pt(12)
    r.font.color.rgb = COLOR_MUTED

    p_author = doc.add_paragraph()
    p_author.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_author.paragraph_format.space_after = Pt(4)
    r = p_author.add_run("จัดทำโดย\nนายกรวิชญ์ คงคล้าย\nรหัสนักศึกษา 6710110006\nหมายเลข Section 01")
    r.font.name = FONT_FAMILY
    r.font.size = Pt(14)
    r.font.color.rgb = COLOR_TEXT

    p_advisor = doc.add_paragraph()
    p_advisor.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_advisor.paragraph_format.space_before = Pt(40)
    p_advisor.paragraph_format.space_after = Pt(40)
    r = p_advisor.add_run("เสนอ\nดร. อนันท์ ชกสุริวงค์\nดร. วรินทร โรจนกรินทร์")
    r.font.name = FONT_FAMILY
    r.font.size = Pt(14)
    r.font.color.rgb = COLOR_TEXT

    p_bottom = doc.add_paragraph()
    p_bottom.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_bottom.paragraph_format.space_before = Pt(60)
    r = p_bottom.add_run(
        "รายงานเล่มนี้เป็นส่วนหนึ่งของรายวิชา 240-318 AI&ML\n"
        "ภาคการศึกษาที่ 1 ปีการศึกษา 2569\n"
        "สาขาวิชาวิศวกรรมคอมพิวเตอร์ ภาควิชาวิศวกรรมคอมพิวเตอร์\n"
        "คณะวิศวกรรมศาสตร์ มหาวิทยาลัยสงขลานครินทร์ วิทยาเขตหาดใหญ่"
    )
    r.font.name = FONT_FAMILY
    r.font.size = Pt(14)
    r.font.color.rgb = COLOR_TEXT

    # =========================================================================
    # สารบัญ (TABLE OF CONTENTS)
    # =========================================================================
    add_title("สารบัญ (Table of Contents)", level=1, page_break=True)
    toc_items = [
        ("บทที่ 1: บทนำ (Introduction)", "1"),
        ("  1.1 ที่มาและความสำคัญของปัญหา (Background & Problem Statement)", "1"),
        ("  1.2 แนวคิดและแนวทางการแก้ปัญหา (Proposed Solution & Rationale)", "2"),
        ("  1.3 วัตถุประสงค์ของโครงงาน (Project Objectives)", "3"),
        ("  1.4 ขอบเขตของโครงงาน (Project Scope)", "3"),
        ("  1.5 ประโยชน์ที่คาดว่าจะได้รับ (Expected Benefits)", "4"),
        ("บทที่ 2: ทฤษฎี เทคโนโลยี และงานที่เกี่ยวข้อง (Background & Related Work)", "5"),
        ("  2.1 หลักการและทฤษฎีพื้นฐาน (Theoretical Background)", "5"),
        ("  2.2 งานวิจัยหรือระบบที่เกี่ยวข้อง (Related Work / Prior Art)", "8"),
        ("  2.3 เครื่องมือ ภาษา และเทคโนโลยีที่ใช้ (Tech Stack & Environment)", "10"),
        ("บทที่ 3: การออกแบบระบบและวิธีดำเนินงาน (System Design & Methodology)", "11"),
        ("  3.1 แผนภาพการทำงานของระบบ (System Workflow & Pipeline)", "11"),
        ("  3.2 สถาปัตยกรรมระบบแบบแยกส่วน 5 บล็อก (Modular Lego Architecture)", "12"),
        ("  3.3 การจัดการชุดข้อมูลและการแบ่งส่วนอย่างเคร่งครัด (Dataset & Preprocessing)", "14"),
        ("  3.4 การออกแบบและพัฒนาโมเดล Hybrid Dual-Engine (Model Training & Synergy)", "16"),
        ("  3.5 ขั้นตอนและกระบวนการทำงานของโครงการ (Implementation Timeline)", "18"),
        ("บทที่ 4: ผลการดำเนินงานและการวิเคราะห์ผล (Results & Analysis)", "19"),
        ("  4.1 ผลลัพธ์ของระบบต้นแบบ (System Implementation & Prototype)", "19"),
        ("  4.2 แผนการทดสอบและตัวชี้วัด (Testing Methodology & Evaluation Metrics)", "21"),
        ("  4.3 การวิเคราะห์ผลลัพธ์เชิงเปรียบเทียบและการตัดเสียงรบกวน (Comparative Analysis)", "22"),
        ("บทที่ 5: สรุปผล ข้อจำกัด และข้อเสนอแนะ (Conclusion & Future Work)", "26"),
        ("  5.1 สรุปผลการดำเนินงาน (Conclusion)", "26"),
        ("  5.2 ปัญหา อุปสรรค และข้อจำกัด (Challenges & Limitations)", "27"),
        ("  5.3 ข้อเสนอแนะและแนวทางการพัฒนาต่อยอด (Future Work)", "28"),
        ("เอกสารอ้างอิง (References)", "29"),
        ("ภาคผนวก (Appendices)", "31"),
    ]
    for title_text, page_num in toc_items:
        p = doc.add_paragraph()
        p.paragraph_format.line_spacing = 1.15
        p.paragraph_format.space_after = Pt(3)
        r1 = p.add_run(title_text)
        r1.font.name = FONT_FAMILY
        r1.font.size = Pt(13)
        if not title_text.startswith("  "):
            r1.bold = True
            r1.font.color.rgb = COLOR_PRIMARY
        dots_count = max(5, 75 - len(title_text) * 2)
        r_dots = p.add_run(" " + "." * dots_count + " ")
        r_dots.font.name = FONT_FAMILY
        r_dots.font.size = Pt(11)
        r_dots.font.color.rgb = COLOR_MUTED
        r2 = p.add_run(page_num)
        r2.font.name = FONT_FAMILY
        r2.font.size = Pt(13)
        r2.bold = True

    # =========================================================================
    # บทที่ 1: บทนำ (INTRODUCTION)
    # =========================================================================
    add_title("บทที่ 1: บทนำ (Introduction)", level=1, page_break=True)

    add_title("1.1 ที่มาและความสำคัญของปัญหา (Background & Problem Statement)", level=2)
    add_p("ในยุคปัจจุบัน สถาปัตยกรรมระบบสารสนเทศขององค์กรได้พัฒนาไปสู่รูปแบบระบบกระจาย (Distributed Systems), คลาวด์คอมพิวติง (Cloud Computing) และโครงสร้างพื้นฐานระดับมหัตข้อมูล (Big Data Infrastructure) เช่น Hadoop Distributed File System (HDFS), Kubernetes, และระบบ CI/CD Pipeline ที่มีความซับซ้อนอย่างยิ่ง ระบบเหล่านี้มีการทำงานพร้อมกันแบบคู่ขนาน (Concurrency) ผ่านคลัสเตอร์เซิร์ฟเวอร์นับร้อยหรือนับพันเครื่อง ซึ่งทำให้เกิดการบันทึกข้อมูลการทำงานของระบบ (System Event Logs) ในปริมาณมหาศาลระดับกิกะไบต์ไปจนถึงเทราไบต์ต่อวัน")
    add_p("System Logs ถือเป็นแหล่งข้อมูลเชิงประจักษ์ (Ground Truth) เพียงแหล่งเดียวที่บันทึกพฤติกรรมการทำงาน สถานะการรับส่งข้อมูล ตลอดจนความล้มเหลวของฮาร์ดแวร์และซอฟต์แวร์ได้อย่างละเอียด อย่างไรก็ดี การตรวจสอบและวิเคราะห์บันทึกเหตุการณ์เหล่านี้ในปัจจุบันยังคงเผชิญกับอุปสรรคและข้อจำกัดที่สำคัญ (Pain Points) 4 ประการ ดังนี้:")

    add_numbered_item("1.", "ข้อมูลมีปริมาณมหาศาลเกินขีดความสามารถของมนุษย์ (Data Volume & High Ingestion Rate): คลัสเตอร์ขนาดกลางผลิต Log นับล้านบรรทัดต่อชั่วโมง การตรวจสอบด้วยมนุษย์ (Manual Inspection) ไม่สามารถตอบสนองต่อเหตุการณ์ขัดข้องได้ทันท่วงที", bold_prefix="ข้อจำกัดด้านปริมาณข้อมูล:")
    add_numbered_item("2.", "การพึ่งพากฎที่ตายตัวและการค้นหาคำสำคัญ (Brittle Keyword Matching & Regular Expressions): แนวทางดั้งเดิมส่วนใหญ่ใช้การดักจับข้อความแจ้งเตือนเช่น `Error`, `Exception`, หรือ `Failed` ซึ่งแนวทางนี้ล้มเหลวโดยสิ้นเชิงในการตรวจจับความผิดปกติที่เกิดจาก 'ลำดับขั้นตอนการทำงานที่ผิดพลาด (Sequential Permutation or Execution Path Anomaly)' เช่น คำสั่งลบไฟล์เกิดขึ้นก่อนที่ขั้นตอนการเขียนข้อมูลจะเสร็จสิ้น แม้ว่าข้อความใน Log แต่ละบรรทัดจะเป็นคำสั่งที่ถูกต้องตามกฎไวยากรณ์และไม่มีคำว่า Error ปรากฏอยู่เลยก็ตาม", bold_prefix="ข้อจำกัดของการค้นหาแบบเดิม:")
    add_numbered_item("3.", "ภาวะแจ้งเตือนล้นเกินและผลบวกลวง (Alert Fatigue & False Alarms): ระบบตรวจจับทั่วไปมักสร้างการแจ้งเตือนพร่ำเพรื่อเมื่อเกิดความผันผวนเล็กน้อย ส่งผลให้วิศวกรดูแลระบบ (Site Reliability Engineers - SREs) เกิดความเหนื่อยล้าจากการแจ้งเตือนและละเลยการแจ้งเตือนที่วิกฤตจริง", bold_prefix="ภาวะแจ้งเตือนล้นเกิน:")
    add_numbered_item("4.", "ขาดเครื่องมือชี้เป้าสาเหตุที่แท้จริง (Lack of Root Cause Localization & Explainability): โมเดล Machine Learning หลายประเภททำหน้าที่เสร็จสิ้นเพียงการระบุว่าเซสชันนั้น 'ผิดปกติ (Anomaly)' ในลักษณะกล่องดำ (Black-box) โดยไม่สามารถระบุบรรทัดที่เกิดปัญหา (Culprit Log Line) หรือบริบทแวดล้อมได้ ทำให้กระบวนการสืบสวนและแก้ไข (Mean Time to Resolution - MTTR) ต้องใช้เวลานานนับชั่วโมงหรือนับวัน", bold_prefix="ขาดความโปร่งใสและการชี้เป้า:")

    add_p("ผลกระทบจากปัญหาดังกล่าวส่งผลกระทบโดยตรงต่อความพร้อมใช้งานของระบบ (High Availability), ความสูญเสียทางธุรกิจจาก Downtime ที่ไม่คาดคิด ตลอดจนภาระต้นทุนด้านบุคลากรไอทีที่ต้องใช้เวลาส่วนใหญ่ไปกับการค้นหาและไล่ตามหาสาเหตุของ Incident ในกองบันทึกข้อมูลขนาดมหึมา")

    add_title("1.2 แนวคิดและแนวทางการแก้ปัญหา (Proposed Solution & Rationale)", level=2)
    add_p("เพื่อแก้ไขปัญหาข้างต้นอย่างยั่งยืน โครงงานนี้จึงนำเสนอ **LogWatchdog** ระบบตรวจจับและระบุสาเหตุความผิดปกติใน System Logs ด้วยสถาปัตยกรรม **Hybrid Dual-Engine** ที่ผสานการทำงานระหว่างโมเดล 2 ชนิด ได้แก่ **Isolation Forest** (ด่านตรวจจับความถี่และปริมาณ) และ **DeepLog LSTM** (ด่านตรวจจับลำดับขั้นตอนเชิงเวลา) เข้าด้วยกันผ่านกลไก **Cascaded Synergy**")
    add_p("ในระบบคอมพิวเตอร์แบบกระจายศูนย์ ความผิดปกติใน System Logs แบ่งออกเป็น 2 มิติที่แตกต่างกันอย่างสิ้นเชิง:")
    add_numbered_item("1.", "ความผิดปกติเชิงปริมาณและความถี่ (Volumetric & Count Outliers): เช่น การเกิดลูปข้อผิดพลาดซ้ำๆ (Infinite Retry Loop), การยิงคำสั่งในปริมาณผิดปกติ (Log Storming / DDoS), หรือการที่ทรัพยากรบางตัวหายไป มิตินี้สามารถตรวจจับได้ดีเยี่ยมด้วยโมเดล Isolation Forest บนเวกเตอร์ความถี่ (Count Vectors)", bold_prefix="มิติด้านความถี่และปริมาณ:")
    add_numbered_item("2.", "ความผิดปกติเชิงลำดับขั้นตอนและเวลา (Sequential & Execution Path Anomalies): เกิดขึ้นเมื่อขั้นตอนการทำงานข้ามสเต็ป ลำดับสลับที่ หรือมีคำสั่งลัดวงจรเกิดขึ้น โดยที่ยอดรวมจำนวนครั้งของแต่ละคำสั่งยังคงเท่าเดิม มิตินี้ต้องอาศัยโครงข่ายประสาทเทียม DeepLog LSTM ในการทำความเข้าใจไวยากรณ์ลำดับการทำงาน (Sequential Workflow Modeling)", bold_prefix="มิติด้านลำดับขั้นตอน:")

    add_callout(
        "สถาปัตยกรรม Cascaded Synergy ใน LogWatchdog ทำหน้าที่ประสานพลังของทั้งสองโมเดลเข้าด้วยกัน โดย DeepLog LSTM จะทำหน้าที่เป็นด่านหน้าตรวจจับความผิดปกติเชิงลำดับ และหากพบกรณีที่ก้ำกึ่ง (1-2 violations ซึ่งอาจเกิดจากการสลับของเธรดการทำงานปกติ) ระบบจะส่งต่อให้ Isolation Forest ตรวจสอบการกระจายตัวของความถี่ หาก Isolation Forest ยืนยันว่ามีความถี่ปกติสมบูรณ์ ระบบจะทำหน้าที่เป็น Noise Suppressor ตัด False Alarm ทิ้งทันที ส่งผลให้ลด False Positive ได้เกือบครึ่งหนึ่ง และยกระดับ F1-Score ให้สูงกว่าการใช้โมเดลเดี่ยวอย่างก้าวกระโดด",
        bold_title="หลักการสำคัญของสถาปัตยกรรม Cascaded Synergy ใน LogWatchdog"
    )

    add_p("นอกจากนี้ LogWatchdog ยังได้พัฒนาต่อยอดด้วยการผสานโมดูล **DeepLogExplainer** เพื่อทำการชี้เป้าบรรทัดที่เป็นจุดเปลี่ยนสถานะผิดปกติ (Culprit Line Localization) พร้อมสกัดหน้าต่างบริบทแวดล้อม 5 บรรทัด และแจกแจงการกระจายตัวของความน่าจะเป็น (Probability Distribution) เพื่อให้ทีมวิศวกรสามารถมองเห็นเหตุผลที่โมเดลตัดสินใจได้อย่างโปร่งใส (White-box Transparency) นำไปสู่การแก้ไขปัญหาที่รวดเร็วและแม่นยำ")

    add_title("1.3 วัตถุประสงค์ของโครงงาน (Project Objectives)", level=2)
    add_p("โครงงานนี้มีวัตถุประสงค์หลักที่สามารถวัดผลได้เชิงประจักษ์ (Measurable Objectives) 5 ประการ ดังนี้:")
    add_numbered_item("1.", "เพื่อออกแบบและพัฒนาระบบสถาปัตยกรรมแบบแยกส่วน 5 บล็อก (Modular Lego Architecture) ที่สามารถสลับเปลี่ยนส่วนประกอบของ Ingestion, Log Parser, Feature Extractor, Model Core, และ Explainer ได้อย่างอิสระ", bold_prefix="สถาปัตยกรรมระบบแบบโมดูลาร์:")
    add_numbered_item("2.", "เพื่อพัฒนาโมเดล Hybrid Dual-Engine ที่ผสาน Isolation Forest และ DeepLog 2-Layer LSTM ด้วยกลไก Cascaded Synergy ให้บรรลุค่า Recall 100.00% (Zero False Negatives) และยกระดับค่า F1-Score สูงกว่าโมเดลเดี่ยวทั้งสองตัว", bold_prefix="ประสิทธิภาพการตรวจจับ:")
    add_numbered_item("3.", "เพื่อพัฒนาระบบ Root Cause Localization & Forensics Explainer ที่สามารถระบุตำแหน่งบรรทัดของ Log ที่เป็นต้นเหตุความผิดปกติได้อย่างแม่นยำ พร้อมดึงบริบทแวดล้อมเพื่อประกอบการวิเคราะห์", bold_prefix="การระบุต้นตอสาเหตุ:")
    add_numbered_item("4.", "เพื่อพัฒนาระบบเว็บแอปพลิเคชันสำหรับสาธิต (Interactive Web Demonstration Dashboard) ด้วย Streamlit และ Altair ที่รองรับการเปรียบเทียบผลลัพธ์ของโมเดล การสืบค้นเชิงนิติวิทยาศาสตร์ และการทดลองรัน Inference สด", bold_prefix="ระบบส่วนต่อประสานและสาธิต:")
    add_numbered_item("5.", "เพื่อสร้างชุดทดสอบระดับหน่วย (Unit Test Suite) ที่ครอบคลุมทุกโมดูลหลัก และมีอัตราการผ่านการทดสอบ 100% ตามมาตรฐานวิศวกรรมซอฟต์แวร์", bold_prefix="ความถูกต้องทางวิศวกรรม:")

    add_title("1.4 ขอบเขตของโครงงาน (Project Scope)", level=2)
    add_p("ขอบเขตการดำเนินงานของโครงงาน LogWatchdog กำหนดไว้ดังนี้:")
    add_numbered_item("1.", "ขอบเขตด้านชุดข้อมูล: ใช้ชุดข้อมูลบันทึกเหตุการณ์มาตรฐานระบบ HDFS จาก LogHub Benchmark (Zhu et al., ICSE 2019) ซึ่งประกอบด้วยข้อมูล Log ดิบกว่า 11.17 ล้านบรรทัด แบ่งเซสชันตาม Block ID จำนวน 575,061 บล็อก และชุดข้อมูลทดสอบ CI/CD Log สำหรับการทดสอบส่วนขยาย", bold_prefix="ชุดข้อมูลมาตรฐาน:")
    add_numbered_item("2.", "ขอบเขตด้านประเภทความผิดปกติ: ตรวจจับทั้งความผิดปกติเชิงปริมาณ (Count Outlier) และความผิดปกติเชิงลำดับขั้นตอนการทำงาน (Sequential Permutation / Step Skipping)", bold_prefix="ประเภทความผิดปกติ:")
    add_numbered_item("3.", "ขอบเขตด้านสถาปัตยกรรมโมเดล: ผสาน Isolation Forest (100 Trees บน Count Vector) ร่วมกับ DeepLog LSTM 2 ชั้น (PyTorch) บนขนาด Sliding Window เท่ากับ 3 เหตุการณ์ และเกณฑ์ตัดสินใจ Top-K (K=3)", bold_prefix="สถาปัตยกรรม AI:")
    add_numbered_item("4.", "ขอบเขตด้านระบบส่วนต่อประสาน: พัฒนาเว็บแดชบอร์ดด้วย Streamlit ที่ทำงานแบบ Local/On-Premises โดยมี 4 แท็บหลัก ได้แก่ การประเมินผลเปรียบเทียบโมเดล, นิติวิทยาศาสตร์บันทึกเหตุการณ์, สนามทดลองการอนุมานสด, และสถาปัตยกรรมระบบ", bold_prefix="ระบบส่วนติดต่อผู้ใช้:")
    add_numbered_item("5.", "ข้อจำกัดนอกขอบเขต (Out-of-Scope Limitations): โครงงานนี้ยังไม่ครอบคลุมการวิเคราะห์ความผิดปกติของค่าพารามิเตอร์ตัวเลข (Parameter Value Anomaly เช่น latency สูงแต่ลำดับยังถูก) และยังไม่รวมการ Deploy บนระบบ Distributed Stream Processing แบบ Multi-cluster (เช่น Apache Kafka)", bold_prefix="ข้อจำกัดนอกขอบเขต:")

    add_title("1.5 ประโยชน์ที่คาดว่าจะได้รับ (Expected Benefits)", level=2)
    add_p("โครงงาน LogWatchdog ก่อให้เกิดประโยชน์ทั้งในมิติทางเทคนิคและมิติการประยุกต์ใช้งานจริง:")
    add_numbered_item("1.", "ลดระยะเวลาในการกู้คืนระบบ (Reduction of MTTR): ทีมวิศวกรไม่ต้องเสียเวลาค้นหา Log ทีละบรรทัด เพราะระบบสามารถชี้เป้าบรรทัดปัญหาและดึงบริบท 5 บรรทัดแวดล้อมมาแสดงได้ทันทีในเวลาไม่ถึงวินาที", bold_prefix="ประโยชน์ต่อการปฏิบัติงาน:")
    add_numbered_item("2.", "ตัดปัญหาภาวะแจ้งเตือนล้นเกิน (Alert Fatigue Elimination): กลไก Cascaded Synergy ช่วยตัด False Positives ทิ้งได้ถึง 46.9% ทำให้การแจ้งเตือนมีความน่าเชื่อถือสูง วิศวกรสามารถตอบสนองต่อเหตุการณ์จริงได้อย่างมั่นใจ", bold_prefix="ความน่าเชื่อถือของการแจ้งเตือน:")
    add_numbered_item("3.", "ความคุ้มค่าด้านทรัพยากรคำนวณ (Computational Efficiency): โมเดลใช้เวลาในการอนุมานต่ำมาก (ระดับมิลลิวินาทีต่อบล็อก) สามารถทำงานบน CPU ทั่วไปได้โดยไม่ต้องพึ่งพาเซิร์ฟเวอร์ GPU ราคาแพง", bold_prefix="ความคุ้มค่าทางเทคนิค:")
    add_numbered_item("4.", "เป็นสถาปัตยกรรมอ้างอิงแบบเปิด (Open Modular Reference Architecture): โค้ดของระบบออกแบบเป็นโมดูลอิสระตาม Lego Concept สามารถนำไปประยุกต์ใช้กับบันทึกเหตุการณ์อื่นๆ เช่น Kubernetes Logs หรือ CI/CD Pipelines ได้ทันที", bold_prefix="ประโยชน์ทางวิชาการและการต่อยอด:")

    # =========================================================================
    # บทที่ 2: ทฤษฎี เทคโนโลยี และงานที่เกี่ยวข้อง (BACKGROUND & RELATED WORK)
    # =========================================================================
    add_title("บทที่ 2: ทฤษฎี เทคโนโลยี และงานที่เกี่ยวข้อง (Background & Related Work)", level=1, page_break=True)

    add_title("2.1 หลักการและทฤษฎีพื้นฐาน (Theoretical Background)", level=2)
    add_p("การพัฒนาระบบ LogWatchdog มีรากฐานมาจากทฤษฎีและเทคโนโลยีสำคัญ 5 ด้าน ดังนี้:")

    add_title("2.1.1 การทำเหมืองแม่พิมพ์ข้อความบันทึกเหตุการณ์ (Log Template Mining & Parsing)", level=3)
    add_p("บันทึกเหตุการณ์ของระบบคอมพิวเตอร์เป็นข้อความกึ่งโครงสร้าง (Semi-structured Text) ซึ่งประกอบด้วยส่วนคงที่ (Constant Part) ที่ถูกนิยามไว้ใน Source Code ของโปรแกรม และส่วนตัวแปร (Variable Part) ที่เปลี่ยนแปลงตามเวลาและบริบท เช่น IP Address, Timestamp, Block ID, หรือ File Size")
    add_p("ในการประมวลผลด้วย Machine Learning เราจำเป็นต้องแปลงข้อความดิบเหล่านี้ให้อยู่ในรูปของรหัสเหตุการณ์เชิงสัญลักษณ์ (Discrete Event ID) โดยใช้อัลกอริทึม Drain (He et al., IEEE ICWS 2017) ซึ่งใช้โครงสร้างต้นไม้พาร์สแบบจำกัดความลึก (Fixed-Depth Parse Tree) ร่วมกับการจับคู่ความคล้ายคลึงของโทเค็น (Token Similarity Matching) และ Regular Expression Masking เพื่อแยกส่วนตัวแปรออกเป็นสัญลักษณ์ <*> ทำให้การพาร์สบันทึกเหตุการณ์ทำได้อย่างรวดเร็วในระดับ O(1) Time Complexity ต่อบรรทัด เหมาะสำหรับงานสตรีมมิงออนไลน์")

    add_title("2.1.2 การตรวจจับความผิดปกติเชิงความหนาแน่นและปริมาณด้วย Isolation Forest", level=3)
    add_p("Isolation Forest (Liu et al., IEEE ICDM 2008) เป็นอัลกอริทึมการเรียนรู้แบบ Unsupervised ที่ออกแบบมาเพื่อตรวจจับค่าผิดปกติ (Outliers) โดยมีสมมติฐานพื้นฐานว่า ข้อมูลที่ผิดปกติจะ 'แปลกแยกและมีจำนวนน้อย' ทำให้สามารถถูกตัดแยก (Isolated) ออกจากข้อมูลปกติได้ง่ายกว่าผ่านโครงสร้างต้นไม้สุ่ม (iTrees)")
    add_p("เมื่อแปลงลำดับ Log ของแต่ละเซสชันให้อยู่ในรูปของเวกเตอร์ความถี่ (Count Vector) โมเดล Isolation Forest จะคำนวณคะแนนความผิดปกติ (Anomaly Score) จากความยาวเส้นทางเฉลี่ยของการตัดแยก:")

    add_equation_box(
        [
            "s(x, n) = 2^(- E(h(x)) / c(n))",
            "c(n) = 2 · (ln(n - 1) + 0.5772156649) - (2 · (n - 1) / n)"
        ],
        title="สมการคำนวณคะแนนความผิดปกติของ Isolation Forest",
        eq_label="สมการที่ 2.1",
        explanation="โดยที่ h(x) คือความยาวเส้นทาง (Path Length) ของจุดข้อมูล x ในต้นไม้แต่ละต้น, E(h(x)) คือค่าเฉลี่ยความยาวเส้นทาง และ c(n) คือความยาวเส้นทางเฉลี่ยของการค้นหาที่ไม่สำเร็จใน Binary Search Tree ที่มีข้อมูล n จุด หากค่า s(x, n) เข้าใกล้ 1 หมายถึงข้อมูลมีแนวโน้มเป็น Outlier สูงมาก"
    )

    add_title("2.1.3 โครงข่ายประสาทเทียมแบบหน่วยความจำระยะสั้นและยาว (Long Short-Term Memory - LSTM)", level=3)
    add_p("Recurrent Neural Networks (RNN) แบบดั้งเดิมมักประสบปัญหาการสลายตัวของความชัน (Vanishing Gradient Problem) เมื่อต้องเรียนรู้ความสัมพันธ์ของข้อมูลลำดับที่ยาว Hochreiter & Schmidhuber (1997) จึงได้เสนอสถาปัตยกรรม LSTM ซึ่งประกอบด้วยหน่วยเซลล์ความจำ (Memory Cell) และกลไกประตูควบคุม 3 ชนิด ดังแสดงในสมการต่อไปนี้:")

    add_equation_box(
        [
            "f_t = σ(W_f · [h_{t-1}, x_t] + b_f)          (Forget Gate)",
            "i_t = σ(W_i · [h_{t-1}, x_t] + b_i)          (Input Gate)",
            "C̃_t = tanh(W_c · [h_{t-1}, x_t] + b_c)       (Candidate Memory)",
            "C_t = f_t ⊙ C_{t-1} + i_t ⊙ C̃_t             (Cell State Update)",
            "o_t = σ(W_o · [h_{t-1}, x_t] + b_o)          (Output Gate)",
            "h_t = o_t ⊙ tanh(C_t)                         (Hidden State)"
        ],
        title="สมการกลไกการทำงานของหน่วยความจำ LSTM (Memory Cell Transitions)",
        eq_label="สมการที่ 2.2",
        explanation="โดยที่ σ คือฟังก์ชัน Sigmoid Activation, ⊙ คือการคูณเชิงสมาชิก (Hadamard Product), W และ b คือเมทริกซ์น้ำหนักและไบแอสของแต่ละประตู ด้วยโครงสร้างนี้ LSTM จึงมีความสามารถในการรักษาข้อมูลบริบทในอดีตและตรวจจับการสลับลำดับได้อย่างแม่นยำ"
    )

    add_title("2.1.4 การทำนายโทเค็นถัดไปและเกณฑ์การตัดสินใจ Top-K (Next-Token Prediction & Top-K Rule)", level=3)
    add_p("ตามแนวคิดของ DeepLog (Du et al., 2017) เมื่อกำหนดลำดับเหตุการณ์ในอดีตจำนวน w ตัวแทนด้วยเวกเตอร์ X = [e_{t-w}, e_{t-w+1}, ..., e_{t-1}] เวกเตอร์เหล่านี้จะถูกส่งผ่านชั้น Embedding และ LSTM เพื่อคำนวณเวกเตอร์สถานะ h_{t-1} จากนั้นจะถูกส่งผ่านชั้น Fully Connected Layer และฟังก์ชัน Softmax เพื่อแปลงเป็นความน่าจะเป็นของเหตุการณ์ถัดไป P(e_t = k | X) เหนือเซตของแม่พิมพ์ทั้งหมด V:")

    add_equation_box(
        [
            "P(e_t = k | X) = exp(z_k) / ∑_{j=1}^{|V|} exp(z_j)"
        ],
        title="สมการการแจกแจงความน่าจะเป็นของเหตุการณ์ถัดไป (Softmax Distribution)",
        eq_label="สมการที่ 2.3",
        explanation="เกณฑ์การตัดสินใจ (Top-K Decision Rule): โมเดลจะเรียงลำดับเหตุการณ์ที่มีความน่าจะเป็นสูงสุด K อันดับแรก หากเหตุการณ์จริง e_t ไม่อยู่ในกลุ่ม Top-K ดังกล่าว ลำดับ ณ จุดนั้นจะถูกบันทึกว่าเกิด Sequential Violation"
    )

    add_title("2.1.5 สถาปัตยกรรม Cascaded Synergy Ensemble (การผสานโมเดลแบบลดเสียงรบกวน)", level=3)
    add_p("จุดอ่อนสำคัญของ DeepLog LSTM เดี่ยวๆ ในทางปฏิบัติ คือ 'ความอ่อนไหวเกินไปต่อความผันผวนระดับบรรทัดเดียว (Single-step Flukes)' ซึ่งมักเกิดจากการสลับของเธรดในระบบแบบกระจายศูนย์ ทำให้เกิด False Positive สูง หากใช้การรวมโมเดลแบบ Naive OR-Voting ยิ่งจะทำให้ False Positive เพิ่มขึ้น LogWatchdog จึงนำเสนอกฎการตัดสินใจแบบ **Cascaded Synergy** ดังสมการที่ 2.4:")

    add_equation_box(
        [
            "ŷ_{hybrid} = 1  (Anomaly)  เมื่อเงื่อนไขใดเงื่อนไขหนึ่งเป็นจริง:",
            "  1. (Severe Sequential Failure)  : (Violations ≥ 3) หรือ (min(P) < 0.01) หรือ (has_oov = True)",
            "  2. (Validated Sequence Anomaly) : (Violations ≥ 1) และ (s_{if} < 0.0)",
            "  3. (Volumetric Storm / DDoS)    : (s_{if} < -0.10)",
            "ŷ_{hybrid} = 0  (Normal)   ในกรณีอื่นๆ ทั้งหมด  [กรอง False Alarm ทิ้ง]"
        ],
        title="กฎการตัดสินใจแบบ Cascaded Synergy (Two-Tier Anomaly Validation Rule)",
        eq_label="สมการที่ 2.4",
        explanation="กลไกนี้ทำให้ Isolation Forest มีหน้าที่สำคัญทางสถาปัตยกรรม คือการเป็น 'Density Validator & Noise Suppressor' ที่คอยกลั่นกรองข้อผิดพลาดเชิงลำดับขนาดเล็กของ LSTM หากความถี่โดยรวมยังปกติสมบูรณ์ จะช่วยตัด False Positive ทิ้งได้ในทันที"
    )

    add_title("2.2 งานวิจัยหรือระบบที่เกี่ยวข้อง (Related Work / Prior Art)", level=2)
    add_p("การตรวจจับความผิดปกติใน System Logs มีการพัฒนาอย่างต่อเนื่องในแวดวงวิชาการ โดยสามารถเปรียบเทียบแนวทางสำคัญได้ตามตารางที่ 2.1:")

    tbl_rel = doc.add_table(rows=5, cols=4)
    tbl_rel.alignment = WD_TABLE_ALIGNMENT.CENTER
    set_table_borders(tbl_rel)
    headers = ["ระบบ / โมเดล", "หลักการทำงาน", "จุดเด่น (Strengths)", "จุดด้อย / ช่องว่าง (Gaps)"]
    for j, h in enumerate(headers):
        cell = tbl_rel.cell(0, j)
        set_cell_background(cell, "2B6CB0")
        set_cell_margins(cell, top=140, bottom=140, left=140, right=140)
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run(h)
        r.bold = True
        r.font.name = FONT_FAMILY
        r.font.size = Pt(13)
        r.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)

    rel_data = [
        ("Keyword & Regex Search", "ค้นหาคำว่า Error, Exception, Fail", "รวดเร็ว ใช้ง่าย ไม่ต้องฝึกโมเดล", "ไม่เข้าใจลำดับขั้นตอน ตรวจไม่พบลำดับกระโดดข้าม มี False Positive สูง"),
        ("Isolation Forest (Count Vector)", "นับความถี่ของ Log Events ในแต่ละเซสชัน", "ทำงานเร็ว ใช้ทรัพยากรน้อย ตรวจจับ Volume Spike ได้ดี", "สูญเสียข้อมูลลำดับเวลา (Temporal Order) ทำให้เกิด False Negatives สูงถึง 569 บล็อก"),
        ("DeepLog LSTM (Du et al., 2017)", "ใช้ LSTM ทำนายลำดับ Token ถัดไป", "จับความผิดปกติของ Execution Path ได้ Recall 100%", "เกิด Alert Fatigue สูงจาก Single-step Flukes (FP สูงถึง 539 บล็อก) และไม่มีโมดูลอธิบายสาเหตุ"),
        ("LogWatchdog: Hybrid Synergy (โครงงานนี้)", "ผสาน iForest (Count) + DeepLog (Seq) ด้วย Cascaded Synergy + DeepLogExplainer", "F1 พุ่งแตะ 84.72% (+10.08%), ลด FP ลง 46.9%, คง Recall 100%, ชี้เป้าบรรทัดปัญหาแบบ White-box", "ยังไม่ครอบคลุมค่าพารามิเตอร์ตัวเลข (กำลังพัฒนาในเฟสถัดไป)")
    ]

    for i, row in enumerate(rel_data):
        for j, val in enumerate(row):
            cell = tbl_rel.cell(i + 1, j)
            bg = "EDF2F7" if i == 3 else ("F7FAFC" if i % 2 == 1 else "FFFFFF")
            set_cell_background(cell, bg)
            set_cell_margins(cell, top=100, bottom=100, left=120, right=120)
            p = cell.paragraphs[0]
            p.paragraph_format.line_spacing = 1.15
            p.paragraph_format.space_after = Pt(0)
            append_formatted_text(p, val, base_size=Pt(12), base_bold=(j == 0))
            if j == 0:
                p.runs[0].font.color.rgb = COLOR_PRIMARY

    p_cap = doc.add_paragraph()
    p_cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_cap = p_cap.add_run("ตารางที่ 2.1: การเปรียบเทียบจุดเด่นและข้อจำกัดระหว่างระบบเดิมกับ LogWatchdog Hybrid Dual-Engine")
    r_cap.font.name = FONT_FAMILY
    r_cap.font.size = Pt(12)
    r_cap.italic = True
    r_cap.font.color.rgb = COLOR_MUTED

    add_p("จากตารางข้างต้น จะเห็นได้ว่า LogWatchdog ได้เข้ามาเติมเต็มช่องว่างทางวิชาการและการนำไปใช้จริง โดยไม่เพียงแต่นำอัลกอริทึม DeepLog มา Implement เท่านั้น แต่ยังแก้ปัญหา Alert Fatigue ด้วยการนำ Isolation Forest มาทำหน้าที่เป็น Density Validator เสริมแรง ทำให้ประสิทธิภาพก้าวกระโดดขึ้นอย่างแท้จริง")

    add_title("2.3 เครื่องมือ ภาษา และเทคโนโลยีที่ใช้ (Tech Stack & Environment)", level=2)
    add_p("ระบบ LogWatchdog ได้รับการพัฒนาภายใต้สภาพแวดล้อมระบบปฏิบัติการ Linux โดยเลือกใช้เครื่องมือมาตรฐานสากล 6 ด้าน ดังนี้:")
    add_numbered_item("1.", "ภาษาโปรแกรมมิ่งหลัก: Python 3.14.7 ทำหน้าที่ขับเคลื่อนทั้งระบบไปป์ไลน์ตั้งแต่ Data Loading, Preprocessing, Neural Network จนถึง Web UI", bold_prefix="ภาษาโปรแกรม:")
    add_numbered_item("2.", "เฟรมเวิร์กการเรียนรู้เชิงลึก (Deep Learning Framework): PyTorch 2.x ใช้สำหรับการสร้างสถาปัตยกรรมโครงข่ายประสาทเทียม 2-Layer LSTM, การฝึกสอนโมเดล, และการทำ Real-time Inference", bold_prefix="โครงข่ายประสาทเทียม:")
    add_numbered_item("3.", "โมเดลความหนาแน่นและสถิติ (Scikit-Learn): IsolationForest Model สำหรับการสร้างด่านตรวจจับความถี่และกรองสัญญาณรบกวน", bold_prefix="การเรียนรู้ของเครื่อง:")
    add_numbered_item("4.", "เหมืองข้อมูลบันทึกเหตุการณ์ (Log Template Miner): Drain3 (IBM Research) ปรับแต่ง Regex สำหรับการมาสก์ IP, Block ID, และตัวเลขลงในรูปแบบโทเค็นสัญลักษณ์", bold_prefix="เครื่องมือพาร์สข้อมูล:")
    add_numbered_item("5.", "ระบบจัดการข้อมูลประสิทธิภาพสูง (Data Handling): Pandas, NumPy, และ PyArrow (Apache Parquet) สำหรับการอ่านและประมวลผลชุดข้อมูลขนาดใหญ่แบบ Columnar Storage ที่ลดการใช้หน่วยความจำลงกว่า 80%", bold_prefix="ระบบจัดการข้อมูล:")
    add_numbered_item("6.", "ส่วนติดต่อผู้ใช้และการทดสอบ (UI & QA): Streamlit และ Altair 6 ในการสร้างแดชบอร์ดเชิงโต้ตอบ พร้อม PyTest ในการรันชุดทดสอบระดับหน่วยครอบคลุม 37 กรณีทดสอบ", bold_prefix="เว็บส่วนต่อประสานและการทดสอบ:")

    # =========================================================================
    # บทที่ 3: การออกแบบระบบและวิธีดำเนินงาน (SYSTEM DESIGN & METHODOLOGY)
    # =========================================================================
    add_title("บทที่ 3: การออกแบบระบบและวิธีดำเนินงาน (System Design & Methodology)", level=1, page_break=True)

    add_title("3.1 แผนภาพการทำงานของระบบ (System Workflow & Pipeline)", level=2)
    add_p("การทำงานของระบบ LogWatchdog ตั้งแต่รับข้อมูลนำเข้าจนกระทั่งส่งออกผลการวิเคราะห์ทางนิติวิทยาศาสตร์ ประกอบด้วยกระบวนการต่อเนื่อง 5 ขั้นตอนหลัก ดังแสดงในภาพรวมกระบวนการ:")
    add_callout(
        "[1. Ingestion Engine]   -> อ่าน Raw Log จาก HDFS หรือ CI/CD Pipelines\n"
        "           |\n"
        "[2. Log Parser]         -> สกัด Block ID และแปลงข้อความเป็นแม่พิมพ์ Event E0-E29 ด้วย Drain3\n"
        "           |\n"
        "[3. Feature Engine]     -> แยกสกัดเป็น 2 สายขนานกัน:\n"
        "                           - สายที่ A: Count Vector (มิติความถี่ 30 มิติ)\n"
        "                           - สายที่ B: Sliding Window Sequences (w=3) [e1, e2, e3]\n"
        "           |\n"
        "[4. Hybrid Dual-Engine] -> ประมวลผลร่วม 2 ด่านด้วย Cascaded Synergy Rule:\n"
        "                           - ด่าน 1: DeepLog 2-Layer LSTM ตรวจลำดับเวลา\n"
        "                           - ด่าน 2: Isolation Forest ยืนยันความหนาแน่นและตัด False Alarms\n"
        "           |\n"
        "[5. Explainer & UI]     -> หากพบ Incident ส่งต่อให้ DeepLogExplainer ชี้เป้าบรรทัดปัญหา แสดงผลบน Web UI",
        bold_title="ภาพรวมกระบวนการทำงานแบบ Hybrid Dual-Engine (End-to-End Pipeline Workflow)"
    )

    add_title("3.2 สถาปัตยกรรมระบบแบบแยกส่วน 5 บล็อก (Modular Lego Architecture)", level=2)
    add_p("เพื่อให้ระบบมีความยืดหยุ่นสูง รองรับการขยายตัว และง่ายต่อการทดสอบ LogWatchdog จึงถูกออกแบบภายใต้หลักการสถาปัตยกรรมแบบตัวต่อเลโก้ 5 บล็อกอิสระ:")

    add_numbered_item("1.", "ทำหน้าที่เชื่อมต่อและสตรีมข้อมูลบันทึกเหตุการณ์จากแหล่งกำเนิดต่างๆ เช่น HDFS Loader สำหรับล็อกระบบไฟล์แบบกระจายศูนย์ และ GitHub Actions Loader สำหรับล็อกกระบวนการ CI/CD มีอินเทอร์เฟซมาตรฐาน `load_lines()` ที่คืนค่าเป็น Generator", bold_prefix="Block 1: Ingestion Engine —")
    add_numbered_item("2.", "ทำหน้าที่แปลงข้อความ Log กึ่งโครงสร้างให้เป็น Structured Log Events โดยใช้ Drain3 Template Miner ซึ่งมีการสร้างตาราง Parse Tree และการมาสก์ค่าคงที่ ทำให้ได้คู่ของ (Event ID, Template String) ส่งต่อให้บล็อกถัดไป", bold_prefix="Block 2: Log Parser —")
    add_numbered_item("3.", "ทำหน้าที่สกัดฟีเจอร์ออกเป็น 2 มิติ คือ เวกเตอร์ความถี่ (Count Vectors) และ เวกเตอร์ลำดับเวลา (Sliding Window, w=3) พร้อมระบบ Pad โทเค็น", bold_prefix="Block 3: Feature Engine —")
    add_numbered_item("4.", "หัวใจการประมวลผลอัจฉริยะแบบคู่ขนาน ประกอบด้วย 3 ส่วนย่อย:", bold_prefix="Block 4: Hybrid Dual-Engine AI Core —")
    add_numbered_item("  4.1", "Brick 4A (Isolation Forest): โมเดลต้นไม้ 100 ต้น ทำหน้าที่เป็น First-line Gatekeeper ตรวจจับความผิดปกติของปริมาณและเป็น Density Validator", level=1)
    add_numbered_item("  4.2", "Brick 4B (DeepLog LSTM): โครงข่ายประสาทเทียม 2 ชั้น (Embedding 32, Hidden 32) ทำหน้าที่ตรวจจับไวยากรณ์ลำดับการทำงาน", level=1)
    add_numbered_item("  4.3", "Brick 4C (HybridLogDetector): กลไกตัดสินใจแบบ Cascaded Synergy ที่ผสานผลลัพธ์ของ 4A และ 4B เพื่อตัด False Positive", level=1)
    add_numbered_item("5.", "ทำหน้าที่วิเคราะห์เชิงลึกเมื่อเกิด Anomaly โดย `DeepLogExplainer` จะทำการคำนวณย้อนกลับหา Culprit Step, สกัด Log Context Window 5 บรรทัด, และส่งออกรายงาน Incident พร้อมนำเสนอผ่าน Streamlit Interactive Dashboard", bold_prefix="Block 5: Explainer & Reporting —")

    add_title("3.3 การจัดการชุดข้อมูลและการแบ่งส่วนอย่างเคร่งครัด (Dataset & Preprocessing)", level=2)
    add_p("ชุดข้อมูลที่นำมาใช้ในการวิจัยและทดสอบระบบคือ HDFS Log Dataset จากคลัง LogHub Benchmark (Zhu et al., ICSE 2019) ซึ่งมีขนาด 11,175,629 บรรทัดดิบ รวม 575,061 บล็อกข้อมูล")
    add_p("เพื่อป้องกันปัญหาการรั่วไหลของข้อมูล (Data Leakage) อย่างเด็ดขาด ระบบได้แบ่งข้อมูลออกเป็น 3 ชุดอิสระ:")
    add_numbered_item("1.", "ชุดฝึกสอน (Training Set): คัดเฉพาะเซสชันปกติ (Normal Sessions) จำนวน 5,000 บล็อก สำหรับฝึกสอนทั้ง LSTM และ Isolation Forest ให้เรียนรู้เฉพาะพฤติกรรมที่ถูกต้องสมบูรณ์", bold_prefix="Training Set:")
    add_numbered_item("2.", "ชุดทดสอบมาตรฐาน (Evaluation Benchmark): ใช้ประเมินประสิทธิภาพเชิงตัวเลข ประกอบด้วยข้อมูล 2,793 เซสชัน (Normal 2,000 บล็อก และ Ground-Truth Anomaly 793 บล็อก) ซึ่งตัดปัญหาโทเค็นแปลกปลอม (Zero-OOV) เพื่อวัดประสิทธิภาพการสลับลำดับอย่างแท้จริง", bold_prefix="Test Benchmark:")
    add_numbered_item("3.", "ชุดข้อมูลสาธิตบริสุทธิ์ (Holdout Validation Showcase): คัดเลือก 3 กรณีศึกษาที่ระบบไม่เคยเห็นมาก่อนในขั้นตอนฝึกหรือทดสอบ ได้แก่ Nominal Lifecycle, Hardware I/O Failure, และ Sequential Permutation เพื่อใช้สาธิตบนหน้าเว็บ", bold_prefix="Holdout Showcase:")

    add_title("3.4 การออกแบบและพัฒนาโมเดล Hybrid Dual-Engine (Model Training & Synergy)", level=2)
    add_p("การตั้งค่าสถาปัตยกรรมและ Hyperparameters ของโมเดลทั้งสองใน LogWatchdog แสดงในตารางที่ 3.1:")

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

    add_title("3.5 ขั้นตอนและกระบวนการทำงานของโครงการ (Implementation Timeline)", level=2)
    add_p("การพัฒนาโครงการ LogWatchdog ดำเนินการตามระเบียบวิธีวิศวกรรมซอฟต์แวร์แบบส่งมอบคุณค่าเป็นรอบ (Milestone-driven Agile Development) 4 ระยะหลัก ดังนี้:")
    add_numbered_item("1.", "Milestone 1 (สัปดาห์ที่ 1-2): การสำรวจปัญหา สกัดชุดข้อมูล HDFS LogHub พัฒนา Block 1 (Ingestion) และ Block 2 (Drain3 Parser) พร้อมเขียน Unit Tests รองรับ", bold_prefix="สำรวจและวางสถาปัตยกรรม:")
    add_numbered_item("2.", "Milestone 2 (สัปดาห์ที่ 3-4): พัฒนา Block 3 และ Block 4 (iForest + DeepLog LSTM บน PyTorch) ฝึกสอนโมเดลบนข้อมูลปกติ และทดสอบ Baseline", bold_prefix="พัฒนาโมเดล AI Core:")
    add_numbered_item("3.", "Milestone 3 (สัปดาห์ที่ 5-6): ค้นพบปัญหา Alert Fatigue ของ LSTM จึงออกแบบสถาปัตยกรรม Cascaded Synergy เพื่อให้ iForest เป็น Noise Filter จนดัน F1 พุ่งแตะ 84.72% สำเร็จ", bold_prefix="พัฒนากลไก Cascaded Synergy:")
    add_numbered_item("4.", "Milestone 4 (สัปดาห์ที่ 7-8): พัฒนา Streamlit Web Dashboard ทั้ง 4 แท็บ ทดสอบ Unit Tests ครบ 37 ข้อ (100% Pass) และจัดทำเอกสารรายงานฉบับสมบูรณ์", bold_prefix="เว็บแดชบอร์ดและการส่งมอบ:")

    # =========================================================================
    # บทที่ 4: ผลการดำเนินงานและการวิเคราะห์ผล (RESULTS & ANALYSIS)
    # =========================================================================
    add_title("บทที่ 4: ผลการดำเนินงานและการวิเคราะห์ผล (Results & Analysis)", level=1, page_break=True)

    add_title("4.1 ผลลัพธ์ของระบบต้นแบบ (System Implementation & Prototype)", level=2)
    add_p("ระบบต้นแบบ LogWatchdog ได้รับการพัฒนาเสร็จสมบูรณ์และเปิดใช้งานผ่าน Web Application Dashboard (Streamlit & Altair) ซึ่งแบ่งการทำงานออกเป็น 4 แท็บสำคัญ:")
    add_numbered_item("1.", "แสดงการเปรียบเทียบประสิทธิภาพเชิงสถิติของทั้ง 3 โมเดล (Isolation Forest, DeepLog LSTM, และ Hybrid Cascaded Synergy) มีตาราง Benchmark, กราฟเปรียบเทียบ, Confusion Matrix แบบ Side-by-Side และการ์ดแสดงจำนวน False Alarms ที่ IF ช่วยกรองออกได้ถึง 253 บล็อก", bold_prefix="Tab 1: Comparative Model Evaluation —")
    add_numbered_item("2.", "สืบสวนเชิงลึกระดับรายเซสชัน รองรับทั้งการสุ่มตรวจใน Benchmark 2,793 บล็อก และโหมด 3 Demo Showcase โดยแสดงผลการตัดสินใจของทั้ง 3 โมเดลพร้อมกัน ไฮไลต์บรรทัดต้นเหตุ (Culprit Line) ด้วยสีแดงสด และพล็อตแท่งแจกแจงความน่าจะเป็น Top-10 Softmax", bold_prefix="Tab 2: Incident Forensics (Dual-Engine) —")
    add_numbered_item("3.", "สนามทดลองการอนุมานแบบสด ผู้ใช้สามารถพิมพ์หรือเลือกตัวเลข Event ID เพื่อดูการตัดสินใจของทั้งสองเครื่องยนต์ พร้อมกลไกตรวจจับและถอดรหัสข้อความแบบ Real-time", bold_prefix="Tab 3: Live Inference Playground —")
    add_numbered_item("4.", "นำเสนอแผนผังสถาปัตยกรรมตัวต่อเลโก้ 5 บล็อก พร้อมการอ้างอิงเปเปอร์วิชาการหลัก (Du et al., He et al., Liu et al., Zhu et al.)", bold_prefix="Tab 4: System Architecture —")

    add_title("4.2 แผนการทดสอบและตัวชี้วัด (Testing Methodology & Evaluation Metrics)", level=2)
    add_p("การประเมินผลระบบแบ่งออกเป็น 2 ด้านอย่างชัดเจน:")
    add_numbered_item("1.", "ดำเนินการผ่าน PyTest Framework ครอบคลุมทั้งสิ้น 37 กรณีทดสอบ ใน 11 โมดูลหลัก ได้แก่ Ingestion Loader, Drain Parser, Sequence Extractor, Count Vectorizer, DeepLog Network, Isolation Forest, Hybrid Detector, Explainer Localization, Incident Reporter, Demo Engine, และ CI/CD Benchmark ผลการทดสอบปรากฏว่า **ผ่านเกณฑ์ 100% (37 passed in 4.05s)**", bold_prefix="การทดสอบด้านคุณภาพซอฟต์แวร์ (QA):")
    add_numbered_item("2.", "วัดผลบนชุดทดสอบมาตรฐาน HDFS Test Benchmark จำนวน 2,793 เซสชัน (Normal 2,000 บล็อก และ Anomaly 793 บล็อก) โดยใช้ตัวชี้วัดมาตรฐานสากล ได้แก่ Accuracy, Precision, Recall, และ F1-Score ร่วมกับเมตริก False Alarm Reduction Rate", bold_prefix="การทดสอบด้าน Machine Learning:")

    add_title("4.3 การวิเคราะห์ผลลัพธ์เชิงเปรียบเทียบและการตัดเสียงรบกวน (Comparative Analysis)", level=2)

    add_title("4.3.1 ผลการทดสอบเชิงปริมาณ (Quantitative Performance Evaluation)", level=3)
    add_p("ผลการประเมินประสิทธิภาพบนชุดทดสอบมาตรฐาน HDFS จำนวน 2,793 เซสชัน เปรียบเทียบระหว่างโมเดลเดี่ยวและการใช้งานแบบ Hybrid Cascaded Synergy แสดงในตารางที่ 4.1:")

    tbl_res = doc.add_table(rows=4, cols=8)
    tbl_res.alignment = WD_TABLE_ALIGNMENT.CENTER
    set_table_borders(tbl_res)
    h_res = ["โมเดล / กลยุทธ์", "มิติที่ตรวจสอบ", "Recall", "Precision", "F1-Score", "Accuracy", "FP", "FN"]
    for j, h in enumerate(h_res):
        cell = tbl_res.cell(0, j)
        set_cell_background(cell, "2B6CB0")
        set_cell_margins(cell, top=140, bottom=140, left=100, right=100)
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run(h)
        r.bold = True
        r.font.name = FONT_FAMILY
        r.font.size = Pt(12)
        r.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)

    res_data = [
        ("🌲 Isolation Forest", "Count / Frequency", "28.25%", "55.72%", "37.49%", "73.25%", "178", "569"),
        ("🧠 DeepLog LSTM", "Sequential Order", "100.00%", "59.53%", "74.64%", "80.70%", "539", "0"),
        ("🛡️ Hybrid (Cascaded Synergy)", "Dual-Engine (Cascaded)", "100.00%", "73.49%", "84.72%", "89.76%", "286", "0")
    ]

    for i, row in enumerate(res_data):
        for j, val in enumerate(row):
            cell = tbl_res.cell(i + 1, j)
            bg = "EDF2F7" if i == 2 else ("F7FAFC" if i % 2 == 1 else "FFFFFF")
            set_cell_background(cell, bg)
            set_cell_margins(cell, top=100, bottom=100, left=100, right=100)
            p = cell.paragraphs[0]
            p.paragraph_format.line_spacing = 1.15
            p.paragraph_format.space_after = Pt(0)
            if j in [2, 3, 4, 5, 6, 7]:
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            append_formatted_text(p, val, base_size=Pt(12), base_bold=(i == 2 or j == 0))
            if i == 2:
                p.runs[0].font.color.rgb = COLOR_PRIMARY

    p_cap3 = doc.add_paragraph()
    p_cap3.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_cap3 = p_cap3.add_run("ตารางที่ 4.1: การเปรียบเทียบผลลัพธ์ประสิทธิภาพระหว่างโมเดลเดี่ยวกับ Hybrid Cascaded Synergy บนชุดทดสอบ HDFS (N = 2,793 Sessions)")
    r_cap3.font.name = FONT_FAMILY
    r_cap3.font.size = Pt(12)
    r_cap3.italic = True
    r_cap3.font.color.rgb = COLOR_MUTED

    add_p("จากผลการทดลองในตารางที่ 4.1 สามารถวิเคราะห์เชิงประจักษ์ได้ 3 ประเด็นสำคัญ:")
    add_numbered_item("1.", "Isolation Forest เดี่ยวๆ พลาดเหตุการณ์ผิดปกติไปถึง 569 บล็อก (FN = 569, Recall 28.25%) เนื่องจากความผิดปกติใน HDFS เป็นการสลับขั้นตอน (Sequential Permutation) ที่จำนวนครั้งของคำสั่งยังเท่าเดิม", bold_prefix="ข้อจำกัดของ Isolation Forest เดี่ยวๆ:")
    add_numbered_item("2.", "DeepLog LSTM เดี่ยวๆ สามารถจับเหตุการณ์ผิดปกติได้ครบทุกบล็อก (Recall 100.00%, FN = 0) แต่มีจุดอ่อนคือ False Positive สูงถึง 539 บล็อก เนื่องจากความผันผวนระดับบรรทัดเดียว (Single-step Fluke) ส่งผลให้ F1-Score อยู่ที่ 74.64%", bold_prefix="จุดเด่นและจุดอ่อนของ DeepLog LSTM เดี่ยวๆ:")
    add_numbered_item("3.", "เมื่อนำทั้งสองโมเดลมาผสานกันด้วยกลไก Cascaded Synergy: Isolation Forest ทำหน้าที่เป็น Noise Suppressor กรอง False Positive ออกไปได้ถึง 253 บล็อก (ลดลง 46.9% จาก 539 เหลือ 286 บล็อก) ทำให้ค่า Precision พุ่งขึ้นเป็น 73.49% และ F1-Score ทะยานขึ้นสู่ 84.72% (เพิ่มขึ้น +10.08% เหนือกว่า LSTM) โดยยังคงรักษา Recall ที่ 100.00% ไว้ได้อย่างสมบูรณ์แบบ", bold_prefix="ความสำเร็จของกลไก Cascaded Synergy:")

    add_title("4.3.2 รายละเอียดเมทริกซ์ความสับสนเคียงข้างกัน (Side-by-Side Confusion Matrices)", level=3)
    add_p("ตารางที่ 4.2 แสดงการแจกแจงเมทริกซ์ความสับสน (Confusion Matrix) เปรียบเทียบทั้ง 3 รูปแบบ:")

    tbl_cm = doc.add_table(rows=4, cols=5)
    tbl_cm.alignment = WD_TABLE_ALIGNMENT.CENTER
    set_table_borders(tbl_cm)
    h_cm = ["โมเดล", "True Positive (TP)", "False Positive (FP)", "True Negative (TN)", "False Negative (FN)"]
    for j, h in enumerate(h_cm):
        cell = tbl_cm.cell(0, j)
        set_cell_background(cell, "2B6CB0")
        set_cell_margins(cell, top=140, bottom=140, left=120, right=120)
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run(h)
        r.bold = True
        r.font.name = FONT_FAMILY
        r.font.size = Pt(12)
        r.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)

    cm_data = [
        ("🌲 Isolation Forest", "224 บล็อก", "178 บล็อก", "1,822 บล็อก", "569 บล็อก (หลุดรอดมาก)"),
        ("🧠 DeepLog LSTM", "793 บล็อก (ครบ 100%)", "539 บล็อก (Alert ล้น)", "1,461 บล็อก", "0 บล็อก (Zero Miss)"),
        ("🛡️ Hybrid (Cascaded Synergy)", "793 บล็อก (ครบ 100%)", "286 บล็อก (ตัด FP สำเร็จ)", "1,714 บล็อก", "0 บล็อก (Zero Miss)")
    ]

    for i, row in enumerate(cm_data):
        for j, val in enumerate(row):
            cell = tbl_cm.cell(i + 1, j)
            bg = "EDF2F7" if i == 2 else ("F7FAFC" if i % 2 == 1 else "FFFFFF")
            set_cell_background(cell, bg)
            set_cell_margins(cell, top=100, bottom=100, left=120, right=120)
            p = cell.paragraphs[0]
            p.paragraph_format.line_spacing = 1.15
            p.paragraph_format.space_after = Pt(0)
            if j > 0:
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            append_formatted_text(p, val, base_size=Pt(12), base_bold=(i == 2 or j == 0))

    p_cap_cm = doc.add_paragraph()
    p_cap_cm.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_cap_cm = p_cap_cm.add_run("ตารางที่ 4.2: การเปรียบเทียบ Confusion Matrices ของโมเดลทั้ง 3 รูปแบบ บนกลุ่มตัวอย่างทดสอบ 2,793 Sessions")
    r_cap_cm.font.name = FONT_FAMILY
    r_cap_cm.font.size = Pt(12)
    r_cap_cm.italic = True
    r_cap_cm.font.color.rgb = COLOR_MUTED

    add_title("4.3.3 การวิเคราะห์เชิงคุณภาพผ่าน 3 กรณีศึกษาจริง (Qualitative Showcase Evaluation)", level=3)
    add_p("เพื่อพิสูจน์ความสามารถในการตรวจจับเชิงประจักษ์ ระบบได้ทดสอบกับ 3 กรณีศึกษาจริงที่ไม่เคยเห็นในขั้นตอนฝึกสอน:")
    add_numbered_item("1.", "บล็อกข้อมูลทำงานตามวงจรชีวิตมาตรฐาน ตั้งแต่การจองพื้นที่ (allocate), การรับสตรีมข้อมูล (receiving/received) ครบ 3 Replicas และการปิดเธรดเครือข่ายอย่างสมบูรณ์ ลำดับเหตุการณ์ทั้งหมด [0, 0, 0, 6, 2, 3, 2, 3, 2, 3, 1, 1, 1] ทั้ง iForest และ DeepLog เห็นพ้องว่าเป็น Normal ระบบตัดสิน Normal อย่างถูกต้อง ปราศจาก False Alarm", bold_prefix="กรณีศึกษาที่ 1: วงจรชีวิตการทำงานปกติ (Case 1: Nominal Lifecycle - blk_6334862664379948501) —")
    add_numbered_item("2.", "ขณะที่ DataNode กำลังรับส่งข้อมูล เกิดข้อผิดพลาดของระบบฮาร์ดแวร์ส่งผลให้เกิด IOException (Event 12 และ 13) และเกิดการสั่ง Retry ซ้ำหลายครั้งจนเซสชันยาวผิดปกติ ทั้ง iForest (ตรวจจับความถี่สูงผิดปกติ) และ DeepLog (ตรวจจับ Exception นอกลู่ทาง) ทำงานผสานกันยืนยัน Anomaly ได้ทั้งคู่", bold_prefix="กรณีศึกษาที่ 2: ความล้มเหลวระดับฮาร์ดแวร์ (Case 2: DataNode I/O Failure - blk_4516306414837452219) —")
    add_numbered_item("3.", "ทุกข้อความใน Log เป็นคำสั่งปกติของระบบ จำนวนความถี่ปกติ ทำให้ iForest พลาด (False Negative) แต่ DeepLog และ Hybrid สามารถตรวจจับการลัดขั้นตอนที่มีคำสั่งลบบล็อก (Event 14) โผล่ขึ้นมาก่อนกำหนดได้อย่างแม่นยำ พิสูจน์ให้เห็นถึงความจำเป็นในการผสานมิติลำดับขั้นตอน", bold_prefix="กรณีศึกษาที่ 3: ความผิดปกติเชิงลำดับขั้นตอน (Case 3: Sequential Permutation - blk_5913130063451277660) —")

    # =========================================================================
    # บทที่ 5: สรุปผล ข้อจำกัด และข้อเสนอแนะ (CONCLUSION & FUTURE WORK)
    # =========================================================================
    add_title("บทที่ 5: สรุปผล ข้อจำกัด และข้อเสนอแนะ (Conclusion & Future Work)", level=1, page_break=True)

    add_title("5.1 สรุปผลการดำเนินงาน (Conclusion)", level=2)
    add_p("โครงงาน LogWatchdog ประสบความสำเร็จอย่างสมบูรณ์ในการออกแบบและพัฒนาระบบตรวจจับและระบุสาเหตุความผิดปกติใน System Logs ด้วยสถาปัตยกรรม Hybrid Dual-Engine บรรลุวัตถุประสงค์หลักทุกข้อที่ตั้งไว้:")
    add_numbered_item("1.", "พัฒนาระบบสถาปัตยกรรมแบบแยกส่วน 5 บล็อก (Lego Architecture) สำเร็จสมบูรณ์ ผ่านการทดสอบ Unit Tests 100% (37/37 tests)", bold_prefix="ความสำเร็จด้านสถาปัตยกรรม:")
    add_numbered_item("2.", "ผสาน Isolation Forest และ DeepLog 2-Layer LSTM ด้วยกลไก Cascaded Synergy จนบรรลุ F1-Score สูงถึง 84.72% (+10.08% เหนือกว่าโมเดลเดี่ยว) ตัด False Positives ลงได้ 46.9% และรักษา Recall 100.00% สมบูรณ์แบบ", bold_prefix="ความสำเร็จด้านโมเดล AI:")
    add_numbered_item("3.", "โมดูล DeepLogExplainer สามารถชี้เป้าบรรทัดปัญหา (Culprit Line) พร้อมนำเสนอบริบทแวดล้อมและการแจกแจงความน่าจะเป็น เปลี่ยนโมเดลจาก Black-box สู่ White-box Transparency ได้จริง", bold_prefix="ความสำเร็จด้าน Explainability:")
    add_numbered_item("4.", "พัฒนา Web Dashboard แบบมืออาชีพด้วย Streamlit และ Altair 6 รองรับการเปรียบเทียบโมเดล นิติวิทยาศาสตร์ และการรันสดแบบเรียลไทม์", bold_prefix="ความสำเร็จด้านการประยุกต์ใช้งาน:")

    add_title("5.2 ปัญหา อุปสรรค และข้อจำกัด (Challenges & Limitations)", level=2)
    add_p("ในระหว่างการดำเนินงาน คณะผู้พัฒนาได้พบปัญหาและข้อจำกัดทางเทคนิคที่สำคัญ 3 ประการ:")
    add_numbered_item("1.", "ลักษณะข้อมูลในโลกจริงมีความไม่สมดุลของคลาสสูงมาก (Normal 97% vs Anomaly 3%) โครงงานจึงเลือกใช้แนวทาง Semi-supervised โดยฝึกสอนโมเดลบนพฤติกรรมปกติเพียงอย่างเดียว", bold_prefix="ความไม่สมดุลของชุดข้อมูล:")
    add_numbered_item("2.", "การรวมโมเดลแบบ Naive OR-Voting ในเบื้องต้นทำให้ False Positive เพิ่มขึ้น จึงต้องพัฒนาต่อยอดสู่ Cascaded Synergy เพื่อให้โมเดลทั้งสองเสริมจุดเด่นและกลบจุดด้อยของกันและกันได้อย่างแท้จริง", bold_prefix="ความท้าทายในการ Ensemble โมเดล:")
    add_numbered_item("3.", "โมเดลปัจจุบันมุ่งเน้นการวิเคราะห์เฉพาะลำดับเหตุการณ์และความถี่ ยังไม่ได้นำค่าพารามิเตอร์ตัวเลข (เช่น latency, packet size) มาคำนวณร่วมด้วย ทำให้ยังไม่ครอบคลุมความผิดปกติประเภท Performance Degradation", bold_prefix="ข้อจำกัดของฟีเจอร์:")

    add_title("5.3 ข้อเสนอแนะและแนวทางการพัฒนาต่อยอด (Future Work)", level=2)
    add_p("เพื่อยกระดับระบบ LogWatchdog ไปสู่ระบบเฝ้าระวังระดับ Enterprise ในอนาคต มีแนวทางการพัฒนาต่อยอด 3 ด้าน:")
    add_numbered_item("1.", "ผสานโมดูล Parameter Value Anomaly Detection ตามทฤษฎี DeepLog ดั้งเดิม โดยใช้ LSTM อีกตัวหนึ่งเพื่อตรวจจับค่าพารามิเตอร์ตัวเลขที่ผิดปกติไปจากแนวโน้มประวัติศาสตร์", bold_prefix="ขยายขีดความสามารถการตรวจจับ:")
    add_numbered_item("2.", "ศึกษาและเปรียบเทียบกับโมเดลยุคใหม่ที่ใช้สถาปัตยกรรม Transformer เช่น LogBERT หรือ Tiny-LLM เพื่อเพิ่มความสามารถในการจับความสัมพันธ์ระยะไกล (Long-range Dependencies)", bold_prefix="สถาปัตยกรรมโมเดลขั้นสูง:")
    add_numbered_item("3.", "เชื่อมต่อระบบเข้ากับ Distributed Streaming Engine เช่น Apache Kafka หรือ Fluentbit เพื่อรองรับการดูดซับสตรีมบันทึกเหตุการณ์แบบ Real-time ขนาดหลายสิบล้านบรรทัดต่อวินาทีในสภาพแวดล้อม Multi-cloud Production", bold_prefix="การรองรับระดับโปรดักชัน:")

    # =========================================================================
    # ส่วนท้าย (BACK MATTER) - REFERENCES & APPENDICES
    # =========================================================================
    add_title("เอกสารอ้างอิง (References)", level=1, page_break=True)
    references = [
        "[1] M. Du, F. Li, G. Zheng, and V. Srikumar, \"DeepLog: Anomaly Detection and Root Cause Analysis from System Logs through Deep Learning,\" in Proceedings of the 2017 ACM SIGSAC Conference on Computer and Communications Security (CCS '17), Dallas, TX, USA, 2017, pp. 1285-1298.",
        "[2] P. He, J. Zhu, Z. Zheng, and M. R. Lyu, \"Drain: An Online Log Parsing Approach with Fixed Depth Tree,\" in 2017 IEEE International Conference on Web Services (ICWS), Honolulu, HI, USA, 2017, pp. 33-40.",
        "[3] J. Zhu, S. He, J. Liu, P. He, Q. Xie, Z. Zheng, and M. R. Lyu, \"Tools and Benchmarks for Automated Log Parsing and Anomaly Detection,\" in Proceedings of the 41st International Conference on Software Engineering: Software Engineering in Practice (ICSE-SEIP '19), Montreal, QC, Canada, 2019, pp. 121-130.",
        "[4] S. Hochreiter and J. Schmidhuber, \"Long Short-Term Memory,\" Neural Computation, vol. 9, no. 8, pp. 1735-1780, 1997.",
        "[5] W. Meng, Y. Liu, Y. Zhu, S. Zhang, D. Pei, Y. Liu, Y. Chen, R. Zhang, S. Tao, P. Sun, and R. Zhou, \"LogAnomaly: Unsupervised Detection of Sequential and Quantitative Anomalies in Unstructured Logs,\" in Proceedings of the 28th International Joint Conference on Artificial Intelligence (IJCAI '19), Macao, China, 2019, pp. 4739-4745.",
        "[6] F. T. Liu, K. M. Ting, and Z.-H. Zhou, \"Isolation Forest,\" in 2008 Eighth IEEE International Conference on Data Mining, Pisa, Italy, 2008, pp. 413-422.",
        "[7] A. Paszke et al., \"PyTorch: An Imperative Style, High-Performance Deep Learning Library,\" in Advances in Neural Information Processing Systems 32 (NeurIPS 2019), Vancouver, Canada, 2019.",
        "[8] S. He, J. Zhu, P. He, and M. R. Lyu, \"Experience Report: System Log Analysis for Anomaly Detection,\" in 2016 IEEE 27th International Symposium on Software Reliability Engineering (ISSRE), Ottawa, ON, Canada, 2016, pp. 207-218."
    ]
    for ref in references:
        p = doc.add_paragraph()
        p.paragraph_format.line_spacing = 1.15
        p.paragraph_format.space_after = Pt(4)
        p.paragraph_format.left_indent = Inches(0.4)
        p.paragraph_format.first_line_indent = Inches(-0.4)
        r = p.add_run(ref)
        r.font.name = FONT_FAMILY
        r.font.size = Pt(12)

    # ภาคผนวก
    add_title("ภาคผนวก (Appendices)", level=1, page_break=True)

    add_title("ภาคผนวก ก: คู่มือการติดตั้งและใช้งานระบบ (Deployment & Setup Guide)", level=2)
    add_p("ระบบ LogWatchdog ได้รับการออกแบบให้สามารถติดตั้งและเปิดรันได้อย่างสะดวกรวดเร็วบนระบบปฏิบัติการ Linux:")
    add_callout(
        "# 1. สร้างและเปิดใช้งาน Virtual Environment\n"
        "python3 -m venv venv\n"
        "source venv/bin/activate\n\n"
        "# 2. ติดตั้ง Dependencies ที่จำเป็น\n"
        "pip install torch torchvision pandas numpy pyarrow streamlit altair drain3 scikit-learn\n\n"
        "# 3. รันชุดทดสอบความถูกต้องของระบบ (37 Unit Tests)\n"
        "./venv/bin/pytest tests/ -v\n\n"
        "# 4. เปิดใช้งาน Web Application Dashboard\n"
        "./run_demo.sh   (หรือ ./venv/bin/streamlit run app.py --server.port 8501)\n\n"
        "# 5. เข้าใช้งานผ่านเว็บเบราว์เซอร์ที่ http://localhost:8501",
        bold_title="คำสั่งการติดตั้งและเปิดรันระบบ LogWatchdog"
    )

    add_title("ภาคผนวก ข: โครงสร้าง Incident Report Payload Schema", level=2)
    add_p("เมื่อระบบตรวจพบความผิดปกติ DeepLogExplainer จะสร้างโครงสร้างรายงานเชิงนิติวิทยาศาสตร์ในรูปแบบ JSON Payload มาตรฐานดังนี้:")
    add_callout(
        "{\n"
        "  \"incident_id\": \"INC-20261007-BLK451630\",\n"
        "  \"timestamp\": \"2026-10-07T15:30:00Z\",\n"
        "  \"session_id\": \"blk_4516306414837452219\",\n"
        "  \"severity\": \"CRITICAL\",\n"
        "  \"anomaly_type\": \"HYBRID_SYNERGY_VIOLATION\",\n"
        "  \"engines_triggered\": [\n"
        "    \"Isolation Forest (Volume/Count Outlier)\",\n"
        "    \"DeepLog LSTM (Sequential Violation)\"\n"
        "  ],\n"
        "  \"root_cause_analysis\": {\n"
        "    \"culprit_line_number\": 14,\n"
        "    \"culprit_template_id\": 12,\n"
        "    \"culprit_message\": \"writeBlock received exception java.io.IOException\",\n"
        "    \"expected_candidates\": [1, 2, 6],\n"
        "    \"candidate_probabilities\": {\"E1\": 0.65, \"E2\": 0.28, \"E12\": 0.001}\n"
        "  },\n"
        "  \"context_window\": [\n"
        "    \"Line 12: PacketResponder for block terminating\",\n"
        "    \"Line 13: Received block of size 67108864\",\n"
        "    \"[CULPRIT] Line 14: writeBlock received exception java.io.IOException\",\n"
        "    \"Line 15: PacketResponder Exception java.io.IOException\"\n"
        "  ]\n"
        "}",
        bold_title="ตัวอย่าง Incident Report Schema (JSON Export)"
    )

    add_title("ภาคผนวก ค: รายการแม่พิมพ์บันทึกเหตุการณ์มาตรฐานระบบ HDFS (Log Templates)", level=2)
    add_p("ตารางแม่พิมพ์เหตุการณ์หลักที่สกัดได้จากชุดข้อมูล HDFS ผ่าน Drain3 Template Miner:")

    tbl_temp = doc.add_table(rows=11, cols=3)
    tbl_temp.alignment = WD_TABLE_ALIGNMENT.CENTER
    set_table_borders(tbl_temp)
    h_temp = ["Event ID", "Log Template String (แม่พิมพ์ข้อความ)", "คำอธิบายเชิงปฏิบัติการ (Operation Description)"]
    for j, h in enumerate(h_temp):
        cell = tbl_temp.cell(0, j)
        set_cell_background(cell, "2B6CB0")
        set_cell_margins(cell, top=140, bottom=140, left=140, right=140)
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run(h)
        r.bold = True
        r.font.name = FONT_FAMILY
        r.font.size = Pt(13)
        r.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)

    temp_data = [
        ("E0", "Receiving block <*> src: <*> dest: <*>", "เริ่มต้นการรับข้อมูลสตรีมบล็อกเข้าสู่ DataNode"),
        ("E1", "Received block <*> of size <*> from <*>", "การรับข้อมูลบล็อกตามขนาดที่กำหนดเสร็จสมบูรณ์"),
        ("E2", "PacketResponder <*> for block <*> terminating", "เธรดเครือข่ายตอบรับแพ็กเก็ตทำงานเสร็จสิ้นและปิดตัว"),
        ("E3", "BLOCK* NameSystem.allocateBlock: <*> <*>", "NameNode ทำการจัดสรรบล็อกและระบุโหนดเก็บสำเนา"),
        ("E4", "BLOCK* ask <*> to replicate <*> to datanode(s) <*>", "คำสั่งร้องขอให้ทำสำเนาบล็อกไปยัง DataNode เพิ่มเติม"),
        ("E5", "BLOCK* ask <*> to delete <*>", "คำสั่งร้องขอให้ลบสำเนาบล็อกที่เกินหรือหมดอายุ"),
        ("E6", "BLOCK* NameSystem.addStoredBlock: blockMap updated", "อัปเดตแผนผังตำแหน่งบล็อกในระบบจัดเก็บสำเร็จ"),
        ("E9", "Deleting block <*> file <*>", "ลบข้อมูลบล็อกออกจากระบบจัดเก็บข้อมูลทางกายภาพ"),
        ("E12", "writeBlock <*> received exception java.io.IOException", "เกิดข้อผิดพลาด I/O กะทันหันขณะเขียนข้อมูลลงดิสก์"),
        ("E14", "BLOCK* NameSystem.delete: <*> is deleted", "ยืนยันการลบบล็อกออกจาก NameNode สมบูรณ์")
    ]

    for i, row in enumerate(temp_data):
        for j, val in enumerate(row):
            cell = tbl_temp.cell(i + 1, j)
            bg = "F7FAFC" if i % 2 == 1 else "FFFFFF"
            set_cell_background(cell, bg)
            set_cell_margins(cell, top=100, bottom=100, left=120, right=120)
            p = cell.paragraphs[0]
            p.paragraph_format.line_spacing = 1.15
            p.paragraph_format.space_after = Pt(0)
            append_formatted_text(p, val, base_size=Pt(11), base_bold=(j == 0))
            if j == 0:
                p.runs[0].font.color.rgb = COLOR_PRIMARY

    # บันทึกไฟล์ DOCX ชั่วคราว และแปลงเป็น ODT ด้วย LibreOffice
    os.makedirs("scratch", exist_ok=True)
    docx_path = "scratch/LogWatchdog_Report_generated.docx"
    odt_target = "LogWatchdog Report.odt"

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

    generated_odt = "LogWatchdog_Report_generated.odt"
    if os.path.exists(generated_odt):
        os.replace(generated_odt, odt_target)
        print(f"แทนที่และบันทึกไฟล์สำเร็จเป็น {odt_target}")
    else:
        print(f"ตรวจสอบไฟล์เป้าหมาย: {odt_target}")

    file_size = os.path.getsize(odt_target)
    print(f"สร้างไฟล์เสร็จสมบูรณ์: {odt_target} (ขนาด: {file_size:,} ไบต์)")

if __name__ == "__main__":
    build_report()
