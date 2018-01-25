# -*- coding: utf-8 -*-

# encoding=utf8
from sklearn.pipeline import Pipeline
from sklearn.linear_model import *
from sklearn.tree import *
from sklearn.neighbors import *
from sklearn.ensemble import *
from sklearn.gaussian_process import *
from sklearn.svm import *
from sklearn.naive_bayes import *
1
from sklearn.cross_validation import train_test_split
from sklearn.metrics import *
from sklearn.neural_network import *
from sklearn.model_selection import *
from sklearn.externals import joblib
from sklearn.preprocessing import *
import pandas as pd
import numpy as np
import sqlite3
import time
import threadpool
import math
import os

'''
判断下一个小时涨跌：avg(o), avg(c), max(max(o),max(c)), min(min(o),min(c)), sum(v)
前1~5个(5分钟)	    均价 最高价 最低价 成交量
前1~5个(30分钟)    均价 最高价 最低价 成交量
前1~5个(3小时)	    均价 最高价 最低价 成交量
共60个因素，一天1440个数据
'''

import random

def learn_from_data_rf(X, y, x_last):
    pipe = Pipeline([['sc', StandardScaler()], ['clf', RandomForestRegressor(n_estimators=66)]])
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.1)  # 测试集占10%
    pipe.fit(X_train, y_train)
    y_pred = pipe.predict(X_test)
    precision = explained_variance_score(y_test, y_pred)
    print('Accuraty:score=%f' % (precision))
    y_last = pipe.predict(x_last)[0]
    return y_last[0], y_last[1], y_last[2], y_last[3], pipe

def learn_from_data_mlp(X, y, x_last):
    regressor = MLPRegressor(hidden_layer_sizes=(52, 20), max_iter=1000, activation = "tanh", solver="lbfgs")
    pipe = Pipeline([['sc', StandardScaler()], ['clf', regressor]])
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.1)  # 测试集占10%
    pipe.fit(X_train, y_train)
    y_pred = pipe.predict(X_test)
    precision = explained_variance_score(y_test, y_pred)
    print('Accuraty:score=%f' % (precision))
    y_last = pipe.predict(x_last)[0]
    return y_last[0], y_last[1], y_last[2], y_last[3], pipe

def GetX(t, cu, tbl, interval):
    cmdx = 'select avg(o), avg(c), max(h), min(l) from %s where t >= %d and t < %d'
    x = list()
    # 24个因子
#    x += list(cu.execute(cmdx % (tbl, t - 300, t)).fetchone())  # 前1个5分钟
#    x += list(cu.execute(cmdx % (tbl, t - 10800, t - 300)).fetchone())  # 前1个3小时
#    x += list(cu.execute(cmdx % (tbl, t - 21600, t - 10800)).fetchone())  # 前2个3小时
#    x += list(cu.execute(cmdx % (tbl, t - 32400, t - 21600)).fetchone())  # 前3个3小时
#    x += list(cu.execute(cmdx % (tbl, t - 43200, t - 32400)).fetchone())  # 前4个3小时
#    x += list(cu.execute(cmdx % (tbl, t - 54000, t - 43200)).fetchone())  # 前5个3小时

    x += list(cu.execute(cmdx % (tbl, t - 300, t)).fetchone())  # 前1个5分钟
    x += list(cu.execute(cmdx % (tbl, t - interval / 5, t - 300)).fetchone())  # 前1个3小时
    x += list(cu.execute(cmdx % (tbl, t - interval * 2 / 5, t - interval / 5)).fetchone())  # 前2个3小时
    x += list(cu.execute(cmdx % (tbl, t - interval * 3 / 5, t - interval * 2 / 5)).fetchone())  # 前3个3小时
    x += list(cu.execute(cmdx % (tbl, t - interval * 4 / 5, t - interval * 3 / 5)).fetchone())  # 前4个3小时
    x += list(cu.execute(cmdx % (tbl, t - interval, t - interval * 4 / 5)).fetchone())  # 前5个3小时

    for i in range(0, len(x)):
        if x[i] is None:  # 用第一个合法数据填补缺失值
            return None
    return x

