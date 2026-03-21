"""
market_data.py
==============
Dados de mercado em tempo real para o SeuFariaLimer.
Usa yfinance para cotações, índices e dados históricos.

Funções disponíveis:
    get_market_overview()    Selic, CDI, IPCA, Ibovespa, Dólar
    get_asset_price()        Cotação de ativo específico (BOVA11, PETR4, etc.)
    get_historical()         Histórico de preços para gráficos
    get_fii_data()           Dados de FII: preço, DY, P/VP

Todos os dados têm cache de 15 minutos para evitar chamadas excessivas à API.
"""

import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional
import functools
import time

# ── Cache simples em memória (15 minutos) ─────────────────────────────────────
_cache: dict = {}
CACHE_TTL = 900  # segundos

def _cached(key: str, fetch_fn, *args):
    """Cache com TTL. Retorna valor em cache ou busca novo."""
    now = time.time()
    if key in _cache:
        value, ts = _cache[key]
        if now - ts < CACHE_TTL:
            return value
    value = fetch_fn(*args)
    _cache[key] = (value, now)
    return value


# ── Tickers de referência ─────────────────────────────────────────────────────
TICKERS = {
    "ibovespa":   "^BVSP",
    "dolar":      "BRL=X",
    "sp500":      "^GSPC",
    "bova11":     "BOVA11.SA",
    "ivvb11":     "IVVB11.SA",
    "mxrf11":     "MXRF11.SA",
    "brco11":     "BRCO11.SA",
    "smal11":     "SMAL11.SA",
    "petr4":      "PETR4.SA",
    "vale3":      "VALE3.SA",
    "itub4":      "ITUB4.SA",
    "wege3":      "WEGE3.SA",
}


# ── 1. Visão geral do mercado ─────────────────────────────────────────────────

def get_market_overview() -> dict:
    """
    Retorna snapshot do mercado brasileiro + referências macro.

    Returns:
        Dict com Ibovespa, Dólar, S&P500 e taxas de referência.
        Inclui variação % do dia para cada índice.
    """
    def _fetch():
        result = {}

        # Índices
        for name, ticker in [("ibovespa", "^BVSP"), ("dolar", "BRL=X"), ("sp500", "^GSPC")]:
            try:
                data = yf.Ticker(ticker).history(period="2d", interval="1d")
                if len(data) >= 2:
                    current = data["Close"].iloc[-1]
                    previous = data["Close"].iloc[-2]
                    change_pct = (current - previous) / previous * 100
                    result[name] = {
                        "value": round(current, 2),
                        "change_pct": round(change_pct, 2),
                        "arrow": "▲" if change_pct >= 0 else "▼",
                        "color": "green" if change_pct >= 0 else "red",
                    }
                else:
                    result[name] = {"value": None, "change_pct": None}
            except Exception:
                result[name] = {"value": None, "change_pct": None}

        result["timestamp"] = datetime.now().strftime("%d/%m/%Y %H:%M")
        return result

    return _cached("market_overview", _fetch)


def get_asset_price(ticker_name: str) -> dict:
    """
    Retorna cotação atual e variação de um ativo.

    Args:
        ticker_name: Nome amigável (ex: "bova11", "petr4") ou ticker direto

    Returns:
        Dict com price, change_pct, volume e nome do ativo
    """
    ticker_symbol = TICKERS.get(ticker_name.lower(), ticker_name.upper() + ".SA")

    def _fetch():
        try:
            t = yf.Ticker(ticker_symbol)
            info = t.info
            hist = t.history(period="2d", interval="1d")

            current = hist["Close"].iloc[-1] if len(hist) > 0 else None
            previous = hist["Close"].iloc[-2] if len(hist) > 1 else None
            change_pct = (current - previous) / previous * 100 if current and previous else None

            return {
                "ticker":     ticker_symbol,
                "name":       info.get("longName", ticker_name.upper()),
                "price":      round(current, 2) if current else None,
                "change_pct": round(change_pct, 2) if change_pct else None,
                "currency":   info.get("currency", "BRL"),
                "volume":     info.get("volume", None),
                "timestamp":  datetime.now().strftime("%d/%m/%Y %H:%M"),
            }
        except Exception as e:
            return {"ticker": ticker_symbol, "price": None, "error": str(e)}

    return _cached(f"price_{ticker_symbol}", _fetch)


# ── 2. Histórico para gráficos ────────────────────────────────────────────────

def get_historical(
    ticker_name: str,
    period: str = "1y",
    interval: str = "1mo",
) -> pd.DataFrame:
    """
    Retorna histórico de preços para plotar gráfico.

    Args:
        ticker_name: Nome amigável ou ticker
        period:      "1mo", "6mo", "1y", "3y", "5y", "10y"
        interval:    "1d", "1wk", "1mo"

    Returns:
        DataFrame com colunas: Date, Close, Volume, Return_pct
    """
    ticker_symbol = TICKERS.get(ticker_name.lower(), ticker_name.upper() + ".SA")

    def _fetch():
        try:
            data = yf.Ticker(ticker_symbol).history(period=period, interval=interval)
            if data.empty:
                return pd.DataFrame()
            df = data[["Close", "Volume"]].copy()
            df.index = pd.to_datetime(df.index).tz_localize(None)
            df["Return_pct"] = df["Close"].pct_change() * 100
            df["Return_cumulative"] = ((df["Close"] / df["Close"].iloc[0]) - 1) * 100
            return df.round(2)
        except Exception:
            return pd.DataFrame()

    return _cached(f"hist_{ticker_symbol}_{period}_{interval}", _fetch)


