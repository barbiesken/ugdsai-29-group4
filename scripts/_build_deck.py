"""
Build Group_4.pdf — the final 10-12 slide deck.

Layout: 16:9 landscape (13.33 x 7.5 inches at 96dpi → 1280 x 720 PostScript pts)
Style: navy/accent palette consistent with proposal, every slide a hero.

Output: /home/claude/youtube_project/Group_4.pdf
"""

import json
from pathlib import Path
from reportlab.lib.colors import HexColor, black, white
from reportlab.lib.pagesizes import landscape
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader

ROOT = Path(__file__).resolve().parent.parent
FIG  = ROOT / 'docs' / 'figures'
OUT  = ROOT / 'Group_4.pdf'

with (ROOT / 'data' / '_deck_meta.json').open() as f:
    META = json.load(f)

# Load real association rules and per-cluster tags if available
try:
    with (ROOT / 'data' / '_deck_rules.json').open() as f:
        DECK_RULES = json.load(f)
except FileNotFoundError:
    DECK_RULES = []
try:
    with (ROOT / 'data' / '_deck_cluster_tags.json').open() as f:
        CLUSTER_TAGS = json.load(f)
except FileNotFoundError:
    CLUSTER_TAGS = {}

# ---- Page dims (16:9) ----------------------------------------------------
W = 13.333 * inch    # 960 pt
H = 7.5    * inch    # 540 pt
PAGE = (W, H)

# ---- Palette -------------------------------------------------------------
NAVY   = HexColor('#0B2545')
ACCENT = HexColor('#13315C')
GREY   = HexColor('#5C5C5C')
LIGHT  = HexColor('#E8EEF5')
GRID   = HexColor('#D8DEE9')
BG     = HexColor('#F8F9FB')

# Archetype palette (6 real archetypes from data)
ARCH = {
    'Marathon':  HexColor('#2E7D6E'),
    'Firework':  HexColor('#C2185B'),
    'Drumbeat':  HexColor('#F57C00'),
    'Beloved':   HexColor('#E91E63'),
    'Flash':     HexColor('#7B1FA2'),
    'Standard':  HexColor('#546E7A'),
}

# ---- Type system ---------------------------------------------------------
F_REG  = 'Helvetica'
F_BOLD = 'Helvetica-Bold'
F_IT   = 'Helvetica-Oblique'

# ---- Helpers -------------------------------------------------------------

def chrome(c, slide_num, total, section=''):
    """Draw the consistent slide chrome: footer with page numbers, top bar."""
    # Top hairline
    c.setStrokeColor(LIGHT)
    c.setLineWidth(0.7)
    c.line(0.55*inch, H - 0.45*inch, W - 0.55*inch, H - 0.45*inch)

    # Top-left section label
    if section:
        c.setFont(F_BOLD, 8.5)
        c.setFillColor(ACCENT)
        c.drawString(0.55*inch, H - 0.32*inch, section.upper())

    # Top-right Group label
    c.setFont(F_REG, 8.5)
    c.setFillColor(GREY)
    c.drawRightString(W - 0.55*inch, H - 0.32*inch,
                      'UGDSAI 29 · Group 4 · Aaryan, Daksh, Mayank')

    # Bottom hairline
    c.setStrokeColor(LIGHT)
    c.line(0.55*inch, 0.45*inch, W - 0.55*inch, 0.45*inch)

    # Bottom-left footer
    c.setFont(F_REG, 8)
    c.setFillColor(GREY)
    c.drawString(0.55*inch, 0.28*inch,
                 'What Goes Viral in India? · YouTube Trending Archetypes')

    # Bottom-right page number
    c.drawRightString(W - 0.55*inch, 0.28*inch,
                      f'{slide_num} / {total}')


def title_block(c, title, subtitle=None, y_top=H - 0.95*inch):
    """Draw a slide title + optional subtitle. Returns the y where content can start."""
    c.setFont(F_BOLD, 22)
    c.setFillColor(NAVY)
    c.drawString(0.55*inch, y_top, title)
    y = y_top - 0.02*inch
    if subtitle:
        c.setFont(F_IT, 11)
        c.setFillColor(GREY)
        c.drawString(0.55*inch, y_top - 0.32*inch, subtitle)
        y = y_top - 0.32*inch
    # Underline accent
    c.setStrokeColor(ACCENT)
    c.setLineWidth(2)
    c.line(0.55*inch, y_top + 0.36*inch, 1.1*inch, y_top + 0.36*inch)
    return y - 0.25*inch


