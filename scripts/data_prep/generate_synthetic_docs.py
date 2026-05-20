"""
Gera documentos sintéticos para substituir self-generated quando o
candidato não tem material disponível.

Estratégia: self-generated (synthetic) — declarado em labels.csv.
Foco: imagens visualmente reconhecíveis como o tipo declarado, suficientes
para testar classificação multimodal.
"""

from pathlib import Path
import random

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import requests
from PIL import Image, ImageDraw, ImageFont, ImageFilter

RAW = Path(__file__).resolve().parents[2] / "data" / "raw"
NON = RAW / "non_clinical"
AMB = RAW / "ambiguous"
CLI = RAW / "clinical"

FONT_REGULAR = "/System/Library/Fonts/Helvetica.ttc"


def _font(size: int):
    try:
        return ImageFont.truetype(FONT_REGULAR, size)
    except Exception:
        return ImageFont.load_default()


# --- Substitutos visuais CC0 via picsum.photos ---

def download_picsum(out_path: Path, w: int, h: int, seed: str) -> None:
    if out_path.exists():
        print(f"SKIP: {out_path.name}")
        return
    url = f"https://picsum.photos/seed/{seed}/{w}/{h}"
    r = requests.get(url, timeout=30, allow_redirects=True)
    r.raise_for_status()
    out_path.write_bytes(r.content)
    print(f"OK: {out_path.name} ({out_path.stat().st_size} bytes)")


def generate_picsum_substitutes() -> None:
    # Para CLIP: portrait → "selfie"; food → "comida"; pet/animal → "pet"
    items = [
        (NON / "synthetic_selfie.jpg", 600, 800, "portrait-person"),
        (NON / "synthetic_food.jpg", 800, 600, "food-meal-plate"),
        (NON / "synthetic_pet.jpg", 800, 600, "dog-cat-pet"),
    ]
    for path, w, h, seed in items:
        try:
            download_picsum(path, w, h, seed)
        except Exception as e:
            print(f"FAIL picsum {path.name}: {e}")


# --- Documentos sintéticos gerados ---

def gen_whatsapp_print() -> None:
    out = NON / "synthetic_whatsapp_print.png"
    if out.exists():
        print(f"SKIP: {out.name}")
        return
    W, H = 720, 1280
    img = Image.new("RGB", (W, H), color="#ECE5DD")
    draw = ImageDraw.Draw(img)
    # Header verde estilo WhatsApp
    draw.rectangle([0, 0, W, 90], fill="#075E54")
    draw.text((100, 30), "Joao - amigo", fill="white", font=_font(28))
    draw.text((100, 60), "online", fill="#90CAF9", font=_font(18))
    # Mensagens
    msgs = [
        ("recebido", "Oi! Tudo bem por ai?"),
        ("enviado", "Tudo otimo! E voce?"),
        ("recebido", "Vamos no cinema sabado?"),
        ("enviado", "Bora! Que filme?"),
        ("recebido", "Pode ser aquele novo de acao"),
        ("enviado", "Fechado! Te ligo amanha pra combinar"),
    ]
    y = 130
    for tipo, txt in msgs:
        cor = "#DCF8C6" if tipo == "enviado" else "white"
        x_box = W - 480 if tipo == "enviado" else 30
        draw.rounded_rectangle([x_box, y, x_box + 450, y + 80], radius=15, fill=cor)
        draw.text((x_box + 20, y + 25), txt, fill="black", font=_font(22))
        y += 110
    img.save(out)
    print(f"OK: {out.name}")


