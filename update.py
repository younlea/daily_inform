import yfinance as yf
import feedparser
import datetime
import urllib.parse
import time
from email.utils import parsedate_to_datetime

# ---------------------------------------------------------
# 1. 헬퍼 함수
# ---------------------------------------------------------
def make_sparkline_url(data_list, color):
    if not data_list or len(data_list) < 2: return ""
    subset = data_list[-30:]
    data_str = ",".join([f"{x:.2f}" for x in subset])
    chart_config = f"{{type:'sparkline',data:{{datasets:[{{data:[{data_str}],borderColor:'{color}',borderWidth:2,fill:false,pointRadius:0}}]}}}}"
    return "https://quickchart.io/chart?c=" + urllib.parse.quote(chart_config)

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

# ---------------------------------------------------------
# 2. 시장 데이터 수집
# ---------------------------------------------------------
print("1. 시장 데이터 수집...")
kospi_val, kospi_chg, kospi_chart = get_metric_data("^KS11", "red")
sp500_val, sp500_chg, sp500_chart = get_metric_data("^GSPC", "red")
usdkrw_val, usdkrw_chg, usdkrw_chart = get_metric_data("KRW=X", "green")

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
            if pct > 0: color_cls, sign, line_color = "bg-red-light text-red", "+", "red"
            elif pct < 0: color_cls, sign, line_color = "bg-blue-light text-blue", "", "blue"
            else: color_cls, sign, line_color = "text-gray", "", "gray"
            chart = make_sparkline_url(hist['Close'].tolist(), line_color)
            link_url = f"https://finance.naver.com/item/main.naver?code={naver_code}"
            korea_table_html += f"<tr onclick=\"window.open('{link_url}', '_blank')\" style=\"cursor:pointer;\"><td><span class='stock-name'>{name} 🔗</span><span class='stock-code'>{code}</span></td><td class='stock-price'>{curr:,.0f}원</td><td><span class='{color_cls}'>{sign}{pct:.2f}%</span></td><td><img src='{chart}' style='height:30px; width:80px;'></td></tr>"
    except: pass
korea_table_html += "</tbody></table>"

# ---------------------------------------------------------
# 3. 뉴스 수집 및 HTML 생성 함수
# ---------------------------------------------------------
print("2. 뉴스 데이터 수집...")
today = datetime.datetime.now()

# 뉴스 항목을 HTML 리스트(<li>)로 변환해주는 함수
def generate_news_list(entries, limit, style="simple"):
    html = ""
    for entry, pub_dt in entries[:limit]:
        diff_days = (today - pub_dt).days
        if diff_days == 0: date_txt = "Today"
        elif diff_days == 1: date_txt = "Yesterday"
        else: date_txt = pub_dt.strftime("%m-%d")
        
        if style == "simple": # 메인 페이지용
            html += f"<li class='news-item'><a href='{entry.link}' target='_blank'>{entry.title}</a> <span class='news-time'>{date_txt}</span></li>"
        else: # 뉴스 전용 페이지용 (카드 형태)
            source_name = entry.get('source', {}).get('title', 'News')
            html += f"""
            <div class='news-card'>
                <a href='{entry.link}' target='_blank' class='news-title'>{entry.title}</a>
                <div class='news-meta'>
                    <span class='source-badge'>{source_name}</span>
                    <span>{date_txt}</span>
                </div>
            </div>
            """
    return html

# 뉴스 소스 정의
rss_economy = [{"url": "https://news.google.com/rss/search?q=stock+market+economy+korea+usa&hl=ko&gl=KR&ceid=KR:ko", "title": "📈 국내외 증시"}]
rss_humanoid = [
    {"url": "https://news.google.com/rss/search?q=humanoid+robot+(startup+OR+unveiled+OR+prototype+OR+new+model)+-vacuum&hl=ko&gl=KR&ceid=KR:ko", "title": "Google News"},
    {"url": "https://humanoidroboticstechnology.com/feed/", "title": "Humanoid Tech Blog"}
]
rss_hand = [
    {"url": "https://news.google.com/rss/search?q=robot+hand+gripper+dexterous+manipulation+tactile+sensor+-vacuum&hl=ko&gl=KR&ceid=KR:ko", "title": "Google News"}
]

