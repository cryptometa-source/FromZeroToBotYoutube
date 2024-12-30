from enum import Enum
from abc import abstractmethod
from Candlesticks import Candlestick

class StrategyState(Enum):
    PENDING = 0,
    COMPLETE = 1,
    FAILED = 2

class SignalState(Enum):
    TRIGGERED = 0,
    UNTRIGGERED = 1

class Value_Type(Enum):
    UI = 0
    SCALED = 1

class Order_Type(Enum):
    BUY = 0
    SELL = 1
    LIMIT_STOP_ORDER = 2,
    SIMPLE_BUY_DIP_STRATEGY = 3,
    OTHER_STRATEGY = 4

class Amount_Units:
    SOL = 0
    USD = 1
    TOKENS = 2
    PERCENT = 3

class Amount:
    def __init__(self, value_type: Value_Type, amount_units: Amount_Units, amount: int, scalar: int):
        self.value_type = value_type
        self.amount_units = amount_units
        self.value = amount
        self.scalar = scalar
    
    def set_amount(self, amount: int):
        self.value = amount

    def ToUiValue(self)->float:
        if self.value_type == Value_Type.UI:
            return self.value
        else:
            return self.value/self.scalar
    
    def ToScaledValue(self)->int:
        if self.value_type == Value_Type.SCALED:
            return self.value
        else:
            return int(self.value*self.scalar)
    
    def GetScalar(self)->float:
        return self.scalar
    
    @staticmethod
    def sol_ui(amount: float):
        return Amount(Value_Type.UI, Amount_Units.SOL, amount, 1E9)

    @staticmethod
    def sol_scaled(amount: int):
        return Amount(Value_Type.SCALED, Amount_Units.SOL, int(amount), 1E9)
    
    @staticmethod
    def tokens_ui(amount: float, scalar: int):
        return Amount(Value_Type.UI, Amount_Units.TOKENS, amount, scalar)
    
    @staticmethod
    def percent_ui(amount: float):
        return Amount(Value_Type.UI, Amount_Units.PERCENT, amount, 100)

class TriggerPrice:
    def __init__(self, in_sell_amount: Amount, target_price: Amount):
        self.in_sell_amount = in_sell_amount
        self.target_price = target_price
        
class PnlOption:
    def __init__(self, trigger_at_percent: Amount, allocation_percent: Amount):
        self.trigger_at_percent = trigger_at_percent
        self.allocation_percent = allocation_percent

    @staticmethod
    def from_dict(values: dict[str, any]):
        return PnlOption(Amount.percent_ui(values.get("trigger_at_percent", 0)),
                        Amount.percent_ui(values.get("allocation_percent", 100)))      
class CallEvent:
    user = ""
    message = ""
    contract_addresses : list[str] = []

class Order:
    def __init__(self, order_type: Order_Type, token_address: str, amount: Amount, slippage: Amount, priority_fee: Amount, confirm_transaction = True):
        self.order_type = order_type
        self.token_address = token_address
        self.amount = amount
        self.slippage = slippage
        self.priority_fee = priority_fee
        self.confirm_transaction = confirm_transaction

class StrategyOrder(Order):
  def __init__(self, order_type: Order_Type, token_address: str, amount_in: Amount, slippage: Amount, priority_fee: Amount, strategy_settings: dict[str, any]):
        Order.__init__(self, order_type, token_address, amount_in, slippage, priority_fee)
        self.strategy_settings = strategy_settings

class OrderWithLimitsStops(Order):
    def __init__(self, token_address: str, base_token_price: Amount, amount_in: Amount, slippage: Amount, priority_fee: Amount):
        Order.__init__(self, Order_Type.LIMIT_STOP_ORDER, token_address, amount_in, slippage, priority_fee)
        
        self.limits: list[PnlOption] = []
        self.stop_losses: list[PnlOption] = []
        self.base_token_price = base_token_price

    def add_pnl_option(self, pnl_option: PnlOption):
        if pnl_option.trigger_at_percent.ToUiValue() > 0:
            self.limits.append(pnl_option)
        elif pnl_option.trigger_at_percent.ToUiValue() < 0:
            self.stop_losses.append(pnl_option)

class TokenAccountInfo:
    def __init__(self, token_address: str, token_account_address: str, balance: Amount):
        self.token_address = token_address
        self.token_account_address = token_account_address
        self.balance = balance

class TokenInfo:
    def __init__(self, token_address):
        self.token_address = token_address
        self.market_id = ''
        self.price = 0
        self.token_vault_ui_amount = 0
        self.sol_vault_address = ''
        self.token_vault_address = ''
        self.sol_address = ''
        self.token_decimals = ''
        self.decimals_scale_factor = 0

class SwapTransactionInfo:
    def __init__(self):
        self.transaction_signature = ''
        self.token_address = ''
        self.payer_address = ''
        self.payer_token_account_address = ''
        self.payer_token_ui_balance = 0
        self.sol_diff = 0 #scaled
        self.token_diff = 0 #ui amount

    def print_swap_info(self):
        sol_amount = str(abs(self.sol_diff)/1e9)
        token_amount = str(abs(self.token_diff))

        if self.sol_diff < 0:
            print(f"{self.payer_address} bought {token_amount} for {sol_amount} SOL")
        else:
            print(f"{self.payer_address} sold {token_amount} for {sol_amount} SOL")

class AbstractMarketManager:
    @abstractmethod
    def get_price(self, token_address: str)->float:
        pass

    @abstractmethod
    def get_candlesticks(self, token_address: str, interval: int)->list[Candlestick]:
        pass
    
class OrderExecutor:
    def __init__(self, market_manager: AbstractMarketManager):#FIXME
        self.market_manager = market_manager

    @abstractmethod
    async def execute_order(self, order: Order, retry_until_successful = False)->str:
        pass
    
    @abstractmethod
    def get_order_transaction(self, tx_signature)->SwapTransactionInfo:
        pass

    @abstractmethod
    def get_account_balance(self, account_address: str)->Amount:
        pass

    def get_market_manager(self)->AbstractMarketManager:
        return self.market_manager