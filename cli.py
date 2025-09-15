#!/usr/bin/env python
import os
import random
import pandas as pd
import csv
from gtts import gTTS
import requests
import subprocess
import shlex
import time
import json
import argparse
import sys
import shutil
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# YouTube API imports (will be installed via requirements)
try:
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    from googleapiclient.http import MediaFileUpload
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    YOUTUBE_API_AVAILABLE = True
except ImportError:
    YOUTUBE_API_AVAILABLE = False
    print("Warning: YouTube API libraries not installed. Auto-upload feature will be disabled.")
    print("Install with: pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib")

# Konfigurasi
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_FOLDER = os.path.join(SCRIPT_DIR, 'output')
TEMP_DIR = os.path.join(SCRIPT_DIR, 'temp')
IMAGE_OUTPUT_DIR = os.path.join(TEMP_DIR, 'images')

# Konfigurasi direktori

def generate_image_from_prompt(prompt: str, output_dir: str = None, count: int = 4, log_callback=print, skip_validation: bool = False):
    """
    Menghasilkan gambar dari prompt menggunakan ImageFX.
    
    Args:
        prompt (str): Prompt untuk generate gambar
        output_dir (str): Direktori output untuk menyimpan gambar
        count (int): Jumlah gambar yang akan digenerate
        log_callback: Function untuk logging
        skip_validation (bool): Jika True, lewati validasi dan gunakan placeholder image
        
    Returns:
        bool: True jika berhasil, False jika gagal
    """
    try:
        # Gunakan output_dir yang diberikan atau default ke IMAGE_OUTPUT_DIR
        if not output_dir:
            output_dir = IMAGE_OUTPUT_DIR
            
        # Pastikan direktori output ada
        os.makedirs(output_dir, exist_ok=True)
        
        # Mode pengujian dengan skip_validation
        if skip_validation:
            log_callback(f"⚠️ Mode pengujian: Melewati generate image sebenarnya untuk prompt: {prompt[:50]}...")
            
            # Cari gambar placeholder dari direktori images jika ada
            placeholder_found = False
            for root, _, files in os.walk(os.path.join(SCRIPT_DIR, 'images')):
                for file in files:
                    if file.lower().endswith(('.png', '.jpg', '.jpeg')):
                        # Salin file placeholder ke output_dir
                        src_file = os.path.join(root, file)
                        for i in range(count):
                            dst_file = os.path.join(output_dir, f"placeholder_{i+1}.jpg")
                            shutil.copy(src_file, dst_file)
                            log_callback(f"📋 Menyalin gambar placeholder ke: {dst_file}")
                        placeholder_found = True
                        break
                if placeholder_found:
                    break
            
            if placeholder_found:
                log_callback(f"✅ {count} gambar placeholder berhasil disalin ke folder: {output_dir}")
                return True
            else:
                # Jika tidak ada gambar placeholder, buat file kosong
                for i in range(count):
                    dummy_file = os.path.join(output_dir, f"dummy_{i+1}.jpg")
                    with open(dummy_file, 'w') as f:
                        f.write("Placeholder image for testing")
                    log_callback(f"📋 Membuat file dummy: {dummy_file}")
                log_callback(f"✅ {count} file dummy berhasil dibuat di folder: {output_dir}")
                return True
        
        # Mode normal dengan ImageFX
        # Ambil Google cookie dari environment variable
        google_cookie = os.environ.get("GOOGLE_COOKIE")
        if not google_cookie:
            log_callback("Error: GOOGLE_COOKIE tidak ditemukan di environment variable atau file .env")
            return False
            
        # Konfigurasi default dari environment variable atau gunakan nilai default
        model = os.getenv("DEFAULT_MODEL", "IMAGEN_3_5")
        size = os.getenv("DEFAULT_SIZE", "PORTRAIT")
        
        # Siapkan command untuk imagefx
        cmd = [
            "imagefx", "generate",
            "--prompt", prompt,
            "--cookie", google_cookie,
            "--model", model,
            "--size", size,
            "--count", str(count),
            "--dir", output_dir
        ]
        
        log_callback(f"🚀 Menjalankan generate image dengan prompt: {prompt[:50]}...")
        result = subprocess.run(cmd, check=True)
        
        if result.returncode == 0:
            log_callback(f"✅ {count} gambar berhasil digenerate, tersimpan di folder: {output_dir}")
            return True
        else:
            log_callback(f"❌ Gagal generate gambar, kode error: {result.returncode}")
            return False
            
    except subprocess.CalledProcessError as e:
        log_callback(f"Error saat menjalankan imagefx: {e}")
        return False
    except Exception as e:
        log_callback(f"Error saat generate gambar: {e}")
        return False

def generate_gtts_audio(text: str):
    """Menghasilkan file audio dari teks menggunakan Google TTS.
    
    Args:
        text (str): Teks yang akan dikonversi menjadi audio
    """
    try:
        if not os.path.exists(TEMP_DIR):
            os.makedirs(TEMP_DIR)
        temp_audio_path = os.path.join(TEMP_DIR, f"temp_audio_{random.randint(1,1000)}.mp3")
        
        tts = gTTS(text, lang='en')
        tts.save(temp_audio_path)
        
        return temp_audio_path
    except Exception as e:
        print(f"Error generating GTTs audio: {e}")
        return None

# Fungsi generate_elevenlabs_audio telah dihapus karena tidak dibutuhkan lagi
# Voice over hanya menggunakan Google Text to Speech

def run_ffmpeg_command(command: list, log_callback):
    """Menjalankan perintah ffmpeg dan mencatat lognya."""
    # Gunakan cara yang kompatibel dengan Windows dan Unix untuk menampilkan command
    if os.name == 'nt':  # Windows
        # Pada Windows, gunakan quotes sederhana untuk logging
        command_str = ' '.join(f'"{arg}"' if ' ' in arg else arg for arg in command)
    else:  # Unix/Mac
        command_str = ' '.join(shlex.quote(arg) for arg in command)
    
    log_callback(f"Menjalankan perintah FFmpeg:\n{command_str}\n")
    try:
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        stdout, stderr = process.communicate()
        if process.returncode != 0:
            log_callback(f"FFmpeg Error:\n{stderr}")
            return False
        return True
    except FileNotFoundError:
        log_callback("Error: FFmpeg tidak ditemukan. Pastikan FFmpeg terinstal dan ada di PATH sistem Anda.")
        return False

def get_audio_duration(audio_path: str) -> float:
    """Menghitung durasi audio dalam detik menggunakan ffprobe.
    
    Args:
        audio_path (str): Path ke file audio
        
    Returns:
        float: Durasi audio dalam detik, atau 0 jika error
    """
    try:
        # Gunakan normpath untuk memastikan path kompatibel dengan sistem operasi
        normalized_path = os.path.normpath(audio_path)
        command = [
            'ffprobe', '-v', 'quiet', '-show_entries', 'format=duration',
            '-of', 'csv=p=0', normalized_path
        ]
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        stdout, stderr = process.communicate()
        
        if process.returncode == 0 and stdout.strip():
            return float(stdout.strip())
        else:
            print(f"Error getting audio duration: {stderr}")
            return 0.0
    except Exception as e:
        print(f"Error in get_audio_duration: {e}")
        return 0.0