def gen_rg_anonimo() -> None:
    out = NON / "synthetic_rg_anonimo.png"
    if out.exists():
        print(f"SKIP: {out.name}")
        return
    W, H = 1000, 650
    img = Image.new("RGB", (W, H), color="#FAFAFA")
    draw = ImageDraw.Draw(img)
    # Borda externa
    draw.rectangle([10, 10, W - 10, H - 10], outline="#1976D2", width=4)
    # Brasao placeholder (circulo)
    draw.ellipse([40, 40, 140, 140], outline="#1976D2", width=3)
    draw.text((60, 75), "BR", fill="#1976D2", font=_font(40))
    # Titulo
    draw.text((180, 50), "REPUBLICA FEDERATIVA DO BRASIL", fill="#1976D2", font=_font(22))
    draw.text((180, 80), "CARTEIRA DE IDENTIDADE", fill="#1976D2", font=_font(20))
    draw.text((180, 110), "(documento ficticio para teste)", fill="#666", font=_font(14))
    # Campos
    fields = [
        (40, 200, "NOME:"),
        (40, 240, "[ANONIMIZADO]"),
        (40, 290, "FILIACAO:"),
        (40, 330, "[ANONIMIZADO]"),
        (40, 380, "DATA DE NASCIMENTO:"),
        (40, 420, "00/00/0000"),
        (40, 470, "REGISTRO GERAL:"),
        (40, 510, "00.000.000-X"),
    ]
    for x, y, txt in fields:
        if "ANONIMIZADO" in txt or txt.startswith("00") or txt.startswith("0"):
            draw.text((x, y), txt, fill="#999", font=_font(20))
        else:
            draw.text((x, y), txt, fill="black", font=_font(18))
    # Espaço foto
    draw.rectangle([700, 200, 950, 480], outline="black", width=2)
    draw.text((760, 320), "FOTO", fill="#999", font=_font(24))
    draw.text((720, 350), "(anonimizado)", fill="#999", font=_font(14))
    img.save(out)
    print(f"OK: {out.name}")


def gen_recibo_supermercado() -> None:
    out = NON / "synthetic_recibo_supermercado.png"
    if out.exists():
        print(f"SKIP: {out.name}")
        return
    W, H = 400, 700
    img = Image.new("RGB", (W, H), color="white")
    draw = ImageDraw.Draw(img)
    lines = [
        (20, 20, "SUPERMERCADO BOM PRECO", _font(18), True),
        (20, 45, "CNPJ 12.345.678/0001-90", _font(12), False),
        (20, 65, "RUA DAS FLORES, 123 - CENTRO", _font(11), False),
        (20, 90, "CUPOM FISCAL ELETRONICO", _font(14), True),
        (20, 130, "ITEM  DESCRICAO        VALOR", _font(11), False),
        (20, 155, "001   ARROZ TIPO 1 5KG  22,90", _font(11), False),
        (20, 175, "002   FEIJAO CARIOCA 1K  8,50", _font(11), False),
        (20, 195, "003   OLEO DE SOJA 900   5,99", _font(11), False),
        (20, 215, "004   ACUCAR REFINADO 1  4,29", _font(11), False),
        (20, 235, "005   CAFE TORRADO 500   18,90", _font(11), False),
        (20, 255, "006   LEITE INTEGRAL 1L  6,49", _font(11), False),
        (20, 280, "TOTAL ............ R$ 67,07", _font(14), True),
        (20, 320, "FORMA DE PAGAMENTO: PIX", _font(11), False),
        (20, 345, "TROCO: R$ 0,00", _font(11), False),
        (20, 400, "19/05/2026 14:32", _font(11), False),
        (20, 430, "ATENDENTE: 42", _font(11), False),
        (20, 470, "OBRIGADO PELA PREFERENCIA!", _font(12), True),
        (20, 510, "VISITE NOSSO SITE", _font(10), False),
        (20, 530, "WWW.BOMPRECO.COM.BR", _font(10), False),
        (20, 600, "= = = = = = = = = = =", _font(10), False),
    ]
    for x, y, txt, font, _bold in lines:
        draw.text((x, y), txt, fill="black", font=font)
    img.save(out)
    print(f"OK: {out.name}")


def gen_embalagem_remedio() -> None:
    out = AMB / "synthetic_embalagem_remedio.png"
    if out.exists():
        print(f"SKIP: {out.name}")
        return
    W, H = 800, 600
    img = Image.new("RGB", (W, H), color="#F0F8FF")
    draw = ImageDraw.Draw(img)
    # Caixa
    draw.rectangle([100, 100, 700, 500], fill="white", outline="#1565C0", width=5)
    draw.rectangle([100, 100, 700, 200], fill="#1565C0")
    draw.text((130, 130), "PARACETAMOL", fill="white", font=_font(40))
    draw.text((130, 175), "500 mg", fill="white", font=_font(20))
    # Conteudo da caixa
    draw.text((130, 230), "Comprimidos revestidos", fill="black", font=_font(18))
    draw.text((130, 260), "20 comprimidos", fill="black", font=_font(22))
    draw.text((130, 310), "Indicacao: analgesico e antitermico", fill="black", font=_font(14))
    draw.text((130, 335), "Posologia: 1 comp a cada 6h", fill="black", font=_font(14))
    draw.text((130, 360), "Uso adulto", fill="black", font=_font(14))
    draw.text((130, 410), "MS - 1.0000.0000.000-1", fill="#666", font=_font(12))
    draw.text((130, 430), "Lote: 12345  Val: 12/2027", fill="#666", font=_font(12))
    draw.text((130, 460), "Industria farmaceutica generica", fill="#666", font=_font(12))
    img.save(out)
    print(f"OK: {out.name}")


