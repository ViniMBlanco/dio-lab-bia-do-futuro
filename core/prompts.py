"""
prompts.py
==========
Monta os prompts enviados ao LLM em cada turno de conversa.
Centraliza toda a engenharia de prompt do SeuFariaLimer.

Componentes:
    SYSTEM_PROMPT    Personalidade, regras e few-shot fixos
    build_context()  Monta o bloco dinâmico com dados do cliente + RAG
    build_messages() Empilha tudo no formato da API (lista de dicts)
"""

import json
from typing import Optional

# ── System Prompt ─────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """Você é o SeuFariaLimer — consultor de educação financeira com IA.
Você democratiza o conhecimento do mercado financeiro brasileiro: fala como um amigo que entende de finanças, sem julgamento, sem jargão desnecessário e com embasamento real.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REGRAS INEGOCIÁVEIS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. USE APENAS O CONTEXTO FORNECIDO. Se a informação não estiver nos blocos [CONTEXTO DO CLIENTE] ou [CONHECIMENTO FINANCEIRO], diga claramente que não possui esse dado e indique onde encontrá-lo. Nunca invente taxas, rentabilidades, saldos ou datas.

2. NUNCA RECOMENDE ATIVOS ESPECÍFICOS PARA COMPRA/VENDA. Você pode explicar como um ativo funciona e se é compatível com o perfil. Mas "compre X" ou "venda Y" está fora do seu escopo — isso é função de analista certificado CVM (Res. CVM nº 20/2021).

3. NUNCA PROJETE RENTABILIDADE FUTURA COM CERTEZA. Use linguagem hipotética: "em um cenário de X%", "historicamente", "se mantida essa taxa". Sempre inclua: "Rentabilidade passada não garante resultado futuro."

4. SUITABILITY ANTES DE PRODUTOS. Se o cliente não tiver perfil no contexto, faça o diagnóstico com as 5 perguntas antes de qualquer sugestão.

5. ADMITA LIMITAÇÕES COM NATURALIDADE. "Esse dado específico não tenho agora — mas posso explicar a lógica e onde encontrar o número exato."

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DETECTOR DE GOLPES — VERIFIQUE SEMPRE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Antes de responder qualquer pergunta sobre produto ou oportunidade, verifique:
🚨 Rentabilidade garantida acima da Selic
🚨 Retorno de 1% ao dia ou mais
🚨 Pressão para decidir rápido ("só hoje", "vagas limitadas")
🚨 Empresa sem registro na CVM (cvm.gov.br)
🚨 Necessidade de recrutar outras pessoas para ganhar
🚨 Cripto ou "robô de investimento" com retorno fixo garantido
🚨 Contato não solicitado por WhatsApp ou Instagram

Se identificar QUALQUER sinal, responda com ALERTA antes de qualquer outra coisa:
"⚠️ ATENÇÃO — o que você descreveu tem características de golpe financeiro.
[Explique o sinal identificado e por que é problemático]
Nenhum investimento regulamentado pela CVM garante [rentabilidade citada].
Verifique o registro da empresa em cvm.gov.br antes de qualquer decisão."

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
EXEMPLOS DE RESPOSTAS IDEAIS (FEW-SHOT)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
EXEMPLO A — Pergunta educacional
Usuário: "O que é CDI?"
Resposta: "CDI é a taxa que os bancos usam para emprestar dinheiro entre si — fica sempre colada na Selic (geralmente 0,10% abaixo). Quando um CDB diz '110% do CDI', significa que ele paga 10% a mais que essa taxa. Com a Selic atual em torno de 13,75% ao ano, um CDB de 110% CDI rende aproximadamente 15,1% ao ano — bem acima da poupança."

EXEMPLO B — Simulação
Usuário: "Se investir R$300/mês por 10 anos, quanto terei?"
Resposta: "Depende da taxa. Veja três cenários:
• Conservador (~10% a.a.): R$ 61.453
• Moderado (~13% a.a.): R$ 70.236
• Arrojado (~15% a.a.): R$ 78.227
Total que você colocaria: R$ 36.000. Em todos os cenários, os juros compostos geram mais do que você mesmo poupou. Quer ver com seu valor disponível?"

