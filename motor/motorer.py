"""Talemotorer. Hver motor har tal_replik(tekst, stemme) -> numpy float32 ved lyd.SR."""

import asyncio
import os
import tempfile
import time
from pathlib import Path

import numpy as np

import lyd
from manuskript import saetninger

TEGN_PR_SEKUND = 14.0  # cirka taletempo på dansk


def forventet_varighed(tekst):
    return max(1.0, len(tekst) / TEGN_PR_SEKUND)


class Statistik:
    def __init__(self):
        self.lyd_sek = 0.0
        self.beregning_sek = 0.0
        self.genforsoeg = 0

    def som_dict(self):
        rtf = self.beregning_sek / self.lyd_sek if self.lyd_sek else None
        return {
            "lyd_sekunder": round(self.lyd_sek, 1),
            "beregning_sekunder": round(self.beregning_sek, 1),
            "beregning_pr_lydminut": round(rtf * 60, 1) if rtf else None,
            "genforsoeg": self.genforsoeg,
        }


class TestMotor:
    """Toner i stedet for tale. Kun til at afprøve kæden uden netadgang."""

    navn = "test"
    visningsnavn = "Testtoner"

    def __init__(self, indst):
        self.indst = indst
        self.stat = Statistik()

    def tal_replik(self, tekst, stemme):
        t0 = time.time()
        stykker = []
        for s in saetninger(tekst):
            n = int(lyd.SR * forventet_varighed(s))
            t = np.arange(n) / lyd.SR
            f = 220.0 if stemme == "dyb" else 440.0
            stykker.append(0.3 * np.sin(2 * np.pi * f * t).astype(np.float32))
            stykker.append(lyd.stilhed(self.indst["pauser"]["mellem_saetninger"]))
        x = np.concatenate(stykker[:-1])
        self.stat.lyd_sek += x.size / lyd.SR
        self.stat.beregning_sek += time.time() - t0
        return x


class EdgeMotor:
    """Microsofts neurale stemmer via edge-tts (uofficiel adgang, ingen nøgle)."""

    navn = "edge"
    visningsnavn = "Edge"

    def __init__(self, indst):
        import edge_tts  # noqa: F401

        self.indst = indst
        self.stat = Statistik()

    def tal_replik(self, tekst, stemme):
        import edge_tts

        t0 = time.time()
        with tempfile.TemporaryDirectory() as tmp:
            sti = Path(tmp) / "replik.mp3"
            for forsoeg in range(4):
                try:
                    kom = edge_tts.Communicate(tekst, stemme, rate=self.indst["edge"]["hastighed"])
                    asyncio.run(kom.save(str(sti)))
                    break
                except Exception:
                    if forsoeg == 3:
                        raise
                    self.stat.genforsoeg += 1
                    time.sleep(3 * (forsoeg + 1))
            x = lyd.trim(lyd.afkod(sti))
        self.stat.lyd_sek += x.size / lyd.SR
        self.stat.beregning_sek += time.time() - t0
        return x


class RoestMotor:
    """Røst v3 (CoRal-projektet), dansk finjustering af Chatterbox. Kører på processoren."""

    navn = "roest"
    visningsnavn = "Røst"
    FILER = [
        "ve.pt",
        "t3_mtl23ls_v2.safetensors",
        "s3gen.pt",
        "grapheme_mtl_merged_expanded_v1.json",
        "conds.pt",
        "Cangjie5_TC.json",
        "audio_samples/00_*",
    ]

    def __init__(self, indst):
        import torch
        from huggingface_hub import snapshot_download
        from chatterbox.mtl_tts import ChatterboxMultilingualTTS

        self.torch = torch
        self.indst = indst
        self.p = indst["roest"]
        self.stat = Statistik()
        torch.set_num_threads(os.cpu_count() or 4)

        t0 = time.time()
        mappe = Path(snapshot_download(self.p["model"], allow_patterns=self.FILER))
        self.model = ChatterboxMultilingualTTS.from_local(mappe, device="cpu")
        self.stemmer = {}
        for navn in ("mic", "nic"):
            proever = sorted((mappe / "audio_samples").glob(f"00_{navn}_*.wav"))
            if not proever:
                raise RuntimeError(f"Fandt ingen stemmeprøver for {navn}")
            ref = np.concatenate([lyd.trim(lyd.afkod(p)) for p in proever])
            with tempfile.TemporaryDirectory() as tmp:
                ref_sti = Path(tmp) / f"{navn}.wav"
                lyd.gem_wav(ref, ref_sti)
                self.model.prepare_conditionals(str(ref_sti), exaggeration=self.p["exaggeration"])
            self.stemmer[navn] = self.model.conds
        self.indlaesning_sek = time.time() - t0

    def _generer(self, tekst, seed):
        self.torch.manual_seed(seed)
        wav = self.model.generate(
            tekst,
            language_id="da",
            exaggeration=self.p["exaggeration"],
            cfg_weight=self.p["cfg_weight"],
            temperature=self.p["temperature"],
            repetition_penalty=self.p["repetition_penalty"],
            min_p=self.p["min_p"],
            top_p=self.p["top_p"],
        )
        return lyd.trim(wav.squeeze(0).cpu().numpy().astype(np.float32))

    def _saetning(self, tekst, stemme):
        """Genererer én sætning og prøver igen, hvis længden er urimelig (fx løbsk generering),
        eller hvis modellen fejler. Det sker af og til ved meget korte replikker som "Et.",
        hvor modellen ikke laver nogen lydbidder."""
        forventet = forventet_varighed(tekst)
        bedst, bedst_afvig, sidste_fejl = None, None, None
        for forsoeg in range(4):
            try:
                x = self._generer(tekst, seed=1000 + forsoeg)
            except Exception as e:  # noqa: BLE001
                sidste_fejl = e
                self.stat.genforsoeg += 1
                continue
            varighed = x.size / lyd.SR
            if 0.4 * forventet <= varighed <= 2.2 * forventet + 1.5:
                return x
            self.stat.genforsoeg += 1
            afvig = abs(np.log(max(varighed, 0.05) / forventet))
            if bedst is None or afvig < bedst_afvig:
                bedst, bedst_afvig = x, afvig
        if bedst is None or bedst.size == 0:
            raise RuntimeError(f"Røst kunne ikke lave lyd til {tekst!r}: {sidste_fejl}")
        return bedst

    def tal_replik(self, tekst, stemme):
        t0 = time.time()
        self.model.conds = self.stemmer[stemme]
        pause = lyd.stilhed(self.indst["pauser"]["mellem_saetninger"])
        stykker = []
        for s in saetninger(tekst, maks=self.p["maks_saetning"]):
            stykker.append(self._saetning(s, stemme))
            stykker.append(pause)
        x = np.concatenate(stykker[:-1]) if stykker else lyd.stilhed(0.1)
        self.stat.lyd_sek += x.size / lyd.SR
        self.stat.beregning_sek += time.time() - t0
        return x


MOTORER = {m.navn: m for m in (RoestMotor, EdgeMotor, TestMotor)}
