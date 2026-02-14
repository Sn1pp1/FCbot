import os
import asyncio
import logging
import random
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
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

# --- КЛАВИАТУРЫ (ИНЛАЙН) ---

def get_main_inline_kb():
    builder = InlineKeyboardBuilder()
    builder.button(text="➕ Записаться", callback_data="reg")
    builder.button(text="🛡 Поделить", callback_data="ask_limit")
    builder.button(text="♻️ Сброс", callback_data="reset")
    builder.button(text="🛑 Стоп", callback_data="stop")
    builder.adjust(2)
    return builder.as_markup()

def get_limit_kb():
    builder = InlineKeyboardBuilder()
    for i in range(4, 9):
        builder.button(text=f"По {i}", callback_data=f"set_limit_{i}")
    builder.adjust(3)
    return builder.as_markup()

def get_split_kb():
    builder = InlineKeyboardBuilder()
    builder.button(text="На 2 команды", callback_data="do_split_2")
    builder.button(text="На 3 команды", callback_data="do_split_3")
    builder.button(text="На 4 команды", callback_data="do_split_4")
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
        "🚀 **СБОР НА ИГРУ ОТКРЫТ!**\n\nНажимай кнопку ниже или пиши **+** в чат.",
        reply_markup=get_main_inline_kb(),
        parse_mode="Markdown"
    )

# Обработка кнопки "Записаться" и текстового "+"
@dp.callback_query(F.data == "reg")
async def callback_reg(callback: types.CallbackQuery):
    await handle_reg_logic(callback.message, callback.from_user)
    await callback.answer()

@dp.message(F.text == "+")
async def message_reg(message: types.Message):
    await handle_reg_logic(message, message.from_user)

async def handle_reg_logic(message, user):
    global is_collecting, participants
    if not is_collecting: return
    
    user_name = user.full_name
    if user_name not in participants:
        participants.append(user_name)
        await message.answer(f"✅ {user_name} в списке! (Всего: {len(participants)})")
    else:
        await message.answer(f"⚠️ {user_name}, ты уже в списке!")

# Обработка кнопки "Поделить"
@dp.callback_query(F.data == "ask_limit")
async def callback_ask_limit(callback: types.CallbackQuery):
    if len(participants) < 2:
        await callback.answer("⚠️ Нужно минимум 2 человека!", show_alert=True)
        return
    await callback.message.answer("📏 По сколько человек в одной команде?", reply_markup=get_limit_kb())
    await callback.answer()

@dp.callback_query(F.data.startswith("set_limit_"))
async def callback_set_limit(callback: types.CallbackQuery):
    global temp_limit
    temp_limit = int(callback.data.split("_")[2])
    await callback.message.edit_text(
        f"🏃 Лимит: {temp_limit} чел/команда\n👥 Игроков: {len(participants)}\n\nНа сколько команд делим?",
        reply_markup=get_split_kb()
    )

@dp.callback_query(F.data.startswith("do_split_"))
async def callback_do_split(callback: types.CallbackQuery):
    num_teams = int(callback.data.split("_")[2])
    result_text = split_logic(num_teams, temp_limit)
    await callback.message.answer(result_text, parse_mode="Markdown")
    await callback.answer()

# Сброс и Стоп
@dp.callback_query(F.data == "reset")
async def callback_reset(callback: types.CallbackQuery):
    global participants
    participants = []
    await callback.message.answer("🗑 Список очищен!")
    await callback.answer()

@dp.callback_query(F.data == "stop")
async def callback_stop(callback: types.CallbackQuery):
    global is_collecting, participants
    is_collecting = False
    participants = []
    await callback.message.edit_text("❌ Сбор закрыт! Всем удачи.")
    await callback.answer()

# --- ЗАПУСК ---
async def main():
    await start_web_server()
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
