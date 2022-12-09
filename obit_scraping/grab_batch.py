import json
from bs4 import BeautifulSoup
from tqdm import tqdm
import requests
import os
import re
import time
import random
import multiprocessing as mp

# Photo processing
import io
import hashlib
from PIL import Image, UnidentifiedImageError

class ObitObject:
	def __init__(self):
		self.name = None
		self.location = None
		self.birthdate = None
		self.deathdate = None
		self.pubdate = None
		self.url = None
		self.para = None
		self.funeral_home_name = None
		self.funeral_home_address = None
		self.site_published = None
		self.newspaper = None
		self.photo_link = None
		self.photo_file = None

	def to_obj(self):
		serialize = lambda s: "" if s is None else s
		obit = {
			"name": serialize(self.name),
			"location": serialize(self.location),
			"birthdate": serialize(self.birthdate),
			"deathdate": serialize(self.deathdate),
			"pubdate": serialize(self.pubdate),
			"url": serialize(self.url),
			"para": serialize(self.para),
			"funeral_home_name": serialize(self.funeral_home_name),
			"funeral_home_address": serialize(self.funeral_home_address),
			"site_published": serialize(self.site_published),
			"newspaper": serialize(self.newspaper),
			"photo_link": serialize(self.photo_link),
			"photo_file": serialize(self.photo_file)
		}
		return obit

## Get birth/death dates and location for one profile
## Args: Format is either 'wt', 'tr' or 'dm', representing Legacy.com, Tributes.com and DignityMemorial
def get_obit_loc_and_date(soup, format, page_url, all_info):
	'''
	Returns an object with any location or date data that can be easily scraped from the soup.

	Parameters:
		soup:   (BeautifulSoup): BeautifulSoup object containing the souped response data.
		format:        (string): Format is either 'wt', 'tr' or 'dm', representing Legacy.com, Tributes.com and DignityMemorial

	Returns:
		loc_and_date_obj: (object): Object with just location and date info, contains empty entries if unparasable
	'''
	loc_and_date_obj = {
		"location": "",
		"birthdate": "",
		"deathdate": "",
		"pubdate": "",
		"url": page_url
	}

	## Get location & date from legacy.com website
	if (format == "wt"):
		## Get location
		at_vals = soup.find_all("div", {"data-component": "AttributeValueText"})
		prog = re.compile("^[A-Z].+, ([A-Z]{2})")
		if at_vals != None:
			for text in at_vals:
				check_match = prog.search(text.text)
				if check_match:
					loc_and_date_obj["location"] = check_match.group(0)
		## Get publish date
		publish_date = soup.find_all("div", {"data-component": "ObituaryEndorsementText"})
		prog = re.compile("([A-Za-z]+\.? [0-9]+, [0-9]{4})")
		if publish_date != None:
			for text in publish_date:
				check_match = prog.search(text.text)
				if check_match:
					loc_and_date_obj["pubdate"] = check_match.group(1)
		## Get birth and death dates
		birth_death_date = soup.find("div", {"data-component":"LifespanText"})
		birth_death_date = birth_death_date.text if birth_death_date else ' - '
		if (birth_death_date):
			loc_and_date_obj["birthdate"] = birth_death_date.split(' - ')[0]
			loc_and_date_obj["deathdate"] = birth_death_date.split(' - ')[1]

	## Get location & date from Tributes.com website
	elif (format == "tr"):
		loc = soup.find("span", {"itemprop": "address"})
		loc_and_date_obj["location"] = '' if loc is None else loc.text
		birth_date = soup.find("meta", {"itemprop":"birthDate"})
		birth_date = '' if birth_date is None else birth_date['content']
		death_date = soup.find("meta", {"itemprop":"deathDate"})
		death_date = '' if death_date is None else death_date['content']
		loc_and_date_obj["birthdate"] = birth_date ## Format: yyyy/mm//dd
		loc_and_date_obj["deathdate"] = death_date
	## Get location & date from Dignity Memorial website
	elif (format == "dm"):
		birth_date = soup.find("span", {"itemprop": "birthDate"})
		birth_date = '' if birth_date is None else birth_date.text
		death_date = soup.find("span", {"itemprop": "deathDate"})
		death_date = '' if death_date is None else death_date.text
		loc_and_date_obj["birthdate"] = birth_date ##Format 'Month Day, Year
		loc_and_date_obj["deathdate"] = death_date
	else:
		print("Invalid format- check get_obit_loc_and_date")

	all_info.location = loc_and_date_obj["location"]
	all_info.birthdate = loc_and_date_obj["birthdate"]
	all_info.deathdate = loc_and_date_obj["deathdate"]
	all_info.pubdate = loc_and_date_obj["pubdate"]
	return all_info


