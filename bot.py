#!/usr/bin/env python3
import re
from uuid import uuid4

import config

from telegram import Update, Bot, Chat, Message, User, InlineKeyboardMarkup, InlineQueryResultArticle, \
    InputTextMessageContent
from telegram.ext import Updater, Filters, RegexHandler, CommandHandler, TypeHandler, CallbackQueryHandler, \
    MessageHandler, ConversationHandler, InlineQueryHandler
from telegram.ext.dispatcher import run_async

from consts import item_filter_kb, stock_re, recipe_re, recipe_parts_re, tavern_hint_re
from helpers import ForwardedFrom, build_craft_kb, gen_craft_tree

from pony import orm
from models import User as dbUser, Recipe as dbRecipe, Item as dbItem

import logging

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=getattr(logging, config.LOGLEVEL))

logger = logging.getLogger("cw-crafts-bot")


def start(bot: Bot, update: Update) -> None:
    logger.debug("Entering: start")

    chat = update.effective_chat  # type: Chat
    msg = update.effective_message  # type: Message
    usr = update.effective_user  # type: User

    msg.reply_text('Welcome to Chat Wars Crafts Bot.\nCheck out /help for more information!')

    logger.debug("Exiting: start")
    return


def help(bot: Bot, update: Update) -> None:
    logger.debug("Entering: help")

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

    logger.debug("Exiting: help")
    return


def version(bot: Bot, update: Update) -> None:
    logger.debug("Entering: version")

    chat = update.effective_chat  # type: Chat
    msg = update.effective_message  # type: Message
    usr = update.effective_user  # type: User

    msg.reply_text(version_string(), parse_mode='HTML')

    logger.debug("Exiting: version")
    return


@run_async
def dbhandler(bot: Bot, update: Update) -> None:
    logger.debug("Entering: dbhandler")

    chat = update.effective_chat  # type: Chat
    msg = update.effective_message  # type: Message
    usr = update.effective_user  # type: User

    update_users = list()
    update_users.append(usr)

    if msg and msg.forward_from:
        update_users.append(msg.forward_from)
    if msg and msg.left_chat_member:
        update_users.append(msg.left_chat_member)
    if msg and msg.new_chat_members:
        update_users.extend(msg.new_chat_members)

    with orm.db_session:
        for u in update_users:
            logger.debug("create or update data for User: {} ({})".format(u.full_name, u.id))
            dbUser.update_or_create(u)

    logger.debug("Exiting: dbhandler")
    return


def craft(bot: Bot, update: Update) -> None:
    logger.debug("Entering: craft")

    chat = update.effective_chat  # type: Chat
    msg = update.effective_message  # type: Message
    usr = update.effective_user  # type: User

    kb_markup = InlineKeyboardMarkup(item_filter_kb)

    msg.reply_text('Which items would you like to view?', reply_markup=kb_markup)

    logger.debug("Exiting: craft")
    return


@orm.db_session
def craft_list(bot: Bot, update: Update, groups: tuple) -> None:
    logger.debug("Entering: craft_list with args %s", groups)

    chat = update.effective_chat  # type: Chat
    msg = update.effective_message  # type: Message
    usr = update.effective_user  # type: User

    update.callback_query.answer(text='Filtering...')

    kb_markup = InlineKeyboardMarkup(item_filter_kb)

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
        items_list += '<code>{:>3}</code> - {}'.format(item.id, item.name)
        items_list += ' (/craft_{})\n'.format(item.id) if item.complex else '\n'

    msg.edit_text(items_list, reply_markup=kb_markup, parse_mode='HTML')

    logger.debug("Exiting: craft_list")
    return


