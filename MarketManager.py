from pubsub import pub
from TradingDTOs import *
from SolanaRpcApi import SolanaRpcApi
from RaydiumTokensMonitor import RaydiumTokensMonitor
from Candlesticks import *
import TokensApi as TokensApi
import Globals as globals
import time

#Manage Tokem Market Activities
class MarketManager(AbstractMarketManager):
    def __init__(self, solana_rpc_api: SolanaRpcApi):
        self.ray_pool_monitor = RaydiumTokensMonitor(solana_rpc_api)

        self.solana_rpc_api = solana_rpc_api
        self.default_chart_intervals = [1, 60] #Keep 1-second, 1-minute  candlesticks; adjust as required
        self.candlesticks : dict[str, Candlesticks]= {}

        self.ray_pool_monitor.start()
        pub.subscribe(topicName=globals.topic_token_update_event, listener=self._handle_token_update)

    def get_token_info(self, token_address:str)->TokenInfo:
        ret_val = self.ray_pool_monitor.get_token_info(token_address)

        if not ret_val:
           ret_val = TokensApi.get_amm_token_pool_data(token_address)
   
        return ret_val

    def get_price(self, token_address: str):
        token_info = self.ray_pool_monitor.get_token_info(token_address)

        if token_info:
            return token_info.price
        else:
            # Get token information
            lp_data = TokensApi.get_amm_token_pool_data(token_address)

            return lp_data.price
    
    def get_swap_info(self, tx_signature: str, signer_pubkey: str, maxtries: int):
        for i in range(maxtries):
            transaction = self.solana_rpc_api.get_transaction(tx_signature)

            if transaction:
                transaction_info = self.solana_rpc_api.parse_swap_transaction(signer_pubkey, transaction)

                return transaction_info
            else:
                time.sleep(1)

    def get_candlesticks(self, token_address: str, interval: int)->list[Candlestick]:
        if token_address in self.candlesticks:
            return self.candlesticks[token_address].get_candlestick_builder(interval).get_all()
        
    def monitor_token(self, token_address: str):
        if token_address not in self.candlesticks:
            self.candlesticks[token_address] = Candlesticks(intervals=self.default_chart_intervals)

        self.ray_pool_monitor.monitor_token(token_address)

    def _handle_token_update(self, arg1: str):
        new_price = self.get_price(arg1)
        self.candlesticks[arg1].update(datetime.now(), new_price)
        new_price_string = f"{new_price:.20f}"
        print(arg1 + " was updated! Price: " + new_price_string)
