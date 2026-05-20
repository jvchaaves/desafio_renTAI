from dataclasses import dataclass

from ..config import settings

SPECIALTY_ADJUSTMENTS: dict[str, float] = {
    # Mais permissivo (FN alto custo)
    "cardiologia": -0.10,
    "oncologia": -0.10,
    "pediatria": -0.08,
    "neurologia": -0.05,
    # Mais conservador (FP alto custo)
    "dermatologia": 0.05,
    "psiquiatria": 0.07,
}


@dataclass
class ThresholdDecision:
    threshold: float
    reason: str


class ThresholdPolicy:
    """Resolve threshold final dado specialty opcional."""

    def __init__(self, base: float | None = None, adaptive: bool | None = None) -> None:
        self.base = settings.classification_threshold if base is None else base
        self.adaptive = (
            settings.adaptive_threshold_enabled if adaptive is None else adaptive
        )

    def resolve(self, specialty: str | None) -> ThresholdDecision:
        base = self.base
        if not self.adaptive:
            return ThresholdDecision(
                threshold=base,
                reason=f"base {base} (modo adaptativo desligado)",
            )
        if specialty is None or not specialty.strip():
            return ThresholdDecision(
                threshold=base,
                reason=f"base {base} (specialty nao informada)",
            )

        key = specialty.strip().lower()
        adj = SPECIALTY_ADJUSTMENTS.get(key, 0.0)
        if adj == 0.0:
            return ThresholdDecision(
                threshold=base,
                reason=f"base {base} (especialidade '{specialty}' sem ajuste registrado)",
            )

        final = max(0.0, min(1.0, base + adj))
        sign = "+" if adj > 0 else ""
        return ThresholdDecision(
            threshold=final,
            reason=f"base {base} {sign}{adj:.2f} ({key})",
        )
