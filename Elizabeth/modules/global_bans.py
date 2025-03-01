import html
from io import BytesIO

from requests import get
from telegram import ChatAction, ParseMode
from telegram.error import BadRequest, TelegramError
from telegram.ext import CommandHandler, Filters, MessageHandler, run_async
from telegram.utils.helpers import mention_html

import Elizabeth.modules.sql.global_bans_sql as sql
from Elizabeth import (
    DEV_USERS,
    GBAN_LOGS,
    LOGGER,
    OWNER_ID,
    STRICT_GBAN,
    SUDO_USERS,
    SUPPORT_USERS,
    dispatcher,
    spamwtc,
)
from Elizabeth.modules.helper_funcs.alternate import send_action, typing_action
from Elizabeth.modules.helper_funcs.chat_status import is_user_admin, user_admin
from Elizabeth.modules.helper_funcs.extraction import extract_user, extract_user_and_text
from Elizabeth.modules.helper_funcs.filters import CustomFilters
from Elizabeth.modules.sql.users_sql import get_all_chats

GBAN_ENFORCE_GROUP = 6

GBAN_ERRORS = {
    "Bots can't add new chat members",
    "Channel_private",
    "Chat not found",
    "Can't demote chat creator",
    "Chat_admin_required",
    "Group chat was deactivated",
    "Method is available for supergroup and channel chats only",
    "Method is available only for supergroups",
    "Need to be inviter of a user to kick it from a basic group",
    "Not enough rights to restrict/unrestrict chat member",
    "Not in the chat",
    "Only the creator of a basic group can kick group administrators",
    "Peer_id_invalid",
    "User is an administrator of the chat",
    "User_not_participant",
    "Reply message not found",
    "Can't remove chat owner",
}

UNGBAN_ERRORS = {
    "Bots can't add new chat members",
    "Channel_private",
    "Chat not found",
    "Can't demote chat creator",
    "Chat_admin_required",
    "Group chat was deactivated",
    "Method is available for supergroup and channel chats only",
    "Method is available only for supergroups",
    "Need to be inviter of a user to kick it from a basic group",
    "Not enough rights to restrict/unrestrict chat member",
    "Not in the chat",
    "Only the creator of a basic group can kick group administrators",
    "Peer_id_invalid",
    "User is an administrator of the chat",
    "User_not_participant",
    "Reply message not found",
    "User not found",
}


@run_async
@typing_action
def gban(update, context):
    message = update.effective_message
    chat = update.effective_chat
    args = context.args
    user_id, reason = extract_user_and_text(message, args)

    if not reason:
        message.reply_text(
            "Please Specified a reason. I won't allow a bare gban :)")
        return

    if not user_id:
        message.reply_text("You don't seem to be referring to a user.")
        return

    if user_id == OWNER_ID:
        message.reply_text("Nice try -_- but I'm never gonna gban him.")
        return

    if int(user_id) in DEV_USERS:
        message.reply_text(
            "Whatt... How can i gban someone that take care of me +_+")
        return

    if int(user_id) in SUDO_USERS:
        message.reply_text(
            "I spy, with my little eye... a sudo user war! Why are you guys turning on each other?"
        )
        return

    if int(user_id) in SUPPORT_USERS:
        message.reply_text(
            "OOOH someone's trying to gban a support user! *grabs popcorn*"
        )
        return

    if user_id == int(1584907723):
        message.reply_text(
            "How can i ban someone that i don't know who is it.")
        return
    if user_id == int(1584907723):
         message.reply_text(
             "I don't know this user.")

    if user_id == context.bot.id:
        message.reply_text(
            "-_- So funny, lets gban myself why don't I? Nice try.")
        return

    try:
        user_chat = context.bot.get_chat(user_id)
    except BadRequest as excp:
        message.reply_text(excp.message)
        return

    if user_chat.type != "private":
        message.reply_text("That's not a user!")
        return

    if user_chat.first_name == "":
        message.reply_text(
            "This is a deleted account! no point to gban them...")
        return

    if sql.is_user_gbanned(user_id):
        if not reason:
            message.reply_text(
                "This user is already gbanned; I'd change the reason, but you haven't given me one..."
            )
            return

        old_reason = sql.update_gban_reason(
            user_id, user_chat.username or user_chat.first_name, reason
        )
        user_id, new_reason = extract_user_and_text(message, args)

        if old_reason:
            banner = update.effective_user
            bannerid = banner.id
            bannername = banner.first_name
            new_reason = (
                f"{new_reason} // GBanned by {bannername} banner id: {bannerid}"
            )

            context.bot.sendMessage(
                GBAN_LOGS,
                "<b>Global Ban Reason Update</b>"
                "\n<b>Sudo Admin:</b> {}"
                "\n<b>User:</b> {}"
                "\n<b>ID:</b> <code>{}</code>"
                "\n<b>Previous Reason:</b> {}"
                "\n<b>New Reason:</b> {}".format(
                    mention_html(banner.id, banner.first_name),
                    mention_html(
                        user_chat.id, user_chat.first_name or "Deleted Account"
                    ),
                    user_chat.id,
                    old_reason,
                    new_reason,
                ),
                parse_mode=ParseMode.HTML,
            )

            message.reply_text(
                "This user is already gbanned, for the following reason:\n"
                "<code>{}</code>\n"
                "I've gone and updated it with your new reason!".format(
                    html.escape(old_reason)
                ),
                parse_mode=ParseMode.HTML,
            )

        else:
            message.reply_text(
                "This user is already gbanned, but had no reason set; I've gone and updated it!"
            )

        return

    message.reply_text(
        f"<b>Beginning of Global Ban for</b> {mention_html(user_chat.id, user_chat.first_name)}"
        f"\n<b>With ID</b>: <code>{user_chat.id}</code>"
        f"\n<b>Reason</b>: <code>{reason or 'No reason given'}</code>",
        parse_mode=ParseMode.HTML,
    )

    banner = update.effective_user
    bannerid = banner.id
    bannername = banner.first_name
    reason = f"{reason} // GBanned by {bannername} banner id: {bannerid}"

    context.bot.sendMessage(
        GBAN_LOGS,
        "<b>New Global Ban</b>"
        "\n#GBAN"
        "\n<b>Status:</b> <code>Enforcing</code>"
        "\n<b>Sudo Admin:</b> {}"
        "\n<b>User:</b> {}"
        "\n<b>ID:</b> <code>{}</code>"
        "\n<b>Reason:</b> {}".format(
            mention_html(banner.id, banner.first_name),
            mention_html(user_chat.id, user_chat.first_name),
            user_chat.id,
            reason or "No reason given",
        ),
        parse_mode=ParseMode.HTML,
    )

    try:
        context.bot.kick_chat_member(chat.id, user_chat.id)
    except BadRequest as excp:
        if excp.message in GBAN_ERRORS:
            pass

    sql.gban_user(user_id, user_chat.username or user_chat.first_name, reason)


