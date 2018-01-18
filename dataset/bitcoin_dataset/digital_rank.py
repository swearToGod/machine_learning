# -*- coding: utf-8 -*-
import sqlite3
import urllib2
import json
from time import time
from time import sleep
import threading
import sys
reload(sys)
sys.setdefaultencoding('utf8')

def fixval(val):
    rat = 1
    val = val.strip(u'¥')
    if val.find(u'亿') != -1:
        val = val.strip(u'亿')
        rat = 10000
    elif val.find(u'万') != -1:
        val = val.strip(u'万')
        rat = 1
    val = str(val).replace(',', '')
    return float(val) * rat

def buildrankdb():
    print 'update rankdb'
    threading.Timer(300, buildrankdb, []).start()  # 5分钟一次

    cu = sqlite3.connect('digital_rank.db')
    cx = cu.cursor()

    t = int(time())

    ranklist = list()
    for page in range(1, 10):
        response = urllib2.urlopen('http://api.fxh.io/v1/coin/?page=%d' % page).read()
        jr = json.loads(response)
        for item in jr['RankList']:
            subresponse = urllib2.urlopen('http://api.fxh.io/v1/coininfo/%s/?' % str(item['CoinCode'])).read()
            subjr = json.loads(subresponse)
            ranklist.append(subjr)

    for item in ranklist:
        try:
            CoinSymbol = str(item['CoinCode'])
            ChangedRate = float(item['ChangedRate'])
            CirculatingSupply = fixval(item['CirculatingSupply'])
            CurPrice = fixval(item['CurPrice_Cny'])
            High = fixval(item['High'])
            Low = fixval(item['Low'])
            MarketCap = fixval(item['MarketCap_Cny'])
            Rank = int(item['Rank'])
            Volume = fixval(item['Volume'])
        except Exception as e:
            continue # 跳过非法数据

        try:
            cmd = 'create table %s (t int primary key, ChangedRate float, CirculatingSupply float, CurPrice float, High float, Low float, MarketCap float, Rank int, Volume int)'
            cx.execute(cmd % CoinSymbol)
        except Exception as e:
            pass

        try:
            cmd = 'insert or ignore into %s values (?,?,?,?,?,?,?,?,?)' % CoinSymbol
            cx.execute(cmd, (t, ChangedRate, CirculatingSupply, CurPrice, High, Low, MarketCap, Rank, Volume))
        except Exception as e:
            pass

        cu.commit()

if __name__ == '__main__':
    threading.Timer(300, buildrankdb, []).start() # 5分钟一次
    while True:
        sleep(300)
