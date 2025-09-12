# YT Short Fashion Generator

Program ini menghasilkan video pendek (shorts) tentang fashion dengan menggunakan file JSON sebagai sumber konten dan gambar dari folder yang ditentukan. Video yang dihasilkan dapat diunggah secara otomatis ke YouTube.

## Persyaratan

Instal semua dependensi yang diperlukan:

```bash
pip install -r requirements.txt
```

## Penggunaan

Program ini menggunakan file JSON sebagai sumber konten. Berikut adalah contoh perintah dasar:

```bash
python cli.py --json path/to/your/content.json --images path/to/images/folder
```

### Contoh File JSON

File JSON harus memiliki format array yang berisi satu atau lebih objek seperti berikut (lihat `example.json`):

```json
[
  {
    "title": "5 Fashion Tips for Men in 2024",
    "voiceover": "Here are 5 essential fashion tips every man should know in 2024. These timeless style rules will help you look your best for any occasion.",
    "description": "Discover the top 5 fashion tips for men in 2024. Follow these style guidelines to elevate your wardrobe and make a great impression wherever you go. #MensFashion #StyleTips",
    "image_prompts": [
      "Man wearing tailored suit with perfect fit",
      "Classic white shirt with quality accessories",
      "Man wearing versatile dark jeans styled properly",
      "Quality leather shoes and matching belt",
      "Minimalist watch and subtle accessories"
    ],
    "tags": [
      "mens fashion",
      "style tips",
      "fashion advice",
      "wardrobe essentials",
      "2024 trends"
    ]
  }
]
```

Field yang wajib ada:
- `title`: Judul video
- `voiceover`: Teks untuk voiceover
- `description`: Deskripsi video untuk YouTube
- `image_prompts`: Array berisi prompt untuk setiap gambar

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