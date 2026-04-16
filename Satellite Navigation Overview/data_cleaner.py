"""
data_cleaner.py
───────────────
Step 1: Load, clean, and perform EDA on the UCS Satellite Database CSV.
Fills missing numeric values with per-orbit-class medians.
Outputs: cleaned DataFrame + EDA plots saved to /outputs/eda/

If satellites_data.csv is not found, generates embedded synthetic data
based on the UCS Satellite Database schema (2,000+ realistic records).
"""

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use("Agg")          # headless backend
import os, math, random, io

# ── Config ────────────────────────────────────────────────────────────
CSV_PATH   = "satellites_data.csv"
OUTPUT_DIR = "outputs/eda"

COLS = [
    "name", "country", "operator", "users", "purpose",
    "orbit_class", "orbit_type", "perigee_km", "apogee_km",
    "eccentricity", "inclination_deg", "period_min",
    "launch_mass_kg", "dry_mass_kg", "power_watts",
    "date_of_launch", "expected_lifetime_yrs",
    "launch_vehicle", "launch_site", "cospar_id",
]

NUM_COLS = [
    "perigee_km", "apogee_km", "eccentricity", "inclination_deg",
    "period_min", "launch_mass_kg", "dry_mass_kg", "power_watts",
    "expected_lifetime_yrs",
]

DARK = {
    "figure.facecolor": "#000510",
    "axes.facecolor":   "#050a1a",
    "axes.edgecolor":   "#00d4ff33",
    "axes.labelcolor":  "#7aa3cc",
    "xtick.color":      "#7aa3cc",
    "ytick.color":      "#7aa3cc",
    "text.color":       "#c0d4f0",
    "grid.color":       "#00d4ff11",
    "grid.linestyle":   "--",
}

# ── Embedded synthetic data generator ────────────────────────────────
ORBIT_CLASSES   = ["LEO", "MEO", "GEO", "HEO", "Elliptical"]
ORBIT_TYPES     = ["Sun-Synchronous", "Polar", "Geostationary", "Molniya",
                   "Inclined Geosynchronous", "Equatorial", "Medium Earth"]
PURPOSES        = [
    "Communications", "Earth Observation", "Navigation/Global Positioning",
    "Space Science", "Earth Science", "Technology Development",
    "Surveillance", "Meteorology", "Amateur Radio", "Military Surveillance",
]
USERS           = ["Civil", "Commercial", "Military", "Government",
                   "Civil/Commercial", "Military/Government"]
COUNTRIES       = [
    "USA", "China", "Russia", "UK", "Japan", "India", "Germany",
    "France", "Canada", "South Korea", "Israel", "Italy", "SpaceX (USA)",
    "UAE", "Brazil", "Australia", "Luxembourg", "Netherlands", "Sweden",
]
OPERATORS       = [
    "NASA", "ESA", "SpaceX / Starlink", "OneWeb", "SES", "Intelsat",
    "ISRO", "JAXA", "Roscosmos", "CNES", "DLR", "CNSA",
    "Planet Labs", "DigitalGlobe", "O3b Networks", "Iridium Communications",
    "Boeing", "Airbus Defence", "Thales Alenia", "Lockheed Martin",
]
VEHICLES        = [
    "Falcon 9", "Ariane 5", "Soyuz-2", "Long March 3B", "PSLV",
    "Atlas V", "Delta IV", "H-IIA", "Vega", "Electron",
    "Starship", "Long March 5", "New Shepard", "Antares",
]
LAUNCH_SITES    = [
    "Kennedy Space Center, USA", "Baikonur Cosmodrome, Kazakhstan",
    "Xichang Satellite Launch Center, China", "Satish Dhawan Space Centre, India",
    "Guiana Space Centre, French Guiana", "Tanegashima Space Center, Japan",
    "Vandenberg Air Force Base, USA", "Cape Canaveral, USA",
    "Plesetsk Cosmodrome, Russia", "Jiuquan Satellite Launch Center, China",
]