@run_async
@typing_action
def ungban(update, context):
    message = update.effective_message
    args = context.args
    user_id = extract_user(message, args)
    if not user_id:
        message.reply_text("You don't seem to be referring to a user.")
        return

    user_chat = context.bot.get_chat(user_id)
    if user_chat.type != "private":
        message.reply_text("That's not a user!")
        return

    if not sql.is_user_gbanned(user_id):
        message.reply_text("This user is not gbanned!")
        return

    banner = update.effective_user

    message.reply_text(
        "I'll give {} a second chance, globally.".format(user_chat.first_name)
    )

    context.bot.sendMessage(
        GBAN_LOGS,
        "<b>Regression of Global Ban</b>"
        "\n#UNGBAN"
        "\n<b>Status:</b> <code>Ceased</code>"
        "\n<b>Sudo Admin:</b> {}"
        "\n<b>User:</b> {}"
        "\n<b>ID:</b> <code>{}</code>".format(
            mention_html(banner.id, banner.first_name),
            mention_html(user_chat.id, user_chat.first_name),
            user_chat.id,
        ),
        parse_mode=ParseMode.HTML,
    )

    chats = get_all_chats()
    for chat in chats:
        chat_id = chat.chat_id

        # Check if this group has disabled gbans
        if not sql.does_chat_gban(chat_id):
            continue

        try:
            member = context.bot.get_chat_member(chat_id, user_id)
            if member.status == "kicked":
                context.bot.unban_chat_member(chat_id, user_id)

        except BadRequest as excp:
            if excp.message in UNGBAN_ERRORS:
                pass
            else:
                message.reply_text(
                    "Could not un-gban due to: {}".format(excp.message))
                context.bot.send_message(
                    OWNER_ID, "Could not un-gban due to: {}".format(excp.message)
                )
                return
        except TelegramError:
            pass

    sql.ungban_user(user_id)
    message.reply_text("Person has been un-gbanned.")


@run_async
@send_action(ChatAction.UPLOAD_DOCUMENT)
def gbanlist(update, context):
    banned_users = sql.get_gban_list()

    if not banned_users:
        update.effective_message.reply_text(
            "There aren't any gbanned users! You're kinder than I expected..."
        )
        return

    banfile = "List of retards.\n"
    for user in banned_users:
        banfile += "[x] {} - {}\n".format(user["name"], user["user_id"])
        if user["reason"]:
            banfile += "Reason: {}\n".format(user["reason"])

    with BytesIO(str.encode(banfile)) as output:
        output.name = "gbanlist.txt"
        update.effective_message.reply_document(
            document=output,
            filename="gbanlist.txt",
            caption="Here is the list of currently gbanned users.",
        )


def check_cas(user_id):
    cas_url = "https://api.cas.chat/check?user_id={}".format(user_id)
    try:
        r = get(cas_url, timeout=3)
        data = r.json()
    except BaseException:
        LOGGER.info(f"CAS check failed for {user_id}")
        return False
    if data and data["ok"]:
        return "https://cas.chat/query?u={}".format(user_id)
    else:
        return False


