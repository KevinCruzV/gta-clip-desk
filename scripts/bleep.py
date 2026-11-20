"""Replace explicit spoken words (sexual terms, swears, slurs) with a beep in a finished clip's audio.

usage: python bleep.py jobs/<id>/edits/clip_<n>.mp4
Uses the word timestamps of jobs/<id>/transcript.json (written by moments.py) and clip_<n>.json (start offset).
The same word lists as the burned captions are used, so what is masked in the text is also bleeped in the audio.
Video is not re-encoded. Run it right after cut.py, before watermark_check.py and check.py.
"""
import json, re, subprocess, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from common import load_json, tool
from cut import _SLURS, _SWEARS
from sexual_terms import SEXUAL


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    clip = Path(sys.argv[1])
    meta = load_json(clip.with_suffix(".json"))
    words = load_json(clip.parent.parent / "transcript.json")
    s0, e0 = float(meta.get("start", 0)), float(meta.get("end", 1e9))
    iv = []
    for w in words:
        t = re.sub(r"[^\w'*-]", "", w["w"])
        if not t or not (SEXUAL.fullmatch(t) or _SLURS.fullmatch(t) or _SWEARS.fullmatch(t)):
            continue
        if not (s0 <= w["s"] < e0):
            continue
        a, b = max(0.0, w["s"] - s0 - 0.06), w["e"] - s0 + 0.06
        if iv and a <= iv[-1][1] + 0.05:
            iv[-1][1] = max(iv[-1][1], b)
        else:
            iv.append([a, b])
    if not iv:
        print("bleep: no explicit word in the audio, nothing to do")
        return
    expr = "+".join(f"between(t,{a:.2f},{b:.2f})" for a, b in iv)
    fc = (f"[0:a]volume=0:enable='{expr}'[m];"
          f"sine=frequency=1000:sample_rate=48000,volume='0.18*({expr})':eval=frame[b];"
          f"[m][b]amix=inputs=2:duration=first:normalize=0[a]")
    tmp = clip.with_name(clip.stem + "_bleep.mp4")
    r = subprocess.run([tool("ffmpeg"), "-y", "-v", "error", "-i", str(clip), "-filter_complex", fc, "-map", "0:v", "-map", "[a]",
                        "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", str(tmp)], capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(f"bleep failed: {r.stderr[-400:]}")
    tmp.replace(clip)
    meta["bleeped"] = [[round(a, 2), round(b, 2)] for a, b in iv]
    clip.with_suffix(".json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"bleep: {len(iv)} segment(s) bleeped in {clip.name}")


if __name__ == "__main__":
    main()
