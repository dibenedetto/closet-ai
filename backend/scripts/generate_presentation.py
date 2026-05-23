"""Genera la presentazione PowerPoint di ClosetAI.

Output: ``docs/presentation.pptx`` (~20 slide, italiano, tema dark).

Uso:

    uv run python scripts/generate_presentation.py

Se la cartella ``docs/screenshots/`` contiene file PNG con i nomi attesi
(``01-home.png``, ``02-add.png``, ``03-detail.png``, ``04-today.png``,
``05-dashboard.png``), vengono inseriti nelle slide corrispondenti.
Altrimenti, al loro posto compaiono placeholder con istruzioni.

Lo script è completamente offline e idempotente: rigeneralo dopo ogni
modifica al progetto per mantenere la presentazione allineata.
"""

from __future__ import annotations

import sys
from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN
from pptx.util import Emu, Inches, Pt

ROOT = Path(__file__).resolve().parent.parent.parent  # backend/scripts/ -> repo root
SCREENSHOTS_DIR = ROOT / "docs" / "screenshots"
OUTPUT_PATH = ROOT / "docs" / "presentation.pptx"

# Palette coerente con la UI (CSS variables in frontend/src/index.css).
BG = RGBColor(0x0F, 0x11, 0x17)
PANEL = RGBColor(0x1A, 0x1D, 0x27)
PANEL_2 = RGBColor(0x23, 0x27, 0x34)
TEXT = RGBColor(0xE6, 0xE7, 0xEC)
MUTED = RGBColor(0x8A, 0x90, 0xA3)
ACCENT = RGBColor(0x7C, 0x9C, 0xFF)
ACCENT_2 = RGBColor(0x5B, 0x7D, 0xF0)
OK = RGBColor(0x4E, 0xC9, 0xA0)
WARN = RGBColor(0xE8, 0xC4, 0x6C)
DANGER = RGBColor(0xE8, 0x5A, 0x6F)

SLIDE_W = Inches(13.333)
SLIDE_H = Inches(7.5)


def _set_slide_background(slide, color: RGBColor) -> None:
    bg = slide.background
    fill = bg.fill
    fill.solid()
    fill.fore_color.rgb = color


def _add_textbox(slide, left, top, width, height, text, *, size=18, bold=False,
                 color=TEXT, align=PP_ALIGN.LEFT, italic=False):
    box = slide.shapes.add_textbox(left, top, width, height)
    tf = box.text_frame
    tf.word_wrap = True
    tf.margin_left = Emu(0)
    tf.margin_right = Emu(0)
    tf.margin_top = Emu(0)
    tf.margin_bottom = Emu(0)
    p = tf.paragraphs[0]
    p.alignment = align
    run = p.add_run()
    run.text = text
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.italic = italic
    run.font.color.rgb = color
    run.font.name = "Calibri"
    return box


def _add_bullets(slide, left, top, width, height, items: list[tuple[str, int]],
                 *, base_size=18, color=TEXT):
    """`items` è una lista di (testo, livello) — livello 0 = primo livello."""
    box = slide.shapes.add_textbox(left, top, width, height)
    tf = box.text_frame
    tf.word_wrap = True
    tf.margin_left = Emu(0)
    for i, (text, level) in enumerate(items):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.level = level
        p.space_after = Pt(6)
        run = p.add_run()
        bullet = "•" if level == 0 else "◦"
        run.text = f"{bullet}  {text}"
        run.font.size = Pt(base_size - level * 2)
        run.font.color.rgb = color if level == 0 else MUTED
        run.font.name = "Calibri"
    return box


def _add_rect(slide, left, top, width, height, fill=PANEL, line=PANEL_2):
    shape = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height)
    shape.fill.solid()
    shape.fill.fore_color.rgb = fill
    shape.line.color.rgb = line
    shape.line.width = Pt(0.75)
    shape.shadow.inherit = False
    shape.text_frame.margin_left = Inches(0.15)
    shape.text_frame.margin_right = Inches(0.15)
    shape.text_frame.margin_top = Inches(0.1)
    shape.text_frame.margin_bottom = Inches(0.1)
    # rimuovi il testo placeholder di default
    shape.text_frame.text = ""
    return shape


def _set_shape_text(shape, lines: list[tuple[str, dict]]) -> None:
    """`lines` è una lista di (testo, options). options accetta size/bold/color/align."""
    tf = shape.text_frame
    tf.word_wrap = True
    for i, (text, opts) in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = opts.get("align", PP_ALIGN.LEFT)
        p.space_after = Pt(opts.get("space_after", 4))
        run = p.add_run()
        run.text = text
        run.font.size = Pt(opts.get("size", 16))
        run.font.bold = opts.get("bold", False)
        run.font.color.rgb = opts.get("color", TEXT)
        run.font.name = "Calibri"


def _add_slide_title(slide, title: str, subtitle: str | None = None) -> None:
    _add_textbox(
        slide, Inches(0.6), Inches(0.4), Inches(12), Inches(0.7), title,
        size=32, bold=True, color=TEXT,
    )
    if subtitle:
        _add_textbox(
            slide, Inches(0.6), Inches(1.05), Inches(12), Inches(0.4), subtitle,
            size=14, color=MUTED,
        )
    # underline
    underline = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE, Inches(0.6), Inches(1.55), Inches(0.8), Emu(30000)
    )
    underline.fill.solid()
    underline.fill.fore_color.rgb = ACCENT
    underline.line.fill.background()


def _add_footer(slide, page_num: int) -> None:
    _add_textbox(
        slide,
        Inches(0.6),
        Inches(7.05),
        Inches(10),
        Inches(0.3),
        "ClosetAI · Virtual Worlds · Master in Informatica per la Salute Digitale · Università di Pisa",
        size=9,
        color=MUTED,
    )
    _add_textbox(
        slide, Inches(12), Inches(7.05), Inches(0.8), Inches(0.3),
        f"{page_num}", size=9, color=MUTED, align=PP_ALIGN.RIGHT,
    )


