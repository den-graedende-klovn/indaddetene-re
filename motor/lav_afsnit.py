"""Laver afsnit for alle nye eller ændrede manuskripter og opdaterer feedet.

    python motor/lav_afsnit.py            laver det, der mangler
    python motor/lav_afsnit.py --behov    skriver kun hvilke motorer der skal bruges
    python motor/lav_afsnit.py --motor test   tvinger én motor (til afprøvning)
"""

import argparse
import json
import platform
import sys
import time
import traceback
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import feed  # noqa: E402
import lyd  # noqa: E402
from manuskript import Pause, laes  # noqa: E402
from motorer import MOTORER  # noqa: E402

ROD = Path(__file__).resolve().parent.parent


def indlaes_json(sti, standard):
    try:
        return json.loads(Path(sti).read_text(encoding="utf-8"))
    except FileNotFoundError:
        return standard


def gem_json(sti, data):
    Path(sti).write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def planlaeg(indst, episoder, tving_motor=None):
    """Returnerer (opgaver, forventede_id, fejl)."""
    opgaver, forventede, fejl = [], set(), []
    efter_id = {e["id"]: e for e in episoder}
    for sti in sorted((ROD / "manuskripter").glob("*.txt")):
        try:
            m = laes(sti, indst["roller"])
        except Exception as e:  # noqa: BLE001
            fejl.append({"manuskript": sti.name, "fejl": str(e)})
            # behold eventuelle eksisterende afsnit fra en tidligere, gyldig version
            forventede.update(i for i in efter_id if efter_id[i]["manuskript"] == sti.name)
            continue
        motorer = [tving_motor] if tving_motor else (m.motorer or [indst["standardmotor"]])
        for motor in motorer:
            if motor not in MOTORER:
                fejl.append({"manuskript": sti.name, "fejl": f"ukendt motor: {motor}"})
                continue
            ep_id = sti.stem if len(motorer) == 1 else f"{sti.stem}-{motor}"
            forventede.add(ep_id)
            gammel = efter_id.get(ep_id)
            if gammel and gammel.get("fingeraftryk") == m.fingeraftryk and gammel.get("motor") == motor:
                continue
            opgaver.append({"id": ep_id, "motor": motor, "manus": m, "flere": len(motorer) > 1})
    return opgaver, forventede, fejl


def byg_lyd(manus, motor, indst):
    p = indst["pauser"]
    stykker = [lyd.stilhed(p["start"])]
    forrige = None
    for d in manus.dele:
        if isinstance(d, Pause):
            stykker.append(lyd.stilhed(d.sekunder))
            forrige = None
            continue
        if forrige is not None:
            stykker.append(lyd.stilhed(p["samme_taler"] if forrige == d.rolle else p["ny_taler"]))
        stemme = indst["roller"][d.rolle][motor.navn]
        stykker.append(motor.tal_replik(d.tekst, stemme))
        forrige = d.rolle
    stykker.append(lyd.stilhed(p["slut"]))
    import numpy as np

    return np.concatenate(stykker)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--behov", action="store_true")
    ap.add_argument("--motor")
    args = ap.parse_args()

    indst = indlaes_json(ROD / "indstillinger.json", None)
    episoder = indlaes_json(ROD / "episoder.json", [])
    opgaver, forventede, fejl = planlaeg(indst, episoder, args.motor)

    if args.behov:
        print(" ".join(sorted({o["motor"] for o in opgaver})))
        return 0

    status = {
        "start": datetime.now().astimezone().isoformat(timespec="seconds"),
        "maskine": f"{platform.node()} ({platform.processor() or platform.machine()})",
        "afsnit": [],
        "motorer": {},
        "fejl": fejl,
    }

    # Fjern afsnit, hvis manuskript er slettet
    for ep in [e for e in episoder if e["id"] not in forventede]:
        (ROD / ep["fil"]).unlink(missing_ok=True)
        episoder.remove(ep)
        status["afsnit"].append({"id": ep["id"], "handling": "fjernet"})

    instanser = {}
    for opg in opgaver:
        navn = opg["motor"]
        try:
            if navn not in instanser:
                t0 = time.time()
                instanser[navn] = MOTORER[navn](indst)
                status["motorer"][navn] = {"opstart_sekunder": round(time.time() - t0, 1)}
            motor = instanser[navn]
            m = opg["manus"]
            t0 = time.time()
            x = byg_lyd(m, motor, indst)
            fil = f"afsnit/{opg['id']}-{m.fingeraftryk}.mp3"
            titel = m.titel + (f" ({motor.visningsnavn})" if opg["flere"] else "")
            bytes_ = lyd.gem_mp3(x, ROD / fil, titel, indst["titel"])
            sekunder = x.size / lyd.SR

            gammel = next((e for e in episoder if e["id"] == opg["id"]), None)
            if gammel:
                if gammel["fil"] != fil:
                    (ROD / gammel["fil"]).unlink(missing_ok=True)
                episoder.remove(gammel)
            episoder.append({
                "id": opg["id"],
                "guid": f"{opg['id']}-{m.fingeraftryk}",
                "titel": titel,
                "beskrivelse": m.beskrivelse,
                "kilder": m.kilder,
                "manuskript": m.sti.name,
                "fingeraftryk": m.fingeraftryk,
                "motor": navn,
                "motor_navn": motor.visningsnavn,
                "fil": fil,
                "bytes": bytes_,
                "sekunder": round(sekunder, 1),
                "udgivet": gammel["udgivet"] if gammel else datetime.now().astimezone().isoformat(timespec="seconds"),
            })
            status["afsnit"].append({
                "id": opg["id"], "handling": "lavet", "motor": navn,
                "lyd_sekunder": round(sekunder, 1), "tegn": m.antal_tegn,
                "beregning_sekunder": round(time.time() - t0, 1),
            })
            print(f"OK  {opg['id']} ({navn}): {sekunder:.0f} s lyd på {time.time() - t0:.0f} s", flush=True)
        except Exception as e:  # noqa: BLE001
            traceback.print_exc()
            status["fejl"].append({"afsnit": opg["id"], "motor": navn, "fejl": f"{type(e).__name__}: {e}"})

    for navn, motor in instanser.items():
        status["motorer"][navn].update(motor.stat.som_dict())

    gem_json(ROD / "episoder.json", sorted(episoder, key=lambda e: e["udgivet"]))
    feed.skriv(ROD, indst, episoder)
    status["slut"] = datetime.now().astimezone().isoformat(timespec="seconds")
    gem_json(ROD / "status.json", status)
    for f in status["fejl"]:
        print("FEJL", f, flush=True)
    return 1 if status["fejl"] else 0


if __name__ == "__main__":
    sys.exit(main())
