# Instructions for running scripts

The general work flow is to run scripts in the following order:

1. [URL scraping](https://github.com/comp-strat/scrape_obituaries/blob/main/url_scraping/url_scraper.py)
2. [Obit scraping](https://github.com/comp-strat/scrape_obituaries/blob/main/obit_scraping/grabObitLinks.py)
3. [Postprocessing](https://github.com/comp-strat/scrape_obituaries/blob/main/postprocessing/processor.py)


### 1. URL scraping

The code in [url_scraper.py](https://github.com/comp-strat/scrape_obituaries/blob/main/url_scraping/url_scraper.py) scrapes all obituary profile links between a given date range.  

#### Instructions

Give the desired start date and end date as arguments while running the script. If we want to scrape urls from 1st January 2016 to 2nd January 2016, we will use the following command on command line.  

```command line
python3 url_scraper.py -s 01/01/2016 -e 01/02/2016
```

If you get blocked by Legacy.com, it typically results in a `json.decoder.JSONDecodeError` error and looks like this:
```bash
Traceback (most recent call last):
  File "url_scraper.py", line 138, in <module>
    main(sys.argv[1:])
  File "url_scraper.py", line 111, in main
    urls = get_all_urls(start_date,end_date)
  File "url_scraper.py", line 66, in get_all_urls
    urls, pages_remaining = get_page_url(1, start_date, end_date)
  File "url_scraper.py", line 51, in get_page_url
    parsedJson = json.loads(m.group(0))
  File "/usr/lib/python3.8/json/__init__.py", line 357, in loads
    return _default_decoder.decode(s)
  File "/usr/lib/python3.8/json/decoder.py", line 337, in decode
    obj, end = self.raw_decode(s, idx=_w(s, 0).end())
  File "/usr/lib/python3.8/json/decoder.py", line 353, in raw_decode
    obj, end = self.scan_once(s, idx)
json.decoder.JSONDecodeError: Expecting property name enclosed in double quotes: line 1 column 2 (char 1)
```

If this happens, consider inserting pauses into [the URL scraping script](https://github.com/comp-strat/scrape_obituaries/blob/main/url_scraping/url_scraper.py)--like inside the `while()` loop within the `get_all_urls()` function.


#### Output

The output is stored in the [url_scraping](https://github.com/comp-strat/scrape_obituaries/tree/main/url_scraping) directory, in a folder named after the query date range. The .txt file itself is named using the timestamp that the script was run.
The general format is

```command line
{query_date_range}/urllist-{current_timestamp}.txt
yyyymmdd-yyyymmdd/urrlist-yyyymmdd-hhmm.txt
```

For example, if the command above was run on 16th March 2022 9:30PM, the output file will be located at

```command line
20160101-20160102/urllist-20220316-2130.txt
```


### 2. Obituary scraping

The code in [obit_scraping](https://github.com/comp-strat/scrape_obituaries/tree/main/obit_scraping) directory scrapes all obituary profiles from a URL list file inputted by the user. 

#### Instructions

First, provide directions for obituary scraping by editing `obits_config.json`, a config file in this form:
```json
{
	"ip": "149.165.171.143", // ip address of the VM to send obits to
	"user": "rmathur", // your username on the VM
	"ssh_path": "/home/rohan/.ssh/id_ed25519", // path to ssh key to get into vm
	"obits_dest_dir": "/mnt/ceph/obits_storage", // where you want all the obituaries to end up
	"scrape_id": "20150101-20150102_20221023-1632", // This is the id of the scrape job. This is also the name of the urllist file in the form of yyyymmdd{start}-yyyymmdd{end}_yyyymmdd-hhmm{url scrape timestamp}
	"batch_size": 30, // how many obituaries you want per file
	"start_batch": 0 // which batch to start on (useful for when a job fails and you don't wanna start from scratch
}
```
The obituary photos will show up in `[obits_dest_dir]/[scrape_id]/[scrape_id]_[batch_num]/[filename].png`, and \
The obituary json will show up in `[obits_dest_dir]/[scrape_id]/[scrape_id]_obits/obits_[batch_num].json`.

After editing the config as you like, just run:
```bash
python3 grab_obits.py
```
A backup of all obituary files and photos will be made in the remote folder indicated in the config file.

## Output
The output is stored in the all_results folder, in a sub-folder named after the query date range. The .json file itself is named with the timestamp indicating when the script was run. 
The general format is 
```bash
{query_date_range}/obits-{current_timestamp}.json
yyyymmdd-yyyymmdd/obits-yyyymmdd-hhmm.json
```

For example, a file with obituaries content between 1st January 2016 and 2nd January 2016, queried on March 16th 2022 10:30PM.
```bash
20160101-20160102/obits-20220316-2230.json
```

This file format is largely the same for the scraped URL files, which are in the form: 
```bash
yyyymmdd{start}-yyyymmdd{end}_yyyymmdd-hhmm{url scrape timestamp}
```

#### Notes on speed and getting blocked

If you get blocked by Legacy.com, it typically results in a `UnicodeDecodeError` that looks like this:
```bash
Traceback (most recent call last):
  File "/usr/lib/python3.10/threading.py", line 1009, in _bootstrap_inner
    self.run()
  File "/media/volume/sdb/obits_venv/lib/python3.10/site-packages/request_boost/__init__.py", line 99, in run
    decoded_data = data.decode(encoding)
UnicodeDecodeError: 'utf-8' codec can't decode byte 0xe2 in position 33952: invalid continuation byte
```

This means you probably weren't being very polite to their servers. To prevent this, the default version of [the request script](obit_scraping/grab_batch.py) uses [the `requests` module](https://pypi.org/project/requests/) with short, random pauses (around 0.5 seconds) between HTML requests to avoid getting blocked by Legacy.com. This is pretty slow. But if you got blocked anyway, consider making the pause longer; the upper and lower bounds are set when `request_slow()` is defined. 

If speed is what you're after, the above workflow can be parallelized with [`request_boost`](https://pypi.org/project/request-boost/). However, we haven't implemented that in this version just yet, though there is a parameter for this called `boosted` under the `ObitConfig` class of [`grab_batch.py`](obit_scraping/grab_batch.py). Using this boosted version would be much faster at runtime, but the ability to run this without getting blocked would require [proper proxy protection](https://free-proxy-list.net/). We haven't figured this out yet, but you're welcome to try implementing it--just note that your IP address might get blocked.


### 3. Postprocessing

The code in [postprocessing](postprocessing/) reads raw scraped data and outputs a processed dataset with location, funeral home, birth/death date, gender, ethnicity, and duplicate information. 

#### Instructions

Our main file is `processor.py`, which runs the postprocessing and duplicate identification workflow. Our main file is `processor.py`, which runs the post-processing and duplicate identification workflow. 

**IMPORTANT: Run `processor.py` under the top-level `scrape_obituaries/` directory. **

The script assumes batched scraped data is already stored under `/mnt/ceph/obit_storage`.

For example, if we want to post-process scraped data from January 1st, 2015 to January 2nd, 2015 (20150101-20150102), queried on October 23rd, 2022 16:32 (20221023-1632), with runname 'test', then we would run the following command in the terminal under the `scrape_obituaries/` directory: 
```bash
python3 postprocessing/processor.py 20150101-20150102 20221023-1632 test
```

## Output
`processor.py` outputs the following files in [the `postprocessing` directory](postprocessing/):

TWO final files
1. Merged dataset with gender, location, race and date information ```{runname}-final_df-{year}.csv```
2. Same dataset as above, but with duplicate information ```{runname}-final_df_duplicates_identified-{year}.csv```

Intermediate files (per batch) - AUTOMATICALLY DELETED after final files are successfully written
1. Dataset with inferred gender ```{runname}-guess_gender-{year}.csv```
2. Dataset with location information ```{runname}-{location_parser}_location_finder-{year}.csv```
3. Dataset with inferred race ```{runname}-run_race-{year}.csv```
4. Dataset with inferred dates ```{runname}-run_dates-{year}.csv```

For example, assuming that we made the same ```postprocess_synchronous(...)``` function call as above, the outputs in the obituaries directory will be: 

```bash
test-final_df-2015.csv
test-final_df_duplicates_identified-2015.csv
```

#### Future improvements?

The postprocessing workflow might be the slowest part of the workflow, because it takes a lot of time to load NLP models--and if you're using "hardcore" location parsing, each entry takes about 1 extra second. This adds up. Coders of Future Times should consider parallelizing the postprocessing workflow, since the most time-consuming steps are completely independent.
