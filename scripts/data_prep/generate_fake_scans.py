"""
Gera versões "fake-scan" de PDFs nativos: renderiza como imagem e
adiciona ruído sintético (rotação, JPEG compressão, blur, contraste
reduzido, sal-pimenta) para simular digitalizações de baixa qualidade.

Também gera versão com marca d'água "AMOSTRA / NAO VALIDO" para
testar o critério N6 da definição operacional.

Estratégia: fake-scan (data_strategy).
"""

from pathlib import Path

import numpy as np
from pdf2image import convert_from_path
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

RAW = Path(__file__).resolve().parents[2] / "data" / "raw"

FONT_REGULAR = "/System/Library/Fonts/Helvetica.ttc"

FAKE_SCANS = [
    {"input": "clinical/lme_federal_PREENCHIDO.pdf",
     "output": "ambiguous/lme_federal_fake_scan.jpg"},
    {"input": "clinical/encaminhamento_se_PREENCHIDO.pdf",
     "output": "ambiguous/encaminhamento_se_fake_scan.jpg"},
    {"input": "clinical/hematosul_hemograma.pdf",
     "output": "ambiguous/hematosul_hemograma_fake_scan.jpg"},
]

WATERMARK = {
    "input": "clinical/cfm_atestado_PREENCHIDO.pdf",
    "output": "ambiguous/cfm_atestado_com_marca_amostra.pdf",
}


def degrade_image(img: Image.Image, seed: int = 0) -> Image.Image:
    rng = np.random.default_rng(seed)
    # 1. Rotacao leve 1.5-3 graus
    angle = float(rng.uniform(-3.0, 3.0))
    img = img.rotate(angle, resample=Image.BICUBIC, expand=False, fillcolor="white")
    # 2. Blur leve (simula desfoco de scanner)
    img = img.filter(ImageFilter.GaussianBlur(radius=0.8))
    # 3. Reduz contraste para simular papel descolorido
    img = ImageEnhance.Contrast(img).enhance(0.85)
    img = ImageEnhance.Brightness(img).enhance(0.95)
    # 4. Adiciona ruido sal-pimenta
    arr = np.array(img)
    if arr.ndim == 3:
        noise_mask = rng.random(arr.shape[:2]) < 0.005
        arr[noise_mask] = 0
        noise_mask = rng.random(arr.shape[:2]) < 0.005
        arr[noise_mask] = 255
    img = Image.fromarray(arr)
    # 5. Saturacao reduzida (papel envelhecido)
    img = ImageEnhance.Color(img).enhance(0.7)
    return img


def make_fake_scan(input_pdf: Path, output_jpg: Path, seed: int) -> None:
    if output_jpg.exists():
        print(f"SKIP: {output_jpg.name}")
        return
    images = convert_from_path(str(input_pdf), dpi=120, first_page=1, last_page=1)
    img = images[0].convert("RGB")
    img = degrade_image(img, seed=seed)
    # Salva como JPEG com qualidade baixa (simula scan comprimido)
    img.save(str(output_jpg), "JPEG", quality=55, optimize=True)
    print(f"OK: {output_jpg.name} ({output_jpg.stat().st_size} bytes)")


def add_amostra_watermark(input_pdf: Path, output_pdf: Path) -> None:
    if output_pdf.exists():
        print(f"SKIP: {output_pdf.name}")
        return
    images = convert_from_path(str(input_pdf), dpi=150, first_page=1, last_page=1)
    img = images[0].convert("RGB")
    W, H = img.size

    # Overlay transparente com texto rotacionado
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    odraw = ImageDraw.Draw(overlay)
    try:
        font = ImageFont.truetype(FONT_REGULAR, 120)
    except Exception:
        font = ImageFont.load_default()
    # Texto rotacionado em diagonal
    text = "AMOSTRA - NAO VALIDO"
    # Cria texto em imagem separada e rotaciona
    txt_img = Image.new("RGBA", (W, 200), (0, 0, 0, 0))
    tdraw = ImageDraw.Draw(txt_img)
    tdraw.text((W // 2 - 600, 50), text, fill=(200, 0, 0, 90), font=font)
    txt_img = txt_img.rotate(30, resample=Image.BICUBIC, expand=False)
    overlay.paste(txt_img, (0, H // 2 - 100), txt_img)
    # Outra linha mais abaixo
    txt_img2 = Image.new("RGBA", (W, 200), (0, 0, 0, 0))
    tdraw2 = ImageDraw.Draw(txt_img2)
    tdraw2.text((W // 2 - 600, 50), text, fill=(200, 0, 0, 70), font=font)
    txt_img2 = txt_img2.rotate(30, resample=Image.BICUBIC, expand=False)
    overlay.paste(txt_img2, (0, H // 2 + 200), txt_img2)

    combined = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
    combined.save(str(output_pdf), "PDF", resolution=150.0)
    print(f"OK: {output_pdf.name}")


def main() -> None:
    for i, item in enumerate(FAKE_SCANS):
        inp = RAW / item["input"]
        out = RAW / item["output"]
        if not inp.exists():
            print(f"SKIP (missing input): {inp.name}")
            continue
        make_fake_scan(inp, out, seed=i + 1)

    inp = RAW / WATERMARK["input"]
    out = RAW / WATERMARK["output"]
    if inp.exists():
        add_amostra_watermark(inp, out)
    else:
        print(f"SKIP watermark (missing input): {inp.name}")


if __name__ == "__main__":
    main()
