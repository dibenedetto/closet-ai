"""Genera la presentazione PowerPoint di ClosetAI.

Output: ``docs/presentation.pptx`` (~13 slide per ~10 min, italiano).

Target: corso di laurea magistrale "Design per l'innovazione sostenibile",
pre-esame. Tono divulgativo, focus sul **cosa** non sul **come**.

Struttura allineata alla slide del docente:

1. Problem setting (sfida sostenibilità)
2. Workflow IA generativa (prompt & tool, confronto, allucinazioni)
3. Strumento Machine Learning (modello, obiettivo)
4. Analisi di sostenibilità (valutazione impatto ambientale)

+ studio di fattibilità (costi, materiali, scalabilità).

Uso:

    uv run python scripts/generate_presentation.py
"""

from __future__ import annotations

import sys
from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN
from pptx.util import Emu, Inches, Pt

ROOT = Path(__file__).resolve().parent.parent.parent
SCREENSHOTS_DIR = ROOT / "docs" / "screenshots"
OUTPUT_PATH = ROOT / "docs" / "presentation.pptx"

# Palette pulita, leggibile a proiettore.
BG = RGBColor(0xF5, 0xF7, 0xFB)
INK = RGBColor(0x1A, 0x1D, 0x27)
MUTED = RGBColor(0x6B, 0x71, 0x82)
ACCENT = RGBColor(0x4A, 0x6D, 0xDC)
ACCENT_SOFT = RGBColor(0xE0, 0xE8, 0xFA)
GREEN = RGBColor(0x2F, 0x8F, 0x6E)
GREEN_SOFT = RGBColor(0xDC, 0xEF, 0xE7)
WARN = RGBColor(0xC8, 0x8B, 0x2E)
DANGER = RGBColor(0xC9, 0x4A, 0x5C)
PANEL = RGBColor(0xFF, 0xFF, 0xFF)
BORDER = RGBColor(0xDC, 0xDF, 0xE8)

SLIDE_W = Inches(13.333)
SLIDE_H = Inches(7.5)


# ============================================================================
# Helpers
# ============================================================================


def _set_slide_background(slide, color: RGBColor) -> None:
    fill = slide.background.fill
    fill.solid()
    fill.fore_color.rgb = color


def _add_textbox(slide, left, top, width, height, text, *, size=18, bold=False,
                 color=INK, align=PP_ALIGN.LEFT, italic=False):
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
                 *, base_size=18, color=INK, line_spacing=10):
    box = slide.shapes.add_textbox(left, top, width, height)
    tf = box.text_frame
    tf.word_wrap = True
    tf.margin_left = Emu(0)
    for i, (text, level) in enumerate(items):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.level = level
        p.space_after = Pt(line_spacing)
        run = p.add_run()
        bullet = "•" if level == 0 else "›"
        run.text = f"{bullet}  {text}"
        run.font.size = Pt(base_size - level * 2)
        run.font.color.rgb = color if level == 0 else MUTED
        run.font.name = "Calibri"
    return box


def _add_card(slide, left, top, width, height, *, fill=PANEL, line=BORDER):
    shape = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height)
    shape.fill.solid()
    shape.fill.fore_color.rgb = fill
    shape.line.color.rgb = line
    shape.line.width = Pt(0.75)
    shape.shadow.inherit = False
    shape.text_frame.margin_left = Inches(0.18)
    shape.text_frame.margin_right = Inches(0.18)
    shape.text_frame.margin_top = Inches(0.12)
    shape.text_frame.margin_bottom = Inches(0.12)
    shape.text_frame.text = ""
    return shape


def _set_card_text(shape, lines: list[tuple[str, dict]]) -> None:
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
        run.font.italic = opts.get("italic", False)
        run.font.color.rgb = opts.get("color", INK)
        run.font.name = "Calibri"


def _add_slide_title(slide, title: str, kicker: str | None = None,
                     subtitle: str | None = None) -> None:
    y = Inches(0.45)
    if kicker:
        _add_textbox(
            slide, Inches(0.6), y, Inches(12), Inches(0.35),
            kicker.upper(), size=11, bold=True, color=ACCENT,
        )
        y += Inches(0.4)
    _add_textbox(
        slide, Inches(0.6), y, Inches(12), Inches(0.7),
        title, size=32, bold=True, color=INK,
    )
    if subtitle:
        _add_textbox(
            slide, Inches(0.6), y + Inches(0.7), Inches(12), Inches(0.5),
            subtitle, size=15, color=MUTED, italic=True,
        )
    underline = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE, Inches(0.6), Inches(1.75), Inches(0.8), Emu(30000)
    )
    underline.fill.solid()
    underline.fill.fore_color.rgb = ACCENT
    underline.line.fill.background()


TOTAL_PAGES = 15


def _add_footer(slide, page_num: int) -> None:
    _add_textbox(
        slide, Inches(0.6), Inches(7.1), Inches(11), Inches(0.3),
        "ClosetAI · Design per l'innovazione sostenibile · pre-esame",
        size=9, color=MUTED,
    )
    _add_textbox(
        slide, Inches(11.8), Inches(7.1), Inches(1), Inches(0.3),
        f"{page_num} / {TOTAL_PAGES}", size=9, color=MUTED, align=PP_ALIGN.RIGHT,
    )