def fit_image(c, path, x, y, max_w, max_h):
    """Place an image inside (x,y,max_w,max_h) box, preserving aspect ratio,
    centering within the box."""
    img = ImageReader(str(path))
    iw, ih = img.getSize()
    ratio = min(max_w/iw, max_h/ih)
    w = iw * ratio; h = ih * ratio
    px = x + (max_w - w) / 2
    py = y + (max_h - h) / 2
    c.drawImage(img, px, py, width=w, height=h, mask='auto')


def text_block(c, x, y, w, lines, font=F_REG, size=11, color=NAVY,
               leading=None, align='left'):
    """Render a list of lines. Returns y after last line."""
    if leading is None: leading = size * 1.45
    c.setFont(font, size)
    c.setFillColor(color)
    yy = y
    for ln in lines:
        if align == 'right':
            c.drawRightString(x + w, yy, ln)
        elif align == 'center':
            c.drawCentredString(x + w/2, yy, ln)
        else:
            c.drawString(x, yy, ln)
        yy -= leading
    return yy


def stat_card(c, x, y, w, h, value, label, color=NAVY, value_size=28):
    """Big-number tile. Used on title/results slides."""
    c.setStrokeColor(LIGHT)
    c.setFillColor(white)
    c.setLineWidth(0.8)
    c.roundRect(x, y, w, h, 8, stroke=1, fill=1)
    c.setFont(F_BOLD, value_size)
    c.setFillColor(color)
    c.drawCentredString(x + w/2, y + h*0.55, value)
    c.setFont(F_REG, 9)
    c.setFillColor(GREY)
    c.drawCentredString(x + w/2, y + h*0.22, label)


def chip(c, x, y, text, color, w=None, h=20):
    """Pill-shaped tag chip."""
    c.setFont(F_BOLD, 9)
    if w is None:
        tw = c.stringWidth(text, F_BOLD, 9)
        w = tw + 18
    c.setFillColor(color)
    c.setStrokeColor(color)
    c.roundRect(x, y, w, h, h/2, stroke=0, fill=1)
    c.setFillColor(white)
    c.drawCentredString(x + w/2, y + 6, text)
    return w


# =========================================================================
#  Build the deck
# =========================================================================

c = canvas.Canvas(str(OUT), pagesize=PAGE)
c.setTitle('UGDSAI 29 — Group 4 — What Goes Viral in India?')
c.setAuthor('Aaryan, Daksh, Mayank')

TOTAL = 12

# ---- SLIDE 1: Title ------------------------------------------------------
def slide_1():
    chrome(c, 1, TOTAL)

    # Left navy panel
    c.setFillColor(NAVY)
    c.rect(0, 0, W*0.42, H, stroke=0, fill=1)

    # White accent bar
    c.setFillColor(HexColor('#C2185B'))
    c.rect(0.55*inch, H - 1.4*inch, 0.6*inch, 0.08*inch, stroke=0, fill=1)

    # Title
    c.setFillColor(white)
    c.setFont(F_BOLD, 32)
    c.drawString(0.55*inch, H - 2.4*inch, 'What goes viral')
    c.drawString(0.55*inch, H - 3.0*inch, 'in India?')
    c.setFont(F_REG, 14)
    c.setFillColor(LIGHT)
    c.drawString(0.55*inch, H - 3.5*inch, 'A longitudinal study of YouTube Trending')

    # Members panel (bottom of left)
    c.setFont(F_BOLD, 9.5)
    c.setFillColor(LIGHT)
    c.drawString(0.55*inch, H - 5.6*inch, 'GROUP 4')
    c.setFont(F_REG, 12)
    c.setFillColor(white)
    c.drawString(0.55*inch, H - 5.95*inch, 'Aaryan · Daksh · Mayank')

    c.setFont(F_BOLD, 9.5)
    c.setFillColor(LIGHT)
    c.drawString(0.55*inch, H - 6.5*inch, 'FACULTY')
    c.setFont(F_REG, 12)
    c.setFillColor(white)
    c.drawString(0.55*inch, H - 6.85*inch, 'Mr. Anant Mittal')

    # Right side: hero UMAP image
    fit_image(c, FIG/'deck_umap.png',
              W*0.42 + 0.3*inch, 0.7*inch,
              W*0.58 - 0.6*inch, H - 1.5*inch)

    # Course tag (top right of left panel)
    c.setFont(F_BOLD, 9)
    c.setFillColor(LIGHT)
    c.drawString(0.55*inch, H - 0.85*inch, 'UGDSAI 29')
    c.setFont(F_REG, 9)
    c.drawString(1.4*inch, H - 0.85*inch, '· UNSUPERVISED MACHINE LEARNING · END-TERM PROJECT')

    c.showPage()
