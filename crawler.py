# Import required libraries
import requests
from fake_useragent import UserAgent
from bs4 import BeautifulSoup
import os
import time

# Generate a random User-Agent for each request
ua = UserAgent()

# Set up Tor proxy (SOCKS5 over localhost)
proxy = {
    "https": "socks5h://127.0.0.1:9050",
    "http": "socks5h://127.0.0.1:9050"
}

# Crawl a given URL using a random User-Agent and Tor proxy
def crawl_page(url):
    header = {
        "User-Agent": ua.random,
        "Cookie": "dcap=..."  # Static cookie value for access
    }
    response = requests.get(url, proxies=proxy, headers=header)
    return response

# Save the HTML content of a response to a file
def save_file(response, subdread, id='home'):
    content = response.text
    html_path = f"webpages/{subdread}/dread_message_{id}.html"
    with open(html_path, 'w') as f:
        f.write(content)
        return html_path

# Read the content of a previously saved HTML file
def open_file(path):
    with open(path, 'r') as f:
        content = f.read()
    return content

# Extract post links from a Dread page
def scrape_links(content):
    soup = BeautifulSoup(content, features='html.parser')
    href = [a['href'] for a in soup.find_all(name='a', attrs={'class': 'title'})]
    return href

# Crawl individual post pages using the extracted links
def crawl_posts(url_posts, subdread):
    print(len(url_posts))
    dread_url = 'http://dreadytofatroptsdj6io7l3xptbet6onoyno2yv7jicoxknyazubrad.onion'
    for url_post in url_posts:
        unique_url = url_post[-20:]  # Use last 20 characters as unique ID
        file_path = f"webpages/{subdread}/dread_message_{unique_url}.html"

        # Skip if already downloaded
        if os.path.exists(file_path):
            print("Page already crawled")
            continue

        # Otherwise, download and save
        print(f"Scraping page {url_post}")
        complete_url = dread_url + url_post
        response = crawl_page(complete_url)
        save_file(response, subdread, unique_url)

# Main execution
if __name__ == '__main__':
    for page_id in range(1, 670):  # Loop through pages 1 to 669
        start_time = time.time()
        print(page_id)

        # Build the URL for the listing page
        subdread = '' # Manually choose the subdread to crawl (we did Psychedelics, XANAX, DrugManufacture, LSD, DankNation, and DrugHub)
        start_page = f'http://dreadytofatroptsdj6io7l3xptbet6onoyno2yv7jicoxknyazubrad.onion/d/{subdread}?p={page_id}'
        

        # Crawl the listing page and save it
        response = crawl_page(start_page)
        path = save_file(response, subdread, id=f"home_{page_id}")

        # Parse the listing page to get post links
        content = open_file(path)
        url_posts = scrape_links(content)

        # Crawl each post in the listing
        crawl_posts(url_posts, subdread)

        end_time = time.time()
        print(f"Page {page_id} crawled within {end_time - start_time} seconds")

    print('done')
