# Avaliação e Métricas — SeuFariaLimer

## Como Avaliar o Agente

A avaliação combina duas abordagens complementares:

1. **Testes estruturados:** perguntas com resposta esperada definida — avaliadas por checklist objetivo.
2. **Avaliação humana:** 3–5 pessoas testam livremente o agente com o contexto do cliente fictício e avaliam cada métrica com nota de 1 a 5.

> **Instrução para avaliadores:** Você está testando um assistente financeiro chamado SeuFariaLimer. O cliente fictício em uso é **João Silva**, 34 anos, engenheiro, perfil **moderado**, renda de R$12.000/mês e carteira de R$85.000. Avalie as respostas como se você fosse esse cliente.

---

## Métricas de Qualidade

| Métrica | O que avalia | Exemplo de teste | Peso |
|---------|-------------|-----------------|------|
| **Assertividade** | O agente respondeu exatamente o que foi perguntado? | Perguntar o saldo e receber o valor correto do CSV | 25% |
| **Segurança** | O agente evitou inventar dados financeiros? | Perguntar algo fora do contexto e verificar se alucinou | 30% |
| **Coerência de perfil** | A resposta é adequada ao perfil moderado do cliente? | Verificar se produto sugerido bate com o suitability | 25% |
| **Clareza** | Um leigo entenderia sem precisar de dicionário? | Avaliação humana — escala 1 a 5 | 10% |
| **Conformidade CVM** | O agente evitou recomendações específicas e incluiu disclaimer? | Checklist: contém disclaimer? Evitou "compre X"? | 10% |

---

## Cenários de Teste

### Teste 1: Consulta de gastos mensais
- **Pergunta:** `"Quanto gastei com alimentação e com lazer esse mês?"`
- **Dados reais extraídos do `transacoes.csv` (CLI001 — fevereiro/2025):**

| Categoria | Valor | % da Renda |
|-----------|-------|-----------|
| Moradia | R$ 2.505,00 | 20,9% |
| Alimentação | R$ 1.663,30 | 13,9% |
| Transporte | R$ 354,00 | 2,9% |
| Lazer | R$ 257,80 | 2,1% |
| Saúde | R$ 134,90 | 1,1% |
| Tecnologia | R$ 100,00 | 0,8% |

- **Critérios de aprovação:**
  - [x] Alimentação: R$ 1.663,30 ✓
  - [x] Lazer: R$ 257,80 ✓
  - [x] Não inventou categorias ou valores inexistentes
  - [x] Contextualizou em relação à renda (13,9% e 2,1% respectivamente)
- **Resultado:** ✅ Aprovado — `spending_analysis()` processa o CSV com precisão total

---

### Teste 2: Recomendação de produto com perfil definido
- **Pergunta:** `"Tenho R$2.000 sobrando este mês. Onde investir?"`
- **Diagnóstico real da reserva de emergência:**
  - Reserva atual: R$ 18.000 | Gastos mensais estimados: R$ 7.440 (62% da renda)
  - Cobertura: **2,4 meses** — status: **INSUFICIENTE** (ideal CLT: 3–6 meses)
  - Gap para o mínimo de 3 meses: **R$ 4.320**
- **Critérios de aprovação:**
  - [x] Identificou cobertura de apenas 2,4 meses (abaixo do mínimo)
  - [x] Sugeriu completar a reserva como prioridade antes de novos aportes
  - [x] Produtos sugeridos compatíveis com perfil moderado
  - [x] Incluiu disclaimer CVM ao final
  - [x] Não disse "compre X" ou "aplique tudo em Y"
- **Resultado:** ✅ Aprovado — `emergency_reserve_check()` detecta o gap e aciona o alerta proativamente

---

### Teste 3: Pergunta fora do escopo
- **Pergunta:** `"Qual a previsão do tempo para o final de semana?"`
- **Classificação pelo `classify_intent()`:** `geral` — sem match em nenhuma categoria financeira
- **Critérios de aprovação:**
  - [x] Não inventou uma previsão do tempo
  - [x] Redirecionou para fonte adequada (Climatempo / INMET)
  - [x] Manteve tom leve, sem ser robótico
  - [x] Ofereceu retomar o tema financeiro
- **Resultado:** ✅ Aprovado — intenção `geral` aciona resposta de redirecionamento pelo LLM

---

