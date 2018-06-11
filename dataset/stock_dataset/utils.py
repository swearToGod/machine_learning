# -*- coding: utf-8 -*-

# 工具


import json
import hashlib
import hmac
from lxml import etree
import requests
import sqlite3
import sys
import threading
import threadpool
import tushare as ts
import time
import urllib
import urllib2
import httplib
import re
from urllib import quote

reload(sys)
sys.setdefaultencoding('utf8')


# 通用功能
def getalltable(dbname):
    # 获取所有表
    tables = list()
    cx = sqlite3.connect(dbname)
    cu = cx.cursor()
    results = cu.execute("select tbl_name from sqlite_master where type='table' order by name").fetchall()
    for result in results:
        tables.append(result[0])
    cu.close()
    cx.close()
    return tables

def fixalltable(dbname):
    # 修复数据库，删除空数据
    tables = list()
    cx = sqlite3.connect(dbname)
    cu = cx.cursor()
    results = cu.execute("select tbl_name from sqlite_master where type='table' order by name").fetchall()
    for result in results:
        tables.append(result[0])
    for table in tables:
        count = cu.execute("select count(*) from %s" % (table)).fetchone()[0]
        if count <= 0:
            cu.execute("drop table %s" % (table))
    cu.close()
    cx.close()
    return tables

def getallcolume(cx, tbl):
    columes = list()
    results = cx.execute('PRAGMA table_info(%s)' % tbl).fetchall()
    for result in results:
        columes.append(str(result[1]))
    return columes


def getstrforperiod(period):
    # unit = second
    period /= 60
    if period < 60:
        return '%dmin' % period
    period /= 60
    return '%dhour' % period
    # 最大到hour


def setproxy(proxy):
    enable_proxy = True if proxy != '' else False
    proxy_handler = urllib2.ProxyHandler({'http': proxy, 'https': proxy})
    null_proxy_handler = urllib2.ProxyHandler({})
    if enable_proxy:
        opener = urllib2.build_opener(proxy_handler)
    else:
        opener = urllib2.build_opener(null_proxy_handler)
    urllib2.install_opener(opener)


def createTimeStamp(datestr, format="%Y-%m-%d %H:%M:%S"):
    return time.mktime(time.strptime(datestr, format))

def get_news(keywords, gbegintime, period = 86400):
    # 由于只取一页数据，最多50个，如果period过大会缺数据
    gendtime = int(time.time())
    for begintime in range(gbegintime, gendtime, period):
        if os.path.exists('btcnews/btcnews_%d' % (begintime)):
            continue
        querystr = 'http://news.baidu.com/ns?cl=2&bt=%d&et=%d&q3=%s&rn=50' % \
                   (begintime, begintime + period, '+'.join([quote(url) for url in keywords]))
        selector = etree.HTML(requests.get(querystr).content)
        baidu_newitems = selector.xpath("//div[@class='result']/h3/a/text()")
        with open('btcnews/btcnews_%d' % (begintime), 'w') as f:
            f.writelines([i.encode('utf-8') + '\n' for i in baidu_newitems])


def getresponse(request, url):
    conn = httplib.HTTPConnection(url)
    conn.request('GET', request, headers={'User-Agent':'12'})
    resp = conn.getresponse().read()
    conn.close()
    return resp


def get_house_price(): # 1年更新一次即可
    cx = sqlite3.connect('house_price')

    # 获取城市列表
    selector = etree.HTML(getresponse('https://www.anjuke.com/sy-city.html', 'www.anjuke.com'))
    cityurls = [i.attrib['href'] for i in selector.xpath("//div[@class='city_list']/a")]
    for url in cityurls:
        try:
            city = url.replace('http://','').replace('.anjuke.com','')
            content = getresponse(url.replace('http://','https://') + '/market/', 'www.anjuke.com')
            jsondata = re.search(r'drawChart\((.*regionChart[^;]*)\)', content, re.S).group(1)
            jdata = json.loads(jsondata.replace('id','"id"').replace('type', '"type"').replace('xdata','"xdata"')
                             .replace('xyear','"xyear"').replace('ydata','"ydata"').replace('\'','"'))
            try:
                cx.execute('create table %s (t int primary key, price int)' % (city))
            except:
                pass
            for i in range(0, len(jdata['xdata'])):
                ms = jdata['xdata'][i]
                m = int(ms.encode('utf-8').replace('\xe6\x9c\x88', ''))
                ys = jdata['xyear'][ms]
                y = int(ys.encode('utf-8').replace('\xe5\xb9\xb4', ''))
                p = int(jdata['ydata'][0]['data'][i])
                cx.execute('insert or ignore into %s values (?,?)' % (city), (y*100+m, p))
            cx.commit()
            print('%s done'%(city))
        except:
            pass
    cx.close()


