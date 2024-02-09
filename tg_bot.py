import logging
from typing import Final
from config import *
from telegram import Update
from telegram.ext import Application, MessageHandler, CommandHandler, filters,\
ContextTypes

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

# Set higher logging level for httpx to avoid all GET and POST
# requests being logged
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

# Command handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user.username
    await update.message.reply_text(f"Привіт, {user}! Для списку команд \
скористайся командою /help")
    
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text('''/help - список команд
/post - надіслати пост
/fumo - Фумізація повідомлень ᗜˬᗜ''')
    
async def fumo_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_message = update.message.text
    await update.message.reply_text(f"{user_message.replace('/fumo', '')} ᗜˬᗜ")
 
# Add functionality, update response, send content to me    
async def post_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message
    print(f'message: ', user_message)
    await update.message.reply_text('''Дякую за пропозицію.
Пост надіслано адміністрації.''')

# Responses
def handle_response(text: str) -> str:
    
    processed:str = text.lower()
    
    if 'fumo' in processed:
        return 'Fumo enjoyer!'
    
    return '''Я не вмію відповідати на повідомлення.
Використай команду зі списку /help.'''

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message_type: str = update.message.chat.type # group or private
    text: str = update.message.text
    
    print(f'User {update.message.chat.username} ({update.message.chat.id}) \
in {message_type}: "{text}"')
    
    if message_type == "group":
        if BOT_NAME in text:
            new_text: str = text.replace(BOT_NAME, '').strip()
            response: str = handle_response(new_text)
        else:
            return
    else:
        response: str = handle_response(text)
        
    print('Bot:', response)
    await update.message.reply_text(response)

async def error(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f'Update {update} caused error {context.error}')
    
    

if __name__ == "__main__":
    print('Starting bot...')
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("post", post_command))
    app.add_handler(CommandHandler("fumo", fumo_command))
    
    # Messages
    app.add_handler(MessageHandler(filters.TEXT, handle_message))
    
    # Errors
    app.add_error_handler(error)
    
    # Bot polling
    print('Polling...')
    app.run_polling(poll_interval=3)