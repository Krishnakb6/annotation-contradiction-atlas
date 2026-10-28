"""
Refined, publication-quality presentation builder for
'The Annotation Contradiction Atlas' (16 Slides).
Clean academic typography, precise benchmark metrics, Unicode formatting (no raw LaTeX),
and perfectly fitted screenshot cards.
"""
import os
import shutil
from PIL import Image
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.enum.shapes import MSO_SHAPE

PHOTO_DIR = r"C:\Users\krish\Downloads\bd photos"
ARCH_IMG = r"docs\presentation_assets\system_architecture.png"
OUTPUT_DIR = "docs"
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "Annotation_Contradiction_Atlas_Presentation.pptx")
DOWNLOADS_FILE = r"C:\Users\krish\Downloads\Annotation_Contradiction_Atlas_Presentation.pptx"

# Color Palette (Clean Academic Theme)
COLOR_CARD_BG = RGBColor(248, 250, 252)       # Light Slate (#F8FAFC)
COLOR_CARD_BORDER = RGBColor(226, 232, 240)   # Slate Border (#E2E8F0)
COLOR_NAVY = RGBColor(15, 23, 42)             # Deep Navy Title (#0F172A)
COLOR_BLUE_TAG = RGBColor(29, 78, 216)        # Accent Blue (#1D4ED8)
COLOR_TAG_BG = RGBColor(239, 246, 255)        # Light Blue Pill (#EFF6FF)
COLOR_BODY = RGBColor(30, 41, 59)             # Body Dark Slate (#1E293B)
COLOR_MUTED = RGBColor(100, 116, 139)         # Muted Slate (#64748B)


def add_header(slide, title, category="RESEARCH PRESENTATION", subtitle=""):
    """Standardized clean academic header."""
    # Category Tag Pill
    tag_box = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(0.38), Inches(3.0), Inches(0.32))
    tag_box.fill.solid()
    tag_box.fill.fore_color.rgb = COLOR_TAG_BG
    tag_box.line.color.rgb = RGBColor(191, 219, 254)
    tag_box.line.width = Pt(1)
    tf = tag_box.text_frame
    tf.word_wrap = True
    tf.margin_top = tf.margin_bottom = tf.margin_left = tf.margin_right = 0
    p = tf.paragraphs[0]
    p.text = category.upper()
    p.font.size = Pt(9.5)
    p.font.bold = True
    p.font.color.rgb = COLOR_BLUE_TAG
    p.font.name = "Calibri"
    p.alignment = PP_ALIGN.CENTER

    # Slide Title
    title_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.72), Inches(11.7), Inches(0.55))
    tf = title_box.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    p = tf.paragraphs[0]
    p.text = title
    p.font.size = Pt(22)
    p.font.bold = True
    p.font.color.rgb = COLOR_NAVY
    p.font.name = "Calibri"

    # Subtitle
    if subtitle:
        sub_box = slide.shapes.add_textbox(Inches(0.8), Inches(1.30), Inches(11.7), Inches(0.32))
        tf = sub_box.text_frame
        tf.word_wrap = True
        tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
        p = tf.paragraphs[0]
        p.text = subtitle
        p.font.size = Pt(11.5)
        p.font.color.rgb = COLOR_MUTED
        p.font.name = "Calibri"

    # Subtle divider line
    divider = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.8), Inches(1.68), Inches(11.7), Inches(0.015))
    divider.fill.solid()
    divider.fill.fore_color.rgb = COLOR_CARD_BORDER
    divider.line.fill.background()


def add_footer(slide, current_slide, total_slides=16):
    """Standardized clean footer."""
    lbl_box = slide.shapes.add_textbox(Inches(0.8), Inches(7.05), Inches(8.0), Inches(0.3))
    tf = lbl_box.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    p = tf.paragraphs[0]
    p.text = "The Annotation Contradiction Atlas • Human Kinome Biocuration"
    p.font.size = Pt(9)
    p.font.color.rgb = COLOR_MUTED
    p.font.name = "Calibri"

    num_box = slide.shapes.add_textbox(Inches(10.5), Inches(7.05), Inches(2.0), Inches(0.3))
    tf = num_box.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    p = tf.paragraphs[0]
    p.text = f"Slide {current_slide} of {total_slides}"
    p.font.size = Pt(9)
    p.font.color.rgb = COLOR_MUTED
    p.font.name = "Calibri"
    p.alignment = PP_ALIGN.RIGHT


def add_structured_card(slide, left, top, width, height, title, items, bg_color=COLOR_CARD_BG, border_color=COLOR_CARD_BORDER):
    """
    Renders a clean card where items is a list of tuples:
    (title, description, is_sub_bullet)
    Guarantees no empty bullets, clean typography, and bold lead-ins.
    """
    card = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height)
    card.fill.solid()
    card.fill.fore_color.rgb = bg_color
    card.line.color.rgb = border_color
    card.line.width = Pt(1)

    tx_box = slide.shapes.add_textbox(left + Inches(0.22), top + Inches(0.20), width - Inches(0.44), height - Inches(0.40))
    tf = tx_box.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0

    # Card title
    p0 = tf.paragraphs[0]
    p0.text = title
    p0.font.size = Pt(13)
    p0.font.bold = True
    p0.font.color.rgb = COLOR_NAVY
    p0.font.name = "Calibri"
    p0.space_after = Pt(8)

    for item in items:
        # item: (item_title, item_desc) or (item_title, item_desc, is_sub)
        is_sub = False
        if len(item) == 3:
            item_title, item_desc, is_sub = item
        else:
            item_title, item_desc = item

        p = tf.add_paragraph()
        p.font.name = "Calibri"
        p.space_after = Pt(6)

        if is_sub:
            p.level = 1
            p.font.size = Pt(10)
            if item_title:
                r1 = p.add_run()
                r1.text = "– " + item_title + (": " if item_desc else "")
                r1.font.bold = True
                r1.font.color.rgb = COLOR_NAVY
            if item_desc:
                r2 = p.add_run()
                r2.text = item_desc
                r2.font.bold = False
                r2.font.color.rgb = COLOR_BODY
        else:
            p.level = 0
            p.font.size = Pt(10.5)
            if item_title:
                r1 = p.add_run()
                r1.text = "• " + item_title + (": " if item_desc else "")
                r1.font.bold = True
                r1.font.color.rgb = COLOR_NAVY
            if item_desc:
                r2 = p.add_run()
                r2.text = item_desc
                r2.font.bold = False
                r2.font.color.rgb = COLOR_BODY


