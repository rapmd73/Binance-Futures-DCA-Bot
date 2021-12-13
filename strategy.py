#pip install ccxt

import config
import pandas as pd
import ccxt
import winsound
duration = 1000  # milliseconds
freq = 440  # Hz

# SETTİNGS
symbolName = input("Symbol (BTC, ETH, LTC...): ").upper()
leverage = float(input("Leverage: "))
baseOrderSize = float(input("Base Order Size: "))
safetyOrderSize = float(input("Safety Order Size: "))
maxSafetyTradesCount = float(input("Max Safety Trades Count: "))
priceDeviation = float(input("Price Deviation %: "))
safetyOrderStepScale = float(input("Safety Order Step Scale: "))
safetyOrderVolumeScale = float(input("Safety Order Volume Scale: "))
takeProfit = float(input("Take Profit %: "))
stopLoss = float(input("Stop Loss %: "))
positionSide = float(input("Position Side = Only Long(1) - Only Short(2) - Long and Short(3): "))

#ATTRIBUTES
first = True
tradeCount = 0
symbol = symbolName+"/USDT"
mainSafetyOrderSize = safetyOrderSize
mainPriceDeviation = priceDeviation

# API CONNECT
exchange = ccxt.binance({
"apiKey": config.apiKey,
"secret": config.secretKey,

'options': {
'defaultType': 'future'
},
'enableRateLimit': True
})

while True:
    try:
        
        balance = exchange.fetch_balance()
        free_balance = exchange.fetch_free_balance()
        positions = balance['info']['positions']
        newSymbol = symbolName+"USDT"
        current_positions = [position for position in positions if float(position['positionAmt']) != 0 and position['symbol'] == newSymbol]
        position_info = pd.DataFrame(current_positions, columns=["symbol", "entryPrice", "unrealizedProfit", "isolatedWallet", "positionAmt", "positionSide"])
        
        # in position?
        if not position_info.empty and position_info["positionAmt"][len(position_info.index) - 1] != 0:
            inPosition = True
        else: 
            inPosition = False
            longPosition = False
            shortPosition = False
            
        # in long position?
        if not position_info.empty and float(position_info["positionAmt"][len(position_info.index) - 1]) > 0:
            longPosition = True
            shortPosition = False
        # in short position?
        if not position_info.empty and float(position_info["positionAmt"][len(position_info.index) - 1]) < 0:
            shortPosition = True
            longPosition = False
        
        
        # LOAD BARS
        bars = exchange.fetch_ohlcv(symbol, timeframe="1m", since = None, limit = 1)
        df = pd.DataFrame(bars, columns=["timestamp", "open", "high", "low", "close", "volume"])
        
        # Starting price
        if first:
            firstPrice = float(df["close"][len(df.index) - 1])
            first = False

        currentPrice = float(df["close"][len(df.index) - 1])
        
        # LONG ENTER
        def longEnter(alinacak_miktar):
            order = exchange.create_market_buy_order(symbol, alinacak_miktar)
            winsound.Beep(freq, duration)
            
        # LONG EXIT
        def longExit():
            order = exchange.create_market_sell_order(symbol, float(position_info["positionAmt"][len(position_info.index) - 1]), {"reduceOnly": True})
            winsound.Beep(freq, duration)

        # SHORT ENTER
        def shortEnter(alincak_miktar):
            order = exchange.create_market_sell_order(symbol, alincak_miktar)
            winsound.Beep(freq, duration)
            
        # SHORT EXIT
        def shortExit():
            order = exchange.create_market_buy_order(symbol, (float(position_info["positionAmt"][len(position_info.index) - 1]) * -1), {"reduceOnly": True})
            winsound.Beep(freq, duration)

        if inPosition == False:
            priceDeviation = mainPriceDeviation
            safetyOrderSize = mainSafetyOrderSize
        
        # LONG ENTER
        if firstPrice - (firstPrice/100) * priceDeviation >= currentPrice and shortPosition == False and maxSafetyTradesCount>tradeCount and float(free_balance["USDT"]) >= baseOrderSize and (positionSide == 1 or positionSide == 3):
            if tradeCount == 0:
                alinacak_miktar = (baseOrderSize * float(leverage)) / float(df["close"][len(df.index) - 1])
            if tradeCount > 0:
                alinacak_miktar = (safetyOrderSize * float(leverage)) / float(df["close"][len(df.index) - 1])
                safetyOrderSize = safetyOrderSize*safetyOrderVolumeScale

            priceDeviation = priceDeviation * safetyOrderStepScale
            longEnter(alinacak_miktar)
            print("LONG ENTER")
            first = True
            tradeCount = tradeCount + 1
        
        # SHORT ENTER
        if ((firstPrice / 100) * priceDeviation) + firstPrice <= currentPrice and longPosition == False and maxSafetyTradesCount>tradeCount and float(free_balance["USDT"]) >= baseOrderSize and (positionSide == 2 or positionSide == 3): 
            if tradeCount == 0:
                alinacak_miktar = (baseOrderSize * float(leverage)) / float(df["close"][len(df.index) - 1])
            if tradeCount > 0:
                alinacak_miktar = (safetyOrderSize * float(leverage)) / float(df["close"][len(df.index) - 1])
                safetyOrderSize = safetyOrderSize*safetyOrderVolumeScale

            priceDeviation = priceDeviation * safetyOrderStepScale
            shortEnter(alinacak_miktar)
            print("SHORT ENTER")
            first = True
            tradeCount = tradeCount + 1
            
            
        # LONG TAKE PROFIT
        if longPosition and ((float(position_info["entryPrice"][len(position_info.index) - 1])/100)*takeProfit)+float(position_info["entryPrice"][len(position_info.index) - 1]) < currentPrice and (positionSide == 1 or positionSide == 3):
            print("TAKE PROFIT")
            longExit()
            first = True
            tradeCount = 0
            
        # SHORT TAKE PROFIT
        if shortPosition and float(position_info["entryPrice"][len(position_info.index) - 1]) - (float(position_info["entryPrice"][len(position_info.index) - 1])/100) * takeProfit >= currentPrice and (positionSide == 2 or positionSide == 3):
            print("TAKE PROFIT")
            shortExit()
            first = True
            tradeCount = 0
            
        # LONG STOP LOSS
        if longPosition and (float(free_balance["USDT"]) <= baseOrderSize or maxSafetyTradesCount<=tradeCount) and firstPrice - (firstPrice/100) * stopLoss >= currentPrice and (positionSide == 1 or positionSide == 3):
            print("STOP LOSS")
            longExit()
            first = True
            tradeCount = 0
        
        # SHORT STOP LOSS
        if shortPosition and (float(free_balance["USDT"]) <= baseOrderSize or maxSafetyTradesCount<=tradeCount) and ((firstPrice / 100) * stopLoss) + firstPrice <= currentPrice and (positionSide == 2 or positionSide == 3):
            print("STOP LOSS")
            shortExit()
            first = True
            tradeCount = 0
            
            
        if longPosition:
            print("In Long Position")
        if shortPosition:
            print("In Short Position")
        if inPosition:
            print("Trade Count: ", tradeCount, " Avarege Price: ", float(position_info["entryPrice"][len(position_info.index) - 1]), " Free Usdt: ", round(float(free_balance["USDT"]),2), " Total Money: ", round(float(balance['total']["USDT"]),2))
        if inPosition == False: 
            print("Starting Price: ", firstPrice, " Current Price: ", currentPrice, " Total Money: ", round(float(balance['total']["USDT"]),2))
        print("=======================================================================================================================================")

    except ccxt.BaseError as Error:
        print ("[ERROR] ", Error )
        continue
