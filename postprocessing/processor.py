import json
import re
import numpy as np
import pandas as pd
import math
import sys
import os
from os import listdir
import seaborn as sns
from os.path import isfile, join

#Text processing package
from metaphone import doublemetaphone # returns rough approximation of how an English word sounds
from unidecode import unidecode #normalize unicode strings
#to remove accents, umlauts, rare letters, and non-typical Unicode normalizations

#Fuzzy matching and record linkage
from fuzzywuzzy import fuzz #For Distance measure between strings
from fuzzywuzzy import process
from typing import Callable, List
import recordlinkage as rl
from recordlinkage.compare import Date
import time

import gender_guesser.detector as gender

from dateutil.relativedelta import relativedelta
from datetime import datetime

from ethnicolr import pred_wiki_ln, pred_wiki_name
from ethnicolr import census_ln, pred_census_ln
from sutime import SUTime

import spacy
from spacy import displacy 
#nlp = spacy.load('xx_ent_wiki_sm')
nlp = spacy.load('en_core_web_sm')
import dateparser

import geopy
from geopy.extra.rate_limiter import RateLimiter
from geopy import distance

import cv2
from deepface import DeepFace

# from allennlp_models import pretrained
# from allennlp.predictors import Predictor
# al = pretrained.load_predictor('tagging-fine-grained-transformer-crf-tagger')

YEAR = None
RUNNAME = ''
filename = '' # listdir(f"../obit_scraping/all_results/{YEAR}0101-{YEAR}1231")[0]
fullpath = '' # f"../obit_scraping/all_results/{YEAR}0101-{YEAR}1231/{filename}"

def create_feature_csv(feature_adder):

    def inner(*args, **kwargs):
        f = open(fullpath)
        data = json.load(f)
        data = [i for i in data if i]
        df = pd.DataFrame.from_dict(data)
        df = df.drop_duplicates()
        f.close()

        df = feature_adder(df, *args, **kwargs)

        df.to_csv(f'postprocessing/{RUNNAME}-{feature_adder.__name__}-{YEAR}.csv')
    
    return inner

# Gender
@create_feature_csv
def guess_gender(df):
    d = gender.Detector()
    def first_name(name):
        ''' Extracts first name 

            Args: 
                name (str): A person's full name
            Returns: 
                The person's first name (str)
        '''
        m = re.match(r'(?:[A-Za-z]{0,2}\. )?([A-Za-z]+) ', name)
        if m:
            return m.group(1).title().strip()
        return ""
    def pronoun_guesser(p):
        mr_count = p.count("Mr")
        ms_count = p.count("Ms")
        mrs_count = p.count("Mrs")
        pronoun_dict = {"unknown": 0,\
                        "male": p.count("Mr")+p.count("he")+p.count("He")+p.count("him")+p.count("Him")+p.count("His")+p.count("his"),\
                        "female": p.count("Ms")+p.count("Mrs")+p.count("she")+p.count("her")+p.count("hers")+p.count("She")+p.count("Her")+p.count("Hers")}
        return max(pronoun_dict, key=pronoun_dict.get)
    df = df.copy()
    df["first_name"] = df["name"].apply(first_name)
    df['sex'] = df.apply(lambda r: d.get_gender(r["first_name"]) if d.get_gender(r["first_name"]) != "unknown" and d.get_gender(r["first_name"]) != "andy" else pronoun_guesser(r["para"]), axis=1)
    
    return df

# Simple location
@create_feature_csv
def simple_location_finder(df):
    df = df.copy()
    location_finder = re.compile(r'((?:[A-Z][a-z]{2,}\s)?[A-Z][a-z]+,\s[A-Z]{2})')
    def get_loc(p):
        poss_locs = location_finder.findall(p)
        if poss_locs:
            # If the paragraph even mentions 'Washington, DC', throw em in the DC pile!
            if "Washington, DC" in poss_locs or ("DC" in p) or ("Columbia" in p) or ("D.C" in p):
                return "Washington, DC"
            # If the paragraph doesn't mention 'Washington, DC', find the most common location mentioned
            else:
                return max(set(poss_locs), key=poss_locs.count)
        elif ("DC" in p) or ("Columbia" in p) or ("D.C" in p):
            return "Washington, DC"
    df["funeral_home_ind"] = df["funeral_home_name"].apply(lambda x: bool(x))
    first_split = df['funeral_home_address'].str.split('|')
    df['fh_address_line1'] = first_split.str[0]
    second_split = first_split.str[1].str.split(',')
    df['fh_address_city'] = second_split.str[0]
    df['fh_address_state'] = second_split.str[1]
    
    df["newspaper_ind"] = df["newspaper"].apply(lambda x: bool(x))
    df["location"] = df.apply(lambda row: "Washington, DC" if row["location"] == "Washington, DC" else get_loc(row["para"]), axis=1)
    return df