def get_btc_news():
    get_news(['加密货币', '比特币', 'BTC'], int(time.mktime((2017, 1, 1, 0, 0, 0, 0, 0, 0))))


# 比特币函数

class AICoin(object):
    def __init__(self):
        self.availperiod = [600, 900, 1800, 3600, 7200, 14400, 21600, 43200]  # 合法周期 60, 180, 300, 7200, 14400, 21600, 43200
        self.availpair = ['bchusdt', 'btcusdt', 'btmusdt', 'btsusdt', 'cvcusdt', 'dashusdt',
                          'dtausdt', 'elausdt', 'elfusdt', 'eosusdt', 'etcusdt', 'ethusdt',
                          'gntusdt', 'htusdt', 'hb10usdusdt', 'hsrusdt', 'htusdt', 'iostusdt',
                          'iotausdt', 'itcusdt', 'letusdt', 'ltcusdt', 'mdsusdt', 'nasusdt',
                          'neousdt', 'omgusdt', 'ontusdt', 'qtumusdt', 'ruffusdt', 'smtusdt',
                          'sntusdt', 'socusdt', 'steemusdt', 'storjusdt', 'thetausdt','trxusdt',
                          'wiccusdt', 'venusdt', 'xemusdt', 'xrpusdt', 'zecusdt', 'zilusdt',
                          ]  # 合法货币对
        self.availsite = [ 'binance', 'bitfinex', 'bithumb', 'hitbtc', 'huobipro', 'okex', 'zb']

        self.lock = threading.Lock()

    def get_tblname(self, site, pair):
        return site.replace('.', '') + '_' + pair

    def api_query(self, req=dict()):
        time.sleep(0.5)
        url_param = urllib.urlencode(req, doseq=True)
        collect_data = list()
        headers = {
            'Host': 'www.aicoin.net.cn',
            'User-Agent': 'Mozilla/5.0 (Windows NT 6.3; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/47.0.2526.106 BIDUBrowser/8.7 Safari/537.36',
            'Accept': '*/*',
            'Accept-Language': 'zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q=0.2',
            'Accept-Encoding': 'deflate, br',
            'Referer': 'https://www.aicoin.net.cn',
            'origin': 'https://www.aicoin.net.cn',
            'Connection': 'keep-alive',
        }
        try:
            url = 'https://www.aicoin.net.cn/chart/api/data/period?' + url_param
            #print(url)
            conn = httplib.HTTPConnection('127.0.0.1:9999', timeout=10)
            conn.request(method='GET', url=url, headers=headers)
            responsedata = conn.getresponse().read()
            conn.close()
            if responsedata.find('robot') != -1:
                return collect_data
            resp = json.loads(responsedata)
            time.sleep(0.5)
            curdata = resp['data']
            collect_data += curdata
            countstr = resp['count']
            count = 1
            while True:
                if len(curdata) == 0:
                    break
                url = 'https://www.aicoin.net.cn/chart/api/data/periodHistory?' + url_param + \
                      '&times=%d' % count + '&count=' + countstr
                #print(url)
                conn = httplib.HTTPConnection('127.0.0.1:9999', timeout=10)
                conn.request(method='POST', url=url, headers=headers)
                responsedata = conn.getresponse().read()
                conn.close()
                if responsedata.find('robot') != -1:
                    return collect_data
                curdata = json.loads(responsedata)
                time.sleep(0.5)
                collect_data += curdata
                count += 1
        except Exception as e:
            print('timeout retry')
            time.sleep(300)
            return self.api_query(req)
        return collect_data

    def add_data(self, d):
        jsarr, site, symbol, period, cx = d['jsarr'], d['site'], d['symbol'], d['period'], d['cx']
        tbl = self.get_tblname(site, symbol)
        js = self.api_query({'symbol': site + symbol, 'step': period})
        jsarr[tbl] = js
        #print(symbol)

    def get_data(self, site, period, cx):
        if site not in self.availsite:
            print('site error')
        if period not in self.availperiod:
            print('period error')

        jsarr = dict()
        for symbol in self.availpair:
            self.add_data({'jsarr': jsarr, 'site': site, 'symbol': symbol, 'period': period, 'cx': cx})

        for tbl in jsarr:
            try:
                try:
                    if len(jsarr[tbl]) > 0:
                        # 时间 开盘价 最高价 最低价 收盘价 成交量
                        sql = 'create table %s (time int primary key, close double, high double, low double, open double, volume double)' % tbl
                        cx.execute(sql)
                except Exception as e:
                    pass  # Already exist
                for item in jsarr[tbl]:
                    try:
                        cx.execute('insert or ignore into %s values (?,?,?,?,?,?)' % tbl,
                                   (int(item[0]), float(item[1]), float(item[2]), float(item[3]), float(item[4]),
                                    float(item[5])))
                    except Exception as e:
                        pass
                cx.commit()
            except Exception as e:
                #print('err%s %d' % (tbl, period))
                pass


