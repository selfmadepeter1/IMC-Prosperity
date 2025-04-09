import json
from typing import Any
from typing import List, Dict
from collections import deque

from datamodel import Listing, Observation, Order, OrderDepth, ProsperityEncoder, Symbol, Trade, TradingState


class Logger:
    def __init__(self) -> None:
        self.logs = ""
        self.max_log_length = 3750

    def print(self, *objects: Any, sep: str = " ", end: str = "\n") -> None:
        self.logs += sep.join(map(str, objects)) + end

    def flush(self, state: TradingState, orders: dict[Symbol, list[Order]], conversions: int, trader_data: str) -> None:
        base_length = len(
            self.to_json(
                [
                    self.compress_state(state, ""),
                    self.compress_orders(orders),
                    conversions,
                    "",
                    "",
                ]
            )
        )

        # We truncate state.traderData, trader_data, and self.logs to the same max. length to fit the log limit
        max_item_length = (self.max_log_length - base_length) // 3

        print(
            self.to_json(
                [
                    self.compress_state(state, self.truncate(state.traderData, max_item_length)),
                    self.compress_orders(orders),
                    conversions,
                    self.truncate(trader_data, max_item_length),
                    self.truncate(self.logs, max_item_length),
                ]
            )
        )

        self.logs = ""

    def compress_state(self, state: TradingState, trader_data: str) -> list[Any]:
        return [
            state.timestamp,
            trader_data,
            self.compress_listings(state.listings),
            self.compress_order_depths(state.order_depths),
            self.compress_trades(state.own_trades),
            self.compress_trades(state.market_trades),
            state.position,
            self.compress_observations(state.observations),
        ]

    def compress_listings(self, listings: dict[Symbol, Listing]) -> list[list[Any]]:
        compressed = []
        for listing in listings.values():
            compressed.append([listing.symbol, listing.product, listing.denomination])

        return compressed

    def compress_order_depths(self, order_depths: dict[Symbol, OrderDepth]) -> dict[Symbol, list[Any]]:
        compressed = {}
        for symbol, order_depth in order_depths.items():
            compressed[symbol] = [order_depth.buy_orders, order_depth.sell_orders]

        return compressed

    def compress_trades(self, trades: dict[Symbol, list[Trade]]) -> list[list[Any]]:
        compressed = []
        for arr in trades.values():
            for trade in arr:
                compressed.append(
                    [
                        trade.symbol,
                        trade.price,
                        trade.quantity,
                        trade.buyer,
                        trade.seller,
                        trade.timestamp,
                    ]
                )

        return compressed

    def compress_observations(self, observations: Observation) -> list[Any]:
        conversion_observations = {}
        for product, observation in observations.conversionObservations.items():
            conversion_observations[product] = [
                observation.bidPrice,
                observation.askPrice,
                observation.transportFees,
                observation.exportTariff,
                observation.importTariff,
                observation.sugarPrice,
                observation.sunlightIndex,
            ]

        return [observations.plainValueObservations, conversion_observations]

    def compress_orders(self, orders: dict[Symbol, list[Order]]) -> list[list[Any]]:
        compressed = []
        for arr in orders.values():
            for order in arr:
                compressed.append([order.symbol, order.price, order.quantity])

        return compressed

    def to_json(self, value: Any) -> str:
        return json.dumps(value, cls=ProsperityEncoder, separators=(",", ":"))

    def truncate(self, value: str, max_length: int) -> str:
        if len(value) <= max_length:
            return value

        return value[: max_length - 3] + "..."


logger = Logger()


class Trader:
    def __init__(self):
        self.positions: Dict[Symbol, int] = {}
        self.avg_entry_prices: Dict[Symbol, float] = {}
        self.last_traded_prices: Dict[Symbol, float] = {}
        self.mid_price_history: Dict[Symbol, deque] = {
            "SQUID_INK": deque(maxlen=20),
            "KELP": deque(maxlen=20),
            "RAINFOREST_RESIN": deque(maxlen=20)
        }

    def run(self, state: TradingState) -> tuple[dict[Symbol, list[Order]], int, str]:
        result: Dict[Symbol, List[Order]] = {}
        conversions = 0
        trader_data = ""

        logger.print("Timestamp:", state.timestamp)

        for product, order_depth in state.order_depths.items():
            orders: List[Order] = []
            current_position = state.position.get(product, 0)
            self.positions[product] = current_position
            logger.print(f"\nProcessing {product} | Position: {current_position}")

            # Track market trades to get the last traded price
            market_trades: List[Trade] = state.market_trades.get(product, [])
            if market_trades:
                last_price = market_trades[-1].price
                self.last_traded_prices[product] = last_price
            else:
                last_price = self.last_traded_prices.get(product, 0)

            # Get best bid and ask
            best_bid = max(order_depth.buy_orders.keys(), default=0)
            best_bid_volume = order_depth.buy_orders.get(best_bid, 0)
            best_ask = min(order_depth.sell_orders.keys(), default=999999)
            best_ask_volume = order_depth.sell_orders.get(best_ask, 0)

            # Fair price and mid-price
            if best_bid > 0 and best_ask < 999999:
                mid_price = (best_bid + best_ask) / 2
            else:
                mid_price = last_price

            self.mid_price_history[product].append(mid_price)
            sma = sum(self.mid_price_history[product]) / len(self.mid_price_history[product])

            # Dynamic delta (0.15% of mid-price)
            delta = 0.0015 * mid_price
            entry_price = self.avg_entry_prices.get(product, mid_price)

            logger.print(f"{product} | Mid: {mid_price:.2f}, SMA: {sma:.2f}, Δ: {delta:.2f}")

            # === Trading Logic === #

            # Trend-based Shorting: Price above SMA → SELL (short)
            if mid_price > sma + delta and current_position > -50 and best_bid > 0:
                short_qty = min(best_bid_volume, 50 + current_position)
                if short_qty > 0:
                    orders.append(Order(product, best_bid, -short_qty))
                    logger.print(f"SHORT {short_qty} @ {best_bid}")

            # Trend-based Long: Price below SMA → BUY
            if mid_price < sma - delta and current_position < 50 and best_ask < 999999:
                buy_qty = min(best_ask_volume, 50 - current_position)
                if buy_qty > 0:
                    orders.append(Order(product, best_ask, buy_qty))
                    # update avg entry price
                    self.avg_entry_prices[product] = (
                        (entry_price * abs(current_position) + best_ask * buy_qty) /
                        max(abs(current_position) + buy_qty, 1)
                    )
                    logger.print(f"BUY {buy_qty} @ {best_ask} | New Avg Entry: {self.avg_entry_prices[product]:.2f}")

            
            if current_position > 0 and best_bid > entry_price + delta:
                sell_qty = min(current_position, best_bid_volume)
                if sell_qty > 0:
                    orders.append(Order(product, best_bid, -sell_qty))
                    logger.print(f"TAKE PROFIT {sell_qty} @ {best_bid}")

           
            if current_position < 0 and best_ask < entry_price - delta:
                cover_qty = min(abs(current_position), best_ask_volume)
                if cover_qty > 0:
                    orders.append(Order(product, best_ask, cover_qty))
                    logger.print(f"COVER SHORT {cover_qty} @ {best_ask}")

            result[product] = orders

        logger.flush(state, result, conversions, trader_data)
        return result, conversions, trader_data