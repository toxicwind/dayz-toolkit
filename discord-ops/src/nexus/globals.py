
from typing import Optional, Any

# Global reference to the bot instance
bot_ref: Optional[Any] = None

def get_bot():
    return bot_ref

def set_bot(bot):
    global bot_ref
    bot_ref = bot
