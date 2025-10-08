This project is a Flask-based chatbot that helps users interact with CapillaryTech documentation.
It first scrapes the official documentation using app.py (BeautifulSoup + Requests) and stores it as JSON.
Then, server.py loads that data to power an AI-like chatbot that answers technical queries with relevant details, bullet summaries, and source links.

Features:

Python web scraping

Keyword-based search & smart responses

Interactive chat API via Flask

Run:

python app.py   # Scrape docs  it take 3 min to scrape then run the server file
python server.py  # Start chatbot server