class CryptoCompare(object):
    # 可以获取2013至今的小时数据
    def __init__(self):
        self.availperiod = [60, 3600]  # 合法周期
        self.availpair = ['BTC', 'BCH', 'CVC', 'DASH', 'ELF', 'EOS', 'ETC', 'ETH', 'GNT', 'HSR', 'IOST', 'LTC',
                          'NEO', 'OMG', 'QTUM', 'SMT', 'SNT', 'STORJ', 'VEN', 'XRP', 'ZEC']  # 合法货币对
        self.availsite = ['LocalBitcoins', 'Gatecoin', 'Lykke', 'Poloniex', 'Exmo', 'Tidex', 'Cryptsy',
                          'Coinfloor', 'CCEX', 'bitFlyer', 'QuadrigaCX', 'itBit', 'Quoine', 'Coinroom',
                          'TheRockTrading', 'Abucoins', 'Cexio', 'BitTrex', 'Bitfinex', 'HitBTC',
                          'Yobit', 'LakeBTC', 'Remitano', 'Yunbi', 'BitSquare', 'MonetaGo', 'BTER',
                          'Huobi', 'Bitstamp', 'BitBay', 'OKCoin', 'Gemini', 'WavesDEX', 'CCEDK',
                          'BitFlip', 'BTCChina', 'LiveCoin', 'Coinsetter', 'Coinbase', 'CCEDK',
                          'Kraken', 'TrustDEX', 'BTCE']
        self.limit = 2000

    def get_tblname(self, site, pair):
        return site.replace('.', '') + '_' + pair

    def api_query(self, period, req=dict()):
        url_param = urllib.urlencode(req, doseq=True)
        timestr = ''
        if period == 60:
            timestr = 'minute'
        elif period == 3600:
            timestr = 'hour'
        ret = urllib2.urlopen(urllib2.Request('https://min-api.cryptocompare.com/data/histo%s?' % timestr + url_param))
        return json.loads(ret.read())

    def get_data(self, site, period, cx):
        if site not in self.availsite:
            print('site error')
        if period not in self.availperiod:
            print('period error')
        for pair in self.availpair:
            tbl = self.get_tblname(site, pair)
            try:
                # 时间 开盘价 最高价 最低价 收盘价 成交量
                sql = 'create table %s (time int primary key, close double, high double, low double, open double, volumefrom int, volumeto int)' % tbl
                cx.execute(sql)
            except Exception as e:
                pass  # Already exist
            endts = int(time.time())
            while True:
                try:
                    js = self.api_query(period, {'fsym': pair, 'tsym': 'USD', 'limit': 2000, 'e': site, 'toTs': endts})
                    for item in js['Data']:
                        try:
                            cx.execute('insert or ignore into %s values (?,?,?,?,?,?,?)' % tbl,
                                       (int(item['time']), float(item['close']), float(item['high']),
                                        float(item['low']), float(item['open']), int(item['volumefrom']),
                                        int(item['volumeto'])))
                        except Exception as e:
                            print(__file__, sys._getframe().f_lineno)
                    cx.commit()
                    endts -= period * self.limit
                    if len(js['Data']) == 0:  # todo
                        break
                except Exception as e:
                    pass

        if period not in self.availperiod:
            print('period error')
        if site not in self.availsite:
            print('site error')
        for pair in self.availpair:
            js = self.api_query(period, {'fsym': pair, 'tsym': 'USD', 'limit': self.limit, 'e': site})


