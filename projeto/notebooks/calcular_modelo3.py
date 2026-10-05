"""Modelo 3: projeta a participacao de macroingredientes na racao.

Treina com estimativas Sindiracoes de 2018 a 2025 e avalia os alvos de
2021 a 2025 em ordem temporal. O quarto grupo mudou de definicao;
a escolha do metodo usa milho, farelo de soja e sorgo. A previsao oficial
de 2026 serve apenas como benchmark externo. A aplicacao mensal assume
participacao constante dentro de cada ano.
"""
import pandas as pd
import numpy as np
from pathlib import Path

PASTA_TRATADOS = Path(__file__).resolve().parent.parent / "documentos" / "tratados"
ORDEM_BOLETINS = ["boletim_jul19", "boletim_jun20", "boletim_mar21", "boletim_maio22", "boletim_jun23", "boletim_maio24", "boletim_maio25", "boletim_mar26"]

ANOS_PROJETAR = [2026, 2027]
ANO_CORTE_TREINO = 2025  # estimativas historicas; 2025 foi publicado em mar/2026

ITENS_MACRO = ["milho", "farelo_soja_46pb", "sorgo", "coprodutos_gordura_vegetal_ddgs"]

# ---------------------------------------------------------------------------
# Parâmetros de Paridade para Cenários de Sensibilidade (Ponto 4)
# ---------------------------------------------------------------------------
PARIDADE_SORGO_MILHO = 0.85
PARIDADE_SOJA_MILHO = 2.00
SENSIBILIDADE_SORGO = 0.10
SENSIBILIDADE_DDGS = 0.05
MAX_AJUSTE_SORGO = 0.025
MAX_AJUSTE_DDGS = 0.015


def resolver_duplicatas(df, tipo):
    """Para cada (ano, item), prioriza 'estimativa' do boletim mais recente;
    sem estimativa, usa 'previsao' do boletim mais recente."""
    d = df[df["tipo"] == tipo].copy()
    d["ordem_boletim"] = d["fonte"].map({b: i for i, b in enumerate(ORDEM_BOLETINS)})
    d["prioridade"] = d["status"].map({"estimativa": 1, "previsao": 0})
    d = d.sort_values(["ano", "item", "prioridade", "ordem_boletim"], ascending=[True, True, False, False])
    return d.drop_duplicates(subset=["ano", "item"], keep="first")


def extrair_participacoes(sindiracoes):
    """Extrai a série de participações históricas de cada macroingrediente."""
    composicao = resolver_duplicatas(sindiracoes, "composicao_racao")
    totais = composicao[composicao["item"] == "total"].set_index("ano")["valor"]

    linhas = []
    for item in ITENS_MACRO:
        item_serie = composicao[composicao["item"] == item].set_index("ano")["valor"]
        status_serie = composicao[composicao["item"] == item].set_index("ano")["status"]
        anos_comuns = sorted(set(item_serie.index) & set(totais.index))
        for ano in anos_comuns:
            linhas.append({
                "ano": ano,
                "item": item,
                "valor": item_serie[ano],
                "total": totais[ano],
                "participacao": item_serie[ano] / totais[ano],
                "status": status_serie[ano],
            })
    return pd.DataFrame(linhas)


def validar_temporalmente(df_part, inicio_treino=2018, anos_teste=None):
    """Avalia janela crescente por ano dos dados, sem recorte por data de publicacao."""
    if anos_teste is None:
        anos_teste = [2021, 2022, 2023, 2024, 2025, 2026]
    metricas = []

    for ano_t in anos_teste:
        treino = df_part[(df_part["ano"] >= inicio_treino) & (df_part["ano"] < ano_t)
                         & (df_part["ano"] <= ANO_CORTE_TREINO)
                         & (df_part["status"] == "estimativa")]
        real = df_part[df_part["ano"] == ano_t].set_index("item")["participacao"]

        for item in ITENS_MACRO:
            tr_item = treino[treino["item"] == item].sort_values("ano")
            x_tr = tr_item["ano"].values
            y_tr = tr_item["participacao"].values
            if len(y_tr) < 3 or item not in real:
                raise ValueError(f"Treino ou referencia insuficiente: {item}, {ano_t}")

            # Modelo 1: Naive (manter última participação observada)
            pred_naive = y_tr[-1]

            # Modelo 2: Tendência Linear simples
            coef = np.polyfit(x_tr, y_tr, 1)
            pred_trend = float(np.polyval(coef, ano_t))

            val_real = real[item]
            mape_naive = abs(pred_naive - val_real) / val_real * 100
            mape_trend = abs(pred_trend - val_real) / val_real * 100

            metricas.append({
                "ano_teste": ano_t,
                "item": item,
                "real": val_real,
                "pred_naive": pred_naive,
                "mape_naive": mape_naive,
                "pred_trend": pred_trend,
                "mape_trend": mape_trend,
            })

    df_met = pd.DataFrame(metricas)
    return df_met


