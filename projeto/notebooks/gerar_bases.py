"""
Gera uma base unificada (producao + precos) por categoria animal.
Roda de dentro de notebooks/, sem argumentos.
"""
import pandas as pd
from pathlib import Path

PASTA_TRATADOS = Path(__file__).resolve().parent.parent / "documentos" / "tratados"
PASTA_SAIDA = PASTA_TRATADOS / "bases_unificadas"
PASTA_SAIDA.mkdir(exist_ok=True)

CATEGORIAS = ["bovinos", "suinos", "frangos", "ovos", "leite"]

precos = pd.read_csv(PASTA_TRATADOS / "precos_tidy.csv")
precos_wide = precos.pivot_table(index="data", columns="variavel", values="valor")

for cat in CATEGORIAS:
    caminho = PASTA_TRATADOS / f"{cat}_tidy.csv"
    if not caminho.exists():
        print(f"[pulado] {cat}: {caminho.name} não encontrado")
        continue

    prod = pd.read_csv(caminho)
    prod_wide = prod.pivot_table(index="data", columns="variavel", values="valor")

    base = prod_wide.join(precos_wide, how="left")
    base.index = pd.to_datetime(base.index)
    base = base.sort_index()

    # checagem rápida de buracos
    faltando = base.isna().sum()
    if faltando.any():
        print(f"[{cat}] valores faltando por coluna:")
        print(faltando[faltando > 0])
    else:
        print(f"[{cat}] sem valores faltando. {len(base)} linhas, de {base.index.min().date()} a {base.index.max().date()}")

    base.to_csv(PASTA_SAIDA / f"base_{cat}.csv")

print("\nBases unificadas salvas em documentos/tratados/bases_unificadas/")