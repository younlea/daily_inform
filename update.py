import yfinance as yf
import feedparser
import datetime
import urllib.parse
import time
from email.utils import parsedate_to_datetime

# ---------------------------------------------------------
# 1. 헬퍼 함수: 미니 차트 & 링크 생성
# ---------------------------------------------------------
def make_sparkline_url(data_list, color):
    if not data_list or len(data_list) < 2: return ""
    subset = data_list[-30:]
    data_str = ",".join([f"{x:.2f}" for x in subset])
    chart_config = f"{{type:'sparkline',data:{{datasets:[{{data:[{data_str}],borderColor:'{color}',borderWidth:2,fill:false,pointRadius:0}}]}}}}"
    return "https://quickchart.io/chart?c=" + urllib.parse.quote(chart_config)

# ---------------------------------------------------------
# 2. 시장 지수 (상단)
# ---------------------------------------------------------
def get_metric_data(ticker, color):
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="1mo")
        if hist.empty: return "N/A", "0.00%", ""
        current = hist['Close'].iloc[-1]
        prev = hist['Close'].iloc[-2]
        change = current - prev
        change_pct = (change / prev) * 100
        
        sign = "+" if change >= 0 else ""
        css_class = "text-red" if change >= 0 else "text-blue"
        
        val_str = f"{current:,.2f}"
        if ticker == "KRW=X": val_str += " 원"
        
        change_str = f"<span class='{css_class}'>{sign}{change:.2f} ({sign}{change_pct:.2f}%)</span>"
        chart_url = make_sparkline_url(hist['Close'].tolist(), color)
        return val_str, change_str, chart_url
    except: return "Error", "-", ""

print("1. 지수 데이터 수집...")
kospi_val, kospi_chg, kospi_chart = get_metric_data("^KS11", "red")
sp500_val, sp500_chg, sp500_chart = get_metric_data("^GSPC", "red")
usdkrw_val, usdkrw_chg, usdkrw_chart = get_metric_data("KRW=X", "green")

# ---------------------------------------------------------
# 3. 한국 주요 주식 (링크 추가됨)
# ---------------------------------------------------------
print("2. 한국 주식 데이터 수집...")
korea_tickers = [
    ('005930.KS', '삼성전자', '005930'),
    ('000660.KS', 'SK하이닉스', '000660'),
    ('373220.KS', 'LG에너지솔루션', '373220'),
    ('207940.KS', '삼성바이오로직스', '207940'),
    ('005380.KS', '현대차', '005380'),
    ('005490.KS', 'POSCO홀딩스', '005490'),
    ('000270.KS', '기아', '000270'),
    ('035420.KS', 'NAVER', '035420')
]

korea_table_html = "<table class='stock-table'><thead><tr><th>종목명</th><th>현재가</th><th>등락률</th><th>추세(1달)</th></tr></thead><tbody>"

for code, name, naver_code in korea_tickers:
    try:
        stock = yf.Ticker(code)
        hist = stock.history(period="1mo")
        if not hist.empty:
            curr = hist['Close'].iloc[-1]
            prev = hist['Close'].iloc[-2]
            pct = ((curr - prev) / prev) * 100
            
            if pct > 0:
                color_cls = "bg-red-light text-red"
                sign = "+"
                line_color = "red"
            elif pct < 0:
                color_cls = "bg-blue-light text-blue"
                sign = ""
                line_color = "blue"
            else:
                color_cls = "text-gray"
                sign = ""
                line_color = "gray"
            
            chart = make_sparkline_url(hist['Close'].tolist(), line_color)
            
            # ★ 네이버 금융 링크 생성 ★
            link_url = f"https://finance.naver.com/item/main.naver?code={naver_code}"
            
            korea_table_html += f"""
            <tr onclick="window.open('{link_url}', '_blank')" style="cursor:pointer;">
                <td>
                    <span class='stock-name'>{name} 🔗</span>
                    <span class='stock-code'>{code}</span>
                </td>
                <td class='stock-price'>{curr:,.0f}원</td>
                <td><span class='{color_cls}'>{sign}{pct:.2f}%</span></td>
                <td><img src='{chart}' style='height:30px; width:80px;'></td>
            </tr>
            """
    except Exception as e:
        print(f"Error {name}: {e}")

