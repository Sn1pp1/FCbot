import os
import asyncio
import random
import logging
from dotenv import load_dotenv
load_dotenv()
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiohttp import web

# --- НАСТРОЙКИ ---
TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(token=TOKEN)
dp = Dispatcher()
logging.basicConfig(level=logging.INFO)

# Состояние
participants = []
is_collecting = False
temp_limit = 5 

def get_main_kb():
    builder = InlineKeyboardBuilder()
    # Кнопка записи видна только если сбор открыт
    if is_collecting:
        builder.button(text="➕ Записаться / Выписаться", callback_data="toggle_reg")
    
    builder.button(text="📋 Кто записан?", callback_data="show_list")
    builder.button(text="🛡 Поделить команды", callback_data="ask_limit")
    
    if is_collecting:
        builder.button(text="🛑 Остановить сбор", callback_data="stop_collect")
    
    builder.button(text="♻️ Сброс (Новый сбор)", callback_data="reset")
    builder.adjust(1)
    return builder.as_markup()

async def update_main_post(message: types.Message):
    status = "🟢 СБОР ОТКРЫТ" if is_collecting else "🔴 СБОР ЗАКРЫТ"
    text = (f"⚽️ **{status}**\n\n📈 Записано: **{len(participants)}**\n\n"
            f"Используйте кнопки ниже для управления.")
    try:
        await message.edit_text(text, reply_markup=get_main_kb(), parse_mode="Markdown")
    except:
        pass

# --- ОБРАБОТЧИКИ ---

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    global participants, is_collecting
    participants = []
    is_collecting = True
    await message.answer("⚽️ **СБОР ОТКРЫТ!**", reply_markup=get_main_kb(), parse_mode="Markdown")

@dp.callback_query(F.data == "toggle_reg")
async def callback_toggle(callback: types.CallbackQuery):
    if not is_collecting:
        await callback.answer("⚠️ Сбор уже закрыт!", show_alert=True)
        return
        
    user_name = callback.from_user.full_name
    if user_name in participants:
        participants.remove(user_name)
        await callback.answer("❌ Выписан")
    else:
        participants.append(user_name)
        await callback.answer("✅ Записан!")
    await update_main_post(callback.message)

@dp.message(F.text == "+")
async def handle_plus(message: types.Message):
    # Если сбор закрыт, бот просто игнорирует плюсики
    if not is_collecting:
        return
        
    user_name = message.from_user.full_name
    if user_name not in participants:
        participants.append(user_name)
        try:
            await message.delete() # Удаляем плюс игрока для чистоты
        except:
            pass
        # Чтобы обновить главное сообщение, нам нужно знать его ID. 
        # В этой версии для простоты просто шлем подтверждение в личку или уведомлением, 
        # либо игрок увидит обновление счетчика, если сам нажмет кнопку.
        # Но лучше всего приучить игроков жать кнопку.

@dp.callback_query(F.data == "stop_collect")
async def stop_collect(callback: types.CallbackQuery):
    global is_collecting
    is_collecting = False
    await update_main_post(callback.message)
    await callback.answer("🚫 Запись остановлена", show_alert=True)

@dp.callback_query(F.data == "show_list")
async def callback_show_list(callback: types.CallbackQuery):
    if not participants:
        await callback.answer("Список пуст", show_alert=True)
    else:
        names = "\n".join([f"{i+1}. {p}" for i, p in enumerate(participants)])
        await callback.answer(f"📋 СПИСОК:\n\n{names}", show_alert=True)

# --- ЛОГИКА ДЕЛЕНИЯ ---

@dp.callback_query(F.data == "ask_limit")
async def ask_limit(callback: types.CallbackQuery):
    if len(participants) < 2:
        await callback.answer("Мало людей!", show_alert=True)
        return
    builder = InlineKeyboardBuilder()
    for i in range(4, 9):
        builder.button(text=f"По {i}", callback_data=f"slim_{i}")
    builder.adjust(2)
    await callback.message.answer("Сколько человек в ОДНОЙ команде?", reply_markup=builder.as_markup())

@dp.callback_query(F.data.startswith("slim_"))
async def set_lim(callback: types.CallbackQuery):
    global temp_limit
    temp_limit = int(callback.data.split("_")[1])
    builder = InlineKeyboardBuilder()
    for i in range(2, 5):
        builder.button(text=f"{i} команды", callback_data=f"split_{i}")
    builder.adjust(1)
    await callback.message.edit_text(f"Лимит: {temp_limit}. Сколько команд?", reply_markup=builder.as_markup())

@dp.callback_query(F.data.startswith("split_"))
async def do_split(callback: types.CallbackQuery):
    num_teams = int(callback.data.split("_")[1])
    total_slots = num_teams * temp_limit
    
    main_roster = list(participants[:total_slots])
    bench = list(participants[total_slots:])
    random.shuffle(main_roster)
    
    teams = [[] for _ in range(num_teams)]
    for i, p in enumerate(main_roster):
        teams[i % num_teams].append(p)
    
    res = f"📋 **ИТОГИ ({num_teams} команды по {temp_limit})**\n\n"
    for i, t in enumerate(teams):
        res += f"👕 **Команда {i+1}:**\n" + "\n".join([f"• {p}" for p in t]) + "\n\n"
    
    if bench:
        res += "🔄 **ЗАМЕНА:**\n" + "\n".join([f"• {p}" for p in bench])
    
    await callback.message.answer(res, parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data == "reset")
async def reset(callback: types.CallbackQuery):
    global participants, is_collecting
    participants = []
    is_collecting = True # При сбросе открываем сбор заново
    await update_main_post(callback.message)
    await callback.answer("Сбор обнулен и открыт заново")

async def handle(request): return web.Response(text="ok")

async def main():
    app = web.Application()
    app.router.add_get("/", handle)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', int(os.environ.get("PORT", 10000)))
    await site.start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

