# -*- coding: utf-8 -*-

# 交易模拟器
import sqlite3
import time
from sklearn.externals import joblib
import numpy as np

def GetX(t, cu, tbl):
    cmdx = 'select avg(o), avg(c), max(h), min(l), sum(v) from %s where t >= %d and t < %d'
    x = list()

    x += list(cu.execute(cmdx % (tbl, t - 300, t)).fetchone())  # 前1个5分钟
    x += list(cu.execute(cmdx % (tbl, t - 10800, t)).fetchone())  # 前1个3小时
    x += list(cu.execute(cmdx % (tbl, t - 21600, t - 10800)).fetchone())  # 前2个3小时
    x += list(cu.execute(cmdx % (tbl, t - 32400, t - 21600)).fetchone())  # 前3个3小时
    x += list(cu.execute(cmdx % (tbl, t - 43200, t - 32400)).fetchone())  # 前4个3小时
    x += list(cu.execute(cmdx % (tbl, t - 54000, t - 43200)).fetchone())  # 前5个3小时
    x += list(cu.execute(cmdx % (tbl, t - 64800, t - 54000)).fetchone())  # 前5个3小时
    x += list(cu.execute(cmdx % (tbl, t - 75600, t - 64800)).fetchone())  # 前6个3小时
    x += list(cu.execute(cmdx % (tbl, t - 86400, t - 75600)).fetchone())  # 前7个3小时
    x += list(cu.execute(cmdx % (tbl, t - 97200, t - 86400)).fetchone())  # 前8个3小时

    for i in range(0, len(x)):
        if x[i] is None:  # 用第一个合法数据填补缺失值
            return None
    return x


