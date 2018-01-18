# -*- coding: utf-8 -*-

import urllib2
import sqlite3
import json
import time
import threadpool
import threading
from lxml import etree
import os

DEBUG = False
ERROR = False

baseurl = 'http://bitkan.com/price'

class HistoryUpdater(object):
    def __init__(self):
        if DEBUG:
            proxy_handler = urllib2.ProxyHandler({
                'http': 'http://127.0.0.1:8888',
                'https': 'http://127.0.0.1:8888',
            })
            urllib2.install_opener(urllib2.build_opener(proxy_handler))
        self.tblcaches = list()
        self.lock = threading.Lock()

    def UpdateOnePrice(self, args):
        '''
        Update Coin type for each website
        :param coinname: btc eth ...
        :param coinid: 123 456 ...
        :param site: conbase.com ....
        :return:
        '''
        coinname, coinid, site = args['arg1'], args['arg2'], args['arg3']
        block = 3600  # 1day
        baseurl = 'http://bitkan.com'
        tbl = site.replace('.', '').replace('-', '') + '_' + coinname
        cx = sqlite3.connect('digitalcash.db')
        cu = cx.cursor()

        # global ERROR
        # if ERROR:
        #    return

        # 防止重复添加
        if tbl in self.tblcaches:
            return
        self.tblcaches.append(tbl)

        # 不存在则创建表
        try:
            # 时间 开盘价 最高价 最低价 收盘价 成交量
            sql = 'create table %s (t int primary key, c float, h float, l float, o float, v float)' % tbl
            cu.execute(sql)
        except Exception as e:
            pass  # Already exist

        begintime = 0

        # 获取数据库最后一项
        try:
            self.lock.acquire()
            sql = 'select max(t) from %s' % tbl
            cu.execute(sql)
            out = cu.fetchone()[0]
            if out is not None:
                begintime = out
            self.lock.release()
        except Exception as e:
            self.lock.release()
            #print 'x', e.message
            return

        if begintime == 1300000000:
            # 在线获取最小值
            try:
                urlext = '/chart/%s/history?symbol=%s&resolution=1&from=1300000000&to=1300000060' % (coinid, site)
                response = urllib2.urlopen(baseurl + urlext).read()
                if response.find('Error') != -1:
                    return  # 服务器异常
                di = json.loads(response)
                if len(di['t']) == 0:
                    return  # 空数据
                if begintime < int(di['t'][0]):
                    begintime = int(di['t'][0])
            except Exception as e:
               pass

        errtime = 0
        begintime += 60 # 最小间隔
        endtime = int(time.time())
        while begintime < endtime:
            endtime = int(time.time())
            urlext = '/chart/%s/history?symbol=%s&resolution=1&from=%d&to=%d' % \
                     (coinid, site, begintime, begintime + block)
            try:
                response = urllib2.urlopen(baseurl + urlext).read()
                di = json.loads(response)
                length = len(di['t'])
                if length == 0:
                    return
                self.lock.acquire()
                for j in range(0, length):

                    cx.execute('insert or ignore into %s values (?,?,?,?,?,?)' % tbl,
                               (int(di['t'][j]), float(di['c'][j]), float(di['h'][j]), float(di['l'][j]),
                                float(di['o'][j]), float(di['v'][j])))
                cx.commit()
                self.lock.release()
                # print '%s-%s done' % (time.ctime(int(di['t'][0])), time.ctime(int(di['t'][-1])))
                begintime += block
                if begintime < int(di['t'][-1]):
                    begintime = int(di['t'][-1]) + block
            except Exception as e:
                # ERROR = True
                #print e.message
                break

        cu.close()
        cx.close()
        #print '%s updated' % tbl
    def UpdateOnePrice(self, args):
        '''
        Update Coin type for each website
        :param coinname: btc eth ...
        :param coinid: 123 456 ...
        :param site: conbase.com ....
        :return:
        '''
        coinname, coinid, site = args['arg1'], args['arg2'], args['arg3']
        block = 3600  # 1day
        baseurl = 'http://bitkan.com'
        tbl = site.replace('.', '').replace('-', '') + '_' + coinname
        cx = sqlite3.connect('digitalcash.db')
        cu = cx.cursor()

        # global ERROR
        # if ERROR:
        #    return

        # 防止重复添加
        if tbl in self.tblcaches:
            return
        self.tblcaches.append(tbl)

        # 不存在则创建表
        try:
            # 时间 开盘价 最高价 最低价 收盘价 成交量
            sql = 'create table %s (t int primary key, c float, h float, l float, o float, v float)' % tbl
            cu.execute(sql)
        except Exception as e:
            pass  # Already exist

        begintime = 0

        # 获取数据库最后一项
        try:
            self.lock.acquire()
            sql = 'select max(t) from %s' % tbl
            cu.execute(sql)
            out = cu.fetchone()[0]
            if out is not None:
                begintime = out
            self.lock.release()
        except Exception as e:
            self.lock.release()
            #print 'x', e.message
            return

        if begintime == 1300000000:
            # 在线获取最小值
            try:
                urlext = '/chart/%s/history?symbol=%s&resolution=1&from=1300000000&to=1300000060' % (coinid, site)
                response = urllib2.urlopen(baseurl + urlext).read()
                if response.find('Error') != -1:
                    return  # 服务器异常
                di = json.loads(response)
                if len(di['t']) == 0:
                    return  # 空数据
                if begintime < int(di['t'][0]):
                    begintime = int(di['t'][0])
            except Exception as e:
                pass

        errtime = 0
        begintime += 60 # 最小间隔
        endtime = int(time.time())
        while begintime < endtime:
            endtime = int(time.time())
            urlext = '/chart/%s/history?symbol=%s&resolution=1&from=%d&to=%d' % \
                     (coinid, site, begintime, begintime + block)
            try:
                response = urllib2.urlopen(baseurl + urlext).read()
                di = json.loads(response)
                length = len(di['t'])
                if length == 0:
                    return
                self.lock.acquire()
                for j in range(0, length):

                    cx.execute('insert or ignore into %s values (?,?,?,?,?,?)' % tbl,
                               (int(di['t'][j]), float(di['c'][j]), float(di['h'][j]), float(di['l'][j]),
                                float(di['o'][j]), float(di['v'][j])))
                cx.commit()
                self.lock.release()
                # print '%s-%s done' % (time.ctime(int(di['t'][0])), time.ctime(int(di['t'][-1])))
                begintime += block
                if begintime < int(di['t'][-1]):
                    begintime = int(di['t'][-1]) + block
            except Exception as e:
                # ERROR = True
                #print e.message
                break

        cu.close()
        cx.close()
        #print '%s updated' % tbl
    def GetConfig(self, args):
        # Update coin websites
        global baseurl
        text, href, cf_args = args['arg1'], args['arg2'], args['arg3']
        coinname = text.replace('?category=', '', ).replace('#categories', '')
        subtree = etree.HTML(urllib2.urlopen(baseurl + href).read())
        subnodes = subtree.xpath("//div[@class='col-md-6']//a")
        for node in subnodes:
            if node.attrib['href'].find('/chart') != -1 and len(node.getchildren()) > 0:
                spannode = node.getchildren()[0]
                if spannode.attrib['class'].find('sprite-') != -1:
                    if spannode.attrib['class'].find('eth') != -1:
                        break  # 未知数据
                    coinid = node.attrib['href'].replace('/chart/', '')
                    site = spannode.attrib['class'].replace('sprite sprite-', '')
                    self.lock.acquire()
                    cf_args.append({'arg1':coinname, 'arg2':coinid, 'arg3':site})
                    self.lock.release()

    def UpdateAll(self):
        '''
        Download configuration from bitkan
        :return:
        '''
        pool = threadpool.ThreadPool(10)

        ct_args = list()
        cf_args = list()
        try:
            tree = etree.HTML(urllib2.urlopen(baseurl).read())
        except Exception as e:
            pass
        nodes = tree.xpath("//ul[@class='nav nav-tabs']//a")
        for node in nodes:
            if node.attrib['href'].find('?category') != -1:
                ct_args.append({'arg1':node.text, 'arg2':node.attrib['href'], 'arg3':cf_args})
        requests = threadpool.makeRequests(self.GetConfig, ct_args)
        [pool.putRequest(req) for req in requests]
        pool.wait()

        requests = threadpool.makeRequests(self.UpdateOnePrice, cf_args)
        [pool.putRequest(req) for req in requests]
        pool.wait()

    def UpdateFromAICoin(self, args):
        coinname, coinid, site, coref = args['arg1'], args['arg2'], args['arg3'], args['arg4']

        tbl = site.replace('.', '').replace('-', '') + '_' + coinname
        cx = sqlite3.connect('digitalcash.db')
        cu = cx.cursor()

        # 不存在则创建表
        try:
            # 时间 开盘价 最高价 最低价 收盘价 成交量
            sql = 'create table %s (t int primary key, c double, h double, l double, o double, v double)' % tbl
            cu.execute(sql)
        except Exception as e:
            pass  # Already exist

        try:
            url = 'https://www.aicoin.net.cn/chart/api/data/period?symbol=%s&step=60' % coinid
            js = json.loads(urllib2.urlopen(url).read())
            for item in js['data']:
                cu.execute('insert or ignore into %s values (?,?,?,?,?,?)' % tbl,
                           (int(item[0]), float(item[1]), float(item[2]), float(item[3]), float(item[4]), float(item[5])))
        except Exception as e:
            pass
        cx.commit()
        cu.close()
        cx.close()
        print '%s updated' % coinname

