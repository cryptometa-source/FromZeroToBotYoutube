from TradingDTOs import *
from TokenDipSignalGenerator import TokenDipSignalGenerator
from AbstractTradingStrategy import AbstractTradingStrategy

class Strategy1(AbstractTradingStrategy):
    def __init__(self, token_info: TokenInfo, order_executor: OrderExecutor, order_settings: StrategyOrder):
        AbstractTradingStrategy.__init__(self, token_info, order_executor)

        self.order_settings = order_settings
        self.token_dip_signal_generator : TokenDipSignalGenerator = None
        self.pnl_options: list[PnlOption] = []
        self.load_from_dict(order_settings.strategy_settings)

    def get_type()->Order_Type:
        return Order_Type.SIMPLE_BUY_DIP_STRATEGY
    
    def process_event(self):
        trigger_state = self.token_dip_signal_generator.update()

        if trigger_state == SignalState.TRIGGERED:
            self.state = StrategyState.COMPLETE  

            #Create and Execute the Buy Order
            buy_order = Order(Order_Type.BUY, self.token_info.token_address, self.order_settings.amount, self.order_settings.slippage, self.order_settings.priority_fee)
            tx_signature = self.order_executor.execute_order(buy_order, True)

            if tx_signature:
                #Setup a limit order with a stop loss
                transaction_info = self.order_executor.get_order_transaction(tx_signature)

                if transaction_info and transaction_info.token_diff > 0:
                    temp_calc = abs(transaction_info.sol_diff/transaction_info.token_diff)   
                    base_token_price = Amount.sol_scaled(temp_calc)
                    tokens_bought = Amount.tokens_ui(transaction_info.token_diff, self.token_info.decimals_scale_factor)
                    
                    sell_order = OrderWithLimitsStops(self.token_info.token_address, base_token_price, tokens_bought, self.order_settings.slippage,
                                                  self.order_settings.priority_fee)
                    
                    for option in self.pnl_options:
                        sell_order.add_pnl_option(option)
                
                    #Start a limit and stop loss order
                    self.order_executor.execute_order(sell_order, True)
            else:
                print("Issue with executing the trade!") #TODO future feature: notify user

            self.stop()

    def load_from_dict(self, strategy_settings: dict[str, any]):                            
            sol_buy_amount = strategy_settings.get('amount_in')
            slippage = strategy_settings.get('slippage')
            priority_fee = strategy_settings.get('priority_fee')
            limit_orders = strategy_settings.get('limit_orders')
            stop_loss_orders = strategy_settings.get('stop_loss_orders')

            if sol_buy_amount:
                self.order_settings.amount.set_amount(sol_buy_amount)

            if slippage:
                self.order_settings.slippage.set_amount(slippage)
        
            if priority_fee:
                self.order_settings.priority_fee.set_amount(priority_fee)

            if limit_orders:
                for order in limit_orders:
                    self.pnl_options.append(PnlOption.from_dict(order))

            if stop_loss_orders:
                for order in stop_loss_orders:
                    self.pnl_options.append(PnlOption.from_dict(order))

            trigger_drop_percent = Amount.percent_ui(strategy_settings.get('trigger_drop_percent'))
            chart_interval = strategy_settings.get('chart_interval')

            self.token_dip_signal_generator = TokenDipSignalGenerator(self.token_info, self.order_executor.get_market_manager(), 
                                                                        chart_interval, trigger_drop_percent)
            