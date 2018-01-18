# -*- coding: utf-8 -*-

#encoding=utf8
from sklearn.pipeline import Pipeline
from sklearn.linear_model import *
from sklearn.tree import *
from sklearn.neighbors import *
from sklearn.ensemble import *
from sklearn.gaussian_process import *
from sklearn.svm import *
from sklearn.naive_bayes import *
from sklearn.preprocessing import *
from sklearn.cross_validation import train_test_split
from sklearn.metrics import *
from sklearn.neural_network import *
from sklearn.model_selection import *
from sklearn.externals import joblib

import pandas as pd
import numpy as np
import sqlite3
import time
import threadpool
import os

'''
判断下一个小时涨跌：avg(o), avg(c), max(max(o),max(c)), min(min(o),min(c)), sum(v)
前1~5个(5分钟)	    均价 最高价 最低价 成交量
前1~5个(30分钟)    均价 最高价 最低价 成交量
前1~5个(3小时)	    均价 最高价 最低价 成交量
共60个因素，一天1440个数据
'''

import random

X_train = None
X_test = None
y_train = None
y_test = None
x_last = None

def findcoef(args):
    ra = args['arg1']
    machine = MLPRegressor(hidden_layer_sizes=ra, max_iter=1000, activation = "relu")

    pipe = Pipeline([['sc', StandardScaler()], ['clf', machine]])
    pipe.fit(X_train, y_train)
    y_pred = pipe.predict(X_test)
    precision = explained_variance_score(y_test, y_pred)
    print('Accuraty:score=%f %s relu' % (precision, ra))


def learn_from_data(machine, X, y, x_last):
    global X_train
    global X_test
    global y_train
    global y_test

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.4)  # 测试集占10%
    pool = threadpool.ThreadPool(2)

    args = [{'arg1':tuple([random.randint(5, 50) for j in range(0, 31)])} for i in range(0, 10000)]
    requests = threadpool.makeRequests(findcoef, args)
    [pool.putRequest(req) for req in requests]
    pool.wait()

    #if classifier_name == 'RandomForestRegressor':
    #    forest = pipes[i].steps[1][1]
    #    for f in range(X_train.shape[1]):
    #        print("%2d) %f" % (f + 1, forest.feature_importances_[f]))
    return None

def GetX(t, cu, tbl):
    cmdx = 'select avg(o), avg(c), max(h), min(l), sum(v) from %s where t >= %d and t < %d'
    x = list()

    x += list(cu.execute(cmdx % (tbl, t - 300, t)).fetchone())  # 前1个5分钟
    x += list(cu.execute(cmdx % (tbl, t - 1800, t)).fetchone())  # 前1个30分钟
    x += list(cu.execute(cmdx % (tbl, t - 3600, t - 1800)).fetchone())  # 前2个30分钟
    x += list(cu.execute(cmdx % (tbl, t - 5400, t - 3600)).fetchone())  # 前3个30分钟
    x += list(cu.execute(cmdx % (tbl, t - 7200, t - 5400)).fetchone())  # 前4个30分钟
    x += list(cu.execute(cmdx % (tbl, t - 9000, t - 7200)).fetchone())  # 前5个30分钟
    x += list(cu.execute(cmdx % (tbl, t - 10800, t)).fetchone())  # 前1个3小时
    x += list(cu.execute(cmdx % (tbl, t - 21600, t - 10800)).fetchone())  # 前2个3小时
    x += list(cu.execute(cmdx % (tbl, t - 32400, t - 21600)).fetchone())  # 前3个3小时
    x += list(cu.execute(cmdx % (tbl, t - 43200, t - 32400)).fetchone())  # 前4个3小时
    x += list(cu.execute(cmdx % (tbl, t - 54000, t - 43200)).fetchone())  # 前5个3小时

    '''
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
    '''
    for i in range(0, len(x)):
        if x[i] is None:  # 用第一个合法数据填补缺失值
            return None
    return x

