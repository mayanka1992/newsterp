#! /usr/bin/python2.4
#
#

import time
import socket
import urllib2
import httplib
import threading
import workerPool
       
socket.setdefaulttimeout(30)


''' This module will query google through Mark\'s tunnel to find
web pages with rss feeds listed. The pages will then be downloaded
and potential rss feeds parsed out. '''

__author__ = "jhebert@cs.washington.edu (Jack Hebert)"


class AskGoogle:
    ''' For queries to run we need the proxy server running. Ask Jack about this. '''
    def __init__(self):
        # TODO: list of states, countries.
        self.queries=['news', 'local news', 'global news', 'international news',
                      'weather', 'business', 'tech', 'sports', 'fashion',
                      'Europe', 'Asia', 'US', 'cbs rss', 'abc', 'komo', 'kiro'
                      'times', 'financial', 'breaking news', 'popular news',
                      'most emailed news', 'newspaper', 'washington', 'seattle'
                      'northwest', 'australia', 'england', 'iraq', 'google',
                      'seattle', 'new york', 'times']

    def Run(self):
        links = []
        for query in self.queries:
            print 'Running query:', query
            for i in range(15):
                links += self.GetLinks(self.SendQuery(query+' rss', str(10*i)))
                print len(links), ' links.'
        print '\n'.join(links)
        print len(links), ' links.'
        return self.FilterLinks(links)

    def FilterLinks(self, links):
        toReturn = {}
        for link in links:
            toReturn[link] = None
        return toReturn.keys()

    def SendQuery(self, query, start):
        try:
            queryString = '/search?q=%(queryString)s&%(otherArgs)s' % (
                { 'queryString' : query.replace(' ', '+'),
                  'otherArgs' : 'start='+start+'&ie=utf-8&oe=utf-8',})
            hostname, port = 'localhost', 5001
            url = 'http://%(hostName)s:%(portNumber)s%(queryString)s' % (
                { 'hostName': hostname,
                  'portNumber' : port,
                  'queryString': queryString, })
            f=urllib2.urlopen(url)
            data=f.read()
            print 'Length received:', len(data)
            return data
        except:
            print "I think I was 404'ed"
        return ''

    def GetLinks(self, page):
        toReturn = []
        results = page.split('<R>')
        for result in results[1:]:
            start = result.find('<U>')
            end = result.find('</U>', start)
            toReturn.append(result[start+3:end])
        return toReturn


class FetchPool:
    def __init__(self, links, keepResults):
        self.results = []
        self.rssPages = []
        self.mutexLock = threading.Lock()
        self.keepResults = keepResults
        self.resultCount = 0
        self.numThreads = 20
        self.threadPool = workerPool.WorkerPool(self.numThreads)
        temp = {}
        for link in links:
            temp[link] = None
        self.urls = temp.keys()
        self.numToDo = len(self.urls)
        self.numDone = 0

    def GetUrl(self):
        toReturn = ''
        self.mutexLock.acquire()
        if(len(self.urls)>0):
            toReturn = self.urls[0]
            self.urls = self.urls[1:]
        self.mutexLock.release()
        return toReturn

    def AddLinkResults(self, links):
        self.mutexLock.acquire()
        if(self.keepResults):
            self.results += links
        self.resultCount += len(links)
        frac = str(self.numDone) + '/' + str(self.numToDo)
        percent = str(float(self.numDone) / (self.numToDo+1))
        print self.resultCount, ' results.', frac, percent, len(self.rssPages)
        self.numDone += 1
        self.mutexLock.release()

    def AddRssResult(self, link):
        self.mutexLock.acquire()
        self.rssPages.append(link)
        print len(self.results), ' results.', str(float(self.numDone) / (self.numToDo+1)), len(self.rssPages)
        f = open('rss.out','a')
        f.write(link)
        f.write('\n')
        f.close()
        self.mutexLock.release()

    def GetResults(self):
        self.mutexLock.acquire()
        toReturn = [self.results, self.rssPages]
        self.results, self.rssPages = [], []
        self.mutexLock.release()
        return toReturn

    def run(self):
        for i in range(self.numThreads):
            self.threadPool.startWorkerJob('!', PageFetcher(self))
        self.threadPool.stop()

    def wait(self):
        while(len(self.urls)>0):
            time.sleep(.5)
        time.sleep(2)


class PageFetcher:
    def __init__(self, pool):
        self.fetchPool = pool
        self.baseUrl = ''
        self.page = ''

    def run(self):
        while(True):
            results = []
            url = self.fetchPool.GetUrl()
            if(url==''):
                break
            try:
                self.FetchPage(url)
                if(self.IsRSS()):
                    self.fetchPool.AddRssResult(url)
                else:
                    results = self.ExtractLinks()
            except ValueError:
                print 'Could not fetch: ', url, ' ValueError.'
            except urllib2.URLError:
                print 'Could not fetch: ', url, ' URLError.'
            except:
                print 'Could not fetch: ', url, ' unknown error.'
            self.fetchPool.AddLinkResults(results)

    def FetchPage(self, urlToFetch):
        if(urlToFetch.find('http')==-1):
            urlToFetch = 'http://'+urlToFetch
        request = urllib2.Request(urlToFetch)
        request.add_header('User-Agent', 'NewsTerp - jhebert@cs.washington.edu')
        opener = urllib2.build_opener()
        self.page = opener.open(request).read() 
        self.baseUrl = urlToFetch

    def IsRSS(self):
        if(self.page.find('<rss version')>-1):
            return True
        elif(self.page.find('<?xml version')>-1):
            return True
        return False

    def ExtractLinks(self):
        toReturn = []
        links = self.page.split('<a href=')[1:]
        for link in links:
            try:
                if(len(link)==0):
                    continue
                if(link.find(' ')>-1):
                    link = link[:link.find(' ')]
                openChar = link[0]
                if((openChar=='"')|(openChar=="'")):
                    end = link.find(openChar, 2)
                else:
                    end = link.find('>')
                toAdd = link[1:end]
                if((toAdd.find('http')!=0)&(toAdd.find('www')!=0)):
                    if((toAdd[0]=='/')|(self.baseUrl[-1]=='/')):
                        toAdd = self.baseUrl + toAdd
                    else:
                        toAdd = self.baseUrl +'/' + toAdd
                toReturn.append(toAdd)
            except:
                pass
        return toReturn

    def GetPage(self):
        return self.page




def main():
    a = AskGoogle()
    links = a.Run()

    #links = ['http://www.google.com', 'www.nytimes.com', 'www.cs.washington.edu']
    f = FetchPool(links, True)
    f.run()
    f.wait()

    print '*****'
    time.sleep(2)
    links1, rss1 = f.GetResults()


    f2 = FetchPool(links1, False)
    f2.run()
    f2.wait()

    print '*****'
    time.sleep(10)
    
    extralinks1, extrarss1 = f.GetResults()
    links2, rss2 = f.GetResults()




main()
