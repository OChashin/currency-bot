import logging
import os
import aiohttp
import asyncio
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import Command
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage

# 🔹 Твой API-токен бота
API_TOKEN = "Your_Token"
CURRENCY_API_KEY = "Your API KEY"  # 🔹 Вставь свой API-ключ от FreeCurrencyAPI
CURRENCY_API_URL = f"https://api.freecurrencyapi.com/v1/latest?apikey={CURRENCY_API_KEY}"

# 🔹 Инициализация бота
bot = Bot(token=API_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=MemoryStorage())

# 🔹 Логирование
logging.basicConfig(level=logging.INFO)

# 🔹 Клавиатура выбора валют
currency_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="USD"), KeyboardButton(text="EUR"), KeyboardButton(text="GBP")],
        [KeyboardButton(text="JPY"), KeyboardButton(text="UAH"), KeyboardButton(text="CNY")]
    ],
    resize_keyboard=True
)

# 🔹 Храним любимые валюты пользователей
user_favorites = {}


# 🔹 Команда /start
@dp.message(Command("start"))
async def start(message: types.Message):
    await message.answer("👋 Привет! Я бот для конвертации валют. Выбери валюту:", reply_markup=currency_keyboard)


# 🔹 Команда /help
@dp.message(Command("help"))
async def help_command(message: types.Message):
    text = """
📌 <b>Список команд:</b>
/convert 100 USD to EUR — конвертировать валюту  
/graph USD EUR — график курса за 10 дней  
/rates USD — текущие курсы для валюты  
/favorite USD EUR — сохранить любимую пару  
/myfavorite — конвертировать любимую пару  
/help — справка по командам  
"""
    await message.answer(text)


# 🔹 Конвертация валют
@dp.message(Command("convert"))
async def convert_currency(message: types.Message):
    try:
        _, amount, from_currency, _, to_currency = message.text.split()
        amount = float(amount)

        async with aiohttp.ClientSession() as session:
            async with session.get(f"{CURRENCY_API_URL}&base_currency={from_currency}") as response:
                data = await response.json()

        rates = data.get("data", {})
        if to_currency in rates:
            result = amount * rates[to_currency]
            await message.answer(f"💱 {amount} {from_currency} = {result:.2f} {to_currency}")
        else:
            await message.answer("❌ Ошибка при конвертации. Проверьте валюты.")
    except Exception:
        await message.answer("⚠️ Неверный формат! Пример: /convert 100 USD to EUR")


# 🔹 Получение графика курса
@dp.message(Command("graph"))
async def graph_currency(message: types.Message):
    try:
        _, from_currency, to_currency = message.text.split()

        end_date = datetime.today().strftime('%Y-%m-%d')
        start_date = (datetime.today() - timedelta(days=10)).strftime('%Y-%m-%d')

        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://api.freecurrencyapi.com/v1/historical?apikey={CURRENCY_API_KEY}&base_currency={from_currency}&date_from={start_date}&date_to={end_date}") as response:
                data = await response.json()

        if "data" not in data:
            await message.answer("❌ Ошибка при получении данных.")
            return

        rates = data["data"]
        dates, values = zip(*sorted((date, rates[date].get(to_currency, 0)) for date in rates))

        plt.figure(figsize=(8, 4))
        plt.plot(dates, values, marker='o', linestyle='-', color='b', label=f"{from_currency} → {to_currency}")
        plt.xlabel("Дата")
        plt.ylabel("Курс")
        plt.title(f"📊 Курс {from_currency} к {to_currency} за 10 дней")
        plt.xticks(rotation=45)
        plt.legend()
        plt.grid()

        graph_path = f"graph_{from_currency}_{to_currency}.png"
        plt.savefig(graph_path)
        plt.close()

        await message.answer_photo(open(graph_path, "rb"))
        os.remove(graph_path)
    except Exception:
        await message.answer("⚠️ Ошибка! Используй формат: /graph USD EUR")


# 🔹 Получение всех курсов для валюты
@dp.message(Command("rates"))
async def get_rates(message: types.Message):
    try:
        _, base_currency = message.text.split()

        async with aiohttp.ClientSession() as session:
            async with session.get(f"{CURRENCY_API_URL}&base_currency={base_currency}") as response:
                data = await response.json()

        rates = data.get("data", {})
        if not rates:
            await message.answer("❌ Ошибка при получении курсов валют.")
            return

        text = f"💹 <b>Курсы валют для {base_currency}:</b>\n"
        for currency, rate in sorted(rates.items()):
            text += f"🔸 {currency}: {rate:.2f}\n"

        await message.answer(text)
    except Exception:
        await message.answer("⚠️ Ошибка! Используй формат: /rates USD")


# 🔹 Сохранение любимой валюты
@dp.message(Command("favorite"))
async def favorite_currency(message: types.Message):
    user_id = message.from_user.id
    try:
        _, from_currency, to_currency = message.text.split()
        user_favorites[user_id] = (from_currency, to_currency)
        await message.answer(f"⭐ Твоя любимая валютная пара сохранена: {from_currency} → {to_currency}")
    except Exception:
        await message.answer("⚠️ Используй формат: /favorite USD EUR")


# 🔹 Конвертация любимой валюты
@dp.message(Command("myfavorite"))
async def my_favorite_currency(message: types.Message):
    user_id = message.from_user.id
    if user_id in user_favorites:
        from_currency, to_currency = user_favorites[user_id]
        await convert_currency(types.Message(text=f"/convert 1 {from_currency} to {to_currency}"))
    else:
        await message.answer("⚠️ Ты не сохранил любимую валютную пару! Используй /favorite")


# 🔹 Обработка кнопок клавиатуры
@dp.message(lambda message: message.text in ["USD", "EUR", "GBP", "JPY", "UAH", "CNY"])
async def handle_currency_choice(message: types.Message):
    await message.answer(f"Ты выбрал {message.text}. Теперь введи сумму и вторую валюту.\nПример: /convert 100 {message.text} to EUR")


# 🔹 Запуск бота (для aiogram 3.7.0)
async def main():
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
