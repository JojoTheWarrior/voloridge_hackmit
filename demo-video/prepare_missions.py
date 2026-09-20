"""Prepare two bounded demo missions without submitting API writes."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(__file__).resolve().parent / "state"


def main():
    rows = json.loads((ROOT / "research/library.json").read_text())
    missions = [
        (
            "clinics",
            "Which rural Nigerian clinics should an electrification team verify first using satellite night lights?",
            ["viirs", "openstreetmap"],
            "fixlist_darkclinics",
            "Start with Nigeria and a bounded, reproducible sample. Join public health-facility coordinates "
            "to settlement night lights, test against public historical facility electricity surveys when "
            "accessible, and identify where the screen is useful and where it fails. Prioritize a defensible "
            "verification workflow rather than claiming present-day electricity status. Preserve observation "
            "and survey dates, missing data, on-site solar ambiguity, precision and recall. No outreach. "
            "Do not expand to all countries or download global rasters. Use windowed reads and a bounded "
            "sample if necessary. Deliver real item-level results suitable for a map, one clear comparison "
            "chart, and a concise evidence-led conclusion. Report the actual scope and counts you achieve.",
        ),
        (
            "flares",
            "Does prioritizing gas flares by nearby population change which sites an environmental monitoring team should investigate first?",
            ["viirs", "openstreetmap", "open-meteo"],
            "fixlist_flares",
            "Compare a volume-based ranking with a nearby-population ranking using public flare and "
            "population data. Scope to Nigeria first unless the full saved catalogue is already available. "
            "Compute the top-list overlap and show concrete sites that move in rank. Use authentic "
            "coordinates and measurements, disclose dates, missingness and ranking definitions. Nearby "
            "population is not measured exposure, illness or lives saved. Do not infer current legal "
            "responsibility or remediation cost. Do not download global rasters or launch a global crawl. "
            "Deliver a bounded real table, a ranking comparison chart, and a useful monitoring decision. "
            "Historical whole-catalogue totals in the notes are not results for a newly computed subset.",
        ),
    ]
    OUT.mkdir(parents=True, exist_ok=True)
    for slug, question, datasets, source, scope in missions:
        selected = [row for row in rows if row["mission"] == source]
        # Preserve source records verbatim; compact whitespace does not change content.
        reference = json.dumps(selected, ensure_ascii=False, separators=(",", ":"))
        assert 0 < len(reference) <= 100_000
        hypothesis = question + "\n\n" + scope + (
            "\n\nKeep the entire mission within its existing 5-ACU cap and reserve effort for the "
            "final report and interactive explorer, which will be requested after your conclusion. "
            "Use public read-only sources only. Do not publish, contact anyone, buy anything, or "
            "invent data when a source is unavailable."
        )
        payload = {"hypothesis": hypothesis, "datasetIds": datasets, "reference": reference}
        (OUT / f"{slug}-request.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
        print(json.dumps({"mission": slug, "question": question, "datasets": datasets,
                          "reference_chars": len(reference), "source_records": len(selected),
                          "max_acu": 5, "submitted": False}))


if __name__ == "__main__":
    main()
