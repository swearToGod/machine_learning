# -*- coding: utf-8 -*-
import sqlite3
import utils
import numpy
import math
import time

class ratiof_fix(object):
    def __init__(self):
        self.name = 'fix'

    def ratio(self, curprice):
        return 1


class ratiof_linear(object):
    def __init__(self):
        self.name = 'linear'

    def ratio(self, curprice):
        return 1.0 / curprice


class ratiof_square(object):
    def __init__(self, time):
        self.name = 'square%d' % time
        self.time = time

    def ratio(self, curprice):
        val = 1.0 / curprice ** self.time
        if val > 10:
            val = 10
        return val


def getavaildays(fi_beginday, fi_data):
    beginday = fi_beginday % 100
    beginmonth = (fi_beginday / 100) % 100
    beginyear = (fi_beginday / 10000)
    mintime = fi_data[0][0]
    maxtime = fi_data[-1][0]
    srclist = [t[0] for t in fi_data]
    result = list()
    while True:
        newtime = beginday + beginmonth * 100 + beginyear * 10000
        if newtime > maxtime:
            break
        if newtime not in srclist:
            for t in range(1, 60):
                tbeginday = beginday + t
                tbeginmonth = beginmonth
                if tbeginday > 28:
                    tbeginday -= 28
                    tbeginmonth += 1
                newtime = tbeginday + tbeginmonth * 100 + beginyear * 10000
                if newtime in srclist:
                    break
        result.append(newtime)
        beginmonth += 1
        if beginmonth > 12:
            beginmonth = 1
            beginyear += 1
    return result


ratiof_arr = [ratiof_square(i) for i in range(0, 20)]


#    模拟定投计算收益
# fi_beginday: 开始定投日 (1~28)
# fi_ratiof: 随净值变化的资金投入率变化函数
# fi_data: 净值数据
def monitor_fixed_invest(fi_beginday, fi_ratiof, fi_data, show=False):
    fi_basemoney = 100
    money_in = 0  # 投入资金
    mount = 0  # 持仓
    # print('fi_beginday:%d, fi_ratiof:%s' % (fi_beginday, fi_ratiof.name))
    maxearn = 0
    last_price = fi_data[0][1]
    daynum_arr = getavaildays(fi_beginday, fi_data)
    maxearn = 0

    for e_data in fi_data:
        if e_data[0] > fi_beginday + 10000:  # 模拟1年
            break
        time = e_data[0]
        cur_price = e_data[1]
        if time in daynum_arr:  # 定投日
            cur_invest_money = fi_basemoney * fi_ratiof.ratio(last_price)
            money_in += cur_invest_money
            mount += cur_invest_money / cur_price
            if show:
                print('time:%d price:%f mount:%f invest:%f' % (time, cur_price, mount, cur_invest_money))
        else:  # 计算获利
            if show:
                print('time:%d price:%f mount:%f earn:%f' % (time, cur_price, mount, cur_price * mount / money_in))
            if maxearn < cur_price * mount / money_in:
                maxearn = cur_price * mount / money_in
                maxearn_time = time
    # print('maxearn:%d-%f' % (maxearn_time, maxearn))
    return maxearn


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


from sklearn.pipeline import Pipeline
from sklearn.ensemble import *
from sklearn.cross_validation import train_test_split
from sklearn.metrics import *
from sklearn.model_selection import *
from sklearn.preprocessing import *


def learn_from_data_rfr(X, y, pipe=None):
    if pipe is None:
        regressor = RandomForestRegressor(n_estimators=66, n_jobs=8)  # n_estimators=66
        pipe = Pipeline([['sc', StandardScaler()], ['clf', regressor]])
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.1)  # 测试集占10%
    pipe.fit(X_train, y_train)
    y_pred = pipe.predict(X_test)
    precision = explained_variance_score(y_test, y_pred)
    # print('Accuraty:score=%f' % (precision))
    return pipe, precision

def learn_from_data_rfc(X, y, pipe=None):
    if pipe is None:
        classifier = RandomForestClassifier(n_estimators=66, n_jobs=8) # n_estimators=66
        pipe = Pipeline([['sc', StandardScaler()], ['clf', classifier]])
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.1)  # 测试集占10%
    pipe.fit(X_train, y_train)
    y_pred = pipe.predict(X_test)
    precision = accuracy_score(y_test, y_pred)
    #for f in range(len(X[0])):
    #   print("%2d) %f" % (f + 1, classifier.feature_importances_[f]))
    return pipe, precision


