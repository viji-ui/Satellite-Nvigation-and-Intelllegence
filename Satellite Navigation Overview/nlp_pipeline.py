"""
nlp_pipeline.py
───────────────
Steps 3-5: Run all NLP tasks on the generated satellite mission profiles.

  Step 3 — VADER-style sentiment scoring
  Step 4 — Rule-based capability tier classification (strategic / operational / basic)
  Step 5 — TF-IDF + K-Means text clustering (6 mission archetypes)

Outputs:
  • Returns an enriched DataFrame
  • Saves outputs/satellite_profiles.csv  (full enriched dataset)
  • Saves outputs/satellite_data.json     (aggregated stats for the dashboard)

Usage:
    python nlp_pipeline.py
"""

import json, os, math, random
from collections import defaultdict, Counter

import pandas as pd
from data_cleaner import load_and_clean
from text_generator import generate_mission_profile


# ── Config ────────────────────────────────────────────────────────────
OUTPUT_DIR    = "outputs"
CSV_OUT       = f"{OUTPUT_DIR}/satellite_profiles.csv"
JSON_OUT      = f"{OUTPUT_DIR}/satellite_data.json"
N_CLUSTERS    = 6
RANDOM_SEED   = 42
SCATTER_SAMPLE = 350


# ═══════════════════════════════════════════════════════════════════════
# STEP 3 — VADER SENTIMENT
# ═══════════════════════════════════════════════════════════════════════

_LEXICON = {
    # Positive signals
    "precise":     2.0, "accurate":    1.8, "critical":    1.0, "important":   1.2,
    "advanced":    1.5, "global":      0.8, "reliable":    1.8, "stable":      1.0,
    "continuous":  0.8, "enables":     1.0, "supports":    0.7, "deliver":     0.6,
    "centimetre":  2.0, "next-generation": 1.5, "broadband": 0.8, "precise":   1.8,
    "validated":   1.0, "operational": 0.6, "positioning": 1.2, "coverage":    0.7,
    "scientific":  0.9, "research":    0.7, "navigation":  1.0, "innovation":  1.3,
    "monitoring":  0.6, "correction":  0.5, "maintain":    0.5, "near-circular": 0.8,
    # Negative signals
    "reconnaissance": -1.0, "surveillance": -1.2, "military":  -0.8,
    "intelligence": -0.9,   "elliptical":  -0.3,  "defence":   -0.5,
    "unstable":   -1.5,     "expired":    -1.8,   "failed":   -2.0,
    "decommissioned": -1.5, "debris":     -2.0,   "highly":   -0.2,
    "polar":      -0.1,     "molniya":    -0.3,
}


def _vader_score(text: str) -> float:
    words = text.lower().replace(",", " ").replace(".", " ").replace("(", " ").replace(")", " ").split()
    raw = sum(_LEXICON.get(w, 0.0) for w in words)
    if raw == 0:
        return 0.0
    return max(-1.0, min(1.0, raw / (1 + abs(raw) * 0.08)))


def _sentiment_label(score: float) -> str:
    if score >= 0.05:   return "Positive"
    if score <= -0.05:  return "Negative"
    return "Neutral"


