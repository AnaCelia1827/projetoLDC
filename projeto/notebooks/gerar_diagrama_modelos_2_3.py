"""Diagrama executivo: método descrito no TAP vs. Modelos 2 e 3 implementados."""

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch


SAIDA = Path(__file__).resolve().parent.parent / "documentos" / "tratados" / "graficos" / "fluxo_modelos_2_3.png"


def caixa(ax, x, y, w, h, titulo, corpo, fundo, borda):
    ax.add_patch(FancyBboxPatch((x, y), w, h,
                 boxstyle="round,pad=0.012,rounding_size=0.018",
                 facecolor=fundo, edgecolor=borda, linewidth=1.6))
    ax.text(x + 0.02, y + h - 0.035, titulo, ha="left", va="top",
            fontsize=14, fontweight="bold", color="#0f172a")
    ax.text(x + 0.02, y + h - 0.095, corpo, ha="left", va="top",
            fontsize=11.5, linespacing=1.55, color="#334155")


def main():
    fig, ax = plt.subplots(figsize=(16, 10), dpi=150)
    fig.patch.set_facecolor("#f8fafc")
    ax.set_facecolor("#f8fafc")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    ax.text(0.04, 0.965, "Da produção animal aos ingredientes da ração",
            fontsize=22, fontweight="bold", color="#0f172a", va="top")
    ax.text(0.04, 0.918, "Como o cálculo descrito no TAP se compara ao protótipo atual",
            fontsize=13, color="#475569", va="top")

    ax.text(0.04, 0.855, "MÉTODO ATUAL DESCRITO NO TAP", fontsize=13,
            fontweight="bold", color="#64748b")
    ax.text(0.515, 0.855, "PROTÓTIPO DESTE REPOSITÓRIO", fontsize=13,
            fontweight="bold", color="#1d4ed8")

    caixa(ax, 0.04, 0.57, 0.435, 0.25,
          "Modelo 2 · ração",
          "Produção esperada × coeficiente fixo\n"
          "de ração por unidade produzida\n\n"
          "Premissa não acompanha mudanças no FCR.",
          "#f1f5f9", "#94a3b8")
    caixa(ax, 0.515, 0.57, 0.445, 0.25,
          "Modelo 2 · ração",
          "Produção mensal prevista (Modelo 1)\n"
          "× FCR projetado por cadeia e ano\n"
          "= ração mensal por cadeia\n\n"
          "FCR: tendência de 2021–2025; soma de 5 cadeias.",
          "#eff6ff", "#3b82f6")

    caixa(ax, 0.04, 0.285, 0.435, 0.25,
          "Modelo 3 · ingredientes",
          "Ração prevista × proporção fixa\n"
          "de cada ingrediente\n\n"
          "Mix estático, sem teste explícito\n"
          "contra alternativas.",
          "#f1f5f9", "#94a3b8")
    caixa(ax, 0.515, 0.285, 0.445, 0.25,
          "Modelo 3 · ingredientes",
          "Ração mensal do Modelo 2\n"
          "× participação do ingrediente em 2025\n"
          "= toneladas do ingrediente por mês\n\n"
          "Ex.: 2026: 84,53 Mt ração × 56,34% = 47,63 Mt milho.",
          "#f0fdf4", "#22c55e")

    for x in (0.257, 0.737):
        ax.annotate("", xy=(x, 0.545), xytext=(x, 0.56),
                    arrowprops=dict(arrowstyle="-|>", color="#475569", lw=2.2,
                                    mutation_scale=18))
    ax.add_patch(FancyBboxPatch((0.04, 0.055), 0.92, 0.185,
                 boxstyle="round,pad=0.012,rounding_size=0.018",
                 facecolor="white", edgecolor="#cbd5e1", linewidth=1.4))
    ax.text(0.06, 0.215, "O que o protótipo agrega hoje", fontsize=14,
            fontweight="bold", color="#0f172a", va="top")
    ax.text(0.06, 0.177,
            "• FCR varia por cadeia e ano; resultados mensais integrados para 2026–2027.\n"
            "• Mix de ingredientes escolhido por backtest: última participação venceu a tendência (6,17% vs. 9,10% de MAPE).",
            fontsize=10.8, color="#334155", va="top", linespacing=1.4)
    ax.text(0.06, 0.103,
            "Limite: o mix principal continua fixo em 2025. Cenários de preço são manuais; o backtest do Modelo 2\n"
            "teve 4,09% de erro médio nos totais anuais, contra 3,98% da baseline. Ganho geral ainda não comprovado.",
            fontsize=10.2, color="#9a3412", va="top", linespacing=1.3)

    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(SAIDA, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    print(SAIDA)


if __name__ == "__main__":
    main()
