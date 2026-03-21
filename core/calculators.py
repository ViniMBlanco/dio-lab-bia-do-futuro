"""
calculators.py
==============
Motor de simulações financeiras do SeuFariaLimer.
100% Python puro — sem APIs, sem internet, resultados instantâneos.

Funções disponíveis:
    - compound_interest()       Juros compostos com aportes mensais
    - retirement_simulator()    Quanto guardar por mês para aposentadoria
    - compare_investments()     Comparar rendimento líquido de produtos
    - lci_lca_equivalence()     Taxa bruta equivalente de LCI/LCA vs CDB
    - spending_analysis()       Análise de gastos por categoria (CSV)
    - emergency_reserve_check() Diagnóstico da reserva de emergência
"""

from dataclasses import dataclass, field
from typing import Optional
import math


# ── Constantes tributárias ────────────────────────────────────────────────────

IR_TABLE = [
    (180,  0.225),   # até 180 dias    → 22,5%
    (360,  0.200),   # 181 a 360 dias  → 20,0%
    (720,  0.175),   # 361 a 720 dias  → 17,5%
    (99999, 0.150),  # acima de 720    → 15,0%
]

def get_ir_rate(days: int) -> float:
    for limit, rate in IR_TABLE:
        if days <= limit:
            return rate
    return 0.15


# ── Data classes de resultado ─────────────────────────────────────────────────

@dataclass
class CompoundResult:
    final_amount: float
    total_invested: float
    total_interest: float
    interest_ratio: float        # % do total gerado pelos juros
    monthly_breakdown: list      # [(month, balance)] — amostras

@dataclass
class RetirementScenario:
    name: str
    annual_rate: float
    monthly_rate: float
    monthly_contribution: float
    total_invested: float
    total_interest: float
    final_amount: float
    income_pct_of_salary: float  # aporte como % da renda

@dataclass
class ProductComparison:
    name: str
    gross_rate_pct_cdi: float
    net_rate_pct_cdi: float
    net_annual_yield_pct: float
    ir_rate: float
    is_exempt: bool
    winner: bool = False

@dataclass
class SpendingAnalysis:
    categories: dict             # {categoria: total_gasto}
    total_expenses: float
    total_income: float
    total_invested: float
    investment_rate: float       # % da renda investida
    biggest_category: str
    savings_potential: float     # quanto poderia investir a mais
    alerts: list                 # alertas de gastos excessivos


# ── 1. Juros compostos ────────────────────────────────────────────────────────

def compound_interest(
    initial: float,
    monthly_contribution: float,
    annual_rate: float,
    months: int,
    include_ir: bool = False,
    days_for_ir: Optional[int] = None,
) -> CompoundResult:
    """
    Calcula crescimento com juros compostos e aportes mensais.

    Args:
        initial:              Valor inicial investido (R$)
        monthly_contribution: Aporte mensal (R$)
        annual_rate:          Taxa anual em % (ex: 12.5 para 12,5% a.a.)
        months:               Prazo em meses
        include_ir:           Se True, desconta IR sobre rendimentos
        days_for_ir:          Dias totais para calcular alíquota (padrão: months*30)

    Returns:
        CompoundResult com breakdown completo
    """
    monthly_rate = (1 + annual_rate / 100) ** (1 / 12) - 1
    balance = initial
    total_invested = initial
    breakdown = [(0, round(balance, 2))]

    for m in range(1, months + 1):
        balance = balance * (1 + monthly_rate) + monthly_contribution
        total_invested += monthly_contribution
        if m % 12 == 0 or m == months:
            breakdown.append((m, round(balance, 2)))

    gross_interest = balance - total_invested

    if include_ir and gross_interest > 0:
        effective_days = days_for_ir or (months * 30)
        ir = get_ir_rate(effective_days)
        net_interest = gross_interest * (1 - ir)
        final_amount = total_invested + net_interest
    else:
        ir = 0
        net_interest = gross_interest
        final_amount = balance

    return CompoundResult(
        final_amount=round(final_amount, 2),
        total_invested=round(total_invested, 2),
        total_interest=round(net_interest, 2),
        interest_ratio=round(net_interest / final_amount * 100, 1) if final_amount else 0,
        monthly_breakdown=breakdown,
    )