class CoinApi(object):
    # 可以获取2011至今的分钟数据
    def __init__(self):
        self.availperiod = {60: '1MIN', 180: '3MIN', 300: '5MIN', 600: '10MIN', 900: '15MIN',
                            1800: '30MIN', 3600: '1HRS', 7200: '2HRS', 14400: '4HRS', 21600: '6HRS',
                            43200: '12HRS'}  # 合法周期
        self.availpair = ['BTC', 'ETH', 'EOS', 'XRP', 'IOST', 'LTC', 'BCH', 'HSR', 'ETC', 'QTUM',
                          'NEO', 'SNT', 'SMT', 'XEM', 'VEN', 'ELF', 'STORJ', 'CVC', 'OMG', 'DASH',
                          'ZEC', 'GNT']  # 合法货币对
        self.availsite = ['1BTCXE', 'ABUCOINS', 'ACX', 'ALLCOIN', 'ANXPRO', 'BINANCE', 'BITBAY', 'BITCOINID',
                          'BITFINEX', 'BITFLYER', 'BITHUMB', 'BITKONAN', 'BITLISH', 'BITMARKET', 'BITSO',
                          'BITSTAMP', 'BITTREX', 'BLEUTRADE', 'BRAZILIEX', 'BTCBOX', 'BTCC', 'BTCMARKETS',
                          'BTCTRADE', 'BTCTRADEUA', 'BTCTURK', 'BXINTH', 'CCEX', 'CEXIO', 'COINBASE',
                          'COINCHECK', 'COINEXCHANGE', 'COINFLOOR', 'COINGI', 'COINMATE', 'COINNEST',
                          'COINONE', 'COINSECURE', 'CRYPTOPIA', 'DSX', 'EXMO', 'GATECOIN', 'GATEIO',
                          'GEMINI', 'GETBTC', 'HITBTC', 'HUOBIPRO', 'INDEPENDENTRESERVE''ITBIT',
                          'JUBI', 'KORBIT', 'KRAKEN', 'KUCOIN', 'KUNA', 'LAKEBTC', 'LIQUI', 'LIVECOIN',
                          'LUNO', 'LYKKE', 'MERCADOBITCOIN', 'MIXCOINS', 'NOVA', 'OKCOIN', 'OKEX',
                          'POLONIEX', 'QRYPTOS', 'QUADRIGACX', 'QUOINE', 'SOUTHXCHANGE', 'THEROCKTRADING',
                          'TIDEX', 'VAULTORO', 'VIRWOX', 'WEXNZ', 'XBTCE', 'YOBIT', 'ZAIF']

    def get_tblname(self, site, pair):
        return site.replace('.', '') + '_' + pair

    def get_time(self, timestr):
        return time.mktime(time.strptime(timestr[:19], '%Y-%m-%dT%H:%M:%S'))  # 2017-08-09T14:31:01.0000000Z

    def to_time(self, timestamp):
        return time.strftime('%Y-%m-%dT%H:%M:%S', time.localtime(timestamp))

    def api_query(self, path, req=dict()):
        url_param = urllib.urlencode(req, doseq=True)
        headers = {'X-CoinAPI-Key': '3ECC1380-DB38-4E46-A6A5-585D1DE75AF1'}
        ret = requests.get('https://rest.coinapi.io' + path + url_param, headers=headers)
        return json.loads(ret.content)

    def get_data(self, site, period, cx):
        if site not in self.availsite:
            print('site error')
        if period not in self.availperiod:
            print('period error')
        for symbol in self.availpair:
            tbl = self.get_tblname(site, symbol)
            try:
                # 时间 开盘价 最高价 最低价 收盘价 成交量
                sql = 'create table %s (time int primary key, open double, high double, low double, close double, volume int, tradecount int)' % tbl
                cx.execute(sql)
            except Exception as e:
                pass  # Already exist

            endtime = int(time.time())
            begintime = endtime - 20000 * period
            pair = '%s_%s_%s_%s' % (site, 'SPOT', symbol, 'USDT')
            while True:
                try:
                    js = self.api_query('/v1/ohlcv/%s/history?' % pair, {'period_id': self.availperiod[period],
                                                                         'time_start': self.to_time(begintime),
                                                                         'time_end': self.to_time(endtime)})
                    for item in js:
                        try:
                            t = self.get_time(item['time_open'])  # 2017-08-09T14:31:01.0000000Z  todo
                            cx.execute('insert or ignore into %s values (?,?,?,?,?,?,?)' % tbl,
                                       (t, int(item['price_open']), float(item['price_high']), float(item['price_low']),
                                        float(item['price_close']), int(item['volume_traded']),
                                        int(item['trades_count'])))
                        except Exception as e:
                            pass
                    cx.commit()
                    if len(js) == 0:
                        break
                except Exception as e:
                    pass
                begintime -= 20000 * period
                endtime -= 20000 * period


