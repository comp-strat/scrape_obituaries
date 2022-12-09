# Post-processing
The code in this directory reads raw scraped data (batched) and outputs a processed dataset with location, funeral home, birth/death date, gender, ethnicity, and duplicate information. 

## Instructions
Our main file is `processor.py`, which runs the post-processing and duplicate identification workflow. 

**IMPORTANT: Run `processor.py` under the top-level `obituaries_private/` directory. **

The script assumes batched scraped data is already stored under `/mnt/ceph/obit_storage`.

For example, if we want to post-process scraped data from January 1st, 2015 to January 2nd, 2015 (20150101-20150102), queried on October 23rd, 2022 16:32 (20221023-1632), with runname 'test', then we would run the following command in the terminal under the `obituaries_private/` directory: 
```bash
python3 postprocessing/processor.py 20150101-20150102 20221023-1632 test
```

## Output
`processor.py` outputs the following files in [the `postprocessing` directory](https://github.com/comp-strat/obituaries_private/postprocessing):

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
