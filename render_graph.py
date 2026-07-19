"""Render corpus.quran.com-style dependency graphs from quran_treebank.db as SVG.

Usage:
    python3 render_graph.py 1:1              # render sentence(s) covering verse 1:1
    python3 render_graph.py 1:1 -o out.svg   # explicit output path (single sentence only)

Layout, mirroring corpus.quran.com/documentation/dependencygraph.jsp:
  - Arabic tokens on a right-to-left baseline (token 0 rightmost), POS-colored,
    with POS tag and English gloss beneath; elided (taqdir) words in grey.
  - Dependency arcs curve below the text with Arabic relation labels (فاعل,
    مفعول به, ...); arc heights stack so nested arcs never cross.
  - Phrase spans (PP, NS, ...) drawn as labeled brackets under the baseline.

Colors come from the pos_tags / rel_labels tables (EQTB lexicons). Pure stdlib.
Requires quran_treebank.db (run build_treebank.py first).
"""

import argparse
import html
import os
import sqlite3

WORKSPACE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE_PATH = os.path.join(WORKSPACE_DIR, "quran_treebank.db")

ARABIC_FONT = "Amiri, 'Scheherazade New', 'Traditional Arabic', serif"
LATIN_FONT = "Georgia, serif"

TOKEN_FONT_SIZE = 30
POS_FONT_SIZE = 12
GLOSS_FONT_SIZE = 11
LABEL_FONT_SIZE = 13
TOKEN_GAP = 26
MARGIN_X = 30
BASELINE_Y = 60
ARC_TOP_GAP = 58      # distance from baseline to the lowest arc level
ARC_LEVEL_STEP = 34
PHRASE_GAP = 30       # below deepest arc
ELIDED_COLOR = "#999999"
DEFAULT_POS_COLOR = "#333333"
DEFAULT_REL_COLOR = "#7a3b2e"


def text_width(text, font_size):
    """Rough width estimate; Arabic glyphs average ~0.55em, Latin ~0.5em."""
    return max(len(text), 1) * font_size * 0.55


def load_sentence(conn, sentence_id):
    tokens = conn.execute(
        """SELECT token_id, is_elided, text_uthmani, pos, translation
           FROM graph_tokens WHERE sentence_id = ? ORDER BY token_id""",
        (sentence_id,),
    ).fetchall()
    edges = conn.execute(
        """SELECT dependent_token_id, head_token_id, rel_ar, rel_en
           FROM graph_edges WHERE sentence_id = ?""",
        (sentence_id,),
    ).fetchall()
    phrases = conn.execute(
        """SELECT start_token_id, end_token_id, label
           FROM graph_phrases WHERE sentence_id = ?""",
        (sentence_id,),
    ).fetchall()
    return tokens, edges, phrases


def arc_levels(edges):
    """Assign each arc a stacking level so shorter arcs sit below longer ones."""
    spans = sorted(edges, key=lambda e: abs(e[0] - e[1]))
    levels = {}
    for dep, head, _, _ in spans:
        lo, hi = min(dep, head), max(dep, head)
        level = 1
        for (dep2, head2), lvl in levels.items():
            lo2, hi2 = min(dep2, head2), max(dep2, head2)
            if lo <= lo2 and hi2 <= hi and (lo2, hi2) != (lo, hi):
                level = max(level, lvl + 1)
        levels[(dep, head)] = level
    return levels


