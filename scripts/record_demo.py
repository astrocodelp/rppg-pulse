"""Record the demo video: screen capture of the Gradio app working end to
end (Playwright video recording), >= 60 s, with real interaction:
landing -> live-webcam tab -> upload tab -> sample synthetic video ->
Estimate pulse -> result -> scroll through table -> phone-sized view.

Output: verify/demo_raw.webm, then stitched with title/end cards to
demo_video/rppg_pulse_demo.mp4 (>= 60 s, H.264, silent).
"""
import sys, time, shutil, subprocess
from pathlib import Path
from playwright.sync_api import sync_playwright
import imageio_ffmpeg

BASE = "http://127.0.0.1:7860"
ROOT = Path(__file__).resolve().parent.parent
SAMPLE = str((ROOT / "assets/sample_face_72bpm.mp4").resolve())
REC = ROOT / "verify" / "rec"
REC.mkdir(parents=True, exist_ok=True)

with sync_playwright() as p:
    exe = str(Path.home() / ".cache/ms-playwright/chromium-1247/chrome-linux64/chrome")
    browser = p.chromium.launch(executable_path=exe)
    ctx = browser.new_context(viewport={"width": 1280, "height": 800},
                              record_video_dir=str(REC),
                              record_video_size={"width": 1280, "height": 800})
    page = ctx.new_page()
    page.goto(BASE, wait_until="domcontentloaded", timeout=60000)
    page.get_by_role("tab", name="Upload a video").wait_for(timeout=60000)
    page.wait_for_timeout(6000)   # landing: title + disclaimer readable
    page.mouse.wheel(0, 200); page.wait_for_timeout(3000)
    page.mouse.wheel(0, -200); page.wait_for_timeout(2000)
    # live webcam tab (no camera on this machine -> shows waiting state)
    page.get_by_role("tab", name="Live webcam").click()
    page.wait_for_timeout(6000)
    # upload tab
    page.get_by_role("tab", name="Upload a video").click()
    page.wait_for_timeout(4000)
    # choose the bundled example (a stranger's no-webcam path)
    ex = page.locator(".gallery-item, table.examples button, .examples img, .examples button").first
    try:
        ex.click(timeout=5000)
    except Exception:
        page.locator("input[type=file]").first.set_input_files(SAMPLE)
    page.wait_for_timeout(6000)
    page.get_by_role("button", name="Estimate pulse").click()
    # wait for result
    for _ in range(45):
        page.wait_for_timeout(1000)
        body = page.locator("body").inner_text()
        if "BPM" in body and "windows answered" in body:
            break
    page.wait_for_timeout(8000)   # hold on result so judges can read it
    page.mouse.wheel(0, 300); page.wait_for_timeout(5000)
    page.mouse.wheel(0, -300); page.wait_for_timeout(3000)
    # phone-sized view of the same app
    page.set_viewport_size({"width": 390, "height": 800})
    page.wait_for_timeout(6000)
    page.get_by_role("tab", name="Upload a video").click()
    page.wait_for_timeout(5000)
    page.set_viewport_size({"width": 1280, "height": 800})
    page.wait_for_timeout(4000)
    video_path = page.video.path()
    ctx.close()   # flush video
    browser.close()

raw = Path(video_path)
print("raw recording:", raw, raw.stat().st_size)
shutil.copy(raw, ROOT / "verify/demo_raw.webm")

import subprocess as sp
sp.run(["python3", str(ROOT / "scripts/stitch_demo.py")], check=True)