def _add_screenshot_or_placeholder(slide, left, top, width, height,
                                   filename: str, caption: str):
    img_path = SCREENSHOTS_DIR / filename
    if img_path.is_file():
        slide.shapes.add_picture(str(img_path), left, top, width=width, height=height)
        return
    # Placeholder
    ph = _add_rect(slide, left, top, width, height, fill=PANEL_2, line=MUTED)
    _set_shape_text(
        ph,
        [
            ("[ screenshot mancante ]", {"size": 14, "bold": True, "color": MUTED, "align": PP_ALIGN.CENTER, "space_after": 6}),
            (filename, {"size": 11, "color": MUTED, "align": PP_ALIGN.CENTER, "space_after": 6}),
            (caption, {"size": 11, "color": MUTED, "align": PP_ALIGN.CENTER}),
            ("Cattura con UI a video, salva in docs/screenshots/, rigenera.",
             {"size": 10, "color": MUTED, "italic": True, "align": PP_ALIGN.CENTER}),
        ],
    )


# ============================================================================
# Slides
# ============================================================================


def _new_slide(prs: Presentation):
    blank = prs.slide_layouts[6]  # blank layout
    slide = prs.slides.add_slide(blank)
    _set_slide_background(slide, BG)
    return slide


def slide_title(prs: Presentation, page: int) -> None:
    slide = _new_slide(prs)
    # Accent block in alto a sinistra
    band = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), Inches(0.25), SLIDE_H
    )
    band.fill.solid()
    band.fill.fore_color.rgb = ACCENT
    band.line.fill.background()

    _add_textbox(
        slide, Inches(0.9), Inches(2.4), Inches(11), Inches(1.2),
        "ClosetAI", size=72, bold=True, color=TEXT,
    )
    _add_textbox(
        slide, Inches(0.9), Inches(3.5), Inches(11), Inches(0.6),
        "Digitalizza il tuo guardaroba. Vesti meglio. Compra meno.",
        size=22, color=ACCENT, italic=True,
    )
    _add_textbox(
        slide, Inches(0.9), Inches(4.6), Inches(11), Inches(0.5),
        "Master in Informatica per la Salute Digitale — Università di Pisa",
        size=15, color=MUTED,
    )
    _add_textbox(
        slide, Inches(0.9), Inches(5.05), Inches(11), Inches(0.5),
        "Corso di Virtual Worlds · A.A. 2025/2026",
        size=15, color=MUTED,
    )
    _add_textbox(
        slide, Inches(0.9), Inches(6.5), Inches(11), Inches(0.4),
        "marcodibenedetto1979@gmail.com",
        size=12, color=MUTED,
    )
    # Niente footer/page number sulla title slide
    _ = page


def slide_problem(prs: Presentation, page: int) -> None:
    slide = _new_slide(prs)
    _add_slide_title(
        slide, "Il problema",
        "Fast fashion: tante magliette comprate, poche indossate, troppe in discarica.",
    )
    # KPI cards
    kpis = [
        ("10%", "delle emissioni globali di CO₂ vengono dal tessile"),
        ("5M", "tonnellate di vestiti buttati in Europa ogni anno"),
        ("7", "volte la media di utilizzi di un capo fast fashion"),
        ("40%", "del guardaroba medio non viene mai indossato"),
    ]
    for i, (number, caption) in enumerate(kpis):
        x = Inches(0.6 + i * 3.1)
        card = _add_rect(slide, x, Inches(2.1), Inches(2.9), Inches(2.2))
        _set_shape_text(
            card,
            [
                (number, {"size": 44, "bold": True, "color": ACCENT, "align": PP_ALIGN.CENTER, "space_after": 8}),
                (caption, {"size": 12, "color": MUTED, "align": PP_ALIGN.CENTER}),
            ],
        )

    _add_textbox(
        slide, Inches(0.6), Inches(4.7), Inches(12), Inches(0.5),
        "A livello individuale, tre comportamenti ricorrenti:",
        size=18, bold=True,
    )
    _add_bullets(
        slide, Inches(0.6), Inches(5.2), Inches(12), Inches(2),
        [
            ("Acquisto impulsivo — non si ha visione di ciò che si possiede", 0),
            ("Capi 'fantasma' — vestiti mai indossati dopo l'acquisto", 0),
            ("Smaltimento prematuro — un capo si butta invece di ripararlo / cederlo / riciclarlo", 0),
        ],
    )
    _add_footer(slide, page)


def slide_solution_flow(prs: Presentation, page: int) -> None:
    slide = _new_slide(prs)
    _add_slide_title(
        slide, "La soluzione: un flusso unico",
        "Catalogazione + tracking d'uso + azioni circolari, supportati dall'AI.",
    )

    steps = [
        ("01", "Catalogazione", "Foto del capo →\nFashion-CLIP estrae\ncategoria, colore,\nembedding 512d.", ACCENT),
        ("02", "Wear log", "Click 'indossato\noggi' → calcoliamo\nutilizzi, cost-per-wear,\ncapi fantasma.", ACCENT),
        ("03", "Recommendation", "'Cosa metto oggi?'\n→ 3 outfit con score\ncolore + meteo + bonus\ncapi fantasma.", ACCENT),
        ("04", "Azioni circolari", "Diagnosi condizione\n→ ripara / scambia /\nvendi / dona /\nricicla. CO₂ evitata.", OK),
        ("05", "Dashboard impatto", "Equivalenze CO₂\n(km auto, voli, m²\nforesta). Coach AI\nche dà consigli.", OK),
    ]
    width = Inches(2.4)
    for i, (num, title, body, color) in enumerate(steps):
        x = Inches(0.6 + i * 2.5)
        card = _add_rect(slide, x, Inches(2.2), width, Inches(4.0))
        _set_shape_text(
            card,
            [
                (num, {"size": 28, "bold": True, "color": color, "space_after": 4}),
                (title, {"size": 16, "bold": True, "color": TEXT, "space_after": 8}),
                (body, {"size": 11, "color": MUTED}),
            ],
        )

    _add_textbox(
        slide, Inches(0.6), Inches(6.4), Inches(12), Inches(0.4),
        "Estensione hardware: specchio smart (Raspberry Pi 5 + monitor verticale + camera).",
        size=12, color=ACCENT, italic=True,
    )
    _add_footer(slide, page)


