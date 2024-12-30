from MarketManager import MarketManager
from SolanaRpcApi import SolanaRpcApi
from TradesManager import TradesManager
from TradingDTOs import *
import os
import asyncio
import json

default_buy_amount = Amount.sol_ui(.001)
default_slippage = Amount.percent_ui(50)
default_priority_fee = Amount.sol_ui(.0004)

async def main():
    http_uri = os.getenv('http_rpc_uri')
    wss_uri = os.getenv('wss_rpc_uri')
    keys_hash = os.getenv('payer_hash')

    if keys_hash:   
        solana_rpc_api = SolanaRpcApi(http_uri, wss_uri)
        market_manager = MarketManager(solana_rpc_api)
        trades_manager = TradesManager(keys_hash, solana_rpc_api, market_manager)    
        
        with open(r'config\strategies.json', 'r') as file:
            strategies = json.load(file)

            if strategies:
                for strategy_settings in strategies:
                    token_address = strategy_settings.get("token_address", "NA")
                    module_filename = strategy_settings.get("module_filename", "NA")

                    if token_address != "NA" and module_filename == "SimpleBuyDipEngine.py":
                        strategy_order = StrategyOrder(Order_Type.SIMPLE_BUY_DIP_STRATEGY, token_address, default_buy_amount, 
                                                       default_slippage, default_priority_fee, strategy_settings)
                        
                        trades_manager.execute_order(strategy_order)

                        trades_manager.market_manager.ray_pool_monitor.join()

asyncio.run(main())