@orm.db_session
def craft_cb(bot: Bot, update: Update, groups: tuple) -> None:
    logger.debug("Entering: craft_cb with args %s", groups)

    chat = update.effective_chat  # type: Chat
    msg = update.effective_message  # type: Message
    usr = update.effective_user  # type: User

    if groups[0]:
        itemid = groups[0]
    else:
        help(bot, update)
        logger.debug("Exiting: craft_cb")
        return

    if itemid == "code":
        msg.reply_text("Replace code with an actual item code you silly goose! eg. /craft_24")
        logger.debug("Exiting: craft_cb")
        return

    logger.debug('craft_cb: fetching recipe for item with id: {}'.format(itemid))

    try:
        item = dbItem[itemid]
    except orm.core.ObjectNotFound:
        msg.reply_text("I'm sorry, but that item is not in the database.")
        logger.debug("Exiting: craft_cb")
        return

    kb_markup = None

    if item.complex:
        recipe_text = '<b>{name}</b>\n\n'.format(name=item.name)
        recipe_text += gen_craft_tree(item)
        kb_markup = build_craft_kb(item)
    else:
        recipe_text = "<b>{}</b> cannot be crafted.".format(item.name)

    if item.ingredient_in:
        recipe_text += '\n\n<b>Used in:</b>'
        for t in item.ingredient_in:
            recipe_text += '<code>\n\t{}</code>'.format(t.result_item.name)
            if t.result_item.complex:
                recipe_text += ' (/craft_{})'.format(t.result_item.id)

    msg.reply_text(recipe_text, reply_markup=kb_markup, parse_mode='HTML')

    logger.debug("Exiting: craft_cb")
    return


@orm.db_session
def process_stock(bot: Bot, update: Update) -> None:
    logger.debug("Entering: process_stock")

    chat = update.effective_chat  # type: Chat
    msg = update.effective_message  # type: Message
    usr = update.effective_user  # type: User

    matches = re.findall(stock_re, msg.text)

    if matches:
        for stock_item in matches:
            itemid, name, qty = stock_item
            logger.debug(f'updating item: {itemid} - {name} x {qty}')
            item = dbItem[itemid]
        msg.reply_text("Stock updated!")
    else:
        msg.reply_text("Send the /more command to @chtwrsbot and forward the stock result here.")

    logger.debug("Exiting: process_stock")
    return


def submit_recipe(bot: Bot, update: Update) -> int:
    logger.debug("Entering: submit_recipe")

    chat = update.effective_chat  # type: Chat
    msg = update.effective_message  # type: Message
    usr = update.effective_user  # type: User

    msg.reply_text("Please forward me the recipe from @chtwrsbot that you would like to submit.")

    logger.debug("Exiting: submit_recipe")
    return 0


def cancel_recipe(bot: Bot, update: Update) -> int:
    logger.debug("Entering: cancel_recipe")

    chat = update.effective_chat  # type: Chat
    msg = update.effective_message  # type: Message
    usr = update.effective_user  # type: User

    msg.reply_text("Recipe submission cancelled. Thank you for trying ^.^")

    logger.debug("Exiting: cancel_recipe")
    return ConversationHandler.END


def process_recipe(bot: Bot, update: Update) -> int:
    logger.debug("Entering: process_recipe")

    chat = update.effective_chat  # type: Chat
    msg = update.effective_message  # type: Message
    usr = update.effective_user  # type: User

    if re.match(recipe_re, msg.text):
        match = re.match(recipe_re, msg.text)
        matches = re.findall(recipe_parts_re, msg.text)
        if matches:
            logger.debug("process_recipe: processing recipe parts")
            with orm.db_session:
                r = dbItem.select(lambda i: i.name == match.group('name')).first()
                if r:
                    logger.debug("process_recipe: item %s found in db, continuing processing", r.name)
                    for part in matches:
                        name, qty = part
                        i = dbItem.select(lambda i: i.name == name).first()
                        logger.debug("process_recipe: adding %s x %s to item recipe", qty, name)
                        dbRecipe(result_item=r.id, ingredient_item=i.id, quantity_req=qty)
                    msg.reply_text("Thanks for submitting the recipe for <b>{}</b>!".format(r.name), parse_mode='HTML')
                else:
                    logger.debug("process_recipe: item not found")
                    msg.reply_text("That item is not in my database. Cancelling recipe submission.")
        return ConversationHandler.END
    elif re.search(tavern_hint_re, msg.text):
        match = re.search(tavern_hint_re, msg.text)
        with orm.db_session:
            r = dbItem.select(lambda i: i.name == match.group('name')).first()
            if r:
                i = dbItem.select(lambda i: i.name == match.group('item')).first()
                if i:
                    if dbRecipe.get(result_item=r.id, ingredient_item=i.id):
                        msg.reply_text("I already know about this part of the recipe. Cancelling recipe submission.")
                        return ConversationHandler.END
                    dbRecipe(result_item=r.id, ingredient_item=i.id, quantity_req=match.group('qty'))
                    msg.reply_text("Thanks for submitting a part for the recipe of <b>{}</b>!".format(r.name),
                                   parse_mode='HTML')
                else:
                    msg.reply_text("{} is not in my database. Cancelling recipe submission.".format(match.group('item')))
            else:
                msg.reply_text("{} is not in my database. Cancelling recipe submission.".format(match.group('name')))
        return ConversationHandler.END
    msg.reply_text("That is not a valid recipe or I fucked up my regex. Please forward it again or /cancel to cancel.")

    logger.debug("Exiting: process_recipe")
    return 0


