import yfinance as yf
import feedparser
import datetime
import urllib.parse
import time
import json
import os
import re
import subprocess
import ollama

# ==========================================
# 1. 설정
# ==========================================
ARCHIVE_FILE = 'news_archive.json'
PROMPT_FILE = 'prompt.md'
MAX_ITEMS = 2000
LOCAL_MODEL = "llama3"

def log(msg):
    print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {msg}")

def load_prompt_template():
    if not os.path.exists(PROMPT_FILE):
        log(f"❌ Error: {PROMPT_FILE} not found!")
        return None
    with open(PROMPT_FILE, 'r', encoding='utf-8') as f:
        return f.read()

def process_news_with_local_llm(title, snippet):
    template = load_prompt_template()
    if not template: return title, snippet

    final_prompt = template.replace("{title}", title).replace("{snippet}", snippet)
    
    try:
        response = ollama.chat(model=LOCAL_MODEL, messages=[{'role': 'user', 'content': final_prompt}])
        result_text = response['message']['content'].strip()
        
        if "|||" in result_text:
            parts = result_text.split("|||")
            title = parts[0].strip().strip('*').strip('#').strip()
            summary = parts[1].strip().strip('*').strip('#').strip()
            return title, summary
        else:
            lines = result_text.split('\n')
            if len(lines) >= 2:
                title = lines[0].strip().strip('*').strip('#').strip()
                summary = " ".join(lines[1:]).strip().strip('*').strip('#').strip()
                return title, summary
            return title.strip().strip('*').strip('#').strip(), result_text.strip().strip('*').strip('#').strip() 
    except Exception as e:
        log(f"❌ LLM Error: {e}")
        return title, snippet

import html

def clean_html(raw_html):
    if not raw_html: return ""
    raw_html = str(raw_html)
    unescaped = html.unescape(raw_html)
    cleanr = re.compile('<.*?>', re.DOTALL)
    text = re.sub(cleanr, '', unescaped)
    cleaned = text.replace('&nbsp;', ' ').strip()
    # log(f"DEBUG CLEAN: {raw_html[:30]}... -> {cleaned[:30]}...")
    return cleaned

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
# 2. 실행 로직
# ==========================================
log(f"🚀 로컬 업데이트 시작 (Model: {LOCAL_MODEL})")
log("📥 Git Pull...")
subprocess.run(["git", "pull"])

log("📈 시장 데이터 수집...")
kospi_val, kospi_chg, kospi_chart = get_metric_data("^KS11", "red")
kosdaq_val, kosdaq_chg, kosdaq_chart = get_metric_data("^KQ11", "red")
sp500_val, sp500_chg, sp500_chart = get_metric_data("^GSPC", "red")
nasdaq_val, nasdaq_chg, nasdaq_chart = get_metric_data("^IXIC", "red")
gold_val, gold_chg, gold_chart = get_metric_data("GC=F", "gold")
silver_val, silver_chg, silver_chart = get_metric_data("SI=F", "silver")
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

log("📰 뉴스 수집 및 로컬 AI 처리...")
archive = load_archive()
existing_links = set(item['link'] for item in archive)

archive = load_archive()
existing_links = set(item['link'] for item in archive)

FEED_CONFIG_FILE = 'feeds.json'

