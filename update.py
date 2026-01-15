import yfinance as yf
import feedparser
import datetime
import urllib.parse
import time

# ---------------------------------------------------------
# 1. 헬퍼 함수: 미니 차트 URL 생성 (QuickChart)
# ---------------------------------------------------------
def make_sparkline_url(data_list, color):
    if not data_list or len(data_list) < 2:
        return ""
    # 최근 30개 데이터만 사용
    subset = data_list[-30:]
    data_str = ",".join([f"{x:.2f}" for x in subset])
    
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

# ---------------------------------------------------------
# 2. 시장 지수 가져오기 (상단 3개용)
# ---------------------------------------------------------
def get_metric_data(ticker, color):
    try:
        stock = yf.Ticker(ticker)
        # 5일치(변동폭 계산용) + 1달치(차트용)
        hist = stock.history(period="1mo")
        if hist.empty: return "N/A", "0.00%", ""

        current = hist['Close'].iloc[-1]
        prev = hist['Close'].iloc[-2]
        change = current - prev
        change_pct = (change / prev) * 100
        
        # 등락에 따른 색상/부호
        if change >= 0:
            sign = "+"
            css_class = "text-red" # 한국은 상승이 빨강
        else:
            sign = ""
            css_class = "text-blue" # 하락이 파랑

        val_str = f"{current:,.2f}"
        if ticker == "KRW=X": val_str += " 원"
        
        change_str = f"<span class='{css_class}'>{sign}{change:.2f} ({sign}{change_pct:.2f}%)</span>"
        chart_url = make_sparkline_url(hist['Close'].tolist(), color)
        
        return val_str, change_str, chart_url
    except:
        return "Error", "-", ""

print("1. 지수 데이터 수집 중...")
kospi_val, kospi_chg, kospi_chart = get_metric_data("^KS11", "red")
sp500_val, sp500_chg, sp500_chart = get_metric_data("^GSPC", "red") # 미국 지수도 상승은 빨강/하락 파랑 로직 공유
usdkrw_val, usdkrw_chg, usdkrw_chart = get_metric_data("KRW=X", "green")


# ---------------------------------------------------------
# 3. 한국 주요 주식 직접 만들기 (위젯 대체)
# ---------------------------------------------------------
print("2. 한국 주식 데이터 수집 중...")
korea_tickers = [
    ('005930.KS', '삼성전자'),
    ('000660.KS', 'SK하이닉스'),
    ('373220.KS', 'LG에너지솔루션'),
    ('207940.KS', '삼성바이오로직스'),
    ('005380.KS', '현대차'),
    ('005490.KS', 'POSCO홀딩스'),
    ('000270.KS', '기아'),
    ('035420.KS', 'NAVER')
]

korea_table_html = "<table class='stock-table'><thead><tr><th>종목명</th><th>현재가</th><th>등락률</th><th>추세(1달)</th></tr></thead><tbody>"

for code, name in korea_tickers:
    try:
        stock = yf.Ticker(code)
        hist = stock.history(period="1mo")
        if not hist.empty:
            curr = hist['Close'].iloc[-1]
            prev = hist['Close'].iloc[-2]
            pct = ((curr - prev) / prev) * 100
            
            # 색상 결정
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
            
            korea_table_html += f"""
            <tr>
                <td>
                    <span class='stock-name'>{name}</span>
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
# 4. 뉴스 가져오기 (기간 필터링 적용)
# ---------------------------------------------------------
print("3. 뉴스 수집 중...")

# URL 뒤에 &tbs=qdr:w (지난 1주), &tbs=qdr:d (지난 24시간)
# 여기서는 안전하게 '지난 1주(w)'로 설정하여 뉴스가 없어서 빈칸이 되는 것을 방지
rss_list = [
    ("https://news.google.com/rss/search?q=stock+market+korea&hl=ko&gl=KR&ceid=KR:ko&tbs=qdr:w", "📈 국내 증시"),
    ("https://news.google.com/rss/search?q=robot+industry+technology&hl=ko&gl=KR&ceid=KR:ko&tbs=qdr:w", "🤖 로봇 산업"),
    ("https://news.google.com/rss/search?q=robot+end+effector+gripper&hl=ko&gl=KR&ceid=KR:ko&tbs=qdr:w", "🦾 로봇 핸드/그리퍼")
]

news_content_html = ""

for url, category in rss_list:
    news_content_html += f"<div class='news-category'><h4><span class='badge'>{category}</span></h4><ul class='news-list'>"
    try:
        feed = feedparser.parse(url)
        # 5개만
        count = 0
        for entry in feed.entries:
            if count >= 5: break
            
            # 날짜 파싱 (오늘/어제 등 표시)
            dt_struct = entry.published_parsed
            if dt_struct:
                dt_obj = datetime.datetime(*dt_struct[:6])
                time_diff = datetime.datetime.now() - dt_obj
                
                # 표시 날짜 포맷
                if time_diff.days < 1:
                    date_display = "오늘/최신"
                elif time_diff.days < 2:
                    date_display = "1일 전"
                else:
                    date_display = f"{dt_obj.month}/{dt_obj.day}"
            else:
                date_display = ""

            news_content_html += f"""
            <li class='news-item'>
                <a href='{entry.link}' target='_blank'>{entry.title}</a>
                <span class='news-time'>{date_display}</span>
            </li>
            """
            count += 1
            
        if count == 0:
            news_content_html += "<li class='news-item'>최근 관련 기사가 없습니다.</li>"
            
    except Exception as e:
        news_content_html += f"<li class='news-item'>뉴스 로딩 실패</li>"
    news_content_html += "</ul></div>"


# ---------------------------------------------------------
# 5. 파일 저장
# ---------------------------------------------------------
print("4. HTML 생성 중...")
now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

with open('template.html', 'r', encoding='utf-8') as f:
    template = f.read()

output = template.replace('{{LAST_UPDATED}}', now_str)

# 지표 교체
output = output.replace('{{KOSPI_VAL}}', kospi_val).replace('{{KOSPI_CHANGE}}', kospi_chg).replace('{{KOSPI_CHART}}', kospi_chart)
output = output.replace('{{SP500_VAL}}', sp500_val).replace('{{SP500_CHANGE}}', sp500_chg).replace('{{SP500_CHART}}', sp500_chart)
output = output.replace('{{USDKRW_VAL}}', usdkrw_val).replace('{{USDKRW_CHANGE}}', usdkrw_chg).replace('{{USDKRW_CHART}}', usdkrw_chart)

# 한국 주식 테이블 교체
output = output.replace('{{KOREA_MARKET_HTML}}', korea_table_html)

# 뉴스 교체
output = output.replace('{{NEWS_CONTENT}}', news_content_html)

with open('index.html', 'w', encoding='utf-8') as f:
    f.write(output)

print("완료! index.html 업데이트됨.")
