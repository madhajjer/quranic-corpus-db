import os
import sqlite3
import urllib.request
import urllib.parse
import json
import time
import re

# Define paths
WORKSPACE_DIR = os.path.dirname(os.path.abspath(__file__))
MORPHOLOGY_DB_PATH = os.path.join(WORKSPACE_DIR, "quran_morphology.db")
HARNESS_DB_PATH = os.path.join(WORKSPACE_DIR, "learning_harness.db")

# URL of the Lane's Lexicon etymology database JSON
LANE_JSON_URL = "https://raw.githubusercontent.com/aliozdenisik/quran-arabic-roots-lane-lexicon/main/quran_arabic_roots_lane_lexicon_2026-02-12.json"

def translate_en_to_id(text):
    if not text:
        return ""
    # Clean text to keep it short for vocabulary mapping
    # (Extract the first sentence or first few words if it's too long)
    match = re.match(r'^([^.;]+)', text)
    clean_text = match.group(1).strip() if match else text
    
    try:
        url = "https://translate.googleapis.com/translate_a/single?client=gtx&sl=en&tl=id&dt=t&q=" + urllib.parse.quote(clean_text)
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=5) as response:
            res = json.loads(response.read().decode('utf-8'))
            translated_text = "".join(segment[0] for segment in res[0] if segment[0])
            return translated_text.strip()
    except Exception as e:
        # Fallback to English if translation API fails
        return clean_text

LANE_JSON_FILE_PATH = os.path.join(WORKSPACE_DIR, "quran_arabic_roots_lane_lexicon_2026-02-12.json")

