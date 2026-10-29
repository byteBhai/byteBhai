"""Draws assets/header.svg: animated banner with the chip mascot (blinks, moustache twitch) and
rotating taglines. Has its own background, so it looks the same in GitHub light and dark mode.
Run once after editing: python scripts/header.py"""
import os
from xml.sax.saxutils import escape

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TAGLINES = ['5 line ka jaadu 🪄', 'Python tricks, desi style 🐍', 'Apps jo roz kaam aayein 📱', 'Roz ek naya Short 🎬']
W, H = 1000, 280
FONT = "'Segoe UI', 'Helvetica Neue', Arial, sans-serif"


def mascot(cx, cy, s):
    """Chip mascot from the channel logo, drawn in vectors. s = chip size."""
    r = s / 2
    pins = []
    for i in range(5):
        o = -r + s * (0.12 + i * 0.19)
        pins += [f'<rect x="{cx + o - 7}" y="{cy - r - 22}" width="14" height="30" rx="5"/>',
                 f'<rect x="{cx + o - 7}" y="{cy + r - 8}" width="14" height="30" rx="5"/>',
                 f'<rect x="{cx - r - 22}" y="{cy + o - 7}" width="30" height="14" rx="5"/>',
                 f'<rect x="{cx + r - 8}" y="{cy + o - 7}" width="30" height="14" rx="5"/>']
    ex = s * 0.2
    return f'''
  <g class="bob">
    <g fill="#1e1b4b">{''.join(pins)}</g>
    <rect x="{cx - r}" y="{cy - r}" width="{s}" height="{s}" rx="{s * 0.16}" fill="#facc15" stroke="#1e1b4b" stroke-width="9"/>
    <rect x="{cx - r + 14}" y="{cy - r + 14}" width="{s - 28}" height="{s * 0.3}" rx="{s * 0.1}" fill="#fff" opacity="0.18"/>
    <circle cx="{cx - r + 30}" cy="{cy - r + 30}" r="8" fill="#3f3a4a"/>
    <text x="{cx}" y="{cy - r + 42}" text-anchor="middle" font-family="Consolas, monospace" font-weight="700" font-size="22" fill="#1e1b4b">&lt;/&gt;</text>
    <g class="blink" fill="#1e1b4b">
      <rect x="{cx - ex - 11}" y="{cy - 22}" width="22" height="34" rx="11"/>
      <rect x="{cx + ex - 11}" y="{cy - 22}" width="22" height="34" rx="11"/>
      <circle cx="{cx - ex + 3}" cy="{cy - 13}" r="4.5" fill="#fff"/>
      <circle cx="{cx + ex + 3}" cy="{cy - 13}" r="4.5" fill="#fff"/>
    </g>
    <path class="tash" fill="#1e1b4b" d="M{cx - 58} {cy + 30} C{cx - 40} {cy + 8} {cx - 12} {cy + 10} {cx} {cy + 20}
      C{cx + 12} {cy + 10} {cx + 40} {cy + 8} {cx + 58} {cy + 30} C{cx + 30} {cy + 22} {cx + 12} {cy + 26} {cx} {cy + 28}
      C{cx - 12} {cy + 26} {cx - 30} {cy + 22} {cx - 58} {cy + 30} Z"/>
    <path d="M{cx - 26} {cy + 46} Q{cx} {cy + 62} {cx + 26} {cy + 46}" stroke="#1e1b4b" stroke-width="7" fill="none" stroke-linecap="round"/>
  </g>'''


def main():
    n = len(TAGLINES)
    each = 3  # seconds per tagline
    lines = ''.join(f'<text class="tag" style="animation-delay:{i * each}s" x="330" y="205">{escape(t)}</text>'
                    for i, t in enumerate(TAGLINES))
    floaters = ''.join(
        f'<text class="float" style="animation-delay:{d}s" x="{x}" y="{y}" font-size="{fs}">{escape(t)}</text>'
        for t, x, y, fs, d in [('{ }', 880, 70, 34, 0), ('</>', 930, 200, 28, 1.2), ('#', 820, 250, 30, 2.1),
                               ('()', 760, 60, 26, 0.6), (';', 960, 120, 34, 1.8), ('[ ]', 700, 255, 26, 2.7)])
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#4f46e5"/><stop offset="0.55" stop-color="#7c3aed"/><stop offset="1" stop-color="#9333ea"/>
    </linearGradient>
    <linearGradient id="name" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0" stop-color="#ffffff"/><stop offset="0.5" stop-color="#fde68a"/><stop offset="1" stop-color="#facc15"/>
    </linearGradient>
  </defs>
  <style>
    .bob {{ animation: bob 3s ease-in-out infinite; }}
    @keyframes bob {{ 0%,100% {{ transform: translateY(0); }} 50% {{ transform: translateY(-7px); }} }}
    .blink {{ transform-box: fill-box; transform-origin: center; animation: blink 4s infinite; }}
    @keyframes blink {{ 0%,44%,50%,100% {{ transform: scaleY(1); }} 47% {{ transform: scaleY(0.1); }} }}
    .tash {{ transform-box: fill-box; transform-origin: center; animation: tash 4s infinite; }}
    @keyframes tash {{ 0%,70%,100% {{ transform: rotate(0); }} 74% {{ transform: rotate(-5deg); }} 78% {{ transform: rotate(5deg); }} 82% {{ transform: rotate(0); }} }}
    .title {{ font: 900 76px {FONT}; letter-spacing: 2px; animation: rise .9s ease-out both; }}
    .sub {{ font: 600 20px {FONT}; fill: #e9d5ff; animation: rise .9s .3s ease-out both; }}
    @keyframes rise {{ from {{ opacity: 0; transform: translateY(18px); }} to {{ opacity: 1; transform: none; }} }}
    .tag {{ font: 700 32px {FONT}; fill: #ffffff; opacity: 0; animation: tag {n * each}s infinite; }}
    @keyframes tag {{ 0% {{ opacity: 0; transform: translateY(14px); }} 4%,{100 / n - 4:.1f}% {{ opacity: 1; transform: none; }}
                      {100 / n:.1f}%,100% {{ opacity: 0; transform: translateY(-14px); }} }}
    .float {{ font-family: Consolas, monospace; font-weight: 700; fill: #ffffff; opacity: .16; animation: float 6s ease-in-out infinite; }}
    @keyframes float {{ 0%,100% {{ transform: translateY(0); }} 50% {{ transform: translateY(-12px); }} }}
    .cursor {{ animation: cur 1s steps(1) infinite; }}
    @keyframes cur {{ 50% {{ opacity: 0; }} }}
  </style>
  <rect width="{W}" height="{H}" rx="22" fill="url(#bg)"/>
  <circle cx="165" cy="140" r="118" fill="#ffffff" opacity="0.08"/>
  {floaters}
  {mascot(165, 140, 150)}
  <text class="title" x="326" y="118" fill="url(#name)">BYTE BHAI</text>
  <text class="sub" x="330" y="156">Python · Android · Shorts in Hinglish</text>
  {lines}
  <rect class="cursor" x="330" y="222" width="46" height="5" rx="2" fill="#facc15"/>
</svg>'''
    os.makedirs(os.path.join(ROOT, 'assets'), exist_ok=True)
    with open(os.path.join(ROOT, 'assets', 'header.svg'), 'w', encoding='utf-8', newline='\n') as f:
        f.write(svg)
    print('assets/header.svg written')


if __name__ == '__main__':
    main()
