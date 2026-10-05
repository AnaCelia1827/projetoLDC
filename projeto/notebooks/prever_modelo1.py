"""
Modelo 1: projeção de jan/2026 a dez/2027, usando o modelo campeão (menor
MAPE) de cada categoria, re-treinado com dados até dez/2025.

Previsão recursiva: cada mês previsto vira input para prever o mês
seguinte (via lags e médias móveis). Preços são mantidos no último valor
observado - é uma premissa de cenário, documentar no relatório; para
análise de sensibilidade depois, basta variar esse valor.

Roda de dentro de notebooks/, sem argumentos.
"""
import pandas as pd
import numpy as np
from pathlib import Path
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression

PASTA_TRATADOS = Path(__file__).resolve().parent.parent / "documentos" / "tratados"
PASTA_BASES = PASTA_TRATADOS / "bases_unificadas"
MESES_PREVER = 24
CORTE_HISTORICO = "2025-12-01"

ALVO_POR_CATEGORIA = {
    "bovinos": "Peso total das carcaças",
    "suinos": "Peso total das carcaças",
    "frangos": "Peso total das carcaças",
    "ovos": "Quantidade de ovos produzidos",
    "leite": "Quantidade de leite cru, resfriado ou não, adquirido",
}
COLUNAS_PRECO = ["preco_milho", "preco_soja_parana", "preco_sorgo_estimado"]

MODELOS = {
    "regressao_linear": LinearRegression,
    "random_forest": lambda: RandomForestRegressor(n_estimators=300, random_state=42),
}


def escolher_campeao(metricas, categoria):
    linhas = metricas[(metricas["categoria"] == categoria) & (metricas["modelo"].isin(MODELOS))]
    if linhas.empty:
        return "regressao_linear"  # default se não houver métrica salva
    return linhas.sort_values("mape_pct").iloc[0]["modelo"]


def montar_linha_features(serie, data_alvo, colunas_preco_presentes, ultimo_preco):
    """Monta uma linha de features para 'data_alvo', usando os valores mais
    recentes (reais ou já previstos) da série para lags e médias móveis."""
    linha = {
        "mes_sin": np.sin(2 * np.pi * data_alvo.month / 12),
        "mes_cos": np.cos(2 * np.pi * data_alvo.month / 12),
        "lag_1": serie.iloc[-1],
        "lag_2": serie.iloc[-2],
        "lag_3": serie.iloc[-3],
        "lag_12": serie.iloc[-12],
        "media_movel_3": serie.iloc[-3:].mean(),
        "media_movel_12": serie.iloc[-12:].mean(),
    }
    for c in colunas_preco_presentes:
        linha[c] = ultimo_preco[c]
    return linha


def prever_categoria(base, alvo, nome_modelo):
    base = base.copy()
    base.index = pd.to_datetime(base.index)
    base = base.sort_index()

    colunas_preco_presentes = [c for c in COLUNAS_PRECO if c in base.columns]
    ultimo_preco = base[colunas_preco_presentes].iloc[-1] if colunas_preco_presentes else {}

    # recria as mesmas features do treino para ajustar o modelo em TODO o histórico
    df = base.copy()
    df["mes_sin"] = np.sin(2 * np.pi * df.index.month / 12)
    df["mes_cos"] = np.cos(2 * np.pi * df.index.month / 12)
    for lag in [1, 2, 3, 12]:
        df[f"lag_{lag}"] = df[alvo].shift(lag)
    df["media_movel_3"] = df[alvo].shift(1).rolling(3).mean()
    df["media_movel_12"] = df[alvo].shift(1).rolling(12).mean()

    features = ["mes_sin", "mes_cos", "lag_1", "lag_2", "lag_3", "lag_12",
                "media_movel_3", "media_movel_12"] + colunas_preco_presentes
    df_treino = df[features + [alvo]].dropna()

    modelo = MODELOS[nome_modelo]()
    modelo.fit(df_treino[features], df_treino[alvo])

    # previsão recursiva mês a mês
    serie = base[alvo].copy()
    ultima_data = base.index[-1]
    previsoes = []
    for i in range(1, MESES_PREVER + 1):
        data_alvo = ultima_data + pd.DateOffset(months=i)
        linha = montar_linha_features(serie, data_alvo, colunas_preco_presentes, ultimo_preco)
        X_linha = pd.DataFrame([linha])[features]
        valor_previsto = modelo.predict(X_linha)[0]
        serie.loc[data_alvo] = valor_previsto
        previsoes.append({"data": data_alvo.strftime("%Y-%m"), "valor_previsto": valor_previsto})

    return previsoes


def main():
    metricas = pd.read_csv(PASTA_TRATADOS / "modelo1_metricas.csv")
    todas_previsoes = []

    for categoria, alvo in ALVO_POR_CATEGORIA.items():
        caminho = PASTA_BASES / f"base_{categoria}.csv"
        if not caminho.exists():
            print(f"[pulado] {categoria}: arquivo não encontrado")
            continue

        base = pd.read_csv(caminho, index_col=0)
        base = base.loc[base.index <= CORTE_HISTORICO]
        if base.empty or base.index[-1] != CORTE_HISTORICO:
            raise ValueError(f"{categoria}: histórico precisa terminar em {CORTE_HISTORICO}")
        campeao = escolher_campeao(metricas, categoria)
        print(f"{categoria}: usando '{campeao}' (modelo campeão)")

        previsoes = prever_categoria(base, alvo, campeao)
        for p in previsoes:
            p["categoria"] = categoria
            p["modelo"] = campeao
            todas_previsoes.append(p)

    resultado = pd.DataFrame(todas_previsoes)[["categoria", "data", "valor_previsto", "modelo"]]
    resultado.to_csv(PASTA_TRATADOS / "modelo1_previsao.csv", index=False)
    print(f"\nSalvo em {PASTA_TRATADOS / 'modelo1_previsao.csv'}")
    print(resultado.head(10).to_string(index=False))


if __name__ == "__main__":
    main()