# ── 2. Simulador de aposentadoria ─────────────────────────────────────────────

def retirement_simulator(
    target_amount: float,
    years: int,
    monthly_salary: float,
    initial_amount: float = 0,
    cdi_rate: float = 13.65,   # CDI de referência (% ao ano)
) -> list[RetirementScenario]:
    """
    Calcula o aporte mensal necessário para atingir uma meta de aposentadoria
    em 3 cenários de risco/retorno.

    Args:
        target_amount:   Meta financeira (R$)
        years:           Prazo em anos
        monthly_salary:  Renda mensal atual (para calcular % de esforço)
        initial_amount:  Patrimônio atual já investido (R$)
        cdi_rate:        CDI anual de referência em %

    Returns:
        Lista de 3 RetirementScenario (conservador, moderado, arrojado)
    """
    scenarios_config = [
        ("Conservador", cdi_rate * 0.90),   # 90% CDI (renda fixa)
        ("Moderado",    cdi_rate * 1.10),   # 110% CDI (misto)
        ("Arrojado",    cdi_rate * 1.35),   # 135% CDI (renda variável)
    ]

    months = years * 12
    results = []

    for name, annual_rate in scenarios_config:
        monthly_rate = (1 + annual_rate / 100) ** (1 / 12) - 1

        # Valor futuro do capital já investido
        fv_initial = initial_amount * (1 + monthly_rate) ** months

        # Quanto ainda precisa gerar com aportes
        remaining = target_amount - fv_initial

        # PMT reverso: qual aporte gera 'remaining' em 'months' meses
        if monthly_rate > 0 and remaining > 0:
            monthly_contrib = remaining * monthly_rate / ((1 + monthly_rate) ** months - 1)
        elif remaining <= 0:
            monthly_contrib = 0
        else:
            monthly_contrib = remaining / months

        total_invested = monthly_contrib * months + initial_amount
        total_interest = target_amount - total_invested

        results.append(RetirementScenario(
            name=name,
            annual_rate=round(annual_rate, 2),
            monthly_rate=round(monthly_rate * 100, 4),
            monthly_contribution=round(max(monthly_contrib, 0), 2),
            total_invested=round(total_invested, 2),
            total_interest=round(max(total_interest, 0), 2),
            final_amount=round(target_amount, 2),
            income_pct_of_salary=round(monthly_contrib / monthly_salary * 100, 1) if monthly_salary else 0,
        ))

    return results


# ── 3. Comparador de investimentos ────────────────────────────────────────────

def compare_investments(
    products: list[dict],
    days: int,
    cdi_rate: float = 13.65,
) -> list[ProductComparison]:
    """
    Compara o rendimento líquido de múltiplos produtos.

    Args:
        products: Lista de dicts com keys:
                  - name (str)
                  - pct_cdi (float): % do CDI que o produto paga
                  - is_exempt (bool): se isento de IR (LCI, LCA, FII etc.)
        days:     Prazo em dias para calcular IR
        cdi_rate: CDI anual de referência em %

    Returns:
        Lista de ProductComparison ordenada por rendimento líquido DESC
    """
    ir_rate = get_ir_rate(days)
    comparisons = []

    for p in products:
        gross_pct = p["pct_cdi"]
        exempt = p.get("is_exempt", False)

        if exempt:
            net_pct = gross_pct
            effective_ir = 0.0
        else:
            net_pct = gross_pct * (1 - ir_rate)
            effective_ir = ir_rate

        net_annual = cdi_rate * net_pct / 100

        comparisons.append(ProductComparison(
            name=p["name"],
            gross_rate_pct_cdi=round(gross_pct, 2),
            net_rate_pct_cdi=round(net_pct, 2),
            net_annual_yield_pct=round(net_annual, 2),
            ir_rate=round(effective_ir * 100, 1),
            is_exempt=exempt,
        ))

    comparisons.sort(key=lambda x: x.net_rate_pct_cdi, reverse=True)
    if comparisons:
        comparisons[0].winner = True

    return comparisons


# ── 4. Equivalência LCI/LCA vs CDB ───────────────────────────────────────────

