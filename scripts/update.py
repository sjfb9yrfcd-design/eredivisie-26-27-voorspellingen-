#!/usr/bin/env python3
"""Haalt de actuele Eredivisie-stand op van NOS Teletekst (pagina 819)
en werkt het data-blok in index.html bij (punten en aantal gespeelde wedstrijden)."""
import datetime, html, json, os, re, sys, urllib.request
from zoneinfo import ZoneInfo

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INDEX = os.path.join(ROOT, "index.html")
URLS = [os.environ["TELETEKST_URL"]] if os.environ.get("TELETEKST_URL") else [
    "https://nos.nl/teletekst/819",
    "https://teletekst-data.nos.nl/json/819",
    "https://teletekst.nos.nl/819",
]
ROW = re.compile(r"^\s*(\d{1,2})\.\s+(.+?)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s*-\s*(\d+)\s*$")
BLOCK = re.compile(r'(<script id="data" type="application/json">)(.*?)(</script>)', re.S)


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (kampioen-site updater)"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", "replace")


def to_text(raw):
    try:
        j = json.loads(raw)
        raw = j.get("content", raw) if isinstance(j, dict) else raw
    except ValueError:
        pass
    text = re.sub(r"<[^>]+>", "", raw)
    return html.unescape(text).replace("\xa0", " ")


def parse(text):
    table = {}
    for line in text.splitlines():
        m = ROW.match(line)
        if not m:
            continue
        pos, name, played, w, d, l, pts = (m.group(1), m.group(2).strip(), *map(int, m.groups()[2:7]))
        if w + d + l != played or 3 * w + d != pts:
            raise ValueError(f"Rij klopt niet intern: {line!r}")
        table[name] = {"played": played, "points": pts}
    if len(table) != 18:
        raise ValueError(f"Verwacht 18 clubs, gevonden {len(table)}")
    return table


def get_table():
    errors = []
    for url in URLS:
        try:
            return parse(to_text(fetch(url)))
        except Exception as e:  # noqa: BLE001
            errors.append(f"{url}: {e}")
    sys.exit("Stand ophalen mislukt:\n" + "\n".join(errors))


def main():
    table = get_table()
    src = open(INDEX, encoding="utf-8").read()
    m = BLOCK.search(src)
    data = json.loads(m.group(2))
    changed = False
    for club, c in data["clubs"].items():
        if club not in table:
            sys.exit(f"{club} staat niet in de teletekststand")
        new = table[club]
        if new["played"] < c["played"]:
            sys.exit(f"{club}: minder wedstrijden dan eerder ({new['played']} < {c['played']}); niets aangepast")
        if new != {"played": c["played"], "points": c["points"]}:
            c["played"], c["points"] = new["played"], new["points"]
            changed = True
    if not changed:
        print("Geen wijzigingen")
        return
    data["updated"] = datetime.datetime.now(ZoneInfo("Europe/Amsterdam")).date().isoformat()
    block = m.group(1) + "\n" + json.dumps(data, ensure_ascii=False, indent=1) + "\n" + m.group(3)
    open(INDEX, "w", encoding="utf-8").write(src[:m.start()] + block + src[m.end():])
    print("Bijgewerkt:", {k: v for k, v in table.items() if k in data["clubs"]})


if __name__ == "__main__":
    main()
