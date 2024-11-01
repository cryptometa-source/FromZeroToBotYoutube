from MarketManager import MarketManager
from SolanaRpcApi import SolanaRpcApi
import asyncio

async def main():
    http_uri = "https://mainnet.helius-rpc.com/?api-key=9addcdb7-6766-4bcb-ac9a-941c90850174"
    wss_uri = "wss://mainnet.helius-rpc.com/?api-key=9addcdb7-6766-4bcb-ac9a-941c90850174"

    solana_rpc_api = SolanaRpcApi(http_uri, wss_uri)
    market_manager = MarketManager(solana_rpc_api)

    user_input = input("Enter a token address to monitor: ")

    await market_manager.monitor_token(user_input)

    market_manager.ray_pool_monitor.join()

asyncio.run(main())