def garantir_limites(shares):
    """Ponto 5: Garante 0 <= s_i <= 1 e soma coerente (não ultrapassa 100%)."""
    s_ajust = {}
    for item, val in shares.items():
        s_ajust[item] = max(0.0, min(1.0, val))

    soma_atual = sum(s_ajust.values())
    soma_alvo = sum(shares.values())
    if soma_atual > 0:
        for item in s_ajust:
            s_ajust[item] = (s_ajust[item] / soma_atual) * soma_alvo
    return s_ajust


def aplicar_cenario_preco(shares_base, rel_sorgo, rel_soja):
    """Ponto 4: Aplica desvio de paridade para cenários de sensibilidade."""
    s = shares_base.copy()

    # 1. Substituição Sorgo <-> Milho
    d_sorgo = np.clip(SENSIBILIDADE_SORGO * (PARIDADE_SORGO_MILHO - rel_sorgo), -MAX_AJUSTE_SORGO, MAX_AJUSTE_SORGO)

    # 2. Substituição Soja/Milho <-> DDGS
    d_ddgs = np.clip(SENSIBILIDADE_DDGS * (rel_soja - PARIDADE_SOJA_MILHO), -MAX_AJUSTE_DDGS, MAX_AJUSTE_DDGS)

    s["sorgo"] += d_sorgo
    s["milho"] -= d_sorgo

    s["coprodutos_gordura_vegetal_ddgs"] += d_ddgs
    s["farelo_soja_46pb"] -= 0.45 * d_ddgs
    s["milho"] -= 0.55 * d_ddgs

    return garantir_limites(s), d_sorgo, d_ddgs


