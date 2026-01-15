import yfinance as yf
import feedparser
import datetime
import urllib.parse
import time

def make_sparkline_url(data_list, color):
    if not data_list or len(data_list) < 2:
        return "https://via.placeholder.com/200x50?text=No+Chart"
    
    # 데이터 포인트 축소 (최근 30일)
    data_str = ",".join([f"{x:.2f}" for x in data_list[-30:]])
    
    # QuickChart API
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

def get_market_data(ticker, color):
    print(f"Fetching {ticker}...")
    try:
        stock = yf.Ticker(ticker)
        # 1달치 데이터
        hist = stock.history(period="1mo")
        if hist.empty:
            return "N/A", ""
            
        current_price = hist['Close'].iloc[-1]
        chart_url = make_sparkline_url(hist['Close'].tolist(), color)
        
        if ticker == "KRW=X":
            price_str = f"{current_price:,.2f} 원"
        else:
            price_str = f"{current_price:,.2f}"
            
        return price_str, chart_url
    except Exception as e:
        print(f"Error: {e}")
        return "Error", ""

# 데이터 가져오기
kospi_val, kospi_chart = get_market_data("^KS11", "red")
sp500_val, sp500_chart = get_market_data("^GSPC", "blue")
usdkrw_val, usdkrw_chart = get_market_data("KRW=X", "green")

# 뉴스 가져오기
print("Fetching News...")
rss_urls = [
    ("https://news.google.com/rss/search?q=stock+market+korea+headline&hl=ko&gl=KR&ceid=KR:ko", "📈 증시 주요 뉴스"),
    ("https://news.google.com/rss/search?q=robot+technology+industry+korea&hl=ko&gl=KR&ceid=KR:ko", "🤖 로봇 산업 뉴스"),
    ("https://news.google.com/rss/search?q=robot+gripper+hand+technology&hl=ko&gl=KR&ceid=KR:ko", "🦾 로봇 핸드 기술")
]

news_html = ""
for url, title in rss_urls:
    try:
        feed = feedparser.parse(url)
        news_html += f"<div class='news-group'><h4>{title}</h4><ul class='news-list'>"
        for entry in feed.entries[:4]:
            dt = entry.published_parsed
            date_str = time.strftime("%m-%d", dt) if dt else ""
            news_html += f"<li class='news-item'><a href='{entry.link}' target='_blank'>{entry.title}</a> <span class='news-date'>({date_str})</span></li>"
        news_html += "</ul></div>"
    except:
        news_html += f"<p>뉴스 로딩 실패: {title}</p>"

# ★ 핵심: template.html을 읽어서 index.html로 저장 ★
print("Writing index.html...")
with open('template.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 데이터 교체
content = content.replace('{{KOSPI_VAL}}', str(kospi_val))
content = content.replace('{{KOSPI_CHART}}', str(kospi_chart))
content = content.replace('{{SP500_VAL}}', str(sp500_val))
content = content.replace('{{SP500_CHART}}', str(sp500_chart))
content = content.replace('{{USDKRW_VAL}}', str(usdkrw_val))
content = content.replace('{{USDKRW_CHART}}', str(usdkrw_chart))
content = content.replace('{{NEWS_CONTENT}}', news_html)
content = content.replace('{{LAST_UPDATED}}', datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

with open('index.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("Done.")