def authenticate_youtube(client_secret_path: str, token_path: str = None):
    """Autentikasi dengan YouTube API menggunakan OAuth2.
    
    Args:
        client_secret_path (str): Path ke file client_secret.json
        token_path (str): Path ke file token.json (optional)
        
    Returns:
        googleapiclient.discovery.Resource: YouTube API service object
    """
    if not YOUTUBE_API_AVAILABLE:
        raise ImportError("YouTube API libraries not installed")
    
    SCOPES = ['https://www.googleapis.com/auth/youtube.upload']
    creds = None
    
    # Load existing token if provided
    if token_path and os.path.exists(token_path):
        try:
            creds = Credentials.from_authorized_user_file(token_path, SCOPES)
        except Exception as e:
            print(f"Error loading token: {e}")
    
    # If there are no (valid) credentials available, let the user log in
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception as e:
                print(f"Error refreshing token: {e}")
                creds = None
        
        if not creds:
            if not os.path.exists(client_secret_path):
                raise FileNotFoundError(f"Client secret file not found: {client_secret_path}")
            
            flow = InstalledAppFlow.from_client_secrets_file(client_secret_path, SCOPES)
            creds = flow.run_local_server(port=0)
        
        # Save the credentials for the next run
        if token_path:
            try:
                with open(token_path, 'w') as token:
                    token.write(creds.to_json())
                print(f"Token berhasil disimpan di: {token_path}")
            except Exception as e:
                print(f"Error menyimpan token: {e}")
    
    return build('youtube', 'v3', credentials=creds)

def upload_to_youtube(youtube_service, video_path: str, title: str, description: str, tags: list, privacy_status: str, log_callback):
    """Upload video ke YouTube.
    
    Args:
        youtube_service: YouTube API service object
        video_path (str): Path ke file video
        title (str): Judul video
        description (str): Deskripsi video
        tags (list): List tags
        privacy_status (str): Status privacy (private, unlisted, public)
        log_callback: Function untuk logging
        
    Returns:
        str: Video ID jika berhasil, None jika gagal
    """
    try:
        # Siapkan body untuk request API
        snippet = {
            'title': title,
            'description': description,
            'categoryId': '22'  # People & Blogs
        }
        
        # Tambahkan tags hanya jika list tidak kosong
        if tags and len(tags) > 0:
            snippet['tags'] = tags
            
        body = {
            'snippet': snippet,
            'status': {
                'privacyStatus': privacy_status,
                'selfDeclaredMadeForKids': False
            }
        }
        
        # Create MediaFileUpload object
        media = MediaFileUpload(video_path, chunksize=-1, resumable=True, mimetype='video/mp4')
        
        log_callback(f"Memulai upload video: {title}")
        
        # Call the API's videos.insert method to create and upload the video
        insert_request = youtube_service.videos().insert(
            part=','.join(body.keys()),
            body=body,
            media_body=media
        )
        
        response = None
        error = None
        retry = 0
        
        while response is None:
            try:
                status, response = insert_request.next_chunk()
                if status:
                    progress = int(status.progress() * 100)
                    log_callback(f"Upload progress: {progress}%")
            except HttpError as e:
                if e.resp.status in [500, 502, 503, 504]:
                    error = f"A retriable HTTP error {e.resp.status} occurred: {e.content}"
                    retry += 1
                    if retry > 3:
                        log_callback(f"Upload failed after 3 retries: {error}")
                        return None
                    log_callback(f"Retrying upload... ({retry}/3)")
                    time.sleep(2 ** retry)
                else:
                    log_callback(f"A non-retriable HTTP error occurred: {e}")
                    return None
            except Exception as e:
                log_callback(f"An error occurred during upload: {e}")
                return None
        
        if response:
            video_id = response['id']
            log_callback(f"Video berhasil diupload! Video ID: {video_id}")
            log_callback(f"URL: https://www.youtube.com/watch?v={video_id}")
            return video_id
        else:
            log_callback("Upload gagal: No response received")
            return None
            
    except Exception as e:
        log_callback(f"Error uploading to YouTube: {e}")
        return None

# Fungsi delete_csv_row dihapus karena tidak digunakan dalam mode JSON

def escape_ffmpeg_text(text):
    """Escape karakter khusus untuk filter teks FFmpeg.
    
    Memastikan kompatibilitas cross-platform antara Windows dan Unix.
    """
    chars_to_escape = ["'", ":", "(", ")", "&", "[", "]", ",", ";", "?", "%", "#", "=", "$"]
    
    # Pada Windows, backslash perlu penanganan khusus
    if os.name == 'nt':
        # Escape backslash terlebih dahulu
        text = text.replace("\\", "\\\\")
    
    for char in chars_to_escape:
        text = text.replace(char, f"\\{char}")
    return text

def delete_video_file(video_path: str, log_callback):
    """Menghapus file video setelah berhasil diupload ke YouTube.
    
    Args:
        video_path (str): Path ke file video yang akan dihapus
        log_callback: Function untuk logging
        
    Returns:
        bool: True jika berhasil, False jika gagal
    """
    try:
        if os.path.exists(video_path):
            # Untuk Windows compatibility, gunakan os.path.normpath
            normalized_path = os.path.normpath(video_path)
            os.remove(normalized_path)
            log_callback(f"Video berhasil dihapus: {normalized_path}")
            return True
        else:
            log_callback(f"Warning: File video tidak ditemukan untuk dihapus: {video_path}")
            return False
            
    except Exception as e:
        log_callback(f"Error menghapus file video: {e}")
        return False

