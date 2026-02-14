import os
import asyncio
import logging
import random
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from aiohttp import web

# --- НАСТРОЙКИ ---
TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(token=TOKEN)
dp = Dispatcher()
logging.basicConfig(level=logging.INFO)

# Состояние бота
is_collecting = False
participants = []

# --- ВЕБ-СЕРВЕР ДЛЯ RENDER (чтобы бот не засыпал) ---
async def handle(request):
    return web.Response(text="ok")

async def start_web_server():
    app = web.Application()
    app.router.add_get("/", handle)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 10000))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()

# --- КЛАВИАТУРА (теперь общая для всех) ---
def get_main_kb():
    builder = ReplyKeyboardBuilder()
    builder.button(text="➕ Записаться на игру")
    builder.button(text="🛡 Поделить на команды")
    builder.button(text="♻️ Сбросить список")
    builder.button(text="🛑 Остановить сбор (STOP)")
    
    builder.adjust(1, 2, 1) 
    return builder.as_markup(resize_keyboard=True)

# --- Функция деления на команды ---
def get_teams_text():
    if len(participants) < 2:
        return "⚠️ Слишком мало людей для деления! (нужно минимум 2)"
    
    temp_list = list(participants)
    random.shuffle(temp_list)
    
    mid = len(temp_list) // 2
    team1 = temp_list[:mid]
    team2 = temp_list[mid:]
    
    res = "⚽️ **РЕЗУЛЬТАТ ЖЕРЕБЬЕВКИ:**\n\n"
    res += "👕 **КОМАНДА 1:**\n" + "\n".join([f"🔹 {p}" for p in team1])
    res += "\n\n  ⚡️  **VS** ⚡️  \n\n"
    res += "👕 **КОМАНДА 2:**\n" + "\n".join([f"🔸 {p}" for p in team2])
    return res

# --- ЛОГИКА ---

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    global is_collecting, participants
    is_collecting = True
    participants = []
    await message.answer(
        "🚀 **СБОР НА ИГРУ ОТКРЫТ!**\n\nЛюбой может нажать **➕ Записаться** или просто написать **+** в чат.",
        reply_markup=get_main_kb(),
        parse_mode="Markdown"
    )

@dp.message(F.text == "➕ Записаться на игру")
@dp.message(F.text == "+")
async def handle_registration(message: types.Message):
    global is_collecting, participants
    if not is_collecting:
        return # Если сбор не запущен, игнорируем плюсы
    
    user_name = message.from_user.full_name
    if user_name not in participants:
        participants.append(user_name)
        await message.reply(f"✅ {user_name} в списке! (Всего: {len(participants)})")
    else:
        await message.reply("Вы уже записаны!")

@dp.message(F.text == "🛡 Поделить на команды")
async def press_divide(message: types.Message):
    # Теперь любой может нажать и посмотреть промежуточный итог
    await message.answer(get_teams_text(), parse_mode="Markdown")

@dp.message(F.text == "♻️ Сбросить список")
async def press_reset(message: types.Message):
    global participants
    participants = []
    await message.answer("🗑 Список участников очищен кем-то из игроков!")

@dp.message(F.text == "🛑 Остановить сбор (STOP)")
@dp.message(Command("stop"))
async def press_stop(message: types.Message):
    global is_collecting, participants
    
    if is_collecting and len(participants) >= 2:
        await message.answer("🏁 **ИТОГОВЫЕ СОСТАВЫ:**")
        await message.answer(get_teams_text(), parse_mode="Markdown")
    
    is_collecting = False
    participants = []
    await message.answer(
        "❌ Сбор закрыт. Всем удачной игры!", 
        reply_markup=types.ReplyKeyboardRemove()
    )

# --- ЗАПУСК ---
async def main():
    await start_web_server()
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
