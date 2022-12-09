counter=2015
while [ $counter -le 2022 ]
do
  echo "Scraping January $counter"
  python3 url_scraper.py -s 01/01/$counter -e 01/31/$counter

  echo "Scraping February $counter"
  python3 url_scraper.py -s 02/01/$counter -e 02/28/$counter

  echo "Scraping March $counter"
  python3 url_scraper.py -s 03/01/$counter -e 03/31/$counter

  echo "Scraping April $counter"
  python3 url_scraper.py -s 04/01/$counter -e 04/30/$counter

  echo "Scraping May $counter"
  python3 url_scraper.py -s 05/01/$counter -e 05/31/$counter

  echo "Scraping June $counter"
  python3 url_scraper.py -s 06/01/$counter -e 06/30/$counter

  echo "Scraping July $counter"
  python3 url_scraper.py -s 07/01/$counter -e 07/31/$counter

  echo "Scraping August $counter"
  python3 url_scraper.py -s 08/01/$counter -e 08/31/$counter

  echo "Scraping September $counter"
  python3 url_scraper.py -s 09/01/$counter -e 09/30/$counter

  echo "Scraping October $counter"
  python3 url_scraper.py -s 10/01/$counter -e 10/31/$counter

  echo "Scraping November $counter"
  python3 url_scraper.py -s 11/01/$counter -e 11/30/$counter

  echo "Scraping December $counter"
  python3 url_scraper.py -s 12/01/$counter -e 12/31/$counter

  ((counter++))
done

echo "All done"
