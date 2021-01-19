import decimal
import math
from typing import Union
import urllib

from binance.client import Client

from .log import get_logger

logger = get_logger(__name__)


class Trading(object):
    def __init__(self, binance_client: Client):
        self.client = binance_client

        # load available symbols
        self.symbols = {}
        self.highest_precision = 8
        self.rate_limits = None
        self.loaded = False
        self.symbols_leverage = {}

    def load(self):
        infos = self.client.futures_exchange_info()

        original_symbol_infos = infos["symbols"]

        for symbol_infos in original_symbol_infos:
            symbol = symbol_infos.pop("symbol")
            precision = symbol_infos["baseAssetPrecision"]

            if precision > self.highest_precision:
                self.highest_precision = precision

            symbol_infos["filters"] = dict(
                map(lambda x: (x.pop("filterType"), x), symbol_infos["filters"])
            )
            self.symbols[symbol] = symbol_infos

        decimal.getcontext().prec = (
            self.highest_precision + 1
        )  # for operations and rounding

        try:
            self.client.futures_change_position_mode(dualSidePosition=True)
        except Exception as e:
            logger.info(e)

        # load rate limits
        self.rate_limits = infos["rateLimits"]
        self.loaded = True

    def create_order(
        self,
        symbol: str,
        side: str,
        order_type: str,
        quantity,
        price=None,
        stop_price=None,
        reduce_only=False,
        leverage=None,
        position_side=None,
    ) -> dict:
        params = {
            "symbol": symbol,
            "side": side,
            "type": order_type,
            "quantity": self.refine_amount(symbol, quantity),
        }

        if leverage is not None and (
            symbol not in self.symbols_leverage
            or self.symbols_leverage[symbol] != leverage
        ):
            self.client.futures_change_leverage(symbol=symbol, leverage=leverage)
            self.symbols_leverage[symbol] = leverage

        if price:
            params["price"] = self.refine_price(symbol, price)

        if stop_price:
            params["stopPrice"] = self.refine_price(symbol, stop_price)

        if reduce_only is not None:
            params["reduce_only"] = reduce_only

        if position_side is not None:
            params["positionSide"] = position_side

        if order_type == "LIMIT":
            params["timeInForce"] = Client.TIME_IN_FORCE_GTC

        order = self.client.futures_create_order(**params)

        return order

    def stop_market(self, symbol, stop_price):
        params = {
            "symbol": symbol,
            "closePosition": True,
            "type": "STOP_MARKET",
            "side": "SELL",
            "stopPrice": stop_price,
            "positionSide": "LONG",
        }

        return self.client.futures_create_order(**params)

    def create_multiple_orders(self, orders):
        pass

    def close_multiple_orders(self, symbol, orders):
        responses = []
        chunk_size = 10
        chunked_orders = [
            orders[i * chunk_size : (i + 1) * chunk_size]
            for i in range((len(orders) + chunk_size - 1) // chunk_size)
        ]

        for current_chunk in chunked_orders:
            serialize_to_string = "[{}]".format(",".join(map(str, current_chunk)))
            order_id_list_encoded = urllib.parse.urlencode(
                {"value": serialize_to_string}
            ).replace("value=", "")

            params = {
                "symbol": symbol,
                "orderIdList": order_id_list_encoded,
            }

            responses.append(self.client.futures_cancel_orders(**params))

        flatten_response = [item for sublist in responses for item in sublist]

        return flatten_response

    def balance(self, asset: str) -> float:
        balances = self.client.futures_account()

        for item in balances["positions"]:
            if item["asset"] == asset:
                return float(item["positionAmt"])

        return 0

    def refine_amount(self, symbol, amount: Union[str, decimal.Decimal], quote=False):
        if type(amount) == str or type(amount) == float:  # to save time for developers
            amount = decimal.Decimal(amount)

        if self.loaded:
            # precision = self.symbols[symbol]["baseAssetPrecision"]
            lot_size_filter = self.symbols[symbol]["filters"]["LOT_SIZE"]
            step_size = decimal.Decimal(lot_size_filter["stepSize"])

            digits = int(round(-math.log(decimal.Decimal(step_size), 10), 0))
            amount = decimal.Decimal(round(amount, digits))

            # logger.debug(_qta_end)

            # amount = (
            #     (
            #         f"%.{precision}f"
            #         % self.__truncate(
            #             amount if quote else (amount - amount % step_size), precision
            #         )
            #     )
            #     .rstrip("0")
            #     .rstrip(".")
            # )
            # logger.debug(amount)

        return amount

    def refine_price(self, symbol, price: Union[str, decimal.Decimal]):
        if type(price) == str or type(price) == float:  # to save time for developers
            price = decimal.Decimal(price)

        if self.loaded:
            precision = self.symbols[symbol]["baseAssetPrecision"]
            # percent_price_filter = self.symbols[symbol]["filters"]["PERCENT_PRICE"]
            price = (
                (f"%.{precision}f" % self.__truncate(price, precision))
                .rstrip("0")
                .rstrip(".")
            )

        return price

    @staticmethod
    def __truncate(f, n):
        return math.floor(f * 10 ** n) / 10 ** n
