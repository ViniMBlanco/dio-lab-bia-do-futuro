"""
app.py - SeuFariaLimer
Interface principal com Streamlit.
Execute com: streamlit run app.py
"""

import streamlit as st
import json
import os
import sys
import pandas as pd
import plotly.graph_objects as go
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ── Configuração da página ────────────────────────────────────────────────────
st.set_page_config(
    page_title="SeuFariaLimer",
    page_icon="💼",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS personalizado ─────────────────────────────────────────────────────────
st.markdown("""
<style>
    .stApp { background-color: #0f1117; }
    /* Texto geral */
    p, span, div, label { color: #e8eaf0 !important; }

    /* Títulos */
    h1, h2, h3, h4 { color: #ffffff !important; }

    /* Texto secundário/legendas */
    .stCaption, small { color: #8892b0 !important; }

    /* Input e selectbox */
    .stTextInput input, .stSelectbox { color: #e8eaf0 !important; }

    .metric-card {
        background: #1e2235;
        border: 1px solid #2d3555;
        border-radius: 10px;
        padding: 14px 16px;
        margin-bottom: 10px;
    }
    .metric-card .label { font-size: 11px; color: #8892b0; text-transform: uppercase; letter-spacing: 0.8px; }
    .metric-card .value { font-size: 20px; font-weight: 700; color: #e8b84b; }
    .metric-card .sub   { font-size: 12px; color: #a0aab8; margin-top: 2px; }

    .profile-badge {
        background: linear-gradient(135deg, #1a1f3c, #252c54);
        border: 1px solid #e8b84b44;
        border-radius: 10px;
        padding: 16px;
        margin-bottom: 14px;
        text-align: center;
    }
    .profile-badge .name   { font-size: 17px; font-weight: 700; color: #fff; }
    .profile-badge .perfil { font-size: 13px; margin-top: 4px; }

    .disclaimer {
        background: #1a1a2e;
        border-left: 3px solid #e8b84b;
        padding: 8px 12px;
        border-radius: 4px;
        font-size: 11px;
        color: #8892b0;
        margin-top: 8px;
    }

    .stButton > button {
        width: 100%;
        background: #1e2235;
        border: 1px solid #2d3555;
        color: #c8d0e0;
        border-radius: 8px;
        font-size: 12px;
        text-align: left;
        padding: 8px 12px;
    }
    .stButton > button:hover {
        border-color: #e8b84b;
        color: #e8b84b;
    }
</style>
""", unsafe_allow_html=True)

# ── Tema dos gráficos ─────────────────────────────────────────────────────────
PLOT_LAYOUT = dict(
    plot_bgcolor="#1e2235",
    paper_bgcolor="#1e2235",
    font=dict(color="#c8d0e0", size=12),
    margin=dict(l=10, r=10, t=35, b=10),
)

# ── Session state ─────────────────────────────────────────────────────────────
for key, default in [("agent", None), ("messages", []), ("client_id", "CLI001"), ("initialized", False)]:
    if key not in st.session_state:
        st.session_state[key] = default

# ── Carregamento de dados ─────────────────────────────────────────────────────
@st.cache_data
def load_clients():
    path = Path("data/perfil_investidor.json")
    if not path.exists():
        st.error("Arquivo data/perfil_investidor.json não encontrado.")
        return []
    with open(path, encoding="utf-8") as f:
        return json.load(f)["clientes"]

@st.cache_data
def load_products():
    path = Path("data/produtos_financeiros.json")
    if not path.exists():
        return [], []
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return data["produtos"], data.get("alertas_golpe", [])

@st.cache_data
def load_transactions(client_id: str):
    path = Path("data/transacoes.csv")
    if not path.exists():
        return pd.DataFrame()
    df = pd.read_csv(path)
    return df[df["id_cliente"] == client_id].copy()

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style='text-align:center; padding:8px 0 16px 0;'>
        <span style='font-size:30px'>💼</span>
        <div style='font-size:22px; font-weight:800; color:#fff;'>
            Seu<span style='color:#e8b84b;'>FariaLimer</span>
        </div>
        <div style='font-size:11px; color:#8892b0; margin-top:2px;'>
            Consultor de Investimentos com IA
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Seleção de cliente
    clients = load_clients()
    if not clients:
        st.stop()

    client_map = {c["id"]: f"{c['nome']} — {c['perfil']['tipo']}" for c in clients}
    selected_id = st.selectbox(
        "Cliente ativo",
        options=list(client_map.keys()),
        format_func=lambda x: client_map[x],
    )

    # Reseta se mudou de cliente
    if selected_id != st.session_state.client_id:
        st.session_state.client_id = selected_id
        st.session_state.agent = None
        st.session_state.messages = []
        st.session_state.initialized = False

    client = next((c for c in clients if c["id"] == selected_id), None)

    if client:
        perfil   = client.get("perfil", {})
        carteira = client.get("carteira_atual", {})
        conta    = client.get("conta", {})
        renda    = client.get("renda_mensal", 0)
        total    = sum(carteira.values())

        # Badge de perfil
        pcolors = {"Conservador": "#10b981", "Moderado": "#3b82f6", "Arrojado": "#f59e0b"}
        pc = pcolors.get(perfil.get("tipo", ""), "#8892b0")
        st.markdown(f"""
        <div class='profile-badge'>
            <div class='name'>{client['nome']}</div>
            <div class='perfil' style='color:{pc};'>
                ● {perfil.get('tipo', 'N/D')} — Score {perfil.get('score', '—')}/100
            </div>
        </div>""", unsafe_allow_html=True)

        # Métricas
        col1, col2 = st.columns(2)
        col1.markdown(f"""<div class='metric-card'>
            <div class='label'>Renda</div>
            <div class='value'>R$ {renda/1000:.0f}k</div>
        </div>""", unsafe_allow_html=True)
        col2.markdown(f"""<div class='metric-card'>
            <div class='label'>Saldo livre</div>
            <div class='value'>R$ {conta.get('saldo_disponivel', 0):,.0f}</div>
        </div>""", unsafe_allow_html=True)

        st.markdown(f"""<div class='metric-card'>
            <div class='label'>Patrimônio total</div>
            <div class='value'>R$ {total:,.0f}</div>
            <div class='sub'>{len(carteira)} classes de ativos</div>
        </div>""", unsafe_allow_html=True)

        # Mini gráfico de carteira
        if carteira:
            fig = go.Figure(go.Pie(
                labels=[k.replace("_", " ").title() for k in carteira.keys()],
                values=list(carteira.values()),
                hole=0.55,
                marker_colors=["#e8b84b","#3b82f6","#10b981","#f59e0b","#8b5cf6","#ef4444"],
                textinfo="percent",
                textfont=dict(size=10),
            ))
            fig.update_layout(**PLOT_LAYOUT, height=220, showlegend=False,
                              title=dict(text="Carteira", font=dict(size=12, color="#8892b0")))
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

        # Metas
        with st.expander("🎯 Metas", expanded=False):
            for m in client.get("metas", []):
                ic = "🟢" if m["prioridade"] == "alta" else "🟡"
                st.markdown(
                    f"{ic} **{m['descricao']}**  \n"
                    f"R$ {m['valor_alvo']:,.0f} em {m['prazo_anos']} anos"
                )

    st.divider()

    if st.button("🔄 Nova conversa", use_container_width=True):
        st.session_state.messages = []
        if st.session_state.agent:
            st.session_state.agent.reset()
        st.rerun()

    st.markdown("""<div class='disclaimer'>
        ⚠️ Ferramenta educacional. Não substitui assessor certificado CVM/ANBIMA.
        Rentabilidade passada não garante resultado futuro.
    </div>""", unsafe_allow_html=True)


# ── Área principal ────────────────────────────────────────────────────────────
st.markdown("""
<div style='padding:8px 0 18px 0; border-bottom:1px solid #2d3555; margin-bottom:20px;'>
    <span style='font-size:22px; font-weight:800; color:#fff;'>
        Seu<span style='color:#e8b84b;'>FariaLimer</span>
    </span>
    <span style='font-size:13px; color:#8892b0; margin-left:12px;'>
        Consultor de investimentos com IA — contexto brasileiro
    </span>
</div>
""", unsafe_allow_html=True)

tab_chat, tab_simulacao, tab_gastos, tab_mercado = st.tabs([
    "💬  Chat",
    "🧮  Simulações",
    "📊  Gastos",
    "📈  Mercado",
])


# ════════════════════════════════════════════════════════════════════════
# ABA 1 — CHAT
# ════════════════════════════════════════════════════════════════════════
with tab_chat:

    # Inicializa o agente
    if not st.session_state.initialized:
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            st.error(
                "**Chave da API não encontrada.**\n\n"
                "Crie o arquivo `.env` na raiz do projeto com:\n"
                "```\nGROQ_API_KEY=gsk_sua_chave_aqui\n```\n"
                "Obtenha gratuitamente em: https://console.groq.com/keys"
            )
            st.stop()

        with st.spinner("Inicializando SeuFariaLimer..."):
            try:
                sys.path.insert(0, str(Path(__file__).parent))
                from core.agent import SeuFariaLimerAgent
                st.session_state.agent = SeuFariaLimerAgent(
                    client_id=st.session_state.client_id,
                    use_rag=True,
                )
                st.session_state.initialized = True

                nome = client["nome"].split()[0] if client else "você"
                tipo = client["perfil"]["tipo"] if client else ""
                welcome = (
                    f"Olá, **{nome}**! 👋 Sou o SeuFariaLimer — seu consultor de investimentos com IA.\n\n"
                    f"Seu perfil é **{tipo}**. Posso te ajudar com:\n"
                    f"- 📚 Explicar produtos financeiros (Tesouro, CDB, FII, ETF...)\n"
                    f"- 🧮 Simular investimentos e aposentadoria\n"
                    f"- 📊 Analisar seus gastos mensais\n"
                    f"- 🛡️ Identificar golpes financeiros\n\n"
                    f"Por onde você quer começar?"
                )
                st.session_state.messages.append({"role": "assistant", "content": welcome})

            except Exception as e:
                st.error(f"Erro ao inicializar o agente: {e}")
                st.stop()

    # Sugestões de perguntas (só quando o chat está no início)
    if len(st.session_state.messages) <= 1:
        st.markdown("##### 💡 Sugestões")
        suggestions = [
            "O que é Tesouro Selic e por que é melhor que a poupança?",
            "Simule R$ 500/mês investidos por 20 anos",
            "Quanto guardar por mês para aposentar com R$ 1.500.000?",
            "Analise meus gastos do mês",
            "LCI 92% CDI ou CDB 110% CDI para 1 ano?",
            "Vi cripto pagando 5% ao mês garantido — é confiável?",
        ]
        cols = st.columns(3)
        for i, s in enumerate(suggestions):
            with cols[i % 3]:
                if st.button(s, key=f"sug_{i}"):
                    st.session_state.messages.append({"role": "user", "content": s})
                    with st.spinner("Pensando..."):
                        resp = st.session_state.agent.chat(s)
                    st.session_state.messages.append({"role": "assistant", "content": resp})
                    st.rerun()
        st.divider()

    # Histórico de mensagens
    for msg in st.session_state.messages:
        avatar = "💼" if msg["role"] == "assistant" else "👤"
        with st.chat_message(msg["role"], avatar=avatar):
            st.markdown(msg["content"])

    # Input do usuário
    if prompt := st.chat_input("Pergunte sobre investimentos, simule cenários ou analise seus gastos..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user", avatar="👤"):
            st.markdown(prompt)

        with st.chat_message("assistant", avatar="💼"):
            with st.spinner(""):
                if st.session_state.agent:
                    response = st.session_state.agent.chat(prompt)
                else:
                    response = "Agente não inicializado. Verifique a chave da API."
            st.markdown(response)

        st.session_state.messages.append({"role": "assistant", "content": response})
        st.rerun()


# ════════════════════════════════════════════════════════════════════════
# ABA 2 — SIMULAÇÕES
# ════════════════════════════════════════════════════════════════════════
with tab_simulacao:
    st.markdown("##### Simule cenários com seus dados reais")

    tipo_sim = st.radio(
        "Tipo de simulação",
        ["📈  Juros compostos", "🎯  Meta de aposentadoria"],
        horizontal=True,
    )
    st.divider()

    if tipo_sim == "📈  Juros compostos":
        c1, c2, c3 = st.columns(3)
        inicial  = c1.number_input("Valor inicial (R$)", min_value=0, value=1000, step=500)
        mensal   = c2.number_input("Aporte mensal (R$)", min_value=0, value=500, step=100)
        anos_sim = c3.slider("Prazo (anos)", 1, 40, 10)

        if st.button("▶  Calcular", type="primary"):
            from core.calculators import compound_interest

            meses = anos_sim * 12
            cenarios = [
                ("Conservador", 10.5, "#10b981"),
                ("Moderado",    13.0, "#3b82f6"),
                ("Arrojado",    15.5, "#f59e0b"),
            ]
            resultados = []
            for nome_c, taxa, cor in cenarios:
                r = compound_interest(inicial, mensal, taxa, meses, include_ir=True, days_for_ir=meses * 30)
                resultados.append((nome_c, taxa, cor, r))

            # Cards de resultado
            cols_r = st.columns(3)
            for i, (nome_c, taxa, cor, r) in enumerate(resultados):
                cols_r[i].markdown(f"""<div class='metric-card' style='border-color:{cor}55;'>
                    <div class='label'>{nome_c} · {taxa}% a.a.</div>
                    <div class='value' style='color:{cor};'>R$ {r.final_amount:,.0f}</div>
                    <div class='sub'>Você investiu: R$ {r.total_invested:,.0f}</div>
                    <div class='sub'>Juros geraram: R$ {r.total_interest:,.0f} ({r.interest_ratio:.0f}%)</div>
                </div>""", unsafe_allow_html=True)

            # Gráfico de crescimento
            fig = go.Figure()
            anos_eixo = list(range(0, anos_sim + 1))
            for nome_c, taxa, cor, r in resultados:
                valores_anuais = [v for m, v in r.monthly_breakdown if m % 12 == 0]
                fig.add_trace(go.Scatter(
                    x=anos_eixo, y=valores_anuais, name=f"{nome_c} ({taxa}%)",
                    line=dict(color=cor, width=2.5), mode="lines",
                ))
            # Linha do total investido
            investido = [inicial + mensal * a * 12 for a in anos_eixo]
            fig.add_trace(go.Scatter(
                x=anos_eixo, y=investido, name="Total investido",
                line=dict(color="#475569", width=1.5, dash="dash"), mode="lines",
            ))
            fig.update_layout(
                **PLOT_LAYOUT,
                title=f"Crescimento ao longo de {anos_sim} anos",
                height=360,
                yaxis=dict(showgrid=True, gridcolor="#2d3555", tickprefix="R$ "),
                xaxis=dict(title="Anos", showgrid=False),
                legend=dict(bgcolor="#1e2235", bordercolor="#2d3555", borderwidth=1),
            )
            st.plotly_chart(fig, use_container_width=True)

    else:
        renda_c  = client.get("renda_mensal", 10000) if client else 10000
        patrim_c = sum(client.get("carteira_atual", {}).values()) if client else 0

        c1, c2 = st.columns(2)
        meta      = c1.number_input("Meta (R$)", min_value=100000, value=1500000, step=100000)
        anos_meta = c1.slider("Prazo (anos)", 5, 40, 26)
        renda_in  = c2.number_input("Renda mensal (R$)", min_value=1000, value=int(renda_c), step=500)
        patrim_in = c2.number_input("Patrimônio atual (R$)", min_value=0, value=int(patrim_c), step=1000)

        if st.button("▶  Calcular aposentadoria", type="primary"):
            from core.calculators import retirement_simulator
            scenss = retirement_simulator(meta, anos_meta, renda_in, patrim_in)

            cols_r = st.columns(3)
            colors_s = ["#10b981", "#3b82f6", "#f59e0b"]
            for i, s in enumerate(scenss):
                contrib = f"R$ {s.monthly_contribution:,.0f}/mês" if s.monthly_contribution > 0 else "Patrimônio já suficiente!"
                cols_r[i].markdown(f"""<div class='metric-card' style='border-color:{colors_s[i]}55;'>
                    <div class='label'>{s.name} · {s.annual_rate:.1f}% a.a.</div>
                    <div class='value' style='color:{colors_s[i]};'>{contrib}</div>
                    <div class='sub'>{s.income_pct_of_salary:.1f}% da sua renda</div>
                    <div class='sub'>Juros geram: R$ {s.total_interest:,.0f}</div>
                </div>""", unsafe_allow_html=True)

            # Gráfico: você investe vs. juros geram
            fig2 = go.Figure()
            fig2.add_trace(go.Bar(
                name="Você investe", x=[s.name for s in scenss],
                y=[s.total_invested for s in scenss], marker_color="#3b82f6",
            ))
            fig2.add_trace(go.Bar(
                name="Juros geram", x=[s.name for s in scenss],
                y=[s.total_interest for s in scenss], marker_color="#e8b84b",
            ))
            fig2.update_layout(
                **PLOT_LAYOUT,
                barmode="stack",
                title=f"Composição de R$ {meta:,.0f} por cenário",
                height=320,
                yaxis=dict(showgrid=True, gridcolor="#2d3555", tickprefix="R$ "),
            )
            st.plotly_chart(fig2, use_container_width=True)


# ════════════════════════════════════════════════════════════════════════
# ABA 3 — GASTOS
# ════════════════════════════════════════════════════════════════════════
with tab_gastos:
    st.markdown("##### Análise de gastos — Fevereiro/2025")

    df_trx = load_transactions(st.session_state.client_id)

    if df_trx.empty:
        st.info("Nenhuma transação encontrada para este cliente.")
    else:
        renda_g = client.get("renda_mensal", 10000) if client else 10000

        gastos_df = df_trx[(df_trx["tipo"] == "debito") & (df_trx["categoria"] != "investimento")]
        invest_df = df_trx[df_trx["categoria"] == "investimento"]

        por_cat  = gastos_df.groupby("categoria")["valor"].sum().abs().sort_values(ascending=False)
        tot_gasto  = float(por_cat.sum())
        tot_invest = float(invest_df["valor"].abs().sum())

        # Métricas topo
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total gasto",       f"R$ {tot_gasto:,.0f}")
        m2.metric("Total investido",   f"R$ {tot_invest:,.0f}")
        m3.metric("Taxa de investimento", f"{tot_invest/renda_g*100:.1f}%",
                  delta="Meta: 15%" if tot_invest / renda_g < 0.15 else "✅ Acima da meta")
        m4.metric("Maior categoria",   str(por_cat.index[0]).capitalize() if not por_cat.empty else "—")

        col_a, col_b = st.columns([3, 2])

        with col_a:
            fig_bar = go.Figure(go.Bar(
                x=[c.capitalize() for c in por_cat.index],
                y=list(por_cat.values),
                marker_color="#e8b84b",
                text=[f"R$ {v:,.0f}" for v in por_cat.values],
                textposition="outside",
            ))
            fig_bar.update_layout(
                **PLOT_LAYOUT,
                title="Gastos por categoria",
                height=320,
                yaxis=dict(showgrid=True, gridcolor="#2d3555"),
                xaxis=dict(tickangle=-20),
            )
            st.plotly_chart(fig_bar, use_container_width=True)

        with col_b:
            labels_d = [c.capitalize() for c in por_cat.index.tolist()] + ["Investimentos"]
            values_d = list(por_cat.values) + [tot_invest]
            fig_pie = go.Figure(go.Pie(
                labels=labels_d, values=values_d, hole=0.5,
                marker_colors=["#e8b84b","#3b82f6","#10b981","#f59e0b","#8b5cf6","#ef4444","#14b8a6"],
                textinfo="percent+label", textfont=dict(size=10),
            ))
            fig_pie.update_layout(**PLOT_LAYOUT, height=320, showlegend=False,
                                  title="Distribuição do dinheiro")
            st.plotly_chart(fig_pie, use_container_width=True)

        # Benchmarks
        st.divider()
        st.markdown("##### Comparação com benchmarks recomendados")
        BENCH = {"moradia": 30, "alimentacao": 15, "transporte": 10, "lazer": 8, "saude": 8, "educacao": 5}
        rows_b = []
        for cat, bm in BENCH.items():
            real = float(por_cat.get(cat, 0)) / renda_g * 100
            rows_b.append({
                "Categoria":         cat.capitalize(),
                "Seu gasto (%)":     round(real, 1),
                "Recomendado (%)":   bm,
                "Status":            "✅ OK" if real <= bm * 1.3 else "⚠️ Alto",
            })
        st.dataframe(pd.DataFrame(rows_b), hide_index=True, use_container_width=True)

        # Evolução do saldo
        df_trx2 = df_trx.copy()
        df_trx2["data"] = pd.to_datetime(df_trx2["data"])
        df_trx2 = df_trx2.sort_values("data")
        fig_saldo = go.Figure(go.Scatter(
            x=df_trx2["data"], y=df_trx2["saldo_apos"],
            fill="tozeroy", line=dict(color="#3b82f6", width=2),
            fillcolor="rgba(59,130,246,0.15)",
        ))
        fig_saldo.update_layout(**PLOT_LAYOUT, title="Evolução do saldo no mês", height=250)
        st.plotly_chart(fig_saldo, use_container_width=True)


# ════════════════════════════════════════════════════════════════════════
# ABA 4 — MERCADO
# ════════════════════════════════════════════════════════════════════════
with tab_mercado:
    st.markdown("##### Taxas de referência e produtos do seu perfil")

    # Taxas macro
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Selic",     "13,75% a.a.")
    c2.metric("CDI",       "13,65% a.a.")
    c3.metric("IPCA 12m",  "4,83%")
    c4.metric("IGP-M 12m", "3,89%")
    st.caption("⚠️ Taxas de referência (março/2025). Para dados em tempo real: bcb.gov.br")

    st.divider()

    # Produtos do perfil do cliente
    st.markdown("##### Produtos compatíveis com seu perfil")
    todos_produtos, _ = load_products()
    if todos_produtos and client:
        perfil_tipo = client["perfil"]["tipo"].lower()
        prods_filtrados = [p for p in todos_produtos if perfil_tipo in p.get("perfis_adequados", [])]

        linhas = []
        for p in prods_filtrados:
            rent = p.get("rentabilidade", {})
            tipo_r = rent.get("tipo", "")
            if tipo_r == "pos_fixado":
                taxa_str = f"{rent.get('percentual_indexador')}% {rent.get('indexador')}"
            elif tipo_r == "hibrido":
                taxa_str = f"IPCA + {rent.get('taxa_adicional')}% a.a."
            elif tipo_r == "variavel":
                dy = rent.get("dividend_yield_referencia_aa")
                taxa_str = f"DY ~{dy}% a.a." if dy else "Variável"
            else:
                taxa_str = "Variável"

            isento = "✅" if p.get("tributacao", {}).get("isento") else "—"
            linhas.append({
                "Produto":        p.get("nome"),
                "Tipo":           p.get("subcategoria", "").upper(),
                "Rentabilidade":  taxa_str,
                "Liquidez":       p.get("liquidez", "—"),
                "Garantia":       p.get("garantia", "—"),
                "Isento IR":      isento,
                "Mín. (R$)":      p.get("investimento_minimo", "—"),
            })
        st.dataframe(pd.DataFrame(linhas), hide_index=True, use_container_width=True)

    st.divider()

    # Comparador de produtos
    st.markdown("##### Comparador de rentabilidade líquida")
    cc1, cc2, cc3 = st.columns(3)
    taxa_lci  = cc1.number_input("LCI/LCA (% CDI)", min_value=50.0, max_value=150.0, value=92.0, step=0.5)
    taxa_cdb  = cc2.number_input("CDB (% CDI)",      min_value=50.0, max_value=200.0, value=110.0, step=0.5)
    prazo_d   = cc3.selectbox("Prazo", [90, 180, 365, 540, 720],
                              index=2, format_func=lambda x: f"{x} dias")

    if st.button("▶  Comparar produtos", type="primary"):
        from core.calculators import compare_investments
        produtos_comp = [
            {"name": f"LCI/LCA {taxa_lci}% CDI", "pct_cdi": taxa_lci, "is_exempt": True},
            {"name": f"CDB {taxa_cdb}% CDI",      "pct_cdi": taxa_cdb, "is_exempt": False},
            {"name": "Tesouro Selic 100% CDI",    "pct_cdi": 100.0,    "is_exempt": False},
        ]
        comps = compare_investments(produtos_comp, days=prazo_d)

        fig_comp = go.Figure(go.Bar(
            x=[c.name for c in comps],
            y=[c.net_rate_pct_cdi for c in comps],
            marker_color=["#e8b84b" if c.winner else "#3b82f6" for c in comps],
            text=[f"{c.net_rate_pct_cdi:.1f}% CDI\n({c.net_annual_yield_pct:.2f}% a.a.)" for c in comps],
            textposition="outside",
        ))
        fig_comp.update_layout(
            **PLOT_LAYOUT,
            title=f"Rendimento líquido — {prazo_d} dias",
            height=320,
            yaxis=dict(showgrid=True, gridcolor="#2d3555", title="% CDI líquido"),
        )
        st.plotly_chart(fig_comp, use_container_width=True)

        winner = next((c for c in comps if c.winner), None)
        if winner:
            st.success(
                f"✅ **Vencedor: {winner.name}** — "
                f"{winner.net_rate_pct_cdi:.1f}% CDI líquido ({winner.net_annual_yield_pct:.2f}% a.a.)"
            )
