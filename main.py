from bs4 import BeautifulSoup
import lxml
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import telebot
import sqlite3
import re
from setup import variables
import time
import threading
import random
import logging

logging.basicConfig(
    level=logging.WARNING,
    filename = "setup/mylog.log",
    format = "%(asctime)s - %(module)s - %(levelname)s - %(funcName)s: %(lineno)d - %(message)s",
    datefmt='%H:%M:%S',
    )
logging.warning('________________________________HELLO__________________________________')


api_key = variables.tg_api
bot = telebot.TeleBot(token = api_key, parse_mode='HTML')

conn = sqlite3.connect('setup/mydatabase.db', check_same_thread=False)
cursor = conn.cursor()

user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36'

def product_sender(chat_id, title, href, img_src, price):
    text = f'{title}\n\n<b><u>Цена:</u></b> {price}\n\n{href}'

    if img_src is not None:
        bot.send_photo(chat_id=chat_id, photo=img_src, caption=text)
    else:
        bot.send_message(chat_id=chat_id, text=text)
        
        

def search_for_updates(chat_id, url): #выдает апдейты если есть
    chrome_options = Options()
    chrome_options.add_argument(f'user-agent={user_agent}')
    chrome_options.add_argument('--headless')  # Запуск в безголовом режиме
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    driver = webdriver.Chrome(options=chrome_options)

    driver.get(url)
    

    html = driver.page_source
    # with open('1out.html',encoding='utf-8') as f:
    #     html = f.read()
    soup = BeautifulSoup(html, 'lxml')
    products = soup.find('div', class_= re.compile(r'^items-items')).find_all('div', class_=re.compile(r"iva-item-root"))
    

    for product in products:
        link_element = product.find('a', class_=re.compile(r"^iva-item-sliderLink"))

        title = link_element.get('title')
        href = 'https://www.avito.ru'+link_element.get('href')

        try:
            img_src = link_element.find('img').get('src')
        except:
            img_src = None # если нет картинки
        price = product.find('div', class_=re.compile(r"price-price")).find('span').text.replace('\xa0', ' ')


        
        
        cursor.execute("SELECT items_url FROM activity WHERE chat_id = ? AND search_url = ?", (chat_id, url))
        current_urls = cursor.fetchone()

        if current_urls[0] != None:
            # Если текущие ссылки есть, добавляем новую ссылку, если она еще не добавлена
            updated_urls = current_urls[0]
            if href not in updated_urls:
                updated_urls += ',' + href
                cursor.execute("UPDATE activity SET items_url = ? WHERE chat_id = ? AND search_url = ?", (updated_urls, chat_id, url))
                conn.commit()

                # Отправляем сообщение
                product_sender(chat_id, title, href, img_src, price)
        else:
            # Если строка отсутствует, добавляем её с первой ссылкой
            cursor.execute("UPDATE activity SET items_url = ? WHERE chat_id = ? AND search_url = ?", (href, chat_id, url))
            conn.commit()

            product_sender(chat_id, title, href, img_src, price)
                   



# Определяем команды для меню
commands = [
    telebot.types.BotCommand("/donate", "Дать мотивацию❤️"),
    telebot.types.BotCommand("/searches", "Мои поиски"),
    telebot.types.BotCommand("/help", "Помощь по боту")
]
# Устанавливаем команды для бота
bot.set_my_commands(commands)


