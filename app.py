import streamlit as st
import pandas as pd
import requests
import json
from decimal import Decimal
import os
import time
from dotenv import load_dotenv

load_dotenv()

FILE_PATH = 'portfolio.csv'
ASSET_OPTIONS = ["BTC", "ETH", "SOL", "WBETH", "PAXG", "BNSOL", "BNB", "0G", "BEAM"]

def load_data():
    if not os.path.exists(FILE_PATH):
        df = pd.DataFrame(columns=['Date', 'Type', 'Asset', 'Tokens', 'USD_Value'])
        df.to_csv(FILE_PATH, index=False)
        return df
    return pd.read_csv(FILE_PATH, dtype={'Tokens': str})

def save_data(df):
    df.to_csv(FILE_PATH, index=False)

def _format_token_str(value: float) -> str:
    d = Decimal(str(value))
    s = format(d.normalize(), 'f')
    if '.' not in s:
        s = s + '.00'
    else:
        frac = s.split('.')[1]
        if len(frac) == 1:
            s = s + '0'
    return s

@st.cache_data(ttl=1800)
def get_all_live_prices(coin_ids_list):
    if not coin_ids_list:
        return {}
    try:
        # Join all coins into one string (e.g., "bitcoin,ethereum,solana")
        ids_str = ",".join(coin_ids_list)
        api_key = os.getenv('API_KEY')
        
        if api_key:
            url = f"https://api.coingecko.com/api/v3/simple/price?ids={ids_str}&vs_currencies=usd&x_cg_demo_api_key={api_key}"
        else:
            url = f"https://api.coingecko.com/api/v3/simple/price?ids={ids_str}&vs_currencies=usd"
            
        response = requests.get(url).json()
        return response
    except Exception:
        return {}

def _load_curated_ids():
    path = 'coinlist-ids.json'
    try:
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return {k.upper(): v for k, v in data.items()}
    except Exception:
        return {}
    return {}

def _save_curated_ids(mapping: dict):
    path = 'coinlist-ids.json'
    try:
        with open(path, 'w', encoding='utf-8') as f:
            json.dump({k.upper(): v for k, v in mapping.items()}, f, indent=2)
    except Exception:
        pass

_CURATED_IDS = _load_curated_ids()

def _load_targets():
    path = 'coin-targets.json'
    try:
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception:
        return {}
    return {}

def _save_targets(mapping: dict):
    path = 'coin-targets.json'
    try:
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(mapping, f, indent=2)
    except Exception:
        pass

def _on_target_change(coin_ticker):
    targets = _load_targets()
    buy_val = st.session_state.get(f"target_buy_{coin_ticker}", 20.0)
    sell_val = st.session_state.get(f"target_sell_{coin_ticker}", 20.0)
    targets[coin_ticker] = {"buy": buy_val, "sell": sell_val}
    _save_targets(targets)

def resolve_symbol(symbol: str) -> str | None:
    return _CURATED_IDS.get(symbol.upper())

st.set_page_config(page_title="Crypto & Fiat Tracker", layout="wide")
st.markdown('''
<style>
    h3 { margin-bottom: 0.5rem !important; }
    p { margin-bottom: 0.2rem !important; font-size: 1rem; }
    .coin-card { padding: 16px; border-radius: 12px; background: linear-gradient(145deg, #1e222d, #131722); border: 1px solid rgba(255, 255, 255, 0.05); border-left: 4px solid #3b82f6; box-shadow: 0 8px 16px rgba(0, 0, 0, 0.3); color: #e2e8f0; transition: transform 0.2s ease; margin-bottom: 1rem; }
    .coin-card:hover { transform: translateY(-2px); border-left: 4px solid #00ff9d; /* Accent changes to neon green on hover */ box-shadow: 0 12px 20px rgba(0, 0, 0, 0.4); }
    .coin-title { font-size: x-large; margin-bottom:6px; font-weight:700; }
    .coin-holdings { margin-bottom:6px; color:var(--text-color); }
    .coin-stats { display:flex; flex-direction:column; gap:4px; }
    .st-emotion-cache-tn0cau { gap: 0.5rem !important; }
    .trade-btn{display:inline-block;padding:8px 16px;border-radius:8px;font-weight:600;font-size:.9rem;text-decoration:none!important;text-align:center;transition:.2s;cursor:pointer}
    .trade-btn.buy{background:rgba(239,68,68,.1);border:1px solid rgba(239,68,68,.4);color:#ef4444}
    .trade-btn.buy:hover{background:rgba(239,68,68,.2);border-color:#ef4444;box-shadow:0 0 12px rgba(239,68,68,.4);transform:translateY(-2px)}
    .trade-btn.sell{background:rgba(0,255,157,.1);border:1px solid rgba(0,255,157,.4);color:#00ff9d}
    .trade-btn.sell:hover{background:rgba(0,255,157,.2);border-color:#00ff9d;box-shadow:0 0 12px rgba(0,255,157,.3);transform:translateY(-2px)}
    .trade-btn.watch{background:rgba(243,186,47,.1);border:1px solid rgba(243,186,47,.4);color:#f3ba2f}
    .trade-btn.watch:hover{background:rgba(243,186,47,.2);border-color:#f3ba2f;box-shadow:0 0 12px rgba(243,186,47,.4);transform:translateY(-2px)}
</style>
''', unsafe_allow_html=True)