# Hardcore location
@create_feature_csv
def hardcore_location_finder(df):
    df = df.copy()
    df["funeral_home_ind"] = df["funeral_home_name"].apply(lambda x: bool(x))
    first_split = df['funeral_home_address'].str.split('|')
    df['fh_address_line1'] = first_split.str[0]
    second_split = first_split.str[1].str.split(',')
    df['fh_address_city'] = second_split.str[0]
    df['fh_address_state'] = second_split.str[1]
    
    df["newspaper_ind"] = df["newspaper"].apply(lambda x: bool(x))
    df_paras = df["para"]
    def location_set(text):
        locs = []
        d = nlp(text).ents
        for e in d:
            if e.label_ in ['LOC'] or e.label_ in ["GPE"]:
                locs.append(e.text)
        return locs
    spacy_locs = df_paras.apply(location_set)
    
    locator = geopy.geocoders.Nominatim(user_agent='mygeocoder')
    geocode = RateLimiter(locator.geocode, min_delay_seconds=1, swallow_exceptions=True)
    def get_dc(p):
        try:
            geo = [geocode(i,addressdetails=True) for i in p]
        except:
            return None
        if geo and len(geo) > 0:
            return list(filter(None, [[i.raw["address"].get("city", None), i.raw["address"].get("state", None)] for i in geo if i]))
        else:
            return None
    
    def combine_address(l):
        if not l:
            return None
        l_states = [i[1] for i in l]
        frequentest = max(set([i for i in l_states if i]), key = l_states.count)
        for i in l:
            if (i[1] == frequentest and i[0]) or i[1] == "District of Columbia":
                return ', '.join(i)
        return frequentest

    sample_addrs = spacy_locs.apply(lambda p: get_dc(p) if len(p) != 0 and p else None)
    df["all_locs"] = sample_addrs
    df["location"] = df["all_locs"].apply(combine_address)
    return df

def transform_to_dtformat(date_list):
    ''' Get correct date formats from SUTime return object (called in get_all_dates(...)) 
    Args:
        date_list (list of dict): List of dates returned by SUTime for each profile
    Returns:
        ret_list (list of str): List of dates converted to string format
    '''

    ret_list = []
    for elem in date_list:
        if elem['type'] == 'DATE':
            ret_list.append(elem['value'])
        ## Date range
        elif (elem['type'] == 'DURATION') and (isinstance(elem['value'], dict)) and (len(elem['value']) != 0):
            try:
                begin = elem['value']['begin']
            except:
                continue
            if (begin[:2] == 'XX'):
                century = '19' if (begin[2:4] > str(YEAR - 2000)) else '20'
                begin = century + begin[2:]
            try:
                end = elem['value']['end']
            except:
                continue
            if (end[:2] == 'XX'):
                century = '19' if (end[2:4] > str(YEAR - 2000)) else '20'
                end = century + end[2:]
            ret_list.append(begin)
            ret_list.append(end)
        else:
            pass
    
    return ret_list
  
def get_all_dates_SU(df):
    ''' Creates new column with list of dates (string) obtained from SUTime '''

    sutime = SUTime(mark_time_ranges=True, include_range=True)
    df['all_dates_su'] = df['para'].apply(lambda p: sutime.parse(p))
    df['all_dates_su'] = df['all_dates_su'].apply(lambda res: transform_to_dtformat(res))
    return df

def get_all_dates_SP(df):
    ''' Creates new column with list of dates (string) obtained from SpaCy '''
      
    def get_dates(text):
        dates = set()
        d = nlp(text).ents
        for e in d:
            if e.label_ in ['DATE']:
                dates.add(e.text)
        return list(dates)
    
    df['all_dates_sp'] = df['para'].apply(lambda p: get_dates(p))
    return df

def get_all_dates_RE(df):
    ''' Creates new columns with 1) list of all dates and 
        2) Age, both obtained from our own regex expressions'''
    
    date_finder = re.compile(r'(Jan(?:uary)?|Feb(?:ruary|uary|rury|rary|ury|ary|ruy|uy)?|Mar(?:ch|c|h)?|Apr(?:il|li|i|l)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust|sut|st|s|t)?|Sep(?:tember|t|tmber|tber|tmbr|tembr)?|Oct(?:ober|obr|obre|obir|ber|oer)?|(?:Nov|Dec)(?:ember|imber|embr|eber|mber|mbr)?)(?:,?) (?:([0-9]{1,2})(?:rd|st|th)?)(?:,? ([0-9]{4}))?')
    age_finder = re.compile(r'[Aa]ge ([0-9]{1,3})')
    yrsold_finder = re.compile(r'([0-9]{1,3}) [Yy]ears [Oo]ld')
    
    df["all_dates_re"] = df["para"].str.findall(date_finder) ## Dates found by regex
    
    ## Ages found by regex
    df["para_ages"] = df["para"].str.findall(age_finder) 
    df['para_ages'] = df['para_ages'] + df['para'].str.findall(yrsold_finder)
    df["age"] = df["para_ages"].apply(lambda x: int(max(x)) if len(x)>0 else None)
    
    return df

