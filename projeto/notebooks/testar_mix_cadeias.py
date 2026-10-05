"""Extrai o mix por cadeia e testa sua agregacao contra a baseline nacional.

O alvo e sempre o agregado das mesmas cinco cadeias do Modelo 2. As edicoes
de 2018-2020 estao transcritas da coluna de cada cadeia dos PDFs oficiais,
com URLs abaixo. Os PDFs de 2021-2025 ja estao no repositorio; suas tabelas
sao extraidas por pdfplumber e confrontadas com os totais nacionais do CSV.
O backtest e por ano de referencia, nao por data de publicacao do boletim.
"""

from pathlib import Path
import pdfplumber
import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
PUROS = RAIZ / "documentos" / "puros" / "sindiracoes"
TRATADOS = RAIZ / "documentos" / "tratados"
CATEGORIAS = ["frangos", "ovos", "suinos", "leite", "bovinos"]
ITENS = ["milho", "farelo_soja_46pb", "sorgo", "coprodutos_gordura_vegetal_ddgs"]
ITENS_E_TOTAL = ITENS + ["total"]

# Valores: milho, farelo de soja, sorgo, coprodutos, total de racao.
# PDFs oficiais, tabela de macroingredientes (coluna de cada cadeia):
# 2018: https://sindiracoes.org.br/wp-content/uploads/2019/07/boletim_informativo_do_setor_julho_2019_vs_final_port_sindiracoes.pdf
# 2019: https://sindiracoes.org.br/wp-content/uploads/2020/06/boletim_informativo_do_setor_junho_2020_vs_final_port_sindiracoes_c.pdf
# 2020: https://sindiracoes.org.br/wp-content/uploads/2021/03/boletim_informativo_do_setor_marco_2021_vs_final_port_sindiracoes.pdf
ANTIGOS = {
    2018: {
        "frangos": (20319809, 7755475, 994685, 0, 31655000),
        "ovos": (4304194, 1328730, 112210, 0, 6814000),
        "suinos": (11158752, 3690720, 435848, 0, 16776000),
        "leite": (3601966, 1265367, 0, 359820, 5997000),
        "bovinos": (778146, 651328, 387610, 155820, 2597000),
    },
    2019: {
        "frangos": (21118993, 8260500, 1033806, 0, 32857000),
        "ovos": (4302931, 1328340, 112177, 0, 6812000),
        "suinos": (11754810, 3982240, 459646, 0, 17692000),
        "leite": (3741312, 1314319, 0, 373740, 6229000),
        "bovinos": (1950204, 1296812, 370849, 310242, 5170700),
    },
    2020: {
        "frangos": (21986069, 8599649, 1076251, 0, 34206000),
        "ovos": (4516435, 1394250, 117743, 0, 7150000),
        "suinos": (12457759, 4220382, 487133, 0, 18750000),
        "leite": (3859035, 1355675, 0, 385500, 6425000),
        "bovinos": (2066861, 1374384, 393032, 328800, 5480000),
    },
}

ARQUIVOS = {
    2021: "boletim_maio22_sindiracoes.pdf",
    2022: "boletim_jun23_sindiracoes.pdf",
    2023: "boletim_maio24_sindiracoes.pdf",
    2024: "boletim_maio25_sindiracoes.pdf",
    2025: "boletim_mar26_sindiracoes.pdf",
}
FONTES = {ano: nome.removesuffix("_sindiracoes.pdf") for ano, nome in ARQUIVOS.items()}
FONTES_ANTIGAS = {2018: "boletim_jul19", 2019: "boletim_jun20",
                  2020: "boletim_mar21"}


def numero(valor):
    if valor is None or not str(valor).strip():
        raise ValueError("Celula de tabela ausente")
    return int(str(valor).replace(".", "").strip())


