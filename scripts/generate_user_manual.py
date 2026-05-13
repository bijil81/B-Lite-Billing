from __future__ import annotations

from pathlib import Path
import sys

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from help_content import HELP_TOPICS


TOPIC_ORDER = [
    "dashboard",
    "billing",
    "customers",
    "appointments",
    "membership",
    "offers",
    "redeem_codes",
    "cloud_sync",
    "staff",
    "inventory",
    "expenses",
    "whatsapp_bulk",
    "reports",
    "closing_report",
    "ai_assistant",
    "settings",
    "admin_panel",
]


def _manual_paths(root: Path) -> tuple[Path, Path]:
    docs = root / "docs"
    docs.mkdir(exist_ok=True)
    return docs / "B_Lite_Management_V6_1_User_Guide.md", docs / "B_Lite_Management_V6_1_User_Guide.pdf"


def write_markdown(root: Path) -> Path:
    md_path, _ = _manual_paths(root)
    lines = [
        "# B-Lite Management v6.1.0 User Guide",
        "",
        "This manual is generated from the same help content used inside the app Help button.",
        "",
        "Use it as the customer-facing workflow guide for daily billing, stock, reports, settings, and administration.",
        "",
        "## Contents",
    ]
    for idx, key in enumerate(TOPIC_ORDER, start=1):
        topic = HELP_TOPICS[key]
        lines.append(f"{idx}. {topic['title']}")
    lines.append("")

    for key in TOPIC_ORDER:
        topic = HELP_TOPICS[key]
        lines.extend([f"## {topic['title']}", "", topic["summary"], ""])
        for section in topic.get("sections", []):
            lines.extend([f"### {section.get('heading', 'Guide')}", ""])
            for item in section.get("items", []):
                lines.append(f"- {item}")
            lines.append("")
    md_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return md_path


def write_pdf(root: Path) -> Path:
    _, pdf_path = _manual_paths(root)
    styles = getSampleStyleSheet()
    title = ParagraphStyle(
        "ManualTitle",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=20,
        leading=24,
        textColor=colors.HexColor("#111827"),
        spaceAfter=8,
    )
    subtitle = ParagraphStyle(
        "ManualSubtitle",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#374151"),
        spaceAfter=14,
    )
    h1 = ParagraphStyle(
        "ManualH1",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=15,
        leading=19,
        textColor=colors.HexColor("#0f172a"),
        spaceBefore=8,
        spaceAfter=6,
    )
    h2 = ParagraphStyle(
        "ManualH2",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=11,
        leading=14,
        textColor=colors.HexColor("#1f2937"),
        spaceBefore=8,
        spaceAfter=4,
    )
    body = ParagraphStyle(
        "ManualBody",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=9,
        leading=12,
        leftIndent=8,
        firstLineIndent=-5,
        textColor=colors.HexColor("#111827"),
        spaceAfter=3,
    )
    small = ParagraphStyle(
        "ManualSmall",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#374151"),
        spaceAfter=8,
    )

    story = [
        Paragraph("B-Lite Management v6.1.0 User Guide", title),
        Paragraph(
            "Customer-facing workflow manual generated from the same content used by the in-app Help button.",
            subtitle,
        ),
        Paragraph("Contents", h1),
    ]
    for idx, key in enumerate(TOPIC_ORDER, start=1):
        story.append(Paragraph(f"{idx}. {HELP_TOPICS[key]['title']}", small))
    story.append(PageBreak())

    for topic_idx, key in enumerate(TOPIC_ORDER):
        topic = HELP_TOPICS[key]
        story.append(Paragraph(topic["title"], h1))
        story.append(Paragraph(topic["summary"], small))
        for section in topic.get("sections", []):
            story.append(Paragraph(section.get("heading", "Guide"), h2))
            for item in section.get("items", []):
                escaped = str(item).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                story.append(Paragraph(f"- {escaped}", body))
            story.append(Spacer(1, 2 * mm))
        if topic_idx != len(TOPIC_ORDER) - 1:
            story.append(PageBreak())

    doc = SimpleDocTemplate(
        str(pdf_path),
        pagesize=A4,
        rightMargin=14 * mm,
        leftMargin=14 * mm,
        topMargin=12 * mm,
        bottomMargin=12 * mm,
        title="B-Lite Management v6.1.0 User Guide",
        author="B-Lite Technologies",
    )
    doc.build(story)
    return pdf_path


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    md_path = write_markdown(root)
    pdf_path = write_pdf(root)
    print(f"Wrote {md_path}")
    print(f"Wrote {pdf_path}")


if __name__ == "__main__":
    main()