# def get_age_nlp(para):
#     ''' Find age using allennlp package
#         Args: 
#             para (str): Obituary paragraph
#         Retirns:
#             temp_max (int): Inferred age from the paragraph
#     '''
#     pred = al.predict(para)
#     ## Finding all numbers from the text
#     date_index = [i for i in range(len(pred['tags'])) if 'DATE' in pred['tags'][i]]
#     date_list = [pred['words'][i] for i in date_index]
#     ## Maximum number that is less than 120 is assigned as age
#     temp_max = 0
#     for num in [int(n) for n in date_list if n.isdigit()]:
#         if (num < 120 and num > temp_max):
#             temp_max = num

#     return temp_max if temp_max != 0 else None

def try_parsing_date(text):
    '''Tries to parse date (helper function) 
        Args:
            text (str): A single date in string format
        Returns:
            ret_date (datetime object): parsed string into proper datetime format  
    '''
    ret_date = dateparser.parse(text, settings={'PREFER_DAY_OF_MONTH': 'first', 'PREFER_DATES_FROM': 'past', 'RELATIVE_BASE': datetime(YEAR, 1, 1)})
    if (not pd.isnull(ret_date)):
        ret_date = ret_date.replace(tzinfo = None)
    if ((not pd.isnull(ret_date)) and (ret_date > datetime.fromisoformat('1900-01-01')) and (ret_date < datetime.today())):
        return ret_date
    else:
        return None

def parse_datestrings(df, year, method): 
    ''' Creates new columns for birthday and deathday containing 1) datetime object, 2) string and 3) parser used.
        birthday: earliest date
        deathday: most-current date before publish date
        
        Assumes all_dates column already populated from get_all_dates(...) functions.

        Args:
            df (pandas dataframe): dataframe containing the profiles and all dates extracted from paragraphs.
            year (int): year that we are scraping from
            method: nlp library used to get dates- either sutime or scrapy
        Returns:
            df (pandas dataframe): same as the df passed in, with extra columns for
                                    birthday, deathday and methods. 
    '''

    for i in df.index:
        
        date_objs = {}
        pub_date = try_parsing_date(df.loc[i, 'pubdate']) ## Try get publish date into datetime format
        if (pd.isnull(pub_date)):
            pub_date = try_parsing_date('{}-12-31'.format(year)) ## Defaults to last day of the year
            
        dates = df.loc[i, 'all_dates'] ## Dates for this row
        
        for d in dates:
            ## Date extracted using Regex
            if isinstance(d, tuple):
                date_year = d[2]
                if date_year == '':
                    date_year = year
                
                try:
                    parsed_date = datetime(int(date_year), datetime.strptime(d[0][:3], '%b').month, int(d[1]))
                except:
                    ## Rare case observed: Feb 29th in non-leap year. Resolve by throwing away the day.
                    #parsed_date = datetime(int(date_year), datetime.strptime(d[0][:3], '%b').month)
                    parsed_date = None

                if parsed_date is not None:
                    string = ' '.join(d)
                    method_i = 'regex'

                    date_objs[string] = [parsed_date, method_i]

            ## Date extracted using non-regex (spaCy or SUTime)
            else:
                parsed_date = try_parsing_date(d)
                if parsed_date is not None:
                    string = d
                    method_i = method

                    date_objs[string] = [parsed_date, method_i]
                    
        birthday, deathday = get_birth_death(date_objs, pub_date, year)
        
        if (not pd.isnull(birthday)):
            df.loc[i, 'birthday'] = birthday[0]
            df.loc[i, 'bday_string'] = birthday[1]
            df.loc[i, 'bday_method'] = birthday[2]
        else:
            df.loc[i, 'birthday'] = np.nan
        
        if (not pd.isnull(deathday)):
            df.loc[i, 'deathday'] = deathday[0]
            df.loc[i, 'dday_string'] = deathday[1]
            df.loc[i, 'dday_method'] = deathday[2]
        else:
            df.loc[i, 'deathday'] = np.nan
    
    return df