class ControlCenter(object):
    def __init__(self, buythresh, sellthupthresh, selldownthresh, tbls, use5min=True):
        self.buythresh = buythresh
        self.sellupthresh = sellthupthresh
        self.selldownthresh = selldownthresh
        self.cx = sqlite3.connect('digitalcash.db')
        self.cu = self.cx.cursor()
        self.comm_coins_tables = tbls # 主区币列表
        self.btc_coins_tables = list() # BTC区币列表
        self.comm_coins = dict() # 主区币种数量
        self.comm_coins_price = dict()
        self.comm_coins_price_max = dict()
        self.btc_coins = dict() # BTC区币种数量
        self.btc_coins_price = dict()
        self.btc_coins_price_max = dict()
        self.dollaramount = 0.0
        self.btcamount = 0.0

        self.machines = dict()
        for tbl in tbls:
            if use5min:
                self.machines[tbl] = joblib.load('traindata/' + tbl + '5min.mac')
            else:
                self.machines[tbl] = joblib.load('traindata/' + tbl + '1min.mac')

        self.ratio_ = {  # 归一化价格，提高预测精度
            'BTC': 10000.0, 'BCH': 1000.0, 'XRP': 1.0, 'ETH': 1000.0, 'LTC': 100.0,
            'DASH': 1000.0,  'EOS': 10.0, 'ETC': 10.0, 'OMG': 10.0, 'ZEC': 100.0,
            'XEM': 1.0, 'ELF': 1.0, 'SMT': 0.1, 'IOST': 0.1, 'VEN': 10.0, 'QTUM': 10.0,
            'NEO': 100.0, 'HSR': 10.0, 'CVC': 1.0, 'STORJ': 1.0, 'GNT': 1.0, 'SNT': 0.1
        }

    def initmoney(self, dollaramount=0.0, btcamount=0.0):
        for tbl in self.comm_coins_tables:
            self.comm_coins[tbl] = 0.0
            self.comm_coins_price[tbl] = 0.0
            self.comm_coins_price_max[tbl] = 0.0
        for tbl in self.btc_coins_tables:
            self.btc_coins[tbl] = 0.0
            self.btc_coins_price[tbl] = 0.0
            self.btc_coins_price_max[tbl] = 0.0
        self.dollaramount = dollaramount
        self.btcamount = btcamount

    def inittime(self):
        # 获取合法时间段
        self.gtime = 0
        self.maxt = 0xffffffff
        for tbl in self.comm_coins_tables:
            curmint, curmaxt, = self.cx.execute("select min(t),max(t) from %s" % tbl).fetchone()
            if curmaxt < self.maxt:
                self.maxt = curmaxt
        self.maxt -= 180
        self.gtime = self.maxt - 888840 # 预测3天余量


    def buy(self, coinid, amount = -1.0):
        # 以市价买入(下一次开盘价)         -1 全买
        curprice, = self.cu.execute('select o from %s where t==%d' % (coinid, self.gtime + 60)).fetchone()
        if coinid in self.comm_coins_tables:
            if self.dollaramount < 1.0:
                return
            if amount < 0.0: # -1
                amount = self.dollaramount
            elif amount > self.dollaramount:
                amount = self.dollaramount
            self.comm_coins[coinid] += amount * 0.998 / curprice # 火币费率
            self.dollaramount -= amount
            self.comm_coins_price[coinid] = curprice
            self.comm_coins_price_max[coinid] = curprice
        elif coinid in self.btc_coins_tables:
            if self.btcamount < 0.00001:
                return
            if amount < 0.0: # -1
                amount = self.btcamount
            elif amount > self.btcamount:
                amount = self.btcamount
            self.btc_coins[coinid] += amount * 0.998 / curprice # 火币费率
            self.btcamount -= amount
            self.btc_coins_price[coinid] = curprice
            self.btc_coins_price_max[coinid] = curprice
        self.optime += 1

        # print 'buy %s' % time.ctime(self.gtime), self.comm_coins, self.dollaramount

    def sell(self, coinid, amount = -1.0):
        # 以市价卖出(下一次开盘价)         -1全卖
        curprice, = self.cu.execute('select o from %s where t==%d' % (coinid, self.gtime + 60)).fetchone()
        if coinid in self.comm_coins_tables:
            if self.comm_coins[coinid] < 0.00001:
                return
            if amount < 0.0: # -1
                amount = self.comm_coins[coinid]
            elif amount > self.comm_coins[coinid]:
                amount = self.comm_coins[coinid]
            self.dollaramount += amount * 0.998 * curprice # 火币费率
            self.comm_coins[coinid] -= amount
            self.comm_coins_price[coinid] = 0.0
            self.comm_coins_price_max[coinid] = 0.0
        elif coinid in self.btc_coins_tables:
            if self.btc_coins[coinid] < 1.0:
                return
            if amount < 0.0: # -1
                amount = self.btc_coins[coinid]
            elif amount > self.btc_coins[coinid]:
                amount = self.btc_coins[coinid]
            self.btcamount += amount * 0.998 * curprice # 火币费率
            self.btc_coins[coinid] -= amount
            self.btc_coins_price[coinid] = 0.0
            self.btc_coins_price_max[coinid] = 0.0
        self.optime += 1

        # print 'sell %s' % time.ctime(self.gtime), self.comm_coins, self.dollaramount

    def sellall(self):
        for coinid in self.comm_coins_tables:
            if self.comm_coins[coinid] < 0.00001:
                continue
            curprice, = self.cu.execute('select o from %s where t==%d' % (coinid, self.gtime + 60)).fetchone()
            amount = self.comm_coins[coinid]
            self.dollaramount += amount * 0.998 * curprice # 火币费率
            self.comm_coins[coinid] -= amount
            self.comm_coins_price[coinid] = 0.0
            self.comm_coins_price_max[coinid] = 0.0
        for coinid in self.btc_coins_tables:
            if self.btc_coins[coinid] < 1.0:
                continue
            curprice, = self.cu.execute('select o from %s where t==%d' % (coinid, self.gtime + 60)).fetchone()
            amount = self.btc_coins[coinid]
            self.btcamount += amount * 0.998 * curprice # 火币费率
            self.btc_coins[coinid] -= amount
            self.btc_coins_price[coinid] = 0
            self.btc_coins_price_max[coinid] = 0
        self.optime += 1

    def get_policy_result(self, coinid, tl):
        # 返回1买， 返回-1卖， 返回0持有

        # 策略1 => 1分钟内涨幅降幅达到各自门限的单个币     门限1天为单位，实时更新
        '''
        op, = self.cu.execute('select o from %s where t==%d' % (coinid, (self.gtime - tl))).fetchone() # 开盘价
        cp, = self.cu.execute('select c from %s where t==%d' % (coinid, (self.gtime - 60))).fetchone() # 收盘价
        if cp / op > self.buythresh:
            return 1
        elif cp / op < self.sellthresh:
            return -1
        return 0
        '''
        # 策略2 => 1分钟内涨幅降幅超过各自门限的多个币     均摊
        op, = self.cu.execute('select o from %s where t==%d' % (coinid, (self.gtime - tl))).fetchone() # 开盘价
        cp, = self.cu.execute('select c from %s where t==%d' % (coinid, (self.gtime - 60))).fetchone() # 收盘价

        x = list()
        # 取前2分钟做预测
        x += list(self.cu.execute('select o, c, h, l from %s where t == %d' % (coinid, self.gtime - 60)).fetchone())
        x += list(self.cu.execute('select o, c, h, l from %s where t == %d' % (coinid, self.gtime - 120)).fetchone())
        ratiokey = coinid.replace('huobipro_', '')
        X = np.array([x]) / self.ratio_[ratiokey]
        pcp = self.machines[coinid].predict(X)[0] # predict price


        bp = 0.0
        mp = 0.0 # max price
        if coinid in self.comm_coins_tables:
            bp = self.comm_coins_price[coinid] # 买入价
            if op > self.comm_coins_price_max[coinid]:
                self.comm_coins_price_max[coinid] = op
            if cp > self.comm_coins_price_max[coinid]:
                self.comm_coins_price_max[coinid] = cp
            mp = self.comm_coins_price_max[coinid]
        elif coinid in self.btc_coins_tables:
            bp = self.btc_coins_price[coinid]
            if op > self.btc_coins_price_max[coinid]:
                self.btc_coins_price_max[coinid] = op
            if cp > self.btc_coins_price_max[coinid]:
                self.btc_coins_price_max[coinid] = cp
            mp = self.btc_coins_price_max[coinid]
        #if cp / op > self.buythresh: # 涨到一定程度则入手
        #    return 1
        #elif bp > 0.0 and (cp / bp > self.sellupthresh or cp / bp < self.selldownthresh): # 已经入手且涨到一定程度则出手
        #    return -1
        #elif mp > 0.0 and cp / mp < self.selldownthresh: # 已经入手且涨到一定程度则出手
        #    return -1
        if pcp / op > self.buythresh:
            return 1
        elif mp > 0.0 and pcp / mp < self.selldownthresh: # 已经入手且预测会降到一定比例
            return -1
        return 0

    def getgain(self, tl):
        gain_all = self.runloop(tl) # 全段增益
        # gain_down = self.runloop(down_begin, down_end, tl)# 下降段增益
        print self.buythresh, self.sellupthresh, self.selldownthresh, gain_all[0], gain_all[1]
        return gain_all[0]

    def runloop(self, tl):
        self.inittime()
        self.initmoney(dollaramount=10000)
        self.optime = 0

        while True:
            sell_coins = list()
            buy_coins = list()
            for coinid in self.comm_coins_tables:
                c = self.get_policy_result(coinid, tl)
                if c == -1: # 卖出信号
                    sell_coins.append(coinid)
                elif c == 0: # 继续持有或者空仓
                    pass
                elif c == 1: # 买入信号
                    buy_coins.append(coinid)
            for item in sell_coins:
                self.sell(item)
            for item in buy_coins:
                self.buy(item, amount=self.dollaramount/len(buy_coins)) # 分摊
            #print 'Current time=%s dollar=%s coin=%s' % (self.gtime, self.dollaramount, self.comm_coins)

            self.gtime += tl

            while True:
                isok = True
                for item in self.comm_coins_tables:
                    nt1 = self.cu.execute('select t from %s where t==%d' % (item, self.gtime)).fetchone()
                    nt2 = self.cu.execute('select t from %s where t==%d' % (item, self.gtime + tl)).fetchone()
                    nt3 = self.cu.execute('select t from %s where t==%d' % (item, self.gtime - tl)).fetchone()
                    nt4 = self.cu.execute('select t from %s where t==%d' % (item, self.gtime + 2 * tl)).fetchone()
                    if nt1 is None or nt2 is None or nt3 is None or nt4 is None: # 时间不连续'
                        self.sellall()
                        self.gtime += tl
                        isok = False
                        break
                if isok:
                    break
            if self.gtime >= self.maxt:
                break
        # print errcount
        self.sellall()
        return self.optime, self.dollaramount / 10000.0

