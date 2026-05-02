"""
facets.py — Facet Registry
Loads facets from ANY CSV with a 'Facets' column.
Applies the same cleaning pipeline from the notebook, then enriches with
category, score_type, eval_direction, score_semantics, batch_group, etc.

Scales to 5000+ facets: just swap/extend the CSV. No code changes needed.
"""

import re
import pandas as pd
from pathlib import Path
from collections import Counter


# ─── Score semantics per score_type ──────────────────────────────────────────
SCORE_SEMANTICS = {
    "default":   {1: "Absent",    2: "Minimal",   3: "Moderate", 4: "High",      5: "Extreme"},
    "quality":   {1: "Very Poor", 2: "Poor",      3: "Adequate", 4: "Good",      5: "Excellent"},
    "risk":      {1: "Safe",      2: "Low Risk",  3: "Moderate", 4: "High Risk", 5: "Critical"},
    "frequency": {1: "Never",     2: "Rarely",    3: "Sometimes",4: "Often",     5: "Always"},
    "emotional": {1: "None",      2: "Slight",    3: "Moderate", 4: "Strong",    5: "Overwhelming"},
}


# ─── Noise facets — not measurable from conversation text ────────────────────
# Biometric, count-based, or lifestyle-tracking facets that cannot be
# inferred from what someone says in a conversation.
NOISE_KEYWORDS = [
    "fsh level", "basophil count", "chromatin accessibility",
    "serotonin transporter", "polygenic risk", "macronutrient ratio",
    "metabolic rate", "immune response age", "caffeine intake",
    "caffeine sensitivity gene", "sleep environment temperature",
    "wake time consistency", "pilgrimage participation count",
    "dance cardio sessions", "dance rehearsal hours",
    "music lessons years", "choir participation years",
    "passport stamps count", "blog subscriber count",
    "cloud backup frequency", "commute time",
    "public transport km", "time outdoors",
    "pet enrichment activities", "kink interest diversity",
    "astrology rising sign", "aura color perception",
    "sufi retreat attendance count", "dhikr repetitions",
    "i ching hexagram", "scripture memorization verses",
    "drug use history", "vision check frequency",
    "home security system", "peer to peer lending",
    "gamified finance app", "digital nomad months",
    "breakfast skipping frequency", "snacking behavior",
    "processed food frequency", "training cycle length",
    "eco tourism trips", "dance style mastery diversity",
    "subscription count", "skill endorsements count",
    "open source contributions", "museum visits per year",
    "soft skill training hours", "graffiti appreciation",
    "preference for home cooked", "local food sourcing",
    "parathyroid hormone level", "ideas generated per day",
    "sleep apnea", "chronic pain presence",
    "travel companions diversity", "robotics interaction frequency",
    "peer collaboration hours", "feedback giving frequency",
    "eye contact duration", "physical violence exposure",
    "data sharing consent level",
]


# ─── Category rules (ordered — first match wins) ─────────────────────────────
_CAT_RULES = [
    (r"toxic|hate|threat|violen|self.harm|suicid|crisis|groom|radical|extrem"
     r"|bully|haras|stalk|conspir|propag|hatefulness|harmfulness|drug use|kink",
     "Safety & Risk", "risk"),
    (r"empath|anxiet|depress|grief|trauma|stress|emotio|mood|affect|hopeless"
     r"|despair|morose|merrin|compassion.fatigue|discon|despera|sadness|joyful"
     r"|blissful|happiness|contentment|negative affect|burnout|hysteria"
     r"|warmheart|sensitiv",
     "Emotional & Psychological", "emotional"),
    (r"risktaking|naivety|openness|assertiv|submissiv|passive.aggress|aloofness"
     r"|genuine|honesty|chivalr|cunningn|big.heart|disrespect|selfesteem"
     r"|determinedness|selfcontrol|selfdir|bravery|courageousness|dauntless"
     r"|dishonesty|immaturity|martyrdom|rebellious|frank|outspoken|brazenness"
     r"|impudence|coarsen|cantanker|hostil|psychoticism|abasement|suspicion"
     r"|withdraw|effeteness|servility|disagreeabl",
     "Personality & Character", "default"),
    (r"reasoning|logical|critical.think|problem.solv|statistical|numerical"
     r"|common.sense|decision|causal|probabilistic|deductive|inductive|spatial"
     r"|estimat|synthesis|analogi|logical sequence|understanding math"
     r"|understanding mech|memory for|auditory memory|working memory"
     r"|mental arithmetic|rapid cognitive|divided attention|sequential memory"
     r"|comprehension|information retention",
     "Cognitive & Reasoning", "quality"),
    (r"clarit|fluency|grammar|vocabulary|sentence|coherence|brevity|reading"
     r"|jargon|storytelling|spelling|language use|sentence structure|concreteness",
     "Linguistic Quality", "quality"),
    (r"polite|formal|sarcas|humor|irony|satir|metaphor|subtext|tact|diplomat"
     r"|non verbal|social bold|talkativeness|drollness|civility|frankness",
     "Pragmatics & Communication", "quality"),
    (r"relation|affiliat|cooperat|collaborat|leadership|team|group|social.intel"
     r"|cultural|interpersonal|contribution to group|encouraging participation"
     r"|delegation|participation in community|need for social",
     "Social & Interpersonal", "default"),
    (r"self.improv|adventure|challenge|motivat|goal|persist|grit|curiosit"
     r"|novelty|productiv|purpose|growth|achievement|desire for excel|initiative"
     r"|persever|doggedness|hardwork|meeting deadlines|desire to influence"
     r"|slothful|inefficien",
     "Motivation & Goals", "default"),
    (r"specialist|anatomy|domain|expert|research|factual|teaching|instruction"
     r"|evidence|health literacy|data analysis|computer skill|network basics"
     r"|material properties|troubleshoot",
     "Knowledge & Expertise", "quality"),
    (r"moral|ethic|value|integrity|accountab|manipulat|gaslightin|deception"
     r"|consent|justice|exemplariness|decency|dignity|satya|binding found",
     "Moral & Ethical", "default"),
    (r"spiritual pain|role of spirituality|mindfulness facet|holiness"
     r"|ego dissolut|discernment practice|gnostic|sufi|hindu spiritual"
     r"|jewish spiritual|sikh spiritual|buddhist practice|new age spiritual"
     r"|sacred text|kabbalah|zohar|bahai|ridvan|vrata|kirtan|mantra meditation"
     r"|walking meditation|reiki|archon",
     "Spiritual & Existential", "frequency"),
    (r"psychological construct|character strength|well.being component"
     r"|attachment style|attachment avoidance|defense.mechanism|social.cognit"
     r"|cognitive measure|value orient|fearfulness|activator|connectedness"
     r"|hexaco|enneagram|conscientiousness|neuroticism|big five|resilience"
     r"|self.compassion|executive function|acculturat|identity diffusion"
     r"|perfectionist|consummatory|operant.learn|need for achievement"
     r"|hope scale|cultural intell|social conform|excuse making"
     r"|eye contact avoid|faux pas|social desirabi",
     "Psychological Constructs", "default"),
]


