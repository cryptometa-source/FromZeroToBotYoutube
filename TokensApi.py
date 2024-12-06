
from TradingDTOs import TokenInfo
import requests
import json

def get_request(request_uri: str):
    response = requests.get(request_uri)

    if response.status_code == 200:
        return response.json()
    else:
        return None
    
def get_swap_transaction(signer_pubkey: str, in_token_address: str, out_token_address: str, amount: int, slippage: int, priority_fee: int):
    quote_jup_uri = 'https://quote-api.jup.ag/v6/quote?inputMint=' + in_token_address + '&outputMint=' + \
                out_token_address + "&amount=" + str(amount) + "&slippageBps=" + str(slippage)
    
    quote = get_request(quote_jup_uri)

    if quote:
        swap_jup_uri = 'https://quote-api.jup.ag/v6/swap'

        headers = {'Content-Type': 'application/json'}

        body = {
            "quoteResponse": quote,
            "userPublicKey": signer_pubkey,
            "wrapAndUnwrapSol": True,
            "prioritizationFeeLamports": priority_fee
            # Uncomment and modify the following line if you have a fee account
            # "feeAccount": "fee_account_public_key"            
        }
        json_data = json.dumps(body)
        response = requests.post(swap_jup_uri, headers=headers, data=json_data)    

        if response:
            json_response = response.json()

            return json_response['swapTransaction']

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
                mintA = data['data'][0]['mintA']
                mintB = data['data'][0]['mintB']
                vaultA = data['data'][0]['vault']['A']
                vaultB = data['data'][0]['vault']['B']

                if mintA['address'] == token_address:
                    token_info.sol_address = mintB['address']
                    token_info.token_decimals = mintA['decimals'] 
                    token_info.token_vault_address = vaultA
                    token_info.sol_vault_address = vaultB
                else:
                    token_info.sol_address = mintA['address']
                    token_info.token_decimals = mintB['decimals'] 
                    token_info.sol_vault_address = vaultA
                    token_info.token_vault_address = vaultB
                    token_info.price = 1/token_info.price
                
                token_info.decimals_scale_factor = pow(10, token_info.token_decimals)        
                return token_info
        except Exception as e:
            print(str(e))
    return