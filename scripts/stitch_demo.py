"""Stitch the recorded demo (verify/demo_raw.webm) into
demo_video/rppg_pulse_demo.mp4 with Pillow-rendered title/end cards."""
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
import subprocess
import imageio_ffmpeg

ROOT = Path(__file__).resolve().parent.parent
font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"


def card(lines, name):
    img = Image.new("RGB", (1280, 800), (14, 22, 38))
    d = ImageDraw.Draw(img)
    f1 = ImageFont.truetype(font_path, 46)
    f2 = ImageFont.truetype(font_path, 30)
    y = 400 - 40 * len(lines)
    for txt, small in lines:
        f = f2 if small else f1
        w = d.textlength(txt, font=f)
        d.text(((1280 - w) / 2, y), txt, font=f, fill=(240, 244, 250))
        y += 70
    img.save(ROOT / f"verify/{name}.png")


card([("rppg-pulse", False),
      ("Camera-based pulse estimation", True),
      ("Wellness demo - NOT a medical device", True)], "card_title")
card([("Frozen held-out test (21 subjects)", False),
      ("MAE 10.96 BPM (95% CI 4.68-19.65)", True),
      ("Pre-registered target <=5 BPM: not met - see README", True),
      ("Protocol, figures, limits: github.com/astrocodelp/rppg-pulse", True)],
     "card_end")
print("cards ok")

ff = imageio_ffmpeg.get_ffmpeg_exe()
V = ROOT / "verify"
for name, secs in (("card_title", 4), ("card_end", 6)):
    subprocess.run([ff, "-y", "-loglevel", "error", "-loop", "1",
                    "-i", str(V / f"{name}.png"), "-t", str(secs), "-r", "30",
                    "-vf", "scale=1280:800", "-c:v", "libx264",
                    "-pix_fmt", "yuv420p", str(V / f"{name}.mp4")], check=True)
subprocess.run([ff, "-y", "-loglevel", "error", "-i", str(V / "demo_raw.webm"),
                "-vf", "scale=1280:800,fps=30", "-c:v", "libx264",
                "-pix_fmt", "yuv420p", "-crf", "20", str(V / "demo_mid.mp4")],
               check=True)
(V / "concat.txt").write_text(
    "file 'card_title.mp4'\nfile 'demo_mid.mp4'\nfile 'card_end.mp4'\n")
out_dir = ROOT / "demo_video"
out_dir.mkdir(exist_ok=True)
out = out_dir / "rppg_pulse_demo.mp4"
subprocess.run([ff, "-y", "-loglevel", "error", "-f", "concat", "-safe", "0",
                "-i", str(V / "concat.txt"), "-c:v", "libx264",
                "-pix_fmt", "yuv420p", "-crf", "20", str(out)], check=True)
pr = subprocess.run([ff, "-i", str(out)], capture_output=True, text=True)
print([l for l in pr.stderr.splitlines() if "Duration" in l or "Stream" in l])
print("size", out.stat().st_size)
