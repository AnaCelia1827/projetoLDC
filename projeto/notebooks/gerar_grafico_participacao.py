"""Gera o gráfico da composição histórica e projetada usada pelo Modelo 3."""

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from calcular_modelo3 import extrair_participacoes


TRATADOS = Path(__file__).resolve().parent.parent / "documentos" / "tratados"
SAIDA = TRATADOS / "graficos" / "participacao_macroingredientes.png"
ITENS = [
    ("milho", "Milho", "#2563eb"),
    ("farelo_soja_46pb", "Farelo de soja", "#16a34a"),
    ("sorgo", "Sorgo", "#f59e0b"),
    ("coprodutos_gordura_vegetal_ddgs", "Coprodutos/gordura/DDGS", "#a855f7"),
]


def montar_dados():
    boletins = pd.read_csv(TRATADOS / "sindiracoes_tidy.csv")
    historico = extrair_participacoes(boletins)
    historico = historico[(historico["ano"] <= 2025) & (historico["status"] == "estimativa")]
    participacoes = historico.pivot(index="ano", columns="item", values="participacao")

    previsao = pd.read_csv(TRATADOS / "modelo3_previsao_anual.csv").set_index("ano")
    if set(previsao.index) != {2026, 2027} or not (previsao["meses_cobertos"] == 12).all():
        raise ValueError("A previsão precisa conter 2026 e 2027 completos")
    for ano, linha in previsao.iterrows():
        for item, _, _ in ITENS:
            participacoes.loc[ano, item] = linha[item] / linha["racao"]

    participacoes = participacoes.sort_index()
    if participacoes[list(i[0] for i in ITENS)].isna().any().any():
        raise ValueError("Há participações ausentes no histórico ou na projeção")
    participacoes["outros"] = 1 - participacoes[[i[0] for i in ITENS]].sum(axis=1)
    if (participacoes < -1e-8).any().any():
        raise ValueError("Há participações negativas ou soma superior a 100%")
    return participacoes


def main():
    dados = montar_dados()
    anos = dados.index.to_numpy()
    x = np.arange(len(anos))
    cores = [item[2] for item in ITENS] + ["#cbd5e1"]
    nomes = [item[1] for item in ITENS] + ["Outros ingredientes"]
    chaves = [item[0] for item in ITENS] + ["outros"]

    fig, ax = plt.subplots(figsize=(12, 6.7), dpi=160)
    fig.patch.set_facecolor("white")
    acumulado = np.zeros(len(anos))
    for chave, nome, cor in zip(chaves, nomes, cores):
        valores = dados[chave].to_numpy() * 100
        for j, valor in enumerate(valores):
            ax.bar(x[j], valor, bottom=acumulado[j], width=0.72, color=cor,
                   hatch="///" if anos[j] >= 2026 else None,
                   edgecolor="white", linewidth=1)
            if valor >= 2.4:
                texto_cor = "#0f172a" if chave in ("sorgo", "outros") else "white"
                ax.text(x[j], acumulado[j] + valor / 2, f"{valor:.1f}%".replace(".", ","),
                        ha="center", va="center", fontsize=9, fontweight="bold", color=texto_cor)
        acumulado += valores

    fronteira = np.flatnonzero(anos >= 2026)[0] - 0.5
    ax.axvline(fronteira, color="#475569", linestyle="--", linewidth=1.3)
    ax.set_xticks(x, [str(ano) for ano in anos], fontsize=11)
    ax.set_ylim(0, 105)
    ax.set_ylabel("Participação no total de ração (%)", fontsize=11)
    ax.set_title("Composição da ração: histórico e projeção do Modelo 3",
                 loc="left", fontsize=15, fontweight="bold", pad=16)
    ax.text(fronteira / 2, 103, "Historico: estimativas Sindiracoes", ha="center", fontsize=10, color="#334155")
    ax.text((fronteira + len(anos) - 0.5) / 2, 103, "Projecao", ha="center", fontsize=10, color="#334155")
    ax.grid(axis="y", color="#e2e8f0", linewidth=0.8)
    ax.set_axisbelow(True)
    ax.spines[["top", "right"]].set_visible(False)

    from matplotlib.patches import Patch
    legenda = [Patch(facecolor=cor, label=nome) for cor, nome in zip(cores, nomes)]
    ax.legend(handles=legenda, loc="upper center", bbox_to_anchor=(0.5, -0.10),
              ncol=3, frameon=False, fontsize=9)
    fig.text(0.075, 0.015,
             "2026–2027: participação de 2025 mantida; volume mensal varia com a ração prevista. "
             "'Outros' = restante até 100%.",
             fontsize=9, color="#475569")
    fig.text(0.075, 0.050,
             "A categoria de coprodutos de 2018-2020 nao inclui gordura vegetal no rotulo do boletim.",
             fontsize=9, color="#475569")
    fig.subplots_adjust(left=0.08, right=0.98, top=0.88, bottom=0.24)
    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(SAIDA, dpi=160)
    plt.close(fig)
    print(SAIDA)


if __name__ == "__main__":
    main()
