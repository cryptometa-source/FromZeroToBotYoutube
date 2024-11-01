
import requests

class TokenInfo:
    def __init__(self, token_address):
        self.token_address = token_address
        self.market_id = ''
        self.price = 0
        self.token_vault_ui_amount = 0
        self.sol_vault_address = ''
        self.token_vault_address = ''


def get_request(request_uri: str):
    response = requests.get(request_uri)

    if response.status_code == 200:
        return response.json()
    else:
        return None
    
#Retrieve a token't liquidity pool data using the Raydium v3 API
def get_amm_token_pool_data(token_address: str)->TokenInfo:
    ray_uri = "https://api-v3.raydium.io/pools"
    ray_uri_marketid_uri = ray_uri + "/info/mint?mint1=" + token_address + "&poolType=all&poolSortField=default&sortType=desc&pageSize=1&page=1"

    #Make the API call
    data = get_request(ray_uri_marketid_uri)
    
    if len(data) > 0:
        try:
            token_info = TokenInfo(token_address)
            token_info.market_id = data['data']['data'][0]['id']
            token_info.price = data['data']['data'][0]['price']

            pool_info_uri = ray_uri + "/key/ids?ids=" + token_info.market_id

            data = get_request(pool_info_uri)

            if len(data) > 0:
                mintAddressA = data['data'][0]['mintA']['address']
                vaultA = data['data'][0]['vault']['A']
                vaultB = data['data'][0]['vault']['B']

                if mintAddressA == token_address:
                    token_info.token_vault_address = vaultA
                    token_info.sol_vault_address = vaultB
                else:
                    token_info.sol_vault_address = vaultA
                    token_info.token_vault_address = vaultB
                    token_info.price = 1/token_info.price
                    
                return token_info
        except Exception as e:
            print(str(e))
    return