def load_feeds():
    if not os.path.exists(FEED_CONFIG_FILE):
        log(f"⚠️ Warning: {FEED_CONFIG_FILE} not found! Using default empty lists.")
        return {"economy": [], "robotics": []}
    try:
        with open(FEED_CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        log(f"❌ Error loading {FEED_CONFIG_FILE}: {e}")
        return {"economy": [], "robotics": []}

feeds_config = load_feeds()
rss_economy = feeds_config.get("economy", [])
# Combine all robotics related feeds (humanoid, hand, paper, etc.)
rss_robotics = feeds_config.get("robotics", [])

# Temporarily map old variable names if needed, or update loops below
# rss_humanoid and rss_hand are now mixed in rss_robotics
# The classification logic will handle the specific category assignment.

def classify_category(title, summary, current_cat):
    # 만약 이미 hand 카테고리면 그대로 유지
    if current_cat == 'hand': return 'hand'
    
    keywords_hand = ["hand", "gripper", "finger", "manipulation", "dexterous", "tactile", "grasping", "핸드", "그리퍼", "손", "매니퓰", "촉각", "파지"]
    keywords_humanoid = ["humanoid", "bipedal", "walking", "locomotion", "torso", "human-centered", "휴머노이드", "이족보행", "보행", "로코모션"]
    
    text = (title + " " + (summary or "")).lower()
    
    for kw in keywords_hand:
        if kw in text:
            return "hand"
            
    for kw in keywords_humanoid:
        if kw in text:
            return "humanoid"
            
    return current_cat

# 기존 아카이브 재분류 (Re-classify existing items)
for item in archive:
    if 'title' not in item: continue
    item['category'] = classify_category(item['title'], item.get('summary', ''), item['category'])


economy_news_latest = []
for src in rss_economy:
    try:
        feed = feedparser.parse(src["url"], agent="Mozilla/5.0")
        for entry in feed.entries[:4]:
            raw_snippet = clean_html(entry.get('description', entry.get('summary', '')))
            # Google News RSS often puts the title in the description too.
            # If description is too short or almost same as title, we might want to flag it?
            
            t_ko, s_ko = process_news_with_local_llm(entry.title, raw_snippet)
            
            # Date parsing
            pub_dt = datetime.datetime.now()
            if hasattr(entry, 'published_parsed') and entry.published_parsed:
                pub_dt = datetime.datetime.fromtimestamp(time.mktime(entry.published_parsed))
            elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                pub_dt = datetime.datetime.fromtimestamp(time.mktime(entry.updated_parsed))

            # Create a clean dictionary
            news_item = {
                "title": t_ko,
                "link": entry.link,
                "summary": s_ko,
                "source": src.get('title', 'Economy News'),
                "date": pub_dt.strftime("%Y-%m-%d %H:%M")
            }
            economy_news_latest.append(news_item)
    except Exception as e:
        log(f"Economy RSS Error: {e}")

today = datetime.datetime.now()
new_items_count = 0

# Separate feeds into News and Papers
rss_robotics_news = [src for src in rss_robotics if src.get('cat') != 'paper']
rss_robotics_papers = [src for src in rss_robotics if src.get('cat') == 'paper']

new_items_count = 0
MAX_PAPERS_COUNT = 8
paper_items_count = 0

def process_feed_list(feed_list, is_paper=False):
    global new_items_count, paper_items_count
    for src in feed_list:
        try:
            feed = feedparser.parse(src["url"], agent="Mozilla/5.0")
            for entry in feed.entries:
                link = entry.link
                if link in existing_links: continue
                
                # Check paper limit
                if is_paper and paper_items_count >= MAX_PAPERS_COUNT:
                    return

                # Check global limit
                if new_items_count >= 200: return

                pub_dt = today
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    pub_dt = datetime.datetime.fromtimestamp(time.mktime(entry.published_parsed))
                elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                    pub_dt = datetime.datetime.fromtimestamp(time.mktime(entry.updated_parsed))
                
                if (today - pub_dt).days > 7: continue

                log(f"🧠 AI Processing: {entry.title[:40]}...")
                raw_snippet = clean_html(entry.get('description', entry.get('summary', '')))
                if not raw_snippet: 
                    raw_snippet = entry.title
                
                title_ko, summary_ko = process_news_with_local_llm(entry.title, raw_snippet)
                
                # Determine category dynamically
                final_cat = classify_category(title_ko, summary_ko, src['cat'])

                # [STRICT FILTERING]
                if src.get('cat') == 'paper' and final_cat == 'paper':
                    log(f"🚫 Filtered out paper: {title_ko} (No keywords matched)")
                    continue

                news_item = {
                    "title": title_ko,
                    "original_title": entry.title,
                    "link": link,
                    "date": pub_dt.strftime("%Y-%m-%d %H:%M"),
                    "source": src['title'],
                    "category": final_cat,
                    "summary": summary_ko
                }
                archive.append(news_item)
                existing_links.add(link)
                new_items_count += 1
                if is_paper: paper_items_count += 1
                
        except Exception as e:
            log(f"RSS Error: {e}")

# 1. Process News First
log("📰 Fetching General News...")
process_feed_list(rss_robotics_news, is_paper=False)

# 2. Process Papers Second (Limited)
if new_items_count < 200:
    log("📄 Fetching Research Papers (Limited)...")
    process_feed_list(rss_robotics_papers, is_paper=True)

save_archive(archive)

log("📝 HTML 생성...")
utc_now = datetime.datetime.now(datetime.timezone.utc)
kst_now = utc_now + datetime.timedelta(hours=9)
now_str = kst_now.strftime("%Y-%m-%d %H:%M:%S (KST)")

def generate_simple_list(items):
    html = ""
    for item in items[:4]:
        title = item.get('title') if isinstance(item, dict) else item.title
        link = item.get('link') if isinstance(item, dict) else item.link
        summary = item.get('summary') if isinstance(item, dict) else getattr(item, 'summary', '')
        
        summary_html = f"<div style='font-size:0.9rem; color:#666; margin-top:4px;'>{summary}</div>" if summary else ""
        meta_html = f"<div style='font-size:0.8rem; color:#999; margin-top:2px;'>{item.get('source', '')} | {item.get('date', '')[:10]}</div>"
        html += f"<li class='news-item'><a href='{link}' target='_blank'>{title}</a>{summary_html}{meta_html}</li>"
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
output_main = output_main.replace('{{KOSDAQ_VAL}}', kosdaq_val).replace('{{KOSDAQ_CHANGE}}', kosdaq_chg).replace('{{KOSDAQ_CHART}}', kosdaq_chart)
output_main = output_main.replace('{{SP500_VAL}}', sp500_val).replace('{{SP500_CHANGE}}', sp500_chg).replace('{{SP500_CHART}}', sp500_chart)
output_main = output_main.replace('{{NASDAQ_VAL}}', nasdaq_val).replace('{{NASDAQ_CHANGE}}', nasdaq_chg).replace('{{NASDAQ_CHART}}', nasdaq_chart)
output_main = output_main.replace('{{GOLD_VAL}}', gold_val).replace('{{GOLD_CHANGE}}', gold_chg).replace('{{GOLD_CHART}}', gold_chart)
output_main = output_main.replace('{{SILVER_VAL}}', silver_val).replace('{{SILVER_CHANGE}}', silver_chg).replace('{{SILVER_CHART}}', silver_chart)
output_main = output_main.replace('{{USDKRW_VAL}}', usdkrw_val).replace('{{USDKRW_CHANGE}}', usdkrw_chg).replace('{{USDKRW_CHART}}', usdkrw_chart)
output_main = output_main.replace('{{KOREA_MARKET_HTML}}', korea_table_html)
output_main = output_main.replace('{{NEWS_CONTENT}}', main_news_html)
with open('index.html', 'w', encoding='utf-8') as f:
    f.write(output_main)

def generate_card_list(items):
    html = ""
    for item in items:
        if 'title' not in item: continue
        summary_html = f"<div class='news-summary' style='color:#555; font-size:0.95rem; margin-top:8px; line-height:1.6;'>💡 {item.get('summary', '')}</div>" if item.get('summary') else ""
        original_title = item.get('original_title', '').replace("'", "&#39;")
        # Star icon added
        star_icon = f"<span class='star-btn' onclick='toggleStar(this, \"{item['link']}\")' style='cursor:pointer; margin-right:8px; font-size:1.2rem; color:#ccc;'>☆</span>"
        
        html += f"""<div class='news-card' data-link='{item['link']}'><div style='display:flex; align-items:flex-start;'>{star_icon}<a href='{item['link']}' target='_blank' class='news-title' style='flex:1;'>{item['title']}</a></div><div class='hidden-keywords' style='display:none;'>{original_title}</div>{summary_html}<div class='news-meta' style='margin-top:10px;'><span class='source-tag'>{item['source']}</span><span class='date-tag'>{item['date'][:10]}</span></div></div>"""
    return html

with open('news_template.html', 'r', encoding='utf-8') as f:
    news_template = f.read()

output_news = news_template.replace('{{LAST_UPDATED}}', now_str)
# Economy section removed from news.html
output_news = output_news.replace('{{HUMANOID_NEWS_FULL}}', generate_card_list(latest_humanoid))
output_news = output_news.replace('{{HAND_NEWS_FULL}}', generate_card_list(latest_hand))
with open('news.html', 'w', encoding='utf-8') as f:
    f.write(output_news)

log("📤 GitHub로 업로드 중...")
try:
    subprocess.run(["git", "add", "."])
    subprocess.run(["git", "commit", "-m", "Local AI Update (RTX 5060 Ti)"])
    subprocess.run(["git", "push"])
    log("✅ 완료! 웹사이트가 업데이트되었습니다.")
except Exception as e:
    log(f"❌ Git Upload Error: {e}")
