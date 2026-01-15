import yfinance as yf
import feedparser
import datetime
import re

# 1. 데이터 가져오기 (KOSPI, S&P500, 원달러 환율)
tickers = {'^KS11': 'kospi-val', '^GSPC': 'sp500-val', 'KRW=X': 'exchange-val'}
data_html = ""

print("Fetching Market Data...")
for ticker, element_id in tickers.items():
    try:
        stock = yf.Ticker(ticker)
        # 최신 종가 가져오기
        hist = stock.history(period="1d")
        if not hist.empty:
            price = hist['Close'].iloc[-1]
            # 포맷팅 (환율은 소수점 2자리, 지수는 소수점 2자리)
            formatted_price = f"{price:,.2f}"
            data_html += f"document.getElementById('{element_id}').innerText = '{formatted_price}';\n"
    except Exception as e:
        print(f"Error fetching {ticker}: {e}")

# 2. 뉴스 가져오기 (Google News RSS - 증시, 로봇)
# 실제 '요약'을 위해서는 OpenAI API 등을 이곳에 연동해야 합니다.
rss_urls = [
    ("https://news.google.com/rss/search?q=stock+market+korea&hl=ko&gl=KR&ceid=KR:ko", "증시 관련 뉴스"),
    ("https://news.google.com/rss/search?q=robot+industry+korea&hl=ko&gl=KR&ceid=KR:ko", "로봇 관련 뉴스")
]

news_html_content = ""

print("Fetching News...")
for url, title in rss_urls:
    feed = feedparser.parse(url)
    news_html_content += f"<h4>{title}</h4><ul>"
    # 상위 3개 뉴스만 추출
    for entry in feed.entries[:3]:
        news_html_content += f"<li class='news-item'><a href='{entry.link}' target='_blank'>{entry.title}</a> <span class='news-date'>({entry.published})</span></li>"
    news_html_content += "</ul>"

# 3. HTML 파일 업데이트
html_file = 'index.html'
with open(html_file, 'r', encoding='utf-8') as f:
    content = f.read()

# 날짜 업데이트
now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# 데이터 삽입 (Javascript로 값 변경하는 방식이 아닌, HTML 직접 수정 방식 사용 for static page)
# 정규표현식으로 기존 값 대체
content = re.sub(r'<p id="kospi-val">.*?</p>', f'<p id="kospi-val">{yf.Ticker("^KS11").history(period="1d")["Close"].iloc[-1]:,.2f}</p>', content)
content = re.sub(r'<p id="sp500-val">.*?</p>', f'<p id="sp500-val">{yf.Ticker("^GSPC").history(period="1d")["Close"].iloc[-1]:,.2f}</p>', content)
content = re.sub(r'<p id="exchange-val">.*?</p>', f'<p id="exchange-val">{yf.Ticker("KRW=X").history(period="1d")["Close"].iloc[-1]:,.2f}</p>', content)

# 뉴스 섹션 교체
# id="news-content" 내부를 교체하기 위한 패턴
pattern_news = r'(<div id="news-content">).*?(</div>)'
replacement_news = f'\\1{news_html_content}\\2'
content = re.sub(pattern_news, replacement_news, content, flags=re.DOTALL)

# 업데이트 시간 교체
pattern_time = r'(<span id="last-updated">).*?(</span>)'
content = re.sub(pattern_time, f'\\1{now}\\2', content)

with open(html_file, 'w', encoding='utf-8') as f:
    f.write(content)

print("Update Complete.")
