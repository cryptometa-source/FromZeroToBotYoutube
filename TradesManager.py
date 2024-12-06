import threading
import TokensApi as TokensApi
import base64
from TradingDTOs import *
from TransactionChecker import TransactionChecker
from MarketManager import MarketManager
from SolanaRpcApi import SolanaRpcApi
from PnlTradingEngine import PnlTradingEngine
from solders.keypair import Keypair
from solders.transaction import VersionedTransaction

c_default_swap_retries = 5

class TradesManager(OrderExecutor):
    def __init__(self, keys_hash: str, solana_rpc_api: SolanaRpcApi, market_manager: MarketManager):
        OrderExecutor.__init__(self, market_manager)
        self.signer_wallet = Keypair.from_base58_string(keys_hash)
        self.signer_pubkey = str(self.signer_wallet.pubkey())
        self.solana_api_rpc = solana_rpc_api
        self.market_manager = market_manager
        self.active_trades : dict[int, PnlTradingEngine] = {} #Key=Trade Count
        self.token_account_dict : dict[str, TokenAccountInfo] = {} #Key=token_address; Associated token accounts for this signer
        self.sol_balance = Amount.sol_ui(0)
        self.active_trade_count = 0
        
        self._update_account_balance(self.signer_pubkey)

    async def execute_order(self, order: Order, retry_until_successful = False)->str:
        tx_signature = None
        token_info = self.market_manager.get_token_info(order.token_address)

        if token_info:
            if order.order_type == Order_Type.BUY or order.order_type == Order_Type.SELL:
                if order.order_type == Order_Type.BUY:
                    in_token_address = token_info.sol_address
                    out_token_address = order.token_address
                elif order.order_type == Order_Type.SELL:
                    in_token_address = order.token_address
                    out_token_address = token_info.sol_address

                should_try = True

                while should_try:
                    tx_signature = self._swap(in_token_address, out_token_address, order.amount, order.slippage, order.priority_fee, order.confirm_transaction)

                    if tx_signature or not retry_until_successful:
                         should_try = False
            else:
                await self.market_manager.monitor_token(order.token_address)
                trade_strategy = self.create_strategy(token_info=token_info, order_executor=self, order=order)
                trade_strategy.start()
                
                self.active_trades[self.active_trade_count] = trade_strategy
                self.active_trade_count += 1

        return tx_signature
    
    @staticmethod
    def create_strategy(token_info: TokenInfo, order_executor: OrderExecutor, order: Order)->PnlTradingEngine:
         if order.order_type == Order_Type.LIMIT_STOP_ORDER and isinstance(order, OrderWithLimitsStops):
            return PnlTradingEngine(token_info, order_executor, order)
         
    def buy(self, token_address: str, buy_amount: int, slippage: int, priority_fee: int, confirm_transaction = True):
        token_info = self.market_manager.get_token_info(token_address)

        return self._swap(token_info.sol_address, token_address, buy_amount, slippage, priority_fee, confirm_transaction)
    
    def sell(self, token_address: str, sell_amount: int, slippage: int, priority_fee: int, confirm_transaction = True):
        token_info = self.market_manager.get_token_info(token_address)

        return self._swap(token_address, token_info.sol_address, sell_amount, slippage, priority_fee, confirm_transaction)
    
    def _swap(self, in_token_address: str, out_token_address: str, amount: Amount, slippage: Amount, priority_fee: Amount, confirm_transaction):
        ret_val = None
        swap_transaction = TokensApi.get_swap_transaction(self.signer_pubkey, in_token_address, out_token_address, amount.ToScaledValue(), slippage.ToScaledValue(), priority_fee.ToScaledValue())

        if swap_transaction:
            raw_bytes = base64.b64decode(swap_transaction)
            raw_tx = VersionedTransaction.from_bytes(raw_bytes)

            signed_transaction = VersionedTransaction(raw_tx.message, [self.signer_wallet])

            if signed_transaction:
                transaction_checker :TransactionChecker = None
                try: 
                    tx_signature = str(signed_transaction.signatures[0])

                    if confirm_transaction:
                        transaction_checker = TransactionChecker(self.solana_api_rpc, tx_signature)
                        transaction_checker.start()
                    else:
                        ret_val = tx_signature
                    
                    for i in range(c_default_swap_retries):
                        print("Try #" + str(i+1))

                        self.solana_api_rpc.send_transaction(signed_transaction)                                                                
                except Exception as e:                    
                    print(tx_signature + " transaction failed to process: " + str(e))

                if transaction_checker and transaction_checker.wait_for_success(timeout=35):
                    ret_val = tx_signature       

        return ret_val
    
    def _update_account_balance(self, contract_address: str):
        if contract_address == self.signer_pubkey:
            new_sol_balance = self.solana_api_rpc.get_account_balance(self.signer_pubkey)
            self.sol_balance.set_amount(new_sol_balance/1E9)
        else:
            token_account_info : TokenAccountInfo = None

            if contract_address not in self.token_account_dict:
                token_info = self.market_manager.get_token_info(contract_address)

                if token_info:
                    token_account_address = self.solana_api_rpc.get_associated_token_account_address(self.signer_pubkey, contract_address)
                    tokens_amount = Amount.tokens_ui(0, token_info.decimals_scale_factor)
                    token_account_info = TokenAccountInfo(contract_address, token_account_address, tokens_amount)

                    self.token_account_dict[contract_address] = token_account_info
            else:
                token_account_info = self.token_account_dict[contract_address]
        
            if token_account_info:
                new_balance = self.solana_api_rpc.get_token_account_balance(token_account_info.token_account_address)

                if new_balance:
                    print(f"New Balance={new_balance}")
                    token_account_info.balance.set_amount(new_balance)

    def get_order_transaction(self, tx_signature)-> SwapTransactionInfo:
        return self.market_manager.get_swap_info(tx_signature, self.signer_pubkey, 30)

    def get_account_balance(self, contract_address: str)->Amount:
        self._update_account_balance(contract_address)

        if contract_address == self.signer_pubkey:
            return self.sol_balance   
        elif contract_address in self.token_account_dict:
            return self.token_account_dict[contract_address].balance