def slide_demo_home(prs: Presentation, page: int) -> None:
    slide = _new_slide(prs)
    _add_slide_title(slide, "Guardaroba", "Hero banner + filtri + griglia capi (categoria, colore, prezzo).")
    _add_screenshot_or_placeholder(
        slide, Inches(0.6), Inches(2.0), Inches(8.5), Inches(4.8),
        "01-home.png",
        "Pagina home con stats riassuntive e filtri",
    )
    _add_bullets(
        slide, Inches(9.5), Inches(2.0), Inches(3.5), Inches(5),
        [
            ("Hero banner: 4 metriche live", 0),
            ("Ricerca testuale", 1),
            ("Filtro per categoria", 1),
            ("Chip attivi / ritirati / tutti", 1),
            ("Quick wear '✓ oggi'", 0),
            ("Click su una card", 1),
            ("→ dettaglio capo", 1),
        ],
        base_size=14,
    )
    _add_footer(slide, page)


def slide_architecture(prs: Presentation, page: int) -> None:
    slide = _new_slide(prs)
    _add_slide_title(slide, "Architettura ad alto livello")

    # Frontend box
    fe = _add_rect(slide, Inches(0.6), Inches(2.0), Inches(3.5), Inches(2.6), fill=PANEL_2)
    _set_shape_text(
        fe,
        [
            ("Frontend", {"size": 18, "bold": True, "color": ACCENT, "space_after": 6}),
            ("React 19 + Vite 7", {"size": 13, "color": TEXT, "space_after": 2}),
            ("TypeScript strict", {"size": 13, "color": MUTED, "space_after": 2}),
            ("6 pagine + 3 componenti AI", {"size": 13, "color": MUTED, "space_after": 2}),
            ("API client tipizzato", {"size": 13, "color": MUTED}),
        ],
    )
    # Backend box
    be = _add_rect(slide, Inches(4.9), Inches(2.0), Inches(3.5), Inches(2.6), fill=PANEL_2)
    _set_shape_text(
        be,
        [
            ("Backend FastAPI", {"size": 18, "bold": True, "color": ACCENT, "space_after": 6}),
            ("Python 3.14 + uv", {"size": 13, "color": TEXT, "space_after": 2}),
            ("SQLAlchemy 2 ORM", {"size": 13, "color": MUTED, "space_after": 2}),
            ("8 router REST", {"size": 13, "color": MUTED, "space_after": 2}),
            ("13 servizi (ML + AI gen)", {"size": 13, "color": MUTED}),
        ],
    )
    # Storage box
    st = _add_rect(slide, Inches(9.2), Inches(2.0), Inches(3.5), Inches(2.6), fill=PANEL_2)
    _set_shape_text(
        st,
        [
            ("Storage", {"size": 18, "bold": True, "color": ACCENT, "space_after": 6}),
            ("SQLite (metadata)", {"size": 13, "color": TEXT, "space_after": 2}),
            ("Filesystem (foto)", {"size": 13, "color": MUTED, "space_after": 2}),
            ("ChromaDB (embedding)", {"size": 13, "color": MUTED, "space_after": 2}),
            ("→ Postgres + S3 in prod", {"size": 12, "color": MUTED, "italic": True}),
        ],
    )

    # ML layer
    ml = _add_rect(slide, Inches(0.6), Inches(5.0), Inches(7.8), Inches(1.8), fill=PANEL, line=ACCENT)
    _set_shape_text(
        ml,
        [
            ("Machine Learning applicato", {"size": 16, "bold": True, "color": ACCENT, "space_after": 4}),
            ("Fashion-CLIP (HuggingFace) · Pillow quantize · ChromaDB k-NN", {"size": 12, "color": TEXT, "space_after": 4}),
            ("Diagnosi euristica · Recommender con regole HSL + meteo + ghost-bonus", {"size": 12, "color": MUTED}),
        ],
    )
    # AI gen layer
    ai = _add_rect(slide, Inches(8.7), Inches(5.0), Inches(4.0), Inches(1.8), fill=PANEL, line=OK)
    _set_shape_text(
        ai,
        [
            ("AI generativa", {"size": 16, "bold": True, "color": OK, "space_after": 4}),
            ("litellm gateway", {"size": 12, "color": TEXT, "space_after": 2}),
            ("diffusers (SD inpainting)", {"size": 12, "color": MUTED, "space_after": 2}),
            ("Cloud + locale pluggable", {"size": 12, "color": MUTED, "italic": True}),
        ],
    )
    _add_footer(slide, page)


def slide_stack(prs: Presentation, page: int) -> None:
    slide = _new_slide(prs)
    _add_slide_title(slide, "Stack tecnico", "Tutte scelte standard, niente lock-in custom.")

    rows = [
        ("Backend", "Python 3.14, FastAPI, SQLAlchemy 2, SQLite", "uv per il package mgmt + lockfile"),
        ("Frontend", "React 19, Vite 7, TypeScript", "react-router 7 · CSS variables"),
        ("ML applicato", "PyTorch CPU, transformers, Fashion-CLIP", "Pillow per immagini"),
        ("AI generativa", "litellm (cloud + Ollama locale), diffusers", "anche modelli locali"),
        ("Vector DB", "ChromaDB persistente", "cosine similarity native"),
        ("Hardware (opz.)", "Raspberry Pi 5 + monitor verticale + Chromium kiosk", "pagina /mirror"),
    ]
    y = Inches(2.0)
    for layer, tech, note in rows:
        row_h = Inches(0.7)
        _add_textbox(slide, Inches(0.6), y, Inches(2.5), row_h, layer, size=16, bold=True, color=ACCENT)
        _add_textbox(slide, Inches(3.2), y, Inches(5.5), row_h, tech, size=14, color=TEXT)
        _add_textbox(slide, Inches(8.8), y, Inches(4.0), row_h, note, size=12, color=MUTED, italic=True)
        y += row_h + Inches(0.15)
    _add_footer(slide, page)


