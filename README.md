# Konverter Morfologi Quranic Arabic Corpus ke Database SQLite

Repositori ini berisi alat untuk mengonversi data morfologi kata-demi-kata (token-by-token) dari **Quranic Arabic Corpus (versi 0.4)** menjadi **Database SQLite** relasional yang terstruktur dan terindeks (`quran_morphology.db`).

Konverter ini mengubah data tabular mentah yang ditransliterasikan dengan skema Buckwalter menjadi skema database relasional yang tangguh, mendukung pencarian di berbagai tingkat linguistik (Surah, Ayat, Kata, Token, dan Akar Kata/Root) serta memungkinkan pencarian teks lengkap (Full-Text Search).

---

## ✨ Fitur Utama

- **Konversi Buckwalter ke Tulisan Arab:** Mengonversi transliterasi Buckwalter (termasuk simbol Utsmani tambahan seperti Alif Khanjariya `ٰ` dan Alif Wasla `ٱ`) kembali ke dalam tulisan Arab yang mudah dibaca.
- **Normalisasi Pencarian Tanpa Harakat:** Secara otomatis menghapus tanda baca (harakat) dan menormalisasi Alif/Ya ke kolom terpisah (`text_arabic_normalized`) sehingga Anda dapat mencari ayat Al-Quran menggunakan tulisan Arab modern biasa (misalnya mencari `"رب العلمin"` atau `"رب العلمين"` akan cocok dengan ejaan Utsmani `رَبِّ ٱلْعَٰلَمِينَ`).
- **Integrasi Terjemahan & Metadata:** Mengunduh dan memproses secara otomatis:
  - Nama resmi Surah dan tempat turunnya (Makkiyah/Madaniyah) dari API `api.alquran.cloud`.
  - Terjemahan bahasa Inggris Sahih International dari `Tanzil.info`.
  - *Kembali secara otomatis ke mode luring (offline) jika koneksi internet tidak tersedia.*
- **Rekonstruksi Kata & Ayat:** Menggabungkan segmen tingkat token untuk merekonstruksi kata secara utuh, susunan kelas kata (seperti `DET+ADJ` atau `P+N`), serta teks ayat yang lengkap.
- **Pencarian Teks Lengkap (Full-Text Search) SQLite FTS5:** Mengindeks tulisan Arab, transliterasi, dan terjemahan bahasa Inggris dalam tabel virtual untuk memberikan performa pencarian di bawah satu milidetik.

---

## 🗄️ Skema Database

Database ini terdiri dari tabel-tabel berikut:

1. **`suras`:** Metadata untuk 114 Surah (nama dalam bahasa Arab dan Inggris, terjemahan nama, jenis wahyu, jumlah ayat).
2. **`verses`:** Teks hasil rekonstruksi dari 6.236 ayat dalam tulisan Arab Utsmani standar, tulisan Arab yang dinormalisasi, Buckwalter transliterasi, dan terjemahan bahasa Inggris.
3. **`words`:** Setiap kata dalam Al-Quran yang dipetakan berdasarkan `(sura_id, verse_num, word_num)`, menampilkan teks (Arab, Arab normalisasi, dan transliterasi) serta struktur kelas kata.
4. **`tokens`:** Segmen sintaksis/morfologi mendalam (seperti awalan, akhiran, akar kata) beserta detail seperti Tag, Lemma, Akar kata, Gender, Jumlah (tunggal/jamak), Kasus/Status, Orang (Persona), Voice, dan Bentuk Kata Kerja.
5. **`roots`:** Indeks unik dari seluruh 1.642 akar kata Arab dalam Al-Quran beserta frekuensi kemunculan yang telah dihitung sebelumnya.
6. **`verses_fts` (Tabel Virtual):** Indeks pencarian teks lengkap yang mempercepat pencarian di seluruh terjemahan dan tulisan Arab yang dinormalisasi.

---

## 🚀 Memulai Penggunaan

### 📋 Persyaratan
- Python 3.x
- WSL (Windows Subsystem for Linux) atau lingkungan Linux/macOS (sangat disarankan).
- Tidak memerlukan pustaka Python eksternal (menggunakan modul bawaan `sqlite3`, `urllib.request`, `re`, dan `json`).