def get_birth_death(date_objs, pub_date, year):
    ''' Helper function to get birthday and deathday from a dictionary of dates passed in
        
        Args: 
            date_objs (dict): Dictionary of dates from one profile, with format {'datestring': [datetime_object, parser]}
            pub_date (datetime object): publish date
            year (int): Year we are scraping from
        Returns:
            birthday, deathday: Each of these are tuples with format (datetime_obj, datestring, parser)
    '''

    birthday = None
    deathday = None
    
    if len(date_objs) > 0:
        
        ## Bday conditions: more than 20 years ago, and after 1900
        possible_birthdates = {}
        for (key, value) in date_objs.items():
            date = value[0]
            if (date.year < year-20 and date.year > 1900):
                possible_birthdates[key] = value
        
        ## Birthday is set to the tuple associated with MIN datetime object.     
        if len(possible_birthdates) > 0:
            birthday = min([(possible_birthdates[key][0],key, possible_birthdates[key][1]) for key in possible_birthdates], key=lambda t: t[0])
        
        ## Dday conditions: after 1950 and less than publish date
        possible_deathdates = {}
        for (key, value) in date_objs.items():
            date = value[0]
            if (date.year > 1950 and date < pub_date):
                possible_deathdates[key] = value
        
        ## Deathdate is set to tuple associated with MAX datetime object        
        if len(possible_deathdates) > 0:
            deathday = max([(possible_deathdates[key][0], key, possible_deathdates[key][1]) for key in possible_deathdates], key=lambda t: t[0])

    return (birthday, deathday)


def add_scraped_dates(df):
    ''' Populate missing or incorrect 'birthday' and 'deathday' fields using scraped dates.

        Args: 
            df (pandas dataframe): dataframe with all profiles and birthday, deathday fields
        Returns:
            df: same as above, but with corrected birthday and deathday fields  
    '''

    for i in df.index:
        
        ## Birthdays and deathdays found from the paragraph.
        birthday_para = df.loc[i, 'birthday']
        try: 
            deathday_para = df.loc[i, 'deathday']
        except KeyError:
            print(df.loc[i,:])
        ## Birthdays and deathdays scraped from page HTML
        birthday_scraped = try_parsing_date(df.loc[i, 'birthdate'])
        deathday_scraped = try_parsing_date(df.loc[i, 'deathdate'])
        
        ## If we are missing birthday from paragraph OR if birthday year from paragraph does not match scraped birthday year
        if (not pd.isnull(birthday_scraped) and
            (pd.isnull(birthday_para) or (birthday_para.year != birthday_scraped.year))):
            df.loc[i, 'birthday'] = birthday_scraped ## Set 'birthday' as scraped birthdate
            df.loc[i, 'bday_string'] = df.loc[i, 'birthdate'] ## Original string for scraped birthday
            df.loc[i, 'bday_method'] = 'scraped'
            
        if (not pd.isnull(deathday_scraped) and
            (pd.isnull(deathday_para) or (deathday_para.year != deathday_scraped.year))):
            df.loc[i, 'deathday'] = deathday_scraped
            df.loc[i, 'dday_string'] = df.loc[i, 'deathdate']
            df.loc[i, 'dday_method'] = 'scraped'
                
    return df


def birthday_from_age(df):

    ''' Populates missing birthdays from age and death date when available.
        Assumes 'birthday' and 'deathday' fields already populated and checked with add_scraped_dates(..)
        
        Note: Scraped dates are most reliable, followed by min(Death-Age, paragraph birthday)

        Args:
            df (pandas dataframe): dataframe with profiles and correct birthday, deathday fields
        Returns:
            df: same as above, but with missing birthdays deduced from Age-death
    '''

    for i in df.index:
        birthday = df.loc[i, 'birthday']
        scraped_birthday = try_parsing_date(df.loc[i, 'birthdate'])
        deathday = df.loc[i, 'deathday']
        age = df.loc[i, 'age']
        if ((not pd.isnull(age)) and (not pd.isnull(deathday)) and age < 120):
            deduced_bday = deathday - relativedelta(years = age)
            ## If birthday field does not match (Death - Age), and there is no scraped birthday, replace birthday field with 
            ## min(Death-Age, paragraph birthday)
            if (pd.isnull(scraped_birthday) and (pd.isnull(birthday) or (deduced_bday.year < birthday.year))):
                df.loc[i, 'birthday'] = deduced_bday
                df.loc[i, 'bday_string'] = np.nan
                df.loc[i, 'bday_method'] = 'deduced (death-age)'
    return df