def item_search(bot: Bot, update: Update, args: list=None) -> None:
    logger.debug("Entering: item_search with args %s", args)

    chat = update.effective_chat  # type: Chat
    msg = update.effective_message  # type: Message
    usr = update.effective_user  # type: User

    if args:
        search_text = ' '.join(args)
        keywords = args
    else:
        search_text = msg.text
        keywords = search_text.split()

    result_text = str()

    with orm.db_session:
        items = dbItem.select(lambda i: i)
        for keyword in keywords:
            items = items.filter(lambda i: keyword.lower() in i.name.lower())

        if len(items) > 1:
            result_text = f'Search results for <b>{search_text}</b>\n'

            for item in items:
                result_text += '<code>{:>3}</code> - {}'.format(item.id, item.name)
                result_text += ' (/craft_{})\n'.format(item.id) if item.complex else ' (/i_{})\n'.format(item.id)
        elif len(items) == 1:
            for item in items:
                return craft_cb(bot, update, (item.id, ))
        else:
            result_text = f'No items matched your search for <b>{search_text}</b>'

    msg.reply_text(result_text, parse_mode='HTML')

    logger.debug("Exiting: item_search")
    return


def craft_inline(bot: Bot, update: Update, groups: tuple) -> None:
    logger.debug("Entering: craft_inline with args %s", groups)

    chat = update.effective_chat  # type: Chat
    msg = update.effective_message  # type: Message
    usr = update.effective_user  # type: User

    if groups:
        item_id, qty = groups
    else:
        logger.debug("Exiting: craft_inline")
        return

    with orm.db_session:
        item_name = dbItem[item_id].name

    results = [
        InlineQueryResultArticle(
            id=uuid4(),
            title=item_name,
            input_message_content=InputTextMessageContent(f'/a_{item_id} {qty}')
        )]

    update.inline_query.answer(results)

    logger.debug("Exiting: craft_inline")
    return


if __name__ == '__main__':
    ud = Updater(config.TOKEN)
    dp = ud.dispatcher

    dp.add_handler(TypeHandler(Update, dbhandler), group=-1)

    dp.add_handler(CommandHandler('start', start))
    dp.add_handler(CommandHandler('help', help))
    dp.add_handler(CommandHandler(['craft', 'items'], craft))

    dp.add_handler(ConversationHandler(entry_points=[CommandHandler('submit', submit_recipe)],
                                       states={
                                           0: [MessageHandler(ForwardedFrom(user_id=408101137), process_recipe)]
                                       },
                                       fallbacks=[CommandHandler('cancel', cancel_recipe)]
                                       )
                   )

    dp.add_handler(MessageHandler(ForwardedFrom(user_id=408101137), process_stock))
    dp.add_handler(CommandHandler(['search', 's', 'find'], item_search, pass_args=True))
    dp.add_handler(MessageHandler(Filters.text, item_search))
    dp.add_handler(CallbackQueryHandler(craft_list, pattern=r'^list\|(.*)', pass_groups=True))
    dp.add_handler(RegexHandler(r'^/(?:craft|i)_(.*)$', craft_cb, pass_groups=True))

    dp.add_handler(InlineQueryHandler(craft_inline, pattern=r'(\w{2,3})-(\d{1,3})', pass_groups=True))

    if config.APP_ENV.startswith('PROD'):
        ud.start_webhook(listen='0.0.0.0', port=config.WEBHOOK_PORT, url_path=config.TOKEN)
        ud.bot.set_webhook(url='https://{}/{}'.format(config.WEBHOOK_URL, config.TOKEN))
    else:
        ud.start_polling(clean=True)
    ud.idle()

