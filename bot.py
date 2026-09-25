import asyncio
import json
import logging
import os
from datetime import datetime

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    Message,
    ReplyKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardRemove,
)
from aiohttp import web
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# ================== НАСТРОЙКИ ==================
BOT_TOKEN = os.environ.get("BOT_TOKEN")
SHEET_ID = "1CUxQ-vv-MpeMEFdOV5me6KYUTqD6CGrEaZ1fesGRLyc"
SHEET_NAME = "Лист1"
WEBHOOK_PATH = "/webhook"
PORT = int(os.environ.get("PORT", 8080))

# ================== GOOGLE SHEETS ==================
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]
creds_dict = json.loads(os.environ.get("GOOGLE_CREDENTIALS", "{}"))
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
gs_client = gspread.authorize(creds)
sheet = gs_client.open_by_key(SHEET_ID).worksheet(SHEET_NAME)

# ================== БОТ ==================
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ================== FSM ==================
class Form(StatesGroup):
    match_id = State()
    reason = State()
    hero = State()

# ================== КЛАВИАТУРА ==================
start_keyboard = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="🔄 Начать заново")]],
    resize_keyboard=True,
)

# ================== ХЕНДЛЕРЫ ==================
@dp.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    await state.set_state(Form.match_id)
    await message.answer(
        "Привет! 👋\n\nВведи ID матча (только цифры):",
        reply_markup=start_keyboard,
    )


@dp.message(F.text == "🔄 Начать заново")
async def restart(message: Message, state: FSMContext):
    await state.clear()
    await state.set_state(Form.match_id)
    await message.answer("Начинаем заново!\n\nВведи ID матча (только цифры):")


@dp.message(Form.match_id)
async def process_match_id(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("❌ Только цифры. Попробуй снова:")
        return
    await state.update_data(match_id=message.text)
    await state.set_state(Form.reason)
    await message.answer("Почему именно этот реплей?")


@dp.message(Form.reason)
async def process_reason(message: Message, state: FSMContext):
    await state.update_data(reason=message.text)
    await state.set_state(Form.hero)
    await message.answer("На ком ты играл?")


@dp.message(Form.hero)
async def process_hero(message: Message, state: FSMContext):
    data = await state.get_data()
    telegram_id = message.from_user.id
    now = datetime.now()

    try:
        sheet.append_row([
            now.strftime("%Y-%m-%d %H:%M:%S"),
            data["match_id"],
            data["reason"],
            message.text,
            telegram_id,
        ])
        await message.answer(
            "✅ Запись добавлена в таблицу!\n\nЧтобы начать заново — нажми кнопку ниже или введи /start.",
            reply_markup=start_keyboard,
        )
    except Exception as e:
        logging.error(f"Sheets error: {e}")
        await message.answer("❌ Ошибка записи в таблицу. Попробуй позже.")

    await state.clear()


# ================== WEBHOOK ==================
async def on_startup(app):
    webhook_url = os.environ.get("WEBHOOK_URL", "")
    if webhook_url:
        await bot.set_webhook(webhook_url + WEBHOOK_PATH)
        logging.info(f"Webhook set to {webhook_url + WEBHOOK_PATH}")


async def handle_webhook(request):
    try:
        data = await request.json()
        update = Update.model_validate(data, context={"bot": bot})
        await dp.feed_update(bot, update)
    except Exception as e:
        logging.error(f"Update error: {e}")
    return web.Response(text="OK")


async def main():
    logging.basicConfig(level=logging.INFO)
    app = web.Application()
    app.router.add_post(WEBHOOK_PATH, handle_webhook)
    app.on_startup.append(on_startup)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    logging.info(f"Server started on port {PORT}")

    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())
