from pathlib import Path
from dotenv import load_dotenv

env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path)

import os, json, logging
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from facets import FACET_REGISTRY, CATEGORIES
from pipeline import (
    ConvTurn, evaluate, summary_stats, FacetScore
)

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

app = FastAPI(
    title="Ocean Across — Conversation Evaluator",
    description="Production-ready 399-facet conversation scoring API",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)



# ─── Pydantic models ──────────────────────────────────────────────────────────

class ContextTurn(BaseModel):
    speaker: str
    text:    str

class EvalRequest(BaseModel):
    turn_id:            str  = "T001"
    speaker:            str  = "user"
    text:               str
    context:            list[ContextTurn] = []
    active_categories:  Optional[list[str]] = None   # None = all 399 facets
    batch_size:         int  = Field(default=25, ge=5, le=50)

class FacetScoreOut(BaseModel):
    facet_id:   str
    facet_name: str
    category:   str
    score:      int
    confidence: float
    reasoning:  str
    direction:  str

class EvalResponse(BaseModel):
    turn_id:     str
    text:        str
    scores:      list[FacetScoreOut]
    summary:     dict
    duration_ms: int
    stage_log:   list[str]


# ─── Routes ───────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {
        "status":       "ok",
        "facets":       len(FACET_REGISTRY),
        "categories":   len(CATEGORIES),
        "model":        "mistral-small-latest",
    }

@app.get("/facets")
def list_facets(category: Optional[str] = None, limit: int = 100):
    data = FACET_REGISTRY
    if category:
        data = [f for f in data if f["category"] == category]
    return {
        "total":      len(data),
        "categories": {c: sum(1 for f in FACET_REGISTRY if f["category"]==c) for c in CATEGORIES},
        "facets":     data[:limit],
    }

@app.get("/categories")
def list_categories():
    out = {}
    for cat in CATEGORIES:
        facets = [f for f in FACET_REGISTRY if f["category"] == cat]
        out[cat] = {"count": len(facets), "sample": [f["facet_name"] for f in facets[:5]]}
    return out

@app.post("/evaluate", response_model=EvalResponse)
def evaluate_turn(req: EvalRequest):
    if not req.text.strip():
        raise HTTPException(400, "text cannot be empty")

    turn = ConvTurn(
        turn_id = req.turn_id,
        speaker = req.speaker,
        text    = req.text,
        context = [{"speaker": c.speaker, "text": c.text} for c in req.context],
    )

    ev = evaluate(turn,
            active_categories=req.active_categories,
            batch_size=req.batch_size)

    stats = summary_stats(ev)

    return EvalResponse(
        turn_id     = ev.turn_id,
        text        = ev.text,
        scores      = [FacetScoreOut(
            facet_id   = s.facet_id,
            facet_name = s.facet_name,
            category   = s.category,
            score      = s.score,
            confidence = s.confidence,
            reasoning  = s.reasoning,
            direction  = s.direction,
        ) for s in ev.scores],
        summary     = stats,
        duration_ms = ev.duration_ms,
        stage_log   = ev.stage_log,
    )


# ─── Conversations bulk endpoint (for the 50-conv zip) ───────────────────────

class BulkConvRequest(BaseModel):
    conversations: list[list[ContextTurn]]   # list of conversations, each a list of turns

@app.post("/bulk-evaluate")
def bulk_evaluate(req: BulkConvRequest):
    results = []
    for ci, conv in enumerate(req.conversations[:50]):
        context_so_far = []
        conv_scores = []
        for ti, turn_data in enumerate(conv):
            turn = ConvTurn(
                turn_id = f"C{ci+1:03d}_T{ti+1:02d}",
                speaker = turn_data.speaker,
                text    = turn_data.text,
                context = context_so_far.copy(),
            )
            ev = evaluate(turn)
            st = summary_stats(ev)
            conv_scores.append({"turn_id": turn.turn_id, "speaker": turn.speaker,
                                 "text": turn.text, "summary": st})
            context_so_far.append({"speaker": turn.speaker, "text": turn.text})
        results.append({"conv_id": f"C{ci+1:03d}", "turns": conv_scores})
    return {"conversations": results}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
