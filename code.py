#!pip install pyupbit
#!pip install slack_sdk

import pyupbit #거래소
import numpy as np
import pandas as pd
import time
import datetime
import pytz #한국시간
import slack_sdk #슬랙

# slack API 키 설정
slack_token = "xoxb-6175565485767-6187284450981-8zICUT1XUHxsf24uS57iQe7D"
client = slack_sdk.WebClient(token = slack_token)
#client.chat_postMessage(channel = "#비트코인-자동매매", text = "Hello World")

# UPbit API 키 설정
access = "HoZqFc3wygaRgdk8PO3e5TassXMx9sbO9cx0ju82"
secret = "hWz8bxNXn68RfzUxgxBjnN95whTLbxh3ix26bxnx"

# 변동성 돌파 전략을 통한 수익률 계산
def get_ror(k):
    # pyupbit 라이브러리를 사용하여 "KRW-BTC" 페어의 일봉 데이터를 최근 7일 동안 가져옴
    df = pyupbit.get_ohlcv("KRW-BTC", count=7)
    # 각 일자별로 변동폭을 계산. 변동폭은 고가와 저가의 차이에 비율 k를 곱한 값.
    df['range'] = (df['high'] - df['low']) * k
    # 목표 매수가를 계산. 목표 매수가는 당일 시가에 전날 변동폭을 더한 값.
    df['target'] = df['open'] + df['range'].shift(1)
    # 수익률을 계산. 만약 당일 고가가 목표 매수가를 넘으면 수익률을 계산하고, 그렇지 않으면 1로 함.
    df['ror'] = np.where(df['high'] > df['target'], df['close'] / df['target'], 1)
    # 누적 수익률을 계산. 마지막 날의 누적 수익률을 반환.
    ror = df['ror'].cumprod().iloc[-1]
    return ror

# 최적의 'k' 값 설정
def best_K_for_best_ror():
    # 빈 딕셔너리를 생성하여 각 k값에 대한 수익률을 저장할 변수를 만듦.
    ror_dic = {}

    # 주어진 범위 내에서 0.1부터 1.0까지 0.1 간격으로 k값을 변경하면서 반복함.
    for k in np.arange(0.1, 1.0, 0.1):
        # 각 k값에 대한 수익률을 계산하는 함수 get_ror(k)를 호출.
        ror = get_ror(k)
        # 계산된 수익률을 딕셔너리에 저장.
        ror_dic[k] = ror
        # 현재 k값과 그에 대한 수익률을 출력.
        # print("%.1f(k값) : %f(수익률)" % (k, ror))

    # 최적의 k값을 찾기 위해 딕셔너리를 순회하면서 최댓값을 찾음.
    max_key = None
    max_value = float('-inf') #음의 무한대

    for key, value in ror_dic.items():
        if value > max_value:
            max_key = key
            max_value = value

    # 최적의 k값과 해당 k값에 대한 수익률을 출력함.
    print("최적의 k값은 %.1f이고, 수익률은 %f이다" % (max_key, max_value))

    # 최적의 k값을 반환
    best_K = max_key
    return best_K

'''
# 이 함수는 최근의 가격 동향을 고려하여 최적의 k 값을 사용하여 매수 목표 가격을 계산
def get_target_price(ticker):
    best_K = best_K_for_best_ror()
    # pyupbit 라이브러리를 사용하여 ticker 페어의 일봉 데이터를 최근 2일 동안 가져옴
    df = pyupbit.get_ohlcv(ticker, interval="day", count=2)

    # 매수 목표 가격을 계산.
    # target_price = 전일 종가 + (전일 고가 - 전일 저가) * 최적의 k값
    target_price = df.iloc[0]['close'] + (df.iloc[0]['high'] - df.iloc[0]['low']) * best_K

    return target_price
'''


def get_target_price(ticker):
    try:
        best_K = best_K_for_best_ror()
        # pyupbit 라이브러리를 사용하여 ticker 페어의 일봉 데이터를 최근 2일 동안 가져옴
        df = pyupbit.get_ohlcv(ticker, interval="day", count=2)

        if df is not None and not df.empty:
            # 매수 목표 가격을 계산.
            # target_price = 전일 종가 + (전일 고가 - 전일 저가) * 최적의 k값
            target_price = df.iloc[0]['close'] + (df.iloc[0]['high'] - df.iloc[0]['low']) * best_K
            return target_price
        else:
            # DataFrame이 None이거나 비어 있는 경우 처리
            print("오류: get_target_price에서 DataFrame이 None 또는 비어 있음")
            return None
    except Exception as e:
        print("get_target_price에서 오류 발생:", e)
        return None
    
    