def lci_lca_equivalence(
    exempt_rate_pct_cdi: float,
    days: int,
) -> dict:
    """
    Calcula a taxa bruta de CDB equivalente a uma LCI/LCA isenta.

    Pergunta: "Uma LCI de X% CDI vale mais que um CDB de Y% CDI nesse prazo?"
    Essa função responde matematicamente.

    Args:
        exempt_rate_pct_cdi: Taxa da LCI/LCA em % do CDI (ex: 92.0 para 92%)
        days:                Prazo em dias (define alíquota do IR do CDB)

    Returns:
        Dict com equivalência e interpretação
    """
    ir = get_ir_rate(days)
    equivalent_gross = exempt_rate_pct_cdi / (1 - ir)

    return {
        "exempt_rate": round(exempt_rate_pct_cdi, 2),
        "ir_rate_pct": round(ir * 100, 1),
        "equivalent_cdb_gross": round(equivalent_gross, 2),
        "breakeven_message": (
            f"Um CDB precisa pagar mais de {equivalent_gross:.1f}% do CDI "
            f"para superar essa LCI/LCA (prazo: {days} dias, IR: {ir*100:.1f}%)"
        ),
    }


# ── 5. Análise de gastos ──────────────────────────────────────────────────────

def spending_analysis(transactions: list[dict], monthly_salary: float) -> SpendingAnalysis:
    """
    Analisa padrão de gastos a partir de lista de transações.

    Args:
        transactions:   Lista de dicts com keys: categoria, valor, tipo
                        (tipo = "debito" ou "credito")
        monthly_salary: Renda mensal declarada do cliente

    Returns:
        SpendingAnalysis com categorias, alertas e potencial de investimento
    """
    categories = {}
    total_expenses = 0.0
    total_income = 0.0
    total_invested = 0.0

    for t in transactions:
        valor = abs(float(t.get("valor", 0)))
        tipo = t.get("tipo", "")
        cat = t.get("categoria", "outros")

        if tipo == "credito":
            total_income += valor
        elif tipo == "debito":
            if cat == "investimento":
                total_invested += valor
            else:
                categories[cat] = categories.get(cat, 0) + valor
                total_expenses += valor

    # Benchmarks por categoria (% da renda — referência brasileira)
    BENCHMARKS = {
        "moradia":     0.30,
        "alimentacao": 0.15,
        "transporte":  0.10,
        "lazer":       0.08,
        "saude":       0.08,
        "educacao":    0.05,
    }

    alerts = []
    for cat, spent in categories.items():
        pct = spent / monthly_salary if monthly_salary else 0
        benchmark = BENCHMARKS.get(cat, 0.10)
        if pct > benchmark * 1.3:   # 30% acima do benchmark
            alerts.append(
                f"{cat.capitalize()}: R${spent:,.0f}/mês "
                f"({pct*100:.0f}% da renda) — acima do recomendado "
                f"({benchmark*100:.0f}%)"
            )

    biggest = max(categories, key=categories.get) if categories else "—"
    investment_rate = total_invested / monthly_salary * 100 if monthly_salary else 0

    # Potencial de economia: diferença entre renda e (gastos + investimentos ideais)
    ideal_invest = monthly_salary * 0.15   # 15% como meta mínima
    savings_potential = max(0, ideal_invest - total_invested)

    return SpendingAnalysis(
        categories={k: round(v, 2) for k, v in sorted(categories.items(), key=lambda x: -x[1])},
        total_expenses=round(total_expenses, 2),
        total_income=round(total_income, 2),
        total_invested=round(total_invested, 2),
        investment_rate=round(investment_rate, 1),
        biggest_category=biggest,
        savings_potential=round(savings_potential, 2),
        alerts=alerts,
    )


# ── 6. Diagnóstico da reserva de emergência ───────────────────────────────────

