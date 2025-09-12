import subprocess
import os
from dotenv import load_dotenv

load_dotenv()

google_cookie = os.getenv("GOOGLE_COOKIE")
if not google_cookie:
    raise EnvironmentError("GOOGLE_COOKIE tidak ditemukan di .env")

model = os.getenv("DEFAULT_MODEL", "IMAGEN_3_5")
size = os.getenv("DEFAULT_SIZE", "PORTRAIT")
output_dir = "outputs"
count = int(os.getenv("DEFAULT_COUNT", 4))  # default 4 jika tidak di .env

os.makedirs(output_dir, exist_ok=True)

with open("prompt2.txt", "r", encoding="utf-8") as f:
    prompt = f.read().strip()

cmd = [
    "imagefx", "generate",
    "--prompt", prompt,
    "--cookie", google_cookie,
    "--model", model,
    "--size", size,
    "--count", str(count),
    "--dir", output_dir
]

print("🚀 Running")
subprocess.run(cmd, check=True)
print(f"✅ {count} gambar berhasil digenerate, cek folder: {output_dir}")