def do_monitor(property_num, period):
    import sqlite3
    dbpath = 'd:\\\\project\\fund.db'
    cu = sqlite3.connect(dbpath)

    X_ = list()  # 期间收益
    y_ = list()
    for tblname in getalltable(dbpath):
        try:
            sql = "select cast(replace(FSRQ,'-','') as int),DWJZ from %s order by FSRQ" % tblname
            g_data = cu.execute(sql).fetchall()
            inf = cu.execute('select size,type,name from fundinfo where codenum=%d' % int(tblname[1:])).fetchone()
            if inf[1] == u'货币型' or inf[1] == u'理财型':
                pass
            else:
                if len(g_data) < property_num * period:
                    continue
                x_ = list()
                for i in range(1, property_num):
                    tx = [j[1] for j in g_data[period * i:period * (i + 1)]]
                    x_.append(numpy.sum(tx))
                X_.append(x_)
                ty = [j[1] for j in g_data[:period]]
                y_.append(numpy.sum(ty))
        except:
            pass
    pipe, precision = learn_from_data_rfr(X_, y_)
    cu.close()
    return pipe, precision


def validate_fund(pipe, property_num, period):  # 寻找拟合度高的
    import sqlite3
    dbpath = 'd:\\\\project\\fund.db'
    cu = sqlite3.connect(dbpath)

    for tblname in getalltable(dbpath):
        try:
            sql = "select cast(replace(FSRQ,'-','') as int),DWJZ from %s order by FSRQ" % tblname
            g_data = cu.execute(sql).fetchall()
            inf = cu.execute('select size,type,name from fundinfo where codenum=%d' % int(tblname[1:])).fetchone()
            if inf[1] == u'货币型' or inf[1] == u'理财型':
                pass
            else:
                if len(g_data) < property_num * period:
                    continue
                x_ = list()
                for i in range(1, property_num):
                    tx = [j[1] for j in g_data[period * i:period * (i + 1)]]
                    x_.append(numpy.sum(tx))
                ty = [j[1] for j in g_data[:period]]
                y_ = numpy.sum(ty)
                y_pred = pipe.predict([x_])
                precision1 = mean_absolute_error([y_], y_pred)
                if precision1 < 0.1:
                    x_ = list()
                    for i in range(0, property_num - 1):
                        tx = [j[1] for j in g_data[period * i:period * (i + 1)]]
                        x_.append(numpy.sum(tx))
                    ratio = pipe.predict([x_])[0] / y_
                    if ratio >= 1.1:
                        print(tblname, ratio)
        except:
            pass
    cu.close()

'''
while True:
    property_num = 5
    period = 30
    pipe, precision = do_monitor(property_num, period)

    print('period=%d property=%d precision=%f' % (period, property_num, precision))
    validate_fund(pipe, property_num, period)  # 最佳
'''

def detect_twine(data, X, y): # 缠检测
    pass

"""
    vnum: 因子数    po:预测后置数    pn: 预测单位数    grad: 合并参数    valt: data类型
"""
def detect_wave_rfc(data, vnum, X, y, grad=1.0, valt='m,m/m', mode='learn'): # 波浪检测
    if valt == 'm,m/m' or valt == 'c,c/c':
        # use mean as base, y as mean(tomorrow)/mean(today)    mean=(open+close)/2
        # use close as base, y as close(tomorrow)/close(today)
        i_data = list()  # index list
        for i in range(1, len(data) - 1):
            if (data[i + 1] - data[i]) * (data[i - 1] - data[i]) / (data[i] * data[i]) > 0.0:
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
                    if i_data[k] >= i - 1:
                        k -= 1
                        break
                x += [data[i_data[j + 1]] / data[i_data[j]] for j in range(k - vnum - 1, k - 1)]
                x += [data[j + 1] / data[j] for j in range(i - vnum - 1, i - 1)]
                X.append(x)
                y.append(data[i] / data[i - 1] >= grad)
        elif mode == 'predict':
            i = len(data)
            x = list()
            for k in range(0, len(i_data)):
                if i_data[k] >= i - 1:
                    k -= 1
                    break
            x += [data[i_data[j + 1]] / data[i_data[j]] for j in range(k - vnum - 1, k - 1)]
            x += [data[j + 1] / data[j] for j in range(i - vnum - 1, i - 1)]
            X.append(x)
    elif valt == 'm,h/c' or valt == 'm,l/c' or valt == 'm,c/c':
            # m,h/c  ->  use mean as base  y as high(tomorrow)/close(today)  mean:0 high:1 close:2
            # m,l/c  ->  use mean as base  y as low(tomorrow)/close(today)  mean:0 low:1 close:2
            # m,c/c  ->  use mean as base  y as close(tomorrow)/close(today)  mean:0 close:1 close:2
        i_data = list()  # index list
        for i in range(1, len(data) - 1):
            if (data[i + 1][0] - data[i][0]) * (data[i - 1][0] - data[i][0]) / (data[i][0] * data[i][0]) > 0.0:
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
                    if i_data[k] >= i - 1:
                        k -= 1
                        break
                x += [data[i_data[j + 1]][0] / data[i_data[j]][0] for j in range(k - vnum - 1, k - 1)]
                x += [data[j + 1][0] / data[j][0] for j in range(i - vnum - 1, i - 1)]
                X.append(x)
                y.append(data[i][1] / data[i - 1][2] >= grad)
        elif mode == 'predict':
            i = len(data)
            x = list()
            for k in range(0, len(i_data)):
                if i_data[k] >= i - 1:
                    k -= 1
                    break
            x += [data[i_data[j + 1]][0] / data[i_data[j]][0] for j in range(k - vnum - 1, k - 1)]
            x += [data[j + 1][0] / data[j][0] for j in range(i - vnum - 1, i - 1)]
            X.append(x)
    return

