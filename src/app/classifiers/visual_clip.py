from __future__ import annotations

import io
import threading
from typing import Any

import numpy as np
from PIL import Image

from ..utils.logging import logger
from .base import ClassificationOutput, VisualClassifierBase

CLIP_MODEL = "ViT-L-14"
CLIP_PRETRAINED = "openai"

POSITIVE_PROMPTS = [
    # Ingles
    "a photo of a medical report document",
    "a scanned medical examination document",
    "a clinical laboratory report with tables and patient data",
    "a medical prescription on paper",
    "a radiology imaging report with text",
    "a medical certificate document",
    # Portugues
    "uma foto de um documento medico",
    "um exame clinico digitalizado",
    "um laudo laboratorial com tabela e dados do paciente",
    "uma receita medica em papel",
    "um laudo de radiologia com texto",
    "um atestado medico",
    "uma prescricao medica com posologia",
    "um hemograma com valores de referencia",
]

NEGATIVE_PROMPTS = [
    # Ingles
    "a selfie photo of a person",
    "a screenshot of a phone screen",
    "a contract or invoice document",
    "a receipt from a store",
    "a casual photo of food",
    "a casual photo of an animal or pet",
    "a photo of a landscape or scenery",
    "a screenshot of a messaging app",
    # Portugues
    "uma selfie de uma pessoa",
    "uma captura de tela de celular",
    "um contrato ou nota fiscal",
    "um recibo de mercado",
    "uma foto casual de comida",
    "uma foto de animal de estimacao",
    "uma foto de paisagem",
    "uma captura de tela de aplicativo de mensagens",
]


_model_lock = threading.Lock()
_model: Any | None = None
_preprocess: Any | None = None
_tokenizer: Any | None = None
_positive_features: np.ndarray | None = None
_negative_features: np.ndarray | None = None


def _load_model_and_prompts() -> None:
    global _model, _preprocess, _tokenizer, _positive_features, _negative_features
    if _model is not None:
        return
    with _model_lock:
        if _model is not None:
            return
        import open_clip
        import torch

        logger.info("clip.load", model=CLIP_MODEL, pretrained=CLIP_PRETRAINED)
        model, _, preprocess = open_clip.create_model_and_transforms(
            CLIP_MODEL, pretrained=CLIP_PRETRAINED
        )
        model.eval()
        tokenizer = open_clip.get_tokenizer(CLIP_MODEL)

        # Pre-computa features dos prompts (so muda se mudarmos os prompts)
        with torch.no_grad():
            pos_tokens = tokenizer(POSITIVE_PROMPTS)
            neg_tokens = tokenizer(NEGATIVE_PROMPTS)
            pos_feat = model.encode_text(pos_tokens)
            neg_feat = model.encode_text(neg_tokens)
            pos_feat = pos_feat / pos_feat.norm(dim=-1, keepdim=True)
            neg_feat = neg_feat / neg_feat.norm(dim=-1, keepdim=True)

        _model = model
        _preprocess = preprocess
        _tokenizer = tokenizer
        _positive_features = pos_feat.cpu().numpy().astype(np.float32)
        _negative_features = neg_feat.cpu().numpy().astype(np.float32)
        logger.info("clip.ready", n_pos_prompts=len(POSITIVE_PROMPTS), n_neg_prompts=len(NEGATIVE_PROMPTS))


def _encode_image(image_png: bytes) -> np.ndarray:
    import torch

    _load_model_and_prompts()
    assert _model is not None and _preprocess is not None

    pil = Image.open(io.BytesIO(image_png)).convert("RGB")
    tensor = _preprocess(pil).unsqueeze(0)  # type: ignore[operator]
    with torch.no_grad():
        feat = _model.encode_image(tensor)
        feat = feat / feat.norm(dim=-1, keepdim=True)
    return feat.cpu().numpy()[0].astype(np.float32)


class ClipVisualClassifier(VisualClassifierBase):
    """Zero-shot via similaridade da imagem com prompts positivos/negativos."""

    def classify_image(self, image_png: bytes) -> ClassificationOutput:
        if not image_png or len(image_png) < 50:
            return ClassificationOutput(
                score=0.5,
                label="neutral",
                justification="Imagem ausente ou vazia; CLIP nao foi acionado.",
                sub_signals={"image_bytes": len(image_png or b"")},
                classifier_name="clip_zero_shot",
            )

        _load_model_and_prompts()
        assert _positive_features is not None and _negative_features is not None

        img_feat = _encode_image(image_png)  # (dim,)

        # Similaridades cosseno (features ja normalizadas)
        sim_pos = _positive_features @ img_feat  # (n_pos,)
        sim_neg = _negative_features @ img_feat  # (n_neg,)

        # Softmax sobre TODOS os prompts juntos para probabilidades calibradas
        all_sims = np.concatenate([sim_pos, sim_neg])
        scaled = all_sims * 100.0  # escala CLIP padrao
        # Numericamente estavel
        scaled -= scaled.max()
        probs = np.exp(scaled) / np.exp(scaled).sum()
        prob_clinical = float(probs[: len(sim_pos)].sum())

        score = max(0.0, min(1.0, prob_clinical))
        label = "clinical" if score >= 0.5 else "non_clinical"

        # Top prompt vencedor (para justificativa)
        top_pos_idx = int(np.argmax(sim_pos))
        top_neg_idx = int(np.argmax(sim_neg))

        justification = (
            f"CLIP atribuiu prob {score:.3f} para documento clinico. "
            f"Prompt visual positivo mais ativado: '{POSITIVE_PROMPTS[top_pos_idx]}' "
            f"(sim={float(sim_pos[top_pos_idx]):.3f}). "
            f"Negativo mais ativado: '{NEGATIVE_PROMPTS[top_neg_idx]}' "
            f"(sim={float(sim_neg[top_neg_idx]):.3f})."
        )

        return ClassificationOutput(
            score=score,
            label=label,
            justification=justification,
            sub_signals={
                "top_positive_prompt": POSITIVE_PROMPTS[top_pos_idx],
                "top_positive_sim": round(float(sim_pos[top_pos_idx]), 4),
                "top_negative_prompt": NEGATIVE_PROMPTS[top_neg_idx],
                "top_negative_sim": round(float(sim_neg[top_neg_idx]), 4),
                "prob_clinical": round(score, 4),
                "prob_non_clinical": round(1.0 - score, 4),
            },
            classifier_name="clip_zero_shot",
        )
