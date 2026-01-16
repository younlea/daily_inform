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
# 3. 한국 주요 주식 (링크 포함)
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
# 4. 뉴스 수집 (검색 로직 개선: 신규 모델 발굴)
# ---------------------------------------------------------
print("3. 뉴스 수집 (카테고리별 분류)...")

rss_sources = [
    # [그룹 1] 국내외 증시 & 경제
    {
        "url": "https://news.google.com/rss/search?q=stock+market+economy+korea+usa&hl=ko&gl=KR&ceid=KR:ko", 
        "title": "📈 국내외 증시 & 경제", 
        "limit": 4 
    },
    
    # [그룹 2] 휴머노이드 로봇 (신규 모델 발굴 강화)
    # 검색어 설명: "휴머노이드 로봇" + (스타트업 OR 공개 OR 프로토타입 OR 신규) -청소기
    {
        "url": "https://news.google.com/rss/search?q=humanoid+robot+(startup+OR+unveiled+OR+prototype+OR+new+model)+-vacuum+-cleaner&hl=ko&gl=KR&ceid=KR:ko", 
        "title": "🤖 휴머노이드 & 신규 로봇", 
        "limit": 4 
    },
    {
        # 전문 매체 (기술 블로그는 신기술 소식이 가장 빠름)
        "url": "https://humanoidroboticstechnology.com/feed/", 
        "title": "🤖 Humanoid Tech (Global Blog)", 
        "limit": 2
    },

    # [그룹 3] 휴머노이드 핸드 & 그리퍼
    {
        "url": "https://news.google.com/rss/search?q=robot+hand+gripper+dexterous+manipulation+tactile+sensor+-vacuum&hl=ko&gl=KR&ceid=KR:ko", 
        "title": "🦾 휴머노이드 핸드 & 그리퍼 기술", 
        "limit": 4
    }
]

news_content_html = ""
today = datetime.datetime.now()

for source in rss_sources:
    try:
        feed = feedparser.parse(source["url"], agent="Mozilla/5.0")
        filtered_entries = []
        
        # 날짜 필터링 (최근 5일)
        for entry in feed.entries:
            pub_dt = None
            if hasattr(entry, 'published_parsed') and entry.published_parsed:
                pub_dt = datetime.datetime.fromtimestamp(time.mktime(entry.published_parsed))
            elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                pub_dt = datetime.datetime.fromtimestamp(time.mktime(entry.updated_parsed))
            
            if pub_dt and (today - pub_dt).days <= 5:
                filtered_entries.append((entry, pub_dt))
        
        # 최신순 정렬
        filtered_entries.sort(key=lambda x: x[1], reverse=True)
        
        if filtered_entries:
            news_content_html += f"<div class='news-category'><h4><span class='badge'>{source['title']}</span></h4><ul class='news-list'>"
            for entry, pub_dt in filtered_entries[:source["limit"]]:
                diff_days = (today - pub_dt).days
                if diff_days == 0: date_txt = "Today"
                elif diff_days == 1: date_txt = "Yesterday"
                else: date_txt = pub_dt.strftime("%m-%d")
                
                news_content_html += f"""
                <li class='news-item'>
                    <a href='{entry.link}' target='_blank'>{entry.title}</a>
                    <span class='news-time'>{date_txt}</span>
                </li>
                """
            news_content_html += "</ul></div>"
            
    except Exception as e:
        print(f"Error fetching {source['title']}: {e}")

if not news_content_html:
    news_content_html = "<div style='text-align:center; color:#888;'>최근 관련 뉴스가 없습니다.</div>"

# ---------------------------------------------------------
# 5. 파일 저장 (한국 시간 적용)
# ---------------------------------------------------------
print("4. HTML 생성...")

utc_now = datetime.datetime.now(datetime.timezone.utc)
kst_now = utc_now + datetime.timedelta(hours=9)
now_str = kst_now.strftime("%Y-%m-%d %H:%M:%S (KST)")

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

print(f"업데이트 완료: {now_str}")
