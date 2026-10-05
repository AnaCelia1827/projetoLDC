"""
Modelo 1: produção mensal por categoria animal.

Para cada categoria: treino até dez/2023 e avaliação recursiva dos 24 meses
completos de jan/2024 a dez/2025. Preços futuros são mantidos no valor de
dez/2023, como na projeção final. Compara regressão linear, Random Forest
e baseline sazonal recursiva (repete os meses de 2023 em 2024 e 2025).

Roda de dentro de notebooks/, sem argumentos.
"""
import pandas as pd
import numpy as np
from pathlib import Path
from sklearn.metrics import mean_squared_error, mean_absolute_percentage_error

PASTA_TRATADOS = Path(__file__).resolve().parent.parent / "documentos" / "tratados"
PASTA_BASES = PASTA_TRATADOS / "bases_unificadas"
MESES_TESTE = 24  # dois anos civis completos: 2024 e 2025
FIM_TREINO = "2023-12-01"
INICIO_TESTE = "2024-01-01"
FIM_TESTE = "2025-12-01"

# categoria -> nome exato da coluna-alvo na base unificada
ALVO_POR_CATEGORIA = {
    "bovinos": "Peso total das carcaças",
    "suinos": "Peso total das carcaças",
    "frangos": "Peso total das carcaças",
    "ovos": "Quantidade de ovos produzidos",
    "leite": "Quantidade de leite cru, resfriado ou não, adquirido",
}

COLUNAS_PRECO = ["preco_milho", "preco_soja_parana", "preco_sorgo_estimado"]


def montar_features(df, alvo):
    """Recebe a base unificada (index=data, colunas=variáveis+preços) e devolve
    X, y com as features de sazonalidade, lags e médias móveis do alvo."""
    df = df.copy()
    df.index = pd.to_datetime(df.index)
    df = df.sort_index()

    df["mes_sin"] = np.sin(2 * np.pi * df.index.month / 12)
    df["mes_cos"] = np.cos(2 * np.pi * df.index.month / 12)

    for lag in [1, 2, 3, 12]:
        df[f"lag_{lag}"] = df[alvo].shift(lag)
    df["media_movel_3"] = df[alvo].shift(1).rolling(3).mean()
    df["media_movel_12"] = df[alvo].shift(1).rolling(12).mean()

    colunas_preco_presentes = [c for c in COLUNAS_PRECO if c in df.columns]
    features = ["mes_sin", "mes_cos", "lag_1", "lag_2", "lag_3", "lag_12",
                "media_movel_3", "media_movel_12"] + colunas_preco_presentes

    df_modelo = df[features + [alvo]].dropna()
    return df_modelo[features], df_modelo[alvo]


def treinar_e_avaliar(base, alvo, categoria):
    from prever_modelo1 import prever_categoria

    base_treino = base.loc[base.index <= FIM_TREINO]
    observado = base.loc[(base.index >= INICIO_TESTE) & (base.index <= FIM_TESTE), alvo]
    esperado = pd.date_range(INICIO_TESTE, FIM_TESTE, freq="MS")
    if len(observado) != MESES_TESTE or not observado.index.equals(esperado):
        raise ValueError(f"{categoria}: teste precisa conter todos os meses de 2024 e 2025")
    if base_treino.empty or base_treino.index[-1] != pd.Timestamp(FIM_TREINO):
        raise ValueError(f"{categoria}: histórico de treino precisa terminar em dez/2023")

    resultados = {}
    detalhes = []
    for nome in ("regressao_linear", "random_forest"):
        previsoes = prever_categoria(base_treino, alvo, nome)
        pred = pd.Series({pd.Timestamp(p["data"]): p["valor_previsto"] for p in previsoes})
        resultados[nome] = {"rmse": mean_squared_error(observado, pred) ** 0.5,
                            "mape": mean_absolute_percentage_error(observado, pred) * 100}
        detalhes.extend({"categoria": categoria, "data": data.strftime("%Y-%m"),
                         "modelo": nome, "observado": real, "previsto": prev}
                        for data, real, prev in zip(observado.index, observado, pred))

    # A cada mês, repete a observação de 2023 correspondente. Não usa os
    # valores observados de 2024/2025 como insumo durante a avaliação.
    base_2023 = base_treino.loc["2023-01-01":"2023-12-01", alvo]
    if len(base_2023) != 12:
        raise ValueError(f"{categoria}: baseline requer os 12 meses de 2023")
    pred_baseline = pd.Series([base_2023.loc[pd.Timestamp(2023, data.month, 1)] for data in esperado], index=esperado)
    resultados["baseline_sazonal"] = {
        "rmse": mean_squared_error(observado, pred_baseline) ** 0.5,
        "mape": mean_absolute_percentage_error(observado, pred_baseline) * 100,
    }
    detalhes.extend({"categoria": categoria, "data": data.strftime("%Y-%m"),
                     "modelo": "baseline_sazonal", "observado": real, "previsto": prev}
                    for data, real, prev in zip(observado.index, observado, pred_baseline))
    return resultados, detalhes


def main():
    linhas_resumo = []
    linhas_detalhe = []
    for categoria, alvo in ALVO_POR_CATEGORIA.items():
        caminho = PASTA_BASES / f"base_{categoria}.csv"
        if not caminho.exists():
            print(f"[pulado] {categoria}: {caminho.name} não encontrado")
            continue

        base = pd.read_csv(caminho, index_col=0)
        if alvo not in base.columns:
            print(f"[aviso] coluna-alvo '{alvo}' não encontrada em base_{categoria}.csv — colunas disponíveis: {list(base.columns)}")
            continue

        base.index = pd.to_datetime(base.index)
        resultados, detalhes = treinar_e_avaliar(base, alvo, categoria)
        linhas_detalhe.extend(detalhes)

        for nome_modelo, r in resultados.items():
            linhas_resumo.append({
                "categoria": categoria, "modelo": nome_modelo,
                "rmse": round(r["rmse"], 2), "mape_pct": round(r["mape"], 2),
            })

    resumo = pd.DataFrame(linhas_resumo)
    print("\n\n=== RESUMO: RMSE e MAPE em jan/2024–dez/2025 (24 meses recursivos) ===")
    print(resumo.to_string(index=False))
    resumo.to_csv(PASTA_TRATADOS / "modelo1_metricas.csv", index=False)
    pd.DataFrame(linhas_detalhe).to_csv(PASTA_TRATADOS / "modelo1_backtest_mensal.csv", index=False)
    print(f"\nSalvos: modelo1_metricas.csv e modelo1_backtest_mensal.csv em {PASTA_TRATADOS}")


if __name__ == "__main__":
    main()