header_col1, header_col2 = st.columns([0.85, 0.15])
with header_col1:
    st.title("📊 Personal Portfolio Tracker")
with header_col2:
    st.write("") 
    is_private = st.toggle("🙈 Hide Balances", value=False)

def secure_val(val, is_currency=True, token_symbol=""):
    if is_private:
        return "****"
    if is_currency:
        return f"${val:,.2f}"
    return f"{val:.4f} {token_symbol}".strip()

if 'input_key' not in st.session_state:
    st.session_state['input_key'] = 0

with st.sidebar:
    st.header("➕ New Transaction")

    tx_type = st.selectbox(
        "Transaction Type",
        ["Deposit Fiat", "Withdraw Fiat", "Buy Crypto", "Sell Crypto", "Earn (Staking)", "Gas (Fee)"]
    )

    if tx_type in ["Deposit Fiat", "Withdraw Fiat"]:
        asset = "USD"
        tokens = 0.0
        usd_value = st.number_input("Amount (USD)", min_value=0.0, format="%.2f", key=f"usd_{st.session_state['input_key']}")
    else:
        asset = st.selectbox("Asset Ticker", options=ASSET_OPTIONS)
        tokens = st.number_input("Quantity of Tokens", min_value=0.0, format="%.9f", step=0.000000001, key=f"tokens_{st.session_state['input_key']}")

        if tx_type in ["Earn (Staking)", "Gas (Fee)"]:
            usd_value = 0.0
            st.info(f"Cost basis is automatically $0 for {tx_type}.")
        else:
            usd_value = st.number_input("Total USD Value of Trade", min_value=0.0, format="%.2f", key=f"usd_{st.session_state['input_key']}")

    if st.button("Save Transaction"):
        tokens_str = _format_token_str(tokens) if isinstance(tokens, (int, float)) else str(tokens)
        new_tx = pd.DataFrame({
            'Date': [pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")],
            'Type': [tx_type],
            'Asset': [asset],
            'Tokens': [tokens_str],
            'USD_Value': [usd_value]
        })

        df = load_data()
        df = pd.concat([df, new_tx], ignore_index=True)
        save_data(df)
        st.session_state['input_key'] += 1
        st.success("Transaction saved successfully!")
        time.sleep(0.5)
        st.rerun()

df = load_data()
df['_Tokens'] = pd.to_numeric(df['Tokens'], errors='coerce').fillna(0.0)

if not df.empty:
    total_deposits = df[df['Type'] == 'Deposit Fiat']['USD_Value'].sum()
    total_withdrawals = df[df['Type'] == 'Withdraw Fiat']['USD_Value'].sum()
    crypto_bought = df[df['Type'] == 'Buy Crypto']['USD_Value'].sum()
    crypto_sold = df[df['Type'] == 'Sell Crypto']['USD_Value'].sum()

    fiat_balance = total_deposits - total_withdrawals - crypto_bought + crypto_sold

    st.subheader("Investments & DCA")
    crypto_assets = list(df[(df['Asset'] != 'USD')]['Asset'].unique())

    mapped_ids = []
    for coin in crypto_assets:
        cid = resolve_symbol(coin)
        if cid:
            mapped_ids.append(cid)
            
    live_prices_data = get_all_live_prices(mapped_ids)

    total_crypto_value = 0.0
    for coin in crypto_assets:
        coin_txs = df[df['Asset'] == coin]
        bought = coin_txs[coin_txs['Type'] == 'Buy Crypto']['_Tokens'].sum()
        earned = coin_txs[coin_txs['Type'] == 'Earn (Staking)']['_Tokens'].sum()
        sold = coin_txs[coin_txs['Type'] == 'Sell Crypto']['_Tokens'].sum()
        gas = coin_txs[coin_txs['Type'] == 'Gas (Fee)']['_Tokens'].sum()
        current_tokens = bought + earned - sold - gas
        
        cid = resolve_symbol(coin)
        price = live_prices_data.get(cid, {}).get('usd', 0.0) if cid else 0.0
        total_crypto_value += (current_tokens * price)

    if 'show_more_assets' not in st.session_state:
        st.session_state['show_more_assets'] = False
    max_initial = 8
    show_all = st.session_state.get('show_more_assets', False)
    display_count = len(crypto_assets) if show_all else min(len(crypto_assets), max_initial)
    assets_to_show = crypto_assets[:display_count]

    for row_start in range(0, len(assets_to_show), 4):
        row = assets_to_show[row_start: row_start + 4]
        cols = st.columns(4)
        for j, coin in enumerate(row):
            coin_txs = df[df['Asset'] == coin]

            bought = coin_txs[coin_txs['Type'] == 'Buy Crypto']['_Tokens'].sum()
            earned = coin_txs[coin_txs['Type'] == 'Earn (Staking)']['_Tokens'].sum()
            sold = coin_txs[coin_txs['Type'] == 'Sell Crypto']['_Tokens'].sum()
            gas = coin_txs[coin_txs['Type'] == 'Gas (Fee)']['_Tokens'].sum()

            current_tokens = bought + earned - sold - gas

            total_spent = coin_txs[coin_txs['Type'] == 'Buy Crypto']['USD_Value'].sum()
            dca = total_spent / (bought + earned) if (bought + earned) > 0 else 0

            sold_usd = coin_txs[coin_txs['Type'] == 'Sell Crypto']['USD_Value'].sum()
            invested_usd = total_spent - sold_usd

            coin_id = resolve_symbol(coin)
            if coin_id is None:
                with cols[j]:
                    st.error(f"Missing mapping for {coin}")
                continue

            live_price = live_prices_data.get(coin_id, {}).get('usd', 0.0)
            if not live_price or live_price == 0.0:
                with cols[j]:
                    st.error(f"Price lookup failed for {coin}")
                continue

            coin_usd_value = current_tokens * live_price

            with cols[j]:
                if is_private:
                    coin_display = "****"
                else:
                    coin_display = coin

                holdings_html = secure_val(current_tokens, is_currency=False, token_symbol=coin) if not is_private else '****'
                dca_html = secure_val(dca)
                live_html = secure_val(live_price)
                current_html = secure_val(coin_usd_value)

                invested_html = secure_val(invested_usd)
                pnl_value = coin_usd_value - invested_usd
                pnl_html = secure_val(pnl_value)
                pct = (pnl_value / invested_usd) if invested_usd != 0 else 0
                pct_html = f"{pct:+.2%}"

                if pct >= 0.20:
                    action_class = 'sell'
                    action_text = 'SELL'
                elif pct <= -0.20:
                    action_class = 'buy'
                    action_text = 'BUY'
                else:
                    action_class = 'watch'
                    action_text = 'See in Binance'

                text_color = "crimson" if pct < 0 else "greenyellow"

                trade_symbol = coin_display
                if str(coin).upper() == 'BEAM':
                    trade_symbol = 'BEAMX'

                trade_url = f"https://www.binance.com/es/trade/{trade_symbol}_USDT?type=spot"

                targets_data = _load_targets()
                saved_targets = targets_data.get(coin, {"buy": 20.0, "sell": 20.0})

                target_buy_key = f"target_buy_{coin}"
                target_sell_key = f"target_sell_{coin}"
                
                if target_buy_key not in st.session_state:
                    st.session_state[target_buy_key] = float(saved_targets.get("buy", 20.0))
                if target_sell_key not in st.session_state:
                    st.session_state[target_sell_key] = float(saved_targets.get("sell", 20.0))
                
                target_buy_pct = st.session_state[target_buy_key]
                target_sell_pct = st.session_state[target_sell_key]

                target_buy_price = dca * (1 - (target_buy_pct / 100))
                target_sell_price = dca * (1 + (target_sell_pct / 100))
                
                target_buy_html = secure_val(target_buy_price)
                target_sell_html = secure_val(target_sell_price)

                card_html = f"""
                <div class="coin-card">
                    <div class="coin-title" style="font-weight:bold; font-size:1.2rem; margin-bottom:8px;">{coin_display}</div>
                    <div class="coin-holdings">{holdings_html}</div>
                    <div><strong>Invested:</strong> {invested_html}</div>
                    <div class="coin-stats" style="margin-top:8px;">
                        <div><strong>DCA:</strong> {dca_html}</div>
                        <div><strong>Live Price:</strong> {live_html}</div>
                        <div><strong>Current Value:</strong> {current_html}</div>
                        <div><strong>P&L:</strong> {pnl_html} <small style="color: {text_color};">({pct_html})</small></div>
                        <div style="margin-top: 10px; padding-top: 10px; border-top: 1px solid rgba(255, 255, 255, 0.1);">
                            <div><strong>Target Buy (-{target_buy_pct:g}%):</strong> <span style="color: #ef4444;">{target_buy_html}</span></div>
                            <div><strong>Target Sell (+{target_sell_pct:g}%):</strong> <span style="color: #00ff9d;">{target_sell_html}</span></div>
                        </div>
                    </div>
                    <div style="margin-top:16px;">
                        <a class="trade-btn {action_class}" href="{trade_url}" target="_blank" rel="noopener">{action_text}</a>
                    </div>
                </div>
                """
                st.markdown(card_html, unsafe_allow_html=True)
                
                with st.expander(f"🎯 Set {coin_display} Targets"):
                    t_col1, t_col2 = st.columns(2)
                    with t_col1:
                        st.number_input(
                            "Buy Drop %", 
                            min_value=0.0, 
                            step=1.0, 
                            key=target_buy_key,
                            on_change=_on_target_change,
                            args=(coin,) # Passes the coin ticker to our auto-save function
                        )
                    with t_col2:
                        st.number_input(
                            "Sell Pump %", 
                            min_value=0.0, 
                            step=1.0, 
                            key=target_sell_key,
                            on_change=_on_target_change,
                            args=(coin,) # Passes the coin ticker to our auto-save function
                        )
                        
        st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

    st.divider()
    st.subheader("Global Portfolio")

    current_portfolio = fiat_balance + total_crypto_value
    net_fiat_invested = total_deposits - total_withdrawals
    pnl = current_portfolio - net_fiat_invested

    pc1, pc2, pc3, pc4 = st.columns(4)
    if is_private:
        pc1.metric("Fiat Balance (Idle Cash)", None)
        pc2.metric("Crypto Value", None)
        pc3.metric("Total Portfolio Value", None)
        pc4.metric("Total P&L", None, delta_color="normal")
    else:
        pc1.metric("Fiat Balance (Idle Cash)", f"${fiat_balance:,.2f}")
        pc2.metric("Crypto Value", f"${total_crypto_value:,.2f}")
        pc3.metric("Total Portfolio Value", f"${current_portfolio:,.2f}")
        pc4.metric("Total P&L", f"${pnl:,.2f}", delta_color="normal")

    st.divider()
    goal_target = 20000.00
    progress_fraction = min(current_portfolio / goal_target, 1.0)
    if is_private:
        st.write(f"**Apartment Goal Progress: *** / ${goal_target:,.0f}**")
    else:
        st.write(f"**Apartment Goal Progress: \\${current_portfolio:,.2f} / ${goal_target:,.2f}**")
        st.progress(progress_fraction)

    st.divider()
    with st.expander("View Raw Transaction History"):
        df_display = df.copy()
        df_display['Date'] = pd.to_datetime(df_display['Date'], format="%Y-%m-%d %H:%M:%S", errors='coerce')
        df_display = df_display.sort_values('Date', ascending=False)
        df_display = df_display.drop(columns=['_Tokens'])
        
        if is_private:
            df_display['Tokens'] = "***"
            df_display['USD_Value'] = "***"
            
        st.dataframe(df_display, width='stretch')

    with st.expander("Edit Coin Mapping"):
        mapping = _load_curated_ids()
        symbols = sorted(set(list(mapping.keys()) + ASSET_OPTIONS))
        sel = st.selectbox("Symbol", options=symbols, index=symbols.index('BTC') if 'BTC' in symbols else 0, key='map_symbol')
        current = mapping.get(sel, '')
        new_id = st.text_input("CoinGecko id", value=current if current is not None else '', key='map_id')
        if st.button("Save Mapping"):
            mapping[sel] = new_id.strip() if new_id.strip() != '' else None
            _save_curated_ids(mapping)
            st.success("Mapping saved")
            st.rerun()

else:
    st.info("👋 Welcome! No transactions found. Use the sidebar to deposit your first Fiat funds or buy Crypto.")