import os
import re
import sqlite3
import urllib.request
import json

# Define paths
WORKSPACE_DIR = os.path.dirname(os.path.abspath(__file__))
CORPUS_FILE_PATH = os.path.join(WORKSPACE_DIR, "quranic-corpus-morphology-0.4.txt")
DB_FILE_PATH = os.path.join(WORKSPACE_DIR, "quran_morphology.db")

# Extended Buckwalter to Arabic Unicode Mapping
BUCKWALTER_TO_ARABIC = {
    # Letters
    'A': '\u0627',  # Alif
    'b': '\u0628',  # Ba
    't': '\u062a',  # Ta
    'v': '\u062b',  # Tha
    'j': '\u062c',  # Jeem
    'H': '\u062d',  # Hah
    'x': '\u062e',  # Khah
    'd': '\u062f',  # Dal
    '*': '\u0630',  # Thal
    'r': '\u0631',  # Ra
    'z': '\u0632',  # Zayn
    's': '\u0633',  # Seen
    '$': '\u0634',  # Sheen
    'S': '\u0635',  # Sad
    'D': '\u0636',  # Dad
    'T': '\u0637',  # Tah
    'Z': '\u0638',  # Zah
    'E': '\u0639',  # Ayn
    'g': '\u063a',  # Ghayn
    'f': '\u0641',  # Fa
    'q': '\u0642',  # Qaf
    'k': '\u0643',  # Kaf
    'l': '\u0644',  # Lam
    'm': '\u0645',  # Meem
    'n': '\u0646',  # Noon
    'h': '\u0647',  # Ha
    'w': '\u0648',  # Waw
    'y': '\u064a',  # Ya
    'Y': '\u0649',  # Alif Maksura
    'p': '\u0629',  # Ta Marbuta
    
    # Hamzas & variants
    '\'': '\u0621', # Hamza (standalone)
    '|': '\u0622',  # Alif Madda
    '>': '\u0623',  # Alif Hamza Above
    '&': '\u0624',  # Waw Hamza
    '<': '\u0625',  # Alif Hamza Below
    '}': '\u0626',  # Ya Hamza
    
    # Diacritics (Harakaat)
    'a': '\u064e',  # Fatha
    'u': '\u064f',  # Damma
    'i': '\u0650',  # Kasra
    'F': '\u064b',  # Fathatayn
    'N': '\u064c',  # Dammatayn
    'K': '\u064d',  # Kasratayn
    '~': '\u0651',  # Shadda
    'o': '\u0652',  # Sukun
    
    # Extended Quranic Symbols
    '`': '\u0670',  # Superscript Alif
    '{': '\u0671',  # Alif Wasla
    '^': '\u0653',  # Maddah Above
    '#': '\u0654',  # Hamza Above
    ':': '\u06e2',  # Small High Seen
    '@': '\u06df',  # Small High Rounded Zero
    '"': '\u06e0',  # Small High Upright Rectangular Zero
    '[': '\u06e8',  # Small High Meem Isolated
    ';': '\u06e5',  # Small Low Seen
    ',': '\u06e5',  # Small Waw
    '.': '\u06e6',  # Small Ya
    '!': '\u06e7',  # Small High Noon
    '-': '\u06ea',  # Empty Centre Low Stop
    '+': '\u06e9',  # Empty Centre High Stop
    '%': '\u06eb',  # Rounded High Stop (Filled Centre)
    ']': '\u06ed',  # Small Low Meem
    '_': '\u0640',  # Tatweel
}