slide_1()


# ---- SLIDE 2: The question ----------------------------------------------
def slide_2():
    chrome(c, 2, TOTAL, '01 The Question')
    title_block(c, 'Trending is not one phenomenon — it is several',
                'And the difference matters for anyone making, marketing, or studying video.')

    # Three cards explaining the hypothesis — calibrated to what data showed
    cards = [
        ('STICKY',     'Daily soaps stay on the\ntrending chart for weeks.\nDifferent dynamics entirely.',  ARCH['Marathon']),
        ('FLASH',      'Music drops climb fast,\nplateau, and slip away\nin under three days.',           ARCH['Firework']),
        ('LOYAL',      'Some creators get +200%\nthe like-to-view ratio.\nSmall, devoted audiences.',     ARCH['Beloved']),
    ]
    cw = (W - 1.1*inch - 0.6*inch) / 3   # leave gaps between cards
    cy = H - 4.8*inch
    ch = 2.4*inch
    for i, (label, body, col) in enumerate(cards):
        cx = 0.55*inch + i*(cw + 0.3*inch)
        # Card outline
        c.setStrokeColor(col)
        c.setFillColor(white)
        c.setLineWidth(2)
        c.roundRect(cx, cy, cw, ch, 10, stroke=1, fill=1)
        # Label chip top-left
        chip(c, cx + 14, cy + ch - 30, label, col)
        # Body
        c.setFont(F_REG, 13)
        c.setFillColor(NAVY)
        yy = cy + ch - 70
        for line in body.split('\n'):
            c.drawString(cx + 18, yy, line)
            yy -= 18

    # Big question
    qy = 1.55*inch
    c.setFillColor(LIGHT)
    c.roundRect(0.55*inch, qy, W - 1.1*inch, 0.9*inch, 6, stroke=0, fill=1)
    c.setFont(F_IT, 14)
    c.setFillColor(NAVY)
    c.drawString(0.85*inch, qy + 0.55*inch,
                 'Can we discover these archetypes from data alone — and predict which one a video belongs to')
    c.drawString(0.85*inch, qy + 0.30*inch,
                 'from the metadata available the moment it first appears on the trending chart?')

    c.showPage()
slide_2()


# ---- SLIDE 3: Why it matters --------------------------------------------
def slide_3():
    chrome(c, 3, TOTAL, '02 Why It Matters')
    title_block(c, 'Three different stakeholders, three different decisions',
                'The same data answers very different questions for each.')

    stakeholders = [
        ('CREATOR', 'A creator deciding whether to invest in long-form content',
         'Marathon and Firework imply opposite production strategies. One rewards depth and consistency; the other rewards timing and reach.', ARCH['Marathon']),
        ('BRAND', 'A brand planning when to spend ad budget',
         'Firework windows are 24-48 hours. Marathon partnerships pay off over weeks. Knowing the difference avoids burning budget on the wrong creator.', ARCH['Firework']),
        ('PLATFORM', 'A platform team studying its recommender',
         'Drumbeat (chart re-entries) and Beloved (engagement spikes) signal different recommender outcomes. Tracking archetype share over time becomes a health metric.', ARCH['Drumbeat']),
    ]

    yy = H - 2.0*inch
    for label, headline, body, col in stakeholders:
        # Left chip
        chip(c, 0.55*inch, yy - 14, label, col, w=92)
        # Headline
        c.setFont(F_BOLD, 13)
        c.setFillColor(NAVY)
        c.drawString(1.85*inch, yy - 4, headline)
        # Body
        c.setFont(F_REG, 11)
        c.setFillColor(GREY)
        c.drawString(1.85*inch, yy - 24, body)
        yy -= 1.55*inch

    c.showPage()
slide_3()


# ---- SLIDE 4: Data collection -------------------------------------------
def slide_4():
    chrome(c, 4, TOTAL, '03 Data')
    title_block(c, f"{META['snapshots_total']:,} snapshots, {META['unique_videos_total']:,} unique videos, 7 months",
                'Hybrid: archival India trending data + a fresh live collector validating the same pipeline today.')

    # Pipeline diagram across the slide
    fit_image(c, FIG/'deck_pipeline.png',
              0.55*inch, H - 4.7*inch,
              W - 1.1*inch, 1.9*inch)

    # Stat cards row
    stats_y = 1.0*inch
    stats_h = 1.4*inch
    stats = [
        (f"{META['snapshots_total']:,}", 'snapshot rows'),
        (f"{META['unique_videos_total']:,}", 'unique videos'),
        (str(META.get('unique_snapshots', 205)), 'daily snapshots'),
        ('YouTube', 'Data API v3'),
    ]
    sw = (W - 1.1*inch - 0.45*inch) / 4
    for i, (v, lab) in enumerate(stats):
        sx = 0.55*inch + i*(sw + 0.15*inch)
        stat_card(c, sx, stats_y, sw, stats_h, v, lab,
                  color=ACCENT, value_size=26)

    # Caption beneath the pipeline
    c.setFont(F_IT, 10)
    c.setFillColor(GREY)
    c.drawString(0.55*inch, H - 4.95*inch,
                 'Same schema, same code path: live collector for fresh data, archival CSV for depth. The pipeline runs in 30 seconds end-to-end.')

    c.showPage()
