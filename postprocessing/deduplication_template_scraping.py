#!/usr/bin/env python
# coding: utf-8


# packages used
import pandas as pd
import numpy as np
import re
import math
from datetime import datetime

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

import warnings
warnings.filterwarnings('ignore')


# 0. Read the data
Obit_data = pd.read_excel('DOB_validation_sample_SpaCy_100positives_100negatives.xlsx')


# 1. De-duplication based on same Obit-link
Obit_data = Obit_data.drop_duplicates(subset=['url'], keep='last').reset_index()
Obit_data= Obit_data.drop(['index'], axis=1)


# 2. Exact matches of Name & (DoB | DoD) 

## If both DoB and DoD are NA, we done include them for identifying duplicates
## as we cannot identify duplicates solely based on name

index_identify_duplicates = Obit_data.dropna(subset=['birthday','deathday'], how='all').index
Obit_data1 = Obit_data.loc[index_identify_duplicates] # This dataset should be used for identifying duplicates
Obit_data2 = Obit_data.drop(Obit_data.index[list(index_identify_duplicates)])

#Drop duplicates
Obit_data1_duplicates_dropped = Obit_data1.drop_duplicates(subset=['name','birthday', 'deathday'], keep='last')

Obit_data1_duplicates_dropped = Obit_data1_duplicates_dropped.reset_index(drop=True)

Obit_data2 = Obit_data2.reset_index(drop=True)

#Join back two parts of the data
Obit_data = pd.concat([Obit_data1_duplicates_dropped,Obit_data2]).reset_index(drop=True)


# 3. Exact matches of Name & Para

Obit_data = Obit_data.drop_duplicates(subset = ['name','para'], keep="last").reset_index(drop=True)

#Pre-processing names

def normalize_unidecode(name: str) -> str:
    return unidecode(name)

Obit_data["name"] = [normalize_unidecode(name) for name in Obit_data["name"]]

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

Obit_data['name_processed'] = name_processing(Obit_data, "name") #adding the processed names as a field


# Add a field for name identifier

name_identifiers = []
for index, row in Obit_data.iterrows():
    name = row.name_processed
    first_name_letters = name.split().pop(0)[0:2] #first two letters of the first name
    last_name_letters = name.split().pop(-1)[0:2] #first two letters of the last name
    first_last_letters = first_name_letters + last_name_letters #concatenate
    name_identifiers.append(first_last_letters)
    
Obit_data["name_identifiers"] = name_identifiers


# Convert deathday field to date format
Obit_data["deathday"] = pd.to_datetime(Obit_data["deathday"], format = "%Y-%m-%d", errors='coerce')


# Convert birthday field to date format
# Birthday is in '%Y-%m-%d %H:%M:%S' format

BD =[]

for index, row in Obit_data.iterrows():
    
    if (type(row['birthday']) is str):
        date_string = row['birthday']
        BD.append(datetime.strptime(date_string, '%Y-%m-%d %H:%M:%S').date())
            
    elif (row['birthday'] != row['birthday']):
        BD.append(row['birthday'])
        
Obit_data['birthday'] = BD

Obit_data["birth_year"] = [ round(date.year) if date==date else np.nan for date in Obit_data["birthday"]] #birth year field
Obit_data["death_year"] = [ round(date.year) if date==date else np.nan for date in Obit_data["deathday"]] #death year field

# Create a field for identifier -> first two letters of first name + last name + Birth year + Death year
Obit_data["identifier"]= [ name + str(BD) + str(DD) for name,BD,DD in zip (Obit_data["name_identifiers"], Obit_data["birth_year"], Obit_data["death_year"])]

Obit_data_copy = Obit_data.copy() #creating a copy of the dataset for comparison


# Fuzzy matching

# Create an index object
indexer = rl.Index()

indexer.block(left_on='death_year', right_on='death_year')
pairs = indexer.index(Obit_data, Obit_data_copy) #44K pairs will be compared for matches

# Creating a compare object
compare = rl.Compare() 

# processed names
compare.string('name_processed','name_processed', threshold=0.95, method='levenshtein', label='compare_processed_FL')

# compare dates
compare.exact('deathday','deathday', label='exact_DoD')

# compare dates
compare.exact('birthday','birthday', label='exact_DoB')

# Compute the matches, this will take a while
matches = compare.compute(pairs, Obit_data, Obit_data_copy)

index1 = matches.index.get_level_values(level=0) #index of the first dataset
index2 = matches.index.get_level_values(level=1) #index of the copy being used for comparison

# filter based on the index
Obit1= Obit_data.filter(items = index1, axis=0) 
Obit2 = Obit_data.filter(items = index2, axis=0)

Obit2 = Obit2[["identifier", "name_processed"]] 
Obit2.columns = ['identifier2', 'name_processed2']

matches = matches.reset_index()

Obit1 = Obit1.reset_index(drop=True)
Obit2 = Obit2.reset_index(drop=True)

matches  = pd.concat([Obit1, Obit2,matches], axis=1)

# Add a field for identifying matches on token set ratio
def distance_set_ratio(s1: str, s2: str) -> int:
    return 100 - fuzz.token_set_ratio(s1, s2)

#comparing two strings and get the score
matches["token_set_ratio_score"] = [ distance_set_ratio(str1, str2) for str1,str2 in zip(matches["name_processed"],matches["name_processed2"])]
matches["token_set_match"] =[1 if score==0 else 0 for score in matches["token_set_ratio_score"]]
matches["drop_flag"] = [ 1 if x==y else 0 for x,y in zip(matches["level_0"], matches["level_1"])]

# As we are comparing the same data set, let's drop the rows where level_0 and level_1 are the same (basically where we are comparing the same row)
matches = matches[matches.drop_flag != 1]

matches[matches.token_set_match == 1]

#Filtering on matches if either of the name comparisons are a match along with either of the date comparisons being a match
matches_final = matches[((matches.compare_processed_FL == 1) | (matches.token_set_match == 1)) & ((matches.deathday == 1) |(matches.birthday == 1)) ]

matches_final.to_csv("matches_final.csv")
