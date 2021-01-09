import pytest

from potosi.dataclasses import OrderUpdateEvent
from potosi.models import Order, OrderPlaceType, Trade
from potosi.services import TradeService


@pytest.fixture
def raw_signal():
    return """ℹ️ Update New Signal Created
〽️ #BTCUSDT
💹 BinanceFutures (Long X5)

➡️ Pending State
💰 18742.84

🔀 Entry Zone 🔀
1️⃣ 33299
2️⃣ 33199
2️⃣ 33099

🔆 Exit Targets:🔆
☑️ 33800 / 5.38%
☑️ 33900 / 8.06%
☑️ 34100 / 13.44%
☑️ 34200 / 16.13%

⛔️ StopLoss ⛔️
➡️ 30450 / 4.07% (Breakeven)
✳️ Breakeven after 2 target
🎇Risk 5/10
https://www.tradingview.com/x/LsOb112c

####################"""


@pytest.fixture
def raw_close_signal():
    return "ℹ️ Update: Signal BTCUSDT Closed"


def test_create_trade(database, parser_signal, raw_signal, mock_trading):
    with database.bind_ctx([Trade, Order]):
        trade_service = TradeService(trading=mock_trading, parser=parser_signal)
        trade_service.create(raw_signal)

        assert 1 == Trade.select().where(Trade.is_opened == True).count()  # noqa: E712
        assert (
            3
            == Order.select()
            .where(
                (Order.status == "NEW")
                & (Order.type == "LIMIT")
                & (Order.place_type == OrderPlaceType.ENTRY)
            )
            .count()
        )

        assert (
            1
            == Order.select()
            .where((Order.target == 1) & (Order.place_type == OrderPlaceType.ENTRY))
            .count()
        )
        assert (
            1
            == Order.select()
            .where((Order.target == 2) & (Order.place_type == OrderPlaceType.ENTRY))
            .count()
        )
        assert (
            1
            == Order.select()
            .where((Order.target == 3) & (Order.place_type == OrderPlaceType.ENTRY))
            .count()
        )
        assert (
            1
            == Order.select()
            .where((Order.status == "NEW") & (Order.type == "STOP_MARKET"))
            .count()
        )
        assert (
            0
            == Order.select()
            .where(
                (Order.status == "NEW")
                & (Order.type == "LIMIT")
                & (Order.place_type == OrderPlaceType.EXIT)
            )
            .count()
        )

        first = Order.get(
            (Order.target == 1) & (Order.place_type == OrderPlaceType.ENTRY)
        )
        assert True is first.is_first_target()


def test_close_trade(
    database, parser_signal, raw_signal, raw_close_signal, mock_trading
):
    with database.bind_ctx([Trade, Order]):
        signal = parser_signal.parser_signal_created(raw_signal)

        trade_service = TradeService(trading=mock_trading, parser=parser_signal)
        trade_service.create(raw_signal)
        condition = (Trade.symbol == signal["symbol"]) & (
            Trade.is_opened == True  # noqa: E712
        )

        assert 1 == Trade.select().where(condition).count()

        trade_service.close(raw_close_signal)

        assert 0 == Trade.select().where(condition).count()


def test_when_first_entry_filled_open_target_orders(
    database, parser_signal, raw_signal, mock_trading
):
    with database.bind_ctx([Trade, Order]):
        signal = parser_signal.parser_signal_created(raw_signal)

        trade_service = TradeService(trading=mock_trading, parser=parser_signal)
        trade_service.create(raw_signal)

        first_entry = Order.get(
            (Order.place_type == OrderPlaceType.ENTRY) & (Order.target == 1)
        )

        order_event = OrderUpdateEvent()
        order_event.event_type = "ORDER_TRADE_UPDATE"
        order_event.order_id = first_entry.order_id
        order_event.symbol = signal["symbol"]
        order_event.order_status = "FILLED"
        order_event.last_filled_qty = first_entry.amount

        trade_service.update(order_event)

        updated_order = Order.get_by_id(first_entry.id)

        assert "FILLED" == updated_order.status
        assert (
            len(signal["exit_targets"])
            == Order.select()
            .where(
                (Order.status == "NEW")
                & (Order.type == "LIMIT")
                & (Order.place_type == OrderPlaceType.EXIT)
            )
            .count()
        )


