"""
Consolida boletins da Sindiracoes. Os de 2019, 2020 e 2021 acrescentam
somente a composicao historica de 2018, 2019 e 2020, respectivamente.
num unico CSV tidy: ano, tipo, item, valor, unidade, fonte, status.

- tipo = "producao_racao": producao de racao por segmento animal, em TONELADAS.
- tipo = "composicao_racao": participacao de cada macroingrediente na coluna
  "TOTAL RACOES" da tabela de macroingredientes de cada boletim, em TONELADAS.
- status = "estimativa" (dado do ano corrente/anterior, ainda sujeito a revisao)
  ou "previsao" (projecao para o ano seguinte). Nenhuma linha e descartada:
  o mesmo ano pode aparecer em mais de um boletim, com status diferente -
  fica a critério de quem for consolidar decidir qual valor manter.
- Os nomes de item foram mantidos estaveis mesmo quando o boletim renomeou o
  ingrediente (ex.: "Calcario" -> "Carbonato de Calcio"; "Farelo/Caroco Algodao"
  -> "Farelo Algodao 38%"); a mudanca de rotulo esta comentada no codigo.
"""
import csv
from pathlib import Path

# ---------------------------------------------------------------------------
# tipo = producao_racao. Cada boletim: { item: { ano: (valor_em_MILHOES_t, status) } }
# Os valores sao convertidos para TONELADAS na hora de escrever o CSV.
# ---------------------------------------------------------------------------

