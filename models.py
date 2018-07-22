#!/usr/bin/env python3

from pony import orm
from mixins import TgMixin

import config

db = orm.Database()


class User(db.Entity, TgMixin):
    id = orm.PrimaryKey(int)
    first_name = orm.Required(str)
    is_bot = orm.Required(bool)
    last_name = orm.Optional(str)
    username = orm.Optional(str)
    language_code = orm.Optional(str)


class Item(db.Entity):
    id = orm.PrimaryKey(str)
    name = orm.Required(str)
    complex = orm.Required(bool, default=False)
    result_of = orm.Set("Recipe", reverse='result_item')
    ingredient_in = orm.Set("Recipe", reverse='ingredient_item')


class Recipe(db.Entity):
    result_item = orm.Required(Item, reverse='result_of')
    ingredient_item = orm.Required(Item, reverse='ingredient_in')
    quantity_req = orm.Required(int)
    orm.composite_key(result_item, ingredient_item)


if not config.APP_ENV.startswith('PROD'):
    orm.set_sql_debug(True)

db.bind(**config.DB_PARAMS)
db.generate_mapping(create_tables=True)


def dataload():
    import json
    with open('data.json', 'r') as fp:
        data = json.load(fp)

    for item in data["items"]:
        with orm.db_session:
            try:
                Item[item["id"]]
            except orm.core.ObjectNotFound:
                    Item(**item)

    for recipe in data["recipes"]:
        with orm.db_session:
            item = Item[recipe["id"]]
            for i in recipe["ingredients"]:
                qty = i[0]
                ingr = Item[i[1]]
                try:
                    Recipe(result_item=item, ingredient_item=ingr, quantity_req=qty)
                except orm.core.TransactionIntegrityError:
                    continue