def frange(x, y, jump):
    if jump > 0.0:
        while x < y:
            yield x
            x += jump
    elif jump < 0.0:
        while x > y:
            yield x
            x += jump

# 1.014 0.985 1011 1.13644701958

import threadpool
if __name__ == '__main__':
    pool = threadpool.ThreadPool(2)
    args = list()
    '''
    for buythresh in frange(1.00, 1.05, 0.01):
        for sellupthresh in frange(1.01, 1.05, 0.01):
            for selldownthresh in frange(0.99, 0.95, -0.01):
                args.append({'arg1':buythresh, 'arg2':sellupthresh,'arg3':selldownthresh})
    requests = threadpool.makeRequests(lambda carg: ControlCenter(buythresh=carg['arg1'], sellthupthresh=carg['arg2'], selldownthresh=carg['arg3']).getgain(60), args)
    [pool.putRequest(req) for req in requests]
    pool.wait()
    '''
    #for buythresh in frange(1.010, 1.001, -0.001):
    #    for selldownthresh in frange(0.90, 0.98, 0.01):
    #buythresh = 1.006
    #selldownthresh = 0.92
    tbls = ['huobipro_EOS', 'huobipro_ETH', 'huobipro_OMG', 'huobipro_XRP', 'huobipro_ZEC']
    #tbls = ['huobipro_GNT', 'huobipro_SNT', 'huobipro_CVC']

    for buythresh in frange(1.001 , 1.009, 0.001):
        for selldownthresh in frange(0.998, 0.985 , -0.001):
            ControlCenter(buythresh, 0.0, selldownthresh, tbls, use5min=True).getgain(60)

