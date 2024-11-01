from MarketManager import MarketManager
from SolanaRpcApi import SolanaRpcApi
from TradesManager import TradesManager
import os
import asyncio

def make_trade(market_manager: MarketManager, trades_manager: TradesManager, token_address, amount: int, slippage, is_buy: bool):
    did_succeed = False
    transaction_info = None

    while not did_succeed:
        if is_buy:
            tx_signature = trades_manager.buy(token_address, amount, slippage)
        else:
            tx_signature = trades_manager.sell(token_address, amount, slippage)

        if tx_signature:
            did_succeed = True

            transaction_info = market_manager.get_swap_info(tx_signature, trades_manager.signer_pubkey, 40)

            if transaction_info:
                transaction_info.print_swap_info()
            
                
    return transaction_info            

async def main():
    http_uri = os.getenv('http_rpc_uri')
    wss_uri = os.getenv('wss_rpc_uri')
    keys_hash = os.getenv('payer_hash')

    if keys_hash:
        solana_rpc_api = SolanaRpcApi(http_uri, wss_uri)
        market_manager = MarketManager(solana_rpc_api)
        trades_manager = TradesManager(keys_hash, solana_rpc_api, market_manager)

        user_input = input("Enter a token address to trade: ")

        buy_amount = int(.001*1e9)
        slippage = int(5000)
       
        print("Buying tokens")
        transaction_info = make_trade(market_manager, trades_manager, user_input, buy_amount, slippage, True)

        if transaction_info:
            print("Selling tokens")
            sell_amount = int(abs(transaction_info.payer_token_balance*1e6))
            transaction_info = make_trade(market_manager, trades_manager, user_input, sell_amount, slippage, False)

        #await market_manager.monitor_token(user_input)
        #market_manager.ray_pool_monitor.join()

asyncio.run(main())
