import os
import sqlite3
import sys
import re

# Define path to the database
WORKSPACE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE_PATH = os.path.join(WORKSPACE_DIR, "quran_morphology.db")

def print_section(title):
    print("\n" + "="*80)
    print(f" {title} ".center(80, "="))
    print("="*80)

def normalize_arabic(text):
    if not text:
        return ""
    # Strip all Arabic diacritics / harakaat
    diacritics_pattern = re.compile(r'[\u064b-\u0652\u0670\u0653\u0654\u0655]')
    text = diacritics_pattern.sub('', text)
    
    # Normalize Alifs
    text = re.sub(r'[ٱآأإ]', '\u0627', text)
    
    # Normalize Ya Hamza and Alif Maksura to standard Ya
    text = re.sub(r'[ئى]', '\u064a', text)
    
    # Normalize Ta Marbuta to Ha
    text = re.sub(r'ة', '\u0647', text)
    
    return text

def query_by_root(conn, root_ar):
    print_section(f"Querying Words with Root: {root_ar}")
    cursor = conn.cursor()
    cursor.execute("""
        SELECT 
            t.sura_id, t.verse_num, t.word_num,
            s.name_english,
            w.text_arabic AS word_arabic,
            t.form_arabic AS segment_arabic,
            t.tag,
            t.features,
            v.translation
        FROM tokens t
        JOIN words w ON t.sura_id = w.sura_id AND t.verse_num = w.verse_num AND t.word_num = w.word_num
        JOIN verses v ON t.sura_id = v.sura_id AND t.verse_num = v.verse_num
        JOIN suras s ON t.sura_id = s.id
        WHERE t.root_arabic = ? OR t.root_transliterated = ?
        LIMIT 10;
    """, (root_ar, root_ar))
    
    results = cursor.fetchall()
    if not results:
        print("No matches found for root.")
        return
        
    print(f"{'Sura:Verse:Word':<18} | {'Surah Name':<12} | {'Word (AR)':<10} | {'Segment':<8} | {'Tag':<5} | {'Features'}")
    print("-"*80)
    for row in results:
        loc = f"{row[0]}:{row[1]}:{row[2]}"
        print(f"{loc:<18} | {row[3]:<12} | {row[4]:<10} | {row[5]:<8} | {row[6]:<5} | {row[7]}")
        print(f"   [Translation] {row[8]}\n")

def query_by_phrase(conn, phrase_ar):
    print_section(f"Searching for Arabic Phrase: {phrase_ar}")
    cursor = conn.cursor()
    
    # Normalize the query phrase first
    normalized_phrase = normalize_arabic(phrase_ar)
    print(f"(Normalized phrase query: '{normalized_phrase}')")
    
    # Search on text_arabic_normalized column in FTS5
    query_str = f'text_arabic_normalized:"{normalized_phrase}"'
    cursor.execute("""
        SELECT 
            v.sura_id, v.verse_num, 
            s.name_english,
            v.text_arabic, 
            v.translation
        FROM verses_fts f
        JOIN verses v ON f.sura_id = v.sura_id AND f.verse_num = v.verse_num
        JOIN suras s ON v.sura_id = s.id
        WHERE verses_fts MATCH ?
        LIMIT 5;
    """, (query_str,))
    
    results = cursor.fetchall()
    if not results:
        print("No matches found for phrase.")
        return
        
    for row in results:
        print(f"Surah {row[0]}:{row[1]} ({row[2]}):")
        print(f"   [Arabic]      {row[3]}")
        print(f"   [Translation] {row[4]}\n")

def search_english_translation(conn, keyword):
    print_section(f"FTS5 Search English Translation: '{keyword}'")
    cursor = conn.cursor()
    cursor.execute("""
        SELECT 
            v.sura_id, v.verse_num, 
            s.name_english,
            v.text_arabic, 
            v.translation
        FROM verses_fts f
        JOIN verses v ON f.sura_id = v.sura_id AND f.verse_num = v.verse_num
        JOIN suras s ON v.sura_id = s.id
        WHERE verses_fts MATCH ?
        LIMIT 5;
    """, (f"translation:{keyword}",))
    
    results = cursor.fetchall()
    if not results:
        print("No matches found.")
        return
        
    for row in results:
        print(f"Surah {row[0]}:{row[1]} ({row[2]}):")
        print(f"   [Arabic]      {row[3]}")
        print(f"   [Translation] {row[4]}\n")

