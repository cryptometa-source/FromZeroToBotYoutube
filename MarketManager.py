from pubsub import pub
from TokensApi import TokenInfo
from SolanaRpcApi import SolanaRpcApi
from RaydiumTokensMonitor import RaydiumTokensMonitor
import TokensApi as TokensApi
import Globals as globals

#Manage Tokem Market Activities
class MarketManager:
    def __init__(self, solana_rpc_api: SolanaRpcApi):
        self.ray_pool_monitor = RaydiumTokensMonitor(solana_rpc_api)
        pub.subscribe(topicName=globals.topic_token_update_event, listener=self._handle_token_update)

        self.ray_pool_monitor.start()

    def get_price(self, token_address: str):
        token_info = self.ray_pool_monitor.get_token_info(token_address)

        if token_info:
            return token_info.price
        else:
            # Get token information
            lp_data = TokensApi.get_amm_token_pool_data(token_address)

            return lp_data.price
    
    async def monitor_token(self, token_address: str):
        await self.ray_pool_monitor.monitor_token(token_address)

    def _handle_token_update(self, arg1: str):
        new_price = self.get_price(arg1)
        new_price_string = f"{new_price:.20f}"
        print(arg1 + " was updated! Price: " + new_price_string)