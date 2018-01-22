# -*- coding: utf-8 -*-

# 交易模拟器
import sqlite3
import time

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
    def __init__(self, buythresh, sellthresh):
        self.buythresh = buythresh
        self.sellthresh = sellthresh
        self.cx = sqlite3.connect('digitalcash.db')
        self.cu = self.cx.cursor()
        self.comm_coins_tables = ['huobipro_BCH', 'huobipro_BTC', 'huobipro_EOS', 'huobipro_ETH',
                  'huobipro_LTC', 'huobipro_OMG', 'huobipro_XRP', 'huobipro_ZEC'] # 主区币列表
        self.btc_coins_tables = list() # BTC区币列表
        self.comm_coins = dict() # 主区币种数量
        self.btc_coins = dict() # BTC区币种数量
        self.dollaramount = 0.0
        self.btcamount = 0.0


    def initmoney(self, dollaramount=0.0, btcamount=0.0):
        for tbl in self.comm_coins_tables:
            self.comm_coins[tbl] = 0.0
        for tbl in self.btc_coins_tables:
            self.btc_coins[tbl] = 0.0
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
        self.gtime = self.maxt - 888888 # 预测3天余量


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
        elif coinid in self.btc_coins_tables:
            if self.btcamount < 0.00001:
                return
            if amount < 0.0: # -1
                amount = self.btcamount
            elif amount > self.btcamount:
                amount = self.btcamount
            self.btc_coins[coinid] += amount * 0.998 / curprice # 火币费率
            self.btcamount -= amount
        self.optime += 1

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
        elif coinid in self.btc_coins_tables:
            if self.btc_coins[coinid] < 1.0:
                return
            if amount < 0.0: # -1
                amount = self.btc_coins[coinid]
            elif amount > self.btc_coins[coinid]:
                amount = self.btc_coins[coinid]
            self.btcamount += amount * 0.998 * curprice # 火币费率
            self.btc_coins[coinid] -= amount
        self.optime += 1

    def sellall(self):
        for coinid in self.comm_coins_tables:
            if self.comm_coins[coinid] < 0.00001:
                return
            curprice, = self.cu.execute('select o from %s where t==%d' % (coinid, self.gtime + 60)).fetchone()
            amount = self.comm_coins[coinid]
            self.dollaramount += amount * 0.998 * curprice # 火币费率
            self.comm_coins[coinid] -= amount
        for coinid in self.btc_coins_tables:
            if self.btc_coins[coinid] < 1.0:
                return self.btc_coins[coinid]
            curprice, = self.cu.execute('select o from %s where t==%d' % (coinid, self.gtime + 60)).fetchone()
            amount = self.btc_coins[coinid]
            self.btcamount += amount * 0.998 * curprice # 火币费率
            self.btc_coins[coinid] -= amount
        self.optime += 1

    def get_policy_result(self, coinid, tl):
        # 返回1买， 返回-1卖， 返回0持有

        # 策略1 => 1分钟内涨幅降幅达到各自门限的单个币     门限1天为单位，实时更新
        op, = self.cu.execute('select o from %s where t==%d' % (coinid, (self.gtime - tl))).fetchone()
        cp, = self.cu.execute('select c from %s where t==%d' % (coinid, (self.gtime - 60))).fetchone()
        if cp / op > self.buythresh:
            return 1
        elif cp / op < self.sellthresh:
            return -1
        return 0

        # 策略2 => 1分钟内涨幅降幅超过各自门限的多个币     均摊

    def getgain(self, tl):
        gain_all = self.runloop(tl) # 全段增益
        # gain_down = self.runloop(down_begin, down_end, tl)# 下降段增益
        return gain_all[0], gain_all[1]

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
                    if nt1 is None or nt2 is None or nt3 is None: # 时间不连续'
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

if __name__ == '__main__':
    buythresh = 1.01
    sellthresh = 0.989
    for buythresh in frange(1.000, 1.020, 0.001):
        for sellthresh in frange(0.999, 0.980, -0.001):
            opc, ratio, = ControlCenter(buythresh=buythresh, sellthresh=sellthresh).getgain(60)

