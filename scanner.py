import yfinance as yf
import pandas as pd
import concurrent.futures
import time

# --- THE MASTER LIST (Stateless) ---
TICKERS = [
    # Top Cap
    "BTC-USD", "ETH-USD", "BNB-USD", "SOL-USD", "XRP-USD", "ADA-USD", "DOGE-USD",
    "AVAX-USD", "TRX-USD", "DOT-USD", "LINK-USD", "MATIC-USD", "SHIB-USD",
    "LTC-USD", "BCH-USD", "ATOM-USD", "UNI-USD", "ICP-USD", "NEAR-USD", "LEO-USD",

    # Layer 1 & Infra
    "APT-USD", "SUI-USD", "SEI-USD", "INJ-USD", "TIA-USD", "KAS-USD", "ALGO-USD",
    "HBAR-USD", "EGLD-USD", "XLM-USD", "XTZ-USD", "EOS-USD", "FTM-USD", "FLOW-USD",
    "MINA-USD", "QNT-USD", "ASTR-USD", "NEO-USD", "IOTA-USD", "KLAY-USD", "CFX-USD",
    "ROSE-USD", "GLMR-USD", "ZIL-USD", "KAVA-USD", "ONE-USD", "CKB-USD", "CELO-USD",

    # Layer 2s
    "ARB-USD", "OP-USD", "MNT-USD", "IMX-USD", "LRC-USD", "METIS-USD", "SKL-USD",
    "STRK-USD", "BLUR-USD", "ZK-USD", "MANTA-USD",

    # AI & Data
    "FET-USD", "RNDR-USD", "GRT-USD", "TAO-USD", "AGIX-USD", "OCEAN-USD", "WLD-USD",
    "JASMY-USD", "AKT-USD", "GLM-USD", "RLC-USD", "NMR-USD",

    # DeFi
    "MKR-USD", "AAVE-USD", "LDO-USD", "SNX-USD", "RUNE-USD", "CRV-USD", "DYDX-USD",
    "GNO-USD", "PENDLE-USD", "1INCH-USD", "COMP-USD", "FXS-USD", "CAKE-USD", "CVX-USD",
    "JUP-USD", "PYTH-USD", "RAY-USD", "OSMO-USD", "LUNA-USD", "LUNC-USD", "RPL-USD",

    # Memes
    "PEPE-USD", "BONK-USD", "WIF-USD", "FLOKI-USD", "BOME-USD", "MEME-USD",
    "MOG-USD", "BRETT-USD", "POPCAT-USD",

    # Gaming/Metaverse
    "GALA-USD", "SAND-USD", "MANA-USD", "AXS-USD", "BEAM-USD", "ENJ-USD", "APE-USD",
    "ILV-USD", "RON-USD", "GMT-USD", "PIXEL-USD", "PRIME-USD", "XAI-USD",

    # Legacy
    "ETC-USD", "XMR-USD", "ZEC-USD", "DASH-USD", "BSV-USD", "XEC-USD", "RVN-USD",
    "BTG-USD", "QTUM-USD", "OMG-USD", "BAT-USD", "ZRX-USD", "ANKR-USD", "CHZ-USD",
    "HOT-USD", "IOST-USD", "SC-USD", "LSK-USD", "WAVES-USD", "ICX-USD", "ONT-USD"
]

# --- CACHE STORAGE ---
CACHE = {
    "data": [],
    "last_scan": 0
}

# --- CALCULATIONS ---
def calculate_rsi_series(series, period=14):
    if len(series) < period: return pd.Series(0, index=series.index)
    delta = series.diff(1)
    gain = (delta.where(delta > 0, 0)).ewm(alpha=1/period, adjust=False).mean()
    loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/period, adjust=False).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def fetch_metadata(ticker):
    coin = yf.Ticker(ticker)
    price = 0
    mcap = 0
    
    # 1. Fast Info
    try:
        price = coin.fast_info.last_price
        mcap = coin.fast_info.market_cap
    except: pass

    # 2. Robust Info (Fallback)
    if mcap is None or mcap == 0:
        try:
            info = coin.info
            mcap = info.get('marketCap', 0)
            if not price: price = info.get('currentPrice', 0) or info.get('regularMarketPrice', 0)
        except: pass
            
    return ticker, price, mcap

