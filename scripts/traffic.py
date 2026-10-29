"""Pulls GitHub traffic for every public repo of the profile owner, keeps the daily numbers in
data/traffic.json (GitHub itself only keeps 14 days) and redraws the dashboard in README.md.
Needs TRAFFIC_TOKEN (fine-grained token, Administration: read). Without it only stars, forks
and downloads are refreshed."""
import json
import os
import urllib.request
from datetime import datetime, timedelta, timezone

USER = os.environ.get('GH_USER', 'byteBhai')
TOKEN = os.environ.get('TRAFFIC_TOKEN', '')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, 'data', 'traffic.json')
README = os.path.join(ROOT, 'README.md')
CHART = os.path.join(ROOT, 'assets', 'views.svg')
START, END = '<!-- DASHBOARD:START -->', '<!-- DASHBOARD:END -->'
CHART_DAYS = 30


def api(path, auth=False):
    req = urllib.request.Request('https://api.github.com' + path, headers={
        'Accept': 'application/vnd.github+json', 'X-GitHub-Api-Version': '2022-11-28', 'User-Agent': USER})
    if auth:
        req.add_header('Authorization', 'Bearer ' + TOKEN)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def load():
    try:
        with open(DATA, encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {'since': None, 'repos': {}}


def collect(store):
    repos = [r for r in api(f'/users/{USER}/repos?per_page=100&type=owner') if not r['fork']]
    for r in repos:
        name = r['name']
        rec = store['repos'].setdefault(name, {'views': {}, 'clones': {}})
        rec['stars'], rec['forks'] = r['stargazers_count'], r['forks_count']
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
    store['since'] = min(days) if days else store['since']
    store['updated'] = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
    return store


def chart(store):
    """Plain SVG bar chart of total views per day for the last CHART_DAYS days."""
    today = datetime.now(timezone.utc).date()
    days = [(today - timedelta(days=i)).isoformat() for i in range(CHART_DAYS - 1, -1, -1)]
    totals = [sum(rec['views'].get(d, [0, 0])[0] for rec in store['repos'].values()) for d in days]
    w, h, pad, base = 720, 220, 36, 180
    top = max(totals + [1])
    bw = (w - 2 * pad) / CHART_DAYS
    bars = []
    for i, (d, v) in enumerate(zip(days, totals)):
        bh = (base - 30) * v / top
        x = pad + i * bw
        bars.append(f'<rect x="{x + 2:.1f}" y="{base - bh:.1f}" width="{bw - 4:.1f}" height="{bh:.1f}" rx="3" fill="#8b5cf6">'
                    f'<title>{d}: {v} views</title></rect>')
        if v:
            bars.append(f'<text x="{x + bw / 2:.1f}" y="{base - bh - 5:.1f}" text-anchor="middle" font-size="10">{v}</text>')
    label = lambda i: f'<text x="{pad + i * bw + bw / 2:.1f}" y="{base + 16}" text-anchor="middle" font-size="10">{days[i][5:]}</text>'
    ticks = ''.join(label(i) for i in range(0, CHART_DAYS, 5)) + label(CHART_DAYS - 1)
    with open(CHART, 'w', encoding='utf-8') as f:
        f.write(f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" '
                f'font-family="Segoe UI, Helvetica, Arial, sans-serif" fill="#8b949e">'
                f'<text x="{pad}" y="20" font-size="14" font-weight="600">Views per day, last {CHART_DAYS} days (all repos)</text>'
                f'<line x1="{pad}" y1="{base}" x2="{w - pad}" y2="{base}" stroke="#8b949e" stroke-opacity="0.4"/>'
                f'{"".join(bars)}{ticks}</svg>')


def top(rows, n=8):
    merged = {}
    for key, count, uniques in rows:
        c, u = merged.get(key, (0, 0))
        merged[key] = (c + count, u + uniques)
    return sorted(merged.items(), key=lambda kv: -kv[1][0])[:n]


def dashboard(store):
    repos = store['repos']
    out = [f'_Last updated: {store.get("updated", "-")}. Tracking since: {store.get("since") or "not yet"}._', '',
           '| Repo | ⭐ Stars | 🍴 Forks | 👀 Views (14 days) | 🧑 Unique visitors (14 days) | 📥 Clones (14 days) | 📦 APK downloads | 👀 Views since tracking began |',
           '|---|---:|---:|---:|---:|---:|---:|---:|']
    for name, rec in sorted(repos.items()):
        v14, c14 = rec.get('views_14d', [0, 0]), rec.get('clones_14d', [0, 0])
        total = sum(c for c, _ in rec['views'].values())
        out.append(f'| [{name}](https://github.com/{USER}/{name}) | {rec["stars"]} | {rec["forks"]} | {v14[0]} | {v14[1]} '
                   f'| {c14[0]} | {rec["downloads"]} | {total} |')
    out += ['', '<img src="assets/views.svg" alt="Views per day" />', '']
    refs = top([r for rec in repos.values() for r in rec.get('referrers', [])])
    out += ['**Where visitors came from (14 days)**', '', '| Source | Views | Unique |', '|---|---:|---:|']
    out += [f'| {k} | {c} | {u} |' for k, (c, u) in refs] or ['| _no data yet_ | | |']
    paths = top([[p[0], p[1], p[2]] for rec in repos.values() for p in rec.get('paths', [])])
    out += ['', '**What they opened (14 days)**', '', '| Page | Views | Unique |', '|---|---:|---:|']
    out += [f'| `{k}` | {c} | {u} |' for k, (c, u) in paths] or ['| _no data yet_ | | |']
    return '\n'.join(out)


def main():
    store = collect(load())
    os.makedirs(os.path.dirname(DATA), exist_ok=True)
    with open(DATA, 'w', encoding='utf-8') as f:
        json.dump(store, f, indent=1, sort_keys=True)
    chart(store)
    with open(README, encoding='utf-8') as f:
        text = f.read()
    head, rest = text.split(START, 1)
    tail = rest.split(END, 1)[1]
    with open(README, 'w', encoding='utf-8', newline='\n') as f:
        f.write(f'{head}{START}\n{dashboard(store)}\n{END}{tail}')
    print('updated', len(store['repos']), 'repos; token', 'used' if TOKEN else 'missing (traffic skipped)')


if __name__ == '__main__':
    main()
