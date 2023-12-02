import pyupbit
import numpy as np
import time
import datetime
import pytz
import slack_sdk

# Slack API 키 설정
slack_token = "xoxb-6175565485767-6187284450981-8zICUT1XUHxsf24uS57iQe7D"
client = slack_sdk.WebClient(token=slack_token)

# UPbit API 키 설정
access = "HoZqFc3wygaRgdk8PO3e5TassXMx9sbO9cx0ju82"
secret = "hWz8bxNXn68RfzUxgxBjnN95whTLbxh3ix26bxnx"

# 변동성 돌파 전략을 통한 수익률 계산
def get_ror(k):
    try:
        # "KRW-BTC" 페어의 일봉 데이터를 최근 7일 동안 가져옴
        df = pyupbit.get_ohlcv("KRW-BTC", count=7)
        
        # 각 일자별로 변동폭을 계산. 변동폭은 고가와 저가의 차이에 비율 k를 곱한 값
        df['range'] = (df['high'] - df['low']) * k
        
        # 목표 매수가를 계산. 목표 매수가는 당일 시가에 전날 변동폭을 더한 값
        df['target'] = df['open'] + df['range'].shift(1)
        
        # 수익률을 계산. 만약 당일 고가가 목표 매수가를 넘으면 수익률을 계산하고, 그렇지 않으면 1로 함
        df['ror'] = np.where(df['high'] > df['target'], df['close'] / df['target'], 1)
        
        # 누적 수익률을 계산하고 마지막 날의 누적 수익률을 반환
        ror = df['ror'].cumprod().iloc[-1]
        return ror
    except Exception as e:
        print("get_ror에서 오류 발생:", e)
        return None

# 최적의 'k' 값을 찾기
def best_K_for_best_ror():
    try:
        # 빈 딕셔너리를 생성하여 각 k값에 대한 수익률을 저장할 변수를 만듦
        ror_dic = {}

        # 주어진 범위 내에서 0.1부터 1.0까지 0.1 간격으로 k값을 변경하면서 반복
        for k in np.arange(0.1, 1.0, 0.1):
            # 각 k값에 대한 수익률을 계산하는 함수 get_ror(k)를 호출
            ror = get_ror(k)
            
            # 계산된 수익률을 딕셔너리에 저장
            ror_dic[k] = ror
            # 현재 k값과 그에 대한 수익률을 출력
            # print("%.1f(k값) : %f(수익률)" % (k, ror))

        # 최적의 k값을 찾기 위해 딕셔너리를 순회하면서 최댓값을 찾음
        max_key = max(ror_dic, key=ror_dic.get)
        max_value = ror_dic[max_key]

        # 최적의 k값과 해당 k값에 대한 수익률을 출력함
        print("최적의 k값은 %.1f이고, 수익률은 %f이다" % (max_key, max_value))

        # 최적의 k값을 반환
        return max_key
    except Exception as e:
        print("best_K_for_best_ror에서 오류 발생:", e)
        return None

# 현재 시간을 한국 시간으로 가져오기
def get_now_korea_time():
    korea_timezone = pytz.timezone('Asia/Seoul')
    now_korea = datetime.datetime.now(korea_timezone)
    return now_korea

# 시작 시간 조회
def get_start_time(ticker):
    try:
        df = pyupbit.get_ohlcv(ticker, interval="day", count=1)
        start_time = df.index[0]
        return start_time
    except Exception as e:
        print("get_start_time에서 오류 발생:", e)
        return None

# 5일 이동 평균선 조회
def get_ma5(ticker):
    try:
        df = pyupbit.get_ohlcv(ticker, interval="day", count=5)
        ma5 = df['close'].rolling(5).mean().iloc[-1]
        return ma5
    except Exception as e:
        print("get_ma5에서 오류 발생:", e)
        return None

# 사용 가능한 잔고를 조회하는 함수
def get_balance(ticker):
    try:
        # upbit 라이브러리를 사용하여 현재 계정의 잔고 정보를 가져옴
        balances = upbit.get_balances()

        # 잔고 정보를 순회하면서 주어진 티커에 해당하는 잔고를 찾음
        for b in balances:
            if 'currency' in b and 'balance' in b:
                if b['currency'] == ticker:
                    # 해당 티커에 대한 잔고가 있으면 그 값을 반환
                    if b['balance'] is not None:
                        return float(b['balance'])
                    else:  # 잔고가 없으면 0을 반환
                        return 0
        # 주어진 티커에 대한 잔고가 없으면 0을 반환
        return 0
    except Exception as e:
        print("get_balance에서 오류 발생:", e)
        return None

# 현재가 조회
def get_current_price(ticker):
    try:
        return pyupbit.get_orderbook(ticker=ticker)["orderbook_units"][0]["ask_price"]
    except Exception as e:
        print("get_current_price에서 오류 발생:", e)
        return None

# 로그인
upbit = pyupbit.Upbit(access, secret)

# 자동매매 시작
def auto_trade():
    try:
        print("자동매매 시작")
        
        while True:
            now = get_now_korea_time()
            start_time = get_start_time("KRW-BTC")  # 09:00 AM UTC
            end_time = start_time + datetime.timedelta(days=1) - datetime.timedelta(seconds=1)
            
            # 09:00 AM부터 08:59:59 AM까지 자동매매 진행
            if start_time < now < end_time:
                target_price = get_target_price("KRW-BTC", 0.5)  # 예제에서는 0.5 사용
                ma5 = get_ma5("KRW-BTC")
                current_price = get_current_price("KRW-BTC")
                print("목표가: {}, 5일 이동평균: {}, 현재가: {}".format(target_price, ma5, current_price))
                
                # 목표가와 현재가를 비교하여 매수 결정
                if target_price < current_price and ma5 < current_price:
                    krw_balance = get_balance("KRW")
                    if krw_balance > 5000:  # 최소 주문 금액 이상일 때만 매수
                        buy_result = upbit.buy_market_order("KRW-BTC", krw_balance * 0.9995)  # 수수료 0.05% 고려
                        print("매수 주문 결과:", buy_result)
                        time.sleep(1)
            else:
                print("자동매매 중지 (장마감 또는 미래 예정 시간)")
                break
            time.sleep(1)
    except Exception as e:
        print("auto_trade에서 오류 발생:", e)

# 자동매매 실행
auto_trade()
