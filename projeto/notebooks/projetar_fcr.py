"""
Projeta o FCR (racao/producao) de cada categoria para os anos futuros,
usando uma regressao linear simples sobre o ano (nao e serie temporal
pura - e so uma tendencia, documentada como premissa).

Roda de dentro de notebooks/, sem argumentos.
"""
import pandas as pd
import numpy as np
from pathlib import Path

PASTA_TRATADOS = Path(__file__).resolve().parent.parent / "documentos" / "tratados"
ANOS_PROJETAR = [2026, 2027]

fcr = pd.read_csv(PASTA_TRATADOS / "fcr_tidy.csv")

linhas = []
for categoria, grupo in fcr.groupby("categoria"):
    grupo = grupo.sort_values("ano")
    x = grupo["ano"].values
    y = grupo["fcr"].values

    coef = np.polyfit(x, y, 1)  # ajuste linear: fcr = a*ano + b
    tendencia_anual = coef[0]

    for ano in ANOS_PROJETAR:
        fcr_projetado = np.polyval(coef, ano)
        linhas.append({"ano": ano, "categoria": categoria, "fcr_projetado": round(fcr_projetado, 4),
                        "tendencia_anual": round(tendencia_anual, 5)})

    direcao = "caindo (ganho de eficiência)" if tendencia_anual < 0 else "subindo (mais ração por unidade produzida)"
    print(f"{categoria}: tendência de {tendencia_anual:+.4f} no FCR por ano — {direcao}")

projetado = pd.DataFrame(linhas)
projetado.to_csv(PASTA_TRATADOS / "fcr_projetado.csv", index=False)
print("\n" + projetado.to_string(index=False))
print(f"\nSalvo em {PASTA_TRATADOS / 'fcr_projetado.csv'}")