producao_racao_por_boletim = {
    "boletim_maio22": {
        "aves_frango_corte": {2021: (35.4, "estimativa"), 2022: (36.8, "previsao")},
        "aves_poedeiras": {2021: (7.19, "estimativa"), 2022: (7.37, "previsao")},
        "aves_total": {2021: (42.6, "estimativa"), 2022: (44.2, "previsao")},
        "suinos": {2021: (19.7, "estimativa"), 2022: (20.4, "previsao")},
        "bovinos_leite": {2021: (6.4, "estimativa"), 2022: (6.5, "previsao")},
        "bovinos_corte": {2021: (5.73, "estimativa"), 2022: (5.87, "previsao")},
        "bovinos_total": {2021: (12.2, "estimativa"), 2022: (12.4, "previsao")},
        "caes_gatos": {2021: (3.48, "estimativa"), 2022: (3.67, "previsao")},
        "equinos": {2021: (0.631, "estimativa"), 2022: (0.643, "previsao")},
        "aquacultura_peixes": {2021: (1.35, "estimativa"), 2022: (1.43, "previsao")},
        "aquacultura_camaroes": {2021: (0.092, "estimativa"), 2022: (0.097, "previsao")},
        "outros": {2021: (0.858, "estimativa"), 2022: (0.870, "previsao")},
        "total_racoes": {2021: (80.8, "estimativa"), 2022: (83.6, "previsao")},
        "sal_mineral": {2021: (4.12, "estimativa"), 2022: (4.33, "previsao")},
        "total_geral": {2021: (85.0, "estimativa"), 2022: (88.0, "previsao")},
    },
    "boletim_jun23": {
        # este boletim nao separa peixes/camaroes dentro de aquacultura
        "aves_frango_corte": {2022: (35.7, "estimativa"), 2023: (36.4, "previsao")},
        "aves_poedeiras": {2022: (6.9, "estimativa"), 2023: (6.8, "previsao")},
        "aves_total": {2022: (42.6, "estimativa"), 2023: (43.2, "previsao")},
        "suinos": {2022: (20.6, "estimativa"), 2023: (21.4, "previsao")},
        "bovinos_leite": {2022: (6.2, "estimativa"), 2023: (6.2, "previsao")},
        "bovinos_corte": {2022: (5.95, "estimativa"), 2023: (6.1, "previsao")},
        "bovinos_total": {2022: (12.1, "estimativa"), 2023: (12.3, "previsao")},
        "caes_gatos": {2022: (3.72, "estimativa"), 2023: (3.9, "previsao")},
        "equinos": {2022: (0.637, "estimativa"), 2023: (0.643, "previsao")},
        "aquacultura_total": {2022: (1.49, "estimativa"), 2023: (1.63, "previsao")},
        "outros": {2022: (0.861, "estimativa"), 2023: (0.864, "previsao")},
        "total_racoes": {2022: (82.0, "estimativa"), 2023: (83.9, "previsao")},
        "sal_mineral": {2022: (3.87, "estimativa"), 2023: (3.84, "previsao")},
        "total_geral": {2022: (85.9, "estimativa"), 2023: (87.8, "previsao")},
    },
    "boletim_maio24": {
        # 2022 aqui já é dado "fechado" (sem asterisco no boletim); tratado como estimativa
        "aves_frango_corte": {2022: (35.7, "estimativa"), 2023: (36.5, "estimativa"), 2024: (37.8, "previsao")},
        "aves_poedeiras": {2022: (6.90, "estimativa"), 2023: (6.90, "estimativa"), 2024: (6.97, "previsao")},
        "aves_total": {2022: (42.6, "estimativa"), 2023: (43.4, "estimativa"), 2024: (44.7, "previsao")},
        "suinos": {2022: (20.6, "estimativa"), 2023: (20.8, "estimativa"), 2024: (21.0, "previsao")},
        "bovinos_leite": {2022: (6.2, "estimativa"), 2023: (6.0, "estimativa"), 2024: (6.2, "previsao")},
        "bovinos_corte": {2022: (6.7, "estimativa"), 2023: (6.6, "estimativa"), 2024: (6.8, "previsao")},
        "bovinos_total": {2022: (12.8, "estimativa"), 2023: (12.6, "estimativa"), 2024: (13.0, "previsao")},
        "caes_gatos": {2022: (3.72, "estimativa"), 2023: (3.88, "estimativa"), 2024: (4.03, "previsao")},
        "equinos": {2022: (0.637, "estimativa"), 2023: (0.640, "estimativa"), 2024: (0.640, "previsao")},
        "aquacultura_peixes": {2022: (1.39, "estimativa"), 2023: (1.43, "estimativa"), 2024: (1.50, "previsao")},
        "aquacultura_camaroes": {2022: (0.179, "estimativa"), 2023: (0.190, "estimativa"), 2024: (0.192, "previsao")},
        "outros": {2022: (0.615, "estimativa"), 2023: (0.620, "estimativa"), 2024: (0.625, "previsao")},
        "total_racoes": {2022: (82.6, "estimativa"), 2023: (83.6, "estimativa"), 2024: (85.7, "previsao")},
        "sal_mineral": {2022: (3.50, "estimativa"), 2023: (3.37, "estimativa"), 2024: (3.52, "previsao")},
        "total_geral": {2022: (86.1, "estimativa"), 2023: (86.9, "estimativa"), 2024: (89.3, "previsao")},
    },
    "boletim_maio25": {
        # gráfico simples do boletim; nao reporta aves_total/bovinos_total agregados
        "aves_frango_corte": {2024: (36.9, "estimativa"), 2025: (37.9, "previsao")},
        "aves_poedeiras": {2024: (7.2, "estimativa"), 2025: (7.4, "previsao")},
        "suinos": {2024: (21.6, "estimativa"), 2025: (22.0, "previsao")},
        "bovinos_corte": {2024: (7.2, "estimativa"), 2025: (7.7, "previsao")},
        "bovinos_leite": {2024: (7.1, "estimativa"), 2025: (7.3, "previsao")},
        "caes_gatos": {2024: (4.0, "estimativa"), 2025: (4.2, "previsao")},
        "sal_mineral": {2024: (3.6, "estimativa"), 2025: (3.9, "previsao")},
        "aquacultura_total": {2024: (1.8, "estimativa"), 2025: (1.9, "previsao")},
        "equinos": {2024: (1.0, "estimativa"), 2025: (1.0, "previsao")},
        "outros": {2024: (0.6, "estimativa"), 2025: (0.6, "previsao")},
        "total_geral": {2024: (91.1, "estimativa"), 2025: (93.8, "previsao")},
    },
    "boletim_mar26": {
        # benchmark final: 2026 = previsao oficial do setor para validar o Modelo 2
        "aves_frango_corte": {2024: (36.9, "estimativa"), 2025: (37.9, "estimativa"), 2026: (39.1, "previsao")},
        "suinos": {2024: (21.6, "estimativa"), 2025: (22.5, "estimativa"), 2026: (23.1, "previsao")},
        "aves_poedeiras": {2024: (7.2, "estimativa"), 2025: (7.4, "estimativa"), 2026: (7.7, "previsao")},
        "bovinos_corte": {2024: (7.2, "estimativa"), 2025: (7.8, "estimativa"), 2026: (8.2, "previsao")},
        "bovinos_leite": {2024: (7.1, "estimativa"), 2025: (7.7, "estimativa"), 2026: (7.9, "previsao")},
        "caes_gatos": {2024: (4.0, "estimativa"), 2025: (4.0, "estimativa"), 2026: (4.2, "previsao")},
        "aquacultura_total": {2024: (1.79, "estimativa"), 2025: (1.89, "estimativa"), 2026: (1.96, "previsao")},
        "equinos": {2024: (1.00, "estimativa"), 2025: (1.01, "estimativa"), 2026: (1.01, "previsao")},
        "outros": {2024: (0.63, "estimativa"), 2025: (0.63, "estimativa"), 2026: (0.63, "previsao")},
        # totais nao aparecem no grafico; vem direto da tabela de macroingredientes deste boletim
        "total_racoes": {2025: (90.756002, "estimativa"), 2026: (93.658727, "previsao")},
        "total_geral": {2024: (91.0, "estimativa"), 2025: (94.176002, "estimativa"), 2026: (97.333727, "previsao")},
    },
}

