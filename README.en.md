# Quranic Arabic Corpus Morphology to SQLite Database Converter

This repository contains tools to convert the token-by-token morphology data of the **Quranic Arabic Corpus (version 0.4)** into a structured, indexed, and relational **SQLite Database** (`quran_morphology.db`).

The converter transforms the raw Buckwalter-transliterated tabular data into a robust relational database schema that supports querying at multiple linguistic levels (Surah, Verse, Word, Token, and Roots) and enables full-text searches.

---

## ✨ Features

- **Buckwalter to Arabic Conversion:** Converts Buckwalter transliteration (including extended Uthmani symbols like Alif Khanjariya `ٰ` and Alif Wasla `ٱ`) back to readable Arabic script.
- **Vowel-Free Search Normalization:** Automatically strips diacritics (harakaat) and normalizes Alifs/Yas to a separate column (`text_arabic_normalized`) so you can search the Quran using plain modern Arabic script (e.g. searching for `"رب العالمين"` matches the Uthmani spelling `رَبِّ ٱلْعَٰلَمِينَ`).
- **Translation & Metadata Integration:** Downloads and parses:
  - Official Surah names and revelation types from the `api.alquran.cloud` API.
  - Sahih International English translation from `Tanzil.info`.
  - *Falls back gracefully to offline mode if no internet connection is available.*
- **Word & Verse Reconstruction:** Aggregates token-level segments to automatically reconstruct whole words, parts of speech signatures (e.g. `DET+ADJ` or `P+N`), and complete verse texts.
- **SQLite FTS5 Full-Text Search:** Indexes Arabic script, transliterations, and English translations in a virtual table for sub-millisecond search performance.

---

## 🗄️ Database Schema

The database consists of the following tables:

1. **`suras`:** Metadata for the 114 Surahs (names in Arabic and English, translation of names, revelation types, total verses).
2. **`verses`:** Reconstructed text of the 6,236 verses in standard Arabic Uthmani script, normalized Arabic, transliterated Buckwalter, and English translation.
3. **`words`:** Every word of the Quran mapped by `(sura_id, verse_num, word_num)`, showing text (Arabic, normalized Arabic, and transliterated) and parts-of-speech structure.
4. **`tokens`:** Fine-grained syntactic/morphological segments (e.g. prefixes, suffixes, stems) with details such as Tag, Lemma, Root, Gender, Number, Case/State, Person, Voice, and Verb Form.
5. **`roots`:** Unique index of all 1,642 Arabic roots in the Quran along with pre-calculated occurrence frequencies.
6. **`verses_fts` (Virtual Table):** Full-text search index powering searches across translations and normalized Arabic script.

---

## 🚀 Getting Started

### 📋 Requirements
- Python 3.x
- WSL (Windows Subsystem for Linux) or Linux/macOS environment (recommended).
- No external Python libraries are required (uses built-in libraries `sqlite3`, `urllib.request`, `re`, and `json`).

### 📦 Setup & Building the Database
1. Make sure you have the morphology corpus file `quranic-corpus-morphology-0.4.txt` in the same directory as the script.
2. Run the converter script inside your WSL or Linux terminal:
   ```bash
   python3 convert_corpus.py
   ```
   *This will take around 5–10 seconds to fetch translation files, parse all 128,219 tokens, reconstruct the Quranic text, and build the database.*

### ☁️ Run in Google Colab
If you prefer not to set up Python locally, you can run the interactive **[quran_morphology_colab.en.ipynb](file:///c:/Users/Muhajir/Downloads/quranic-corpus-morphology-0.4/quran_morphology_colab.en.ipynb)** directly in Google Colab:
1. Open Google Colab (https://colab.research.google.com) and upload the `quran_morphology_colab.en.ipynb` notebook.
2. Run the cells sequentially. The notebook provides code cells to upload the morphology corpus file, generate the database, and run interactive search queries (e.g. root lookups, phrase matchers, and verse inspectors) through simple web forms.

---

## 🔍 Examples of Queries

You can execute the query showcase script to test standard database queries:
```bash
python3 query_examples.py
```

### 1. Root Query Example (e.g. Root `رحم` - Mercy)
```sql
SELECT t.sura_id, t.verse_num, w.text_arabic, t.tag, t.features, v.translation
FROM tokens t
JOIN words w ON t.sura_id = w.sura_id AND t.verse_num = w.verse_num AND t.word_num = w.word_num
JOIN verses v ON t.sura_id = v.sura_id AND t.verse_num = v.verse_num
WHERE t.root_arabic = 'رحم'
LIMIT 5;
```

### 2. Normalized Phrase Query Example (e.g. `"رب العلمين"`)
```sql
SELECT v.sura_id, v.verse_num, v.text_arabic, v.translation
FROM verses_fts f
JOIN verses v ON f.sura_id = v.sura_id AND f.verse_num = v.verse_num
WHERE verses_fts MATCH 'text_arabic_normalized:"رب العلمين"';
```

### 3. Translation Search Example (e.g. `"Paradise"`)
```sql
SELECT v.sura_id, v.verse_num, v.text_arabic, v.translation
FROM verses_fts f
JOIN verses v ON f.sura_id = v.sura_id AND f.verse_num = v.verse_num
WHERE verses_fts MATCH 'translation:Paradise'
LIMIT 5;
```

---

## 🧠 Vocabulary Learning Harness Database

We have added a vocabulary learning database (`learning_harness.db`) mapping all 1,642 roots in the Quran to their core vocabulary definitions in both English and Indonesian.

- **Local JSON Lexicon Source:** [quran_arabic_roots_lane_lexicon_2026-02-12.json](file:///c:/Users/Muhajir/Downloads/quranic-corpus-morphology-0.4/quran_arabic_roots_lane_lexicon_2026-02-12.json) (11MB local cache of Lane's Arabic-English Lexicon database).
- **Harness Builder Script:** [build_learning_harness.py](file:///c:/Users/Muhajir/Downloads/quranic-corpus-morphology-0.4/build_learning_harness.py).
- **Generated Database:** `learning_harness.db` containing table `learning_harness` with schema:
  - `id` (INTEGER PRIMARY KEY)
  - `root` (TEXT) - Arabic root (e.g., `رحم`)
  - `en_word` (TEXT) - English vocabulary definition
  - `id_word` (TEXT) - Indonesian vocabulary definition (translated on-the-fly)

### How to rebuild / run the harness:
```bash
python3 build_learning_harness.py
```

