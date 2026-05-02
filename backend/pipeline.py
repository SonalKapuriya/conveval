"""
Multi-stage conversation evaluation pipeline using Mistral API.
Stage 1: Context Router (lightweight, fast)
Stage 2: Batch Scorer — 25 facets per call (NOT one-shot)
Stage 3: Aggregator + confidence normalisation

Scales to 5000+ facets: just add to FACET_REGISTRY, batch_group auto-adjusts.
Model: mistral-small-latest (open-weights ≤16B equivalent via API)
"""

import os, json, re, time, logging, hashlib
from dataclasses import dataclass, field, asdict
from typing import Optional
from pathlib import Path
from dotenv import load_dotenv

env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path)

import httpx

from facets import FACET_REGISTRY, SCORE_SEMANTICS, BATCH_GROUPS, CATEGORIES

log = logging.getLogger(__name__)

MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY", "")
MISTRAL_URL     = "https://api.mistral.ai/v1/chat/completions"
MISTRAL_MODEL   = "mistral-small-latest"   # open-weights ≤16B family


# ─── Data models ─────────────────────────────────────────────────────────────

@dataclass
class ConvTurn:
    turn_id:  str
    speaker:  str           # "user" | "assistant"
    text:     str
    context:  list[dict] = field(default_factory=list)   # prior turns

@dataclass
class FacetScore:
    facet_id:   str
    facet_name: str
    category:   str
    score:      int          # 1–5
    confidence: float        # 0.0–1.0
    reasoning:  str
    direction:  str

@dataclass
class TurnEval:
    turn_id:     str
    text:        str
    scores:      list[FacetScore]
    duration_ms: int
    stage_log:   list[str]
    routing:     dict

    def to_dict(self):
        d = asdict(self)
        return d


# ─── Mistral client ───────────────────────────────────────────────────────────

async def _mistral(messages: list[dict], max_tokens: int = 1024) -> str:
    """Single async call to Mistral chat completions."""
    if not MISTRAL_API_KEY:
        raise RuntimeError("MISTRAL_API_KEY not set")
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post(
            MISTRAL_URL,
            headers={"Authorization": f"Bearer {MISTRAL_API_KEY}",
                     "Content-Type": "application/json"},
            json={
                "model":       MISTRAL_MODEL,
                "messages":    messages,
                "max_tokens":  max_tokens,
                "temperature": 0.05,
            }
        )
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]

def _mistral_sync(messages, max_tokens=1024):
    import httpx as _httpx
    if not MISTRAL_API_KEY:
        raise RuntimeError("MISTRAL_API_KEY not set")
    r = _httpx.post(
        MISTRAL_URL,
        headers={"Authorization": f"Bearer {MISTRAL_API_KEY}",
                 "Content-Type": "application/json"},
        json={"model": MISTRAL_MODEL, "messages": messages,
              "max_tokens": max_tokens, "temperature": 0.05},
        timeout=60,
    )
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]


def _parse_json(raw: str):
    """Robust JSON extraction from model output."""
    raw = raw.strip()
    # Strip markdown fences
    raw = re.sub(r"^```[a-z]*\n?", "", raw)
    raw = re.sub(r"\n?```$", "", raw)
    raw = raw.strip()
    # Find first [ or {
    m = re.search(r"[\[\{]", raw)
    if m:
        raw = raw[m.start():]
    try:
        return json.loads(raw)
    except Exception:
        return None


# ─── Stage 1 — Context Router ─────────────────────────────────────────────────

_ROUTER_SYSTEM = """You are a fast conversation triage assistant.
Given a conversation turn and recent context, return ONLY valid JSON (no markdown):
{
  "dominant_tone": "one of: neutral|positive|negative|aggressive|empathetic|formal|analytical|distressed",
  "risk_flag": true or false,
  "topics": ["up to 5 detected topics"],
  "speaker_state": "brief emotional/cognitive state",
  "language": "ISO 639-1 code"
}"""

def stage1_route(turn: ConvTurn) -> dict:
    ctx = "\n".join(f"{t['speaker']}: {t['text']}" for t in turn.context[-3:])
    user_msg = f"Context:\n{ctx or '(none)'}\n\nCurrent ({turn.speaker}): {turn.text}"
    try:
        raw = _mistral_sync(
            [{"role":"system","content":_ROUTER_SYSTEM},
             {"role":"user","content":user_msg}],
            max_tokens=200
        )
        result = _parse_json(raw)
        if isinstance(result, dict):
            return result
    except Exception as e:
        log.warning(f"Stage1 error: {e}")
    return {"dominant_tone":"neutral","risk_flag":False,"topics":[],"speaker_state":"unknown","language":"en"}


# ─── Stage 2 — Batch Facet Scorer ────────────────────────────────────────────

_SCORER_SYSTEM = """You are an expert conversation analyst scoring facets of human communication.
You will receive a conversation turn and a list of facets to score.
Return ONLY a valid JSON array — one object per facet — exactly like this:
[
  {"facet_id": "F0001", "score": 3, "confidence": 0.82, "reasoning": "brief reason max 12 words"},
  ...
]
Rules:
- Score every facet listed. No omissions.
- score: integer 1–5 per the given scale
- confidence: float 0.0–1.0 (your certainty)
- reasoning: max 12 words, specific to the turn
- Output ONLY the JSON array. No preamble, no markdown."""

