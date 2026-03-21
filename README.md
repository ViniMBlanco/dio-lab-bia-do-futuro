# 💼 SeuFariaLimer — Consultor de Investimentos com IA Generativa

## Contexto

Os assistentes virtuais no setor financeiro estão evoluindo de simples chatbots reativos para **agentes inteligentes e proativos**. O **SeuFariaLimer** é um agente financeiro educacional que utiliza IA Generativa para:

- **Democratizar** o acesso à orientação financeira de qualidade para a classe média brasileira
- **Personalizar** respostas com base no perfil de risco e objetivos de cada cliente
- **Simular** cenários de investimento com juros compostos, aposentadoria e comparativos de produtos
- **Proteger** o usuário identificando golpes financeiros automaticamente antes de qualquer resposta
- **Garantir segurança** e confiabilidade via RAG — o agente só responde com base em documentos curados

> O nome é uma brincadeira com o termo popular "Faria Limer" — o especialista do mercado financeiro paulistano. O "Seu" transforma esse conhecimento em algo particular, acessível e do seu lado.

---

## O Que Foi Entregue

### 1. Documentação do Agente

- **Caso de Uso:** Consultoria educacional de investimentos para a classe média brasileira (renda R$3k–R$15k/mês), resolvendo três barreiras: falta de acesso, complexidade dos produtos e medo de golpes
- **Persona:** SeuFariaLimer — fala como um amigo que entende de finanças, sem julgamento e sem jargão desnecessário
- **Arquitetura:** RAG com 3 camadas de contexto (system prompt + dados do cliente + ChromaDB) e roteamento de intenção antes do LLM
- **Segurança:** Detector de golpes em Python puro (antes do LLM), RAG obrigatório para dados financeiros, suitability antes de qualquer produto, disclaimer automático CVM/ANBIMA

📄 [`docs/01-documentacao-agente.md`](./docs/01-documentacao-agente.md)

---

### 2. Base de Conhecimento

Dados mockados na pasta [`data/`](./data/) com contexto brasileiro real:

| Arquivo | Formato | Descrição |
|---------|---------|-----------|
| `transacoes.csv` | CSV | 49 transações de fevereiro/2025 para 3 clientes com categorias de gastos |
| `historico_atendimento.csv` | CSV | 18 interações anteriores com intenção classificada por cliente |
| `perfil_investidor.json` | JSON | 3 perfis completos (Moderado, Conservador, Arrojado) com suitability CVM |
| `produtos_financeiros.json` | JSON | 10 produtos financeiros brasileiros com regras de adequação por perfil |

Além dos dados, a base de conhecimento inclui 5 documentos financeiros curados em PT-BR vetorizados no ChromaDB:

| Documento | Conteúdo |
|-----------|----------|
| `01_perfil_investidor.md` | Suitability: conservador, moderado e arrojado |
| `02_renda_fixa.md` | Tesouro Direto, CDB, LCI, LCA, tributação IR |
| `03_renda_variavel.md` | Ações, ETFs, FIIs, BDRs, criptomoedas |
| `04_conceitos_fundamentais.md` | Juros compostos, reserva de emergência, inflação |
| `05_faq.md` | 15 perguntas frequentes do iniciante ao avançado |

📄 [`docs/02-base-conhecimento.md`](./docs/02-base-conhecimento.md)

---

### 3. Prompts do Agente

- **System Prompt:** Persona + 5 regras inegociáveis (CVM) + detector de golpes + 3 exemplos few-shot + disclaimer obrigatório
- **Exemplos de Interação:** 4 cenários completos (diagnóstico de perfil, análise de carteira, simulação de aposentadoria, alerta de golpe)
- **Edge Cases:** Fora do escopo, dados inexistentes, tentativa de acesso a dados de terceiros, prompt injection

📄 [`docs/03-prompts.md`](./docs/03-prompts.md)

---

### 4. Aplicação Funcional

Interface Streamlit com 4 abas funcionais:

| Aba | Funcionalidade |
|-----|---------------|
| 💬 Chat | Conversa com o agente — RAG + perfil do cliente + memória de sessão + sugestões clicáveis |
| 🧮 Simulações | Juros compostos e simulador de aposentadoria com gráficos Plotly interativos |
| 📊 Gastos | Análise de gastos mensais por categoria com benchmarks e evolução de saldo |
| 📈 Mercado | Taxas de referência, tabela de produtos do perfil e comparador de rentabilidade líquida |

📁 Código na raiz do projeto — veja **Como Rodar** abaixo

---

### 5. Avaliação e Métricas

8 testes estruturados com critérios de aprovação explícitos:

| Teste | O que valida |
|-------|-------------|
| T1 | Consulta de gastos a partir do CSV |
| T2 | Recomendação de produto respeitando o perfil |
| T3 | Redirecionamento de perguntas fora do escopo |
| T4 | Admissão de produto inexistente na base |
| T5 | Detecção de golpe financeiro |
| T6 | Simulação de aposentadoria com dados reais do cliente |
| T7 | Persistência de contexto na memória de sessão |
| T8 | Comparação de CDB vs LCI com cálculo correto de IR |

