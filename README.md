# YT Short Fashion Generator

Program ini menghasilkan video pendek (shorts) tentang fashion pria dengan menggunakan file JSON sebagai sumber konten dan gambar dari folder yang ditentukan. Video yang dihasilkan dapat diunggah secara otomatis ke YouTube. Program ini menggunakan prompt.txt untuk menghasilkan konten yang bervariasi dan SEO-optimized untuk YouTube Shorts.

## Persyaratan

Instal semua dependensi yang diperlukan:

```bash
pip install -r requirements.txt
```

## Penggunaan

Program ini dapat menggunakan file JSON sebagai sumber konten atau menghasilkan konten baru menggunakan prompt.txt. Berikut adalah contoh perintah dasar:

```bash
python cli.py --json path/to/your/content.json --images path/to/images/folder
```

### Menggunakan prompt.txt

Untuk menghasilkan konten baru, Anda dapat menggunakan file prompt.txt yang sudah disediakan. File ini berisi instruksi untuk menghasilkan konten YouTube Shorts dengan aturan khusus untuk judul, voiceover, deskripsi, dan image prompts.

#### Format Judul yang Diperbarui

Prompt.txt telah dioptimalkan untuk menghasilkan judul yang lebih bervariasi dengan format yang berbeda-beda:

- Selalu menggunakan angka 5 jika menggunakan format numbering ("5 Essential...", "5 Must-Have...")
- Variasi format judul: Question, Command, Benefit, Curiosity, dan Statement
- Kategori judul yang berotasi: numbering, how-to/guide, seasonal/occasion, style concept, dan color-focused
- Selalu menggunakan tahun 2025 jika mereferensikan tahun
- Tidak mengulang struktur atau kata yang sama dari generasi sebelumnya

Untuk menghasilkan konten dengan prompt.txt, gunakan perintah berikut:

```bash
# Menggunakan OpenAI API untuk menghasilkan konten dari prompt.txt
python generate_content.py

# Atau jika Anda ingin langsung menggunakan konten yang dihasilkan untuk membuat video
python cli.py --prompt prompt.txt --images images/1
```

> **Catatan**: Pastikan Anda telah mengatur API key yang diperlukan di file .env jika menggunakan OpenAI API.

### Contoh File JSON

File JSON harus memiliki format array yang berisi satu atau lebih objek seperti berikut (lihat `example.json`):

```json
[
  {
    "title": "5 Timeless Pieces Every Man Should Own in 2025",
    "voiceover": "Here are 5 essential wardrobe pieces every stylish man needs in 2025. These versatile items will elevate your look for any occasion and never go out of style.",
    "description": "Discover the 5 must-have wardrobe essentials for men in 2025. Which piece is your favorite? Comment below! #MensFashion #StyleEssentials #MensWardrobe #OldMoney #MensStyle #OutfitInspo #2025Style",
    "image_prompts": [
      "Handsome white American man wearing a perfectly tailored navy blazer on city street in daylight with natural bright lighting, clean modern street fashion photography, sharp focus, cinematic, eye-catching",
      "Handsome white American man wearing quality white oxford shirt with subtle details on city street in daylight with natural bright lighting, clean modern street fashion photography, sharp focus, cinematic, eye-catching",
      "Handsome white American man wearing premium dark selvedge denim jeans with perfect fit on city street in daylight with natural bright lighting, clean modern street fashion photography, sharp focus, cinematic, eye-catching",
      "Handsome white American man wearing minimalist leather dress shoes in rich brown color on city street in daylight with natural bright lighting, clean modern street fashion photography, sharp focus, cinematic, eye-catching",
      "Handsome white American man wearing classic camel overcoat with modern proportions on city street in daylight with natural bright lighting, clean modern street fashion photography, sharp focus, cinematic, eye-catching"
    ],
    "tags": [
      "mens fashion",
      "style essentials",
      "wardrobe staples",
      "timeless style",
      "2025 fashion",
      "mens style guide",
      "classic menswear"
    ]
  }
]
```

Field yang wajib ada:
- `title`: Judul video (selalu menggunakan angka 5 jika menggunakan format numbering)
- `voiceover`: Teks untuk voiceover (10-15 detik untuk suara pria yang percaya diri)
- `description`: Deskripsi video untuk YouTube (termasuk call-to-action dan 5-7 hashtag)
- `image_prompts`: Array berisi 5 prompt untuk setiap gambar (setiap prompt menampilkan outfit atau aksesori berbeda)

Field opsional:
- `tags`: Array berisi tag untuk YouTube

### Opsi Tambahan

```
--output PATH         Path ke folder output (default: ./output)
--duration N          Durasi gambar dalam detik (default: 3)
--dark-overlay        Gunakan overlay gelap pada gambar
--no-zoom             Nonaktifkan efek zoom pada gambar
--voiceover           Gunakan voiceover (menggunakan layanan gtts)
--music PATH          Folder berisi file musik untuk background
--limit N             Batasi jumlah data yang diproses dari file JSON
```

### Upload ke YouTube

Untuk mengupload video ke YouTube, tambahkan opsi berikut:

```
--youtube             Upload ke YouTube setelah pembuatan video
--client-secret PATH  Path ke file client_secret.json untuk YouTube API
--token PATH          Path ke file token.json untuk YouTube API (opsional)
--title-template STR  Template judul untuk YouTube (default: {title})
--description STR     Template deskripsi untuk YouTube (default: {description})
--tags STR            Tags untuk YouTube, dipisahkan dengan koma
--privacy CHOICE      Status privasi YouTube (private, unlisted, public)
--auto-delete         Hapus video setelah berhasil diupload ke YouTube
```

## Contoh Perintah

### Contoh Dasar

```bash
# Windows
python cli.py --json data\example.json --images images\1

# macOS/Linux
python cli.py --json data/example.json --images images/1
```

### Dengan Voiceover dan Efek

```bash
# Windows
python cli.py --json data\example.json --images images\1 --voiceover --dark-overlay --duration 4

# macOS/Linux
python cli.py --json data/example.json --images images/1 --voiceover --dark-overlay --duration 4
```

### Dengan Prompt dan Voiceover

```bash
# Windows
python cli.py --prompt prompt.txt --images images\1 --voiceover

# macOS/Linux
python cli.py --prompt prompt.txt --images images/1 --voiceover
```

### Dengan Upload YouTube

```bash
# Windows
python cli.py --json data\example.json --images images\1 --voiceover --youtube --client-secret client_secret.json --privacy unlisted

# macOS/Linux
python cli.py --json data/example.json --images images/1 --voiceover --youtube --client-secret client_secret.json --privacy unlisted
```

Untuk bantuan lebih lanjut, jalankan:

```bash
python cli.py --help
```