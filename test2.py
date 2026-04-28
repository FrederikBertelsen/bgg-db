import cloudscraper

url = "https://boardgamegeek.com/boardgame/342942"

scraper = cloudscraper.create_scraper()
response = scraper.get(url)

print(response.status_code)
print(response.text[:1000])  # print the first 1000 characters of the HTML