def extrair_pdfs(tidy):
    linhas = []
    for ano, nome in ARQUIVOS.items():
        with pdfplumber.open(PUROS / nome) as pdf:
            paginas = [(i, p) for i, p in enumerate(pdf.pages)
                       if "MACROINGREDIENTES" in (p.extract_text() or "")]
            if len(paginas) != 1:
                raise ValueError(f"{nome}: esperado uma pagina de macroingredientes")
            pagina, page = paginas[0]
            tabelas = page.extract_tables()
            if len(tabelas) != 1:
                raise ValueError(f"{nome}: esperado uma tabela")
            tabela = tabelas[0]
            # Nos boletins de 2023 em diante, pdfplumber incorpora o nome
            # da primeira cadeia na coluna 0; nas edicoes anteriores, na 1.
            primeira = 0 if tabela[0][0] else 1
            colunas = [primeira, 3, 5, 7, 9]
            fonte = FONTES[ano]
            for item in ITENS_E_TOTAL:
                esperado = tidy[(tidy.ano == ano) & (tidy.tipo == "composicao_racao")
                                & (tidy.item == item) & (tidy.fonte == fonte)
                                & (tidy.status == "estimativa")].valor
                if len(esperado) != 1:
                    raise ValueError(f"Falta total nacional: {ano}, {item}")
                candidatos = [r for r in tabela[2:] if r[-6] and
                              str(r[-6]).replace(".", "").isdigit() and
                              numero(r[-6]) == int(esperado.iloc[0])]
                if len(candidatos) != 1:
                    raise ValueError(f"Linha ambigua: {ano}, {item}")
                linha = candidatos[0]
                for categoria, coluna in zip(CATEGORIAS, colunas):
                    linhas.append((ano, categoria, item, numero(linha[coluna]),
                                   fonte, pagina + 1, "estimativa"))
    return linhas


def carregar_historico():
    tidy = pd.read_csv(TRATADOS / "sindiracoes_tidy.csv")
    linhas = []
    for ano, por_categoria in ANTIGOS.items():
        for categoria, valores in por_categoria.items():
            for item, valor in zip(ITENS_E_TOTAL, valores):
                linhas.append((ano, categoria, item, valor,
                               FONTES_ANTIGAS[ano],
                               4 if ano != 2020 else 5, "estimativa"))
    linhas.extend(extrair_pdfs(tidy))
    d = pd.DataFrame(linhas, columns=["ano", "categoria", "item", "valor_toneladas",
                                      "fonte", "pdf_pagina", "status"])
    if d.duplicated(["ano", "categoria", "item"]).any() or len(d) != 8 * 5 * 5:
        raise ValueError("Serie por cadeia incompleta ou duplicada")
    wide = d.pivot(index=["ano", "categoria"], columns="item", values="valor_toneladas")
    if (wide[ITENS].sum(axis=1) > wide["total"]).any() or (wide < 0).any().any():
        raise ValueError("Valores de composicao inconsistentes")
    for ano in range(2018, 2026):
        nacional = tidy[(tidy.ano == ano) & (tidy.tipo == "composicao_racao")
                        & (tidy.status == "estimativa")].set_index("item")
        for item in ITENS_E_TOTAL:
            if wide.loc[ano, item].sum() > nacional.loc[item, "valor"]:
                raise ValueError(f"Cinco cadeias excedem total nacional: {ano}, {item}")
    d.to_csv(TRATADOS / "modelo3_mix_cadeias_historico.csv", index=False)
    return wide


def comparar_ano(wide, ano, pesos, origem):
    anterior = wide.loc[ano - 1].loc[CATEGORIAS]
    atual = wide.loc[ano].loc[CATEGORIAS]
    pesos = pesos.reindex(CATEGORIAS)
    if pesos.isna().any() or (pesos <= 0).any():
        raise ValueError(f"Pesos incompletos para {ano}")
    saida = []
    for item in ITENS:
        mix_anterior = anterior[item] / anterior["total"]
        baseline = anterior[item].sum() / anterior["total"].sum()
        ponderada = float((pesos * mix_anterior).sum() / pesos.sum())
        real = atual[item].sum() / atual["total"].sum()
        real_t = atual[item].sum()
        for metodo, previsto in [("ultima_participacao_5_cadeias", baseline),
                                 ("mix_por_cadeia", ponderada)]:
            volume_previsto = previsto * pesos.sum()
            saida.append({
                "ano": ano, "origem_pesos": origem, "item": item, "metodo": metodo,
                "participacao_real": real, "participacao_prevista": previsto,
                "erro_participacao_pp": abs(previsto - real) * 100,
                "mape_participacao_pct": abs(previsto - real) / real * 100,
                "toneladas_referencia": real_t, "toneladas_previstas": volume_previsto,
                "mape_volume_pct": abs(volume_previsto - real_t) / real_t * 100,
                "racao_prevista_5_cadeias": pesos.sum(),
                "racao_referencia_5_cadeias": atual["total"].sum(),
            })
    return saida


