import os
import asyncio
import logging
import random
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from aiohttp import web

# --- НАСТРОЙКИ ---
TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(token=TOKEN)
dp = Dispatcher()
logging.basicConfig(level=logging.INFO)

is_collecting = False
participants = []
temp_limit = 5

# --- ВЕБ-СЕРВЕР ---
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

# --- КЛАВИАТУРЫ ---
def get_main_kb():
    builder = ReplyKeyboardBuilder()
    builder.button(text="➕ Записаться на игру")
    builder.button(text="🛡 Поделить на команды")
    builder.button(text="♻️ Сбросить список")
    builder.button(text="🛑 Остановить сбор (STOP)")
    builder.adjust(1, 2, 1)
    return builder.as_markup(resize_keyboard=True)

def get_limit_kb():
    builder = InlineKeyboardBuilder()
    for i in range(4, 9):
        builder.button(text=f"По {i}", callback_data=f"set_limit_{i}")
    builder.adjust(3)
    return builder.as_markup()

def get_split_kb():
    builder = InlineKeyboardBuilder()
    builder.button(text="На 2 команды", callback_data="split_2")
    builder.button(text="На 3 команды", callback_data="split_3")
    builder.button(text="На 4 команды", callback_data="split_4")
    builder.adjust(1)
    return builder.as_markup()

# --- ЛОГИКА ДЕЛЕНИЯ ---
def split_logic(num_teams, limit_per_team):
    if not participants:
        return "Список пуст!"
    
    temp_list = list(participants)
    random.shuffle(temp_list)
    
    total_slots = num_teams * limit_per_team
    main_players = temp_list[:total_slots]
    bench_players = temp_list[total_slots:]
    
    teams = [[] for _ in range(num_teams)]
    for i, player in enumerate(main_players):
        teams[i % num_teams].append(player)
    
    res = "⚽️ **РЕЗУЛЬТАТ ЖЕРЕБЬЕВКИ:**\n\n"
    for i, team in enumerate(teams):
        if team:
            res += f"👕 **КОМАНДА {i+1}** ({len(team)}/{limit_per_team})\n"
            res += "\n".join([f"🔹 {p}" for p in team]) + "\n\n"
    
    if bench_players:
        res += "🔄 **ЗАМЕНА / ОЧЕРЕДЬ:**\n"
        res += "\n".join([f"🔸 {p}" for p in bench_players])
    
    return res

# --- ОБРАБОТЧИКИ ---

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    global is_collecting, participants
    is_collecting = True
    participants = []
    await message.answer(
        "🚀 **СБОР НА ИГРУ ОТКРЫТ!**\n\nНажимай кнопки или пиши **+**",
        reply_markup=get_main_kb(),
        parse_mode="Markdown"
    )

@dp.message(F.text == "➕ Записаться на игру")
@dp.message(F.text == "+")
async def handle_registration(message: types.Message):
    global is_collecting, participants
    if not is_collecting: return
    
    user_name = message.from_user.full_name
    if user_name not in participants:
        participants.append(user_name)
        await message.reply(f"✅ {user_name} в списке! (Всего: {len(participants)})")
    else:
        await message.reply("Вы уже в списке!")

@dp.message(F.text == "🛡 Поделить на команды")
async def press_divide(message: types.Message):
    if len(participants) < 2:
        await message.answer("⚠️ Нужно минимум 2 человека!")
        return
    await message.answer("📏 По сколько человек в одной команде?", reply_markup=get_limit_kb())

@dp.callback_query(F.data.startswith("set_limit_"))
async def callback_limit(callback: types.CallbackQuery):
    global temp_limit
    temp_limit = int(callback.data.split("_")[2])
    await callback.message.edit_text(
        f"🏃 Лимит: {temp_limit} чел/команда\n👥 Всего игроков: {len(participants)}\n\nНа сколько команд делим?",
        reply_markup=get_split_kb()
    )

@dp.callback_query(F.data.startswith("split_"))
async def callback_split(callback: types.CallbackQuery):
    num_teams = int(callback.data.split("_")[1])
    result_text = split_logic(num_teams, temp_limit)
    await callback.message.answer(result_text, parse_mode="Markdown")
    await callback.answer()

@dp.message(F.text == "♻️ Сбросить список")
async def press_reset(message: types.Message):
    global participants
    participants = []
    await message.answer("🗑 Список очищен!")

@dp.message(F.text == "🛑 Остановить сбор (STOP)")
@dp.message(Command("stop"))
async def press_stop(message: types.Message):
    global is_collecting, participants
    is_collecting = False
    participants = []
    await message.answer("❌ Сбор закрыт!", reply_markup=types.ReplyKeyboardRemove())

async def main():
    await start_web_server()
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.error("Bot stopped!")