def detect_his_rfc(data, vnum, X, y, grad=1.0, mode='learn'): # 历史检测
    # close:0 open:1 high:2 low:3 vol:4
    ibe, ien = vnum + 1, len(data)
    if mode == 'learn':
        for i in range(ibe, ien):
            try:
                x = list()
                x += [data[j + 1][0] / data[j][0] for j in range(i - vnum - 1, i - 1)]
                y_ = data[i][0] / data[i - 1][0] >= grad
                X.append(x)
                y.append(y_)
            except:
                pass
    elif mode == 'predict':
        try:
            i = len(data)
            x = list()
            x += [data[j + 1][0] / data[j][0] for j in range(i - vnum - 1, i - 1)]
            X.append(x)
        except:
            pass
    return

# 股票日线参数：total=66666 vnum=? grad=?
'''
      6                    7                    8                         9
1.02  0.873256337183 8666  0.870914542729 8714  0.88200899550224887 8578  0.866716641679 8817
1.03  0.926953652317 4776  0.928785607196 4809  0.8971514242878561  7680  0.923538230885 4894
1.04  0.958602069897 2745  0.956821589205 2760  0.90224887556221889 6900  0.949325337331 2821
1.05  0.973301334933 1672  0.974062968516 1680  0.91349325337331333 6326  0.972113943028 1720
'''

# 股票周线参数：total=66666 vnum=? grad=?
'''
     6                    7                    8                    9
1.04 0.856307184641 9809  0.857421289355 9862  0.840305892937 9903  0.851574212894 9987
1.05 0.892905354732 7296  0.893553223388 7326  0.89248762933 7356   0.888755622189 7420
'''

# 股票月线参数：total=66666 vnum=? grad=?
'''
     6                    7                    8                    9
1.14 0.853117505995 9861  0.862777444511 9825  0.854807259637 9823  0.861856907155 9791
1.15 0.864958033573 9026  0.882273545291 8990  0.868756562172 8994  0.876556172191 8970
1.16 0.879496402878 8238  0.877324535093 8209  0.882705864707 8223  0.883005849708 8200
1.17 0.889238609113 7523  0.893971205759 7500  0.891555422229 7519  0.894855257237 7496
1.18 0.900179856115 6847  0.892471505699 6824  0.905804709765 6852  0.897705114744 6841
'''

# huobi 12小时参数：vnum=10 grad=?
'''
1.05 0.871128871129 10001 1404
1.055 0.893106893107 10001 1229
1.06 0.906093906094 10001 1069
'''

# huobi 6小时参数：vnum=10 grad=?
'''
1.035 0.880079286422 10081 1492
1.04 0.883052527255 10081 1253
1.045 0.919722497522 10081 1059
'''

# huobi 4小时参数：vnum=10 grad=?
'''
1.025 0.849264705882 10877 1764
1.03 0.878676470588 10877 1448
1.035 0.903492647059 10877 1193
'''

