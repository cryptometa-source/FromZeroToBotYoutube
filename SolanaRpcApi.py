from jsonrpcclient import request, parse, Ok, Error
import requests

class SolanaRpcApi:

    def __init__(self, rpc_uri, wss_uri):
        self.rpc_uri = rpc_uri
        self.wss_uri = wss_uri
    
    def run_rpc_method(self, request_name: str, params):
        json_request = request(request_name, params=params)
        response = requests.post(self.rpc_uri, json=json_request)

        parsed = parse(response.json())

        if isinstance(parsed, Error): 
            return None
        else:
            return parsed

    def get_account_balance(self, account_address: str)->float:
        response = self.run_rpc_method("getBalance", [ account_address ])
        
        if response:
            return response.result['value']
        else:
            return None

    @staticmethod
    def get_account_subscribe_request(account_address: str):
         return {
                "jsonrpc": "2.0",
                "id": 420,
                "method": "accountSubscribe",
                "params": [
                account_address, # pubkey of account we want to subscribe to
                {
                    "encoding": "jsonParsed", # base58, base64, base65+zstd, jsonParsed
                    "commitment": "confirmed", # defaults to finalized if unset
                }
            ]
        }       