def test_when_no_first_target_archived_cancel_pending_entry_orders(
    database, parser_signal, raw_signal, mock_trading
):
    with database.bind_ctx([Trade, Order]):
        signal = parser_signal.parser_signal_created(raw_signal)

        trade_service = TradeService(trading=mock_trading, parser=parser_signal)
        trade_service.create(raw_signal)

        # filled first entry
        first_entry = Order.get(
            (Order.place_type == OrderPlaceType.ENTRY) & (Order.target == 1)
        )

        order_event = OrderUpdateEvent()
        order_event.event_type = "ORDER_TRADE_UPDATE"
        order_event.order_id = first_entry.order_id
        order_event.symbol = signal["symbol"]
        order_event.order_status = "FILLED"
        order_event.last_filled_qty = first_entry.amount

        trade_service.update(order_event)

        # filled second entry
        second_entry = Order.get(
            (Order.place_type == OrderPlaceType.ENTRY) & (Order.target == 2)
        )

        order_event.order_id = second_entry.order_id
        order_event.last_filled_qty = second_entry.amount

        trade_service.update(order_event)

        updated_order = Order.get_by_id(second_entry.id)

        assert "FILLED" == updated_order.status
        assert (
            2
            == Order.select()
            .where(
                (Order.status == "FILLED")
                & (Order.type == "LIMIT")
                & (Order.place_type == OrderPlaceType.ENTRY)
            )
            .count()
        )

        assert (
            len(signal["exit_targets"])
            == Order.select()
            .where(
                (Order.status == "CANCELLED")
                & (Order.type == "LIMIT")
                & (Order.place_type == OrderPlaceType.EXIT)
            )
            .count()
        )

        assert (
            len(signal["exit_targets"])
            == Order.select()
            .where(
                (Order.status == "NEW")
                & (Order.type == "LIMIT")
                & (Order.place_type == OrderPlaceType.EXIT)
            )
            .count()
        )


def test_when_first_target_archived_cancel_pending_entry_orders(
    database, parser_signal, raw_signal, mock_trading
):
    with database.bind_ctx([Trade, Order]):
        signal = parser_signal.parser_signal_created(raw_signal)

        trade_service = TradeService(trading=mock_trading, parser=parser_signal)
        trade_service.create(raw_signal)

        # filled first entry
        first_entry = Order.get(
            (Order.place_type == OrderPlaceType.ENTRY) & (Order.target == 1)
        )

        order_event = OrderUpdateEvent()
        order_event.event_type = "ORDER_TRADE_UPDATE"
        order_event.order_id = first_entry.order_id
        order_event.symbol = signal["symbol"]
        order_event.order_status = "FILLED"
        order_event.last_filled_qty = first_entry.amount

        trade_service.update(order_event)

        # filled first target
        first_target = Order.get(
            (Order.place_type == OrderPlaceType.EXIT) & (Order.target == 1)
        )

        order_event.order_id = first_target.order_id
        order_event.last_filled_qty = first_target.amount

        trade_service.update(order_event)

        updated_order = Order.get_by_id(first_target.id)

        assert "FILLED" == updated_order.status
        assert (
            2
            == Order.select()
            .where(
                (Order.status == "CANCELLED")
                & (Order.place_type == OrderPlaceType.ENTRY)
                & (Order.target.in_([2, 3]))
            )
            .count()
        )

        assert (len(signal["exit_targets"]) - 1) == Order.select().where(
            (Order.status == "NEW")
            & (Order.type == "LIMIT")
            & (Order.place_type == OrderPlaceType.EXIT)
            & (Order.target > 1)
        ).count()

        assert (
            1
            == Order.select()
            .where((Order.status == "NEW") & (Order.type == "STOP_MARKET"))
            .count()
        )
        assert (
            1
            == Order.select()
            .where((Order.status == "CANCELLED") & (Order.type == "STOP_MARKET"))
            .count()
        )


def test_when_stoploss_archived_close_pending_orders(
    database, parser_signal, raw_signal, mock_trading
):
    with database.bind_ctx([Trade, Order]):
        signal = parser_signal.parser_signal_created(raw_signal)

        trade_service = TradeService(trading=mock_trading, parser=parser_signal)
        trade_service.create(raw_signal)

        # filled entries orders
        entries = (
            Order.select()
            .where((Order.place_type == OrderPlaceType.ENTRY) & (Order.type == "LIMIT"))
            .order_by(Order.target.asc())
        )

        order_event = OrderUpdateEvent()
        order_event.event_type = "ORDER_TRADE_UPDATE"
        order_event.symbol = signal["symbol"]
        order_event.order_status = "FILLED"

        for o in entries:
            order_event.order_id = o.order_id
            order_event.last_filled_qty = o.amount
            trade_service.update(order_event)

        # filled first target
        first_target = Order.get(
            (Order.place_type == OrderPlaceType.EXIT) & (Order.target == 1)
        )

        order_event.order_id = first_target.order_id
        order_event.last_filled_qty = first_target.amount
        trade_service.update(order_event)

        # stoploss
        sl_order = Order.get((Order.type == "STOP_MARKET") & (Order.status == "NEW"))
        order_event.order_id = sl_order.order_id
        order_event.last_filled_qty = sl_order.amount
        trade_service.update(order_event)

        # trade
        trade = Trade.get(Trade.symbol == signal["symbol"])

        assert False is trade.is_opened
        assert (
            0
            == Order.select()
            .where((Order.status == "NEW") & (Order.type != "STOP_MARKET"))
            .count()
        )
