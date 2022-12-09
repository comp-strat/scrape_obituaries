#!/bin/bash
#
#Description: Prints to stdout the total number of URLs (lines) in each file containing URLs.
#USAGE: sudo bash count_urls_by_file.sh | less

for dir in ./*/
do
    dir=${dir%*/}      # remove the trailing "/"
    echo "${dir##*/}"    # print everything after the final "/"
    for f in $(find $dir/ -type f -print0)
    do
        echo "$f"
        cat $f | wc -l
    done
    echo ""
done
