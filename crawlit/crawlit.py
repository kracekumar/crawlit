#!/usr/bin/env python
# -*- coding: utf-8 -*-

import reppy.cache
import tldextract
import requests
from BeautifulSoup import BeautifulSoup
from time import sleep
import datetime

import platform
import sys
import os
import logging
import json
import Queue
from urlparse import urlparse


#http://stackoverflow.com/questions/16506429/check-if-element-is-already-in-a-queue
class SetQueue(Queue.Queue):
    def _init(self, maxsize):
        self.queue = set()

    def _put(self, item):
        self.queue.add(item)

    def _get(self):
        return self.queue.pop()


def get_logger(name=u'crawlit'):
    logger = logging.getLogger(name)
    hdlr = logging.FileHandler(name + u'.log')
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    hdlr.setFormatter(formatter)
    logger.addHandler(hdlr)
    logger.setLevel(logging.INFO)
    return logger


MAJOR_VERSION, MINOR_VERSION, PATCH_VERSION = '0', '1', '0'

visited_urls = set([])

urls_to_visit = SetQueue()

sess = requests.Session()
count_to_stop = None
logger = get_logger()


def get_version():
    return u'.'.join([MAJOR_VERSION, MINOR_VERSION, PATCH_VERSION])


def default_user_agent(name="crawlit"):
    """Return a string representing the default user agent."""
    #https://github.com/kennethreitz/requests/blob/master/requests/utils.py#L440
    _implementation = platform.python_implementation()

    if _implementation == 'CPython':
        _implementation_version = platform.python_version()
    elif _implementation == 'PyPy':
        _implementation_version = '%s.%s.%s' % (sys.pypy_version_info.major,
                                                sys.pypy_version_info.minor,
                                                sys.pypy_version_info.micro)
        if sys.pypy_version_info.releaselevel != 'final':
            _implementation_version = ''.join([_implementation_version, sys.pypy_version_info.releaselevel])
    elif _implementation == 'Jython':
        _implementation_version = platform.python_version()  # Complete Guess
    elif _implementation == 'IronPython':
        _implementation_version = platform.python_version()  # Complete Guess
    else:
        _implementation_version = 'Unknown'

    try:
        p_system = platform.system()
        p_release = platform.release()
    except IOError:
        p_system = 'Unknown'
        p_release = 'Unknown'

    return u" ".join(['{0}/{1}'.format(name, get_version()),
                     '%s/%s' % (_implementation, _implementation_version),
                     '%s/%s' % (p_system, p_release)])


def fetch_robots_rules(url):
    robots = reppy.cache.RobotsCache()
    rules = robots.fetch(url)
    return rules


def is_same_domain(url1, url2):
    """Check seedurl and other url belongs to same domain.
    >>>is_same_domain("http://kracekumar.wordpress.com", "http://wordpress.com")
    True
    >>>is_same_domain("http://kracekumar.com", "http://tumblr.com")
    False
    """
    return tldextract.extract(url1).domain == tldextract.extract(url2).domain


def extract_links(data):
    """
    parse the page and extract all links in the data.
    Check whether all links belong to same domain and add them to queue if
    content-type is text/html.
    """
    soup = BeautifulSoup(data)
    for link in soup.findAll("a"):
        for pair in link.attrs:
            if pair[0] == u'href':
                yield pair[1]


def update_queue(url, links):
    """Add the extracted links to queue"""
    rules = fetch_robots_rules(url)
    for link in links:
        full_link = link
        # Relative url, so make it full url
        if link.startswith("/"):
            full_link = make_abs_url(url, link)

        # Check if url is already visited
        # Check if crawler is allowed to fetch
        # Allow only same domain request
        # filter same page url like #disqus_thread
        #print full_link, full_link in visited_urls
        if not full_link in visited_urls and rules.allowed(full_link, user_agent) and is_same_domain(url, full_link) and not full_link.count("#"):
            urls_to_visit.put_nowait(full_link)