def render_sentence(conn, sentence_id):
    tokens, edges, phrases = load_sentence(conn, sentence_id)
    pos_colors = dict(conn.execute("SELECT pos, color FROM pos_tags"))
    rel_colors = dict(conn.execute("SELECT rel_en, color FROM rel_labels"))

    # x layout: token 0 rightmost (RTL). First pass computes widths.
    widths = [
        max(text_width(t[2] or "(*)", TOKEN_FONT_SIZE),
            text_width(t[4] or "", GLOSS_FONT_SIZE), 40)
        for t in tokens
    ]
    total_w = sum(widths) + TOKEN_GAP * (len(tokens) - 1) + 2 * MARGIN_X
    centers = {}
    x = total_w - MARGIN_X
    for t, w in zip(tokens, widths):
        centers[t[0]] = x - w / 2
        x -= w + TOKEN_GAP

    levels = arc_levels(edges)
    max_level = max(levels.values(), default=0)
    arc_base_y = BASELINE_Y + ARC_TOP_GAP
    phrase_y = arc_base_y + max_level * ARC_LEVEL_STEP + PHRASE_GAP
    total_h = phrase_y + (30 if phrases else 0) + 20

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{total_w:.0f}" '
        f'height="{total_h:.0f}" viewBox="0 0 {total_w:.0f} {total_h:.0f}">',
        f'<rect width="100%" height="100%" fill="white"/>',
    ]

    # Tokens: Arabic form, POS tag, gloss.
    for token_id, is_elided, text, pos, gloss in tokens:
        cx = centers[token_id]
        color = ELIDED_COLOR if is_elided else pos_colors.get(pos, DEFAULT_POS_COLOR)
        parts.append(
            f'<text x="{cx:.1f}" y="{BASELINE_Y}" text-anchor="middle" '
            f'font-family="{ARABIC_FONT}" font-size="{TOKEN_FONT_SIZE}" '
            f'fill="{color}" direction="rtl">{html.escape(text or "(*)")}</text>'
        )
        parts.append(
            f'<text x="{cx:.1f}" y="{BASELINE_Y + 18}" text-anchor="middle" '
            f'font-family="{LATIN_FONT}" font-size="{POS_FONT_SIZE}" '
            f'fill="{color}">{html.escape(pos or "")}</text>'
        )
        if gloss:
            parts.append(
                f'<text x="{cx:.1f}" y="{BASELINE_Y + 33}" text-anchor="middle" '
                f'font-family="{LATIN_FONT}" font-size="{GLOSS_FONT_SIZE}" '
                f'fill="#666666">{html.escape(gloss)}</text>'
            )

    # Arcs: quadratic curves below the text, arrowhead at the dependent end.
    for dep, head, rel_ar, rel_en in edges:
        x1, x2 = centers[dep], centers[head]
        level = levels[(dep, head)]
        y0 = BASELINE_Y + 40
        peak = arc_base_y + level * ARC_LEVEL_STEP
        mid_x = (x1 + x2) / 2
        color = rel_colors.get(rel_en, DEFAULT_REL_COLOR)
        parts.append(
            f'<path d="M {x1:.1f} {y0} Q {mid_x:.1f} {peak} {x2:.1f} {y0}" '
            f'fill="none" stroke="{color}" stroke-width="1.5"/>'
        )
        parts.append(
            f'<path d="M {x1 - 4:.1f} {y0 + 7} L {x1:.1f} {y0} L {x1 + 4:.1f} {y0 + 7} Z" '
            f'fill="{color}"/>'
        )
        label_y = (y0 + peak) / 2 + 4
        parts.append(
            f'<text x="{mid_x:.1f}" y="{label_y:.1f}" text-anchor="middle" '
            f'font-family="{ARABIC_FONT}" font-size="{LABEL_FONT_SIZE}" '
            f'fill="{color}" direction="rtl">{html.escape(rel_ar or rel_en or "")}</text>'
        )

    # Phrase brackets under everything.
    for start, end, label in phrases:
        x_right = centers[start] + widths[start] / 2 if start in centers else None
        x_left = centers[end] - widths[end] / 2 if end in centers else None
        if x_right is None or x_left is None:
            continue
        parts.append(
            f'<path d="M {x_left:.1f} {phrase_y - 6} L {x_left:.1f} {phrase_y} '
            f'L {x_right:.1f} {phrase_y} L {x_right:.1f} {phrase_y - 6}" '
            f'fill="none" stroke="#555555" stroke-width="1.2"/>'
        )
        parts.append(
            f'<text x="{(x_left + x_right) / 2:.1f}" y="{phrase_y + 16}" '
            f'text-anchor="middle" font-family="{LATIN_FONT}" '
            f'font-size="{POS_FONT_SIZE}" fill="#555555">{html.escape(label or "")}</text>'
        )

    parts.append("</svg>")
    return "\n".join(parts)


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("verse", help="sura:verse, e.g. 1:1")
    parser.add_argument("-o", "--output", help="output SVG path")
    args = parser.parse_args()

    sura, verse = (int(p) for p in args.verse.split(":"))
    conn = sqlite3.connect(DB_FILE_PATH)
    sentence_ids = [
        r[0] for r in conn.execute(
            """SELECT DISTINCT sentence_id FROM graph_tokens
               WHERE sura_id = ? AND verse_num = ? ORDER BY sentence_id""",
            (sura, verse),
        )
    ]
    if not sentence_ids:
        raise SystemExit(f"No treebank sentence found for {args.verse}")

    for sentence_id in sentence_ids:
        svg = render_sentence(conn, sentence_id)
        if args.output and len(sentence_ids) == 1:
            out = args.output
        else:
            out = os.path.join(WORKSPACE_DIR, f"graph_{sura}_{verse}_s{sentence_id}.svg")
        with open(out, "w", encoding="utf-8") as f:
            f.write(svg)
        print(f"Wrote {out}")
    conn.close()


if __name__ == "__main__":
    main()