def add_sentiment(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["sentiment_compound"] = df["description"].apply(_vader_score).round(4)
    df["sentiment_label"]    = df["sentiment_compound"].apply(_sentiment_label)
    print(f"[nlp_pipeline] Sentiment done. Distribution:\n"
          f"  {df['sentiment_label'].value_counts().to_dict()}")
    return df


# ═══════════════════════════════════════════════════════════════════════
# STEP 4 — CAPABILITY TIER CLASSIFICATION
# ═══════════════════════════════════════════════════════════════════════

def _capability_score(row: pd.Series) -> int:
    """
    12-point capability rubric.
    Scores strategic importance, orbital sophistication, and mission criticality.
    """
    score = 0

    # Orbit class value
    orbit_scores = {"GEO": 4, "MEO": 3, "HEO": 3, "Elliptical": 2, "LEO": 1}
    score += orbit_scores.get(row["orbit_class"], 1)

    # Purpose criticality
    purpose = row["purpose"].lower()
    if any(k in purpose for k in ["navigat", "position", "gnss", "gps"]):  score += 3
    elif any(k in purpose for k in ["commun", "broadband"]):                score += 2
    elif any(k in purpose for k in ["earth ob", "science", "meteoro"]):     score += 2
    elif any(k in purpose for k in ["surveil", "military", "reconnais"]):   score += 2
    else:                                                                     score += 1

    # Mass → sophistication proxy
    mass = row["launch_mass_kg"]
    if mass > 4000:   score += 3
    elif mass > 1500: score += 2
    elif mass > 300:  score += 1

    # Lifetime → engineering maturity
    if row["expected_lifetime_yrs"] >= 15: score += 2
    elif row["expected_lifetime_yrs"] >= 8: score += 1

    return min(score, 12)


def _capability_label(score: int) -> str:
    if score >= 9:   return "Strategic Tier"
    if score >= 6:   return "Operational Tier"
    if score >= 3:   return "Support Tier"
    return "Experimental Tier"


def add_capability(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["capability_score"] = df.apply(_capability_score, axis=1)
    df["capability_label"] = df["capability_score"].apply(_capability_label)
    print(f"[nlp_pipeline] Capability done. Distribution:\n"
          f"  {df['capability_label'].value_counts().to_dict()}")
    return df


# ═══════════════════════════════════════════════════════════════════════
# STEP 5 — TF-IDF + K-MEANS CLUSTERING
# ═══════════════════════════════════════════════════════════════════════

CLUSTER_NAMES = {
    0: "LEO Earth Watchers",
    1: "GEO Comms Backbone",
    2: "Navigation Constellation",
    3: "Military & Surveillance",
    4: "Scientific Explorers",
    5: "Technology Demonstrators",
}


def add_clusters(df: pd.DataFrame, n_clusters: int = N_CLUSTERS) -> pd.DataFrame:
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.cluster import KMeans

        vectorizer = TfidfVectorizer(max_features=600, stop_words="english")
        X = vectorizer.fit_transform(df["description"])

        km = KMeans(n_clusters=n_clusters, random_state=RANDOM_SEED, n_init=10)
        df = df.copy()
        df["cluster"] = km.fit_predict(X)

        terms = vectorizer.get_feature_names_out()
        cluster_labels = {}
        for cid in range(n_clusters):
            center = km.cluster_centers_[cid]
            top_term = terms[center.argsort()[-1]]
            cluster_labels[cid] = CLUSTER_NAMES.get(cid, f"C{cid}:{top_term}")
        df["cluster_label"] = df["cluster"].map(cluster_labels)

        print(f"[nlp_pipeline] Clustering done. Cluster sizes:\n"
              f"  {df['cluster_label'].value_counts().to_dict()}")
    except ImportError:
        print("[nlp_pipeline] WARNING: sklearn not installed — skipping clustering.")
        df["cluster"]       = -1
        df["cluster_label"] = "unclustered"

    return df


# ═══════════════════════════════════════════════════════════════════════
# AGGREGATION FOR DASHBOARD JSON
# ═══════════════════════════════════════════════════════════════════════

_STOP = {
    "satellite", "orbit", "from", "its", "and", "the", "this", "that", "with",
    "for", "into", "over", "upon", "within", "provides", "launched", "operated",
    "vehicle", "aboard", "expected", "remain", "designed", "carries", "enabling",
    "approximately", "altitude", "trajectory", "inclination", "period", "minutes",
    "launch", "mass", "operational", "years", "operations", "duration",
}


def _word_freq(df: pd.DataFrame, col_val: str, col: str = "sentiment_label",
               top_n: int = 25) -> list:
    counter = Counter()
    for desc in df[df[col] == col_val]["description"]:
        words = [
            w.lower().strip(".,!?;:()")
            for w in desc.split()
            if len(w) > 3 and w.lower().strip(".,!?;:()") not in _STOP
        ]
        counter.update(words)
    return counter.most_common(top_n)


def build_dashboard_json(df: pd.DataFrame) -> dict:
    """Aggregate all stats needed by index.html and save to JSON."""

    # Combined ranking score (40% sentiment + 60% capability)
    df["combined_score"] = (
        df["sentiment_compound"] * 0.4 + (df["capability_score"] / 12) * 0.6
    ).round(4)

    top10 = (
        df.sort_values("combined_score", ascending=False)
        .head(10)
        [[
            "name", "country", "operator", "users", "purpose",
            "orbit_class", "orbit_type", "perigee_km", "apogee_km",
            "launch_mass_kg", "expected_lifetime_yrs", "launch_vehicle",
            "launch_site", "launch_year",
            "description", "sentiment_compound", "sentiment_label",
            "capability_score", "capability_label", "combined_score",
        ]]
        .to_dict(orient="records")
    )

    # Sentiment by orbit class
    orbit_avg_sent = (
        df.groupby("orbit_class")["sentiment_compound"]
        .mean().round(4).to_dict()
    )

    # Orbit class counts
    orbit_counts = df["orbit_class"].value_counts().to_dict()

    # Purpose counts
    purpose_counts = df["purpose"].value_counts().head(8).to_dict()

    # Launch year trend (1990-2025)
    yr = df.groupby("launch_year").size()
    yr = yr[(yr.index >= 1990) & (yr.index <= 2025)]
    launch_trend = [{"year": int(y), "count": int(c)} for y, c in yr.items()]

    # Top 10 operators by fleet size
    op_counts = df["operator"].value_counts().head(10)
    top_operators = [[k, int(v)] for k, v in op_counts.items()]

    # Top countries by fleet size
    country_counts = df["country"].value_counts().head(12).to_dict()

    # Capability tier distribution
    cap_counts = df["capability_label"].value_counts().to_dict()

    # Sentiment distribution
    sent_counts = df["sentiment_label"].value_counts().to_dict()

    # User type distribution
    user_counts = df["users"].value_counts().to_dict()

    # Word frequencies (positive vs negative sentiment descriptions)
    top_pos_words = _word_freq(df, "Positive")
    top_neg_words = _word_freq(df, "Negative")

    # Scatter plot sample (perigee vs apogee, bubble = mass)
    random.seed(RANDOM_SEED)
    sample = df.sample(min(SCATTER_SAMPLE, len(df)), random_state=RANDOM_SEED)
    scatter_data = [
        {
            "name":     r["name"],
            "perigee":  round(float(r["perigee_km"]), 1),
            "apogee":   round(float(r["apogee_km"]), 1),
            "mass":     round(float(r["launch_mass_kg"]), 1),
            "sent":     round(float(r["sentiment_compound"]), 4),
            "cap":      r["capability_label"],
            "purpose":  r["purpose"],
            "orbit":    r["orbit_class"],
        }
        for _, r in sample.iterrows()
        if r["perigee_km"] > 0 and r["apogee_km"] > 0 and r["launch_mass_kg"] > 0
    ]

    # Full search index (all satellites, minimal fields)
    search_index = (
        df[[
            "name", "country", "operator", "users", "purpose",
            "orbit_class", "launch_year", "launch_vehicle",
            "sentiment_compound", "sentiment_label",
            "capability_label", "capability_score",
            "description", "combined_score",
            "perigee_km", "apogee_km", "launch_mass_kg",
            "expected_lifetime_yrs",
        ]]
        .rename(columns={"sentiment_compound": "sentiment"})
        .round(4)
        .to_dict(orient="records")
    )

    return {
        "total":          len(df),
        "orbit_avg_sent": orbit_avg_sent,
        "orbit_counts":   orbit_counts,
        "purpose_counts": purpose_counts,
        "launch_trend":   launch_trend,
        "top_operators":  top_operators,
        "country_counts": country_counts,
        "cap_counts":     cap_counts,
        "sent_counts":    sent_counts,
        "user_counts":    user_counts,
        "top10":          top10,
        "scatter_data":   scatter_data,
        "top_pos_words":  top_pos_words,
        "top_neg_words":  top_neg_words,
        "search_index":   search_index,
    }


# ═══════════════════════════════════════════════════════════════════════
# FULL PIPELINE RUNNER
# ═══════════════════════════════════════════════════════════════════════

def run_pipeline(csv_path: str = "satellites_data.csv") -> pd.DataFrame:
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # 1. Load & clean
    df = load_and_clean(csv_path)

    # 2. Generate mission profiles
    print("[nlp_pipeline] Generating mission profiles…")
    df["description"] = df.apply(generate_mission_profile, axis=1)

    # 3. Sentiment
    df = add_sentiment(df)

    # 4. Capability tier
    df = add_capability(df)

    # 5. Clustering
    df = add_clusters(df)

    # 6. Save enriched CSV
    df.to_csv(CSV_OUT, index=False)
    print(f"[nlp_pipeline] Saved enriched CSV → {CSV_OUT}")

    # 7. Build & save dashboard JSON
    dashboard = build_dashboard_json(df)
    with open(JSON_OUT, "w") as f:
        json.dump(dashboard, f)
    print(f"[nlp_pipeline] Saved dashboard JSON → {JSON_OUT}  "
          f"({os.path.getsize(JSON_OUT) // 1024} KB)")

    return df


if __name__ == "__main__":
    df = run_pipeline()
    print(f"\n[nlp_pipeline] Pipeline complete. {len(df):,} satellites enriched.")
    print(df[["name", "sentiment_label", "capability_label", "cluster_label"]].head(8).to_string())
