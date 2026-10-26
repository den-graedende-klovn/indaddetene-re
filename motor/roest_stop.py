"""Rettelse af Røsts stopmekanisme, så sætningernes sidste stavelse ikke klippes af.

Den flersprogede Chatterbox-model, som Røst bygger på, har en "AlignmentStreamAnalyzer",
der tvinger generationen til at stoppe, hvis den tror, modellen er gået i stå. Den er for
streng (chatterbox-tts 0.1.7):

1. Gentagelse: stop allerede ved to ens lydbidder i træk, også midt i sætningen.
   Lange vokaler og bløde endelser giver ofte to ens bidder.
2. Lang hale: stop, når de sidste tre tegn har varet over 5 rammer (0,2 sekunder).
   En dansk slutstavelse varer tit længere.
3. Hver kørsel tilføjer nye "hooks" til modellen uden at fjerne de gamle.

Kendt hos andre:
- https://github.com/resemble-ai/chatterbox/issues/519
- https://github.com/jamiepine/voicebox/issues/587 (forslaget til gentagelsesreglen nedenfor)

`step` er kopieret fra chatterbox (MIT-licens, Resemble AI) og ændret, så grænserne kan
indstilles. Tilstanden "original" genskaber den oprindelige opførsel til sammenligning.
"""

import logging

import torch

log = logging.getLogger(__name__)

TILSTANDE = {
    # lang_hale: rammer à 40 ms; gentagelser: antal ens lydbidder i træk;
    # kraev_komplet: gentagelser stopper kun, når hele teksten er nået.
    "original": {"lang_hale": 5, "gentagelser": 2, "kraev_komplet": False},
    "lempelig": {"lang_hale": 15, "gentagelser": 3, "kraev_komplet": True},
}

_tilstand = dict(TILSTANDE["lempelig"])
_hooks = []
_installeret = False
taellere = {"lang_hale": 0, "justering": 0, "gentagelse": 0, "fejl_i_rettelse": 0}


def saet(navn):
    if navn not in TILSTANDE:
        raise ValueError(f"ukendt stop-tilstand: {navn} (brug {', '.join(TILSTANDE)})")
    _tilstand.clear()
    _tilstand.update(TILSTANDE[navn])


def installer():
    """Lapper AlignmentStreamAnalyzer. Kaldes én gang, efter at chatterbox er importeret."""
    global _installeret
    if _installeret:
        return
    from chatterbox.models.t3.inference import alignment_stream_analyzer as asa

    klasse = asa.AlignmentStreamAnalyzer
    original_init = klasse.__init__
    original_step = klasse.step

    def __init__(self, *args, **kwargs):
        # Fjern de forrige kørslers hooks, før der sættes nye.
        while _hooks:
            _hooks.pop().remove()
        original_init(self, *args, **kwargs)

    def _add_attention_spy(self, tfmr, buffer_idx, layer_idx, head_idx):
        def hook(module, input, output):
            if isinstance(output, tuple) and len(output) > 1 and output[1] is not None:
                self.last_aligned_attns[buffer_idx] = output[1][0, head_idx].cpu()

        target = tfmr.layers[layer_idx].self_attn
        _hooks.append(target.register_forward_hook(hook))
        if hasattr(tfmr, "config") and hasattr(tfmr.config, "output_attentions"):
            self.original_output_attentions = tfmr.config.output_attentions
            self.original_attn_implementation = getattr(tfmr.config, "_attn_implementation", None)
            if getattr(tfmr.config, "_attn_implementation", None) == "sdpa":
                tfmr.config._attn_implementation = "eager"
            tfmr.config.output_attentions = True

    def step(self, logits, next_token=None):
        try:
            return _step(self, logits, next_token)
        except Exception:  # noqa: BLE001
            taellere["fejl_i_rettelse"] += 1
            log.exception("Fejl i rettet stopmekanisme, bruger den oprindelige")
            return original_step(self, logits, next_token)

    klasse.__init__ = __init__
    klasse._add_attention_spy = _add_attention_spy
    klasse.step = step
    _installeret = True


def _step(self, logits, next_token=None):
    t = _tilstand
    aligned_attn = torch.stack(self.last_aligned_attns).mean(dim=0)
    i, j = self.text_tokens_slice
    if self.curr_frame_pos == 0:
        A_chunk = aligned_attn[j:, i:j].clone().cpu()
    else:
        A_chunk = aligned_attn[:, i:j].clone().cpu()
    A_chunk[:, self.curr_frame_pos + 1:] = 0
    self.alignment = torch.cat((self.alignment, A_chunk), dim=0)

    A = self.alignment
    T, S = A.shape

    cur_text_posn = A_chunk[-1].argmax()
    discontinuity = not (-4 < cur_text_posn - self.text_position < 7)
    if not discontinuity:
        self.text_position = cur_text_posn

    false_start = (not self.started) and (A[-2:, -2:].max() > 0.1 or A[:, :4].max() < 0.5)
    self.started = not false_start
    if self.started and self.started_at is None:
        self.started_at = T

    self.complete = self.complete or self.text_position >= S - 3
    if self.complete and self.completed_at is None:
        self.completed_at = T

    long_tail = bool(self.complete and (A[self.completed_at:, -3:].sum(dim=0).max() >= t["lang_hale"]))
    alignment_repetition = bool(self.complete and (A[self.completed_at:, :-5].max(dim=1).values.sum() > 5))

    if next_token is not None:
        if isinstance(next_token, torch.Tensor):
            token_id = next_token.item() if next_token.numel() == 1 else next_token.view(-1)[0].item()
        else:
            token_id = next_token
        self.generated_tokens.append(token_id)
        if len(self.generated_tokens) > 8:
            self.generated_tokens = self.generated_tokens[-8:]

    n = t["gentagelser"]
    token_repetition = (
        (self.complete or not t["kraev_komplet"])
        and len(self.generated_tokens) >= n + 1
        and len(set(self.generated_tokens[-n:])) == 1
    )

    # Undertryk slut-tegnet, indtil teksten næsten er læst (uændret fra originalen).
    if cur_text_posn < S - 3 and S > 5:
        logits[..., self.eos_idx] = -(2**15)

    if long_tail or alignment_repetition or token_repetition:
        taellere["lang_hale" if long_tail else "justering" if alignment_repetition else "gentagelse"] += 1
        logits = -(2**15) * torch.ones_like(logits)
        logits[..., self.eos_idx] = 2**15

    self.curr_frame_pos += 1
    return logits
