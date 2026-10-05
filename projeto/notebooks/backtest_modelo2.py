"""Backtest anual do pipeline produção -> FCR -> ração para 2024 e 2025.

Para cada ano-alvo, usa somente anos de referência anteriores no ajuste.
O candidato de produção é escolhido por validação no ano anterior ao alvo.
As datas de publicação dos boletins podem ser posteriores ao ano de referência;
portanto, este é um backtest por ano dos dados, não por data de disponibilidade.
"""

from pathlib import Path

import numpy as np
import pandas as pd

from prever_modelo1 import ALVO_POR_CATEGORIA, MODELOS, prever_categoria


TRATADOS = Path(__file__).resolve().parent.parent / "documentos" / "tratados"
BASES = TRATADOS / "bases_unificadas"
ANOS_TESTE = (2024, 2025)
CATEGORIAS_EM_KG = {"bovinos", "suinos", "frangos"}


def prever_ano(base, alvo, modelo, ano):
    """Prevê 12 meses recursivos a partir de dezembro do ano anterior."""
    corte = pd.Timestamp(ano - 1, 12, 1)
    treino = base.loc[base.index <= corte]
    if treino.empty or treino.index[-1] != corte:
        raise ValueError(f"Histórico precisa terminar em {corte:%Y-%m}")
    previsoes = prever_categoria(treino, alvo, modelo)[:12]
    datas = [p["data"] for p in previsoes]
    esperadas = list(pd.period_range(f"{ano}-01", f"{ano}-12", freq="M").astype(str))
    if datas != esperadas:
        raise ValueError(f"Previsão de {ano} não contém seus 12 meses completos")
    return np.array([p["valor_previsto"] for p in previsoes], dtype=float)


def escolher_modelo_sem_olhar_alvo(base, alvo, ano_alvo):
    """Valida os candidatos no ano anterior; nunca usa o ano-alvo na escolha."""
    ano_validacao = ano_alvo - 1
    reais = base.loc[f"{ano_validacao}-01-01":f"{ano_validacao}-12-01", alvo]
    if len(reais) != 12 or (reais <= 0).any():
        raise ValueError(f"Faltam observações válidas de {ano_validacao}")
    erros = {}
    for modelo in MODELOS:
        previsto = prever_ano(base, alvo, modelo, ano_validacao)
        erros[modelo] = float(np.mean(np.abs(previsto - reais.to_numpy()) / reais.to_numpy()) * 100)
    escolhido = min(erros, key=erros.get)
    return escolhido, ano_validacao, erros


def gerar_grafico_erros(detalhe):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    categorias = ["bovinos", "frangos", "leite", "ovos", "suinos"]
    rotulos = ["Bovinos", "Frangos", "Leite", "Ovos", "Suínos"]
    fig, axes = plt.subplots(1, 2, figsize=(11.5, 5), sharey=True, dpi=160)
    fig.patch.set_facecolor("white")
    y = np.arange(len(categorias))
    for ax, ano in zip(axes, ANOS_TESTE):
        d = detalhe[detalhe["ano"] == ano].set_index("categoria").loc[categorias]
        ax.barh(y - 0.18, d["erro_pipeline_pct"], height=0.34, color="#2563eb", label="Pipeline")
        ax.barh(y + 0.18, d["erro_baseline_pct"], height=0.34, color="#94a3b8", label="Baseline")
        ax.set_title(str(ano), fontsize=13, fontweight="bold")
        ax.set_xlabel("Erro percentual absoluto anual (%)")
        ax.set_yticks(y, rotulos)
        ax.invert_yaxis()
        ax.set_xlim(0, 18)
        ax.grid(axis="x", color="#e2e8f0")
        ax.set_axisbelow(True)
        ax.spines[["top", "right"]].set_visible(False)
    fig.suptitle("Backtest do Modelo 2 por cadeia: pipeline × baseline", fontsize=15, fontweight="bold")
    fig.legend(*axes[0].get_legend_handles_labels(), loc="lower center",
               bbox_to_anchor=(0.5, 0.10), ncol=2, frameon=False)
    fig.text(0.5, 0.025, "Referência: estimativa anual de ração nos boletins Sindirações.",
             ha="center", fontsize=9, color="#475569")
    fig.subplots_adjust(left=0.14, right=0.98, top=0.83, bottom=0.27, wspace=0.12)
    saida = TRATADOS / "graficos" / "modelo2_backtest_erros.png"
    saida.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(saida, dpi=160)
    plt.close(fig)
    return saida


