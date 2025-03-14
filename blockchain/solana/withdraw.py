# blockchain/solana/withdraw.py
from solders.keypair import Keypair
from solana.rpc.async_api import AsyncClient
from solana.transaction import Transaction
from spl.token.instructions import transfer, TransferParams

async def send_solana_transaction(keypair: Keypair, destination: str, lamports: int) -> str:
    client = AsyncClient("https://api.mainnet-beta.solana.com")
    tx = Transaction().add(
        transfer(TransferParams(
            source=keypair.pubkey(),
            dest=destination,
            owner=keypair.pubkey(),
            amount=lamports
        ))
    )
    resp = await client.send_transaction(tx, keypair)
    await client.close()
    return resp["result"]