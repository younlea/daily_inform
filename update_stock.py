import yfinance as yf
import datetime
import urllib.parse
import json
import os

# ==========================================
# 설정
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
        # 1시간 간격 업데이트이므로 최근 데이터 가져오기
        hist = stock.history(period="5d", interval="1h") 
        if hist.empty: 
            # 장 마감 등으로 데이터 없으면 일별 데이터로 백업
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
        
        # 차트용 데이터는 일별 종가 사용 (깔끔하게 보이기 위해)
        hist_daily = stock.history(period="1mo")
        chart_url = make_sparkline_url(hist_daily['Close'].tolist(), color)
        
        return val_str, change_str, chart_url
    except: return "Error", "-", ""

def load_archive():
    if os.path.exists(ARCHIVE_FILE):
        with open(ARCHIVE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

# ==========================================
# 실행 로직 (주식만 갱신)
# ==========================================
print("1. 시장 데이터 수집 (Hourly Update)...")
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
# HTML 생성 (뉴스는 기존 데이터 유지)
# ==========================================
print("2. HTML 갱신 (뉴스는 기존 데이터 유지)...")

# 기존에 저장된 뉴스 데이터 불러오기
archive = load_archive()
economy_news_latest = [x for x in archive if x['category'] == 'economy'][:4]
latest_humanoid = [x for x in archive if x['category'] == 'humanoid'][:4]
latest_hand = [x for x in archive if x['category'] == 'hand'][:4]

utc_now = datetime.datetime.now(datetime.timezone.utc)
kst_now = utc_now + datetime.timedelta(hours=9)
now_str = kst_now.strftime("%Y-%m-%d %H:%M:%S (KST)")

def generate_simple_list(items):
    html = ""
    for item in items:
        title = item.get('title')
        link = item.get('link')
        html += f"<li class='news-item'><a href='{link}' target='_blank'>{title}</a></li>"
    return html

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

print("✅ 완료! 주식 정보 업데이트됨.")
