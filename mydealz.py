#!/usr/bin/python

'''
The MIT License (MIT)
Copyright (c) 2015 Roy Freytag
Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:
The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
'''

import bs4 as bs
import datetime
import json
import re
import requests
import sys
import time
import urllib.parse
import urllib.request
from colorama import init, Fore, Back, Style
from pyshorteners import Shortener

# Basic stuff
init(autoreset=True) # Colorama
shortener = Shortener('Isgd')
page_number = 12
debug_mode = 0
short_url = 0
telegram = 0
tg_updateid = None

# Get settings from file
settings = {}
exec(open("./settings.txt").read(), None, settings)
if settings["debug_mode"]:
        debug_mode = 1
if settings["short_url"]:
        short_url = 1
if settings["telegram"]:
        telegram = 1
max_pages = settings["max_pages"]
sleep_time = settings["sleep_time"]
tg_token = settings["tg_token"]
tg_url = "https://api.telegram.org/bot{}/".format(tg_token)

# Get already found deals from file
found_deals = [line.rstrip('\n') for line in open ("./found.txt")]
print("Bereits gespeicherte Deals:", len(found_deals))

# Get wanted articles from file
wanted_articles = [line.rstrip('\n') for line in open ("./wanted.txt")]
print("Suche nach Deals für:", wanted_articles)
print("---------------")

# Debug mode
def debug(text):
        if debug_mode:
                print(Fore.YELLOW + "DEBUG: " + text)
        return 0

# Unix time handler
def gettime(unix):
        time = datetime.datetime.fromtimestamp(int(unix)).strftime('%Y-%m-%d %H:%M:%S')
        return time

# Telegram functions
# from: https://www.codementor.io/garethdwyer/building-a-telegram-bot-using-python-part-1-goi5fncay
def get_url(url):
        response = requests.get(url)
        content = response.content.decode("utf-8")
        return content

def get_json_from_url(url):
        content = get_url(url)
        js = json.loads(content)
        return js

def get_updates(offset=None):
        url = tg_url + "getUpdates?timeout=100"
        if offset:
            url += "&offset={}".format(offset)
        js = get_json_from_url(url)
        return js

def get_last_update_id(updates):
    update_ids = []
    for update in updates["result"]:
        update_ids.append(int(update["update_id"]))
    return max(update_ids)

def get_last_chat_id_and_text(updates):
        num_updates = len(updates["result"])
        last_update = num_updates - 1
        text = updates["result"][last_update]["message"]["text"]
        chat_id = updates["result"][last_update]["message"]["chat"]["id"]
        return (text, chat_id)

def send_message(text, chat_id):
        text = urllib.parse.quote_plus(text)
        url = tg_url + "sendMessage?text={}&chat_id={}&disable_web_page_preview=true".format(text, chat_id)
        get_url(url)

# Main
while True:
    # Check Telegram for commands
    #updates = get_updates(tg_updateid)
    #if len(updates["result"]) > 0:
    #        tg_updateid = get_last_update_id(updates) + 1

    # Scraper
    while page_number < max_pages+1:
            debug("Scraping page " + str(page_number))

            # Request settings
            site = "https://www.mydealz.de/deals-new?page="+str(page_number)
            header = {"user-agent": "Mozilla/5.0 (Windows NT 10.0; WOW64; rv:50.0) Gecko/20100101 Firefox/50.0"}
            request = urllib.request.Request(site, headers=header)
            src = urllib.request.urlopen(request).read()
            soup = bs.BeautifulSoup(src, 'lxml')
            #time.sleep(3)

            # Get listings
            listings = soup.find_all("article")
            if listings is None:
                    print("Keine Listings gefunden. Seite geändert?")

            for articles in listings:
                    for wanted_item in wanted_articles:
                            deals = articles.find_all("a", string=re.compile("(?i).*("+wanted_item+").*"), class_=re.compile("cept-tt linkPlain space--r-1 space--v-1"))
                            for thread in deals:
                                    # Check if this deal has been found before
                                    dealid = articles.attrs["id"]
                                    if dealid in found_deals:
                                            debug("Deal already found " + dealid)
                                            break

                                    # Get deal info
                                    title = thread.string
                                    timestamp = thread.parent.parent.parent.find(class_=re.compile("mute--text overflow--wrap-off space--h-2")).attrs['datetime']

                                    # Fetch and shorten URL
                                    link = thread.get("href")
                                    if short_url:
                                            proc_link = shortener.short(link)
                                    else:
                                            proc_link = link

                                    # Try to fetch price (may fail for freebies)
                                    try:
                                            pricestr = thread.parent.parent.parent.find(class_=re.compile("thread-price")).string.strip()
                                    except:
                                            pricestr = "0"

                                    # Replace Euro sign for processing
                                    if("€" in pricestr):
                                            price = float(pricestr.replace('€', '').replace('.', '').replace(',', '.'))
                                    else:
                                            price = 0

                                    print("[%s] %s für %s Euro: %s" % (gettime(timestamp), title.replace('€', ''), int(price), proc_link))
                                    if telegram:
                                            send_message(("%s (%s €): %s" % (title, int(price), proc_link)), 12345)

                                    # Save deal to prevent duplicate messaging
                                    with open("./found.txt", "a") as found:
                                            found.write(dealid + "\n")
            page_number += 1
            time.sleep(3)

    else:
            # Things to do after every cycle
            page_number = 1
            found_deals = [line.rstrip('\n') for line in open ("./found.txt")]
            time.sleep(sleep_time)

# Debug only
#with open('temp.txt', 'w') as file_:
#    file_.write(str(out2)) #encode("utf-8")
