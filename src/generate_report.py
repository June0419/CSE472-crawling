"""Generate the final CSE 472 Project I report as a polished PDF."""

from __future__ import annotations

import csv
import json
import os
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    Image,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

ROOT_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT_DIR / "data"
OUTPUT_DIR = ROOT_DIR / "output"
ANALYSIS_DIR = OUTPUT_DIR / "analysis"
FIGURE_DIR = OUTPUT_DIR / "figures"
GEHPI_DIR = OUTPUT_DIR / "gephi"
PDF_DIR = OUTPUT_DIR / "pdf"
REPORT_PATH = PDF_DIR / "CSE472_Project1_Report.pdf"

NAVY = colors.HexColor("#172033")
PURPLE = colors.HexColor("#6D28D9")
BLUE = colors.HexColor("#2563EB")
ORANGE = colors.HexColor("#EA580C")
SLATE = colors.HexColor("#536078")
LIGHT = colors.HexColor("#F4F6FA")
LINE = colors.HexColor("#D9E0EA")
WHITE = colors.white


def _csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def _paragraph(text: str, style: ParagraphStyle) -> Paragraph:
    return Paragraph(text, style)


def _styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "ReportTitle",
            parent=base["Title"],
            fontName="Helvetica-Bold",
            fontSize=27,
            leading=32,
            textColor=NAVY,
            alignment=TA_LEFT,
            spaceAfter=14,
        ),
        "subtitle": ParagraphStyle(
            "Subtitle",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=14,
            leading=20,
            textColor=SLATE,
            spaceAfter=9,
        ),
        "h1": ParagraphStyle(
            "H1",
            parent=base["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=17,
            leading=21,
            textColor=NAVY,
            spaceBefore=10,
            spaceAfter=8,
            keepWithNext=True,
        ),
        "h2": ParagraphStyle(
            "H2",
            parent=base["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=12.5,
            leading=16,
            textColor=PURPLE,
            spaceBefore=8,
            spaceAfter=5,
            keepWithNext=True,
        ),
        "body": ParagraphStyle(
            "Body",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=9.6,
            leading=13.6,
            textColor=NAVY,
            spaceAfter=7,
        ),
        "bullet": ParagraphStyle(
            "Bullet",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=9.4,
            leading=13,
            textColor=NAVY,
            leftIndent=14,
            firstLineIndent=-8,
            bulletIndent=2,
            spaceAfter=4,
        ),
        "caption": ParagraphStyle(
            "Caption",
            parent=base["Normal"],
            fontName="Helvetica-Oblique",
            fontSize=8.2,
            leading=11,
            textColor=SLATE,
            alignment=TA_CENTER,
            spaceBefore=4,
            spaceAfter=8,
        ),
        "small": ParagraphStyle(
            "Small",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=7.8,
            leading=10.4,
            textColor=NAVY,
        ),
        "small_header": ParagraphStyle(
            "SmallHeader",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=10,
            textColor=WHITE,
            alignment=TA_CENTER,
        ),
        "code": ParagraphStyle(
            "Code",
            parent=base["Code"],
            fontName="Courier",
            fontSize=7.4,
            leading=10,
            textColor=NAVY,
            leftIndent=8,
            rightIndent=8,
            borderColor=LINE,
            borderWidth=0.6,
            borderPadding=7,
            backColor=LIGHT,
            spaceBefore=4,
            spaceAfter=7,
        ),
        "run_code": ParagraphStyle(
            "RunCode",
            parent=base["Code"],
            fontName="Courier",
            fontSize=6.8,
            leading=8.4,
            textColor=NAVY,
            leftIndent=8,
            rightIndent=8,
            borderColor=LINE,
            borderWidth=0.6,
            borderPadding=6,
            backColor=LIGHT,
            spaceBefore=4,
            spaceAfter=7,
        ),
        "callout": ParagraphStyle(
            "Callout",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=10,
            leading=14,
            textColor=NAVY,
            leftIndent=12,
            rightIndent=12,
            borderColor=PURPLE,
            borderWidth=1.2,
            borderPadding=9,
            backColor=colors.HexColor("#F5F1FF"),
            spaceBefore=5,
            spaceAfter=9,
        ),
    }


def _table(
    data: list[list[object]],
    widths: list[float],
    styles: dict[str, ParagraphStyle],
    header: bool = True,
) -> Table:
    converted: list[list[object]] = []
    for row_index, row in enumerate(data):
        row_style = styles["small_header"] if header and row_index == 0 else styles["small"]
        converted.append(
            [cell if isinstance(cell, Paragraph) else Paragraph(escape(str(cell)), row_style) for cell in row]
        )
    table = Table(converted, colWidths=widths, repeatRows=1 if header else 0, hAlign="LEFT")
    commands: list[tuple] = [
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LINEBELOW", (0, 0), (-1, -1), 0.45, LINE),
    ]
    if header:
        commands.extend(
            [
                ("BACKGROUND", (0, 0), (-1, 0), NAVY),
                ("LINEBELOW", (0, 0), (-1, 0), 0.8, NAVY),
            ]
        )
    for index in range(1 if header else 0, len(data)):
        if index % 2 == 0:
            commands.append(("BACKGROUND", (0, index), (-1, index), LIGHT))
    table.setStyle(TableStyle(commands))
    return table


def _figure(path: Path, caption: str, styles: dict[str, ParagraphStyle], width: float = 6.55 * inch) -> KeepTogether:
    if not path.exists():
        raise FileNotFoundError(f"Required report figure not found: {path}")
    image = Image(str(path))
    image._restrictSize(width, 6.6 * inch)
    return KeepTogether([image, Paragraph(caption, styles["caption"])])


def _header_footer(canvas, document) -> None:
    canvas.saveState()
    width, height = letter
    canvas.setStrokeColor(LINE)
    canvas.setLineWidth(0.5)
    canvas.line(0.68 * inch, height - 0.48 * inch, width - 0.68 * inch, height - 0.48 * inch)
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(SLATE)
    canvas.drawString(0.68 * inch, height - 0.38 * inch, "CSE 472 | Project I | 2025 Palisades Fire")
    canvas.drawRightString(width - 0.68 * inch, 0.38 * inch, f"Page {document.page}")
    canvas.restoreState()


def _cover(canvas, document) -> None:
    canvas.saveState()
    width, height = letter
    canvas.setFillColor(NAVY)
    canvas.rect(0, height - 1.05 * inch, width, 1.05 * inch, fill=1, stroke=0)
    canvas.setFillColor(PURPLE)
    canvas.rect(0, 0, 0.14 * inch, height, fill=1, stroke=0)
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(SLATE)
    canvas.drawRightString(width - 0.7 * inch, 0.42 * inch, "Generated from the reproducible project pipeline")
    canvas.restoreState()


def _bullet(text: str, styles: dict[str, ParagraphStyle]) -> Paragraph:
    return Paragraph(f"• {text}", styles["bullet"])


def build_report() -> Path:
    PDF_DIR.mkdir(parents=True, exist_ok=True)
    styles = _styles()
    posts_payload = json.loads((DATA_DIR / "posts.json").read_text(encoding="utf-8"))
    users_payload = json.loads((DATA_DIR / "users.json").read_text(encoding="utf-8"))
    metrics = json.loads((ANALYSIS_DIR / "network_metrics.json").read_text(encoding="utf-8"))
    user_measures = _csv(ANALYSIS_DIR / "user_node_measures.csv")
    keyword_rows = _csv(ANALYSIS_DIR / "llm_keyword_frequencies.csv")
    keyword_examples = _csv(ANALYSIS_DIR / "post_keywords_llm.csv")[:5]
    prompt = (ANALYSIS_DIR / "llm_keyword_prompt.txt").read_text(encoding="utf-8").strip()

    info = metrics["information_diffusion"]
    users = metrics["user_interaction"]
    post_meta = posts_payload["metadata"]
    user_meta = users_payload["metadata"]
    top_users = sorted(
        user_measures, key=lambda row: -int(row["one_hop_relations"])
    )[:5]

    document = SimpleDocTemplate(
        str(REPORT_PATH),
        pagesize=letter,
        rightMargin=0.68 * inch,
        leftMargin=0.68 * inch,
        topMargin=0.62 * inch,
        bottomMargin=0.58 * inch,
        title="CSE 472 Project I - 2025 Palisades Fire on Mastodon",
        author=os.getenv("REPORT_AUTHOR", "CSE 472 Student"),
        subject="Social media data collection, network analysis, and LLM content analysis",
    )

    story: list[object] = []
    story.extend(
        [
            Spacer(1, 1.3 * inch),
            Paragraph("CSE 472: Social Media Mining", styles["subtitle"]),
            Paragraph("Project I - Social Media Data Analysis", styles["title"]),
            Spacer(1, 0.12 * inch),
            Paragraph("2025 Palisades Fire on Mastodon", ParagraphStyle(
                "CoverTopic", parent=styles["h1"], fontSize=20, leading=25, textColor=PURPLE, spaceAfter=12
            )),
            Paragraph(
                "Data collection, information diffusion, user interaction, network measures, and local LLM keyword analysis",
                styles["subtitle"],
            ),
            Spacer(1, 0.28 * inch),
            Table(
                [
                    [Paragraph("DATA", styles["small_header"]), Paragraph("NETWORKS", styles["small_header"]), Paragraph("CONTENT", styles["small_header"])],
                    [
                        Paragraph("500 focal posts<br/>200 users", styles["body"]),
                        Paragraph("2 network views<br/>Gephi layouts", styles["body"]),
                        Paragraph("1,500 LLM keywords<br/>500 posts x 3", styles["body"]),
                    ],
                ],
                colWidths=[2.05 * inch] * 3,
                style=TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
                        ("BACKGROUND", (0, 1), (-1, 1), LIGHT),
                        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                        ("BOX", (0, 0), (-1, -1), 0.7, LINE),
                        ("INNERGRID", (0, 0), (-1, -1), 0.5, LINE),
                        ("TOPPADDING", (0, 0), (-1, -1), 8),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                    ]
                ),
            ),
            Spacer(1, 0.35 * inch),
            Paragraph("Submission date: September 2026", styles["subtitle"]),
            Paragraph("Repository: github.com/June0419/CSE472-crawling", styles["subtitle"]),
            PageBreak(),
        ]
    )

    story.extend(
        [
            Paragraph("Executive Summary", styles["h1"]),
            Paragraph(
                "This project examines public Mastodon discussion of the 2025 Palisades Fire. It combines keyword-based post collection, seed-user expansion, two network views, Gephi visualization, structural network measures, and local Llama 3.2 keyword extraction. The final dataset contains 500 focal hashtag posts, 431 context posts retained for reply chains, and 200 relevant users.",
                styles["body"],
            ),
            Paragraph(
                f"The information-diffusion graph is highly fragmented ({info['components']} weak components; density {info['density']:.6f}), while the user network has a large component containing {users['largest_component_share']:.1%} of users. Its average degree is {users['average_degree']:.2f}. PageRank, degree, and betweenness distributions all show concentration around a small group of structurally prominent accounts. A local LLM generated exactly three keywords for each focal post, producing a 1,500-keyword corpus for the final word cloud.",
                styles["callout"],
            ),
            Paragraph("1. Disaster Event and Research Objective", styles["h1"]),
            Paragraph(
                "The Palisades Fire began on January 7, 2025, southeast of Palisades Drive in Pacific Palisades, Los Angeles County. CAL FIRE's incident record reports 23,448 acres burned, 6,845 structures destroyed, 975 damaged, and 12 confirmed civilian fatalities [1]. The event generated immediate safety information and longer-running discussion about evacuation, losses, recovery, insurance, policy, and secondary hazards.",
                styles["body"],
            ),
            Paragraph(
                "The objective is to study how disaster-related information appears and propagates on Mastodon, identify structurally important posts and users, and summarize the content themes with an LLM. Results describe the collected public sample rather than all Mastodon users or the wider population.",
                styles["body"],
            ),
            Paragraph("2. Data Collection", styles["h1"]),
            Paragraph("2.1 Keyword-based posts", styles["h2"]),
            Paragraph(
                "The collector queried the Mastodon REST API [2] on mastodon.social using three event-specific hashtags: <b>#PalisadesFire</b>, <b>#PacificPalisadesFire</b>, and <b>#PalisadesWildfire</b>. These terms combine the event name, affected location, and disaster type, reducing ambiguity while covering common naming variants. Posts were deduplicated by status ID. Reply-context requests added parent and descendant statuses needed to reconstruct conversation edges.",
                styles["body"],
            ),
            _table(
                [
                    ["Collection item", "Count / value"],
                    ["Focal hashtag posts", post_meta["hashtag_post_count"]],
                    ["Context posts for network edges", post_meta["context_post_count"]],
                    ["Total statuses stored", post_meta["collected_count"]],
                    ["Source instance", post_meta["source_instance"]],
                    ["Collected at (UTC)", post_meta["collected_at_utc"]],
                ],
                [2.8 * inch, 3.6 * inch],
                styles,
            ),
            Spacer(1, 0.08 * inch),
            Paragraph("2.2 User-based expansion", styles["h2"]),
            Paragraph(
                "Six seed accounts were selected after verifying that their collected posts addressed the Palisades Fire. They include active disaster-information accounts and journalists. The crawler expanded through mentions, replies, and reblogs, then filled remaining slots with authors of verified event posts. This produced 200 users and 170 unique undirected interaction edges.",
                styles["body"],
            ),
            Paragraph(
                "Seed users: " + ", ".join(f"@{escape(value)}" for value in user_meta["seed_users"]),
                styles["body"],
            ),
            Paragraph("2.3 Stored attributes and ethics", styles["h2"]),
            Paragraph(
                "The two required JSON datasets retain public post identifiers, timestamps, language, cleaned text, reply/reblog links, hashtags, engagement counts, account metadata, and interaction types. The project uses only public API responses, keeps the access token outside Git, and reports aggregate patterns. Usernames appear only where needed to interpret network prominence; centrality is not treated as credibility.",
                styles["body"],
            ),
        ]
    )

    story.extend(
        [
            Paragraph("3. Network Construction and Gephi Visualization", styles["h1"]),
            Paragraph(
                "Python and NetworkX [3] were used to construct both graphs and export GEXF/GraphML files. Gephi [4] provided the final layouts and styling. Node size is proportional to degree in both views. The project files retain every node; only isolated nodes are hidden from the report PNGs to improve legibility.",
                styles["body"],
            ),
            _table(
                [
                    ["Network", "Nodes", "Edges", "Direction", "Edge meaning"],
                    ["Information diffusion", info["nodes"], info["edges"], "Directed", "Parent/original post -> reply or reblog"],
                    ["User interaction", users["nodes"], users["edges"], "Undirected", "Mention, reply, or reblog interaction"],
                ],
                [1.45 * inch, 0.65 * inch, 0.65 * inch, 0.8 * inch, 2.9 * inch],
                styles,
            ),
            Spacer(1, 0.1 * inch),
            Paragraph("3.1 Information diffusion network", styles["h2"]),
            Paragraph(
                "Each node is a post or reply. A directed edge runs from a parent/original status to a collected reply or reblog. ForceAtlas2 was used so related cascades attract one another. Nodes are colored by post type and sized by degree.",
                styles["body"],
            ),
            _figure(
                GEHPI_DIR / "information_diffusion_gephi.png",
                "Figure 1. Information diffusion network in Gephi (ForceAtlas2; node size = degree; isolates hidden in the report image).",
                styles,
            ),
            PageBreak(),
            Paragraph("3.2 User interaction network", styles["h2"]),
            Paragraph(
                "Each node is a sampled account. An undirected weighted edge records at least one mention, reply, or reblog interaction; edge weight counts repeated interactions. Yifan Hu was used as a deliberately different layout. Node color represents Louvain community and node size represents degree.",
                styles["body"],
            ),
            _figure(
                GEHPI_DIR / "user_network_gephi.png",
                "Figure 2. User interaction network in Gephi (Yifan Hu; node size = degree; color = modularity community; isolates hidden in the report image).",
                styles,
            ),
            PageBreak(),
        ]
    )

    story.extend(
        [
            Paragraph("4. User Network Measures", styles["h1"]),
            Paragraph(
                "Three meaningful measures were selected: PageRank for recursive structural influence, degree for immediate 1-hop connectivity, and betweenness centrality for brokerage across shortest paths. The complete per-user values are in <i>user_node_measures.csv</i>.",
                styles["body"],
            ),
            _table(
                [
                    ["Metric", "Result"],
                    ["Average 1-hop relations (global mean degree)", f"{users['average_degree']:.2f}"],
                    ["Density", f"{users['density']:.6f}"],
                    ["Connected components", users["components"]],
                    ["Isolates", users["isolates"]],
                    ["Largest component", f"{users['largest_component_nodes']} users ({users['largest_component_share']:.1%})"],
                    ["Average clustering coefficient", f"{users['average_clustering']:.4f}"],
                    ["Louvain modularity", f"{users['modularity_louvain']:.4f}"],
                ],
                [3.45 * inch, 2.8 * inch],
                styles,
            ),
            Spacer(1, 0.08 * inch),
            Paragraph("4.1 PageRank", styles["h2"]),
            Paragraph(
                "The distribution is strongly right-skewed. Most users receive small PageRank scores, while a few hub accounts receive much larger values. This indicates concentrated structural influence rather than an evenly distributed interaction network.",
                styles["body"],
            ),
            _figure(
                FIGURE_DIR / "user_pagerank_distribution.png",
                "Figure 3. PageRank histogram. Log scales reveal the long upper tail while retaining the dense low-score region.",
                styles,
                width=6.25 * inch,
            ),
            PageBreak(),
            Paragraph("4.2 Degree and local/global connectivity", styles["h2"]),
            Paragraph(
                f"At the local level, each node's degree is its number of distinct immediate interaction partners. At the global level, the average is {users['average_degree']:.2f} relations per user. The coexistence of {users['isolates']} isolates with a 91-degree hub shows why the mean alone is not representative of the typical user.",
                styles["body"],
            ),
            _figure(
                FIGURE_DIR / "user_degree_distribution.png",
                "Figure 4. Degree distribution and the required global mean of 1-hop relations.",
                styles,
                width=6.25 * inch,
            ),
            Paragraph("4.3 Betweenness centrality", styles["h2"]),
            Paragraph(
                "Betweenness is zero for many users because they do not lie on a shortest path between other sampled accounts. The positive scores also form a long tail, so a small set of accounts bridges otherwise separated regions of the interaction graph.",
                styles["body"],
            ),
            _figure(
                FIGURE_DIR / "user_betweenness_distribution.png",
                "Figure 5. Betweenness distribution, separating zero values from the positive-score histogram.",
                styles,
                width=6.25 * inch,
            ),
            PageBreak(),
            Paragraph("4.4 Structurally prominent accounts", styles["h2"]),
            _table(
                [["Account", "Degree", "Weighted degree", "PageRank", "Betweenness"]]
                + [
                    [
                        f"@{row['account']}",
                        row["one_hop_relations"],
                        f"{float(row['weighted_relations']):.0f}",
                        f"{float(row['pagerank']):.5f}",
                        f"{float(row['betweenness_centrality']):.5f}",
                    ]
                    for row in top_users
                ],
                [2.15 * inch, 0.7 * inch, 0.9 * inch, 1.0 * inch, 1.0 * inch],
                styles,
            ),
            Paragraph(
                "The rankings show prominence inside this collected sample. They should not be interpreted as measures of authority, truthfulness, or influence outside the selected hashtags and seed expansion.",
                styles["body"],
            ),
        ]
    )

    story.extend(
        [
            Paragraph("5. LLM Content Analysis", styles["h1"]),
            Paragraph(
                "Llama 3.2 3B was run locally through Ollama. Structured JSON output [5] and temperature 0 were used to require exactly three distinct English keywords for each of the 500 focal hashtag posts. This yielded 1,500 keyword assignments. Local inference avoided sending public post text to a hosted LLM API. Llama 3.2 is an instruction-tuned text model intended for tasks including summarization [6].",
                styles["body"],
            ),
            Paragraph("5.1 Exact prompt", styles["h2"]),
            Paragraph(escape(prompt).replace("\n", "<br/>"), styles["code"]),
            Paragraph("5.2 Example outputs", styles["h2"]),
            _table(
                [["Post excerpt", "Three LLM keywords"]]
                + [
                    [
                        row["post_excerpt"][:180],
                        "; ".join(row[f"keyword_{index}"] for index in range(1, 4)),
                    ]
                    for row in keyword_examples
                ],
                [4.35 * inch, 2.0 * inch],
                styles,
            ),
            PageBreak(),
            Paragraph("5.3 Keyword frequency and word cloud", styles["h2"]),
            _figure(
                FIGURE_DIR / "palisades_fire_keyword_wordcloud.png",
                "Figure 6. Word cloud generated from the 1,500 LLM keywords. Word size is proportional to frequency.",
                styles,
            ),
            _figure(
                FIGURE_DIR / "palisades_fire_top_keywords.png",
                "Figure 7. The 15 most frequent normalized LLM keywords.",
                styles,
                width=6.25 * inch,
            ),
            Paragraph("5.4 Prominent and unexpected themes", styles["h2"]),
            _table(
                [["Rank", "Keyword", "Frequency", "Posts"]]
                + [
                    [
                        row["rank"],
                        row["keyword"],
                        row["frequency"],
                        f"{float(row['post_share_percent']):.1f}%",
                    ]
                    for row in keyword_rows[:12]
                ],
                [0.55 * inch, 3.35 * inch, 1.0 * inch, 1.0 * inch],
                styles,
            ),
            Paragraph(
                "The expected focal-event and Los Angeles terms dominate, but related-event and recovery topics also appear. In particular, Eaton Fire references show that users often discussed the January 2025 Los Angeles fires together. Weather, debris-flow, burn-scar, insurance, legal, and rebuilding terms demonstrate that the conversation extended beyond active flames into secondary hazards and long-term recovery. A sparse, unexpected tail including Will Rogers, Volkswagen, and Palestine reveals cross-topic hashtag reuse or incidental references; these terms were retained rather than manually removed.",
                styles["body"],
            ),
        ]
    )

    story.extend(
        [
            Paragraph("6. Limitations", styles["h1"]),
            _bullet("Mastodon is decentralized; mastodon.social returns only posts known to that instance.", styles),
            _bullet("Hashtag collection overrepresents users who tag posts and does not capture all relevant discussion.", styles),
            _bullet("Reply context was capped, so some cascades may remain incomplete.", styles),
            _bullet("The 200-user graph is a relevance-focused sample expanded from six seeds, not the complete social graph.", styles),
            _bullet("Centrality measures are sensitive to sampling and edge definitions.", styles),
            _bullet("A 3B-parameter LLM can simplify or inconsistently normalize themes; structured output and transparent post-level results make auditing possible.", styles),
            Paragraph("7. Reproducibility and Run Instructions", styles["h1"]),
            Paragraph(
                "Create the virtual environment, install dependencies, add the Mastodon token only to <i>.env</i>, and run the pipeline below. The real token is excluded from Git. Ollama and the Llama 3.2 model are required only for the LLM step.",
                styles["body"],
            ),
            Paragraph(
                escape(
                    "python -m venv .venv\n"
                    ".\\.venv\\Scripts\\Activate.ps1\n"
                    "python -m pip install -r requirements.txt\n"
                    "python src/test_connection.py\n"
                    "python src/collect_posts.py\n"
                    "python src/collect_users.py\n"
                    "python src/build_networks.py\n"
                    "python src/analyze_networks.py\n"
                    "python src/plot_user_measures.py\n"
                    "ollama pull llama3.2:3b\n"
                    "python src/extract_keywords_llm.py\n"
                    "python src/analyze_content.py\n"
                    "python src/generate_report.py"
                ).replace("\n", "<br/>"),
                styles["run_code"],
            ),
            Paragraph("8. References", styles["h1"]),
            Paragraph("[1] CAL FIRE. <i>Palisades Fire incident record</i>. https://www.fire.ca.gov/incidents/2025/1/7/palisades-fire", styles["body"]),
            Paragraph("[2] Mastodon Documentation. <i>API introduction and timelines</i>. https://docs.joinmastodon.org/client/intro/", styles["body"]),
            Paragraph("[3] NetworkX Developers. <i>NetworkX documentation</i>. https://networkx.org/documentation/stable/", styles["body"]),
            Paragraph("[4] Gephi. <i>The Open Graph Viz Platform</i>. https://gephi.org/", styles["body"]),
            Paragraph("[5] Ollama. <i>Structured Outputs</i>. https://docs.ollama.com/capabilities/structured-outputs", styles["body"]),
            Paragraph("[6] Ollama Model Library. <i>Llama 3.2</i>. https://ollama.com/library/llama3.2", styles["body"]),
            Paragraph("[7] Mueller, A. <i>word_cloud documentation</i>. https://amueller.github.io/word_cloud/", styles["body"]),
            Paragraph("[8] Bastian, M., Heymann, S., and Jacomy, M. (2009). <i>Gephi: An Open Source Software for Exploring and Manipulating Networks</i>. ICWSM.", styles["body"]),
        ]
    )

    document.build(story, onFirstPage=_cover, onLaterPages=_header_footer)
    return REPORT_PATH


def main() -> None:
    path = build_report()
    print(f"Report written to {path}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        raise SystemExit(f"Report generation failed: {exc}") from exc
