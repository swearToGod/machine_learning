# -*- coding: utf-8 -*-
'''
    Time        : 2017/12/26 0026 13:23
    Company     : B Inc.
    Author      : lichao
    File        : test
    Description : 
    
'''

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

import pandas as pd
import numpy as np
import sqlite3
import time
import threadpool
from copy import copy

'''
判断下一个小时涨跌：avg(c), max(h), min(l), sum(v)
前1~5个(5分钟)	    均价 最高价 最低价 成交量
前1~5个(30分钟)    均价 最高价 最低价 成交量
前1~5个(3小时)	    均价 最高价 最低价 成交量
共60个因素，一天1440个数据
'''


clfs = [ # 分类器
    SGDClassifier(),
    KNeighborsClassifier(n_neighbors=20),
    DecisionTreeClassifier(),
    AdaBoostClassifier(),
    BaggingClassifier(),
    GradientBoostingClassifier(),
    RandomForestClassifier(),
]

def learn_from_data(X, y, type, mscores=None):
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.1) # 测试集占10%
    if type == 'classifier':
        pipes = [Pipeline([
            ['sc', StandardScaler()],
            ['clf', clf]
        ]) for clf in copy(clfs)]  # 用于统一化初值处理、分类
        for i in range(0, len(clfs)):
            start = time.time()
            pipes[i].fit(X_train, y_train)
            y_pred = pipes[i].predict(X_test)
            minscore = accuracy_score(y_test, y_pred)
            if mscores is not None:
                mscores.append(minscore)
            end = time.time()
            #print('Accuraty:%s score=%f time=%d predict=%f' % (clfs[i].__str__().split('(')[0], minscore, end - start, pipes[i].predict(xlast)))
        return pipes

    elif type == 'regressor':
        ress = [  # 回归器
            AdaBoostRegressor(),
            BaggingRegressor(),
            DecisionTreeRegressor(),
            ExtraTreeRegressor(),
            GaussianProcessRegressor(),
            GradientBoostingRegressor(),
            KNeighborsRegressor(n_neighbors=20),
            PassiveAggressiveRegressor(),
            RandomForestRegressor(),
            SGDRegressor(),
            SVR(),
        ]

        pipes = [Pipeline([
            ['sc', StandardScaler()],
            ['clf', clf]
        ]) for clf in ress]  # 用于统一化初值处理、分类
        for i in range(0, len(ress)):
            start = time.time()
            pipes[i].fit(X_train, y_train)
            y_pred = pipes[i].predict(X_test)
            minscore = explained_variance_score(y_test, y_pred)
            if mscores is not None:
                mscores.append(minscore)
            ei = mean_squared_error(y_test, y_pred)
            end = time.time()
            #print('Accuraty:%s score=%f time=%d err=%f predict=%f' % (ress[i].__str__().split('(')[0], minscore, end - start, ei, pipes[i].predict(xlast)))
        return pipes
    return list()

def GetX(t, cu, tbl):
    cmdx = 'select avg(c), max(h), min(l), sum(v) from %s where t >= %d and t < %d'
    x = list()
    x += list(cu.execute(cmdx % (tbl, t - 300, t)).fetchone())  # 前1个5分钟
    x += list(cu.execute(cmdx % (tbl, t - 600, t - 300)).fetchone())  # 前2个5分钟
    x += list(cu.execute(cmdx % (tbl, t - 900, t - 600)).fetchone())  # 前3个5分钟
    x += list(cu.execute(cmdx % (tbl, t - 1200, t - 900)).fetchone())  # 前4个5分钟
    x += list(cu.execute(cmdx % (tbl, t - 1500, t - 1200)).fetchone())  # 前5个5分钟
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
    for i in range(0, len(x)):
        if x[i] is None:  # 用第一个合法数据填补缺失值
            for j in range(0, len(x)):
                if x[j] is not None:
                    x[i], x[i + 1], x[i + 2], x[i + 3] = x[j], x[j], x[j], x[j]
                    break
    return x

def learn_from_coef(pipes, X, y): # 系数调整
    XX = list()
    for i in range(0, len(X)):
        xx = list()
        for pipe in pipes:
            xx.append(pipe.predict(np.array([X[i]]))[0])
        XX.append(xx)
    minscores = list()
    pipescoef = learn_from_data(np.array(XX), np.array(y), 'regressor', minscores)
    minindx = 0
    for i in range(1, len(pipescoef)):
        if minscores[i] > minscores[minindx]:
            minindx = i
    print 'accuracy %s %f' % (pipescoef[minindx].steps[1][1].__str__().split('(')[0], minscores[minindx])
    return pipescoef[minindx]

