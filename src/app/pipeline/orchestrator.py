from __future__ import annotations

import threading
import time
import uuid
from pathlib import Path
from typing import Literal

import numpy as np

from ..api.schemas import (
    ConfigurationType,
    FusionWeights,
    LabelType,
    ProcessingPath,
    ReasonType,
    SubSignals,
    ValidateResponse,
)
from ..classifiers import (
    ClassificationOutput,
    ClipVisualClassifier,
    EmbeddingsCentroidClassifier,
)
from ..classifiers.embeddings import build_centroids
from ..config import settings
from ..fusion import fuse_scores
from ..pipeline.router import DocumentRouter
from ..thresholds.policy import ThresholdPolicy
from ..utils.logging import logger


class Orchestrator:
    """Componente unico chamado pelo endpoint /v1/validate."""

    def __init__(
        self,
        *,
        configuration: ConfigurationType | None = None,
        threshold_policy: ThresholdPolicy | None = None,
    ) -> None:
        self.router = DocumentRouter()
        self.text_clf = EmbeddingsCentroidClassifier()
        self.visual_clf = ClipVisualClassifier()
        self.policy = threshold_policy or ThresholdPolicy()
        self.configuration: ConfigurationType = (
            configuration or settings.active_configuration
        )
        self._fit_lock = threading.Lock()
        self._fit_done = False

    def fit_text_classifier(
        self,
        positive_texts: list[str],
        negative_texts: list[str],
    ) -> None:
        """Calibra centroides do classificador textual (Config B/C)."""
        with self._fit_lock:
            self.text_clf.fit(positive_texts, negative_texts)
            self._fit_done = True

    def fit_text_with_centroids(self, *, emb_pos: np.ndarray, emb_neg: np.ndarray) -> None:
        """Atalho para LOO — recebe embeddings ja calculados."""
        with self._fit_lock:
            self.text_clf.fit_with_centroids(build_centroids(emb_pos, emb_neg))
            self._fit_done = True

    @property
    def is_text_fit(self) -> bool:
        return self._fit_done

    def validate(
        self,
        *,
        file_bytes: bytes,
        mime: str,
        specialty: str | None = None,
        request_id: str | None = None,
    ) -> ValidateResponse:
        t0 = time.perf_counter()
        req_id = request_id or uuid.uuid4().hex

        try:
            doc = self.router.extract(file_bytes, mime)
        except Exception as exc:
            logger.exception("orchestrator.extract_failed", request_id=req_id)
            return self._invalid_response(
                request_id=req_id,
                reason="file_unreadable",
                detail=f"Falha na extracao: {exc}",
                processing_path="pdf_native",
                latency_ms=int((time.perf_counter() - t0) * 1000),
            )

        text_out: ClassificationOutput | None = None
        visual_out: ClassificationOutput | None = None

        if self.configuration in ("B", "C"):
            if not self._fit_done:
                logger.warning("orchestrator.text_not_fit_skip")
            else:
                try:
                    text_out = self.text_clf.classify(doc)
                except Exception as exc:
                    logger.exception("orchestrator.text_failed", request_id=req_id)
                    text_out = ClassificationOutput(
                        score=0.5, label="neutral",
                        justification=f"Falha no classificador textual: {exc}",
                        classifier_name="embeddings_centroid",
                    )

        if self.configuration in ("A", "C"):
            try:
                visual_out = self.visual_clf.classify_image(doc.first_page_image_png)
            except Exception as exc:
                logger.exception("orchestrator.visual_failed", request_id=req_id)
                visual_out = ClassificationOutput(
                    score=0.5, label="neutral",
                    justification=f"Falha no classificador visual: {exc}",
                    classifier_name="clip_zero_shot",
                )

        if self.configuration == "A":
            fused = self._wrap_single(visual_out, doc.extraction_quality, source="visual")
        elif self.configuration == "B":
            fused = self._wrap_single(text_out, doc.extraction_quality, source="text")
        else:
            fused = fuse_scores(text_out, visual_out, doc.extraction_quality)

        decision = self.policy.resolve(specialty)
        valid = fused.score >= decision.threshold

        sub_signals = SubSignals(
            text=(text_out.sub_signals if text_out else {}),
            visual=(visual_out.sub_signals if visual_out else {}),
            extraction_quality=round(doc.extraction_quality, 4),
            fusion_weights=FusionWeights(
                text=fused.weights_used.get("text", 0.0),
                visual=fused.weights_used.get("visual", 0.0),
            ),
        )

        label: LabelType = "clinical" if valid else "non_clinical"
        reason: ReasonType | None = None if valid else "non_clinical"
        # Heuristica para input nao-processavel: texto vazio + imagem vazia
        if not valid and not doc.text and len(doc.first_page_image_png) < 100:
            reason = "no_content"

        latency_ms = int((time.perf_counter() - t0) * 1000)
        logger.info(
            "orchestrator.done",
            request_id=req_id,
            valid=valid,
            score=round(fused.score, 4),
            configuration=self.configuration,
            mode=doc.mode,
            threshold=decision.threshold,
            latency_ms=latency_ms,
        )

        return ValidateResponse(
            valid=valid,
            score=round(fused.score, 4),
            label=label,
            threshold_applied=decision.threshold,
            threshold_reason=decision.reason,
            justification=fused.justification,
            reason=reason,
            doc_type_detected=None,  # nao inferido nesta versao
            processing_path=_map_mode_to_path(doc.mode),
            sub_signals=sub_signals,
            request_id=req_id,
            latency_ms=latency_ms,
        )

    def _wrap_single(
        self,
        signal: ClassificationOutput | None,
        extraction_quality: float,
        *,
        source: Literal["text", "visual"],
    ) -> object:
        from ..fusion.score_fusion import FusedResult
        if signal is None or signal.label == "neutral":
            return FusedResult(
                score=0.5, label="non_clinical",
                justification=(
                    f"Configuracao '{self.configuration}' nao produziu sinal {source} valido."
                ),
                weights_used={"text": 0.0, "visual": 0.0},
            )
        return FusedResult(
            score=signal.score,
            label=signal.label if signal.label != "neutral" else "non_clinical",
            justification=signal.justification,
            weights_used={"text": 1.0 if source == "text" else 0.0,
                          "visual": 1.0 if source == "visual" else 0.0},
        )

    def _invalid_response(
        self,
        *,
        request_id: str,
        reason: ReasonType,
        detail: str,
        processing_path: ProcessingPath,
        latency_ms: int,
    ) -> ValidateResponse:
        return ValidateResponse(
            valid=False, score=0.0, label="non_clinical",
            threshold_applied=settings.classification_threshold,
            threshold_reason="erro de processamento — threshold nao aplicado",
            justification=detail,
            reason=reason,
            doc_type_detected=None,
            processing_path=processing_path,
            sub_signals=SubSignals(
                extraction_quality=0.0,
                fusion_weights=FusionWeights(text=0.0, visual=0.0),
            ),
            request_id=request_id, latency_ms=latency_ms,
        )