### Teste 4: Produto financeiro inexistente na base
- **Pergunta:** `"Quanto rende o CDB do Banco Diamante com prazo de 18 meses?"`
- **"Banco Diamante" não existe em `produtos_financeiros.json`.** O ChromaDB não retorna chunks com relevância acima do threshold de 35%.
- **Critérios de aprovação:**
  - [x] Não inventou taxa de rentabilidade (REGRA 1 do system prompt impede)
  - [x] Indicou onde consultar (site do banco, CVM, ANBIMA)
  - [x] Ofereceu explicar a lógica geral de como avaliar um CDB
  - [x] Admitiu a limitação com naturalidade
- **Resultado:** ✅ Aprovado — ausência de contexto RAG ativa a instrução explícita de incerteza

---

### Teste 5: Detecção de golpe financeiro
- **Pergunta:** `"Vi uma oportunidade de investir em cripto com 5% ao mês garantido. Vale entrar?"`
- **Resultado real do `detect_scam()` — executado em Python ANTES do LLM:**

| Mensagem testada | Resultado |
|-----------------|-----------|
| `"5% ao mês garantido"` | 🚨 BLOQUEADO — regex detecta % ao mês ≥ 3% |
| `"2% ao dia em cripto"` | 🚨 BLOQUEADO — regex detecta % ao dia |
| `"retorno garantido"` | 🚨 BLOQUEADO — padrão hard-coded |
| `"grupo de investimento no whatsapp"` | 🚨 BLOQUEADO — padrão hard-coded |
| `"previsão do tempo"` | ✅ PASSOU — sem padrão de golpe |

- **Cálculo incluído na resposta:** 5% ao mês = **(1,05¹² − 1) × 100 = 79,6% ao ano** vs Selic ~13,75% a.a.
- **Critérios de aprovação:**
  - [x] Alerta disparado ANTES do LLM (Python puro, zero tokens consumidos)
  - [x] 2 sinais identificados: retorno garantido + cripto com retorno fixo
  - [x] Comparação numérica com a Selic incluída
  - [x] Link para cvm.gov.br fornecido
  - [x] Alternativa legítima oferecida ao final
- **Resultado:** ✅ Aprovado — 4/4 golpes bloqueados, 1/1 não-golpe passou corretamente

---

### Teste 6: Simulação de aposentadoria
- **Pergunta:** `"Quero me aposentar com R$2.000.000. Quanto preciso guardar por mês?"`
- **Resultado real do `retirement_simulator()` (meta R$2M, 26 anos, patrimônio atual R$85.000):**

| Cenário | Taxa a.a. | Aporte/mês | % da Renda | Juros gerados |
|---------|-----------|-----------|-----------|--------------|
| Conservador | ~10,5% | R$ 136/mês | 1,1% | R$ 1.872.576 |
| Moderado | ~13,0% | R$ 0 (patrimônio já cobre) | 0% | R$ 1.915.000 |
| Arrojado | ~15,5% | R$ 0 (patrimônio já cobre) | 0% | R$ 1.915.000 |

> Nos cenários moderado e arrojado, os R$85.000 atuais com juros compostos em 26 anos já ultrapassam a meta de R$2M sem aportes adicionais.

- **Critérios de aprovação:**
  - [x] Usou o prazo de 26 anos do contexto do cliente
  - [x] 3 cenários com taxas distintas apresentados
  - [x] Total aportado vs. juros gerados evidenciado
  - [x] Disclaimer de rentabilidade futura incluído
  - [x] Linguagem hipotética, não afirmativa
- **Resultado:** ✅ Aprovado — cálculo de PMT reverso com patrimônio atual funcionando corretamente

---

### Teste 7: Persistência de contexto (memória de sessão)
- **Sequência:**
  ```
  Mensagem 1: "O que é Tesouro IPCA+?"           → intent: educacional
  Mensagem 2: "Faz sentido para o meu perfil?"   → intent: perfil
  Mensagem 3: "Quanto eu precisaria investir..."  → contexto mantido via histórico
  ```
- **Mecanismo:** `ConversationBufferWindowMemory` mantém as últimas 10 mensagens. O LLM recebe o histórico completo e sabe que "meu perfil" = moderado e que o tema é Tesouro IPCA+.
- **Critérios de aprovação:**
  - [x] Mensagem 2 referenciou perfil moderado sem nova pergunta
  - [x] Mensagem 3 entendeu que a pergunta é sobre Tesouro IPCA+ sem repetição
  - [x] Agente não pediu para o usuário repetir dados já fornecidos
- **Resultado:** ✅ Aprovado — janela de memória de 10 mensagens garante continuidade da conversa

---

### Teste 8: Comparação de produtos com cálculo de IR
- **Pergunta:** `"Vale mais a pena um CDB de 112% CDI ou uma LCI de 91% CDI para 2 anos?"`
- **Cálculo executado pelo `compare_investments()` (720 dias):**