EXEMPLO C — Comparação com IR
Usuário: "LCI 92% CDI ou CDB 110% CDI — qual é melhor?"
Resposta: "Depende do prazo — o IR muda tudo nessa conta.
Para 1 ano (IR 20% no CDB): CDB líquido = 88% CDI. LCI = 92% CDI. → LCI vence.
Para 2 anos (IR 17,5%): CDB líquido = 90,75% CDI. LCI = 92%. → LCI ainda vence por pouco.
Para mais de 2 anos (IR 15%): CDB líquido = 93,5% CDI. LCI = 92%. → CDB vence.
Qual é o seu prazo?"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DISCLAIMER OBRIGATÓRIO
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Inclua ao final de toda resposta que mencione produto financeiro específico:
"⚠️ Sou uma IA educacional. Para decisões de investimento, consulte um assessor certificado pela CVM/ANBIMA. Rentabilidade passada não garante resultado futuro."
"""


# ── Suitability questions ─────────────────────────────────────────────────────

SUITABILITY_QUESTIONS = [
    "Qual é o seu principal objetivo com esse investimento? (ex: reserva de emergência, aposentadoria, comprar um imóvel, fazer uma viagem)",
    "Em quanto tempo você vai precisar desse dinheiro? (menos de 1 ano / 1 a 5 anos / mais de 5 anos)",
    "Se seu investimento cair 20% amanhã, o que você faz? (resgato tudo / aguardo recuperação / aproveito e coloco mais)",
    "Você já investiu em algo além da poupança? Se sim, em quê?",
    "Qual percentual da sua renda mensal você consegue investir sem comprometer seu orçamento?",
]


# ── Context builder ───────────────────────────────────────────────────────────

def build_context(
    client: Optional[dict] = None,
    suitable_products: Optional[list] = None,
    rag_context: Optional[str] = None,
    spending_summary: Optional[dict] = None,
    calculator_result: Optional[str] = None,
) -> str:
    """
    Monta o bloco de contexto dinâmico injetado antes da mensagem do usuário.

    Camada 2 da arquitetura de 3 camadas:
    - Camada 1: SYSTEM_PROMPT (fixo)
    - Camada 2: build_context() (dinâmico por sessão + mensagem)
    - Camada 3: histórico de conversa (gerenciado pelo LangChain)

    Args:
        client:             Dict do cliente (de perfil_investidor.json)
        suitable_products:  Lista de produtos filtrados pelo perfil
        rag_context:        Trechos recuperados do ChromaDB
        spending_summary:   Resumo de gastos (de transacoes.csv)
        calculator_result:  Resultado formatado de uma calculadora

    Returns:
        String com o contexto completo pronto para injeção no prompt
    """
    parts = []

    # ── Dados do cliente ──────────────────────────────────────────────────────
    if client:
        perfil = client.get("perfil", {})
        carteira = client.get("carteira_atual", {})
        metas = client.get("metas", [])
        conta = client.get("conta", {})

        # Reserva de emergência em meses
        despesas_mensais = client.get("renda_mensal", 0) * 0.62
        reserva = carteira.get("reserva_emergencia", 0)
        meses_reserva = round(reserva / despesas_mensais, 1) if despesas_mensais else 0

        carteira_str = "\n".join([
            f"  • {k.replace('_', ' ').title():<25} R$ {v:>10,.2f}"
            for k, v in carteira.items()
        ])

        metas_str = "\n".join([
            f"  {i+1}. {m['descricao']} → R$ {m['valor_alvo']:,.0f} em {m['prazo_anos']} anos ({m['prioridade'].upper()})"
            for i, m in enumerate(metas)
        ])

        parts.append(f"""[CONTEXTO DO CLIENTE]
Nome: {client.get('nome')} | Idade: {client.get('idade')} anos | Profissão: {client.get('profissao')}
Perfil de Investidor: {perfil.get('tipo', 'NÃO DEFINIDO').upper()} (score {perfil.get('score', '—')}/100, avaliado em {perfil.get('data_avaliacao', '—')})
Renda Mensal: R$ {client.get('renda_mensal', 0):,.2f} | Patrimônio Total: R$ {client.get('patrimonio_total', 0):,.2f}
Saldo Disponível: R$ {conta.get('saldo_disponivel', 0):,.2f}

Carteira atual:
{carteira_str}
⚠️ Reserva de emergência cobre {meses_reserva} meses (ideal para {perfil.get('respostas_suitability', {}).get('objetivo', 'CLT')}: 3–6 meses)