def slide_module_classification(prs: Presentation, page: int) -> None:
    slide = _new_slide(prs)
    _add_slide_title(
        slide, "M1 · Catalogazione capi (Fashion-CLIP)",
        "Una foto → categoria + colore + embedding 512d, in 64 ms su CPU.",
    )
    _add_bullets(
        slide, Inches(0.6), Inches(2.1), Inches(7.5), Inches(4.5),
        [
            ("Modello: patrickjohncyh/fashion-clip (CLIP fine-tunato su 700k immagini fashion)", 0),
            ("Approccio zero-shot su 14 categorie italiane", 0),
            ("Prompt EN precomputati → embedding testuale", 1),
            ("Cosine similarity tra image embedding e text embeddings → softmax", 1),
            ("Embedding salvati in ChromaDB (riusabili per recommender)", 0),
            ("Colore dominante: Pillow quantize + filtro sfondo chiaro", 0),
            ("Fallback Mock: deterministico, per i test e ambienti senza torch", 0),
            ("Benchmark: Mock 4ms · Fashion-CLIP 64ms post-warmup (CPU)", 0),
        ],
    )
    code = _add_rect(slide, Inches(8.5), Inches(2.1), Inches(4.5), Inches(4.5),
                    fill=PANEL_2, line=PANEL_2)
    _set_shape_text(
        code,
        [
            ("classify(image_path)", {"size": 13, "bold": True, "color": ACCENT, "space_after": 6}),
            ("→ ClassificationResult", {"size": 12, "color": TEXT, "space_after": 8}),
            ("category: 't-shirt'", {"size": 11, "color": MUTED, "space_after": 2}),
            ("color: 'blu'", {"size": 11, "color": MUTED, "space_after": 2}),
            ("confidence: 0.83", {"size": 11, "color": MUTED, "space_after": 2}),
            ("embedding: float[512]", {"size": 11, "color": MUTED, "space_after": 10}),
            ("env CLOSETAI_CLASSIFIER", {"size": 11, "color": ACCENT, "italic": True, "space_after": 2}),
            ("= fashion-clip | mock", {"size": 11, "color": MUTED, "italic": True}),
        ],
    )
    _add_footer(slide, page)


def slide_module_wear(prs: Presentation, page: int) -> None:
    slide = _new_slide(prs)
    _add_slide_title(
        slide, "M2 · Wear log + cost-per-wear",
        "Quante volte hai indossato un capo? Quanto ti è costato a utilizzo?",
    )
    _add_bullets(
        slide, Inches(0.6), Inches(2.1), Inches(8), Inches(4.5),
        [
            ("Modello WearEvent: item_id + worn_on (date) + occasion + created_at", 0),
            ("Cascade delete: eliminando un capo, i suoi wear event spariscono", 1),
            ("Endpoint: POST /items/{id}/wear, batch insert, lista, delete", 0),
            ("Stats per capo: wear_count, last_worn, cost_per_wear, days_since_last_worn", 0),
            ("Stats guardaroba: investimento totale, cpw medio, top worn, ghost count", 0),
            ("Capi fantasma: 0 utilizzi e posseduti da ≥ N giorni (configurabile)", 0),
            ("UI: pulsante '✓ oggi' sulla card · storico utilizzi nel detail", 0),
            ("Esclude i capi 'ritirati' (donati/venduti/...) dalle metriche attive", 1),
        ],
    )
    # Formula card
    fcard = _add_rect(slide, Inches(9), Inches(2.1), Inches(4), Inches(2),
                      fill=PANEL_2, line=ACCENT)
    _set_shape_text(
        fcard,
        [
            ("Cost-per-wear", {"size": 14, "bold": True, "color": ACCENT, "align": PP_ALIGN.CENTER, "space_after": 8}),
            ("= price / wear_count", {"size": 14, "color": TEXT, "align": PP_ALIGN.CENTER, "space_after": 8}),
            ("€89 / 30 = € 2,96", {"size": 16, "bold": True, "color": OK, "align": PP_ALIGN.CENTER}),
        ],
    )
    _add_footer(slide, page)


def slide_module_recommender(prs: Presentation, page: int) -> None:
    slide = _new_slide(prs)
    _add_slide_title(
        slide, "M3 · Outfit recommender",
        "'Cosa metto oggi?' — combinazioni dei tuoi capi, condizionate dal meteo.",
    )
    _add_bullets(
        slide, Inches(0.6), Inches(2.1), Inches(7.5), Inches(4.5),
        [
            ("Generazione candidati: combinazioni top/bottom/dress/outerwear/shoes", 0),
            ("Filtro meteo: shorts/t-shirt esclusi se freddo, cappotto se caldo", 0),
            ("Score colore (HSL): neutri, analoghi, complementari, split-complementary", 0),
            ("Score meteo: adeguatezza temperatura + pioggia (Open-Meteo API)", 0),
            ("Fallback Open-Meteo: meteo 'mite' se network down → demo offline-friendly", 1),
            ("Bonus 'capi fantasma': incentiva l'uso di capi mai indossati", 0),
            ("Diversità: rimuove proposte con troppo overlap", 0),
            ("Feedback utente (like/dislike) persistito in tabella outfit_feedback", 0),
        ],
    )
    # Score formula
    s = _add_rect(slide, Inches(8.5), Inches(2.1), Inches(4.5), Inches(2.5),
                  fill=PANEL_2, line=ACCENT)
    _set_shape_text(
        s,
        [
            ("Score totale", {"size": 14, "bold": True, "color": ACCENT, "align": PP_ALIGN.CENTER, "space_after": 8}),
            ("0.55 · colore", {"size": 13, "color": TEXT, "align": PP_ALIGN.CENTER, "space_after": 2}),
            ("+ 0.35 · meteo", {"size": 13, "color": TEXT, "align": PP_ALIGN.CENTER, "space_after": 2}),
            ("+ bonus fantasma (≤ 0.15)", {"size": 13, "color": TEXT, "align": PP_ALIGN.CENTER, "space_after": 6}),
            ("= match in [0, 1]", {"size": 14, "bold": True, "color": OK, "align": PP_ALIGN.CENTER}),
        ],
    )
    _add_footer(slide, page)