def LearnFromPrice(args):
    coinname, coinid, site, coref = args['arg1'], args['arg2'], args['arg3'], args['arg4']
    cx = sqlite3.connect('digitalcash.db')
    cu = cx.cursor()

    ###################################预测后三小时######################################
    X = list()
    y_max = list() # 预测未来半天最高点
    y_min = list() # 预测未来半天最低点

    tbl = site.replace('.', '').replace('-', '') + '_' + coinname

    maxt, mint, = cu.execute('select max(t), min(t) from %s' % tbl).fetchone()
    maxt, mint = maxt - 7200, mint + 54000 # 修正
    count, = cu.execute('select count(*) from %s' % tbl).fetchone()
    if count < 3000: # 数据量过少不预测
        return

    curtbl = site.replace('.', '').replace('-', '') + '_' + coinname
    ratio = 100000 if curtbl.find('_BTC') != -1 else 1

    # 反持久化
    machine_file = 'traindata/' + '_' + tbl + '_1hour' + '.mac'
    hidden_layer_sizes = (20,) * 80
    max_iter = 10000
    if os.path.exists(machine_file):
        traindata = joblib.load(machine_file)
        if 'lastt' not in traindata or '12_max' not in traindata or '01_min' not in traindata:
            traindata['lastt'] = mint

            # SGDRegressor 0.93
            # MLPRegressor 0.96
            #  MLPRegressor BernoulliRBM PassiveAggressiveRegressor
            #MLPRegressor
            traindata['12_max'] = MLPRegressor(hidden_layer_sizes=hidden_layer_sizes, max_iter=max_iter) #RandomForestRegressor(n_estimators=200)
            traindata['01_min'] = MLPRegressor(hidden_layer_sizes=hidden_layer_sizes, max_iter=max_iter) #RandomForestRegressor(n_estimators=200)
    else:
        traindata = dict()
        traindata['lastt'] = mint
        traindata['12_max'] = MLPRegressor(hidden_layer_sizes=hidden_layer_sizes, max_iter=max_iter) #RandomForestRegressor(n_estimators=200)
        traindata['01_min'] = MLPRegressor(hidden_layer_sizes=hidden_layer_sizes, max_iter=max_iter) #RandomForestRegressor(n_estimators=200)
    machine_12hour_max = traindata['12_max']
    machine_01hour_min = traindata['01_min']
    mint = traindata['lastt']  # 最后学习时间

    for t in range(mint, maxt, 60): # 1min为单位
        x = GetX(t, cu, tbl)
        if x is None:
            continue
        min_, = cu.execute('select min(l) from %s where t >= %d and t < %d' % (curtbl, t, t + 3600)).fetchone()
        if min_ is None:
            continue
        max_, = cu.execute('select max(h) from %s where t >= %d and t < %d' % (curtbl, t + 3600, t + 7200)).fetchone()
        if max_ is None:
            continue
        X.append(x)
        y_min.append(min_)
        y_max.append(max_)

    x_last = GetX(maxt, cu, tbl)
    if x_last is None: # 数据不全不预测
        return

    cur = cu.execute('select c from %s where t = %d' % (curtbl, maxt)).fetchone()[0]
    print '%s Cur=%f dataset=%d' % (curtbl, cur * ratio, len(X))

    maxd = learn_from_data(machine_12hour_max, np.array(X) * ratio, np.array(y_max) * ratio, np.array([x_last]) * ratio)
    print '\nPredict %s maximum %s~%s:predict=%s' % (coinname, time.ctime(maxt + 3600), time.ctime(maxt + 7200), maxd)

    mind = learn_from_data(machine_01hour_min, np.array(X) * ratio, np.array(y_min) * ratio, np.array([x_last]))
    print '\nPredict %s minimium %s~%s:predict=%s' % (coinname, time.ctime(maxt), time.ctime(maxt + 3600), mind)

    rrratio = (maxd - mind) / mind
    if rrratio > 0.1:
        print '#######################%s %f#####################' % (coinname, rrratio)

    # 持久化
    traindata['lastt'] = maxt
    joblib.dump(traindata, machine_file)

    cu.close()
    cx.close()

from digital_coin_db import HistoryUpdater

def gp(arg):
    HistoryUpdater().UpdateFromAICoin(arg)
    LearnFromPrice(arg)

