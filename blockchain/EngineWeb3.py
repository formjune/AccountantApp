from decimal import Decimal
import enum
import datetime
import json
import requests
import web3
try:
    from web3.middleware import ExtraDataToPOAMiddleware
except:
    from web3.middleware import geth_poa_middleware as ExtraDataToPOAMiddleware
from tools import Config


class NetworkType(enum.Enum):

    web3 = 0
    url = 1


ABI = json.load(open("resources/abi.json", encoding="utf-8"))
EXPLORER_URLS = {}
NETWORK_TYPE = {}
NETWORKS = {}


def initializeNetworks():
    networks = json.load(open("resources/networks.json", encoding="utf-8"))
    for name, data in networks.items():
        EXPLORER_URLS[name] = data["prefix"]
        try:
            apikey = Config.API_KEYS[name]
            assert apikey
        except (KeyError, AssertionError):
            continue
        tokens_lower = {address.lower(): token for (address, token) in data["tokens"].items()}
        if "token_divider" in data:
            dividers_lower = {address.lower(): token for (address, token) in data["token_divider"].items()}
        else:
            dividers_lower = {}

        if data["type"] == "url":
            NETWORK_TYPE[name] = NetworkType.url
            NETWORKS[name] = data["url"], apikey, tokens_lower, data["divider"], dividers_lower
        else:
            web_app = web3.Web3(web3.HTTPProvider(apikey))
            if data["poa"]:
                web_app.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
            NETWORK_TYPE[name] = NetworkType.web3
            NETWORKS[name] = web_app, tokens_lower, data["divider"], dividers_lower
    print("loaded networks: " + ", ".join(NETWORKS))


def getDivider(main_divider, token_divider, token_address) -> float:
    try:
        return token_divider[token_address]
    except KeyError:
        return main_divider


def getBlockTime(block: int, network: str) -> datetime.date:
    """get block time by block number"""
    return datetime.date.fromtimestamp(NETWORKS[network][0].eth.get_block(block, False)["timestamp"])


def getUrl(tx_hash: str, network: str) -> str:
    try:
        return EXPLORER_URLS[network] + tx_hash
    except KeyError:
        print("network not found")
        return ""


def findTransfers(network: str, address: str) -> dict:
    """
    Для web3-сетей (get_logs) используем заполненный 32-байтовый (64 hex) адрес;
    для explorer-сетей (tokentx) — обычный unpadded адрес.
    """
    raw_address = address.lower()
    # 24 нуля + 40 hex → 64 hex символа → 32 байта
    padded_address = "0x" + raw_address[2:].rjust(64, "0")

    if NETWORK_TYPE[network] == NetworkType.web3:
        # для JSON-RPC get_logs
        return findTransfersWeb3(network, padded_address)
    else:
        # для Etherscan-style API tokentx
        return findTransfersExplorer(network, raw_address)



def findTransfersExplorer(network, address) -> dict:
    transfers = {}
    # старые переменные остаются
    for token_address, token_name in NETWORKS[network][2].items():
        # стартовый блок можно хранить где-то в БД — сейчас 0
        new_tx = findTokenTransfersExplorer(
            network,
            address,
            token_address,
            token_name,
            start_block=0,
            end_block="latest"
        )
        transfers.update(new_tx)
    return transfers



