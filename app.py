import streamlit as st
import pandas as pd
import requests
import json
from decimal import Decimal
import os
import time

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

def get_live_price(coin_id="bitcoin"):
    try:
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={coin_id}&vs_currencies=usd"
        response = requests.get(url).json()
        return response[coin_id]['usd']
    except Exception:
        return 0.0

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


def resolve_symbol(symbol: str) -> str | None:
    return _CURATED_IDS.get(symbol.upper())

st.set_page_config(page_title="Crypto & Fiat Tracker", layout="wide")
st.title("📊 Personal Portfolio Tracker")

if 'tx_type' not in st.session_state:
    st.session_state['tx_type'] = 'Deposit Fiat'
if 'asset' not in st.session_state:
    st.session_state['asset'] = 'BTC'
if 'tokens' not in st.session_state:
    st.session_state['tokens'] = 0.0
if 'usd_value' not in st.session_state:
    st.session_state['usd_value'] = 0.0
if st.session_state.get('should_reset'):
    st.session_state['tx_type'] = 'Deposit Fiat'
    st.session_state['asset'] = 'BTC'
    st.session_state['tokens'] = 0.0
    st.session_state['usd_value'] = 0.0
    st.session_state.pop('should_reset', None)

with st.sidebar:
    st.header("➕ New Transaction")

    tx_type = st.selectbox(
        "Transaction Type",
        ["Deposit Fiat", "Withdraw Fiat", "Buy Crypto", "Sell Crypto", "Earn (Staking)", "Gas (Fee)"],
        key='tx_type'
    )

    if tx_type in ["Deposit Fiat", "Withdraw Fiat"]:
        asset = "USD"
        tokens = 0.0
        usd_value = st.number_input("Amount (USD)", min_value=0.0, format="%.2f", key='usd_value')
    else:
        ASSET_OPTIONS = ["BTC", "ETH", "SOL", "WBETH", "PAXG", "BNSOL", "BNB", "0G", "BEAM"]
        default_asset = st.session_state.get('asset', 'BTC')
        default_index = ASSET_OPTIONS.index(default_asset) if default_asset in ASSET_OPTIONS else 0
        asset = st.selectbox("Asset Ticker", options=ASSET_OPTIONS, index=default_index, key='asset')
        tokens = st.number_input("Quantity of Tokens", min_value=0.0, format="%.9f", step=0.000000001, key='tokens')

        if tx_type in ["Earn (Staking)", "Gas (Fee)"]:
            usd_value = 0.0
            st.info(f"Cost basis is automatically $0 for {tx_type}.")
        else:
            usd_value = st.number_input("Total USD Value of Trade", min_value=0.0, format="%.2f", key='usd_value')

    if st.button("Save Transaction"):
        # read current widget values from session_state where appropriate
        tokens_val = st.session_state.get('tokens', tokens) if 'tokens' in st.session_state else tokens
        asset_val = st.session_state.get('asset', asset) if 'asset' in st.session_state else asset
        usd_val = st.session_state.get('usd_value', usd_value) if 'usd_value' in st.session_state else usd_value

        tokens_str = _format_token_str(tokens_val) if isinstance(tokens_val, (int, float)) else str(tokens_val)
        new_tx = pd.DataFrame({
            'Date': [pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")],
            'Type': [tx_type],
            'Asset': [asset_val],
            'Tokens': [tokens_str],
            'USD_Value': [usd_val]
        })

        df = load_data()
        df = pd.concat([df, new_tx], ignore_index=True)
        save_data(df)
        st.session_state['should_reset'] = True
        placeholder = st.empty()
        placeholder.success("Transaction saved successfully!")
        time.sleep(.5)
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

    crypto_assets = df[(df['Asset'] != 'USD')]['Asset'].unique()

    total_crypto_value = 0.0

    cols = st.columns(len(crypto_assets)) if len(crypto_assets) > 0 else st.columns(1)

    for i, coin in enumerate(crypto_assets):
        coin_txs = df[df['Asset'] == coin]

        bought = coin_txs[coin_txs['Type'] == 'Buy Crypto']['_Tokens'].sum()
        earned = coin_txs[coin_txs['Type'] == 'Earn (Staking)']['_Tokens'].sum()
        sold = coin_txs[coin_txs['Type'] == 'Sell Crypto']['_Tokens'].sum()
        gas = coin_txs[coin_txs['Type'] == 'Gas (Fee)']['_Tokens'].sum()

        current_tokens = bought + earned - sold - gas

        total_spent = coin_txs[coin_txs['Type'] == 'Buy Crypto']['USD_Value'].sum()
        dca = total_spent / (bought + earned) if (bought + earned) > 0 else 0

        coin_id = resolve_symbol(coin)
        if coin_id is None:
            with cols[i]:
                st.error("Sorry, something's wrong with CoinGecko or the local mapping; update coinlist-ids.json")
            continue

        live_price = get_live_price(coin_id)
        if not live_price or live_price == 0.0:
            with cols[i]:
                st.error("Sorry, CoinGecko price lookup failed; try again later")
            continue

        coin_usd_value = current_tokens * live_price
        total_crypto_value += coin_usd_value

        with cols[i]:
            st.metric(f"{coin} Holdings", f"{current_tokens:.4f} {coin}")
            st.write(f"**DCA:** ${dca:,.2f}")
            st.write(f"**Live Price:** ${live_price:,.2f}")
            st.write(f"**Current Value:** ${coin_usd_value:,.2f}")

    st.divider()
    st.subheader("Global Portfolio")

    current_portfolio = fiat_balance + total_crypto_value
    net_fiat_invested = total_deposits - total_withdrawals
    pnl = current_portfolio - net_fiat_invested

    pc1, pc2, pc3, pc4 = st.columns(4)
    pc1.metric("Fiat Balance (Idle Cash)", f"${fiat_balance:,.2f}")
    pc2.metric("Crypto Value", f"${total_crypto_value:,.2f}")
    pc3.metric("Total Portfolio Value", f"${current_portfolio:,.2f}")
    pc4.metric("Total P&L", f"${pnl:,.2f}", delta_color="normal")

    st.write("---")
    goal_target = 20000.00
    progress_fraction = min(current_portfolio / goal_target, 1.0)
    st.write(f"**Apartment Goal Progress: ${current_portfolio:,.2f} / ${goal_target:,.0f}**")
    st.progress(progress_fraction)

    st.write("---")
    with st.expander("View Raw Transaction History"):
        df_display = df.copy()
        df_display['Date'] = pd.to_datetime(df_display['Date'], format="%Y-%m-%d %H:%M:%S", errors='coerce')
        df_display = df_display.sort_values('Date', ascending=False)
        df_display = df_display.drop(columns=['_Tokens'])
        st.dataframe(df_display, use_container_width=True)

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
            st.experimental_rerun()

else:
    st.info("👋 Welcome! No transactions found. Use the sidebar to deposit your first Fiat funds or buy Crypto.")