# --- MAIN FUNCTION ---
def scan_market(min_mcap_billion=0):
    global CACHE
    
    current_time = time.time()
    
    # 1. CHECK CACHE
    # If cache is fresh (< 60s), use it. Otherwise, fetch new data.
    if current_time - CACHE["last_scan"] < 60 and CACHE["data"]:
        print("Returning Cached Data...")
        full_data = CACHE["data"]
    else:
        print(f"Cache expired. Scanning {len(TICKERS)} coins...")
        full_data = run_full_scan()
        # Save to cache
        if full_data:
            CACHE["data"] = full_data
            CACHE["last_scan"] = current_time

    # 2. APPLY FILTER (This happens every time, even on cached data)
    # Convert User Input (Billions) to Raw Number
    limit = min_mcap_billion * 1_000_000_000
    
    filtered_results = []
    for coin in full_data:
        # If user asks for 0.5B, we hide anything smaller
        if coin['mcap'] >= limit:
            filtered_results.append(coin)
            
    return filtered_results

def run_full_scan():
    valid_tickers = []
    metadata = {}

    # A. Fetch Metadata (Parallel)
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        future_to_ticker = {executor.submit(fetch_metadata, t): t for t in TICKERS}
        for future in concurrent.futures.as_completed(future_to_ticker):
            t, price, mcap = future.result()
            
            # Basic Validity Checks (Must have price, must have Mcap)
            if price is None or price <= 0: continue
            if mcap is None or mcap <= 0: continue
            
            metadata[t] = {'price': price, 'mcap': mcap}
            valid_tickers.append(t)
    
    if not valid_tickers: return []

    # B. Bulk History
    try:
        data_15m = yf.download(valid_tickers, period="5d", interval="15m", group_by='ticker', threads=True, progress=False)
        data_1h = yf.download(valid_tickers, period="1mo", interval="1h", group_by='ticker', threads=True, progress=False)
        data_1d = yf.download(valid_tickers, period="6mo", interval="1d", group_by='ticker', threads=True, progress=False)
    except: return []

    final_data = []

    # C. Process
    for t in valid_tickers:
        try:
            if len(valid_tickers) > 1:
                df_15 = data_15m[t] if t in data_15m else pd.DataFrame()
                df_1h = data_1h[t] if t in data_1h else pd.DataFrame()
                df_1d = data_1d[t] if t in data_1d else pd.DataFrame()
            else:
                df_15, df_1h, df_1d = data_15m, data_1h, data_1d

            def get_rsi(df, resample=None):
                if df.empty or 'Close' not in df.columns: return 0
                closes = df['Close'].dropna()
                if resample: closes = closes.resample(resample).last().dropna()
                if closes.empty: return 0
                return round(calculate_rsi_series(closes).iloc[-1], 2)

            rsi_15m = get_rsi(df_15)
            rsi_1h = get_rsi(df_1h)
            rsi_4h = get_rsi(df_1h, resample='4h')
            rsi_1d = get_rsi(df_1d)

            m_data = metadata[t]
            
            final_data.append({
                "symbol": t.replace("-USD", ""),
                "ticker": t,
                "price": round(m_data['price'], 6) if m_data['price'] < 0.1 else round(m_data['price'], 2),
                "mcap": m_data['mcap'],
                "rsi_15m": rsi_15m,
                "rsi_1h": rsi_1h,
                "rsi_4h": rsi_4h,
                "rsi_1d": rsi_1d
            })

        except: continue
            
    final_data.sort(key=lambda x: x["mcap"], reverse=True)

    return final_data