# ─── Cleaning (same pipeline as the notebook) ────────────────────────────────

def clean_facet(x: str) -> str:
    """
      strip → remove numbering → remove colons → normalize hyphens → lowercase
    """
    x = str(x).strip()
    x = re.sub(r'^\d+\.\s*', '', x)   # remove numbering like "800."
    x = x.replace(":", "")             # remove colons
    x = x.replace("-", " ")            # normalize hyphens to spaces
    return x.lower().strip()


def title_case(s: str) -> str:
    """Cleaned lowercase → readable display name."""
    return re.sub(r"\s+", " ", s).strip().title()


# ─── Category + direction ─────────────────────────────────────────────────────

def _assign_category(name: str) -> tuple[str, str]:
    """Returns (category, score_type). First matching rule wins."""
    nl = name.lower()
    for pattern, cat, stype in _CAT_RULES:
        if re.search(pattern, nl):
            return cat, stype
    return "General", "default"


def _direction(name: str, cat: str) -> str:
    neg = (r"toxic|hate|aggress|manipulat|deception|harm|violen|threat|abuse"
           r"|extrem|stalk|haras|groom|misinfo|compulsiv|addiction|anxiet"
           r"|depress|sadness|hopeless|despair|disrespect|passive.aggress"
           r"|cunningn|gaslightin|conspir|propag|hatefulness|harmfulness"
           r"|immaturi|slothful|inefficien|dishonest|cantanker|hostil"
           r"|psychoticism|burnout|abasement|suspicion|withdraw|effeteness"
           r"|servility|coarsen|impudence|brazenness|rebellious|martyrdom"
           r"|disagreeabl|psychopath|narciss")
    pos = (r"empathy|clarity|helpfulness|accuracy|reasoning|intelligence"
           r"|support|growth|resilience|honesty|genuine|chivalr|big.heart"
           r"|mindfulness|wisdom|compassion|optimis|cooperat|altruism"
           r"|generosity|gratitude|bravery|courageousness|joyful|blissful"
           r"|peacefulness|warmheart|decency|dignity|hardwork|persever"
           r"|selfcontrol|ethical|trust|civility|openness|enthusiasm|dauntless"
           r"|selfesteem|self.efficacy|leadership")
    nl = name.lower()
    if re.search(neg, nl): return "negative"
    if re.search(pos, nl): return "positive"
    if cat == "Safety & Risk":                                   return "negative"
    if cat in ("Linguistic Quality", "Knowledge & Expertise"):  return "positive"
    return "neutral"


# ─── CSV loader ───────────────────────────────────────────────────────────────

