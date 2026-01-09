import requests
from bs4 import BeautifulSoup
import pandas as pd


def get_articles_from_page(page_number=1):
    
    url = f"https://books.toscrape.com/catalogue/page-{page_number}.html"

    response = requests.get(url)

    content = response.content

    soup = BeautifulSoup(content, 'html.parser')

    list_of_books = soup.find('ol')

    book_articles = list_of_books.find_all('article', class_='product_pod')
        
    return book_articles


def main():
    
    books = []
    
    for page in range(1, 5):
        
        articles = get_articles_from_page(page)
        
        for article in articles:
            image = article.find('img')
            title = image['alt']
            rating = article.find('p')['class'][1]
            price = article.find('p', class_='price_color').string
            price = float(price[1:])
            books.append([title, price, rating])
    
    df = pd.DataFrame(books, columns=['Title', 'Price', 'Star Rating'])
    df.to_csv('books.csv')
    
    
if __name__ == "__main__":
    main()