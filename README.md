# Not-Cotrader Bot

A multi-chain trading bot for Telegram, enabling fast and seamless token swaps on TON (via STON.fi) and Solana (via Jupiter DEX). Built for traders who value speed, simplicity, and control, Not-Cotrader offers wallet management, token information, and a streamlined trading experience.

## Table of Contents
- [Overview](#overview)
- [Features](#features)
- [Requirements](#requirements)
- [Installation](#installation)
- [Usage](#usage)
- [Project Structure](#project-structure)
- [Contributing](#contributing)
- [License](#license)
- [Acknowledgments](#acknowledgments)

## Overview
Not-Cotrader is a Telegram bot designed to facilitate cryptocurrency trading across multiple blockchains, currently supporting TON and Solana. It integrates with STON.fi for TON swaps and Jupiter DEX for Solana swaps, providing users with a unified interface to buy tokens, manage wallets, and explore trading options. The bot is built with Python, leveraging the `telegram.ext` library for Telegram integration, `tonutils` for TON blockchain operations, and `solders` for Solana interactions.

This project was developed as a submission, showcasing a functional trading bot with a focus on user experience and multi-chain compatibility.

## Features
- **Multi-Chain Trading**: Swap tokens on TON (STON.fi) and Solana (Jupiter DEX).(fall backs coming soon)
- **Wallet Management**: Automatically generate TON and Solana wallets for new users, with balance display and deposit options.
- **Token Information**: Fetch and display detailed token info (e.g., price, market cap, liquidity).
- **Settings**: Configure chain-specific preferences (gas fee, notifications, wallet format, currency).
- **Trading Interface**: Intuitive menu with Buy, Sell, Positions, PnL, Token List, and more (some features in AI Mode preview).
- **Conversation Flow**: Streamlined buy process with manual amount and slippage settings.
- **Error Handling**: Robust exception handling with user-friendly feedback.

## Requirements
- Python 3.12+
- Telegram Bot Token (get from `@BotFather`)
- TON API Key (from [tonconsole.com](https://tonconsole.com))
- **Dependencies**:
  - `telegram[all]`
  - `tonutils-core`
  - `pytoniq-core`
  - `solders`
  - `aiohttp`
  - `cryptography`

## Installation
1. **Clone the Repository**:
   ```bash
   git clone https://github.com/yourusername/not-cotrader.git
   cd not-cotrader
  ### Set Up Virtual Environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

TELEGRAM_TOKEN="your_telegram_bot_token"
TON_API_KEY="your_ton_api_key"


Alternatively, set these as environment variables:

```bash
export TELEGRAM_TOKEN="your_telegram_bot_token"
export TON_API_KEY="your_ton_api_key"
```


## initialize The DB

```bash
python init.py
```

## Run the Bot:

```bash
python bot/main.py
```

## Usage
Start the Bot:
In Telegram, send /start to the bot.

**New users**: Agree to terms, set up wallets, and access the trading menu.

**Returning users**: See wallet balances and the trading menu directly.

### Main Menu:
- **Buy**: Enter a token address, set amount and slippage, execute a trade.
- **Sell**: (Coming soon) Sell tokens from your wallet.
- **Positions**: View sample trading positions (AI Mode preview).
- **PnL**: Check simulated profit and loss (AI Mode preview).
- **Token List**: Browse a sample token list (AI Mode preview).
- **Orders**: (Coming soon) Manage open orders.
- **Wallet**: View wallet addresses and balances.
- **Settings**: Adjust gas fees, notifications, wallet format, and currency for TON/Solana.
- **Feedback**: (Coming soon) Provide feedback.
- **Help**: Get bot info and support contact (`@aystek`).

### Example Buy Flow:
1. Click "Buy" from the main menu.
2. Send a token address (e.g., `EQCxE6mUtQJKFnGfaROTKOt1lZbDiiX1kCixRvHtdxyYphGV` for TON).
3. Adjust amount (e.g., `1.5 TON`) and slippage (e.g., `5%`), then execute the trade.

### Project Structure
```bash
not-cotrader/
├── bot/
│   ├── handlers/
│   │   ├── buy.py         # Buy conversation handler
│   │   ├── help.py        # Help message handler
│   │   ├── positions.py   # Positions preview handler
│   │   ├── pnl.py         # PnL preview handler
│   │   ├── sell.py        # Sell handler (placeholder)
│   │   ├── settings.py    # Chain-specific settings handler
│   │   ├── start.py       # Start and wallet setup handler
│   │   ├── token_details.py # Token info handler
│   │   ├── token_list.py  # Token list preview handler
│   │   ├── wallet.py      # Wallet management handler
│   ├── main.py            # Bot entry point and handler registration
│   ├── __init__.py        # Initialize db
├── blockchain/
│   ├── solana/
│   │   ├── trade.py      # Solana swap logic (Jupiter DEX)
│   │   ├── token.py      # Solana token utilities
│   │   ├── wallet.py     # Solana wallet creation
│   │   ├── utils.py      # Solana utilities
│   ├── ton/
│   │   ├── trade.py      # TON swap logic (STON.fi)
│   │   ├── token.py      # TON token utilities
│   │   ├── wallet.py     # TON wallet creation
│   │   ├── utils.py      # TON utilities
├── database/
│   ├── db.py             # Database session and models
├── services/
│   ├── crypto.py         # Encryption utilities
│   ├── token_info.py     # Token info fetching and formatting
│   ├── utils.py          # General utilities (e.g., balance fetching)
│   ├── wallet_management.py # Wallet CRUD operations
├── tests/                # Test cases (incomplete)
├── requirements.txt      # Project dependencies
├── .env                  # Environment variables (not tracked)
├── README.md             # This file
```

## Contributing
Contributions are welcome! To contribute:

1. Fork the repository.
2. Create a feature branch (`git checkout -b feature/your-feature`).
3. Commit changes (`git commit -m "Add your feature"`).
4. Push to the branch (`git push origin feature/your-feature`).
5. Open a pull request.

Please ensure code follows PEP 8 and includes relevant tests (though tests are currently incomplete due to time constraints).

## License
This project is licensed under the MIT License. See the `LICENSE` file for details.

## Acknowledgments
- **STON.fi**: TON decentralized exchange integration.
- **Jupiter DEX**: Solana decentralized exchange integration.
- **Telegram**: Platform for bot deployment.
- **Contributors**: `@aystek` (support contact).
-- **The Notcoin team**: for the push 