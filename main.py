from datamodel import OrderDepth, TradingState, Order
from typing import List, Dict

class Trader:
    def __init__(self, spread=0.02, order_size=10, position_limit=50):
        self.spread = spread
        self.order_size = order_size
        self.position_limit = position_limit
        self.positions: Dict[str, int] = {} 
    def run(self, state: TradingState):
        print("Observations: " + str(state.observations))  
        result = {}

        for product in state.order_depths:
            order_depth: OrderDepth = state.order_depths[product]
            orders: List[Order] = []

            
            current_position = self.positions.get(product, 0)
            acceptable_price = 10  
           
            if len(order_depth.sell_orders) > 0:
                best_ask, best_ask_amount = list(order_depth.sell_orders.items())[0]

               
                if current_position < self.position_limit and int(best_ask) < acceptable_price:
                    print("BUY", str(-best_ask_amount) + "x", best_ask)
                    orders.append(Order(product, best_ask, -best_ask_amount))

            if len(order_depth.buy_orders) > 0:
                best_bid, best_bid_amount = list(order_depth.buy_orders.items())[0]

                
                if current_position > -self.position_limit and int(best_bid) > acceptable_price:
                    print("SELL", str(best_bid_amount) + "x", best_bid)
                    orders.append(Order(product, best_bid, -best_bid_amount))

            
            if product not in self.positions:
                self.positions[product] = 0  
            self.positions[product] += sum(order.size for order in orders)  
           
            result[product] = orders

        
        traderData = "SAMPLE"
        conversions = 1  
        
        return result, conversions, traderData