def gen_curva_febre() -> None:
    out = AMB / "synthetic_curva_febre.png"
    if out.exists():
        print(f"SKIP: {out.name}")
        return
    fig, ax = plt.subplots(figsize=(8, 6), dpi=100)
    # Fundo cor papel quadriculado
    fig.patch.set_facecolor("#FFFEF5")
    ax.set_facecolor("#FFFEF5")
    # Dados ficticios
    rng = np.random.default_rng(42)
    dias = np.arange(1, 8)
    temps = 36.5 + rng.normal(0, 0.3, 7) + np.array([0, 0.5, 1.8, 2.0, 1.2, 0.4, 0.0])
    # Linha "manuscrita" — varia espessura
    ax.plot(dias, temps, color="blue", linewidth=2.5, marker="o", markersize=8)
    # Anotações manuscritas
    ax.annotate("PICO", xy=(4, temps[3]), xytext=(4.5, 39.5),
                fontsize=14, color="red", fontstyle="italic")
    ax.set_xlabel("Dias", fontsize=14, fontstyle="italic")
    ax.set_ylabel("Temperatura (C)", fontsize=14, fontstyle="italic")
    ax.set_title("Curva de febre - acompanhamento domiciliar", fontsize=14, fontstyle="italic")
    ax.grid(True, color="#DDD", linewidth=0.5)
    ax.set_ylim(35.5, 40.5)
    ax.set_xlim(0.5, 7.5)
    # Adiciona texto "manuscrito"
    ax.text(5.5, 35.8, "anotado por\npaciente", fontsize=10, fontstyle="italic", color="#555")
    plt.tight_layout()
    plt.savefig(out, dpi=100)
    plt.close()
    print(f"OK: {out.name}")


def gen_print_portal_sus() -> None:
    out = AMB / "synthetic_print_portal_sus.png"
    if out.exists():
        print(f"SKIP: {out.name}")
        return
    W, H = 720, 1280
    img = Image.new("RGB", (W, H), color="white")
    draw = ImageDraw.Draw(img)
    # Status bar do celular
    draw.rectangle([0, 0, W, 50], fill="#333")
    draw.text((20, 15), "21:34", fill="white", font=_font(16))
    draw.text((W - 80, 15), "100%", fill="white", font=_font(16))
    # Header do app
    draw.rectangle([0, 50, W, 150], fill="#0066CC")
    draw.text((30, 70), "Meu SUS Digital", fill="white", font=_font(28))
    draw.text((30, 110), "Vacinacao", fill="white", font=_font(20))
    # Lista de vacinas
    vacinas = [
        ("BCG", "01/01/2000", "Posto Centro"),
        ("Hepatite B", "15/01/2000", "Posto Centro"),
        ("Triplice viral", "08/2001", "UBS Bessa"),
        ("Febre amarela", "12/2019", "UBS Bessa"),
        ("COVID-19 (1a dose)", "15/03/2021", "Centro de Convencoes"),
        ("COVID-19 (2a dose)", "20/06/2021", "Centro de Convencoes"),
        ("Influenza", "05/2023", "UBS Bessa"),
    ]
    y = 200
    for nome, data, local in vacinas:
        draw.rectangle([20, y, W - 20, y + 100], outline="#DDD", width=1)
        draw.text((40, y + 15), nome, fill="black", font=_font(20))
        draw.text((40, y + 45), f"Aplicada em: {data}", fill="#555", font=_font(14))
        draw.text((40, y + 70), f"Local: {local}", fill="#555", font=_font(14))
        y += 120
    img.save(out)
    print(f"OK: {out.name}")


