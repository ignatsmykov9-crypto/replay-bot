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
    Update,
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

# ================== ССЫЛКИ ==================
LINK_YOUTUBE = "https://www.youtube.com/@sereGGa"
LINK_TWITCH = "https://www.twitch.tv/etoseregga"
LINK_VK = "https://vk.ru/etoseregga"
LINK_BOOSTY = "https://boosty.to/sereggaotec"
LINK_TELEGRAM = "https://t.me/sereggabets"
LINK_FOOTBALL = "https://t.me/stoparikfootball"
LINK_REVIEW = "https://boosty.to/sereggaotec/purchase/3086351"

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

# ================== КЛАВИАТУРЫ ==================
main_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📂 Мои ссылки")],
        [KeyboardButton(text="⚽ Футбол"), KeyboardButton(text="🎯 Отдельный разбор")],
        [KeyboardButton(text="📥 Скинуть реплей")],
    ],
    resize_keyboard=True,
)

links_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="▶️ YouTube"), KeyboardButton(text="🟣 Twitch")],
        [KeyboardButton(text="🔵 VK"), KeyboardButton(text="🟠 Boosty")],
        [KeyboardButton(text="✈️ Telegram")],
        [KeyboardButton(text="⬅️ Назад")],
    ],
    resize_keyboard=True,
)

back_keyboard = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="⬅️ Назад")]],
    resize_keyboard=True,
)

cancel_keyboard = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="❌ Отмена")]],
    resize_keyboard=True,
)

# ================== ХЕНДЛЕРЫ ==================

# /start — главное меню
@dp.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "Здаров бандит\n"
        "Все что интересно ниже",
        reply_markup=main_keyboard,
    )


# ===== РАЗДЕЛ «МОИ ССЫЛКИ» =====
@dp.message(F.text == "📂 Мои ссылки")
async def open_links(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "Выбирай, куда перейти:",
        reply_markup=links_keyboard,
    )


@dp.message(F.text == "▶️ YouTube")
async def link_youtube(message: Message):
    await message.answer(f"▶️ YouTube:\n{LINK_YOUTUBE}", reply_markup=back_keyboard)


@dp.message(F.text == "🟣 Twitch")
async def link_twitch(message: Message):
    await message.answer(f"🟣 Twitch:\n{LINK_TWITCH}", reply_markup=back_keyboard)


@dp.message(F.text == "🔵 VK")
async def link_vk(message: Message):
    await message.answer(f"🔵 VK:\n{LINK_VK}", reply_markup=back_keyboard)


@dp.message(F.text == "🟠 Boosty")
async def link_boosty(message: Message):
    await message.answer(f"🟠 Boosty:\n{LINK_BOOSTY}", reply_markup=back_keyboard)


@dp.message(F.text == "✈️ Telegram")
async def link_telegram(message: Message):
    await message.answer(f"✈️ Telegram:\n{LINK_TELEGRAM}", reply_markup=back_keyboard)


# ===== РАЗДЕЛ «ФУТБОЛ» =====
@dp.message(F.text == "⚽ Футбол")
async def open_football(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        f"⚽ Футбольный клуб:\n{LINK_FOOTBALL}",
        reply_markup=back_keyboard,
    )


# ===== РАЗДЕЛ «ОТДЕЛЬНЫЙ РАЗБОР» =====
@dp.message(F.text == "🎯 Отдельный разбор")
async def open_review(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        f"🎯 Отдельный разбор твоего реплея:\n{LINK_REVIEW}",
        reply_markup=back_keyboard,
    )


# ===== КНОПКА «НАЗАД» =====
@dp.message(F.text == "⬅️ Назад")
async def go_back(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "Главное меню:",
        reply_markup=main_keyboard,
    )


# ===== РАЗДЕЛ «СКИНУТЬ РЕПЛЕЙ» =====
@dp.message(F.text == "📥 Скинуть реплей")
async def start_replay(message: Message, state: FSMContext):
    await state.clear()
    await state.set_state(Form.match_id)
    await message.answer(
        "Введи ID матча (только цифры):",
        reply_markup=cancel_keyboard,
    )


# Отмена — возврат в главное меню
@dp.message(F.text == "❌ Отмена")
async def cancel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "Отменено. Если захочешь скинуть реплей — нажми кнопку ниже.",
        reply_markup=main_keyboard,
    )


# ШАГ 1: ID матча
@dp.message(Form.match_id)
async def process_match_id(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("❌ Только цифры. Попробуй снова:")
        return
    await state.update_data(match_id=message.text)
    await state.set_state(Form.reason)
    await message.answer("Почему именно этот реплей?")


# ШАГ 2: Причина
@dp.message(Form.reason)
async def process_reason(message: Message, state: FSMContext):
    await state.update_data(reason=message.text)
    await state.set_state(Form.hero)
    await message.answer("На ком ты играл?")


# ШАГ 3: Герой → запись в таблицу
@dp.message(Form.hero)
async def process_hero(message: Message, state: FSMContext):
    data = await state.get_data()
    now = datetime.now()

    username = message.from_user.username
    if username:
        user_field = "@" + username
    else:
        user_field = str(message.from_user.id)

    try:
        sheet.append_row([
            now.strftime("%Y-%m-%d %H:%M:%S"),
            data["match_id"],
            data["reason"],
            message.text,
            user_field,
        ])
        await message.answer(
            "✅ Ну вот и всё, посмотрим что у тебя там\n\n"
            "Хочешь скинуть ещё один реплей?",
            reply_markup=main_keyboard,
        )
    except Exception as e:
        logging.error(f"Sheets error: {e}")
        await message.answer("❌ Ошибка", reply_markup=main_keyboard)

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


async def health_check(request):
    return web.Response(text="OK")


async def main():
    logging.basicConfig(level=logging.INFO)
    app = web.Application()
    app.router.add_post(WEBHOOK_PATH, handle_webhook)
    app.router.add_get("/health", health_check)
    app.on_startup.append(on_startup)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    logging.info(f"Server started on port {PORT}")

    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())