def _map_mode_to_path(mode: str) -> ProcessingPath:
    mapping = {"pdf_native": "pdf_native", "ocr": "ocr", "image_direct": "image_direct"}
    return mapping.get(mode, "ocr")  # type: ignore[return-value]


_orch_lock = threading.Lock()
_orch: Orchestrator | None = None


def get_orchestrator() -> Orchestrator:
    global _orch
    if _orch is None:
        with _orch_lock:
            if _orch is None:
                _orch = Orchestrator()
                _load_centroids_artifact(_orch)
    return _orch


def _load_centroids_artifact(orch: Orchestrator) -> None:
    """
    Carrega centroides pre-computados de artifacts/centroids.npz (ADR-005).

    Esse arquivo e gerado offline por:
        PYTHONPATH=src python -m app.training.build_artifact

    Se o artifact nao existir, o serviço sobe mas a Config B/C nao funciona
    ate ele ser gerado. Config A (so CLIP) continua disponivel.
    """
    repo_root = Path(__file__).resolve().parents[3]
    npz_path = repo_root / "artifacts" / "centroids.npz"
    meta_path = repo_root / "artifacts" / "centroids.meta.json"

    if not npz_path.exists():
        logger.warning(
            "orchestrator.artifact_missing",
            path=str(npz_path.relative_to(repo_root)),
            hint="rode 'python -m app.training.build_artifact' para gerar",
        )
        return

    try:
        import json as _json
        from ..classifiers.embeddings import CentroidPair

        data = np.load(npz_path)
        meta = _json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}
        centroids = CentroidPair(
            positive=data["positive"],
            negative=data["negative"],
            n_positive=int(meta.get("n_positive", 0)),
            n_negative=int(meta.get("n_negative", 0)),
        )
        orch.text_clf.fit_with_centroids(centroids)
        orch._fit_done = True
        logger.info(
            "orchestrator.artifact_loaded",
            n_pos=centroids.n_positive,
            n_neg=centroids.n_negative,
            dim=int(centroids.positive.shape[0]),
            built_at=meta.get("built_at_utc"),
        )
    except Exception:
        logger.exception("orchestrator.artifact_load_failed")