def add_image_card(slide, left, top, width, height, image_path, caption=""):
    """Inserts an image inside a neat white frame with preserved aspect ratio and caption."""
    if not os.path.exists(image_path):
        print(f"Warning: Image path missing: {image_path}")
        return

    # Frame card
    card = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, left, top, width, height)
    card.fill.solid()
    card.fill.fore_color.rgb = RGBColor(255, 255, 255)
    card.line.color.rgb = RGBColor(203, 213, 225)
    card.line.width = Pt(1)

    # Calculate dimensions
    with Image.open(image_path) as img:
        img_w, img_h = img.size
    aspect = img_w / img_h

    avail_h = height - Inches(0.40 if caption else 0.12)
    avail_w = width - Inches(0.16)

    box_aspect = avail_w / avail_h
    if aspect > box_aspect:
        disp_w = avail_w
        disp_h = avail_w / aspect
    else:
        disp_h = avail_h
        disp_w = avail_h * aspect

    offset_x = left + (width - disp_w) / 2
    offset_y = top + Inches(0.06) + (avail_h - disp_h) / 2

    slide.shapes.add_picture(image_path, offset_x, offset_y, disp_w, disp_h)

    if caption:
        cap_box = slide.shapes.add_textbox(left, top + height - Inches(0.34), width, Inches(0.28))
        tf = cap_box.text_frame
        tf.word_wrap = True
        tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
        p = tf.paragraphs[0]
        p.text = caption
        p.font.size = Pt(8.5)
        p.font.italic = True
        p.font.color.rgb = COLOR_MUTED
        p.font.name = "Calibri"
        p.alignment = PP_ALIGN.CENTER


def add_notes(slide, text):
    """Sets presenter speaker notes."""
    tf = slide.notes_slide.notes_text_frame
    tf.text = text