def _add_screenshot_or_placeholder(slide, left, top, width, height,
                                   filename: str, caption: str):
    img_path = SCREENSHOTS_DIR / filename
    if img_path.is_file():
        slide.shapes.add_picture(str(img_path), left, top, width=width, height=height)
        return
    ph = _add_card(slide, left, top, width, height, fill=ACCENT_SOFT, line=ACCENT)
    _set_card_text(
        ph,
        [
            ("[ screenshot ]", {"size": 14, "bold": True, "color": ACCENT, "align": PP_ALIGN.CENTER, "space_after": 8}),
            (filename, {"size": 11, "color": MUTED, "align": PP_ALIGN.CENTER, "space_after": 4}),
            (caption, {"size": 11, "color": MUTED, "italic": True, "align": PP_ALIGN.CENTER}),
        ],
    )


# ============================================================================
# Slides
# ============================================================================


def _new_slide(prs: Presentation):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _set_slide_background(slide, BG)
    return slide


def slide_01_title(prs: Presentation, page: int) -> None:
    slide = _new_slide(prs)
    # Banda decorativa verticale
    band = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), Inches(0.3), SLIDE_H
    )
    band.fill.solid()
    band.fill.fore_color.rgb = ACCENT
    band.line.fill.background()

    _add_textbox(
        slide, Inches(0.9), Inches(1.6), Inches(11), Inches(0.5),
        "PRE-ESAME · PROGETTO AI ECO-SOSTENIBILE", size=12, bold=True, color=ACCENT,
    )
    _add_textbox(
        slide, Inches(0.9), Inches(2.2), Inches(11), Inches(1.4),
        "ClosetAI", size=80, bold=True, color=INK,
    )
    _add_textbox(
        slide, Inches(0.9), Inches(3.7), Inches(11), Inches(0.6),
        "Il guardaroba intelligente che ti aiuta a vestire meglio comprando meno.",
        size=22, color=GREEN, italic=True,
    )
    _add_textbox(
        slide, Inches(0.9), Inches(5.0), Inches(11), Inches(0.4),
        "Design per l'innovazione sostenibile — Università di Pisa",
        size=15, color=MUTED,
    )
    _add_textbox(
        slide, Inches(0.9), Inches(5.4), Inches(11), Inches(0.4),
        "Marco Di Benedetto · A.A. 2025/2026",
        size=14, color=MUTED,
    )
    _ = page


def slide_02_problem(prs: Presentation, page: int) -> None:
    slide = _new_slide(prs)
    _add_slide_title(
        slide, "Compriamo troppi vestiti.",
        kicker="01 · La sfida",
        subtitle="L'industria della moda è una delle più impattanti del pianeta.",
    )

    kpis = [
        ("10%", "delle emissioni globali\ndi CO₂", ACCENT),
        ("5 mln", "tonnellate di vestiti\nbuttati in Europa /anno", DANGER),
        ("7×", "utilizzi medi di un\ncapo fast fashion", WARN),
        ("40%", "del guardaroba medio\nnon viene mai indossato", DANGER),
    ]
    for i, (number, caption, color) in enumerate(kpis):
        x = Inches(0.6 + i * 3.1)
        card = _add_card(slide, x, Inches(2.3), Inches(2.9), Inches(2.0))
        _set_card_text(
            card,
            [
                (number, {"size": 44, "bold": True, "color": color, "align": PP_ALIGN.CENTER, "space_after": 6}),
                (caption, {"size": 12, "color": MUTED, "align": PP_ALIGN.CENTER}),
            ],
        )

    _add_textbox(
        slide, Inches(0.6), Inches(4.8), Inches(12), Inches(0.5),
        "A casa nostra, tre comportamenti ricorrenti:",
        size=18, bold=True,
    )
    _add_bullets(
        slide, Inches(0.6), Inches(5.4), Inches(12), Inches(1.8),
        [
            ("Compriamo d'impulso  — non sappiamo davvero cosa abbiamo già", 0),
            ("Capi 'fantasma'  — vestiti dimenticati nell'armadio, mai indossati", 0),
            ("Buttiamo invece di riparare, scambiare o donare", 0),
        ],
    )
    _add_footer(slide, page)


def slide_03_solution(prs: Presentation, page: int) -> None:
    slide = _new_slide(prs)
    _add_slide_title(
        slide, "Un'app che fa tre cose, insieme.",
        kicker="02 · La soluzione",
    )

    pillars = [
        ("📷", "Digitalizza", "Fotografi un capo: l'app\nlo cataloga in automatico\n(categoria, colore).", ACCENT),
        ("📊", "Traccia", "Un click per dire\n'l'ho indossato oggi':\ncalcola quanto vale\nogni capo nel tempo.", ACCENT),
        ("♻️", "Allunga la vita", "Quando un capo è 'stanco',\nti suggerisce di ripararlo,\nscambiarlo, venderlo o donarlo.\nMisura la CO₂ risparmiata.", GREEN),
    ]
    for i, (icon, title, body, color) in enumerate(pillars):
        x = Inches(0.6 + i * 4.2)
        card = _add_card(slide, x, Inches(2.3), Inches(4.0), Inches(3.6))
        _set_card_text(
            card,
            [
                (icon, {"size": 42, "color": color, "align": PP_ALIGN.CENTER, "space_after": 4}),
                (title, {"size": 22, "bold": True, "color": INK, "align": PP_ALIGN.CENTER, "space_after": 10}),
                (body, {"size": 13, "color": MUTED, "align": PP_ALIGN.CENTER}),
            ],
        )

    _add_textbox(
        slide, Inches(0.6), Inches(6.2), Inches(12), Inches(0.5),
        "Tutto questo dentro un'unica esperienza, senza dover saltare tra app diverse.",
        size=14, color=GREEN, italic=True, align=PP_ALIGN.CENTER,
    )
    _add_footer(slide, page)


