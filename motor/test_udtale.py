"""Tjek af udtalelaget. Kør: python motor/test_udtale.py"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from udtale import Undtagelser, omskriv_ord, til_tale  # noqa: E402

# Eksempler fra Anatomionline, "Regler om udtale"
ANATOMIONLINE = {
    "caecum": "sækum",
    "foetus": "føtus",
    "cella": "sella",
    "cystis": "systis",
    "caput": "kaput",
    "crista": "krista",
    "coccygis": "koksygis",
    "saccus": "sakkus",
    "fascia": "fasia",
    "sclerus": "sklerus",
    "disci": "diski",
    "brachium": "brakium",
    "pharynx": "farynks",
    "maxilla": "maksilla",
    "zygoma": "sygoma",
}

# Øre-næse-hals-termer
OENH = {
    "oropharynx": "orofarynks",
    "cochlea": "koklea",
    "concha": "konka",
    "processus": "prosessus",
    "facialis": "fasialis",
    "vestibulocochlearis": "vestibulokoklearis",
    "oesophagus": "øsofagus",
    "thyroidea": "tyroidea",
    "carcinoma": "karsinoma",
    "rhinitis": "rinitis",
    "catarrhalis": "katarralis",
    "otosclerosis": "otosklerosis",
    "musculus": "muskulus",
    "cholesteatoma": "kolesteatoma",
    "Streptococcus": "Streptokokkus",
    "pneumoniae": "pneumoniæ",
    "aeruginosa": "æruginosa",
    "Haemophilus": "Hæmofilus",
    "schwannom": "sjvannom",
    "ischias": "iskias",
}

# Danske ord, der ikke må ændres
URORT = [
    "forhøjet", "ophold", "koen", "broen", "temaer", "dataenhed", "anaerob", "aerob",
    "operation", "station", "case", "cases", "check", "chef", "computertomografi",
    "scintigrafi", "nethinde", "forhold", "patientens", "glandula", "submandibularis",
]


def main():
    fejl = []
    for o, f in {**ANATOMIONLINE, **OENH}.items():
        r = omskriv_ord(o)
        if r != f:
            fejl.append(f"regel: {o} -> {r}, forventet {f}")

    und = Undtagelser(Path("/dev/null"))
    for o in URORT:
        r, _ = til_tale(o, und=und)
        if r != o and o not in ("scintigrafi", "computertomografi"):
            fejl.append(f"dansk ord ændret: {o} -> {r}")
    # scintigrafi ender på -i og behandles som latin, men sc foran i giver s, som er dansk udtale
    if til_tale("scintigrafi", und=und)[0] != "sintigrafi":
        fejl.append("scintigrafi skal blive til sintigrafi")

    # Undtagelser: forrang, beskyttelse, flere ord, jokertegn og store bogstaver
    import tempfile

    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as f:
        f.write("oropharynx = oro-farynks\nnervus vestibulocochlearis = nervus vestibulo-koklearis\n"
                "cochle* = kokle\nfascia = fascia\nlatin: caput\nMenière* = menjær\n")
    und = Undtagelser(Path(f.name))
    tilfaelde = {
        "Oropharynx og larynx.": "Oro-farynks og larynks.",
        "Nervus vestibulocochlearis.": "Nervus vestibulo-koklearis.",
        "Et cochleaimplantat.": "Et kokleaimplantat.",
        "Fascia og cella.": "Fascia og sella.",
        "Caput.": "Kaput.",
        "Ménière og Menières sygdom.": "Menjær og Menjærs sygdom.",
    }
    for o, f_ in tilfaelde.items():
        r, _ = til_tale(o, und=und)
        if r != f_:
            fejl.append(f"undtagelse: {o!r} -> {r!r}, forventet {f_!r}")
    if til_tale("Oropharynx.", regler=False, und=und)[0] != "Oro-farynks.":
        fejl.append("undtagelser skal virke, selvom reglerne er slået fra")

    for linje in fejl:
        print("FEJL", linje)
    print(f"{len(fejl)} fejl")
    return 1 if fejl else 0


if __name__ == "__main__":
    sys.exit(main())
