"""Udtalelag: omskriver latinske og medicinske ord til dansk lydskrift lige før talesyntesen.

Manuskripterne og shownotes beholder den korrekte stavning. Kun teksten, der
sendes til talemotoren, ændres.

To lag, i denne rækkefølge:
1. Undtagelser fra udtale/undtagelser.txt (håndlavet liste). Har altid forrang,
   og en undtagelse bliver ikke omskrevet yderligere af reglerne.
2. Generelle regler for dansk udtale af latin, efter Anatomionline, "Regler om
   udtale" (https://www.anatomionline.dk/regler-om-udtale/). Reglerne bruges kun
   på ord, der ligner latin (se er_latin), så almindelige danske ord ikke røres.

Afprøvning:
    python motor/udtale.py "Sidder den i oropharynx eller i glandula submandibularis?"
    python motor/udtale.py manuskripter/2026-10-16-vestibulaer-paroksysmi.txt
"""

import re
import sys
import unicodedata
from pathlib import Path

ROD = Path(__file__).resolve().parent.parent
UNDTAGELSESFIL = ROD / "udtale" / "undtagelser.txt"

L = "A-Za-zÆØÅæøåÄäÖöÜüÉéÈèËëÏïÁáÍíÓóÚúÀàÂâÊêÎîÔôÛû"
ORD_RE = re.compile(f"[{L}]+")
FORTUNGE = "eiyæø"  # e, i, y samt ae og oe, efter at de er skrevet om til æ og ø

# Et ord behandles som latin, hvis det er mindst 5 bogstaver og ender sådan.
# Endelser, der er almindelige i danske ord (-e, -er, -en, -es, -ens, -ion), er bevidst udeladt.
LATINSKE_ENDELSER = (
    "a", "ae", "i", "io", "is", "us", "um", "or", "om", "ose", "osis",
    "ax", "ex", "ix", "yx", "nx",
)
MIN_LAENGDE = 5

# Reglerne anvendes i rækkefølge på ét ord ad gangen (små bogstaver).
REGLER = [
    # Anatomionline: z i schizo- udtales ts.
    (r"schiz", "skits"),
    # Supplement: tysk sch i egennavne, fx Schwann og schwannom.
    (r"schw", "sjv"),
    # Anatomionline: ae som æ (caecum), men ikke i aero- (luft), hvor vokalerne udtales hver for sig.
    (r"ae(?!ro)", "æ"),
    # Anatomionline: oe som ø (foetus).
    (r"oe", "ø"),
    # Anatomionline: ch som k (brachium).
    (r"ch", "k"),
    # Anatomionline: ph som f (pharynx).
    (r"ph", "f"),
    # Supplement, ikke på siden: th som t (thorax), rh som r i ordstart og efter r (rhinitis, catarrhalis), qu som kv.
    (r"th", "t"),
    (r"^rh", "r"),
    (r"rrh", "rr"),
    (r"qu", "kv"),
    # Anatomionline: sci i endelser som ski (disci).
    (r"sci$", "ski"),
    # Anatomionline: sc foran e, i, y, ae, oe som s (fascia), ellers sk (sclerus).
    (rf"sc(?=[{FORTUNGE}])", "s"),
    (r"sc", "sk"),
    # Anatomionline: cc foran e, i, y, ae, oe som ks (coccygis), ellers kk (saccus).
    (rf"cc(?=[{FORTUNGE}])", "ks"),
    (r"cc", "kk"),
    # Anatomionline: c foran e, i, y, ae, oe som s (cella, cystis), ellers k (caput, crista).
    (rf"c(?=[{FORTUNGE}])", "s"),
    (r"c", "k"),
    # Anatomionline: x som ks (maxilla), z som s (zygoma).
    (r"x", "ks"),
    (r"z", "s"),
]
REGLER = [(re.compile(m), e) for m, e in REGLER]


# Accenter ignoreres i undtagelser, så "Menière" også rammer "Ménière". æ, ø og å er egne bogstaver.
_VARIANTER = {
    "a": "aáàâäã", "e": "eéèêë", "i": "iíìîï", "o": "oóòôõö", "u": "uúùûü", "y": "yýÿü", "c": "cç", "n": "nñ",
}


def _bogstav(t):
    if t.lower() in "æøå":
        return re.escape(t)
    grund = unicodedata.normalize("NFKD", t.lower())[0]
    return f"[{_VARIANTER[grund]}]" if grund in _VARIANTER else re.escape(t)


