#!/usr/bin/env python3

from collections import deque, defaultdict

from telegram.ext import BaseFilter
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from models import Item, Recipe


class ForwardedFrom(BaseFilter):
    def __init__(self, user_id):
        if isinstance(user_id, int):
            self.valid_ids = [user_id]
        elif isinstance(user_id, list):
            self.valid_ids = user_id
        else:
            raise ValueError("Accepts int or list as argument")

    def filter(self, message):
        if message.forward_from:
            fwd_usr = message.forward_from
            return fwd_usr.id in self.valid_ids
        return False


def gen_craft_tree(item: Item) -> str:
    output_list = str()
    shopping_list = defaultdict(int)
    mystack = deque()
    for i in item.result_of.order_by(lambda i: i.ingredient_item.id):
        mystack.appendleft((i, 0, i.quantity_req))
    while mystack:
        t, l, qty = mystack.popleft()
        t = t.ingredient_item
        if t.complex:
            for i in t.result_of.order_by(lambda i: i.id):
                mystack.appendleft((i, l+1, qty*i.quantity_req))
        else:
            shopping_list[t.name] += qty
        output_list += '<code>{}{} x {}</code>\n'.format('  '*l, qty, t.name)
#        pprint(shopping_list)
    return output_list


def build_craft_kb(item: Item) -> InlineKeyboardMarkup:
    keyboard = []
    for ingr in item.result_of:
        qty = ingr.quantity_req
        ingr = ingr.ingredient_item
        keyboard.append([InlineKeyboardButton(text=f'{ingr.name}', switch_inline_query=f'{ingr.id}-{qty}')])
    return InlineKeyboardMarkup(keyboard)
