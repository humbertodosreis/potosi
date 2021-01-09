#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from os import path
import re

from binance.client import Client as BinanceClient
from telethon import events, TelegramClient

from potosi.config import settings
from potosi.db import database
from potosi.log import get_logger
from potosi.parser_signal import ParserSignal
from potosi.services import TradeService
from potosi.trading import Trading

logger = get_logger(__name__)

# Remember to use your own values from my.telegram.org!
client = TelegramClient(
    path.abspath(path.join(settings.ROOT_PATH, "data", "anon")),
    int(settings.TELEGRAM_API_ID),
    settings.TELEGRAM_API_HASH,
)

# user_input_channel = 'wcsebot'
USER_INPUT_CHANNEL = "me"

# binance client
binance_client = BinanceClient(settings.BINANCE_API_KEY, settings.BINANCE_API_SECRET)
binance_client.FUTURES_URL = "https://testnet.binancefuture.com/fapi"
binance_client.API_URL = "https://testnet.binance.vision/api"

trade = Trading(binance_client=binance_client)
trade.load()

parser = ParserSignal()
parser.download_codes()

trade_service = TradeService(trading=trade, parser=parser)


def is_signal_created(msg: str) -> bool:
    return "Update New Signal Created" in msg


def is_signal_closed(msg: str) -> bool:
    return "Signal Closed" in msg or re.search("Update: Signal ([A-Z0-9]+) Closed", msg)


def is_stoploss_updated(msg: str) -> bool:
    return "Stoploss Updated" in msg


@client.on(events.NewMessage(chats=USER_INPUT_CHANNEL, pattern=is_signal_created))
async def message_created_trade(event):
    logger.info("new signal received")

    trade_service.create(event.message.message)

    logger.info("trade created")


@client.on(events.NewMessage(chats=USER_INPUT_CHANNEL, pattern=is_stoploss_updated))
async def message_stoploss(event):
    logger.info("Stoploss Updated")

    # obtem o saldo da conta
    # multiplica o valor por alancagem
    # divide o valor pelo numero de entradas (70-30)
    # calcula a quantidade de compra para cada entrada
    # Cria uma ordem stoploss com o valor total
    # Cria as ordens de entrada

    # procurar a ultima orderm aberta para o par
    # atualizar o stoploss
    # enviar notificação para o telegram


@client.on(events.NewMessage(chats=USER_INPUT_CHANNEL, pattern=is_signal_closed))
async def message_signal_close(event):
    logger.info("Signal Closed")
    trade_service.close(raw_signal=event.message.message)


if __name__ == "__main__":
    with database:
        with client:
            logger.info("Start listener")
            client.run_until_disconnected()
