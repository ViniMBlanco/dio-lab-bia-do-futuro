# Base de Conhecimento — SeuFariaLimer
> Versão 1.0 | Projeto: Consultor de Investimentos com IA Generativa

---

## Dados Utilizados

| Arquivo | Formato | Utilização no Agente |
|---------|---------|---------------------|
| `data/perfil_investidor.json` | JSON | Fonte primária de personalização. Carregado no início de cada sessão para montar o bloco de contexto do cliente: perfil de risco, metas, carteira atual, saldo disponível e histórico de suitability. Determina quais produtos e categorias o agente pode ou não mencionar. |
| `data/produtos_financeiros.json` | JSON | Catálogo de referência de produtos financeiros com rentabilidade, liquidez, garantias, tributação e campo `perfis_adequados`. Usado para filtrar dinamicamente quais produtos apresentar conforme o perfil do cliente. Também contém a lista `alertas_golpe`, injetada fixamente no system prompt. |
| `data/historico_atendimento.csv` | CSV | Contextualiza interações anteriores do cliente: produtos já consultados, intenções recorrentes e nível de satisfação. Permite continuidade de conversa ("você perguntou sobre FIIs em novembro — quer retomar?") e alimenta o classificador de intenção com padrões reais de uso. |
| `data/transacoes.csv` | CSV | Analisar padrão de gastos mensais do cliente por categoria (alimentação, moradia, lazer, investimentos). Carregado sob demanda — apenas quando a intenção classificada é `analise_carteira` ou `planejamento`. Permite ao agente contextualizar capacidade de aporte ("você investiu R$2.420 este mês — equivale a 37% da sua renda"). |

