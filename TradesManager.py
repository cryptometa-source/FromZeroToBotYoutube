import threading
import TokensApi as TokensApi
import base64
from TransactionChecker import TransactionChecker
from MarketManager import MarketManager
from SolanaRpcApi import SolanaRpcApi
from solders.keypair import Keypair
from solders.transaction import VersionedTransaction

c_default_swap_retries = 5

class TradesManager(threading.Thread):
    def __init__(self, keys_hash: str, solana_rpc_api: SolanaRpcApi, market_manager: MarketManager):
        threading.Thread.__init__(self)
        self.signer_wallet = Keypair.from_base58_string(keys_hash)
        self.signer_pubkey = str(self.signer_wallet.pubkey())
        self.solana_api_rpc = solana_rpc_api
        self.market_manager = market_manager

    def buy(self, token_address: str, buy_amount: int, slippage: int, confirm_transaction = True):
        token_info = self.market_manager.get_token_info(token_address)

        return self._swap(token_info.sol_address, token_address, buy_amount, slippage, confirm_transaction)
    
    def sell(self, token_address: str, sell_amount: int, slippage: int, confirm_transaction = True):
        token_info = self.market_manager.get_token_info(token_address)

        return self._swap(token_address, token_info.sol_address, sell_amount, slippage, confirm_transaction)
    
    def _swap(self, in_token_address, out_token_address, amount, slippage, confirm_transaction):
        ret_val = None
        swap_transaction = TokensApi.get_swap_transaction(self.signer_pubkey, in_token_address, out_token_address, amount, slippage)

        if swap_transaction:
            raw_bytes = base64.b64decode(swap_transaction)
            raw_tx = VersionedTransaction.from_bytes(raw_bytes)

            signed_transaction = VersionedTransaction(raw_tx.message, [self.signer_wallet])

            if signed_transaction:
                try: 
                    tx_signature = str(signed_transaction.signatures[0])

                    if confirm_transaction:
                        transaction_checker = TransactionChecker(self.solana_api_rpc, tx_signature)
                        transaction_checker.start()
                    else:
                        ret_val = tx_signature
                    
                    for i in range(c_default_swap_retries):
                        print("Try #" + str(i+1))

                        self.solana_api_rpc.send_transaction(signed_transaction, 10)

                        #if confirm_transaction and transaction_checker.wait_for_success(timeout=5):
                        #    ret_val = tx_signature
                        #    break
                                                                
                except Exception as e:                    
                    print(tx_signature + " transaction failed to process: " + str(e))

        if transaction_checker and transaction_checker.wait_for_success(timeout=35):
            ret_val = tx_signature       

        return ret_val