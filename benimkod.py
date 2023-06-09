import pandas as pd
import requests
import talib
import numpy as np
from binance.client import Client
from telegram import Update
from telegram.ext import Updater, CommandHandler, CallbackContext


class Data:
    def __init__(self, interval, symbol, period, telegram):
        self.interval = interval
        self.symbol = symbol
        self.period = period
        self.x = telegram

    def fetchData(self, context: CallbackContext):
        binanceUrl = 'https://api.binance.com/api/v3/klines'
        params = {
            'symbol': self.symbol.upper(),
            'interval': self.interval
        }
        response = requests.get(binanceUrl, params=params)
        data = response.json()

        df = pd.DataFrame(data)
        df.columns = ['open_time', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'quote_asset_volume',
                    'number_of_trades', 'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore']
        df['close'] = pd.to_numeric(df['close'])
        df['low'] = pd.to_numeric(df['low'])
        df['high'] = pd.to_numeric(df['high'])

        # Calculate RSI
        delta = df['close'].diff()
        up = delta.clip(lower=0)
        down = -1*delta.clip(upper=0)
        ema_up = up.ewm(com=self.period-1, adjust=False).mean()
        ema_down = down.ewm(com=self.period-1, adjust=False).mean()
        rs = ema_up/ema_down
        rsi = 100 - (100/(1 + rs))

        # Calculate StochRSI 'K' and 'D' lines
        min_rsi = rsi.rolling(window=self.period).min()
        max_rsi = rsi.rolling(window=self.period).max()
        stoch_rsi_k = 100 * (rsi - min_rsi) / (max_rsi - min_rsi)
        stoch_rsi_d = stoch_rsi_k.rolling(window=3).mean()

        # Calculate Stochastic Oscillator
        low_min = df['low'].rolling(window=self.period).min()
        high_max = df['high'].rolling(window=self.period).max()
        df['%K'] = (df['close'] - low_min)*100/(high_max - low_min)
        df['%D'] = df['%K'].rolling(window=3).mean()

        context.bot_data['k'] = stoch_rsi_k.iloc[-1]
        context.bot_data['d'] = stoch_rsi_d.iloc[-1]
        context.bot_data['%K'] = df['%K'].iloc[-1]
        context.bot_data['%D'] = df['%D'].iloc[-1]

        self.analyze_data(context)



    def analyze_data(self, context: CallbackContext):
        k = context.bot_data.get('k')
        d = context.bot_data.get('d')
        stoch_k = context.bot_data.get('%K')
        stoch_d = context.bot_data.get('%D')

        if k is not None and d is not None and stoch_k is not None and stoch_d is not None:
            action = 'BEKLE'

            # Check StochRSI
            if k < 30 and d < 30:
                action = 'AL - StochRSI'
            elif k > 70 and d > 70:
                action = 'SAT - StochRSI'
            
            # Check Stochastic Oscillator
            if stoch_k < 20 and stoch_d < 20:
                action = 'AL - Stokastik'
            elif stoch_k > 80 and stoch_d > 80:
                action = 'SAT - Stokastik'

            context.bot.send_message(chat_id=self.x.chat_id,
                                    text=f'Son Stokastik RSI K değeri: {k:.2f}, D değeri: {d:.2f}, '
                                        f'Son Stokastik Oscillator K değeri: {stoch_k:.2f}, D değeri: {stoch_d:.2f}, '
                                        f'Yapılacak işlem: {action}')



class Telegram:
    def __init__(self, TOKEN, CHAT_ID):
        self.token = TOKEN
        self.chat_id = CHAT_ID

    def runBot(self, token, data_instance):
        updater = Updater(token=self.token)
        dispatcher = updater.dispatcher
        dispatcher.add_handler(CommandHandler('start', self.basla))
        updater.start_polling()
        job_queue = updater.job_queue
        job_queue.run_repeating(data_instance.fetchData, interval=60, first=0)
        updater.idle()

    def basla(self, update: Update, _: CallbackContext):
        update.message.reply_text('Ben bir telegram botuyum')


if __name__ == '__main__':
    telegram_instance = Telegram(, )
    data_instance = Data('15m', 'ethtry', 14, telegram_instance)
    telegram_instance.runBot(, data_instance)
