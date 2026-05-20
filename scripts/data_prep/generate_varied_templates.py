"""
Gera multiplas variacoes de cada template oficial preenchido com dados
sinteticos. O objetivo e DILUIR o vies do centroide positivo (L1 do
limitacoes-do-dataset.md): com mais variacao em nomes, datas,
especialidades e CRMs, o centroide deixa de aprender padroes especificos
e passa a aprender estrutura clinica geral.

Para cada template, gera N_VARIATIONS arquivos com combinacoes aleatorias
de nome, data, CRM, especialidade e conteudo clinico.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from pathlib import Path

from pdf2image import convert_from_path
from PIL import Image, ImageDraw, ImageFont

RAW = Path(__file__).resolve().parents[2] / "data" / "raw" / "clinical"
FONT_REGULAR = "/System/Library/Fonts/Helvetica.ttc"
FONT_BOLD = "/System/Library/Fonts/HelveticaNeue.ttc"

# Quantas variacoes gerar por template
N_VARIATIONS = 3

# Seed para reprodutibilidade
random.seed(42)

# ----------------------------------------------------------------------
# Pools de variacao
# ----------------------------------------------------------------------

PRIMEIROS_NOMES = [
    "Ana", "Beatriz", "Camila", "Daniela", "Eduarda", "Fernanda",
    "Gabriela", "Helena", "Isabela", "Juliana", "Karina", "Larissa",
    "Mariana", "Natalia", "Olivia", "Patricia", "Renata", "Sabrina",
    "Tatiana", "Vanessa", "Andre", "Bruno", "Carlos", "Daniel",
    "Eduardo", "Felipe", "Gustavo", "Henrique", "Igor", "Joao",
    "Lucas", "Marcos", "Nicolas", "Otavio", "Pedro", "Rafael",
    "Sergio", "Thiago", "Vitor", "Wagner", "Caio", "Diego",
    "Fabio", "Leonardo", "Matheus", "Paulo", "Ricardo", "Rodrigo",
    "Antonio", "Bernardo",
]
SOBRENOMES = [
    "Silva", "Santos", "Oliveira", "Souza", "Pereira", "Lima",
    "Costa", "Almeida", "Ferreira", "Rodrigues", "Carvalho", "Gomes",
    "Martins", "Araujo", "Ribeiro", "Nascimento", "Barbosa", "Cardoso",
    "Cavalcanti", "Mendes", "Moreira", "Nunes", "Pinto", "Ramos",
    "Rocha", "Vieira", "Andrade", "Cunha", "Dias", "Freitas",
    "Lopes", "Machado", "Marques", "Melo", "Monteiro", "Moura",
    "Nogueira", "Pacheco", "Queiroz", "Reis", "Sales", "Tavares",
    "Teixeira", "Torres", "Vasconcelos", "Xavier", "Bezerra", "Coelho",
]

ESTADOS = ["AC", "AL", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MG",
           "MS", "MT", "PA", "PB", "PE", "PI", "PR", "RJ", "RN", "RO",
           "RR", "RS", "SC", "SE", "SP", "TO", "AP"]

ESPECIALIDADES_E_CONTEUDO = {
    "clinica_geral": [
        ("sinusite aguda", "Amoxicilina 500mg - 1 cap de 8/8h por 7 dias", "afastamento de 3 (tres) dias"),
        ("gastrite aguda", "Omeprazol 20mg - 1 cap em jejum por 30 dias", "afastamento de 2 (dois) dias"),
        ("infeccao urinaria", "Ciprofloxacino 500mg - 1 cp de 12/12h por 5 dias", "afastamento de 3 (tres) dias"),
        ("enxaqueca", "Sumatriptano 50mg - 1 cp ao iniciar crise", "afastamento de 1 (um) dia"),
        ("rinite alergica", "Loratadina 10mg - 1 cp ao dia", "sem necessidade de afastamento"),
    ],
    "cardiologia": [
        ("hipertensao arterial sistemica", "Losartana 50mg - 1 cp/dia", "acompanhamento ambulatorial"),
        ("dor precordial atipica", "ECG seriado + troponina", "encaminhamento para CER de cardiologia"),
        ("arritmia supraventricular", "Propranolol 40mg - 1 cp de 12/12h", "acompanhamento mensal"),
        ("insuficiencia cardiaca leve", "Enalapril 10mg + Furosemida 40mg", "acompanhamento cardiologico"),
    ],
    "endocrinologia": [
        ("diabetes mellitus tipo 2", "Metformina 850mg - 1 cp de 12/12h", "acompanhamento trimestral"),
        ("hipotireoidismo", "Levotiroxina 50mcg - 1 cp em jejum", "TSH em 60 dias"),
        ("obesidade", "Orientacoes nutricionais + atividade fisica", "reavaliacao em 90 dias"),
    ],
    "neurologia": [
        ("cefaleia tensional", "Amitriptilina 25mg - 1 cp a noite", "acompanhamento neurologico"),
        ("vertigem postural", "Betahistina 24mg - 1 cp de 12/12h por 14 dias", "afastamento de 5 (cinco) dias"),
    ],
    "medicina_trabalho": [
        ("avaliacao admissional", "Apto sem restricoes", "exame realizado"),
        ("retorno apos afastamento", "Apto a retornar as atividades habituais", "alta medica"),
    ],
    "pediatria": [
        ("amigdalite estreptococica", "Amoxicilina 250mg/5ml - 5ml de 8/8h por 10 dias", "afastamento escolar de 7 (sete) dias"),
        ("otite media aguda", "Cefuroxima suspensao - conforme peso por 7 dias", "afastamento de 3 (tres) dias"),
    ],
    "dermatologia": [
        ("dermatite atopica", "Hidratante 2x/dia + corticoide topico", "acompanhamento mensal"),
        ("acne grau II", "Adapaleno 0,1% gel a noite", "reavaliacao em 60 dias"),
    ],
    "ortopedia": [
        ("entorse de tornozelo grau I", "Repouso, elevacao, gelo + anti-inflamatorio", "afastamento de 7 (sete) dias"),
        ("lombalgia mecanica", "Cetorolaco 10mg de 8/8h por 5 dias", "afastamento de 3 (tres) dias"),
    ],
}


@dataclass
class Variation:
    """Dados sinteticos aleatorios usados para preencher um template."""

    paciente: str
    data: str
    crm: str
    medico: str
    especialidade: str
    diagnostico: str
    prescricao: str
    conduta: str
    cpf: str
    cns: str


def random_date() -> str:
    """Data aleatoria entre 2024-01-01 e 2026-05-19, formato DD/MM/AAAA."""
    ano = random.choice([2024, 2025, 2026])
    if ano == 2026:
        mes = random.randint(1, 5)
        if mes == 5:
            dia = random.randint(1, 19)
        else:
            dia = random.randint(1, 28)
    else:
        mes = random.randint(1, 12)
        dia = random.randint(1, 28)
    return f"{dia:02d}/{mes:02d}/{ano}"


def random_cpf() -> str:
    n = [random.randint(0, 9) for _ in range(11)]
    return f"{n[0]}{n[1]}{n[2]}.{n[3]}{n[4]}{n[5]}.{n[6]}{n[7]}{n[8]}-{n[9]}{n[10]}"


def random_cns() -> str:
    return f"7{random.randint(0, 9)}{random.randint(0, 9)} {random.randint(1000, 9999)} {random.randint(1000, 9999)} {random.randint(1000, 9999)}"


def random_variation() -> Variation:
    nome = f"{random.choice(PRIMEIROS_NOMES)} {random.choice(SOBRENOMES)} {random.choice(SOBRENOMES)}"
    med = f"Dr(a). {random.choice(PRIMEIROS_NOMES)} {random.choice(SOBRENOMES)}"
    estado = random.choice(ESTADOS)
    crm = f"CRM-{estado} {random.randint(1000, 99999)}"
    especialidade = random.choice(list(ESPECIALIDADES_E_CONTEUDO.keys()))
    diag, presc, cond = random.choice(ESPECIALIDADES_E_CONTEUDO[especialidade])
    return Variation(
        paciente=nome,
        data=random_date(),
        crm=crm,
        medico=med,
        especialidade=especialidade,
        diagnostico=diag,
        prescricao=presc,
        conduta=cond,
        cpf=random_cpf(),
        cns=random_cns(),
    )


def _font(size: int, bold: bool):
    try:
        return ImageFont.truetype(FONT_BOLD if bold else FONT_REGULAR, size)
    except Exception:
        return ImageFont.load_default()


def _render_with_overlays(input_pdf: Path, output_pdf: Path, overlays) -> None:
    images = convert_from_path(str(input_pdf), dpi=150, first_page=1, last_page=1)
    img = images[0].convert("RGB")
    draw = ImageDraw.Draw(img)
    W, H = img.size
    for x_rel, y_rel, text, size, bold in overlays:
        x, y = int(x_rel * W), int(y_rel * H)
        draw.text((x, y), text, fill="black", font=_font(size, bold))
    img.save(str(output_pdf), "PDF", resolution=150.0)


# ----------------------------------------------------------------------
# Builders de overlay por template
# ----------------------------------------------------------------------


def overlays_atestado(v: Variation) -> list:
    return [
        (0.12, 0.38, f"Paciente: {v.paciente}", 18, False),
        (0.12, 0.42, f"Data: {v.data}", 14, False),
        (0.12, 0.50, f"Atesto, para os devidos fins, que o(a) paciente acima esteve", 14, False),
        (0.12, 0.53, f"sob meus cuidados profissionais em {v.data}, com diagnostico", 14, False),
        (0.12, 0.56, f"de {v.diagnostico}. {v.conduta.capitalize()}.", 14, False),
        (0.12, 0.75, v.medico, 16, True),
        (0.12, 0.78, v.crm, 14, False),
    ]


def overlays_receituario(v: Variation) -> list:
    return [
        (0.12, 0.30, f"Paciente: {v.paciente}", 18, False),
        (0.12, 0.34, f"Data: {v.data}", 14, False),
        (0.12, 0.42, "Prescricao medica:", 16, True),
        (0.12, 0.48, f"Diagnostico: {v.diagnostico}", 14, False),
        (0.12, 0.55, f"1) {v.prescricao}", 14, False),
        (0.12, 0.62, f"Orientacoes: {v.conduta}", 14, False),
        (0.12, 0.78, v.medico, 16, True),
        (0.12, 0.81, v.crm, 14, False),
    ]


def overlays_lme(v: Variation) -> list:
    return [
        (0.10, 0.22, f"Paciente: {v.paciente}", 14, True),
        (0.10, 0.25, f"CPF: {v.cpf}  Cartao SUS: {v.cns}", 12, False),
        (0.10, 0.32, f"Diagnostico: {v.diagnostico}", 12, False),
        (0.10, 0.36, f"Medicamento solicitado: {v.prescricao}", 12, False),
        (0.10, 0.40, "Periodo: 6 meses, com reavaliacao trimestral", 12, False),
        (0.10, 0.55, f"Justificativa: paciente em acompanhamento ambulatorial para", 12, False),
        (0.10, 0.58, f"controle de {v.diagnostico}. Manutencao do tratamento atual.", 12, False),
        (0.10, 0.80, v.medico, 14, True),
        (0.10, 0.83, f"{v.crm} - Especialidade: {v.especialidade}", 12, False),
        (0.10, 0.87, f"Data: {v.data}", 12, False),
    ]


def overlays_encaminhamento(v: Variation) -> list:
    return [
        (0.10, 0.18, f"Paciente: {v.paciente}", 14, True),
        (0.10, 0.21, f"Cartao SUS: {v.cns}", 12, False),
        (0.10, 0.30, "Unidade de origem: UBS APS", 12, False),
        (0.10, 0.34, f"Especialidade solicitada: {v.especialidade}", 14, True),
        (0.10, 0.40, "Motivo do encaminhamento:", 13, True),
        (0.10, 0.44, f"Paciente em acompanhamento por {v.diagnostico}.", 12, False),
        (0.10, 0.47, "Solicito avaliacao especializada para conduta complementar.", 12, False),
        (0.10, 0.50, f"Sob terapia atual: {v.prescricao}.", 12, False),
        (0.10, 0.80, v.medico, 14, True),
        (0.10, 0.83, f"{v.crm} - Medico(a) da Familia", 12, False),
        (0.10, 0.87, f"Data: {v.data}", 12, False),
    ]


def overlays_laudo_pericial(v: Variation) -> list:
    return [
        (0.10, 0.25, f"Periciado: {v.paciente}", 14, True),
        (0.10, 0.29, f"CPF: {v.cpf}", 12, False),
        (0.10, 0.40, "Conclusao da pericia medica:", 13, True),
        (0.10, 0.46, f"Periciado(a) apresenta historico clinico compativel com", 12, False),
        (0.10, 0.49, f"{v.diagnostico}, em acompanhamento medico regular.", 12, False),
        (0.10, 0.52, f"Sob terapia: {v.prescricao}.", 12, False),
        (0.10, 0.55, f"Parecer: {v.conduta.capitalize()}.", 12, False),
        (0.10, 0.80, v.medico, 14, True),
        (0.10, 0.83, f"{v.crm} - {v.especialidade}", 12, False),
        (0.10, 0.87, f"Data: {v.data}", 12, False),
    ]


TEMPLATES = [
    ("cfm_atestado_template.pdf", "cfm_atestado_v{n}.pdf", overlays_atestado),
    ("cfm_receituario_template.pdf", "cfm_receituario_v{n}.pdf", overlays_receituario),
    ("lme_federal_template.pdf", "lme_federal_v{n}.pdf", overlays_lme),
    ("encaminhamento_se_template.pdf", "encaminhamento_se_v{n}.pdf", overlays_encaminhamento),
    ("goiania_laudo_pericial_template.pdf", "goiania_laudo_pericial_v{n}.pdf", overlays_laudo_pericial),
]


def main() -> None:
    # Remove os PREENCHIDOs antigos (sera substituidos pelas variacoes _v1, _v2, _v3)
    for old in [
        "cfm_atestado_PREENCHIDO.pdf",
        "cfm_receituario_PREENCHIDO.pdf",
        "lme_federal_PREENCHIDO.pdf",
        "encaminhamento_se_PREENCHIDO.pdf",
        "goiania_laudo_pericial_PREENCHIDO.pdf",
        "cfm_atestado_PREENCHIDO_foto.jpg",
    ]:
        p = RAW / old
        if p.exists():
            p.unlink()
            print(f"removido: {old}")

    variations_by_doc: dict[str, list[str]] = {}
    for template_name, output_pattern, overlays_fn in TEMPLATES:
        template_path = RAW / template_name
        if not template_path.exists():
            print(f"SKIP {template_name} — template fonte ausente")
            continue
        gerados = []
        for i in range(1, N_VARIATIONS + 1):
            v = random_variation()
            output_path = RAW / output_pattern.format(n=i)
            _render_with_overlays(template_path, output_path, overlays_fn(v))
            gerados.append(output_path.name)
            print(f"OK: {output_path.name} (paciente={v.paciente}, especialidade={v.especialidade}, data={v.data})")
        variations_by_doc[template_name] = gerados

    print()
    print(f"Total: {sum(len(v) for v in variations_by_doc.values())} documentos gerados")
    print(f"({N_VARIATIONS} variacoes x {len(variations_by_doc)} templates)")


if __name__ == "__main__":
    main()
