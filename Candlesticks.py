from datetime import datetime, timedelta

class Candlestick:
    def __init__(self, start_time: datetime, interval_secs: int, open_price: float):
        self.start_time = start_time
        self.end_time = start_time + timedelta(seconds=interval_secs)
        self.open = open_price
        self.high = open_price
        self.low = open_price
        self.close = open_price
        self.volume = 0
    
    def update(self, price):
        if price > self.high:
            self.high = price
        elif price < self.low:
            self.low = price
        
        self.close = price
        self.volume += 1  # Increment volume (can replace with actual traded volume if available)
    
class CandlestickBuilder:
    def __init__(self, interval: int, max_length = 1000):
        self.interval = interval
        self.current_candle: Candlestick = None
        self.candlesticks : list[Candlestick] = []  # Store historical candlesticks
        self.max_length = max_length

    def update(self, timestamp: datetime, price: float):
        if self.current_candle is None or timestamp >= self.current_candle.end_time:
            self.current_candle = Candlestick(start_time=timestamp, interval_secs=self.interval, open_price=price)
            self.candlesticks.append(self.current_candle)

            if len(self.candlesticks) > self.max_length :  # Keep only the latest candles for memory efficiency
                self.candlesticks.pop(0)

        # Update the current candle
        self.current_candle.update(price)
    
    def get_all(self)->list[Candlestick]:
        return self.candlesticks
    
    def get(self, count: int)->list[Candlestick]:
        if len(self.candlesticks) >= count:
           return self.candlesticks[-count:]
            
class Candlesticks:
    def __init__(self, intervals: list[int], max_length = 1000):
        self.candlestick_builders : dict[int, CandlestickBuilder] = {}
        
        for interval in intervals:
            self.candlestick_builders[interval] = CandlestickBuilder(interval=interval, max_length=max_length)
    
    def update(self, timestamp: datetime, price: float):
        for candlestick_builder in self.candlestick_builders.values():
            candlestick_builder.update(timestamp, price)
        
    def get_candlestick_builder(self, interval: int)->CandlestickBuilder:
        if interval in self.candlestick_builders:
            return self.candlestick_builders[interval]    