SURAH_FALLBACK_NAMES = [
    "Al-Fatihah", "Al-Baqarah", "Ali 'Imran", "An-Nisa", "Al-Ma'idah", "Al-An'am", "Al-A'raf", "Al-Anfal", "At-Tawbah", "Yunus",
    "Hud", "Yusuf", "Ar-Ra'd", "Ibrahim", "Al-Hijr", "An-Nahl", "Al-Isra", "Al-Kahf", "Maryam", "Ta-Ha",
    "Al-Anbiya", "Al-Hajj", "Al-Mu'minun", "An-Nur", "Al-Furqan", "Ash-Shu'ara", "An-Naml", "Al-Qasas", "Al-Ankabut", "Ar-Rum",
    "Luqman", "As-Sajdah", "Al-Ahzab", "Saba", "Fatir", "Ya-Sin", "As-Saffat", "Sad", "Az-Zumar", "Ghafir",
    "Fussilat", "Ash-Shura", "Az-Zukhruf", "Ad-Dukhan", "Al-Jathiyah", "Al-Ahqaf", "Muhammad", "Al-Fath", "Al-Hujurat", "Qaf",
    "Adh-Dhariyat", "At-Tur", "An-Najm", "Al-Qamar", "Ar-Rahman", "Al-Waqi'ah", "Al-Hadid", "Al-Mujadilah", "Al-Hashr", "Al-Mumtahanah",
    "As-Saff", "Al-Jumu'ah", "Al-Munafiqun", "At-Taghabun", "At-Talaq", "At-Tahrim", "Al-Mulk", "Al-Qalam", "Al-Haqqah", "Al-Ma'arij",
    "Nuh", "Al-Jinn", "Al-Muzzammil", "Al-Muddaththir", "Al-Qiyamah", "Al-Insan", "Al-Mursalat", "An-Naba", "An-Nazi'at", "Abasa",
    "At-Takwir", "Al-Infitar", "Al-Mutaffifin", "Al-Inshiqaq", "Al-Buruj", "At-Tariq", "Al-A'la", "Al-Ghashiyah", "Al-Fajr", "Al-Balad",
    "Ash-Shams", "Al-Layl", "Ad-Duha", "Ash-Sharh", "At-Tin", "Al-Alaq", "Al-Qadr", "Al-Bayyinah", "Az-Zalzalah", "Al-Adiyat",
    "Al-Qari'ah", "At-Takathur", "Al-Asr", "Al-Humazah", "Al-Fil", "Quraysh", "Al-Ma'un", "Al-Kawthar", "Al-Kafirun", "An-Nasr",
    "Al-Masad", "Al-Ikhlas", "Al-Falaq", "An-Nas"
]

def buckwalter_to_arabic(text):
    if not text:
        return ""
    return "".join(BUCKWALTER_TO_ARABIC.get(char, char) for char in text)

def normalize_arabic(text):
    if not text:
        return ""
    # Strip all Arabic diacritics / harakaat (range \u064b to \u0652, superscript alif \u0670, hamza/madda marks \u0653-\u0655)
    diacritics_pattern = re.compile(r'[\u064b-\u0652\u0670\u0653\u0654\u0655]')
    text = diacritics_pattern.sub('', text)
    
    # Normalize Alifs: ٱ (alif wasla), آ (alif madda), أ (alif hamza above), إ (alif hamza below) to standard Alif ا
    text = re.sub(r'[ٱآأإ]', '\u0627', text)
    
    # Normalize Ya Hamza ئ and Alif Maksura ى to standard Ya ي
    text = re.sub(r'[ئى]', '\u064a', text)
    
    # Normalize Ta Marbuta ة to Ha ه
    text = re.sub(r'ة', '\u0647', text)
    
    return text

def fetch_surah_metadata():
    print("Fetching Surah metadata from api.alquran.cloud...")
    try:
        url = "http://api.alquran.cloud/v1/surah"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as response:
            res = json.loads(response.read().decode('utf-8'))
            if res.get('code') == 200:
                print("Successfully fetched Surah metadata.")
                return res['data']
    except Exception as e:
        print(f"Failed to fetch Surah metadata ({e}). Using offline fallbacks.")
    return None

def fetch_translation():
    print("Fetching Sahih International English translation from Tanzil.info...")
    translation_dict = {}
    try:
        url = "https://tanzil.info/trans/en.sahih"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=15) as response:
            lines = response.read().decode('utf-8').splitlines()
            for line in lines:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                parts = line.split('|')
                if len(parts) >= 3:
                    s_num, v_num, trans_text = int(parts[0]), int(parts[1]), parts[2]
                    translation_dict[(s_num, v_num)] = trans_text
            print(f"Successfully fetched {len(translation_dict)} verse translations.")
    except Exception as e:
        print(f"Failed to fetch translation ({e}). Proceeding without translation.")
    return translation_dict

