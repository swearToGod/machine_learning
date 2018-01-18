# -*- coding: utf-8 -*-
import urllib2
import json
import sqlite3
import time
import threadpool

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
import threading

DEBUG = False
begintime = 0
if DEBUG:
    proxy_handler = urllib2.ProxyHandler({'http': '127.0.0.1:8888',
                                          'https': '127.0.0.1:8888'})
    opener = urllib2.build_opener(proxy_handler)
    urllib2.install_opener(opener)

cookies = urllib2.urlopen(urllib2.Request('http://xueqiu.com/S/SH000001', headers={'User-Agent': ''})).headers['set-cookie']
lock = threading.Lock()

def GetXueQiuStock(stockindx):
    print 'update %s' % stockindx
    baseurl = 'http://xueqiu.com/stock/forchartk/stocklist.json?'
    params = 'symbol=%s&period=1day&type=normal&end=%d&count=%d'

    global cookies
    global begintime
    request = urllib2.Request(baseurl + (params  % (stockindx, begintime * 1000, 0)), headers={
        'Cookie': cookies, 'User-Agent': ''})
    try:
        response = urllib2.urlopen(request).read()
    except Exception as e:
        return
    jsondata = json.loads(response)

    vec = jsondata['chartlist']
    if len(vec) < 1000:
        return

    if ord(stockindx[0]) in range(ord('0'), ord('9') + 1):
        stockindx = 'HK' + stockindx # 避免港股无法创建表
    if ord(stockindx[-1]) in range(ord('A'), ord('Z') + 1):
        stockindx = 'AM' + stockindx # 增加美股标志

    cx = sqlite3.connect('stock.db')
    cu = cx.cursor()

    lock.acquire()
    try:
        # time, open, close, high, low, turnrate, volume
        cmd = 'create table %s (time int primary key, ma5 float, ma10 float, ma20 float, ma30 float, high float, low float, volume int)'
        cu.execute(cmd % stockindx)
    except Exception as e:
        pass
    for item in vec:
        cx.execute('insert or ignore into %s values (?,?,?,?,?,?,?,?)' % stockindx,
                   (int(item['timestamp']) / 1000, float(item['ma5']), float(item['ma10']), float(item['ma20']), float(item['ma30']),
                    float(item['high']), float(item['low']), int(item['lot_volume'])))
    cx.commit()
    lock.release()

    cu.close()
    cx.close()


clfs = [ # 分类器
    SGDClassifier(),
    KNeighborsClassifier(n_neighbors=20),
    DecisionTreeClassifier(),
    AdaBoostClassifier(),
    BaggingClassifier(),
    GradientBoostingClassifier(),
    RandomForestClassifier(),
]

ress = [ # 回归器
    SGDRegressor(),
    KNeighborsRegressor(n_neighbors=20),
    DecisionTreeRegressor(),
    AdaBoostRegressor(),
    BaggingRegressor(),
    GradientBoostingRegressor(),
    RandomForestRegressor()
]

def learn_from_data(X, y, type):
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.1) # 测试集占10%

    if type == 'classifier':
        pipes = [Pipeline([
            ['sc', StandardScaler()],
            ['clf', clf]
        ]) for clf in clfs]  # 用于统一化初值处理、分类
        for i in range(0, len(clfs)):
            start = time.time()
            pipes[i].fit(X_train, y_train)
            y_pred = pipes[i].predict(X_test)
            accuracy = accuracy_score(y_test, y_pred)
            end = time.time()
            print('Accuraty:%s score=%f time=%d' % (clfs[i].__str__().split('(')[0], accuracy, end - start))
    elif type == 'regressor':
        pipes = [Pipeline([
            ['sc', StandardScaler()],
            ['clf', clf]
        ]) for clf in ress]  # 用于统一化初值处理、分类
        for i in range(0, len(ress)):
            start = time.time()
            pipes[i].fit(X_train, y_train)
            y_pred = pipes[i].predict(X_test)
            accuracy = r2_score(y_test, y_pred)
            end = time.time()
            if accuracy > 0.999:
                print('Accuraty:%s score=%f time=%d' % (ress[i].__str__().split('(')[0], accuracy, end - start))

