from datamodel import OrderDepth, UserId, TradingState, Order
from typing import List
import string

class Trader:
    
    def __init__(self):
        self.positions = {}  
        
    def run(self, state: TradingState):
        print("traderData: " + state.traderData)
        print("Observations: " + str(state.observations))

       
        result = {}
        for product in state.order_depths:
            order_depth: OrderDepth = state.order_depths[product]
            orders: List[Order] = []
            acceptable_price = 10 
            print("Acceptable price : " + str(acceptable_price))
            print("Buy Order depth : " + str(len(order_depth.buy_orders)) + ", Sell order depth : " + str(len(order_depth.sell_orders)))

           
            current_position = self.positions.get(product, 0)
            print(f"Current position for {product}: {current_position}")
            
            if len(order_depth.sell_orders) != 0:
                best_ask, best_ask_amount = list(order_depth.sell_orders.items())[0]
                if int(best_ask) < acceptable_price and current_position < 50:
                    order_size = min(-best_ask_amount, 50 - current_position)  
                    if order_size != 0:
                        print("BUY", str(order_size) + "x", best_ask)
                        orders.append(Order(product, best_ask, quantity=order_size))

            if len(order_depth.buy_orders) != 0:
                best_bid, best_bid_amount = list(order_depth.buy_orders.items())[0]
                if int(best_bid) > acceptable_price and current_position > -50:
                    order_size = min(best_bid_amount, 50 + current_position)  # Ensure position does not exceed limit
                    if order_size != 0:
                        print("SELL", str(order_size) + "x", best_bid)
                        orders.append(Order(product, best_bid, quantity=order_size))

            result[product] = orders

            
            self.positions[product] = current_position + sum(order.quantity for order in orders)
    
        
        traderData = "SAMPLE"
        
       
        conversions = 1
        return result, conversions, traderData
