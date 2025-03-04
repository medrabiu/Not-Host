**# Not-Cotrader Bot**

**A Telegram bot for trading tokens on Solana and TON blockchains using decentralized exchanges (Jupiter for Solana, STON.fi for TON). Built with Python, it leverages `solana-py`, `solders`, and `tonutils` to manage wallets, fetch token info, and execute swaps.**

**## Features**

- **Wallet Management**: Generates and stores encrypted Solana and TON wallets.
- **Token Details**: Displays token info (price, liquidity, market cap) when a contract address is sent.
- **Buy Tokens**:
  - **Solana**: Swaps SOL to tokens via Jupiter DEX.
  - **TON**: Swaps TON to Jettons via STON.fi on mainnet.
- **User Interface**: Inline keyboards for slippage, amount, and trade execution.

**## Requirements**

- **Python 3.12+**
- **Dependencies**:
  ```bash
  pip install telegram-ext solana solders aiohttp tonutils-core pytoniq-core python-dotenv
TON API Key from tonconsole.com
Telegram Bot Token from BotFather
## Setup

Clone Repository:

bash
Copy
git clone <repository_url>
cd Not-Cotrader
Environment Variables: Create a .env file in the root directory:

env
Copy
TELEGRAM_TOKEN="your_telegram_bot_token"
TON_API_KEY="your_ton_api_key"
Load it in your shell:

bash
Copy
source .env
Install Dependencies:

bash
Copy
pip install -r requirements.txt
Database: Uses SQLite (bot.db) for wallet storage, initialized automatically.

## Usage

Start Bot:

bash
Copy
python bot/main.py
Commands:

/start: Displays trading menu.
Send a Solana or TON token address to view details and trade options.
Trading:

From /start > "Buy": Enter a token address, set amount/slippage, execute trade.
From token details: Use inline buttons to adjust and execute swaps.
Example:

Send EQCxE6mUtQJKFnGfaROTKOt1lZbDiiX1kCixRvHtdxyYphGV (TONCOIN-wrapped BTC).
Set amount (e.g., 0.05 TON), slippage (5%), click "Execute Trade".
## Architecture

### Directory Structure

graphql
Copy
Not-Cotrader/
├── bot/
│   ├── handlers/
│   │   ├── buy.py               # Buy handler for Solana/TON swaps
│   │   ├── token_details.py      # Token info display
│   │   ├── wallet.py             # Wallet management UI
│   │   └── ...                   # Other handlers (start, sell, etc.)
│   └── main.py                   # Bot entry point
├── blockchain/
│   ├── solana/
│   │   ├── trade.py              # Jupiter DEX swap logic
│   │   └── wallet.py             # Solana wallet generation
│   ├── ton/
│   │   ├── trade.py              # STON.fi swap logic
│   │   └── wallet.py             # TON wallet generation
├── services/
│   ├── crypto.py                # Encryption utilities
│   ├── token_info.py            # Token data fetching
│   ├── utils.py                 # Balance and USD value utils
│   └── wallet_management.py     # Wallet storage/retrieval
├── tests/
│   ├── test_solana_trade.py     # Unit tests for Solana swaps
│   └── test_ton_trade.py        # Unit tests for TON swaps
├── bot.db                       # SQLite database
├── .env                         # Environment variables
└── README.md                    # This file
### Key Components

Handlers: Manage Telegram interactions (e.g., buy.py for swaps).
Blockchain: Chain-specific logic (Solana: Jupiter, TON: STON.fi).
Services: Shared utilities (encryption, token info, wallet management).
Database: Stores user wallets (bot.db).
## Configuration

TON_API_KEY: Required for TON mainnet swaps via TonAPI.
TELEGRAM_TOKEN: Bot authentication with Telegram.
IS_TESTNET: Toggle in blockchain/ton/trade.py (currently False for mainnet).
## Edge Cases (Current Limitations)

Gas Fees: Fixed at 0.05 TON in total_amount; may need adjustment for complex swaps.
Output Amount: Uses min_amount_out as placeholder; actual token amount requires on-chain confirmation.
Retries: No retry logic for failed swaps (planned enhancement).
Limitations: Most of the limitations are due to free APIs and Public Mainnet API that influence speed and accuracy.
## Troubleshooting

"Invalid token schema": Ensure TON_API_KEY is set and valid.
"Insufficient TON": Fund wallet with >0.1 TON (swap + gas).
"Token not in wallet":
Check tx_hash on Tonscan.
Add Jetton manually in Tonkeeper (Settings > Add Token).
"Address mismatch": Revisit wallet generation alignment between tonsdk and tonutils.
"Token fetching and price updates": Check the logic to ensure tokens and price are fetched properly.
## Development

### Testing

Unit Tests:

bash
Copy
pytest -v tests/
Mainnet Testing:

Fund wallet with real TON (e.g., UQAGxZX19X2Q8vdemE9y1yUdJXWRgNiR8wIxohZO3shEdsAJ).
Use a mainnet Jetton (e.g., EQCxE6mUtQJKFnGfaROTKOt1lZbDiiX1kCixRvHtdxyYphGV).
Execute swap and verify on Tonscan.
### Contributing

Fork the repository, create a branch, and submit a pull request.
Follow PEP 8 style guidelines (flake8 recommended).
## Roadmap

Sell Handler: Implement token selling on Solana/TON (final touches).
Limit Orders: Add support for price-based trades (next release).
Real Output: Fetch actual swap output post-confirmation.
Error Retries: Add retry logic for transient failures.
Conversational Trading: Using LLMs to automate trades (currently in beta, read-only for now).
vbnet
Copy

Now the markdown is properly formatted for GitHub with appropriate heading styles, code blocks, and text formatting using `**`. This will ensure that everything is well structured and clear when you paste it into your repository.
You said:
give me actual real output markdown formatting 
ChatGPT said:
Certainly! Here's the correctly formatted markdown for actual output, using proper markdown syntax with code blocks, headings, lists, and other formatting elements:

markdown
Copy
# **Not-Cotrader Bot**

**A Telegram bot for trading tokens on Solana and TON blockchains using decentralized exchanges (Jupiter for Solana, STON.fi for TON). Built with Python, it leverages `solana-py`, `solders`, and `tonutils` to manage wallets, fetch token info, and execute swaps.**

## **Features**

- **Wallet Management**: Generates and stores encrypted Solana and TON wallets.
- **Token Details**: Displays token info (price, liquidity, market cap) when a contract address is sent.
- **Buy Tokens**:
  - **Solana**: Swaps SOL to tokens via Jupiter DEX.
  - **TON**: Swaps TON to Jettons via STON.fi on mainnet.
- **User Interface**: Inline keyboards for slippage, amount, and trade execution.

## **Requirements**

- **Python 3.12+**
- **Dependencies**:
  ```bash
  pip install telegram-ext solana solders aiohttp tonutils-core pytoniq-core python-dotenv
