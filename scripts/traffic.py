"""Pulls GitHub traffic for every public repo of the profile owner, keeps the daily numbers in
data/traffic.json (GitHub itself only keeps 14 days), reads the latest YouTube uploads from the
channel's public RSS feed and redraws the README blocks and the SVG cards in assets/.
Needs TRAFFIC_TOKEN (fine-grained token, Administration: read) for traffic. Without it only
stars, forks, followers, downloads and YouTube are refreshed."""
import json
import os
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from xml.sax.saxutils import escape

USER = os.environ.get('GH_USER', 'byteBhai')
TOKEN = os.environ.get('TRAFFIC_TOKEN', '')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, 'data', 'traffic.json')
CONFIG = os.path.join(ROOT, 'config.json')
README = os.path.join(ROOT, 'README.md')
ASSETS = os.path.join(ROOT, 'assets')
CHART_DAYS = 30
FONT = "'Segoe UI', 'Helvetica Neue', Arial, sans-serif"
# cards carry their own dark background so they look the same in GitHub light and dark mode
CARD_BG = '<linearGradient id="card" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#1e1b4b"/><stop offset="1" stop-color="#2e1065"/></linearGradient>'


def get(url, auth=False):
    req = urllib.request.Request(url, headers={'User-Agent': USER, 'Accept': 'application/vnd.github+json',
                                               'X-GitHub-Api-Version': '2022-11-28'})
    if auth:
        req.add_header('Authorization', 'Bearer ' + TOKEN)
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


def api(path, auth=False):
    return json.loads(get('https://api.github.com' + path, auth))