def parse_pronoun_features(pron_val, info):
    if not pron_val:
        return
    info['person'] = pron_val[0]
    if len(pron_val) == 3:
        info['gender'] = pron_val[1]
        info['number'] = pron_val[2]
    elif len(pron_val) == 2:
        if pron_val[1] in ('M', 'F'):
            info['gender'] = pron_val[1]
        elif pron_val[1] in ('S', 'D', 'P'):
            info['number'] = pron_val[1]

def parse_features(features_str):
    parts = features_str.split('|')
    seg_type = parts[0]
    info = {
        'segment_type': seg_type,
        'pos': None,
        'lemma': None,
        'root': None,
        'gender': None,
        'number': None,
        'person': None,
        'case_state': None,
        'aspect_mood': None,
        'voice': None,
        'form_derived': None
    }
    
    for part in parts[1:]:
        if ':' in part:
            key, val = part.split(':', 1)
            if key == 'POS':
                info['pos'] = val
            elif key == 'LEM':
                info['lemma'] = val
            elif key == 'ROOT':
                info['root'] = val
            elif key == 'PRON':
                parse_pronoun_features(val, info)
            elif key == 'SP':
                pass
        else:
            if part in ('NOM', 'ACC', 'GEN'):
                info['case_state'] = part
            elif part == 'INDEF':
                info['case_state'] = (info['case_state'] + '+INDEF') if info['case_state'] else 'INDEF'
            elif part in ('M', 'F'):
                info['gender'] = part
            elif part in ('S', 'D', 'P'):
                info['number'] = part
            elif part in ('1', '2', '3'):
                info['person'] = part
            elif part in ('PERF', 'IMPF', 'IMPV'):
                info['aspect_mood'] = part
            elif part in ('JUS', 'SUBJ'):
                info['aspect_mood'] = (info['aspect_mood'] + f'+{part}') if info['aspect_mood'] else part
            elif part in ('ACT', 'PASS'):
                info['voice'] = part
            elif part.startswith('(') and part.endswith(')'):
                info['form_derived'] = part[1:-1]
            elif len(part) in (2, 3) and part[0] in ('1', '2', '3'):
                info['person'] = part[0]
                if len(part) == 3:
                    info['gender'] = part[1]
                    info['number'] = part[2]
                elif len(part) == 2:
                    if part[1] in ('M', 'F'):
                        info['gender'] = part[1]
                    elif part[1] in ('S', 'D', 'P'):
                        info['number'] = part[1]
    return info