@create_feature_csv
def run_dates(df, parser):

    ''' Run entire workflow for getting dates 
        Args: 
            df (pandas dataframe): raw scraped obituary data
            parser (string): nlp library used to find dates, either 'sutime' or 'spacy'
        Returns:
            ret_df (pandas dataframe): same as above, but with additional columns containing 
                                        complete information on birthday and deathday
    '''

    ret_df = df.copy()
    
    ret_df = get_all_dates_RE(ret_df)
    # ret_df['age_nlp'] = ret_df['para'].apply(lambda x: get_age_nlp(x))
    # ret_df['age'] = ret_df['age'].fillna(ret_df['age_nlp'])

    if (parser == 'spacy'):
        ret_df = get_all_dates_SP(ret_df)
        ret_df['all_dates'] = ret_df['all_dates_sp'] + ret_df['all_dates_re']
    elif (parser == 'sutime'):
        ret_df = get_all_dates_SU(ret_df)
        ret_df['all_dates'] = ret_df['all_dates_su'] + ret_df['all_dates_re']
    else:
        print('invalid parser: must be spacy or sutime')

    ret_df = parse_datestrings(ret_df, YEAR, parser)

    ret_df = add_scraped_dates(ret_df)
    ret_df = birthday_from_age(ret_df)

    return ret_df

@create_feature_csv
def run_race(df, photo_path):

    ''' Create 'race' column using ethnicolr.
        
        Args:
            df (pandas dataframe): raw scraped obituary data
        Returns:
            df: same as above, but with additional 'race' column containing predicted race
    '''
    
    def first_name(name):
        ''' Extracts first name 
            Args: 
                name (str): A person's full name
            Returns: 
                The person's first name (str)
        '''
        m = re.match(r'(?:[A-Za-z]{0,2}\. )?([A-Za-z]+) ', name)
        if m:
            return m.group(1).title().strip()
        return ""
    
    def pred_race(filepath):
        img = cv2.imread(filepath)
        try:
            prediction = DeepFace.analyze(img)
            main_race = prediction['dominant_race']
            race_dict = prediction['race']
            pred_race_value = sorted(race_dict.values())[-1]
            diff_highest = pred_race_value - sorted(race_dict.values())[-2]
        except:
            main_race = ''
            pred_race_value  = ''
            diff_highest = ''
        return main_race, pred_race_value, diff_highest
        
    for i in df.index:
        photo_tag = df.loc[i, 'photo_file']
        if (pd.notnull(photo_tag) and (photo_tag != "")):
            main_race, pred_race_value, diff_highest = pred_race(photo_path + photo_tag)
            df.loc[i, 'photo_pred_race'] = main_race
            df.loc[i, 'photo_pred_race_value'] = pred_race_value
            df.loc[i, 'photo_diff_highest'] = diff_highest
                        
    temp_df = df.copy()
    temp_df['name'] = temp_df['name'].apply(lambda string: string.replace(' Sr.', ''))
    temp_df['name'] = temp_df['name'].apply(lambda string: string.replace(' Jr.', ''))
    temp_df['last_name'] = temp_df['name'].apply(lambda name: name.split(' ')[-1])
    # temp_df['last_name'] = temp_df['last_name'].apply(lambda name: name.lower())
    temp_df['first_name'] = temp_df['name'].apply(first_name)
    
    ## Highest probability race returned from Wikipedia data (both first and last name)
    # wiki_pct = pred_wiki_name(temp_df, 'last_name', 'first_name').set_index('rowindex')  
    # df['race_wiki'] = wiki_pct['race']

    ## All probabilities from Census data (last name only)
    pct = census_ln(temp_df, 'last_name', year=2010).set_index(temp_df.index)[['pctwhite', 'pctblack', 'pctapi', 'pctaian', 'pct2prace', 'pcthispanic']]
    pct = pct.replace('(S)', np.nan).apply(pd.to_numeric).fillna(0)
    df['pred_race'] = pct.idxmax(axis = 1) 
    df['race_pred_value'] = pct.max(axis = 1)
    df.loc[df['race_pred_value'] == 0, 'pred_race'] = ''
    df['race_diff_highest'] = df['race_pred_value'] - pct.apply(lambda x: x.nlargest(2).iloc[1], axis = 1)

    return df

@create_feature_csv
def sample(df, size):
    return df.sample(size)

