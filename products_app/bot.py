import telebot
from telebot import types

TOKEN = '7617663130:AAEuX-g0KbLm9rjCXRJUu_bUJm5IUxeu8qY'

CHAT_ID = '-4731854641'

bot = telebot.TeleBot(TOKEN, parse_mode=None)

def send_self_order():
    markup = types.InlineKeyboardMarkup()
    accept_button = types.InlineKeyboardButton('Прийняти', callback_data='accept')
    decline_button = types.InlineKeyboardButton('Відмовити', callback_data='decline')
    markup.add(accept_button, decline_button)
    
    bot.send_message(CHAT_ID, 'Закак: _______________________', reply_markup=markup)