# 1.006 0.0 0.92 1080 1.43089288825 老方式

'''新方式
1.003 0.0 0.996 1401 12.5469636229
1.003 0.0 0.995 1299 10.8663905117
1.003 0.0 0.994 1175 11.8316084557
1.003 0.0 0.993 1069 10.3887163542
1.004 0.0 0.998 1275 11.1172858965
1.004 0.0 0.997 1205 11.5745643027
1.004 0.0 0.996 1111 14.3638341349
1.004 0.0 0.995 1053 12.2681686347
1.004 0.0 0.994 989 13.1326687923
1.004 0.0 0.993 909 11.8009702802
1.004 0.0 0.992 851 10.2375119841
1.005 0.0 0.998 985 12.3365723754
1.005 0.0 0.997 943 12.318184034
1.005 0.0 0.996 883 14.455391234
1.005 0.0 0.995 839 12.7748413459
1.005 0.0 0.994 801 13.4872051462
1.005 0.0 0.993 741 12.2346299964
1.005 0.0 0.992 699 11.0779757715
1.005 0.0 0.991 667 10.1121607448
1.006 0.0 0.998 809 10.1922924324
1.006 0.0 0.997 779 10.277665708
1.006 0.0 0.996 737 11.3848652664
1.006 0.0 0.995 703 10.3214453609
1.006 0.0 0.994 675 11.1966086655
1.006 0.0 0.993 635 10.7124143927
1.006 0.0 0.992 597 10.2696751067
'''