def slide_04_user_journey(prs: Presentation, page: int) -> None:
    slide = _new_slide(prs)
    _add_slide_title(
        slide, "Come si usa, in pratica.",
        kicker="03 · L'esperienza utente",
    )

    steps = [
        ("Fotografo", "un nuovo capo\nche ho comprato"),
        ("L'app riconosce", "categoria e colore\nin automatico"),
        ("Indosso", "il capo e clicco\n'✓ oggi' nell'app"),
        ("Chiedo", "'cosa metto oggi?'\nmi propone outfit"),
        ("Vedo", "il mio impatto\nsulla dashboard"),
    ]
    step_w = Inches(2.3)
    gap = Inches(0.15)
    start_x = Inches(0.6)
    for i, (verb, detail) in enumerate(steps):
        x = start_x + (step_w + gap) * i
        card = _add_card(slide, x, Inches(2.5), step_w, Inches(2.4),
                        fill=PANEL, line=BORDER)
        _set_card_text(
            card,
            [
                (f"{i+1}", {"size": 36, "bold": True, "color": ACCENT, "align": PP_ALIGN.CENTER, "space_after": 4}),
                (verb, {"size": 16, "bold": True, "color": INK, "align": PP_ALIGN.CENTER, "space_after": 6}),
                (detail, {"size": 11, "color": MUTED, "align": PP_ALIGN.CENTER}),
            ],
        )
        # Freccia tra step
        if i < len(steps) - 1:
            arrow_x = x + step_w + Inches(0.01)
            arrow = slide.shapes.add_shape(
                MSO_SHAPE.RIGHT_ARROW, arrow_x, Inches(3.5),
                Inches(0.13), Inches(0.4),
            )
            arrow.fill.solid()
            arrow.fill.fore_color.rgb = ACCENT
            arrow.line.fill.background()

    _add_textbox(
        slide, Inches(0.6), Inches(5.3), Inches(12), Inches(0.5),
        "Nessun obbligo, nessun questionario. Tutto avviene con foto e tap.",
        size=14, color=MUTED, italic=True, align=PP_ALIGN.CENTER,
    )

    # Pagina extra: estensione hardware
    _add_textbox(
        slide, Inches(0.6), Inches(6.1), Inches(12), Inches(0.4),
        "🪞  Estensione opzionale: uno specchio smart in camera mostra orologio, meteo e l'outfit suggerito.",
        size=13, color=GREEN, italic=True, align=PP_ALIGN.CENTER,
    )
    _add_footer(slide, page)


def slide_05_demo_home(prs: Presentation, page: int) -> None:
    slide = _new_slide(prs)
    _add_slide_title(
        slide, "Il guardaroba digitale",
        kicker="04 · Demo · schermata 1",
        subtitle="In cima trovo subito le metriche chiave del mio armadio.",
    )
    _add_screenshot_or_placeholder(
        slide, Inches(0.6), Inches(2.1), Inches(8.0), Inches(4.7),
        "01-home.png", "Pagina principale con filtri",
    )
    bullets = _add_card(slide, Inches(8.9), Inches(2.1), Inches(4.0), Inches(4.7),
                       fill=ACCENT_SOFT, line=ACCENT)
    _set_card_text(
        bullets,
        [
            ("Cosa si vede:", {"size": 14, "bold": True, "color": ACCENT, "space_after": 10}),
            ("→ N° capi attivi", {"size": 13, "color": INK, "space_after": 6}),
            ("→ Utilizzi totali", {"size": 13, "color": INK, "space_after": 6}),
            ("→ Quanti 'fantasma'", {"size": 13, "color": INK, "space_after": 6}),
            ("→ Cost-per-wear medio", {"size": 13, "color": INK, "space_after": 12}),
            ("Filtri per categoria,", {"size": 13, "color": MUTED, "space_after": 2}),
            ("colore, stato attivo/", {"size": 13, "color": MUTED, "space_after": 2}),
            ("ritirato + ricerca.", {"size": 13, "color": MUTED, "space_after": 10}),
            ("Tasto rapido 'indossato", {"size": 13, "color": GREEN, "space_after": 2}),
            ("oggi' sulla card.", {"size": 13, "color": GREEN}),
        ],
    )
    _add_footer(slide, page)


def slide_06_demo_today_dashboard(prs: Presentation, page: int) -> None:
    slide = _new_slide(prs)
    _add_slide_title(
        slide, "Cosa metto oggi? + Dashboard impatto",
        kicker="04 · Demo · schermate 2 e 3",
        subtitle="L'AI propone outfit basati sul meteo. La dashboard mostra l'impatto.",
    )
    _add_screenshot_or_placeholder(
        slide, Inches(0.6), Inches(2.1), Inches(6.0), Inches(4.7),
        "04-today.png", "Proposte outfit del giorno",
    )
    _add_screenshot_or_placeholder(
        slide, Inches(6.9), Inches(2.1), Inches(6.0), Inches(4.7),
        "05-dashboard.png", "Dashboard impatto sostenibilità",
    )
    _add_footer(slide, page)


