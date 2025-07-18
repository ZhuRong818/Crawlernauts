#!/usr/bin/env python3

import sys
import time
import logging
import random
import argparse
import json
import csv
import re
import pickle
from pathlib import Path
from urllib.parse import urlparse, urljoin, urldefrag, quote, unquote, urlunparse
from urllib.robotparser import RobotFileParser
from collections import defaultdict
from queue import Queue, Empty
from threading import Thread, Lock, Event
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from bs4 import BeautifulSoup
from logging.handlers import RotatingFileHandler
import sqlite3

from prometheus_client import Counter, Gauge, start_http_server

DEFAULT_START_URLS = ["https://example.com"]
DEFAULT_MAX_PAGES    = 20
POLITENESS_DELAY     = 1.0
USER_AGENT           = "MyCrawlerBot/1.0 (+https://example.com/bot)"
TIMEOUT              = 10
PROXIES              = None
MAX_LINKS_PER_PAGE   = None
DB_PATH              = "data/crawler.db"
MAX_TEXT_LENGTH      = 10000
LOG_FILE             = "logs/crawler.log"
LOG_LEVEL            = "INFO"
MAX_LOG_BYTES        = 10 * 1024 * 1024
BACKUP_COUNT         = 5

pages_fetched = Counter('crawler_pages_fetched', 'Total pages successfully fetched')
pages_failed  = Counter('crawler_pages_failed',  'Total pages failed fetch')
queue_size    = Gauge('crawler_queue_size',    'Current queue size')
items_saved   = Counter('crawler_items_saved',  'Total items saved to storage')

# http headers
DEFAULT_HEADERS = {
    "User-Agent":  USER_AGENT,
    "Accept":   "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language":  "en-US,en;q=0.5",
}


def setup_logger(name, log_file=None, level=None, max_bytes=None, backup_count=None):
    level = level or LOG_LEVEL
    logger = logging.getLogger(name)
    logger.setLevel(level)
    if not logger.handlers:
        log_path = log_file or LOG_FILE
        Path(log_path).parent.mkdir(parents=True, exist_ok=True)
        handler = RotatingFileHandler(
            log_path,
            maxBytes=int(max_bytes or MAX_LOG_BYTES),
            backupCount=int(backup_count or BACKUP_COUNT)
        )
        fmt = '%(asctime)s %(levelname)s [%(name)s] %(message)s'
        handler.setFormatter(logging.Formatter(fmt, datefmt='%Y-%m-%d %H:%M:%S'))
        logger.addHandler(handler)
        console = logging.StreamHandler()
        console.setFormatter(handler.formatter)
        logger.addHandler(console)
    return logger

setup_logger(__name__)
logger = logging.getLogger(__name__)
DEFAULT_PORTS = {'http': '80', 'https': '443'}

def normalize_url(url):
    parsed  = urlparse(url)
    scheme  = parsed.scheme.lower()
    hostname= parsed.hostname.lower() if parsed.hostname else ''
    port    = f":{parsed.port}" if parsed.port and str(parsed.port) != DEFAULT_PORTS.get(scheme) else ''
    path    = quote(unquote(parsed.path or ''), safe="/%")
    query   = quote(unquote(parsed.query or ''), safe="=&?/%")
    return urlunparse((scheme, hostname + port, path, '', query, ''))

def is_valid_url(url):
    parsed = urlparse(url)
    return parsed.scheme in ("http", "https") and bool(parsed.netloc)

def get_domain(url):
    parsed = urlparse(url)
    return parsed.netloc.split('@')[-1]

session = requests.Session()
retries = Retry(
    total=3,
    backoff_factor=0.3,
    status_forcelist=[500,502,503,504],
    allowed_methods=["GET","HEAD"]
)
adapter = HTTPAdapter(max_retries=retries)
session.mount("http://", adapter)
session.mount("https://", adapter)
_robot_parsers = {}

def can_fetch(url):
    parsed = urlparse(url)
    base   = f"{parsed.scheme}://{parsed.netloc}"
    if base not in _robot_parsers:
        rp = RobotFileParser(); rp.set_url(f"{base}/robots.txt")
        try: rp.read()
        except Exception:
            logger.warning(f"Failed robots.txt for {base}")
            rp = None
        _robot_parsers[base] = rp
    rp = _robot_parsers.get(base)
    return True if rp is None else rp.can_fetch(USER_AGENT, url)