## Save the obituary profile photo in the results folder (where scraped obits are saved)
def save_image_from_url(url, photo_config):
	'''
	Parameters:
	   url (str): website link to the obituary profile picture

	Returns:
		filename (str): the .png file name of the saved image.
	'''
	if url == '':
		return ''
	response = requests.get(url, headers={"User-agent": "Mozilla/5.0"})
	image_content = response.content
	image_file = io.BytesIO(image_content)
	image = Image.open(image_file).convert("RGB")

	filename = hashlib.sha1(image_content).hexdigest()[:10] + ".png"


	photo_dirname = photo_config["photo_dirname"]

	image.save(photo_dirname + "_"+ filename, "PNG", quality=80)
	if photo_config["send_photos"]:
		conf = photo_config
		send_cmd = f"sudo scp -i {conf['ssh_path']} {photo_dirname}_{filename} {conf['user']}@{conf['ip']}:{conf['dest_dir']}"
		os.system(send_cmd)

	return filename

def construct_obit_obj(raw_obit, photo_config):
	all_info = ObitObject()
	soup = BeautifulSoup(raw_obit[0], 'html.parser')

	page_url = raw_obit[1]
	all_info.url = page_url
	obit_object_wt = soup.find("div", "data-component"=="ObituaryParagraph") #legacy.com
	if page_url.find("legacy.com") == -1:
		obit_object_wt = None
	obit_object_tr = soup.find("div", {"id": "obit_text_page_1"}) #tributes.com
	if page_url.find("tributes.com") == -1:
		obit_object_tr = None
	obit_object_dm = soup.find("h2", {"class": "text-center mt-30"}) #Dignity Memorial

	## Parser for legacy.com
	if (obit_object_wt is not None): 
		name = soup.find("h2", {"data-component": "NameHeadingText"})
		newspaper = soup.find("div", {"data-component":"ObituaryEndorsementText"})

		all_info = get_obit_loc_and_date(soup, "wt", page_url, all_info) # Gets obit object with location and date

		all_h3s = obit_object_wt.findAll('h3', recursive=True)
		all_head_texts = obit_object_wt.findAll("div", {"class": "Box-sc-ucqo0b-0 Text-sc-8i5r1a-0 fNnNbH gacyGL"})
		# all_info["funeral_home_name"] = ""
		# all_info["funeral_home_address"] = ""
		para_counter = 0
		for i in all_h3s:
			if i.text == "BORN":
				all_info.birthdate = all_head_texts[para_counter].text
				para_counter += 1
			elif i.text == "DIED":
				all_info.deathdate = all_head_texts[para_counter].text
				para_counter += 1
			elif i.text == "FUNERAL HOME":
				all_info.funeral_home_name = all_head_texts[para_counter].text
				# The funeral home name takes up 3 lines for address and stuff
				all_info.funeral_home_address = "|".join([all_head_texts[j].text for j in range(para_counter+1, para_counter+3)])
				para_counter += 3
			elif i.text == "UPCOMING SERVICE":
				para_counter += 4

		para_text = soup.findAll("p", attrs={"data-component": "ObituaryParagraph"})
		all_info.para = '' if len(para_text) == 0 else para_text[0].text # Add obit paragraph 
		all_info.site_published = "legacy" # Add site published 
		all_info.name = '' if name is None else name.text

		## regex here to get only newspaper name
		newspaper = 'NOTFOUND' if newspaper is None else newspaper.text
		just_newspaper_name = re.search(r'Published by (.*?) (on|from)', newspaper)
		all_info.newspaper = '' if just_newspaper_name is None else just_newspaper_name.group(1)
		
		photo_link = soup.find("img", {"data-component": "ObitImage"})
		all_info.photo_link = '' if photo_link is None else photo_link['src']
		try:
			all_info.photo_file = save_image_from_url(all_info.photo_link, photo_config)
		except UnidentifiedImageError as e:
			print(f"Failed to identify file at {all_info.photo_link} due to {e}")

		return all_info
	## Parser for tributes.com
	elif (obit_object_tr is not None):
		text = [p.text for p in obit_object_tr.find_all("p")]
		text = " ".join(text)
		name = soup.find("span", {"itemprop": "name"})
		
		all_info = get_obit_loc_and_date(soup, "tr", page_url, all_info)
		all_info.para = text
		all_info.site_published = "tributes"
		all_info.name = '' if name is None else name.text
		all_info.newspaper = ''

		funeral_class = soup.find("div", {"class": "funeralhome-section"})
		all_info.funeral_home_address = ""
		all_info.funeral_home_address = ""
		if funeral_class is not None:
			funeral_things = []
			for s in funeral_class.findChildren("span", recursive=True):
				funeral_things += re.findall(r'([A-Za-z0-9].+)(?:\\r)?', s.text)
			all_info.funeral_home_name = funeral_things.pop(0)
			all_info.funeral_home_address = ""
			for i in funeral_things:
				if i != "Email Us":
					all_info.funeral_home_address += i.replace('\r', '') + "|"
		return all_info
	## Parser for Dignity Memorial
	# elif (obit_object_dm is not None):
	#     text = obit_object_dm.text
	#     more_text_obj = soup.find("div", {"class": "content short-bio text-left"})
	#     more_text = '' if more_text_obj is None else [p.text for p in  more_text_obj.find_all("p")]
	#     text = text + " ".join(more_text)
	#     name = soup.find("h1", {"id": "obit-name"})
		
	#     all_info = get_obit_loc_and_date(soup, "dm", page_url)
	#     all_info["para"] = text
	#     all_info["site_published"] = "dignity"
	#     all_info["name"] = '' if name is None else name.text
	#     all_info['newspaper'] = ''
	#     if not "funeral_home_name" in all_info:
	#         all_info["funeral_home_name"] = ""
	#         all_info["funeral_home_address"] = ""
	#     return all_info
	## Other websites that we can't parse for now
	else:
		print(soup.url, 'NOT ACCESSED')
		return None

