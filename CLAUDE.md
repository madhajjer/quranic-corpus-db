# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

This repo converts the **Quranic Arabic Corpus (morphology, v0.4)** — a tab-separated
Buckwalter-transliterated text file — into indexed SQLite databases for linguistic
search. There is no application server or UI; the deliverables are the `.py` build
scripts, the generated `.db` files, and the Colab notebooks that wrap them.

Pure standard-library Python 3 (`sqlite3`, `urllib.request`, `re`, `json`). **No
external dependencies, no package manager, no test suite, no lint config.** Do not add
a `requirements.txt` or third-party imports unless explicitly asked.

## Commands

```bash
python3 convert_corpus.py        # Parse the corpus .txt -> quran_morphology.db (~5-10s)
python3 query_examples.py        # Run sample queries against quran_morphology.db
python3 build_learning_harness.py # Build learning_harness.db from quran_morphology.db + Lane lexicon
```

Both scripts resolve all paths relative to their own file location (`WORKSPACE_DIR`),
so they can be run from any working directory. On Windows use `python` if `python3`
is unavailable.

### Build order dependency
`build_learning_harness.py` reads `quran_morphology.db`, so `convert_corpus.py` must
run first. Each script `DROP`s and recreates its tables on every run — builds are fully
idempotent and destructive to prior DB contents.

## Architecture

### Pipeline (`convert_corpus.py`)
The core transform is corpus `.txt` → relational SQLite. Key stages in `main()`:
1. **Fetch external data** (optional, network) — Surah metadata from `api.alquran.cloud`
   and Sahih International translations from `tanzil.info`. Both fail gracefully to
   offline fallbacks (`SURAH_FALLBACK_NAMES`, empty translations) so the build always
   completes without internet.
2. **Parse** each corpus line `(sura:verse:word:token)\tform\ttag\tfeatures`, grouping
   tokens by `(sura, verse, word)` in `word_map`.
3. **Reconstruct** words (concatenate token forms), verses (space-join words), and the
   `DET+ADJ`-style brief POS strings.
4. **Populate** `roots`, `suras`, `words`, `tokens`, `verses`, then the FTS5 index.

### Two transforms that everything depends on
- `buckwalter_to_arabic()` — maps Buckwalter transliteration (incl. extended Quranic
  symbols like Alif Wasla `{`, superscript Alif `` ` ``) to Arabic Unicode via
  `BUCKWALTER_TO_ARABIC`.
- `normalize_arabic()` — strips harakat and folds Alif/Ya/Ta-Marbuta variants, producing
  the `text_arabic_normalized` column. **This is what makes harakat-free search work**:
  users query modern Arabic spelling and match Uthmani orthography. The identical
  function is duplicated in `query_examples.py` — keep the two copies in sync if you
  change normalization rules.

### `parse_features()` — the morphology decoder
Splits the pipe-delimited features field into structured columns (`pos`, `lemma`, `root`,
`gender`, `number`, `person`, `case_state`, `aspect_mood`, `voice`, `form_derived`).
Handles both `KEY:VALUE` parts (`POS:N`, `ROOT:rHm`, `PRON:...`) and bare flag tokens
(`NOM`, `PERF`, `M`, `P`). Pronoun features have a dedicated `parse_pronoun_features()`
helper. This is the most fragile part of parsing — new/unusual feature codes are silently
dropped rather than erroring.

### Database schema (quran_morphology.db)
`suras` (114) → `verses` (6,236) → `words` → `tokens` (~128k), plus `roots` (~1,642 with
precomputed `occurrence_count`) and the `verses_fts` FTS5 virtual table. Relationships are
keyed on natural `(sura_id, verse_num, word_num, token_num)` tuples, not surrogate FKs.
Full-text queries use column filters, e.g. `verses_fts MATCH 'text_arabic_normalized:"..."'`
or `'translation:Paradise'`. See `query_examples.py` for canonical JOIN patterns across
all levels.

### Learning harness (`build_learning_harness.py`)
Independent secondary build. Reads roots from `quran_morphology.db`, joins them against
the local **Lane's Lexicon** cache `quran_arabic_roots_lane_lexicon_2026-02-12.json`
(11MB; falls back to downloading from GitHub if missing), and produces
`learning_harness.db` — a flat `learning_harness(root, en_word, id_word)` vocab table.
Indonesian glosses come from the unofficial Google Translate web endpoint with a 0.05s
per-request delay; failures fall back to the English text. This step is network-bound and
slow (~1,642 sequential HTTP calls).

## Notebooks
`*_colab.ipynb` are self-contained Google Colab wrappers (upload corpus → build → query
via form widgets). `*.en.ipynb` / `README.en.md` are English mirrors of the Indonesian
primary docs — update both language variants together when changing user-facing content.

## Dependency graph reconstruction (in progress)
See **HANDOFF.md** — active effort to recreate corpus.quran.com dependency graphs locally
from the Extended Quranic Treebank (EQTB) data in `eqtb/`. The morphology .txt has no
syntax data; do not look for dependency relations in it. `eqtb/Quranic.csv` (57 MB,
gitignored) re-extracts from `eqtb/Quranic.rar`. Work happens in WSL
(`/mnt/c/...`) because Windows-side Python is unavailable in this environment.

## Data file constraint
`quranic-corpus-morphology-0.4.txt` carries a GPL copyright header that legally prohibits
modification. Treat it as read-only source input; never edit or reformat it.
