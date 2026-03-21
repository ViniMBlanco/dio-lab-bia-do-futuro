"""
agent.py
========
Orquestrador principal do SeuFariaLimer.

Responsabilidades:
    1. Carregar contexto do cliente (JSON/CSV) na inicialização
    2. Classificar a intenção de cada mensagem
    3. Buscar contexto RAG no ChromaDB quando necessário
    4. Executar calculadoras quando intenção = simulação
    5. Chamar o LLM (Groq) com o contexto completo montado
    6. Manter memória de sessão (últimas 10 trocas)
    7. Injetar disclaimer automático quando necessário

Uso:
    agent = SeuFariaLimerAgent(client_id="CLI001")
    response = agent.chat("O que é Tesouro Selic?")
    print(response)
"""

import os
import json
import re
import pandas as pd
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

from groq import Groq

from core.prompts import (
    SYSTEM_PROMPT, build_context, build_messages,
    detect_scam, classify_intent
)
from core.calculators import (
    compound_interest, retirement_simulator,
    compare_investments, lci_lca_equivalence,
    spending_analysis, emergency_reserve_check
)

load_dotenv()

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE_DIR  = Path(__file__).parent.parent
DATA_DIR  = BASE_DIR / "data"
KB_DIR    = BASE_DIR / "knowledge_base"

DISCLAIMER = (
    "\n\n---\n⚠️ *Sou uma IA educacional. Para decisões de investimento, "
    "consulte um assessor certificado pela CVM/ANBIMA. "
    "Rentabilidade passada não garante resultado futuro.*"
)

PRODUCTS_TRIGGER = [
    "tesouro", "cdb", "lci", "lca", "fii", "etf", "ações", "acoes",
    "bova11", "ivvb11", "mxrf11", "poupança", "poupanca", "pgbl", "vgbl",
    "renda fixa", "renda variável", "investimento", "produto"
]


