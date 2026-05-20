def compute_extraction_quality(text: str, pages: int) -> float:
    """
    Retorna score em [0, 1] estimando confiabilidade do texto extraído.

    Componentes:
    - alpha_ratio: fração de caracteres alfabéticos no texto extraído
      (baixo = ruído de OCR, fragmentação)
    - density: densidade de caracteres por página (baixo = pouco
      conteúdo capturado relativo ao tamanho do documento)

    Texto totalmente vazio retorna 0.0.
    """
    if not text or pages <= 0:
        return 0.0

    total_chars = len(text)
    if total_chars == 0:
        return 0.0

    alpha_chars = sum(1 for c in text if c.isalpha() or c == " ")
    alpha_ratio = alpha_chars / total_chars  # [0, 1]

    # Densidade típica de página: ~500-2000 chars úteis.
    # Saturamos em 500 para não premiar páginas excessivamente densas.
    chars_per_page = total_chars / pages
    density_score = min(1.0, chars_per_page / 500.0)

    quality = alpha_ratio * density_score
    return max(0.0, min(1.0, quality))