def generate_content_with_qwen(prompt_file_path: str, log_callback):
    """Menghasilkan konten untuk video menggunakan AI Qwen.
    
    Args:
        prompt_file_path (str): Path ke file prompt
        log_callback: Function untuk logging
        
    Returns:
        dict: Konten yang dihasilkan dalam format JSON, atau None jika gagal
    """
    # Pastikan direktori temp ada
    if not os.path.exists(TEMP_DIR):
        os.makedirs(TEMP_DIR)
        log_callback(f"Membuat direktori temp: {TEMP_DIR}")
    try:
        # Cek API key dari environment variable
        api_key = os.getenv("DASHSCOPE_API_KEY")
        if not api_key:
            log_callback("Error: DASHSCOPE_API_KEY tidak ditemukan di environment variable")
            return None
            
        # Baca file prompt
        with open(prompt_file_path, 'r', encoding='utf-8') as f:
            prompt_content = f.read()
            
        log_callback("Menginisialisasi OpenAI client untuk Qwen API...")
        client = OpenAI(
            api_key=api_key,
            base_url="https://dashscope-intl.aliyuncs.com/compatible-mode/v1"
        )
        
        log_callback("Mengirim permintaan ke Qwen API...")
        completion = client.chat.completions.create(
            model="qwen-plus-latest",
            messages=[
                {"role": "user", "content": prompt_content}
            ],
            temperature=0.7,  # Sedikit kreativitas untuk variasi konten
            max_tokens=1000   # Batasi panjang respons
        )
        
        # Ambil respons dari API
        response_content = completion.choices[0].message.content
        log_callback("Respons diterima dari Qwen API")
        
        # Coba parse respons sebagai JSON
        try:
            # Cari tanda kurung kurawal pertama dan terakhir untuk mengekstrak JSON
            start_idx = response_content.find('{')
            end_idx = response_content.rfind('}')
            
            if start_idx == -1 or end_idx == -1:
                log_callback("Error: Respons tidak mengandung format JSON yang valid")
                return None
                
            json_content = response_content[start_idx:end_idx+1]
            content_data = json.loads(json_content)
            
            # Validasi struktur JSON
            required_fields = ['title', 'voiceover', 'description', 'image_prompts']
            for field in required_fields:
                if field not in content_data:
                    log_callback(f"Error: Field '{field}' tidak ditemukan dalam respons JSON")
                    return None
            
            # Pastikan image_prompts adalah array dengan minimal 1 item
            if not isinstance(content_data['image_prompts'], list) or len(content_data['image_prompts']) < 1:
                log_callback("Error: Field 'image_prompts' harus berupa array dengan minimal 1 item")
                return None
                
            # Field 'tags' bersifat opsional
            if 'tags' in content_data and not isinstance(content_data['tags'], list):
                log_callback("Warning: Field 'tags' harus berupa array. Menggunakan array kosong sebagai default.")
                content_data['tags'] = []
                
            log_callback(f"Konten berhasil dihasilkan dengan judul: {content_data['title']}")
            
            # Simpan output.json di folder temp secara default
            output_json_path = os.path.join(TEMP_DIR, "output.json")
            try:
                with open(output_json_path, 'w', encoding='utf-8') as f:
                    json.dump(content_data, f, indent=2, ensure_ascii=False)
                log_callback(f"Output JSON disimpan di: {output_json_path}")
            except Exception as e:
                log_callback(f"Warning: Gagal menyimpan output JSON: {e}")
                
            return content_data
            
        except json.JSONDecodeError as e:
            log_callback(f"Error parsing JSON dari respons: {e}")
            log_callback(f"Respons mentah: {response_content}")
            return None
            
    except Exception as e:
        log_callback(f"Error menghasilkan konten dengan Qwen API: {e}")
        return None

def load_content_from_json(json_file_path: str, log_callback):
    """Membaca konten untuk video dari file JSON.
    
    Args:
        json_file_path (str): Path ke file JSON
        log_callback: Function untuk logging
        
    Returns:
        list: Daftar konten yang dibaca dari file JSON, atau None jika gagal
    """
    try:
        # Baca file JSON
        with open(json_file_path, 'r', encoding='utf-8') as f:
            content_data = json.load(f)
        
        log_callback(f"Membaca konten dari file JSON: {json_file_path}")
        
        # Periksa apakah content_data adalah list atau objek tunggal
        if isinstance(content_data, list):
            # Format array objek JSON
            log_callback(f"Format JSON: Array dengan {len(content_data)} entri")
            
            # Validasi setiap objek dalam array
            for i, item in enumerate(content_data):
                # Validasi struktur JSON untuk setiap item
                required_fields = ['title', 'voiceover', 'description', 'image_prompts']
                for field in required_fields:
                    if field not in item:
                        log_callback(f"Error: Field '{field}' tidak ditemukan dalam entri #{i+1} file JSON")
                        return None
                
                # Field 'tags' bersifat opsional dalam file JSON
                if 'tags' in item and not isinstance(item['tags'], list):
                    log_callback(f"Warning: Field 'tags' pada entri #{i+1} harus berupa array. Menggunakan array kosong sebagai default.")
                    item['tags'] = []
        else:
            # Format objek JSON tunggal (untuk kompatibilitas mundur)
            log_callback("Format JSON: Objek tunggal (bukan array)")
            
            # Validasi struktur JSON
            required_fields = ['title', 'voiceover', 'description', 'image_prompts']
            for field in required_fields:
                if field not in content_data:
                    log_callback(f"Error: Field '{field}' tidak ditemukan dalam file JSON")
                    return None
                    
            # Field 'tags' bersifat opsional dalam file JSON
            if 'tags' in content_data and not isinstance(content_data['tags'], list):
                log_callback("Warning: Field 'tags' harus berupa array. Menggunakan array kosong sebagai default.")
                content_data['tags'] = []
                
        # Validasi image_prompts
        if isinstance(content_data, list):
            # Validasi image_prompts untuk setiap item dalam array
            for i, item in enumerate(content_data):
                if not isinstance(item['image_prompts'], list) or len(item['image_prompts']) < 1:
                    log_callback(f"Error: Field 'image_prompts' pada entri #{i+1} harus berupa array dengan minimal 1 item")
                    return None
        else:
            # Validasi image_prompts untuk objek tunggal
            if not isinstance(content_data['image_prompts'], list) or len(content_data['image_prompts']) < 1:
                log_callback("Error: Field 'image_prompts' harus berupa array dengan minimal 1 item")
                return None
            
        log_callback("Konten berhasil dibaca dari file JSON")
        return content_data
        
    except json.JSONDecodeError as e:
        log_callback(f"Error parsing JSON dari file: {e}")
        return None
    except Exception as e:
        log_callback(f"Error membaca konten dari file JSON: {e}")
        return None