def detect_minN_rfc(data, vnum, X, y, grad=8, mode='learn'): # 预测未来N天低点
    # close:0 open:1 high:2 low:3 vol:4
    ibe, ien = vnum + 1, len(data)
    if mode == 'learn':
        for i in range(ibe, ien - vnum):
            try:
                x = list()
                x += [data[j + 1][0] / data[j][0] for j in range(i - vnum - 1, i - 1)]
                y_ = numpy.sum([1 if data[j][0] >= data[i - 1][0] else 0 for j in range(i - 2, i + grad - 1)]) >= grad + 1
                X.append(x)
                y.append(y_)
            except:
                pass
    elif mode == 'predict':
        i = ien
        try:
            x = list()
            x += [data[j + 1][0] / data[j][0] for j in range(i - vnum - 1, i - 1)]
            X.append(x)
        except:
            pass

# 股票日线参数：total=66666 vnum=? thres=?
'''
   6                         7                         8                         9
6  0.87897420515896818 8126  0.88142707240293805 8227  0.87884240515819467 8326  0.88200899550224887 8578
7  0.89547090581883626 7230  0.89551791335631836 7326  0.89143799670115464 7439  0.8971514242878561  7680
8  0.904619076184763   6445  0.90016489281966716 6574  0.9037336932073774  6684  0.90224887556221889 6900
9  0.91831534772182255 5934  0.91515514915305052 6001  0.91348028190133457 6129  0.91349325337331333 6326
'''

# 股票周线参数：total=66666 vnum=? thres=?
'''
   6                         7                         8                         9
6  0.88527294541091783 7727  0.89278752436647169 7614  0.89157168566286737 7807  0.88982161594963272  7930
7  0.89922015596880622 6807  0.90178437546858603 6767  0.91226754649070185 6925  0.90226352870634086  7038
8  0.91556688662267549 6158  0.91318038686459735 6128  0.9115176964607079 6277   0.90885924149302955  6373
9  0.92026378896882499 5635  0.91737891737891741 5667  0.92291541691661672 5817  0.91905261579973019  5927

'''

# 股票月线参数：total=66666 vnum=? thres=?
'''
   6                         7                         8                         9
6  0.86913506220956382 8984  0.87509371719898033 8949  0.87464387464387461 9046  0.87672465506898623 9096
7  0.88112726727627044 8224  0.87899235267656317 8194  0.88049182786024893 8298  0.88392321535692864 8338
8  0.88937190825963119 7658  0.88603988603988604 7632  0.88903883640725745 7732  0.89502099580083982 7771
9  0.895952023988006   7235  0.89863547758284601 7081  0.89428699955015745 7169  0.89652069586082783 7191
'''

# huobi 12小时参数：vnum=?
'''
4 0.882527147088 1231
5 0.896517412935 1105
'''

# huobi 6小时参数：vnum=?
'''
4 0.888779527559 1183
5 0.906126482213 1065
'''

# huobi 4小时参数：vnum=?
'''
4 0.883912248629 1323
5 0.900183150183 1134
'''

def monitor_wave(dbpath, filter, vnum, thres):
    cu = sqlite3.connect(dbpath)

    for vnum in range(6, 10):
        for tt in range(2, 6):
            thres = 1 + tt/100.0

            X = list()
            y = list()
            for tblname in getalltable(dbpath):
                # mean:0 high:1 close:2
                if filter is not None and not tblname.startswith(filter):
                    continue
                g_data = cu.execute("select time,close,open,high,low from %s order by time" % tblname).fetchall()
                t_data = [[i[1],i[2],i[3],i[4]] for i in g_data[-66:]]
                detect_his_rfc(t_data, vnum, X, y, thres, 'learn')
                if len(y) > 66666:
                    break
            pipe, precision = learn_from_data_rfc(X, y)

            print vnum, thres, precision,numpy.sum([1 if i else 0 for i in y])

    cu.close()
    return pipe

def evaluate_wave(dbpath, pipe, filter, vnum, thres):
    cu = sqlite3.connect(dbpath)

    for tblname in getalltable(dbpath):
        if filter is not None and not tblname.startswith(filter):
            continue
        X = list()
        y = list()
        X_p = list()
        # mean:0 high:1 close:2
        g_data = cu.execute("select time,close,open,high,low from %s order by time" % tblname).fetchall()
        t_data = [[i[1], i[2], i[3], i[4]] for i in g_data]
        if len(t_data) < 100:
            continue
        detect_his_rfc(t_data, vnum, X, y, thres, 'learn')
        pipe, precision = learn_from_data_rfc(X, y, pipe)
        detect_his_rfc(t_data, vnum, X_p, y, thres, 'predict')
        if pipe.predict(X_p)[0] and precision >= 0.9 and len(y) > 20:
            print(tblname, precision, time.ctime(g_data[-1][0]))
    cu.close()

