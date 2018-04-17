#!/usr/bin/env python3

from telegram.ext import BaseFilter
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from models import Item

import pip
import os
import subprocess

class ForwardedFrom(BaseFilter):
    def __init__(self, user_id):
        self.user_id = user_id

    def filter(self, message):
        if message.forward_from:
            fwd_usr = message.forward_from
            return fwd_usr.id == self.user_id
        return False


def version_string():
    ver_str = '<b>Version Info:</b>\n'
    app_ver = os.getenv('OPENSHIFT_BUILD_COMMIT',
                        str(subprocess.check_output(['git', 'rev-parse', 'HEAD']), 'utf-8'))[:7]
    ver_str += '<code>commit-{}</code>\n'.format(app_ver)
    ver_str += '\n<b>Package Versions:</b>\n'
    for pkg in pip.get_installed_distributions(skip=('wheel', 'pip', 'setuptools')):
        ver_str += '<code>{}</code>\n'.format(pkg)

    return ver_str


def build_craft_kb(item: Item) -> InlineKeyboardMarkup:
    keyboard = []
    for ingr in item.result_of:
        qty = ingr.quantity_req
        ingr = ingr.ingredient_item
        keyboard.append([InlineKeyboardButton(text=f'{ingr.name}', switch_inline_query=f'{ingr.id}-{qty}')])
    return InlineKeyboardMarkup(keyboard)