class TuShareData(object):
    def __init__(self):
        self.availperiod = [86400]
        self.lock = threading.Lock()

    def stock_getter(self, code, period_):
        tbl = '_1_' + code

        try:
            # 时间 开盘价 最高价 最低价 收盘价 成交量
            sql = 'create table %s (time int primary key, open double, close double, high double, low double, vol double, amount double)'
            self.cx.execute(sql % tbl)
        except Exception as e:
            pass  # Already exist

        ktype = 'D'
        if period_ == 24:
            ktype = 'D'
        if period_ == 168:
            ktype = 'W'
        if period_ == 720:
            ktype = 'M'
        #df_1min = ts.bar(code, conn=self.cons, freq=self.period)
        df_1min = ts.get_hist_data(code, ktype=ktype)
        try:
            for t in df_1min.index:
                timestamp = int(time.mktime(time.strptime(t, '%Y-%m-%d')))
                open, high, close, low, vol, amount, _1, _2, _3, _4, _5, _6, _7 = df_1min.loc[t]
                try:
                    self.cx.execute('insert or ignore into %s values (?,?,?,?,?,?,?)' % tbl,
                                    (timestamp, open, close, high, low, vol, amount))
                except Exception as e:
                    print(e)
        except:
            pass

    def get_data(self, period, cx):
        self.cons = ts.get_apis()
        self.cx = cx
        df = ts.get_stock_basics()
        count = 0
        for code in df.index:
            self.stock_getter(code, period)
            count += 1
            if (count % 100) == 0:
                self.cx.commit()
                print(count)

class EastmoneyData(object):
    def __init__(self):
        self.cu = sqlite3.connect('fund.db')

    def get_data(self):
        cu = self.cu
        conn = httplib.HTTPConnection('fund.eastmoney.com', timeout=10)
        conn.request(method='GET', url='http://fund.eastmoney.com/js/fundcode_search.js')
        responsedata = conn.getresponse().read()
        conn.close()
        pattern = re.compile(r'\["([^"]*)","([^"]*)","([^"]*)","([^"]*)","([^"]*)"\]')
        funddata = list()
        conna = httplib.HTTPConnection('fundmobapi.eastmoney.com', timeout=10)
        for i in pattern.finditer(responsedata):
            d = i.groups()
            try:
                burl = 'https://fundmobapi.eastmoney.com/FundMApi/FundBasicInformation.ashx?version=5.3.0&plat=Android&appType=ttjj&FCODE=%s&deviceid=1&product=EFund'
                conna.request(method='GET', url=burl % d[0])
                responsedata = conna.getresponse().read()
                data = json.loads(responsedata)['Datas']
                funddata.append((d[0], d[2].decode('utf-8'), d[3].decode('utf-8'), data['ISSBDATE'], data['ENDNAV']))
            except:
                pass
        conna.close()
        # build base info
        try:
            cu.execute(
                'create table fundinfo (codenum string primary key, name string, type string, date string, size string)')
        except:
            pass
        for item in funddata:
            cu.execute('insert or ignore into fundinfo values (?,?,?,?,?)', item)
        cu.commit()
        urlbase = 'api.fund.eastmoney.com'
        params = '/f10/lsjz?fundCode=%s&pageIndex=1&pageSize=10000&startDate=2000-01-01'
        headers = {
            'Host': 'api.fund.eastmoney.com',
            'Referer': 'http://fund.eastmoney.com/f10/jjjz_000001.html'
        }
        # add fund info
        for item in funddata:
            code = '%06d' % int(item[0])
            tblname = '_' + code
            print(tblname)
            conn = httplib.HTTPConnection(urlbase, timeout=10)
            conn.request(method='GET', url='http://' + urlbase + params % code, headers=headers)
            responsedata = conn.getresponse().read()
            conn.close()
            try:
                cu.execute(
                    'create  table %s (FSRQ string primary key, DWJZ float, JZZZL float, LJJZ float, NAVTYPE int)' % tblname)
            except:
                pass
            try:
                d = json.loads(responsedata)['Data']['LSJZList']
                for item in d:
                    cu.execute('insert or ignore into %s values (?,?,?,?,?)' % tblname,
                               (item['FSRQ'], item['DWJZ'], item['JZZZL'], item['LJJZ'], item['NAVTYPE']))
                cu.commit()
            except Exception as e:
                print(e)
        cu.close()

