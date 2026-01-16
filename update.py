import yfinance as yf
import feedparser
import datetime
import urllib.parse
import time
import json
import os
from email.utils import parsedate_to_datetime

# ==========================================
# 1. 설정 및 헬퍼 함수
# ==========================================
ARCHIVE_FILE = 'news_archive.json'

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

# ==========================================
# 2. 아카이브(JSON) 관리 함수
# ==========================================
def load_archive():
    if os.path.exists(ARCHIVE_FILE):
        with open(ARCHIVE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

def save_archive(data):
    # 날짜 최신순 정렬
    data.sort(key=lambda x: x['date'], reverse=True)
    with open(ARCHIVE_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ==========================================
# 3. 데이터 수집 및 처리
# ==========================================
print("1. 시장 데이터 수집...")
kospi_val, kospi_chg, kospi_chart = get_metric_data("^KS11", "red")
sp500_val, sp500_chg, sp500_chart = get_metric_data("^GSPC", "red")
usdkrw_val, usdkrw_chg, usdkrw_chart = get_metric_data("KRW=X", "green")

# 한국 주식 테이블 생성
korea_tickers = [
    ('005930.KS', '삼성전자', '005930'), ('000660.KS', 'SK하이닉스', '000660'),
    ('373220.KS', 'LG에너지솔루션', '373220'), ('207940.KS', '삼성바이오로직스', '207940'),
    ('005380.KS', '현대차', '005380'), ('005490.KS', 'POSCO홀딩스', '005490'),
    ('000270.KS', '기아', '000270'), ('035420.KS', 'NAVER', '035420')
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

# ==========================================
# 4. 뉴스 수집 및 아카이빙
# ==========================================
print("2. 뉴스 데이터 수집 및 아카이빙...")
archive = load_archive()
existing_links = set(item['link'] for item in archive)

# 뉴스 소스 정의 (Economy는 아카이빙 안하고 메인에만 표시, Humanoid/Hand는 아카이빙)
rss_economy = [{"url": "https://news.google.com/rss/search?q=stock+market+economy+korea+usa&hl=ko&gl=KR&ceid=KR:ko", "title": "📈 국내외 증시", "cat": "economy"}]
rss_humanoid = [
    {"url": "https://news.google.com/rss/search?q=humanoid+robot+(startup+OR+unveiled+OR+prototype+OR+new+model)+-vacuum&hl=ko&gl=KR&ceid=KR:ko", "title": "Google News", "cat": "humanoid"},
    {"url": "https://humanoidroboticstechnology.com/feed/", "title": "Humanoid Tech Blog", "cat": "humanoid"}
]
rss_hand = [
    {"url": "https://news.google.com/rss/search?q=robot+hand+gripper+dexterous+manipulation+tactile+sensor+-vacuum&hl=ko&gl=KR&ceid=KR:ko", "title": "Google News", "cat": "hand"}
]

# 경제 뉴스 가져오기 (저장 안 함, 최신만 사용)
economy_news_latest = []
for src in rss_economy:
    try:
        feed = feedparser.parse(src["url"], agent="Mozilla/5.0")
        for entry in feed.entries[:4]:
            economy_news_latest.append(entry)
    except: pass

# 로봇 뉴스 가져오기 (저장함)
today = datetime.datetime.now()
new_items_count = 0

for src in rss_humanoid + rss_hand:
    try:
        feed = feedparser.parse(src["url"], agent="Mozilla/5.0")
        for entry in feed.entries:
            link = entry.link
            
            # 이미 저장된 뉴스면 건너뜀
            if link in existing_links:
                continue
            
            # 날짜 파싱
            pub_dt = today # 기본값
            if hasattr(entry, 'published_parsed') and entry.published_parsed:
                pub_dt = datetime.datetime.fromtimestamp(time.mktime(entry.published_parsed))
            elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                pub_dt = datetime.datetime.fromtimestamp(time.mktime(entry.updated_parsed))
            
            # 너무 오래된 뉴스(7일 이상)는 처음 가져올 때 무시 (DB 오염 방지)
            if (today - pub_dt).days > 7:
                continue

            # 아카이브에 추가할 데이터 구조
            news_item = {
                "title": entry.title,
                "link": link,
                "date": pub_dt.strftime("%Y-%m-%d %H:%M"), # 정렬을 위한 문자열
                "source": src['title'],
                "category": src['cat'],
                "timestamp": pub_dt.timestamp()
            }
            archive.append(news_item)
            existing_links.add(link)
            new_items_count += 1
    except Exception as e:
        print(f"RSS Error: {e}")

# 아카이브 저장
save_archive(archive)
print(f"새로운 뉴스 {new_items_count}개 추가됨. 총 {len(archive)}개 아카이빙 중.")

# ==========================================
# 5. HTML 생성
# ==========================================
print("3. HTML 페이지 생성...")
utc_now = datetime.datetime.now(datetime.timezone.utc)
kst_now = utc_now + datetime.timedelta(hours=9)
now_str = kst_now.strftime("%Y-%m-%d %H:%M:%S (KST)")

# [메인 페이지용 HTML 생성] - 최근 4개씩만
def generate_simple_list(items):
    html = ""
    for item in items[:4]:
        # item이 feedparser 객체일 수도 있고, dict일 수도 있음
        title = item.get('title') if isinstance(item, dict) else item.title
        link = item.get('link') if isinstance(item, dict) else item.link
        html += f"<li class='news-item'><a href='{link}' target='_blank'>{title}</a></li>"
    return html

# 아카이브에서 카테고리별로 분류 (최신순 정렬되어 있음)
latest_humanoid = [x for x in archive if x['category'] == 'humanoid']
latest_hand = [x for x in archive if x['category'] == 'hand']

main_news_html = ""
if economy_news_latest:
    main_news_html += f"<div class='news-category'><h4><span class='badge'>📈 증시/경제</span></h4><ul class='news-list'>{generate_simple_list(economy_news_latest)}</ul></div>"
if latest_humanoid:
    main_news_html += f"<div class='news-category'><h4><span class='badge'>🤖 휴머노이드</span></h4><ul class='news-list'>{generate_simple_list(latest_humanoid)}</ul></div>"
if latest_hand:
    main_news_html += f"<div class='news-category'><h4><span class='badge'>🦾 핸드/그리퍼</span></h4><ul class='news-list'>{generate_simple_list(latest_hand)}</ul></div>"

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

# [뉴스 페이지용 HTML 생성] - 전체 리스트 (카드 형태)
def generate_card_list(items):
    html = ""
    for item in items:
        html += f"""
        <div class='news-card'>
            <a href='{item['link']}' target='_blank' class='news-title'>{item['title']}</a>
            <div class='news-meta'>
                <span class='source-tag'>{item['source']}</span>
                <span class='date-tag'>{item['date'][:10]}</span>
            </div>
        </div>
        """
    return html

with open('news_template.html', 'r', encoding='utf-8') as f:
    news_template = f.read()

output_news = news_template.replace('{{LAST_UPDATED}}', now_str)
output_news = output_news.replace('{{HUMANOID_NEWS_FULL}}', generate_card_list(latest_humanoid))
output_news = output_news.replace('{{HAND_NEWS_FULL}}', generate_card_list(latest_hand))

with open('news.html', 'w', encoding='utf-8') as f:
    f.write(output_news)

print("완료: index.html 및 news.html 업데이트됨.")