📄 [`docs/04-metricas.md`](./docs/04-metricas.md)

---

### 6. Pitch

Roteiro de 3 minutos com slides de apoio cobrindo: o problema (Brasileiros não investem por falta de conhecimento), a solução (assessor particular com IA), demonstração dos 3 fluxos principais e diferencial técnico (RAG + conformidade CVM + stack 100% gratuita).

📄 [`docs/05-pitch.md`](./docs/05-pitch.md)

---

## Ferramentas Utilizadas

| Categoria | Ferramenta |
|-----------|-----------|
| **LLM** | [Groq API](https://console.groq.com/) — Llama 3.3 70B (gratuito, 14.400 req/dia) |
| **Interface** | [Streamlit](https://streamlit.io/) — interface web responsiva |
| **Base Vetorial** | [ChromaDB](https://www.trychroma.com/) — banco vetorial local |
| **Embeddings** | [Sentence Transformers](https://www.sbert.net/) — modelo multilíngue PT-BR |
| **Orquestração** | [LangChain](https://www.langchain.com/) — chunking e pipeline RAG |
| **Gráficos** | [Plotly](https://plotly.com/) — visualizações interativas |
| **Dados de Mercado** | [yfinance](https://pypi.org/project/yfinance/) — cotações em tempo real |

> **Custo total da stack: R$ 0,00/mês** — todas as ferramentas são gratuitas ou open-source.

---

## Estrutura do Repositório

```
📁 dio-lab-bia-do-futuro/
│
├── 📄 README.md                        # Este arquivo
│
├── 📁 data/                            # Dados mockados dos clientes
│   ├── perfil_investidor.json          # 3 perfis com suitability CVM completo
│   ├── produtos_financeiros.json       # 10 produtos com regras de adequação
│   ├── historico_atendimento.csv       # 18 interações classificadas por intenção
│   └── transacoes.csv                  # 49 transações de fev/2025
│
├── 📁 docs/                            # Documentação do desafio
│   ├── 01-documentacao-agente.md       # Caso de uso, persona e arquitetura
│   ├── 02-base-conhecimento.md         # Estratégia de dados e RAG
│   ├── 03-prompts.md                   # System prompt e exemplos de interação
│   ├── 04-metricas.md                  # 8 testes estruturados de avaliação
│   └── 05-pitch.md                     # Roteiro do pitch de 3 minutos
│
├── 📁 core/                            # Lógica principal do agente
│   ├── __init__.py
│   ├── agent.py                        # Orquestrador (Groq + RAG + memória)
│   ├── calculators.py                  # Simulações financeiras (Python puro)
│   └── prompts.py                      # System prompt + detector de golpes
│
├── 📁 knowledge_base/                  # Base de conhecimento RAG
│   ├── build_knowledge_base.py         # Vetoriza documentos no ChromaDB (1x)
│   ├── retriever.py                    # Interface de consulta ao ChromaDB
│   └── documents/                      # 5 documentos financeiros em PT-BR
│
├── 📁 utils/
│   └── market_data.py                  # Cotações via yfinance
│
├── 📁 assets/                          # Imagens e diagramas
│
├── 📄 app.py                           # Aplicação principal (Streamlit)
├── 📄 requirements.txt                 # Dependências Python
├── 📄 .env.example                     # Template de variáveis de ambiente
└── 📄 .gitignore                       # Arquivos ignorados pelo Git
```

---

## Como Rodar

### Pré-requisitos
- Python 3.11 (recomendado — Python 3.14 tem incompatibilidades com algumas libs)
- Conta gratuita no [Groq](https://console.groq.com/keys) para obter a API key

### 1. Clone o repositório

```bash
git clone https://github.com/ViniMBlanco/dio-lab-bia-do-futuro.git
cd dio-lab-bia-do-futuro
```

### 2. Crie e ative o ambiente virtual

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Mac/Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. Instale as dependências

```bash
pip install -r requirements.txt
```

### 4. Configure a API key

Copie o template e preencha com sua chave:

```bash
cp .env.example .env
```

Edite o `.env`:
```
GROQ_API_KEY=gsk_sua_chave_aqui
```

### 5. Construa a base de conhecimento (apenas uma vez)

```bash
cd knowledge_base
python build_knowledge_base.py
cd ..
```

### 6. Rode a aplicação

```bash
streamlit run app.py
```

Acesse em: **http://localhost:8501**

---

## Dicas de Uso

- Troque o **cliente ativo** na sidebar para testar os 3 perfis: João (Moderado), Ana (Conservador), Lucas (Arrojado)
- Use as **sugestões clicáveis** na aba Chat para explorar as funcionalidades rapidamente
- A aba **Simulações** usa os dados reais do cliente selecionado como valores padrão
- Para testar o detector de golpes, pergunte algo como *"vi um investimento pagando 5% ao mês garantido"*

---

## Aviso Legal

O SeuFariaLimer é uma ferramenta de **educação financeira**. As informações fornecidas não constituem recomendação de investimento. Consulte sempre um assessor certificado pela **CVM/ANBIMA** antes de tomar decisões financeiras.