def slide_07_ai_map(prs: Presentation, page: int) -> None:
    slide = _new_slide(prs)
    _add_slide_title(
        slide, "Dove c'è l'intelligenza artificiale.",
        kicker="05 · Il cuore del progetto",
        subtitle="Sette punti del prodotto in cui un modello AI fa il lavoro al posto tuo.",
    )

    uses = [
        ("📷", "Riconosce il capo", "Capisce da sola se è una\nt-shirt blu o una giacca\nmarrone.", "Vision"),
        ("🎨", "Estrae il colore", "Trova il colore dominante\nignorando lo sfondo bianco.", "Vision"),
        ("👗", "Suggerisce outfit", "Combina i capi che hai\ncon meteo + regole estetiche.", "Regole + AI"),
        ("🛠️", "Diagnostica la condizione", "Capisce se un capo è nuovo,\nbuono, usurato o danneggiato.", "Regole"),
        ("✍️", "Descrive il capo", "Scrive una breve descrizione\ndel capo in italiano.", "AI generativa"),
        ("💬", "Coach sostenibilità", "Ti dà consigli personalizzati\nsul tuo guardaroba.", "AI generativa"),
        ("📖", "Tutorial riparazione", "Crea istruzioni passo-passo\nper riparare il difetto.", "AI generativa"),
        ("🪞", "Prova virtuale (try-on)", "Genera un'immagine di te\nche indossi il capo.", "AI generativa"),
    ]
    col_w = Inches(3.05)
    row_h = Inches(1.2)
    start_x = Inches(0.6)
    start_y = Inches(2.1)
    gap_x = Inches(0.1)
    gap_y = Inches(0.12)
    for i, (icon, title, desc, badge) in enumerate(uses):
        col = i % 4
        row = i // 4
        x = start_x + (col_w + gap_x) * col
        y = start_y + (row_h + gap_y) * row
        is_gen = badge == "AI generativa"
        color = GREEN if is_gen else ACCENT
        soft = GREEN_SOFT if is_gen else ACCENT_SOFT
        card = _add_card(slide, x, y, col_w, row_h, fill=soft, line=color)
        _set_card_text(
            card,
            [
                (f"{icon}  {title}", {"size": 13, "bold": True, "color": INK, "space_after": 2}),
                (desc, {"size": 10, "color": MUTED, "space_after": 2}),
                (badge, {"size": 9, "bold": True, "color": color, "italic": True}),
            ],
        )

    legend = _add_card(slide, Inches(0.6), Inches(4.8), Inches(12.3), Inches(2.0),
                      fill=PANEL, line=BORDER)
    _set_card_text(
        legend,
        [
            ("Due tipi di AI, due ruoli ben distinti:", {"size": 15, "bold": True, "color": INK, "space_after": 8}),
            ("🟦  AI applicata  → riconoscere, classificare, dare suggerimenti basati su regole.",
             {"size": 13, "color": ACCENT, "space_after": 4}),
            ("🟩  AI generativa  → produrre nuovi contenuti (testi, immagini) personalizzati per te.",
             {"size": 13, "color": GREEN, "space_after": 6}),
            ("Questa distinzione era proprio quello che il corso ci chiedeva di dimostrare.",
             {"size": 12, "color": MUTED, "italic": True}),
        ],
    )
    _add_footer(slide, page)


def slide_07b_ai_pipeline(prs: Presentation, page: int) -> None:
    slide = _new_slide(prs)
    _add_slide_title(
        slide, "Come lavorano insieme i modelli AI.",
        kicker="05b · La pipeline",
        subtitle="Blu = pre-addestrato · Verde = rete addestrata da noi. Due livelli collegati dai dati.",
    )

    # ── Fascia 1: per ogni capo ──────────────────────────────────────────
    _add_textbox(slide, Inches(0.6), Inches(1.95), Inches(12), Inches(0.35),
                 "📷  PER OGNI CAPO · dalla foto", size=12, bold=True, color=INK)

    capo_boxes = [
        ("Fashion-CLIP", "pre-addestrato", "→ categoria + colore", ACCENT, ACCENT_SOFT),
        ("Rete stato + tutorial", "addestrata da noi", "→ nuovo / usurato /\ndanneggiato\n→ tutorial di recupero", GREEN, GREEN_SOFT),
        ("Tabella CO₂", "Ellen MacArthur", "→ impatto energetico\ndel singolo capo", WARN, PANEL),
    ]
    box_w = Inches(4.0)
    for i, (title, kind, out, color, soft) in enumerate(capo_boxes):
        x = Inches(0.6) + (box_w + Inches(0.17)) * i
        card = _add_card(slide, x, Inches(2.35), box_w, Inches(1.9), fill=soft, line=color)
        _set_card_text(
            card,
            [
                (title, {"size": 15, "bold": True, "color": INK, "space_after": 2}),
                (kind, {"size": 10, "italic": True, "color": color, "space_after": 8}),
                (out, {"size": 12, "color": MUTED}),
            ],
        )

    # freccia "i dati si accumulano"
    arrow = slide.shapes.add_shape(MSO_SHAPE.DOWN_ARROW, Inches(6.3), Inches(4.35),
                                   Inches(0.7), Inches(0.45))
    arrow.fill.solid()
    arrow.fill.fore_color.rgb = INK
    arrow.line.fill.background()
    _add_textbox(slide, Inches(7.1), Inches(4.42), Inches(6), Inches(0.4),
                 "le etichette di ogni capo si accumulano nel guardaroba",
                 size=11, italic=True, color=MUTED)

    # ── Fascia 2: su tutto il guardaroba ─────────────────────────────────
    _add_textbox(slide, Inches(0.6), Inches(4.95), Inches(12), Inches(0.35),
                 "🧩  SU TUTTO IL GUARDAROBA · sull'insieme dei capi", size=12, bold=True, color=INK)

    g1 = _add_card(slide, Inches(0.6), Inches(5.35), Inches(6.05), Inches(1.4),
                   fill=GREEN_SOFT, line=GREEN)
    _set_card_text(
        g1,
        [
            ("Rete gap analysis", {"size": 15, "bold": True, "color": INK, "space_after": 2}),
            ("addestrata da noi · non guarda le foto, guarda l'inventario",
             {"size": 10, "italic": True, "color": GREEN, "space_after": 6}),
            ("→ vuoti funzionali: \"manca una giacca\", \"troppe t-shirt\"",
             {"size": 12, "color": MUTED}),
        ],
    )
    g2 = _add_card(slide, Inches(6.85), Inches(5.35), Inches(6.05), Inches(1.4),
                   fill=GREEN_SOFT, line=GREEN)
    _set_card_text(
        g2,
        [
            ("Somma impatti evitati", {"size": 15, "bold": True, "color": INK, "space_after": 2}),
            ("azioni circolari × % di CO₂ risparmiata",
             {"size": 10, "italic": True, "color": GREEN, "space_after": 6}),
            ("→ CO₂ totale evitata, mostrata nella dashboard impatto",
             {"size": 12, "color": MUTED}),
        ],
    )
    _add_footer(slide, page)