def fetch(url):
    if not can_fetch(url):
        logger.info(f"Blocked by robots.txt: {url}")
        pages_failed.inc()
        return None
    headers = DEFAULT_HEADERS.copy()
    proxies = {"http": random.choice(PROXIES), "https": random.choice(PROXIES)} if PROXIES else None
    try:
        resp = session.get(url, headers=headers, timeout=TIMEOUT, proxies=proxies)
        if resp.status_code == 200:
            pages_fetched.inc()
            time.sleep(random.uniform(0.1,0.5))
            return resp
        else:
            pages_failed.inc()
            return None
    except Exception:
        logger.exception(f"Fetching error: {url}")
        pages_failed.inc()
        return None

def parse(response, include_regex, exclude_regex):
    base = response.url
    soup = BeautifulSoup(response.text, 'lxml')
    links= set()
    for tag in soup.find_all('a', href=True):
        href = tag['href']
        abs_url,_ = urldefrag(urljoin(base, href))
        if include_regex and not any(r.search(abs_url) for r in include_regex): continue
        if exclude_regex and any(r.search(abs_url) for r in exclude_regex): continue
        links.add(abs_url)
        if MAX_LINKS_PER_PAGE and len(links)>=MAX_LINKS_PER_PAGE: break

    title = soup.title.string.strip() if soup.title else ''
    desc  = ''
    meta  = soup.find('meta', attrs={'name':'description'})
    if meta and meta.get('content'): desc = meta['content'].strip()

    og      = {tag.get('property'):tag['content']
               for tag in soup.find_all('meta', property=True)
               if tag.get('property','').startswith('og:') and tag.get('content')}
    twitter = {tag.get('name'):tag['content']
               for tag in soup.find_all('meta', attrs={'name':True})
               if tag.get('name','').startswith('twitter:') and tag.get('content')}

    jsonld=[]
    for script in soup.find_all('script', type='application/ld+json'):
        if not script.string: continue
        try: jsonld.append(json.loads(script.string))
        except json.JSONDecodeError: pass

    text = soup.get_text(separator=' ', strip=True)
    item = {
        'url': base,
        'title': title,
        'description': desc,
        'og': og,
        'twitter': twitter,
        'jsonld': jsonld,
        'text': text,
        'html': response.text
    }
    return links, [item]

class Storage:
    def __init__(self, db_path=DB_PATH):
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.conn   = sqlite3.connect(db_path, check_same_thread=False)
        self.db_lock= Lock()
        self._create()

    def _create(self):
        self.conn.execute('''CREATE TABLE IF NOT EXISTS items(
            url TEXT PRIMARY KEY,
            title TEXT,
            description TEXT,
            og TEXT,
            twitter TEXT,
            jsonld TEXT,
            text TEXT,
            html TEXT
        )''')
        existing = [col[1] for col in self.conn.execute("PRAGMA table_info(items)")]
        for col in ('og','twitter','jsonld'):
            if col not in existing:
                try: self.conn.execute(f"ALTER TABLE items ADD COLUMN {col} TEXT")
                except: logger.warning(f"Could not add column {col}")
        self.conn.commit()

    def save(self, item):
        text = (item.get('text') or '')[:MAX_TEXT_LENGTH]
        sql = '''INSERT INTO items(url,title,description,og,twitter,jsonld,text,html)
                 VALUES(?,?,?,?,?,?,?,?)
                 ON CONFLICT(url) DO UPDATE SET
                   title=excluded.title,
                   description=excluded.description,
                   og=excluded.og,
                   twitter=excluded.twitter,
                   jsonld=excluded.jsonld,
                   text=excluded.text,
                   html=excluded.html;'''
        data = (
            item['url'],
            item['title'],
            item['description'],
            json.dumps(item['og'],      ensure_ascii=False),
            json.dumps(item['twitter'], ensure_ascii=False),
            json.dumps(item['jsonld'],  ensure_ascii=False),
            text,
            item['html']
        )
        try:
            with self.db_lock:
                self.conn.execute(sql, data)
                self.conn.commit()
            items_saved.inc()
        except:
            logger.exception(f"Save failed: {item['url']}")