class ObitConfig:
	def __init__(self):
		self.low_memory = False # Whether to use low memory mode
		self.boosted = False # Whether to use requests boost
		self.send_photos = True # Whether to send photos to vm
		self.photo_config = None # Contains necessary info to send photos to vm
		self.print_progress = True # Whether to print out progress bar
		self.save_raw = False # Whether to save raw html

		self.id = "test" # ID to identify batch

# Headers that work for scraping Legacy.com
obit_headers = {
	'authority': 'www.legacy.com',
	'upgrade-insecure-requests': '1',
	'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.102 Safari/537.36',
	'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
	'sec-gpc': '1',
	'sec-fetch-site': 'none',
	'sec-fetch-mode': 'navigate',
	'sec-fetch-user': '?1',
	'sec-fetch-dest': 'document',
	'accept-language': 'en-US,en;q=0.9',
}

def request_slow(url, min_wait=20, max_wait=80):
	'''Make request of URL and insert random pause (in given range) before moving on.

	Parameters:
		url (string): single website to download with requests
		min_wait (int): minimum pause after request is completed, in hundredths of a second, i.e. enter 100 to have a minimum pause of 1.00 seconds
		max_wait (int): maximum pause after request is completed, in hundredths of a second, i.e. enter 200 to have a maximum pause of 2.00 seconds

	Returns:
		requested (object): requests-generated object representing scraped website
	'''
	
	# initialize
	requested = None

	with requests.Session() as session: # open session
		session.keep_alive = False # don't keep session going after
		try:
			requested = session.get(url, headers=obit_headers, stream=False) # get data
		except requests.exceptions.ConnectionError as e:
			print(e)
	
	time.sleep(random.randrange(min_wait, max_wait)/100) # pause after scraping done

	return requested

# Takes in a list of urls and returns a list of ObitObjects
def batch_scrape(url_list, obit_config):
	assert(not obit_config.boosted) # has not been implemented yet
	assert(not obit_config.save_raw) # has not been implemented yet
	assert(obit_config.low_memory) # parallel version has not been implemented yet

	# obituary scraping
	url_iterable = url_list
	if obit_config.print_progress:
		url_iterable = tqdm(url_list, "URL Requests")

	raw_obits = []
	for url in url_iterable:
		requested = request_slow(url)
		try:
			raw_obits.append(requested.text) # just append html, don't need rest of Response object
		except AttributeError as e: # in case of connection errors
			print(f'Failed to request data from {url} due to this `AttributeError`:')
			print(e)
	raw_obits = list(zip(raw_obits, url_list))

	# obituary parsing
	all_obits = []
	if not obit_config.low_memory: # multiprocessing version
		print("Parsing the obituaries in parallel...")
		#all_obits = pool.map(scrape_para_and_location, raw_obits)
		pool = mp.Pool()
		for result in tqdm(pool.imap_unordered(construct_obit_obj, [(raw_obits, obit_config.photo_config)])):
			all_obits.append(result)
		pool.close()
	else: # slower, non-MP version for less compute resources
		print("Parsing the obituaries in NOT-parallel way...")
		all_obits = [construct_obit_obj(raw_obit, obit_config.photo_config) for raw_obit in tqdm(raw_obits)]
	print("DONE parsing web pages.")
	return all_obits