def verse_morphology_breakdown(conn, sura, verse):
    print_section(f"Morphological Breakdown for Verse {sura}:{verse}")
    cursor = conn.cursor()
    
    cursor.execute("SELECT text_arabic, translation FROM verses WHERE sura_id = ? AND verse_num = ?;", (sura, verse))
    verse_info = cursor.fetchone()
    if not verse_info:
        print("Verse not found.")
        return
        
    print(f"Verse Arabic:      {verse_info[0]}")
    print(f"Verse Translation: {verse_info[1]}")
    print("-"*80)
    
    cursor.execute("""
        SELECT 
            word_num, token_num, segment_type,
            form_arabic, tag, pos, lemma_arabic, root_arabic, features
        FROM tokens
        WHERE sura_id = ? AND verse_num = ?
        ORDER BY word_num, token_num;
    """, (sura, verse))
    
    tokens = cursor.fetchall()
    current_word = None
    
    for t in tokens:
        word_num = t[0]
        if current_word != word_num:
            current_word = word_num
            print(f"\nWord {word_num}:")
            
        seg_num = t[1]
        seg_type = t[2]
        form_ar = t[3]
        tag = t[4]
        pos = t[5] if t[5] else '-'
        lemma = t[6] if t[6] else '-'
        root = t[7] if t[7] else '-'
        feat = t[8]
        
        print(f"  Token {seg_num} ({seg_type:<6}): {form_ar:<8} | Tag: {tag:<4} | POS: {pos:<4} | Lemma: {lemma:<8} | Root: {root:<6} | Features: {feat}")

def show_statistics(conn):
    print_section("Quranic Linguistics Statistics")
    cursor = conn.cursor()
    
    # 1. Top 10 Roots
    print("Top 10 Most Frequent Roots in the Quran:")
    cursor.execute("""
        SELECT root_arabic, root_transliterated, occurrence_count 
        FROM roots 
        WHERE root_arabic IS NOT NULL
        ORDER BY occurrence_count DESC 
        LIMIT 10;
    """)
    top_roots = cursor.fetchall()
    print(f"   {'Rank':<4} | {'Root (AR)':<10} | {'Root (BW)':<10} | {'Occurrences'}")
    print("   " + "-"*45)
    for i, row in enumerate(top_roots, 1):
        print(f"   {i:<4} | {row[0]:<10} | {row[1]:<10} | {row[2]}")
    print()
    
    # 2. POS Distribution
    print("Distribution of Major Part of Speech (POS) Tags:")
    cursor.execute("""
        SELECT tag, COUNT(*) as cnt 
        FROM tokens 
        GROUP BY tag 
        ORDER BY cnt DESC 
        LIMIT 10;
    """)
    pos_dist = cursor.fetchall()
    print(f"   {'Tag':<6} | {'Occurrences'}")
    print("   " + "-"*22)
    for row in pos_dist:
        print(f"   {row[0]:<6} | {row[1]}")
    print()

def main():
    if not os.path.exists(DB_FILE_PATH):
        print(f"Error: Database file not found at {DB_FILE_PATH}")
        print("Please run convert_corpus.py first.")
        sys.exit(1)
        
    conn = sqlite3.connect(DB_FILE_PATH)
    
    # Execute query showcases
    show_statistics(conn)
    
    # Search by Root 'rHm' (رحم - Mercy/Merciful)
    query_by_root(conn, "رحم")
    
    # Search by Phrase 'رب العلمين' (Lord of the worlds - Uthmani spelling)
    query_by_phrase(conn, "رب العلمين")
    
    # Search English translation for 'Paradise'
    search_english_translation(conn, "Paradise")
    
    # Detailed morphological breakdown of Surah 1, Verse 1 (Al-Fatihah, Ayah 1)
    verse_morphology_breakdown(conn, 1, 1)
    
    conn.close()

if __name__ == "__main__":
    main()