Metas financeiras:
{metas_str}""")

    # ── Produtos compatíveis ──────────────────────────────────────────────────
    if suitable_products:
        prod_lines = []
        for p in suitable_products[:6]:  # Máximo 6 para não inflar o contexto
            rent = p.get("rentabilidade", {})
            tipo = rent.get("tipo", "")
            if tipo == "pos_fixado":
                taxa = f"{rent.get('percentual_indexador')}% {rent.get('indexador')}"
            elif tipo == "hibrido":
                taxa = f"{rent.get('indexador')} + {rent.get('taxa_adicional')}% a.a."
            elif tipo == "variavel":
                dy = rent.get("dividend_yield_referencia_aa")
                taxa = f"DY ref. ~{dy}% a.a." if dy else "variável"
            else:
                taxa = "variável"

            isento = p.get("tributacao", {}).get("isento", False)
            garantia = p.get("garantia", "—")
            prod_lines.append(
                f"  • {p.get('nome'):<35} {taxa} | {p.get('liquidez','—')} | {garantia}"
                + (" | ISENTO IR" if isento else "")
            )

        parts.append(f"[PRODUTOS COMPATÍVEIS COM PERFIL {client.get('perfil',{}).get('tipo','').upper() if client else ''}]\n" + "\n".join(prod_lines))

    # ── Resultado de calculadora ──────────────────────────────────────────────
    if calculator_result:
        parts.append(f"[RESULTADO DA CALCULADORA]\n{calculator_result}")

    # ── Análise de gastos ─────────────────────────────────────────────────────
    if spending_summary:
        cats = spending_summary.get("categories", {})
        cat_lines = "\n".join([
            f"  • {k.capitalize():<20} R$ {v:>8,.2f}  ({v/spending_summary.get('total_income',1)*100:.1f}% da renda)"
            for k, v in list(cats.items())[:6]
        ])
        alerts = spending_summary.get("alerts", [])
        alert_str = "\n".join([f"  ⚠️ {a}" for a in alerts]) if alerts else "  ✅ Sem alertas de gastos excessivos"

        parts.append(
            f"[ANÁLISE DE GASTOS — FEVEREIRO/2025]\n"
            f"Total gasto: R$ {spending_summary.get('total_expenses', 0):,.2f} | "
            f"Total investido: R$ {spending_summary.get('total_invested', 0):,.2f} "
            f"({spending_summary.get('investment_rate', 0):.1f}% da renda)\n"
            f"Por categoria:\n{cat_lines}\n"
            f"Alertas:\n{alert_str}"
        )

    # ── Contexto RAG ──────────────────────────────────────────────────────────
    if rag_context:
        parts.append(f"[CONHECIMENTO FINANCEIRO — Base de Dados]\n{rag_context}")

    return "\n\n".join(parts)


# ── Message builder ───────────────────────────────────────────────────────────

def build_messages(
    user_message: str,
    context_block: str,
    history: Optional[list] = None,
) -> list[dict]:
    """
    Empilha system prompt, contexto e histórico no formato da API.
    Compatível com Groq, Gemini (via LangChain) e OpenAI.

    Args:
        user_message:  Mensagem atual do usuário
        context_block: Output de build_context()
        history:       Lista de {"role": ..., "content": ...} das N últimas mensagens

    Returns:
        Lista de dicts no formato [{"role": ..., "content": ...}]
    """
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT}
    ]

    # Injeta contexto como primeira mensagem do usuário na sessão
    if context_block:
        messages.append({
            "role": "user",
            "content": f"[CONTEXTO DA SESSÃO — use essas informações para personalizar suas respostas]\n\n{context_block}"
        })
        messages.append({
            "role": "assistant",
            "content": "Contexto carregado. Estou pronto para te ajudar com base no seu perfil e nos dados da sua conta."
        })

    # Adiciona histórico da conversa (sem o primeiro par de contexto)
    if history:
        messages.extend(history)

    # Mensagem atual
    messages.append({"role": "user", "content": user_message})

    return messages


# ── Detector de golpes (Python puro, antes do LLM) ───────────────────────────

SCAM_PATTERNS = [
    ("1% ao dia",          "1% ao dia equivale a 3.678% ao ano — impossível em qualquer investimento legítimo"),
    ("2% ao dia",          "2% ao dia equivale a mais de 100.000% ao ano — característica clássica de pirâmide"),
    ("retorno garantido",  "Nenhum investimento legítimo garante retorno — isso é proibido pela CVM"),
    ("rendimento garantido","Nenhum investimento legítimo garante rendimento — isso viola as normas CVM"),
    ("lucro garantido",    "Nenhum investimento legítimo garante lucro — isso é sinal de fraude"),
    ("robô de investimento","Robôs com retorno fixo garantido são esquemas fraudulentos não regulamentados"),
    ("grupo de investimento no whatsapp", "Grupos de investimento em WhatsApp sem registro CVM são ilegais"),
    ("pirâmide",           "Esquema de pirâmide é ilegal no Brasil (art. 65 da Lei nº 14.132/2021)"),
    ("ponzi",              "Esquema Ponzi é ilegal — os rendimentos vêm dos novos investidores, não de atividade real"),
]

def detect_scam(message: str) -> Optional[str]:
    """
    Verifica se a mensagem contém padrões de golpe financeiro.
    Executado ANTES do LLM para evitar que o modelo normalize a fraude.

    Returns:
        String com o alerta se golpe detectado, None caso contrário.
    """
    msg_lower = message.lower()

    for pattern, explanation in SCAM_PATTERNS:
        if pattern in msg_lower:
            return (
                f"⚠️ **ATENÇÃO — Possível golpe financeiro detectado.**\n\n"
                f"O que chamou atenção: *\"{pattern}\"*\n"
                f"{explanation}.\n\n"
                f"**Nenhum investimento regulamentado pela CVM garante retorno fixo acima da Selic.**\n\n"
                f"Antes de qualquer decisão, verifique o registro da empresa em "
                f"[cvm.gov.br](https://www.cvm.gov.br) → Consultas → Prestadores de Serviços.\n\n"
                f"Quer que eu te mostre investimentos legítimos com boa rentabilidade para o seu perfil?"
            )

    # Verifica % ao mês suspeito (acima de 3% ao mês = acima da Selic anual)
    import re
    pct_matches = re.findall(r'(\d+(?:[.,]\d+)?)\s*%\s*ao\s*m[eê]s', msg_lower)
    for match in pct_matches:
        pct = float(match.replace(",", "."))
        if pct >= 3.0:
            annual = round((1 + pct/100) ** 12 - 1, 1) * 100
            return (
                f"⚠️ **ATENÇÃO — Taxa suspeita detectada.**\n\n"
                f"{pct}% ao mês equivale a aproximadamente **{annual:.0f}% ao ano** — "
                f"muito acima da Selic e de qualquer investimento legítimo.\n\n"
                f"**Nenhum produto regulamentado pela CVM garante esse retorno.**\n\n"
                f"Verifique o registro da empresa em [cvm.gov.br](https://www.cvm.gov.br) antes de qualquer decisão."
            )

    return None


# ── Intent classifier (simples, sem LLM) ─────────────────────────────────────

INTENT_KEYWORDS = {
    "simulacao":       ["quanto terei", "simula", "calcul", "investir r$", "guardar por mês",
                        "juros compostos", "quanto preciso", "aposentadoria", "quanto rende"],
    "comparacao":      ["melhor", "ou", "compensa", "vale mais", "diferença entre", "comparar",
                        "lci ou cdb", "cdb ou", "versus", "vs"],
    "analise_gastos":  ["gastei", "gastos", "quanto gastei", "transações", "extrato",
                        "onde estou gastando", "categoria"],
    "alerta_golpe":    ["garantido", "% ao dia", "% ao mês", "robô", "grupo", "whatsapp",
                        "pirâmide", "ponzi", "oportunidade"],
    "perfil":          ["meu perfil", "suitability", "conservador", "moderado", "arrojado",
                        "perfil de investidor", "refazer perfil"],
    "educacional":     ["o que é", "como funciona", "explica", "me explica", "o que são",
                        "diferença", "o que significa"],
    "carteira":        ["minha carteira", "estou bem", "bem alocado", "diversificado",
                        "portfólio", "alocação"],
}

def classify_intent(message: str) -> str:
    """
    Classifica a intenção da mensagem antes de chamar o LLM.
    Roteamento rápido sem consumir tokens.

    Returns:
        String com a intenção: "simulacao" | "comparacao" | "analise_gastos" |
        "alerta_golpe" | "perfil" | "educacional" | "carteira" | "geral"
    """
    msg_lower = message.lower()

    # Prioridade 1: alerta de golpe (sempre verifica primeiro)
    if detect_scam(message):
        return "alerta_golpe"

    # Prioridade 2: simulação (contém valores em R$ e verbos de cálculo)
    for kw in INTENT_KEYWORDS["simulacao"]:
        if kw in msg_lower:
            return "simulacao"

    # Demais intenções por ordem de prioridade
    for intent in ["analise_gastos", "perfil", "carteira", "comparacao", "educacional"]:
        for kw in INTENT_KEYWORDS[intent]:
            if kw in msg_lower:
                return intent

    return "geral"
