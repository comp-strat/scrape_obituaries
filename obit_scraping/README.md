# Obituary profile scraper
The code in this directory scrapes all obituary profiles from a URL list file inputted by the user. 

## Instructions
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