def slide_08_workflow_genai(prs: Presentation, page: int) -> None:
    slide = _new_slide(prs)
    _add_slide_title(
        slide, "Come ho usato l'AI generativa per costruire il progetto.",
        kicker="06 · Workflow",
        subtitle="Strumenti, prompt, confronto e (sì) allucinazioni incontrate.",
    )

    # Tool table
    tools_card = _add_card(slide, Inches(0.6), Inches(2.1), Inches(6.0), Inches(4.7),
                          fill=PANEL, line=BORDER)
    _set_card_text(
        tools_card,
        [
            ("STRUMENTI USATI", {"size": 11, "bold": True, "color": ACCENT, "space_after": 8}),
            ("Claude (Anthropic)", {"size": 14, "bold": True, "color": INK, "space_after": 2}),
            ("Codice, design dell'architettura,", {"size": 11, "color": MUTED, "space_after": 2}),
            ("scrittura della documentazione.", {"size": 11, "color": MUTED, "space_after": 10}),
            ("Fashion-CLIP (HuggingFace)", {"size": 14, "bold": True, "color": INK, "space_after": 2}),
            ("Modello pre-addestrato che riconosce i capi.", {"size": 11, "color": MUTED, "space_after": 10}),
            ("Stable Diffusion (HuggingFace)", {"size": 14, "bold": True, "color": INK, "space_after": 2}),
            ("Modello generativo per il try-on virtuale.", {"size": 11, "color": MUTED, "space_after": 10}),
            ("python-pptx + Claude", {"size": 14, "bold": True, "color": INK, "space_after": 2}),
            ("Questa stessa presentazione è generata", {"size": 11, "color": MUTED, "space_after": 0}),
            ("automaticamente da uno script.", {"size": 11, "color": MUTED}),
        ],
    )

    # Confronto + allucinazioni
    cmp_card = _add_card(slide, Inches(6.9), Inches(2.1), Inches(6.0), Inches(2.25),
                        fill=ACCENT_SOFT, line=ACCENT)
    _set_card_text(
        cmp_card,
        [
            ("CONFRONTO ALTERNATIVE", {"size": 11, "bold": True, "color": ACCENT, "space_after": 6}),
            ("Cloud (Claude, OpenAI) vs Locale (Ollama):", {"size": 12, "bold": True, "color": INK, "space_after": 2}),
            ("→ cloud = qualità superiore", {"size": 11, "color": MUTED, "space_after": 2}),
            ("→ locale = privacy + zero costi", {"size": 11, "color": MUTED, "space_after": 6}),
            ("Fashion-CLIP vs CLIP generico:", {"size": 12, "bold": True, "color": INK, "space_after": 2}),
            ("→ il primo conosce 700k immagini di moda,", {"size": 11, "color": MUTED, "space_after": 2}),
            ("riconosce molto meglio i capi.", {"size": 11, "color": MUTED}),
        ],
    )
    hall_card = _add_card(slide, Inches(6.9), Inches(4.55), Inches(6.0), Inches(2.25),
                         fill=GREEN_SOFT, line=DANGER)
    _set_card_text(
        hall_card,
        [
            ("ALLUCINAZIONI INCONTRATE", {"size": 11, "bold": True, "color": DANGER, "space_after": 6}),
            ("• AI che propone materiali poco realistici", {"size": 11, "color": INK, "space_after": 2}),
            ("  per riparare una zip (es. colla termica)", {"size": 10, "color": MUTED, "space_after": 6}),
            ("• AI che inventa funzioni del linguaggio", {"size": 11, "color": INK, "space_after": 2}),
            ("  TypeScript non ancora disponibili", {"size": 10, "color": MUTED, "space_after": 6}),
            ("Soluzione: verifica umana + fallback su una", {"size": 11, "italic": True, "color": MUTED, "space_after": 2}),
            ("base di tutorial 'sicuri' scritti a mano.", {"size": 11, "italic": True, "color": MUTED}),
        ],
    )
    _add_footer(slide, page)


