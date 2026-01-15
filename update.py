import yfinance as yf
import feedparser
import datetime
import re
import time
import urllib.parse

# 차트 생성을 위한 함수 (QuickChart 사용)
def make_sparkline_url(data_list, color='blue'):
    if not data_list:
        return ""
    # 데이터가 너무 많으면 URL이 길어지므로 최근 30개만 사용
    data_str = ",".join([f"{x:.2f}" for x in data_list[-30:]])
    
    # QuickChart API URL 생성 (배경 투명, 선 그래프, 포인트 없음)
    chart_config = f"""
    {{
        type: 'sparkline',
        data: {{
            datasets: [{{
                data: [{data_str}],
                borderColor: '{color}',
                borderWidth: 2,
                fill: false,
                pointRadius: 0
            }}]
        }}
    }}
    """
    base_url = "https://quickchart.io/chart?c="
    return base_url + urllib.parse.quote(chart_config)

def get_market_data(ticker, color='rgba(0, 116, 217, 1)'):
    try:
        stock = yf.Ticker(ticker)
        # 1달치 데이터 가져오기 (그래프용)
        hist = stock.history(period="1mo")
        if not hist.empty:
            current_price = hist['Close'].iloc[-1]
            price_list = hist['Close'].tolist()
            chart_url = make_sparkline_url(price_list, color)
            return current_price, chart_url
        return None, None
    except Exception as e:
        print(f"Error fetching {ticker}: {e}")
        return None, None

# 1. 데이터 가져오기 (가격 및 차트 URL)
print("1. Fetching Market Data...")
# KOSPI (빨간색 계열), S&P500 (파란색 계열), 환율 (초록색 계열)
kospi_val, kospi_chart = get_market_data("^KS11", "red")
sp500_val, sp500_chart = get_market_data("^GSPC", "blue")
usdkrw_val, usdkrw_chart = get_market_data("KRW=X", "green")

# 2. 뉴스 가져오기 (RSS)
print("2. Fetching News...")
rss_urls = [
    ("https://news.google.com/rss/search?q=stock+market+korea+headline&hl=ko&gl=KR&ceid=KR:ko", "📈 증시 주요 뉴스"),
    ("https://news.google.com/rss/search?q=robot+technology+industry+korea&hl=ko&gl=KR&ceid=KR:ko", "🤖 로봇/기술 뉴스"),
    ("https://news.google.com/rss/search?q=robot+gripper+hand+technology&hl=ko&gl=KR&ceid=KR:ko", "🦾 로봇 핸드 & 그리퍼 기술")
]

news_html = ""
for url, title in rss_urls:
    try:
        feed = feedparser.parse(url)
        news_html += f"<div class='news-group'><h4>{title}</h4><ul>"
        # 뉴스 항목이 없으면 메시지 표시
        if not feed.entries:
             news_html += "<li class='news-item'>최근 관련 뉴스가 없습니다.</li>"
        else:
            for entry in feed.entries[:4]: # 4개씩 가져오기
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

# 값 교체 로직
if kospi_val:
    content = re.sub(r'<p id="kospi-val">.*?</p>', f'<p id="kospi-val">{kospi_val:,.2f}</p>', content)
    content = re.sub(r'<img id="kospi-chart" class="chart-img" src=".*?"', f'<img id="kospi-chart" class="chart-img" src="{kospi_chart}"', content)

if sp500_val:
    content = re.sub(r'<p id="sp500-val">.*?</p>', f'<p id="sp500-val">{sp500_val:,.2f}</p>', content)
    content = re.sub(r'<img id="sp500-chart" class="chart-img" src=".*?"', f'<img id="sp500-chart" class="chart-img" src="{sp500_chart}"', content)

if usdkrw_val:
    content = re.sub(r'<p id="exchange-val">.*?</p>', f'<p id="exchange-val">{usdkrw_val:,.2f} 원</p>', content)
    content = re.sub(r'<img id="exchange-chart" class="chart-img" src=".*?"', f'<img id="exchange-chart" class="chart-img" src="{usdkrw_chart}"', content)

# 뉴스 섹션 교체
content = re.sub(r'(<div id="news-content">).*?(</div>)', f'\\1{news_html}\\2', content, flags=re.DOTALL)

# 업데이트 시간
content = re.sub(r'(<span id="last-updated">).*?(</span>)', f'\\1{now}\\2', content)

with open(html_file, 'w', encoding='utf-8') as f:
    f.write(content)

print("Update Complete.")
