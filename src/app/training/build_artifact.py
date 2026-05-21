from __future__ import annotations

import csv
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from ..classifiers.embeddings import EMBEDDING_MODEL, build_centroids, encode_texts
from ..utils.logging import logger, setup_logging

ROOT = Path(__file__).resolve().parents[3]
LABELS_CSV = ROOT / "data" / "labeled" / "labels.csv"
CACHE_DIR = ROOT / "cache" / "extracted"
ARTIFACTS_DIR = ROOT / "artifacts"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _index_cache_by_filename() -> dict[str, str]:
    """
    Mapeia filename → texto a partir do cache de extração.

    Usamos filename (não file_id) porque o hash do file_id pode divergir
    entre cache antigo e labels.csv atual sem que o conteúdo mude.
    """
    by_name: dict[str, str] = {}
    for jp in CACHE_DIR.glob("*.json"):
        try:
            meta = json.loads(jp.read_text(encoding="utf-8"))
            name = meta.get("filename")
            text = meta.get("text", "")
            if name and text and len(text) >= 10:
                by_name[name] = text
        except Exception:
            continue
    return by_name


def build() -> dict:
    """Constroi o artifact e salva em artifacts/. Retorna metadata."""
    setup_logging("INFO")
    if not LABELS_CSV.exists():
        raise RuntimeError(f"labels.csv ausente em {LABELS_CSV}")
    if not CACHE_DIR.exists() or not any(CACHE_DIR.iterdir()):
        raise RuntimeError(
            f"Cache de extracao vazio em {CACHE_DIR}. "
            "Rode 'PYTHONPATH=src python -m app.evaluation.runner extract' antes."
        )

    cache_by_name = _index_cache_by_filename()
    if not cache_by_name:
        raise RuntimeError(f"Cache vazio ou inválido em {CACHE_DIR}")

    pos_texts: list[str] = []
    neg_texts: list[str] = []
    skipped = 0
    with LABELS_CSV.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            label = row.get("label")
            if label not in ("clinical", "non-clinical"):
                continue  # ignora ambiguous no fit
            text = cache_by_name.get(row["filename"])
            if text is None:
                skipped += 1
                continue
            if label == "clinical":
                pos_texts.append(text)
            else:
                neg_texts.append(text)

    if not pos_texts or not neg_texts:
        raise RuntimeError(
            f"Sem exemplos suficientes: n_pos={len(pos_texts)}, n_neg={len(neg_texts)}"
        )

    logger.info("artifact.encoding", n_pos=len(pos_texts), n_neg=len(neg_texts))
    emb_pos = encode_texts(pos_texts)
    emb_neg = encode_texts(neg_texts)
    centroids = build_centroids(emb_pos, emb_neg)

    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    npz_path = ARTIFACTS_DIR / "centroids.npz"
    meta_path = ARTIFACTS_DIR / "centroids.meta.json"

    np.savez_compressed(
        npz_path,
        positive=centroids.positive,
        negative=centroids.negative,
    )

    meta = {
        "version": "1",
        "embedding_model": EMBEDDING_MODEL,
        "dim": int(emb_pos.shape[1]),
        "n_positive": centroids.n_positive,
        "n_negative": centroids.n_negative,
        "n_skipped_no_cache": skipped,
        "labels_csv_sha256": _sha256(LABELS_CSV),
        "built_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False))

    logger.info(
        "artifact.built",
        npz=str(npz_path.relative_to(ROOT)),
        meta=str(meta_path.relative_to(ROOT)),
        **{k: v for k, v in meta.items() if k != "labels_csv_sha256"},
    )
    return meta


def main() -> int:
    try:
        build()
        return 0
    except Exception as exc:
        logger.exception("artifact.failed", err=str(exc))
        return 1


if __name__ == "__main__":
    sys.exit(main())
