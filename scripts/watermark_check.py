"""Look for a leftover watermark/logo/overlay burned into a finished clip.

usage: python watermark_check.py <clip.mp4> [--strict] [--sheet path.jpg]
Samples frames, finds regions that stay static (barely change) and carry edges (text/logo), ignoring the area where
cut.py puts its own captions. Static blobs touching the screen borders are what a stream logo, viewer counter,
channel name or platform watermark looks like.
PASS  nothing suspicious.   WARN  small static blob: open the sheet and judge.   FAIL  large static blob on a border.
--strict lowers the thresholds. Writes a contact sheet (<clip>_wmcheck.jpg) with suspects boxed in red.
Exit code 1 on FAIL only.
"""
import argparse, json, sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).parent))
from common import load_json

W, H = 1080, 1920
CAP_Y = {"fill": 1380, "blur": 1460, "facecam": 1120, "react": 1560}


def sample(path, n=14):
    import cv2
    cap = cv2.VideoCapture(str(path))
    total = cap.get(cv2.CAP_PROP_FRAME_COUNT); fps = cap.get(cv2.CAP_PROP_FPS) or 30
    dur = total / fps if total else 0
    start = 3.0 if dur > 6 else 0.0   # skip the hook box shown in the first seconds
    frames = []
    for k in range(n):
        cap.set(cv2.CAP_PROP_POS_MSEC, (start + (dur - start) * (k + 0.5) / n) * 1000)
        ok, f = cap.read()
        if ok:
            frames.append(cv2.resize(f, (W, H)) if f.shape[:2] != (H, W) else f)
    cap.release()
    return frames


def main():
    import cv2
    ap = argparse.ArgumentParser()
    ap.add_argument("clip"); ap.add_argument("--strict", action="store_true"); ap.add_argument("--sheet")
    a = ap.parse_args()
    clip = Path(a.clip)
    if not clip.exists():
        sys.exit(f"FAIL file not found: {clip}")
    meta = load_json(clip.with_suffix(".json")) if clip.with_suffix(".json").exists() else {}
    cap_y = CAP_Y.get(meta.get("layout", ""), 1380)
    frames = sample(clip)
    if len(frames) < 4:
        sys.exit("FAIL not enough frames to analyse")
    gray = np.stack([cv2.cvtColor(f, cv2.COLOR_BGR2GRAY).astype(np.float32) for f in frames])
    std = gray.std(0); med = np.median(gray, 0).astype(np.uint8)
    edges = cv2.Canny(med, 60, 160) > 0
    static = (std < 6) & cv2.dilate(edges.astype(np.uint8), np.ones((7, 7), np.uint8)).astype(bool)
    static[cap_y - 230:cap_y + 230, :] = False          # our own word-by-word captions
    mask = cv2.morphologyEx(static.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((25, 25), np.uint8))
    n, lab, stats, _ = cv2.connectedComponentsWithStats(mask, connectivity=8)
    warn_px, fail_px = (1500, 6000) if a.strict else (3000, 12000)
    mx, my_top, my_bot = int(W * 0.16), int(H * 0.12), int(H * 0.10)
    suspects = []
    for i in range(1, n):
        x, y, w, h, area = stats[i]
        px = int((lab[y:y + h, x:x + w] == i).sum())
        border = x < mx or x + w > W - mx or y < my_top or y + h > H - my_bot
        if px >= warn_px and border and w < W * 0.8:
            suspects.append({"box": [int(x), int(y), int(w), int(h)], "px": px, "level": "FAIL" if px >= fail_px else "WARN"})
    level = "FAIL" if any(s["level"] == "FAIL" for s in suspects) else ("WARN" if suspects else "PASS")

    sheet = Path(a.sheet) if a.sheet else clip.with_name(clip.stem + "_wmcheck.jpg")
    if level != "PASS":
        tiles = []
        for f in frames[:6]:
            g = f.copy()
            for s in suspects:
                x, y, w, h = s["box"]; cv2.rectangle(g, (x, y), (x + w, y + h), (0, 0, 255), 6)
            tiles.append(cv2.resize(g, (270, 480)))
        while len(tiles) < 6:
            tiles.append(np.zeros_like(tiles[0]))
        cv2.imwrite(str(sheet), np.vstack([np.hstack(tiles[:3]), np.hstack(tiles[3:6])]))
    for s in suspects:
        print(f"{s['level']}  static overlay at x,y,w,h={s['box']} ({s['px']} px)")
    print(f"{level}  watermark check ({len(frames)} frames, {'strict' if a.strict else 'normal'})"
          + (f"  sheet: {sheet}" if level != 'PASS' else ""))
    print("RESULT: " + level)
    sys.exit(1 if level == "FAIL" else 0)


if __name__ == "__main__":
    main()
