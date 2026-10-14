"""Indlæsning af manuskripter.

Format (UTF-8 tekstfil i manuskripter/):

    titel: Knude på halsen hos voksne
    beskrivelse: En eller to sætninger, der vises i podcast-appen.
    motor: roest            (valgfri; flere adskilles med komma)
    kilder:
    - Titel, udgiver, årstal, link
    ---
    VÆRT: Replik ...
    EKSPERT: Replik ...
    [pause 5]

Linjer uden rollenavn hænges på den forrige replik.
"""

import hashlib
import re
from dataclasses import dataclass, field
from pathlib import Path

PAUSE_RE = re.compile(r"^\[\s*pause\s+(\d+(?:[.,]\d+)?)\s*\]$", re.IGNORECASE)
REPLIK_RE = re.compile(r"^([A-Za-zÆØÅæøå][A-Za-zÆØÅæøå \-]{0,30}?)\s*:\s*(.*)$")
SAETNING_RE = re.compile(r"(?<=[.!?])\s+")


@dataclass
class Replik:
    rolle: str
    tekst: str


@dataclass
class Pause:
    sekunder: float


@dataclass
class Manuskript:
    sti: Path
    titel: str
    beskrivelse: str = ""
    motorer: list = field(default_factory=list)
    kilder: list = field(default_factory=list)
    dele: list = field(default_factory=list)
    fingeraftryk: str = ""

    @property
    def antal_tegn(self):
        return sum(len(d.tekst) for d in self.dele if isinstance(d, Replik))


def laes(sti, roller):
    sti = Path(sti)
    raa = sti.read_text(encoding="utf-8").replace("\r\n", "\n")
    linjer = raa.split("\n")
    try:
        skel = next(i for i, l in enumerate(linjer) if l.strip() == "---")
    except StopIteration:
        raise ValueError(f"{sti.name}: mangler en linje med --- mellem hoved og dialog")

    hoved = {}
    kilder = []
    aktuel = None
    for linje in linjer[:skel]:
        s = linje.strip()
        if not s:
            continue
        if s.startswith("- ") and aktuel == "kilder":
            kilder.append(s[2:].strip())
            continue
        if ":" in s:
            k, v = s.split(":", 1)
            aktuel = k.strip().lower()
            if v.strip():
                hoved[aktuel] = v.strip()
    if "titel" not in hoved:
        raise ValueError(f"{sti.name}: mangler 'titel:'")

    gyldige = {r.upper() for r in roller}
    dele = []
    for nr, linje in enumerate(linjer[skel + 1:], start=skel + 2):
        s = linje.strip()
        if not s:
            continue
        m = PAUSE_RE.match(s)
        if m:
            dele.append(Pause(float(m.group(1).replace(",", "."))))
            continue
        m = REPLIK_RE.match(s)
        if m and m.group(1).strip().upper() in gyldige:
            tekst = m.group(2).strip()
            dele.append(Replik(m.group(1).strip().upper(), tekst))
            continue
        if dele and isinstance(dele[-1], Replik):
            dele[-1].tekst = (dele[-1].tekst + " " + s).strip()
            continue
        raise ValueError(f"{sti.name} linje {nr}: ukendt rolle eller tekst uden rolle: {s[:60]}")

    dele = [d for d in dele if not (isinstance(d, Replik) and not d.tekst)]
    if not any(isinstance(d, Replik) for d in dele):
        raise ValueError(f"{sti.name}: ingen repliker fundet")

    motorer = [m.strip().lower() for m in hoved.get("motor", "").split(",") if m.strip()]
    return Manuskript(
        sti=sti,
        titel=hoved["titel"],
        beskrivelse=hoved.get("beskrivelse", ""),
        motorer=motorer,
        kilder=kilder,
        dele=dele,
        fingeraftryk=hashlib.sha256(raa.encode("utf-8")).hexdigest()[:8],
    )


def saetninger(tekst, maks=220, kort=30):
    """Deler en replik i sætninger. Lange sætninger deles ved komma, korte slås sammen."""
    dele = [d.strip() for d in SAETNING_RE.split(tekst) if d.strip()]
    ud = []
    for d in dele:
        while len(d) > maks:
            snit = d.rfind(", ", 0, maks)
            if snit < 40:
                snit = d.rfind(" ", 0, maks)
            if snit < 20:
                snit = maks
            ud.append(d[: snit + 1].strip())
            d = d[snit + 1:].strip()
        if d:
            ud.append(d)
    samlet = []
    for d in ud:
        if samlet and len(samlet[-1]) < kort and len(samlet[-1]) + len(d) + 1 <= maks:
            samlet[-1] = samlet[-1] + " " + d
        else:
            samlet.append(d)
    return samlet
