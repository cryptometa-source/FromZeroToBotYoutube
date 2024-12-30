from pubsub import pub
#from TokensApi import TokenInfo FIXME
from TradingDTOs import TokenInfo
from SolanaRpcApi import SolanaRpcApi
import Globals as globals
import TokensApi as TokensApi
import json
import asyncio
import threading
import websockets

class RaydiumTokensMonitor(threading.Thread):
    def __init__(self, solana_rpc_api: SolanaRpcApi):
        threading.Thread.__init__(self)
        self.token_infos = {}
        self.updated_tokens = set()
        self.solana_rpc_api = solana_rpc_api
        self.wsocket = None
        self.write_queue = asyncio.Queue()  # Queue for outgoing messages

    def get_token_info(self, token_address):
        if token_address in self.token_infos:
            if token_address in self.updated_tokens:
                self._update_price(token_address)

                try:
                    self.updated_tokens.remove(token_address)
                except Exception as e:
                    print(token_address + " already removed.")
            
            return self.token_infos[token_address]
        else:
            return None

    def monitor_token(self, token_address: str):
        if self.wsocket:
            if token_address in self.token_infos:
                token_info = self.token_infos[token_address]
            else: 
                token_info = TokensApi.get_amm_token_pool_data(token_address)

                if token_info:
                    self.token_infos[token_address] = token_info
                else:
                    return
            
            request = self.solana_rpc_api.get_account_subscribe_request(token_info.token_vault_address)
            json_request = json.dumps(request)

            self.write_queue.put_nowait(json_request)

    async def _init_event_loop(self):
       await asyncio.gather(self._send_requests(), self._read_socket())

    def run(self):        
        asyncio.run(self._init_event_loop())

    def _update_price(self, token_address: str):
        if token_address in self.token_infos:
            sol_vault_address = self.token_infos[token_address].sol_vault_address
            sol_balance = self.solana_rpc_api.get_account_balance(sol_vault_address)
            token_info = self.token_infos[token_address]
            
            if sol_balance and token_info.token_vault_ui_amount > 0:
                sol_balance /= 1e9
            
                token_info.price = sol_balance/token_info.token_vault_ui_amount

    async def _send_requests(self):
       while True:
            try:        
                request = await self.write_queue.get()

                if request:
                    await self.wsocket.send(request)
            except Exception as e:
                print("Error " + str(e))

    async def _read_socket(self):
        while True:
            try:               
                async with websockets.connect(self.solana_rpc_api.wss_uri) as websocket:
                    self.wsocket = websocket  
  
                    token_addresses = list(self.token_infos.keys())

                    for token_address in token_addresses:
                        self.monitor_token(token_address)

                    try:
                        while True:
                            received = await websocket.recv()
                            jsonData = json.loads(received)
                            self._process(jsonData)
                    except TimeoutError as e:
                        print(str(e))
            except Exception as e:
                print("Error " + str(e))

    def _process(self, data: dict):
        params = data.get('params', None)
        
        if params:
            parsed_info = params['result']['value']['data']['parsed']['info']

            token_address = parsed_info['mint']
            token_ui_amount = parsed_info['tokenAmount']['uiAmount']

            token_info = self.token_infos[token_address]

            token_info.token_vault_ui_amount = token_ui_amount

            self.updated_tokens.add(token_address)

            pub.sendMessage(topicName=globals.topic_token_update_event, arg1=token_address)
            
            









    
