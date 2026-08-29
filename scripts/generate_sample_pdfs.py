from pathlib import Path
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib import colors

OUT = Path(__file__).resolve().parents[1] / "sample_data"
OUT.mkdir(exist_ok=True)

profiles = {
    "apex_systems.pdf": {
        "name": "Apex Systems",
        "summary": "Strong technical design and security controls, but a higher commercial proposal and moderate delivery schedule.",
        "solution": "Apex proposes a modular cloud architecture with API integrations, containerized services, horizontal scaling and observability. The design includes an integration gateway and automated deployment pipeline.",
        "timeline": "16 weeks: discovery 2, architecture 3, build 7, integration 2, testing 2. Team: 9 specialists.",
        "price": "$1.45M implementation plus $240K annual support. Assumptions include cloud hosting billed separately.",
        "security": "Encryption in transit and at rest, role-based access control, centralized audit logging, vulnerability scanning and annual penetration testing. ISO 27001 certification is stated.",
        "support": "24x7 critical incident support with 30-minute response target. Three comparable transformation references are listed.",
    },
    "brightpath_tech.pdf": {
        "name": "BrightPath Tech",
        "summary": "Lowest price and fastest timeline, with limited compliance detail and fewer documented references.",
        "solution": "BrightPath proposes a lightweight web platform with REST APIs and managed cloud services. Integration details are high level and some interface dependencies are to be confirmed.",
        "timeline": "10 weeks: design 2, build 5, testing 2, launch 1. Team: 5 people.",
        "price": "$780K fixed implementation plus $120K annual support. Cloud costs and third-party licenses are excluded.",
        "security": "Mentions encryption, passwords and access controls, but provides limited certification, audit and privacy detail. Penetration testing is not explicitly committed.",
        "support": "Business-hours support with next-business-day response for standard issues. One similar reference is provided.",
    },
    "nexaworks.pdf": {
        "name": "NexaWorks",
        "summary": "Balanced proposal with the strongest implementation plan and a mature support model.",
        "solution": "NexaWorks proposes a service-oriented architecture, API management, automated CI/CD, integration testing and scalable managed infrastructure. Dependencies are mapped in an implementation workbook.",
        "timeline": "14 weeks: discovery 2, design 2, build 5, integrations 2, UAT 2, transition 1. Team: 8 people with named roles and milestone owners.",
        "price": "$1.08M implementation plus $180K annual support. Pricing includes training and knowledge transfer; cloud consumption is usage-based.",
        "security": "Role-based access, encryption, centralized logs, privacy controls and quarterly vulnerability assessment are described. Specific certification status is not stated.",
        "support": "24x7 support, service manager, monthly service reviews, knowledge base and four comparable references.",
    },
    "orbit_digital.pdf": {
        "name": "Orbit Digital",
        "summary": "Strong experience and references with medium pricing, but the integration approach is comparatively vague.",
        "solution": "Orbit proposes a cloud-first platform with analytics, configurable workflows and standard APIs. The proposal says integrations will follow an agreed interface catalogue but gives limited technical detail.",
        "timeline": "13 weeks with phased delivery. Team: 7 people. Milestones are listed, but integration workstream detail is limited.",
        "price": "$1.02M implementation plus $190K annual support. Travel and optional analytics modules are excluded.",
        "security": "Encryption, least-privilege access, audit logs and incident response procedures are described. Compliance certifications are referenced without detailed evidence.",
        "support": "24x7 support, named service lead and six comparable references across public-sector and enterprise programs.",
    },
}

def make_pdf(filename, p):
    path = OUT / filename
    doc = SimpleDocTemplate(str(path), pagesize=A4, rightMargin=18*mm, leftMargin=18*mm, topMargin=16*mm, bottomMargin=16*mm)
    styles = getSampleStyleSheet()
    story = [
        Paragraph(p["name"], styles["Title"]),
        Paragraph("Synthetic RFP Response — Classroom Demonstration", styles["Heading2"]),
        Spacer(1, 8),
        Paragraph("<b>1. Executive Summary</b>", styles["Heading2"]),
        Paragraph(p["summary"], styles["BodyText"]),
        Spacer(1, 8),
        Paragraph("<b>2. Proposed Solution and Implementation Approach</b>", styles["Heading2"]),
        Paragraph(p["solution"], styles["BodyText"]),
        PageBreak(),
        Paragraph("<b>3. Timeline, Team and Milestones</b>", styles["Heading2"]),
        Paragraph(p["timeline"], styles["BodyText"]),
        Spacer(1, 10),
        Paragraph("<b>4. Price Table and Assumptions</b>", styles["Heading2"]),
        Table(
            [["Item", "Proposal"],
             ["Implementation", p["price"].split(" plus ")[0]],
             ["Annual support", p["price"].split(" plus ")[1].split(".")[0] if " plus " in p["price"] else "See proposal"],
             ["Assumptions", p["price"].split(". ", 1)[1] if ". " in p["price"] else "See proposal"]],
            colWidths=[45*mm, 125*mm],
            style=TableStyle([
                ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#312e81")),
                ("TEXTCOLOR", (0,0), (-1,0), colors.white),
                ("GRID", (0,0), (-1,-1), .4, colors.grey),
                ("VALIGN", (0,0), (-1,-1), "TOP"),
                ("PADDING", (0,0), (-1,-1), 6),
            ])
        ),
        PageBreak(),
        Paragraph("<b>5. Security, Compliance and Risk Controls</b>", styles["Heading2"]),
        Paragraph(p["security"], styles["BodyText"]),
        Spacer(1, 10),
        Paragraph("<b>6. Support, Experience and References</b>", styles["Heading2"]),
        Paragraph(p["support"], styles["BodyText"]),
        Spacer(1, 12),
        Paragraph("<b>Known Risks / Open Items</b>", styles["Heading2"]),
        Paragraph(
            "This synthetic document intentionally contains a mix of strengths, weaknesses and incomplete evidence so the evaluation workflow can demonstrate evidence-grounded scoring and validation.",
            styles["BodyText"],
        ),
    ]
    doc.build(story)
    print(path)

for filename, profile in profiles.items():
    make_pdf(filename, profile)
