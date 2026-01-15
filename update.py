import yfinance as yf
import feedparser
import datetime
import urllib.parse
import time

# ----------------------------------------
# 1. 퀵차트(QuickChart) URL 생성 함수
# ----------------------------------------
def make_sparkline_url(data_list, color='blue'):
    if not data_list or len(data_list) < 2:
        # 데이터 없으면 빈 투명 이미지 리턴
        return "https://quickchart.io/chart?c={type:'sparkline',data:{datasets:[{data:[0]}]}}"
    
    # 최근 30일 데이터만 사용
    data_str = ",".join([f"{x:.2f}" for x in data_list[-30:]])
    
    # 차트 설정
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
    return "https://quickchart.io/chart?c=" + urllib.parse.quote(chart_config)

# ----------------------------------------
# 2. 시장 데이터 가져오기 (가격 + 차트)
# ----------------------------------------
def get_market_data(ticker, color):
    try:
        print(f"Fetching {ticker}...")
        stock = yf.Ticker(ticker)
        # 1달치 데이터 요청
        hist = stock.history(period="1mo")
        
        if hist.empty:
            return "N/A", ""
            
        current_price = hist['Close'].iloc[-1]
        price_list = hist['Close'].tolist()
        chart_url = make_sparkline_url(price_list, color)
        
        # 포맷팅 (환율은 '원', 나머지는 그냥 숫자)
        if ticker == "KRW=X":
            price_str = f"{current_price:,.2f} 원"
        else:
            price_str = f"{current_price:,.2f}"
            
        return price_str, chart_url
    except Exception as e:
        print(f"Error fetching {ticker}: {e}")
        return "Error", ""

# 실행
kospi_val, kospi_chart = get_market_data("^KS11", "red")
sp500_val, sp500_chart = get_market_data("^GSPC", "blue")
usdkrw_val, usdkrw_chart = get_market_data("KRW=X", "green")

# ----------------------------------------
# 3. 뉴스 가져오기 (RSS)
# ----------------------------------------
print("Fetching News...")

rss_config = [
    ("https://news.google.com/rss/search?q=stock+market+korea+headline&hl=ko&gl=KR&ceid=KR:ko", "📈 증시 주요 뉴스"),
    ("https://news.google.com/rss/search?q=robot+technology+industry+korea&hl=ko&gl=KR&ceid=KR:ko", "🤖 로봇 산업 뉴스"),
    ("https://news.google.com/rss/search?q=robot+gripper+hand+technology&hl=ko&gl=KR&ceid=KR:ko", "🦾 로봇 핸드/그리퍼 기술")
]

news_html = ""

for url, title in rss_config:
    try:
        feed = feedparser.parse(url)
        news_html += f"<div class='news-group'><h4>{title}</h4><ul class='news-list'>"
        
        # 뉴스 4개씩만
        for entry in feed.entries[:4]:
            pub_date = entry.published_parsed
            date_str = time.strftime("%m-%d %H:%M", pub_date) if pub_date else ""
            news_html += f"<li class='news-item'><a href='{entry.link}' target='_blank'>{entry.title}</a> <span class='news-date'>({date_str})</span></li>"
        
        if not feed.entries:
            news_html += "<li class='news-item'>최근 관련 뉴스가 없습니다.</li>"
            
        news_html += "</ul></div>"
    except Exception as e:
        print(f"News Error {url}: {e}")
        news_html += f"<p>뉴스 로딩 실패: {title}</p>"

# ----------------------------------------
# 4. HTML 파일 읽고 구멍 채우기 (Replace 방식)
# ----------------------------------------
html_file = 'index.html'
now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

with open(html_file, 'r', encoding='utf-8') as f:
    content = f.read()

# 확실하게 치환 (Placeholder Replace)
content = content.replace('{{KOSPI_VAL}}', str(kospi_val))
content = content.replace('{{KOSPI_CHART}}', str(kospi_chart))

content = content.replace('{{SP500_VAL}}', str(sp500_val))
content = content.replace('{{SP500_CHART}}', str(sp500_chart))

content = content.replace('{{USDKRW_VAL}}', str(usdkrw_val))
content = content.replace('{{USDKRW_CHART}}', str(usdkrw_chart))

content = content.replace('{{NEWS_CONTENT}}', news_html)
content = content.replace('{{LAST_UPDATED}}', now_str)

# ----------------------------------------
# 5. 파일 저장
# ----------------------------------------
with open(html_file, 'w', encoding='utf-8') as f:
    f.write(content)

print("Update Complete Successfully.")