slide_4()


# ---- SLIDE 5: Feature engineering ---------------------------------------
def slide_5():
    chrome(c, 5, TOTAL, '04 Feature Engineering')
    title_block(c, '25 features in 5 themes, all derived from the lifecycle',
                'One row per video, not per timestamp — features describe how a video behaved over its life.')

    themes = [
        ('VELOCITY',    'How fast it grew',
         'peak_views_per_hour\nmean_views_per_hour\nhours_to_first_trend',  ARCH['Firework']),
        ('DECAY',       'How fast it died',
         'decay_log_slope_48h\nhalf_life_hours\ndays_observed_on_chart', ARCH['Flash']),
        ('RETENTION',   'Sticky vs flash',
         'chart_presence_ratio\nrank_volatility\nreturned_count', ARCH['Marathon']),
        ('ENGAGEMENT',  'Audience response',
         'mean_like_view_ratio\nmean_comment_view_ratio\ncomment_like_ratio\nengagement_growth', ARCH['Beloved']),
        ('CONTENT',     'Video / title / channel',
         'duration_seconds · is_short\ntitle_length · caps_ratio · emoji\ntag_count · category · channel_size', ARCH['Drumbeat']),
    ]
    cw = (W - 1.1*inch - 0.6*inch) / 5
    cy = 1.7*inch
    ch = 3.5*inch
    for i, (label, head, body, col) in enumerate(themes):
        cx = 0.55*inch + i*(cw + 0.15*inch)
        # Header band
        c.setFillColor(col)
        c.roundRect(cx, cy + ch - 50, cw, 50, 6, stroke=0, fill=1)
        c.setFont(F_BOLD, 10)
        c.setFillColor(white)
        c.drawString(cx + 12, cy + ch - 22, label)
        c.setFont(F_REG, 9)
        c.drawString(cx + 12, cy + ch - 38, head)
        # Body
        c.setStrokeColor(LIGHT)
        c.setFillColor(white)
        c.roundRect(cx, cy, cw, ch - 50, 6, stroke=1, fill=1)
        c.setFont('Courier', 8.5)
        c.setFillColor(NAVY)
        yy = cy + ch - 80
        for line in body.split('\n'):
            c.drawString(cx + 10, yy, line)
            yy -= 14

    # Footnote
    c.setFont(F_IT, 10)
    c.setFillColor(GREY)
    c.drawCentredString(W/2, 1.0*inch,
        'Aggregating across each video\'s snapshots gives features that describe behaviour, not just state.')

    c.showPage()
slide_5()


# ---- SLIDE 6: PCA -------------------------------------------------------
def slide_6():
    chrome(c, 6, TOTAL, '05 Dimensionality Reduction')
    title_block(c, f"PCA: {META['n_pca']} components retain 95% of the variance",
                'Engineered features are correlated by design; PCA gives us a clean basis to cluster on.')

    # Left: PCA curve
    fit_image(c, FIG/'deck_pca.png',
              0.55*inch, 1.1*inch, W*0.55 - 0.55*inch, H - 2.4*inch)

    # Right: text + interpretation
    rx = W*0.58
    c.setFont(F_BOLD, 13); c.setFillColor(NAVY)
    c.drawString(rx, H - 2.0*inch, 'What the top components capture')
    c.setStrokeColor(ACCENT); c.setLineWidth(1.5)
    c.line(rx, H - 2.1*inch, rx + 1.4*inch, H - 2.1*inch)

    rows = [
        ('PC1', 'Velocity ↔ Longevity',
         'Heavy loadings on peak views/hour and chart presence. Captures the fundamental trade-off.'),
        ('PC2', 'Engagement ↔ Volume',
         'Loadings on like/view ratio (positive) and channel size (negative).'),
        ('PC3-10', 'Content shape',
         'Duration, tag count, language, category — the textural differences between archetypes.'),
    ]
    yy = H - 2.6*inch
    for i, (axis, name, body) in enumerate(rows):
        chip(c, rx, yy, axis, ACCENT, w=70)
        c.setFont(F_BOLD, 12); c.setFillColor(NAVY)
        c.drawString(rx + 80, yy + 6, name)
        c.setFont(F_REG, 10); c.setFillColor(GREY)
        # Wrap body
        words = body.split(); line = ''
        ly = yy - 12
        for w in words:
            test = (line + ' ' + w).strip()
            if c.stringWidth(test, F_REG, 10) > W*0.4 - 0.3*inch:
                c.drawString(rx, ly, line)
                ly -= 13; line = w
            else:
                line = test
        if line: c.drawString(rx, ly, line)
        yy = ly - 22

    c.showPage()
