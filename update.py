import yfinance as yf
import feedparser
import datetime
import re
import time

def get_price(ticker):
    try:
        stock = yf.Ticker(ticker)
        # 1일치 데이터 가져오기
        hist = stock.history(period="1d")
        if not hist.empty:
            return hist['Close'].iloc[-1]
        return None
    except Exception as e:
        print(f"Error fetching {ticker}: {e}")
        return None

# 1. 데이터 가져오기
print("1. Fetching Market Data...")
kospi = get_price("^KS11")
sp500 = get_price("^GSPC")
usdkrw = get_price("KRW=X")

# 2. 뉴스 가져오기 (RSS)
print("2. Fetching News...")
rss_urls = [
    ("https://news.google.com/rss/search?q=stock+market+korea+headline&hl=ko&gl=KR&ceid=KR:ko", "📈 증시 주요 뉴스"),
    ("https://news.google.com/rss/search?q=robot+technology+industry+korea&hl=ko&gl=KR&ceid=KR:ko", "🤖 로봇/기술 뉴스")
]

news_html = ""
for url, title in rss_urls:
    try:
        feed = feedparser.parse(url)
        news_html += f"<div class='news-group'><h4>{title}</h4><ul>"
        for entry in feed.entries[:5]: # 5개씩 가져오기
            pub_date = entry.published_parsed
            date_str = time.strftime("%m-%d %H:%M", pub_date) if pub_date else ""
            news_html += f"<li class='news-item'><a href='{entry.link}' target='_blank'>{entry.title}</a> <span class='news-date'>({date_str})</span></li>"
        news_html += "</ul></div>"
    except Exception as e:
        print(f"Error fetching news {url}: {e}")

# 3. HTML 파일 업데이트
html_file = 'index.html'
with open(html_file, 'r', encoding='utf-8') as f:
    content = f.read()

# 날짜
now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

# 정규표현식으로 내용 교체 (내용이 무엇이든 id가 맞으면 무조건 교체)
if kospi:
    content = re.sub(r'<p id="kospi-val">.*?</p>', f'<p id="kospi-val">{kospi:,.2f}</p>', content)
if sp500:
    content = re.sub(r'<p id="sp500-val">.*?</p>', f'<p id="sp500-val">{sp500:,.2f}</p>', content)
if usdkrw:
    content = re.sub(r'<p id="exchange-val">.*?</p>', f'<p id="exchange-val">{usdkrw:,.2f} 원</p>', content)

# 뉴스 섹션 교체
content = re.sub(r'(<div id="news-content">).*?(</div>)', f'\\1{news_html}\\2', content, flags=re.DOTALL)

# 업데이트 시간
content = re.sub(r'(<span id="last-updated">).*?(</span>)', f'\\1{now}\\2', content)

with open(html_file, 'w', encoding='utf-8') as f:
    f.write(content)

print("Update Complete.")