def process_video_entry(row, output_folder, image_duration, use_voiceover, use_dark_overlay, youtube_config, log_callback, auto_delete_enabled=False, no_zoom=False, music_folder=None, image_prompts=None, generate_images=False, skip_image_validation=False):
    """Memproses satu entri dari data JSON menjadi satu video menggunakan FFmpeg.
    
    Args:
        row: Data dalam format pandas Series yang berisi informasi video
        output_folder: Folder untuk menyimpan video hasil
        image_duration: Durasi setiap gambar dalam detik (jika tidak menggunakan voiceover)
        use_voiceover: Flag untuk menggunakan voiceover (menggunakan layanan gtts)
        use_dark_overlay: Flag untuk menambahkan overlay gelap pada gambar
        youtube_config: Konfigurasi untuk upload YouTube
        log_callback: Function untuk logging
        auto_delete_enabled: Flag untuk menghapus video setelah upload
        no_zoom: Flag untuk menonaktifkan efek zoom
        music_folder: Folder berisi file musik untuk background
        image_prompts: List prompt untuk pemilihan gambar dari file JSON
        generate_images: Flag untuk menghasilkan gambar dari image_prompts menggunakan ImageFX
        skip_image_validation: Flag untuk melewati validasi ImageFX (hanya untuk pengujian)
    """
    temp_files = []
    
    try:
        if 'title' not in row or pd.isna(row['title']) or str(row['title']).strip() == '':
            log_callback("Error: Judul video kosong atau tidak valid")
            return False
        
        if 'caption' not in row or pd.isna(row['caption']) or str(row['caption']).strip() == '':
            log_callback("Error: Teks caption kosong atau tidak valid")
            return False
        
        title = str(row['title']).replace(' ', '_').replace('/', '_').replace('\\', '_')
        log_callback(f"--- Memproses video untuk: '{row['title']}' ---")

        if not os.path.exists(TEMP_DIR):
            os.makedirs(TEMP_DIR)
        
        # Gunakan satu folder temp untuk gambar hasil generate
        images_folder = IMAGE_OUTPUT_DIR
        os.makedirs(images_folder, exist_ok=True)
        
        # Hapus semua file di folder temp/images sebelum generate baru
        log_callback("Menghapus file gambar yang ada di folder temp/images...")
        for f in os.listdir(images_folder):
            os.remove(os.path.join(images_folder, f))
        
        log_callback(f"Menggunakan folder temp untuk gambar: {images_folder}")
        
        # Ambil image_prompts dari argumen fungsi
        if not image_prompts:
            log_callback("Error: 'image_prompts' tidak tersedia.")
            return False
        
        # Generate gambar dari image_prompts jika diminta
        if generate_images:
            log_callback(f"Menggunakan {len(image_prompts)} image prompts untuk generate gambar")
            
            # Generate **satu** gambar untuk setiap prompt
            for i, prompt in enumerate(image_prompts):
                log_callback(f"Prompt {i+1}: {prompt}")
                
                # Generate gambar dari prompt dan simpan langsung di folder images_folder
                success = generate_image_from_prompt(
                    prompt=prompt,
                    output_dir=images_folder,
                    count=1,  # Mengubah count menjadi 1
                    log_callback=log_callback,
                    skip_validation=skip_image_validation
                )
                
                if not success:
                    log_callback(f"Error: Gagal generate gambar untuk prompt {i+1}. Menghentikan proses.")
                    return False
        
        # Ambil semua gambar yang tersedia di folder images_folder
        all_images = [os.path.join(images_folder, img) for img in os.listdir(images_folder) if img.lower().endswith(('.png', '.jpg', '.jpeg'))]
        
        if not all_images:
            if skip_image_validation:
                log_callback("Warning: Tidak ada gambar yang digenerate. Mencari gambar placeholder.")
                # Buat file dummy jika tidak ada gambar placeholder
                log_callback("Tidak ada gambar placeholder, membuat file dummy")
                
                # Buat minimal 5 file dummy
                dummy_files = []
                for i in range(5):
                    dummy_path = os.path.join(images_folder, f"dummy_{i+1}.jpg")
                    with open(dummy_path, "w") as f:
                        f.write("dummy image for testing")
                    dummy_files.append(dummy_path)
                    log_callback(f"Membuat file dummy: {dummy_path}")
                
                all_images = dummy_files
            else:
                log_callback("Error: Tidak ada gambar yang berhasil digenerate di folder temp.")
                return False
        
        # Pilih gambar secara acak untuk scene pertama (judul)
        title_image = random.choice(all_images)
        log_callback(f"Menggunakan gambar {os.path.basename(title_image)} untuk scene judul")
        
        # Buat salinan dari all_images untuk digunakan dalam scene-scene berikutnya
        scene_images = all_images.copy()
        random.shuffle(scene_images)
        
        # Pastikan gambar untuk judul muncul di awal, diikuti oleh gambar-gambar scene
        selected_images = [title_image] + scene_images

        audio_path = None
        if use_voiceover:
            voiceover_text = row['caption']
            # Gunakan gtts sebagai satu-satunya layanan voiceover
            audio_path = generate_gtts_audio(voiceover_text)
            
            if not audio_path:
                log_callback("Gagal membuat voiceover.")
                return False
            temp_files.append(audio_path)
            
            # Gunakan list command untuk kompatibilitas cross-platform
            ffprobe_cmd = ['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', audio_path]
            audio_duration_str = subprocess.check_output(ffprobe_cmd).strip().decode('utf-8')
            audio_duration = float(audio_duration_str) if audio_duration_str else 0
            avg_duration = audio_duration / len(selected_images) if len(selected_images) > 0 else 0
        else:
            avg_duration = image_duration

        video_clips_paths = []
        for i, img_path in enumerate(selected_images):
            clip_output = os.path.join(TEMP_DIR, f"clip_{i}.mp4")
            temp_files.append(clip_output)
            
            # Terapkan efek zoom jika tidak dinonaktifkan
            if not no_zoom:
                # Random zoom effect: zoom in (1.0 to 1.3) or zoom out (1.3 to 1.0)
                zoom_direction = random.choice(['in', 'out'])
                if zoom_direction == 'in':
                    # Zoom in: start from 1.0, gradually zoom to 1.3
                    zoom_filter = f"scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,zoompan=z='1+0.3*on/{int(avg_duration*25)}':d={int(avg_duration*25)}:s=1080x1920"
                    log_callback(f"Scene {i+1}: Menerapkan efek zoom in pada {os.path.basename(img_path)}")
                else:
                    # Zoom out: start from 1.3, gradually zoom to 1.0
                    zoom_filter = f"scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,zoompan=z='1.3-0.3*on/{int(avg_duration*25)}':d={int(avg_duration*25)}:s=1080x1920"
                    log_callback(f"Scene {i+1}: Menerapkan efek zoom out pada {os.path.basename(img_path)}")
            else:
                # Tanpa efek zoom - menggunakan crop untuk menghilangkan border hitam
                zoom_filter = f"scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920"
                log_callback(f"Scene {i+1}: Tanpa efek zoom pada {os.path.basename(img_path)}")
            
            # Tambahkan overlay gelap jika diaktifkan
            if use_dark_overlay:
                zoom_filter += ",colorize=0.3:0.3:0.3:0.3"
                log_callback(f"Scene {i+1}: Menambahkan overlay gelap")
            
            command = [
                'ffmpeg', '-loop', '1', '-i', img_path, '-vf',
                zoom_filter,
                '-t', str(avg_duration), '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-y', clip_output
            ]
            if not run_ffmpeg_command(command, log_callback): return False
            video_clips_paths.append(clip_output)
        
        concat_list_path = os.path.join(TEMP_DIR, 'concat_list.txt')
        temp_files.append(concat_list_path)
        with open(concat_list_path, 'w') as f:
            for path in video_clips_paths:
                # Gunakan normpath untuk memastikan path kompatibel dengan sistem operasi
                normalized_path = os.path.normpath(os.path.abspath(path))
                # Escape backslash untuk Windows compatibility
                if os.name == 'nt':  # Windows
                    normalized_path = normalized_path.replace('\\', '\\\\')
                f.write(f"file '{normalized_path}'\n")

        final_video_no_audio = os.path.join(TEMP_DIR, 'final_video_no_audio.mp4')
        temp_files.append(final_video_no_audio)
        command = [
            'ffmpeg', '-f', 'concat', '-safe', '0', '-i', concat_list_path, 
            '-c', 'copy', '-y', final_video_no_audio
        ]
        if not run_ffmpeg_command(command, log_callback): return False
        
        output_path = os.path.join(output_folder, f"{title}.mp4")
        
        # Pilih file musik secara acak jika folder musik disediakan
        music_path = None
        if music_folder and os.path.exists(music_folder):
            music_files = [os.path.join(music_folder, f) for f in os.listdir(music_folder) 
                          if f.lower().endswith(('.mp3', '.wav', '.m4a', '.aac'))]
            if music_files:
                music_path = random.choice(music_files)
                log_callback(f"Menggunakan musik: {os.path.basename(music_path)}")
            else:
                log_callback(f"Warning: Tidak ada file musik yang ditemukan di {music_folder}")
        
        # Tambahkan caption text jika menggunakan voiceover
        if use_voiceover and audio_path:
            # Path ke font Anton-Regular.ttf dengan kompatibilitas cross-platform
            font_path = os.path.join(SCRIPT_DIR, 'fonts', 'Anton-Regular.ttf')
            
            # Periksa keberadaan font, gunakan fallback jika tidak ada
            if not os.path.exists(font_path):
                # Coba buat direktori fonts jika belum ada
                fonts_dir = os.path.join(SCRIPT_DIR, 'fonts')
                if not os.path.exists(fonts_dir):
                    os.makedirs(fonts_dir)
                log_callback("Warning: Font Anton-Regular.ttf tidak ditemukan, menggunakan font sistem")
                # Gunakan font default sistem berdasarkan OS
                if os.name == 'nt':  # Windows
                    font_path = 'C:\\Windows\\Fonts\\Arial.ttf'
                else:  # macOS/Unix
                    font_path = '/System/Library/Fonts/Helvetica.ttc'
            
            # Bagi teks caption menjadi segmen-segmen untuk sinkronisasi
            voiceover_text = row['caption']
            words = voiceover_text.split()
            
            # Hitung durasi audio untuk timing subtitle
            audio_duration = get_audio_duration(audio_path)
            if audio_duration <= 0:
                log_callback("Error: Tidak dapat menentukan durasi audio")
                return False
            
            # Tambahkan caption ke video dengan timing sinkron
            video_with_caption = os.path.join(TEMP_DIR, f'video_with_caption_{int(time.time())}.mp4')
            temp_files.append(video_with_caption)
            
            # Gunakan normpath untuk memastikan path kompatibel dengan sistem operasi
            font_absolute_path = os.path.normpath(os.path.abspath(font_path))
            
            # Buat filter drawtext dengan timing sinkron untuk setiap segmen
            drawtext_filters = []
            words_per_second = len(words) / audio_duration if audio_duration > 0 else 1
            words_per_segment = max(8, min(15, int(words_per_second * 4)))  # 8-15 kata per segmen untuk teks lebih panjang
            
            # Mulai caption setelah judul besar (1 detik)
            current_time = 1.0
            for i in range(0, len(words), words_per_segment):
                segment_words = words[i:i + words_per_segment]
                segment_text = ' '.join(segment_words).upper()
                
                # Hapus karakter bermasalah
                segment_text = segment_text.replace("'", "").replace(":", "").replace("(", "").replace(")", "")
                
                # Implementasi text wrapping dengan line_spacing FFmpeg
                max_chars_per_line = 35  # Maksimal karakter per baris
                
                # Hitung timing untuk segmen ini
                segment_duration = len(segment_words) / words_per_second
                start_time = current_time
                end_time = min(current_time + segment_duration, audio_duration)
                
                if len(segment_text) > max_chars_per_line:
                    # Bagi teks menjadi beberapa baris
                    words_in_segment = segment_text.split()
                    lines = []
                    current_line = ""
                    
                    for word in words_in_segment:
                        if len(current_line + " " + word) <= max_chars_per_line:
                            current_line += (" " if current_line else "") + word
                        else:
                            if current_line:
                                lines.append(current_line)
                            current_line = word
                    
                    if current_line:
                        lines.append(current_line)
                    
                    # Gabungkan dengan newline dan gunakan line_spacing
                    multiline_text = "\n".join(lines)
                    # Escape karakter khusus untuk FFmpeg
                    multiline_text = escape_ffmpeg_text(multiline_text)
                    
                    # Buat filter dengan line_spacing untuk multi-baris dan margin horizontal
                    margin_horizontal = 40  # Margin kiri dan kanan 40px
                    # Posisi x dengan margin: center dalam area yang tersisa setelah dikurangi margin
                    x_position = f"({margin_horizontal}+(w-{margin_horizontal*2}-text_w)/2)"
                    drawtext_filter = f"drawtext=fontfile='{font_absolute_path}':text='{multiline_text}':fontcolor=yellow:fontsize=70:x={x_position}:y=(h-text_h)/2:line_spacing=10:text_align=center:borderw=3:bordercolor=black:enable='between(t,{start_time:.2f},{end_time:.2f})'"
                    drawtext_filters.append(drawtext_filter)
                else:
                    # Teks pendek, gunakan satu filter saja dengan margin horizontal
                    margin_horizontal = 40  # Margin kiri dan kanan 40px
                    # Posisi x dengan margin: center dalam area yang tersisa setelah dikurangi margin
                    x_position = f"({margin_horizontal}+(w-{margin_horizontal*2}-text_w)/2)"
                    # Escape karakter khusus untuk FFmpeg
                    segment_text = escape_ffmpeg_text(segment_text)
                    drawtext_filter = f"drawtext=fontfile='{font_absolute_path}':text='{segment_text}':fontcolor=yellow:fontsize=70:x={x_position}:y=(h-text_h)/2:text_align=center:borderw=3:bordercolor=black:enable='between(t,{start_time:.2f},{end_time:.2f})'"
                    drawtext_filters.append(drawtext_filter)
                
                current_time = end_time
            
            # Tambahkan filter untuk judul besar di awal video (1 detik)
            title_text = row['title'].upper()
            # Escape karakter khusus untuk FFmpeg
            title_text = escape_ffmpeg_text(title_text)
            
            # Bagi judul menjadi beberapa baris jika terlalu panjang
            max_chars_per_line = 15
            words = title_text.split()
            lines = []
            current_line = ""
            
            for word in words:
                if len(current_line) + len(word) + 1 <= max_chars_per_line:
                    if current_line:
                        current_line += " " + word
                    else:
                        current_line = word
                else:
                    lines.append(current_line)
                    current_line = word
            
            if current_line:
                lines.append(current_line)
            
            # Gabungkan baris dengan newline untuk FFmpeg
            multiline_title = "\n".join(lines)
            
            # Atur ukuran font untuk judul (lebih besar dari sebelumnya)
            title_font_size = 130 if len(lines) > 1 else 150
            
            title_filter = f"drawtext=fontfile='{font_absolute_path}':text='{multiline_title}':fontcolor=yellow:fontsize={title_font_size}:x=(w-text_w)/2:y=(h-text_h)/2:text_align=center:borderw=5:bordercolor=black:enable='between(t,0,0.75)'"
            
            # Gabungkan semua filter drawtext
            combined_filter = ','.join([title_filter] + drawtext_filters)
            
            command = [
                'ffmpeg', '-i', final_video_no_audio,
                '-vf', combined_filter,
                '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-y', video_with_caption
            ]
            if not run_ffmpeg_command(command, log_callback): return False
            
            # Gabungkan dengan audio (delay audio 0.75 detik untuk menunggu judul besar selesai)
            if music_path:
                # Jika ada musik, gabungkan voiceover dan musik
                log_callback("Menggabungkan video dengan voiceover dan musik background")
                # Buat file audio sementara dengan voiceover dan musik
                mixed_audio = os.path.join(TEMP_DIR, f'mixed_audio_{int(time.time())}.aac')
                temp_files.append(mixed_audio)
                
                # Gabungkan voiceover (dengan delay) dan musik (dengan volume lebih rendah)
                command = [
                    'ffmpeg', '-i', audio_path, '-i', music_path,
                    '-filter_complex', 'adelay=750|750[voice];[1:a]volume=0.3[music];[voice][music]amix=inputs=2:duration=longest',
                    '-c:a', 'aac', '-b:a', '192k', '-y', mixed_audio
                ]
                if not run_ffmpeg_command(command, log_callback): return False
                
                # Gabungkan video dengan audio campuran
                command = [
                    'ffmpeg', '-i', video_with_caption, '-i', mixed_audio,
                    '-c:v', 'copy', '-c:a', 'copy', '-map', '0:v:0', '-map', '1:a:0',
                    '-shortest', '-y', output_path
                ]
                if not run_ffmpeg_command(command, log_callback): return False
            else:
                # Hanya voiceover tanpa musik
                command = [
                    'ffmpeg', '-i', video_with_caption, '-i', audio_path, 
                    '-c:v', 'copy', '-c:a', 'aac', '-map', '0:v:0', '-map', '1:a:0',
                    '-af', 'adelay=750|750', '-y', output_path
                ]
                if not run_ffmpeg_command(command, log_callback): return False
        else:
            # Tambahkan judul besar di awal video meskipun tidak menggunakan voiceover
            font_path = os.path.join(SCRIPT_DIR, 'fonts', 'Anton-Regular.ttf')
            
            # Periksa keberadaan font, gunakan fallback jika tidak ada
            if not os.path.exists(font_path):
                # Coba buat direktori fonts jika belum ada
                fonts_dir = os.path.join(SCRIPT_DIR, 'fonts')
                if not os.path.exists(fonts_dir):
                    os.makedirs(fonts_dir)
                log_callback("Warning: Font Anton-Regular.ttf tidak ditemukan, menggunakan font sistem")
                # Gunakan font default sistem berdasarkan OS
                if os.name == 'nt':  # Windows
                    font_path = 'C:\\Windows\\Fonts\\Arial.ttf'
                else:  # macOS/Unix
                    font_path = '/System/Library/Fonts/Helvetica.ttc'
            
            # Gunakan normpath untuk memastikan path kompatibel dengan sistem operasi
            font_absolute_path = os.path.normpath(os.path.abspath(font_path))
            
            # Siapkan teks judul
            title_text = row['title'].upper()
            # Escape karakter khusus untuk FFmpeg
            title_text = escape_ffmpeg_text(title_text)
            
            # Bagi judul menjadi beberapa baris jika terlalu panjang
            max_chars_per_line = 15
            words = title_text.split()
            lines = []
            current_line = ""
            
            for word in words:
                if len(current_line) + len(word) + 1 <= max_chars_per_line:
                    if current_line:
                        current_line += " " + word
                    else:
                        current_line = word
                else:
                    lines.append(current_line)
                    current_line = word
            
            if current_line:
                lines.append(current_line)
            
            # Gabungkan baris dengan newline untuk FFmpeg
            multiline_title = "\n".join(lines)
            
            # Atur ukuran font untuk judul (lebih besar dari sebelumnya)
            title_font_size = 130 if len(lines) > 1 else 150
            
            # Buat filter untuk judul besar di awal video (0.75 detik pertama)
            title_filter = f"drawtext=fontfile='{font_absolute_path}':text='{multiline_title}':fontcolor=yellow:fontsize={title_font_size}:x=(w-text_w)/2:y=(h-text_h)/2:text_align=center:borderw=5:bordercolor=black:enable='between(t,0,0.75)'"
            
            video_with_title = os.path.join(TEMP_DIR, f'video_with_title_{int(time.time())}.mp4')
            temp_files.append(video_with_title)
            
            # Tambahkan judul ke video
            command = [
                'ffmpeg', '-i', final_video_no_audio,
                '-vf', title_filter,
                '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-y', video_with_title
            ]
            if not run_ffmpeg_command(command, log_callback): return False
            
            # Tambahkan musik jika ada
            if music_path:
                log_callback("Menambahkan musik background ke video")
                command = [
                    'ffmpeg', '-i', video_with_title, '-i', music_path,
                    '-c:v', 'copy', '-c:a', 'aac', '-map', '0:v:0', '-map', '1:a:0',
                    '-shortest', '-af', 'volume=0.3', '-y', output_path
                ]
                if not run_ffmpeg_command(command, log_callback): return False
            else:
                # Tanpa musik, gunakan video dengan judul saja
                command = ['ffmpeg', '-i', video_with_title, '-c:v', 'copy', '-y', output_path]
                if not run_ffmpeg_command(command, log_callback): return False

        log_callback(f"Video berhasil disimpan di: {output_path}")
        
        # Upload ke YouTube jika diaktifkan
        if youtube_config and youtube_config.get('enabled', False):
            try:
                log_callback("Memulai proses upload ke YouTube...")
                
                # Autentikasi YouTube
                youtube_service = authenticate_youtube(
                    youtube_config['client_secret_path'],
                    youtube_config.get('token_path')
                )
                
                # Siapkan metadata video
                video_title = youtube_config['title_template'].format(title=row['title'])
                # Gunakan template description dengan data dari CSV
                if 'description' in row and pd.notna(row['description']) and str(row['description']).strip():
                    video_description = youtube_config['description'].format(description=row['description'])
                else:
                    # Fallback jika tidak ada kolom description di CSV
                    video_description = youtube_config['description'].replace('{description}', 'Generated by AI Video Short Generator')
                
                # Gunakan tags dari content_data jika ada (mode JSON), jika tidak gunakan dari youtube_config
                if 'content_tags' in youtube_config and youtube_config['content_tags']:
                    video_tags = youtube_config['content_tags']
                    log_callback(f"Menggunakan tags dari file JSON: {video_tags}")
                else:
                    video_tags = [tag.strip() for tag in youtube_config['tags'].split(',') if tag.strip()]
                    log_callback(f"Menggunakan tags dari konfigurasi YouTube: {video_tags}")
                
                privacy_status = youtube_config['privacy']
                
                # Upload video
                video_id = upload_to_youtube(
                    youtube_service,
                    output_path,
                    video_title,
                    video_description,
                    video_tags,
                    privacy_status,
                    log_callback
                )
                
                if video_id:
                    log_callback(f"Video berhasil diupload ke YouTube dengan ID: {video_id}")
                    
                    # Auto-delete jika diaktifkan
                    if auto_delete_enabled:
                        log_callback("Auto-delete diaktifkan, menghapus file...")
                        
                        # Hapus file video
                        if delete_video_file(output_path, log_callback):
                            log_callback("File video berhasil dihapus")
                        else:
                            log_callback("Gagal menghapus file video")
                            
                        # Hapus file gambar di folder temp/images
                        if os.path.exists(IMAGE_OUTPUT_DIR):
                            log_callback("Menghapus file gambar di folder temp/images...")
                            for f in os.listdir(IMAGE_OUTPUT_DIR):
                                try:
                                    os.remove(os.path.join(IMAGE_OUTPUT_DIR, f))
                                except Exception as e:
                                    log_callback(f"Gagal menghapus file gambar {f}: {e}")
                            log_callback("File gambar berhasil dihapus")
                            
                        # Hapus file JSON di folder temp
                        output_json_path = os.path.join(TEMP_DIR, "output.json")
                        if os.path.exists(output_json_path):
                            try:
                                os.remove(output_json_path)
                                log_callback("File JSON berhasil dihapus")
                            except Exception as e:
                                log_callback(f"Gagal menghapus file JSON: {e}")

                else:
                    log_callback("Upload ke YouTube gagal")
                    
            except Exception as e:
                log_callback(f"Error saat upload ke YouTube: {e}")
        
        return True

    except Exception as e:
        log_callback(f"Error dalam proses: {e}")
        return False
    finally:
        for f in temp_files:
            if os.path.exists(f):
                os.remove(f)