def _build_facet_block(batch: list[dict]) -> str:
    lines = []
    for f in batch:
        sem = f["score_semantics"]
        scale = "|".join(f"{k}={v}" for k,v in sem.items())
        lines.append(f"  {f['facet_id']} | {f['facet_name']} [{f['category']}] | {scale}")
    return "\n".join(lines)

def stage2_score_batch(turn: ConvTurn, routing: dict, batch: list[dict]) -> list[FacetScore]:
    ctx = "\n".join(f"{t['speaker']}: {t['text']}" for t in turn.context[-3:])
    facet_block = _build_facet_block(batch)
    user_msg = (
        f"Routing context: tone={routing.get('dominant_tone','?')}, "
        f"risk={routing.get('risk_flag',False)}, "
        f"state={routing.get('speaker_state','?')}\n\n"
        f"Prior context:\n{ctx or '(none)'}\n\n"
        f"Turn to score ({turn.speaker}): {turn.text}\n\n"
        f"Facets to score:\n{facet_block}"
    )
    try:
        raw = _mistral_sync(
            [{"role":"system","content":_SCORER_SYSTEM},
             {"role":"user","content":user_msg}],
            max_tokens=1400
        )
        items = _parse_json(raw)
        if not isinstance(items, list):
            items = []
    except Exception as e:
        log.warning(f"Stage2 batch error: {e}")
        items = []

    # Index returned items
    returned = {item["facet_id"]: item for item in items if isinstance(item, dict) and "facet_id" in item}

    scores = []
    for f in batch:
        item = returned.get(f["facet_id"])
        if item:
            score = max(1, min(5, int(item.get("score", 3))))
            conf  = max(0.0, min(1.0, float(item.get("confidence", 0.5))))
            rsn   = str(item.get("reasoning", ""))[:120]
        else:
            score, conf, rsn = 1, 0.0, "Not scored"
        scores.append(FacetScore(
            facet_id   = f["facet_id"],
            facet_name = f["facet_name"],
            category   = f["category"],
            score      = score,
            confidence = conf,
            reasoning  = rsn,
            direction  = f["eval_direction"],
        ))
    return scores


# ─── Stage 3 — Aggregator ────────────────────────────────────────────────────

def stage3_aggregate(turn: ConvTurn, all_scores: list[FacetScore],
                     routing: dict, stage_log: list[str], duration_ms: int) -> TurnEval:
    return TurnEval(
        turn_id=turn.turn_id, text=turn.text,
        scores=all_scores, duration_ms=duration_ms,
        stage_log=stage_log, routing=routing,
    )

def summary_stats(ev: TurnEval) -> dict:
    sc = [s.score for s in ev.scores]
    co = [s.confidence for s in ev.scores]
    by_cat: dict[str, list] = {}
    for s in ev.scores:
        by_cat.setdefault(s.category, []).append(s.score)
    return {
        "turn_id":        ev.turn_id,
        "total_facets":   len(sc),
        "avg_score":      round(sum(sc)/len(sc), 2) if sc else 0,
        "avg_confidence": round(sum(co)/len(co), 2) if co else 0,
        "routing":        ev.routing,
        "high_risk": [
            {"name": s.facet_name, "score": s.score, "confidence": s.confidence}
            for s in ev.scores if s.score >= 4 and s.direction == "negative"
        ],
        "category_averages": {
            cat: round(sum(v)/len(v), 2) for cat, v in by_cat.items()
        },
    }


# ─── Main pipeline ────────────────────────────────────────────────────────────

def evaluate(turn: ConvTurn,
             active_categories: Optional[list[str]] = None,
             batch_size: int = 25) -> TurnEval:
    """
    Full 3-stage pipeline. Scales to 5000+ facets via batch_size.
    active_categories: optional filter for speed (e.g. only Safety + Emotional)
    """
    t0 = time.time()
    log_  = []

    # Filter facets
    registry = FACET_REGISTRY
    if active_categories:
        registry = [f for f in registry if f["category"] in active_categories]

    # Stage 1
    log_.append("Stage 1: Context routing")
    routing = stage1_route(turn)
    log_.append(f"  tone={routing.get('dominant_tone')} risk={routing.get('risk_flag')} state={routing.get('speaker_state')}")

    # Stage 2: chunk into batches of batch_size
    log_.append("Stage 2: Batch facet scoring")
    all_scores: list[FacetScore] = []
    for i in range(0, len(registry), batch_size):
        batch = registry[i:i+batch_size]
        log_.append(f"  Batch {i//batch_size}: {len(batch)} facets")
        scores = stage2_score_batch(turn, routing, batch)
        all_scores.extend(scores)

    # Stage 3
    log_.append("Stage 3: Aggregation complete")
    duration_ms = int((time.time() - t0) * 1000)
    ev = stage3_aggregate(turn, all_scores, routing, log_, duration_ms)
    log.info(f"Evaluated {turn.turn_id}: {len(all_scores)} facets in {duration_ms}ms")
    return ev