def postprocess_synchronous(infile, runname, location_parser, year, photo_path):
    ''' Runs the entire postprocessing workflow
        
        Args:
            infile (str): raw .json file containing scraped obituaries
            runname (str): batch size information
            location_parser (str): type of location parser to use- 'simple' or 'hardcore'
            year (int): the year we scraped from
    '''

    global fullpath, RUNNAME, YEAR
    if (infile[:4] == '/mnt'):
        fullpath = infile
    else:
        fullpath = f'obit_scraping/all_results/{infile}'
    RUNNAME = runname
    YEAR = year
    
    ## Call functions to get gender, race, location and dates
    guess_gender()
    run_race(photo_path)
    if location_parser == 'simple':
        simple_location_finder()
    else:
        hardcore_location_finder()
    run_dates('sutime')

    gender_df = pd.read_csv(f'postprocessing/{RUNNAME}-guess_gender-{YEAR}.csv')
    race_df = pd.read_csv(f'postprocessing/{RUNNAME}-run_race-{YEAR}.csv')
    location_df = pd.read_csv(f'postprocessing/{RUNNAME}-simple_location_finder-{YEAR}.csv')
    dates_df = pd.read_csv(f'postprocessing/{RUNNAME}-run_dates-{YEAR}.csv')

    def drop_y(df):
        ''' Drops duplicate columns from merging '''
        # list comprehension of the cols that end with '_y'
        to_drop = [x for x in df if x.endswith('_y')]
        df.drop(to_drop, axis=1, inplace=True)

    def rename_x(df):
        ''' Rename columns after merging '''
        for col in df:
            if col.endswith('_x'):
                df.rename(columns={col:col.rstrip('_x')}, inplace=True)

    ## Create final_df with all fields via merging the dataframes
    final_df = gender_df
    for df in [race_df, location_df, dates_df]:
        final_df = pd.merge(final_df, df, how = 'outer', on = 'para')
        drop_y(final_df)
        rename_x(final_df)
    
    final_df.to_csv('postprocessing/{}-final_df-{}.csv'.format(RUNNAME, YEAR))
    
    ## Remove intermediate files upon successfully writing final_df
    os.remove(f'postprocessing/{RUNNAME}-guess_gender-{YEAR}.csv')
    os.remove(f'postprocessing/{RUNNAME}-run_race-{YEAR}.csv')
    os.remove(f'postprocessing/{RUNNAME}-simple_location_finder-{YEAR}.csv')
    os.remove(f'postprocessing/{RUNNAME}-run_dates-{YEAR}.csv')
    