def gen_receita_manuscrita() -> None:
    out = AMB / "synthetic_receita_manuscrita.png"
    if out.exists():
        print(f"SKIP: {out.name}")
        return
    W, H = 800, 1000
    # Background cor de papel
    img = Image.new("RGB", (W, H), color="#FFFCEF")
    # Adiciona ruido tipo papel
    arr = np.array(img)
    noise = np.random.default_rng(0).integers(-8, 8, arr.shape, dtype=np.int16)
    arr = np.clip(arr.astype(np.int16) + noise, 0, 255).astype(np.uint8)
    img = Image.fromarray(arr)
    draw = ImageDraw.Draw(img)
    # Tentar uma fonte cursiva/italica
    font_cursive_large = _font(38)
    font_cursive_med = _font(28)
    font_cursive_sm = _font(22)
    # Cabeçalho timbrado
    draw.text((50, 50), "Dr. Pedro Henrique Souza", fill="#0a2e5c", font=_font(22))
    draw.text((50, 80), "Clinica Geral - CRM-PB 67890", fill="#0a2e5c", font=_font(16))
    draw.line([(50, 110), (W - 50, 110)], fill="#0a2e5c", width=2)
    # Corpo "manuscrito" — usar texto italic + cor azul caneta
    pen_color = "#1A237E"
    draw.text((60, 160), "Paciente: Maria das Gracas", fill=pen_color, font=font_cursive_med)
    draw.text((60, 210), "Data: 19 / 05 / 2026", fill=pen_color, font=font_cursive_sm)
    draw.text((60, 290), "Rx", fill=pen_color, font=font_cursive_large)
    draw.text((130, 305), "Amoxicilina 500mg", fill=pen_color, font=font_cursive_med)
    draw.text((130, 355), "Tomar 1 cp de 8/8h", fill=pen_color, font=font_cursive_sm)
    draw.text((130, 395), "por 7 dias", fill=pen_color, font=font_cursive_sm)
    draw.text((60, 480), "Dipirona 500mg s/n", fill=pen_color, font=font_cursive_med)
    draw.text((130, 520), "se febre > 38°C", fill=pen_color, font=font_cursive_sm)
    draw.text((60, 700), "Dr. Pedro H. Souza", fill=pen_color, font=font_cursive_med)
    draw.text((60, 740), "CRM-PB 67890", fill=pen_color, font=font_cursive_sm)
    # Aplicar leve blur para simular caligrafia manuscrita
    img = img.filter(ImageFilter.GaussianBlur(radius=0.7))
    img.save(out)
    print(f"OK: {out.name}")


def gen_laudo_raiox_sintetico() -> None:
    """Substituto para Open-i NIH (que pode ser difícil de baixar automaticamente)."""
    out = CLI / "synthetic_laudo_raiox.png"
    if out.exists():
        print(f"SKIP: {out.name}")
        return
    W, H = 1200, 900
    img = Image.new("RGB", (W, H), color="white")
    draw = ImageDraw.Draw(img)
    # Header timbrado
    draw.rectangle([0, 0, W, 90], fill="#003B71")
    draw.text((30, 25), "Hospital Universitario Federal", fill="white", font=_font(26))
    draw.text((30, 55), "Servico de Radiologia", fill="white", font=_font(16))
    # Identificacao
    draw.text((30, 120), "LAUDO DE RADIOGRAFIA DE TORAX", fill="black", font=_font(22))
    draw.text((30, 170), "Paciente: Ricardo Albuquerque Pinto", fill="black", font=_font(16))
    draw.text((30, 195), "Idade: 47 anos        Sexo: M", fill="black", font=_font(14))
    draw.text((30, 215), "Registro: 2026-RAD-005439", fill="black", font=_font(14))
    draw.text((30, 240), "Data do exame: 18/05/2026", fill="black", font=_font(14))
    # Caixa simulando imagem do raio-x
    draw.rectangle([30, 280, 530, 780], fill="#1a1a1a", outline="black")
    draw.text((150, 510), "[imagem radiografica]", fill="#888", font=_font(20))
    # Laudo (lado direito)
    laudo_txt = [
        "TECNICA: Radiografia simples de torax",
        "em PA e perfil.",
        "",
        "ACHADOS:",
        "Estruturas osseas integras, sem sinais",
        "de fraturas ou consolidacoes anormais.",
        "Espaco pleural livre, sem evidencias",
        "de derrame ou pneumotorax.",
        "Parenquima pulmonar com transparencia",
        "preservada bilateralmente.",
        "Silhueta cardiaca dentro dos limites",
        "da normalidade.",
        "Mediastino centralizado, sem alargamento.",
        "Hilos pulmonares de aspecto habitual.",
        "",
        "CONCLUSAO:",
        "Exame dentro dos parametros da",
        "normalidade. Sem alteracoes agudas.",
    ]
    y = 290
    for line in laudo_txt:
        draw.text((570, y), line, fill="black", font=_font(15))
        y += 22
    # Assinatura
    draw.text((570, 730), "Dr. Helena Carvalho Andrade", fill="black", font=_font(16))
    draw.text((570, 752), "CRM-PB 78901 - Radiologista", fill="black", font=_font(14))
    draw.text((570, 774), "Data do laudo: 18/05/2026", fill="black", font=_font(14))
    img.save(out)
    print(f"OK: {out.name}")


