import requests
import router_api
import os
import asyncio
import json
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, executor
from aiogram.types import Message

load_dotenv()

bot = Bot(token=os.getenv("BOT_API_TOKEN"))
dp = Dispatcher(bot)

# Файл для хранения chat_id, куда слать уведомления
NOTIFY_CHAT_FILE = "notify_chat_id.txt"

def save_notify_chat(chat_id: int):
    with open(NOTIFY_CHAT_FILE, "w") as f:
        f.write(str(chat_id))

def load_notify_chat() -> int | None:
    try:
        with open(NOTIFY_CHAT_FILE, "r") as f:
            return int(f.read().strip())
    except (FileNotFoundError, ValueError, OSError):
        return None

last_present = set()
last_was_empty = False  # чтобы не спамить "офис опустел" каждый раз

async def monitor_presence():
    global last_present, last_was_empty
    while True:
        try:
            current_people = set(router_api.get_present_people())
            chat_id = load_notify_chat()

            if chat_id:
                # 1. Кто пришёл?
                newly_arrived = current_people - last_present
                for person in newly_arrived:
                    await bot.send_message(chat_id, f"👋 {person} пришёл(ла) в офис!")

                # 2. Кто ушёл?
                just_left = last_present - current_people
                for person in just_left:
                    await bot.send_message(chat_id, f"🚪 {person} ушёл(ла) из офиса.")

                # 3. Офис стал пустым (и раньше не был пустым)?
                is_now_empty = len(current_people) == 0
                if is_now_empty and not last_was_empty and len(last_present) > 0:
                    await bot.send_message(chat_id, "🕗 Офис опустел...")

                last_was_empty = is_now_empty

            last_present = current_people

        except Exception as e:
            print(f"[ERROR] Ошибка при мониторинге: {e}")

        await asyncio.sleep(60)

# === Обработчики команд ===

@dp.message_handler(commands=['start'])
async def send_welcome(message: Message):
    await message.reply(
        "Привет! Я бот офиса.\n"
        "Команды: ClumbaTech\n"
        "/getip — мой внешний IP\n"
        "/whoishere — кто в офисе\n"
        "/setnotify — включить уведомления в этом чате"
    )

@dp.message_handler(commands=['getip'])
async def send_ip(message: Message):
    try:
        ip_response = requests.get('https://ipv4-internet.yandex.net/api/v0/ip', timeout=5).text
        await message.answer(ip_response.strip('"'))
    except Exception as e:
        await message.answer("❌ Не удалось получить IP")

@dp.message_handler(commands=['whoishere'])
async def who_is_here(message: Message):
    response = router_api.convert_to_string()
    await message.answer(response)

@dp.message_handler(commands=['setnotify'])
async def set_notify_chat(message: Message):
    save_notify_chat(message.chat.id)
    await message.answer("✅ Уведомления о появлении сотрудников включены в этом чате!")

@dp.message_handler()
async def echo(message: Message):
    await message.answer("Неизвестная команда. Используй /start для справки.")

# === Запуск ===

if __name__ == '__main__':
    # Запускаем фоновую задачу мониторинга
    loop = asyncio.get_event_loop()
    loop.create_task(monitor_presence())
    
    # Запускаем бота
    executor.start_polling(dp, skip_updates=True)