def _altitude_for_orbit(orbit_class: str):
    """Return realistic (perigee, apogee) km ranges per orbit class."""
    if orbit_class == "LEO":
        p = random.randint(300, 1400)
        a = p + random.randint(0, 200)
    elif orbit_class == "MEO":
        p = random.randint(2000, 20000)
        a = p + random.randint(0, 2000)
    elif orbit_class == "GEO":
        p = random.randint(35700, 35900)
        a = p + random.randint(0, 300)
    elif orbit_class == "HEO":
        p = random.randint(200, 1000)
        a = random.randint(30000, 45000)
    else:  # Elliptical
        p = random.randint(500, 2000)
        a = random.randint(10000, 35000)
    return p, a


def generate_embedded_data(n: int = 2050, seed: int = 42) -> pd.DataFrame:
    """Generate realistic synthetic satellite data matching UCS schema."""
    random.seed(seed)
    rows = []
    for i in range(1, n + 1):
        orbit  = random.choice(ORBIT_CLASSES)
        perig, apog = _altitude_for_orbit(orbit)
        purpose = random.choice(PURPOSES)
        user    = random.choice(USERS)
        country = random.choice(COUNTRIES)
        op      = random.choice(OPERATORS)
        yr      = random.randint(1990, 2024)
        month   = random.randint(1, 12)
        day     = random.randint(1, 28)
        mass    = random.uniform(50, 8000)
        lifetime = round(random.uniform(1.5, 20.0), 1)
        incl   = round(random.uniform(0, 98), 2)
        period = round(math.sqrt(((perig + apog) / 2 + 6371) ** 3 / 398600) * 2 * math.pi / 60, 1)
        eccen  = round((apog - perig) / (apog + perig + 2 * 6371), 5)
        cospar = f"{yr}-{i:03d}A"
        rows.append({
            "name":               f"SAT-{country[:3].upper()}-{i:04d}",
            "country":            country,
            "operator":           op,
            "users":              user,
            "purpose":            purpose,
            "orbit_class":        orbit,
            "orbit_type":         random.choice(ORBIT_TYPES),
            "perigee_km":         perig,
            "apogee_km":          apog,
            "eccentricity":       eccen,
            "inclination_deg":    incl,
            "period_min":         period,
            "launch_mass_kg":     round(mass, 1),
            "dry_mass_kg":        round(mass * random.uniform(0.4, 0.8), 1),
            "power_watts":        round(random.uniform(100, 20000), 0),
            "date_of_launch":     f"{yr}-{month:02d}-{day:02d}",
            "expected_lifetime_yrs": lifetime,
            "launch_vehicle":     random.choice(VEHICLES),
            "launch_site":        random.choice(LAUNCH_SITES),
            "cospar_id":          cospar,
        })
    return pd.DataFrame(rows)


# ── Helpers ───────────────────────────────────────────────────────────
def safe_float(v):
    try:
        f = float(v)
        return None if math.isnan(f) else f
    except Exception:
        return None


def apply_dark():
    plt.rcParams.update(DARK)