> **Sobre datasets públicos (Hugging Face):** Os dados foram construídos localmente para garantir aderência ao contexto regulatório brasileiro (CVM, ANBIMA, tributação IR, FGC). Para expansão futura da base de Q&A, os datasets [`financial-qa-10K`](https://huggingface.co/datasets/virattt/financial-qa-10K) e [`FinanceBench`](https://huggingface.co/datasets/PatronusAI/financebench) do Hugging Face são compatíveis com a arquitetura RAG do projeto, desde que o conteúdo seja validado e traduzido/adaptado para o contexto brasileiro antes da vetorização.

---

## Adaptações nos Dados

Os arquivos foram criados do zero — não havia dados pré-existentes. As decisões de design foram:

**`perfil_investidor.json`**
Expandido além do mínimo necessário para cobrir os requisitos de suitability da **Resolução CVM nº 30/2021**: além do tipo de perfil (conservador/moderado/arrojado), cada cliente tem `score` numérico (0–100), `respostas_suitability` com as 6 dimensões regulatórias (objetivo, prazo, reação a perdas, experiência prévia, percentual de renda investível e tolerância máxima a perdas) e `data_avaliacao` para controle de validade do perfil.

A carteira atual foi detalhada por classe de ativo (não apenas o total) para permitir análise de diversificação sem necessidade de cálculos externos. Foram criados 3 clientes com perfis intencionalmente distintos — cobrindo os três arquétipos do público-alvo definido no Documento 1.

**`produtos_financeiros.json`**
Adicionados campos que não existem em catálogos padrão de mercado, mas são essenciais para a lógica do agente:
- `perfis_adequados` (array): permite filtragem automática por perfil sem lógica adicional
- `uso_recomendado`: enum que faz matching direto com os objetivos do cliente (ex: `"reserva_emergencia"` → Tesouro Selic)
- `observacoes`: texto educacional em linguagem acessível, reaproveitado diretamente no prompt do LLM

A seção `alertas_golpe` foi separada dos produtos como uma lista independente, para que possa ser injetada no system prompt sem misturar com o catálogo de produtos.

**`historico_atendimento.csv`**
Campo `intencao` adicionado com categorias controladas (`duvida_produto`, `simulacao`, `suitability`, `comparacao`, `alerta_golpe`, `analise_carteira`, `planejamento`). Esse campo espelha as categorias do classificador de intenção do agente, criando consistência entre os dados históricos e o roteamento em tempo real.

**`transacoes.csv`**
Transações de investimento (aportes, dividendos, compra de ativos) foram incluídas intencionalmente como uma categoria própria (`investimento`), para que o agente possa reconhecer e reforçar comportamentos financeiros positivos — não apenas analisar gastos.

---

## Estratégia de Integração

### Como os dados são carregados?

O carregamento segue uma estratégia de **duas velocidades**, equilibrando performance e relevância:

**Carregamento de sessão (eager loading) — uma vez por sessão**
Os dados leves e sempre necessários são carregados na inicialização da sessão, antes da primeira mensagem do usuário:

```python
def load_session_context(client_id: str) -> dict:
    """
    Carrega perfil do cliente e produtos compatíveis no início da sessão.
    Esses dados são incluídos em TODA interação — ficam no context block.
    """
    # 1. Perfil completo do cliente
    with open("data/perfil_investidor.json") as f:
        perfis = json.load(f)["clientes"]
    cliente = next(c for c in perfis if c["id"] == client_id)

    # 2. Produtos filtrados pelo perfil (reduz tokens enviados ao LLM)
    with open("data/produtos_financeiros.json") as f:
        catalogo = json.load(f)
    perfil_tipo = cliente["perfil"]["tipo"].lower()
    produtos = [p for p in catalogo["produtos"]
                if perfil_tipo in p["perfis_adequados"]]
    alertas = catalogo["alertas_golpe"]

    # 3. Últimas 5 interações do histórico (para continuidade)
    historico = (pd.read_csv("data/historico_atendimento.csv")
                   .query(f"id_cliente == '{client_id}'")
                   .sort_values("data", ascending=False)
                   .head(5)
                   .to_dict("records"))

    return {
        "cliente": cliente,
        "produtos_adequados": produtos,
        "alertas_golpe": alertas,
        "historico_recente": historico,
    }
```

**Carregamento sob demanda (lazy loading) — apenas quando necessário**
Os dados pesados (transações) são carregados e agregados somente quando a intenção classificada exige análise financeira — evitando tokens desnecessários na maioria das interações:

```python
def load_spending_summary(client_id: str) -> dict:
    """
    Carregado APENAS quando intenção = 'analise_carteira' ou 'planejamento'.
    """
    df = pd.read_csv("data/transacoes.csv")
    df_cliente = df[df["id_cliente"] == client_id]

    gastos_por_categoria = (df_cliente[df_cliente["tipo"] == "debito"]
                             .groupby("categoria")["valor"]
                             .sum().abs().to_dict())
    total_investido = abs(df_cliente[df_cliente["categoria"] == "investimento"]
                          ["valor"].sum())
    saldo_atual = df_cliente["saldo_apos"].iloc[-1]

    return {
        "gastos_por_categoria": gastos_por_categoria,
        "total_investido_mes": total_investido,
        "saldo_atual": saldo_atual,
        "percentual_investido": round(
            total_investido / cliente["renda_mensal"] * 100, 1
        ),
    }
```

---

### Como os dados são usados no prompt?

O prompt enviado ao LLM é montado em **três camadas empilhadas**, cada uma com origem e função distintas:

```
┌─────────────────────────────────────────────────────────┐
│  CAMADA 1 — SYSTEM PROMPT (fixo por sessão)             │
│  Origem: código hard-coded + alertas_golpe do JSON      │
│  Conteúdo: persona, regras de comportamento,            │
│            limitações CVM, alertas de golpe             │
│  Atualização: nunca muda durante a sessão               │
└─────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────┐
│  CAMADA 2 — CONTEXT BLOCK (dinâmico por sessão)         │
│  Origem: perfil_investidor.json + produtos_financeiros  │
│           + historico_atendimento.csv                   │
│  Conteúdo: dados do cliente, carteira atual, metas,     │
│            produtos compatíveis, últimas interações     │
│  Atualização: reconstruído a cada nova sessão           │
└─────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────┐
│  CAMADA 3 — RAG CONTEXT (dinâmico por mensagem)         │
│  Origem: ChromaDB ← documentos .md vetorizados          │
│  Conteúdo: 3–4 trechos dos docs financeiros mais        │
│            relevantes para a pergunta atual             │
│  Atualização: reconsultado a cada mensagem              │
└─────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────┐
│  HISTÓRICO DE CONVERSA (últimas 10 mensagens)           │
│  Origem: LangChain ConversationBufferWindowMemory       │
└─────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────┐
│  MENSAGEM ATUAL DO USUÁRIO                              │
└─────────────────────────────────────────────────────────┘
```

**Regra de ouro:** o LLM nunca recebe apenas a pergunta do usuário. Sempre recebe contexto estruturado das camadas 1, 2 e 3 antes de processar qualquer mensagem. Isso é o que diferencia respostas genéricas de respostas verdadeiramente personalizadas — e é o que reduz alucinações a quase zero em dados financeiros.

---

## Exemplo de Contexto Montado

O exemplo abaixo mostra o contexto real enviado ao LLM quando **João Silva** pergunta *"Tenho R$5.200 disponíveis. Faz sentido aumentar minha posição em FIIs agora?"*

---

```
=== SYSTEM PROMPT ===
Você é o SeuFariaLimer, um assistente educacional de investimentos pessoais.
Fale como um amigo que entende de finanças — sem jargão desnecessário, sem
julgamento, com paciência e embasamento real.

REGRAS INEGOCIÁVEIS:
• Nunca recomende a compra ou venda de um ativo específico (Resolução CVM nº 20/2021)
• Nunca projete ou garanta rentabilidade futura
• Se a informação não estiver no contexto fornecido, diga que não sabe
• Toda resposta sobre produto financeiro deve encerrar com o disclaimer abaixo

DISCLAIMER OBRIGATÓRIO:
"⚠️ Sou uma IA educacional. Para decisões de investimento, consulte um
assessor certificado CVM/ANBIMA."

ALERTAS DE GOLPE — verifique SEMPRE se a pergunta envolve:
• Rentabilidade garantida acima da Selic
• Pressão para investir rapidamente
• Empresa sem registro CVM ou Banco Central
• Recrutamento de novos investidores como fonte de ganho
• Retorno de 1% ao dia ou mais
• Operações em criptomoedas com retorno garantido
Se identificar qualquer um desses padrões, responda com alerta de segurança
antes de qualquer outra coisa.

=== CONTEXTO DO CLIENTE ===
Nome: João Silva | Idade: 34 anos | Profissão: Engenheiro de Software
Perfil de Investidor: MODERADO (score 62/100, avaliado em 15/09/2024)
Renda Mensal: R$ 12.000 | Patrimônio Total: R$ 85.000

Carteira atual:
• Reserva de Emergência : R$ 18.000  ⚠️ representa 1,5 meses (ideal: 3–6)
• Tesouro Selic         : R$ 22.000
• CDB                   : R$ 15.000
• FII                   : R$  8.000
• Ações                 : R$ 12.000
• Poupança              : R$ 10.000  ⚠️ rendimento abaixo do Tesouro Selic

Metas:
1. Aposentadoria → R$ 1.500.000 em 26 anos (prioridade: ALTA)
2. Viagem internacional → R$ 25.000 em 2 anos (prioridade: MÉDIA)

Saldo disponível: R$ 5.200
Interações recentes: CDB vs LCI (out/24), FIIs e dividendos (nov/24),
                     simulação de aportes mensais (fev/25)

Produtos compatíveis com perfil MODERADO:
• Tesouro IPCA+ 2035 : IPCA + 6,8% a.a. | Venc. 2035 | Mín. R$30 | Gov. Federal
• LCI Bradesco       : 92% CDI | isento IR | 90 dias | FGC R$250k
• BOVA11 (ETF)       : replica Ibovespa | taxa 0,10% a.a. | D+2
• IVVB11 (ETF)       : replica S&P500 | taxa 0,24% a.a. | D+2
• MXRF11 (FII)       : DY ref. ~12,5% a.a. | dividendos isentos IR | D+2
• BRCO11 (FII)       : DY ref. ~9,8% a.a. | dividendos isentos IR | D+2

=== CONHECIMENTO FINANCEIRO (RAG — ChromaDB) ===
[Fonte 1 | FIIs — Renda Variável | Relevância: 94%]
FII é um fundo que investe em imóveis ou títulos relacionados a imóveis.
Ao comprar cotas, você se torna "dono" de uma fração de shoppings, galpões
logísticos, lajes corporativas etc. Os FIIs são obrigados por lei a distribuir
95% do lucro. Na prática, a maioria paga mensalmente — e os rendimentos são
isentos de IR para pessoa física...

[Fonte 2 | FIIs — Renda Variável | Relevância: 89%]
Dividend Yield (DY): quanto o FII distribui em relação ao preço da cota.
Referência saudável em 2024/2025: 8% a 12% ao ano. P/VP < 1 indica cota
negociada com desconto em relação ao patrimônio do fundo...

[Fonte 3 | FAQ | Relevância: 82%]
Vale a pena investir em FIIs para renda passiva? Para R$2.000/mês de renda
passiva com DY médio de 10% a.a. (0,83%/mês), você precisaria de aprox.
R$240.000 investidos. Riscos: vacância dos imóveis, aumento da Selic
(que torna renda fixa mais competitiva), má gestão do fundo...

=== HISTÓRICO DA CONVERSA ===
[Nova sessão — sem mensagens anteriores]

=== PERGUNTA DO USUÁRIO ===
"Tenho R$5.200 disponíveis. Faz sentido aumentar minha posição em FIIs agora?"
```

---

**Resposta esperada do SeuFariaLimer com esse contexto:**

> "Boa pergunta, João! Antes de pensar em aumentar FIIs, deixa eu te mostrar um ponto importante que aparece na sua carteira:
>
> Sua reserva de emergência está em R$18.000 — equivale a **1,5 meses** da sua renda. O ideal para um CLT com estabilidade é ter pelo menos 3 meses (R$36.000). Isso significa que, tecnicamente, você ainda está **R$18.000 abaixo do colchão de segurança ideal** antes de expandir renda variável.
>
> Dito isso, se você já se sente confortável com o nível atual da reserva e entende o risco, FIIs fazem sentido para o seu perfil moderado. Com R$5.200, algumas opções dentro da sua lista de produtos compatíveis rendem dividendos mensais isentos de IR — o que é uma vantagem real no longo prazo.
>
> Quer que eu faça uma simulação de quanto esses R$5.200 renderiam em dividendos mensais com os FIIs do seu catálogo? Ou prefere primeiro a gente avaliar se compensa completar a reserva de emergência?
>
> ⚠️ *Sou uma IA educacional. Para decisões de investimento, consulte um assessor certificado CVM/ANBIMA.*"