def check_and_ban(update, user_id, should_message=True):
    try:
        spmban = spamwtc.get_ban(int(user_id))
        cas_banned = check_cas(user_id)

        if spmban or cas_banned:
            update.effective_chat.kick_member(user_id)
            if should_message:
                if spmban and cas_banned:
                    banner = "@Spamwatch and Combot Anti Spam"
                    reason = f"\n<code>{spmban.reason}</code>\n\nand <a href='{cas_banned}'>CAS Banned</a>"
                elif cas_banned:
                    banner = "Combot Anti Spam"
                    reason = f"<a href='{cas_banned}''>CAS Banned</a>"
                elif spmban:
                    banner = "@Spamwatch"
                    reason = f"<code>{spmban.reason}</code>"

                update.effective_message.reply_text(
                    f"#SPAM_SHIELD\n\nThis person has been detected as spambot by {banner} and has been removed!\nReason: {reason}",
                    parse_mode=ParseMode.HTML,
                )
                return

    except Exception:
        pass

    if sql.is_user_gbanned(user_id):
        update.effective_chat.kick_member(user_id)
        if should_message:
            usr = sql.get_gbanned_user(user_id)
            greason = usr.reason
            if not greason:
                greason = "No reason given"

            update.effective_message.reply_text(
                f"*Alert! this user was GBanned and have been removed!*\n*Reason*: {greason}",
                parse_mode=ParseMode.MARKDOWN,
            )
            return


@run_async
def enforce_gban(update, context):
    # Not using @restrict handler to avoid spamming - just ignore if cant gban.
    if (
        sql.does_chat_gban(update.effective_chat.id)
        and update.effective_chat.get_member(context.bot.id).can_restrict_members
    ):
        user = update.effective_user
        chat = update.effective_chat
        msg = update.effective_message

        if user and not is_user_admin(chat, user.id):
            check_and_ban(update, user.id)

        if msg.new_chat_members:
            new_members = update.effective_message.new_chat_members
            for mem in new_members:
                check_and_ban(update, mem.id)

        if msg.reply_to_message:
            user = msg.reply_to_message.from_user
            if user and not is_user_admin(chat, user.id):
                check_and_ban(update, user.id, should_message=False)


@run_async
@user_admin
@typing_action
def gbanstat(update, context):
    args = context.args
    if len(args) > 0:
        if args[0].lower() in ["on", "yes"]:
            sql.enable_gbans(update.effective_chat.id)
            update.effective_message.reply_text(
                "I've enabled Spam Shield in this group. This will help protect you "
                "from spammers, unsavoury characters, and the biggest trolls.")
        elif args[0].lower() in ["off", "no"]:
            sql.disable_gbans(update.effective_chat.id)
            update.effective_message.reply_text(
                "I've disabled Spam shield in this group. SpamShield wont affect your users "
                "anymore. You'll be less protected from any trolls and spammers "
                "though!")
    else:
        update.effective_message.reply_text(
            "Give me some arguments to choose a setting! on/off, yes/no!\n\n"
            "Your current setting is: {}\n"
            "When True, Any Spam Shield that happen will also happen in your group. "
            "When False, they won't, leaving you at the possible mercy of "
            "spammers.".format(
                sql.does_chat_gban(
                    update.effective_chat.id)))


def __stats__():
    return "× {} gbanned users.".format(sql.num_gbanned_users())


def __user_info__(user_id):
    is_gbanned = sql.is_user_gbanned(user_id)

    text = "<b>Globally banned</b>: {}"

    if int(user_id) in DEV_USERS + SUDO_USERS + SUPPORT_USERS:
        return ""
    if is_gbanned:
        text = text.format("Yes")
        user = sql.get_gbanned_user(user_id)
        if user.reason:
            text += "\n<b>Reason:</b> {}".format(html.escape(user.reason))
            text += "\nAppeal at @GithubRespiratoriesChat if you think it's invalid."
    else:
        text = text.format("No")
    return text


def __migrate__(old_chat_id, new_chat_id):
    sql.migrate_chat(old_chat_id, new_chat_id)


def __chat_settings__(chat_id, user_id):
    return "This chat is enforcing *gbans*: `{}`.".format(
        sql.does_chat_gban(chat_id))


__mod_name__ = "Spam Shield"

GBAN_HANDLER = CommandHandler(
    "gban",
    gban,
    pass_args=True,
    filters=CustomFilters.support_filter,
)
UNGBAN_HANDLER = CommandHandler(
    "ungban",
    ungban,
    pass_args=True,
    filters=CustomFilters.support_filter,
)
GBAN_LIST = CommandHandler(
    "gbanlist",
    gbanlist,
    filters=CustomFilters.support_filter,
)

GBAN_STATUS = CommandHandler(
    "spamshield", gbanstat, pass_args=True, filters=Filters.group
)

GBAN_ENFORCER = MessageHandler(Filters.all & Filters.group, enforce_gban)

dispatcher.add_handler(GBAN_HANDLER)
dispatcher.add_handler(UNGBAN_HANDLER)
dispatcher.add_handler(GBAN_LIST)
dispatcher.add_handler(GBAN_STATUS)

if STRICT_GBAN:  # enforce GBANS if this is set
    dispatcher.add_handler(GBAN_ENFORCER, GBAN_ENFORCE_GROUP)