# ── Main pipeline ─────────────────────────────────────────────────────
def load_and_clean(csv_path: str = CSV_PATH) -> pd.DataFrame:
    """Load CSV or generate synthetic data, clean and return DataFrame."""
    if os.path.exists(csv_path):
        df = pd.read_csv(csv_path, encoding="latin1")
        # Normalise common UCS column name variants
        rename_map = {
            "Name of Satellite, Alternate Names": "name",
            "Name of Satellite":                  "name",
            "Country of Operator/Owner":          "country",
            "Country of Operator":                "country",
            "Operator/Owner":                     "operator",
            "Users":                              "users",
            "Purpose":                            "purpose",
            "Class of Orbit":                     "orbit_class",
            "Type of Orbit":                      "orbit_type",
            "Perigee (km)":                       "perigee_km",
            "Apogee (km)":                        "apogee_km",
            "Eccentricity":                       "eccentricity",
            "Inclination (degrees)":              "inclination_deg",
            "Period (minutes)":                   "period_min",
            "Launch Mass (kg.)":                  "launch_mass_kg",
            "Dry Mass (kg.)":                     "dry_mass_kg",
            "Power (watts)":                      "power_watts",
            "Date of Launch":                     "date_of_launch",
            "Expected Lifetime (yrs.)":           "expected_lifetime_yrs",
            "Launch Vehicle":                     "launch_vehicle",
            "Launch Site":                        "launch_site",
            "COSPAR Number":                      "cospar_id",
        }
        df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})
        print(f"[data_cleaner] Loaded CSV: {csv_path} ({len(df):,} rows)")
    else:
        print(f"[data_cleaner] '{csv_path}' not found — generating embedded synthetic data…")
        df = generate_embedded_data()

    # Keep only recognised columns (fill missing)
    for col in COLS:
        if col not in df.columns:
            df[col] = None

    df = df[COLS].copy()

    # Parse launch year
    try:
        df["launch_year"] = pd.to_datetime(
            df["date_of_launch"], errors="coerce"
        ).dt.year.fillna(2000).astype(int)
    except Exception:
        df["launch_year"] = 2000

    # Fill numeric missing with per-orbit-class median
    df[NUM_COLS] = df.groupby("orbit_class")[NUM_COLS].transform(
        lambda x: x.fillna(x.median())
    )
    df[NUM_COLS] = df[NUM_COLS].fillna(df[NUM_COLS].median())

    # Clean categoricals
    for col in ["orbit_class", "purpose", "users", "country", "operator"]:
        df[col] = df[col].fillna("Unknown").astype(str).str.strip()

    print(
        f"[data_cleaner] {len(df):,} satellites across "
        f"{df['orbit_class'].nunique()} orbit classes, "
        f"{df['country'].nunique()} countries."
    )
    return df


