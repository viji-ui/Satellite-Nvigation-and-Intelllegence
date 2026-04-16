"""
text_generator.py
─────────────────
Step 2: Convert each satellite row into a rich natural-language mission profile
using a deterministic template engine — no external model required.

Usage (standalone):
    python text_generator.py

Usage (as module):
    from text_generator import generate_mission_profile
    df["description"] = df.apply(generate_mission_profile, axis=1)
"""

import pandas as pd
from data_cleaner import load_and_clean


# ── Classification helpers ────────────────────────────────────────────
def _orbit_description(orbit_class: str, perigee: float, apogee: float) -> str:
    alt = (perigee + apogee) / 2
    if orbit_class == "LEO":
        return f"a low Earth orbit (LEO) at approximately {int(alt):,} km altitude"
    elif orbit_class == "MEO":
        return f"a medium Earth orbit (MEO) at approximately {int(alt):,} km altitude"
    elif orbit_class == "GEO":
        return "a geostationary orbit (GEO) at ~35,786 km, maintaining a fixed position over Earth"
    elif orbit_class == "HEO":
        return (f"a highly elliptical orbit (HEO) ranging from {int(perigee):,} km "
                f"to {int(apogee):,} km altitude")
    else:
        return (f"an elliptical orbit ranging from {int(perigee):,} km "
                f"to {int(apogee):,} km")


def _mass_category(mass_kg: float) -> str:
    if mass_kg < 10:   return "a femto/picosat (under 10 kg)"
    if mass_kg < 100:  return "a nanosatellite (10–100 kg)"
    if mass_kg < 500:  return "a microsatellite (100–500 kg)"
    if mass_kg < 2000: return "a medium-class satellite (500–2,000 kg)"
    return "a heavy-class satellite (over 2,000 kg)"


def _lifetime_desc(yrs: float) -> str:
    if yrs < 3:   return "short-duration"
    if yrs < 8:   return "medium-duration"
    if yrs < 15:  return "long-duration"
    return "ultra-long-duration"


def _purpose_verb(purpose: str) -> str:
    purpose = purpose.lower()
    if "commun"   in purpose: return "provide broadband and voice communications services"
    if "earth ob" in purpose: return "conduct continuous Earth observation and remote sensing"
    if "navigat"  in purpose: return "deliver precise positioning and navigation signals"
    if "meteoro"  in purpose: return "monitor atmospheric conditions and weather patterns"
    if "science"  in purpose: return "conduct scientific research and space science experiments"
    if "surveil"  in purpose: return "perform reconnaissance and surveillance operations"
    if "military" in purpose: return "support military communications and intelligence gathering"
    if "technolog"in purpose: return "test and validate next-generation space technologies"
    if "amateur"  in purpose: return "support amateur radio communications globally"
    return "execute its designated space mission"


def _user_context(users: str) -> str:
    u = users.lower()
    if "military" in u and "civil" in u:
        return "serving both military and civilian stakeholders"
    if "military" in u:
        return "serving military and defence agencies"
    if "commercial" in u and "civil" in u:
        return "supporting commercial enterprises and civil institutions"
    if "commercial" in u:
        return "operated for commercial telecommunications and data services"
    if "civil" in u:
        return "providing services to civil and governmental organisations"
    if "government" in u:
        return "operated under direct government mandate"
    return "supporting a range of institutional users"


def _eccentricity_note(ecc: float) -> str:
    if ecc < 0.01:   return "Its orbit is nearly perfectly circular, ensuring consistent coverage."
    if ecc < 0.05:   return "The orbit is slightly elliptical, providing stable service windows."
    if ecc < 0.3:    return "Its moderately elliptical orbit enables extended dwell time over target regions."
    return "Its highly elliptical orbit delivers extended coverage over polar and high-latitude areas."


def _navigation_relevance(purpose: str) -> str:
    p = purpose.lower()
    if "navigat" in p or "position" in p or "gps" in p or "gnss" in p:
        return (" It forms a critical node in the global navigation satellite system (GNSS), "
                "enabling centimetre-level positioning accuracy for aviation, maritime, and terrestrial users.")
    if "commun" in p:
        return (" Its communications payload supports relay of navigation correction signals "
                "and timing data for ground-based augmentation systems.")
    if "earth ob" in p:
        return (" Imagery from this satellite assists in map updating and geospatial reference "
                "frame maintenance for navigation infrastructure.")
    return ""


# ── Core generator ────────────────────────────────────────────────────
def generate_mission_profile(row: pd.Series) -> str:
    """Build a human-readable mission profile for a single satellite row."""
    name        = str(row["name"])
    country     = str(row["country"])
    operator    = str(row["operator"])
    users       = str(row["users"])
    purpose     = str(row["purpose"])
    orbit_class = str(row["orbit_class"])
    orbit_type  = str(row["orbit_type"])
    perigee     = float(row["perigee_km"])
    apogee      = float(row["apogee_km"])
    eccentricity= float(row["eccentricity"])
    inclination = float(row["inclination_deg"])
    period      = float(row["period_min"])
    mass        = float(row["launch_mass_kg"])
    lifetime    = float(row["expected_lifetime_yrs"])
    vehicle     = str(row["launch_vehicle"])
    site        = str(row["launch_site"])
    year        = int(row.get("launch_year", 2000))

    orbit_desc    = _orbit_description(orbit_class, perigee, apogee)
    mass_cat      = _mass_category(mass)
    lifetime_desc = _lifetime_desc(lifetime)
    purpose_verb  = _purpose_verb(purpose)
    user_ctx      = _user_context(users)
    ecc_note      = _eccentricity_note(eccentricity)
    nav_rel       = _navigation_relevance(purpose)

    return (
        f"{name} is {mass_cat} operated by {operator} ({country}), launched in {year} "
        f"aboard a {vehicle} from {site}. "
        f"Its primary mission is to {purpose_verb}, {user_ctx}. "
        f"The satellite occupies {orbit_desc} on a {orbit_type} trajectory, "
        f"with an orbital inclination of {inclination:.1f}° and a period of {period:.1f} minutes. "
        f"{ecc_note} "
        f"Designed for {lifetime_desc} operations, it carries a {mass:.0f} kg launch mass "
        f"and is expected to remain operational for {lifetime:.1f} years.{nav_rel}"
    )


# ── Entry point ───────────────────────────────────────────────────────
if __name__ == "__main__":
    df = load_and_clean()
    df["description"] = df.apply(generate_mission_profile, axis=1)

    # Preview 3 samples
    for _, row in df.sample(3, random_state=7).iterrows():
        print("─" * 72)
        print(row["description"])
    print("─" * 72)
    print(f"[text_generator] Generated {len(df):,} mission profiles.")
