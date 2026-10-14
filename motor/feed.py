"""Skriver feed.xml (RSS til podcast-apps) og index.html ud fra episoder.json."""

import html
from datetime import datetime
from email.utils import format_datetime
from pathlib import Path
from xml.sax.saxutils import escape


def _varighed(sek):
    sek = int(round(sek))
    return f"{sek // 3600:d}:{sek % 3600 // 60:02d}:{sek % 60:02d}"


def _beskrivelse_html(ep):
    dele = []
    if ep.get("beskrivelse"):
        dele.append(f"<p>{html.escape(ep['beskrivelse'])}</p>")
    if ep.get("kilder"):
        punkter = "".join(f"<li>{html.escape(k)}</li>" for k in ep["kilder"])
        dele.append(f"<p>Kilder:</p><ul>{punkter}</ul>")
    dele.append(f"<p><small>Stemmer: {html.escape(ep.get('motor_navn', ep['motor']))}. "
                "Indholdet er genereret med kunstig intelligens og kan indeholde fejl.</small></p>")
    return "".join(dele)


def skriv(rod, indst, episoder):
    rod = Path(rod)
    base = indst["adresse"].rstrip("/") + "/"
    eps = sorted(episoder, key=lambda e: e["udgivet"], reverse=True)
    nu = format_datetime(datetime.now().astimezone())

    items = []
    for ep in eps:
        dato = format_datetime(datetime.fromisoformat(ep["udgivet"]))
        url = base + ep["fil"]
        items.append(f"""    <item>
      <title>{escape(ep['titel'])}</title>
      <description><![CDATA[{_beskrivelse_html(ep)}]]></description>
      <enclosure url="{escape(url)}" length="{ep['bytes']}" type="audio/mpeg"/>
      <guid isPermaLink="false">{escape(ep['guid'])}</guid>
      <pubDate>{dato}</pubDate>
      <itunes:duration>{_varighed(ep['sekunder'])}</itunes:duration>
      <itunes:explicit>false</itunes:explicit>
    </item>""")

    feed = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>{escape(indst['titel'])}</title>
    <link>{escape(base)}</link>
    <atom:link href="{escape(base)}feed.xml" rel="self" type="application/rss+xml"/>
    <language>{indst.get('sprog', 'da')}</language>
    <description>{escape(indst['beskrivelse'])}</description>
    <itunes:author>{escape(indst['forfatter'])}</itunes:author>
    <itunes:summary>{escape(indst['beskrivelse'])}</itunes:summary>
    <itunes:image href="{escape(base)}cover.png"/>
    <image><url>{escape(base)}cover.png</url><title>{escape(indst['titel'])}</title><link>{escape(base)}</link></image>
    <itunes:category text="Health &amp; Fitness"><itunes:category text="Medicine"/></itunes:category>
    <itunes:explicit>false</itunes:explicit>
    <itunes:block>Yes</itunes:block>
    <lastBuildDate>{nu}</lastBuildDate>
{chr(10).join(items)}
  </channel>
</rss>
"""
    (rod / "feed.xml").write_text(feed, encoding="utf-8")

    raekker = []
    for ep in eps:
        dato = datetime.fromisoformat(ep["udgivet"]).strftime("%d.%m.%Y")
        raekker.append(f"""      <li>
        <div class="titel">{html.escape(ep['titel'])}</div>
        <div class="meta">{dato} · {int(ep['sekunder']) // 60}:{int(ep['sekunder']) % 60:02d} · {html.escape(ep.get('motor_navn', ep['motor']))}</div>
        <audio controls preload="none" src="{html.escape(ep['fil'])}"></audio>
      </li>""")
    side = f"""<!doctype html>
<html lang="da">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="robots" content="noindex, nofollow">
  <title>{html.escape(indst['titel'])}</title>
  <link rel="alternate" type="application/rss+xml" href="feed.xml">
  <style>
    :root {{ --bg:#f6f4ef; --fg:#1d2a2c; --mut:#5d6b6d; --kort:#ffffff; --streg:#dcd8cf; --acc:#1f6f6b; }}
    @media (prefers-color-scheme: dark) {{ :root {{ --bg:#121819; --fg:#e7ecec; --mut:#9aa8a9; --kort:#1b2324; --streg:#2c3739; --acc:#5fbdb6; }} }}
    body {{ margin:0; background:var(--bg); color:var(--fg); font:16px/1.5 system-ui, sans-serif; }}
    main {{ max-width:680px; margin:0 auto; padding:24px 16px 48px; }}
    h1 {{ margin:0 0 4px; font-size:1.6rem; }}
    p {{ color:var(--mut); }}
    .feed {{ display:block; padding:10px 12px; background:var(--kort); border:1px solid var(--streg); border-radius:8px; word-break:break-all; font-family:ui-monospace, monospace; font-size:.85rem; }}
    ul {{ list-style:none; padding:0; }}
    li {{ background:var(--kort); border:1px solid var(--streg); border-radius:10px; padding:14px; margin:12px 0; }}
    .titel {{ font-weight:600; }}
    .meta {{ color:var(--mut); font-size:.85rem; margin:2px 0 8px; }}
    audio {{ width:100%; }}
    a {{ color:var(--acc); }}
  </style>
</head>
<body>
  <main>
    <h1>{html.escape(indst['titel'])}</h1>
    <p>{html.escape(indst['beskrivelse'])}</p>
    <p>Abonnér i din podcast-app med denne adresse:</p>
    <code class="feed">{html.escape(base)}feed.xml</code>
    <ul>
{chr(10).join(raekker) or '      <li>Ingen afsnit endnu.</li>'}
    </ul>
  </main>
</body>
</html>
"""
    (rod / "index.html").write_text(side, encoding="utf-8")
