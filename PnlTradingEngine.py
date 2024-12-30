from TradingDTOs import *
#from TokensApi import TokenInfo #FIXME
from pubsub import pub
import threading
import Globals as globals
import asyncio

class PnlTradingEngine(threading.Thread):
    def __init__(self, token_info: TokenInfo, order_executor: OrderExecutor, initial_order: OrderWithLimitsStops):
        threading.Thread.__init__(self)
        self.state = StrategyState.PENDING
        self.token_info = token_info
        self.slippage = initial_order.slippage
        self.priority_fee = initial_order.priority_fee
        self.initial_order = initial_order
        self.order_executor = order_executor      
        self.limit_order_trigger : TriggerPrice = None
        self.stop_loss_trigger : TriggerPrice  = None
        self.current_tokens = initial_order.amount.ToUiValue()
        self.max_slippage = Amount.percent_ui(100)
        self.updates_lock = threading.Lock()
        self.unprocessed_event_counter = 0
    
    def run(self):        
        self._init_strategy(self.initial_order.base_token_price, self.initial_order.amount)

    def _get_triggered_sell_amount(self, price: float):
        sell_amount = 0
        
        if self.limit_order_trigger and price >= self.limit_order_trigger.target_price.ToUiValue():
            sell_amount = self.limit_order_trigger.in_sell_amount.ToUiValue()
            print(f"Limit Order triggered")
        elif self.stop_loss_trigger and price <= self.stop_loss_trigger.target_price.ToUiValue(): 
            sell_amount = self.stop_loss_trigger.in_sell_amount.ToUiValue()
            print(f"Stop Loss Order triggered")

        return sell_amount
    
    @staticmethod
    def get_trigger_price(pnl_option: PnlOption, base_token_price: Amount, tokens_amount: Amount):
        pnl_percent = pnl_option.trigger_at_percent.ToUiValue()/100
        allocation_percent = pnl_option.allocation_percent.ToUiValue()/100
        allocated_amount = Amount.tokens_ui(tokens_amount.ToUiValue()*allocation_percent, tokens_amount.GetScalar())            
        target_price = Amount.sol_ui(base_token_price.ToUiValue()*(1+pnl_percent))
        
        return TriggerPrice(allocated_amount, target_price)
    
    def _init_strategy(self, base_token_price: Amount, tokens_amount: Amount):
        if len(self.initial_order.limits) > 0:
            self.limit_order_trigger = self.get_trigger_price(self.initial_order.limits[0], base_token_price, tokens_amount)
            print(f"Price={self.limit_order_trigger.target_price.ToUiValue()} Limit Order")
          
        if len(self.initial_order.stop_losses) > 0:
            self.stop_loss_trigger = self.get_trigger_price(self.initial_order.stop_losses[0], base_token_price, tokens_amount)
            print(f"Price={self.stop_loss_trigger.target_price.ToUiValue()} Stop Loss Order")

        pub.subscribe(topicName=globals.topic_token_update_event, listener=self._handle_update)

    def _process_event_task(self):
        if self.updates_lock.acquire(blocking=False):
            new_price = self.order_executor.get_market_manager().get_price(self.token_info.token_address)
            sell_amount = self._get_triggered_sell_amount(new_price)

            if sell_amount > 0:
                sell_amount = Amount.tokens_ui(min(sell_amount, self.current_tokens), self.token_info.decimals_scale_factor)
                new_order = Order(Order_Type.SELL, self.token_info.token_address, sell_amount, self.max_slippage, self.priority_fee)

                tx_signature = self.order_executor.execute_order(new_order, True)

                if tx_signature:
                    self.current_tokens -= sell_amount.ToUiValue() #Assumes all tokens sold
                    
                    if self.current_tokens <= 0:
                        self.state = StrategyState.COMPLETE  
                        pub.unsubscribe(topicName=globals.topic_token_update_event, listener=self._handle_update)

            self.updates_lock.release()

            if self.state != StrategyState.COMPLETE and self.unprocessed_event_counter > 0:
                self._process_event_task()
                self.unprocessed_event_counter = 0
        else:
            self.unprocessed_event_counter += 1        

    def _handle_update(self, arg1: str):
        if self.state != StrategyState.COMPLETE and arg1 == self.token_info.token_address:
            process_thread = threading.Timer(0, self._process_event_task)
            process_thread.start()