"""
    vnum: 因子数    po:预测后置数    pn: 预测单位数    grad: 合并参数    valt: data类型
"""
def detect_wave_rfc(data, vnum, X, y, grad=0.0, valt='single', mode='learn'): # 波浪检测
    if valt == 'single':
        i_data = list()  # index list
        for i in range(1, len(data) - 1):
            if (data[i + 1] - data[i]) * (data[i - 1] - data[i]) / (data[i] * data[i]) > grad:
                i_data.append(i)
        if vnum + 2 > len(i_data):
            return
        ibe, ien = i_data[vnum + 1], len(data)
        if ibe >= ien:
            return
        if mode == 'learn':
            for i in range(ibe, ien):
                # 取前8个波形
                x = list()
                for k in range(0, len(i_data)):
                    if i_data[k] >= i:
                        break
                x += [data[i_data[j + 1]] / data[i_data[j]] for j in range(k - vnum - 1, k - 1)]
                x += [data[j + 1] / data[j] for j in range(i - vnum - 1, i - 1)]
                X.append(x)
                y.append(data[i] > data[i - 1])
        elif mode == 'predict':
            i = len(data)
            x = list()
            for k in range(0, len(i_data)):
                if i_data[k] >= i:
                    break
            x += [data[i_data[j + 1]] / data[i_data[j]] for j in range(k - vnum - 1, k - 1)]
            x += [data[j + 1] / data[j] for j in range(i - vnum - 1, i - 1)]
            X.append(x)
    elif valt == 'openclose': # open=[0] close=[1]
        i_data = list()  # index list
        j_data = list()
        for i in range(1, len(data) - 1):
            if (data[i + 1][0] - data[i][0]) * (data[i - 1][0] - data[i][0]) / (data[i][0] * data[i][0]) > grad:
                i_data.append(i)
            if (data[i + 1][1] - data[i][1]) * (data[i - 1][1] - data[i][1]) / (data[i][1] * data[i][1]) > grad:
                j_data.append(i)
        if vnum + 2 > len(i_data) or vnum + 2 > len(j_data):
            return
        ibe, ien = max(i_data[vnum + 1], j_data[vnum + 1]), len(data)
        if ibe >= ien:
            return
        if mode == 'learn':
            for i in range(ibe, ien):
                # 取前8个波形
                x = list()
                for k in range(0, len(i_data)):
                    if i_data[k] >= i:
                        break
                for l in range(0, len(j_data)):
                    if j_data[l] >= i:
                        break
                x += [data[i_data[j + 1]][0] / data[i_data[j]][0] for j in range(k - vnum - 1, k - 1)]
                x += [data[j_data[j + 1]][1] / data[j_data[j]][1] for j in range(l - vnum - 1, l - 1)]
                x += [data[j + 1][0] / data[j][0] for j in range(i - vnum - 1, i - 1)]
                x += [data[j + 1][1] / data[j][1] for j in range(i - vnum - 1, i - 1)]
                X.append(x)
                y.append(data[i][1] > data[i - 1][0]) # close > open
        elif mode == 'predict':
            i = len(data)
            x = list()
            for k in range(0, len(i_data)):
                if i_data[k] >= i:
                    break
            for l in range(0, len(j_data)):
                if j_data[l] >= i:
                    break
            x += [data[i_data[j + 1]][0] / data[i_data[j]][0] for j in range(k - vnum - 1, k - 1)]
            x += [data[j_data[j + 1]][1] / data[j_data[j]][1] for j in range(l - vnum - 1, l - 1)]
            x += [data[j + 1][0] / data[j][0] for j in range(i - vnum - 1, i - 1)]
            x += [data[j + 1][1] / data[j][1] for j in range(i - vnum - 1, i - 1)]
            X.append(x)
    return

