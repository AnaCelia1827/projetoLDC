"""
Converte um CSV exportado da CEPEA (Consulta ao Banco de Dados) para o formato
tidy usado no projeto: data (AAAA-MM), variavel, valor, unidade.

Pré-requisito: o .xls baixado da CEPEA precisa ser salvo como CSV primeiro
(Excel ou LibreOffice Calc: Arquivo > Salvar como > CSV UTF-8), porque é um
formato antigo de planilha que não tem uma biblioteca Python leve para leitura
direta neste ambiente.

Uso:
    python cepea_para_tidy.py cepea_soja.csv preco_soja_parana producao_tidy_precos.csv
                                ^entrada        ^nome da variável   ^saída (cria ou anexa)
"""
import csv
import re
import sys


def detectar_separador(caminho_entrada):
    with open(caminho_entrada, encoding="utf-8-sig") as f:
        amostra = f.read(4096)
    # Excel em pt-BR normalmente exporta CSV com ";" (porque "," já é o decimal)
    return ";" if amostra.count(";") > amostra.count(",") else ","


def parse_cepea_csv(caminho_entrada, nome_variavel, unidade="R$/saca de 60 kg", coluna_valor=1):
    separador = detectar_separador(caminho_entrada)
    with open(caminho_entrada, encoding="utf-8-sig") as f:
        linhas = list(csv.reader(f, delimiter=separador))

    idx_cabecalho = next(
        (i for i, l in enumerate(linhas) if l and l[0].strip().lower() == "data"), None
    )
    if idx_cabecalho is None:
        raise ValueError(
            f"Não encontrei uma linha começando com 'Data' em {caminho_entrada} "
            f"(separador detectado: '{separador}'). Confira se o arquivo é mesmo "
            f"a exportação da CEPEA e não foi editado."
        )
    registros = []
    for linha in linhas[idx_cabecalho + 1:]:
        if not linha or not linha[0]:
            continue
        m = re.match(r"(\d{2})/(\d{4})", linha[0].strip())
        if not m:
            continue
        mes, ano = m.groups()
        if coluna_valor >= len(linha) or linha[coluna_valor].strip() == "":
            continue
        valor_str = linha[coluna_valor].strip().replace(".", "").replace(",", ".")
        registros.append(
            {
                "data": f"{ano}-{mes}",
                "variavel": nome_variavel,
                "valor": float(valor_str),
                "unidade": unidade,
            }
        )
    return registros


def salvar_tidy(registros, caminho_saida, anexar=False):
    modo = "a" if anexar else "w"
    escrever_cabecalho = not anexar
    with open(caminho_saida, modo, encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["data", "variavel", "valor", "unidade"])
        if escrever_cabecalho:
            w.writeheader()
        w.writerows(registros)


ARQUIVOS_PADRAO = {
    "cepea_soja.csv": "preco_soja_parana",
    "cepea_milho.csv": "preco_milho",
}
FATOR_SORGO = 0.85  # regra de mercado: sorgo ~ 80-90% do preço do milho


def processar_pasta_precos():
    """Roda sem argumentos: procura cepea_soja.csv e cepea_milho.csv em
    ../documentos/puros/precos (relativo a este script, dentro de notebooks/),
    gera ../documentos/tratados/precos_tidy.csv e já deriva o sorgo do milho."""
    from pathlib import Path

    pasta_precos = Path(__file__).resolve().parent.parent / "documentos" / "puros" / "precos"
    pasta_tratados = Path(__file__).resolve().parent.parent / "documentos" / "tratados"
    caminho_saida = pasta_tratados / "precos_tidy.csv"

    todos_registros = []
    for arquivo, nome_variavel in ARQUIVOS_PADRAO.items():
        caminho_entrada = pasta_precos / arquivo
        if not caminho_entrada.exists():
            print(f"[pulado] {arquivo} não encontrado em {pasta_precos}")
            continue
        registros = parse_cepea_csv(str(caminho_entrada), nome_variavel)
        print(f"{nome_variavel}: {len(registros)} linhas")
        todos_registros.extend(registros)

    milho = [r for r in todos_registros if r["variavel"] == "preco_milho"]
    if milho:
        for r in milho:
            todos_registros.append(
                {**r, "variavel": "preco_sorgo_estimado", "valor": round(r["valor"] * FATOR_SORGO, 2)}
            )
        print(f"preco_sorgo_estimado: {len(milho)} linhas (derivado do milho x {FATOR_SORGO})")
    else:
        print("[aviso] milho não processado, sorgo não pôde ser derivado")

    salvar_tidy(todos_registros, str(caminho_saida), anexar=False)
    print(f"\nTotal: {len(todos_registros)} linhas escritas em {caminho_saida}")


if __name__ == "__main__":
    if len(sys.argv) >= 4:
        entrada, nome_variavel, saida = sys.argv[1], sys.argv[2], sys.argv[3]
        import os

        anexar = os.path.exists(saida)
        registros = parse_cepea_csv(entrada, nome_variavel)
        salvar_tidy(registros, saida, anexar=anexar)
        print(f"{len(registros)} linhas escritas em {saida} (variavel='{nome_variavel}')")
    else:
        processar_pasta_precos()