def test():
    # Build database
    global begintime
    time_ = time.localtime()
    time__ = time.struct_time([time_.tm_year, time_.tm_mon, time_.tm_mday + 1, 0, 0, 0, 0, 0, 0])
    begintime = int(time.mktime(time__))

    pool = threadpool.ThreadPool(100)
    P = list() # SZ SH
    P += ['SH001%03d' % i for i in range(0, 999)] # 国债现货
    P += ['SH110%03d' % i for i in range(0, 999)] # 企业债券
    P += ['SH120%03d' % i for i in range(0, 999)] # 企业债券
    P += ['SH129%03d' % i for i in range(0, 999)]  # 可转换债券
    P += ['SH100%03d' % i for i in range(0, 999)]  # 可转换债券
    P += ['SH201%03d' % i for i in range(0, 999)]  # 国债回购
    P += ['SH310%03d' % i for i in range(0, 999)]  # 国债期货
    P += ['SH500%03d' % i for i in range(0, 999)]  # 基金
    P += ['SH550%03d' % i for i in range(0, 999)]  # 基金
    P += ['SH600%03d' % i for i in range(0, 999)]  # A股
    P += ['SH601%03d' % i for i in range(0, 999)]  #
    P += ['SH603%03d' % i for i in range(0, 999)]  #
    P += ['SH700%03d' % i for i in range(0, 999)]  # 配股
    P += ['SH710%03d' % i for i in range(0, 999)]  # 转配股
    P += ['SH701%03d' % i for i in range(0, 999)]  # 转配股再配股
    P += ['SH711%03d' % i for i in range(0, 999)]  # 转配股再转配股
    P += ['SH720%03d' % i for i in range(0, 999)]  # 红利
    P += ['SH730%03d' % i for i in range(0, 999)]  # 新股申购
    P += ['SH735%03d' % i for i in range(0, 999)]  # 新基金申购
    P += ['SH737%03d' % i for i in range(0, 999)]  # 新股配售
    P += ['SH900%03d' % i for i in range(0, 999)]  # B股

    P += ['SZ00%04d' % i for i in range(0, 999)]  # A股证券
    P += ['SZ03%04d' % i for i in range(0, 999)]  # A股A2权证
    P += ['SZ07%04d' % i for i in range(0, 999)]  # A股增发
    P += ['SZ08%04d' % i for i in range(0, 999)]  # A股A1权证
    P += ['SZ09%04d' % i for i in range(0, 999)]  # A股转配
    P += ['SZ10%04d' % i for i in range(0, 999)]  # 国债现货
    P += ['SZ11%04d' % i for i in range(0, 999)]  # 债券
    P += ['SZ12%04d' % i for i in range(0, 999)]  # 可转换债券
    P += ['SZ13%04d' % i for i in range(0, 999)]  # 国债回购
    P += ['SZ17%04d' % i for i in range(0, 999)]  # 原有投资基金
    P += ['SZ18%04d' % i for i in range(0, 999)]  # 证券投资基金
    P += ['SZ20%04d' % i for i in range(0, 999)]  # B股证券
    P += ['SZ27%04d' % i for i in range(0, 999)]  # B股增发
    P += ['SZ28%04d' % i for i in range(0, 999)]  # B股权证
    P += ['SZ30%04d' % i for i in range(0, 999)]  # 创业板证券
    P += ['SZ37%04d' % i for i in range(0, 999)]  # 创业板增发
    P += ['SZ38%04d' % i for i in range(0, 999)]  # 创业板权证
    P += ['SZ39%04d' % i for i in range(0, 999)]  # 综合指数/成份指数

    P += ['%05d' % i for i in range(0, 9999)] # 港股

    P += ['%c' % (65 + i % 26) for i in range(0, 26)]  # 美股
    P += ['%c%c' % (65 + i / 26, 65 + i % 26) for i in range(0, 676)]  # 美股
    P += ['%c%c%c' % (65 + i / 676, 65 + (i % 676) / 26, 65 + i % 26) for i in range(0, 17576)]  # 美股
    P += ['%c%c%c%c' % (65 + i / 17576, 65 + (i % 17576) / 676, 65 + (i % 676) / 26, 65 + i % 26) for i in range(0, 456976)]  # 美股

    requests = threadpool.makeRequests(GetXueQiuStock, P)
    [pool.putRequest(req) for req in requests]
    pool.wait()


    '''
    X = list()
    y_1 = list() # 预测未来一天ma5
    y_2 = list() # 预测未来一天最高点
    y_3 = list() # 预测未来一天最低点

    seltime = 0

    cx = sqlite3.connect('stock.db')
    cu = cx.cursor()

    cu.execute('select time, ma5, high, low, volume from %s' % tbl)
    datalist = cu.fetchall()
    if len(datalist) < 32:
        return###
    for i in range(32, len(datalist)):
        t, y_ma5, y_high, y_low, volume = tuple(datalist[i])
        y_1.append(y_ma5)
        y_2.append(y_high)
        y_3.append(y_low)
        x = list()
        x += list(datalist[i - 1][1:]) # 前1个1天
        x += list(datalist[i - 2][1:]) # 前2个1天
        x += list(datalist[i - 3][1:]) # 前3个1天
        x += list(datalist[i - 4][1:]) # 前4个1天
        x += list(datalist[i - 5][1:]) # 前5个1天
        cmdx = 'select avg(ma5), max(high), min(low), sum(volume) from %s where time >= %d and time < %d'
        x += list(cu.execute(cmdx % (tbl, datalist[i - 5][0], datalist[i - 1][0])).fetchone())  # 前1个5天
        x += list(cu.execute(cmdx % (tbl, datalist[i - 10][0], datalist[i - 6][0])).fetchone()) # 前2个5天
        x += list(cu.execute(cmdx % (tbl, datalist[i - 15][0], datalist[i - 11][0])).fetchone())# 前3个5天
        x += list(cu.execute(cmdx % (tbl, datalist[i - 20][0], datalist[i - 16][0])).fetchone())# 前4个5天
        x += list(cu.execute(cmdx % (tbl, datalist[i - 25][0], datalist[i - 21][0])).fetchone())# 前5个5天
        x += list(cu.execute(cmdx % (tbl, datalist[i - 30][0], datalist[i - 26][0])).fetchone())# 前1个30天
        X.append(x)

    cu.close()
    cx.close()

    #print 'Predict ma5'
    #learn_from_data(np.array(X), np.array(y_1), 'regressor')
    #print 'Predict min'
    learn_from_data(np.array(X), np.array(y_2), 'regressor')
    #print 'Predict max'
    #learn_from_data(np.array(X), np.array(y_3), 'regressor')
    '''

'''
股票机器学习因素，判断第二天涨跌：
前1~5个(1天)   ma5 最高价 最低价 成交量	
前1~5个(5天)   ma5 最高价 最低价 成交量
前1个(30天)	    ma5 最高价 最低价 成交量
共44个因素
'''

if __name__ == '__main__':
    test()