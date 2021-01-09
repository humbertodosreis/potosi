import re

import demoji


class ParserSignal(object):
    def __init__(self):
        self.__is_downloaded_codes = False

    @staticmethod
    def __extract_price(value: str, char: str) -> str:
        index = value.find(char)
        return value[:index].strip()

    def download_codes(self):
        if self.__is_downloaded_codes is False:
            demoji.download_codes()
            self.__is_downloaded_codes = True

    def parser_signal_created(self, signal_text: str) -> dict:
        """
        Given a text with some signal, returns either dict.
        """
        # self.__download_codes()

        lines = demoji.replace(signal_text, "").splitlines()

        last_index = 0
        chunks = []
        for i, v in enumerate(lines):
            if not v.strip() or len(lines) - 1 == i:
                chunks.append(lines[last_index:i])
                last_index = i + 1

        chunks = filter(lambda x: len(x) > 0, chunks)

        signal = {
            "market": None,
            "symbol": None,
            "position_side": None,
            "leverage": None,
            "entry_zone": [],
            "exit_targets": [],
            "stoploss": None,
        }

        for value in chunks:
            if "Entry Zone" in value[0]:
                signal["entry_zone"] = list(map(lambda x: x.strip(), value[1:]))
            elif "Exit Targets" in value[0]:
                signal["exit_targets"] = list(
                    map(lambda x: self.__extract_price(x, "/"), value[1:])
                )
            elif "StopLoss" in value[0]:
                signal["stoploss"] = self.__extract_price(value[1], "/")
            elif "Update New Signal Created" in value[0]:
                index = value[1].find("#")

                signal["symbol"] = value[1][index + 1 :]

                match = re.search(
                    r"(Binance|BinanceFutures) \((Long|Short) X(\d+)\)",
                    value[2].strip(),
                )
                signal["market"] = match.group(1)
                signal["position_side"] = match.group(2)
                signal["leverage"] = int(match.group(3))

        return signal

    def parser_signal_closed(self, signal_text: str) -> str:
        # self.__download_codes()

        signal_text = demoji.replace(signal_text, "")
        match = re.search(r"#([A-Z0-9]+) Signal Closed", signal_text)

        if not match:
            match = re.search("Update: Signal ([A-Z0-9]+) Closed", signal_text)

        return match.group(1)

    def parser_stoploss_updated(self, signal_text: str) -> dict:
        # self.__download_codes()

        line_symbol, _, line_previous, line_updated, _, _ = demoji.replace(
            signal_text, ""
        ).splitlines()

        match = re.search(r"#([A-Z0-9]+) Stoploss Updated", line_symbol)
        symbol = match.group(1)

        index = line_previous.find("-")
        previous_stop_price = line_previous[index + 1 :].strip()

        index = line_updated.find("-")
        updated_stop_price = line_updated[index + 1 :].strip()

        return {
            "symbol": symbol,
            "previous_stop_price": previous_stop_price,
            "updated_stop_price": updated_stop_price,
        }