korea_table_html += "</tbody></table>"

# ---------------------------------------------------------
# 4. 뉴스 (엄격한 날짜 필터링)
# ---------------------------------------------------------
print("3. 뉴스 수집 및 날짜 필터링...")
# 검색어 최적화
rss_list = [
    ("https://news.google.com/rss/search?q=stock+market+korea&hl=ko&gl=KR&ceid=KR:ko", "📈 국내 증시"),
    ("https://news.google.com/rss/search?q=robot+industry+news+korea&hl=ko&gl=KR&ceid=KR:ko", "🤖 로봇 산업"),
    ("https://news.google.com/rss/search?q=robot+gripper+technology&hl=ko&gl=KR&ceid=KR:ko", "🦾 로봇 기술")
]

news_content_html = ""
today = datetime.datetime.now()

for url, category in rss_list:
    try:
        feed = feedparser.parse(url)
        filtered_entries = []
        
        # ★ 날짜 필터링 로직 (최근 3일 이내만) ★
        for entry in feed.entries:
            if hasattr(entry, 'published_parsed'):
                pub_date = datetime.datetime.fromtimestamp(time.mktime(entry.published_parsed))
                # 3일(72시간) 이내 기사만 통과
                if (today - pub_date).days <= 3:
                    filtered_entries.append(entry)
        
        # 걸러진 기사가 있을 때만 카테고리 표시
        if filtered_entries:
            news_content_html += f"<div class='news-category'><h4><span class='badge'>{category}</span></h4><ul class='news-list'>"
            for entry in filtered_entries[:3]: # 카테고리 당 최대 3개
                pub_dt = datetime.datetime.fromtimestamp(time.mktime(entry.published_parsed))
                # 날짜 표시 (오늘/어제)
                diff_days = (today - pub_dt).days
                if diff_days == 0: date_txt = "오늘"
                elif diff_days == 1: date_txt = "어제"
                else: date_txt = pub_dt.strftime("%m-%d")
                
                news_content_html += f"""
                <li class='news-item'>
                    <a href='{entry.link}' target='_blank'>{entry.title}</a>
                    <span class='news-time'>{date_txt}</span>
                </li>
                """
            news_content_html += "</ul></div>"
            
    except Exception as e:
        print(f"News Error: {e}")

if not news_content_html:
    news_content_html = "<div style='text-align:center; color:#888; padding:20px;'>최근 3일간 주요 뉴스가 없습니다.</div>"

# ---------------------------------------------------------
# 5. 파일 저장
# ---------------------------------------------------------
print("4. HTML 생성...")
now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

with open('template.html', 'r', encoding='utf-8') as f:
    template = f.read()

output = template.replace('{{LAST_UPDATED}}', now_str)
output = output.replace('{{KOSPI_VAL}}', kospi_val).replace('{{KOSPI_CHANGE}}', kospi_chg).replace('{{KOSPI_CHART}}', kospi_chart)
output = output.replace('{{SP500_VAL}}', sp500_val).replace('{{SP500_CHANGE}}', sp500_chg).replace('{{SP500_CHART}}', sp500_chart)
output = output.replace('{{USDKRW_VAL}}', usdkrw_val).replace('{{USDKRW_CHANGE}}', usdkrw_chg).replace('{{USDKRW_CHART}}', usdkrw_chart)
output = output.replace('{{KOREA_MARKET_HTML}}', korea_table_html)
output = output.replace('{{NEWS_CONTENT}}', news_content_html)

with open('index.html', 'w', encoding='utf-8') as f:
    f.write(output)

print("업데이트 완료.")