# ── EDA plots ─────────────────────────────────────────────────────────
def run_eda(df: pd.DataFrame, out_dir: str = OUTPUT_DIR):
    """Produce 5 EDA plots and save to out_dir."""
    os.makedirs(out_dir, exist_ok=True)
    apply_dark()

    C1 = "#00d4ff"
    C2 = "#ff6b00"
    C3 = "#39ff14"
    C4 = "#8b5cf6"
    C5 = "#ffd700"

    # ── 1. Orbit class distribution ──────────────────────────────────
    fig, ax = plt.subplots(figsize=(10, 5))
    orbit_counts = df["orbit_class"].value_counts()
    colors = [C1, C2, C3, C4, C5, "#ff4466"][:len(orbit_counts)]
    bars = ax.barh(orbit_counts.index, orbit_counts.values,
                   color=colors, edgecolor="none")
    ax.set_xlabel("Number of Satellites")
    ax.set_title("Satellite Count by Orbit Class", fontsize=13, pad=12)
    ax.grid(axis="x")
    for bar in bars:
        ax.text(bar.get_width() + 5, bar.get_y() + bar.get_height() / 2,
                f"{int(bar.get_width()):,}", va="center", fontsize=9, color="#7aa3cc")
    fig.tight_layout()
    fig.savefig(f"{out_dir}/01_orbit_types.png", dpi=150)
    plt.close(fig)
    print("[data_cleaner] Saved 01_orbit_types.png")

    # ── 2. Launch year trend ─────────────────────────────────────────
    fig, ax = plt.subplots(figsize=(12, 5))
    yr_counts = df.groupby("launch_year").size()
    yr_counts = yr_counts[(yr_counts.index >= 1990) & (yr_counts.index <= 2025)]
    ax.fill_between(yr_counts.index, yr_counts.values, alpha=0.25, color=C1)
    ax.plot(yr_counts.index, yr_counts.values, color=C1, linewidth=2.5, marker="o",
            markersize=4)
    ax.set_xlabel("Year")
    ax.set_ylabel("Satellites Launched")
    ax.set_title("Satellite Launch Trend (1990 – 2025)", fontsize=13, pad=12)
    ax.grid(True)
    fig.tight_layout()
    fig.savefig(f"{out_dir}/02_launch_year_trend.png", dpi=150)
    plt.close(fig)
    print("[data_cleaner] Saved 02_launch_year_trend.png")

    # ── 3. Mass vs Altitude scatter ──────────────────────────────────
    fig, ax = plt.subplots(figsize=(10, 6))
    orbit_classes = df["orbit_class"].unique()
    colors_map = {o: c for o, c in zip(orbit_classes,
                  [C1, C2, C3, C4, C5, "#ff4466", "#aaffaa"])}
    for orbit in orbit_classes:
        sub = df[df["orbit_class"] == orbit]
        mask = (sub["launch_mass_kg"] > 0) & (sub["apogee_km"] > 0)
        ax.scatter(
            sub[mask]["launch_mass_kg"], sub[mask]["apogee_km"],
            s=12, alpha=0.5, color=colors_map.get(orbit, C1), label=orbit
        )
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("Launch Mass (kg) — log scale")
    ax.set_ylabel("Apogee Altitude (km) — log scale")
    ax.set_title("Launch Mass vs Apogee Altitude by Orbit Class", fontsize=13, pad=12)
    ax.legend(fontsize=8, framealpha=0.15)
    ax.grid(True)
    fig.tight_layout()
    fig.savefig(f"{out_dir}/03_mass_vs_altitude.png", dpi=150)
    plt.close(fig)
    print("[data_cleaner] Saved 03_mass_vs_altitude.png")

    # ── 4. Top 8 operators ───────────────────────────────────────────
    fig, ax = plt.subplots(figsize=(11, 5))
    op_counts = df["operator"].value_counts().head(8)
    bars2 = ax.bar(range(len(op_counts)), op_counts.values,
                   color=[C1, C2, C3, C4, C5, "#ff4466", "#4fc3f7", "#b89af0"],
                   edgecolor="none", width=0.7)
    ax.set_xticks(range(len(op_counts)))
    ax.set_xticklabels(op_counts.index, rotation=25, ha="right", fontsize=9)
    ax.set_ylabel("Number of Satellites")
    ax.set_title("Top 8 Satellite Operators by Fleet Size", fontsize=13, pad=12)
    ax.grid(axis="y")
    for bar in bars2:
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 5,
                f"{int(bar.get_height()):,}", ha="center", fontsize=9, color="#7aa3cc")
    fig.tight_layout()
    fig.savefig(f"{out_dir}/04_top_operators.png", dpi=150)
    plt.close(fig)
    print("[data_cleaner] Saved 04_top_operators.png")

    # ── 5. Purpose distribution (donut) ─────────────────────────────
    fig, ax = plt.subplots(figsize=(8, 8))
    purp = df["purpose"].value_counts()
    top6   = purp.head(6)
    others = purp.iloc[6:].sum()
    labels = list(top6.index) + ["Others"]
    sizes  = list(top6.values) + [others]
    pie_colors = [C1, C2, C3, C4, C5, "#ff4466", "#888888"]
    wedges, texts, autotexts = ax.pie(
        sizes, labels=labels, colors=pie_colors,
        autopct="%1.1f%%", startangle=130, pctdistance=0.82,
        wedgeprops={"edgecolor": "#000510", "linewidth": 2, "width": 0.55},
    )
    for t in texts + autotexts:
        t.set_color("#c0d4f0")
        t.set_fontsize(9)
    ax.set_title("Satellite Purpose Distribution", fontsize=13, pad=20)
    fig.tight_layout()
    fig.savefig(f"{out_dir}/05_purpose_distribution.png", dpi=150)
    plt.close(fig)
    print("[data_cleaner] Saved 05_purpose_distribution.png")

    print(f"[data_cleaner] All EDA plots saved to: {out_dir}/")


# ── Entry point ───────────────────────────────────────────────────────
if __name__ == "__main__":
    df = load_and_clean()
    run_eda(df)
