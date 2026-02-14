import os
import asyncio
import json
import random
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import WebAppInfo, ReplyKeyboardRemove
from aiohttp import web

# --- НАСТРОЙКИ ---
TOKEN = os.getenv("BOT_TOKEN")
# URL вашего приложения на Render (например: mybot.onrender.com)
APP_URL = os.getenv("RENDER_EXTERNAL_HOSTNAME", "localhost") 

bot = Bot(token=TOKEN)
dp = Dispatcher()
logging.basicConfig(level=logging.INFO)

# Состояние
is_collecting = False
participants = []
temp_limit = 5

# --- HTML ИНТЕРФЕЙСА (Web App) ---
HTML_CONTENT = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
               background: #1c1c1e; color: white; padding: 20px; margin: 0; }
        .header { text-align: center; margin-bottom: 20px; }
        .player-item { background: #2c2c2e; padding: 12px; border-radius: 10px; 
                      margin-bottom: 8px; display: flex; justify-content: space-between; }
        .num { color: #0a84ff; font-weight: bold; margin-right: 10px; }
        button { background: #0a84ff; color: white; border: none; padding: 15px; 
                border-radius: 12px; width: 100%; font-size: 16px; font-weight: 600; cursor: pointer; }
        .empty { text-align: center; color: #8e8e93; margin: 40px 0; }
    </style>
</head>
<body>
    <div class="header">
        <h2 id="title">Загрузка...</h2>
    </div>
    <button id="mainBtn" onclick="toggleReg()">ЗАПИСАТЬСЯ</button>
    <div id="playerList"></div>

    <script>
        let tg = window.Telegram.WebApp;
        tg.expand();
        
        const urlParams = new URLSearchParams(window.location.search);
        let players = JSON.parse(urlParams.get("players") || "[]");
        let userName = tg.initDataUnsafe.user ? tg.initDataUnsafe.user.first_name : "Игрок";

        function render() {
            document.getElementById('title').innerText = "Записано: " + players.length;
            const listDiv = document.getElementById('playerList');
            if (players.length === 0) {
                listDiv.innerHTML = '<div class="empty">Пока никого нет. Будь первым!</div>';
            } else {
                listDiv.innerHTML = players.map((p, i) => 
                    `<div class="player-item"><span><span class="num">${i+1}.</span>${p}</span></div>`
                ).join('');
            }
            
            const btn = document.getElementById('mainBtn');
            if (players.includes(userName)) {
                btn.innerText = "❌ ВЫПИСАТЬСЯ";
                btn.style.background = "#ff453a";
            } else {
                btn.innerText = "✅ ЗАПИСАТЬСЯ";
                btn.style.background = "#30d158";
            }
        }

        function toggleReg() {
            tg.sendData(JSON.stringify({user: userName}));
            tg.close();
        }
        render();
    </script>
</body>
</html>
"""

# --- ВЕБ-СЕРВЕР ---
async def handle_gui(request):
    return web.Response(text=HTML_CONTENT, content_type='text/html')

async def handle_ping(request):
    return web.Response(text="alive")

async def start_web_server():
    app = web.Application()
    app.router.add_get("/", handle_ping)
    app.router.add_get("/gui", handle_gui)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 10000))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()

# --- ЛОГИКА БОТА ---

def get_main_kb():
    builder = InlineKeyboardBuilder()
    # Передаем список игроков прямо в URL, чтобы Web App его отобразил
    encoded_players = json.dumps(participants)
    web_app_url = f"https://{APP_URL}/gui?players={encoded_players}"
    
    builder.button(text="📱 Список / Записаться", web_app=WebAppInfo(url=web_app_url))
    builder.button(text="🛡 Поделить", callback_data="ask_limit")
    builder.button(text="♻️ Сброс", callback_data="reset")
    builder.adjust(1)
    return builder.as_markup()

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    global is_collecting, participants
    is_collecting = True
    participants = []
    await message.answer(
        "⚽️ **СБОР НА ИГРУ ОТКРЫТ!**\n\nИспользуй кнопку ниже для записи. Список теперь внутри приложения!",
        reply_markup=get_main_kb(),
        parse_mode="Markdown"
    )

# Когда Web App закрывается и присылает данные
@dp.message(F.content_type == "web_app_data")
async def web_app_receive(message: types.Message):
    global participants
    data = json.loads(message.web_app_data.data)
    user = data['user']
    
    if user in participants:
        participants.remove(user)
        msg = f"❌ {user} выписался."
    else:
        participants.append(user)
        msg = f"✅ {user} записался!"
    
    # Удаляем сервисное сообщение от Web App и присылаем подтверждение
    await message.delete()
    confirm = await message.answer(f"{msg}\nВсего: {len(participants)}", reply_markup=get_main_kb())
    
    # Через 5 секунд удаляем уведомление, чтобы чат был чистым
    await asyncio.sleep(5)
    await confirm.delete()

# Остальная логика деления (лимиты и т.д.)
@dp.callback_query(F.data == "ask_limit")
async def ask_limit(callback: types.CallbackQuery):
    builder = InlineKeyboardBuilder()
    for i in range(4, 8):
        builder.button(text=f"По {i}", callback_data=f"set_lim_{i}")
    builder.adjust(2)
    await callback.message.answer("По сколько человек в команде?", reply_markup=builder.as_markup())
    await callback.answer()

@dp.callback_query(F.data.startswith("set_lim_"))
async def set_lim(callback: types.CallbackQuery):
    global temp_limit
    temp_limit = int(callback.data.split("_")[2])
    builder = InlineKeyboardBuilder()
    for i in range(2, 5):
        builder.button(text=f"На {i} команды", callback_data=f"split_{i}")
    builder.adjust(1)
    await callback.message.edit_text(f"Лимит: {temp_limit}. На сколько команд делим?", reply_markup=builder.as_markup())

@dp.callback_query(F.data.startswith("split_"))
async def do_split(callback: types.CallbackQuery):
    num_teams = int(callback.data.split("_")[1])
    
    temp_list = list(participants)
    random.shuffle(temp_list)
    
    total_slots = num_teams * temp_limit
    main = temp_list[:total_slots]
    bench = temp_list[total_slots:]
    
    teams = [[] for _ in range(num_teams)]
    for i, p in enumerate(main):
        teams[i % num_teams].append(p)
    
    res = "📋 **РЕЗУЛЬТАТЫ:**\n\n"
    for i, t in enumerate(teams):
        res += f"👕 Команда {i+1}:\n" + "\n".join([f"• {p}" for p in t]) + "\n\n"
    
    if bench:
        res += "🔄 Замена:\n" + "\n".join([f"• {p}" for p in bench])
        
    await callback.message.answer(res)
    await callback.answer()

@dp.callback_query(F.data == "reset")
async def reset(callback: types.CallbackQuery):
    global participants
    participants = []
    await callback.message.answer("Список очищен")
    await callback.answer()

async def main():
    # Запускаем и сервер, и бота одновременно
    await asyncio.gather(start_web_server(), dp.start_polling(bot))

if __name__ == "__main__":
    asyncio.run(main())