def main():
    fcr = pd.read_csv(TRATADOS / "fcr_tidy.csv")
    linhas = []

    for ano in ANOS_TESTE:
        for categoria, alvo in ALVO_POR_CATEGORIA.items():
            base = pd.read_csv(BASES / f"base_{categoria}.csv", index_col=0, parse_dates=True)
            base = base.sort_index()
            modelo, ano_validacao, erros_validacao = escolher_modelo_sem_olhar_alvo(base, alvo, ano)
            producao_prevista = prever_ano(base, alvo, modelo, ano)
            if categoria in CATEGORIAS_EM_KG:
                producao_prevista = producao_prevista / 1000
            producao_prevista_anual = float(producao_prevista.sum())

            hist_fcr = fcr[(fcr["categoria"] == categoria) & (fcr["ano"] < ano)].sort_values("ano")
            if len(hist_fcr) < 3 or hist_fcr["ano"].iloc[-1] != ano - 1:
                raise ValueError(f"FCR histórico insuficiente para {categoria} em {ano}")
            coef = np.polyfit(hist_fcr["ano"], hist_fcr["fcr"], 1)
            fcr_tendencia = float(np.polyval(coef, ano))
            fcr_ultimo = float(hist_fcr["fcr"].iloc[-1])
            if fcr_tendencia <= 0:
                raise ValueError(f"FCR projetado não positivo: {categoria} {ano}")

            referencia = fcr[(fcr["categoria"] == categoria) & (fcr["ano"] == ano)]
            if len(referencia) != 1:
                raise ValueError(f"Falta ração de referência para {categoria} {ano}")
            real_racao = float(referencia["racao_toneladas"].iloc[0])
            real_producao = float(referencia["producao"].iloc[0])
            if categoria in CATEGORIAS_EM_KG:
                real_producao /= 1000

            previsto_pipeline = producao_prevista_anual * fcr_tendencia
            # Baseline implantável: repetir a demanda de ração do último ano.
            previsto_baseline = float(hist_fcr["racao_toneladas"].iloc[-1])
            # Diagnóstico de FCR: usa produção observada do ano-alvo. Não é forecast.
            fcr_tendencia_oraculo = real_producao * fcr_tendencia
            fcr_ultimo_oraculo = real_producao * fcr_ultimo

            linhas.append({
                "ano": ano,
                "categoria": categoria,
                "modelo_producao": modelo,
                "ano_validacao_modelo1": ano_validacao,
                "mape_validacao_linear_pct": erros_validacao["regressao_linear"],
                "mape_validacao_rf_pct": erros_validacao["random_forest"],
                "ultimo_ano_treino_producao": ano - 1,
                "primeiro_ano_treino_fcr": int(hist_fcr["ano"].iloc[0]),
                "ultimo_ano_treino_fcr": int(hist_fcr["ano"].iloc[-1]),
                "fcr_tendencia": fcr_tendencia,
                "fcr_ultimo": fcr_ultimo,
                "producao_prevista_unidade_fcr": producao_prevista_anual,
                "racao_prevista_toneladas": previsto_pipeline,
                "racao_baseline_toneladas": previsto_baseline,
                "racao_referencia_toneladas": real_racao,
                "erro_pipeline_pct": abs(previsto_pipeline / real_racao - 1) * 100,
                "erro_baseline_pct": abs(previsto_baseline / real_racao - 1) * 100,
                "erro_fcr_tendencia_isolado_pct": abs(fcr_tendencia_oraculo / real_racao - 1) * 100,
                "erro_fcr_ultimo_isolado_pct": abs(fcr_ultimo_oraculo / real_racao - 1) * 100,
            })

    detalhe = pd.DataFrame(linhas).sort_values(["ano", "categoria"])
    detalhe.to_csv(TRATADOS / "modelo2_backtest_categorias.csv", index=False)
    totais = detalhe.groupby("ano")[[
        "racao_prevista_toneladas", "racao_baseline_toneladas", "racao_referencia_toneladas"
    ]].sum().reset_index()
    totais["erro_pipeline_pct"] = abs(totais["racao_prevista_toneladas"] / totais["racao_referencia_toneladas"] - 1) * 100
    totais["erro_baseline_pct"] = abs(totais["racao_baseline_toneladas"] / totais["racao_referencia_toneladas"] - 1) * 100
    totais.to_csv(TRATADOS / "modelo2_backtest_totais.csv", index=False)

    resumo = pd.DataFrame([
        {"escopo": "10 comparacoes categoria-ano", "metrica": "MAPE", "pipeline": detalhe["erro_pipeline_pct"].mean(),
         "baseline": detalhe["erro_baseline_pct"].mean(), "unidade": "%"},
        {"escopo": "2 totais anuais de cinco categorias", "metrica": "MAPE", "pipeline": totais["erro_pipeline_pct"].mean(),
         "baseline": totais["erro_baseline_pct"].mean(), "unidade": "%"},
        {"escopo": "10 comparacoes categoria-ano", "metrica": "RMSE", "pipeline": np.sqrt(np.mean((detalhe["racao_prevista_toneladas"] - detalhe["racao_referencia_toneladas"]) ** 2)),
         "baseline": np.sqrt(np.mean((detalhe["racao_baseline_toneladas"] - detalhe["racao_referencia_toneladas"]) ** 2)),
         "unidade": "toneladas"},
        {"escopo": "2 totais anuais de cinco categorias", "metrica": "RMSE", "pipeline": np.sqrt(np.mean((totais["racao_prevista_toneladas"] - totais["racao_referencia_toneladas"]) ** 2)),
         "baseline": np.sqrt(np.mean((totais["racao_baseline_toneladas"] - totais["racao_referencia_toneladas"]) ** 2)),
         "unidade": "toneladas"},
    ])
    resumo.to_csv(TRATADOS / "modelo2_backtest_resumo.csv", index=False)
    grafico = gerar_grafico_erros(detalhe)

    print("\nBacktest por categoria (milhões de toneladas):")
    mostrar = detalhe[["ano", "categoria", "modelo_producao", "racao_referencia_toneladas",
                       "racao_prevista_toneladas", "racao_baseline_toneladas",
                       "erro_pipeline_pct", "erro_baseline_pct"]].copy()
    for coluna in ("racao_referencia_toneladas", "racao_prevista_toneladas", "racao_baseline_toneladas"):
        mostrar[coluna] /= 1_000_000
    print(mostrar.round(2).to_string(index=False))
    print("\nTotal das cinco categorias (milhões de toneladas):")
    mostrar_total = totais.copy()
    for coluna in ("racao_referencia_toneladas", "racao_prevista_toneladas", "racao_baseline_toneladas"):
        mostrar_total[coluna] /= 1_000_000
    print(mostrar_total.round(2).to_string(index=False))
    print(f"\nMAPE das 10 comparações categoria-ano: pipeline {detalhe['erro_pipeline_pct'].mean():.2f}% "
          f"| baseline {detalhe['erro_baseline_pct'].mean():.2f}%")
    print(f"MAPE dos dois totais anuais: pipeline {totais['erro_pipeline_pct'].mean():.2f}% "
          f"| baseline {totais['erro_baseline_pct'].mean():.2f}%")
    print(f"FCR isolado com produção observada, 10 comparações: tendência "
          f"{detalhe['erro_fcr_tendencia_isolado_pct'].mean():.2f}% | "
          f"último FCR {detalhe['erro_fcr_ultimo_isolado_pct'].mean():.2f}%")
    print("\nResumo completo:")
    print(resumo.to_string(index=False))
    print(f"Gráfico: {grafico}")


if __name__ == "__main__":
    main()
