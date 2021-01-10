import decimal
import math
from typing import Union
import urllib

from binance.client import Client


class Trading(object):
    def __init__(self, binance_client: Client):
        self.client = binance_client

        # load available symbols
        self.symbols = {}
        self.highest_precision = 8
        self.rate_limits = None
        self.loaded = False

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
    ) -> dict:
        params = {
            "symbol": symbol,
            "side": side,
            "type": order_type,
            "timeInForce": Client.TIME_IN_FORCE_GTC,
            "quantity": self.refine_amount(symbol, quantity),
            "reducyOnly": reduce_only,
        }

        if leverage is not None:
            self.client.futures_change_leverage(symbol=symbol, leverage=leverage)

        if price:
            params["price"] = self.refine_price(symbol, price)

        if stop_price:
            params["stopPrice"] = self.refine_price(symbol, stop_price)

        order = self.client.futures_create_order(**params)

        return order

    def create_multiple_orders(self, orders):
        # chunk_size = 5
        # chunked_orders = [
        #     orders[i * chunk_size : (i + 1) * chunk_size]
        #     for i in range((len(orders) + chunk_size - 1) // chunk_size)
        # ]

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
            precision = self.symbols[symbol]["baseAssetPrecision"]
            lot_size_filter = self.symbols[symbol]["filters"]["LOT_SIZE"]
            step_size = decimal.Decimal(lot_size_filter["stepSize"])
            amount = (
                (
                    f"%.{precision}f"
                    % self.__truncate(
                        amount if quote else (amount - amount % step_size), precision
                    )
                )
                .rstrip("0")
                .rstrip(".")
            )
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
