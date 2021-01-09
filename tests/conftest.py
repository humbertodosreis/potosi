import secrets
import uuid

from peewee import SqliteDatabase
import pytest
from pytest_mock import MockerFixture

from potosi.models import Order, Trade
from potosi.parser_signal import ParserSignal

MODELS = [Trade, Order]
secrets_generator = secrets.SystemRandom()


@pytest.fixture
def database():
    db = SqliteDatabase(":memory:", autoconnect=True)
    db.bind(MODELS, bind_refs=False, bind_backrefs=False)

    db.connect()
    db.create_tables(MODELS)

    yield db

    db.drop_tables(MODELS)
    db.close()


@pytest.fixture
def parser_signal():
    parser = ParserSignal()
    parser.download_codes()

    return parser


@pytest.fixture
def mock_trading(mocker: MockerFixture):
    def return_data(*args, **kwargs):
        return {
            "orderId": secrets_generator.randint(100, 999_999),
            "clientOrderId": uuid.uuid4().hex,
            "symbol": kwargs["symbol"],
            "type": kwargs["order_type"],
            "status": "NEW",
            "origQty": kwargs["quantity"],
        }

    mock_trading = mocker.MagicMock(name="trading")
    mock_trading.create_order.side_effect = return_data

    return mocker.patch("potosi.trading.Trading", new=mock_trading)


# @pytest.fixture()
# def trade_service(mock_trading):
#     parser = ParserSignal()
#     parser.download_codes()
#
#     return TradeService(trading=mock_trading, parser=parser)