def slide_09a_ml_pretrained(prs: Presentation, page: int) -> None:
    slide = _new_slide(prs)
    _add_slide_title(
        slide, "Riconoscere il capo (Fashion-CLIP)",
        kicker="07a · ML applicato — modello pre-addestrato",
        subtitle="Un modello vision già addestrato che adattiamo al nostro guardaroba.",
    )

    # Modello
    model_card = _add_card(slide, Inches(0.6), Inches(2.1), Inches(6.0), Inches(2.3),
                          fill=PANEL, line=ACCENT)
    _set_card_text(
        model_card,
        [
            ("MODELLO", {"size": 11, "bold": True, "color": ACCENT, "space_after": 4}),
            ("Fashion-CLIP", {"size": 22, "bold": True, "color": INK, "space_after": 6}),
            ("Sviluppato da Patrick John Chia (2023), pre-addestrato", {"size": 12, "color": MUTED, "space_after": 2}),
            ("su 700.000 immagini di capi di abbigliamento.", {"size": 12, "color": MUTED, "space_after": 4}),
            ("Open-source, gratuito, scaricabile da HuggingFace.", {"size": 12, "italic": True, "color": GREEN}),
        ],
    )
    # Obiettivo
    obj_card = _add_card(slide, Inches(6.9), Inches(2.1), Inches(6.0), Inches(2.3),
                        fill=PANEL, line=ACCENT)
    _set_card_text(
        obj_card,
        [
            ("OBIETTIVO", {"size": 11, "bold": True, "color": ACCENT, "space_after": 4}),
            ("Classificazione zero-shot", {"size": 18, "bold": True, "color": INK, "space_after": 6}),
            ("Una foto in ingresso → l'AI decide a quale", {"size": 12, "color": MUTED, "space_after": 2}),
            ("delle 14 categorie appartiene (t-shirt, jeans,", {"size": 12, "color": MUTED, "space_after": 2}),
            ("camicia, vestito, scarpe, …) e quanto è sicura.", {"size": 12, "color": MUTED, "space_after": 4}),
            ("Non serve riaddestrare: le categorie le scelgo io.", {"size": 12, "italic": True, "color": GREEN}),
        ],
    )

    # Pipeline visuale
    _add_textbox(
        slide, Inches(0.6), Inches(4.65), Inches(12), Inches(0.4),
        "Il flusso, semplificato:", size=14, bold=True,
    )
    steps = [
        ("📷", "Foto del capo"),
        ("🧠", "Fashion-CLIP la 'guarda'"),
        ("🏷️", "Restituisce: categoria,\ncolore, confidenza"),
        ("💾", "Salvo nel guardaroba"),
    ]
    step_w = Inches(2.7)
    gap = Inches(0.3)
    start_x = Inches(0.6)
    for i, (icon, label) in enumerate(steps):
        x = start_x + (step_w + gap) * i
        card = _add_card(slide, x, Inches(5.2), step_w, Inches(1.5),
                        fill=ACCENT_SOFT, line=ACCENT)
        _set_card_text(
            card,
            [
                (icon, {"size": 28, "color": ACCENT, "align": PP_ALIGN.CENTER, "space_after": 2}),
                (label, {"size": 11, "color": INK, "align": PP_ALIGN.CENTER}),
            ],
        )
        if i < len(steps) - 1:
            arrow_x = x + step_w + Inches(0.05)
            arrow = slide.shapes.add_shape(
                MSO_SHAPE.RIGHT_ARROW, arrow_x, Inches(5.85),
                Inches(0.2), Inches(0.3),
            )
            arrow.fill.solid()
            arrow.fill.fore_color.rgb = ACCENT
            arrow.line.fill.background()
    _add_footer(slide, page)


def slide_09b_ml_trained(prs: Presentation, page: int) -> None:
    slide = _new_slide(prs)
    _add_slide_title(
        slide, "Tre modelli addestrati da noi",
        kicker="07b · ML applicato — codice Python in notebook",
        subtitle="ml/notebooks/closetai_ml.ipynb: classificazione + regressione + clustering.",
    )

    tasks = [
        ("🎯", "Classificazione",
         "Predire se un capo diventerà 'fantasma'.\n\nModello: Logistic Regression\n\nEs.: 'Attenzione, hai già 3\ncappotti acquistati a maggio.'",
         "AUC ≈ 0,80"),
        ("📈", "Regressione",
         "Stimare gli utilizzi nei prossimi\n90 giorni.\n\nModello: Random Forest\n\nEs.: 'Questo capo verrà indossato\n~6 volte → cost-per-wear € 5,80'",
         "MAE ≈ 2-3 utilizzi"),
        ("🧩", "Clustering",
         "Raggruppare i capi in 'stili'\nsenza etichette.\n\nModello: K-Means (K=5) + PCA\n\nEs.: 'cluster casual estivo',\n'occasioni formali'.",
         "Silhouette ≈ 0,30"),
    ]
    for i, (icon, title, body, metric) in enumerate(tasks):
        x = Inches(0.6 + i * 4.2)
        card = _add_card(slide, x, Inches(2.1), Inches(4.0), Inches(4.0),
                        fill=ACCENT_SOFT, line=ACCENT)
        _set_card_text(
            card,
            [
                (f"{icon}  {title}", {"size": 18, "bold": True, "color": INK, "space_after": 8}),
                (body, {"size": 12, "color": MUTED, "space_after": 10}),
                (metric, {"size": 14, "bold": True, "color": GREEN}),
            ],
        )

    note = _add_card(slide, Inches(0.6), Inches(6.2), Inches(12.3), Inches(0.7),
                    fill=GREEN_SOFT, line=GREEN)
    _set_card_text(
        note,
        [
            ("Tutto su dati realistici sintetici (300 capi). Per il prodotto reale, basta sostituirli col wear log dell'utente.",
             {"size": 12, "color": INK, "italic": True, "align": PP_ALIGN.CENTER}),
        ],
    )
    _add_footer(slide, page)


