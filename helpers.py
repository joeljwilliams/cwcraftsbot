#!/usr/bin/env python3

from telegram.ext import BaseFilter
import re

stock_re = re.compile(r"^/a_(?P<id>\w+)\s(?P<name>[\w\s]+)\sx\s(?P<qty>\d+)$", re.MULTILINE)
recipe_re = re.compile(r"^📃(?P<name>[\w ]+) \(recipe\):$", re.MULTILINE)
recipe_parts_re = re.compile(r"^(?P<name>[\w\. ]+) x (?P<qty>\d+)$", re.MULTILINE)
tavern_hint_re = re.compile(r"recipe of (?P<name>[\w ]+) saying that you need (?P<qty>\d+) (?P<item>[\w ]+)\.")


class ForwardedFrom(BaseFilter):
    def __init__(self, user_id):
        self.user_id = user_id

    def filter(self, message):
        if message.forward_from:
            fwd_usr = message.forward_from
            return fwd_usr.id == self.user_id
        return False
