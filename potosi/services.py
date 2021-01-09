from typing import Callable

from binance.client import Client as BinanceClient
from peewee import fn

from .dataclasses import OrderUpdateEvent
from .log import get_logger
from .models import Order, OrderPlaceType, Trade
from .parser_signal import ParserSignal
from .trading import Trading

logger = get_logger(__name__)


class TradeService(object):
    def __init__(self, trading: Trading, parser: ParserSignal):
        self.parser_signal = parser
        self.trading = trading

    def create(self, raw_signal: str):
        # try:
        signal_parsed = self.parser_signal.parser_signal_created(raw_signal)

        # 20 USD
        entry_zone = signal_parsed["entry_zone"]
        leverage = signal_parsed["leverage"]
        amount = 25.0 * leverage
        entries = []

        # calculate entries
        entries_percentages = [amount]

        if len(entry_zone) == 3:
            entries_percentages = [amount * 0.7, amount * 0.2, amount * 0.1]
        elif len(entry_zone) == 2:
            entries_percentages = [amount * 0.8, amount * 0.1]

        for i, v in enumerate(entries_percentages):
            amount = float(v) / float(entry_zone[i])
            entries.append([float(entry_zone[i]), amount])

        trade_created = Trade.create(
            symbol=signal_parsed["symbol"], raw_signal=raw_signal
        )

        # create orders
        total_amount = 0
        target = 1

        for entry in entries:
            order = self.trading.create_order(
                symbol=signal_parsed["symbol"],
                side=BinanceClient.SIDE_BUY,
                order_type="LIMIT",
                price=str(entry[0]),
                quantity=str(entry[1]),
            )

            Order.create(
                trade=trade_created,
                order_id=order["orderId"],
                client_order_id=order["clientOrderId"],
                symbol=order["symbol"],
                type=order["type"],
                status=order["status"],
                place_type=OrderPlaceType.ENTRY,
                target=target,
            )
            total_amount = total_amount + float(order["origQty"])
            target = target + 1

        # stop loss order
        sl_order = self.trading.create_order(
            symbol=signal_parsed["symbol"],
            side=BinanceClient.SIDE_SELL,
            order_type="STOP_MARKET",
            quantity=total_amount,
            stop_price=signal_parsed["stoploss"],
        )

        Order.create(
            trade=trade_created,
            order_id=sl_order["orderId"],
            client_order_id=sl_order["clientOrderId"],
            symbol=sl_order["symbol"],
            type=sl_order["type"],
            status=sl_order["status"],
            place_type=OrderPlaceType.EXIT,
            amount=sl_order["origQty"],
        )
        # except BinanceAPIException as e:
        #     logger.exception(e)
        # except Exception as e:
        #     logger.exception(e)

    def close(self, raw_signal):
        # try:
        symbol = self.parser_signal.parser_signal_closed(raw_signal)
        trade = Trade.get_or_none(
            (Trade.symbol == symbol) & (Trade.is_opened == True)  # noqa: E712
        )

        if trade is None:
            return

        extract_order_id: Callable[[Order], int] = lambda order: order.order_id

        orders_id = list(map(extract_order_id, trade.orders))
        self.trading.close_multiple_orders(symbol, orders_id)

        trade.is_opened = False
        trade.save()
        # except Exception as e:
        #     logger.exception('Exception occurred')

    def update(self, order_event: OrderUpdateEvent):
        # quando preenchido
        # se uma ordem stoploss for preenchida
        order = Order.get_or_none(Order.order_id == order_event.order_id)

        if order is None:
            return

        trade = order.trade
        order.status = order_event.order_status

        if (
            order_event.order_status == "FILLED"
            or order_event.order_status == "PARTIALLY_FILLED"
        ):
            order.amount = order_event.last_filled_qty

        order.save()

        if order_event.order_status == "PARTIALLY_FILLED":
            return

        signal = self.parser_signal.parser_signal_created(trade.raw_signal)
        to_insert = []

        if order_event.order_status == "FILLED":
            if order.is_entry_order() and order.type == "LIMIT":

                if not order.is_first_target():
                    entry_orders = (
                        Order.select(Order.order_id)
                        .where(
                            (Order.trade == trade)
                            & (Order.place_type == OrderPlaceType.EXIT)
                            & (Order.status == "NEW")
                        )
                        .dicts()
                    )

                    orders_id = []
                    for row in entry_orders:
                        orders_id.append(row["order_id"])

                    if len(orders_id):
                        self.trading.close_multiple_orders(
                            symbol=trade.symbol, orders=orders_id
                        )
                        Order.update(status="CANCELLED").where(
                            Order.order_id << orders_id
                        ).execute()

                query = Order.select(fn.SUM(Order.amount)).where(
                    (Order.trade == trade)
                    & (Order.place_type == OrderPlaceType.ENTRY)
                    & (
                        (Order.status == "FILLED")
                        | (Order.status == "PARTIALLY_FILLED")
                    )
                )

                # calcular quando nao tiver saldo para criar as demais ordens
                result_query = query.scalar()
                amount = 0 if result_query is None else result_query
                amount_per_target = amount / len(signal["exit_targets"])
                nth = 1

                for entry in signal["exit_targets"]:
                    result = self.trading.create_order(
                        symbol=signal["symbol"],
                        side=BinanceClient.SIDE_SELL,
                        order_type="LIMIT",
                        price=str(entry),
                        quantity=str(amount_per_target),
                        reduce_only=True,
                    )

                    to_insert.append(
                        {
                            "order_id": result["orderId"],
                            "client_order_id": result["clientOrderId"],
                            "symbol": result["symbol"],
                            "type": result["type"],
                            "status": result["status"],
                            "trade": trade,
                            "target": nth,
                            "place_type": OrderPlaceType.EXIT,
                        }
                    )
                    nth = nth + 1

                Order.insert_many(to_insert).execute()
            elif order.is_exit_order() and order.type == "LIMIT":
                if order.is_first_target():
                    entry_orders = (
                        Order.select(Order.order_id)
                        .where(
                            (Order.trade == trade)
                            & (Order.place_type == OrderPlaceType.ENTRY)
                            & (Order.status == "NEW")
                        )
                        .dicts()
                    )

                    orders_id = []
                    for row in entry_orders:
                        orders_id.append(row["order_id"])

                    if len(orders_id):
                        self.trading.close_multiple_orders(
                            symbol=trade.symbol, orders=orders_id
                        )
                        Order.update(status="CANCELLED").where(
                            Order.order_id << orders_id
                        ).execute()

                # update stoploss order
                stoploss_order = Order.get(
                    (Order.type == "STOP_MARKET")
                    & (Order.place_type == OrderPlaceType.EXIT)
                )

                self.trading.close_multiple_orders(
                    symbol=trade.symbol, orders=[stoploss_order.order_id]
                )
                stoploss_order.status = "CANCELLED"
                stoploss_order.save()

                query = Order.select(fn.SUM(Order.amount)).where(
                    (Order.trade == trade)
                    & (Order.place_type == OrderPlaceType.ENTRY)
                    & (
                        (Order.status == "FILLED")
                        | (Order.status == "PARTIALLY_FILLED")
                    )
                )

                # calcular quando nao tiver saldo para criar as demais ordens
                result_query = query.scalar()
                amount = 0 if result_query is None else result_query

                # stop loss order
                new_sl_order = self.trading.create_order(
                    symbol=trade.symbol,
                    side=BinanceClient.SIDE_SELL,
                    order_type="STOP_MARKET",
                    quantity=amount,
                    stop_price=stoploss_order,
                )

                Order.create(
                    trade=trade,
                    order_id=new_sl_order["orderId"],
                    client_order_id=new_sl_order["clientOrderId"],
                    symbol=new_sl_order["symbol"],
                    type=new_sl_order["type"],
                    status=new_sl_order["status"],
                    place_type=OrderPlaceType.EXIT,
                    amount=new_sl_order["origQty"],
                )
            elif order.type == "STOP_MARKET":
                entry_orders = (
                    Order.select(Order.order_id)
                    .where((Order.trade == trade) & (Order.status == "NEW"))
                    .dicts()
                )

                orders_id = []
                for row in entry_orders:
                    orders_id.append(row["order_id"])

                if len(orders_id):
                    self.trading.close_multiple_orders(
                        symbol=trade.symbol, orders=orders_id
                    )
                    Order.update(status="CANCELLED").where(
                        Order.order_id << orders_id
                    ).execute()

                trade.is_opened = False
                trade.save()
