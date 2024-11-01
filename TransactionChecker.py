from SolanaRpcApi import SolanaRpcApi
import threading
import time
import asyncio
import websockets
import json

class TransactionChecker(threading.Thread):    
    def __init__(self, solana_rpc_api: SolanaRpcApi, tx_signature: str, timeout=60):
        threading.Thread.__init__(self)
        self.solana_rpc_api = solana_rpc_api
        self.tx_signature = tx_signature
        self.timeout = timeout
        self.final_response = None
        self.time_started = 0
        self.time_stopped = 0
        self.stop_event = threading.Event()

    def run(self):
        self.time_started = time.time()
        asyncio.run(self._check_transaction())

    def get_taken(self):
        if self.time_stopped > 0:
            return self.time_stopped - self.time_started
        else:
            return time.time()-self.time_started
        
    def did_succeed(self):
        if self.final_response: #and self.final_response['params']['result']['value']['err'] == None:
            return True
        else:
            return False
    
    def wait_for_success(self, timeout: int):
        self.stop_event.wait(timeout=timeout)

        return self.did_succeed()

    async def _check_transaction(self):
        async with websockets.connect(self.solana_rpc_api.wss_uri) as websocket:
            sub_request = self.solana_rpc_api.get_signature_request(self.tx_signature)
            request_bytes = json.dumps(sub_request)
            
            await websocket.send(request_bytes)

            response = await websocket.recv()

            if response:
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=self.timeout)

                    if response:
                        print("Received a response!" + str(response))
                        self.final_response = json.loads(response)
                except TimeoutError as e:
                    print("TransactionChecker Timed out!")

                self.time_stopped = time.time()
                self.stop_event.set()




    