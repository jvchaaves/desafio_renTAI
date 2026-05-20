from __future__ import annotations

import csv
import hashlib
import json
import re
import sys
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from ..utils.logging import logger


def _group_id(filename: str) -> str:
    """
    Deriva o "grupo" de origem de um arquivo, removendo sufixos de variacao.

    Justificativa: documentos com mesma base de template (ex.: cfm_atestado_v1,
    v2, v3, _em_branco, _com_marca_amostra) compartilham layout/texto base.
    Em Leave-One-Out por documento, deixar 2 irmaos no treino mantem o
    template "memorizado" no centroide — superestima recall.

    Leave-One-Group-Out remove TODOS do mesmo grupo, simulando "doc novo,
    de origem nunca vista".
    """
    name = Path(filename).stem  # tira pasta + extensao
    # Remove sufixos de variacao (ordem importa: mais especifico primeiro)
    name = re.sub(r"_com_marca_amostra$", "", name)
    name = re.sub(r"_em_branco$", "", name)
    name = re.sub(r"_fake_scan$", "", name)
    name = re.sub(r"_anonimo$", "", name)
    name = re.sub(r"_modelo\d+$", "", name)
    name = re.sub(r"_v\d+$", "", name)
    return name

ROOT = Path(__file__).resolve().parents[3]
DATA_RAW = ROOT / "data" / "raw"
LABELS_CSV = ROOT / "data" / "labeled" / "labels.csv"
RESULTS_DIR = ROOT / "docs" / "05-resultados"
CACHE_DIR = ROOT / "cache" / "extracted"


@dataclass
class CachedExtraction:
    """Resultado da extracao persistido em disco."""

    file_id: str
    filename: str
    label: str
    expected_decision: str
    doc_type: str
    mode: str
    specialty: str
    data_strategy: str
    text: str
    extraction_quality: float
    processing_path: str
    image_path: str  # caminho relativo do PNG da primeira pagina


def _file_id(filename: str) -> str:
    return hashlib.sha256(filename.encode()).hexdigest()[:16]


def _infer_mime(path: Path) -> str:
    e = path.suffix.lower()
    if e == ".pdf":
        return "application/pdf"
    if e == ".png":
        return "image/png"
    if e in (".jpg", ".jpeg"):
        return "image/jpeg"
    if e in (".tif", ".tiff"):
        return "image/tiff"
    return "application/octet-stream"


# ----------------------------------------------------------------------
# FASE 1 — EXTRACAO COM CACHE
# ----------------------------------------------------------------------


def extract_all(force: bool = False) -> list[CachedExtraction]:
    """
    Le labels.csv, extrai cada doc via DocumentRouter, persiste em
    cache/extracted/. Idempotente — pula docs ja extraidos a menos que
    force=True.
    """
    from ..pipeline.router import DocumentRouter

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    router = DocumentRouter()

    rows = list(_read_labels())
    logger.info("extract.start", n=len(rows))
    results: list[CachedExtraction] = []

    for idx, row in enumerate(rows):
        fp = DATA_RAW / row["filename"]
        if not fp.exists():
            logger.warning("extract.missing_file", filename=row["filename"])
            continue
        fid = _file_id(row["filename"])
        meta_path = CACHE_DIR / f"{fid}.json"
        img_path = CACHE_DIR / f"{fid}.png"

        if not force and meta_path.exists() and img_path.exists():
            cache = CachedExtraction(**json.loads(meta_path.read_text()))
            results.append(cache)
            logger.info("extract.cached", i=idx, file=row["filename"])
            continue

        try:
            data = fp.read_bytes()
            mime = _infer_mime(fp)
            doc = router.extract(data, mime)
            img_path.write_bytes(doc.first_page_image_png)
            cache = CachedExtraction(
                file_id=fid,
                filename=row["filename"],
                label=row["label"],
                expected_decision=row["expected_decision"],
                doc_type=row.get("doc_type", ""),
                mode=row.get("mode", ""),
                specialty=row.get("specialty", ""),
                data_strategy=row.get("data_strategy", ""),
                text=doc.text,
                extraction_quality=float(doc.extraction_quality),
                processing_path=doc.mode,
                image_path=str(img_path.relative_to(ROOT)),
            )
            meta_path.write_text(json.dumps(cache.__dict__, ensure_ascii=False, indent=2))
            results.append(cache)
            logger.info(
                "extract.ok",
                i=idx, file=row["filename"],
                chars=len(doc.text), quality=round(doc.extraction_quality, 2),
                mode=doc.mode,
            )
        except Exception:
            logger.exception("extract.failed", filename=row["filename"])

    logger.info("extract.done", n=len(results))
    return results


