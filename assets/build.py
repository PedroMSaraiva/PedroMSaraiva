"""Render the profile header and the 12-month activity chart as light/dark SVGs.

Usage: GITHUB_TOKEN=... python assets/build.py [login]
       python assets/build.py --selftest
"""
import base64, datetime as dt, json, os, sys, urllib.request
from collections import OrderedDict
from pathlib import Path

HERE = Path(__file__).parent
OUT = HERE / "svg"
THEMES = {
    "light": dict(bg="#F2F5F8", fg="#121821", muted="#4E5B6B", line="#C9D3DD", bar="#9FB3C6", accent="#9A5F0A", ring="#121821"),
    "dark": dict(bg="#121821", fg="#E3EAF0", muted="#94A3B3", line="#2A3442", bar="#3E5470", accent="#E3A645", ring="#C9D6E2"),
}
CORE = "#D9962B"


def font(name, file):
    b64 = base64.b64encode((HERE / "fonts" / file).read_bytes()).decode()
    return f"@font-face{{font-family:'{name}';src:url(data:font/woff2;base64,{b64}) format('woff2')}}"


FONTS = font("ArchivoX", "archivo-name.woff2") + font("PlexMono", "plexmono.woff2")
MONO = "font-family:PlexMono,ui-monospace,Menlo,monospace;font-weight:500"
MOTION = "@media (prefers-reduced-motion:reduce){*{animation:none!important}}"


def mark(x, y, size, ring):
    s = size / 64
    return (f'<g transform="translate({x} {y}) scale({s})">'
            f'<circle cx="32" cy="32" r="27" fill="none" stroke="{ring}" stroke-width="5"/>'
            f'<circle cx="28.5" cy="35.5" r="16" fill="none" stroke="{ring}" stroke-width="5"/>'
            f'<circle class="core" cx="26" cy="38" r="6.5" fill="{CORE}"/></g>')


def header(t):
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 200" width="1000" height="200" role="img" aria-label="Pedro Saraiva, AI engineer">
<style>{FONTS}{MOTION}
.core{{animation:cycle 7s ease-in-out infinite}}
@keyframes cycle{{0%,62%,100%{{transform:none}}74%{{transform:translateY(-14px)}}86%{{transform:translateY(3px)}}}}
.name{{font-family:ArchivoX,'Arial Black',Arial,sans-serif;font-weight:800;font-size:64px;letter-spacing:-2px}}
.sub{{{MONO};font-size:15px;letter-spacing:2.4px}}</style>
<rect width="1000" height="200" rx="0" fill="{t["bg"]}"/>
{mark(40, 52, 96, t["ring"])}
<text x="168" y="112" class="name" fill="{t["fg"]}">Pedro Saraiva</text>
<text x="171" y="148" class="sub" fill="{t["muted"]}">AI ENGINEER · AGENTS IN PRODUCTION <tspan fill="{t["accent"]}">+</tspan> THE INFRA UNDER THEM</text>
<line x1="0" y1="199" x2="1000" y2="199" stroke="{t["line"]}" stroke-width="2"/>
</svg>'''


def fetch_days(login, token):
    q = 'query($l:String!){user(login:$l){contributionsCollection{contributionCalendar{weeks{contributionDays{date contributionCount}}}}}}'
    req = urllib.request.Request("https://api.github.com/graphql",
                                 data=json.dumps({"query": q, "variables": {"l": login}}).encode(),
                                 headers={"Authorization": f"bearer {token}", "Content-Type": "application/json"})
    weeks = json.load(urllib.request.urlopen(req))["data"]["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]
    return [(d["date"], d["contributionCount"]) for w in weeks for d in w["contributionDays"]]


def summarize(days):
    """days: [(iso_date, count)] in date order -> (months OrderedDict 'YYYY-MM' -> total, total, active days, longest streak)."""
    months, streak, best = OrderedDict(), 0, 0
    for date, n in days:
        months[date[:7]] = months.get(date[:7], 0) + n
        streak = streak + 1 if n else 0
        best = max(best, streak)
    months = OrderedDict(list(months.items())[-12:])
    return months, sum(n for _, n in days), sum(1 for _, n in days if n), best


def chart(t, months, total, active, streak):
    W, H, left, right, top, base = 1000, 300, 40, 960, 96, 250
    peak = max(months.values()) or 1
    slot = (right - left) / len(months)
    bw = slot * 0.56
    hot = max(months, key=months.get)
    bars = []
    for i, (ym, n) in enumerate(months.items()):
        h = max(2, (base - top) * n / peak)
        x = left + i * slot + (slot - bw) / 2
        fill = t["accent"] if ym == hot else t["bar"]
        label = dt.date(int(ym[:4]), int(ym[5:]), 1).strftime("%b").upper()
        bars.append(
            f'<g><title>{label} {ym[:4]}: {n} contributions</title>'
            f'<rect x="{x:.1f}" y="{base - h:.1f}" width="{bw:.1f}" height="{h:.1f}" fill="{fill}"/>'
            f'<text x="{x + bw / 2:.1f}" y="{base - h - 8:.1f}" text-anchor="middle" class="v" fill="{t["fg"] if ym == hot else t["muted"]}">{n}</text></g>'
            f'<text x="{x + bw / 2:.1f}" y="{base + 22}" text-anchor="middle" class="m" fill="{t["muted"]}">{label}</text>')
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-label="{total} contributions in the last 12 months">
<style>{FONTS}{MOTION}
text{{{MONO}}} .h{{font-size:13px;letter-spacing:2px}} .v{{font-size:12px}} .m{{font-size:11px;letter-spacing:1px}}
</style>
<rect width="{W}" height="{H}" fill="{t["bg"]}"/>
<text x="{left}" y="44" class="h" fill="{t["fg"]}">LAYER BY LAYER · LAST 12 MONTHS</text>
<text x="{right}" y="44" text-anchor="end" class="h" fill="{t["muted"]}">{total} CONTRIBUTIONS · {active} ACTIVE DAYS · BEST RUN {streak} D</text>
<line x1="{left}" y1="{base}" x2="{right}" y2="{base}" stroke="{t["line"]}" stroke-width="1"/>
{"".join(bars)}
</svg>'''


def selftest():
    days = [("2026-01-01", 1), ("2026-01-02", 2), ("2026-01-03", 0), ("2026-02-01", 3), ("2026-02-02", 4), ("2026-02-03", 5)]
    months, total, active, streak = summarize(days)
    assert months == OrderedDict([("2026-01", 3), ("2026-02", 12)]), months
    assert (total, active, streak) == (15, 5, 3), (total, active, streak)
    assert "<rect" in chart(THEMES["dark"], months, total, active, streak)
    print("selftest ok")


if __name__ == "__main__":
    if sys.argv[1:] == ["--selftest"]:
        selftest(); sys.exit()
    login = sys.argv[1] if len(sys.argv) > 1 else "PedroMSaraiva"
    stats = summarize(fetch_days(login, os.environ["GITHUB_TOKEN"]))
    OUT.mkdir(exist_ok=True)
    for name, t in THEMES.items():
        (OUT / f"header-{name}.svg").write_text(header(t))
        (OUT / f"activity-{name}.svg").write_text(chart(t, *stats))
    print("wrote", sorted(p.name for p in OUT.iterdir()))
