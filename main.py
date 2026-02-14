import os
import asyncio
import random
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiohttp import web

# --- НАСТРОЙКИ ---
TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(token=TOKEN)
dp = Dispatcher()
logging.basicConfig(level=logging.INFO)

# Глобальные переменные
participants = []
is_collecting = False
temp_limit = 5 # Временная переменная для хранения выбранного лимита

# --- КЛАВИАТУРА ГЛАВНОГО ПОСТА ---
def get_main_kb():
    builder = InlineKeyboardBuilder()
    builder.button(text="➕ Записаться / Выписаться", callback_data="toggle_reg")
    builder.button(text="📋 Кто записан?", callback_data="show_list")
    builder.button(text="🛡 Поделить команды", callback_data="ask_limit")
    builder.button(text="♻️ Сброс", callback_data="reset")
    builder.adjust(1)
    return builder.as_markup()

# --- ФУНКЦИЯ ОБНОВЛЕНИЯ ГЛАВНОГО СООБЩЕНИЯ ---
async def update_main_post(message: types.Message):
    text = (
        f"⚽️ **СБОР НА ИГРУ ОТКРЫТ!**\n\n"
        f"📈 Записано игроков: **{len(participants)}**\n\n"
        f"Нажми кнопку ниже, чтобы добавиться в состав или посмотреть список участников."
    )
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
    await message.answer(
        f"⚽️ **СБОР НА ИГРУ ОТКРЫТ!**\n\n📈 Записано игроков: **0**",
        reply_markup=get_main_kb(),
        parse_mode="Markdown"
    )

@dp.callback_query(F.data == "toggle_reg")
async def callback_toggle(callback: types.CallbackQuery):
    user_name = callback.from_user.full_name
    if user_name in participants:
        participants.remove(user_name)
        await callback.answer(f"❌ {user_name}, вы выписались", show_alert=False)
    else:
        participants.append(user_name)
        await callback.answer(f"✅ {user_name}, вы записаны!", show_alert=False)
    await update_main_post(callback.message)

@dp.callback_query(F.data == "show_list")
async def callback_show_list(callback: types.CallbackQuery):
    if not participants:
        await callback.answer("Список пока пуст!", show_alert=True)
    else:
        names_list = "\n".join([f"{i+1}. {name}" for i, name in enumerate(participants)])
        await callback.answer(f"📋 ТЕКУЩИЙ СОСТАВ:\n\n{names_list}", show_alert=True)

# --- ЛОГИКА ДЕЛЕНИЯ (ШАГ 1: ВЫБОР ЛИМИТА) ---
@dp.callback_query(F.data == "ask_limit")
async def ask_limit(callback: types.CallbackQuery):
    if len(participants) < 2:
        await callback.answer("⚠️ Нужно хотя бы 2 человека!", show_alert=True)
        return
    
    builder = InlineKeyboardBuilder()
    for i in range(4, 9): # Кнопки от 4 до 8 человек в команде
        builder.button(text=f"По {i} чел.", callback_data=f"set_lim_{i}")
    builder.adjust(2)
    await callback.message.answer("Шаг 1: Выбери лимит (сколько человек в ОДНОЙ команде):", reply_markup=builder.as_markup())
    await callback.answer()

# --- ЛОГИКА ДЕЛЕНИЯ (ШАГ 2: КОЛИЧЕСТВО КОМАНД) ---
@dp.callback_query(F.data.startswith("set_lim_"))
async def set_lim(callback: types.CallbackQuery):
    global temp_limit
    temp_limit = int(callback.data.split("_")[2])
    
    builder = InlineKeyboardBuilder()
    for i in range(2, 5): # Кнопки на 2, 3 или 4 команды
        builder.button(text=f"{i} команды", callback_data=f"split_{i}")
    builder.adjust(1)
    
    await callback.message.edit_text(
        f"Выбран лимит: **{temp_limit} чел. в команде**.\nШаг 2: На сколько команд делим?",
        reply_markup=builder.as_markup(),
        parse_mode="Markdown"
    )
    await callback.answer()

# --- ЛОГИКА ДЕЛЕНИЯ (ФИНАЛ: РАСЧЕТ) ---
@dp.callback_query(F.data.startswith("split_"))
async def do_split(callback: types.CallbackQuery):
    num_teams = int(callback.data.split("_")[1])
    
    # 1. Берем копию списка, чтобы не испортить основной
    all_players = list(participants)
    
    # 2. Рассчитываем общее кол-во мест
    total_slots = num_teams * temp_limit
    
    # 3. Отделяем основу от замены (по порядку записи!)
    main_roster = all_players[:total_slots]
    bench = all_players[total_slots:]
    
    # 4. Перемешиваем только тех, кто попал в основу
    random.shuffle(main_roster)
    
    # 5. Распределяем по командам
    teams = [[] for _ in range(num_teams)]
    for i, p in enumerate(main_roster):
        teams[i % num_teams].append(p)
    
    # 6. Формируем красивый текст
    res = f"📋 **ИТОГИ ЖЕРЕБЬЕВКИ ({num_teams} команды по {temp_limit} чел.)**\n\n"
    
    for i, t in enumerate(teams):
        res += f"👕 **Команда {i+1}:**\n" + "\n".join([f"• {p}" for p in t]) + "\n\n"
    
    if bench:
        res += "🔄 **ЗАМЕНА / ОЧЕРЕДЬ:**\n" + "\n".join([f"• {p}" for p in bench])
    
    await callback.message.answer(res, parse_mode="Markdown")
    await callback.answer()

# --- ОСТАЛЬНОЕ ---
@dp.callback_query(F.data == "reset")
async def callback_reset(callback: types.CallbackQuery):
    global participants
    participants = []
    await update_main_post(callback.message)
    await callback.answer("🗑 Список очищен")

async def handle(request): return web.Response(text="alive")

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