def create_database(conn):
    cursor = conn.cursor()
    
    # Drop existing tables to recreate with new schema
    cursor.execute("DROP TABLE IF EXISTS tokens;")
    cursor.execute("DROP TABLE IF EXISTS words;")
    cursor.execute("DROP TABLE IF EXISTS verses;")
    cursor.execute("DROP TABLE IF EXISTS suras;")
    cursor.execute("DROP TABLE IF EXISTS roots;")
    cursor.execute("DROP TABLE IF EXISTS verses_fts;")
    
    # 1. Suras Table
    cursor.execute("""
    CREATE TABLE suras (
        id INTEGER PRIMARY KEY,
        name_arabic TEXT NOT NULL,
        name_english TEXT NOT NULL,
        translation TEXT NOT NULL,
        type TEXT NOT NULL,
        total_verses INTEGER NOT NULL
    );
    """)
    
    # 2. Verses Table
    cursor.execute("""
    CREATE TABLE verses (
        id INTEGER PRIMARY KEY,
        sura_id INTEGER NOT NULL,
        verse_num INTEGER NOT NULL,
        text_arabic TEXT NOT NULL,
        text_arabic_normalized TEXT NOT NULL,
        text_transliterated TEXT NOT NULL,
        translation TEXT,
        FOREIGN KEY (sura_id) REFERENCES suras(id),
        UNIQUE(sura_id, verse_num)
    );
    """)
    
    # 3. Words Table
    cursor.execute("""
    CREATE TABLE words (
        id INTEGER PRIMARY KEY,
        sura_id INTEGER NOT NULL,
        verse_num INTEGER NOT NULL,
        word_num INTEGER NOT NULL,
        text_arabic TEXT NOT NULL,
        text_arabic_normalized TEXT NOT NULL,
        text_transliterated TEXT NOT NULL,
        part_of_speech_brief TEXT NOT NULL,
        FOREIGN KEY (sura_id, verse_num) REFERENCES verses(sura_id, verse_num)
    );
    """)
    
    # 4. Tokens Table
    cursor.execute("""
    CREATE TABLE tokens (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sura_id INTEGER NOT NULL,
        verse_num INTEGER NOT NULL,
        word_num INTEGER NOT NULL,
        token_num INTEGER NOT NULL,
        segment_type TEXT NOT NULL,
        form_transliterated TEXT NOT NULL,
        form_arabic TEXT NOT NULL,
        tag TEXT NOT NULL,
        features TEXT NOT NULL,
        pos TEXT,
        lemma_transliterated TEXT,
        lemma_arabic TEXT,
        root_transliterated TEXT,
        root_arabic TEXT,
        gender TEXT,
        number TEXT,
        person TEXT,
        case_state TEXT,
        aspect_mood TEXT,
        voice TEXT,
        form_derived TEXT,
        FOREIGN KEY (sura_id, verse_num, word_num) REFERENCES words(sura_id, verse_num, word_num),
        FOREIGN KEY (root_transliterated) REFERENCES roots(root_transliterated)
    );
    """)
    
    # 5. Roots Table
    cursor.execute("""
    CREATE TABLE roots (
        root_transliterated TEXT PRIMARY KEY,
        root_arabic TEXT NOT NULL,
        occurrence_count INTEGER DEFAULT 0
    );
    """)
    
    # 6. FTS5 Virtual Table
    cursor.execute("""
    CREATE VIRTUAL TABLE verses_fts USING fts5(
        sura_id UNINDEXED,
        verse_num UNINDEXED,
        text_arabic,
        text_arabic_normalized,
        text_transliterated,
        translation
    );
    """)
    
    # Indexes for optimization
    cursor.execute("CREATE INDEX idx_verses_sura_verse ON verses(sura_id, verse_num);")
    cursor.execute("CREATE INDEX idx_words_sura_verse_word ON words(sura_id, verse_num, word_num);")
    cursor.execute("CREATE INDEX idx_tokens_sura_verse_word ON tokens(sura_id, verse_num, word_num);")
    cursor.execute("CREATE INDEX idx_tokens_root ON tokens(root_transliterated);")
    
    conn.commit()

