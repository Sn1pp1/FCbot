import os
import asyncio
import logging
import random
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from aiohttp import web

# Настройки
TOKEN = os.getenv("BOT_TOKEN")
TRIGGER_PHRASE = "+"
participants = set()

bot = Bot(token=TOKEN)
dp = Dispatcher()
logging.basicConfig(level=logging.INFO)

# --- ВЕБ-СЕРВЕР ДЛЯ RENDER (чтобы не было Timed Out) ---
async def handle(request):
    return web.Response(text="ok")

async def start_web_server():
    app = web.Application()
    app.router.add_get("/", handle)
    runner = web.AppRunner(app)
    await runner.setup()
    # Render дает порт в переменной окружения PORT, если нет - берем 10000
    port = int(os.environ.get("PORT", 10000))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    print(f"Веб-сервер запущен на порту {port}")

# --- ЛОГИКА БОТА ---
def get_start_keyboard():
    builder = ReplyKeyboardBuilder()
    builder.button(text="🚀 Запустить сбор")
    return builder.as_markup(resize_keyboard=True)

def get_main_keyboard():
    builder = ReplyKeyboardBuilder()
    builder.button(text="+")
    builder.button(text="🛡 Поделить на команды")
    builder.button(text="♻️ Сброс")
    builder.adjust(1, 2)
    return builder.as_markup(resize_keyboard=True)

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer("Привет! Нажми на кнопку ниже.", reply_markup=get_start_keyboard())

@dp.message(F.text == "🚀 Запустить сбор")
async def open_menu(message: types.Message):
    await message.answer("Меню открыто!", reply_markup=get_main_keyboard())

@dp.message(F.text == TRIGGER_PHRASE)
async def register(message: types.Message):
    user_name = message.from_user.full_name
    if user_name not in participants:
        participants.add(user_name)
        await message.reply(f"✅ {user_name} в списке! Всего: {len(participants)}")
    else:
        await message.reply("Вы уже записаны.")

@dp.message(F.text == "🛡 Поделить на команды")
async def divide(message: types.Message):
    if len(participants) < 2:
        await message.answer("Нужно минимум 2 человека!")
        return
    players = list(participants)
    random.shuffle(players)
    mid = len(players) // 2
    team1, team2 = players[:mid], players[mid:]
    res = f"⚔️ **КОМАНДА 1:**\n" + "\n".join(team1) + f"\n\n🛡 **КОМАНДА 2:**\n" + "\n".join(team2)
    await message.answer(res, parse_mode="Markdown")

@dp.message(F.text == "♻️ Сброс")
async def reset(message: types.Message):
    participants.clear()
    await message.answer("Список очищен!")

# --- ЗАПУСК ---
async def main():
    # Запускаем "обманку" для Render
    await start_web_server()
    # Очищаем вебхуки и запускаем бота
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