TON API Key from tonconsole.com
Telegram Bot Token from BotFather
Setup
Clone Repository:

bash
Copy
git clone <repository_url>
cd Not-Cotrader
Environment Variables: Create a .env file in the root directory:

env
Copy
TELEGRAM_TOKEN="your_telegram_bot_token"
TON_API_KEY="your_ton_api_key"
Load it in your shell:

bash
Copy
source .env
Install Dependencies:

bash
Copy
pip install -r requirements.txt
Database: Uses SQLite (bot.db) for wallet storage, initialized automatically.

Usage
Start Bot:

bash
Copy
python bot/main.py
Commands:

/start: Displays trading menu.
Send a Solana or TON token address to view details and trade options.
Trading:

From /start > "Buy": Enter a token address, set amount/slippage, execute trade.
From token details: Use inline buttons to adjust and execute swaps.
Example:

Send EQCxE6mUtQJKFnGfaROTKOt1lZbDiiX1kCixRvHtdxyYphGV (TONCOIN-wrapped BTC).
Set amount (e.g., 0.05 TON), slippage (5%), click "Execute Trade".
Architecture
Directory Structure
plaintext
Copy
Not-Cotrader/
├── bot/
│   ├── handlers/
│   │   ├── buy.py               # Buy handler for Solana/TON swaps
│   │   ├── token_details.py      # Token info display
│   │   ├── wallet.py             # Wallet management UI
│   │   └── ...                   # Other handlers (start, sell, etc.)
│   └── main.py                   # Bot entry point
├── blockchain/
│   ├── solana/
│   │   ├── trade.py              # Jupiter DEX swap logic
│   │   └── wallet.py             # Solana wallet generation
│   ├── ton/
│   │   ├── trade.py              # STON.fi swap logic
│   │   └── wallet.py             # TON wallet generation
├── services/
│   ├── crypto.py                # Encryption utilities
│   ├── token_info.py            # Token data fetching
│   ├── utils.py                 # Balance and USD value utils
│   └── wallet_management.py     # Wallet storage/retrieval
├── tests/
│   ├── test_solana_trade.py     # Unit tests for Solana swaps
│   └── test_ton_trade.py        # Unit tests for TON swaps
├── bot.db                       # SQLite database
├── .env                         # Environment variables
└── README.md                    # This file
Key Components
Handlers: Manage Telegram interactions (e.g., buy.py for swaps).
Blockchain: Chain-specific logic (Solana: Jupiter, TON: STON.fi).
Services: Shared utilities (encryption, token info, wallet management).
Database: Stores user wallets (bot.db).
Configuration
TON_API_KEY: Required for TON mainnet swaps via TonAPI.
TELEGRAM_TOKEN: Bot authentication with Telegram.
IS_TESTNET: Toggle in blockchain/ton/trade.py (currently False for mainnet).
Edge Cases (Current Limitations)
Gas Fees: Fixed at 0.05 TON in total_amount; may need adjustment for complex swaps.
Output Amount: Uses min_amount_out as placeholder; actual token amount requires on-chain confirmation.
Retries: No retry logic for failed swaps (planned enhancement).
Limitations: Most of the limitations are due to free APIs and Public Mainnet API that influence speed and accuracy.
Troubleshooting
"Invalid token schema": Ensure TON_API_KEY is set and valid.
"Insufficient TON": Fund wallet with >0.1 TON (swap + gas).
"Token not in wallet":
Check tx_hash on Tonscan.
Add Jetton manually in Tonkeeper (Settings > Add Token).
"Address mismatch": Revisit wallet generation alignment between tonsdk and tonutils.
"Token fetching and price updates": Check the logic to ensure tokens and price are fetched properly.
Development
Testing
Unit Tests:

bash
Copy
pytest -v tests/
Mainnet Testing:

Fund wallet with real TON (e.g., UQAGxZX19X2Q8vdemE9y1yUdJXWRgNiR8wIxohZO3shEdsAJ).
Use a mainnet Jetton (e.g., EQCxE6mUtQJKFnGfaROTKOt1lZbDiiX1kCixRvHtdxyYphGV).
Execute swap and verify on Tonscan.
Contributing
Fork the repository, create a branch, and submit a pull request.
Follow PEP 8 style guidelines (flake8 recommended).
Roadmap
Sell Handler: Implement token selling on Solana/TON (final touches).
Limit Orders: Add support for price-based trades (next release).
Real Output: Fetch actual swap output post-confirmation.
Error Retries: Add retry logic for transient failures.
Conversational Trading: Using LLMs to automate trades (currently in beta, read-only for now).
