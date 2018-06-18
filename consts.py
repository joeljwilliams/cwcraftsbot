#!/usr/bin/env python3

import re
from telegram import InlineKeyboardButton, InlineKeyboardMarkup


stock_re = re.compile(r"^/a_(?P<id>\w+)\s(?P<name>[\w\s]+)\sx\s(?P<qty>\d+)$", re.MULTILINE)
recipe_re = re.compile(r"^📃(?P<name>[\w ]+) \(recipe\):$", re.MULTILINE)
recipe_parts_re = re.compile(r"^(?P<name>[\w\. ]+) x (?P<qty>\d+)$", re.MULTILINE)

item_filter_kb = [[InlineKeyboardButton('All', callback_data='list|all')],
                   [InlineKeyboardButton('Basic', callback_data='list|basic'),
                    InlineKeyboardButton('Crafted', callback_data='list|complex')],
                   [InlineKeyboardButton('Fragments', callback_data='list|fragment'),
                    InlineKeyboardButton('Armors', callback_data='list|armour')],
                   [InlineKeyboardButton('Recipes', callback_data='list|recipe'),
                    InlineKeyboardButton('Weapons', callback_data='list|weapon')]]

