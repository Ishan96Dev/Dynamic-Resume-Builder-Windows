# Copyright (c) 2026 Ishan Chakraborty
# SPDX-License-Identifier: MIT
"""Dynamic resume generator - same visual template as create_resume_docx.py,
but driven entirely by a data dictionary supplied by the user.

Author: Ishan Chakraborty
License: MIT
"""
import io
from datetime import datetime

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

# (accent colour, light background) pairs cycled through for cards
PALETTE = [
    ("2563EB", "EFF6FF"),
    ("7C3AED", "F5F3FF"),
    ("16A34A", "DCFCE7"),
    ("D97706", "FEF3C7"),
    ("DB2777", "FDF2F8"),
    ("0891B2", "ECFEFF"),
]


def _rgb(hex_color):
    return RGBColor(int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16))


def _s(value):
    return (value or "").strip() if isinstance(value, str) else ""


def _list(value):
    return value if isinstance(value, list) else []


def set_cell_shading(cell, color):
    shd = OxmlElement("w:shd")
    shd.set(qn("w:fill"), color)
    cell._tc.get_or_add_tcPr().append(shd)


def set_cell_border(cell, color="2563EB", size="8"):
    tcPr = cell._tc.get_or_add_tcPr()
    borders = OxmlElement("w:tcBorders")
    for side in ("top", "left", "bottom", "right"):
        b = OxmlElement(f"w:{side}")
        b.set(qn("w:val"), "single")
        b.set(qn("w:sz"), size)
        b.set(qn("w:color"), color)
        borders.append(b)
    tcPr.append(borders)


def set_left_border(cell, color="2563EB", size="24"):
    tcPr = cell._tc.get_or_add_tcPr()
    borders = OxmlElement("w:tcBorders")
    b = OxmlElement("w:left")
    b.set(qn("w:val"), "single")
    b.set(qn("w:sz"), size)
    b.set(qn("w:color"), color)
    borders.append(b)
    tcPr.append(borders)


def add_hyperlink(paragraph, url, text, color="2563EB", font_size=10):
    r_id = paragraph.part.relate_to(
        url, "http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink", is_external=True
    )
    link = OxmlElement("w:hyperlink")
    link.set(qn("r:id"), r_id)
    run = OxmlElement("w:r")
    rPr = OxmlElement("w:rPr")
    c = OxmlElement("w:color")
    c.set(qn("w:val"), color)
    rPr.append(c)
    u = OxmlElement("w:u")
    u.set(qn("w:val"), "single")
    rPr.append(u)
    for tag in ("w:sz", "w:szCs"):
        sz = OxmlElement(tag)
        sz.set(qn("w:val"), str(font_size * 2))
        rPr.append(sz)
    run.append(rPr)
    t = OxmlElement("w:t")
    t.text = text
    run.append(t)
    link.append(run)
    paragraph._p.append(link)


def add_section_heading(doc, text, color="2563EB"):
    para = doc.add_paragraph()
    para.paragraph_format.space_before = Pt(12)
    para.paragraph_format.space_after = Pt(8)
    run = para.add_run(text)
    run.font.size = Pt(14)
    run.font.bold = True
    run.font.color.rgb = _rgb(color)
    pPr = para._p.get_or_add_pPr()
    pBdr = OxmlElement("w:pBdr")
    bottom = OxmlElement("w:bottom")
    bottom.set(qn("w:val"), "single")
    bottom.set(qn("w:sz"), "12")
    bottom.set(qn("w:color"), color)
    pBdr.append(bottom)
    pPr.append(pBdr)


def _url(u):
    u = _s(u)
    if u and not u.startswith(("http://", "https://", "mailto:")):
        u = "https://" + u
    return u


def _strip_scheme(u):
    return _s(u).replace("https://", "").replace("http://", "").rstrip("/")


