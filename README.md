===============================
crawlit
===============================

Python web crawler with limitations.

* Free software: BSD license
* Documentation: http://crawlit.rtfd.org.

Installation
----

- `$ git clone https://github.com/kracekumar/crawlit.git`
- `$ cd crawlit`
- `$ sudo python setup.py install ` or `$ pip install -r requirements`

Usage:
-----

#### Crawl python.org

- `$ crawlit http://python.org`

New directory will be created and all html files will be dumped.

#### Crawl only 2000 page from python.org

- `$ crawlit http://python.org --count 2000`

Features
--------

- Single threaded
- Auto recovery of crawler
- Obeys Robots rule
- Crawls links from same domain
- Downloads only html files
- Uses `requests stream` option so headers are fetched and body is fetched when needed


TODO
----
- Add multiprocessing support for multi domain urls