def load(path, default):
    try:
        with open(path, encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return default


def collect(store):
    repos = [r for r in api(f'/users/{USER}/repos?per_page=100&type=owner') if not r['fork']]
    store['followers'] = api(f'/users/{USER}')['followers']
    for r in repos:
        name = r['name']
        rec = store['repos'].setdefault(name, {'views': {}, 'clones': {}})
        rec['stars'], rec['forks'], rec['about'] = r['stargazers_count'], r['forks_count'], r['description'] or ''
        rec['downloads'] = sum(a['download_count'] for rel in api(f'/repos/{USER}/{name}/releases?per_page=100')
                               for a in rel.get('assets', []))
        if not TOKEN:
            continue
        for kind in ('views', 'clones'):
            got = api(f'/repos/{USER}/{name}/traffic/{kind}', auth=True)
            for day in got[kind]:
                # a day already stored is overwritten: GitHub's latest figure for that day wins
                rec[kind][day['timestamp'][:10]] = [day['count'], day['uniques']]
            rec[kind + '_14d'] = [got['count'], got['uniques']]
        rec['referrers'] = [[x['referrer'], x['count'], x['uniques']]
                            for x in api(f'/repos/{USER}/{name}/traffic/popular/referrers', auth=True)]
        rec['paths'] = [[x['path'], x['count'], x['uniques']]
                        for x in api(f'/repos/{USER}/{name}/traffic/popular/paths', auth=True)]
    days = [d for rec in store['repos'].values() for d in rec['views']]
    store['since'] = min(days) if days else store.get('since')
    store['updated'] = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
    return store


def youtube(channel_id, n=6):
    """Latest uploads from the public RSS feed (no API key needed)."""
    ns = {'a': 'http://www.w3.org/2005/Atom', 'yt': 'http://www.youtube.com/xml/schemas/2015'}
    feed = ET.fromstring(get(f'https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}'))
    out = []
    for e in feed.findall('a:entry', ns)[:n]:
        out.append({'id': e.find('yt:videoId', ns).text, 'title': e.find('a:title', ns).text,
                    'link': e.find('a:link', ns).get('href'), 'date': e.find('a:published', ns).text[:10]})
    return out


def totals(store):
    repos = store['repos'].values()
    add = lambda key, i: sum(rec.get(key, [0, 0])[i] for rec in repos)
    return {'views': add('views_14d', 0), 'uniques': add('views_14d', 1), 'clones': add('clones_14d', 0),
            'downloads': sum(rec['downloads'] for rec in repos), 'stars': sum(rec['stars'] for rec in repos),
            'followers': store.get('followers', 0),
            'all_views': sum(c for rec in repos for c, _ in rec['views'].values())}


def write(name, svg):
    with open(os.path.join(ASSETS, name), 'w', encoding='utf-8', newline='\n') as f:
        f.write(svg)


def stats_card(store):
    t = totals(store)
    tiles = [('👀', 'Views', t['views'], '14 days'), ('🧑', 'Unique visitors', t['uniques'], '14 days'),
             ('📥', 'Clones', t['clones'], '14 days'), ('📦', 'APK downloads', t['downloads'], 'all time'),
             ('⭐', 'Stars', t['stars'], 'all repos'), ('🤝', 'Followers', t['followers'], 'GitHub')]
    w, h, cols = 1000, 360, 3
    tw, th, gap, top = 300, 110, 25, 70
    left = (w - cols * tw - (cols - 1) * gap) / 2
    cells = []
    for i, (emo, label, value, note) in enumerate(tiles):
        x, y = left + (i % cols) * (tw + gap), top + (i // cols) * (th + 20)
        cells.append(f'''<g class="tile" style="animation-delay:{0.12 * i:.2f}s">
    <rect x="{x}" y="{y}" width="{tw}" height="{th}" rx="16" fill="#ffffff" fill-opacity="0.06" stroke="#a78bfa" stroke-opacity="0.35"/>
    <text x="{x + 22}" y="{y + 44}" font-size="28">{emo}</text>
    <text x="{x + 66}" y="{y + 42}" class="label">{escape(label)}</text>
    <text x="{x + 66}" y="{y + 88}" class="value">{value:,}</text>
    <text x="{x + tw - 18}" y="{y + 88}" class="note" text-anchor="end">{escape(note)}</text></g>''')
    since = store.get('since')
    foot = f'{t["all_views"]:,} views since {since}' if since else 'tracking starts after the first daily run'
    write('stats.svg', f'''<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">
  <defs>{CARD_BG}</defs>
  <style>
    text {{ font-family: {FONT}; }}
    .h {{ font-size: 22px; font-weight: 800; fill: #ffffff; }}
    .label {{ font-size: 16px; font-weight: 600; fill: #c4b5fd; }}
    .value {{ font-size: 38px; font-weight: 900; fill: #facc15; }}
    .note {{ font-size: 13px; fill: #a1a1aa; }}
    .foot {{ font-size: 14px; fill: #a1a1aa; }}
    .tile {{ opacity: 0; animation: up .6s ease-out forwards; }}
    @keyframes up {{ from {{ opacity: 0; transform: translateY(14px); }} to {{ opacity: 1; transform: none; }} }}
    .live {{ animation: pulse 1.6s ease-in-out infinite; }}
    @keyframes pulse {{ 0%,100% {{ opacity: 1; }} 50% {{ opacity: .25; }} }}
  </style>
  <rect width="{w}" height="{h}" rx="22" fill="url(#card)"/>
  <text x="{left}" y="44" class="h">📊 GitHub dashboard</text>
  <circle class="live" cx="{w - left - 70}" cy="37" r="6" fill="#22c55e"/>
  <text x="{w - left}" y="43" class="foot" text-anchor="end">LIVE</text>
  {''.join(cells)}
  <text x="{left}" y="{h - 18}" class="foot">{escape(foot)} · updated {escape(store.get("updated", "-"))}</text>
</svg>''')


def views_chart(store):
    today = datetime.now(timezone.utc).date()
    days = [(today - timedelta(days=i)).isoformat() for i in range(CHART_DAYS - 1, -1, -1)]
    vals = [sum(rec['views'].get(d, [0, 0])[0] for rec in store['repos'].values()) for d in days]
    w, h, pad, base = 1000, 300, 40, 240
    peak = max(vals + [1])
    bw = (w - 2 * pad) / CHART_DAYS
    bars = []
    for i, v in enumerate(vals):
        bh = max((base - 80) * v / peak, 3)
        x = pad + i * bw
        bars.append(f'<rect class="bar" style="animation-delay:{0.03 * i:.2f}s" x="{x + 3:.1f}" y="{base - bh:.1f}" '
                    f'width="{bw - 6:.1f}" height="{bh:.1f}" rx="4" fill="url(#bar)" fill-opacity="{1 if v else 0.25}"/>')
        if v:
            bars.append(f'<text class="num" style="animation-delay:{0.03 * i + 0.5:.2f}s" x="{x + bw / 2:.1f}" '
                        f'y="{base - bh - 7:.1f}" text-anchor="middle">{v}</text>')
    ticks = ''.join(f'<text class="tick" x="{pad + i * bw + bw / 2:.1f}" y="{base + 22}" text-anchor="middle">'
                    f'{datetime.fromisoformat(days[i]).strftime("%d %b")}</text>'
                    for i in list(range(0, CHART_DAYS, 6)) + [CHART_DAYS - 1])
    write('views.svg', f'''<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">
  <defs>{CARD_BG}<linearGradient id="bar" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#facc15"/><stop offset="1" stop-color="#8b5cf6"/></linearGradient></defs>
  <style>
    text {{ font-family: {FONT}; }}
    .h {{ font-size: 22px; font-weight: 800; fill: #ffffff; }}
    .sub {{ font-size: 14px; fill: #a1a1aa; }}
    .num {{ font-size: 12px; font-weight: 700; fill: #fde68a; opacity: 0; animation: fade .4s ease-out forwards; }}
    .tick {{ font-size: 12px; fill: #a1a1aa; }}
    .bar {{ transform-box: fill-box; transform-origin: bottom; transform: scaleY(0); animation: grow .7s ease-out forwards; }}
    @keyframes grow {{ to {{ transform: scaleY(1); }} }}
    @keyframes fade {{ to {{ opacity: 1; }} }}
  </style>
  <rect width="{w}" height="{h}" rx="22" fill="url(#card)"/>
  <text x="{pad}" y="44" class="h">📈 Views per day</text>
  <text x="{w - pad}" y="44" class="sub" text-anchor="end">last {CHART_DAYS} days · all repos · {sum(vals):,} views</text>
  <line x1="{pad}" y1="{base}" x2="{w - pad}" y2="{base}" stroke="#a78bfa" stroke-opacity="0.35"/>
  {''.join(bars)}{ticks}
</svg>''')


def top(rows, n=8):
    merged = {}
    for key, count, uniques in rows:
        c, u = merged.get(key, (0, 0))
        merged[key] = (c + count, u + uniques)
    return sorted(merged.items(), key=lambda kv: -kv[1][0])[:n]


def dashboard(store):
    repos = store['repos']
    out = ['<p align="center"><img src="assets/stats.svg" alt="GitHub stats" width="100%" /></p>',
           '<p align="center"><img src="assets/views.svg" alt="Views per day" width="100%" /></p>', '',
           '### 🌍 Log kahan se aaye (14 days)', '']
    refs = top([r for rec in repos.values() for r in rec.get('referrers', [])])
    if refs:
        out += ['```mermaid', 'pie showData', '    title Visitors by source']
        out += [f'    "{k.replace(chr(34), "")}" : {c}' for k, (c, _) in refs]
        out += ['```']
    else:
        out += ['_Abhi koi data nahi. Pehle visitors aane do_ 🙂']
    paths = top([[p[0], p[1], p[2]] for rec in repos.values() for p in rec.get('paths', [])])
    out += ['', '<details>', '<summary><b>📄 Kaunse pages khule (14 days)</b></summary>', '',
            '| Page | Views | Unique |', '|---|---:|---:|']
    out += [f'| `{k}` | {c} | {u} |' for k, (c, u) in paths] or ['| _no data yet_ | | |']
    out += ['', '</details>', '', '<details>', '<summary><b>📦 Har repo ka hisaab</b></summary>', '',
            '| Repo | ⭐ | 🍴 | 👀 Views (14d) | 🧑 Unique (14d) | 📥 Clones (14d) | 📦 Downloads | 👀 Views since tracking |',
            '|---|---:|---:|---:|---:|---:|---:|---:|']
    for name, rec in sorted(repos.items()):
        v14, c14 = rec.get('views_14d', [0, 0]), rec.get('clones_14d', [0, 0])
        out.append(f'| [{name}](https://github.com/{USER}/{name}) | {rec["stars"]} | {rec["forks"]} | {v14[0]} | '
                   f'{v14[1]} | {c14[0]} | {rec["downloads"]} | {sum(c for c, _ in rec["views"].values())} |')
    out += ['', '</details>', '', f'<sub>Updated daily by GitHub Actions · last run {store.get("updated", "-")}</sub>']
    return '\n'.join(out)


def youtube_block(cfg):
    if not cfg.get('youtube_channel_id'):
        return '_Channel link coming soon._'
    vids = youtube(cfg['youtube_channel_id'])
    if not vids:
        return f'_Pehla video jaldi aa raha hai._ [Channel dekho]({cfg["youtube_url"]})'
    cells = [f'<td align="center" width="33%"><a href="{escape(v["link"])}"><img src="https://i.ytimg.com/vi/{v["id"]}/hqdefault.jpg" '
             f'width="100%" alt="{escape(v["title"], {chr(34): "&quot;"})}" /></a><br/><sub><b>{escape(v["title"])}</b></sub></td>'
             for v in vids]
    rows = ['<tr>' + ''.join(cells[i:i + 3]) + '</tr>' for i in range(0, len(cells), 3)]
    return '\n'.join(['<table>', *rows, '</table>', '',
                      f'<p align="center"><a href="{cfg["youtube_url"]}?sub_confirmation=1"><b>▶️ Subscribe karo, roz naya jaadu</b></a></p>'])


def replace_block(text, tag, body):
    start, end = f'<!-- {tag}:START -->', f'<!-- {tag}:END -->'
    head, rest = text.split(start, 1)
    return f'{head}{start}\n{body}\n{end}{rest.split(end, 1)[1]}'


def main():
    cfg = load(CONFIG, {})
    store = collect(load(DATA, {'since': None, 'repos': {}}))
    os.makedirs(os.path.dirname(DATA), exist_ok=True)
    os.makedirs(ASSETS, exist_ok=True)
    with open(DATA, 'w', encoding='utf-8') as f:
        json.dump(store, f, indent=1, sort_keys=True)
    stats_card(store)
    views_chart(store)
    with open(README, encoding='utf-8') as f:
        text = f.read()
    text = replace_block(text, 'DASHBOARD', dashboard(store))
    text = replace_block(text, 'YOUTUBE', youtube_block(cfg))
    with open(README, 'w', encoding='utf-8', newline='\n') as f:
        f.write(text)
    print('updated', len(store['repos']), 'repos; token', 'used' if TOKEN else 'missing (traffic skipped)')


if __name__ == '__main__':
    main()