@bot.message_handler(content_types=['text'])
def main(message):
    if message.text == '/start':
        bot.send_message(chat_id=message.from_user.id, text='Здравствуйте! Чтобы добавить отслеживание, отправьте url страницы авито с уже выстроенными фильтрами и <u><b>обязательной фильтрацией по дате</b></u>.')

    elif message.text == '/help':
        bot.send_message(chat_id=message.from_user.id, text='Чтобы добавить отслеживание, отправьте url страницы авито с уже выстроенными фильтрами и <u><b>обязательной фильтрацией по дате</b></u>.')
    
    elif message.text == '/donate':
        bot.send_message(chat_id=message.from_user.id, text=f'<u><b>Смотивируй меня❤️</b></u>\n\nСбербанк\n<code>{variables.card}</code>\n\nUSDT-TON\n<code>{variables.usdt_ton}</code>\n\nHMSTR-coin\n<code>{variables.hmstr}</code>')
    
    elif message.text == '/searches':
        markup = telebot.types.InlineKeyboardMarkup(row_width=5)
        message_text = ''
        k=1
        for url_perebor_1 in cursor.execute(f"SELECT rowid, search_url FROM activity WHERE chat_id=?", (message.chat.id,)):
            message_text += f'{k}. {url_perebor_1[1]}\n\n'
            markup.add(telebot.types.InlineKeyboardButton(text=f'🗑️{k}', callback_data=f'del_{url_perebor_1[0]} {k}'))
            k+=1

        if k==1:
            bot.send_message(chat_id=message.chat.id, text= '<u><b>Поисков нет</b></u>\n\n')
        else:
            bot.send_message(chat_id=message.chat.id, text= '<u><b>Статус:</b></u>\n\n'+message_text, reply_markup=markup)
        
    
    elif message.text.startswith('https://www.avito.ru/'):

        if len([i for i in cursor.execute("SELECT search_url FROM activity WHERE chat_id = ?", (message.chat.id,))]) == 2:
            bot.send_message(chat_id=message.from_user.id, text='Ограничение на одновременный поиск = 2')
        else:
            cursor.execute("SELECT * FROM activity WHERE search_url=? and chat_id=?", (message.text, message.chat.id))
            
            # Если URL не найден, добавляем его
            if cursor.fetchone() is None:
                cursor.execute("INSERT INTO activity (chat_id, search_url) VALUES (?, ?)", (message.from_user.id, message.text))
                conn.commit()  # Фиксируем изменения

                search_count = cursor.execute("SELECT * FROM activity WHERE chat_id=?", (message.from_user.id,))
                markup = telebot.types.InlineKeyboardMarkup()
                markup.add(telebot.types.InlineKeyboardButton(text=f'🔍Всего {len([1 for _ in search_count])} в поиске', callback_data='search_count'))
                bot.send_message(chat_id=message.from_user.id, text='✅Добавлено в поиск',reply_markup=markup)
            else:
                search_count = cursor.execute("SELECT * FROM activity WHERE chat_id=?", (message.from_user.id,))
                markup = telebot.types.InlineKeyboardMarkup()
                markup.add(telebot.types.InlineKeyboardButton(text=f'🔍Всего {len([1 for _ in search_count])} в поиске', callback_data='search_count'))
                bot.send_message(chat_id=message.from_user.id, text='❌Уже в поиске',reply_markup=markup)

        
@bot.callback_query_handler(func=lambda call: True)
def answer(call:telebot.types.CallbackQuery):
    if call.data =='search_count':
        markup = telebot.types.InlineKeyboardMarkup(row_width=5)
        message_text = ''
        k=1
        for url_perebor_1 in cursor.execute(f"SELECT rowid, search_url FROM activity WHERE chat_id=?", (call.message.chat.id,)):
            message_text += f'{k}. {url_perebor_1[1]}\n\n'
            markup.add(telebot.types.InlineKeyboardButton(text=f'🗑️{k}', callback_data=f'del_{url_perebor_1[0]} {k}'))
            k+=1
        
        bot.send_message(chat_id=call.message.chat.id, text= '<u><b>Статус:</b></u>\n\n'+message_text, reply_markup=markup)
        bot.answer_callback_query(call.id)

    elif call.data.startswith('del_'):
        cursor.execute("DELETE FROM activity WHERE rowid=?", (call.data.split()[0].replace('del_', ''),))
        conn.commit()

        bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
        bot.send_message(chat_id=call.message.chat.id, text=f'Поиск "{call.data.split()[1]}" удален')
        bot.answer_callback_query(call.id)
        
        
def process_feed():
    while True:
        time.sleep(variables.db_update_time)

        urls_for_search = cursor.execute("SELECT chat_id, search_url FROM activity WHERE search_url IS NOT NULL")
        rows = cursor.fetchall()

        if len(rows) > 0:

            united_time_for_updates = variables.united_time_for_updates

            random.shuffle(rows)

            for chat_id, search_url in rows:
                if cursor.execute(f"SELECT search_url FROM activity WHERE chat_id=? and search_url=?", (chat_id, search_url)).fetchone() != None:
                    search_for_updates(chat_id, search_url)
                    time.sleep(united_time_for_updates)
        


if __name__ == '__main__':
    try:
        thread = threading.Thread(target=process_feed, daemon=True)
        thread.start()
        bot.polling(none_stop=True, skip_pending=True)
    except Exception as err:
        logging.exception(str(err))
        print('??????????????????___Fatal error has occured!___?????????????????',end='\n')
        print(err)