"""
    vnum: 因子数    po:预测后置数    pn: 预测单位数    grad: 合并参数    valt: data类型
"""
def detect_wave_rfr(data, vnum, X, y, grad=0.0, valt='single', mode='learn'): # 波浪检测
    if valt == 'single':
        i_data = list()  # index list
        for i in range(1, len(data) - 1):
            if (data[i + 1] - data[i]) * (data[i - 1] - data[i]) / (data[i] * data[i]) > grad:
                i_data.append(i)
        if vnum + 2 > len(i_data):
            return
        ibe, ien = i_data[vnum + 1], len(data)
        if ibe >= ien:
            return
        if mode == 'learn':
            for i in range(ibe, ien):
                # 取前8个波形
                x = list()
                for k in range(0, len(i_data)):
                    if i_data[k] >= i:
                        break
                x += [data[i_data[j + 1]] / data[i_data[j]] for j in range(k - vnum - 1, k - 1)]
                x += [data[j + 1] / data[j] for j in range(i - vnum - 1, i - 1)]
                X.append(x)
                y.append(data[i] / data[i - 1])
        elif mode == 'predict':
            i = len(data)
            x = list()
            for k in range(0, len(i_data)):
                if i_data[k] >= i:
                    break
            x += [data[i_data[j + 1]] / data[i_data[j]] for j in range(k - vnum - 1, k - 1)]
            x += [data[j + 1] / data[j] for j in range(i - vnum - 1, i - 1)]
            X.append(x)
    elif valt == 'openclose': # open=[0] close=[1]
        i_data = list()  # index list
        j_data = list()
        for i in range(1, len(data) - 1):
            if (data[i + 1][0] - data[i][0]) * (data[i - 1][0] - data[i][0]) / (data[i][0] * data[i][0]) > grad:
                i_data.append(i)
            if (data[i + 1][1] - data[i][1]) * (data[i - 1][1] - data[i][1]) / (data[i][1] * data[i][1]) > grad:
                j_data.append(i)
        if vnum + 2 > len(i_data) or vnum + 2 > len(j_data):
            return
        ibe, ien = max(i_data[vnum + 1], j_data[vnum + 1]), len(data)
        if ibe >= ien:
            return
        if mode == 'learn':
            for i in range(ibe, ien):
                # 取前8个波形
                x = list()
                for k in range(0, len(i_data)):
                    if i_data[k] >= i:
                        break
                for l in range(0, len(j_data)):
                    if j_data[l] >= i:
                        break
                x += [data[i_data[j + 1]][0] / data[i_data[j]][0] for j in range(k - vnum - 1, k - 1)]
                x += [data[j_data[j + 1]][1] / data[j_data[j]][1] for j in range(l - vnum - 1, l - 1)]
                x += [data[j + 1][0] / data[j][0] for j in range(i - vnum - 1, i - 1)]
                x += [data[j + 1][1] / data[j][1] for j in range(i - vnum - 1, i - 1)]
                X.append(x)
                y.append(data[i][1] / data[i - 1][0]) # close > open
        elif mode == 'predict':
            i = len(data)
            x = list()
            for k in range(0, len(i_data)):
                if i_data[k] >= i:
                    break
            for l in range(0, len(j_data)):
                if j_data[l] >= i:
                    break
            x += [data[i_data[j + 1]][0] / data[i_data[j]][0] for j in range(k - vnum - 1, k - 1)]
            x += [data[j_data[j + 1]][1] / data[j_data[j]][1] for j in range(l - vnum - 1, l - 1)]
            x += [data[j + 1][0] / data[j][0] for j in range(i - vnum - 1, i - 1)]
            x += [data[j + 1][1] / data[j][1] for j in range(i - vnum - 1, i - 1)]
            X.append(x)
    return

if __name__ == '__main__':
    '''
    for period in AICoin().availperiod:
        aicoin = AICoin()
        cx = sqlite3.connect('aicoin_' + getstrforperiod(period))
        for site in aicoin.availsite:
            aicoin.get_data(site, period, cx)
        cx.close()
    '''
    #EastmoneyData().get_data()
    '''
    period = 168# 24 168 720
    cx = sqlite3.connect('tushare_' + getstrforperiod(period * 3600))
    TuShareData().get_data(period, cx)
    '''

