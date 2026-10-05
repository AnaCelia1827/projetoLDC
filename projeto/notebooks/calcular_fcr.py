"""
Calcula o FCR equivalente (toneladas de racao / unidade de producao) por
cadeia e por ano, cruzando:
  - documentos/tratados/sindiracoes_modelo.csv  (racao, anual, pode ter
    mais de uma linha por ano/item - boletins diferentes revisando o mesmo ano)
  - documentos/tratados/{categoria}_tidy.csv     (producao do IBGE, mensal,
    agregada aqui para anual)

Roda de dentro de notebooks/, sem argumentos.
"""
import pandas as pd
from pathlib import Path

PASTA_TRATADOS = Path(__file__).resolve().parent.parent / "documentos" / "tratados"

# ordem cronologica dos boletins, do mais antigo ao mais recente
ORDEM_BOLETINS = ["boletim_maio22", "boletim_jun23", "boletim_maio24", "boletim_maio25", "boletim_mar26"]

# (categoria IBGE, nome da variavel na tabela tidy, item correspondente na Sindiracoes, unidade da producao)
MAPEAMENTO = [
    ("frangos", "Peso total das carcaças", "aves_frango_corte", "kg"),
    ("suinos", "Peso total das carcaças", "suinos", "kg"),
    ("bovinos", "Peso total das carcaças", "bovinos_corte", "kg"),
    ("ovos", "Quantidade de ovos produzidos", "aves_poedeiras", "mil duzias"),
    ("leite", "Quantidade de leite cru, resfriado ou não, adquirido", "bovinos_leite", "mil litros"),
]


def resolver_sindiracoes(df_racao):
    """Para cada (ano, item), mantem so uma linha: prioriza status='estimativa'
    vindo do boletim mais recente; se nao houver estimativa, usa a 'previsao'
    do boletim mais recente."""
    df = df_racao[df_racao["tipo"] == "producao_racao"].copy()
    df["ordem_boletim"] = df["fonte"].map({b: i for i, b in enumerate(ORDEM_BOLETINS)})
    df["prioridade"] = df["status"].map({"estimativa": 1, "previsao": 0})
    df = df.sort_values(["ano", "item", "prioridade", "ordem_boletim"], ascending=[True, True, False, False])
    return df.drop_duplicates(subset=["ano", "item"], keep="first")


def main():
    racao = pd.read_csv(PASTA_TRATADOS / "sindiracoes_modelo.csv")
    racao_resolvida = resolver_sindiracoes(racao)

    linhas_fcr = []
    for categoria, variavel, item_racao, unidade_producao in MAPEAMENTO:
        caminho = PASTA_TRATADOS / f"{categoria}_tidy.csv"
        if not caminho.exists():
            print(f"[pulado] {categoria}: arquivo não encontrado")
            continue

        prod = pd.read_csv(caminho)
        prod = prod[prod["variavel"] == variavel].copy()
        if prod.empty:
            print(f"[aviso] variável '{variavel}' não encontrada em {categoria}_tidy.csv")
            continue

        prod["ano"] = prod["data"].str[:4].astype(int)
        producao_anual = prod.groupby("ano")["valor"].sum()  # soma dos 12 meses = total do ano
        meses_por_ano = prod.groupby("ano")["valor"].count()  # quantos meses entraram na soma

        racao_item = racao_resolvida[racao_resolvida["item"] == item_racao].set_index("ano")["valor"]

        for ano in sorted(set(producao_anual.index) & set(racao_item.index)):
            if meses_por_ano[ano] < 12:
                print(f"[aviso] {categoria} {ano}: só {meses_por_ano[ano]} meses de produção — ano incompleto, FCR não calculado")
                continue

            prod_ano = producao_anual[ano]
            racao_ano_ton = racao_item[ano]  # já em toneladas

            if unidade_producao == "kg":
                prod_ano_ton = prod_ano / 1000
                fcr = racao_ano_ton / prod_ano_ton  # kg ração / kg produto
            else:
                # ovos (mil dúzias) e leite (mil litros): mantém a unidade original,
                # o FCR aqui é toneladas de ração por mil dúzias/litros, não é
                # comparável entre si nem com frango/suíno/bovino
                fcr = racao_ano_ton / prod_ano

            linhas_fcr.append(
                {
                    "ano": ano,
                    "categoria": categoria,
                    "producao": prod_ano,
                    "unidade_producao": unidade_producao,
                    "racao_toneladas": racao_ano_ton,
                    "fcr": round(fcr, 4),
                }
            )

    fcr_df = pd.DataFrame(linhas_fcr).sort_values(["categoria", "ano"])
    fcr_df.to_csv(PASTA_TRATADOS / "fcr_tidy.csv", index=False)
    print(fcr_df.to_string(index=False))
    print(f"\nSalvo em {PASTA_TRATADOS / 'fcr_tidy.csv'}")


if __name__ == "__main__":
    main()