def make_abs_url(seed_url, link):
    parsed_url = urlparse(seed_url)
    return parsed_url.scheme + "://" + parsed_url.netloc + link


def write_to_disk(url, data, dir_name, encoding="utf-8-sig"):
    try:
        # if not in right directory, change directory
        if not os.getcwdu().endswith(dir_name):
            os.chdir(dir_name)
        with open(url.replace("/", "_") + ".html", "w") as f:
            f.write(data)
    except OSError, e:
        logger.error(e)
        exit(1)


def crawl(url):
    """Crawl the page and extract links"""

    if not url in visited_urls:
        try:
            r = sess.get(url, headers={'User-Agent': user_agent}, stream=True)
            visited_urls.add(url)
            # Don't download non html files
            if r.headers['content-type'] == "text/html":
                print url, datetime.datetime.now()
                links = extract_links(r.text.encode("utf-8"))
                update_queue(url, links)
                return r.text.encode('utf-8', 'ignore')
        # what if url is email address
        except requests.exceptions.MissingSchema, e:
            pass
        except requests.ConnectionError, e:
            # Any requests exception, log and don't quit.
            logger.error(e)


def crawl_and_store(url, dir_name):
    data = crawl(url)
    if data:
        write_to_disk(url, data, dir_name)


user_agent = default_user_agent()


def main():
    global count_to_stop
    import argparse

    parser = argparse.ArgumentParser(
        version=get_version(),
        description='crawl a given url')
    parser.add_argument('urls', metavar='urls',
        type=unicode, nargs='*', help='seed url')
    parser.add_argument('--count', metavar='count',
        type=int, help='foo of the %(prog)s program')

    args = parser.parse_args()

    if len(args.urls) is 0:
        parser.print_usage()
        exit(1)

    # Focus only on one site for time being
    url = args.urls[0]
    count_to_stop = args.count
    total_pages_crawled = 0

    recovery_file = "crawlit_queue.json"
    # check if recovery_file exists and recover data
    try:
        if os.path.exists(recovery_file):
            with open(recovery_file) as f:
                data = json.load(f)
            if 'seedurl' in data and data['seedurl'] == url:
                if 'seedurl' in data:
                    for item in data['queue']:
                        urls_to_visit.put_nowait(item)
                if 'count' in data:
                    total_pages_crawled = data['count']
    except OSError, e:
        print(e)
        logger.error(e)
        exit(1)

    try:
        # Create a directory to store all html files
        dir_name = url.replace("/", "_")
        if not os.path.isdir(dir_name):
            try:
                # file, directory name cannot contain /
                os.mkdir(dir_name)
                os.chdir(dir_name)
            except OSError, e:
                print(e)
                logger.error(e)
                exit(1)

        crawl_and_store(url, dir_name=dir_name)
        total_pages_crawled += 1

        # Now create a gevent pool and start fetching url
        rules = fetch_robots_rules(url)
        delay = rules.delay(user_agent) or 0
        while not urls_to_visit.empty():
            start = datetime.datetime.now()
            crawl_and_store(urls_to_visit.get_nowait(), dir_name=dir_name)
            total_pages_crawled += 1
            diff = (datetime.datetime.now() - start).total_seconds() - delay
            print diff, urls_to_visit.qsize()
            if diff:
                sleep(delay)

            if total_pages_crawled >= count_to_stop:
                msg = u"Maximum crawl count ({0}) hit.".format(count_to_stop)
                logger.info(msg)
                print(msg)
                exit(1)

    except KeyboardInterrupt, e:
        # write all items to json file, so next time recover
        d = {'seedurl': url, 'queue': [], 'count': total_pages_crawled}
        os.chdir("..")
        while not urls_to_visit.empty():
            d['queue'].append(urls_to_visit.get_nowait().encode("utf-8"))
            try:
                with open(recovery_file, "w") as f:
                    json.dump(d, f)
                logger.info(u"Dumped data to recovery file: {0}".format(recovery_file))
            except OSError, e:
                logger.error(e)
        print(e)
        exit(1)

if __name__ == "__main__":
    main()