def slide_module_circular(prs: Presentation, page: int) -> None:
    slide = _new_slide(prs)
    _add_slide_title(
        slide, "M4 · Modulo circolare",
        "Diagnosi condizione capo → azioni concrete con stima CO₂ evitata.",
    )

    states = [
        ("Nuovo", "mai indossato e <60g posseduto", OK),
        ("Buono", "fino a 30 utilizzi e <2 anni", ACCENT),
        ("Usurato", "30-80 utilizzi o 2-5 anni", WARN),
        ("Danneggiato", ">80 utilizzi o >5 anni", DANGER),
    ]
    width = Inches(3.0)
    for i, (state, criteria, color) in enumerate(states):
        x = Inches(0.6 + i * 3.1)
        card = _add_rect(slide, x, Inches(2.1), width, Inches(1.6))
        _set_shape_text(
            card,
            [
                (state, {"size": 18, "bold": True, "color": color, "space_after": 4}),
                (criteria, {"size": 11, "color": MUTED}),
            ],
        )

    _add_textbox(
        slide, Inches(0.6), Inches(4.0), Inches(12), Inches(0.4),
        "5 azioni circolari × stima CO₂ evitata per categoria (tabella Ellen MacArthur):",
        size=14, bold=True, color=TEXT,
    )
    actions = [
        ("Riparazione", "70%", ACCENT),
        ("Swap", "100%", OK),
        ("Vendita", "100%", OK),
        ("Donazione", "100%", OK),
        ("Riciclo", "30%", WARN),
    ]
    for i, (action, pct, color) in enumerate(actions):
        x = Inches(0.6 + i * 2.5)
        card = _add_rect(slide, x, Inches(4.6), Inches(2.4), Inches(1.3))
        _set_shape_text(
            card,
            [
                (action, {"size": 14, "bold": True, "color": TEXT, "align": PP_ALIGN.CENTER, "space_after": 4}),
                (f"−{pct} CO₂", {"size": 16, "bold": True, "color": color, "align": PP_ALIGN.CENTER}),
            ],
        )
    _add_textbox(
        slide, Inches(0.6), Inches(6.2), Inches(12), Inches(0.5),
        "Esempio: donare una giacca (25 kg CO₂eq di produzione) × 100% evitata = 25 kg salvati.",
        size=12, color=MUTED, italic=True,
    )
    _add_footer(slide, page)


def slide_demo_dashboard(prs: Presentation, page: int) -> None:
    slide = _new_slide(prs)
    _add_slide_title(
        slide, "Dashboard impatto",
        "CO₂ evitata tradotta in equivalenze concrete (km auto, voli, m² foresta).",
    )
    _add_screenshot_or_placeholder(
        slide, Inches(0.6), Inches(2.0), Inches(8.5), Inches(4.8),
        "05-dashboard.png",
        "Dashboard con coach AI, stat card, bar chart azioni circolari",
    )
    _add_bullets(
        slide, Inches(9.5), Inches(2.0), Inches(3.5), Inches(5),
        [
            ("5 stat card live", 0),
            ("Coach AI in cima", 0),
            ("Equivalenze CO₂", 0),
            ("≈ km auto", 1),
            ("≈ voli Pisa-Roma", 1),
            ("≈ m² foresta /anno", 1),
            ("Bar chart azioni", 0),
            ("Top capi indossati", 0),
            ("Lista capi fantasma", 0),
        ],
        base_size=13,
    )
    _add_footer(slide, page)


def slide_ai_two_roles(prs: Presentation, page: int) -> None:
    slide = _new_slide(prs)
    _add_slide_title(
        slide, "AI in due ruoli distinti",
        "Requisito del corso: dimostrare ML applicato e AI generativa.",
    )

    # ML applicato
    ml = _add_rect(slide, Inches(0.6), Inches(2.1), Inches(6.0), Inches(4.7),
                   fill=PANEL, line=ACCENT)
    _set_shape_text(
        ml,
        [
            ("🔬 Machine Learning applicato", {"size": 18, "bold": True, "color": ACCENT, "space_after": 10}),
            ("Componente funzionale del prodotto.", {"size": 13, "color": MUTED, "italic": True, "space_after": 12}),
            ("✓ Classificazione capi (Fashion-CLIP)", {"size": 13, "color": TEXT, "space_after": 4}),
            ("✓ Estrazione colore dominante", {"size": 13, "color": TEXT, "space_after": 4}),
            ("✓ Outfit recommender (HSL + meteo)", {"size": 13, "color": TEXT, "space_after": 4}),
            ("✓ Diagnosi condizione capo (euristica)", {"size": 13, "color": TEXT, "space_after": 4}),
            ("✓ k-NN su embedding ChromaDB", {"size": 13, "color": TEXT, "space_after": 4}),
            ("✓ Stima CO₂ × categoria × azione", {"size": 13, "color": TEXT}),
        ],
    )
    # AI generativa
    ai = _add_rect(slide, Inches(6.8), Inches(2.1), Inches(6.0), Inches(4.7),
                   fill=PANEL, line=OK)
    _set_shape_text(
        ai,
        [
            ("✨ AI generativa", {"size": 18, "bold": True, "color": OK, "space_after": 10}),
            ("Supporto al design e all'esperienza.", {"size": 13, "color": MUTED, "italic": True, "space_after": 12}),
            ("✓ Descrizione capi via LLM", {"size": 13, "color": TEXT, "space_after": 4}),
            ("✓ Coach AI sostenibilità", {"size": 13, "color": TEXT, "space_after": 4}),
            ("✓ Tutorial riparazione dinamici", {"size": 13, "color": TEXT, "space_after": 4}),
            ("✓ Try-on virtuale (SD inpainting)", {"size": 13, "color": TEXT, "space_after": 4}),
            ("⨯ Asset visivi (Pillow + esterno)", {"size": 13, "color": MUTED, "space_after": 4}),
            ("⨯ UI/UX prototipo (esterno)", {"size": 13, "color": MUTED}),
        ],
    )
    _add_footer(slide, page)


