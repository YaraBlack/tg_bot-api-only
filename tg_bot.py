import logging
from typing import TypedDict, Literal, cast
from config import *
from telegram import (
    Update,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    InputMediaAudio,
    InputMediaPhoto,
    InputMediaAnimation,
    InputMediaVideo,
)
from telegram.ext import (
    Application,
    MessageHandler,
    CommandHandler,
    filters,
    ContextTypes,
    CallbackContext,
    ConversationHandler,
)
from telegram.helpers import effective_message_type

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

# Set higher logging level for httpx to avoid all GET and POST
# requests being logged
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

# Set constants
admins_ids: tuple = ADMINS_IDS
ANON_STEP, PROPOSED_CONTENT_STEP = range(2)
MEDIA_GROUP_TYPES = {
    "audio": InputMediaAudio,
    "video": InputMediaVideo,
    "photo": InputMediaPhoto,
    "animation": InputMediaAnimation,
}

post_proposal_user = [None, None]
isAnon = False


# Create typed dictionary for media item
class MsgDict(TypedDict):
    media_type: Literal["audio", "video", "photo", "animation"]
    media_id: str
    caption: str
    message_id: int


# Function to handle sending media group
async def sendMediaGroup(context: CallbackContext):
    bot = context.bot
    context.job.data = cast(list[MsgDict], context.job.data)
    media = []
    for msg_dict in context.job.data:
        media.append(
            MEDIA_GROUP_TYPES[msg_dict["media_type"]](
                media=msg_dict["media_id"], caption=msg_dict["caption"]
            )
        )
        if not media:
            return

        await bot.send_media_group(chat_id=ADMINS_IDS[0], media=media)


# Function to send a notification to admins
async def sendNotification(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global post_proposal_user, isAnon
    msg_text = ""
    await update.message.reply_text(
        "Дякую! Твій пост надісланий на перевірку адміністрації!"
    )
    if isAnon:
        msg_text = "Анонім запропонував пост."
    else:
        msg_text = f"@{post_proposal_user[1]} ({post_proposal_user[0]}) запропонував пост."
    for admin_id in ADMINS_IDS:
        await context.bot.send_message(
            chat_id=admin_id,
            text=msg_text,
        )
    return


# Command handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user.username
    await update.message.reply_text(
        f"Привіт, {user}! Для списку команд \
скористайся командою /help"
    )


async def helpCommand(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    await update.message.reply_text(
        """/help - список команд
/post - надіслати пост
/fumo - Фумізація повідомлень ᗜˬᗜ"""
    )


async def getUserIdCommand(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    await update.message.reply_text(
        f"Твій Telegram User ID: {update.effective_user.id}"
    )


async def fumoCommand(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    user_message = update.message.text
    await update.message.reply_text(f"{user_message.replace('/fumo', '')} ᗜˬᗜ")


# Add functionality, update response, send content to me
async def postCommand(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:

    reply_keyboard = [["Так", "Ні"]]

    await update.message.reply_text(
        "Чи бажаєш відправити пост анонімно?",
        reply_markup=ReplyKeyboardMarkup(
            reply_keyboard,
            one_time_keyboard=True,
            resize_keyboard=True,
        ),
    )

    return ANON_STEP


async def checkAnon(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:

    if (
        update.message.text.lower() == "так"
        or update.message.text.lower() == "ні"
    ):
        if update.message.text.lower() == "так":
            global isAnon
            isAnon = True
        elif update.message.text.lower() == "ні":
            global post_proposal_user
            post_proposal_user[0] = update.message.from_user.id
            post_proposal_user[1] = update.message.from_user.username
        await update.message.reply_text("Надішли свій пост (до 10-ти файлів):")
        return PROPOSED_CONTENT_STEP
    else:
        await update.message.reply_text(
            "Невірний варіант відповіді. Спробуй ще раз."
        )
        return None


async def proposeContent(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:

    if update.message.media_group_id:
        message = update.effective_message
        media_type = effective_message_type(message)
        media_id = (
            message.photo[-1].file_id
            if message.photo
            else message.effective_attachment.file_id
        )
        msg_dict = {
            "media_type": media_type,
            "media_id": media_id,
            "caption": message.caption_html,
            "message_id": message.message_id,
        }
        # jobs = context.job_queue.get_jobs_by_name(str(message.media_group_id))
        # if jobs:
        #     jobs[0].data.append(msg_dict)
        # else:
        print("Running job")
        context.job_queue.run_once(
            callback=sendMediaGroup,
            when=2,
            data=[msg_dict],
            name=str(message.media_group_id),
        )
        return None
    else:
        await sendNotification(update, context)
        for admin_id in ADMINS_IDS:
            await context.bot.forward_message(
                chat_id=admin_id,
                from_chat_id=update.effective_chat.id,
                message_id=update.message.message_id,
            )
        return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Відмінено.")
    return ConversationHandler.END


# Responses
def handle_response(text: str) -> str:

    processed: str = text.lower()

    if "fumo" in processed:
        return "Fumo enjoyer!"

    return """Я не вмію відповідати на повідомлення.
Використай команду зі списку /help."""


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message_type: str = update.message.chat.type  # group or private
    text: str = update.message.text

    print(
        f'User {update.message.chat.username} ({update.message.chat.id}) \
in {message_type}: "{text}"'
    )

    if message_type == "group":
        if BOT_NAME in text:
            new_text: str = text.replace(BOT_NAME, "").strip()
            response: str = handle_response(new_text)
        else:
            return
    else:
        response: str = handle_response(text)

    print("Bot:", response)
    await update.message.reply_text(response)


async def error(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f"Update {update} caused error {context.error}")


if __name__ == "__main__":
    print("Starting bot...")
    app = Application.builder().token(BOT_TOKEN).build()

    # Commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", helpCommand))
    app.add_handler(CommandHandler("id", getUserIdCommand))
    app.add_handler(CommandHandler("fumo", fumoCommand))

    # Messages
    # app.add_handler(MessageHandler(filters.TEXT, handle_message))

    # Conversation
    app.add_handler(
        ConversationHandler(
            entry_points=[CommandHandler("post", postCommand)],
            states={
                ANON_STEP: [
                    MessageHandler(
                        filters.Regex("^(Так|Ні|так|ні)$"), checkAnon
                    )
                ],
                PROPOSED_CONTENT_STEP: [
                    MessageHandler(
                        filters.PHOTO
                        | filters.ANIMATION
                        | filters.AUDIO
                        | filters.VIDEO
                        | filters.VOICE
                        | filters.TEXT
                        | filters.Sticker.ALL
                        | filters.VIDEO_NOTE
                        | filters.VOICE,
                        proposeContent,
                    )
                ],
            },
            fallbacks=[CommandHandler("cancel", cancel)],
        )
    )

    # Errors
    app.add_error_handler(error)
    if "messages" not in app.bot_data:
        app.bot_data = {"messages": {}}
    # Bot polling
    print("Polling...")
    app.run_polling(poll_interval=1, allowed_updates=Update.ALL_TYPES)
