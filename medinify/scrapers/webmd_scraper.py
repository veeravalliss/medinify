"""
Drug review scraper for Medinify.

This module scrapes comments from WebMD along with their rating.
Based on work by Amy Olex 11/13/17.
"""

import re
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup
import csv

class WebMDScraper():
    """
    Class to scrap drug reviews from WebMD

    Attributes:
        all_pages: Boolean for whether or not to scrape all pages
        pages: int for # of pages to scrape if all_pages is 0
        review_list: List of review dictionary items
    """

    all_pages = True
    pages = 1
    review_list = []

    def __init__(self, all_pages=True, pages=1):
        self.all_pages = all_pages
        self.pages = pages

    def max_pages(self, input_url):
        """Finds number of review pages for this drug.

        Args:
            input_url: URL for the first page of reviews.
        Returns:
            (int) Highest page number
        """
        page = requests.get(input_url)
        soup = BeautifulSoup(page.text, 'html.parser')
        if 'Be the first to share your experience with this treatment.' in soup.find('div', {'id': 'heading'}).text:
            return 0
        total_reviews_text = soup.find('span', {'class': 'totalreviews'}).text
        total_reviews = [int(s) for s in total_reviews_text.split() if s.isdigit()][0]

        # Does the equivalent of max_pages = ceil(total_reviews / 5) without the math library
        max_pages = total_reviews // 5
        if total_reviews % 5 != 0:
            max_pages += 1

        print('Found ' + str(total_reviews) + ' reviews.')
        print('Scraping ' + str(max_pages) + ' pages...')
        return max_pages

    def scrape_page(self, page_url):
        """Scrapes a single page for reviews and adds them to review_list

        Args:
            page_url: URL of the page to scrape.
        """
        page = requests.get(page_url)
        soup = BeautifulSoup(page.text, 'html.parser')
        reviews = soup.find_all('div', attrs={'class': 'userPost'})

        for review in reviews:
            comment = review.find('p', id=re.compile("^comFull*")).text
            comment = comment.replace('Comment:', '').replace('Hide Full Comment', '')
            comment = ' '.join(comment.splitlines())

            ratings = review.find_all('span', attrs={'class': 'current-rating'})
            effectiveness = int(ratings[0].text.replace('Current Rating:', '').strip())
            ease = int(ratings[1].text.replace('Current Rating:', '').strip())
            satisfaction = int(ratings[2].text.replace('Current Rating:', '').strip())

            self.review_list.append({'comment': comment,
                                     'effectiveness': effectiveness,
                                     'ease of use': ease,
                                     'satisfaction': satisfaction})

    def scrape(self, input_url):
        """Scrapes the reviews from WebMD

        Args:
            input_url : WebMD URL to scrape
        """

        print('Scraping WebMD...')

        self.review_list = []

        quote_page1 = input_url + '&pageIndex='
        quote_page2 = '&sortby=3&conditionFilter=-1'
        num_pages = 0

        if self.all_pages:
            num_pages = self.max_pages(input_url)
        else:
            num_pages = self.pages

        for i in range(num_pages):
            page_url = quote_page1 + str(i) + quote_page2
            self.scrape_page(page_url)

            page = i + 1
            if page % 10 == 0:
                print('Scraped ' + str(page) + ' pages...')

        print('Reviews scraped: ' + str(len(self.review_list)))

        return self.review_list

    def get_common_drugs(self):
        """ Get all urls for 'common' drug review pages

        Returns:
            List of urls for each drug's review page
        """
        url = 'https://www.webmd.com/drugs/2/index?show=drugs'
        page = requests.get(url)
        soup = BeautifulSoup(page.text, 'html.parser')
        drug_names = soup.find_all('a', {'class': 'common-result-name'})
        drug_review_links = soup.find_all('a', {'class': 'common-result-review'})
        drug_review_pages = []

        for i in range(1, len(drug_names)):
            name = drug_names[i].text
            relative_link = drug_review_links[i]['href']
            absolute_link = urljoin(url, relative_link)
            drug_review_pages.append({'name': name, 'url': absolute_link})

        return drug_review_pages

    def get_drug_urls(self, file_path, output_file):

        drugs = []
        with open(file_path, 'r') as drug_names:
            drugs_reader = csv.reader(drug_names)
            for row in drugs_reader:
                drugs.append(row[0])

        # search for drugs in drug name file on WebMD
        first_search_url = 'https://www.webmd.com/search/search_results/default.aspx?query='
        unfound_drugs = []
        drug_results_urls = {}
        for drug in drugs:
            print('Searching for {}'.format(drug))
            search_url = first_search_url + drug.lower()
            search_page = requests.get(search_url)
            search_soup = BeautifulSoup(search_page.text, 'html.parser')
            search_results = search_soup.find_all('p', {'class': 'search-results-doc-title'})
            for link in search_results:
                if 'Drug Results for' in link.text:
                    query_url = 'https://www.webmd.com' + link.find('a').attrs['href']
                    drug_results_urls[drug] = query_url
                    print('Drug results page for {} found!\n'.format(drug))
            if drug not in drug_results_urls.keys():
                unfound_drugs.append(drug)

        drugs = drug_results_urls.keys()

        # search for drug info page url
        drug_info_urls = {}
        for drug in drugs:
            drug_results_url = drug_results_urls[drug]
            drug_results_page = requests.get(drug_results_url)
            drug_results_soup = BeautifulSoup(drug_results_page.text, 'html.parser')

            print('Searching for {} info page'.format(drug))
            if drug_results_soup.find('a', {'class': 'drug-review'}):
                print('Found {} info page!\n'.format(drug))
                drug_info_url = drug_results_urls[drug]
                drug_info_urls[drug] = drug_info_url

            elif drug_results_soup.find('a', {'data-metrics-link': 'result_1'}):
                drug_versions_html = drug_results_soup.find_all('a', {'data-metrics-link': 'result_1'})
                version_urls = []
                for drug_version in drug_versions_html:
                    version_url = 'https://www.webmd.com' + drug_version.attrs['href']
                    version_urls.append(version_url)

                max_reviews = 0
                max_url = ''

                for version_url in version_urls:
                    version_page = requests.get(version_url)
                    version_soup = BeautifulSoup(version_page.text, 'html.parser')
                    num_reviews_text = version_soup.find('a', {'class': 'drug-review'}).text
                    num_reviews = int(num_reviews_text.split()[2].replace('(', '').replace(')', '').replace(',', ''))
                    if num_reviews > max_reviews:
                        max_reviews = num_reviews
                        max_url = version_url

                if max_url != '':
                    print('Found version of {} with most reviews!\n'.format(drug))
                    drug_info_urls[drug] = max_url

        # searches on drug info pages for drug review pages
        drug_review_pages = {}
        for drug in drugs:
            print('Searching for {} reviews page'.format(drug))
            drug_info = drug_info_urls[drug]
            drug_info_page = requests.get(drug_info)
            drug_info_soup = BeautifulSoup(drug_info_page.text, 'html.parser')
            if drug_info_soup.find('a', {'class': 'drug-review'}):
                print('Found {} reviews page\n'.format(drug))
                drug_review_page = 'https://www.webmd.com' + drug_info_soup.find('a', {'class': 'drug-review'}).attrs['href']
                drug_review_pages[drug] = drug_review_page

        print('Found urls for {} drugs'.format(len(drug_review_pages)))
        print('Did not find urls for {} drugs:\n {}\n'.format(len(unfound_drugs), unfound_drugs))

        print('Writing url csv file')
        review_urls = []
        for drug in drugs:
            review_urls.append({'Drug': drug, 'URL': drug_review_pages[drug]})

        # writes url csv file
        with open(output_file, 'w') as url_csv:
            fieldnames = ['Drug', 'URL']
            writer = csv.DictWriter(url_csv, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(review_urls)

        print('Finished writing!')