def slide_llm_gateway(prs: Presentation, page: int) -> None:
    slide = _new_slide(prs)
    _add_slide_title(
        slide, "✨ AI generativa: gateway pluggable",
        "Un'unica funzione generate() parla con tutti i provider. ADR-008.",
    )

    providers = [
        ("Anthropic (Claude)", "claude-haiku-4-5", "ANTHROPIC_API_KEY", "cloud", ACCENT),
        ("OpenAI", "openai/gpt-4o-mini", "OPENAI_API_KEY", "cloud", ACCENT),
        ("Ollama", "ollama/llama3.2:3b", "(nessuna)", "LOCALE", OK),
        ("HuggingFace", "huggingface/Qwen2.5", "HF_TOKEN", "cloud / locale", ACCENT),
    ]
    _add_textbox(slide, Inches(0.6), Inches(1.9), Inches(3.5), Inches(0.4),
                 "Provider", size=12, bold=True, color=MUTED)
    _add_textbox(slide, Inches(4.2), Inches(1.9), Inches(3.5), Inches(0.4),
                 "Modello (esempio)", size=12, bold=True, color=MUTED)
    _add_textbox(slide, Inches(7.8), Inches(1.9), Inches(2.8), Inches(0.4),
                 "Credenziali", size=12, bold=True, color=MUTED)
    _add_textbox(slide, Inches(10.6), Inches(1.9), Inches(2.3), Inches(0.4),
                 "Sede", size=12, bold=True, color=MUTED)
    y = Inches(2.3)
    for provider, model, creds, sede, color in providers:
        _add_textbox(slide, Inches(0.6), y, Inches(3.5), Inches(0.4), provider, size=14, bold=True, color=TEXT)
        _add_textbox(slide, Inches(4.2), y, Inches(3.5), Inches(0.4), model, size=12, color=MUTED)
        _add_textbox(slide, Inches(7.8), y, Inches(2.8), Inches(0.4), creds, size=12, color=MUTED)
        _add_textbox(slide, Inches(10.6), y, Inches(2.3), Inches(0.4), sede, size=12, bold=True, color=color)
        y += Inches(0.45)

    bullets = _add_rect(slide, Inches(0.6), Inches(4.4), Inches(12.2), Inches(2.4),
                       fill=PANEL_2, line=PANEL_2)
    _set_shape_text(
        bullets,
        [
            ("Vantaggi:", {"size": 14, "bold": True, "color": ACCENT, "space_after": 6}),
            ("• Cambio provider = un solo env var, nessun cambio di codice", {"size": 12, "color": TEXT, "space_after": 4}),
            ("• Ollama locale = privacy completa, nessuna API key, nessun costo", {"size": 12, "color": TEXT, "space_after": 4}),
            ("• Cache risposte in tabella llm_cache con TTL 24h (riduce costi e latenza)", {"size": 12, "color": TEXT, "space_after": 4}),
            ("• Graceful fallback: se LLM non disponibile, endpoint → 503 e UI nasconde i bottoni AI", {"size": 12, "color": TEXT}),
        ],
    )
    _add_footer(slide, page)


def slide_tryon(prs: Presentation, page: int) -> None:
    slide = _new_slide(prs)
    _add_slide_title(
        slide, "✨ Try-on virtuale",
        "Stable Diffusion 2 inpainting via diffusers. Anche locale. ADR-007.",
    )
    _add_bullets(
        slide, Inches(0.6), Inches(2.1), Inches(7), Inches(4.7),
        [
            ("Backend pluggable: TryOnBackend (ABC)", 0),
            ("DisabledBackend (default) → 503 esplicito", 1),
            ("DiffusersLocalBackend → SD 2 inpainting (5 GB pesi)", 1),
            ("Pipeline MVP:", 0),
            ("Upload ritratto (multipart) → resize/pad 512×512", 1),
            ("Maschera 'torso' euristica (rettangolo centrale)", 1),
            ("Prompt = 'a photorealistic portrait of a person wearing a {color} {category}'", 1),
            ("Inferenza diffusers (20 step)", 1),
            ("CPU: 30s-3min per immagine · GPU CUDA: 5-10s", 0),
            ("Privacy: il ritratto NON viene salvato, solo l'output sintetico", 0),
        ],
    )
    placeholder = _add_rect(slide, Inches(8.0), Inches(2.1), Inches(5.0), Inches(4.7),
                            fill=PANEL_2, line=OK)
    _set_shape_text(
        placeholder,
        [
            ("Path di sblocco IDM-VTON", {"size": 14, "bold": True, "color": OK, "align": PP_ALIGN.CENTER, "space_after": 8}),
            ("Per try-on garment-aware:", {"size": 12, "color": TEXT, "space_after": 6}),
            ("class IdmVtonBackend(TryOnBackend):", {"size": 11, "color": MUTED, "space_after": 4}),
            ("    def generate(...):", {"size": 11, "color": MUTED, "space_after": 4}),
            ("        # IDM-VTON inference", {"size": 11, "color": MUTED, "space_after": 6}),
            ("Cambio: un env var.", {"size": 12, "color": ACCENT, "italic": True, "align": PP_ALIGN.CENTER, "space_after": 4}),
            ("Nessuna modifica al chiamante.", {"size": 12, "color": ACCENT, "italic": True, "align": PP_ALIGN.CENTER}),
        ],
    )
    _add_footer(slide, page)


def slide_mirror(prs: Presentation, page: int) -> None:
    slide = _new_slide(prs)
    _add_slide_title(
        slide, "Estensione: specchio smart",
        "Raspberry Pi 5 + monitor portrait + Chromium kiosk → /mirror",
    )
    _add_bullets(
        slide, Inches(0.6), Inches(2.1), Inches(7.0), Inches(4.7),
        [
            ("Pagina /mirror minimalissima, fullscreen kiosk", 0),
            ("Orologio 96px + data + meteo", 1),
            ("Outfit suggerito del giorno (refresh 5 min)", 1),
            ("Niente topbar/nav, percepibile come specchio", 1),
            ("Setup hardware in docs/raspberry-pi.md", 0),
            ("Chromium kiosk via scripts/start-mirror.sh", 1),
            ("Autostart systemd o Wayfire", 1),
            ("Variazione demo: monitor 24\" su cavalletto", 1),
            ("Sviluppo futuro:", 0),
            ("Webcam + PIR → wear log automatico", 1),
            ("'Ti ho visto: questo era l'outfit?'", 1),
        ],
    )
    placeholder = _add_rect(slide, Inches(8.0), Inches(2.1), Inches(5.0), Inches(4.7),
                            fill=PANEL_2, line=ACCENT)
    _set_shape_text(
        placeholder,
        [
            ("[ render /mirror ]", {"size": 14, "bold": True, "color": MUTED, "align": PP_ALIGN.CENTER, "space_after": 12}),
            ("07:34", {"size": 48, "color": TEXT, "align": PP_ALIGN.CENTER, "space_after": 4}),
            ("martedì 15 ottobre", {"size": 12, "color": MUTED, "align": PP_ALIGN.CENTER, "space_after": 12}),
            ("☀️ 18°C", {"size": 22, "color": TEXT, "align": PP_ALIGN.CENTER, "space_after": 14}),
            ("OUTFIT DEL GIORNO", {"size": 10, "color": MUTED, "align": PP_ALIGN.CENTER, "space_after": 6}),
            ("camicia · jeans · scarpe", {"size": 14, "color": ACCENT, "align": PP_ALIGN.CENTER}),
        ],
    )
    _add_footer(slide, page)