def findTokenTransfersExplorer(
    network: str,
    address: str,
    token_address: str,
    token_name: str,
    start_block: int = 0,
    end_block: str = "latest"
) -> dict:
    """
    ERC20 Token Transfer Events по API tokentx.
    Возвращает dict ключ → tx, где ключ = (tx_hash, receiver).
    """
    base_url, api_key, tokens, main_divider, token_divider = NETWORKS[network]
    raw_divider = getDivider(main_divider, token_divider, token_address)
    divider = Decimal(str(raw_divider))

    transfers = {}
    page = 1
    page_size = 1000
    while True:
        params = {
            "module":           "account",
            "action":           "tokentx",
            "contractaddress":  token_address,
            "address":          address,
            "startblock":       start_block,
            "endblock":         end_block,
            "sort":             "asc",
            "page":             page,
            "offset":           page_size,
            "apikey":           api_key,
        }
        page_params = {"page": page, "offset": page_size}
        print(f"DEBUG tokentx page={page}, params={page_params}")

        resp = requests.get(base_url, params=params, timeout=10)
        data = resp.json()
        if data.get("status") != "1" or not data.get("result"):
            print("DEBUG tokentx done, no more results or error:", data.get("message"))
            break

        results = data["result"]
        print(f"DEBUG tokentx got {len(results)} items on page {page}")

        for item in results:
            tx_hash  = item["hash"].lower()
            sender   = item["from"].lower()
            receiver = item["to"].lower()
            value    = Decimal(item["value"])
            amount   = float(value / divider)
            block    = int(item["blockNumber"])
            date     = datetime.date.fromtimestamp(int(item["timeStamp"]))

            tx_key = (tx_hash, receiver)
            transfers[tx_key] = {
                "block":         block,
                "network":       network,
                "sender":        sender,
                "receiver":      receiver,
                "amount":        amount,
                "amount_tx":     amount,
                "token":         token_name,
                "token_address": token_address,
                "tx_hash":       tx_hash,
                "date":          date,
            }

        # Если вернулось меньше, чем page_size, значит это последняя страница
        if len(results) < page_size:
            break
        page += 1

    return transfers


def findTransfersWeb3(network, address) -> dict:
    """find transfers via web3 library. for avalance"""
    web_app, tokens, main_divider, token_divider = NETWORKS[network]
    event = web_app.keccak(text="Transfer(address,address,uint256)").hex()
    transfers = {}
    for topic in ((event, None, address), (event, address, None)):
        for tx in web_app.eth.get_logs({"fromBlock": 1, "toBlock": "latest", "topics": topic}):
            token_address = tx["address"].lower()
            if token_address not in tokens:
                continue
            divider = getDivider(main_divider, token_divider, token_address)
            amount = int(tx["data"].hex(), 16) / divider
            if amount < .5:
                continue
            tx_hash = tx["transactionHash"].hex().lower()
            receiver = "0x" + tx["topics"][2].hex()[-40:]
            transfers[(tx_hash, receiver.lower())] = {
                "block": tx["blockNumber"],
                "network": network,
                "sender": "0x" + tx["topics"][1].hex()[-40:],
                "receiver": receiver,
                "amount": amount,
                "amount_tx": amount,
                "token": tokens[tx["address"].lower()],
                "token_address": tx["address"],
                "tx_hash": tx_hash,
            }
    return transfers


def getBalance(network, address) -> float:
    if NETWORK_TYPE[network] == NetworkType.web3:
        return getBalanceWeb3(network, address)
    else:
        return getBalanceExplorer(network, address)


def getBalanceExplorer(network, address) -> float:
    base_url, api_key, tokens, main_divider, token_divider = NETWORKS[network]
    balance = 0
    for token_address in tokens:
        divider = getDivider(main_divider, token_divider, token_address)
        params = {
            "module": "account",
            "action": "tokenbalance",
            "tag": "latest",
            "contractaddress": token_address,
            "address": address,
            "apikey": api_key
        }
        response = requests.get(base_url, params=params)
        balance += int(response.json()["result"]) / divider
    return balance


def getBalanceWeb3(network, address) -> float:
    web_app, tokens, main_divider, token_divider = NETWORKS[network]
    balance = 0
    for token_address in tokens:
        divider = getDivider(main_divider, token_divider, token_address)
        contract = web_app.eth.contract(web_app.to_checksum_address(token_address), abi=ABI)
        balance += contract.functions.balanceOf(web_app.to_checksum_address(address)).call() / divider
    return balance



initializeNetworks()