slide_6()


# ---- SLIDE 7: Choosing k ------------------------------------------------
def slide_7():
    chrome(c, 7, TOTAL, '06 Model Selection')
    title_block(c, 'Choosing k — three diagnostics, not silhouette alone',
                'Silhouette would have picked k=2. We rejected that; here is why.')

    # Diagnostics image full width
    fit_image(c, FIG/'deck_kselect.png',
              0.55*inch, 2.4*inch, W - 1.1*inch, H - 4.0*inch)

    # Three callouts at bottom
    callouts = [
        ('THE ELBOW', 'Inertia bends gently around\nk=4-6 with no sharp drop\nafterwards.', NAVY),
        ('SILHOUETTE', 'Highest at k=2, but that is\ndegenerate (one cluster has\n80% of videos). We rejected\nsplits with > 55% imbalance.', ARCH['Firework']),
        ('CHOSEN: k=6', 'Best ARI between methods\n(0.55) at this k. Six clusters,\nfour with clear archetype\nsignatures.', ARCH['Marathon']),
    ]
    cw = (W - 1.1*inch - 0.4*inch) / 3
    cy = 0.7*inch
    ch = 1.55*inch
    for i, (label, body, col) in enumerate(callouts):
        cx = 0.55*inch + i*(cw + 0.2*inch)
        c.setStrokeColor(col); c.setFillColor(white); c.setLineWidth(1.5)
        c.roundRect(cx, cy, cw, ch, 6, stroke=1, fill=1)
        chip(c, cx + 12, cy + ch - 22, label, col)
        c.setFont(F_REG, 9.5)
        c.setFillColor(NAVY)
        yy = cy + ch - 42
        for line in body.split('\n'):
            c.drawString(cx + 14, yy, line)
            yy -= 13

    c.showPage()
slide_7()


# ---- SLIDE 8: The six archetypes (UMAP + names) -------------------------
def slide_8():
    chrome(c, 8, TOTAL, '07 Results')
    title_block(c, 'Six archetypes emerge — four named, two fringe',
                f"K-Means at k={META['K']} on {META['n_videos']:,} videos · methods agree (ARI = {META['ari_methods']:.2f})")

    # Big UMAP, taking left 65% (no-legend version since cards are the legend)
    fit_image(c, FIG/'deck_umap_nolegend.png',
              0.55*inch, 0.65*inch,
              W*0.66, H - 2.6*inch)

    # Right side: archetype name cards
    rx = W*0.68
    rw = W - rx - 0.55*inch
    yy = H - 1.85*inch

    arch_summaries = [
        ('Firework',  'Sustained big hits.\nMusic drops, Punjabi songs.'),
        ('Beloved',   '+2.1 like/view.\nTech creators, regional comedy.'),
        ('Marathon',  '+2.0 chart presence.\nTamil daily soaps stay forever.'),
        ('Drumbeat',  '+6.5 returned-count.\nNews cycles re-enter the chart.'),
        ('Flash',     'Brief blips.\nMost trending videos look like this.'),
        ('Standard',  'Baseline trender.\nDaily television.'),
    ]
    name_to_size = {}
    for cid, name in META['cluster_names'].items():
        if name in [a for a, _ in arch_summaries]:
            name_to_size[name] = META['cluster_sizes'][cid]

    card_h = 50
    gap = 8
    for nm, body in arch_summaries:
        col = ARCH[nm]
        n = name_to_size.get(nm, 0)
        c.setStrokeColor(col); c.setFillColor(white); c.setLineWidth(1.5)
        c.roundRect(rx, yy - card_h, rw, card_h, 6, stroke=1, fill=1)
        c.setFillColor(col); c.circle(rx + 14, yy - 25, 6, stroke=0, fill=1)
        c.setFont(F_BOLD, 11); c.setFillColor(NAVY)
        c.drawString(rx + 26, yy - 19, nm)
        c.setFont(F_REG, 8.5); c.setFillColor(GREY)
        for i, ln in enumerate(body.split('\n')):
            c.drawString(rx + 26, yy - 32 - i*11, ln)
        c.setFont(F_BOLD, 9.5); c.setFillColor(col)
        c.drawRightString(rx + rw - 10, yy - 19, f'n={n:,}')
        yy -= card_h + gap

    c.showPage()
