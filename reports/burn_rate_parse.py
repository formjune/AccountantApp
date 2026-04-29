import enum
import json
import datetime
import web3
from web3.middleware import geth_poa_middleware
from tools import Config

data = json.load(open("db.json"))
class NetworkEnum(enum.Enum):

    mainnet = 0
    binance = 1
    polygon = 2
    # #arbitrum = 3
    # def __str__(self) -> str:
    #     return self._name_

    def values():
        l = [v.value for v in NetworkEnum]
        return tuple(l)

    def convert(command: str):
        converted = [i_type for i_type in NetworkEnum if command.lower()
                     == i_type._name_]
        if converted:
            return converted[0]
        else:
            raise Exception("Incorrect str for conversion")



MAINNET_TOKENS = {
    "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48".lower(): "USDC",
    "0xdAC17F958D2ee523a2206206994597C13D831ec7".lower(): "USDT",
}
BINANCE_TOKENS = {
    "0x8AC76a51cc950d9822D68b83fE1Ad97B32Cd580d".lower(): "USDC",
    "0x55d398326f99059fF775485246999027B3197955".lower(): "BSC-USD"
}
POLYGON_TOKENS = {
    "0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359".lower(): "USDC",
    "0xc2132D05D31c914a87C6611C10748AEb04B58e8F".lower(): "USDT"
}
ARBITRUM_TOKENS = {
    "0xaf88d065e77c8cC2239327C5EDb3A432268e5831".lower(): "USDC",
    "0xFd086bC7CD5C481DCC9C85ebE478A1C0b69FCbb9".lower(): "USDT"
}
MAINNET_APP = web3.Web3(web3.HTTPProvider(Config.WEB3_MAINNET))
BINANCE_APP = web3.Web3(web3.HTTPProvider(Config.WEB3_BINANCE))
POLYGON_APP = web3.Web3(web3.HTTPProvider(Config.WEB3_POLYGON))
ARBITRUM_APP = web3.Web3(web3.HTTPProvider(Config.WEB3_ARBITRUM))
BINANCE_APP.middleware_onion.inject(geth_poa_middleware, layer=0)
POLYGON_APP.middleware_onion.inject(geth_poa_middleware, layer=0)
ARBITRUM_APP.middleware_onion.inject(geth_poa_middleware, layer=0)
BLOCKCHAIN = {
    NetworkEnum.mainnet: (MAINNET_APP, MAINNET_TOKENS, 1e6),
    NetworkEnum.binance: (BINANCE_APP, BINANCE_TOKENS, 1e18),
    NetworkEnum.polygon: (POLYGON_APP, POLYGON_TOKENS, 1e6),
#    NetworkEnum.arbitrum: (ARBITRUM_APP, ARBITRUM_TOKENS, 1e6),
}

          
def findTransferAmount(wallet: str, network: NetworkEnum, blocknum: int) -> float:
    web_app, tokens, divider = BLOCKCHAIN[network]
    wallet = f"0x000000000000000000000000{wallet[2:]}"
    event = web_app.keccak(text="Transfer(address,address,uint256)").hex()
    for topic in ((event, None, wallet), (event, wallet, None)):
        for tx in web_app.eth.get_logs({"fromBlock": blocknum, "toBlock": blocknum, "topics": topic}):
            if tx["address"].lower() not in tokens:
                continue
            amount = int(tx["data"].hex(), 16) / divider
            if amount < .5:
                continue
            print( {
                "block": tx["blockNumber"],
                "network": network,
                "sender": "0x" + tx["topics"][1].hex()[-40:],
                "receiver": "0x" + tx["topics"][2].hex()[-40:],
                "amount": amount,
                "token": tokens[tx["address"].lower()],
                "token_address": tx["address"],
                "tx_hash": tx["transactionHash"].hex(),
            })
            return amount
        


main_wallet = data["transfer_wallets"][0]["wallet"].lower()
print(main_wallet)
staff = data["staff"]
staff_wallets = {s["wallet"].lower() for s in staff}

salaries = {}
soft = {}
marketing = {}
others = {}

#rework regular spendings
spendings_data = {}
for spending in data["regular_spending"]:
    spendings_data[spending["id"]] = float(spending["amount"])

employee_by_wallet = {}
for employee in staff:
    employee_by_wallet[employee["wallet"].lower()] = employee

salaries_by_input = {}

for employee in staff:
    if employee["type"] == "dismissed":
        continue
    salaries_by_input[employee["position"]]=salaries_by_input.get(employee["position"], 0) + spendings_data[employee["salary_id"]]
# for position in salaries_by_input:
#     print(position, salaries_by_input[position], sep=';')

for tx in data["transfers"]:
    if tx["sender"] == main_wallet:
        date = datetime.datetime.strptime(tx["date"], "%Y-%m-%d").strftime("%m_%y") #"date": "2024-02-05",
        amount = float(tx["amount"])
        if tx["complete"] == "true":
            amount = findTransferAmount(tx["receiver"], NetworkEnum.convert(tx["network"]), int(tx["block"]))
        if tx["receiver"].lower() in staff_wallets:
            employee = employee_by_wallet[tx["receiver"].lower()]
            employee["fact_geting"] = employee.get("fact_geting", {})
            empl_fact = employee["fact_geting"]
            empl_fact[date] = empl_fact.get(date, 0) + amount
            print(employee, spendings_data[employee["salary_id"]])
            salaries[date] = salaries.get(date, 0) + amount
            print ("salar", salaries[date], date)
        else:
            others[date]=others.get(date, 0) + amount
                
    
for date in sorted(salaries):
    print(date, salaries[date], sep=';')

print ("___")

for date in sorted(others):
    print(date, others[date], sep=';')
            
print ("\n___\n")

for employee in employee_by_wallet:
    print("\n", employee_by_wallet[employee]["position"])
    if employee_by_wallet[employee].get("fact_geting") is None:
        continue
    for date in sorted(employee_by_wallet[employee]["fact_geting"]):
        print(date, employee_by_wallet[employee]["fact_geting"][date], sep=';')
