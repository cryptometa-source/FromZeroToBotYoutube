from PnlTradingEngine import PnlTradingEngine
from TradingDTOs import *
import time

class MockMarketManager(AbstractMarketManager):
    def __init__(self):
        self.price = 1

    def get_price(self, token_address: str):
        return self.price
    
class MockOrderExecutor(OrderExecutor):
    def  __init__(self, market_manager):
        OrderExecutor.__init__(self, market_manager)
    
    @abstractmethod
    async def execute_order(self, order: Order, retry_until_successful = False)->str:
        return "DONE"

def test_PnlTradingEngine():    
    #Setup Mock Market Manager
    market_manager = MockMarketManager()

    token_address = "test_token"
    token_info = TokenInfo(token_address)
    token_info.decimals_scale_factor = 1E9

    #Setup Order
    slippage = Amount.percent_ui(50)
    priority_fee = Amount.sol_ui(.0004)
    profit_limit = PnlOption(trigger_at_percent = Amount.percent_ui(100), percent_allocation = Amount.percent_ui(100))
    stop_loss = PnlOption(trigger_at_percent = Amount.percent_ui(-80), percent_allocation = Amount.percent_ui(100))
    base_token_price = Amount.sol_ui(market_manager.get_price("test_token"))
    tokens_bought = Amount.tokens_ui(1000, token_info.decimals_scale_factor)
    order = OrderWithLimitsStops(token_address, base_token_price, tokens_bought, slippage, priority_fee)          
    order.add_pnl_option(profit_limit)
    order.add_pnl_option(stop_loss)

    #Setup Mock Executor
    order_executor = MockOrderExecutor(market_manager)

    engine = PnlTradingEngine(token_info, order_executor, order)

    engine.start()

    #Check if limit order or stop order triggers
    engine._handle_update(token_address)

    time.sleep(1)

    assert engine.state == StrategyState.PENDING

    limit_price = (1+profit_limit.trigger_at_percent.ToUiValue()/100)*base_token_price.ToUiValue()
    stop_price = (1+stop_loss.trigger_at_percent.ToUiValue()/100)*base_token_price.ToUiValue()
    
    #Force Limit Price
    market_manager.price = limit_price
    engine._handle_update(token_address)

    time.sleep(2)
    
    assert engine.state == StrategyState.COMPLETE

    #Reset State
    engine.state = StrategyState.PENDING

    #Force Stop Loss Price
    market_manager.price = stop_price
    engine._handle_update(token_address)

    time.sleep(2)
    
    assert engine.state == StrategyState.COMPLETE
    
test_PnlTradingEngine()