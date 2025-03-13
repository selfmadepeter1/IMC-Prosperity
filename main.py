import backtrader as bt

class MarketMakingStrategy(bt.Strategy):
    params = (("spread", 0.02), ("order_size", 10))

    def __init__(self):
        self.buy_order = None  
        self.sell_order = None  
        self.last_bid_price = None
        self.last_ask_price = None

    def next(self):
        price = self.data.close[0]  

        # Compute new bid and ask prices
        bid_price = price * (1 - self.params.spread / 2)
        ask_price = price * (1 + self.params.spread / 2)

        # Only update orders if the bid/ask price has changed
        if self.buy_order and self.last_bid_price != bid_price:
            self.cancel(self.buy_order)
            self.buy_order = self.buy(size=self.params.order_size, price=bid_price, exectype=bt.Order.Limit)

        if self.sell_order and self.last_ask_price != ask_price:
            self.cancel(self.sell_order)
            self.sell_order = self.sell(size=self.params.order_size, price=ask_price, exectype=bt.Order.Limit)

        # Update last bid/ask prices
        self.last_bid_price = bid_price
        self.last_ask_price = ask_price

    def notify_order(self, order):
        """ Handles order status updates """
        if order.status in [order.Completed]:
            if order.isbuy():
                print(f"BUY EXECUTED: {order.executed.price}")
            elif order.issell():
                print(f"SELL EXECUTED: {order.executed.price}")


cerebro = bt.Cerebro()
cerebro.addstrategy(MarketMakingStrategy)


data = bt.feeds.GenericCSVData(dataname='market_data.csv', dtformat=2, openinterest=-1)
cerebro.adddata(data)


cerebro.run()
cerebro.plot()