#if __name__ == '__main__':
#    HistoryUpdater().UpdateAll()

'''
比特币机器学习因素，判断下一个小时涨跌：
前1~16个(1分钟)		开盘价 最高价 最低价 收盘价 成交量	
前1~4个(15分钟)		开盘价 最高价 最低价 收盘价 成交量
前1~4个(1小时)		开盘价 最高价 最低价 收盘价 成交量
前1~2个(1天)		开盘价 最高价 最低价 收盘价 成交量
共130个因素，一天1440个数据
'''

'''
lock = threading.Lock()
def getinfo(i):
    response = urllib2.urlopen('http://bitkan.com/chart/%d' % i).read()
    matcher = re.search(re.compile(r'ChartMain.init\((.*)\)'), response)
    if matcher is not None:
        j = json.loads(matcher.group(1))
        if len(j) > 0 and 'market_config' in j:
            config = j['market_config']
            lock.acquire()
            print config['coin_name'], config['site'], config['tbl_name']
            lock.release()

pool = threadpool.ThreadPool(20)
requests = threadpool.makeRequests(getinfo, [i for i in range(0, 99999)])
[pool.putRequest(req) for req in requests]
pool.wait()
'''

'''
BTC bitstamp bitstamp
BTC bitfinex bitfinex
LTC bitfinex ltc_bitfinex
LTC okcoin.com ltc_okcoin_intl
BTC okcoin.com okcoin_intl
BTC okex.com okcoin_this_week
LTC okex.com ltc_okcoin_this_week
BTC okex.com okcoin_next_week
BTC okex.com okcoin_quarter
LTC okex.com ltc_okcoin_next_week
BTC coinbase coinbase
LTC okex.com ltc_okcoin_quarter
BTC itbit itbit
BTC gemini gemini
BTC coinnice coinnice_future
BTC coinnice coinnice_spot
BTC kraken 87
BTC cex 88
BTC bithumb 97
BTC bitflyer 93
DASH poloniex poloniex_dash
BTS poloniex poloniex_bts
ETH kraken kraken_eth
ETH bitfinex bitfinex_eth
LSK poloniex poloniex_lsk
DOGE poloniex poloniex_doge
ETC poloniex poloniex_etc
XRP poloniex poloniex_xrp
SC poloniex poloniex_sc
FCT poloniex poloniex_fct
XMR poloniex poloniex_xmr
MAID poloniex poloniex_maid
ETH poloniex poloniex_eth
EMC bittrex 163
ETC bitfinex bfx_etc
ETC kraken kraken_etc
REP poloniex poloniex_rep
ZEC poloniex poloniex_zec
XEM poloniex poloniex_xem
GAME poloniex poloniex_game
STEEM poloniex poloniex_steem
GNT poloniex poloniex_gnt
DGB poloniex poloniex_dgb
NXT poloniex poloniex_nxt
BURST poloniex poloniex_burst
BCN poloniex poloniex_bcn
XEM bittrex 208
DCR poloniex poloniex_dcr
DGD bittrex 205
XRP bittrex 206
XLM bittrex 207
WAVES bittrex 209
STEEM bittrex 210
PIVX bittrex 212
DOGE bittrex 213
DGB bittrex 214
DCR bittrex 215
WINGS bittrex bittrex_wings_btc
ETH okcoin.com okcoin_intl_eth
NEO bittrex 223
XMR bittrex 222
GBYTE bittrex 227
LSK bittrex 226
MAID bittrex 228
GNO bittrex 225
FCT bittrex 229
PPC bittrex 230
STRAT poloniex 231
GNO poloniex 232
ARDR poloniex 233
PPC poloniex 235
XMR bitfinex bitfinex_xmr
LTC bitstamp 251
BNT bittrex 252
EOS bitfinex 254
BCH huobi.pro 268
BCH bittrex 269
BCH binance 275
GAS binance 276
BNB binance 277
NEO binance 278
ETH binance 279
QTUM binance 281
LTC binance 280
BNT binance 284
SNT binance 283
EOS binance 285
WTC binance 301
DNT binance 302
MCO binance 303
ICN binance 304
OAX binance 305
BCH poloniex poloniex_bcc
AMP poloniex poloniex_amp
XPM poloniex poloniex_xpm
BLK poloniex poloniex_blk
EXP poloniex poloniex_exp
SBD poloniex poloniex_sbd
RIC poloniex poloniex_ric
NMC poloniex poloniex_nmc
XCP poloniex poloniex_xcp
VTC poloniex poloniex_vtc
BTCD poloniex poloniex_btcd
SYS poloniex poloniex_sys
VRC poloniex poloniex_vrc
GRC poloniex poloniex_grc
EMC2 poloniex poloniex_emc2
PINK poloniex poloniex_pink
FLO poloniex poloniex_flo
HUC poloniex poloniex_huc
NAV poloniex poloniex_nav
LBC poloniex poloniex_lbc
POT poloniex poloniex_pot
OMNI poloniex poloniex_omni
CLAM poloniex poloniex_clam
BCY poloniex poloniex_bcy
PASC poloniex poloniex_pasc
XBC poloniex poloniex_xbc
VIA poloniex poloniex_via
FLDC poloniex poloniex_fldc
BELA poloniex poloniex_bela
RADS poloniex poloniex_rads
NEOS poloniex poloniex_neos
NXC poloniex poloniex_nxc
BTM poloniex poloniex_btm
XVC poloniex poloniex_xvc
ETH bittrex 402
ETC bittrex 403
EXP bittrex 406
AMP bittrex 404
SBD bittrex 405
CLUB bittrex 408
VOX bittrex 407_vox
NXT bittrex 409
DASH bittrex 410
BLK bittrex 412
SYS bittrex 413
XCP bittrex 414
VTC bittrex 415
RDD bittrex 416
BTCD bittrex 417
RBY bittrex 418
XMG bittrex 420
GRC bittrex 422
VRC bittrex 421
FLO bittrex 423
PINK bittrex 424
GEO bittrex 425
BRK bittrex 428
ZEC bittrex 427
XZC bittrex 429
FTC bittrex 430
ARK bittrex 432
DTB bittrex 433
RLC bittrex 434
TRST bittrex 435
LNM bittrex 436
GUP bittrex 437
FLDC bittrex 439
RISE bittrex 440
OK bittrex 441
ANT bittrex 443
SC bittrex 444
XVG bittrex 445
NAV bittrex 447
BCY bittrex 446
GNT bittrex 448
BAT bittrex 449
1ST bittrex 451
UBQ bittrex 450
ZEN bittrex 452
MYST bittrex 454
CFI bittrex 453
PTOY bittrex 455
GRS bittrex 456
QRL bittrex 457
NMR bittrex 458
SNT bittrex 459
PAY bittrex 460
MCO bittrex 461
NEOS bittrex 462
ARDR bittrex 463
GAME bittrex 464
DCT bittrex 465
XEL bittrex 466
OMG bittrex 467
CVC bittrex 468
ZCL bittrex 469
ADT bittrex 470
COVAL bittrex 471
QTUM bittrex 472
ADX bittrex 473
STORJ bittrex 474
MTL bittrex 475
SWIFT bittrex 476
EDG bittrex 477
QTUM coinone 479
QTUM binance 481
HSR acx 482
BCH okex.com 485
DASH bithumb 486
DASH bitfinex 487
DASH kraken 488
DASH hitbtc 489
DASH hitbtc 490
DASH poloniex 491
DASH bitfinex 492
BCH bitfinex 493
BT2 bitfinex 494
BT1 bitfinex 495
XRP bithumb 496
ETH bithumb 498
BCH bithumb 497
LTC bithumb 499
ETC bithumb 501
ZEC bithumb 502
XMR bithumb 503
XRP coinone 504
BTC coinone 505
ETH coinone 506
BCH coinone 507
ETC coinone 508
ZEC bitfinex 509
ZEC bitfinex 510
XRP bitfinex 511
XRP bitfinex 512
IOTA bitfinex 513
IOTA bitfinex 514
IOTA bitfinex 515
EOS bitfinex 516
EOS bitfinex 518
SAN bitfinex 519
SAN bitfinex 520
SAN bitfinex 521
OMG bitfinex 523
OMG bitfinex 522
OMG bitfinex 524
NEO bitfinex 525
NEO bitfinex 526
NEO bitfinex 527
ETP bitfinex 528
ETP bitfinex 529
QTUM bitfinex 531
ETP bitfinex 530
QTUM bitfinex 532
QTUM bitfinex 533
AVT bitfinex 534
AVT bitfinex 535
AVT bitfinex 536
BCH hitbtc 537
XMR hitbtc 538
ETH hitbtc 540
ZEC hitbtc 539
BCH hitbtc 541
BTC hitbtc 542
LTC hitbtc 543
XMR hitbtc 544
XRP hitbtc 545
XDN hitbtc 546
BCH hitbtc 547
ZEC hitbtc 548
ETH hitbtc 549
ADX hitbtc 551
EOS hitbtc 550
NXT hitbtc 552
LTC hitbtc 554
ETC hitbtc 553
MAID hitbtc 555
BCN hitbtc 556
XTZ hitbtc 557
STRAT hitbtc 558
XEM hitbtc 559
SNT hitbtc 560
XDN hitbtc 561
LSK hitbtc 562
COSS hitbtc 563
LRC hitbtc 564
CDT hitbtc 565
XEM hitbtc 566
DOGE hitbtc 567
DOGE hitbtc 568
MAID hitbtc 569
LRC hitbtc 571
XMR hitbtc 570
NXT hitbtc 572
BQX hitbtc 573
SNC hitbtc 574
EDG hitbtc 575
AEON hitbtc 576
MTH hitbtc 577
BCN hitbtc 578
MTH hitbtc 579
XTZ hitbtc 580
STX hitbtc 581
XTZ hitbtc 582
NEO hitbtc 583
BET hitbtc 584
MSP hitbtc 585
ZRC hitbtc 586
BNT hitbtc 588
IXT hitbtc 589
EOS hitbtc 587
ZRX hitbtc 590
ZRX hitbtc 591
CSNO hitbtc 592
HPC hitbtc 593
HVN hitbtc 594
AVT hitbtc 595
TKR hitbtc 596
STX hitbtc 597
NET hitbtc 598
NDC hitbtc 600
STX hitbtc 599
OPT hitbtc 601
RVT hitbtc 602
DICE hitbtc 603
NEO hitbtc 604
AE hitbtc 605
PPC hitbtc 606
OMG hitbtc 608
EOS hitbtc 609
CDT hitbtc 610
HVN hitbtc 611
MCAP hitbtc 612
CCT hitbtc 613
QAU hitbtc 614
TNT hitbtc 615
ZRX hitbtc 616
QAU hitbtc 617
POE hitbtc 618
BMC hitbtc 619
DCT hitbtc 620
TNT hitbtc 621
EBET hitbtc 622
POE hitbtc 623
NEO hitbtc 624
XVG hitbtc 625
ORME hitbtc 626
PPC hitbtc 627
PLR hitbtc 629
DNT hitbtc 628
PING hitbtc 630
VERI hitbtc 631
BMC hitbtc 632
SNC hitbtc 633
TRX hitbtc 634
EMGO hitbtc 635
PIX hitbtc 636
TRX hitbtc 637
PAY hitbtc 638
STRAT hitbtc 640
MYB hitbtc 641
YOYOW hitbtc 642
VEN hitbtc 643
PIX hitbtc 644
BMC hitbtc 645
TRST hitbtc 646
WAVES hitbtc 647
FCN hitbtc 648
SKIN hitbtc 649
DENT hitbtc 650
FYN hitbtc 651
SNC hitbtc 652
PPT hitbtc 653
VERI hitbtc 654
SC hitbtc 655
PLBT hitbtc 657
CDT hitbtc 656
DCN hitbtc 658
NTO hitbtc 659
STEEM hitbtc 660
ZEC hitbtc 661
BNT hitbtc 662
QTUM hitbtc 663
SNGLS hitbtc 664
SUR hitbtc 665
ICN hitbtc 666
TAAS hitbtc 667
1ST hitbtc 668
DGB hitbtc 669
CFI hitbtc 670
TIX hitbtc 671
PRO hitbtc 672
ETC hitbtc 673
SNM hitbtc 674
IND hitbtc 675
PLU hitbtc 676
MANA hitbtc 677
BAS hitbtc 678
ETC hitbtc 679
PLU hitbtc 680
PTOY hitbtc 682
XVG hitbtc 681
FUN hitbtc 683
XVG hitbtc 684
RLC hitbtc 685
GUP hitbtc 686
OAX hitbtc 687
FUN hitbtc 689
NXC hitbtc 688
TAAS hitbtc 690
ARDR hitbtc 691
CFI hitbtc 692
PTOY hitbtc 693
CVC hitbtc 695
TKN hitbtc 696
DCN hitbtc 697
ANT hitbtc 698
DGD hitbtc 700
LUN hitbtc 702
GAME hitbtc 701
REP hitbtc 699
EMC hitbtc 703
GNO hitbtc 704
TNT hitbtc 705
WINGS hitbtc 706
DSH hitbtc 707
1ST hitbtc 708
OAX hitbtc 711
DASH hitbtc 712
DICE hitbtc 714
SBD hitbtc 713
OAX hitbtc 715
QCN hitbtc 718
UET hitbtc 717
TIME hitbtc 721
FUN hitbtc 719
XAUR hitbtc 722
DDF hitbtc 720
XAUR hitbtc 723
TRX hitbtc 724
SAN hitbtc 726
TIME hitbtc 727
SWT hitbtc 728
AMP hitbtc 730
SWT hitbtc 729
ETH bitflyer 736
BCH bitflyer 737
ETH coinbase 749
BTC coinbase 751
LTC coinbase 750
ETH coinbase 752
ETH coinbase 754
LTC coinbase 753
BTC coinbase 755
LTC coinbase 756
2GIVE bittrex 758
1ST bittrex 757
ADA bittrex 760
ABY bittrex 759
ADT bittrex 762
ADX bittrex 763
AGRS bittrex 765
AEON bittrex 764
ANT bittrex 766
APX bittrex 767
AUR bittrex 768
BAT bittrex 769
BAY bittrex 770
BCH bittrex 771
BCH bittrex 772
BITB bittrex 773
BLITZ bittrex 774
BLOCK bittrex 775
BRX bittrex 777
BNT bittrex 776
BSD bittrex 778
BTC bittrex 780
BURST bittrex 782
BYC bittrex 783
CANN bittrex 784
CFI bittrex 785
CLAM bittrex 786
CLOAK bittrex 787
Capricoin bittrex 788
Creditbit bittrex 789
CRW bittrex 791
Creditbit bittrex 790
CVC bittrex 793
CURE bittrex 792
DASH bittrex 795
DASH bittrex 796
DGB bittrex 797
DGD bittrex 798
DMD bittrex 799
LTC poloniex poloniex_ltc
LTC bittrex 407
EFL bittrex 804
EGC bittrex 805
ENRG bittrex 807
EMC2 bittrex 806
ERC bittrex 808
ETC bittrex 809
ETC bittrex 810
EXCL bittrex 812
ETH bittrex 811
FAIR bittrex 813
FCT bittrex 814
FUN bittrex 815
FUN bittrex 816
GAM bittrex 817
GBG bittrex 818
GNO bittrex 821
GLD bittrex 820
GCR bittrex 819
GNT bittrex 822
GOLOS bittrex 823
GUP bittrex 824
HMQ bittrex 825
HMQ bittrex 826
INCNT bittrex 827
INFX bittrex 828
IOC bittrex 829
ION bittrex 830
KMD bittrex 832
KORE bittrex 833
IOP bittrex 831
LBC bittrex 834
LGD bittrex 835
LGD bittrex 836
LMC bittrex 837
LTC bittrex 838
LTC bittrex 839
LUN bittrex 840
MCO bittrex 841
MonaCoin bittrex 845
MLN bittrex 844
MTL bittrex 846
MUE bittrex 847
MUSIC bittrex 848
MYST bittrex 849
NEO bittrex 850
NEO bittrex 851
NMR bittrex 853
NLG bittrex 852
NXC bittrex 854
NXS bittrex 855
OMG bittrex 856
OMG bittrex 857
OMNI bittrex 858
PART bittrex 859
PAY bittrex 860
PKB bittrex 862
PDC bittrex 861
POT bittrex 863
PTOY bittrex 865
PTC bittrex 864
QTUM bittrex 867
QRL bittrex 866
QWARK bittrex 868
RADS bittrex 869
REP bittrex 870
REP bittrex 871
RLC bittrex 872
SC bittrex 874
SEQ bittrex 875
SHIFT bittrex 876
SLR bittrex 878
SIB bittrex 877
SLS bittrex 879
SNRG bittrex 881
SPHR bittrex 883
SNT bittrex 882
START bittrex 885
SPR bittrex 884
STORJ bittrex 886
STRAT bittrex 888
STRAT bittrex 887
SWT bittrex 889
SYNX bittrex 890
THC bittrex 891
TKS bittrex 894
TRIG bittrex 895
TRST bittrex 896
TRUST bittrex 897
TX bittrex 898
UNB bittrex 899
VIA bittrex 901
VRM bittrex 902
VTR bittrex 903
WINGS bittrex 905
WAVES bittrex 904
XEM bittrex 908
XDN bittrex 907
XLM bittrex 909
XMR bittrex 911
XMY bittrex 912
XMR bittrex 910
XRP bittrex 913
XRP bittrex 914
XST bittrex 915
WhiteCoin bittrex 917
XVC bittrex 916
ZEC bittrex 919
ZEC bittrex 918
BTC okex.com 920
LTC okex.com 921
ETH okex.com 922
ETC okex.com 923
ETC okex.com 925
ETH okex.com 924
HSR allcoin 926
HSR neraex 927
HSR cryptopia 928
HSR bit-z 929
ETH bitstamp 930
BTC quoine 933
ETH quoine 934
BCH kraken 935
BCH kraken 936
BCH cex 937
BTG kkex 938
BCH kkex 941
BCH bitfinex 943
BCH poloniex 944
BCH cex 945
BCH cryptopia 946
BCH cex 947
ETH huobi.pro 949
LTC huobi.pro 950
ETC huobi.pro 951
ETH huobi.pro 955
BTC huobi.pro 954
LTC huobi.pro 956
BCH huobi.pro 957
BTC zb 958
LTC zb 960
BCH okex.com 959
ETH zb 961
ETC zb 962
BTS zb 963
EOS zb 965
BCH zb 964
QTUM zb 966
HSR zb 967
LTC zb 968
ETH zb 969
ETC zb 970
BTS zb 971
BCH zb 972
EOS zb 973
QTUM zb 974
HSR zb 975
ETH bitstar 977
BTC bitstar 976
ETC bitstar 978
LTC bitstar 979
BCH bitstar 980
LTC liqui 981
DASH liqui 984
ETH liqui 988
ICN liqui 987
GNT liqui 992
WINGS liqui 993
WAVES liqui 998
BTC binance 1001
BTC poloniex 1003
MLN liqui 1010
TIME liqui 1011
GNT liqui 1012
LTC liqui 1013
DASH liqui 1014
ICN liqui 1016
MLN liqui 1017
WAVES liqui 1019
TIME liqui 1020
LTC liqui 1024
BTC liqui 1025
DASH liqui 1026
ETH liqui 1027
ICN liqui 1028
GNT liqui 1029
WAVES liqui 1033
TIME liqui 1035
MLN liqui 1034
REP liqui 1036
EDG liqui 1037
REP liqui 1038
EDG liqui 1039
REP liqui 1040
EDG liqui 1041
RLC liqui 1043
RLC liqui 1042
RLC liqui 1044
TRST liqui 1045
TRST liqui 1046
TRST liqui 1047
WINGS liqui 1049
WINGS liqui 1048
GNO liqui 1052
GNO liqui 1053
GNO liqui 1054
GUP liqui 1055
GUP liqui 1056
GUP liqui 1057
TAAS liqui 1058
TAAS liqui 1059
TAAS liqui 1060
TKN liqui 1064
TKN liqui 1065
TKN liqui 1066
ANT liqui 1073
ANT liqui 1074
ANT liqui 1075
BAT liqui 1076
BAT liqui 1077
BAT liqui 1078
QRL liqui 1079
QRL liqui 1081
QRL liqui 1080
BNT liqui 1082
BNT liqui 1083
BNT liqui 1084
MGO liqui 1086
MGO liqui 1085
MGO liqui 1087
MYST liqui 1088
MYST liqui 1089
MYST liqui 1090
SNGLS liqui 1091
SNGLS liqui 1092
SNGLS liqui 1093
PTOY liqui 1094
PTOY liqui 1095
PTOY liqui 1096
CFI liqui 1097
CFI liqui 1098
CFI liqui 1099
SNM liqui 1100
SNM liqui 1101
SNM liqui 1102
SNT liqui 1103
SNT liqui 1104
SNT liqui 1105
MCO liqui 1106
MCO liqui 1107
MCO liqui 1108
STORJ liqui 1109
STORJ liqui 1110
STORJ liqui 1111
ADX liqui 1112
ADX liqui 1113
ADX liqui 1114
EOS liqui 1115
EOS liqui 1116
EOS liqui 1117
PAY liqui 1118
PAY liqui 1119
PAY liqui 1120
XID liqui 1121
XID liqui 1122
XID liqui 1123
OMG liqui 1124
OMG liqui 1125
SAN liqui 1127
OMG liqui 1126
SAN liqui 1128
SAN liqui 1129
CVC liqui 1133
CVC liqui 1134
CVC liqui 1135
NET liqui 1136
NET liqui 1137
NET liqui 1138
DGD liqui 1139
DGD liqui 1140
DGD liqui 1141
OAX liqui 1142
OAX liqui 1143
OAX liqui 1144
BCH liqui 1145
BCH liqui 1146
BCH liqui 1147
DNT liqui 1148
DNT liqui 1149
DNT liqui 1150
STX liqui 1151
STX liqui 1152
STX liqui 1153
ZRX liqui 1154
ZRX liqui 1155
ZRX liqui 1156
TNT liqui 1157
TNT liqui 1158
TNT liqui 1159
AE liqui 1160
AE liqui 1162
AE liqui 1161
VEN liqui 1164
VEN liqui 1163
VEN liqui 1165
BMC liqui 1167
BMC liqui 1168
BMC liqui 1166
MANA liqui 1169
MANA liqui 1170
MANA liqui 1171
PRO liqui 1172
PRO liqui 1173
PRO liqui 1174
KNC liqui 1175
KNC liqui 1176
KNC liqui 1177
SALT liqui 1178
SALT liqui 1179
SALT liqui 1180
IND liqui 1183
IND liqui 1181
IND liqui 1182
TRX liqui 1184
TRX liqui 1186
ENG liqui 1187
TRX liqui 1185
ENG liqui 1189
ENG liqui 1188
AST liqui 1190
AST liqui 1191
AST liqui 1192
REQ liqui 1193
REQ liqui 1195
REQ liqui 1194
ETH bit-z 1196
LTC bit-z 1197
FCT bit-z 1198
GXS bit-z 1199
LSK bit-z 1200
XPM bit-z 1203
ZEC bit-z 1202
ETC bit-z 1201
PPC bit-z 1204
XAS bit-z 1206
MZC bit-z 1205
DOGE bit-z 1207
LTC aex 1208
ETH aex 1209
ETC aex 1210
DOGE aex 1211
BCH aex 1212
XRP aex 1213
BTS aex 1214
ARDR aex 1215
DASH aex 1216
XLM aex 1217
XEM aex 1218
BLK aex 1219
XZC aex 1220
NXT aex 1221
SYS aex 1222
INF aex 1223
VASH aex 1224
MGC aex 1225
EAC aex 1227
NCS aex 1228
XPM aex 1226
HLB aex 1229
QRK aex 1230
RIC aex 1231
MEC aex 1232
ZCC aex 1233
WDC aex 1234
XCN aex 1235
TAG aex 1236
TMC aex 1237
BTC bitstamp 1238
ETH bitstamp 1239
XRP bitstamp 1240
LTC bitstamp 1241
DASH okex.com 1242
ZEC okex.com 1243
NEO okex.com 1244
GAS okex.com 1245
HSR okex.com 1246
QTUM okex.com 1247
BTG okex.com 1248
ZEC okex.com 1250
DASH okex.com 1249
NEO okex.com 1251
GAS okex.com 1252
HSR okex.com 1253
QTUM okex.com 1254
ETC huobi.pro 1255
DASH huobi.pro 1256
DASH huobi.pro 1257
EOS huobi.pro 1258
OMG huobi.pro 1259
MTL huobi.pro 1260
KNC huobi.pro 1261
RDN huobi.pro 1262
STORJ huobi.pro 1264
ZRX huobi.pro 1263
RCN huobi.pro 1265
AST huobi.pro 1266
EOS huobi.pro 1267
RDN huobi.pro 1269
RCN huobi.pro 1270
OMG huobi.pro 1268
BTC cex.com 1272
BCH cex.com 1273
LTC cex.com 1275
ETH cex.com 1274
DASH cex.com 1276
ETC cex.com 1277
ETH binance 1281
BCH binance 1280
NEO binance 1282
QSP binance 1286
ETH binance 1284
POWR binance 1285
BNB binance 1283
IOTA binance 1287
XRP binance 1288
RDN binance 1289
ETC binance 1291
DASH binance 1290
LSK binance 1292
EOS binance 1293
GXS binance 1294
STORJ binance 1295
TNT binance 1296
RCN binance 1297
BNB binance 1298
HSR binance 1299
OMG binance 1300
MDA binance 1301
XMR binance 1302
MTL binance 1303
POE binance 1306
XZC binance 1304
NULS binance 1307
QSP binance 1305
MTH binance 1309
BTG binance 1308
BCH bitstamp 1310
BCH bitstamp 1311
BCH bitstamp 1312
ETH coin900 1313
SBTC coin900 1314
EOS huobi.pro 1315
OMG huobi.pro 1316
MCO huobi.pro 1317
MCO huobi.pro 1318
CMT huobi.pro 1319
BTG okex.com 1322
CMT huobi.pro 1320
BTG okex.com 1321
LRC okex.com 1323
LRC okex.com 1324
LRC okex.com 1325
MCO okex.com 1326
MCO okex.com 1327
MCO okex.com 1328
NULS okex.com 1329
NULS okex.com 1330
NULS okex.com 1331
LLT cex.com 1332
DASH zb 1333
XRP zb 1334
BCD zb 1335
XRP zb 1336
BCD zb 1337
DASH zb 1338
SBTC zb 1339
SBTC okex.com 1340
QTUM huobi.pro 1341
QTUM huobi.pro 1342
ZEC huobi.pro 1343
ZEC huobi.pro 1344
ETH gate 1345
LLT gate 1346
QTUM gate 1348
LLT gate 1349
BTC gate 1347
QASH gate 1350
EOS gate 1351
QASH gate 1352
BTM gate 1353
BTM gate 1354
ETH gate 1355
LTC gate 1356
BCH gate 1357
SNT gate 1358
HSR gate 1359
EOS gate 1360
ETC gate 1361
SNT gate 1363
LTC gate 1362
ETC gate 1364
QTUM gate 1365
BCH gate 1366
BTG gate 1367
EOS gate 1368
AE gate 1369
AE gate 1370
INK gate 1371
BOT gate 1372
FIL gate 1373
LRC gate 1374
ZEC gate 1375
QTUM gate 1376
ZSC gate 1377
INK gate 1378
BCD gate 1379
VEN gate 1380
LRC gate 1381
QASH gate 1382
PAY gate 1384
BTG gate 1383
BOT gate 1385
STORJ gate 1386
UBTC zb 1387
SMT huobi.pro 1389
UBTC zb 1388
SBTC huobi.pro 1391
SMT huobi.pro 1390
BCX huobi.pro 1392
CVC huobi.pro 1393
CVC huobi.pro 1394
MANA huobi.pro 1395
MANA huobi.pro 1396
WABI binance 1397
WABI binance 1398
TNB okex.com 1399
TNB okex.com 1400
TNB okex.com 1401
XRP okex.com 1402
XRP okex.com 1403
XRP okex.com 1404
MANA okex.com 1405
MANA okex.com 1406
MANA okex.com 1407
CTR okex.com 1408
LINK okex.com 1413
LINK okex.com 1411
CTR okex.com 1409
LINK okex.com 1412
CTR okex.com 1410
SALT okex.com 1414
SALT okex.com 1415
SALT okex.com 1416
1ST okex.com 1417
1ST okex.com 1418
1ST okex.com 1419
WTC okex.com 1420
WTC okex.com 1421
WTC okex.com 1422
SNGLS okex.com 1423
SNGLS okex.com 1424
SNGLS okex.com 1425
SNM okex.com 1426
SNM okex.com 1427
SNM okex.com 1428
ZRX okex.com 1429
ZRX okex.com 1431
BNT okex.com 1433
BNT okex.com 1432
ZRX okex.com 1430
BNT okex.com 1434
CVC okex.com 1435
CVC okex.com 1436
CVC okex.com 1437
VEN huobi.pro 1438
ETH okex.com 1456
ETH okex.com 1457
SALT huobi.pro 1440
ETC okex.com 1443
CMT okex.com 1450
BCD okex.com 1445
SALT huobi.pro 1441
DGD okex.com 1451
BCH okex.com 1453
ACT okex.com 1449
SBTC okex.com 1446
AVT okex.com 1448
BTG okex.com 1444
BCX okex.com 1447
VEN huobi.pro 1439
ETH okex.com 1458
BCH okex.com 1455
ETC okex.com 1459
ETC okex.com 1460
MCO bit-z 1462
UNIT bit-z 1463
PYLNT bit-z 1464
ETC okex.com 1461
BTF gate 1466
BTF gate 1465
TSL gate 1467
BIFI gate 1468
BIFI gate 1469
DAI gate 1470
IOTA gate 1471
IOTA gate 1472
ADA gate 1473
ADA gate 1474
LSK gate 1475
LSK gate 1476
WAVES gate 1477
WAVES gate 1478
NAS gate 1480
NAS gate 1479
LBTC zb 1481
LBTC zb 1482
HSR huobi.pro 1483
HSR huobi.pro 1484
WAX huobi.pro 1485
BTM huobi.pro 1486
ELF huobi.pro 1487
NAS huobi.pro 1488
AION binance 1490
ELF binance 1489
NEBL binance 1491
BRD binance 1492
MCO binance 1493
EDO binance 1494
WINGS binance 1495
QVT okex.com 1496
QVT okex.com 1497
QVT okex.com 1498
QSP okex.com 1499
QSP okex.com 1500
QSP okex.com 1501
BTM okex.com 1502
BTM okex.com 1503
ARK okex.com 1505
AST okex.com 1508
ARK okex.com 1506
ARK okex.com 1507
AST okex.com 1509
AST okex.com 1510
SUB okex.com 1511
BTM okex.com 1504
SUB okex.com 1512
SUB okex.com 1513
DNT okex.com 1514
DNT okex.com 1515
FUN okex.com 1517
DNT okex.com 1516
FUN okex.com 1518
FUN okex.com 1519
ELF okex.com 1520
ELF okex.com 1521
ELF okex.com 1522
TRX okex.com 1524
TRX okex.com 1523
TRX okex.com 1525
EVX okex.com 1526
EVX okex.com 1527
EVX okex.com 1528
MDA okex.com 1529
MDA okex.com 1530
MDA okex.com 1531
MTH okex.com 1532
MTH okex.com 1533
MTH okex.com 1534
MTL okex.com 1535
MTL okex.com 1536
MTL okex.com 1537
ACE okex.com 1538
XEM okex.com 1541
ACE okex.com 1540
ACE okex.com 1539
XEM okex.com 1542
XEM okex.com 1543
DGB okex.com 1544
DGB okex.com 1545
DGB okex.com 1546
PPT okex.com 1547
PPT okex.com 1548
PPT okex.com 1549
OAX okex.com 1551
OAX okex.com 1550
OAX okex.com 1552
REQ okex.com 1553
REQ okex.com 1554
REQ okex.com 1555
ENG okex.com 1556
ENG okex.com 1557
ICN okex.com 1559
ENG okex.com 1558
ICN okex.com 1560
ICN okex.com 1561
RCN okex.com 1562
RCN okex.com 1563
RCN okex.com 1564

11.29-17:00   12.29-17:00   CHANGE
BTC:9585	~	14515         50%
BCH:1574	~	2613          66%
ETH:471	    ~	720           53%
LTC:90	    ~	257           185%
XRP:0.25	~	1.15          360%
DASH:638	~	1095          72%
ETC:26	    ~	28            8%
EOS:4	    ~	8.3           100%
ZEC:309 	~	504           63%
OMG:8.3 	~	14.6          76%
QTUM:19	    ~	47            147%
'''

