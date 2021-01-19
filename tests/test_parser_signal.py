import pytest

from potosi.parser_signal import ParserSignal


@pytest.fixture()
def signal():
    return """ℹ️ Update New Signal Created
〽️ #BTCUSDT
💹 BinanceFutures (Long X5)

➡️ Pending State
💰 18742.84

🔀 Entry Zone 🔀
1️⃣ 18700
2️⃣ 18600
2️⃣ 18500

🔆 Exit Targets:🔆
☑️ 18800 / 100%

⛔️ StopLoss ⛔️
➡️ 18450 / 4.07% (Breakeven)
✳️ Breakeven after 2 target
🎇Risk 5/10
https://www.tradingview.com/x/LsOb112c
"""


def test_parser_signal_created(signal):
    parser = ParserSignal()
    order = parser.parser_signal_created(signal)

    assert order == {
        "symbol": "BTCUSDT",
        "market": "BinanceFutures",
        "position_side": "Long",
        "leverage": 5,
        "entry_zone": ["18700", "18600", "18500"],
        "exit_targets": ["18800"],
        "stoploss": "18450",
    }


def test_parse_signal_close():
    signal = """ℹ️ #TRXUSDT Signal Closed

〽️ BinanceFutures With 3x Leverage

💰 Total of 1\\8 target hit
Profit  13.95%"""

    signal2 = "ℹ️ Update: Signal LTCUSDT Closed"

    parser = ParserSignal()
    result = parser.parser_signal_closed(signal)
    result2 = parser.parser_signal_closed(signal2)

    assert result == "TRXUSDT"
    assert result2 == "LTCUSDT"


def test_parse_signal_cancelled():
    signal = """ℹ️ #LINKUSDT Signal Cancelled

〽️ BinanceFutures With 5x Leverage"""

    parser = ParserSignal()
    result = parser.parser_signal_closed(signal)

    assert result == "LINKUSDT"


def test_parser_stoploss_updated():
    signal = """⚠️ #BNBUSDT Stoploss Updated

💰 Previous Stop Price - 29.13
💰 Updated Stop Price - 30.3

Please adjust your trade to match the change"""

    parser = ParserSignal()
    result = parser.parser_stoploss_updated(signal)

    assert result == {
        "symbol": "BNBUSDT",
        "previous_stop_price": "29.13",
        "updated_stop_price": "30.3",
    }