def slide_privacy(prs: Presentation, page: int) -> None:
    slide = _new_slide(prs)
    _add_slide_title(
        slide, "Privacy by design",
        "Foto del corpo, della camera da letto, di vestiti: tutto sensibile.",
    )
    _add_bullets(
        slide, Inches(0.6), Inches(2.1), Inches(12), Inches(5),
        [
            ("Nessun upload in cloud nell'MVP — tutto in data/ locale, gitignored", 0),
            ("Foto capi salvate con UUID, non più collegabili al nome originale", 0),
            ("Embedding vettoriali in ChromaDB → non reversibili a immagine", 0),
            ("Try-on: il ritratto NON viene salvato; solo l'output sintetico in data/tryon/", 0),
            ("LLM 'cloud': l'utente sceglie consapevolmente se mandare query a Claude/OpenAI", 0),
            ("→ alternativa Ollama locale: zero rete, zero API key, privacy completa", 1),
            ("Roadmap ONNX export del classifier → inference nel browser dell'utente", 0),
            ("Niente PII salvata: il prototipo è single-user locale, no auth, no analytics", 0),
        ],
    )
    _add_footer(slide, page)


def slide_metrics(prs: Presentation, page: int) -> None:
    slide = _new_slide(prs)
    _add_slide_title(slide, "Metriche di impatto", "Ogni feature popola una metrica concreta.")

    metrics = [
        ("Utilizzi/capo", "M2", ACCENT),
        ("Cost-per-wear", "M2", ACCENT),
        ("Capi fantasma", "M2 + M6", WARN),
        ("CO₂ evitata", "M4 + M6", OK),
        ("Capi salvati", "M4", OK),
        ("Acquisti evitati", "M3 (futuro)", MUTED),
    ]
    width = Inches(4.0)
    for i, (metric, modules, color) in enumerate(metrics):
        col = i % 3
        row = i // 3
        x = Inches(0.6 + col * 4.2)
        y = Inches(2.1 + row * 2.0)
        card = _add_rect(slide, x, y, width, Inches(1.7))
        _set_shape_text(
            card,
            [
                (metric, {"size": 20, "bold": True, "color": color, "align": PP_ALIGN.CENTER, "space_after": 8}),
                (f"modulo {modules}", {"size": 12, "color": MUTED, "align": PP_ALIGN.CENTER}),
            ],
        )
    _add_textbox(
        slide, Inches(0.6), Inches(6.4), Inches(12), Inches(0.4),
        "Equivalenze: 1 km auto media UE ≈ 0,18 kg CO₂eq · 1 m² foresta ≈ 8 kg/anno · 1 volo PSA-FCO ≈ 80 kg pro capite",
        size=11, color=MUTED, italic=True,
    )
    _add_footer(slide, page)


def slide_adr_recap(prs: Presentation, page: int) -> None:
    slide = _new_slide(prs)
    _add_slide_title(
        slide, "Decisioni architetturali (ADR)",
        "Otto decisioni documentate in docs/architecture.md con alternative e motivazioni.",
    )
    rows = [
        ("ADR-001", "Persistenza: SQLite + FS oggi, Postgres + S3 in prod"),
        ("ADR-002", "Migrazioni: create_all + ALTER TABLE idempotenti (no Alembic finché schema cambia)"),
        ("ADR-003", "Classifier: Fashion-CLIP (zero-shot + embedding 512d riusabili)"),
        ("ADR-004", "Embedding storage: ChromaDB persistente locale"),
        ("ADR-005", "Inference server-side oggi, ONNX/on-device come estensione"),
        ("ADR-006", "Colore dominante: PIL quantize + filtro sfondo chiaro"),
        ("ADR-007", "Try-on: backend pluggable (DiffusersLocalBackend), default disabled"),
        ("ADR-008", "LLM gateway: litellm (Anthropic/OpenAI/Ollama/HF) + DB cache 24h"),
    ]
    y = Inches(2.1)
    for adr, desc in rows:
        _add_textbox(slide, Inches(0.6), y, Inches(1.5), Inches(0.4), adr,
                     size=14, bold=True, color=ACCENT)
        _add_textbox(slide, Inches(2.3), y, Inches(10.5), Inches(0.4), desc,
                     size=13, color=TEXT)
        y += Inches(0.55)
    _add_footer(slide, page)


def slide_numbers(prs: Presentation, page: int) -> None:
    slide = _new_slide(prs)
    _add_slide_title(slide, "Numeri del progetto", "6 fasi + 1 estensione AI generativa.")
    metrics = [
        ("106", "test backend", OK),
        ("100%", "passing", OK),
        ("325 kB", "bundle JS (102 kB gzip)", ACCENT),
        ("64 ms", "inferenza Fashion-CLIP (CPU)", ACCENT),
        ("16", "endpoint REST documentati", ACCENT),
        ("8", "ADR motivate", ACCENT),
        ("18", "endpoint AI generativa", OK),
        ("5", "feature AI runtime", OK),
    ]
    for i, (num, caption, color) in enumerate(metrics):
        col = i % 4
        row = i // 4
        x = Inches(0.6 + col * 3.1)
        y = Inches(2.0 + row * 2.4)
        card = _add_rect(slide, x, y, Inches(2.9), Inches(2.1))
        _set_shape_text(
            card,
            [
                (num, {"size": 36, "bold": True, "color": color, "align": PP_ALIGN.CENTER, "space_after": 6}),
                (caption, {"size": 12, "color": MUTED, "align": PP_ALIGN.CENTER}),
            ],
        )
    _add_footer(slide, page)


def slide_modules_assignment(prs: Presentation, page: int) -> None:
    slide = _new_slide(prs)
    _add_slide_title(
        slide, "Modularità: 6 moduli per 6 sottogruppi",
        "Ogni modulo è assegnabile in modo indipendente.",
    )
    modules = [
        ("M1", "Catalogazione capi (vision)", "Fashion-CLIP, embedding, colore"),
        ("M2", "Wear log + cost-per-wear", "CRUD + analytics"),
        ("M3", "Outfit recommender", "Regole + meteo + feedback"),
        ("M4", "Diagnosi e azioni circolari", "Vision classifier + tabella CO₂ + LLM"),
        ("M5", "UI / Specchio fisico", "React + Vite, opz. RPi5"),
        ("M6", "Dashboard impatto", "Aggregazione metriche + visualizzazioni"),
    ]
    y = Inches(2.1)
    for code, title, tech in modules:
        _add_textbox(slide, Inches(0.6), y, Inches(0.8), Inches(0.5),
                     code, size=22, bold=True, color=ACCENT)
        _add_textbox(slide, Inches(1.6), y, Inches(5), Inches(0.5),
                     title, size=16, bold=True, color=TEXT)
        _add_textbox(slide, Inches(6.8), y, Inches(6), Inches(0.5),
                     tech, size=14, color=MUTED, italic=True)
        y += Inches(0.7)
    _add_footer(slide, page)