def build_all_slides():
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    blank = prs.slide_layouts[6]

    # =========================================================================
    # SLIDE 1: TITLE SLIDE
    # =========================================================================
    s1 = prs.slides.add_slide(blank)
    bg = s1.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(0.8), Inches(11.733), Inches(5.9))
    bg.fill.solid()
    bg.fill.fore_color.rgb = RGBColor(241, 245, 249)
    bg.line.color.rgb = RGBColor(203, 213, 225)
    bg.line.width = Pt(1.5)

    tb = s1.shapes.add_textbox(Inches(1.3), Inches(1.2), Inches(10.7), Inches(0.35))
    p = tb.text_frame.paragraphs[0]
    p.text = "BIOLOGICAL DATABASES & KNOWLEDGE DISCOVERY • COURSE PROJECT"
    p.font.size = Pt(11)
    p.font.bold = True
    p.font.color.rgb = COLOR_BLUE_TAG

    tb2 = s1.shapes.add_textbox(Inches(1.3), Inches(1.65), Inches(10.7), Inches(1.6))
    tf2 = tb2.text_frame
    tf2.word_wrap = True
    p2 = tf2.paragraphs[0]
    p2.text = "The Annotation Contradiction Atlas"
    p2.font.size = Pt(32)
    p2.font.bold = True
    p2.font.color.rgb = COLOR_NAVY
    p2.space_after = Pt(6)

    psub = tf2.add_paragraph()
    psub.text = "An Evidence-Aware Database & Decision-Support System for Detecting Potentially Inconsistent Human Protein Kinase Annotations"
    psub.font.size = Pt(15.5)
    psub.font.color.rgb = COLOR_MUTED

    div = s1.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(1.3), Inches(3.45), Inches(10.7), Inches(0.015))
    div.fill.solid()
    div.fill.fore_color.rgb = RGBColor(203, 213, 225)
    div.line.fill.background()

    meta = s1.shapes.add_textbox(Inches(1.3), Inches(3.75), Inches(5.8), Inches(2.3))
    tf3 = meta.text_frame
    tf3.word_wrap = True
    p = tf3.paragraphs[0]
    p.text = "Project Team Members:"
    p.font.size = Pt(12)
    p.font.bold = True
    p.font.color.rgb = COLOR_NAVY
    p.space_after = Pt(4)

    for m in ["A. Sai Charan", "Sri Rithvik", "Krishna Kiriti"]:
        pm = tf3.add_paragraph()
        pm.text = f"•  {m}"
        pm.font.size = Pt(12.5)
        pm.font.color.rgb = COLOR_BODY
        pm.space_after = Pt(2)

    pd = tf3.add_paragraph()
    pd.space_before = Pt(8)
    pd.text = "Department of Computer Science and Engineering"
    pd.font.size = Pt(11)
    pd.font.color.rgb = COLOR_MUTED

    # Highlights card
    s1_c = s1.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(7.5), Inches(3.75), Inches(4.5), Inches(2.4))
    s1_c.fill.solid()
    s1_c.fill.fore_color.rgb = RGBColor(255, 255, 255)
    s1_c.line.color.rgb = RGBColor(191, 219, 254)
    s1_c.line.width = Pt(1)
    s1_ctf = s1_c.text_frame
    s1_ctf.word_wrap = True
    p = s1_ctf.paragraphs[0]
    p.text = "Core System Overview"
    p.font.size = Pt(12)
    p.font.bold = True
    p.font.color.rgb = COLOR_NAVY
    p.space_after = Pt(6)

    overview_points = [
        ("Dataset Scale", "500 human kinases & 5,464 UniProt annotations"),
        ("Multi-Evidence", "ESM-2 language model + Motifs + Alignment + ECO"),
        ("Triage Logic", "Explicit segregation of biological exceptions (pseudokinases)"),
        ("Interactive Web UI", "Streamlit platform with reproducible benchmark suite")
    ]
    for k, v in overview_points:
        pb = s1_ctf.add_paragraph()
        pb.space_after = Pt(3)
        r1 = pb.add_run()
        r1.text = "✔ " + k + ": "
        r1.font.bold = True
        r1.font.size = Pt(10)
        r1.font.color.rgb = COLOR_NAVY
        r2 = pb.add_run()
        r2.text = v
        r2.font.size = Pt(10)
        r2.font.color.rgb = COLOR_BODY

    add_notes(s1, "Good morning/afternoon. Today we present The Annotation Contradiction Atlas. This project creates an evidence-aware database and decision-support triage system to detect potentially misannotated human protein kinase functions in public databases.")

    # =========================================================================
    # SLIDE 2: MOTIVATION & PROBLEM STATEMENT
    # =========================================================================
    s2 = prs.slides.add_slide(blank)
    add_header(s2, "The Annotation Inconsistency Challenge in Protein Databases", "SCIENTIFIC MOTIVATION", "Why automated functional transfer causes transitive error propagation across repositories")
    add_footer(s2, 2)

    add_structured_card(s2, Inches(0.8), Inches(1.85), Inches(4.8), Inches(5.0), "The Biocuration Challenge", [
        ("Exponential Sequence Growth", "Next-generation sequencing produces protein sequences far faster than manual biochemical experiments can characterize them."),
        ("Automated Inheritance Hazard", "Curated repositories (UniProtKB) rely heavily on automated homology transfer; erroneous or ambiguous functional labels are systematically propagated to newly sequenced homologs."),
        ("Subtle Biological Context", "A divergent sequence or missing catalytic motif is not necessarily an error; it may be an allosteric regulator, an atypical kinase, or a natural pseudokinase."),
        ("Core Research Question", "Can integrating protein language models, sequence similarity, catalytic motif checks, and annotation provenance prioritize inconsistencies more explainably than individual methods?"),
        ("Project Objective", "Build a transparent decision-support triage assistant—not an automated oracle—for expert biocurators.")
    ])

    add_image_card(s2, Inches(5.8), Inches(1.85), Inches(6.7), Inches(5.0),
                   os.path.join(PHOTO_DIR, "WhatsApp Image 2026-10-28 at 21.25.01.jpeg"),
                   "Figure 1: Scientific motivation, research question, and conserved kinase architecture documentation.")

    add_notes(s2, "Biomedical research relies heavily on curated databases like UniProtKB. However, automated inheritance creates a dangerous error propagation loop. A key nuance is that unusual sequences are not always wrong—some are natural pseudokinases.")

    # =========================================================================
    # SLIDE 3: SYSTEM ARCHITECTURE & DATA FLOW
    # =========================================================================
    s3 = prs.slides.add_slide(blank)
    add_header(s3, "End-to-End System Architecture & Data Flow", "SYSTEM ARCHITECTURE", "Four independent computational evidence layers feed into an evidence-aware triage engine")
    add_footer(s3, 3)

    add_structured_card(s3, Inches(0.8), Inches(1.85), Inches(4.5), Inches(5.0), "Architectural Pipeline", [
        ("1. UniProtKB Data Ingestion", "Ingests 500 human protein kinases, 5,464 functional annotations, and Evidence & Conclusion Ontology (ECO) codes."),
        ("2. Multi-Evidence Analysis", "Combines four distinct analytical perspectives:"),
        ("ESM-2 Language Model", "Dense 320-d embeddings from esm2_t6_8M_UR50D for manifold anomaly scoring.", True),
        ("Sequence Similarity", "Needleman-Wunsch & k-mer Jaccard overlap to find nearest characterized reference.", True),
        ("Catalytic Motif Scanner", "Checks canonical VAIK, HRD, and DFG subdomains with strict linear order.", True),
        ("Annotation Provenance", "Categorizes ECO codes into Experimental, Phylogenetic, Computational, and Author tiers.", True),
        ("3. Evidence Scoring Engine", "Computes a weighted contradiction index (0.0 to 1.0) with calibrated thresholds."),
        ("4. Streamlit Decision Atlas", "Routes entries into dual triage queues: suspected conflicts vs biological exceptions.")
    ])

    add_image_card(s3, Inches(5.5), Inches(1.85), Inches(7.0), Inches(5.0),
                   ARCH_IMG,
                   "Figure 2: End-to-end pipeline from UniProt ingestion through four evidence engines to Streamlit decision queues.")

    add_notes(s3, "Our pipeline has four main stages: UniProt data ingestion, four multi-evidence engines, an evidence-aware scoring engine, and dual-queue triage in Streamlit.")

    # =========================================================================
    # SLIDE 4: CONSERVED CATALYTIC ARCHITECTURE
    # =========================================================================
    s4 = prs.slides.add_slide(blank)
    add_header(s4, "Conserved Protein Kinase Catalytic Triad & Motif Rules", "BIOLOGICAL DOMAIN KNOWLEDGE", "Essential biochemical landmarks required for canonical phosphotransfer activity")
    add_footer(s4, 4)

    add_structured_card(s4, Inches(0.8), Inches(1.85), Inches(4.8), Inches(5.0), "The Catalytic Triad", [
        ("Subdomain II — VAIK Motif", "Consensus: [LIVMAFY][AVILMF][IVATC][K]. Invariant Lysine (K) forms critical salt bridges with alpha- and beta-phosphates of ATP to orient the triphosphate chain for attack."),
        ("Subdomain VIB — HRD Motif", "Consensus: [HYF][RKN][D]. Invariant Aspartate (D) acts as the catalytic base accepting a proton from the substrate hydroxyl group (Ser/Thr/Tyr)."),
        ("Subdomain VII — DFG Motif", "Consensus: [D][FYSW][GSA]. Invariant Aspartate (D) coordinates divalent magnesium (Mg²⁺), stabilizing the ATP phosphate chain during transfer."),
        ("Strict Spatial Ordering", "Motifs must appear in strict linear order: VAIK -> HRD -> DFG. Disruptions or reversed spacing signal domain rearrangements or non-standard architectures.")
    ])

    add_image_card(s4, Inches(5.8), Inches(1.85), Inches(6.7), Inches(5.0),
                   os.path.join(PHOTO_DIR, "WhatsApp Image 2026-10-28 at 22.12.01.jpeg"),
                   "Figure 3: Conserved catalytic motifs table and primary sequence highlighter showing VAIK, HKD, and DFG landmarks.")

    add_notes(s4, "The catalytic triad consists of VAIK in subdomain II, HRD in subdomain VIB, and DFG in subdomain VII. Our system verifies both motif sequence identity and their linear spatial order.")

    # =========================================================================
    # SLIDE 5: ATLAS OVERVIEW & PROVENANCE TIERS
    # =========================================================================
    s5 = prs.slides.add_slide(blank)
    add_header(s5, "Atlas Overview: 500 Human Kinases & Evidence Tiers", "DATABASE COMPOSITION", "Ingestion scale, baseline review distribution, and evidence provenance breakdown")
    add_footer(s5, 5)

    add_structured_card(s5, Inches(0.8), Inches(1.85), Inches(4.8), Inches(5.0), "Database Summary Metrics", [
        ("Curated Ingestion Scale", "500 human protein kinases imported from UniProtKB/Swiss-Prot (Taxonomy ID: 9606) with 5,464 individual functional annotation statements."),
        ("Experimental Provenance (84.8%)", "4,634 annotations supported by direct in vitro biochemical assays (ECO:0000269)."),
        ("Phylogenetic Curated (7.3%)", "401 annotations transferred through expert phylogenetic curation (ECO:0000250)."),
        ("Unspecified & Author Statements", "336 baseline records (6.1%) and 93 author statements (1.7%, ECO:0000305)."),
        ("Baseline Review Distribution", "97.3% evaluated as congruent / low review priority; 2.7% flagged for moderate review."),
        ("Reproducible Checkpointing", "Run ID RUN_20261023_232805_4412ea completed under random seed 42.")
    ])

    add_image_card(s5, Inches(5.8), Inches(1.85), Inches(6.7), Inches(5.0),
                   os.path.join(PHOTO_DIR, "WhatsApp Image 2026-10-28 at 21.24.55.jpeg"),
                   "Figure 4: Atlas Overview Dashboard showing database metrics, review priority donut chart, and evidence tier histogram.")

    add_notes(s5, "Slide 5 shows the live dashboard view. We imported 500 human kinases and 5,464 annotations. Over 84% have direct experimental evidence, allowing the system to use high-confidence records as reference anchors.")

    # =========================================================================
    # SLIDE 6: SUSPECTED ANNOTATION CONFLICTS QUEUE
    # =========================================================================
    s6 = prs.slides.add_slide(blank)
    add_header(s6, "Prioritized Review Queue for Potential Inconsistencies", "BIOCURATION TRIAGE", "Ordinary review queue for candidates exhibiting multi-evidence computational discordance")
    add_footer(s6, 6)

    add_structured_card(s6, Inches(0.8), Inches(1.85), Inches(4.7), Inches(5.0), "Triage Workspace Highlights", [
        ("Focused Biocurator Queue", "Isolates proteins exhibiting conflicting computational signals across sequence similarity, catalytic motifs, or ESM-2 embeddings."),
        ("Exclusion of Biological Exceptions", "Natural pseudokinases are excluded by default to ensure the queue focuses strictly on suspected annotation errors."),
        ("Interactive Filtering Controls", "Allows curators to filter candidates by review priority tier (High, Moderate), primary discordant signal, or evidence tier."),
        ("Live Candidate: SPEG (Q15772)", "Striated muscle preferentially expressed kinase flagged with Moderate review priority (Score: 0.407)."),
        ("Primary Discordant Signal", "Low reference sequence homology (5.2% identity) and motif ordering deviations warranting manual inspection.")
    ])

    add_image_card(s6, Inches(5.7), Inches(1.85), Inches(6.8), Inches(5.0),
                   os.path.join(PHOTO_DIR, "WhatsApp Image 2026-10-28 at 21.24.90.jpeg"),
                   "Figure 5: Contradiction Explorer queue isolating suspected annotation conflicts with explicit filtering options.")

    add_notes(s6, "Here is the Contradiction Explorer review queue. It prioritizes entries by contradiction score. SPEG is flagged with Moderate priority due to low homology and inverted motif positions, providing a clear triage candidate.")

    # =========================================================================
    # SLIDE 7: SIDE-BY-SIDE REFERENCE COMPARISON
    # =========================================================================
    s7 = prs.slides.add_slide(blank)
    add_header(s7, "Inspect Candidates Against Characterized Reference Kinases", "COMPARATIVE INSPECTION", "Side-by-side alignment of motif boundaries, sequence identity, and functional annotations")
    add_footer(s7, 7)

    add_structured_card(s7, Inches(0.8), Inches(1.85), Inches(4.7), Inches(5.0), "Explainable Biocuration Support", [
        ("Transparent Comparative Triage", "Instead of presenting an opaque numerical score, the system pairs candidates directly with their closest characterized reference kinase."),
        ("Candidate Profile (SPEG / Q15772)", "Motifs detected at HRD (position 77), DFG (position 1035), and VAIK (position 1627)."),
        ("Reference Profile (LMTK3 / Q96Q04)", "Canonical linear motif spacing: VAIK at 161, HRD at 178, DFG at 284."),
        ("Sequence Identity", "5.2% global alignment identity against nearest characterized kinase."),
        ("Actionable Curator Insight", "The inverted motif spacing explains the high anomaly score without assuming an outright clerical error, pointing curators to multi-domain architecture.")
    ])

    add_image_card(s7, Inches(5.7), Inches(1.85), Inches(6.8), Inches(5.0),
                   os.path.join(PHOTO_DIR, "WhatsApp Image 2026-10-28 at 21.24.58.jpeg"),
                   "Figure 6: Side-by-side reference comparison comparing candidate kinase SPEG against closest reference LMTK3.")

    add_notes(s7, "Slide 7 shows our side-by-side reference comparison tool. Looking at SPEG side-by-side with LMTK3 reveals that the catalytic motifs are separated across thousands of amino acids, suggesting multidomain architecture.")

    # =========================================================================
    # SLIDE 8: BIOLOGICAL EXCEPTIONS VS MISANNOTATIONS
    # =========================================================================
    s8 = prs.slides.add_slide(blank)
    add_header(s8, "Pseudokinases Are Biological Exceptions, Not Errors", "SCIENTIFIC DISTINCTION", "Rigorous segregation between natural evolutionary divergence and clerical database mistakes")
    add_footer(s8, 8)

    add_structured_card(s8, Inches(0.8), Inches(1.85), Inches(5.7), Inches(5.0), "The Pseudokinase Challenge", [
        ("Prevalence in Human Kinome", "Approximately 10% of all human protein kinases are pseudokinases—proteins structurally homologous to kinases that have lost catalytic phosphotransfer activity."),
        ("Legitimate Biological Functions", "Pseudokinases act as vital allosteric regulators, scaffold complexes, and signaling switches (e.g. VRK3, ILK, STRAD-alpha)."),
        ("Evolutionary Adaptation", "Missing catalytic motifs reflect millions of years of evolutionary adaptation, not clerical or functional database errors."),
        ("Triage False-Alarm Hazard", "If a system treats missing motifs as proof of misannotation, pseudokinases will flood the review queue with false alarms."),
        ("Architectural Safeguard", "The Atlas routes pseudokinases to an independent Biological Exceptions tab with diagnostic divergence scores and explicit caveats.")
    ])

    add_structured_card(s8, Inches(6.8), Inches(1.85), Inches(5.7), Inches(5.0), "Operational Queue Distinction", [
        ("Queue A: Suspected Conflicts", "Focus: Potential clerical errors, unverified automated transfers, and misassigned catalytic activities."),
        ("Triage Goal", "Prioritize entries for biocurator re-annotation or manual verification.", True),
        ("Primary Metric", "Review Priority (High, Moderate, Low).", True),
        ("Action", "Submit review flag to UniProt biocuration team.", True),
        ("Queue B: Biological Exceptions", "Focus: Characterize legitimate non-catalytic variants and pseudokinases."),
        ("Triage Goal", "Quantify degree of structural divergence from canonical active kinases.", True),
        ("Primary Metric", "Diagnostic Contradiction Score (divergence index).", True),
        ("Action", "Document scaffolding role and atypical subdomain signatures.", True)
    ], bg_color=RGBColor(239, 246, 255), border_color=RGBColor(191, 219, 254))

    add_notes(s8, "This is a key conceptual distinction: pseudokinases represent about 10% of human kinases. They are not mistakes—they are natural scaffolds. We isolate them in a separate queue so they don't generate false positives.")

    # =========================================================================
    # SLIDE 9: CASE STUDY: VRK3 & ILK
    # =========================================================================
    s9 = prs.slides.add_slide(blank)
    add_header(s9, "Deep Dive Case Study: Human Pseudokinases VRK3 & ILK", "EMPIRICAL CASE STUDY", "Validating system response on naturally occurring, experimentally characterized pseudokinases")
    add_footer(s9, 9)

    add_structured_card(s9, Inches(0.8), Inches(1.85), Inches(4.8), Inches(5.0), "Empirical Case Study Findings", [
        ("VRK3 (Q9Y616) — Inactive Ser/Thr Kinase", "Assigned annotation: Inactive serine/threonine-protein kinase VRK3."),
        ("VRK3 Atypical Motifs", "Catalytic loop mutated from HRD to HGA; activation segment altered from DFG to SSG.", True),
        ("Diagnostic Score", "0.4537 (Moderate structural divergence).", True),
        ("Biological Function", "Nuclear scaffold that activates VHR phosphatase and suppresses ERK signaling.", True),
        ("ILK (Q13418) — Integrin-Linked Kinase", "Assigned annotation: Integrin-linked protein kinase (pseudokinase)."),
        ("ILK Atypical Motifs", "Catalytic loop mutated to FKK; activation segment altered to DFF.", True),
        ("Diagnostic Score", "0.7167 (High structural divergence).", True),
        ("Biological Function", "Core focal adhesion scaffold connecting integrins to the actin cytoskeleton.", True),
        ("System Verification", "Both correctly flagged for structural divergence without being mislabeled as database errors.")
    ])

    add_image_card(s9, Inches(5.8), Inches(1.85), Inches(6.7), Inches(5.0),
                   os.path.join(PHOTO_DIR, "WhatsApp Image 2026-10-28 at 21.24.57.jpeg"),
                   "Figure 7: Biological Exceptions detail view showing characterization priority, motif summaries, and explicit scientific caveats for VRK3 and ILK.")

    add_notes(s9, "Slide 9 inspects VRK3 and ILK directly. VRK3 has HGA and SSG mutations; ILK has FKK and DFF mutations. Our platform accurately measures their structural divergence while confirming their valid non-catalytic annotations.")

    # =========================================================================
    # SLIDE 10: CANONICAL CONTROL: EGFR (P00533)
    # =========================================================================
    s10 = prs.slides.add_slide(blank)
    add_header(s10, "Canonical Reference Inspection: EGFR (P00533)", "CANONICAL CONTROL", "Validating multi-evidence congruence on a fully characterized receptor tyrosine kinase")
    add_footer(s10, 10)

    add_structured_card(s10, Inches(0.8), Inches(1.85), Inches(4.7), Inches(5.0), "Multi-Evidence Synthesis", [
        ("Gold-Standard Active Control", "Epidermal Growth Factor Receptor (1,210 aa) serves as a canonical active receptor tyrosine kinase control."),
        ("Catalytic Motif Integrity", "Anomaly score = 0.000. All 3 canonical subdomains fully intact (VAIK pos 742, HKD pos 805, DFG pos 855)."),
        ("ESM-2 Manifold Position", "Anomaly score = 0.036. Firmly centered on the active kinase embedding manifold."),
        ("Evidence Provenance", "Experimental tier backed by 38 distinct Swiss-Prot records with direct PubMed literature citations."),
        ("System Decision", "Classified as Congruent / Low Review Priority (Composite score: 0.26). Confirms zero false alarms on standard active kinases.")
    ])

    add_image_card(s10, Inches(5.7), Inches(1.85), Inches(6.8), Inches(5.0),
                   os.path.join(PHOTO_DIR, "WhatsApp Image 2026-10-28 at 22.12.02.jpeg"),
                   "Figure 8: Protein record for EGFR (P00533) showing radar component anomaly breakdown and analytical evidence synthesis.")

    add_notes(s10, "Slide 10 demonstrates our canonical control: EGFR. The radar chart shows zero motif anomaly, an ESM-2 anomaly score of only 0.036, and strong experimental provenance, correctly resulting in Low Review Priority.")

    # =========================================================================
    # SLIDE 11: BENCHMARK V2 EXPERIMENTAL SETUP
    # =========================================================================
    s11 = prs.slides.add_slide(blank)
    add_header(s11, "Scientific Benchmark v2: Experimental Design", "BENCHMARK METHODOLOGY", "Controlled synthetic perturbations, natural exceptions, and a strict zero-leakage split")
    add_footer(s11, 11)

    add_structured_card(s11, Inches(0.8), Inches(1.85), Inches(5.7), Inches(5.0), "Benchmark Design & Partitioning", [
        ("Strict Zero-Leakage Protocol", "Benchmark cases are divided into two equal partitions to guarantee unbiased evaluation:"),
        ("Calibration Partition (N=21)", "Used strictly to optimize and freeze decision thresholds (tau = 0.1814 for ESM-2).", True),
        ("Independent Test Partition (N=21)", "Evaluated with completely frozen parameters to prevent data leakage.", True),
        ("Documented Categories (N=44)", "Cases cover the full spectrum of biological and clerical possibilities:"),
        ("Category A: Congruent Controls (N=10)", "Experimentally confirmed active human kinases.", True),
        ("Category B: Natural Exceptions (N=2)", "Natural pseudokinases (VRK3, ILK) evaluated in diagnostic mode.", True),
        ("Category C: Controlled Inconsistencies (N=32)", "Controlled synthetic label swaps and catalytic motif knockouts.", True),
        ("Standardized Matrix Orientation", "Positives = Inconsistent / Perturbed instances; Negatives = Congruent Controls.")
    ])

    add_structured_card(s11, Inches(6.8), Inches(1.85), Inches(5.7), Inches(5.0), "Controlled Perturbation Types", [
        ("1. Synthetic Label Contradictions", "Assigned an incompatible functional annotation (e.g. non-kinase catalytic label assigned to a canonical kinase). Tests sequence similarity and language model functional manifold sensitivity."),
        ("2. Catalytic Motif Knockouts", "Targeted in silico point mutations disrupting the VAIK, HRD, or DFG active-site triad. Tests sensitivity of the catalytic motif scanner and language model embedding representations."),
        ("3. Non-Kinase Outgroups", "Unrelated globular proteins (e.g. globins, lysozymes) mislabeled as protein kinases. Tests sequence alignment and global embedding boundaries.")
    ], bg_color=RGBColor(241, 245, 249), border_color=RGBColor(203, 213, 225))

    add_notes(s11, "Slide 11 details our evaluation methodology. Benchmark v2 contains 44 cases partitioned into Calibration (N=21) and Independent Test (N=21), guaranteeing zero test leakage.")

    # =========================================================================
    # SLIDE 12: INDEPENDENT TEST SET RESULTS
    # =========================================================================
    s12 = prs.slides.add_slide(blank)
    add_header(s12, "Independent Test Set Results Across Detection Methods", "EMPIRICAL RESULTS", "Rigorous evaluation on the independent test partition (N=21) with frozen thresholds")
    add_footer(s12, 12)

    add_structured_card(s12, Inches(0.8), Inches(1.85), Inches(4.6), Inches(5.0), "Comparative Method Findings", [
        ("Sequence Similarity Baseline", "Precision: 0.7500 | Recall: 0.5000 | F1-Score: 0.6000 | Specificity: 0.7778 | Accuracy: 0.6190. Achieved the highest overall F1-score across all methods."),
        ("ESM-2 Embedding Anomaly", "Precision: 0.6667 | Recall: 0.1667 | F1-Score: 0.2667 | Specificity: 0.8889 | Accuracy: 0.4762. Strong specificity, but misses subtle active-site knockouts."),
        ("Kinase Biological Features (Motifs)", "Precision: 1.0000 | Recall: 0.0833 | F1-Score: 0.1538 | Specificity: 1.0000 | Accuracy: 0.4762. Perfect precision (zero false positives), acting as an absolute sieve."),
        ("Evidence-Aware Ensemble", "Precision: 0.6667 | Recall: 0.1667 | F1-Score: 0.2667 | Specificity: 0.8889 | Accuracy: 0.4762.")
    ])

    add_image_card(s12, Inches(5.6), Inches(1.85), Inches(6.9), Inches(5.0),
                   os.path.join(PHOTO_DIR, "WhatsApp Image 2026-10-28 at 21.24.59.jpeg"),
                   "Figure 9: Scientific Benchmark Console showing independent test set metrics across all four detection methods.")

    add_notes(s12, "Slide 12 presents the exact numbers from our benchmark. Sequence Similarity achieved the highest overall F1-score of 0.6000, while the Motifs method achieved 100% precision with zero false positives.")

    # =========================================================================
    # SLIDE 13: VISUALIZATIONS & CONFUSION MATRIX
    # =========================================================================
    s13 = prs.slides.add_slide(blank)
    add_header(s13, "Metric Visualizations & Confusion Matrix Analysis", "ERROR ANALYSIS", "Visualizing precision-recall trade-offs and scikit-learn standard confusion matrices")
    add_footer(s13, 13)

    add_structured_card(s13, Inches(0.8), Inches(1.85), Inches(4.6), Inches(5.0), "Confusion Matrix Insights", [
        ("Trade-Off Visualization", "Grouped bar charts illustrate the complementary strengths of motif checking (100% precision) versus sequence alignment (balanced 50% recall)."),
        ("Confusion Matrix (Sequence Similarity)", "Evaluated on N=21 frozen test cases:"),
        ("True Negatives (TN = 7)", "Correctly passed congruent control kinases.", True),
        ("True Positives (TP = 6)", "Correctly flagged functional label contradictions.", True),
        ("False Negatives (FN = 6)", "Perturbations retaining high background sequence identity.", True),
        ("False Positives (FP = 2)", "Divergent natural kinases flagged due to low baseline identity.", True),
        ("Curator Takeaway", "Multi-evidence integration prevents biocurators from relying on any single fragile algorithm.")
    ])

    add_image_card(s13, Inches(5.6), Inches(1.85), Inches(6.9), Inches(5.0),
                   os.path.join(PHOTO_DIR, "WhatsApp Image 2026-10-28 at 21.24.91.jpeg"),
                   "Figure 10: Method performance comparison chart and scikit-learn formatted confusion matrix for sequence similarity baseline.")

    add_notes(s13, "Here are the visual charts and confusion matrix. Sequence similarity correctly identified 7 true negatives and 6 true positives, confirming solid discrimination on the frozen test set.")

    # =========================================================================
    # SLIDE 14: ESM-2 EMBEDDING ANOMALY DIAGNOSTICS
    # =========================================================================
    s14 = prs.slides.add_slide(blank)
    add_header(s14, "Why Dense Embeddings Dilute Local Active-Site Mutations", "MACHINE LEARNING INSIGHT", "Scientific diagnostics on ESM-2 language model representations and sensitivity sweeps")
    add_footer(s14, 14)

    add_structured_card(s14, Inches(0.8), Inches(1.85), Inches(4.7), Inches(5.0), "The ESM-2 Dilution Effect", [
        ("The Investigation", "Why did the ESM-2 transformer achieve only 0.1667 recall on sequence perturbations?"),
        ("The Mathematical Cause", "Kinase sequences average 400 to 1,200 residues. Global mean-pooling averages 320-d token vectors across the entire sequence length."),
        ("Negligible Shift in Vector Space", "A localized active-site mutation (3-4 amino acids) constitutes less than 0.5% of the sequence, causing minimal change in global embedding distance."),
        ("Threshold Sensitivity Sweep", "Calibrated cutoff: tau = 0.1814. At tau >= 0.40, the fraction of flagged cases collapses to zero."),
        ("Architectural Takeaway", "Local catalytic verification requires active-site windowed attention, not global sequence mean pooling.")
    ])

    add_image_card(s14, Inches(5.7), Inches(1.85), Inches(6.8), Inches(5.0),
                   os.path.join(PHOTO_DIR, "WhatsApp Image 2026-10-28 at 21.25.00.jpeg"),
                   "Figure 11: ESM-2 diagnostics table across benchmark categories and threshold sensitivity sweep curve.")

    add_notes(s14, "Slide 14 offers a major scientific insight: global mean-pooling dilutes localized point mutations across long proteins. That is why simple motif checkers and alignment tools are necessary complements to LLMs.")

    # =========================================================================
    # SLIDE 15: LIMITATIONS & FUTURE ROADMAP
    # =========================================================================
    s15 = prs.slides.add_slide(blank)
    add_header(s15, "Scientific Limitations & Future Directions", "DISCUSSION & ROADMAP", "Operational boundaries and high-impact engineering extensions")
    add_footer(s15, 15)

    add_structured_card(s15, Inches(0.8), Inches(1.85), Inches(5.7), Inches(5.0), "Current System Boundaries", [
        ("Decision Support, Not Automated Oracle", "In silico contradiction flags highlight review priorities; they do not prove an annotation is wrong. Physical biochemical assays remain required to definitively verify phosphotransfer."),
        ("Global Embedding Dilution", "Mean-pooled ESM-2 embeddings dilute localized point mutations across long sequence backbones."),
        ("Dataset Boundary", "Initial implementation focused exclusively on human protein kinases (500 records)."),
        ("Synthetic Label Distribution", "Inconsistencies modeled through controlled synthetic swaps; real-world database errors may be more subtle.")
    ])

    add_structured_card(s15, Inches(6.8), Inches(1.85), Inches(5.7), Inches(5.0), "Future Research Directions", [
        ("1. Active-Site Attention Pooling", "Extract ESM-2 representations using attention masks centered strictly around the catalytic cleft rather than full-sequence mean pooling."),
        ("2. AlphaFold 3D Geometric Analysis", "Integrate predicted atomic coordinates to evaluate catalytic cleft volume, pocket electrostatics, and ATP-binding geometry."),
        ("3. Kinome-Wide & Multi-Family Expansion", "Generalize the framework to human phosphatases, ubiquitin ligases, and G-protein coupled receptors (GPCRs)."),
        ("4. Biocurator Feedback Loop", "Incorporate active learning where curator verdicts update review weights dynamically.")
    ], bg_color=RGBColor(248, 250, 252), border_color=RGBColor(203, 213, 225))

    add_notes(s15, "Slide 15 covers limitations and future work. We emphasize that our system is an assistant, not an oracle. Future work includes active-site windowed embeddings and AlphaFold 3D pocket geometry.")

    # =========================================================================
    # SLIDE 16: CONCLUSIONS & KEY TAKEAWAYS
    # =========================================================================
    s16 = prs.slides.add_slide(blank)
    add_header(s16, "Project Summary & Core Contributions", "CONCLUSIONS", "Summary of deliverables, scientific lessons, and open-source availability")
    add_footer(s16, 16)

    add_structured_card(s16, Inches(0.8), Inches(1.85), Inches(6.0), Inches(5.0), "Core Scientific Contributions", [
        ("Transparent Multi-Evidence Triage", "Successfully integrated sequence similarity, protein language models (ESM-2), catalytic motif scanners, and ECO provenance into a coherent decision-support framework."),
        ("Scientifically Defensible Pseudokinase Handling", "Established that natural biological exceptions (VRK3, ILK) must be rigorously separated from suspected annotation errors to prevent triage false-alarm pollution."),
        ("Honest Empirical Evaluation", "Benchmark v2 demonstrated that simpler sequence alignment baselines (F1 = 0.6000) outperformed global language model embeddings (F1 = 0.2667) due to sequence length dilution.")
    ])

    add_structured_card(s16, Inches(7.1), Inches(1.85), Inches(5.4), Inches(5.0), "Project Deliverables & Repository", [
        ("Interactive Web Application", "Full Streamlit web platform with SQLite persistence, interactive search, side-by-side reference comparison, and reproducible checkpoints."),
        ("Automated Test Suite", "50 passing unit and integration tests covering database models, UniProt ingestion, motifs, embeddings, and UI components."),
        ("Research Paper & Documentation", "Full scientific manuscript and documentation included."),
        ("Open-Source Repository", "github.com/Krishnakb6/annotation-contradiction-atlas"),
        ("Questions & Discussion", "Thank you! We welcome your questions and feedback.")
    ], bg_color=RGBColor(239, 246, 255), border_color=RGBColor(191, 219, 254))

    add_notes(s16, "In conclusion, The Annotation Contradiction Atlas provides a transparent, evidence-aware decision support system for biocurators. Thank you, and we welcome any questions!")

    # Save
    prs.save(OUTPUT_FILE)
    print(f"Presentation saved successfully to: {OUTPUT_FILE}")

    try:
        shutil.copyfile(OUTPUT_FILE, DOWNLOADS_FILE)
        print(f"Presentation copied to: {DOWNLOADS_FILE}")
    except Exception as e:
        print(f"Copy error: {e}")


if __name__ == "__main__":
    build_all_slides()
