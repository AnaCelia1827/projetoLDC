"""
Modelo 2: demanda de ração = produção prevista (Modelo 1) x FCR projetado.

Une modelo1_previsao.csv (jan/2026 a dez/2027, kg ou mil-unidades) com
fcr_projetado.csv (anual) e gera a demanda de ração mensal e anual, em toneladas. No fim,
compara o total anual de 2026 com o benchmark oficial do boletim_mar26
(total_racoes em sindiracoes_tidy.csv) para validar o modelo.

Roda de dentro de notebooks/, sem argumentos.
"""
import pandas as pd
from pathlib import Path

PASTA_TRATADOS = Path(__file__).resolve().parent.parent / "documentos" / "tratados"

# categorias cuja producao do Modelo 1 esta em KG (precisa /1000 pra virar toneladas
# antes de multiplicar pelo FCR); ovos e leite ja estao em mil-unidades, sem conversao.
CATEGORIAS_EM_KG = {"bovinos", "suinos", "frangos"}


ALVO_POR_CATEGORIA = {
    "bovinos": "Peso total das carcaças",
    "suinos": "Peso total das carcaças",
    "frangos": "Peso total das carcaças",
    "ovos": "Quantidade de ovos produzidos",
    "leite": "Quantidade de leite cru, resfriado ou não, adquirido",
}


def main():
    previsao = pd.read_csv(PASTA_TRATADOS / "modelo1_previsao.csv")
    fcr = pd.read_csv(PASTA_TRATADOS / "fcr_projetado.csv")

    producao = previsao.copy()
    meses_esperados = set(pd.period_range("2026-01", "2027-12", freq="M").astype(str))
    for categoria in ALVO_POR_CATEGORIA:
        meses = set(producao.loc[producao["categoria"] == categoria, "data"])
        if meses != meses_esperados:
            raise ValueError(f"{categoria}: previsão deve cobrir jan/2026 a dez/2027, sem lacunas")

    producao["ano"] = producao["data"].str[:4].astype(int)
    producao = producao.merge(fcr, on=["categoria", "ano"], how="left")

    faltando = producao[producao["fcr_projetado"].isna()]
    if not faltando.empty:
        anos_faltando = sorted(faltando["ano"].unique())
        print(f"[aviso] sem FCR projetado para os anos {anos_faltando} — essas linhas ficam sem ração prevista. "
              f"Rode projetar_fcr.py com ANOS_PROJETAR incluindo esses anos.")

    def calcular_racao(linha):
        producao_eq = linha["valor_previsto"] / 1000 if linha["categoria"] in CATEGORIAS_EM_KG else linha["valor_previsto"]
        return producao_eq * linha["fcr_projetado"]

    producao["racao_toneladas"] = producao.apply(calcular_racao, axis=1)

    producao.to_csv(PASTA_TRATADOS / "modelo2_previsao_mensal.csv", index=False)

    anual = producao.groupby(["categoria", "ano"])["racao_toneladas"].sum().reset_index()
    anual_wide = anual.pivot(index="ano", columns="categoria", values="racao_toneladas")
    anual_wide["total_5_categorias"] = anual_wide.sum(axis=1)

    print("Demanda de ração anual prevista (toneladas), por categoria:")
    print(anual_wide.round(0).to_string())

    # validação contra o benchmark oficial do setor (boletim_mar26)
    caminho_sindiracoes = PASTA_TRATADOS / "sindiracoes_tidy.csv"
    if caminho_sindiracoes.exists():
        sindiracoes = pd.read_csv(caminho_sindiracoes)
        benchmark = sindiracoes[
            (sindiracoes["item"] == "total_racoes")
            & (sindiracoes["fonte"] == "boletim_mar26")
            & (sindiracoes["ano"] == 2026)
        ]
        if not benchmark.empty and 2026 in anual_wide.index:
            valor_benchmark = benchmark.iloc[0]["valor"]
            nosso_total_5cat = anual_wide.loc[2026, "total_5_categorias"]
            print(f"\n--- Validação 2026 ---")
            print(f"Benchmark oficial (TOTAL RAÇÕES, todas as cadeias): {valor_benchmark:,.0f} toneladas")
            print(f"Soma das nossas 5 categorias (bovinos, suínos, frangos, ovos, leite): {nosso_total_5cat:,.0f} toneladas")
            print("Nota: o benchmark inclui cães/gatos, equinos, aquacultura e outros, que não modelamos — "
                  "a diferença esperada é aproximadamente o que esses segmentos representam.")

    anual_wide.to_csv(PASTA_TRATADOS / "modelo2_previsao_anual.csv")
    print(f"\nSalvos: modelo2_previsao_mensal.csv e modelo2_previsao_anual.csv em {PASTA_TRATADOS}")


if __name__ == "__main__":
    main()
