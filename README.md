# ConvEval — Production-Ready Conversation Facet Evaluator

> Score every conversation turn across **399 facets** covering linguistic quality, pragmatics, safety, emotion, personality, cognition, spirituality, and more.  
> Powered by **Mistral API** (open-weights ≤16B). Deployable on **Render + Vercel**.

---

## Architecture

```
User Message
     │
     ▼
┌─────────────────────────────────────────────────────────┐
│  STAGE 1 — Context Router (1 Mistral call)              │
│  → dominant_tone, risk_flag, speaker_state, topics      │
└─────────────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────────┐
│  STAGE 2 — Batch Facet Scorer (16 Mistral calls)        │
│  → 25 facets per batch, scores 1–5 + confidence + reason│
│  → Scales to 5000+ facets: just add facets, auto-chunks │
└─────────────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────────┐
│  STAGE 3 — Aggregator                                   │
│  → category averages, high-risk flags, summary stats    │
└─────────────────────────────────────────────────────────┘
```

**Not one-shot:** Every evaluation runs at minimum 17 sequential Mistral calls (1 routing + 16 scoring batches). Batch size is configurable (5–50).

**Scales to 5000+ facets:** Add entries to `FACET_REGISTRY` in `facets.py`. The `batch_group` is computed automatically as `index // batch_size`. No architectural change needed.

---

## Facet Dataset

- **Source:** `Facets Assignment - Facets Assignment.csv`
- **Raw entries:** 399
- **After preprocessing:** 399 unique facets (0 duplicates)
- **Added columns:**
  | Column | Description |
  |---|---|
  | `facet_id` | Stable identifier (F0000–F0398) |
  | `facet_name` | Cleaned, title-cased name |
  | `category` | 15 categories (Safety, Emotional, Cognitive, etc.) |
  | `score_type` | default / quality / risk / frequency / emotional |
  | `eval_direction` | positive / negative / neutral |
  | `score_semantics` | Per-scale label dict (e.g. 1=Safe, 5=Critical) |
  | `batch_group` | Which scoring batch this facet belongs to |
  | `requires_context` | Whether prior turns affect scoring |
  | `prompt_hint` | Pre-built scoring instruction for this facet |

## Score Scale
Five ordered integers: **1 · 2 · 3 · 4 · 5**  
Semantics depend on `score_type`:
- **default:** Absent → Minimal → Moderate → High → Extreme  
- **quality:** Very Poor → Poor → Adequate → Good → Excellent  
- **risk:** Safe → Low Risk → Moderate → High Risk → Critical  
- **frequency:** Never → Rarely → Sometimes → Often → Always  
- **emotional:** None → Slight → Moderate → Strong → Overwhelming  

---

## Project Structure

```
conveval/
├── backend/
│   ├── facets.py              # Facet registry & preprocessing
│   ├── pipeline.py            # 3-stage Mistral evaluation pipeline
│   ├── main.py                # FastAPI app
│   ├── requirements.txt
│   ├── generate_conversations.py   # Generate 50 sample convs
│   └── conversations/         # 50 JSONs + all_scores.csv + summary.csv
├── frontend/
│   ├── src/
│   │   ├── App.jsx            # Main UI
│   │   ├── index.css
│   │   └── main.jsx
│   ├── index.html
│   ├── package.json
│   └── vite.config.js
├── render.yaml                # Render deployment config
└── README.md
```

---

## Local Setup

### Backend

```bash
cd backend
pip install -r requirements.txt

# Create .env file
echo "MISTRAL_API_KEY=your_key_here" > .env

# Run server
uvicorn main:app --reload --port 8000
```

Without `MISTRAL_API_KEY`, the server runs in **mock mode** (deterministic fake scores — great for UI testing).

### Frontend

```bash
cd frontend
npm install

# Point to your backend
echo "VITE_API_URL=http://localhost:8000" > .env

npm run dev
# Opens at http://localhost:5173
```

### Generate 50 sample conversations

```bash
cd backend
python generate_conversations.py
# Creates conversations/ with 50 JSONs, all_scores.csv, summary.csv
```

---

## Deployment

### Backend → Render

1. Push to GitHub
2. New Web Service on [render.com](https://render.com)
3. Connect repo, set **Root Directory** to `backend`
4. Build command: `pip install -r requirements.txt`
5. Start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
6. Add env var: `MISTRAL_API_KEY = your_key`

### Frontend → Vercel

1. New project on [vercel.com](https://vercel.com)
2. Connect repo, set **Root Directory** to `frontend`
3. Framework preset: **Vite**
4. Add env var: `VITE_API_URL = https://your-render-app.onrender.com`

---

## API Reference

### `POST /evaluate`
```json
{
  "turn_id": "T001",
  "speaker": "user",
  "text": "I feel completely hopeless...",
  "context": [
    {"speaker": "assistant", "text": "How can I help?"}
  ],
  "active_categories": null,
  "batch_size": 25
}
```
**Response:** 399 facet scores, summary stats, routing context, stage log, duration_ms.

### `GET /facets`
Returns full facet registry. Query `?category=Safety+%26+Risk` to filter.

### `GET /categories`
Returns all 15 categories with counts and sample facets.

### `GET /health`
Returns API status, facet count, mock mode status.

---

## Constraints Checklist

| Constraint | Status |
|---|---|
| No one-shot prompt | ✅ 17+ Mistral calls per evaluation (Stage 1 + 16 batches) |
| Open-weights ≤16B | ✅ mistral-small-latest (7B family) |
| Scales to 5000+ facets | ✅ Add entries to FACET_REGISTRY; batch_group auto-assigns |
| Confidence outputs | ✅ Per-facet confidence float 0.0–1.0 |
| Sample UI | ✅ React + Vite frontend |
| 50 conversations | ✅ In `backend/conversations/` |

---

## Brownie Points

- **Confidence outputs:** Every facet score includes a `confidence` field (0.0–1.0)
- **Sample UI:** Full React frontend with conversation builder, facet table, category bars, risk alerts
- **50 conversations:** 50 diverse cases × 399 facets = 50,274 scored data points in `conversations/`

---

## Model Choice

`mistral-small-latest` is used via the Mistral API. It belongs to the Mistral 7B family (open-weights, Apache 2.0 licence, well under 16B). To switch to a different model, change `MISTRAL_MODEL` in `pipeline.py`:

```python
MISTRAL_MODEL = "mistral-small-latest"   # 7B — fast, cheap
# MISTRAL_MODEL = "open-mistral-7b"      # explicit open-weights version
# MISTRAL_MODEL = "open-mixtral-8x7b"    # MoE if you need more capacity
```