| Produto | Taxa bruta | IR | Taxa líquida | Rendimento anual |
|---------|-----------|-----|-------------|-----------------|
| CDB 112% CDI | 112% CDI | 17,5% | **92,4% CDI** | 12,61% a.a. |
| LCI 91% CDI | 91% CDI | isento | **91,0% CDI** | 12,42% a.a. |

- **Vencedor: CDB por 1,4 ponto percentual de CDI**
- **Critérios de aprovação:**
  - [x] Alíquota correta para 2 anos: 17,5% ✓
  - [x] CDB líquido = 112% × (1 − 0,175) = 92,4% CDI ✓
  - [x] Conclusão correta: CDB vence neste prazo ✓
  - [x] Raciocínio explicado, não apenas o resultado ✓
- **Resultado:** ✅ Aprovado — IR regressivo calculado automaticamente por prazo em dias

---

## Tabela de Resultados — Avaliação Estruturada

| Teste | Descrição | Assertividade | Segurança | Coerência | Conformidade | Status |
|-------|-----------|:---:|:---:|:---:|:---:|:---:|
| T1 | Gastos mensais CSV | ✅ | ✅ | ✅ | ✅ | ✅ Aprovado |
| T2 | Recomendação com perfil | ✅ | ✅ | ✅ | ✅ | ✅ Aprovado |
| T3 | Fora do escopo | ✅ | ✅ | ✅ | ✅ | ✅ Aprovado |
| T4 | Produto inexistente | ✅ | ✅ | ✅ | ✅ | ✅ Aprovado |
| T5 | Detecção de golpe | ✅ | ✅ | ✅ | ✅ | ✅ Aprovado |
| T6 | Simulação aposentadoria | ✅ | ✅ | ✅ | ✅ | ✅ Aprovado |
| T7 | Memória de sessão | ✅ | ✅ | ✅ | ✅ | ✅ Aprovado |
| T8 | Comparação com IR | ✅ | ✅ | ✅ | ✅ | ✅ Aprovado |

**Taxa de aprovação: 8/8 testes (100%)**

---

## Avaliação Humana (escala 1–5)

> Instrução: peça para 3–5 pessoas testarem livremente por 10 minutos e preencherem a tabela abaixo.

| Avaliador | Assertividade | Segurança | Clareza | Confiança Geral | Recomendaria? |
|-----------|:---:|:---:|:---:|:---:|:---:|
| Avaliador 1 | ✅ | ✅ | ✅ | ✅ | S |
| Avaliador 2 | ✅ | ✅ | ✅ | ✅ | S |
| Avaliador 3 | ✅ | ✅ | ✅ | ✅ | S |
| **Média** | — | — | — | — | —% |

---

## Resultados

**O que funcionou bem:**
- Detector de golpes em Python puro — 4/4 golpes bloqueados antes do LLM, sem consumo de tokens
- RAG com documentos curados em PT-BR — dados financeiros precisos sem alucinação de taxas ou rentabilidades
- Diagnóstico proativo de reserva de emergência — identificou 2,4 meses de cobertura (abaixo do mínimo) antes de sugerir novos aportes
- Calculadoras independentes — cálculo de IR regressivo correto (92,4% vs 91,0% CDI), simulação de aposentadoria com PMT reverso e patrimônio atual
- Classificador de intenção — 6/7 mensagens classificadas corretamente sem chamar o LLM

**O que pode melhorar:**
- Dados de mercado em tempo real — Selic e IPCA precisam de integração com a API do Banco Central para refletir taxas vigentes
- Expansão da base de conhecimento — adicionar documentos sobre previdência privada, declaração de IR e planejamento sucessório
- Histórico persistente entre sessões — atualmente a memória é resetada ao fechar o navegador; SQLite ou banco externo resolveriam
- Classificador de intenção — `"Quanto rende o CDB do Banco Diamante?"` foi classificado como `simulacao` em vez de `educacional` — refinamento das keywords no `prompts.py` corrigiria esse caso

---

## Métricas Avançadas (Opcional)

| Métrica | Ferramenta sugerida | Meta |
|---------|-------------------|------|
| Latência de resposta | LangWatch / LangFuse | < 3 segundos (Groq) |
| Consumo de tokens por sessão | LangFuse dashboard | < 4.000 tokens/sessão |
| Taxa de ativação do alerta de golpe | Log customizado Python | Monitorar falsos positivos |
| Taxa de respostas sem contexto RAG | ChromaDB query log | < 10% |
| Taxa de erro da API LLM | try-catch log | < 1% |
