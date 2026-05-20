from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
RESULTS_DIR = ROOT / "docs" / "05-resultados"


def _load() -> tuple[list[dict], dict]:
    csv_path = RESULTS_DIR / "run_results.csv"
    json_path = RESULTS_DIR / "metricas_globais.json"
    if not csv_path.exists() or not json_path.exists():
        raise FileNotFoundError("Rode 'python -m app.evaluation.runner classify' primeiro")
    with csv_path.open() as f:
        rows = list(csv.DictReader(f))
    summary = json.loads(json_path.read_text())
    return rows, summary


def _fmt_metrics(m: dict) -> str:
    if not m or m.get("n", 0) == 0:
        return "—"
    return (
        f"acc={m['accuracy']:.3f} | P={m['precision_pos']:.3f} | "
        f"R={m['recall_pos']:.3f} | F1={m['f1_pos']:.3f} | F1macro={m['f1_macro']:.3f}"
    )


def _row_for_config(summary: dict, cfg: str, mode: str) -> tuple[float, str]:
    m = summary["configs"][cfg][mode]["global"]
    return m["f1_macro"], _fmt_metrics(m)


def build_report() -> str:
    rows, summary = _load()
    n = summary["n_docs"]

    out: list[str] = []
    out.append("# Relatorio E-001 — Comparacao Config A / B / C\n")
    out.append(f"**N = {n}** documentos (LOO Cross-Validation para Config B/C).\n")
    out.append("Gerado automaticamente por `app.evaluation.report`.\n")

    # Tabela comparativa principal
    out.append("\n## 1. Metricas globais\n")
    out.append("| Config | Threshold | Accuracy | Precision | Recall | F1 (pos) | F1 macro |")
    out.append("|---|---|---|---|---|---|---|")
    for cfg in ("A", "B", "C"):
        for mode in ("uniform", "adaptive"):
            m = summary["configs"][cfg][mode]["global"]
            out.append(
                f"| **{cfg}** | {mode} | {m['accuracy']:.3f} | {m['precision_pos']:.3f} "
                f"| {m['recall_pos']:.3f} | {m['f1_pos']:.3f} | {m['f1_macro']:.3f} |"
            )

    # Vencedor
    best = max(
        ((cfg, mode, summary["configs"][cfg][mode]["global"]["f1_macro"])
         for cfg in ("A", "B", "C") for mode in ("uniform", "adaptive")),
        key=lambda x: x[2],
    )
    out.append(f"\n**Vencedor (F1 macro)**: Config {best[0]} com threshold {best[1]} (F1 macro = {best[2]:.3f}).\n")

    # Confusoes globais
    out.append("\n## 2. Matrizes de confusao (global, threshold uniforme)\n")
    out.append("| Config | TP | TN | FP | FN |")
    out.append("|---|---|---|---|---|")
    for cfg in ("A", "B", "C"):
        c = summary["configs"][cfg]["uniform"]["global"]["confusion"]
        out.append(f"| **{cfg}** | {c['tp']} | {c['tn']} | {c['fp']} | {c['fn']} |")

    # Estratificacao por modo
    out.append("\n## 3. Estratificacao por modo (digital / scan / photo)\n")
    for cfg in ("A", "B", "C"):
        by_mode = summary["configs"][cfg]["uniform"]["by_mode"]
        out.append(f"\n### Config {cfg} (threshold uniforme)\n")
        out.append("| Modo | N | Accuracy | F1 macro |")
        out.append("|---|---|---|---|")
        for mode, m in sorted(by_mode.items()):
            out.append(
                f"| {mode} | {m['n']} | {m['accuracy']:.3f} | {m['f1_macro']:.3f} |"
            )

    # Estratificacao por label
    out.append("\n## 4. Estratificacao por label (clinical / non-clinical / ambiguous)\n")
    for cfg in ("A", "B", "C"):
        by_label = summary["configs"][cfg]["uniform"]["by_label"]
        out.append(f"\n### Config {cfg} (threshold uniforme)\n")
        out.append("| Label | N | Accuracy | F1 macro |")
        out.append("|---|---|---|---|")
        for lbl, m in sorted(by_label.items()):
            out.append(
                f"| {lbl} | {m['n']} | {m['accuracy']:.3f} | {m['f1_macro']:.3f} |"
            )

    # FP / FN listados (para inspecao manual no item 2.5)
    out.append("\n## 5. Falsos Positivos e Falsos Negativos por configuracao\n")
    for cfg in ("A", "B", "C"):
        sub = [r for r in rows if r["config"] == cfg]
        fps = [r for r in sub if int(r["expected_valid"]) == 0 and int(r["valid_uniform"]) == 1]
        fns = [r for r in sub if int(r["expected_valid"]) == 1 and int(r["valid_uniform"]) == 0]
        out.append(f"\n### Config {cfg}\n")
        out.append(f"**Falsos positivos ({len(fps)})** — aceitos mas eram invalidos:\n")
        if fps:
            for r in fps:
                out.append(
                    f"- `{r['filename']}` (score={r['score']}, label={r['label']}, "
                    f"strategy={r['data_strategy']})"
                )
        else:
            out.append("- nenhum")
        out.append(f"\n**Falsos negativos ({len(fns)})** — rejeitados mas eram validos:\n")
        if fns:
            for r in fns:
                out.append(
                    f"- `{r['filename']}` (score={r['score']}, label={r['label']}, "
                    f"strategy={r['data_strategy']})"
                )
        else:
            out.append("- nenhum")

    # Uniforme vs adaptivo (E-003)
    out.append("\n## 6. Limiar uniforme vs adaptivo (E-003 pre-registrado)\n")
    out.append("| Config | F1 macro uniforme | F1 macro adaptivo | Delta |")
    out.append("|---|---|---|---|")
    for cfg in ("A", "B", "C"):
        f_u = summary["configs"][cfg]["uniform"]["global"]["f1_macro"]
        f_a = summary["configs"][cfg]["adaptive"]["global"]["f1_macro"]
        out.append(f"| **{cfg}** | {f_u:.3f} | {f_a:.3f} | {f_a - f_u:+.3f} |")

    out.append("\n*Criterio pre-registrado (ADR-003): se ΔF1 < 0.02 em todas as configs, "
               "considerar inconclusivo e migrar para E-004 (limiar por extraction_quality).*\n")

    return "\n".join(out)


def main() -> None:
    text = build_report()
    out = RESULTS_DIR / "relatorio-e001.md"
    out.write_text(text, encoding="utf-8")
    print(f"OK: {out} ({len(text.splitlines())} linhas)")


if __name__ == "__main__":
    main()