# ---------------------------------------------------------------------------
# tipo = composicao_racao. Coluna "TOTAL RACOES" da tabela de macroingredientes
# de cada boletim, ja em TONELADAS (nao precisa multiplicar).
# ---------------------------------------------------------------------------

composicao_racao_por_boletim = {
    # Coluna TOTAL RACOES, apenas estimativas. Fontes oficiais:
    # https://sindiracoes.org.br/wp-content/uploads/2019/07/boletim_informativo_do_setor_julho_2019_vs_final_port_sindiracoes.pdf (p. 4)
    # https://sindiracoes.org.br/wp-content/uploads/2020/06/boletim_informativo_do_setor_junho_2020_vs_final_port_sindiracoes_c.pdf (p. 4)
    # https://sindiracoes.org.br/wp-content/uploads/2021/03/boletim_informativo_do_setor_marco_2021_vs_final_port_sindiracoes.pdf (p. 5)
    # O grupo de coprodutos de 2018-2020 nao nomeia gordura vegetal,
    # incluida explicitamente no rotulo de 2021 em diante.
    "boletim_jul19": {
        "milho": {2018: (42_428_716, "estimativa")},
        "farelo_soja_46pb": {2018: (15_072_958, "estimativa")},
        "sorgo": {2018: (2_022_993, "estimativa")},
        "coprodutos_gordura_vegetal_ddgs": {2018: (1_117_978, "estimativa")},
        "total": {2018: (69_156_015, "estimativa")},
    },
    "boletim_jun20": {
        "milho": {2019: (45_213_996, "estimativa")},
        "farelo_soja_46pb": {2019: (16_756_978, "estimativa")},
        "sorgo": {2019: (2_073_758, "estimativa")},
        "coprodutos_gordura_vegetal_ddgs": {2019: (1_164_305, "estimativa")},
        "total": {2019: (74_294_151, "estimativa")},
    },
    "boletim_mar21": {
        "milho": {2020: (47_392_551, "estimativa")},
        "farelo_soja_46pb": {2020: (17_553_990, "estimativa")},
        "sorgo": {2020: (2_177_384, "estimativa")},
        "coprodutos_gordura_vegetal_ddgs": {2020: (1_225_830, "estimativa")},
        "total": {2020: (77_941_309, "estimativa")},
    },
    "boletim_maio22": {
        "milho": {2021: (49_660_268, "estimativa"), 2022: (51_401_641, "previsao")},
        "farelo_soja_46pb": {2021: (17_732_817, "estimativa"), 2022: (18_345_030, "previsao")},
        "trigo_coprodutos": {2021: (656_784, "estimativa"), 2022: (681_959, "previsao")},
        "farinhas_gorduras_origem_animal": {2021: (4_320_740, "estimativa"), 2022: (4_504_775, "previsao")},
        "sorgo": {2021: (1_963_662, "estimativa"), 2022: (2_009_490, "previsao")},
        "farelo_caroco_algodao": {2021: (1_134_900, "estimativa"), 2022: (1_159_170, "previsao")},
        "calcario_carbonato_calcio": {2021: (1_252_921, "estimativa"), 2022: (1_288_762, "previsao")},
        "farelo_gluten_milho_21": {2021: (688_794, "estimativa"), 2022: (713_620, "previsao")},
        "farelo_gluten_milho_60": {2021: (50_803, "estimativa"), 2022: (53_459, "previsao")},
        "fosfato_mono_dicalcico": {2021: (362_440, "estimativa"), 2022: (373_033, "previsao")},
        "sal": {2021: (279_649, "estimativa"), 2022: (289_423, "previsao")},
        "ureia_pecuaria": {2021: (140_900, "estimativa"), 2022: (144_030, "previsao")},
        "coprodutos_gordura_vegetal_ddgs": {2021: (1_777_524, "estimativa"), 2022: (1_829_086, "previsao")},
        "lisina_hcl": {2021: (162_020, "estimativa"), 2022: (167_979, "previsao")},
        "metionina": {2021: (126_515, "estimativa"), 2022: (131_293, "previsao")},
        "coprodutos_lacteos": {2021: (103_730, "estimativa"), 2022: (106_911, "previsao")},
        "plasma": {2021: (8_887, "estimativa"), 2022: (9_216, "previsao")},
        "premixes": {2021: (415_936, "estimativa"), 2022: (430_723, "previsao")},
        "total": {2021: (80_839_291, "estimativa"), 2022: (83_639_600, "previsao")},
    },
    "boletim_jun23": {
        "milho": {2022: (50_006_859, "estimativa"), 2023: (51_191_720, "previsao")},
        "farelo_soja_46pb": {2022: (17_637_948, "estimativa"), 2023: (18_003_672, "previsao")},
        "trigo_coprodutos": {2022: (674_224, "estimativa"), 2023: (707_475, "previsao")},
        "farinhas_gorduras_origem_animal": {2022: (4_261_435, "estimativa"), 2023: (4_412_138, "previsao")},
        "sorgo": {2022: (2_551_329, "estimativa"), 2023: (2_583_209, "previsao")},
        "coprodutos_gordura_vegetal_ddgs": {2022: (3_255_528, "estimativa"), 2023: (3_327_521, "previsao")},
        "calcario_carbonato_calcio": {2022: (1_245_087, "estimativa"), 2023: (1_252_757, "previsao")},
        "farelo_gluten_milho_21": {2022: (705_626, "estimativa"), 2023: (731_668, "previsao")},
        "farelo_gluten_milho_60": {2022: (53_961, "estimativa"), 2023: (56_468, "previsao")},
        "fosfato_mono_dicalcico": {2022: (369_202, "estimativa"), 2023: (371_695, "previsao")},
        "sal": {2022: (285_053, "estimativa"), 2023: (292_471, "previsao")},
        "ureia_pecuaria": {2022: (143_957, "estimativa"), 2023: (146_900, "previsao")},
        "lisina_hcl": {2022: (165_908, "estimativa"), 2023: (170_572, "previsao")},
        "metionina": {2022: (135_196, "estimativa"), 2023: (138_059, "previsao")},
        "coprodutos_lacteos": {2022: (106_568, "estimativa"), 2023: (110_111, "previsao")},
        "plasma": {2022: (9_297, "estimativa"), 2023: (9_675, "previsao")},
        "premixes": {2022: (422_586, "estimativa"), 2023: (432_890, "previsao")},
        "total": {2022: (82_029_765, "estimativa"), 2023: (83_939_000, "previsao")},
    },
    "boletim_maio24": {
        # esta tabela só trouxe TOTAL RACOES para 2023/2024 (2022 nao consta)
        "milho": {2023: (49_397_403, "estimativa"), 2024: (50_609_649, "previsao")},
        "farelo_soja_46pb": {2023: (17_594_005, "estimativa"), 2024: (18_079_238, "previsao")},
        "trigo_coprodutos": {2023: (706_380, "estimativa"), 2024: (728_450, "previsao")},
        "farinhas_gorduras_origem_animal": {2023: (4_212_231, "estimativa"), 2024: (4_343_061, "previsao")},
        "sorgo": {2023: (4_414_823, "estimativa"), 2024: (4_532_860, "previsao")},
        "farelo_caroco_algodao": {2023: (1_230_247, "estimativa"), 2024: (1_275_825, "previsao")},  # "Farelo Algodao 38%"
        "calcario_carbonato_calcio": {2023: (1_199_646, "estimativa"), 2024: (1_221_688, "previsao")},  # "Carbonato de Calcio"
        "farelo_gluten_milho_21": {2023: (746_101, "estimativa"), 2024: (772_194, "previsao")},
        "farelo_gluten_milho_60": {2023: (51_096, "estimativa"), 2024: (53_056, "previsao")},
        "fosfato_mono_dicalcico": {2023: (268_291, "estimativa"), 2024: (275_116, "previsao")},
        "sal": {2023: (431_644, "estimativa"), 2024: (443_603, "previsao")},
        "ureia_pecuaria": {2023: (179_423, "estimativa"), 2024: (184_861, "previsao")},  # "Ureia Pecuaria/Enxofre/Magnesio 50"
        "coprodutos_gordura_vegetal_ddgs": {2023: (2_215_841, "estimativa"), 2024: (2_292_083, "previsao")},
        "lisina_hcl": {2023: (171_980, "estimativa"), 2024: (176_956, "previsao")},
        "metionina": {2023: (171_217, "estimativa"), 2024: (175_707, "previsao")},
        "coprodutos_lacteos": {2023: (107_211, "estimativa"), 2024: (108_454, "previsao")},
        "plasma": {2023: (8_424, "estimativa"), 2024: (8_509, "previsao")},
        "premixes": {2023: (443_556, "estimativa"), 2024: (455_489, "previsao")},
        "total": {2023: (83_549_519, "estimativa"), 2024: (85_736_800, "previsao")},
    },
    "boletim_maio25": {
        "milho": {2024: (49_730_899, "estimativa"), 2025: (51_061_176, "previsao")},
        "farelo_soja_46pb": {2024: (18_820_143, "estimativa"), 2025: (19_355_563, "previsao")},
        "trigo_coprodutos": {2024: (1_545_791, "estimativa"), 2025: (1_586_773, "previsao")},
        "farinhas_gorduras_origem_animal": {2024: (4_222_319, "estimativa"), 2025: (4_350_148, "previsao")},
        "sorgo": {2024: (4_597_092, "estimativa"), 2025: (4_752_837, "previsao")},
        "farelo_caroco_algodao": {2024: (1_378_317, "estimativa"), 2025: (1_459_474, "previsao")},
        "calcario_carbonato_calcio": {2024: (1_311_807, "estimativa"), 2025: (1_345_841, "previsao")},
        "farelo_gluten_milho_21": {2024: (815_964, "estimativa"), 2025: (848_811, "previsao")},
        "farelo_gluten_milho_60": {2024: (53_019, "estimativa"), 2025: (55_103, "previsao")},
        "fosfato_mono_dicalcico": {2024: (220_994, "estimativa"), 2025: (227_784, "previsao")},
        "sal": {2024: (328_967, "estimativa"), 2025: (340_039, "previsao")},
        "ureia_pecuaria": {2024: (206_492, "estimativa"), 2025: (216_154, "previsao")},
        "coprodutos_gordura_vegetal_ddgs": {2024: (3_275_061, "estimativa"), 2025: (3_402_572, "previsao")},
        "lisina_hcl": {2024: (184_105, "estimativa"), 2025: (188_723, "previsao")},
        "metionina": {2024: (185_943, "estimativa"), 2025: (190_513, "previsao")},
        "coprodutos_lacteos": {2024: (113_955, "estimativa"), 2025: (116_420, "previsao")},
        "plasma": {2024: (8_737, "estimativa"), 2025: (8_913, "previsao")},
        "premixes": {2024: (464_474, "estimativa"), 2025: (478_034, "previsao")},
        "total": {2024: (87_464_080, "estimativa"), 2025: (89_984_880, "previsao")},
    },
    "boletim_mar26": {
        # boletim mais recente: 2026 e a previsao-benchmark para validar o Modelo 2
        "milho": {2025: (51_133_621, "estimativa"), 2026: (52_726_448, "previsao")},
        "farelo_soja_46pb": {2025: (19_751_185, "estimativa"), 2026: (20_387_132, "previsao")},
        "trigo_coprodutos": {2025: (1_615_973, "estimativa"), 2026: (1_658_295, "previsao")},
        "farinhas_gorduras_origem_animal": {2025: (4_011_591, "estimativa"), 2026: (4_128_586, "previsao")},
        "sorgo": {2025: (4_844_705, "estimativa"), 2026: (5_010_877, "previsao")},
        "farelo_caroco_algodao": {2025: (1_483_188, "estimativa"), 2026: (1_558_850, "previsao")},
        "calcario_carbonato_calcio": {2025: (1_361_242, "estimativa"), 2026: (1_407_427, "previsao")},
        "farelo_gluten_milho_21": {2025: (911_214, "estimativa"), 2026: (940_337, "previsao")},  # 21% e 60% unificados neste boletim
        "fosfato_mono_dicalcico": {2025: (233_700, "estimativa"), 2026: (240_787, "previsao")},
        "sal": {2025: (343_872, "estimativa"), 2026: (355_295, "previsao")},
        "ureia_pecuaria": {2025: (221_649, "estimativa"), 2026: (230_680, "previsao")},
        "coprodutos_gordura_vegetal_ddgs": {2025: (3_772_953, "estimativa"), 2026: (3_910_089, "previsao")},
        "lisina_hcl": {2025: (189_397, "estimativa"), 2026: (195_222, "previsao")},
        "metionina": {2025: (191_424, "estimativa"), 2026: (197_129, "previsao")},
        "coprodutos_lacteos": {2025: (119_464, "estimativa"), 2026: (122_483, "previsao")},
        "plasma": {2025: (9_091, "estimativa"), 2026: (9_322, "previsao")},
        "premixes": {2025: (561_731, "estimativa"), 2026: (579_770, "previsao")},
        "total": {2025: (90_756_002, "estimativa"), 2026: (93_658_727, "previsao")},
    },
}

linhas = []

for fonte, itens in producao_racao_por_boletim.items():
    for item, por_ano in itens.items():
        for ano, (valor_milhoes, status) in por_ano.items():
            linhas.append([ano, "producao_racao", item, round(valor_milhoes * 1_000_000), "toneladas", fonte, status])

for fonte, itens in composicao_racao_por_boletim.items():
    for item, por_ano in itens.items():
        for ano, (valor_toneladas, status) in por_ano.items():
            linhas.append([ano, "composicao_racao", item, valor_toneladas, "toneladas", fonte, status])

linhas.sort(key=lambda r: (r[1], r[2], r[0], r[5]))

saida = Path(__file__).resolve().parent.parent / "documentos" / "tratados" / "sindiracoes_tidy.csv"
with open(saida, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["ano", "tipo", "item", "valor", "unidade", "fonte", "status"])
    w.writerows(linhas)

print(f"{len(linhas)} linhas escritas em {saida}")
print(f"Boletins de composicao incluidos: {list(composicao_racao_por_boletim.keys())}")
