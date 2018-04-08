#!/usr/bin/env python3
import re

import config

from telegram import Update, Bot, Chat, Message, User, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Updater, RegexHandler, CommandHandler, TypeHandler, CallbackQueryHandler, MessageHandler, \
    ConversationHandler
from telegram.ext.dispatcher import run_async

from helpers import ForwardedFrom, stock_re, recipe_re, recipe_parts_re

from pony import orm
from models import User as dbUser, Recipe as dbRecipe, Item as dbItem

import logging

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=getattr(logging, config.LOGLEVEL))

logger = logging.getLogger(__name__)


def start(bot: Bot, update: Update) -> None:
    chat = update.effective_chat  # type: Chat
    msg = update.effective_message  # type: Message
    usr = update.effective_user  # type: User

    msg.reply_text('Welcome to Chat Wars Crafts Bot.\nCheck out /help for more information!')


def help(bot: Bot, update: Update) -> None:
    chat = update.effective_chat  # type: Chat
    msg = update.effective_message  # type: Message
    usr = update.effective_user  # type: User

    msg.reply_text("This bot was created to help you with your <a href='http://t.me/chtwrsbot'>Chat Wars</a> "
                   "crafting needs.\n\n"
                   "To get started, please forward your /more from @chtwrsbot to me.\nYou may also view all available "
                   "craftable items with the /craft command.\nTo view the crafting recipe for a specific item you may "
                   "use the /craft_code command, where <code>code</code> is the item code of the item to craft.\n\n"
                   "To add a recipe to the database, you may use the /submit command.",
                   parse_mode='HTML',
                   disable_web_page_preview=True)


@run_async
def dbhandler(bot: Bot, update: Update) -> None:
    chat = update.effective_chat  # type: Chat
    msg = update.effective_message  # type: Message
    usr = update.effective_user  # type: User
    logger.debug("create or update data for User: {} ({})".format(usr.full_name, usr.id))
    with orm.db_session:
        dbUser.update_or_create(usr)


def craft(bot: Bot, update: Update) -> None:
    chat = update.effective_chat  # type: Chat
    msg = update.effective_message  # type: Message
    usr = update.effective_user  # type: User

    kb = [[InlineKeyboardButton('All', callback_data='list|all')],
          [InlineKeyboardButton('Basic', callback_data='list|basic'),
           InlineKeyboardButton('Crafted', callback_data='list|complex')],
          [InlineKeyboardButton('Weapons', callback_data='list|weapon'),
           InlineKeyboardButton('Armors', callback_data='list|armour')],
          [InlineKeyboardButton('Recipes', callback_data='list|recipe'),
           InlineKeyboardButton('Fragments', callback_data='list|fragment')]]

    kb_markup = InlineKeyboardMarkup(kb)

    msg.reply_text('Which items would you like to view?', reply_markup=kb_markup)


@orm.db_session
def craft_list(bot: Bot, update: Update, groups: tuple) -> None:
    chat = update.effective_chat  # type: Chat
    msg = update.effective_message  # type: Message
    usr = update.effective_user  # type: User

    update.callback_query.answer(text='Filtering...')

    kb = [[InlineKeyboardButton('All', callback_data='list|all')],
          [InlineKeyboardButton('Basic', callback_data='list|basic'),
           InlineKeyboardButton('Crafted', callback_data='list|complex')],
          [InlineKeyboardButton('Weapons', callback_data='list|weapon'),
           InlineKeyboardButton('Armors', callback_data='list|armour')],
          [InlineKeyboardButton('Recipes', callback_data='list|recipe'),
           InlineKeyboardButton('Fragments', callback_data='list|fragment')]]

    kb_markup = InlineKeyboardMarkup(kb)

    item_filter = groups[0]

    if item_filter == 'all':
        items = dbItem.select(lambda i: i)
    elif item_filter == 'basic':
        items = dbItem.select(lambda i: not i.complex)
    elif item_filter == 'complex':
        items = dbItem.select(lambda i: i.complex)
    elif item_filter == 'armour':
        items = dbItem.select(lambda i: i.id.startswith('a'))
    elif item_filter == 'weapon':
        items = dbItem.select(lambda i: i.id.startswith('w'))
    elif item_filter == 'recipe':
        items = dbItem.select(lambda i: i.id.startswith('r'))
    elif item_filter == 'fragment':
        items = dbItem.select(lambda i: i.id.startswith('k'))
    else:
        items = list()

    items_list = '<b>{} items</b>\n'.format(item_filter.title())

    for item in items:
        items_list += '{} - {}'.format(item.id, item.name)
        items_list += ' (/craft_{})\n'.format(item.id) if item.complex else '\n'

    msg.edit_text(items_list, reply_markup=kb_markup, parse_mode='HTML')