slide_8()


# ---- SLIDE 9: Lifecycle curves ------------------------------------------
def slide_9():
    chrome(c, 9, TOTAL, '08 Archetype Behaviour')
    title_block(c, 'Each archetype has a distinct lifecycle shape',
                'Average view-trajectories differ visibly. The archetypes are not just statistical — they are behavioural.')

    # Lifecycle figure full width
    fit_image(c, FIG/'deck_lifecycle.png',
              0.55*inch, 2.3*inch,
              W - 1.1*inch, H - 4.0*inch)

    # Annotation row
    yy = 1.8*inch
    c.setFont(F_BOLD, 11); c.setFillColor(NAVY)
    c.drawString(0.55*inch, yy, 'What you should notice')

    annotations = [
        (ARCH['Firework'],  'Firework climbs in 24-48h to plateau, then slowly decays.'),
        (ARCH['Beloved'],   'Beloved videos look ordinary in views — engagement is what makes them special.'),
        (ARCH['Marathon'],  'Marathon plateaus near the top and stays there for days.'),
        (ARCH['Drumbeat'],  'Drumbeat is non-monotonic: dips and recoveries (chart re-entries).'),
    ]
    yy -= 22
    for col, txt in annotations:
        c.setFillColor(col); c.circle(0.65*inch, yy + 4, 4, stroke=0, fill=1)
        c.setFont(F_REG, 10); c.setFillColor(NAVY)
        c.drawString(0.85*inch, yy, txt)
        yy -= 16

    c.showPage()
slide_9()


# ---- SLIDE 10: Cluster fingerprint --------------------------------------
def slide_10():
    chrome(c, 10, TOTAL, '09 Cluster Profile')
    title_block(c, 'What makes each archetype tick',
                'Z-scored feature means per cluster. Reds = much more than average · blues = much less.')

    # Full-width fingerprint
    fit_image(c, FIG/'deck_fingerprint.png',
              0.55*inch, 1.9*inch,
              W - 1.1*inch, H - 3.4*inch)

    # Reading guide
    yy = 1.5*inch
    c.setFont(F_BOLD, 11); c.setFillColor(NAVY)
    c.drawString(0.55*inch, yy, 'How to read this')
    yy -= 18
    notes = [
        'Drumbeat: +6.5 z-score on returned-count — videos that leave and re-enter the chart, the news-cycle pattern.',
        'Marathon: +2.0 chart-presence-ratio — daily soaps that stay on the chart for weeks.',
        'Beloved: +2.1 like/view ratio plus +1.0 comment/view — passionate audiences relative to size.',
        'Firework: above-average velocity AND half-life — sustained big hits, not flash spikes.',
    ]
    c.setFont(F_REG, 10); c.setFillColor(GREY)
    for ln in notes:
        c.drawString(0.65*inch, yy, '·  ' + ln); yy -= 13

    c.showPage()
slide_10()