def slide_10_sustainability(prs: Presentation, page: int) -> None:
    slide = _new_slide(prs)
    _add_slide_title(
        slide, "Analisi di sostenibilità",
        kicker="08 · L'impatto",
        subtitle="Ogni azione viene tradotta in CO₂ risparmiata, con equivalenze concrete.",
    )

    # Big metric
    hero = _add_card(slide, Inches(0.6), Inches(2.1), Inches(5.0), Inches(4.7),
                    fill=GREEN_SOFT, line=GREEN)
    _set_card_text(
        hero,
        [
            ("ESEMPIO DI DEMO", {"size": 11, "bold": True, "color": GREEN, "align": PP_ALIGN.CENTER, "space_after": 12}),
            ("65 kg", {"size": 72, "bold": True, "color": GREEN, "align": PP_ALIGN.CENTER, "space_after": 4}),
            ("di CO₂ evitati", {"size": 18, "color": INK, "align": PP_ALIGN.CENTER, "space_after": 20}),
            ("equivalente a:", {"size": 13, "color": MUTED, "align": PP_ALIGN.CENTER, "space_after": 10}),
            ("≈ 360 km in auto risparmiati", {"size": 14, "bold": True, "color": INK, "align": PP_ALIGN.CENTER, "space_after": 4}),
            ("≈ 8 m² di foresta /anno", {"size": 14, "bold": True, "color": INK, "align": PP_ALIGN.CENTER, "space_after": 4}),
            ("≈ 0,8 voli Pisa-Roma", {"size": 14, "bold": True, "color": INK, "align": PP_ALIGN.CENTER}),
        ],
    )

    # How we compute
    how = _add_card(slide, Inches(5.9), Inches(2.1), Inches(7.0), Inches(4.7),
                   fill=PANEL, line=BORDER)
    _set_card_text(
        how,
        [
            ("COME LO MISURIAMO", {"size": 11, "bold": True, "color": ACCENT, "space_after": 8}),
            ("Per ogni capo, conosciamo la sua impronta CO₂", {"size": 13, "color": INK, "space_after": 4}),
            ("di produzione (fonte: Ellen MacArthur Foundation):", {"size": 13, "color": INK, "space_after": 10}),
            ("• T-shirt:  7 kg     • Jeans:    32 kg", {"size": 13, "color": MUTED, "space_after": 4}),
            ("• Camicia: 10 kg     • Giacca:   25 kg", {"size": 13, "color": MUTED, "space_after": 4}),
            ("• Maglione: 14 kg    • Cappotto: 40 kg", {"size": 13, "color": MUTED, "space_after": 16}),
            ("Per ogni azione circolare, una % evitata:", {"size": 13, "color": INK, "space_after": 8}),
            ("• Donare / scambiare / vendere → 100%", {"size": 13, "color": GREEN, "space_after": 4}),
            ("• Riparare → 70%   • Riciclare → 30%", {"size": 13, "color": GREEN, "space_after": 12}),
            ("Es. donare una giacca = 25 kg risparmiati.", {"size": 13, "italic": True, "color": MUTED}),
        ],
    )
    _add_footer(slide, page)


def slide_11_feasibility(prs: Presentation, page: int) -> None:
    slide = _new_slide(prs)
    _add_slide_title(
        slide, "Studio di fattibilità",
        kicker="09 · Costi, materiali, scalabilità",
        subtitle="Si può davvero portare un prodotto del genere sul mercato?",
    )

    cols = [
        ("💰 Costi", ACCENT, [
            "Hardware: laptop + telefono.",
            "Modelli AI: tutti gratuiti / open-source.",
            "Cloud opzionale: ~€ 0,01 a utente/mese",
            "(grazie al caching delle risposte).",
            "Specchio smart: ~€ 200 una tantum.",
        ]),
        ("🧱 Materiali", GREEN, [
            "Tutto open-source (no licenze):",
            "FastAPI, React, Fashion-CLIP,",
            "Stable Diffusion, ChromaDB.",
            "Ne consegue piena trasparenza,",
            "audit possibile, no lock-in vendor.",
        ]),
        ("📈 Scalabilità", WARN, [
            "MVP: single-user, locale.",
            "→ Cloud per multi-utente (Postgres+S3).",
            "→ AI on-device per privacy estrema.",
            "→ Versione enterprise con marketplace",
            "second-hand integrato.",
        ]),
    ]
    for i, (title, color, items) in enumerate(cols):
        x = Inches(0.6 + i * 4.2)
        card = _add_card(slide, x, Inches(2.1), Inches(4.0), Inches(4.7),
                        fill=PANEL, line=color)
        lines = [(title, {"size": 18, "bold": True, "color": color, "space_after": 10})]
        for item in items:
            lines.append((item, {"size": 12, "color": INK, "space_after": 6}))
        _set_card_text(card, lines)
    _add_footer(slide, page)