def download_lane_lexicon():
    # Try local load first
    if os.path.exists(LANE_JSON_FILE_PATH):
        print(f"Loading Lane's Lexicon from local file: {LANE_JSON_FILE_PATH}...")
        try:
            with open(LANE_JSON_FILE_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            roots_list = data.get('roots', [])
            roots_dict = {}
            for entry in roots_list:
                rb = entry.get('root_buckwalter')
                if rb:
                    roots_dict[rb] = entry
            print("Successfully loaded Lane's Lexicon from local file.")
            return roots_dict
        except Exception as e:
            print(f"Failed to read local Lane's Lexicon file: {e}. Falling back to download...")
            
    print(f"Downloading Lane's Lexicon JSON database (approx. 11MB) from {LANE_JSON_URL}...")
    try:
        req = urllib.request.Request(LANE_JSON_URL, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=30) as response:
            data = json.loads(response.read().decode('utf-8'))
            print("Successfully downloaded Lane's Lexicon JSON.")
            
            # Save locally for future use
            try:
                with open(LANE_JSON_FILE_PATH, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False)
                print(f"Saved Lane's Lexicon locally to {LANE_JSON_FILE_PATH}")
            except Exception as e:
                print(f"Warning: Failed to save Lane's Lexicon locally: {e}")
                
            roots_list = data.get('roots', [])
            roots_dict = {}
            for entry in roots_list:
                rb = entry.get('root_buckwalter')
                if rb:
                    roots_dict[rb] = entry
            return roots_dict
    except Exception as e:
        print(f"Error downloading Lane's Lexicon database: {e}")
        return {}

def main():
    if not os.path.exists(MORPHOLOGY_DB_PATH):
        print(f"Error: Morphology database not found at {MORPHOLOGY_DB_PATH}")
        print("Please build it first using convert_corpus.py.")
        return
        
    # Download root vocabulary definitions
    lane_roots = download_lane_lexicon()
    if not lane_roots:
        print("Failed to load root definitions. Exiting.")
        return
        
    print("Connecting to morphology database to retrieve roots...")
    conn_morph = sqlite3.connect(MORPHOLOGY_DB_PATH)
    cursor_morph = conn_morph.cursor()
    
    # Get all roots and their transliterations from our build database
    cursor_morph.execute("SELECT root_arabic, root_transliterated, occurrence_count FROM roots WHERE root_arabic IS NOT NULL;")
    roots_in_db = cursor_morph.fetchall()
    conn_morph.close()
    
    total_roots = len(roots_in_db)
    print(f"Found {total_roots} roots in morphology database.")
    
    # Connect and initialize Learning Harness database
    print(f"Initializing learning harness database at: {HARNESS_DB_PATH}")
    conn_harness = sqlite3.connect(HARNESS_DB_PATH)
    cursor_harness = conn_harness.cursor()
    
    cursor_harness.execute("DROP TABLE IF EXISTS learning_harness;")
    cursor_harness.execute("""
        CREATE TABLE learning_harness (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            root TEXT NOT NULL,
            en_word TEXT,
            id_word TEXT
        );
    """)
    conn_harness.commit()
    
    # Process and insert root vocabulary
    print("Processing roots and translating definitions to Indonesian...")
    insert_records = []
    
    start_time = time.time()
    for idx, (root_ar, root_trans, count) in enumerate(roots_in_db, 1):
        # Look up root details in the downloaded Lane's Lexicon
        # The key in lane_roots dictionary matches the transliterated root (or root_trans)
        lane_entry = lane_roots.get(root_trans, {})
        
        # Extract English vocabulary meaning
        en_meaning = ""
        if lane_entry:
            # We look for summary_en first, then fall back to English definitions/summaries
            en_meaning = lane_entry.get('summary_en', '')
            if not en_meaning:
                # Clean up general summaries or definitions if summary_en is missing
                en_meaning = f"Root relating to {root_trans}"
        else:
            en_meaning = f"Root relating to {root_trans}"
            
        # Clean and shorten English meaning to represent vocabulary words / core actions
        # Let's extract the first part to make it a concise vocab card
        en_meaning = en_meaning.replace(" (assumed tropical)", "").replace(" (tropical)", "")
        
        # Translate to Indonesian (id_word)
        id_meaning = translate_en_to_id(en_meaning)
        
        # For roots with very long definitions, strip trailing periods and brackets
        en_vocab = en_meaning.strip()
        id_vocab = id_meaning.strip()
        
        insert_records.append((root_ar, en_vocab, id_vocab))
        
        # Print progress and estimate remaining time
        if idx % 100 == 0 or idx == total_roots:
            elapsed = time.time() - start_time
            avg_time = elapsed / idx
            eta = avg_time * (total_roots - idx)
            print(f"Progress: {idx}/{total_roots} roots processed. ETA: {eta:.1f}s")
            
        # Small delay to respect Google Translate web API limits
        time.sleep(0.05)
        
    print("Writing records to learning_harness database...")
    cursor_harness.executemany("""
        INSERT INTO learning_harness (root, en_word, id_word)
        VALUES (?, ?, ?);
    """, insert_records)
    conn_harness.commit()
    
    # Print stats
    cursor_harness.execute("SELECT COUNT(*) FROM learning_harness;")
    loaded_count = cursor_harness.fetchone()[0]
    
    print("\n" + "="*45)
    print("LEARNING HARNESS DATABASE GENERATED!")
    print(f"Database saved to: {HARNESS_DB_PATH}")
    print(f"Total Roots loaded: {loaded_count}")
    print("="*45 + "\n")
    
    # Show first 10 entries as preview
    cursor_harness.execute("SELECT id, root, en_word, id_word FROM learning_harness LIMIT 10;")
    preview = cursor_harness.fetchall()
    print("Preview of first 10 roots in harness:")
    print(f"{'ID':<4} | {'Root':<5} | {'English Meaning':<50} | {'Indonesian Meaning'}")
    print("-"*100)
    for row in preview:
        print(f"{row[0]:<4} | {row[1]:<5} | {row[2][:50]:<50} | {row[3]}")
        
    conn_harness.close()

if __name__ == "__main__":
    main()
