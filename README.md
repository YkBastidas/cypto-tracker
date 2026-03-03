# Crypto & Fiat Tracker

Simple personal portfolio tracker built with Streamlit. Tracks fiat deposits/withdrawals and crypto transactions, preserves token formatting as entered, and fetches live prices using CoinGecko IDs from a curated mapping file.

Getting started

- Prerequisites: Python 3.10+ and pip
- Install dependencies:

```bash
pip install -r requirements.txt
```

- Run the app:

```bash
streamlit run app.py
```

Notes

- Edit `coinlist-ids.json` from the app (Edit Coin Mapping) to add or correct symbol→CoinGecko id mappings.
- Tokens are stored in `portfolio.csv` as the original string users entered; an internal numeric column is used for calculations.
- Use the `🙈 Hide Balances` toggle to mask monetary values locally (frontend-only).

Configuration

- Optionally set an API key in a `.env` file as `API_KEY`

License

This project is licensed under the MIT License — see `LICENSE`.

