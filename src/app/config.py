from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ROOT / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Classificação (ADR-003) ---
    # Threshold base 0.50 = ponto de equilibrio teorico apos a calibracao
    # sigmoid do score textual (T=10). Ver ADR-003 secao "calibracao do limiar".
    classification_threshold: float = 0.50
    adaptive_threshold_enabled: bool = True

    # --- Fusão (ADR-002) — pesos default, modulados por extraction_quality ---
    text_weight: float = 0.6
    visual_weight: float = 0.4

    # --- Configuração ativa (decidida empiricamente em E-001) ---
    # Vencedor: C (fusão) com threshold adaptativo (F1 macro 0.564)
    active_configuration: Literal["A", "B", "C"] = "C"

    # --- Limites da API ---
    max_file_size_mb: int = 20
    allowed_mime_types: str = "application/pdf,image/png,image/jpeg,image/tiff"

    # --- Observabilidade ---
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"

    @property
    def allowed_mime_list(self) -> list[str]:
        return [m.strip() for m in self.allowed_mime_types.split(",") if m.strip()]

    @property
    def max_file_size_bytes(self) -> int:
        return self.max_file_size_mb * 1024 * 1024


settings = Settings()
