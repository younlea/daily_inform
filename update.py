import yfinance as yf
import feedparser
import datetime
import urllib.parse
import time
import json
import os
import re
import google.generativeai as genai

# ==========================================
# 1. 설정 및 헬퍼 함수
# ==========================================
ARCHIVE_FILE = 'news_archive.json'
MAX_ITEMS = 2000

# [디버깅] API 키 확인
GEMINI_KEY = os.environ.get('GEMINI_API_KEY')
if GEMINI_KEY:
    print(f"✅ DEBUG: GEMINI_API_KEY 감지됨")
    genai.configure(api_key=GEMINI_KEY)
else:
    print("❌ DEBUG: GEMINI_API_KEY 없음!")

# 모델 가져오기 (1.5 Flash -> Pro 순서로 시도)
def get_ai_model():
    # 1순위: 1.5 Flash (빠름)
    try:
        return genai.GenerativeModel('gemini-1.5-flash')
    except:
        pass
    # 2순위: Pro (안정적)
    try:
        return genai.GenerativeModel('gemini-pro')
    except:
        return None

MODEL_INSTANCE = None
if GEMINI_KEY:
    MODEL_INSTANCE = get_ai_model()

# ★★★ 문법 오류 수정됨 (global 선언 위치 이동) ★★★
def process_news_with_ai(title, snippet):
    # 함수 내부에서 전역 변수를 바꾸려면 맨 위에 선언해야 함
    global MODEL_INSTANCE
    
    fallback_summary = snippet[:300] + ("..." if len(snippet) > 300 else "")
    
    if not MODEL_INSTANCE:
        return title, fallback_summary
    
    # 재시도 로직
    max_retries = 3
    for attempt in range(max_retries):
        try:
            # 프롬프트: JSON 대신 특수 구분자(|||)를 사용해달라고 요청
            prompt = f"""
            Role: Professional Tech Reporter (Korea).
            Task: Translate title and summarize content into Korean.

            Format your response exactly like this:
            KOREAN_TITLE ||| KOREAN_SUMMARY

            Rules:
            1. Title: Natural Korean translation.
            2. Summary: 2-3 sentences in Korean. Noun-ending style (~함).
            3. Do NOT output markdown, JSON, or any other text. Just the formatted string.

            Input Title: {title}
            Input Snippet: {snippet}
            """
            
            # JSON 모드 끄고 일반 텍스트 모드로 요청
            response = MODEL_INSTANCE.generate_content(prompt)
            result_text = response.text.strip()
            
            # 구분자(|||)로 나누기
            if "|||" in result_text:
                parts = result_text.split("|||")
                title_ko = parts[0].strip()
                summary_ko = parts[1].strip()
                return title_ko, summary_ko
            else:
                return title, result_text
            
        except Exception as e:
            error_msg = str(e)
            if "429" in error_msg or "quota" in error_msg.lower():
                print(f"⚠️ Quota Limit! Waiting 60s... (Attempt {attempt+1})")
                time.sleep(60)
                continue
            elif "404" in error_msg:
                 # 모델 못 찾으면 gemini-pro로 교체해서 재시도
                print("⚠️ Model not found. Switching to gemini-pro...")
                MODEL_INSTANCE = genai.GenerativeModel('gemini-pro')
                continue
            else:
                print(f"❌ AI Error: {error_msg}")
                return title, fallback_summary
    
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
            
            # AI 처리
            title_ko, summary_ko = process_news_with_ai(entry.title, raw_snippet)
            
            # 10초 대기
            print("Cooling down (10s)...")
            time.sleep(10) 

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
            
            if new_items_count >= 15:
                print("⚠️ 안전을 위해 이번 실행은 15개까지만 처리합니다.")
                break
        
        if new_items_count >= 15: break

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