class Undtagelser:
    def __init__(self, sti=UNDTAGELSESFIL):
        self.erstatninger = []  # (regex, erstatning)
        self.latin = set()
        if not Path(sti).exists():
            return
        for nr, linje in enumerate(Path(sti).read_text(encoding="utf-8").splitlines(), start=1):
            s = linje.split("#", 1)[0].strip()
            if not s:
                continue
            if s.lower().startswith("latin:"):
                self.latin.update(o.strip().lower() for o in s[6:].split(",") if o.strip())
                continue
            if "=" not in s:
                raise ValueError(f"udtale/undtagelser.txt linje {nr}: mangler '=': {s}")
            term, udtale = (d.strip() for d in s.split("=", 1))
            if not term or not udtale:
                raise ValueError(f"udtale/undtagelser.txt linje {nr}: tom side af '=': {s}")
            self.erstatninger.append((self._monster(term), udtale.strip("*"), term))
        # Længste først, så "nervus vestibulocochlearis" vinder over "nervus".
        self.erstatninger.sort(key=lambda t: -len(t[2]))

    @staticmethod
    def _monster(term):
        start_fri, slut_fri = term.startswith("*"), term.endswith("*")
        kerne = r"\s+".join("".join(_bogstav(t) for t in d) for d in term.strip("*").split())
        foer = "" if start_fri else f"(?<![{L}])"
        efter = "" if slut_fri else f"(?![{L}])"
        return re.compile(foer + kerne + efter, re.IGNORECASE)


_undtagelser = None


def undtagelser():
    global _undtagelser
    if _undtagelser is None:
        _undtagelser = Undtagelser()
    return _undtagelser


def er_latin(ord_lav, ekstra_latin=frozenset()):
    if ord_lav in ekstra_latin:
        return True
    return len(ord_lav) >= MIN_LAENGDE and ord_lav.endswith(LATINSKE_ENDELSER)


def omskriv_ord(ord_):
    lav = ord_.lower()
    for monster, erstatning in REGLER:
        lav = monster.sub(erstatning, lav)
    return _samme_forbogstav(ord_, lav)


def _samme_forbogstav(original, ny):
    if original[:1].isupper() and ny:
        return ny[0].upper() + ny[1:]
    return ny


def til_tale(tekst, regler=True, und=None):
    """Returnerer (tekst til talemotoren, {original: udtale})."""
    und = und or undtagelser()
    aendringer = {}

    # Lag 1: undtagelser. Erstattede stykker beskyttes mod reglerne.
    stykker = [(tekst, False)]
    for monster, erstatning, _ in und.erstatninger:
        nye = []
        for s, beskyttet in stykker:
            if beskyttet:
                nye.append((s, True))
                continue
            pos = 0
            for m in monster.finditer(s):
                ny = _samme_forbogstav(m.group(0), erstatning)
                nye.append((s[pos:m.start()], False))
                nye.append((ny, True))
                if ny != m.group(0):
                    aendringer[m.group(0)] = ny
                pos = m.end()
            nye.append((s[pos:], False))
        stykker = [(s, b) for s, b in nye if s]

    # Lag 2: regler for latinske ord.
    ud = []
    for s, beskyttet in stykker:
        if beskyttet or not regler:
            ud.append(s)
            continue

        def erstat(m):
            o = m.group(0)
            if not er_latin(o.lower(), und.latin):
                return o
            ny = omskriv_ord(o)
            if ny != o:
                aendringer[o] = ny
            return ny

        ud.append(ORD_RE.sub(erstat, s))
    return "".join(ud), aendringer


def _main(argv):
    if not argv:
        print(__doc__)
        return 1
    arg = " ".join(argv)
    sti = Path(arg)
    if sti.suffix == ".txt" and sti.exists():
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import json

        from manuskript import Replik, laes

        roller = json.loads((ROD / "indstillinger.json").read_text(encoding="utf-8"))["roller"]
        m = laes(sti, roller)
        alle = {}
        for d in m.dele:
            if isinstance(d, Replik):
                if m.udtale:
                    alle.update(til_tale(d.tekst)[1])
        for o, n in sorted(alle.items(), key=lambda t: t[0].lower()):
            print(f"{o:35} -> {n}")
        print(f"\n{len(alle)} ord ændret" + ("" if m.udtale else " (udtale: fra i manuskriptet)"))
        return 0
    tale, aendr = til_tale(arg)
    print(tale)
    for o, n in aendr.items():
        print(f"  {o} -> {n}")
    return 0


if __name__ == "__main__":
    sys.exit(_main(sys.argv[1:]))
