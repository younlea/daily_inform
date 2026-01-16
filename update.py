import yfinance as yf
import feedparser
import datetime
import urllib.parse
import time
import json
import os
import re
import requests

# ==========================================
# 1. 설정 및 헬퍼 함수
# ==========================================
ARCHIVE_FILE = 'news_archive.json'
MAX_ITEMS = 2000
GEMINI_KEY = os.environ.get('GEMINI_API_KEY')

# 모델 후보군 (2.0이 반응이 있었으므로 최상단 배치)
CANDIDATE_MODELS = [
    "gemini-2.0-flash-exp",
    "gemini-1.5-flash",
    "gemini-1.5-flash-latest",
    "gemini-1.5-flash-001",
    "gemini-pro"
]

ACTIVE_MODEL = None

if GEMINI_KEY:
    print(f"✅ DEBUG: API Key Loaded")
else:
    print("❌ DEBUG: API Key Missing!")

# ★★★ 수정됨: 429(과부하)도 '성공'으로 간주하고 선택함 ★★★
def find_working_model():
    print("\n🔍 AI 모델 생존 확인 중...")
    
    payload = {"contents": [{"parts": [{"text": "hi"}]}]}
    
    for model in CANDIDATE_MODELS:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        try:
            print(f"   👉 Testing '{model}'...", end=" ")
            response = requests.post(
                url,
                headers={"Content-Type": "application/json"},
                params={"key": GEMINI_KEY},
                json=payload,
                timeout=10
            )
            
            if response.status_code == 200:
                print("✅ 정상 (200 OK)")
                return model
            elif response.status_code == 429:
                print("✅ 생존 확인 (429 과부하 - 대기 후 사용 가능)")
                print("      -> 이 모델을 선택하고 잠시 대기합니다.")
                time.sleep(5) # 숨 고르기
                return model
            else:
                print(f"❌ 실패 ({response.status_code})")
                
        except Exception as e:
            print(f"❌ 에러 ({e})")
            
    return None

if GEMINI_KEY:
    ACTIVE_MODEL = find_working_model()
    if ACTIVE_MODEL:
        print(f"\n🎉 [확정] 오늘의 모델: {ACTIVE_MODEL}")
    else:
        print("\n🚨 [실패] 사용 가능한 모델이 없습니다. (영어 원문 저장)")

def process_news_with_ai(title, snippet):
    fallback_summary = snippet[:300] + ("..." if len(snippet) > 300 else "")
    
    if not GEMINI_KEY or not ACTIVE_MODEL:
        return title, fallback_summary

    prompt = f"""
    Role: Professional Tech Reporter (Korea).
    Task: Translate the title into Korean and summarize the snippet into Korean.
    
    Input Title: {title}
    Input Snippet: {snippet}

    Requirements:
    1. Title: Natural Korean translation.
    2. Summary: 2-3 sentences in Korean. Noun-ending style (e.g., ~함, ~임).
    3. Output Format: "KOREAN_TITLE ||| KOREAN_SUMMARY"
    4. Do NOT output anything else. Just the formatted string.
    """

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{ACTIVE_MODEL}:generateContent"
    payload = { "contents": [{ "parts": [{"text": prompt}] }] }
    
    # ★★★ 독한 재시도 로직 (429 뜨면 최대 3번, 60초씩 대기) ★★★
    for attempt in range(3):
        try:
            response = requests.post(
                url,
                headers={"Content-Type": "application/json"},
                params={"key": GEMINI_KEY},
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                try:
                    result = response.json()
                    result_text = result['candidates'][0]['content']['parts'][0]['text'].strip()
                    if "|||" in result_text:
                        parts = result_text.split("|||")
                        return parts[0].strip(), parts[1].strip()
                    else:
                        return title, result_text
                except:
                    return title, fallback_summary
            
            elif response.status_code == 429:
                print(f"⚠️ Quota Limit! 60초 대기 중... ({attempt+1}/3)")
                time.sleep(60) # 1분 강제 휴식
                continue # 다시 시도
            
            else:
                print(f"❌ Error {response.status_code}")
                # 404면 답이 없으니 포기
                if response.status_code == 404:
                    return title, fallback_summary
                time.sleep(5)
                continue

        except Exception as e:
            print(f"❌ Net Error: {e}")
            time.sleep(5)
            continue
            
    return title, fallback_summary

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
# 3. 뉴스 수집 및 AI 처리
# ==========================================
print("2. 뉴스 데이터 수집 및 AI 처리...")
archive = load_archive()
existing_links = set(item['link'] for item in archive)

rss_economy = [{"url": "https://news.google.com/rss/search?q=stock+market+economy+korea+usa&hl=ko&gl=KR&ceid=KR:ko", "title": "📈 국내외 증시", "cat": "economy"}]

rss_humanoid = [
    {"url": "https://news.google.com/rss/search?q=humanoid+robot+(startup+OR+unveiled+OR+prototype+OR+new+model)+-vacuum&hl=ko&gl=KR&ceid=KR:ko", "title": "Google News", "cat": "humanoid"},
    {"url": "https://techxplore.com/rss-feed/robotics-news/", "title": "Tech Xplore", "cat": "humanoid"},
    {"url": "https://spectrum.ieee.org/feeds/topic/robotics.rss", "title": "IEEE Spectrum", "cat": "humanoid"},
    {"url": "https://www.therobotreport.com/feed/", "title": "The Robot Report", "cat": "humanoid"},
    {"url": "http://www.irobotnews.com/rss/all.xml", "title": "로봇신문", "cat": "humanoid"},
    {"url": "https://humanoidroboticstechnology.com/feed/", "title": "Humanoid Tech Blog", "cat": "humanoid"}
]

rss_hand = [
    {"url": "https://news.google.com/rss/search?q=robot+hand+gripper+dexterous+manipulation+tactile+sensor+-vacuum&hl=ko&gl=KR&ceid=KR:ko", "title": "Google News", "cat": "hand"}
]

economy_news_latest = []
for src in rss_economy:
    try:
        feed = feedparser.parse(src["url"], agent="Mozilla/5.0")
        for entry in feed.entries[:4]:
            economy_news_latest.append(entry)
    except: pass

today = datetime.datetime.now()
new_items_count = 0

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

            print(f"AI Processing: {entry.title}...")
            raw_snippet = clean_html(entry.get('description', entry.get('summary', '')))
            
            title_ko, summary_ko = process_news_with_ai(entry.title, raw_snippet)
            
            # ★★★ 2.0 모델은 무료 할당량이 적으므로 30초 대기 필수 ★★★
            print("Cooling down (30s)...")
            time.sleep(30) 

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
            
            # 안전하게 10개만
            if new_items_count >= 10:
                print("⚠️ 안전을 위해 이번 실행은 10개까지만 처리합니다.")
                break
        
        if new_items_count >= 10: break

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
        title = item.get('title') if isinstance(item, dict) else item.title
        link = item.get('link') if isinstance(item, dict) else item.link
        html += f"<li class='news-item'><a href='{link}' target='_blank'>{title}</a></li>"
    return html

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
