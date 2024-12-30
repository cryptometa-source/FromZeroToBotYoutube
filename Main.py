from MarketManager import MarketManager
from SolanaRpcApi import SolanaRpcApi
from TradesManager import TradesManager
from TradingDTOs import *
import os
import asyncio

sol_buy_amount = Amount.sol_ui(.001)
slippage = Amount.percent_ui(50)
priority_fee = Amount.sol_ui(.0004)
profit_limit = PnlOption(trigger_at_percent = Amount.percent_ui(600), allocation_percent = Amount.percent_ui(100))
stop_loss = PnlOption(trigger_at_percent = Amount.percent_ui(-80), allocation_percent = Amount.percent_ui(100))

async def main():
    http_uri = os.getenv('http_rpc_uri')
    wss_uri = os.getenv('wss_rpc_uri')
    keys_hash = os.getenv('payer_hash')

    if keys_hash:
        solana_rpc_api = SolanaRpcApi(http_uri, wss_uri)
        market_manager = MarketManager(solana_rpc_api)
        trades_manager = TradesManager(keys_hash, solana_rpc_api, market_manager)

        while True:
            token_address = input("Enter a token address to trade: ")

            order = Order(Order_Type.BUY, token_address, sol_buy_amount, slippage, priority_fee)

            tx_signature = trades_manager.execute_order(order, True)
            token_info = market_manager.get_token_info(token_address)
            transaction_info = trades_manager.get_order_transaction(tx_signature)

            if transaction_info and transaction_info.token_diff > 0:
                temp_calc = abs(transaction_info.sol_diff/transaction_info.token_diff)   
                base_token_price = Amount.sol_ui(temp_calc/1E9)
                tokens_bought = Amount.tokens_ui(transaction_info.token_diff, token_info.decimals_scale_factor)

                order = OrderWithLimitsStops(token_address, base_token_price, tokens_bought, slippage, priority_fee)
                order.add_pnl_option(profit_limit)
                order.add_pnl_option(stop_loss)

                trades_manager.execute_order(order, True)

                market_manager.ray_pool_monitor.join()

asyncio.run(main())