def run_crawler(url: str, mode: str, value):

    try:
        if mode in ('css', 'tag', 'text', 'image'):
            response = requests.get(url, headers=DEFAULT_HEADERS, timeout=TIMEOUT)
            if response.status_code != 200:
                raise Exception(f"Failed to fetch URL (status {response.status_code})")
            soup = BeautifulSoup(response.text, 'lxml')
        if mode == 'text':
            # Get the first paragraph directly under <body>
            first_para = soup.select_one('body > p')
            text_content = first_para.get_text(strip=True) if first_para else ''
            return [ { 'Text': text_content } ]
        elif mode == 'image':
            os.makedirs(img_dir, exist_ok=True)
            images = soup.find_all('img')
            base_dir = os.path.abspath(os.path.dirname(__file__))
            img_dir = os.path.join(base_dir, "..", "frontend", "build", "static", "images")

            results = []
            for img in images:
                src = img.get('src')
                if not src:
                    continue
                img_url = urljoin(url, src)
                try:
                    img_resp = requests.get(img_url, timeout=TIMEOUT)
                    if img_resp.status_code == 200:
                        # determine a save filename
                        ext = ""
                        if '.' in img_url.split('/')[-1]:
                            ext = '.' + img_url.split('/')[-1].split('.')[-1][:5]
                        elif 'image/' in img_resp.headers.get('Content-Type', ''):

                            ext = '.' + img_resp.headers['Content-Type'].split('/')[-1]
                        filename = f"{uuid.uuid4().hex}{ext}"
                        file_path = os.path.join(img_dir, filename)
                        with open(file_path, 'wb') as f:
                            f.write(img_resp.content)
                        results.append({
                            'Image URL': img_url,
                            'Saved File': f"/static/images/{filename}"
                        })
                except Exception as e:
                    logging.exception(f"Image download failed for {img_url}: {e}")
            return results
        elif mode == 'tag':

            elements = soup.find_all(value)
            return [ { 'Content': el.get_text(strip=True) } for el in elements ]
        elif mode == 'css':

            elements = soup.select(value)
            return [ { 'Content': el.get_text(strip=True) } for el in elements ]
        elif mode == 'max_pages':

            max_pages = int(value) if value is not None else DEFAULT_MAX_PAGES
            storage = Storage(db_path=DB_PATH)
            sched = Scheduler(
                start_urls=[url],
                max_pages=max_pages,
                workers=1,
                resume_file="crawler_resume.pkl",
                include_patterns=[],
                exclude_patterns=[]
            )
            sched.run(storage, metrics_port=None)
            rows = storage.conn.execute(
                'SELECT url, title, description FROM items'
            ).fetchall()
            return [ {'url': r[0], 'title': r[1], 'description': r[2]} for r in rows ]
        else:

            raise ValueError(f"Unsupported crawl mode: {mode}")
    except Exception as e:
        logger.exception("run_crawler failed")
        raise

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Enhanced web crawler")
    parser.add_argument('--start-urls',    nargs='+', default=None)
    parser.add_argument('--max-pages',     type=int, default=None)
    parser.add_argument('--workers',       type=int, default=5)
    parser.add_argument('--resume-file',   default='crawler_resume.pkl')
    parser.add_argument('--include-pattern', action='append', default=[])
    parser.add_argument('--exclude-pattern', action='append', default=[])
    parser.add_argument('--metrics-port',  type=int, default=None)
    parser.add_argument('--output',  help='Output file', default=None)
    parser.add_argument('--format', choices=['jsonl','csv'], default='jsonl')
    args = parser.parse_args()

    start_urls = args.start_urls or DEFAULT_START_URLS
    max_pages  = args.max_pages  or DEFAULT_MAX_PAGES

    storage = Storage()
    sched= Scheduler(
        start_urls,
        max_pages,
        args.workers,
        args.resume_file,
        args.include_pattern,
        args.exclude_pattern


    )
    sched.run(storage, args.metrics_port)