def get_data(pipes_data, pipe_coef, x):
    xx = list()
    for pipe in pipes_data:
        xx.append(pipe.predict(x)[0])
    return pipe_coef.predict(np.array([xx]))[0]


def LearnFromPrice(args):
    coinname, coinid, site, coref = args['arg1'], args['arg2'], args['arg3'], args['arg4']

    cx = sqlite3.connect('digitalcash.db')
    cu = cx.cursor()

    ###################################预测后一小时######################################
    X = list()
    y_2 = list() # 预测未来一小时平均价格
    y_3 = list() # 预测未来一小时最高点
    y_4 = list() # 预测未来一小时最低点

    z_ = list()
    for x_ in coref:
        tbl = site.replace('.', '').replace('-', '') + '_' + x_
        z_.append(cu.execute('select max(t), min(t) from %s' % (tbl)).fetchone())
    maxt, mint = z_[0][0], z_[0][1]
    for y_ in z_:
        if y_[0] < maxt:
            maxt = y_[0]
        if y_[1] > mint:
            mint = y_[1]

    curtbl = site.replace('.', '').replace('-', '') + '_' + coinname
    for t in range(maxt - 3600, mint + 54000, -60):
        cmdy = 'select avg(c), max(h), min(l) from %s where t >= %d and t < %d'
        avg_, max_, min_ = cu.execute(cmdy % (curtbl, t, t + 3600)).fetchone()
        if avg_ is None:
            continue
        y_2.append(avg_)
        y_3.append(max_)
        y_4.append(min_)

        x = list()
        for x_ in coref:
            tbl = site.replace('.', '').replace('-', '') + '_' + x_
            x += GetX(t, cu, tbl)
        X.append(x)

    x_last = list()
    for x_ in coref:
        tbl = site.replace('.', '').replace('-', '') + '_' + x_
        x_last += GetX(maxt, cu, tbl)

    cur = cu.execute('select c from %s where t = %d' % (curtbl, maxt)).fetchone()[0]

    #print '\nPredict %s average %s~%s cur=%f:' % (coinname, time.ctime(maxt), time.ctime(maxt + 3600), cur)
    # learn_from_data(np.array(X), np.array(y_2), 'regressor', np.array([x_last]))

    pipes_data = learn_from_data(np.array(X), np.array(y_3), 'regressor')
    pipe_coef = learn_from_coef(pipes_data, np.array(X), np.array(y_3))
    out_data = get_data(pipes_data, pipe_coef, np.array([x_last]))
    print '\nPredict %s maximum %s~%s:cur=%f predict=%f' % (coinname, time.ctime(maxt), time.ctime(maxt + 3600), cur, out_data)

    pipes_data = learn_from_data(np.array(X), np.array(y_4), 'regressor')
    pipe_coef = learn_from_coef(pipes_data, np.array(X), np.array(y_4))
    out_data = get_data(pipes_data, pipe_coef, np.array([x_last]))
    print '\nPredict %s minimium %s~%s:cur=%f predict=%f' % (coinname, time.ctime(maxt), time.ctime(maxt + 3600), cur, out_data)


    #####################################预测后二小时#######################################
    X = list()
    y_2 = list()  # 预测未来一小时平均价格
    y_3 = list()  # 预测未来一小时最高点
    y_4 = list()  # 预测未来一小时最低点

    z_ = list()
    for x_ in coref:
        tbl = site.replace('.', '').replace('-', '') + '_' + x_
        z_.append(cu.execute('select max(t), min(t) from %s' % (tbl)).fetchone())
    maxt, mint = z_[0][0], z_[0][1]
    for y_ in z_:
        if y_[0] < maxt:
            maxt = y_[0]
        if y_[1] > mint:
            mint = y_[1]


    for t in range(maxt - 7200, mint + 54000, -60):
        cmdy = 'select avg(c), max(h), min(l) from %s where t >= %d and t < %d'
        avg_, max_, min_ = cu.execute(cmdy % (curtbl, t, t + 7200)).fetchone()
        if avg_ is None:
            continue
        y_2.append(avg_)
        y_3.append(max_)
        y_4.append(min_)

        x = list()
        for x_ in coref:
            tbl = site.replace('.', '').replace('-', '') + '_' + x_
            x += GetX(t, cu, tbl)
        X.append(x)

    x_last = list()
    for x_ in coref:
        tbl = site.replace('.', '').replace('-', '') + '_' + x_
        x_last += GetX(maxt, cu, tbl)

    cur = cu.execute('select c from %s where t = %d' % (curtbl, maxt)).fetchone()[0]

    #print '\nPredict %s average %s~%s cur=%f:' % (coinname, time.ctime(maxt + 3600), time.ctime(maxt + 7200), cur)
    #learn_from_data(np.array(X), np.array(y_2), 'regressor', np.array([x_last]))

    pipes_data = learn_from_data(np.array(X), np.array(y_3), 'regressor')
    pipe_coef = learn_from_coef(pipes_data, np.array(X), np.array(y_3))
    out_data = get_data(pipes_data, pipe_coef, np.array([x_last]))
    print '\nPredict %s maximum %s~%s:cur=%f predict=%f' % (coinname, time.ctime(maxt + 3600), time.ctime(maxt + 7200), cur, out_data)

    pipes_data = learn_from_data(np.array(X), np.array(y_4), 'regressor')
    pipe_coef = learn_from_coef(pipes_data, np.array(X), np.array(y_4))
    out_data = get_data(pipes_data, pipe_coef, np.array([x_last]))
    print '\nPredict %s minimium %s~%s:cur=%f predict=%f' % (coinname, time.ctime(maxt + 3600), time.ctime(maxt + 7200), cur, out_data)


    #####################################预测后三小时#######################################
    X = list()
    y_2 = list()  # 预测未来一小时平均价格
    y_3 = list()  # 预测未来一小时最高点
    y_4 = list()  # 预测未来一小时最低点

    z_ = list()
    for x_ in coref:
        tbl = site.replace('.', '').replace('-', '') + '_' + x_
        z_.append(cu.execute('select max(t), min(t) from %s' % (tbl)).fetchone())
    maxt, mint = z_[0][0], z_[0][1]
    for y_ in z_:
        if y_[0] < maxt:
            maxt = y_[0]
        if y_[1] > mint:
            mint = y_[1]


    for t in range(maxt - 10800, mint + 54000, -60):
        cmdy = 'select avg(c), max(h), min(l) from %s where t >= %d and t < %d'
        avg_, max_, min_ = cu.execute(cmdy % (curtbl, t, t + 10800)).fetchone()
        if avg_ is None:
            continue
        y_2.append(avg_)
        y_3.append(max_)
        y_4.append(min_)

        x = list()
        for x_ in coref:
            tbl = site.replace('.', '').replace('-', '') + '_' + x_
            x += GetX(t, cu, tbl)
        X.append(x)

    x_last = list()
    for x_ in coref:
        tbl = site.replace('.', '').replace('-', '') + '_' + x_
        x_last += GetX(maxt, cu, tbl)

    cur = cu.execute('select c from %s where t = %d' % (curtbl, maxt)).fetchone()[0]

    #print '\nPredict %s average %s~%s cur=%f:' % (coinname, time.ctime(maxt + 3600), time.ctime(maxt + 7200), cur)
    #learn_from_data(np.array(X), np.array(y_2), 'regressor', np.array([x_last]))

    pipes_data = learn_from_data(np.array(X), np.array(y_3), 'regressor')
    pipe_coef = learn_from_coef(pipes_data, np.array(X), np.array(y_3))
    out_data = get_data(pipes_data, pipe_coef, np.array([x_last]))
    print '\nPredict %s maximum %s~%s:cur=%f predict=%f' % (coinname, time.ctime(maxt + 7200), time.ctime(maxt + 10800), cur, out_data)

    pipes_data = learn_from_data(np.array(X), np.array(y_4), 'regressor')
    pipe_coef = learn_from_coef(pipes_data, np.array(X), np.array(y_4))
    out_data = get_data(pipes_data, pipe_coef, np.array([x_last]))
    print '\nPredict %s minimium %s~%s:cur=%f predict=%f' % (coinname, time.ctime(maxt + 7200), time.ctime(maxt + 10800), cur, out_data)

    #####################################预测后四小时#######################################
    X = list()
    y_2 = list()  # 预测未来一小时平均价格
    y_3 = list()  # 预测未来一小时最高点
    y_4 = list()  # 预测未来一小时最低点

    z_ = list()
    for x_ in coref:
        tbl = site.replace('.', '').replace('-', '') + '_' + x_
        z_.append(cu.execute('select max(t), min(t) from %s' % (tbl)).fetchone())
    maxt, mint = z_[0][0], z_[0][1]
    for y_ in z_:
        if y_[0] < maxt:
            maxt = y_[0]
        if y_[1] > mint:
            mint = y_[1]


    for t in range(maxt - 14400, mint + 54000, -60):
        cmdy = 'select avg(c), max(h), min(l) from %s where t >= %d and t < %d'
        avg_, max_, min_ = cu.execute(cmdy % (curtbl, t, t + 14400)).fetchone()
        if avg_ is None:
            continue
        y_2.append(avg_)
        y_3.append(max_)
        y_4.append(min_)

        x = list()
        for x_ in coref:
            tbl = site.replace('.', '').replace('-', '') + '_' + x_
            x += GetX(t, cu, tbl)
        X.append(x)

    x_last = list()
    for x_ in coref:
        tbl = site.replace('.', '').replace('-', '') + '_' + x_
        x_last += GetX(maxt, cu, tbl)

    cur = cu.execute('select c from %s where t = %d' % (curtbl, maxt)).fetchone()[0]

    #print '\nPredict %s average %s~%s cur=%f:' % (coinname, time.ctime(maxt + 3600), time.ctime(maxt + 7200), cur)
    #learn_from_data(np.array(X), np.array(y_2), 'regressor', np.array([x_last]))

    pipes_data = learn_from_data(np.array(X), np.array(y_3), 'regressor')
    pipe_coef = learn_from_coef(pipes_data, np.array(X), np.array(y_3))
    out_data = get_data(pipes_data, pipe_coef, np.array([x_last]))
    print '\nPredict %s maximum %s~%s:cur=%f predict=%f' % (coinname, time.ctime(maxt + 10800), time.ctime(maxt + 14400), cur, out_data)

    pipes_data = learn_from_data(np.array(X), np.array(y_4), 'regressor')
    pipe_coef = learn_from_coef(pipes_data, np.array(X), np.array(y_4))
    out_data = get_data(pipes_data, pipe_coef, np.array([x_last]))
    print '\nPredict %s minimium %s~%s:cur=%f predict=%f' % (coinname, time.ctime(maxt + 10800), time.ctime(maxt + 14400), cur, out_data)

    #####################################预测后五小时#######################################
    X = list()
    y_2 = list()  # 预测未来一小时平均价格
    y_3 = list()  # 预测未来一小时最高点
    y_4 = list()  # 预测未来一小时最低点

    z_ = list()
    for x_ in coref:
        tbl = site.replace('.', '').replace('-', '') + '_' + x_
        z_.append(cu.execute('select max(t), min(t) from %s' % (tbl)).fetchone())
    maxt, mint = z_[0][0], z_[0][1]
    for y_ in z_:
        if y_[0] < maxt:
            maxt = y_[0]
        if y_[1] > mint:
            mint = y_[1]


    for t in range(maxt - 18000, mint + 54000, -60):
        cmdy = 'select avg(c), max(h), min(l) from %s where t >= %d and t < %d'
        avg_, max_, min_ = cu.execute(cmdy % (curtbl, t, t + 18000)).fetchone()
        if avg_ is None:
            continue
        y_2.append(avg_)
        y_3.append(max_)
        y_4.append(min_)

        x = list()
        for x_ in coref:
            tbl = site.replace('.', '').replace('-', '') + '_' + x_
            x += GetX(t, cu, tbl)
        X.append(x)

    x_last = list()
    for x_ in coref:
        tbl = site.replace('.', '').replace('-', '') + '_' + x_
        x_last += GetX(maxt, cu, tbl)

    cur = cu.execute('select c from %s where t = %d' % (curtbl, maxt)).fetchone()[0]

    #print '\nPredict %s average %s~%s cur=%f:' % (coinname, time.ctime(maxt + 3600), time.ctime(maxt + 7200), cur)
    #learn_from_data(np.array(X), np.array(y_2), 'regressor', np.array([x_last]))

    pipes_data = learn_from_data(np.array(X), np.array(y_3), 'regressor')
    pipe_coef = learn_from_coef(pipes_data, np.array(X), np.array(y_3))
    out_data = get_data(pipes_data, pipe_coef, np.array([x_last]))
    print '\nPredict %s maximum %s~%s:cur=%f predict=%f' % (coinname, time.ctime(maxt + 14400), time.ctime(maxt + 18000), cur, out_data)

    pipes_data = learn_from_data(np.array(X), np.array(y_4), 'regressor')
    pipe_coef = learn_from_coef(pipes_data, np.array(X), np.array(y_4))
    out_data = get_data(pipes_data, pipe_coef, np.array([x_last]))
    print '\nPredict %s minimium %s~%s:cur=%f predict=%f' % (coinname, time.ctime(maxt + 14400), time.ctime(maxt + 18000), cur, out_data)

    #####################################预测后六小时#######################################
    X = list()
    y_2 = list()  # 预测未来一小时平均价格
    y_3 = list()  # 预测未来一小时最高点
    y_4 = list()  # 预测未来一小时最低点

    z_ = list()
    for x_ in coref:
        tbl = site.replace('.', '').replace('-', '') + '_' + x_
        z_.append(cu.execute('select max(t), min(t) from %s' % (tbl)).fetchone())
    maxt, mint = z_[0][0], z_[0][1]
    for y_ in z_:
        if y_[0] < maxt:
            maxt = y_[0]
        if y_[1] > mint:
            mint = y_[1]


    for t in range(maxt - 21600, mint + 54000, -60):
        cmdy = 'select avg(c), max(h), min(l) from %s where t >= %d and t < %d'
        avg_, max_, min_ = cu.execute(cmdy % (curtbl, t, t + 21600)).fetchone()
        if avg_ is None:
            continue
        y_2.append(avg_)
        y_3.append(max_)
        y_4.append(min_)

        x = list()
        for x_ in coref:
            tbl = site.replace('.', '').replace('-', '') + '_' + x_
            x += GetX(t, cu, tbl)
        X.append(x)

    x_last = list()
    for x_ in coref:
        tbl = site.replace('.', '').replace('-', '') + '_' + x_
        x_last += GetX(maxt, cu, tbl)

    cur = cu.execute('select c from %s where t = %d' % (curtbl, maxt)).fetchone()[0]

    #print '\nPredict %s average %s~%s cur=%f:' % (coinname, time.ctime(maxt + 3600), time.ctime(maxt + 7200), cur)
    #learn_from_data(np.array(X), np.array(y_2), 'regressor', np.array([x_last]))

    pipes_data = learn_from_data(np.array(X), np.array(y_3), 'regressor')
    pipe_coef = learn_from_coef(pipes_data, np.array(X), np.array(y_3))
    out_data = get_data(pipes_data, pipe_coef, np.array([x_last]))
    print '\nPredict %s maximum %s~%s:cur=%f predict=%f' % (coinname, time.ctime(maxt + 18000), time.ctime(maxt + 21600), cur, out_data)

    pipes_data = learn_from_data(np.array(X), np.array(y_4), 'regressor')
    pipe_coef = learn_from_coef(pipes_data, np.array(X), np.array(y_4))
    out_data = get_data(pipes_data, pipe_coef, np.array([x_last]))
    print '\nPredict %s minimium %s~%s:cur=%f predict=%f' % (coinname, time.ctime(maxt + 18000), time.ctime(maxt + 21600), cur, out_data)

    cu.close()
    cx.close()