def main():
    if not os.path.exists(CORPUS_FILE_PATH):
        print(f"Error: Corpus file not found at {CORPUS_FILE_PATH}")
        return

    # Fetch external metadata & translation
    suras_meta = fetch_surah_metadata()
    translation_dict = fetch_translation()
    
    print("Connecting to database...")
    conn = sqlite3.connect(DB_FILE_PATH)
    create_database(conn)
    cursor = conn.cursor()
    
    # Parse corpus file
    print("Parsing Quranic corpus morphology file...")
    
    word_map = {}
    roots_set = set()
    roots_count = {}
    surah_max_verses = {}
    
    line_count = 0
    with open(CORPUS_FILE_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line_count += 1
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            
            # Read columns
            parts = line.split("\t")
            if len(parts) < 4:
                continue
                
            location_str = parts[0].strip()
            form_trans = parts[1].strip()
            tag = parts[2].strip()
            features_str = parts[3].strip()
            
            # Parse Location e.g. (1:1:1:1)
            loc_match = re.match(r"\((\d+):(\d+):(\d+):(\d+)\)", location_str)
            if not loc_match:
                continue
                
            s_num, v_num, w_num, t_num = map(int, loc_match.groups())
            
            # Track max verses for Surah metadata
            surah_max_verses[s_num] = max(surah_max_verses.get(s_num, 0), v_num)
            
            # Parse features
            feat_info = parse_features(features_str)
            
            # Translate form, lemma, root
            form_arabic = buckwalter_to_arabic(form_trans)
            lemma_arabic = buckwalter_to_arabic(feat_info['lemma']) if feat_info['lemma'] else None
            
            root_trans = feat_info['root']
            root_arabic = None
            if root_trans:
                root_arabic = buckwalter_to_arabic(root_trans)
                roots_set.add((root_trans, root_arabic))
                roots_count[root_trans] = roots_count.get(root_trans, 0) + 1
            
            token_rec = {
                'sura_id': s_num,
                'verse_num': v_num,
                'word_num': w_num,
                'token_num': t_num,
                'segment_type': feat_info['segment_type'],
                'form_transliterated': form_trans,
                'form_arabic': form_arabic,
                'tag': tag,
                'features': features_str,
                'pos': feat_info['pos'],
                'lemma_transliterated': feat_info['lemma'],
                'lemma_arabic': lemma_arabic,
                'root_transliterated': root_trans,
                'root_arabic': root_arabic,
                'gender': feat_info['gender'],
                'number': feat_info['number'],
                'person': feat_info['person'],
                'case_state': feat_info['case_state'],
                'aspect_mood': feat_info['aspect_mood'],
                'voice': feat_info['voice'],
                'form_derived': feat_info['form_derived']
            }
            
            key = (s_num, v_num, w_num)
            if key not in word_map:
                word_map[key] = []
            word_map[key].append(token_rec)
            
            if line_count % 30000 == 0:
                print(f"Processed {line_count} lines...")
                
    print(f"Finished parsing. Total unique words parsed: {len(word_map)}")
    
    # 1. Populate roots
    print("Inserting roots...")
    root_records = []
    for r_trans, r_ar in roots_set:
        count = roots_count.get(r_trans, 0)
        root_records.append((r_trans, r_ar, count))
    cursor.executemany("INSERT INTO roots (root_transliterated, root_arabic, occurrence_count) VALUES (?, ?, ?);", root_records)
    conn.commit()
    
    # 2. Populate suras
    print("Inserting Surah metadata...")
    sura_records = []
    for s_id in range(1, 115):
        tot_v = surah_max_verses.get(s_id, 0)
        name_ar = f"سورة {s_id}"
        name_en = SURAH_FALLBACK_NAMES[s_id - 1]
        trans_en = "Translation"
        rev_type = "Meccan"
        
        if suras_meta and s_id - 1 < len(suras_meta):
            meta = suras_meta[s_id - 1]
            name_ar = meta.get('name', name_ar)
            name_en = meta.get('transliteration_en', name_en)
            trans_en = meta.get('translation_en', trans_en)
            rev_type = meta.get('revelationType', rev_type)
            if 'numberOfAyahs' in meta:
                tot_v = meta['numberOfAyahs']
                
        sura_records.append((s_id, name_ar, name_en, trans_en, rev_type, tot_v))
    cursor.executemany("INSERT INTO suras (id, name_arabic, name_english, translation, type, total_verses) VALUES (?, ?, ?, ?, ?, ?);", sura_records)
    conn.commit()
    
    # 3. Aggregate words, verses and tokens
    print("Reconstructing words and verses...")
    words_records = []
    tokens_records = []
    verse_map = {}
    
    sorted_word_keys = sorted(word_map.keys())
    
    for s_num, v_num, w_num in sorted_word_keys:
        tokens_in_word = sorted(word_map[(s_num, v_num, w_num)], key=lambda x: x['token_num'])
        
        word_trans = "".join(t['form_transliterated'] for t in tokens_in_word)
        word_ar = "".join(t['form_arabic'] for t in tokens_in_word)
        word_ar_norm = normalize_arabic(word_ar)
        
        pos_brief = "+".join(t['tag'] for t in tokens_in_word)
        word_id = s_num * 1000000 + v_num * 1000 + w_num
        words_records.append((word_id, s_num, v_num, w_num, word_ar, word_ar_norm, word_trans, pos_brief))
        
        for t in tokens_in_word:
            tokens_records.append((
                s_num, v_num, w_num, t['token_num'], t['segment_type'],
                t['form_transliterated'], t['form_arabic'], t['tag'], t['features'],
                t['pos'], t['lemma_transliterated'], t['lemma_arabic'],
                t['root_transliterated'], t['root_arabic'],
                t['gender'], t['number'], t['person'], t['case_state'],
                t['aspect_mood'], t['voice'], t['form_derived']
            ))
            
        v_key = (s_num, v_num)
        if v_key not in verse_map:
            verse_map[v_key] = {'words_trans': [], 'words_ar': []}
        verse_map[v_key]['words_trans'].append(word_trans)
        verse_map[v_key]['words_ar'].append(word_ar)
        
    print(f"Inserting {len(words_records)} words into table...")
    cursor.executemany("""
        INSERT INTO words (id, sura_id, verse_num, word_num, text_arabic, text_arabic_normalized, text_transliterated, part_of_speech_brief)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?);
    """, words_records)
    conn.commit()
    
    print(f"Inserting {len(tokens_records)} tokens into table...")
    cursor.executemany("""
        INSERT INTO tokens (
            sura_id, verse_num, word_num, token_num, segment_type,
            form_transliterated, form_arabic, tag, features,
            pos, lemma_transliterated, lemma_arabic,
            root_transliterated, root_arabic,
            gender, number, person, case_state,
            aspect_mood, voice, form_derived
        ) VALUES (
            ?, ?, ?, ?, ?,
            ?, ?, ?, ?,
            ?, ?, ?,
            ?, ?,
            ?, ?, ?, ?,
            ?, ?, ?
        );
    """, tokens_records)
    conn.commit()
    
    # 4. Insert Verses and populate FTS5
    print("Reconstructing and inserting verses...")
    verses_records = []
    sorted_verse_keys = sorted(verse_map.keys())
    
    for s_num, v_num in sorted_verse_keys:
        v_id = s_num * 1000 + v_num
        text_ar = " ".join(verse_map[(s_num, v_num)]['words_ar'])
        text_ar_norm = normalize_arabic(text_ar)
        text_trans = " ".join(verse_map[(s_num, v_num)]['words_trans'])
        translation = translation_dict.get((s_num, v_num), None)
        
        verses_records.append((v_id, s_num, v_num, text_ar, text_ar_norm, text_trans, translation))
        
    cursor.executemany("""
        INSERT INTO verses (id, sura_id, verse_num, text_arabic, text_arabic_normalized, text_transliterated, translation)
        VALUES (?, ?, ?, ?, ?, ?, ?);
    """, verses_records)
    conn.commit()
    
    # 5. Populate FTS5 table
    print("Populating Full-Text Search (FTS5) table...")
    cursor.execute("""
    INSERT INTO verses_fts (sura_id, verse_num, text_arabic, text_arabic_normalized, text_transliterated, translation)
    SELECT sura_id, verse_num, text_arabic, text_arabic_normalized, text_transliterated, IFNULL(translation, '') FROM verses;
    """)
    conn.commit()
    
    # Done! Summarize stats
    cursor.execute("SELECT COUNT(*) FROM suras;")
    num_suras = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM verses;")
    num_verses = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM words;")
    num_words = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM tokens;")
    num_tokens = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM roots;")
    num_roots = cursor.fetchone()[0]
    
    print("\n" + "="*40)
    print("DATABASE BUILD COMPLETE SUCCESSFUL!")
    print(f"Database saved to: {DB_FILE_PATH}")
    print(f"Total Suras loaded:      {num_suras}")
    print(f"Total Verses loaded:     {num_verses}")
    print(f"Total Words loaded:      {num_words}")
    print(f"Total Tokens loaded:     {num_tokens}")
    print(f"Total Unique Roots:      {num_roots}")
    print("="*40 + "\n")
    
    conn.close()

if __name__ == "__main__":
    main()