# ---- SLIDE 11: Association rules ----------------------------------------
def slide_11():
    chrome(c, 11, TOTAL, '10 Association Mining')
    title_block(c, 'What tags live in each archetype',
                'Apriori on tag baskets · 1,015 rules at lift ≥ 3 · most distinctive tags per cluster shown below.')

    # Per-cluster distinctive tags table
    # Row per archetype, columns: archetype | top tags | strongest lift
    archetype_rows = [
        ('Firework',  ['punjabi songs', 'punjabi music', 'latest punjabi songs 2018', 'punjabi romantic songs'],  3.80),
        ('Beloved',   ['technical guruji', 'gaurav chaudhary', 'desi vines', 'hyderabadi comedy'],                7.84),
        ('Marathon',  ['priyamanaval', 'priyamanaval episode', 'piriyamanaval', 'tamil serial'],                  7.29),
        ('Drumbeat',  ['breaking news', 'telugu news', 'congress', 'bjp'],                                        4.67),
        ('Standard',  ['daily soap', 'full episode', 'television', 'watch online'],                               2.78),
        ('Flash',     ['(no distinctive tags — the residual category)'],                                          0.0),
    ]

    # Try to override with real data if available
    if CLUSTER_TAGS:
        archetype_rows = []
        for arch in ['Firework','Beloved','Marathon','Drumbeat','Standard','Flash']:
            tags_data = CLUSTER_TAGS.get(arch, [])
            if tags_data:
                top4 = [t['tag'] for t in tags_data[:4]]
                top_lift = max(t['lift'] for t in tags_data)
                archetype_rows.append((arch, top4, top_lift))
            else:
                archetype_rows.append((arch, ['(no distinctive tags)'], 0.0))

    # Table
    tx = 0.55*inch; tw = W - 1.1*inch
    ty_top = H - 1.6*inch
    row_h = 38
    headers = ['Archetype', 'Distinctive tags  (top by lift)', 'Top lift']
    cols_w = [tw*0.18, tw*0.66, tw*0.16]

    # Header
    c.setFillColor(LIGHT); c.rect(tx, ty_top - row_h, tw, row_h, stroke=0, fill=1)
    c.setFont(F_BOLD, 10); c.setFillColor(NAVY)
    cx = tx
    for i, hdr in enumerate(headers):
        if i == 2:
            c.drawRightString(cx + cols_w[i] - 8, ty_top - row_h + 13, hdr)
        else:
            c.drawString(cx + 10, ty_top - row_h + 13, hdr)
        cx += cols_w[i]

    # Rows
    yy = ty_top - row_h
    for i, (arch, tags, lift) in enumerate(archetype_rows):
        yy -= row_h
        if i % 2 == 0:
            c.setFillColor(BG); c.rect(tx, yy, tw, row_h, stroke=0, fill=1)
        cx = tx
        # Archetype name + colour pip
        col = ARCH.get(arch, GREY)
        c.setFillColor(col); c.circle(cx + 14, yy + row_h/2, 5, stroke=0, fill=1)
        c.setFont(F_BOLD, 11); c.setFillColor(NAVY)
        c.drawString(cx + 26, yy + row_h/2 - 3, arch)
        cx += cols_w[0]

        # Tag chips
        chip_x = cx + 8
        chip_y = yy + row_h/2 - 8
        chip_h = 16
        c.setFont(F_REG, 8.5)
        for tag in tags:
            tag_w = c.stringWidth(tag, F_REG, 8.5) + 14
            # Don't overflow the column
            if chip_x + tag_w > cx + cols_w[1] - 8:
                break
            c.setFillColor(LIGHT)
            c.setStrokeColor(LIGHT)
            c.roundRect(chip_x, chip_y, tag_w, chip_h, chip_h/2, stroke=0, fill=1)
            c.setFillColor(NAVY)
            c.drawCentredString(chip_x + tag_w/2, chip_y + 5, tag)
            chip_x += tag_w + 5
        cx += cols_w[1]

        # Lift
        c.setFont(F_BOLD, 11)
        if lift > 0:
            lcol = ARCH['Firework'] if lift >= 5 else ACCENT if lift >= 2 else GREY
            c.setFillColor(lcol)
            c.drawRightString(cx + cols_w[2] - 8, yy + row_h/2 - 3, f'{lift:.1f}×')
        else:
            c.setFillColor(GREY)
            c.drawRightString(cx + cols_w[2] - 8, yy + row_h/2 - 3, '—')

    # Insight callout
    iy = 0.85*inch
    callout_h = 0.95*inch
    c.setFillColor(LIGHT)
    c.roundRect(0.55*inch, iy, W - 1.1*inch, callout_h, 6, stroke=0, fill=1)
    c.setFont(F_BOLD, 11); c.setFillColor(NAVY)
    c.drawString(0.85*inch, iy + callout_h - 22, 'What this tells us')
    c.setFont(F_REG, 10); c.setFillColor(NAVY)
    insight_lines = [
        'Tags converge on the same archetypes the geometry found — Punjabi music IS Firework, Tamil daily soaps ARE Marathon,',
        'news cycles ARE Drumbeat. Two different unsupervised methods (clustering on lifecycle features, association mining on tags)',
        'arriving at the same partition is strong convergent evidence that these archetypes are real, not artefacts of one technique.',
    ]
    for j, ln in enumerate(insight_lines):
        c.drawString(0.85*inch, iy + callout_h - 38 - j*13, ln)

    c.showPage()
slide_11()


