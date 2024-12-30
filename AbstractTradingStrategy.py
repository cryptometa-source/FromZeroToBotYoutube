from TradingDTOs import *
from abc import abstractmethod
from pubsub import pub
import threading
import Globals as globals

class AbstractTradingStrategy(threading.Thread):
    def __init__(self, token_info: TokenInfo, order_executor: OrderExecutor):
        threading.Thread.__init__(self)
        self.token_info = token_info
        self.order_executor = order_executor
        self.state = StrategyState.PENDING
        self.updates_lock = threading.Lock()
        self.unprocessed_event_counter = 0

    def run(self):        
        pub.subscribe(topicName=globals.topic_token_update_event, listener=self._handle_update)

    def stop(self):
        pub.unsubscribe(topicName=globals.topic_token_update_event, listener=self._handle_update)

    def _process_event_task(self):
        if self.updates_lock.acquire(blocking=False):
            self.process_event()

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

    @abstractmethod
    def get_type()->Order_Type:
        pass
    
    @abstractmethod
    def process_event(self):
        pass