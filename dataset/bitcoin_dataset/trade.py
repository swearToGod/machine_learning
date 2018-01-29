# -*- coding: utf-8 -*-

import sys
reload(sys)
sys.setdefaultencoding('utf8')

from huobi import HuobiUtil
from huobi import HuobiService
from threading import Timer
from threading import Lock
from time import time



#print HuobiService.get_symbols()
#print HuobiService.get_kline('btcusdt', '1min', 1000)
#print HuobiService.get_accounts()
#print HuobiService.get_balance()  获取每种货币数

'''
/market/history/kline 获取K线数据
/market/detail/merged 获取聚合行情(Ticker)
/market/trade 获取 Trade Detail 数据
/market/detail 获取 Market Detail 24小时成交量数据
/v1/common/symbols 查询系统支持的所有交易对及精度
/v1/common/currencys 查询系统支持的所有币种
/v1/common/timestamp
/v1/account/accounts 查询当前用户的所有账户(即account-id)
/v1/account/accounts/{account-id}/balance 查询指定账户的余额
/v1/order/orders/place
/v1/order/orders/{order-id}/submitcancel
/v1/order/orders/batchcancel
/v1/order/orders/{order-id}查询某个订单详情
/v1/order/orders/{order-id}/matchresults 查询某个订单的成交明细
/v1/order/orders 查询当前委托、历史委托
/v1/order/matchresults 查询当前成交、历史成交
'''
buythresh, sellupthresh, selldownthresh = 1.007, 1.195, 0.984

usdtcoins = { # buyprice不随时间变化，所以不能放在kline
    'usdt':{ 'buyprice': 0.0, 'maxprice': 0.0, 'balance': 0.0, 'buy': False },
    'eos': { 'buyprice': 0.0, 'maxprice': 0.0, 'balance': 0.0, 'buy': False },
    'eth': { 'buyprice': 0.0, 'maxprice': 0.0, 'balance': 0.0, 'buy': False },
    'omg': { 'buyprice': 0.0, 'maxprice': 0.0, 'balance': 0.0, 'buy': False },
    'xrp': { 'buyprice': 0.0, 'maxprice': 0.0, 'balance': 0.0, 'buy': False },
    'zec': { 'buyprice': 0.0, 'maxprice': 0.0, 'balance': 0.0, 'buy': False },
}
symbols = ['eosusdt', 'ethusdt', 'omgusdt', 'xrpusdt', 'zecusdt']
kline = { i : dict()  for i in symbols }        # 这一分钟

DEBUG = True

def buy(amount, symbol):
    if not DEBUG:
        HuobiService.send_order(amount, '', symbol, 'buy-market')
    coinid = symbol.replace('usdt', '')
    usdtcoins[coinid]['buyprice'] = kline[symbol]['close']
    usdtcoins[coinid]['buy'] = True
    usdtcoins['usdt']['balance'] -= amount
    usdtcoins[coinid]['balance'] += amount / kline[symbol]['close']
    print 'buy', amount, symbol

def sell(amount, symbol):
    if not DEBUG:
        HuobiService.send_order(amount, '', symbol, 'sell-market')
    coinid = symbol.replace('usdt', '')
    usdtcoins[coinid]['buyprice'] = 0
    usdtcoins[coinid]['buy'] = False
    usdtcoins['usdt']['balance'] += amount * kline[symbol]['close']
    usdtcoins[coinid]['balance'] -= amount
    print 'sell', amount, symbol

def get_balance():
    if not DEBUG:
        return HuobiService.get_balance()['data']['list']
    else:
        return {
            'usdt': { 'type':'trace', 'balance': 10000.0 }
        }

def on_minute():
    global kline, usdt, buythresh, sellupthresh, selldownthresh
    Timer(60, on_minute).start()
    curtime = int(time())
    # 更新价格
    try:
        for symbol in kline:
            klinedata = HuobiService.get_kline(symbol, '1min', 1)['data'][0]
            kline[symbol]['time'] = klinedata['id']
            kline[symbol]['high'] = klinedata['high']
            kline[symbol]['low'] = klinedata['low']
            kline[symbol]['open'] = klinedata['open']
            kline[symbol]['close'] = klinedata['close']
            print symbol, kline[symbol], kline[symbol]
            if curtime - klinedata['id'] > 120:
                print 'Time different from server:', symbol
            coinid = symbol.replace('usdt', '')
            # 如果购买则更新maxprice
            if coinid in usdtcoins and usdtcoins[coinid]['buy']:
                if klinedata['high'] > usdtcoins[coinid]['maxprice']:
                    usdtcoins[coinid]['maxprice'] = klinedata['high']
    except Exception as e:
        print 'Error in get_kline', e.message
        return

    # 更新当前货币量
    try:
        balancedata = get_balance()
        for item in balancedata:
            if item['type'] == 'trace' and (item['currency']) in usdtcoins: # 不算冻结资金
                usdtcoins[item]['balance'] = float(item['balance'])
    except Exception as e:
        pass

    # 检测哪些币要卖
    buyable_symbols = []
    for symbol in kline:
        # 策略2 => 1分钟内涨幅降幅超过各自门限的多个币     均摊
        optype = 'none' # none buy sell
        if symbol.endswith('usdt') and symbol != 'usdt':
            coinid = symbol.replace('usdt', '')
            op = kline[symbol]['open']  # 开盘价
            cp = kline[symbol]['close']  # 收盘价
            bp = usdtcoins[coinid]['buyprice']
            mp = usdtcoins[coinid]['maxprice']

            if cp / op > buythresh:  # 涨到一定程度则入手
                buyable_symbols.append(symbol)
            #elif bp > 0.0 and (cp / bp > sellupthresh or cp / bp < selldownthresh):  # 已经入手且降到一定程度则出手
            #    optype = 'buy-market'
            elif mp > 0.0 and cp / mp < selldownthresh:
                # 市价卖出，清除数据
                sell(usdtcoins[coinid]['balance'], symbol)
                usdtcoins[coinid] = { 'buyprice': 0.0, 'maxprice': 0.0, 'balance': 0.0, 'optype': 'none' }

    # 更新卖出后的usdt数量 #需要等待吗？
    usdtamount = 0.0
    try:
        balancedata = get_balance()
        for item in balancedata:
            coinid = item['currency']
            if item['type'] == 'trace' and coinid in usdtcoins: # 不算冻结资金
                usdtcoins[item]['balance'] = float(item['balance'])
            if coinid == 'usdt':
                usdtamount = float(item['balance'])
    except Exception as e:
        pass

    if usdtamount > 1.0 and len(buyable_symbols) > 0: # 如果有可买货币则进行对冲
        splitamount = usdtamount / len(buyable_symbols)
        for symbol in buyable_symbols:
            coinid = symbol.replace('usdt', '')
            buy(splitamount, symbol)
            usdtcoins[coinid]['buy'] = True


def sellall():
    # 紧急情况卖出所有币
    # 更新当前货币量
    global kline
    try:
        for item in get_balance():
            if item['type'] == 'trace' and (item['currency']) in usdtcoins: # 不算冻结资金
                usdtcoins[item]['balance'] = float(item['balance'])
    except Exception as e:
        pass
    for symbol in kline:
        coinid = symbol.replace('usdt', '')
        sell(usdtcoins[coinid]['balance'], symbol)


if __name__ == '__main__':
    on_minute()
    Timer(60, on_minute).start()

