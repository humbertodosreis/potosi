class OrderUpdateEvent:
    def __init__(self):
        self.event_type = ""
        self.event_time = 0
        self.transaction_time = 0
        self.symbol = ""
        self.client_order_id = ""
        self.side = None
        self.type = None
        self.time_in_force = None
        self.orig_qty = 0.0
        self.price = 0.0
        self.avg_price = 0.0
        self.stop_price = 0.0
        self.execution_type = ""
        self.order_status = ""
        self.order_id = None
        self.last_filled_qty = 0.0
        self.cumulative_filled_qty = 0.0
        self.last_filled_price = 0.0
        self.commission_asset = None
        self.commission_amount = 0
        self.order_trade_time = 0
        self.trade_id = None
        self.bids_notional = 0.0
        self.asks_notional = 0.0
        self.is_marker_side = None
        self.is_reduce_only = None
        self.working_type = 0.0
        self.is_close_position = None
        self.activation_price = 0.0
        self.callback_rate = 0.0
        self.position_side = None

    @staticmethod
    def json_parse(json_data: dict):
        result = OrderUpdateEvent()
        result.event_type = json_data["e"]
        result.event_time = int(json_data["E"])
        result.transaction_time = int(json_data["T"])

        data_group = json_data["o"]
        result.symbol = data_group["s"]
        result.client_order_id = data_group["c"]
        result.side = data_group["S"]
        result.type = data_group["o"]
        result.time_in_force = data_group["f"]
        result.orig_qty = float(data_group["q"])
        result.price = float(data_group["p"])
        result.avg_price = float(data_group["ap"])
        result.stop_price = float(data_group["sp"])
        result.execution_type = data_group["x"]
        result.order_status = data_group["X"]
        result.order_id = int(data_group["i"])
        result.last_filled_qty = float(data_group["l"])
        result.cumulative_filled_qty = float(data_group["z"])
        result.last_filled_price = float(data_group["L"])

        result.commission_asset = None if "N" not in data_group else data_group["N"]
        result.commission_amount = (
            None if "n" not in data_group else float(data_group["n"])
        )
        result.order_trade_time = (
            None if "T" not in data_group else int(data_group["T"])
        )
        result.trade_id = None if "t" not in data_group else int(data_group["t"])
        result.bids_notional = float(data_group["b"])
        result.asks_notional = float(data_group["a"])
        result.is_marker_side = bool(data_group["m"])
        result.is_reduce_only = bool(data_group["R"])
        result.working_type = data_group["wt"]
        result.is_close_position = bool(data_group["cp"])
        result.activation_price = None if "AP" not in data_group else data_group["AP"]
        result.callback_rate = None if "cr" not in data_group else data_group["cr"]
        result.position_side = data_group["ps"]

        return result