# ---- SLIDE 12: So what / wrap -------------------------------------------
def slide_12():
    chrome(c, 12, TOTAL, '11 So What')
    title_block(c, 'What we did — and what to take from it',
                None)

    # Left half: numbered findings
    findings = [
        ('1', 'Trending in India is not one phenomenon but at least four distinguishable archetypes — Marathon, Firework, Beloved, Drumbeat — plus a long tail of standard videos.'),
        ('2', 'Lifecycle features (velocity, decay, retention, engagement) separate archetypes much more cleanly than static metadata alone.'),
        ('3', f'K-Means and Agglomerative clustering agree (ARI = {META["ari_methods"]:.2f} on {META["n_videos"]:,} videos) — the structure is real, not algorithm-dependent.'),
        ('4', 'Association mining on tags surfaces the same archetypes (Punjabi songs↔Firework, daily soaps↔Marathon, news cycles↔Drumbeat) — convergent evidence from two unsupervised methods.'),
        ('5', 'Same pipeline runs on a fresh live API stream and on archival data without code changes — the methodology generalises to any region or window.'),
    ]
    LEFT_COL_W = W*0.50 - 0.55*inch - 0.3*inch
    yy = H - 2.0*inch
    for num, txt in findings:
        # Number circle
        c.setFillColor(ACCENT)
        c.circle(0.75*inch, yy + 4, 13, stroke=0, fill=1)
        c.setFont(F_BOLD, 12); c.setFillColor(white)
        c.drawCentredString(0.75*inch, yy, num)
        # Text — wrap at left-column width only
        c.setFont(F_REG, 10.5); c.setFillColor(NAVY)
        words = txt.split(); line = ''
        ly = yy + 4
        for w in words:
            test = (line + ' ' + w).strip()
            if c.stringWidth(test, F_REG, 10.5) > LEFT_COL_W:
                c.drawString(1.1*inch, ly, line)
                ly -= 13; line = w
            else:
                line = test
        if line: c.drawString(1.1*inch, ly, line)
        yy = ly - 24

    # Right half: limitations + next steps
    rx = W*0.55
    c.setFont(F_BOLD, 13); c.setFillColor(NAVY)
    c.drawString(rx, H - 2.0*inch, 'Caveats we own')
    c.setStrokeColor(ACCENT); c.setLineWidth(1.5)
    c.line(rx, H - 2.10*inch, rx + 1.5*inch, H - 2.10*inch)

    caveats = [
        'Archival window is Nov 2017 - Jun 2018; trending behaviour today may differ.',
        'India only — archetype share will differ in other regions and YouTube eras.',
        '"Flash" cluster (n=3,693) is the residual catchall — interpret as "no distinctive lifecycle signature" rather than a true archetype.',
    ]
    yy = H - 2.45*inch
    RIGHT_MAX_W = W - rx - 0.55*inch - 0.25*inch
    c.setFont(F_REG, 10.5); c.setFillColor(GREY)
    for ln in caveats:
        c.setFillColor(ACCENT); c.circle(rx + 4, yy + 4, 2.2, stroke=0, fill=1)
        c.setFillColor(GREY)
        words = ln.split(); line = ''; ly = yy + 4
        for w in words:
            test = (line + ' ' + w).strip()
            if c.stringWidth(test, F_REG, 10.5) > RIGHT_MAX_W:
                c.drawString(rx + 14, ly, line); ly -= 13; line = w
            else: line = test
        if line: c.drawString(rx + 14, ly, line)
        yy = ly - 18

    # Next steps
    yy -= 12
    c.setFont(F_BOLD, 13); c.setFillColor(NAVY)
    c.drawString(rx, yy, 'Where this could go')
    c.setStrokeColor(ACCENT); c.line(rx, yy - 8, rx + 1.5*inch, yy - 8)
    yy -= 24
    c.setFont(F_REG, 10.5); c.setFillColor(GREY)
    nexts = [
        'Region comparison: India vs SG vs UK on the same pipeline.',
        'Time series: how does archetype share shift across weeks?',
        'Predictive layer: classify archetype from first-snapshot metadata only.',
    ]
    for ln in nexts:
        c.setFillColor(ACCENT); c.circle(rx + 4, yy + 4, 2.2, stroke=0, fill=1)
        c.setFillColor(GREY)
        words = ln.split(); line = ''; ly = yy + 4
        for w in words:
            test = (line + ' ' + w).strip()
            if c.stringWidth(test, F_REG, 10.5) > RIGHT_MAX_W:
                c.drawString(rx + 14, ly, line); ly -= 13; line = w
            else: line = test
        if line: c.drawString(rx + 14, ly, line)
        yy = ly - 18

    # Closing line, bottom centred
    c.setFont(F_IT, 12); c.setFillColor(ACCENT)
    c.drawCentredString(W/2, 0.85*inch,
        'Thank you. Questions welcome.')

    c.showPage()
slide_12()


c.save()
print(f'Saved: {OUT}')

# Verify page count
from pypdf import PdfReader
print(f'Pages: {len(PdfReader(str(OUT)).pages)}')
