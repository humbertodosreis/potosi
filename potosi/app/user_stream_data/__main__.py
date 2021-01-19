#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import threading
import time

from binance.client import Client as BinanceClient
from unicorn_binance_websocket_api.unicorn_binance_websocket_api_manager import (
    BinanceWebSocketApiManager,
)

from potosi.config import settings
from potosi.dataclasses import OrderUpdateEvent
from potosi.log import get_logger
from potosi.parser_signal import ParserSignal
from potosi.services import TradeService
from potosi.trading import Trading

logger = get_logger(__name__)

WEBSOCKET_EXCHANGE = "binance.com-futures-testnet"

# binance client
binance_client = BinanceClient(settings.BINANCE_API_KEY, settings.BINANCE_API_SECRET)
binance_client.FUTURES_URL = "https://testnet.binancefuture.com/fapi"
binance_client.API_URL = "https://testnet.binance.vision/api"

trade = Trading(binance_client=binance_client)
trade.load()

parser = ParserSignal()

trade_service = TradeService(trading=trade, parser=parser)


def print_stream_data_from_stream_buffer(binance_websocket_api_manager):
    while True:
        if binance_websocket_api_manager.is_manager_stopping():
            exit(0)

        oldest_stream_data_from_stream_buffer = (
            binance_websocket_api_manager.pop_stream_data_from_stream_buffer()
        )

        if oldest_stream_data_from_stream_buffer is False:
            time.sleep(0.01)
        else:
            logger.info(oldest_stream_data_from_stream_buffer)
            stream = json.loads(oldest_stream_data_from_stream_buffer)

            if stream["e"] == "ORDER_TRADE_UPDATE":
                try:
                    logger.info("Order update received")
                    event = OrderUpdateEvent.json_parse(stream)
                    trade_service.update(order_event=event)
                except Exception as e:
                    logger.exception(e)


# monitor the streams
if __name__ == "__main__":
    logger.info("starting...")

    # create instances of BinanceWebSocketApiManager
    ubwa_com = BinanceWebSocketApiManager(exchange=WEBSOCKET_EXCHANGE)

    # create the userData streams
    user_stream_id = ubwa_com.create_stream(
        "arr",
        "!userData",
        api_key=settings.BINANCE_API_KEY,
        api_secret=settings.BINANCE_API_SECRET,
    )

    # start a worker process to move the received stream_data
    # from the stream_buffer to a print function
    worker_thread = threading.Thread(
        target=print_stream_data_from_stream_buffer, args=(ubwa_com,)
    )
    worker_thread.start()

    try:
        while True:
            # ubwa_com.print_stream_info(user_stream_id)
            time.sleep(1)
            # os.system("clear")
    except KeyboardInterrupt:
        logger.info("Stopping ... just wait a few seconds!")
        ubwa_com.stop_manager_with_all_streams()