def build_resume(data, photo_bytes=None):
    """Create a resume .docx from `data`; returns the document as BytesIO."""
    doc = Document()
    for section in doc.sections:
        section.top_margin = Inches(0.4)
        section.bottom_margin = Inches(0.4)
        section.left_margin = Inches(0.5)
        section.right_margin = Inches(0.5)

    # ---------------- HEADER ----------------
    has_photo = bool(photo_bytes)
    header = doc.add_table(rows=1, cols=2 if has_photo else 1)
    header.alignment = WD_TABLE_ALIGNMENT.CENTER
    header.autofit = False
    left = header.cell(0, 0)
    set_cell_shading(left, "EFF6FF")
    set_left_border(left, "2563EB", "36")

    p = left.paragraphs[0]
    p.paragraph_format.space_before = Pt(12)
    r = p.add_run(_s(data.get("name")).upper() or "YOUR NAME")
    r.font.size = Pt(28)
    r.font.bold = True
    r.font.color.rgb = RGBColor(31, 41, 55)

    if _s(data.get("title")):
        r = left.add_paragraph().add_run(_s(data["title"]))
        r.font.size = Pt(12)
        r.font.bold = True
        r.font.color.rgb = RGBColor(37, 99, 235)
    if _s(data.get("subtitle")):
        r = left.add_paragraph().add_run(_s(data["subtitle"]))
        r.font.size = Pt(10)
        r.font.italic = True
        r.font.color.rgb = RGBColor(107, 114, 128)

    c1 = left.add_paragraph()
    c1.paragraph_format.space_before = Pt(8)
    parts = 0

    def sep(par):
        nonlocal parts
        if parts:
            par.add_run("    |    ").font.size = Pt(10)
        parts += 1

    if _s(data.get("email")):
        sep(c1)
        c1.add_run("📧 ").font.size = Pt(10)
        add_hyperlink(c1, "mailto:" + _s(data["email"]), _s(data["email"]))
    if _s(data.get("alt_email")):
        sep(c1)
        add_hyperlink(c1, "mailto:" + _s(data["alt_email"]), _s(data["alt_email"]) + " (Alt)", "6B7280")
    if _s(data.get("phone")):
        sep(c1)
        c1.add_run("📱 " + _s(data["phone"])).font.size = Pt(10)

    bits = []
    if _s(data.get("location")):
        bits.append("📍 " + _s(data["location"]))
    if _s(data.get("dob")):
        bits.append("🎂 DOB: " + _s(data["dob"]))
    if bits:
        left.add_paragraph().add_run("    |    ".join(bits)).font.size = Pt(10)

    links = [
        ("🔗 ", data.get("linkedin"), "LinkedIn Profile"),
        ("💻 ", data.get("github"), None),
        ("🌐 ", data.get("website"), "Portfolio Website"),
    ]
    c3 = left.add_paragraph()
    parts = 0
    for icon, url, label in links:
        if _s(url):
            sep(c3)
            c3.add_run(icon).font.size = Pt(10)
            add_hyperlink(c3, _url(url), label or _strip_scheme(url))
    left.add_paragraph().paragraph_format.space_after = Pt(8)

    if has_photo:
        header.columns[0].width = Inches(5.5)
        header.columns[1].width = Inches(1.5)
        right = header.cell(0, 1)
        set_cell_shading(right, "EFF6FF")
        ip = right.paragraphs[0]
        ip.alignment = WD_ALIGN_PARAGRAPH.CENTER
        ip.paragraph_format.space_before = Pt(12)
        try:
            ip.add_run().add_picture(io.BytesIO(photo_bytes), width=Inches(1.3))
        except Exception:
            ip.add_run("📷").font.size = Pt(40)
    doc.add_paragraph()

    # ---------------- SUMMARY ----------------
    if _s(data.get("summary")):
        add_section_heading(doc, "💼 PROFESSIONAL SUMMARY", "7C3AED")
        t = doc.add_table(rows=1, cols=1)
        cell = t.cell(0, 0)
        set_cell_shading(cell, "F5F3FF")
        set_left_border(cell, "7C3AED", "24")
        sp = cell.paragraphs[0]
        sp.paragraph_format.space_before = Pt(8)
        sp.paragraph_format.space_after = Pt(8)
        sp.add_run(_s(data["summary"])).font.size = Pt(10)

    # ---------------- SKILLS ----------------
    skills = [s for s in _list(data.get("skills")) if _s(s.get("category")) or _s(s.get("items"))]
    if skills:
        add_section_heading(doc, "🛠️ TECHNICAL SKILLS", "2563EB")
        t = doc.add_table(rows=1, cols=1)
        cell = t.cell(0, 0)
        set_cell_shading(cell, "F8FAFC")
        for i, s in enumerate(skills):
            par = cell.add_paragraph()
            par.paragraph_format.space_before = Pt(2)
            par.paragraph_format.space_after = Pt(2)
            r = par.add_run(_s(s.get("category")) + ": ")
            r.font.bold = True
            r.font.size = Pt(10)
            r.font.color.rgb = _rgb(PALETTE[i % len(PALETTE)][0])
            r = par.add_run(_s(s.get("items")))
            r.font.size = Pt(10)
            r.font.color.rgb = RGBColor(55, 65, 81)

    # ---------------- EXPERIENCE ----------------
    jobs = [j for j in _list(data.get("experience")) if _s(j.get("title")) or _s(j.get("company"))]
    if jobs:
        add_section_heading(doc, "💼 PROFESSIONAL EXPERIENCE", "2563EB")
        for i, job in enumerate(jobs):
            color, bg = PALETTE[i % len(PALETTE)]
            t = doc.add_table(rows=1, cols=1)
            cell = t.cell(0, 0)
            set_cell_shading(cell, bg)
            set_left_border(cell, color, "24")
            hp = cell.paragraphs[0]
            hp.paragraph_format.space_before = Pt(8)
            r = hp.add_run(_s(job.get("title")))
            r.font.bold = True
            r.font.size = Pt(14)
            r.font.color.rgb = RGBColor(31, 41, 55)
            if _s(job.get("dates")):
                hp.add_run("      ").font.size = Pt(10)
                r = hp.add_run(_s(job["dates"]))
                r.font.bold = True
                r.font.size = Pt(11)
                r.font.color.rgb = RGBColor(55, 65, 81)
            comp = " | ".join(x for x in (_s(job.get("company")), _s(job.get("location"))) if x)
            if comp:
                r = cell.add_paragraph().add_run(comp)
                r.font.italic = True
                r.font.size = Pt(11)
                r.font.color.rgb = _rgb(color)
            for duty in _list(job.get("duties")):
                if not _s(duty):
                    continue
                dp = cell.add_paragraph()
                dp.paragraph_format.space_before = Pt(1)
                dp.paragraph_format.space_after = Pt(1)
                dp.add_run("• " + _s(duty)).font.size = Pt(10)
            cell.add_paragraph().paragraph_format.space_after = Pt(6)
            doc.add_paragraph()

    # ---------------- PROJECTS ----------------
    projects = [p for p in _list(data.get("projects")) if _s(p.get("title"))]
    if projects:
        add_section_heading(doc, "🚀 PROJECTS", "7C3AED")
        for i, proj in enumerate(projects):
            color, bg = PALETTE[i % len(PALETTE)]
            t = doc.add_table(rows=1, cols=1)
            cell = t.cell(0, 0)
            set_cell_shading(cell, bg)
            set_cell_border(cell, bg, "4")
            tp = cell.paragraphs[0]
            tp.paragraph_format.space_before = Pt(6)
            r = tp.add_run(_s(proj["title"]))
            r.font.bold = True
            r.font.size = Pt(12)
            r.font.color.rgb = _rgb(color)
            if _s(proj.get("description")):
                cell.add_paragraph().add_run(_s(proj["description"])).font.size = Pt(10)
            if _s(proj.get("url")) or _s(proj.get("live_url")):
                lp = cell.add_paragraph()
                lp.paragraph_format.space_after = Pt(6)
                if _s(proj.get("url")):
                    lp.add_run("🔗 ").font.size = Pt(9)
                    add_hyperlink(lp, _url(proj["url"]), "[Source / Details]", color, 9)
                if _s(proj.get("live_url")):
                    lp.add_run("    |    🚀 " if _s(proj.get("url")) else "🚀 ").font.size = Pt(9)
                    add_hyperlink(lp, _url(proj["live_url"]), "[Live Demo]", "16A34A", 9)
            doc.add_paragraph()

    # ---------------- EDUCATION ----------------
    edu = [e for e in _list(data.get("education")) if _s(e.get("degree")) or _s(e.get("school"))]
    if edu:
        add_section_heading(doc, "🎓 EDUCATION", "2563EB")
        for i, e in enumerate(edu):
            color, bg = PALETTE[i % len(PALETTE)]
            t = doc.add_table(rows=1, cols=1)
            cell = t.cell(0, 0)
            set_cell_shading(cell, bg)
            set_left_border(cell, color, "18")
            tp = cell.paragraphs[0]
            tp.paragraph_format.space_before = Pt(6)
            r = tp.add_run(_s(e.get("degree")))
            r.font.bold = True
            r.font.size = Pt(11)
            r.font.color.rgb = _rgb(color)
            school = " | ".join(x for x in (_s(e.get("school")), _s(e.get("year"))) if x)
            if school:
                cell.add_paragraph().add_run(school).font.size = Pt(10)
            sp = cell.add_paragraph()
            sp.paragraph_format.space_after = Pt(6)
            if _s(e.get("details")):
                r = sp.add_run(_s(e["details"]))
                r.font.size = Pt(9)
                r.font.italic = True
                r.font.color.rgb = RGBColor(107, 114, 128)
            doc.add_paragraph()

    # ---------------- CERTIFICATIONS ----------------
    certs = [c for c in _list(data.get("certifications")) if _s(c.get("name"))]
    if certs:
        add_section_heading(doc, "🏅 CERTIFICATIONS", "EA580C")
        cols = min(3, len(certs))
        rows = (len(certs) + cols - 1) // cols
        t = doc.add_table(rows=rows, cols=cols)
        t.alignment = WD_TABLE_ALIGNMENT.CENTER
        for i, c in enumerate(certs):
            color, bg = PALETTE[i % len(PALETTE)]
            cell = t.cell(i // cols, i % cols)
            set_cell_shading(cell, bg)
            set_cell_border(cell, bg, "4")
            par = cell.paragraphs[0]
            par.alignment = WD_ALIGN_PARAGRAPH.CENTER
            par.paragraph_format.space_before = Pt(10)
            par.paragraph_format.space_after = Pt(10)
            r = par.add_run("🏆 " + _s(c["name"]) + "\n")
            r.font.bold = True
            r.font.size = Pt(10)
            r.font.color.rgb = _rgb(color)
            r = par.add_run(_s(c.get("issuer")))
            r.font.size = Pt(9)
            r.font.color.rgb = RGBColor(107, 114, 128)

    # ---------------- INTERESTS ----------------
    interests = [x for x in _list(data.get("interests")) if _s(x)]
    if interests:
        add_section_heading(doc, "🎯 ACTIVITIES & INTERESTS", "2563EB")
        ap = doc.add_paragraph()
        ap.paragraph_format.space_before = Pt(4)
        for i, x in enumerate(interests):
            ap.add_run(f"  {_s(x)}  ").font.size = Pt(10)
            if i < len(interests) - 1:
                ap.add_run("•").font.size = Pt(10)

    # ---------------- DECLARATION ----------------
    add_section_heading(doc, "📝 CANDIDATE DECLARATION", "2563EB")
    t = doc.add_table(rows=1, cols=1)
    cell = t.cell(0, 0)
    set_cell_shading(cell, "F8FAFC")
    set_cell_border(cell, "2563EB", "8")
    dp = cell.paragraphs[0]
    dp.paragraph_format.space_before = Pt(8)
    dp.add_run(
        "I hereby declare that all the information provided above is true and correct to the best of my "
        "knowledge and belief. I understand that any false or misleading information may result in the "
        "rejection of my application or termination of employment if discovered at a later date."
    ).font.size = Pt(10)
    sp = cell.add_paragraph()
    sp.paragraph_format.space_before = Pt(16)
    sp.add_run(f"Date: {datetime.now().strftime('%d/%m/%Y')}").font.size = Pt(10)
    place = _s(data.get("place")) or _s(data.get("location"))
    if place:
        sp.add_run(f"\nPlace: {place}").font.size = Pt(10)
    lp = cell.add_paragraph()
    lp.paragraph_format.space_before = Pt(24)
    lp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    lp.add_run("_________________________").font.size = Pt(10)
    np_ = cell.add_paragraph()
    np_.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    r = np_.add_run(f"({_s(data.get('name'))})")
    r.font.size = Pt(10)
    r.font.bold = True
    cp = cell.add_paragraph()
    cp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    cp.paragraph_format.space_after = Pt(8)
    r = cp.add_run("Candidate Signature")
    r.font.size = Pt(9)
    r.font.italic = True
    r.font.color.rgb = RGBColor(107, 114, 128)

    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf

