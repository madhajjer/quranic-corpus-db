"""Build quran_treebank.db from the Extended Quranic Treebank (EQTB) data in eqtb/.

Parses eqtb/Quranic.csv (UTF-16 LE, tab-separated, 51 columns, ~132k tokens covering
the whole Quran) plus the RelLabels.csv / pos.csv lexicons into an SQLite database of
per-sentence dependency graphs in the style of corpus.quran.com.

Data model (verified against verse 1:1):
  - token_id is SENTENCE-LOCAL (0-based); a sentence may span multiple verses.
  - ref_token_id is the sentence-local token_id of the dependency head.
  - rel_label 'root' points at itself (sentence root); 'NonRel' means no arc
    (e.g. a DET segment attached morphologically, not syntactically).
  - Rows with location '_' and form '(*)' are elided (taqdir) words resolved by
    the treebank; they carry pos + rel but no Quran location.
  - is_constituent=1 rows open a phrase node: constituents_loc '[a-b]' gives the
    sentence-local token span, constituent_label the phrase tag (PP, NS, ...).

Requires eqtb/Quranic.csv; if missing, extract it from eqtb/Quranic.rar
(`unrar x Quranic.rar`). Run time: ~15s. Idempotent: drops and recreates all tables.
"""

import io
import os
import re
import sqlite3

WORKSPACE_DIR = os.path.dirname(os.path.abspath(__file__))
EQTB_DIR = os.path.join(WORKSPACE_DIR, "eqtb")
CORPUS_CSV = os.path.join(EQTB_DIR, "Quranic.csv")
REL_LABELS_CSV = os.path.join(EQTB_DIR, "RelLabels.csv")
POS_CSV = os.path.join(EQTB_DIR, "pos.csv")
DB_FILE_PATH = os.path.join(WORKSPACE_DIR, "quran_treebank.db")

NULLS = {"_", "-", ""}


def nz(value):
    """Return None for the EQTB null markers, else the stripped value."""
    value = value.strip()
    return None if value in NULLS else value


def read_utf16_tsv(path):
    """Yield rows of a UTF-16 tab-separated file as dicts keyed by header."""
    with io.open(path, encoding="utf-16", newline="") as f:
        header = f.readline().rstrip("\r\n").split("\t")
        header = [h.strip() for h in header]
        for line in f:
            line = line.rstrip("\r\n")
            if not line:
                continue
            yield dict(zip(header, line.split("\t")))


def create_schema(conn):
    conn.executescript(
        """
        DROP TABLE IF EXISTS graph_tokens;
        DROP TABLE IF EXISTS graph_edges;
        DROP TABLE IF EXISTS graph_phrases;
        DROP TABLE IF EXISTS sentences;
        DROP TABLE IF EXISTS rel_labels;
        DROP TABLE IF EXISTS pos_tags;

        CREATE TABLE sentences (
            sentence_id INTEGER PRIMARY KEY,
            sura_start INTEGER, verse_start INTEGER,
            sura_end INTEGER, verse_end INTEGER,
            token_count INTEGER
        );

        CREATE TABLE graph_tokens (
            tid INTEGER PRIMARY KEY,          -- global row id from the CSV
            sentence_id INTEGER NOT NULL,
            token_id INTEGER NOT NULL,        -- sentence-local, 0-based
            is_elided INTEGER NOT NULL,       -- 1 = taqdir word, no Quran location
            sura_id INTEGER, verse_num INTEGER, word_num INTEGER, token_num INTEGER,
            text_uthmani TEXT,                -- Arabic; '(*)' placeholder if elided
            text_imlaai TEXT,
            buckwalter TEXT,
            phonetic TEXT,
            translation TEXT,
            pos TEXT, pos_ar TEXT,
            segment TEXT,                     -- PREFIX / STEM / SUFFIX
            lemma TEXT, lemma_ar TEXT,
            root TEXT, root_ar TEXT,
            features TEXT,
            rel_label TEXT, rel_label_ar TEXT,
            ref_token_id INTEGER              -- head token_id (sentence-local)
        );
        CREATE INDEX idx_gtok_sentence ON graph_tokens(sentence_id, token_id);
        CREATE INDEX idx_gtok_location
            ON graph_tokens(sura_id, verse_num, word_num, token_num);

        CREATE TABLE graph_edges (
            sentence_id INTEGER NOT NULL,
            dependent_token_id INTEGER NOT NULL,  -- sentence-local
            head_token_id INTEGER NOT NULL,       -- sentence-local
            rel_en TEXT, rel_ar TEXT
        );
        CREATE INDEX idx_gedge_sentence ON graph_edges(sentence_id);

        CREATE TABLE graph_phrases (
            sentence_id INTEGER NOT NULL,
            start_token_id INTEGER NOT NULL,      -- sentence-local span, inclusive
            end_token_id INTEGER NOT NULL,
            label TEXT,
            text TEXT
        );
        CREATE INDEX idx_gphrase_sentence ON graph_phrases(sentence_id);

        CREATE TABLE rel_labels (
            rel_id INTEGER PRIMARY KEY,
            rel_en TEXT, rel_ar TEXT, rel_nho TEXT,
            color1 TEXT, color TEXT
        );

        CREATE TABLE pos_tags (
            pid INTEGER PRIMARY KEY,
            pos TEXT, pos_ar TEXT, pos_en TEXT,
            color1 TEXT, color TEXT
        );
        """
    )


LOCATION_RE = re.compile(r"\((\d+):(\d+):(\d+):(\d+)\)")


def main():
    if not os.path.exists(CORPUS_CSV):
        raise SystemExit(
            f"Missing {CORPUS_CSV}. Extract it from eqtb/Quranic.rar first "
            "(e.g. `unrar x Quranic.rar`)."
        )

    conn = sqlite3.connect(DB_FILE_PATH)
    create_schema(conn)

    for row in read_utf16_tsv(REL_LABELS_CSV):
        conn.execute(
            "INSERT INTO rel_labels VALUES (?,?,?,?,?,?)",
            (int(row["rel_id"]), nz(row["rel_en"]), nz(row["rel_ar"]),
             nz(row["rel_nho"]), nz(row["rel_color1"]), nz(row["rel_color"])),
        )
    for row in read_utf16_tsv(POS_CSV):
        conn.execute(
            "INSERT INTO pos_tags VALUES (?,?,?,?,?,?)",
            (int(row["pid"]), nz(row["pos"]), nz(row["pos_ar"]),
             nz(row["pos_en"]), nz(row["color1"]), nz(row["color"])),
        )

    token_count = 0
    sentence_bounds = {}  # sentence_id -> [sura_start, verse_start, sura_end, verse_end, n]
    for row in read_utf16_tsv(CORPUS_CSV):
        sentence_id = int(row["sentence_id"])
        token_id = int(row["token_id"])
        loc_match = LOCATION_RE.match(row["location"].strip())
        if loc_match:
            sura, verse, word, tok = (int(g) for g in loc_match.groups())
            is_elided = 0
        else:
            sura = verse = word = tok = None
            is_elided = 1

        rel_en = nz(row["rel_label"])
        ref = int(row["ref_token_id"])
        conn.execute(
            "INSERT INTO graph_tokens VALUES "
            "(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (int(row["tid"]), sentence_id, token_id, is_elided,
             sura, verse, word, tok,
             nz(row["uthmani_token"]), nz(row["imlaai_token"]),
             nz(row["uthmani_unicode"]),  # Buckwalter transliteration
             nz(row["phonetic"]), nz(row["trans"]),
             nz(row["pos"]), nz(row["pos_ar"]), nz(row["segment"]),
             nz(row["lemma"]), nz(row["lemma_ar"]),
             nz(row["root"]), nz(row["root_ar"]), nz(row["features"]),
             rel_en, nz(row["rel_label_ar"]), ref),
        )
        token_count += 1

        if rel_en and rel_en not in ("NonRel", "root"):
            conn.execute(
                "INSERT INTO graph_edges VALUES (?,?,?,?,?)",
                (sentence_id, token_id, ref, rel_en, nz(row["rel_label_ar"])),
            )

        if row["is_constituent"].strip() == "1":
            span = re.match(r"\[(\d+)-(\d+)\]", row["constituents_loc"].strip())
            if span:
                conn.execute(
                    "INSERT INTO graph_phrases VALUES (?,?,?,?,?)",
                    (sentence_id, int(span.group(1)), int(span.group(2)),
                     nz(row["constituent_label"]), nz(row["constituents"])),
                )

        bounds = sentence_bounds.setdefault(sentence_id, [sura, verse, None, None, 0])
        if sura is not None:
            if bounds[0] is None:
                bounds[0], bounds[1] = sura, verse
            bounds[2], bounds[3] = sura, verse
        bounds[4] += 1

    for sentence_id, b in sentence_bounds.items():
        conn.execute("INSERT INTO sentences VALUES (?,?,?,?,?,?)",
                     (sentence_id, b[0], b[1], b[2], b[3], b[4]))

    conn.commit()

    n_sent = conn.execute("SELECT COUNT(*) FROM sentences").fetchone()[0]
    n_edge = conn.execute("SELECT COUNT(*) FROM graph_edges").fetchone()[0]
    n_phrase = conn.execute("SELECT COUNT(*) FROM graph_phrases").fetchone()[0]
    n_elided = conn.execute(
        "SELECT COUNT(*) FROM graph_tokens WHERE is_elided = 1").fetchone()[0]
    print(f"Built {DB_FILE_PATH}")
    print(f"  tokens:    {token_count} ({n_elided} elided)")
    print(f"  sentences: {n_sent}")
    print(f"  edges:     {n_edge}")
    print(f"  phrases:   {n_phrase}")
    conn.close()


if __name__ == "__main__":
    main()