def normalizing(data):
    if len(data.shape) == 1:
        max_ = data.max() * 1.01
        min_ = data.min() * 0.09
        return (data - min_) / (max_ - min_)
    elif len(data.shape) == 2:
        width = data.shape[1]
        for i in range(0, width):
            slip = data[:,i]
            max_ = slip.max() * 1.01
            min_ = slip.min() * 0.09
            data[:,i] = (slip - min_) / (max_ - min_)
        return data
    return None

pcx = sqlite3.connect('digitalcash_predict.db')
pcu = pcx.cursor()

def create_predict_table(cu, tbl):
    # 不存在则创建表
    try:
        # 时间 开盘价 最高价 最低价 收盘价 成交量
        sql = 'create table %s (t int primary key, minp float, maxp float, mint int, maxt int)' % tbl
        cu.execute(sql)
    except Exception as e:
        pass  # Already exist

def LearnFromPrice(args):
    coinname, coinid, site, coref = args['arg1'], args['arg2'], args['arg3'], args['arg4']
    cx = sqlite3.connect('digitalcash.db')
    cu = cx.cursor()

    '''
    ###################################预测后一小时######################################
    X = list()
    y = list()  # 预测未来半天最高点/最低点/及最低点与最高点时间差

    tbl = site.replace('.', '').replace('-', '') + '_' + coinname

    maxt, mint, = cu.execute('select max(t), min(t) from %s' % tbl).fetchone()
    maxt_, mint_ = maxt - 3600, mint + 3600  # 修正
    count, = cu.execute('select count(*) from %s' % tbl).fetchone()
    if count < 30000:  # 数据量过少不预测
        return

    curtbl = site.replace('.', '').replace('-', '') + '_' + coinname
    ratio = -1.0
    for t in range(mint_, maxt_, 60):  # 1min为单位
        x = GetX(t, cu, tbl, 3600)
        if x is None:
            continue
        # 搜索区间内高点
        tmin, min_ = cu.execute('select t, min(l) from %s where t >= %d and t < %d' % (curtbl, t, t + 3600)).fetchone()
        # 搜索最低点之后的相对最高点
        if min_ is None:
            continue
        tmax, max_ = cu.execute('select t, max(h) from %s where t >= %d and t < %d' % (curtbl, tmin, t + 3600)).fetchone()
        if max_ is None:
            continue
        X.append(x)
        if ratio < 0.0:
            ratio = math.pow(10, int(math.log(x[0], 10)))
        y.append([min_ / ratio, max_ / ratio, (tmin - t) / 1000.0, (tmax - tmin) / 1000.0]) # 尽量归一化
        # 预测最小值，相对最大值，最小值时间，相对最大值时间
    x_last = GetX(maxt, cu, tbl, 3600)
    if x_last is None:  # 数据不全不预测
        return

    cur = cu.execute('select c from %s where t = %d' % (curtbl, maxt)).fetchone()[0]
    print '\n%s Cur=%f dataset=%d' % (curtbl, cur, len(X))

    pmin, pmax, pmint, pdifft, pipe = learn_from_data_rf(np.array(X) / ratio, np.array(y), np.array([x_last]) / ratio)
    print 'Predict %s %s~%s:predict=min=%f max=%f growth=%f mintime=%fhour reltime=%fhour' % (coinname, time.ctime(maxt),
                      time.ctime(maxt + 3600), pmin, pmax, (pmax - pmin) / pmin, pmint * 1000 / 3600, pdifft * 1000 / 3600)


    ###################################预测后三小时######################################
    X = list()
    y = list()  # 预测未来半天最高点/最低点/及最低点与最高点时间差

    tbl = site.replace('.', '').replace('-', '') + '_' + coinname

    maxt, mint, = cu.execute('select max(t), min(t) from %s' % tbl).fetchone()
    maxt_, mint_ = maxt - 10800, mint + 10800  # 修正
    count, = cu.execute('select count(*) from %s' % tbl).fetchone()
    if count < 30000:  # 数据量过少不预测
        return

    curtbl = site.replace('.', '').replace('-', '') + '_' + coinname
    ratio = -1.0
    for t in range(mint_, maxt_, 60):  # 1min为单位
        x = GetX(t, cu, tbl, 10800)
        if x is None:
            continue
        # 搜索区间内高点
        tmin, min_ = cu.execute('select t, min(l) from %s where t >= %d and t < %d' % (curtbl, t, t + 10800)).fetchone()
        # 搜索最低点之后的相对最高点
        if min_ is None:
            continue
        tmax, max_ = cu.execute('select t, max(h) from %s where t >= %d and t < %d' % (curtbl, tmin, t + 10800)).fetchone()
        if max_ is None:
            continue
        X.append(x)
        if ratio < 0.0:
            ratio = math.pow(10, int(math.log(x[0], 10)))
        y.append([min_ / ratio, max_ / ratio, (tmin - t) / 1000.0, (tmax - tmin) / 1000.0]) # 尽量归一化
        # 预测最小值，相对最大值，最小值时间，相对最大值时间
    x_last = GetX(maxt, cu, tbl, 3600)
    if x_last is None:  # 数据不全不预测
        return

    cur = cu.execute('select c from %s where t = %d' % (curtbl, maxt)).fetchone()[0]
    print '\n%s Cur=%f dataset=%d' % (curtbl, cur, len(X))

    pmin, pmax, pmint, pdifft, pipe = learn_from_data_rf(np.array(X) / ratio, np.array(y), np.array([x_last]) / ratio)
    print 'Predict %s %s~%s:predict=min=%f max=%f growth=%f mintime=%fhour reltime=%fhour' % (coinname, time.ctime(maxt),
                      time.ctime(maxt + 3600), pmin, pmax, (pmax - pmin) / pmin, pmint * 1000 / 3600, pdifft * 1000 / 3600)
    '''

    ###################################预测后十五小时######################################
    X = list()
    y = list()  # 预测未来半天最高点/最低点/及最低点与最高点时间差

    tbl = site.replace('.', '').replace('-', '') + '_' + coinname

    maxt, mint, = cu.execute('select max(t), min(t) from %s' % tbl).fetchone()
    maxt_, mint_ = maxt - 54000, mint + 54000  # 修正
    count, = cu.execute('select count(*) from %s' % tbl).fetchone()
    if count < 30000:  # 数据量过少不预测
        return

    curtbl = site.replace('.', '').replace('-', '') + '_' + coinname
    ratio = -1.0
    for t in range(mint_, maxt_, 60):  # 1min为单位
        x = GetX(t, cu, tbl, 54000)
        if x is None:
            continue
        # 搜索区间内高点
        tmin, min_ = cu.execute('select t, min(l) from %s where t >= %d and t < %d' % (curtbl, t, t + 54000)).fetchone()
        # 搜索最低点之后的相对最高点
        if min_ is None:
            continue
        tmax, max_ = cu.execute('select t, max(h) from %s where t >= %d and t < %d' % (curtbl, tmin, t + 54000)).fetchone()
        if max_ is None:
            continue
        X.append(x)
        if ratio < 0.0:
            ratio = math.pow(10, int(math.log(x[0], 10)))
        y.append([min_ / ratio, max_ / ratio, (tmin - t) / 10000.0, (tmax - tmin) / 10000.0]) # 尽量归一化
        # 预测最小值，相对最大值，最小值时间，相对最大值时间
    x_last = GetX(maxt, cu, tbl, 54000)
    if x_last is None:  # 数据不全不预测
        return

    cur = cu.execute('select c from %s where t = %d' % (curtbl, maxt)).fetchone()[0]
    print '\n%s Cur=%f dataset=%d' % (curtbl, cur, len(X))

    pmin, pmax, pmint, pdifft, pipe = learn_from_data_rf(np.array(X) / ratio, np.array(y), np.array([x_last]) / ratio)
    print 'Predict %s %s~%s:predict=min=%f max=%f growth=%f mintime=%fhour reltime=%fhour' % (coinname, time.ctime(maxt),
                      time.ctime(maxt + 54000), pmin, pmax, (pmax - pmin) / pmin, pmint * 10000 / 3600, pdifft * 10000 / 3600)

    #pmin, pmax, pmint, pdifft, pipe = learn_from_data_mlp(np.array(X) * ratio, np.array(y), np.array([x_last]) * ratio)
    #print 'Predict %s %s~%s:predict=min=%f max=%f growth=%f mintime=%fhour reltime=%fhour' % (coinname, time.ctime(maxt),
    #                  time.ctime(maxt + 54000), pmin, pmax, (pmax - pmin) / pmin, pmint * 10000 / 3600, pdifft * 10000 / 3600)

    '''
    joblib.dump(pipe, 'traindata/' + tbl + '.mac')

    # 更新历史预测结果
    try:
        create_predict_table(pcu, tbl)
        pcx.execute('insert or ignore into %s values (?,?,?,?,?)' % tbl,
               (maxt, pmin / ratio, pmax / ratio, (pmax - pmin) / pmin, pmint * 10000 / 3600, pdifft * 10000 / 3600))
        pcx.commit()
    except Exception as e:
        pass
    '''

    cu.close()
    cx.close()