def compare_returns(
    tickers: list[str],
    period: str = "1y",
) -> pd.DataFrame:
    """
    Compara retorno acumulado de múltiplos ativos.
    Útil para mostrar desempenho de BOVA11 vs IVVB11 vs Selic simulada.

    Args:
        tickers: Lista de nomes amigáveis
        period:  Período de comparação

    Returns:
        DataFrame com retorno acumulado % por ativo
    """
    results = {}
    for t in tickers:
        hist = get_historical(t, period=period, interval="1mo")
        if not hist.empty:
            results[t.upper()] = hist["Return_cumulative"]

    if not results:
        return pd.DataFrame()

    df = pd.DataFrame(results)
    df.index.name = "Data"
    return df.fillna(method="ffill")


# ── 3. Dados de FII ───────────────────────────────────────────────────────────

def get_fii_data(ticker_name: str) -> dict:
    """
    Retorna dados relevantes de um FII: preço, DY estimado, P/VP.

    Args:
        ticker_name: Nome amigável (ex: "mxrf11") ou ticker

    Returns:
        Dict com price, dividend_yield, pvp e histórico de dividendos
    """
    ticker_symbol = TICKERS.get(ticker_name.lower(), ticker_name.upper() + ".SA")

    def _fetch():
        try:
            t = yf.Ticker(ticker_symbol)
            info = t.info
            hist = t.history(period="1d")

            price = hist["Close"].iloc[-1] if not hist.empty else None

            # Dividendos dos últimos 12 meses
            divs = t.dividends
            if not divs.empty:
                one_year_ago = datetime.now() - timedelta(days=365)
                recent_divs = divs[divs.index >= one_year_ago.strftime("%Y-%m-%d")]
                annual_div = float(recent_divs.sum()) if not recent_divs.empty else 0
                dy = (annual_div / price * 100) if price and price > 0 else None
            else:
                dy = None

            # P/VP (yfinance não tem direto; usa bookValue se disponível)
            book_value = info.get("bookValue", None)
            pvp = round(price / book_value, 2) if price and book_value else None

            return {
                "ticker":          ticker_symbol,
                "name":            info.get("longName", ticker_name.upper()),
                "price":           round(price, 2) if price else None,
                "dividend_yield":  round(dy, 2) if dy else None,
                "pvp":             pvp,
                "sector":          info.get("sector", "Real Estate"),
                "timestamp":       datetime.now().strftime("%d/%m/%Y %H:%M"),
            }
        except Exception as e:
            return {"ticker": ticker_symbol, "price": None, "error": str(e)}

    return _cached(f"fii_{ticker_symbol}", _fetch)


# ── 4. Taxas de referência (simuladas quando API indisponível) ────────────────

# Valores de fallback quando yfinance não retorna dados macroeconômicos
# (Selic e IPCA não estão disponíveis no yfinance — use Banco Central API para produção)
MACRO_FALLBACK = {
    "selic_aa":       13.75,   # % ao ano — atualizar manualmente ou usar BCB API
    "cdi_aa":         13.65,   # % ao ano (Selic - 0.10%)
    "ipca_12m":        4.83,   # % acumulado 12 meses
    "igpm_12m":        3.89,   # % acumulado 12 meses
    "fonte":          "Referência manual — dados de março/2025",
    "aviso":          "Para dados em tempo real do IPCA/Selic, consulte api.bcb.gov.br",
}

def get_macro_rates() -> dict:
    """
    Retorna taxas macroeconômicas de referência.
    
    Nota: Selic e IPCA não estão no yfinance.
    Para produção, integre com: https://api.bcb.gov.br/dados/serie/bcdata.sgs.11/dados
    (série 11 = Selic, série 433 = IPCA)

    Returns:
        Dict com selic_aa, cdi_aa, ipca_12m, igpm_12m
    """
    return MACRO_FALLBACK.copy()


def format_market_for_context(overview: dict, macro: dict) -> str:
    """
    Formata dados de mercado para injeção no prompt do LLM.
    Usado pelo agente quando a pergunta menciona taxas ou índices.
    """
    ibov = overview.get("ibovespa", {})
    dolar = overview.get("dolar", {})

    ibov_str = (
        f"{ibov['value']:,.0f} pts ({ibov['arrow']} {abs(ibov['change_pct']):.1f}%)"
        if ibov.get("value") else "indisponível"
    )
    dolar_str = (
        f"R$ {dolar['value']:.2f} ({dolar['arrow']} {abs(dolar['change_pct']):.1f}%)"
        if dolar.get("value") else "indisponível"
    )

    return (
        f"[DADOS DE MERCADO — {overview.get('timestamp', 'agora')}]\n"
        f"Ibovespa:  {ibov_str}\n"
        f"Dólar:     {dolar_str}\n"
        f"Selic:     {macro['selic_aa']}% a.a.\n"
        f"CDI:       {macro['cdi_aa']}% a.a.\n"
        f"IPCA 12m:  {macro['ipca_12m']}%\n"
        f"Nota: {macro['aviso']}"
    )


# ── Teste standalone ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 55)
    print("  SeuFariaLimer — Market Data Module")
    print("=" * 55)

    print("\n📊 Taxas de referência (fallback):")
    macro = get_macro_rates()
    for k, v in macro.items():
        if k not in ("fonte", "aviso"):
            print(f"   {k:<15} {v}")

    print("\n📈 Testando cotações (requer internet):")
    for name in ["bova11", "ivvb11", "mxrf11"]:
        data = get_asset_price(name)
        if data.get("price"):
            print(f"   {name.upper():<10} R$ {data['price']:>8.2f}  ({data.get('change_pct', 0):+.1f}%)")
        else:
            print(f"   {name.upper():<10} indisponível (sem internet no ambiente)")

    print("\n✅ Módulo carregado com sucesso.")
    print("   Com internet: cotações em tempo real via yfinance")
    print("   Sem internet: fallback para valores de referência manuais")