def de_duplication(df):

    ''' Runs the entire duplicate identification process.
    
    Args:
        df (pandas dataframe): dataframe with dates, gender, location and race information.
    Outputs:
        df: same as input df, but with extra columns containing duplicate information. 
    '''
    
    # 1. De-duplication based on same Obit-link: The below two lines of code are to
    #be uncommented only when url is completely populated
    #df = df.drop_duplicates(subset=['url'], keep='last').reset_index()
    #df= df.drop(['index'], axis=1)
    

    # 2. Exact matches of Name & (DoB | DoD) 

    ## If both DoB and DoD are NA, we done include them for identifying duplicates
    ## as we cannot identify duplicates solely based on name

    index_indentify_duplicates = df.dropna(subset=['birthday','deathday'], how='all').index
    df1 = df.loc[index_indentify_duplicates] # This dataset should be used for identifying duplicates
    # print(index_indentify_duplicates)
    # print(df)
    # print(df.index)
    # print(index_indentify_duplicates)
    # df2 = df.drop(df.index[list(index_indentify_duplicates)])
    df2 = df.drop(index_indentify_duplicates)
    
    #Drop duplicates
    df1 = df1.drop_duplicates(subset=['name','birthday', 'deathday'], keep='last')
    df1 = df1.reset_index()
    df1 = df1.drop("index", axis=1)
    
    df2 = df2.reset_index()
    df2 = df2.drop("index", axis=1)
    
    #Join back two parts of the data
    df = pd.concat([df1,df2]).reset_index()
    df = df.drop("index", axis=1)
    
    # 3. Exact matches of Name & Para
    df = df.drop_duplicates(subset = ['name','para'], keep="last")
    df = df.reset_index()
    df = df.drop("index", axis=1)
    
    #Pre-processing names
    def normalize_unidecode(name: str) -> str:
        return unidecode(name)
    
    df["name"] = [normalize_unidecode(str(name)) for name in df["name"]]

    nonalphanumeric_re = re.compile(r"[^\w ]+") #compiling a regular expression of nonalphanumeric characters
    whitespace_re = re.compile(r" +") #compiling a regular expression of white spaces
    
    
    def name_processing(data, field="full_name"):
    
        '''
         This function takes the data frame and text field to be pre-processed as the inputs. 
         The function removes any character which is not a letter, a number, or a space, and collapses several spaces to one
        '''
    
        processed_list =[]
    
        for index,row in data.iterrows():
        
        
            if  row[field] != row[field]: #if the name is NA
                processed_list.append(row[field])
        
        
            elif row[field] == row[field]: #if the name is present
                processed_list.append(whitespace_re.sub(" ", nonalphanumeric_re.sub(" ", row[field].lower())))
                #process the data
            
        return processed_list

    name_processed = name_processing(df, "name")
    df['name_processed'] = name_processed #adding the processed names as a field
    
    
    #Adding a field for name identifier
    name_identifiers = []
    for index, row in df.iterrows():
        name = row.name_processed
        first_name_letters = name.split().pop(0)[0:2] #first two letters of the first name
        last_name_letters = name.split().pop(-1)[0:2] #first two letters of the last name
        first_last_letters = first_name_letters + last_name_letters #concatenate
        name_identifiers.append(first_last_letters)
    
    df["name_identifiers"] = name_identifiers
    
    #Converting deathday field to date format
    df["deathday"] = pd.to_datetime(df["deathday"], format = "%Y-%m-%d", errors='coerce')
    
    
    
    
    #Converting birthday field to date format
    #Birthday is in '%Y-%m-%d %H:%M:%S' format
    BD =[]
    for index, row in df.iterrows():
    
        if (type(row['birthday']) is str):
            date_string = row['birthday']
            if len(date_string)==19:
                BD.append(datetime.strptime(date_string, '%Y-%m-%d %H:%M:%S').date())
            elif len(date_string)==10:
                BD.append(datetime.strptime(date_string, '%Y-%m-%d').date())
                
            
        elif (row['birthday'] != row['birthday']):
            BD.append(row['birthday'])
        
    df['birthday'] = BD
    
    df["birth_year"] = [ round(date.year) if date==date else np.nan for date in df["birthday"]] #birth year field
    df["death_year"] = [ round(date.year) if date==date else np.nan for date in df["deathday"]] #death year field
    
    # Creating a field for identifier -> first two letters of first name + last name + Birth year + Death year
    df["identifier"]= [ name + str(BD) + str(DD) for name,BD,DD in zip (df["name_identifiers"], df["birth_year"], df["death_year"])]
    
   


    df_copy = df #creating a copy of the dataset for comparison
    
    #Fuzzy matching
    #creating an index object
    indexer = rl.Index()
    indexer.block(left_on='death_year', right_on='death_year')
    pairs = indexer.index(df, df_copy)

    # Creating a compare object
    compare = rl.Compare() 

    #processed names
    compare.string('name_processed','name_processed', threshold=0.95, method='levenshtein', label='compare_processed_FL')

    #comparing dates
    compare.exact('deathday','deathday', label='exact_DoD')

    #comparing dates
    compare.exact('birthday','birthday', label='exact_DoB')
    
    # Compute the matches, this will take a while
    matches = compare.compute(pairs, df, df_copy)
    
    
    index1 = matches.index.get_level_values(level=0) #index of the first dataset
    index2 = matches.index.get_level_values(level=1) #index of the copy being used for comparison
    
    #filter based on the index
    Obit1= df.filter(items = index1, axis=0) 
    Obit2 = df.filter(items = index2, axis=0)
    Obit2 = Obit2[["identifier", "name_processed"]] 
    Obit2.columns = ['identifier2', 'name_processed2'] 
    
    matches = matches.reset_index()
    
    Obit1 = Obit1.reset_index()
    Obit1 = Obit1.drop("index", axis=1)

    Obit2 = Obit2.reset_index()
    Obit2 = Obit2.drop("index", axis=1)
    
    matches  = pd.concat([Obit1, Obit2, matches], axis=1)
    
    #Adding a field for identifying matches on token set ratio
    def distance_set_ratio(s1: str, s2: str) -> int:
        return 100 - fuzz.token_set_ratio(s1, s2)

    #comparing two strings and get the score
    matches["token_set_ratio_score"] = [ distance_set_ratio(str1, str2) for str1,str2 in zip(matches["name_processed"],matches["name_processed2"])]
    matches["token_set_match"] =[1 if score==0 else 0 for score in matches["token_set_ratio_score"]]
    
    matches["drop_flag"] = [ 1 if x==y else 0 for x,y in zip(matches["level_0"], matches["level_1"])]
    
    #As we are comparing the same data set, dropping the rows where level_0 and level_1 are the same (basically where we are comparing the same row)
    matches = matches[matches.drop_flag != 1]
    
    #Filtering on matches if either of the name comparisons are a match along with either of the date comparisons being a match
    matches_final = matches[((matches.compare_processed_FL == 1) | (matches.token_set_match == 1)) & ((matches.exact_DoD == 1) |(matches.exact_DoB == 1)) ]

    matches_final = matches_final[['identifier2', 'name_processed2', 'level_0', 'level_1', 'compare_processed_FL', 'exact_DoD', 'exact_DoB',
       'token_set_ratio_score', 'token_set_match']]
    matches_final.columns = ['identifier2', 'name_processed2', 'match_index_level_0', 'match_index_level_1','compare_processed_FL', 'exact_DoD', 'exact_DoB',
       'token_set_ratio_score', 'token_set_match']
    
    
    matches_final["duplicate_remove"] = [ 1 if x>y else 0 for x,y in zip(matches_final["match_index_level_0"], matches_final['match_index_level_1'])]
    #matches_final = matches_final.drop_duplicates(subset =["identifier", "match_index_level_0"], keep='last')
    
    df = df.reset_index()
    
    df = pd.merge(df,matches_final, left_on="index",right_on="match_index_level_0", how="left")
    #In the resulting df, we will be able to identify the other row to which a particular row is a duplicate.
    #In case the same person has multiple duplicates, we will have another row to show that match. 
    #We are to ultimately remove all the rows where the index of level 0 is greater than level 1.(i.e based on "duplicate_remove_flag")
    #And also drop duplicates based on unique identifier and level 0 index
    
    ## Uncomment if we want to directly generate outfile
    #df.to_csv('postprocessing/{}-final_df_duplicates_identified-{}.csv'.format(RUNNAME, YEAR))

    return df