from digital_coin_db import HistoryUpdater

if __name__ == '__main__':
    args = [
        # arg4平衡币种之间影响
        {'arg1': 'BTC', 'arg2': '954', 'arg3': 'huobi.pro', 'arg4': ['BTC']},
        {'arg1': 'ETH', 'arg2': '955', 'arg3': 'huobi.pro', 'arg4': ['ETH']},
        {'arg1': 'LTC', 'arg2': '956', 'arg3': 'huobi.pro', 'arg4': ['LTC']},
        {'arg1': 'BCH', 'arg2': '957', 'arg3': 'huobi.pro', 'arg4': ['BCH']},
        {'arg1': 'DASH', 'arg2': '1256', 'arg3': 'huobi.pro', 'arg4': ['DASH']},
        {'arg1': 'ETC', 'arg2': '1255', 'arg3': 'huobi.pro', 'arg4': ['ETC']},
        {'arg1': 'EOS', 'arg2': '1315', 'arg3': 'huobi.pro', 'arg4': ['EOS']},
        {'arg1': 'OMG', 'arg2': '1316', 'arg3': 'huobi.pro', 'arg4': ['OMG']},
        {'arg1': 'ZEC', 'arg2': '1343', 'arg3': 'huobi.pro', 'arg4': ['ZEC']},
        {'arg1': 'HSR', 'arg2': '1483', 'arg3': 'huobi.pro', 'arg4': ['HSR']},
        # binance bittrex bithumb bitfinex 平衡搬砖影响
    ]
    pool = threadpool.ThreadPool(10)

    while True:
        requests = threadpool.makeRequests(HistoryUpdater().UpdateOnePrice, args)
        [pool.putRequest(req) for req in requests]
        pool.wait()

        for arg in args:
            LearnFromPrice(
                arg
            )
        time.sleep(1200) # 20分钟预测一次

