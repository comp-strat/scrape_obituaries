# Scraping online obituaries for public health surveillance

This codebase contains code for scraping obituaries from Legacy.com. The workflow has three steps: 
1. scrape URLs of obituary listings
2. scrape obituary text from URLs 
3. process the text to compute age, gender, and race for the deceased

In brief, our goal is to evaluate how well these obituaries track official death records using the test case of Washington, DC.

## Project overview

This study aims (1) to evaluate the feasibility and accuracy of using open-source data for monitoring COVID-19 and (2) to estimate demographic-specific excess mortality from all causes in 2020 and 2021 using official death records and obituary data. Automated data collection from text mining of openly available online obituaries could allow us to derive quick estimates of the age, sex, and race distribution of deaths by location in a cost-effective way, which is currently not possible since federal available datasets do not offer the necessary granularity or timeliness needed for monitoring efforts that can inform policy. The approaches this study will pursue will also help prepare tools to monitor future outbreaks and understand other types of causes of death, e.g., AIDS or opioid overdose.

## Instructions

First, install things by following the [kickstart guide to setup and installations](SETUP.md). 
  - Note that there are a few special setup steps for [SUTime](https://github.com/FraBle/python-sutime) (which [require Maven](https://maven.apache.org/install.html)) and SpaCy (namely `python3 -m spacy download en_core_web_sm`). Everything else can be handled by creating a virtual environment and running `pip3 install -r requirements.txt`.

Then execute the code for each step by following the [run instructions](RUN_SCRIPTS.md). The three steps are url scraping, obituary scraping, and  postprocessing.
