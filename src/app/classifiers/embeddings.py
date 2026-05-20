from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Any

import numpy as np

from ..extractors.base import ExtractedDocument
from ..utils.logging import logger
from .base import ClassificationOutput, TextClassifierBase

EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"

# Singleton lazy do modelo
_model_lock = threading.Lock()
_model: Any | None = None


def _get_model() -> Any:
    global _model
    if _model is None:
        with _model_lock:
            if _model is None:
                from sentence_transformers import SentenceTransformer
                logger.info("embeddings.load", model=EMBEDDING_MODEL)
                _model = SentenceTransformer(EMBEDDING_MODEL)
                logger.info("embeddings.ready")
    return _model


def encode_texts(texts: list[str]) -> np.ndarray:
    """Encode lista de textos. Retorna array L2-normalizado (cosine=dot)."""
    model = _get_model()
    arr = model.encode(
        texts,
        batch_size=8,
        normalize_embeddings=True,
        show_progress_bar=False,
        convert_to_numpy=True,
    )
    return np.asarray(arr, dtype=np.float32)


@dataclass
class CentroidPair:
    """Centroides positivo e negativo aprendidos no fit."""

    positive: np.ndarray  # (dim,) — vetor medio dos exemplos clinical
    negative: np.ndarray  # (dim,) — vetor medio dos exemplos non-clinical
    n_positive: int
    n_negative: int


class EmbeddingsCentroidClassifier(TextClassifierBase):
    """
    Embeddings -> distancia de centroide.

    Uso em producao:
        clf = EmbeddingsCentroidClassifier()
        clf.fit(texts_pos, texts_neg)  # uma vez, na inicialização
        out = clf.classify(doc)        # por requisição

    Uso em avaliacao (LOO): evaluation/loo.py orquestra recriacao
    do centroide para cada doc removido.
    """

    def __init__(self) -> None:
        self._centroids: CentroidPair | None = None

    def fit(self, texts_positive: list[str], texts_negative: list[str]) -> None:
        if not texts_positive or not texts_negative:
            raise ValueError("Need at least 1 positive and 1 negative example")
        emb_pos = encode_texts(texts_positive)
        emb_neg = encode_texts(texts_negative)
        self._centroids = CentroidPair(
            positive=_l2_normalize(emb_pos.mean(axis=0)),
            negative=_l2_normalize(emb_neg.mean(axis=0)),
            n_positive=len(texts_positive),
            n_negative=len(texts_negative),
        )
        logger.info(
            "embeddings.fit",
            n_pos=len(texts_positive),
            n_neg=len(texts_negative),
            dim=emb_pos.shape[1],
        )

    def fit_with_centroids(self, centroids: CentroidPair) -> None:
        """Atalho — usado por LOO para injetar centroides pre-computados."""
        self._centroids = centroids

    def classify(self, doc: ExtractedDocument) -> ClassificationOutput:
        if self._centroids is None:
            raise RuntimeError("Classifier not fit yet. Call .fit() first.")

        if not doc.text or len(doc.text.strip()) < 3:
            # Sem texto util — score neutro com sinal de baixa confianca
            return ClassificationOutput(
                score=0.5,
                label="neutral",
                justification="Texto extraido vazio ou muito curto; nao foi possivel avaliar.",
                sub_signals={
                    "text_chars": len(doc.text or ""),
                    "extraction_quality": doc.extraction_quality,
                },
                classifier_name="embeddings_centroid",
            )

        emb = encode_texts([doc.text])[0]
        sim_pos = float(np.dot(emb, self._centroids.positive))
        sim_neg = float(np.dot(emb, self._centroids.negative))
        # Sigmoid com temperatura calibra a escala do cosseno.
        # Cossenos de sentence-transformers ficam tipicamente em [0.4, 0.9],
        # entao diff = sim_pos - sim_neg tipicamente em [-0.3, +0.3].
        # T=10 faz com que diff=0.1 (separacao tipica) produza score ~0.73.
        # Justificativa: log(0.7/0.3)/0.1 ~= 8.5, arredondado para 10.
        T = 10.0
        diff = sim_pos - sim_neg
        score = 1.0 / (1.0 + float(np.exp(-diff * T)))
        score = max(0.0, min(1.0, score))

        label = "clinical" if score >= 0.5 else "non_clinical"
        justification = (
            f"Texto extraido tem similaridade {sim_pos:.3f} com classe clinica "
            f"e {sim_neg:.3f} com nao-clinica (cosine). Score fundido {score:.3f}."
        )
        return ClassificationOutput(
            score=score,
            label=label,
            justification=justification,
            sub_signals={
                "sim_positive": round(sim_pos, 4),
                "sim_negative": round(sim_neg, 4),
                "text_chars": len(doc.text),
                "extraction_quality": doc.extraction_quality,
            },
            classifier_name="embeddings_centroid",
        )


def _l2_normalize(v: np.ndarray) -> np.ndarray:
    n = np.linalg.norm(v)
    if n < 1e-12:
        return v
    return v / n


def build_centroids(
    emb_positive: np.ndarray, emb_negative: np.ndarray
) -> CentroidPair:
    """Helper para LOO: dado embeddings ja calculados, monta centroides."""
    return CentroidPair(
        positive=_l2_normalize(emb_positive.mean(axis=0)),
        negative=_l2_normalize(emb_negative.mean(axis=0)),
        n_positive=len(emb_positive),
        n_negative=len(emb_negative),
    )