def backtest(wide):
    linhas = []
    for ano in range(2019, 2026):
        linhas.extend(comparar_ano(wide, ano, wide.loc[ano, "total"],
                                    "racao_do_ano_diagnostico"))
    m2 = pd.read_csv(TRATADOS / "modelo2_backtest_categorias.csv")
    for ano in (2024, 2025):
        pesos = m2[m2.ano == ano].set_index("categoria")["racao_prevista_toneladas"]
        linhas.extend(comparar_ano(wide, ano, pesos, "modelo2_backtest"))
    detalhe = pd.DataFrame(linhas)
    detalhe.to_csv(TRATADOS / "modelo3_mix_cadeias_backtest.csv", index=False)
    resumos = []
    for origem, dados in detalhe.groupby("origem_pesos"):
        for periodo, recorte in [("todos_os_anos", dados)] + [
                (str(ano), d) for ano, d in dados.groupby("ano")]:
            for grupo, itens in [("tres_comparaveis", ITENS[:3]),
                                 ("quatro_grupos", ITENS)]:
                for metodo, d in recorte[recorte.item.isin(itens)].groupby("metodo"):
                    resumos.append({
                        "origem_pesos": origem, "periodo": periodo,
                        "grupo": grupo, "metodo": metodo,
                        "n_comparacoes": len(d),
                        "mape_participacao_pct": d.mape_participacao_pct.mean(),
                        "mape_volume_pct": d.mape_volume_pct.mean(),
                    })
    pd.DataFrame(resumos).to_csv(TRATADOS / "modelo3_mix_cadeias_resumo.csv",
                                 index=False)
    return detalhe


def prever(wide):
    m2 = pd.read_csv(TRATADOS / "modelo2_previsao_mensal.csv")
    base = wide.loc[2025].loc[CATEGORIAS]
    shares = base[ITENS].div(base["total"], axis=0)
    linhas = []
    for linha in m2.itertuples(index=False):
        if linha.categoria not in CATEGORIAS or linha.ano not in (2026, 2027):
            continue
        for item in ITENS:
            linhas.append({"data": linha.data, "ano": linha.ano,
                           "categoria": linha.categoria, "item": item,
                           "racao_modelo2_toneladas": linha.racao_toneladas,
                           "participacao_2025_na_cadeia": shares.loc[linha.categoria, item],
                           "ingrediente_previsto_toneladas":
                               linha.racao_toneladas * shares.loc[linha.categoria, item]})
    mensal = pd.DataFrame(linhas)
    if len(mensal) != 24 * 5 * 4:
        raise ValueError("Previsao mensal por cadeia incompleta")
    mensal.to_csv(TRATADOS / "modelo3_mix_cadeias_previsao_mensal.csv", index=False)
    anual = (mensal.groupby(["ano", "item"])
             .agg(ingrediente_previsto_toneladas=("ingrediente_previsto_toneladas", "sum"),
                  racao_5_cadeias_toneladas=("racao_modelo2_toneladas", "sum"))
             .reset_index())
    # Racao foi repetida uma vez por ingrediente, mas nao por categoria.
    anual["participacao_prevista"] = (anual["ingrediente_previsto_toneladas"] /
                                       anual["racao_5_cadeias_toneladas"])
    anual.to_csv(TRATADOS / "modelo3_mix_cadeias_previsao_anual.csv", index=False)
    return anual


def main():
    wide = carregar_historico()
    detalhe = backtest(wide)
    anual = prever(wide)
    amostra = detalhe[(detalhe.origem_pesos == "modelo2_backtest") &
                      (detalhe.item != "coprodutos_gordura_vegetal_ddgs")]
    print("MAPE 2024-2025, tres ingredientes, pesos previstos pelo Modelo 2:")
    print(amostra.groupby("metodo")[["mape_participacao_pct", "mape_volume_pct"]]
          .mean().round(3).to_string())
    print("\nPrevisao experimental para as cinco cadeias:")
    print(anual.round(3).to_string(index=False))


if __name__ == "__main__":
    main()