def run_duplicates_breakdown(infile, runname, year):
    ''' Splits the input dataset into smaller subsets and runs the de_duplication(...) 
    function. (smaller dataset resolves the problem of process being killed due to resource starvation)

    Args:
        infile (.csv): postprocessed dataset with location, dates, gender and race information.
        year (int): the year we scraped from
        runname (str): user-defined tag to be appended to the front of the outfile
    Outputs:
        same .csv as infile, but with extra columns containing duplicate identifiaction
    '''
    stepsize = 1000

    df_all = pd.read_csv(infile)
    df_all['grand_index'] = df_all.index ## Preserve initial index
    df_all = df_all.sort_values(by = 'name') ## Sort by names (alphabetical order) before splitting dataset
    
    df_final = de_duplication(df_all.iloc[0:stepsize, ]) 
    i = stepsize
    while (i+stepsize < len(df_all.index)):
        df_temp = de_duplication(df_all.iloc[i:(i+stepsize), ]) ## Run deduplication on small df
        df_final = pd.concat([df_final, df_temp])
        i += stepsize
    df_last = de_duplication(df_all.iloc[i:len(df_all.index), ])
    df_final = pd.concat([df_final,df_last])

    df_final = df_final.sort_values('grand_index')
    df_final.to_csv('/mnt/ceph/obits_storage/{}-final_df_duplicates_identified-{}.csv'.format(runname, year))

def main(argv):
    date_range = argv[1]
    scrape_time = argv[2]
    run_name = argv[3]
    year = int(date_range[:4])
    filepath = f'/mnt/ceph/obits_storage/{date_range}_{scrape_time}/'
    
    obits_dir = f'{filepath}{date_range}_{scrape_time}_obits/' 
    photos_dir = f'{filepath}{date_range}_{scrape_time}' 
    
    ## Iterate through obit batches and post-process. Concatenate results to final_df.
    final_df = None 
    for filename in os.listdir(obits_dir):
        f = obits_dir + filename
        batch_num = re.search("(\d+)", filename)[0]
        batch_runname = run_name + '_' + batch_num 
        photo_path = f'{photos_dir}_{batch_num}/photos_{batch_num}_'
        postprocess_synchronous(f, batch_runname, 'simple', year, photo_path)
        df = pd.read_csv('postprocessing/{}-final_df-{}.csv'.format(batch_runname, year))
        if final_df is None:
            final_df = df
        else:
            final_df = pd.concat([final_df, df], axis=0)
    
    final_df.index = np.arange(0, final_df.shape[0])
    cols = [c for c in df.columns if not 'Unnamed:' in c]
    final_df = final_df[cols]

    final_df.to_csv('/mnt/ceph/obits_storage/{}-final_df-{}.csv'.format(run_name, year))
    ## Delete batch outputs after final output is successfully written
    for filename in os.listdir(obits_dir):
        batch_num = re.search("(\d+)", filename)[0]
        batch_runname = run_name + '_' + batch_num 
        os.remove('postprocessing/{}-final_df-{}.csv'.format(batch_runname, year))
            
    run_duplicates_breakdown('/mnt/ceph/obits_storage/{}-final_df-{}.csv'.format(run_name, year), run_name, year)
        

if __name__ == "__main__":
    main(sys.argv)
    
    
# postprocess_synchronous('20200101-20200105/obits-20220927-2136.json', 'test-fh-npaper', 'simple', 2020)
# run_duplicates_breakdown('postprocessing/{}-final_df-{}.csv'.format(RUNNAME, YEAR), RUNNAME, YEAR)