def main():
    sindiracoes = pd.read_csv(PASTA_TRATADOS / "sindiracoes_tidy.csv")
    df_part = extrair_participacoes(sindiracoes)

    # -----------------------------------------------------------------------
    # Ponto 2 e 3: Treino estrito até 2025 e Validação Temporal Walk-Forward
    # -----------------------------------------------------------------------
    df_metricas = validar_temporalmente(df_part)
    df_metricas.to_csv(PASTA_TRATADOS / "modelo3_metricas.csv", index=False)

    # Compara as duas janelas sob os mesmos alvos de 2024-2025.
    metricas_antigas = validar_temporalmente(df_part, inicio_treino=2021,
                                             anos_teste=[2024, 2025])
    comparacao = []
    for nome, dados in [("2021-2025", metricas_antigas),
                        ("2018-2025", df_metricas[df_metricas["ano_teste"].isin([2024, 2025])])]:
        for grupo, itens in [("quatro_grupos", ITENS_MACRO),
                             ("tres_comparaveis", ITENS_MACRO[:3])]:
            for metodo, coluna in [("ultima_participacao", "mape_naive"),
                                   ("tendencia_linear", "mape_trend")]:
                recorte = dados[dados["item"].isin(itens)]
                comparacao.append({"janela_treino": nome, "anos_teste": "2024-2025",
                                   "grupo": grupo, "metodo": metodo,
                                   "mape_medio_pct": recorte[coluna].mean()})
    pd.DataFrame(comparacao).to_csv(PASTA_TRATADOS / "modelo3_comparacao_janelas.csv", index=False)

    metricas_historicas = df_metricas[(df_metricas["ano_teste"] <= ANO_CORTE_TREINO)
                                    & (df_metricas["item"].isin(ITENS_MACRO[:3]))]
    mape_geral_naive = metricas_historicas["mape_naive"].mean()
    mape_geral_trend = metricas_historicas["mape_trend"].mean()

    print("======================================================================")
    print("1. VALIDAÇÃO TEMPORAL (Ponto 3 - Walk-Forward / Backtest):")
    print("======================================================================")
    print("Avaliacao em ordem temporal por ano dos dados:")
    print(df_metricas[["ano_teste", "item", "real", "pred_naive", "mape_naive", "pred_trend", "mape_trend"]].round(4).to_string(index=False))
    print("\nComparacao das janelas nos mesmos anos de teste (2024-2025):")
    print(pd.DataFrame(comparacao).round(3).to_string(index=False))
    print(f"\n--> MAPE medio historico (2021-2025, tres grupos comparaveis): ultima = {mape_geral_naive:.2f}% | tendencia = {mape_geral_trend:.2f}%")

    # Escolha do modelo campeão baseada no menor MAPE geral (mesma lógica do Modelo 1)
    # O quarto grupo mudou de definicao; nao determina o metodo principal.
    modelo_campeao = "naive" if mape_geral_naive <= mape_geral_trend else "trend"
    print(f"--> Modelo Campeão Selecionado: '{modelo_campeao.upper()}' (menor erro nas projeções)")

    # -----------------------------------------------------------------------
    # Ponto 2: Projeção de 2026 e 2027 treinada até 2025
    # -----------------------------------------------------------------------
    treino_historico = df_part[df_part["ano"] <= ANO_CORTE_TREINO]
    ultimas_participacoes_2025 = treino_historico[treino_historico["ano"] == ANO_CORTE_TREINO].set_index("item")["participacao"].to_dict()

    coeficientes_trend = {}
    for item, grupo in treino_historico.groupby("item"):
        coeficientes_trend[item] = np.polyfit(grupo["ano"], grupo["participacao"], 1)

    shares_projetados = {}
    for ano in ANOS_PROJETAR:
        if modelo_campeao == "naive":
            # Naive: mantém a última participação real observada (2025)
            s_proj = ultimas_participacoes_2025.copy()
        else:
            s_proj = {item: float(np.polyval(coeficientes_trend[item], ano)) for item in ITENS_MACRO}
        shares_projetados[ano] = garantir_limites(s_proj)

    # Comparação Out-of-Sample para 2026 contra Benchmark Oficial Sindirações
    bench_2026 = df_part[df_part["ano"] == 2026].set_index("item")["participacao"].to_dict()
    print("\n======================================================================")
    print("2. COMPARACAO COM PREVISAO OFICIAL DE 2026 (NAO REALIZADO):")
    print("======================================================================")
    comparativo_2026 = []
    for item in ITENS_MACRO:
        previsto = shares_projetados[2026][item]
        oficial = bench_2026.get(item, np.nan)
        erro_pct = abs(previsto - oficial) / oficial * 100 if not np.isnan(oficial) else np.nan
        comparativo_2026.append({
            "item": item,
            "nosso_modelo_previsto": previsto,
            "sindiracoes_oficial_2026": oficial,
            "erro_percentual": erro_pct
        })
    print(pd.DataFrame(comparativo_2026).round(4).to_string(index=False))

    # -----------------------------------------------------------------------
    # Ponto 4: Cenários de Sensibilidade por Preço Relativo
    # -----------------------------------------------------------------------
    cenarios_config = {
        "Base (Preços Estáveis)": {"rel_sorgo": 0.85, "rel_soja": 1.93},
        "Cenário 1: Milho Caro / Sorgo Competitivo": {"rel_sorgo": 0.78, "rel_soja": 1.93},
        "Cenário 2: Soja Cara / Estímulo a DDGS": {"rel_sorgo": 0.85, "rel_soja": 2.20},
    }

    # Carrega dados do Modelo 2
    caminho_m2_mensal = PASTA_TRATADOS / "modelo2_previsao_mensal.csv"
    caminho_m2_anual = PASTA_TRATADOS / "modelo2_previsao_anual.csv"
    if not caminho_m2_mensal.exists() or not caminho_m2_anual.exists():
        raise FileNotFoundError("Execute calcular_modelo2.py antes do calcular_modelo3.py.")

    m2_mensal = pd.read_csv(caminho_m2_mensal)
    racao_mensal = m2_mensal.groupby(["data", "ano"])["racao_toneladas"].sum().reset_index()
    for ano in ANOS_PROJETAR:
        meses = set(racao_mensal.loc[racao_mensal["ano"] == ano, "data"])
        esperados = set(pd.period_range(f"{ano}-01", f"{ano}-12", freq="M").astype(str))
        if meses != esperados:
            raise ValueError(f"Modelo 2 precisa conter os 12 meses de {ano}")
    if set(racao_mensal["ano"]) != set(ANOS_PROJETAR):
        raise ValueError("Modelo 2 deve conter somente 2026 e 2027")

    # -----------------------------------------------------------------------
    # Ponto 1 e 5: Saída Mensal sob Premissa de Mix Constante ao Longo do Ano
    # -----------------------------------------------------------------------
    linhas_mensais = []
    for _, row in racao_mensal.iterrows():
        data_str = row["data"]
        ano = int(row["ano"])
        racao_t = row["racao_toneladas"]

        # Mix anual projetado aplicado uniformemente aos meses desse ano
        s_ano = shares_projetados[ano]

        linha = {
            "data": data_str,
            "ano": ano,
            "racao_toneladas": round(racao_t, 1),
        }
        for item in ITENS_MACRO:
            linha[f"{item}_toneladas"] = round(racao_t * s_ano[item], 1)
        linha["total_macroingredientes_toneladas"] = round(
            sum(linha[f"{item}_toneladas"] for item in ITENS_MACRO), 1
        )
        linhas_mensais.append(linha)

    df_mensal = pd.DataFrame(linhas_mensais)
    df_mensal.to_csv(PASTA_TRATADOS / "modelo3_previsao_mensal.csv", index=False)

    # -----------------------------------------------------------------------
    # Ponto 1: Saída anual para dois anos completos
    # -----------------------------------------------------------------------
    colunas_itens_ton = [f"{item}_toneladas" for item in ITENS_MACRO]
    anual_agregado = df_mensal.groupby("ano")[colunas_itens_ton + ["total_macroingredientes_toneladas", "racao_toneladas"]].sum().reset_index()
    anual_agregado.columns = [c.replace("_toneladas", "") for c in anual_agregado.columns]

    # Identificação clara do período e meses cobertos
    rotulos_periodo = {2026: "2026", 2027: "2027"}
    meses_cobertos = {2026: 12, 2027: 12}

    anual_agregado.insert(1, "periodo", anual_agregado["ano"].map(rotulos_periodo))
    anual_agregado.insert(2, "meses_cobertos", anual_agregado["ano"].map(meses_cobertos))
    anual_agregado["racao_anualizada_estimada"] = round(anual_agregado["racao"] * (12 / anual_agregado["meses_cobertos"]), 1)

    anual_agregado.to_csv(PASTA_TRATADOS / "modelo3_previsao_anual.csv", index=False)

    # -----------------------------------------------------------------------
    # Tabela de Cenários de Sensibilidade de Preço Relativo (Ponto 4)
    # -----------------------------------------------------------------------
    linhas_cenarios = []
    # Testando cenários para o ano de 2026 (ano com volume fechado)
    total_racao_2026 = anual_agregado.loc[anual_agregado["ano"] == 2026, "racao"].values[0]
    s_base_2026 = shares_projetados[2026]

    for nome_cenario, params in cenarios_config.items():
        s_cen, d_sorgo, d_ddgs = aplicar_cenario_preco(s_base_2026, params["rel_sorgo"], params["rel_soja"])
        linha_cen = {
            "cenario": nome_cenario,
            "rel_sorgo_milho": params["rel_sorgo"],
            "rel_soja_milho": params["rel_soja"],
            "delta_sorgo_pct": round(d_sorgo * 100, 3),
            "delta_ddgs_pct": round(d_ddgs * 100, 3),
        }
        for item in ITENS_MACRO:
            linha_cen[f"{item}_toneladas"] = round(total_racao_2026 * s_cen[item])
        linhas_cenarios.append(linha_cen)

    df_cenarios = pd.DataFrame(linhas_cenarios)
    df_cenarios.to_csv(PASTA_TRATADOS / "modelo3_cenarios.csv", index=False)

    # -----------------------------------------------------------------------
    # Exibições de Diagnóstico no Terminal
    # -----------------------------------------------------------------------
    print("\n======================================================================")
    print("3. PROJEÇÃO ANUAL CONSOLIDADA (2026 e 2027 completos):")
    print("======================================================================")
    cols_show = ["ano", "periodo", "meses_cobertos", "milho", "farelo_soja_46pb", "sorgo", "coprodutos_gordura_vegetal_ddgs", "total_macroingredientes", "racao", "racao_anualizada_estimada"]
    print(anual_agregado[cols_show].round(0).to_string(index=False))
    print("\n*Nota: ambos os anos incluem janeiro a dezembro (12 meses).")

    print("\n======================================================================")
    print("4. CENÁRIOS DE SENSIBILIDADE POR PREÇO RELATIVO (Ponto 4 - Ano 2026):")
    print("======================================================================")
    cols_cen = ["cenario", "rel_sorgo_milho", "rel_soja_milho", "milho_toneladas", "farelo_soja_46pb_toneladas", "sorgo_toneladas", "coprodutos_gordura_vegetal_ddgs_toneladas"]
    print(df_cenarios[cols_cen].round(0).to_string(index=False))

    print("\n======================================================================")
    print("5. AMOSTRA DA PROJEÇÃO MENSAL (Ponto 5 - Primeiros Meses de 2026):")
    print("======================================================================")
    cols_m = ["data", "racao_toneladas", "milho_toneladas", "farelo_soja_46pb_toneladas", "sorgo_toneladas", "coprodutos_gordura_vegetal_ddgs_toneladas"]
    print(df_mensal.head(6)[cols_m].round(0).to_string(index=False))

    print("\n======================================================================")
    print("6. ARQUIVOS ATUALIZADOS COM SUCESSO:")
    print("======================================================================")
    print(f"- {PASTA_TRATADOS / 'modelo3_metricas.csv'} (backtest temporal das abordagens)")
    print(f"- {PASTA_TRATADOS / 'modelo3_previsao_anual.csv'} (2026 e 2027 completos)")
    print(f"- {PASTA_TRATADOS / 'modelo3_previsao_mensal.csv'} (24 meses de 2026-01 a 2027-12)")
    print(f"- {PASTA_TRATADOS / 'modelo3_cenarios.csv'} (sensibilidade a preços relativos)")


if __name__ == "__main__":
    main()
