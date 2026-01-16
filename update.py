import yfinance as yf
import feedparser
import datetime
import urllib.parse
import time
import json
import os
import re
# ★★★ 번역기 라이브러리 (키 필요 없음, 무제한) ★★★
from deep_translator import GoogleTranslator

# ==========================================
# 1. 설정 및 헬퍼 함수
# ==========================================
ARCHIVE_FILE = 'news_archive.json'
MAX_ITEMS = 2000

# ★★★ 텍스트 번역 함수 ★★★
def translate_text(text):
    if not text: return ""
    try:
        # 영어를 한국어로 번역 (고유명사는 구글 번역기 로직을 따름)
        translated = GoogleTranslator(source='auto', target='ko').translate(text)
        return translated
    except Exception as e:
        print(f"❌ Translation Error: {e}")
        return text # 에러나면 원문 그대로 리턴

def clean_html(raw_html):
    cleanr = re.compile('<.*?>')
    text = re.sub(cleanr, '', raw_html)
    return text.replace('&nbsp;', ' ').strip()

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

def load_archive():
    if os.path.exists(ARCHIVE_FILE):
        with open(ARCHIVE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

def save_archive(data):
    data.sort(key=lambda x: x['date'], reverse=True)
    if len(data) > MAX_ITEMS: data = data[:MAX_ITEMS]
    with open(ARCHIVE_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ==========================================
# 2. 시장 데이터 수집
# ==========================================
print("1. 시장 데이터 수집...")
kospi_val, kospi_chg, kospi_chart = get_metric_data("^KS11", "red")
sp500_val, sp500_chg, sp500_chart = get_metric_data("^GSPC", "red")
usdkrw_val, usdkrw_chg, usdkrw_chart = get_metric_data("KRW=X", "green")

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
# 3. 뉴스 수집 및 번역
# ==========================================
print("2. 뉴스 데이터 수집 및 번역 (Deep Translator)...")
archive = load_archive()
existing_links = set(item['link'] for item in archive)

# [경제 뉴스] - 아침 브리핑용
rss_economy = [{"url": "https://news.google.com/rss/search?q=stock+market+economy+korea+usa&hl=ko&gl=KR&ceid=KR:ko", "title": "📈 국내외 증시", "cat": "economy"}]

# [휴머노이드/로봇 일반 뉴스] - 요청하신 영문 사이트 완벽 포함
rss_humanoid = [
    {"url": "https://news.google.com/rss/search?q=humanoid+robot+(startup+OR+unveiled+OR+prototype+OR+new+model)+-vacuum&hl=ko&gl=KR&ceid=KR:ko", "title": "Google News", "cat": "humanoid"},
    {"url": "https://techxplore.com/rss-feed/robotics-news/", "title": "Tech Xplore", "cat": "humanoid"},
    {"url": "https://spectrum.ieee.org/feeds/topic/robotics.rss", "title": "IEEE Spectrum", "cat": "humanoid"},
    {"url": "https://www.therobotreport.com/feed/", "title": "The Robot Report", "cat": "humanoid"},
    {"url": "http://www.irobotnews.com/rss/all.xml", "title": "로봇신문", "cat": "humanoid"},
    {"url": "https://humanoidroboticstechnology.com/feed/", "title": "Humanoid Tech Blog", "cat": "humanoid"}
]

# [로봇 핸드/그리퍼 뉴스]
rss_hand = [
    {"url": "https://news.google.com/rss/search?q=robot+hand+gripper+dexterous+manipulation+tactile+sensor+-vacuum&hl=ko&gl=KR&ceid=KR:ko", "title": "Google News", "cat": "hand"}
]

# ★★★ [수정됨] 경제 뉴스도 번역 처리 ★★★
economy_news_latest = []
print("   >> Processing Economy News...")
for src in rss_economy:
    try:
        feed = feedparser.parse(src["url"], agent="Mozilla/5.0")
        for entry in feed.entries[:4]:
            # 제목 번역!
            entry.title = translate_text(entry.title)
            economy_news_latest.append(entry)
            time.sleep(0.5) # 짧은 대기
    except: pass

today = datetime.datetime.now()
new_items_count = 0

print("   >> Processing Robot News...")
for src in rss_humanoid + rss_hand:
    try:
        feed = feedparser.parse(src["url"], agent="Mozilla/5.0")
        for entry in feed.entries:
            link = entry.link
            if link in existing_links: continue
            
            pub_dt = today
            if hasattr(entry, 'published_parsed') and entry.published_parsed:
                pub_dt = datetime.datetime.fromtimestamp(time.mktime(entry.published_parsed))
            elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                pub_dt = datetime.datetime.fromtimestamp(time.mktime(entry.updated_parsed))
            
            if (today - pub_dt).days > 7: continue

            print(f"Processing: {entry.title}...")
            raw_snippet = clean_html(entry.get('description', entry.get('summary', '')))
            
            # ★★★ 제목과 요약문 번역 ★★★
            title_ko = translate_text(entry.title)
            # 내용은 너무 길면 500자만 잘라서 번역
            summary_ko = translate_text(raw_snippet[:500]) 
            
            time.sleep(1) 

            news_item = {
                "title": title_ko,
                "original_title": entry.title,
                "link": link,
                "date": pub_dt.strftime("%Y-%m-%d %H:%M"),
                "source": src['title'],
                "category": src['cat'],
                "summary": summary_ko
            }
            archive.append(news_item)
            existing_links.add(link)
            new_items_count += 1
            
            # 20개 제한
            if new_items_count >= 20:
                print("🛑 20개 처리 완료. 종료합니다.")
                break
        
        if new_items_count >= 20: break

    except Exception as e:
        print(f"RSS Error: {e}")

save_archive(archive)
print(f"New items: {new_items_count}")

# ==========================================
# 4. HTML 생성
# ==========================================
print("3. HTML 생성...")
utc_now = datetime.datetime.now(datetime.timezone.utc)
kst_now = utc_now + datetime.timedelta(hours=9)
now_str = kst_now.strftime("%Y-%m-%d %H:%M:%S (KST)")

# 메인 페이지 (index.html)
def generate_simple_list(items):
    html = ""
    for item in items[:4]:
        # 여기서는 이미 번역된 title을 사용하거나, economy_news_latest의 경우 위에서 번역해둔 title 사용
        title = item.get('title') if isinstance(item, dict) else item.title
        link = item.get('link') if isinstance(item, dict) else item.link
        html += f"<li class='news-item'><a href='{link}' target='_blank'>{title}</a></li>"
    return html

latest_humanoid = [x for x in archive if x['category'] == 'humanoid']
latest_hand = [x for x in archive if x['category'] == 'hand']

main_news_html = ""
# 경제 뉴스도 이제 한글로 나옵니다
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

# 뉴스 페이지 (news.html)
def generate_card_list(items):
    html = ""
    for item in items:
        summary_html = f"<div class='news-summary' style='color:#555; font-size:0.95rem; margin-top:8px; line-height:1.6;'>💡 {item.get('summary', '')}</div>" if item.get('summary') else ""
        original_title = item.get('original_title', '').replace("'", "&#39;")
        html += f"""
        <div class='news-card'>
            <a href='{item['link']}' target='_blank' class='news-title'>{item['title']}</a>
            <div class='hidden-keywords' style='display:none;'>{original_title}</div>
            {summary_html}
            <div class='news-meta' style='margin-top:10px;'>
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

print("완료!")
