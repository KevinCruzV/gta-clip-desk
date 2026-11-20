"""Queue of new GTA 6 videos (Twitch VODs) from the streamers listed in accounts.csv, and ONLY them.

usage: python accounts.py accounts.csv [--since 24] [--limit 5] [--out queue.md] [--game-only]
Reads the `streamer` column; a row counts only if `authorized` is yes/true/1. Anything not in the file is never queried.
Writes <out> (markdown table, newest first) and <out stem>.json.
"""
import argparse, csv, json, re, sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import twitch

GTA = re.compile(r"\b(gta\s*-?\s*(6|vi)|grand theft auto\s*(6|vi))\b", re.I)
Q = """query($l:String!,$n:Int!){ user(login:$l){ displayName videos(first:$n, sort:TIME, type:ARCHIVE){ edges{ node{
 id title createdAt viewCount lengthSeconds game{ name } } } } } }"""


def load_accounts(path):
    rows = list(csv.DictReader(Path(path).read_text(encoding="utf-8-sig").splitlines()))
    ok = [r["streamer"].strip().lower() for r in rows
          if r.get("streamer") and (r.get("authorized") or "").strip().lower() in ("yes", "true", "1", "y")]
    if not ok:
        sys.exit(f"no authorized streamer in {path}")
    return ok


def load_skip(path):
    """URLs already processed (first token of each non-comment line of the skip file). Missing file = nothing skipped."""
    if not path or not Path(path).exists():
        return set()
    out = set()
    for line in Path(path).read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            out.add(line.split()[0].rstrip("/"))
    return out


def is_gta(title, game):
    return bool(GTA.search(title or "") or GTA.search(game or "") or "grand theft auto vi" in (game or "").lower())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("accounts"); ap.add_argument("--since", type=float, default=24, help="hours")
    ap.add_argument("--limit", type=int, default=5); ap.add_argument("--out", default="queue.md")
    ap.add_argument("--depth", type=int, default=12, help="recent VODs to inspect per streamer")
    ap.add_argument("--max-minutes", type=int, default=0, help="ignore VODs longer than this (0 = no limit)")
    ap.add_argument("--skip-file", help="done.txt: URLs already processed, never proposed again")
    a = ap.parse_args()
    streamers = load_accounts(a.accounts)
    skip = load_skip(a.skip_file)
    cutoff = datetime.now(timezone.utc) - timedelta(hours=a.since)
    items, errors = [], []
    for login in streamers:
        try:
            u = (twitch.gql(Q, {"l": login, "n": a.depth}).get("data") or {}).get("user")
        except Exception as e:
            errors.append(f"{login}: {str(e)[:80]}"); continue
        if not u:
            errors.append(f"{login}: user not found"); continue
        for e in (u.get("videos") or {}).get("edges") or []:
            n = e.get("node") or {}
            ts = datetime.fromisoformat(n["createdAt"].replace("Z", "+00:00"))
            game = (n.get("game") or {}).get("name") or ""
            if ts < cutoff or not is_gta(n.get("title"), game):
                continue
            if a.max_minutes and (n.get("lengthSeconds") or 0) > a.max_minutes * 60:
                continue
            if f"https://www.twitch.tv/videos/{n['id']}" in skip:
                continue
            items.append({"streamer": login, "name": u.get("displayName") or login, "title": n.get("title") or "",
                          "created_at": n["createdAt"], "views": n.get("viewCount") or 0,
                          "minutes": round((n.get("lengthSeconds") or 0) / 60), "game": game,
                          "url": f"https://www.twitch.tv/videos/{n['id']}"})
    items.sort(key=lambda x: x["created_at"], reverse=True)
    items = items[: a.limit]
    out = Path(a.out)
    lines = [f"# Queue: GTA 6 videos of the last {a.since:g} h ({len(streamers)} authorized streamers)", ""]
    if items:
        lines += ["| # | streamer | title | posted (UTC) | length | views | url |", "|---|---|---|---|---|---|---|"]
        for i, x in enumerate(items, 1):
            lines.append(f"| {i} | {x['name']} | {x['title'].replace('|', '/')} | {x['created_at']} | {x['minutes']} min | {x['views']} | {x['url']} |")
    else:
        lines.append("Nothing new.")
    if errors:
        lines += ["", "Lookup errors: " + "; ".join(errors)]
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    out.with_suffix(".json").write_text(json.dumps(items, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(items)} item(s) -> {out}" + (f" ({len(errors)} lookup error(s))" if errors else ""))


if __name__ == "__main__":
    main()