def slide_limits(prs: Presentation, page: int) -> None:
    slide = _new_slide(prs)
    _add_slide_title(slide, "Limitazioni note + estensioni future",
                     "Onestà intellettuale: ecco cosa il prototipo NON copre.")
    cols = [
        ("Limitazioni note", DANGER, [
            "Bias dataset: moda occidentale, femminile, taglie standard",
            "Stime CO₂ medie per categoria, non LCA puntuali",
            "Try-on con maschera euristica (non garment-aware)",
            "Auth: single-user locale (consapevole)",
            "Privacy DPIA non eseguita per uso produzione",
        ]),
        ("Estensioni future", OK, [
            "Detection automatica outfit da foto (multi-label)",
            "ONNX export per inference on-device",
            "Marketplace second-hand (Vinted, Wallapop link)",
            "Modalità famiglia / guardaroba condiviso",
            "Gap analysis pre-acquisto",
            "Notifiche push capi non indossati",
        ]),
    ]
    for i, (title, color, items) in enumerate(cols):
        x = Inches(0.6 + i * 6.3)
        card = _add_rect(slide, x, Inches(2.1), Inches(6.1), Inches(4.7),
                         fill=PANEL_2, line=color)
        bullet_lines = [(title, {"size": 18, "bold": True, "color": color, "space_after": 12})]
        for it in items:
            bullet_lines.append((f"•  {it}", {"size": 12, "color": TEXT, "space_after": 6}))
        _set_shape_text(card, bullet_lines)
    _add_footer(slide, page)


def slide_demo_today(prs: Presentation, page: int) -> None:
    slide = _new_slide(prs)
    _add_slide_title(
        slide, "Cosa metto oggi?",
        "Tre proposte di outfit, con breakdown colore + meteo + ghost bonus.",
    )
    _add_screenshot_or_placeholder(
        slide, Inches(0.6), Inches(2.0), Inches(8.5), Inches(4.8),
        "04-today.png",
        "Pagina /today con tre outfit, meteo, like/dislike",
    )
    _add_bullets(
        slide, Inches(9.5), Inches(2.0), Inches(3.5), Inches(5),
        [
            ("Meteo live (Open-Meteo)", 0),
            ("Fallback se rete down", 1),
            ("Per ogni proposta:", 0),
            ("Thumbnails capi", 1),
            ("Match score totale", 1),
            ("Breakdown colore", 1),
            ("Breakdown meteo", 1),
            ("Rationale testuale", 1),
            ("Azioni:", 0),
            ("'Indosso questo' → multi-wear log", 1),
            ("Like/dislike → feedback DB", 1),
        ],
        base_size=12,
    )
    _add_footer(slide, page)


def slide_closing(prs: Presentation, page: int) -> None:
    slide = _new_slide(prs)
    band = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), Inches(0.25), SLIDE_H
    )
    band.fill.solid()
    band.fill.fore_color.rgb = OK
    band.line.fill.background()

    _add_textbox(
        slide, Inches(0.9), Inches(2.0), Inches(11), Inches(1.0),
        "Grazie.", size=64, bold=True, color=TEXT,
    )
    _add_textbox(
        slide, Inches(0.9), Inches(3.1), Inches(11), Inches(0.7),
        "Vesti meglio. Compra meno. Compra usato.",
        size=22, color=OK, italic=True,
    )
    _add_textbox(
        slide, Inches(0.9), Inches(4.3), Inches(11), Inches(0.5),
        "Domande?",
        size=20, color=ACCENT,
    )

    box = _add_rect(slide, Inches(0.9), Inches(5.2), Inches(11.5), Inches(1.5),
                    fill=PANEL_2, line=PANEL_2)
    _set_shape_text(
        box,
        [
            ("Per provarlo:", {"size": 14, "bold": True, "color": ACCENT, "space_after": 4}),
            ("./scripts/setup.sh && ./scripts/run-backend.sh && ./scripts/run-frontend.sh",
             {"size": 13, "color": TEXT, "space_after": 4}),
            ("→ http://localhost:5173", {"size": 13, "color": OK, "space_after": 4}),
            ("Documentazione: README.md, PROJECT.md, PLAN.md, docs/architecture.md, docs/api.md",
             {"size": 12, "color": MUTED}),
        ],
    )
    _ = page  # niente footer sulla closing


# ============================================================================
# Build
# ============================================================================


def build() -> Path:
    prs = Presentation()
    prs.slide_width = SLIDE_W
    prs.slide_height = SLIDE_H

    slides = [
        slide_title,
        slide_problem,
        slide_solution_flow,
        slide_architecture,
        slide_stack,
        slide_demo_home,
        slide_module_classification,
        slide_module_wear,
        slide_module_recommender,
        slide_module_circular,
        slide_demo_today,
        slide_demo_dashboard,
        slide_ai_two_roles,
        slide_llm_gateway,
        slide_tryon,
        slide_mirror,
        slide_privacy,
        slide_metrics,
        slide_adr_recap,
        slide_modules_assignment,
        slide_numbers,
        slide_limits,
        slide_closing,
    ]

    for i, builder in enumerate(slides, start=1):
        builder(prs, i)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    prs.save(str(OUTPUT_PATH))
    return OUTPUT_PATH


if __name__ == "__main__":
    out = build()
    found_screenshots = sum(
        1
        for n in ("01-home.png", "02-add.png", "03-detail.png", "04-today.png", "05-dashboard.png")
        if (SCREENSHOTS_DIR / n).is_file()
    )
    print(f"==> Presentazione generata: {out}")
    print(f"    Slide totali: 23")
    print(f"    Screenshot trovati: {found_screenshots}/5")
    if found_screenshots < 5:
        print(
            f"    (Cattura gli screenshot mancanti in {SCREENSHOTS_DIR} e rigenera "
            "per sostituire i placeholder.)"
        )
    sys.exit(0)