if __name__ == '__main__':

    pool = threadpool.ThreadPool(1)

    args = [
        {'arg1': 'ACT_BTC', 'arg2': 'huobiproactbtc', 'arg3': 'huobi.pro', 'arg4': []},
        {'arg1': 'AST_BTC', 'arg2': 'huobiproastbtc', 'arg3': 'huobi.pro', 'arg4': []},
        {'arg1': 'BAT_BTC', 'arg2': 'huobiprobatbtc', 'arg3': 'huobi.pro', 'arg4': []},
        {'arg1': 'BCH', 'arg2': 'huobiprobchusdt', 'arg3': 'huobi.pro', 'arg4': []},
        {'arg1': 'BIFI_BTC', 'arg2': 'huobiprobifibtc', 'arg3': 'huobi.pro', 'arg4': []},
        {'arg1': 'BCD_BTC', 'arg2': 'huobiprobcdbtc', 'arg3': 'huobi.pro', 'arg4': []},
        {'arg1': 'BCX_BTC', 'arg2': 'huobiprobcxbtc', 'arg3': 'huobi.pro', 'arg4': []},
        {'arg1': 'BTC', 'arg2': 'huobiprobtcusdt', 'arg3': 'huobi.pro', 'arg4': []},
        {'arg1': 'BTM_BTC', 'arg2': 'huobiprobtmbtc', 'arg3': 'huobi.pro', 'arg4': []},
        {'arg1': 'BTM_BTC', 'arg2': 'huobiprobtmbtc', 'arg3': 'huobi.pro', 'arg4': []},
        {'arg1': 'CMT_BTC', 'arg2': 'huobiprocmtbtc', 'arg3': 'huobi.pro', 'arg4': []},
        {'arg1': 'CVC_BTC', 'arg2': 'huobiprocvcbtc', 'arg3': 'huobi.pro', 'arg4': []},
        {'arg1': 'DASH', 'arg2': 'huobiproetcusdt', 'arg3': 'huobi.pro', 'arg4': []},
        {'arg1': 'DBC_BTC', 'arg2': 'huobiprodbcbtc', 'arg3': 'huobi.pro', 'arg4': []},
        {'arg1': 'DGD_BTC', 'arg2': 'huobiprodgdbtc', 'arg3': 'huobi.pro', 'arg4': []},
        {'arg1': 'ELF_BTC', 'arg2': 'huobiproelfbtc', 'arg3': 'huobi.pro', 'arg4': []},
        {'arg1': 'EOS', 'arg2': 'huobiproeosusdt', 'arg3': 'huobi.pro', 'arg4': []},
        {'arg1': 'ETC', 'arg2': 'huobiprobtcusdt', 'arg3': 'huobi.pro', 'arg4': []},
        {'arg1': 'ETH', 'arg2': 'huobiproethusdt', 'arg3': 'huobi.pro', 'arg4': []},
        {'arg1': 'GAS_BTC', 'arg2': 'huobiprogasbtc', 'arg3': 'huobi.pro', 'arg4': []},
        {'arg1': 'GNT_BTC', 'arg2': 'huobiprogntbtc', 'arg3': 'huobi.pro', 'arg4': []},
        {'arg1': 'GNX_BTC', 'arg2': 'huobiprognxbtc', 'arg3': 'huobi.pro', 'arg4': []},
        {'arg1': 'ICX_BTC', 'arg2': 'huobiproicxbtc', 'arg3': 'huobi.pro', 'arg4': []},
        {'arg1': 'ITC_BTC', 'arg2': 'huobiproitcbtc', 'arg3': 'huobi.pro', 'arg4': []},
        {'arg1': 'KNC_BTC', 'arg2': 'huobiprokncbtc', 'arg3': 'huobi.pro', 'arg4': []},
        {'arg1': 'LTC', 'arg2': 'huobiproltcusdt', 'arg3': 'huobi.pro', 'arg4': []},
        {'arg1': 'MANA_BTC', 'arg2': 'huobipromanabtc', 'arg3': 'huobi.pro', 'arg4': []},
        {'arg1': 'MCO_BTC', 'arg2': 'huobipromcobtc', 'arg3': 'huobi.pro', 'arg4': []},
        {'arg1': 'MDS_BTC', 'arg2': 'huobipromdsbtc', 'arg3': 'huobi.pro', 'arg4': []},
        {'arg1': 'MTL_BTC', 'arg2': 'huobipromtlbtc', 'arg3': 'huobi.pro', 'arg4': []},
        {'arg1': 'NAS_BTC', 'arg2': 'huobipronasbtc', 'arg3': 'huobi.pro', 'arg4': []},
        {'arg1': 'NEO_BTC', 'arg2': 'huobiproneobtc', 'arg3': 'huobi.pro', 'arg4': []},
        {'arg1': 'OMG', 'arg2': 'huobiproomgusdt', 'arg3': 'huobi.pro', 'arg4': []},
        {'arg1': 'PROPY_BTC', 'arg2': 'huobipropropybtc', 'arg3': 'huobi.pro', 'arg4': []},
        {'arg1': 'QASH_BTC', 'arg2': 'huobiproqashbtc', 'arg3': 'huobi.pro', 'arg4': []},
        {'arg1': 'QSP_BTC', 'arg2': 'huobiproqspbtc', 'arg3': 'huobi.pro', 'arg4': []},
        {'arg1': 'RCN_BTC', 'arg2': 'huobiprorcnbtc', 'arg3': 'huobi.pro', 'arg4': []},
        {'arg1': 'RDN_BTC', 'arg2': 'huobiprordnbtc', 'arg3': 'huobi.pro', 'arg4': []},
        {'arg1': 'REQ_BTC', 'arg2': 'huobiproreqbtc', 'arg3': 'huobi.pro', 'arg4': []},
        {'arg1': 'RPX_BTC', 'arg2': 'huobiprorpxbtc', 'arg3': 'huobi.pro', 'arg4': []},
        {'arg1': 'SALT_BTC', 'arg2': 'huobiprosaltbtc', 'arg3': 'huobi.pro', 'arg4': []},
        {'arg1': 'SMT_BTC', 'arg2': 'huobiprosmtbtc', 'arg3': 'huobi.pro', 'arg4': []},
        {'arg1': 'SNT_BTC', 'arg2': 'huobiprosntbtc', 'arg3': 'huobi.pro', 'arg4': []},
        {'arg1': 'STORJ_BTC', 'arg2': 'huobiprostorjbtc', 'arg3': 'huobi.pro', 'arg4': []},
        {'arg1': 'SWFTC_BTC', 'arg2': 'huobiproswftcbtc', 'arg3': 'huobi.pro', 'arg4': []},
        {'arg1': 'TNB_BTC', 'arg2': 'huobiprotnbbtc', 'arg3': 'huobi.pro', 'arg4': []},
        {'arg1': 'TNT_BTC', 'arg2': 'huobiprotntbtc', 'arg3': 'huobi.pro', 'arg4': []},
        {'arg1': 'TOPC_BTC', 'arg2': 'huobiprotopcbtc', 'arg3': 'huobi.pro', 'arg4': []},
        {'arg1': 'VEN_BTC', 'arg2': 'huobiprovenbtc', 'arg3': 'huobi.pro', 'arg4': []},
        {'arg1': 'WAX_BTC', 'arg2': 'huobiprowaxbtc', 'arg3': 'huobi.pro', 'arg4': []},
        {'arg1': 'WICC_BTC', 'arg2': 'huobiprowiccbtc', 'arg3': 'huobi.pro', 'arg4': []},
        {'arg1': 'XRP', 'arg2': 'huobiproxrpusdt', 'arg3': 'huobi.pro', 'arg4': []},
        {'arg1': 'ZEC', 'arg2': 'huobiprozecusdt', 'arg3': 'huobi.pro', 'arg4': []},
        {'arg1': 'ZEC_BTC', 'arg2': 'huobiprozecbtc', 'arg3': 'huobi.pro', 'arg4': []},
        {'arg1': 'ZRX_BTC', 'arg2': 'huobiprozrxbtc', 'arg3': 'huobi.pro', 'arg4': []}
    ]

    while True:
        #requests = threadpool.makeRequests(HistoryUpdater().UpdateFromAICoin, args)
        requests = threadpool.makeRequests(LearnFromPrice, args)
        [pool.putRequest(req) for req in requests]
        pool.wait()




