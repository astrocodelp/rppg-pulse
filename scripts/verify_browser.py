"""Browser verification of the Gradio demo with Playwright (Chromium).

Checks desktop + 320px phone layout, keyboard focus visibility, the upload
flow end to end with the synthetic 72 BPM face video, screenshots saved
under verify/. Exits non-zero on any failed check.
"""
import sys, time, json
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:7860"
OUT = Path("verify"); OUT.mkdir(exist_ok=True)
SAMPLE = str(Path("assets/sample_face_72bpm.mp4").resolve())
results = []

def check(name, ok, detail=""):
    results.append((name, bool(ok), detail))
    print(("PASS" if ok else "FAIL"), name, detail)

with sync_playwright() as p:
    import os
    exe = os.path.expanduser("~/.cache/ms-playwright/chromium-1247/chrome-linux64/chrome")
    browser = p.chromium.launch(executable_path=exe)
    # ---------- desktop ----------
    page = browser.new_page(viewport={"width": 1280, "height": 900})
    errs = []
    page.on("pageerror", lambda e: errs.append(str(e)))
    page.goto(BASE, wait_until="load", timeout=60000)
    page.wait_for_timeout(4000)
    check("title", "rppg-pulse" in page.title(), page.title())
    check("h1 present", page.locator("h1").count() >= 1)
    check("disclaimer visible", page.get_by_text("not a medical device").first.is_visible())
    # tabs are buttons
    upload_tab = page.get_by_role("tab", name="Upload a video")
    check("upload tab is role=tab", upload_tab.count() == 1)
    upload_tab.click()
    page.wait_for_timeout(800)
    file_input = page.locator('input[type=file][accept*="video"]').first
    file_input.set_input_files(SAMPLE)
    page.wait_for_timeout(2500)
    page.get_by_role("button", name="Estimate pulse").click()
    # wait for result (analysis ~10-20 s CPU)
    got = None
    for _ in range(60):
        page.wait_for_timeout(1000)
        body = page.locator("body").inner_text()
        if "BPM" in body and "Median" in body:
            got = body; break
        if "No estimate" in body and "windows answered" not in body and "quality gate" in body:
            got = body; break
    check("upload flow produced result", got is not None)
    if got:
        import re
        m = re.search(r"(\d+)\s*BPM", got)
        bpm = int(m.group(1)) if m else None
        check("estimate near injected 72 BPM (±6)", bpm is not None and abs(bpm - 72) <= 6, f"got {bpm}")
        check("windows answered line", "windows answered" in got)
    check("no JS page errors", len(errs) == 0, "; ".join(errs[:3]))
    page.screenshot(path=str(OUT / "desktop_upload_result.png"), full_page=True)
    # keyboard focus visibility: tab through first controls
    page.keyboard.press("Tab")
    focus_info = page.evaluate("""() => {
        const el = document.activeElement;
        if (!el || el === document.body) return null;
        const s = getComputedStyle(el);
        return {tag: el.tagName, outline: s.outlineStyle + ' ' + s.outlineWidth, text: (el.innerText||el.ariaLabel||'').slice(0,40)};
    }""")
    check("first Tab lands on a control", focus_info is not None, str(focus_info))
    # contrast check on disclaimer colours (computed)
    disc = page.locator(".disclaimer").first
    colors = disc.evaluate("""el => {const s=getComputedStyle(el);return {fg:s.color,bg:s.backgroundColor};}""")
    def lum(rgb):
        import re
        vals = [int(v)/255 for v in re.findall(r"\d+", rgb)[:3]]
        vals = [v/12.92 if v <= 0.03928 else ((v+0.055)/1.055)**2.4 for v in vals]
        return 0.2126*vals[0]+0.7152*vals[1]+0.0722*vals[2]
    l1, l2 = lum(colors["fg"]), lum(colors["bg"])
    ratio = (max(l1,l2)+0.05)/(min(l1,l2)+0.05)
    check("disclaimer contrast >= 4.5", ratio >= 4.5, f"{ratio:.2f}:1")
    # ---------- phone 320px ----------
    phone = browser.new_page(viewport={"width": 320, "height": 640},
                             is_mobile=True, has_touch=True,
                             user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15")
    phone.goto(BASE, wait_until="load", timeout=60000)
    phone.wait_for_timeout(4000)
    scrollw = phone.evaluate("document.documentElement.scrollWidth")
    check("320px no horizontal overflow", scrollw <= 322, f"scrollWidth={scrollw}")
    check("phone disclaimer visible", phone.get_by_text("not a medical device").first.is_visible())
    phone.screenshot(path=str(OUT / "phone_320.png"), full_page=True)
    up = phone.get_by_role("tab", name="Upload a video")
    up.click(); phone.wait_for_timeout(800)
    phone.screenshot(path=str(OUT / "phone_320_upload.png"), full_page=True)
    scrollw2 = phone.evaluate("document.documentElement.scrollWidth")
    check("320px upload tab no overflow", scrollw2 <= 322, f"scrollWidth={scrollw2}")
    browser.close()

ok = all(r[1] for r in results)
Path("verify/results.json").write_text(json.dumps(results, indent=1))
print("ALL PASS" if ok else "SOME FAILED")
sys.exit(0 if ok else 1)
