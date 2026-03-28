# Pitch (3 minutos) — SeuFariaLimer

> Os slides de apoio estão disponíveis em [`assets/SeuFariaLimer_Pitch.pptx`](../assets/SeuFariaLimer_Pitch.pptx)

---

## Roteiro Sugerido

### 1. O Problema (30 seg)

> Qual dor do cliente você resolve?

O Brasil tem mais de 217 milhões de pessoas, mas menos de 5 milhões investem ativamente na bolsa — menos de 2,5% da população.

Por quê? Não é falta de dinheiro. É falta de acesso. Assessoria financeira de qualidade é reservada para quem já tem patrimônio. Plataformas como XP e BTG oferecem assessores humanos, mas com foco em clientes com R$100k+. Para quem tem R$500 para começar, a orientação disponível se resume a vídeos genéricos do YouTube feitos por influenciadores com conflito de interesse.

Além do acesso, existem mais duas barreiras: a **complexidade** — CDB, LCI, FII, ETF, PGBL, cada produto com regras de tributação e liquidez diferentes, sem orientação contextualizada — e o **medo**: a proliferação de golpes financeiros torna o ambiente percebido como perigoso e inacessível para quem está começando.

---

### 2. A Solução (1 min)

> Como seu agente resolve esse problema?

O **SeuFariaLimer** — uma brincadeira com o "Faria Limer", o especialista do mercado financeiro paulistano inacessível para a maioria. O "Seu" transforma esse conhecimento em algo particular, próximo e do seu lado.

É um consultor de educação financeira com IA generativa, focado no contexto brasileiro — com Tesouro Direto, CDB, LCI, FII, ETF, regulações CVM e tributação IR. Não é um chatbot genérico.

O agente resolve o problema em quatro frentes:

**Perfil personalizado:** antes de sugerir qualquer produto, faz o diagnóstico de suitability conversacional — conservador, moderado ou arrojado — seguindo as diretrizes da Resolução CVM nº 30/2021. A resposta muda completamente dependendo do perfil.

**Simulações reais:** juros compostos, aposentadoria, comparativo de produtos com desconto correto do imposto de renda. Não é teoria genérica — é o cenário específico do usuário com seus números.

**Análise de gastos:** conecta com o histórico de transações e identifica onde o usuário está gastando acima dos benchmarks recomendados e quanto sobra para investir mensalmente.

**Detector de golpes:** antes de qualquer resposta, o sistema verifica padrões de fraude em Python puro — sem nem chamar o modelo de linguagem. "5% ao mês garantido" é bloqueado imediatamente, com o cálculo: isso equivale a 79,6% ao ano, bem acima da Selic.

---

### 3. Demonstração (1 min)

> Mostre o agente funcionando (pode ser gravação de tela)

A demonstração mostra 3 fluxos em sequência:

**Fluxo 01 — Diagnóstico de Perfil:**
Cliente novo, sem histórico. Usuário digita: *"Tenho R$800 e quero começar a investir."* O agente não responde com uma lista de produtos — ele faz as 5 perguntas de suitability de forma conversacional e, ao final, apresenta apenas os produtos compatíveis com o perfil identificado.

**Fluxo 02 — Simulação de Aposentadoria:**
João Silva, 34 anos, perfil moderado. Usuário pergunta: *"Quero me aposentar com R$2.000.000. Quanto preciso guardar por mês?"* O agente calcula três cenários (conservador, moderado e arrojado) mostrando o aporte mensal necessário, o total que o usuário vai colocar e quanto os juros compostos vão gerar sozinhos ao longo de 26 anos.

**Fluxo 03 — Alerta de Golpe:**
Usuário pergunta: *"Vi um investimento em cripto pagando 5% ao mês garantido. Vale entrar?"* O alerta dispara antes do LLM processar qualquer coisa — identifica dois sinais simultâneos de fraude, faz o cálculo (5%/mês = 79,6%/ano vs. Selic de 13,75%) e direciona para verificação em cvm.gov.br.

---

### 4. Diferencial e Impacto (30 seg)

> Por que essa solução é inovadora e qual é o impacto dela na sociedade?

Três diferenciais técnicos que importam:

**RAG com base de conhecimento curada:** o agente não alucina dados financeiros porque só responde com base em documentos verificados sobre o mercado brasileiro — Tesouro Direto, CDB, FII, ETF, tributação IR, regulações CVM.

**Conformidade CVM por design:** nunca recomenda ativo específico para compra, disclaimer automático em toda resposta sobre produto, suitability obrigatório antes de qualquer sugestão de investimento.

**Stack 100% gratuita:** Groq API, ChromaDB, Streamlit, Sentence Transformers. Custo de infraestrutura zero — democratizando não só o acesso ao conhecimento, mas também a capacidade de construir esse tipo de solução.

O impacto: são 40 milhões de brasileiros da classe média com renda entre R$3 mil e R$15 mil por mês — com capital disponível para investir, mas sem orientação qualificada e acessível. O SeuFariaLimer não substitui um assessor humano certificado. Ele prepara o usuário para essa conversa — mais informado, menos ansioso e menos vulnerável a golpes.

O conhecimento do Faria Lima não precisa mais ser exclusivo.

---

## Checklist do Pitch

- [x] Duração máxima de 3 minutos
- [x] Problema claramente definido — 3 barreiras: acesso, complexidade, confiança
- [x] Solução demonstrada na prática — 3 fluxos: perfil, simulação, alerta de golpe
- [x] Diferencial explicado — RAG curado, conformidade CVM, stack gratuita
- [x] Slides de apoio criados em `.pptx` com paleta visual do projeto
- [x] Áudio e vídeo com boa qualidade
- [x] Gravação de tela do agente funcionando

---

## Link do Vídeo

> Cole aqui o link do seu pitch após a gravação (Google Drive)

https://drive.google.com/file/d/1U4ExQ_LpJBn9VcRILVtY4lLqjS7NO8rx/view?usp=sharing 
