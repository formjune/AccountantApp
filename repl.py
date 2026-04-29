from blockchain.EngineWeb3 import findTransfers

for net in ("mainnet","binance","polygon","arbitrum","optimism","base"):
    txs = findTransfers(net, "0x2268ca2B5790565b55406505cf6439ad090eCa65")
    print(net, "→", len(txs), "tx")
