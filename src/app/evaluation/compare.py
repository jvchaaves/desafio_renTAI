from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
RESULTS = ROOT / "docs" / "05-resultados"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    baseline = _load(RESULTS / "metricas_globais_e001_baseline.json")
    new = _load(RESULTS / "metricas_globais.json")

    print(f"\n{'Comparacao E-001 (baseline) vs E-006 (otimizado)':^70}")
    print("=" * 70)

    print(f"\n{'Config':<10}{'Modo':<14}{'F1 baseline':>14}{'F1 E-006':>14}{'Delta':>10}")
    print("-" * 70)
    for cfg in ("A", "B", "C"):
        for mode in ("uniform", "adaptive"):
            b = baseline["configs"][cfg][mode]["global"]["f1_macro"]
            n = new["configs"][cfg][mode]["global"]["f1_macro"]
            delta = n - b
            arrow = "↑" if delta > 0.005 else ("↓" if delta < -0.005 else "—")
            print(f"{cfg:<10}{mode:<14}{b:>14.3f}{n:>14.3f}{delta:>+9.3f} {arrow}")

    print(f"\n{'Accuracy / Precision / Recall (Config C, adaptive)':^70}")
    print("-" * 70)
    bc = baseline["configs"]["C"]["adaptive"]["global"]
    nc = new["configs"]["C"]["adaptive"]["global"]
    for key, label in (
        ("accuracy", "Accuracy"),
        ("precision_pos", "Precision (pos)"),
        ("recall_pos", "Recall (pos)"),
        ("f1_pos", "F1 (pos)"),
        ("f1_macro", "F1 macro"),
    ):
        b = bc.get(key, 0)
        n = nc.get(key, 0)
        delta = n - b
        arrow = "↑" if delta > 0.005 else ("↓" if delta < -0.005 else "—")
        print(f"  {label:<20}{b:>14.3f}{n:>14.3f}{delta:>+9.3f} {arrow}")

    print(f"\n{'Confusao Config C adaptive':^70}")
    print("-" * 70)
    bc_c = baseline["configs"]["C"]["adaptive"]["global"]["confusion"]
    nc_c = new["configs"]["C"]["adaptive"]["global"]["confusion"]
    print(f"  {'':>14}{'TP':>8}{'TN':>8}{'FP':>8}{'FN':>8}")
    print(f"  {'Baseline':<14}{bc_c['tp']:>8}{bc_c['tn']:>8}{bc_c['fp']:>8}{bc_c['fn']:>8}")
    print(f"  {'E-006':<14}{nc_c['tp']:>8}{nc_c['tn']:>8}{nc_c['fp']:>8}{nc_c['fn']:>8}")
    print()


if __name__ == "__main__":
    main()
