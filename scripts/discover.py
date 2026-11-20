"""Most viewed Twitch GTA 6 clips, restricted to the streamers of accounts.csv.

usage: python discover.py --twitch-clips LAST_DAY [--limit 5] --mine-only [--accounts accounts.csv] [--out discover.md]
Periods: LAST_DAY, LAST_WEEK, LAST_MONTH, ALL_TIME.
--mine-only is required: this script has no way to check permission for any other streamer, so it refuses to
look at anyone outside accounts.csv (no "ask first" results are ever produced).
"""
import argparse, csv, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import twitch
from accounts import is_gta, load_accounts, load_skip

Q = """query($l:String!,$p:ClipsPeriod!,$n:Int!){ user(login:$l){ displayName clips(first:$n, criteria:{period:$p, sort:VIEWS_DESC}){ edges{ node{
 title viewCount createdAt url durationSeconds game{ name } } } } } }"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--twitch-clips", dest="period", required=True, choices=["LAST_DAY", "LAST_WEEK", "LAST_MONTH", "ALL_TIME"])
    ap.add_argument("--limit", type=int, default=5); ap.add_argument("--out", default="discover.md")
    ap.add_argument("--accounts", default="accounts.csv")
    ap.add_argument("--mine-only", action="store_true")
    ap.add_argument("--per-streamer", type=int, default=15)
    ap.add_argument("--min-seconds", type=int, default=15, help="shorter clips cannot yield a 15 s moment")
    ap.add_argument("--skip-file", help="done.txt: URLs already processed, never proposed again")
    a = ap.parse_args()
    if not a.mine_only:
        sys.exit("refused: pass --mine-only (only streamers listed as authorized in accounts.csv can be processed)")
    streamers = load_accounts(a.accounts)
    skip = load_skip(a.skip_file)
    items, errors = [], []
    for login in streamers:
        try:
            u = (twitch.gql(Q, {"l": login, "p": a.period, "n": a.per_streamer}).get("data") or {}).get("user")
        except Exception as e:
            errors.append(f"{login}: {str(e)[:80]}"); continue
        if not u:
            errors.append(f"{login}: user not found"); continue
        for e in (u.get("clips") or {}).get("edges") or []:
            n = e.get("node") or {}
            game = (n.get("game") or {}).get("name") or ""
            if not is_gta(n.get("title"), game):
                continue
            if (n.get("durationSeconds") or 0) < a.min_seconds or (n.get("url") or "").rstrip("/") in skip:
                continue
            items.append({"streamer": login, "name": u.get("displayName") or login, "title": n.get("title") or "",
                          "views": n.get("viewCount") or 0, "seconds": n.get("durationSeconds") or 0,
                          "created_at": n.get("createdAt"), "url": n.get("url"), "status": "authorized"})
    items.sort(key=lambda x: x["views"], reverse=True)
    items = items[: a.limit]
    lines = [f"# Top GTA 6 Twitch clips ({a.period}), authorized streamers only", ""]
    if items:
        lines += ["| # | streamer | title | views | length | posted (UTC) | status | url |", "|---|---|---|---|---|---|---|---|"]
        for i, x in enumerate(items, 1):
            lines.append(f"| {i} | {x['name']} | {x['title'].replace('|', '/')} | {x['views']} | {x['seconds']} s | {x['created_at']} | authorized | {x['url']} |")
    else:
        lines.append("Nothing found.")
    if errors:
        lines += ["", "Lookup errors: " + "; ".join(errors)]
    out = Path(a.out)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    out.with_suffix(".json").write_text(json.dumps(items, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(items)} clip(s) -> {out}" + (f" ({len(errors)} lookup error(s))" if errors else ""))


if __name__ == "__main__":
    main()
