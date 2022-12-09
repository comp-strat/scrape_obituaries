# URL scraper
The code in url_scraper.py scrapes all obituary profile links between a given date range.  

## Instructions
Scrape urls from 1st January 2016 to 2nd January 2016.
```bash
python3 url_scraper.py -s 01/01/2016 -e 01/02/2016
```

## Output
The output is stored in this directory, in a folder named after the query date range. The .txt file itself is named using the timestamp that the script was run.
The general format is
```bash
{query_date_range}/urllist-{current_timestamp}.txt
yyyymmdd-yyyymmdd/urrlist-yyyymmdd-hhmm.txt
```
For example, if the command above was run on 16th March 2022 9:30PM, the output file will be located at
```bash
20160101-20160102/urllist-20220316-2130.txt
```
