import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from blockchain.ton.trade import execute_ton_swap
from services.crypto import CIPHER

class MockWallet:
    def __init__(self):
        self.public_key = "UQAGxZX19X2Q8vdemE9y1yUdJXWRgNiR8wIxohZO3shEdsAJ"
        self.encrypted_private_key = "mock_encrypted_mnemonic"  # Match actual type

@pytest.mark.asyncio
async def test_execute_ton_swap_success():
    mock_wallet = MockWallet()
    mnemonic = " ".join(["word"] * 24)
    with patch.object(CIPHER, "decrypt", return_value=mnemonic):  # Return string, not bytes
        with patch("tonutils.wallet.WalletV4R2.from_mnemonic", return_value=(MagicMock(), None, None, None)) as mock_wallet_init:
            mock_wallet_instance = mock_wallet_init.return_value[0]
            mock_wallet_instance.transfer = AsyncMock(return_value="mock_tx_hash")
            with patch("tonutils.jetton.dex.stonfi.StonfiRouterV1.get_swap_ton_to_jetton_tx_params", 
                       AsyncMock(return_value=("to_address", 50000000, "body"))):
                result = await execute_ton_swap(
                    mock_wallet,
                    "EQCxE6mUtQJKFnGfaROTKOt1lZbDiiX1kCixRvHtdxyYphGV",
                    0.05,
                    50
                )
                assert result["tx_id"] == "mock_tx_hash"
                assert result["output_amount"] == 49875000

@pytest.mark.asyncio
async def test_execute_ton_swap_decryption_failure():
    mock_wallet = MockWallet()
    with patch.object(CIPHER, "decrypt", side_effect=Exception("Decryption failed")):
        with pytest.raises(Exception, match="Failed to execute TON swap via STON.fi: Decryption failed"):
            await execute_ton_swap(mock_wallet, "EQCx...", 0.05, 50)