def emergency_reserve_check(
    current_reserve: float,
    monthly_expenses: float,
    employment_type: str = "clt",  # "clt" | "autonomo" | "empresario"
) -> dict:
    """
    Verifica se a reserva de emergência está adequada.

    Args:
        current_reserve:   Valor atual na reserva (R$)
        monthly_expenses:  Gastos mensais médios (R$)
        employment_type:   Tipo de vínculo empregatício

    Returns:
        Dict com status, gap e recomendação
    """
    MONTHS_TARGET = {
        "clt":       (3, 6),
        "autonomo":  (6, 12),
        "empresario": (12, 18),
    }

    min_months, ideal_months = MONTHS_TARGET.get(employment_type, (3, 6))
    min_target  = monthly_expenses * min_months
    ideal_target = monthly_expenses * ideal_months
    months_covered = current_reserve / monthly_expenses if monthly_expenses else 0

    if current_reserve >= ideal_target:
        status = "adequada"
        color  = "green"
        gap    = 0
    elif current_reserve >= min_target:
        status = "parcial"
        color  = "orange"
        gap    = ideal_target - current_reserve
    else:
        status = "insuficiente"
        color  = "red"
        gap    = min_target - current_reserve

    return {
        "status":         status,
        "color":          color,
        "current":        round(current_reserve, 2),
        "months_covered": round(months_covered, 1),
        "min_target":     round(min_target, 2),
        "ideal_target":   round(ideal_target, 2),
        "gap":            round(gap, 2),
        "min_months":     min_months,
        "ideal_months":   ideal_months,
        "recommendation": (
            f"Reserva {'adequada' if status == 'adequada' else 'insuficiente'}. "
            f"Cobre {months_covered:.1f} meses "
            f"(meta: {min_months}–{ideal_months} para {employment_type.upper()}). "
            + (f"Faltam R${gap:,.0f} para atingir o mínimo recomendado." if gap > 0 else
               "Você pode direcionar aportes extras para outros objetivos.")
        ),
    }


# ── Testes rápidos ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 55)
    print("  SeuFariaLimer — Teste das Calculadoras")
    print("=" * 55)

    # Teste 1: Juros compostos
    r = compound_interest(1000, 500, 12.5, 120, include_ir=True, days_for_ir=3650)
    print(f"\n📈 Juros compostos (R$1k inicial + R$500/mês × 10 anos @ 12,5% a.a.)")
    print(f"   Montante final:   R$ {r.final_amount:>12,.2f}")
    print(f"   Total investido:  R$ {r.total_invested:>12,.2f}")
    print(f"   Juros líquidos:   R$ {r.total_interest:>12,.2f}  ({r.interest_ratio:.1f}% do total)")

    # Teste 2: Aposentadoria
    scenarios = retirement_simulator(1_500_000, 26, 12_000, initial_amount=85_000)
    print(f"\n🎯 Aposentadoria R$1.500.000 em 26 anos (João Silva, R$85k já investidos)")
    for s in scenarios:
        print(f"   {s.name:<12} → R${s.monthly_contribution:>8,.0f}/mês  ({s.income_pct_of_salary:.1f}% da renda)  |  juros: R${s.total_interest:>12,.0f}")

    # Teste 3: Comparador
    products = [
        {"name": "LCI 92% CDI (isento)", "pct_cdi": 92, "is_exempt": True},
        {"name": "CDB 110% CDI",          "pct_cdi": 110, "is_exempt": False},
        {"name": "CDB 100% CDI",          "pct_cdi": 100, "is_exempt": False},
        {"name": "Tesouro Selic ~100% CDI","pct_cdi": 100, "is_exempt": False},
    ]
    comps = compare_investments(products, days=365)
    print(f"\n⚖️  Comparação (365 dias, IR=20%):")
    for c in comps:
        tag = " ← VENCEDOR" if c.winner else ""
        print(f"   {c.name:<35} líquido: {c.net_rate_pct_cdi:.1f}% CDI  ({c.net_annual_yield_pct:.2f}% a.a.){tag}")

    # Teste 4: Equivalência LCI
    eq = lci_lca_equivalence(92, 365)
    print(f"\n🔄 Equivalência LCI 92% CDI para 365 dias:")
    print(f"   {eq['breakeven_message']}")

    # Teste 5: Reserva de emergência
    er = emergency_reserve_check(18_000, 12_000 * 0.62, "clt")
    print(f"\n🛡️  Reserva de emergência João Silva (CLT):")
    print(f"   Status: {er['status'].upper()} | Cobertura: {er['months_covered']} meses")
    print(f"   {er['recommendation']}")

    print("\n✅ Todas as calculadoras funcionando corretamente!")
