import asyncio
import logging
import random
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import ReplyKeyboardBuilder

TOKEN = "8305924362:AAGtvSHflfwn51wTwtqNw_Kf1v_Rbpp65iQ"
TRIGGER_PHRASE = "+"
participants = set()

bot = Bot(token=TOKEN)
dp = Dispatcher()
logging.basicConfig(level=logging.INFO)

# 1. Начальное меню (только кнопка Старт)
def get_start_keyboard():
    builder = ReplyKeyboardBuilder()
    builder.button(text="🚀 Запустить сбор")
    return builder.as_markup(resize_keyboard=True)

# 2. Основное рабочее меню
def get_main_keyboard():
    builder = ReplyKeyboardBuilder()
    builder.button(text="+")
    builder.button(text="🛡 Поделить на команды")
    builder.button(text="♻️ Сброс")
    builder.adjust(1, 2)
    return builder.as_markup(resize_keyboard=True)

# Обработка команды /start
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "Привет! Нажми на кнопку ниже, чтобы открыть панель управления сбором.",
        reply_markup=get_start_keyboard()
    )

# Обработка нажатия кнопки "Запустить сбор"
@dp.message(F.text == "🚀 Запустить сбор")
async def open_menu(message: types.Message):
    await message.answer(
        "Меню открыто! Инструкция:\n1. Участники нажимают '+'\n2. Нажми 'Поделить', когда все соберутся.",
        reply_markup=get_main_keyboard()
    )

# Регистрация участника
@dp.message(F.text == TRIGGER_PHRASE)
async def register_participant(message: types.Message):
    user_name = message.from_user.full_name
    if user_name not in participants:
        participants.add(user_name)
        await message.reply(f"✅ {user_name} в списке! Всего: {len(participants)}")
    else:
        await message.reply("Вы уже записаны.")

# Деление на команды
@dp.message(F.text == "🛡 Поделить на команды")
async def divide_teams(message: types.Message):
    if len(participants) < 2:
        await message.answer("Нужно хотя бы 2 человека для игры!")
        return

    players_list = list(participants)
    random.shuffle(players_list)

    mid = len(players_list) // 2
    team1 = players_list[:mid]
    team2 = players_list[mid:]

    res = (
        f"⚔️ **КОМАНДА 1 ({len(team1)}):**\n" + "\n".join([f"👤 {p}" for p in team1]) +
        f"\n\n🛡 **КОМАНДА 2 ({len(team2)}):**\n" + "\n".join([f"👤 {p}" for p in team2])
    )
    await message.answer(res, parse_mode="Markdown")

# Сброс списка
@dp.message(F.text == "♻️ Сброс")
async def reset_list(message: types.Message):
    participants.clear()
    await message.answer("Список очищен. Жду новых участников!")

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())