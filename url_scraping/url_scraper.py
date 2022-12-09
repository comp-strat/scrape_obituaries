import json
import requests
import re
import sys,getopt

from bs4 import BeautifulSoup
from datetime import datetime
import os
from os.path import dirname, abspath

##Get all urls from one page
def get_page_url(page_num, start_date, end_date):
    page_urls = []
    # Headers that legacy likes
    headers = {
        'authority': 'www.legacy.com',
        'accept': 'text/javascript, application/javascript, application/ecmascript, application/x-ecmascript, */*; q=0.01',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.102 Safari/537.36',
        'x-requested-with': 'XMLHttpRequest',
        'sec-gpc': '1',
        'sec-fetch-site': 'same-origin',
        'sec-fetch-mode': 'cors',
        'sec-fetch-dest': 'empty',
        'referer': 'https://www.legacy.com/obituaries/legacy/obituary-search.aspx?daterange=88888&startdate=20160101&enddate=20170101&countryid=1&stateid=10&affiliateid=all&entriesperpage=30',
        'accept-language': 'en-US,en;q=0.9',
        'cookie': 'LegacySearchExpanded=1',
    }

    # Parameter object to get the right set of links
    params = (
        ('affiliateid', '0'),
        ('countryid', '1'),
        ('daterange', '88888'),
        ('stateid', '10'),
        ('townname', ''),
        ('keyword', ''),
        ('startdate', start_date),
        ('enddate', end_date),
        ('entriesperpage', '30'),
        ('page', str(page_num)),
        ('previousDateType', '0'),
        ('position', 'undefined'),
        ('callback', 'jQuery224070609234720949_1645213491331'),
        ('_', '1645213491332'),
    )

    # Making initial request
    response = requests.get('https://www.legacy.com/obituaries/legacy/api/obituarysearch', headers=headers, params=params)
    # Getting the json object from the weird jquery callback
    m = re.search('(\{.+\})', response.text)
    parsedJson = json.loads(m.group(0))

    # Grabbin' the obituary URL from the json object
    for entry in parsedJson['Entries']:
        # print('url: ', entry['obitlink'])
        page_urls.append(entry['obitlink'])
    
    # Checking how many pages are left to parse
    pages_remaining = parsedJson['NumPageRemaining']
    return page_urls, pages_remaining

## Get all urls between start and end dates
def get_all_urls(start_date, end_date):

    all_urls = []
    urls, pages_remaining = get_page_url(1, start_date, end_date)
    print(start_date)
    print(end_date)
    print()
    ''' 
    If the request has more than 100 pages of URLs, Legacy's API shits itself and gives us overflow obituaries from weird dates
    To deal with this we divide up the date range into small enough quantities (recursively) to not have more than 100 pages being asked for at a time
    '''
    if (pages_remaining >= 100):
        start = datetime.strptime(start_date, "%Y%m%d").date()
        end = datetime.strptime(end_date, "%Y%m%d").date()
        mid = start + (end - start)/2
        all_urls = get_all_urls(start_date, mid.strftime("%Y%m%d")) + get_all_urls(mid.strftime("%Y%m%d"), end_date)
    
    else:
        page_num = 1
        while(pages_remaining > 0):
            urls, pages_remaining = get_page_url(page_num, start_date, end_date)
            all_urls.extend(urls)
            print('pages remaining: ', pages_remaining)
            page_num += 1

    return all_urls

# Just command line argument setup and stuff
def main(argv):
    start_date = "20160101"
    end_date = "20160102"
    try:
        opts, args = getopt.getopt(argv,"hds:e:",["start_date=","end_date="])
    except getopt.GetoptError:
        print('url_scraper.py -s <start date as mm/dd/yyyy> -e <end date as mm/dd/yyyy>')
        print('url_scraper.py -d for using 1/1/2016 to 1/2/2016')
    for opt, arg in opts:
        if opt == '-h':
            print('url_scraper.py -s <start date as mm/dd/yyyy> -e <end date as mm/dd/yyyy>')
            print('url_scraper.py -d for using 1/1/2016 to 1/2/2016')
            sys.exit()
        elif opt in ("-s", "--start_date"):
            arg_arr = arg.split('/')
            start_date = arg_arr[2]+arg_arr[0]+arg_arr[1]
        elif opt in ("-e", "--end_date"):
            arg_arr = arg.split('/')
            end_date = arg_arr[2]+arg_arr[0]+arg_arr[1]

    urls = get_all_urls(start_date,end_date)
    # Taking out some urls that we know will be unreadable
    filtered_urls = filter(lambda u: (not "ls000" in u) and (not "getnamefromnoticetext" in u), urls)

    ## Direct output to the correct folder
    path_to_result_file = f"{start_date}-{end_date}/" ## 'url_scraping/yyyymmdd-yyyymmdd' (query date range folder)
    result_filename = 'urllist-' + datetime.now().strftime("%Y%m%d-%H%M") + '.txt' ## 'urllist-yyyymmdd-hhmm.txt' (current timestamp file)
    path_to_result_file = path_to_result_file + result_filename
    os.makedirs(dirname(path_to_result_file), exist_ok=True) ## Create folder if it doesn't already exist

    f = open(path_to_result_file, "w")
    for i in filtered_urls:
        f.write(i+"\n")
    f.close()

def scrape_to_file(start_date, end_date, outfile):
    urls = get_all_urls(start_date,end_date)
    # Taking out some urls that we know will be unreadable
    filtered_urls = filter(lambda u: (not "ls000" in u) and (not "getnamefromnoticetext" in u), urls)
    os.makedirs(dirname('url_scraping/scheduled_scrapes'), exist_ok=True)
    f = open(f'url_scraping/scheduled_scrapes/urllist-{outfile}.txt', "w+")
    for i in filtered_urls:
        f.write(i+"\n")
    f.close()


if __name__ == "__main__":
    main(sys.argv[1:])
