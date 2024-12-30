from PnlTradingEngine import PnlTradingEngine
from Strategy1 import Strategy1
from Candlesticks import Candlesticks
from TradingDTOs import *
from datetime import datetime, timedelta
import random
import time

class MockMarketManager(AbstractMarketManager):
    def __init__(self):
        self.current_price = 1
        self.candlesticks = Candlesticks([1, 60])
        self.current_time = datetime.now()

    def get_candlesticks(self, token_address: str, interval: int)->list[Candlestick]:
        return self.candlesticks.get_candlestick_builder(interval).get_all()

    def update_price(self, new_price: float):
        self.candlesticks.update(self.current_time, new_price)
        self.current_price = new_price
        self.current_time += timedelta(seconds=1)

    def get_price(self, token_address: str):
        return self.current_price
    
class MockOrderExecutor(OrderExecutor):
    def  __init__(self, market_manager):
        OrderExecutor.__init__(self, market_manager)
    
    @abstractmethod
    def execute_order(self, order: Order, retry_until_successful = False)->str:
        return "DONE"

class TestSetup:
    market_manager = MockMarketManager()
   
    #Populate default candlesticks for a mock token
    for i in range(600): # Simulate 2 minutes of data
        price = random.uniform(100, 200)
        market_manager.update_price(price)       

    token_info = TokenInfo("test_token")
    token_info.decimals_scale_factor = 1E9

    #Setup Order
    default_buy_amount = Amount.sol_ui(.001)
    slippage = Amount.percent_ui(50)
    priority_fee = Amount.sol_ui(.0004)
    profit_limit = PnlOption(trigger_at_percent = Amount.percent_ui(100), allocation_percent = Amount.percent_ui(100))
    stop_loss = PnlOption(trigger_at_percent = Amount.percent_ui(-80), allocation_percent = Amount.percent_ui(100))
    base_token_price = Amount.sol_ui(market_manager.get_price("test_token"))
    tokens_bought = Amount.tokens_ui(1000, token_info.decimals_scale_factor)
    order = OrderWithLimitsStops(token_info.token_address, base_token_price, tokens_bought, slippage, priority_fee)          
    order.add_pnl_option(profit_limit)
    order.add_pnl_option(stop_loss)

    #Setup Mock Executor
    order_executor = MockOrderExecutor(market_manager)

def test_Strategy1():
    test_setup = TestSetup()

    strategy_settings =  {
        "module_filename" : "SimpleBuyDipEngine.py",
        "strategy_title" : "Buy the Dip on a 1 minute chart",
        "token_address" : "2zMMhcVQEXDtdE6vsFS7S7D5oUodfJHE8vd1gnBouauv",
        "trigger_drop_percent": 2,
        "chart_interval": 1,
        "limit_orders" : [{"trigger_at_percent": 80, "allocation_percent": 100}],
        "stop_loss_orders" : [{"trigger_at_percent": -80, "allocation_percent": 100}]
    }
    
    token_address = test_setup.token_info.token_address      
    strategy_order = StrategyOrder(Order_Type.SIMPLE_BUY_DIP_STRATEGY, token_address, test_setup.default_buy_amount,
                                                            test_setup.slippage, test_setup.priority_fee, strategy_settings)                                    
    engine = Strategy1(test_setup.token_info, test_setup.order_executor, strategy_order)
    engine.start()
    
    #Force a 10% jump
    test_setup.market_manager.update_price(test_setup.market_manager.current_price * 1.1)
    engine._process_event_task()
    
    assert engine.state == StrategyState.PENDING
    
    #Force a 2% drop
    test_setup.market_manager.update_price(test_setup.market_manager.current_price * .95)
    
    engine._process_event_task()

    assert engine.state == StrategyState.COMPLETE

def test_PnlTradingEngine():    
    test_setup = TestSetup()

    engine = PnlTradingEngine(test_setup.token_info, test_setup.order_executor, test_setup.order)

    engine.start()

    #Check if limit order or stop order triggers
    engine._process_event_task()

    assert engine.state == StrategyState.PENDING

    limit_price = (1+test_setup.profit_limit.trigger_at_percent.ToUiValue()/100)*test_setup.base_token_price.ToUiValue()
    stop_price = (1+test_setup.stop_loss.trigger_at_percent.ToUiValue()/100)*test_setup.base_token_price.ToUiValue()
    
    #Force Limit Price
    test_setup.market_manager.current_price = limit_price
    engine._process_event_task()
    
    assert engine.state == StrategyState.COMPLETE

    #Reset State
    engine.state = StrategyState.PENDING

    #Force Stop Loss Price
    test_setup.market_manager.current_price = stop_price
    engine._process_event_task()
    
    assert engine.state == StrategyState.COMPLETE
    
test_Strategy1()

test_PnlTradingEngine()