def load_cache() -> list[CachedExtraction]:
    """Carrega todas as extracoes do cache (chamado pela fase 2)."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    out: list[CachedExtraction] = []
    for row in _read_labels():
        fid = _file_id(row["filename"])
        meta_path = CACHE_DIR / f"{fid}.json"
        if not meta_path.exists():
            logger.warning("classify.cache_miss", file=row["filename"])
            continue
        out.append(CachedExtraction(**json.loads(meta_path.read_text())))
    return out


def _read_labels() -> Iterable[dict]:
    with LABELS_CSV.open(encoding="utf-8") as f:
        yield from csv.DictReader(f)


# ----------------------------------------------------------------------
# FASE 2 — CLASSIFICACAO COM CACHE
# ----------------------------------------------------------------------


def classify_all() -> dict:
    """
    Le cache de extracoes e roda as 3 configs com LOO. Salva resultados.
    """
    from ..classifiers import ClipVisualClassifier, EmbeddingsCentroidClassifier
    from ..classifiers.embeddings import build_centroids, encode_texts
    from ..extractors.base import ExtractedDocument
    from ..fusion import fuse_scores
    from ..thresholds.policy import ThresholdPolicy

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    records = load_cache()
    if not records:
        raise RuntimeError("Cache vazio — rode 'extract' primeiro")
    logger.info("classify.loaded", n=len(records))

    pos_idx = [i for i, r in enumerate(records) if r.expected_decision == "valid"]
    neg_idx = [i for i, r in enumerate(records) if r.expected_decision == "invalid"]
    groups = [_group_id(r.filename) for r in records]
    n_groups = len(set(groups))
    logger.info(
        "classify.split",
        n_pos=len(pos_idx),
        n_neg=len(neg_idx),
        n_groups=n_groups,
        mode="leave-one-group-out",
    )

    # Embeddings textuais (filtrando textos vazios)
    texts = [r.text if r.text and len(r.text) > 10 else "" for r in records]
    nonempty = [i for i, t in enumerate(texts) if t]
    emb_by_idx: dict[int, np.ndarray] = {}
    if nonempty:
        logger.info("classify.encoding_text", n=len(nonempty))
        emb_arr = encode_texts([texts[i] for i in nonempty])
        for k, orig_i in enumerate(nonempty):
            emb_by_idx[orig_i] = emb_arr[k]
        logger.info("classify.encoded")

    # CLIP em todas as imagens (1 vez)
    clip_clf = ClipVisualClassifier()
    visual_outs = []
    logger.info("classify.visual_start")
    for i, r in enumerate(records):
        img_bytes = (ROOT / r.image_path).read_bytes()
        vo = clip_clf.classify_image(img_bytes)
        visual_outs.append(vo)
        if (i + 1) % 8 == 0:
            logger.info("classify.visual_progress", done=i + 1, total=len(records))
    logger.info("classify.visual_done")

    # LOO para Config B/C
    policy = ThresholdPolicy()
    text_clf = EmbeddingsCentroidClassifier()
    results: list[dict] = []

    for i, rec in enumerate(records):
        vo = visual_outs[i]

        # Config A: so CLIP
        results.append(_make_result_row("A", rec, text_out=None, visual_out=vo, policy=policy))

        # Leave-One-Group-Out para Config B/C: remove TODOS os irmaos
        # do mesmo template/origem (ver _group_id e ADR sobre validacao).
        text_out = None
        if i in emb_by_idx:
            g_i = groups[i]
            pos_no_i = [j for j in pos_idx if groups[j] != g_i and j in emb_by_idx]
            neg_no_i = [j for j in neg_idx if groups[j] != g_i and j in emb_by_idx]
            if pos_no_i and neg_no_i:
                emb_pos = np.stack([emb_by_idx[j] for j in pos_no_i])
                emb_neg = np.stack([emb_by_idx[j] for j in neg_no_i])
                text_clf.fit_with_centroids(build_centroids(emb_pos, emb_neg))
                fake_doc = ExtractedDocument(
                    text=rec.text, pages=1,
                    mode=rec.processing_path,  # type: ignore[arg-type]
                    extraction_quality=rec.extraction_quality,
                    first_page_image_png=b"",
                )
                text_out = text_clf.classify(fake_doc)

        results.append(_make_result_row("B", rec, text_out=text_out, visual_out=None, policy=policy))

        if text_out is None or text_out.label == "neutral":
            # C cai pra visao
            results.append(_make_result_row("C", rec, text_out=None, visual_out=vo, policy=policy))
        else:
            fused = fuse_scores(text_out, vo, rec.extraction_quality)
            row = _make_fused_row("C", rec, fused.score, text_out, vo, policy)
            results.append(row)

    out_csv = RESULTS_DIR / "run_results.csv"
    _write_csv(out_csv, results)
    logger.info("classify.csv_saved", n=len(results), path=str(out_csv))

    summary = _summarize(results, records)
    out_json = RESULTS_DIR / "metricas_globais.json"
    out_json.write_text(json.dumps(summary, indent=2, ensure_ascii=False))
    logger.info("classify.summary_saved", path=str(out_json))
    return summary


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------


def _make_result_row(
    config: str,
    rec: CachedExtraction,
    *,
    text_out,
    visual_out,
    policy,
) -> dict:
    if config == "A":
        score = visual_out.score if visual_out and visual_out.label != "neutral" else 0.5
    elif config == "B":
        score = text_out.score if text_out and text_out.label != "neutral" else 0.5
    else:  # C single-sided fallback
        score = (
            visual_out.score if visual_out and visual_out.label != "neutral"
            else (text_out.score if text_out and text_out.label != "neutral" else 0.5)
        )
    return _build_row(config, rec, score, text_out, visual_out, policy)


def _make_fused_row(config, rec, score, text_out, visual_out, policy) -> dict:
    return _build_row(config, rec, score, text_out, visual_out, policy)


def _build_row(config, rec, score, text_out, visual_out, policy) -> dict:
    decision_uniform = policy.resolve(None)
    valid_uniform = score >= decision_uniform.threshold

    decision_adapt = policy.resolve(rec.specialty if rec.specialty else None)
    valid_adapt = score >= decision_adapt.threshold

    return {
        "config": config,
        "filename": rec.filename,
        "label": rec.label,
        "expected_decision": rec.expected_decision,
        "doc_type": rec.doc_type,
        "mode": rec.mode,
        "specialty": rec.specialty,
        "data_strategy": rec.data_strategy,
        "extraction_quality": round(rec.extraction_quality, 4),
        "processing_path": rec.processing_path,
        "score": round(float(score), 4),
        "text_score": (
            round(text_out.score, 4) if text_out and text_out.label != "neutral" else None
        ),
        "visual_score": (
            round(visual_out.score, 4) if visual_out and visual_out.label != "neutral" else None
        ),
        "threshold_uniform": decision_uniform.threshold,
        "valid_uniform": int(valid_uniform),
        "threshold_adaptive": decision_adapt.threshold,
        "valid_adaptive": int(valid_adapt),
        "expected_valid": int(rec.expected_decision == "valid"),
    }


def _write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)


def _summarize(results: list[dict], records: list[CachedExtraction]) -> dict:
    out = {"n_docs": len(records), "configs": {}}
    for cfg in ("A", "B", "C"):
        rows = [r for r in results if r["config"] == cfg]
        out["configs"][cfg] = {
            "uniform": _metrics_block(rows, "valid_uniform"),
            "adaptive": _metrics_block(rows, "valid_adaptive"),
        }
    return out


def _metrics_block(rows: list[dict], threshold_key: str) -> dict:
    y_true = [r["expected_valid"] for r in rows]
    y_pred = [r[threshold_key] for r in rows]
    metrics = _compute_metrics(y_true, y_pred)
    by_label = {}
    for lbl in {r["label"] for r in rows}:
        sub = [r for r in rows if r["label"] == lbl]
        by_label[lbl] = _compute_metrics(
            [r["expected_valid"] for r in sub],
            [r[threshold_key] for r in sub],
        )
    by_mode = {}
    for m in {r["mode"] for r in rows if r["mode"]}:
        sub = [r for r in rows if r["mode"] == m]
        by_mode[m] = _compute_metrics(
            [r["expected_valid"] for r in sub],
            [r[threshold_key] for r in sub],
        )
    by_specialty = {}
    for sp in {r["specialty"] for r in rows if r["specialty"]}:
        sub = [r for r in rows if r["specialty"] == sp]
        by_specialty[sp] = _compute_metrics(
            [r["expected_valid"] for r in sub],
            [r[threshold_key] for r in sub],
        )
    return {
        "global": metrics,
        "by_label": by_label,
        "by_mode": by_mode,
        "by_specialty": by_specialty,
    }


def _compute_metrics(y_true, y_pred) -> dict:
    yt = list(y_true)
    yp = list(y_pred)
    n = len(yt)
    if n == 0:
        return {"n": 0}
    tp = sum(1 for a, b in zip(yt, yp, strict=True) if a == 1 and b == 1)
    tn = sum(1 for a, b in zip(yt, yp, strict=True) if a == 0 and b == 0)
    fp = sum(1 for a, b in zip(yt, yp, strict=True) if a == 0 and b == 1)
    fn = sum(1 for a, b in zip(yt, yp, strict=True) if a == 1 and b == 0)
    acc = (tp + tn) / n
    prec = tp / (tp + fp) if (tp + fp) else 0.0
    rec = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * prec * rec / (prec + rec) if (prec + rec) else 0.0
    prec_neg = tn / (tn + fn) if (tn + fn) else 0.0
    rec_neg = tn / (tn + fp) if (tn + fp) else 0.0
    f1_neg = 2 * prec_neg * rec_neg / (prec_neg + rec_neg) if (prec_neg + rec_neg) else 0.0
    return {
        "n": n,
        "accuracy": round(acc, 4),
        "precision_pos": round(prec, 4),
        "recall_pos": round(rec, 4),
        "f1_pos": round(f1, 4),
        "f1_macro": round((f1 + f1_neg) / 2, 4),
        "confusion": {"tp": tp, "tn": tn, "fp": fp, "fn": fn},
    }


# ----------------------------------------------------------------------
# CLI
# ----------------------------------------------------------------------


def main() -> None:
    from ..utils.logging import setup_logging
    setup_logging("INFO")

    phase = sys.argv[1] if len(sys.argv) > 1 else "all"
    if phase == "extract":
        extract_all()
    elif phase == "classify":
        summary = classify_all()
        print(json.dumps(summary, indent=2, ensure_ascii=False))
    elif phase == "all":
        extract_all()
        # Free PaddleOCR antes da classificacao para reduzir pressao de memoria
        import gc

        from ..extractors import ocr as ocr_module
        ocr_module._ocr_instance = None
        gc.collect()
        summary = classify_all()
        print(json.dumps(summary, indent=2, ensure_ascii=False))
    else:
        print(f"phase invalido: {phase!r}. Use extract|classify|all", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