# RSS 파싱 및 통합 함수
def fetch_and_sort(sources, days_limit=5):
    all_entries = []
    for src in sources:
        try:
            feed = feedparser.parse(src["url"], agent="Mozilla/5.0")
            for entry in feed.entries:
                pub_dt = None
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    pub_dt = datetime.datetime.fromtimestamp(time.mktime(entry.published_parsed))
                elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                    pub_dt = datetime.datetime.fromtimestamp(time.mktime(entry.updated_parsed))
                
                if pub_dt and (today - pub_dt).days <= days_limit:
                    # 소스 타이틀 주입
                    if not hasattr(entry, 'source'): entry['source'] = {}
                    entry['source']['title'] = src['title']
                    all_entries.append((entry, pub_dt))
        except: pass
    all_entries.sort(key=lambda x: x[1], reverse=True)
    return all_entries

# 데이터 가져오기
entries_economy = fetch_and_sort(rss_economy)
entries_humanoid = fetch_and_sort(rss_humanoid)
entries_hand = fetch_and_sort(rss_hand)

# ---------------------------------------------------------
# 4. HTML 파일 2개 생성 (Main & News Page)
# ---------------------------------------------------------
print("3. HTML 페이지 생성...")
utc_now = datetime.datetime.now(datetime.timezone.utc)
kst_now = utc_now + datetime.timedelta(hours=9)
now_str = kst_now.strftime("%Y-%m-%d %H:%M:%S (KST)")

# [A] 메인 페이지 (index.html) 생성
# 메인용 뉴스 HTML 조립 (각 섹션별 소량만)
main_news_html = ""
if entries_economy:
    main_news_html += f"<div class='news-category'><h4><span class='badge'>📈 증시/경제</span></h4><ul class='news-list'>{generate_news_list(entries_economy, 4, 'simple')}</ul></div>"
if entries_humanoid:
    main_news_html += f"<div class='news-category'><h4><span class='badge'>🤖 휴머노이드</span></h4><ul class='news-list'>{generate_news_list(entries_humanoid, 4, 'simple')}</ul></div>"
if entries_hand:
    main_news_html += f"<div class='news-category'><h4><span class='badge'>🦾 핸드/그리퍼</span></h4><ul class='news-list'>{generate_news_list(entries_hand, 4, 'simple')}</ul></div>"

with open('template.html', 'r', encoding='utf-8') as f:
    template = f.read()
output_main = template.replace('{{LAST_UPDATED}}', now_str)
output_main = output_main.replace('{{KOSPI_VAL}}', kospi_val).replace('{{KOSPI_CHANGE}}', kospi_chg).replace('{{KOSPI_CHART}}', kospi_chart)
output_main = output_main.replace('{{SP500_VAL}}', sp500_val).replace('{{SP500_CHANGE}}', sp500_chg).replace('{{SP500_CHART}}', sp500_chart)
output_main = output_main.replace('{{USDKRW_VAL}}', usdkrw_val).replace('{{USDKRW_CHANGE}}', usdkrw_chg).replace('{{USDKRW_CHART}}', usdkrw_chart)
output_main = output_main.replace('{{KOREA_MARKET_HTML}}', korea_table_html)
output_main = output_main.replace('{{NEWS_CONTENT}}', main_news_html)

with open('index.html', 'w', encoding='utf-8') as f:
    f.write(output_main)

# [B] 뉴스 전용 페이지 (news.html) 생성
# 뉴스용 HTML 조립 (대량 노출)
humanoid_full_html = generate_news_list(entries_humanoid, 20, "card") # 최대 20개
hand_full_html = generate_news_list(entries_hand, 20, "card") # 최대 20개

if not humanoid_full_html: humanoid_full_html = "<p>최근 뉴스가 없습니다.</p>"
if not hand_full_html: hand_full_html = "<p>최근 뉴스가 없습니다.</p>"

with open('news_template.html', 'r', encoding='utf-8') as f:
    news_template = f.read()

output_news = news_template.replace('{{LAST_UPDATED}}', now_str)
output_news = output_news.replace('{{HUMANOID_NEWS_FULL}}', humanoid_full_html)
output_news = output_news.replace('{{HAND_NEWS_FULL}}', hand_full_html)

with open('news.html', 'w', encoding='utf-8') as f:
    f.write(output_news)

print("완료: index.html 및 news.html 업데이트됨.")
