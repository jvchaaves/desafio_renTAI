from dataclasses import dataclass

from ..classifiers.base import ClassificationOutput


@dataclass
class FusedResult:
    score: float
    label: str  # 'clinical' | 'non_clinical'
    justification: str
    weights_used: dict[str, float]  # {'text': float, 'visual': float}


def _weights_for_quality(extraction_quality: float) -> tuple[float, float]:
    """Retorna (w_texto, w_visual) com base na qualidade do texto extraido."""
    if extraction_quality > 0.7:
        return 0.7, 0.3
    if extraction_quality >= 0.3:
        return 0.5, 0.5
    return 0.2, 0.8


def fuse_scores(
    text: ClassificationOutput | None,
    visual: ClassificationOutput | None,
    extraction_quality: float,
) -> FusedResult:
    """
    Funde scores. Comportamento:
    - Se SO um sinal valido, usa ele puro (w=1.0).
    - Se texto retornou 'neutral' (sem texto util), ignora — visao dita.
    - Caso geral: media ponderada modulada por extraction_quality.
    """
    if text is None and visual is None:
        return FusedResult(
            score=0.5, label="non_clinical",
            justification="Nenhum sinal de classificacao disponivel.",
            weights_used={"text": 0.0, "visual": 0.0},
        )

    # Casos degenerados: 1 sinal so
    if text is None or text.label == "neutral":
        if visual is None:
            return FusedResult(
                score=text.score if text else 0.5,
                label=(text.label if text else "non_clinical"),
                justification=(text.justification if text else "Sem sinais."),
                weights_used={"text": 0.0, "visual": 0.0},
            )
        score = visual.score
        return FusedResult(
            score=score,
            label="clinical" if score >= 0.5 else "non_clinical",
            justification=(
                f"Texto indisponivel ou neutro — decisao por sinal visual. "
                f"{visual.justification}"
            ),
            weights_used={"text": 0.0, "visual": 1.0},
        )
    if visual is None:
        return FusedResult(
            score=text.score,
            label=text.label if text.label != "neutral" else "non_clinical",
            justification=f"Sinal visual indisponivel. {text.justification}",
            weights_used={"text": 1.0, "visual": 0.0},
        )

    # Caso geral: media ponderada
    w_t, w_v = _weights_for_quality(extraction_quality)
    score = w_t * text.score + w_v * visual.score
    score = max(0.0, min(1.0, score))
    label = "clinical" if score >= 0.5 else "non_clinical"

    justification = (
        f"Decisao por fusao texto+visao com pesos w_texto={w_t}, w_visual={w_v} "
        f"(modulados por extraction_quality={extraction_quality:.2f}). "
        f"Sinal textual: {text.justification} "
        f"Sinal visual: {visual.justification}"
    )
    return FusedResult(
        score=score,
        label=label,
        justification=justification,
        weights_used={"text": w_t, "visual": w_v},
    )
