from __future__ import print_function
import urllib
import urllib2
import threading
import pickle
import time
import re
import os
from bs4 import BeautifulSoup
import sys
reload(sys)
sys.setdefaultencoding('utf8')

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
    try:
        soup = BeautifulSoup(webpage)
        ul_c1 = BeautifulSoup(soup.select("ul.c1").__str__())
        ul_c2 = BeautifulSoup(soup.select("ul.c2").__str__())
        star = ul_c1.select("li > span > span > img")[0].get("alt")
        size = ul_c1.select("li > span")[3].next_sibling.__str__()
        downcount = ul_c1.select("li > span")[4].next_sibling.__str__()
        tags = ""
        for item in ul_c2.select("li.linktags > a"):
            tags = tags + item.text.decode("unicode_escape") + ";"
        lock.acquire()
        file.write("%05d, %s, %s, %s, %s, %s\n" % (indx, name.group(1), star, size, downcount, tags))
        file.flush()
        lock.release()
    except Exception as e:
        return
    print(indx, searchout.group(1))


lock = threading.Lock()
pool = threadPool()	
file = open("index2", "w")

for indx in range(0, 28000):
    # dothing(indx)
    pool.add(threading.Thread(target=dothing, args=(indx,)))
pool.end()

file.close()