def slide_12_limits_future(prs: Presentation, page: int) -> None:
    slide = _new_slide(prs)
    _add_slide_title(
        slide, "Cosa il prototipo non fa (ancora).",
        kicker="10 · Onestà intellettuale",
        subtitle="E dove potrebbe andare in futuro.",
    )
    cols = [
        ("Limitazioni di oggi", DANGER, [
            "I modelli AI sono pensati per moda occidentale: meno precisi su capi etnici.",
            "Le stime di CO₂ sono medie per categoria, non una vera analisi del ciclo di vita.",
            "Il try-on virtuale è un'illusione visiva, non un vero camerino digitale.",
            "Per ora è personale: non ci sono account né condivisione.",
        ]),
        ("Estensioni naturali", GREEN, [
            "Riconoscere automaticamente l'outfit dalla foto di uno specchio.",
            "Integrare marketplace second-hand (Vinted, Wallapop) per chiudere il cerchio della vendita.",
            "Modalità famiglia / armadio condiviso.",
            "Suggerimento pre-acquisto: 'questo capo riempie un vuoto del tuo guardaroba?'",
        ]),
    ]
    for i, (title, color, items) in enumerate(cols):
        x = Inches(0.6 + i * 6.3)
        card = _add_card(slide, x, Inches(2.1), Inches(6.1), Inches(4.7),
                        fill=PANEL, line=color)
        lines = [(title, {"size": 18, "bold": True, "color": color, "space_after": 12})]
        for item in items:
            lines.append((f"•  {item}", {"size": 13, "color": INK, "space_after": 10}))
        _set_card_text(card, lines)
    _add_footer(slide, page)


def slide_13_closing(prs: Presentation, page: int) -> None:
    slide = _new_slide(prs)
    band = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), Inches(0.3), SLIDE_H
    )
    band.fill.solid()
    band.fill.fore_color.rgb = GREEN
    band.line.fill.background()

    _add_textbox(
        slide, Inches(0.9), Inches(2.0), Inches(11), Inches(1.1),
        "Grazie.", size=72, bold=True, color=INK,
    )
    _add_textbox(
        slide, Inches(0.9), Inches(3.2), Inches(11), Inches(0.7),
        "Vesti meglio. Compra meno. Allunga la vita dei tuoi capi.",
        size=22, color=GREEN, italic=True,
    )
    _add_textbox(
        slide, Inches(0.9), Inches(4.5), Inches(11), Inches(0.5),
        "Domande?", size=24, color=ACCENT,
    )

    box = _add_card(slide, Inches(0.9), Inches(5.4), Inches(11.5), Inches(1.4),
                   fill=PANEL, line=BORDER)
    _set_card_text(
        box,
        [
            ("Materiale di approfondimento (per chi vuole guardare):",
             {"size": 13, "bold": True, "color": ACCENT, "space_after": 6}),
            ("→ Codice, documentazione e roadmap completi su questo repository.",
             {"size": 13, "color": INK, "space_after": 4}),
            ("→ Architettura, decisioni tecniche e analisi di impatto in docs/.",
             {"size": 13, "color": INK}),
        ],
    )
    _ = page


# ============================================================================
# Build
# ============================================================================


def build() -> Path:
    prs = Presentation()
    prs.slide_width = SLIDE_W
    prs.slide_height = SLIDE_H

    slides = [
        slide_01_title,
        slide_02_problem,
        slide_03_solution,
        slide_04_user_journey,
        slide_05_demo_home,
        slide_06_demo_today_dashboard,
        slide_07_ai_map,
        slide_07b_ai_pipeline,
        slide_08_workflow_genai,
        slide_09a_ml_pretrained,
        slide_09b_ml_trained,
        slide_10_sustainability,
        slide_11_feasibility,
        slide_12_limits_future,
        slide_13_closing,
    ]

    for i, builder in enumerate(slides, start=1):
        builder(prs, i)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    prs.save(str(OUTPUT_PATH))
    return OUTPUT_PATH


if __name__ == "__main__":
    out = build()
    expected_screenshots = ("01-home.png", "02-add.png", "03-detail.png",
                            "04-today.png", "05-dashboard.png")
    found = sum(1 for n in expected_screenshots if (SCREENSHOTS_DIR / n).is_file())
    print(f"==> Presentazione generata: {out}")
    print(f"    Slide totali: {TOTAL_PAGES}  (target: ~10 min di parlato)")
    print(f"    Screenshot trovati: {found}/{len(expected_screenshots)}")
    if found < len(expected_screenshots):
        missing = [n for n in expected_screenshots if not (SCREENSHOTS_DIR / n).is_file()]
        print(f"    Mancanti: {', '.join(missing)}")
        print(f"    Aggiungili in {SCREENSHOTS_DIR} e rigenera per sostituire i placeholder.")
    sys.exit(0)