def monitor_minN(dbpath, filter, vnum, thres):
    cu = sqlite3.connect(dbpath)

    for vnum in range(6, 10):
        for thres in range(6, 10):
            X = list()
            y = list()
            for tblname in getalltable(dbpath):
                # mean:0 high:1 close:2
                if filter is not None and not tblname.startswith(filter):
                    continue
                g_data = cu.execute("select time,close,open,high,low from %s order by time" % tblname).fetchall()
                t_data = [[i[1],i[2],i[3],i[4]] for i in g_data[-66:]]
                detect_minN_rfc(t_data, vnum, X, y, thres, 'learn')
                if len(y) > 66666:
                    break
            pipe, precision = learn_from_data_rfc(X, y)
            print(vnum,thres, precision, numpy.sum([1 if i else 0 for i in y]))

    cu.close()
    return pipe

def evaluate_minN(dbpath, pipe, filter, vnum, thres):
    cu = sqlite3.connect(dbpath)

    for tblname in getalltable(dbpath):
        if filter is not None and not tblname.startswith(filter):
            continue
        X = list()
        y = list()
        X_p = list()
        # mean:0 high:1 close:2
        g_data = cu.execute("select time,close,open,high,low from %s order by time" % tblname).fetchall()
        t_data = [[i[1], i[2], i[3], i[4]] for i in g_data]
        if len(t_data) < 100:
            continue
        detect_minN_rfc(t_data, vnum, X, y, thres, 'learn')
        pipe, precision = learn_from_data_rfc(X, y, pipe)
        detect_minN_rfc(t_data, vnum, X_p, y, thres, 'predict')
        if pipe.predict(X_p)[0] and precision >= 0.9 and len(y) > 20:
            print(tblname, precision, time.ctime(g_data[-1][0]))
    cu.close()

import utils

update = False

dbpaths = [
    #{'d':12, 'p': 'aicoin_12hour', 's': 1.045, 'f':'huobipro'},
    #{'d':6, 'p': 'aicoin_6hour', 's': 1.03, 'f':'huobipro'},
    #{'d':4, 'p': 'aicoin_4hour', 's': 1.02, 'f':'huobipro'},
    {'d':24, 'p': 'tushare_24hour', 'vnum': 6, 'thres': 1.02, 'f':None},
    {'d':168, 'p': 'tushare_168hour', 'vnum': 6, 'thres': 1.04, 'f':None},
    {'d':720, 'p': 'tushare_720hour', 'vnum': 6, 'thres': 1.14, 'f':None},
]
for dbpath in dbpaths:
    # update
    if dbpath['p'].find('aicoin') != -1 and update:
        period = dbpath['d'] * 3600
        aicoin = utils.AICoin()
        cx = sqlite3.connect('aicoin_' + utils.getstrforperiod(period))
        aicoin.get_data('huobipro', period, cx)
        cx.close()
    print("wave handle interval:", dbpath)
    for i in range(6):
        pipe = monitor_wave(dbpath['p'], dbpath['f'], dbpath['vnum'], dbpath['thres'])
        evaluate_wave(dbpath['p'], pipe, dbpath['f'], dbpath['vnum'], dbpath['thres'])

dbpaths = [
    #{'d':12, 'p': 'aicoin_12hour', 's': 4, 'f':'huobipro'},
    #{'d':6, 'p': 'aicoin_6hour', 's': 4, 'f':'huobipro'},
    #{'d':4, 'p': 'aicoin_4hour', 's': 4, 'f':'huobipro'},
    {'d':24, 'p': 'tushare_24hour', 'vnum': 6, 'thres': 6, 'f':None},
    {'d':168, 'p': 'tushare_168hour', 'vnum': 6, 'thres': 6, 'f':None},
    {'d':720, 'p': 'tushare_720hour', 'vnum': 6, 'thres': 6, 'f':None},
]
for dbpath in dbpaths:
    # update
    print("minN handle interval:", dbpath)
    for i in range(6):
        pipe = monitor_minN(dbpath['p'], dbpath['f'], dbpath['vnum'], dbpath['thres'])
        evaluate_minN(dbpath['p'], pipe, dbpath['f'], dbpath['vnum'], dbpath['thres'])


