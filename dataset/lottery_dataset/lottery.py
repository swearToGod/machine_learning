# -*- coding: utf-8 -*-

from sklearn.pipeline import Pipeline
from sklearn.linear_model import *
from sklearn.tree import *
from sklearn.neighbors import *
from sklearn.ensemble import *
from sklearn.preprocessing import *
from sklearn.cross_validation import train_test_split
from sklearn.metrics import *
from sklearn.model_selection import *
import numpy as np

import urllib2
import hashlib
import json
import sqlite3
from datetime import datetime
from time import mktime, time
from collections import OrderedDict



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
            minscore = 1.0 # 记录最小准确度用于后续进一步优化
            start = time()
            for j in range(0, testnum):
                pipes[i].fit(X_train, y_train)
                y_pred = pipes[i].predict(X_test)
                accuracy = accuracy_score(y_test, y_pred)
                if accuracy < minscore:
                    minscore = accuracy
            end = time()
            print('Accuraty:%s score=%.2f time=%d' % (clfs[i].__str__().split('(')[0], minscore, end - start))
    elif type == 'regressor':
        pipes = [Pipeline([
            ['sc', StandardScaler()],
            ['clf', clf]
        ]) for clf in ress]  # 用于统一化初值处理、分类
        for i in range(0, len(ress)):
            minscore = 1.0 # 记录最小准确度用于后续进一步优化
            start = time()
            maxerror = 1.0
            for j in range(0, testnum):
                pipes[i].fit(X_train, y_train)
                y_pred = pipes[i].predict(X_test)
                accuracy = explained_variance_score(y_test, y_pred)
                accuracy1 = mean_absolute_error(y_test, y_pred)
                if accuracy1 > maxerror:
                    maxerror = accuracy1
                if accuracy < minscore:
                    minscore = accuracy
            end = time()
            print('Accuraty:%s score=%.2f err=%d time=%d' % (ress[i].__str__().split('(')[0], minscore, maxerror, end - start))

testnum = 1

def getLotteryInfo():
    url = 'http://client.fcaimao.com/lottery/issue_notify.htm'
    appid = 'd12f273d-5218-ef562-ae01-fa2er4d23862'
    sourceusername = 'cps_dv01'
    lotterid = '10032'

    cx = sqlite3.connect('lottery.db')
    cu = cx.cursor()
    try:
        cu.execute('create table lottery (t int primary key, r0 int, r1 int, r2 int, r3 int, r4 int, r5 int, b int)')
    except Exception as e:
        pass

    querybegin = 0
    querysize = 15

    while True:
        d_1 = OrderedDict()
        d_1['lotteryId'] = '10032'
        d_1['firstRow'] = '%d' % querybegin
        d_1['fetchSize'] = '%d' % querysize
        d_1['requestType'] = '7'
        d_1['version'] = '3.5.1'
        d_1['appname'] = 'lottery'
        d_1['sourceUserName'] = 'cps_dv01'

        d_2 = d_1.values()
        d_2.append(appid)
        d_2.sort(reverse=True)
        signdata = '[%s]' % (', '.join(d_2))
        sign = hashlib.md5(signdata).hexdigest().lower()
        d_1['sign'] = sign[8: 16] + sign[24: 32] + sign[16: 24] + sign[0: 8]

        d_1_arr = list()
        for k in d_1:
            d_1_arr.append('%s=%s' % (k, d_1[k]))
        post = '&'.join(d_1_arr)
        response = urllib2.urlopen(urllib2.Request(url, post)).read()
        jsondata = json.loads(response)
        l = len(jsondata)
        if l == 0:
            break
        for item in jsondata:
            t = int(mktime(datetime.strptime(item['drawTime'], "%Y-%m-%d %H:%M:%S").timetuple()))
            numb = item['drawNumber']
            r0 = int(numb[0: 2])
            r1 = int(numb[3: 5])
            r2 = int(numb[6: 8])
            r3 = int(numb[9: 11])
            r4 = int(numb[12: 14])
            r5 = int(numb[15: 17])
            b = int(numb[18: 20])
            cx.execute('insert or ignore into lottery values (?,?,?,?,?,?,?,?)', (t, r0, r1, r2, r3, r4, r5, b))
        cx.commit()

        querybegin += l

    cu.close()
    cx.close()

#getLotteryInfo()

def builddata():
    cx = sqlite3.connect('lottery.db')
    cu = cx.cursor()
    X = list()
    y = list()

    cu.execute('select r0,r1,r2,r3,r4,r5,b from lottery')
    data = cu.fetchall()
    for i in range(0, len(data) - 10):
        x = list()
        x.append(data[i+1][0])
        x.append(data[i+1][1])
        x.append(data[i+1][2])
        x.append(data[i+1][3])
        x.append(data[i+1][4])
        x.append(data[i+1][5])
        x.append(data[i+1][6])
        x.append(data[i+2][0])
        x.append(data[i+2][1])
        x.append(data[i+2][2])
        x.append(data[i+2][3])
        x.append(data[i+2][4])
        x.append(data[i+2][5])
        x.append(data[i+2][6])
        x.append(data[i+3][0])
        x.append(data[i+3][1])
        x.append(data[i+3][2])
        x.append(data[i+3][3])
        x.append(data[i+3][4])
        x.append(data[i+3][5])
        x.append(data[i+3][6])
        x.append(data[i+4][0])
        x.append(data[i+4][1])
        x.append(data[i+4][2])
        x.append(data[i+4][3])
        x.append(data[i+4][4])
        x.append(data[i+4][5])
        x.append(data[i+4][6])
        x.append(data[i+5][0])
        x.append(data[i+5][1])
        x.append(data[i+5][2])
        x.append(data[i+5][3])
        x.append(data[i+5][4])
        x.append(data[i+5][5])
        x.append(data[i+5][6])
        X.append(x)
        y.append(data[i][6])
    learn_from_data(np.array(X), np.array(y), 'regressor')

builddata()