def gen_cartao_vacina_sintetico() -> None:
    """Substituto para CISVALI que falhou no download."""
    out = CLI / "synthetic_cartao_vacina.png"
    if out.exists():
        print(f"SKIP: {out.name}")
        return
    W, H = 900, 600
    img = Image.new("RGB", (W, H), color="#FFF8E1")
    draw = ImageDraw.Draw(img)
    # Borda
    draw.rectangle([15, 15, W - 15, H - 15], outline="#2E7D32", width=4)
    draw.rectangle([15, 15, W - 15, 90], fill="#2E7D32")
    draw.text((40, 30), "MINISTERIO DA SAUDE - SUS", fill="white", font=_font(22))
    draw.text((40, 58), "CARTAO NACIONAL DE VACINACAO - ADULTO", fill="white", font=_font(16))
    # Identificacao paciente
    draw.text((40, 110), "Nome: Beatriz Cordeiro Pinto", fill="black", font=_font(20))
    draw.text((40, 140), "Data de nascimento: 22/11/1985", fill="black", font=_font(14))
    draw.text((40, 162), "Cartao SUS: 700 1122 3344 5566", fill="black", font=_font(14))
    # Tabela vacinas
    draw.text((40, 200), "VACINA", fill="#2E7D32", font=_font(14))
    draw.text((300, 200), "DATA", fill="#2E7D32", font=_font(14))
    draw.text((460, 200), "LOTE", fill="#2E7D32", font=_font(14))
    draw.text((600, 200), "PROFISSIONAL", fill="#2E7D32", font=_font(14))
    draw.line([(30, 222), (W - 30, 222)], fill="#666", width=1)
    vacinas = [
        ("dT - dupla adulto", "10/05/2024", "AS22441", "Enf. Maria Lopes"),
        ("Hepatite B - dose unica reforco", "12/03/2023", "HB99123", "Enf. Carlos Silva"),
        ("Febre amarela", "20/12/2019", "FA88122", "Enf. Ana Souza"),
        ("Triplice viral SCR", "15/04/2010", "SCR77501", "Tec. Pedro Lima"),
        ("Influenza 2026", "12/04/2026", "IF26001", "Enf. Maria Lopes"),
        ("COVID-19 (booster)", "18/02/2024", "CV24010", "Enf. Maria Lopes"),
    ]
    y = 235
    for vac, data, lote, prof in vacinas:
        draw.text((40, y), vac, fill="black", font=_font(13))
        draw.text((300, y), data, fill="black", font=_font(13))
        draw.text((460, y), lote, fill="black", font=_font(13))
        draw.text((600, y), prof, fill="black", font=_font(13))
        y += 28
    # Rodapé
    draw.text((40, 540), "UBS Bessa - Joao Pessoa/PB", fill="#666", font=_font(12))
    draw.text((40, 562), "Documento ficticio gerado para teste de classificador", fill="#999", font=_font(10))
    img.save(out)
    print(f"OK: {out.name}")


def main() -> None:
    NON.mkdir(parents=True, exist_ok=True)
    AMB.mkdir(parents=True, exist_ok=True)
    CLI.mkdir(parents=True, exist_ok=True)

    print("\n=== Substitutos visuais via picsum.photos (CC0) ===")
    generate_picsum_substitutes()

    print("\n=== Documentos sintéticos não-clínicos ===")
    gen_whatsapp_print()
    gen_rg_anonimo()
    gen_recibo_supermercado()

    print("\n=== Documentos sintéticos ambíguos ===")
    gen_embalagem_remedio()
    gen_curva_febre()
    gen_print_portal_sus()
    gen_receita_manuscrita()

    print("\n=== Substitutos clínicos (Open-i e cartão de vacina) ===")
    gen_laudo_raiox_sintetico()
    gen_cartao_vacina_sintetico()


if __name__ == "__main__":
    main()