# Fungsi untuk logging ke konsol
def console_log(message):
    print(message)

def main():
    # Inisialisasi counter untuk tracking hasil
    completed_count = 0
    error_count = 0
    
    # Buat parser argumen command line
    parser = argparse.ArgumentParser(description='AI Video Short Generator CLI')
    
    # Grup argumen untuk sumber data (JSON atau generate dengan Qwen)
    data_group = parser.add_mutually_exclusive_group(required=True)
    data_group.add_argument('--json', help='Path ke file JSON data yang sudah ada')
    data_group.add_argument('--generate', action='store_true', help='Generate konten baru menggunakan AI Qwen')
    parser.add_argument('--prompt', help='Path ke file prompt untuk AI Qwen (diperlukan jika --generate digunakan)')
    parser.add_argument('--output-json', help='Path untuk menyimpan hasil generate JSON (opsional, hanya berlaku jika --generate digunakan)')
    
    # Argumen gambar
    
    # Argumen opsional
    parser.add_argument('--output', default=OUTPUT_FOLDER, help=f'Path ke folder output (default: {OUTPUT_FOLDER})')
    parser.add_argument('--duration', type=int, default=3, help='Durasi gambar dalam detik (default: 3)')
    parser.add_argument('--dark-overlay', action='store_true', help='Gunakan overlay gelap pada gambar')
    parser.add_argument('--no-zoom', action='store_true', help='Nonaktifkan efek zoom pada gambar')
    parser.add_argument('--generate-images', action='store_true', help='Generate gambar dari image_prompts menggunakan ImageFX (wajib diaktifkan)')
    parser.add_argument('--skip-image-validation', action='store_true', help='Lewati validasi ImageFX (hanya untuk pengujian)')
    
    # Argumen voiceover
    parser.add_argument('--voiceover', action='store_true', help='Gunakan voiceover (menggunakan layanan gtts)')
    
    # Argumen musik
    parser.add_argument('--music', help='Folder berisi file musik untuk background (opsional)')
    
    # Argumen YouTube
    parser.add_argument('--youtube', action='store_true', help='Upload ke YouTube setelah pembuatan video')
    parser.add_argument('--client-secret', help='Path ke file client_secret.json untuk YouTube API')
    parser.add_argument('--token', help='Path ke file token.json untuk YouTube API (opsional)')
    parser.add_argument('--title-template', default='{title}', help='Template judul untuk YouTube (default: {title})')
    parser.add_argument('--description', default='{description}', help='Template deskripsi untuk YouTube (default: {description})')
    parser.add_argument('--tags', default='', help='Tags untuk YouTube, dipisahkan dengan koma')
    parser.add_argument('--privacy', choices=['private', 'unlisted', 'public'], default='private', help='Status privasi YouTube (default: private)')
    parser.add_argument('--auto-delete', action='store_true', help='Hapus video setelah berhasil diupload ke YouTube')
    
    # Argumen untuk membatasi jumlah data yang diproses
    parser.add_argument('--limit', type=int, help='Batasi jumlah data yang diproses dari file JSON')
    
    args = parser.parse_args()
    
    # Validasi argumen umum
    if not args.generate_images:
        print("Error: Anda harus mengaktifkan --generate-images untuk menghasilkan gambar dari prompt")
        print("Gunakan: python cli.py --generate --prompt <file_prompt> --generate-images --output-json <path_output> [--voiceover]")
        return 1
        
    # Validasi GOOGLE_COOKIE untuk generate_images
    if args.generate_images and not os.getenv("GOOGLE_COOKIE") and not args.skip_image_validation:
        print("Error: GOOGLE_COOKIE tidak ditemukan di environment variable")
        print("Tambahkan GOOGLE_COOKIE=<nilai_cookie> ke file .env atau environment variable")
        print("Atau gunakan --skip-image-validation untuk melewati validasi ini (hanya untuk pengujian)")
        return 1
        
    # Validasi command imagefx tersedia
    if args.generate_images and not args.skip_image_validation:
        try:
            subprocess.run(["imagefx", "--version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        except FileNotFoundError:
            print("Error: Command 'imagefx' tidak ditemukan di sistem")
            print("Pastikan imagefx sudah terinstal dan tersedia di PATH")
            print("Atau gunakan --skip-image-validation untuk melewati validasi ini (hanya untuk pengujian)")
            return 1
        
    # Validasi argumen prompt untuk mode generate
    if args.generate and not args.prompt:
        print("Error: Anda harus menyediakan file prompt dengan --prompt ketika menggunakan --generate")
        print("Gunakan: python cli.py --generate --prompt <file_prompt> --generate-images --output-json <path_output> [--voiceover]")
        return 1
        
    # Validasi keberadaan file prompt
    if args.prompt and not os.path.exists(args.prompt):
        print(f"Error: File prompt tidak ditemukan: {args.prompt}")
        return 1
        
    
    if args.music and not os.path.exists(args.music):
        print(f"Error: Folder musik tidak ditemukan: {args.music}")
        return 1
    
    # Validasi ElevenLabs telah dihapus karena tidak digunakan lagi
    
    if args.youtube and not args.client_secret:
        print("Error: Client Secret JSON diperlukan untuk upload YouTube")
        return 1
    
    # Pastikan direktori output ada
    if not os.path.exists(args.output):
        os.makedirs(args.output)
        print(f"Folder output dibuat: {args.output}")
        
    # Pastikan direktori temp ada
    if not os.path.exists(TEMP_DIR):
        os.makedirs(TEMP_DIR)
        print(f"Folder temp dibuat: {TEMP_DIR}")
        
    # Pastikan direktori temp/images ada untuk gambar hasil generate
    temp_images_dir = IMAGE_OUTPUT_DIR
    if not os.path.exists(temp_images_dir):
        os.makedirs(temp_images_dir)
        print(f"Folder untuk gambar hasil generate dibuat: {temp_images_dir}")
    
    # Validasi argumen khusus untuk mode JSON
    if args.json:
        if not os.path.exists(args.json):
            print(f"Error: File JSON tidak ditemukan: {args.json}")
            return 1
    # Validasi argumen khusus untuk mode generate dengan Qwen
    elif args.generate:
        if not args.prompt:
            print("Error: File prompt (--prompt) diperlukan saat menggunakan opsi --generate")
            return 1
        if not os.path.exists(args.prompt):
            print(f"Error: File prompt tidak ditemukan: {args.prompt}")
            return 1
        if not os.getenv("DASHSCOPE_API_KEY"):
            print("Error: DASHSCOPE_API_KEY tidak ditemukan")
            print("Silakan tambahkan DASHSCOPE_API_KEY=<your_api_key> ke file .env di direktori project")
            print("atau set dengan: export DASHSCOPE_API_KEY=<your_api_key>")
            return 1
    
    # Siapkan konfigurasi YouTube jika diaktifkan
    youtube_config = None
    if args.youtube:
        if not YOUTUBE_API_AVAILABLE:
            print("Warning: YouTube API libraries tidak terinstall. Auto-upload dinonaktifkan.")
            print("Install dengan: pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib")
        else:
            # Auto-generate token path if not provided
            token_path = args.token
            if not token_path:
                # Create token.json in same directory as client_secret.json
                client_secret_dir = os.path.dirname(args.client_secret)
                token_path = os.path.join(client_secret_dir, 'token.json')
            
            youtube_config = {
                'enabled': True,
                'client_secret_path': args.client_secret,
                'token_path': token_path,
                'title_template': args.title_template,
                'description': args.description,
                'tags': args.tags,
                'privacy': args.privacy
            }
            print("Auto-upload YouTube diaktifkan")
            print(f"Token akan disimpan di: {token_path}")
    
    # Proses video dari file JSON atau generate dengan Qwen
    completed_count = 0
    error_count = 0
    
    # Tentukan sumber konten (file JSON atau generate dengan Qwen)
    if args.json:
        print(f"Menggunakan file JSON sebagai sumber konten: {args.json}")
        # Baca konten dari file JSON
        content_data_list = load_content_from_json(args.json, console_log)
    elif args.generate:
        print(f"Menggunakan AI Qwen untuk generate konten dari prompt: {args.prompt}")
        # Generate konten dengan Qwen
        content_data_list = generate_content_with_qwen(args.prompt, console_log)
        
        # Simpan hasil generate ke file JSON jika diminta
        # Pindahkan kode ini ke setelah generate konten tambahan (jika ada limit)
        # untuk memastikan semua konten yang digenerate tersimpan
    else:
        # Seharusnya tidak terjadi karena argumen grup bersifat required=True
        print("Error: Tidak ada sumber konten yang ditentukan (--json atau --generate)")
        return 1
    
    if not content_data_list:
        print("Error: Gagal membaca konten dari file JSON")
        return 1
    
    # Pastikan content_data_list adalah list
    if not isinstance(content_data_list, list):
        content_data_list = [content_data_list]
    
    # Terapkan batasan jumlah data jika opsi --limit digunakan
    original_count = len(content_data_list)
    
    # Jika menggunakan mode generate dan ada limit, generate konten sebanyak limit
    if args.generate and args.limit and args.limit > 0:
        # Jika sudah ada konten dari generate sebelumnya, gunakan sebagai konten awal
        generated_content = content_data_list[0] if content_data_list else None
        
        # Generate konten tambahan jika jumlah kurang dari limit
        # Tambahkan buffer untuk mengantisipasi kegagalan pemrosesan
        target_generate = args.limit
        max_attempts = max(10, target_generate * 2)  # Maksimal 2x limit atau minimal 10 percobaan
        attempts = 0
        
        while len(content_data_list) < target_generate and attempts < max_attempts:
            attempts += 1
            print(f"\nMengenerate konten tambahan ({len(content_data_list)+1}/{target_generate})...")
            new_content = generate_content_with_qwen(args.prompt, console_log)
            if new_content:
                content_data_list.append(new_content)
            else:
                print(f"Gagal generate konten tambahan (percobaan {attempts}/{max_attempts})")
                if attempts >= max_attempts:
                    print("Mencapai batas maksimum percobaan, melanjutkan dengan konten yang sudah ada")
                    break
                
        print(f"Berhasil generate {len(content_data_list)} konten dari target {target_generate}")
    # Untuk mode JSON, batasi jumlah data yang diproses
    elif args.limit and args.limit > 0 and args.limit < len(content_data_list):
        content_data_list = content_data_list[:args.limit]
        print(f"Membatasi pemrosesan hanya untuk {args.limit} dari {original_count} entri video dalam file JSON")
    else:
        print(f"Ditemukan {len(content_data_list)} entri video dalam file JSON")
        
    # Simpan hasil generate ke file JSON jika diminta (setelah semua konten digenerate)
    if args.generate and args.output_json:
        output_dir = os.path.dirname(args.output_json)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)
            
        with open(args.output_json, 'w', encoding='utf-8') as f:
            json.dump(content_data_list, f, indent=2, ensure_ascii=False)
        print(f"Hasil generate disimpan ke: {args.output_json}")
    
    # Proses setiap entri dalam file JSON
    success_count = 0  # Hitung berapa video yang berhasil diproses
    target_count = args.limit if args.limit and args.limit > 0 else len(content_data_list)
    
    for index, content_data in enumerate(content_data_list):
        # Jika sudah mencapai target jumlah video yang berhasil, hentikan proses
        if success_count >= target_count:
            print(f"\nTarget {target_count} video berhasil tercapai. Menghentikan proses.")
            break
            
        print(f"\nMemproses entri #{index+1}: {content_data.get('title', 'Tanpa judul')}")
        
        # Konversi konten menjadi format yang kompatibel dengan process_video_entry
        row = pd.Series({
            'title': content_data['title'],
            'caption': content_data['voiceover'],
            'description': content_data['description']
            # Tidak perlu memasukkan image_prompts ke Series untuk menghindari konflik
        })
        
        # Gunakan image_prompts langsung dari content_data
        image_prompts = content_data['image_prompts']
        
        # Tambahkan tags jika ada dalam content_data, jika tidak gunakan list kosong
        # Ini akan digunakan nanti dalam proses upload YouTube
        tags = content_data.get('tags', [])
        
        # Tambahkan tags ke youtube_config jika ada
        if youtube_config and tags:
            youtube_config_copy = youtube_config.copy()
            youtube_config_copy['content_tags'] = tags
        else:
            youtube_config_copy = youtube_config
        
        # Proses video
        result = process_video_entry(
            row,
            args.output,
            args.duration,
            args.voiceover,
            args.dark_overlay,
            youtube_config_copy,
            console_log,
            auto_delete_enabled=args.auto_delete,
            no_zoom=args.no_zoom,
            music_folder=args.music,
            image_prompts=image_prompts,
            generate_images=args.generate_images,
            skip_image_validation=args.skip_image_validation if hasattr(args, 'skip_image_validation') else False
        )
        
        if result:
            completed_count += 1
            success_count += 1
            print(f"Video #{index+1} berhasil diproses. ({success_count}/{target_count})")
        else:
            error_count += 1
            print(f"Video #{index+1} gagal diproses.")

    print(f"\nProses selesai. {completed_count} video berhasil, {error_count} error.")
    return 0

if __name__ == '__main__':
    sys.exit(main())