"""
Converte um CSV exportado do SIDRA (formato "largo", um mês por par de colunas)
em uma tabela "tidy": uma linha por (data, território, tipo_inspecao, variavel).

Funciona para os CSVs de bovinos, suínos, frangos, ovos e leite baixados com a
opção "Exibir unidades de medida como coluna" marcada, mesma estrutura para todos.

Uso:
    python sidra_para_tidy.py producao_bovinos_mensal.csv producao_bovinos_tidy.csv
"""
import csv
import re
import sys
from datetime import date
from dateutil.relativedelta import relativedelta


def parse_sidra_wide(path_entrada):
    with open(path_entrada, "r", encoding="utf-8-sig", newline="") as f:
        linhas = list(csv.reader(f, delimiter=";"))

    registros = []
    variavel_atual = None
    data_inicial = None

    for linha in linhas:
        if not linha or not any(linha):
            continue

        primeira = linha[0].strip()

        # Início de um novo bloco de variável, ex.: "Variável - Peso total das carcaças"
        m = re.match(r"Vari[aá]vel\s*-\s*(.+)", primeira)
        if m:
            variavel_atual = m.group(1).strip()
            data_inicial = None
            continue

        # Linha de cabeçalho com o primeiro trimestre/ano, ex.: "1º trimestre 1997"
        if data_inicial is None:
            m = re.search(r"trimestre\s+(\d{4})", " ".join(linha))
            if m and "trimestre" in " ".join(linha).lower():
                ano = int(m.group(1))
                data_inicial = date(ano, 1, 1)


        # Linha de dados: primeira e segunda colunas são texto (território, tipo de
        # inspeção), a partir da terceira vêm pares (valor, unidade)
        if variavel_atual and data_inicial and primeira and not primeira.startswith(
            ("Fonte", "Nota", "Tabela")
        ):
            territorio = linha[0]
            tipo_inspecao = linha[1] if len(linha) > 1 else None
            pares = linha[2:]

            mes_idx = 0
            for i in range(0, len(pares) - 1, 2):
                valor, unidade = pares[i], pares[i + 1]
                if valor == "" or valor is None:
                    mes_idx += 1
                    continue
                competencia = data_inicial + relativedelta(months=mes_idx)
                registros.append(
                    {
                        "data": competencia.strftime("%Y-%m"),
                        "territorio": territorio,
                        "tipo_inspecao": tipo_inspecao,
                        "variavel": variavel_atual,
                        "valor": valor,
                        "unidade": unidade,
                    }
                )
                mes_idx += 1
            # depois de consumir a linha de dados, aguarda o próximo bloco de variável
            data_inicial = None

    return registros


def salvar_tidy(registros, path_saida):
    with open(path_saida, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(
            f, fieldnames=["data", "territorio", "tipo_inspecao", "variavel", "valor", "unidade"]
        )
        w.writeheader()
        w.writerows(registros)


ARQUIVOS_PADRAO = {
    "bovinos": "producao_bovinos_mensal.csv",
    "suinos": "producao_suinos_mensal.csv",
    "frangos": "producao_frangos_mensal.csv",
    "ovos": "producao_ovos_mensal.csv",
    "leite": "producao_leite_mensal.csv",
}


def processar_pasta_documentos():
    """Roda sem argumentos: procura os 5 CSVs em ../documentos (relativo a este
    script, dentro de notebooks/) e gera os *_tidy.csv na mesma pasta."""
    from pathlib import Path

    pasta_docs = Path(__file__).resolve().parent.parent / "documentos/puros/producao"
    for nome, arquivo in ARQUIVOS_PADRAO.items():
        caminho_entrada = pasta_docs / arquivo
        if not caminho_entrada.exists():
            print(f"[pulado] {arquivo} não encontrado em {pasta_docs}")
            continue
        registros = parse_sidra_wide(str(caminho_entrada))
        caminho_saida = pasta_docs / f"{nome}_tidy.csv"
        salvar_tidy(registros, str(caminho_saida))
        print(f"{nome}: {len(registros)} linhas -> {caminho_saida.name}")


if __name__ == "__main__":
    if len(sys.argv) >= 3:
        entrada, saida = sys.argv[1], sys.argv[2]
        registros = parse_sidra_wide(entrada)
        salvar_tidy(registros, saida)
        print(f"{len(registros)} linhas escritas em {saida}")
    else:
        processar_pasta_documentos()