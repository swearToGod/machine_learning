from __future__ import print_function
import urllib
import urllib2
import threading
import pickle
import time
import re
import os

def reporthook(blocknum, bs, size):
    per = 100.0 * blocknum * bs / size
    print('%.2f%% ' % per, end='')

class threadPool(object):
    workers = 16
    jobs = [None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None]
    def add(self, job):
        while True:
            for index in range(0, self.workers):
                if self.jobs[index] is None or not self.jobs[index].isAlive():
                    self.jobs[index] = job
                    job.start()
                    return
            time.sleep(0.5)
    def end(self):
        for job in self.jobs:
            job.join()

def dothing(indx):
    try:
        webpage = urllib2.urlopen('http://soft.anruan.com/%d' % indx).read()
    except Exception as e:
        return
    name = re.search('<h1 class="txt fl">(.*)</h1>', webpage)
    searchout = re.search('href="(.*\.apk)', webpage)
    if searchout == None or searchout.group(1) == None:
        return
    apkurl = searchout.group(1)
    signame = '%dw' % (indx / 10000) + '/' + '%d' % indx
    apkfilename = '%dw' % (indx / 10000) + '/' + apkurl.split('/')[-1]
    # print('%d %s %s' % (indx, name.group(1), apkfilename))
    if not os.path.exists(signame):
        print('%d %s %s' % (indx, name.group(1), apkfilename))
        urllib.urlretrieve(apkurl, apkfilename)
        os.system('D:\\WandouLabs\\aapt.exe d badging %s > %s' % (apkfilename, signame))
        # os.remove(apkfilename)

lock = threading.Lock()
pool = threadPool()	

for indx in range(0, 28000):
    # dothing(indx)
    pool.add(threading.Thread(target=dothing, args=(indx,)))
pool.end()