from digital_coin_db import HistoryUpdater


def gp(arg):
    HistoryUpdater().UpdateFromAICoin(arg)
    LearnFromPrice(arg)


if __name__ == '__main__':

    args = [
        {'arg1': 'ACT_BTC', 'arg2': 'huobiproactbtc', 'arg3': 'huobi.pro', 'arg4': []},
        {'arg1': 'AIDOC_BTC', 'arg2': 'huobiproaidocbtc', 'arg3': 'huobi.pro', 'arg4': []},
        {'arg1': 'APPC_BTC', 'arg2': 'huobiproappcbtc', 'arg3': 'huobi.pro', 'arg4': []},
        {'arg1': 'AST_BTC', 'arg2': 'huobiproastbtc', 'arg3': 'huobi.pro', 'arg4': []},
        {'arg1': 'BAT_BTC', 'arg2': 'huobiprobatbtc', 'arg3': 'huobi.pro', 'arg4': []},
        {'arg1': 'BCH', 'arg2': 'huobiprobchusdt', 'arg3': 'huobi.pro', 'arg4': []},
        {'arg1': 'BIFI_BTC', 'arg2': 'huobiprobifibtc', 'arg3': 'huobi.pro', 'arg4': []},
        {'arg1': 'BCD_BTC', 'arg2': 'huobiprobcdbtc', 'arg3': 'huobi.pro', 'arg4': []},
        {'arg1': 'BCX_BTC', 'arg2': 'huobiprobcxbtc', 'arg3': 'huobi.pro', 'arg4': []},
        {'arg1': 'BTC', 'arg2': 'huobiprobtcusdt', 'arg3': 'huobi.pro', 'arg4': []},
        {'arg1': 'BTM_BTC', 'arg2': 'huobiprobtmbtc', 'arg3': 'huobi.pro', 'arg4': []},
        {'arg1': 'CHAT_BTC', 'arg2': 'huobiprochatbtc', 'arg3': 'huobi.pro', 'arg4': []},
        {'arg1': 'CMT_BTC', 'arg2': 'huobiprocmtbtc', 'arg3': 'huobi.pro', 'arg4': []},
        {'arg1': 'CVC', 'arg2': 'huobiprocvcusdt', 'arg3': 'huobi.pro', 'arg4': []},
        {'arg1': 'CVC_BTC', 'arg2': 'huobiprocvcbtc', 'arg3': 'huobi.pro', 'arg4': []},
        {'arg1': 'DASH', 'arg2': 'huobiprodashusdt', 'arg3': 'huobi.pro', 'arg4': []},
        {'arg1': 'DAT_BTC', 'arg2': 'huobiprodatbtc', 'arg3': 'huobi.pro', 'arg4': []},
        {'arg1': 'DBC_BTC', 'arg2': 'huobiprodbcbtc', 'arg3': 'huobi.pro', 'arg4': []},
        {'arg1': 'DGD_BTC', 'arg2': 'huobiprodgdbtc', 'arg3': 'huobi.pro', 'arg4': []},
        {'arg1': 'ELF_BTC', 'arg2': 'huobiproelfbtc', 'arg3': 'huobi.pro', 'arg4': []},
        {'arg1': 'EOS', 'arg2': 'huobiproeosusdt', 'arg3': 'huobi.pro', 'arg4': []},
        {'arg1': 'ETC', 'arg2': 'huobiproetcusdt', 'arg3': 'huobi.pro', 'arg4': []},
        {'arg1': 'ETH', 'arg2': 'huobiproethusdt', 'arg3': 'huobi.pro', 'arg4': []},
        {'arg1': 'GAS_BTC', 'arg2': 'huobiprogasbtc', 'arg3': 'huobi.pro', 'arg4': []},
        {'arg1': 'GNT', 'arg2': 'huobiprogntusdt', 'arg3': 'huobi.pro', 'arg4': []},
        {'arg1': 'GNT_BTC', 'arg2': 'huobiprogntbtc', 'arg3': 'huobi.pro', 'arg4': []},
        {'arg1': 'GNX_BTC', 'arg2': 'huobiprognxbtc', 'arg3': 'huobi.pro', 'arg4': []},
        {'arg1': 'HSR', 'arg2': 'huobiprohsrusdt', 'arg3': 'huobi.pro', 'arg4': []},
        {'arg1': 'ICX_BTC', 'arg2': 'huobiproicxbtc', 'arg3': 'huobi.pro', 'arg4': []},
        {'arg1': 'IOST_BTC', 'arg2': 'huobiproiostbtc', 'arg3': 'huobi.pro', 'arg4': []},
        {'arg1': 'ITC_BTC', 'arg2': 'huobiproitcbtc', 'arg3': 'huobi.pro', 'arg4': []},
        {'arg1': 'KNC_BTC', 'arg2': 'huobiprokncbtc', 'arg3': 'huobi.pro', 'arg4': []},
        {'arg1': 'LET_BTC', 'arg2': 'huobiproletbtc', 'arg3': 'huobi.pro', 'arg4': []},
        {'arg1': 'LINK_BTC', 'arg2': 'huobiprolinkbtc', 'arg3': 'huobi.pro', 'arg4': []},
        {'arg1': 'LTC', 'arg2': 'huobiproltcusdt', 'arg3': 'huobi.pro', 'arg4': []},
        {'arg1': 'MANA_BTC', 'arg2': 'huobipromanabtc', 'arg3': 'huobi.pro', 'arg4': []},
        {'arg1': 'MCO_BTC', 'arg2': 'huobipromcobtc', 'arg3': 'huobi.pro', 'arg4': []},
        {'arg1': 'MDS_BTC', 'arg2': 'huobipromdsbtc', 'arg3': 'huobi.pro', 'arg4': []},
        {'arg1': 'MTL_BTC', 'arg2': 'huobipromtlbtc', 'arg3': 'huobi.pro', 'arg4': []},
        {'arg1': 'NAS_BTC', 'arg2': 'huobipronasbtc', 'arg3': 'huobi.pro', 'arg4': []},
        {'arg1': 'NEO', 'arg2': 'huobiproneousdt', 'arg3': 'huobi.pro', 'arg4': []},
        {'arg1': 'NEO_BTC', 'arg2': 'huobiproneobtc', 'arg3': 'huobi.pro', 'arg4': []},
        {'arg1': 'OMG', 'arg2': 'huobiproomgusdt', 'arg3': 'huobi.pro', 'arg4': []},
        {'arg1': 'OST_BTC', 'arg2': 'huobiproostbtc', 'arg3': 'huobi.pro', 'arg4': []},
        {'arg1': 'PROPY_BTC', 'arg2': 'huobipropropybtc', 'arg3': 'huobi.pro', 'arg4': []},
        {'arg1': 'POWER_BTC', 'arg2': 'huobipropowrbtc', 'arg3': 'huobi.pro', 'arg4': []},
        {'arg1': 'QASH_BTC', 'arg2': 'huobiproqashbtc', 'arg3': 'huobi.pro', 'arg4': []},
        {'arg1': 'QSP_BTC', 'arg2': 'huobiproqspbtc', 'arg3': 'huobi.pro', 'arg4': []},
        {'arg1': 'QTUM', 'arg2': 'huobiproqtumusdt', 'arg3': 'huobi.pro', 'arg4': []},
        {'arg1': 'QUN_BTC', 'arg2': 'huobiproqunbtc', 'arg3': 'huobi.pro', 'arg4': []},
        {'arg1': 'RCN_BTC', 'arg2': 'huobiprorcnbtc', 'arg3': 'huobi.pro', 'arg4': []},
        {'arg1': 'RDN_BTC', 'arg2': 'huobiprordnbtc', 'arg3': 'huobi.pro', 'arg4': []},
        {'arg1': 'REQ_BTC', 'arg2': 'huobiproreqbtc', 'arg3': 'huobi.pro', 'arg4': []},
        {'arg1': 'RPX_BTC', 'arg2': 'huobiprorpxbtc', 'arg3': 'huobi.pro', 'arg4': []},
        {'arg1': 'SALT_BTC', 'arg2': 'huobiprosaltbtc', 'arg3': 'huobi.pro', 'arg4': []},
        {'arg1': 'SMT_BTC', 'arg2': 'huobiprosmtbtc', 'arg3': 'huobi.pro', 'arg4': []},
        {'arg1': 'SNT', 'arg2': 'huobiprosntusdt', 'arg3': 'huobi.pro', 'arg4': []},
        {'arg1': 'SNT_BTC', 'arg2': 'huobiprosntbtc', 'arg3': 'huobi.pro', 'arg4': []},
        {'arg1': 'STORJ', 'arg2': 'huobiprostorjusdt', 'arg3': 'huobi.pro', 'arg4': []},
        {'arg1': 'STORJ_BTC', 'arg2': 'huobiprostorjbtc', 'arg3': 'huobi.pro', 'arg4': []},
        {'arg1': 'SWFTC_BTC', 'arg2': 'huobiproswftcbtc', 'arg3': 'huobi.pro', 'arg4': []},
        {'arg1': 'THETA_BTC', 'arg2': 'huobiprothetabtc', 'arg3': 'huobi.pro', 'arg4': []},
        {'arg1': 'TNB_BTC', 'arg2': 'huobiprotnbbtc', 'arg3': 'huobi.pro', 'arg4': []},
        {'arg1': 'TNT_BTC', 'arg2': 'huobiprotntbtc', 'arg3': 'huobi.pro', 'arg4': []},
        {'arg1': 'TOPC_BTC', 'arg2': 'huobiprotopcbtc', 'arg3': 'huobi.pro', 'arg4': []},
        {'arg1': 'VEN_BTC', 'arg2': 'huobiprovenbtc', 'arg3': 'huobi.pro', 'arg4': []},
        {'arg1': 'WAX_BTC', 'arg2': 'huobiprowaxbtc', 'arg3': 'huobi.pro', 'arg4': []},
        {'arg1': 'WICC_BTC', 'arg2': 'huobiprowiccbtc', 'arg3': 'huobi.pro', 'arg4': []},
        {'arg1': 'XEM_BTC', 'arg2': 'huobiproxembtc', 'arg3': 'huobi.pro', 'arg4': []},
        {'arg1': 'XRP', 'arg2': 'huobiproxrpusdt', 'arg3': 'huobi.pro', 'arg4': []},
        {'arg1': 'YEE_BTC', 'arg2': 'huobiproyeebtc', 'arg3': 'huobi.pro', 'arg4': []},
        {'arg1': 'ZEC', 'arg2': 'huobiprozecusdt', 'arg3': 'huobi.pro', 'arg4': []},
        {'arg1': 'ZEC_BTC', 'arg2': 'huobiprozecbtc', 'arg3': 'huobi.pro', 'arg4': []},
        {'arg1': 'ZRX_BTC', 'arg2': 'huobiprozrxbtc', 'arg3': 'huobi.pro', 'arg4': []}
    ]

    while True:
        pool = threadpool.ThreadPool(10)
        requests = threadpool.makeRequests(HistoryUpdater().UpdateFromAICoin, args)
        [pool.putRequest(req) for req in requests]
        pool.wait()

        pool = threadpool.ThreadPool(1)
        requests = threadpool.makeRequests(LearnFromPrice, args)
        [pool.putRequest(req) for req in requests]
        pool.wait()