# 시작 시간 조회
def get_start_time(ticker):
    df = pyupbit.get_ohlcv(ticker, interval="day", count=1)
    start_time = df.index[0]
    return start_time

# 5일 이동 평균선 조회
def get_ma5(ticker):
    df = pyupbit.get_ohlcv(ticker, interval="day", count=5)
    ma5 = df['close'].rolling(5).mean().iloc[-1]
    return ma5

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
                    else: # 잔고가 없으면 0을 반환
                        return 0
        # 주어진 티커에 대한 잔고가 없으면 0을 반환
        return 0
    except Exception as e:
        # 예외가 발생하면 에러 메시지를 출력하고 0을 반환
        print_balance_e = f"사용가능한 잔고를 조회하는 과정에서 에러가 발생했습니다: {e}"
        client.chat_postMessage(channel = "#비트코인-자동매매", text = print_balance_e) #에러메세지 슬랙으로 보냄
        return 0


# 현재가 조회
def get_current_price(ticker):
    return pyupbit.get_orderbook(ticker=ticker)["orderbook_units"][0]["ask_price"]


# 로그인
upbit = pyupbit.Upbit(access, secret)

# 한국 시간대 설정
korea_timezone = pytz.timezone('Asia/Seoul')
now_korea = datetime.datetime.now(korea_timezone)
start_time = get_start_time("KRW-BTC")

print("현재 시간:", now_korea) #디버깅
print("시작 시간:", start_time) #디버깅

# 자동매매 시작: 단타-> 당일 매매, 변동성 돌파 전략을 기본으로 함
print("자동매매 시작")
while True:
    try:
        # 현재 시간을 한국 시간으로 가져오기
        now = datetime.datetime.now(korea_timezone)
        start_time = get_start_time("KRW-BTC").replace(tzinfo=korea_timezone) #09:00
        end_time = (start_time + datetime.timedelta(days=1)).replace(tzinfo=korea_timezone) #다음날의 09:00

        # start_time 이후이고, (end_time - 10초) 이전일 때 실행할 작업
        # 예: 특정 거래 가능 시간에만 거래를 수행하는 등의 작업
        # 오늘 09:00부터 다음날의 08:59:49까지
        if start_time <= now < (end_time - datetime.timedelta(seconds=10)):
            print("첫 번째 조건 들어감") #디버깅
            target_price = get_target_price("KRW-BTC")
            ma5 = get_ma5("KRW-BTC")
            current_price = get_current_price("KRW-BTC")

            # 1) 매수 조건으로 현재 가격이 목표가격보다 더 큰 경우로 설정
            # => 목표가보다 현재가가 더 큰걸 원한다는 것은 상승장을 예측하겠다는 의미
            # 2) 매수 조건으로 현재 가격이 이동평균선보다 높은 경우로 설정
            # => 일반적으로 현재 가격이 이동평균선보다 크면 상승장이기 때문에 상승장을 예측하겠다는 의미
            if current_price >= target_price and current_price >= ma5:
                krw = get_balance("KRW")
                if krw >= 5000:
                    buy_result = upbit.buy_market_order("KRW-BTC", krw * 0.9995)
                    print(buy_result) # 거래소 어플에서 알림이 오기 때문에 굳이 슬랙 메시지를 보내지 않음

        # start_time 이전이거나, (end_time - 10초) 이후일 때 실행할 작업
        # 예: 특정 거래 가능 시간 이외의 시간에는 다른 동작을 하는 등의 작업
        # 10초전에 싹 팔아버림-> 다음 날의 08:59:50부터 08:59:59까지 일괄매도
        elif (end_time - datetime.timedelta(seconds=10)) <= now < end_time:
            print("두 번째 조건 들어감") #디버깅
            btc = get_balance("BTC")
            if btc >= 0.00008:
                # 팔때는 수수료를 감안하지 않고 전수매도를 해야함.
                # 그렇게 되면 코인은 전수매도되고 원화에서 수수료가 나감.
                # 수수료를 반영하면 코인을 덜 팔고 일부 코인이 잔고에 남음.
                sell_result = upbit.sell_market_order("KRW-BTC", btc)
                print(sell_result) # 거래소 어플에서 알림이 오기 때문에 굳이 슬랙 메시지를 보내지 않음

        time.sleep(1)
    except Exception as e:
        print_autotrade_e = f"자동매매 하는 과정에서 에러가 발생했습니다: {e}"
        client.chat_postMessage(channel = "#비트코인-자동매매", text = print_autotrade_e) #슬랙으로 에러메시지 보냄
        time.sleep(1)

