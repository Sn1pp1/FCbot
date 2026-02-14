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

# --- СОЗДАНИЕ КЛАВИАТУРЫ ---
def get_main_kb():
    builder = InlineKeyboardBuilder()
    builder.button(text="➕ Записаться / Выписаться", callback_data="toggle_reg")
    builder.button(text="📋 Кто записан?", callback_data="show_list")
    builder.button(text="🛡 Поделить команды", callback_data="ask_limit")
    builder.button(text="♻️ Сброс", callback_data="reset")
    # Располагаем кнопки в один столбец для удобства на телефонах
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
    except Exception as e:
        logging.error(f"Ошибка при обновлении поста: {e}")

# --- ОБРАБОТЧИКИ СОБЫТИЙ ---

# Команда /start
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

# Обработка записи и выписки (одной кнопкой)
@dp.callback_query(F.data == "toggle_reg")
async def callback_toggle(callback: types.CallbackQuery):
    user_name = callback.from_user.full_name
    
    if user_name in participants:
        participants.remove(user_name)
        # show_alert=False создает маленькую плашку сверху экрана
        await callback.answer(f"❌ {user_name}, вы выписались", show_alert=False)
    else:
        participants.append(user_name)
        await callback.answer(f"✅ {user_name}, вы записаны!", show_alert=False)
    
    # Обновляем текст основного сообщения со счетчиком
    await update_main_post(callback.message)

# Показ списка участников во всплывающем окне (Alert)
@dp.callback_query(F.data == "show_list")
async def callback_show_list(callback: types.CallbackQuery):
    if not participants:
        await callback.answer("Список пока пуст! Будь первым! 🏃‍♂️", show_alert=True)
    else:
        names_list = "\n".join([f"{i+1}. {name}" for i, name in enumerate(participants)])
        # show_alert=True создает окно с кнопкой "ОК"
        await callback.answer(f"📋 ТЕКУЩИЙ СОСТАВ:\n\n{names_list}", show_alert=True)

# Очистка списка
@dp.callback_query(F.data == "reset")
async def callback_reset(callback: types.CallbackQuery):
    global participants
    participants = []
    await update_main_post(callback.message)
    await callback.answer("🗑 Список полностью очищен", show_alert=False)

# Быстрое деление на 2 команды
@dp.callback_query(F.data == "ask_limit")
async def ask_limit(callback: types.CallbackQuery):
    if len(participants) < 2:
        await callback.answer("⚠️ Нужно хотя бы 2 человека для деления!", show_alert=True)
        return
    
    # Копируем и перемешиваем список
    temp_list = list(participants)
    random.shuffle(temp_list)
    
    # Делим пополам
    mid = len(temp_list) // 2
    team1 = temp_list[:mid]
    team2 = temp_list[mid:]
    
    res = (
        "📋 **РЕЗУЛЬТАТ ЖЕРЕБЬЕВКИ**\n\n"
        "👕 **Команда 1:**\n" + "\n".join([f"• {p}" for p in team1]) + "\n\n"
        "👕 **Команда 2:**\n" + "\n".join([f"• {p}" for p in team2])
    )
    
    await callback.message.answer(res, parse_mode="Markdown")
    await callback.answer()

# --- ВЕБ-СЕРВЕР ДЛЯ RENDER ---
async def handle(request):
    return web.Response(text="Бот активен и работает!")

async def main():
    # Настройка сервера
    app = web.Application()
    app.router.add_get("/", handle)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 10000))
    site = web.TCPSite(runner, '0.0.0.0', port)
    
    # Запуск сервера и бота параллельно
    await site.start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Бот остановлен")