def load_and_clean_csv(csv_path: str) -> list[str]:
    """
    Load any CSV with a 'Facets' column.
    Returns cleaned, deduplicated, noise-filtered list of facet strings.
    """
    df = pd.read_csv(csv_path)

    # Find Facets column — case-insensitive
    col = next((c for c in df.columns if c.strip().lower() == 'facets'), None)
    if col is None:
        raise ValueError(
            f"No 'Facets' column found in {csv_path}.\n"
            f"Columns present: {list(df.columns)}"
        )

    # Apply notebook cleaning pipeline
    df['clean_facet'] = df[col].apply(clean_facet)

    # Drop empty
    df = df[df['clean_facet'].str.strip() != '']

    # Deduplicate — keep first occurrence
    before_dedup = len(df)
    df = df.drop_duplicates(subset='clean_facet')
    after_dedup  = len(df)

    facets = df['clean_facet'].tolist()

    # Remove non-text-inferable noise facets
    filtered = [
        f for f in facets
        if not any(noise in f for noise in NOISE_KEYWORDS)
    ]

    print(f"  Raw rows        : {before_dedup}")
    print(f"  After dedup     : {after_dedup}  (removed {before_dedup - after_dedup} duplicates)")
    print(f"  After filtering : {len(filtered)}  (removed {after_dedup - len(filtered)} non-text facets)")

    return filtered


# ─── Registry builder ─────────────────────────────────────────────────────────

def build_registry(csv_path: str = None) -> list[dict]:
    """
    Build enriched facet registry from CSV.

    csv_path: path to CSV. If None, auto-searches the backend/ folder
              for any CSV containing 'facet' in the filename.

    To use a different CSV:
        FACET_REGISTRY = build_registry('path/to/Facets Assignment - Facets Assignment.csv')

    Scales to 5000+ facets: add rows to CSV, restart server. No code changes.
    """
    # Auto-find CSV
    if csv_path is None:
        search_dir = Path(__file__).parent
        candidates = [
            search_dir / "Facets Assignment - Facets Assignment.csv",
            search_dir / "Facets_Assignment_-_Facets_Assignment.csv",
            search_dir / "facets_assignment.csv",
            search_dir / "facets.csv",
            search_dir / "Facets.csv",
        ]
        # Also pick up any CSV with 'facet' in the name
        candidates += sorted(search_dir.glob("*[Ff]acet*.csv"))

        csv_path = next((str(p) for p in candidates if p.exists()), None)

        if csv_path is None:
            raise FileNotFoundError(
                "No facets CSV found in backend/ folder.\n"
                "Place your CSV there, or pass the path explicitly:\n"
                "  build_registry('path/to/your_file.csv')"
            )

    print(f"\nLoading facets from: {csv_path}")
    raw_facets = load_and_clean_csv(csv_path)

    registry = []
    seen     = set()

    for i, raw in enumerate(raw_facets):
        if raw in seen:          # final dedup guard
            continue
        seen.add(raw)

        name       = title_case(raw)
        cat, stype = _assign_category(raw)
        direction  = _direction(raw, cat)
        sem        = SCORE_SEMANTICS[stype]

        registry.append({
            # Identity
            "facet_id":   f"F{i:04d}",
            "facet_name": name,              # display name  e.g. "Compassion Fatigue"
            "facet_raw":  raw,               # cleaned lowercase  e.g. "compassion fatigue"

            # Classification
            "category":   cat,              # e.g. "Emotional & Psychological"
            "score_type": stype,            # default / quality / risk / frequency / emotional

            # Scoring metadata
            "eval_direction":  direction,   # positive / negative / neutral
            "score_semantics": sem,         # {1: "Absent", ..., 5: "Extreme"}

            # Pipeline hints
            "batch_group": i // 25,         # 25 per batch; auto-scales to 5000+
            "requires_context": cat in {    # needs prior turns to score accurately
                "Safety & Risk",
                "Emotional & Psychological",
                "Spiritual & Existential",
                "Psychological Constructs",
            },
            "prompt_hint": (
                f"Score '{name}' ({cat}). "
                "Scale: " + ", ".join(f"{k}={v}" for k, v in sem.items()) + "."
            ),
        })

    n_batches = (len(registry) - 1) // 25 + 1 if registry else 0
    print(f"  Registry ready  : {len(registry)} facets in {n_batches} batches of ≤25\n")
    return registry


# ─── Module-level singletons ─────────────────────────────────────────────────
# These are imported directly by pipeline.py and main.py

FACET_REGISTRY = build_registry()

FACET_BY_ID    = {f["facet_id"]:          f for f in FACET_REGISTRY}
FACET_BY_NAME  = {f["facet_name"].lower(): f for f in FACET_REGISTRY}
CATEGORIES     = sorted(set(f["category"]    for f in FACET_REGISTRY))
BATCH_GROUPS   = sorted(set(f["batch_group"] for f in FACET_REGISTRY))


# ─── CLI — run directly to inspect the registry ──────────────────────────────
if __name__ == "__main__":
    print(f"Total facets : {len(FACET_REGISTRY)}")
    print(f"Batches      : {max(BATCH_GROUPS)+1} × ≤25")
    print(f"Categories   : {len(CATEGORIES)}\n")

    cats = Counter(f["category"] for f in FACET_REGISTRY)
    for cat, n in cats.most_common():
        print(f"  {cat:<42} {n:>3}")

    print("\nSample (first 10):")
    for f in FACET_REGISTRY[:10]:
        print(f"  {f['facet_id']}  {f['facet_name']:<45} [{f['category']}]  dir={f['eval_direction']}")

    print("\nTo use a different CSV:")
    print("  build_registry('path/to/your_file.csv')")