### 📦 Konfigurasi & Pembuatan Database
1. Pastikan Anda memiliki berkas korpus morfologi `quranic-corpus-morphology-0.4.txt` di direktori yang sama dengan skrip.
2. Jalankan skrip konverter di terminal WSL atau Linux Anda:
   ```bash
   python3 convert_corpus.py
   ```
   *Proses ini membutuhkan waktu sekitar 5–10 detik untuk mengunduh terjemahan, menganalisis seluruh 128.219 token, merekonstruksi teks Al-Quran, dan membuat database.*

### ☁️ Jalankan di Google Colab
Jika Anda tidak ingin mengonfigurasi Python secara lokal, Anda dapat menjalankan notebook interaktif **[quran_morphology_colab.ipynb](file:///c:/Users/Muhajir/Downloads/quranic-corpus-morphology-0.4/quran_morphology_colab.ipynb)** secara langsung di Google Colab:
1. Buka Google Colab (https://colab.research.google.com) dan unggah berkas notebook `quran_morphology_colab.ipynb`.
2. Jalankan sel-sel kode secara berurutan. Notebook ini menyediakan antarmuka interaktif bagi Anda untuk mengunggah berkas korpus morfologi, membangun database, dan melakukan kueri pencarian (seperti pencarian akar kata, pencarian frasa, dan peninjauan morfologi ayat) menggunakan formulir web sederhana.

---

## 🔍 Contoh Kueri

Anda dapat menjalankan skrip percontohan kueri untuk menguji kueri database standar:
```bash
python3 query_examples.py
```

### 1. Contoh Kueri Akar Kata (misalnya Akar Kata `رحم` - Kasih Sayang / Rahmat)
```sql
SELECT t.sura_id, t.verse_num, w.text_arabic, t.tag, t.features, v.translation
FROM tokens t
JOIN words w ON t.sura_id = w.sura_id AND t.verse_num = w.verse_num AND t.word_num = w.word_num
JOIN verses v ON t.sura_id = v.sura_id AND t.verse_num = v.verse_num
WHERE t.root_arabic = 'رحم'
LIMIT 5;
```

### 2. Contoh Kueri Frasa Normalisasi (misalnya `"رب العلمin"`)
```sql
SELECT v.sura_id, v.verse_num, v.text_arabic, v.translation
FROM verses_fts f
JOIN verses v ON f.sura_id = v.sura_id AND f.verse_num = v.verse_num
WHERE verses_fts MATCH 'text_arabic_normalized:"رب العلمين"';
```

### 3. Contoh Pencarian Terjemahan (misalnya `"Paradise"`)
```sql
SELECT v.sura_id, v.verse_num, v.text_arabic, v.translation
FROM verses_fts f
JOIN verses v ON f.sura_id = v.sura_id AND f.verse_num = v.verse_num
WHERE verses_fts MATCH 'translation:Paradise'
LIMIT 5;
```

---

## 🧠 Database Pembelajaran Kosakata (Learning Harness)

Kami telah menambahkan database pembelajaran kosakata (`learning_harness.db`) yang memetakan seluruh 1.642 akar kata Arab di dalam Al-Quran ke dalam arti kosakata inti baik dalam bahasa Inggris maupun bahasa Indonesia.

- **Sumber Kamus JSON Lokal:** [quran_arabic_roots_lane_lexicon_2026-02-12.json](file:///c:/Users/Muhajir/Downloads/quranic-corpus-morphology-0.4/quran_arabic_roots_lane_lexicon_2026-02-12.json) (Cache lokal 11MB dari database Lane's Arabic-English Lexicon).
- **Skrip Pembuat Database:** [build_learning_harness.py](file:///c:/Users/Muhajir/Downloads/quranic-corpus-morphology-0.4/build_learning_harness.py).
- **Database Hasil Pembuatan:** `learning_harness.db` yang berisi tabel `learning_harness` dengan skema:
  - `id` (INTEGER PRIMARY KEY)
  - `root` (TEXT) - Akar kata Arab (misal: `رحم`)
  - `en_word` (TEXT) - Arti kosakata dalam bahasa Inggris
  - `id_word` (TEXT) - Arti kosakata dalam bahasa Indonesia (diterjemahkan otomatis)

### Cara membuat ulang / menjalankan skrip:
```bash
python3 build_learning_harness.py
```