class SeuFariaLimerAgent:
    """
    Agente principal do SeuFariaLimer.
    Instanciar uma vez por sessão de usuário.
    """

    def __init__(self, client_id: str = "CLI001", use_rag: bool = True):
        self.client_id = client_id
        self.use_rag   = use_rag
        self.history: list[dict] = []   # Memória de sessão
        self.max_history = 20           # Máximo de mensagens no histórico (10 trocas)

        # Inicializa cliente Groq
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError(
                "GROQ_API_KEY não encontrada.\n"
                "Crie o arquivo .env com: GROQ_API_KEY=gsk_sua_chave\n"
                "Obtenha gratuitamente em: https://console.groq.com/keys"
            )
        self.llm = Groq(api_key=api_key)
        self.model = "llama-3.3-70b-versatile"

        # Carrega dados do cliente
        self.client        = None
        self.products      = []
        self.scam_alerts   = []
        self.transactions  = []
        self._load_client_data()

        # Inicializa RAG retriever
        self.retriever = None
        if use_rag:
            self._init_retriever()

        print(f"✅ SeuFariaLimer inicializado para: {self.client.get('nome', client_id)}")
        print(f"   Perfil: {self.client.get('perfil', {}).get('tipo', 'N/A')}")
        print(f"   RAG: {'ativo' if self.retriever else 'desativado'}")

    # ── Data loading ──────────────────────────────────────────────────────────

    def _load_client_data(self):
        """Carrega perfil, produtos filtrados e transações."""
        # Perfil do cliente
        perfil_path = DATA_DIR / "perfil_investidor.json"
        with open(perfil_path, encoding="utf-8") as f:
            all_profiles = json.load(f)["clientes"]
        self.client = next(
            (c for c in all_profiles if c["id"] == self.client_id),
            all_profiles[0]
        )

        # Produtos filtrados pelo perfil
        produtos_path = DATA_DIR / "produtos_financeiros.json"
        with open(produtos_path, encoding="utf-8") as f:
            catalog = json.load(f)
        perfil_tipo = self.client.get("perfil", {}).get("tipo", "").lower()
        self.products = [
            p for p in catalog["produtos"]
            if perfil_tipo in p.get("perfis_adequados", [])
        ]
        self.scam_alerts = catalog.get("alertas_golpe", [])

        # Transações (lazy — carrega mas não processa agora)
        trx_path = DATA_DIR / "transacoes.csv"
        if trx_path.exists():
            df = pd.read_csv(trx_path)
            self.transactions = (
                df[df["id_cliente"] == self.client_id]
                .to_dict("records")
            )

    def _init_retriever(self):
        """Inicializa ChromaDB retriever."""
        try:
            from knowledge_base.retriever import FinMentorRetriever
            self.retriever = FinMentorRetriever(n_results=3, min_relevance=35.0)
        except Exception as e:
            print(f"   ⚠️ RAG indisponível (execute build_knowledge_base.py): {e}")
            self.retriever = None

    # ── Calculator routing ────────────────────────────────────────────────────

    def _run_calculator(self, message: str) -> Optional[str]:
        """
        Extrai parâmetros da mensagem e executa a calculadora correta.
        Retorna resultado formatado ou None se não conseguir extrair.
        """
        msg = message.lower()

        # ── Aposentadoria / meta financeira ───────────────────────────────────
        if any(w in msg for w in ["aposentar", "aposentadoria", "independência financeira"]):
            metas = self.client.get("metas", [])
            meta_apos = next((m for m in metas if "aposentadoria" in m["descricao"].lower()
                              or "independência" in m["descricao"].lower()), None)

            # Tenta extrair valor da mensagem
            valores = re.findall(r'r\$\s*([\d.,]+)', msg)
            if valores:
                target = float(valores[0].replace(".", "").replace(",", "."))
            elif meta_apos:
                target = meta_apos["valor_alvo"]
            else:
                return None

            anos = meta_apos["prazo_anos"] if meta_apos else 20
            renda = self.client.get("renda_mensal", 10000)
            patrimonio = self.client.get("patrimonio_total", 0)

            scenarios = retirement_simulator(target, anos, renda, patrimonio)
            lines = [
                f"🎯 **Meta:** R$ {target:,.0f} em {anos} anos\n"
            ]
            for s in scenarios:
                if s.monthly_contribution == 0:
                    contrib_str = "Patrimônio atual já suficiente!"
                else:
                    contrib_str = f"R$ {s.monthly_contribution:,.0f}/mês ({s.income_pct_of_salary:.1f}% da renda)"
                lines.append(
                    f"**{s.name}** (~{s.annual_rate:.1f}% a.a.)\n"
                    f"  Aporte necessário: {contrib_str}\n"
                    f"  Você coloca: R$ {s.total_invested:,.0f} | Juros geram: R$ {s.total_interest:,.0f}"
                )
            return "\n\n".join(lines)

        # ── Juros compostos / simulação de aporte ─────────────────────────────
        valores = re.findall(r'r\$\s*([\d.,]+)', msg)
        if valores and any(w in msg for w in ["mês", "mes", "mensais", "por mês"]):
            monthly = float(valores[0].replace(".", "").replace(",", "."))
            initial = 0
            if len(valores) > 1:
                initial = float(valores[1].replace(".", "").replace(",", "."))

            # Extrai anos
            anos_match = re.search(r'(\d+)\s*anos?', msg)
            years = int(anos_match.group(1)) if anos_match else 10
            months = years * 12

            lines = [f"📈 **Simulação:** R$ {monthly:,.0f}/mês por {years} anos\n"]
            for name, rate in [("Conservador", 10.5), ("Moderado", 13.0), ("Arrojado", 15.5)]:
                r = compound_interest(initial, monthly, rate, months, include_ir=True, days_for_ir=months*30)
                lines.append(
                    f"**{name}** (~{rate}% a.a.)\n"
                    f"  Montante final: R$ {r.final_amount:,.0f}\n"
                    f"  Você coloca: R$ {r.total_invested:,.0f} | Juros geram: R$ {r.total_interest:,.0f} ({r.interest_ratio:.0f}% do total)"
                )
            return "\n\n".join(lines)

        # ── Comparação LCI vs CDB ─────────────────────────────────────────────
        if "lci" in msg or "lca" in msg:
            pcts = re.findall(r'(\d+(?:[.,]\d+)?)\s*%', msg)
            if len(pcts) >= 2:
                rates = [float(p.replace(",", ".")) for p in pcts[:2]]
                dias_match = re.search(r'(\d+)\s*(?:dias?|meses?|anos?)', msg)
                if dias_match:
                    n = int(dias_match.group(1))
                    unit = dias_match.group(0)
                    days = n * 30 if "mes" in unit else n * 365 if "ano" in unit else n
                else:
                    days = 365

                products_to_compare = [
                    {"name": f"LCI/LCA {rates[0]}% CDI", "pct_cdi": rates[0], "is_exempt": True},
                    {"name": f"CDB {rates[1]}% CDI",      "pct_cdi": rates[1], "is_exempt": False},
                ]
                comps = compare_investments(products_to_compare, days)
                winner = next(c for c in comps if c.winner)
                loser  = next(c for c in comps if not c.winner)

                return (
                    f"⚖️ **Comparação para {days} dias (IR: {comps[1].ir_rate}% no CDB):**\n\n"
                    f"**{winner.name}** → {winner.net_rate_pct_cdi:.1f}% CDI líquido ({winner.net_annual_yield_pct:.2f}% a.a.) ✅\n"
                    f"**{loser.name}**  → {loser.net_rate_pct_cdi:.1f}% CDI líquido ({loser.net_annual_yield_pct:.2f}% a.a.)\n\n"
                    f"**Vencedor: {winner.name}** por {winner.net_rate_pct_cdi - loser.net_rate_pct_cdi:.1f} ponto percentual de CDI."
                )

        return None

    # ── Spending analysis ─────────────────────────────────────────────────────

    def _get_spending_summary(self) -> Optional[dict]:
        if not self.transactions:
            return None
        analysis = spending_analysis(
            self.transactions,
            self.client.get("renda_mensal", 10000)
        )
        return {
            "categories":      analysis.categories,
            "total_expenses":  analysis.total_expenses,
            "total_income":    analysis.total_income,
            "total_invested":  analysis.total_invested,
            "investment_rate": analysis.investment_rate,
            "alerts":          analysis.alerts,
        }

    # ── Main chat method ──────────────────────────────────────────────────────

    def chat(self, user_message: str) -> str:
        """
        Processa uma mensagem do usuário e retorna a resposta do agente.

        Fluxo:
        1. Detector de golpe (Python puro, sem LLM)
        2. Classificação de intenção
        3. Executa calculadora se necessário
        4. Busca RAG se necessário
        5. Monta contexto completo
        6. Chama LLM
        7. Injeta disclaimer se necessário
        8. Atualiza histórico
        """

        # ── 1. Detector de golpe ──────────────────────────────────────────────
        scam_alert = detect_scam(user_message)
        if scam_alert:
            self._update_history(user_message, scam_alert)
            return scam_alert

        # ── 2. Classifica intenção ────────────────────────────────────────────
        intent = classify_intent(user_message)

        # ── 3. Calculadora ────────────────────────────────────────────────────
        calculator_result = None
        if intent == "simulacao":
            calculator_result = self._run_calculator(user_message)

        # ── 4. Análise de gastos ──────────────────────────────────────────────
        spending_summary = None
        if intent == "analise_gastos":
            spending_summary = self._get_spending_summary()

        # ── 5. RAG retrieval ──────────────────────────────────────────────────
        rag_context = None
        if self.retriever and intent in ("educacional", "comparacao", "carteira", "geral", "simulacao"):
            try:
                rag_context = self.retriever.get_context_for_llm(user_message)
            except Exception:
                rag_context = None

        # ── 6. Monta contexto ─────────────────────────────────────────────────
        context_block = build_context(
            client=self.client,
            suitable_products=self.products if intent in ("carteira", "comparacao", "geral") else None,
            rag_context=rag_context,
            spending_summary=spending_summary,
            calculator_result=calculator_result,
        )

        # ── 7. Monta mensagens ────────────────────────────────────────────────
        # Contexto só na primeira mensagem da sessão; histórico depois
        if not self.history:
            messages = build_messages(user_message, context_block, history=None)
        else:
            # Contexto já foi injetado; só usa histórico + mensagem atual
            messages = [{"role": "system", "content": SYSTEM_PROMPT}]
            messages.extend(self.history[-self.max_history:])
            if calculator_result or spending_summary:
                # Inclui resultado de calculadora no contexto da mensagem atual
                enriched = f"{user_message}\n\n[Dados calculados automaticamente para sua análise]\n{calculator_result or ''}"
                messages.append({"role": "user", "content": enriched})
            else:
                messages.append({"role": "user", "content": user_message})

        # ── 8. Chama o LLM ────────────────────────────────────────────────────
        try:
            response = self.llm.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.2,
                max_tokens=1024,
            )
            answer = response.choices[0].message.content.strip()
        except Exception as e:
            answer = (
                f"Desculpe, tive um problema ao processar sua mensagem. "
                f"Erro: {str(e)[:100]}\n\n"
                f"Tente novamente em alguns instantes."
            )

        # ── 9. Disclaimer automático ──────────────────────────────────────────
        msg_lower = user_message.lower()
        needs_disclaimer = any(trigger in msg_lower for trigger in PRODUCTS_TRIGGER)
        if needs_disclaimer and DISCLAIMER.strip() not in answer:
            answer += DISCLAIMER

        # ── 10. Atualiza histórico ─────────────────────────────────────────────
        self._update_history(user_message, answer)

        return answer

    def _update_history(self, user_msg: str, assistant_msg: str):
        """Mantém janela deslizante de histórico."""
        self.history.append({"role": "user",      "content": user_msg})
        self.history.append({"role": "assistant",  "content": assistant_msg})
        if len(self.history) > self.max_history:
            self.history = self.history[-self.max_history:]

    def reset(self):
        """Reinicia a conversa mantendo o contexto do cliente."""
        self.history = []
        print("🔄 Conversa reiniciada.")

    def get_profile_summary(self) -> str:
        """Retorna resumo do perfil do cliente atual."""
        if not self.client:
            return "Nenhum cliente carregado."
        p = self.client.get("perfil", {})
        carteira = self.client.get("carteira_atual", {})
        total = sum(carteira.values())
        return (
            f"**{self.client.get('nome')}** | {self.client.get('idade')} anos\n"
            f"Perfil: **{p.get('tipo', 'N/D')}** (score {p.get('score', '—')}/100)\n"
            f"Renda: R$ {self.client.get('renda_mensal', 0):,.0f}/mês\n"
            f"Carteira total: R$ {total:,.0f}\n"
            f"Saldo disponível: R$ {self.client.get('conta', {}).get('saldo_disponivel', 0):,.0f}"
        )


# ── CLI interativo para testes ────────────────────────────────────────────────

if __name__ == "__main__":
    import sys

    print("=" * 55)
    print("  SeuFariaLimer — Modo Interativo")
    print("=" * 55)
    print("Clientes disponíveis: CLI001 (João/Moderado), CLI002 (Ana/Conservador), CLI003 (Lucas/Arrojado)")

    client_id = input("\nID do cliente [CLI001]: ").strip() or "CLI001"

    try:
        agent = SeuFariaLimerAgent(client_id=client_id)
        print(f"\n{agent.get_profile_summary()}")
        print("\nDigite 'sair' para encerrar, 'reset' para nova conversa.\n")

        while True:
            user_input = input("Você: ").strip()
            if not user_input:
                continue
            if user_input.lower() == "sair":
                print("Até logo!")
                break
            if user_input.lower() == "reset":
                agent.reset()
                continue

            response = agent.chat(user_input)
            print(f"\nSeuFariaLimer: {response}\n")

    except ValueError as e:
        print(f"\n❌ Erro de configuração: {e}")
        sys.exit(1)