@orm.db_session
def craft_cb(bot: Bot, update: Update, groups: tuple) -> None:
    chat = update.effective_chat  # type: Chat
    msg = update.effective_message  # type: Message
    usr = update.effective_user  # type: User

    if groups[0]:
        itemid = groups[0]
    else:
        help(bot, update)
        return

    if itemid == "code":
        msg.reply_text("Replace code with an actual item code you silly goose! eg. /craft_24")
        return

    logger.debug('fetching recipe for item with id: {}'.format(itemid))

    try:
        item = dbItem[itemid]
    except orm.core.ObjectNotFound:
        msg.reply_text("I'm sorry, but that item is not in the database.")
        return

    if item.complex:
        recipe_text = '<b>{name}</b>'.format(name=item.name)
        for ingr in item.result_of:
            recipe_text += '<code>\n\t{:>3} x {}</code>'.format(ingr.quantity_req, ingr.ingredient_item.name)
            if ingr.ingredient_item.complex:
                recipe_text += ' (/craft_{})'.format(ingr.ingredient_item.id)

    else:
        recipe_text = "<b>{}</b> cannot be crafted.".format(item.name)

    if item.ingredient_in:
        recipe_text += '\n\n<b>Used in:</b>'
        for t in item.ingredient_in:
            recipe_text += '<code>\n\t{}</code>'.format(t.result_item.name)
            if t.result_item.complex:
                recipe_text += ' (/craft_{})'.format(t.result_item.id)

    msg.reply_text(recipe_text, parse_mode='HTML')


@orm.db_session
def process_stock(bot: Bot, update: Update) -> None:
    chat = update.effective_chat  # type: Chat
    msg = update.effective_message  # type: Message
    usr = update.effective_user  # type: User

    matches = re.findall(stock_re, msg.text)

    if matches:
        for stock in matches:
            id, name, qty = stock
            item = dbItem[id]
        msg.reply_text("Stock updated!")
    else:
        msg.reply_text("Send the /more command to @chtwrsbot and forward the stock result here.")
        return


def submit_recipe(bot: Bot, update: Update) -> int:
    chat = update.effective_chat  # type: Chat
    msg = update.effective_message  # type: Message
    usr = update.effective_user  # type: User

    msg.reply_text("Please forward me the recipe from @chtwrsbot that you would like to submit.")

    return 0


def cancel_recipe(bot: Bot, update: Update) -> int:
    chat = update.effective_chat  # type: Chat
    msg = update.effective_message  # type: Message
    usr = update.effective_user  # type: User

    msg.reply_text("Recipe submission cancelled. Thank you for trying ^.^")

    return ConversationHandler.END


def process_recipe(bot: Bot, update: Update) -> int:
    chat = update.effective_chat  # type: Chat
    msg = update.effective_message  # type: Message
    usr = update.effective_user  # type: User

    match = re.match(recipe_re, msg.text)

    if match:
        matches = re.findall(recipe_parts_re, msg.text)
        if matches:
            with orm.db_session:
                r = dbItem.select(lambda i: i.name == match.group('name')).first()
                if r:
                    for part in matches:
                        name, qty = part
                        i = dbItem.select(lambda i: i.name == name).first()
                        dbRecipe(result_item=r.id, ingredient_item=i.id, quantity_req=qty)
                    msg.reply_text("Thanks for submitting the recipe for <b>{}</b>!".format(r.name), parse_mode='HTML')
                else:
                    msg.reply_text("That item is not in my database. Cancelling recipe submission.")

            return ConversationHandler.END

    msg.reply_text("That is not a valid recipe or I fucked up my regex. Please forward it again or /cancel to cancel.")
    return 0


if __name__ == '__main__':
    ud = Updater(config.TOKEN)
    dp = ud.dispatcher

    dp.add_handler(TypeHandler(Update, dbhandler), group=-1)

    dp.add_handler(CommandHandler('start', start))
    dp.add_handler(CommandHandler('help', help))
    dp.add_handler(CommandHandler('craft', craft))

    dp.add_handler(ConversationHandler(entry_points=[CommandHandler('submit', submit_recipe)],
                                       states={
                                           0: [MessageHandler(ForwardedFrom(user_id=408101137), process_recipe)]
                                       },
                                       fallbacks=[CommandHandler('cancel', cancel_recipe)]
                                       )
                   )

    dp.add_handler(MessageHandler(ForwardedFrom(user_id=408101137), process_stock))
    dp.add_handler(CallbackQueryHandler(craft_list, pattern=r'^list\|(.*)', pass_groups=True))
    dp.add_handler(RegexHandler(r'^/craft_(.*)', craft_cb, pass_groups=True))

    if config.APP_ENV == 'PROD':
        ud.start_webhook(listen='0.0.0.0', port=config.WEBHOOK_PORT, url_path=config.TOKEN)
        ud.bot.set_webhook(url='https://{}/{}'.format(config.WEBHOOK_URL, config.TOKEN))
    else:
        ud.start_polling(clean=True)
    ud.idle()
