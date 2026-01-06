import datetime
import queue
import traceback
from bs4 import BeautifulSoup
import json
import requests

BASE_URL = "https://www.walmart.com"
OUTPUT_FILE = "product_info.jsonl"
ERRORS_LOG_FILE = "errors.txt"

BASE_HEADERS = {
    "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "accept": "application/json",
    "accept-language": "en-US",
    "accept-encoding": "gzip, deflate, br, zstd",
}

search_queries = ["computers", "laptops", "desktops", "monitors", "printers", "hard+drives", "usb", "cords", "cameras", 
                  "mouse", "keyboard", "microphones", "speakers", "radio", "tablets", "android", "apple", "watch", "smart+watch", 
                  "fridge", "airconditioning", "wifi", "router", "modem", "desk", "xbox", "playstation", "nintendo"]


# Initialize a queue for product URLs and a set for seen URLs
product_queue = queue.Queue()
seen_urls = set()

def get_product_links(query, page_number=1):
    search_url = f"https://www.walmart.ca/en/search?q={query}&page={page_number}"
    
    response = requests.get(search_url, headers=BASE_HEADERS)
    
    soup = BeautifulSoup(response.text, "html.parser")
    
    links = soup.find_all('a', href=True)
    
    product_links = []
    
    for link in links:
        link_href = link["href"]
        if "/ip/" in link['href']:
            if "https" in link_href:
                full_url = link_href
            else:
                full_url = "https://walmart.com" + link_href
                
            product_links.append(full_url)
            
    return product_links 

def extract_initial_data(page_props):
    # Try exact match first
    if "initialData" in page_props:
        return page_props["initialData"].get("data", {})
    # Fallback: scan for a key that matches the pattern
    for key in page_props:
        if key.startswith("initial") and key.endswith("Data"):
            return page_props[key].get("data", {})
    return {}

def extract_product_info(product_url):

    response = requests.get(product_url, headers=BASE_HEADERS)

    webpage = BeautifulSoup(response.text, "html.parser")
 
    script_tag = webpage.find("script", id="__NEXT_DATA__")

    data = json.loads(script_tag.string)
    page_props = data.get("props", {}).get("pageProps", {})
    initial_data = extract_initial_data(page_props)
    product_data = initial_data["product"]
    reviews_data = initial_data.get("reviews", {})

    product_info = {
        "price": product_data["priceInfo"]["currentPrice"]["price"],
        "review_count": reviews_data.get("totalReviewCount", 0), 
        "item_id": product_data["usItemId"],
        "avg_rating": reviews_data.get("averageOverallRating", 0),
        "product_name": product_data["name"],
        "brand": product_data.get("brand", ""),
        "availability": product_data["availabilityStatus"],
        "image_url": product_data["imageInfo"]["thumbnailUrl"],
        "short_description": product_data.get("shortDescription", "")
        }

    return product_info

def log_error(url, exc, log_path="errors.txt"):
    with open(log_path, "a", encoding="utf-8") as log_file:
        log_file.write("-----\n")
        log_file.write(f"[{datetime.datetime.now().isoformat()}] ERROR for {url}\n")
        log_file.write("Exception: " + repr(exc) + "\n")
        log_file.write("Traceback:\n")
        log_file.write("".join(traceback.format_exception(type(exc), exc, exc.__traceback__)))
        log_file.write("\n")
        
def trim_error_log(log_path="errors.txt", max_lines=500):
    try:
        with open(log_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except FileNotFoundError:
        return  # nothing to trim yet

    if len(lines) <= max_lines:
        return  # nothing to trim

    trimmed = lines[-max_lines:]

    with open(log_path, "w", encoding="utf-8") as f:
        f.writelines(trimmed)

def main():
    
  trim_error_log(ERRORS_LOG_FILE, max_lines=500)

  with open(OUTPUT_FILE, "w") as file:
        page_number = 1
        for search in search_queries:
            product_links = get_product_links(search, page_number)
            if not product_links or page_number > 99:
                continue
            
            for link in product_links:
                if link not in seen_urls:
                    product_queue.put(link)
                    seen_urls.add(link)
            
            while not product_queue.empty():
                product_url = product_queue.get()
                
                try:
                    product_info = extract_product_info(product_url)
                    if product_info:
                        file.write(json.dumps(product_info)+"\n")
                except Exception as e:
                    log_error(product_url, e, ERRORS_LOG_FILE)
            
            page_number += 1
            
                
      
if __name__ == "__main__":
    main()