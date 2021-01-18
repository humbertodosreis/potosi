import datetime
from enum import IntEnum, unique

from peewee import (
    BigIntegerField,
    BooleanField,
    CharField,
    DateTimeField,
    DecimalField,
    ForeignKeyField,
    SmallIntegerField,
    TextField,
)

from .db import BaseModel


@unique
class OrderPlaceType(IntEnum):
    ENTRY = 0
    EXIT = 1


class Trade(BaseModel):
    symbol = CharField(max_length=10)
    raw_signal = TextField()
    created_date = DateTimeField(default=datetime.datetime.now)
    is_opened = BooleanField(default=True)


class Order(BaseModel):
    order_id = BigIntegerField()
    client_order_id = CharField(max_length=22)
    symbol = CharField(max_length=10)
    type = CharField()
    status = CharField()
    amount = DecimalField(max_digits=14, decimal_places=8, default=0.0)
    place_type = SmallIntegerField(default=OrderPlaceType.ENTRY)
    target = SmallIntegerField(default=0)
    price = DecimalField(max_digits=14, decimal_places=8, default=0.0)
    created_date = DateTimeField(default=datetime.datetime.now)
    trade = ForeignKeyField(Trade, backref="orders", on_delete="CASCADE")

    def is_entry_order(self) -> bool:
        return self.place_type == OrderPlaceType.ENTRY

    def is_exit_order(self) -> bool:
        return self.place_type == OrderPlaceType.EXIT

    def is_first_target(self) -> bool:
        return self.target == 1

    def is_nth_target(self, nth) -> bool:
        return self.target == nth
