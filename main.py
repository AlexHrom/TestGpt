import aiohttp
import openai
from aiogram import Bot, types
from aiogram.dispatcher import Dispatcher
from aiogram.utils import executor
import json
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
import logging
import io
from aiogram.types import InputFile
import asyncio
import time

file = open('config.json', 'r')
config = json.load(file)

openai.api_key = config['openai']
bot = Bot(config['token'])
dp = Dispatcher(bot)

chat_storage = {}
timestamps = {}

messages = [
    {"role": "system", "content": "You are AI-powered assistant in Telegram connected via Bot API, your creator is @AleksFolt."},
    {"role": "user", "content": "Привет"}
]


def update(messages, role, content):
    messages.append({"role": role, "content": content})
    return messages


@dp.message_handler(commands=['chatgpt'])
async def start_chatting(message: types.Message):
    chat_id = message.chat.id
    if chat_id not in chat_storage:
        chat_storage[chat_id] = []
    if chat_id not in timestamps:
        timestamps[chat_id] = []

    # Отправляем сообщение пользователю с инструкцией
    await message.answer("Теперь отправьте мне ваш запрос")

    # Регистрируем обработчик для дальнейших сообщений пользователя
    @dp.message_handler(chat_id=chat_id)
    async def continue_chatting(message: types.Message):
        # Обновляем историю сообщений пользователя
        chat_id = message.chat.id
        update(chat_storage[chat_id], "user", message.text)

        # Проверяем, если превышен лимит запросов
        if is_request_limit_exceeded(chat_id):
            await message.answer("Извините за минуту можно делать только три вопроса")
            return

        # Отправляем сообщение с уведомлением, что запрос обрабатывается
        sent_message = await message.answer("ChatGPT обрабатывает запрос...")

        # Показываем действие "печатает" (typing)
        await bot.send_chat_action(chat_id, action=types.ChatActions.TYPING)

        # Запрашиваем ответ у API OpenAI
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=chat_storage[chat_id]
        )

        # Отправляем ответ пользователю
        await sent_message.delete()
        await message.answer(response.choices[0].get('text') or response.choices[0]['message'].get('content'))

        # Обновляем временную метку
        timestamps[chat_id].append(time.time())


# Функция для проверки превышения лимита запросов
def is_request_limit_exceeded(chat_id):
    current_timestamp = time.time()
    request_limit = 3  # Лимит запросов за минуту
    timestamp_list = timestamps[chat_id]

    # Удаляем метки времени, которые превышают одну минуту
    timestamp_list = [
        timestamp for timestamp in timestamp_list if current_timestamp - timestamp < 60]

    # Обновляем список меток времени
    timestamps[chat_id] = timestamp_list

    # Проверяем превышение лимита
    if len(timestamp_list) >= request_limit:
        return True

    return False


@dp.message_handler(commands=['start'])
async def start_command(message: types.Message):
    user_name = message.from_user.first_name
    await message.answer(
        f"Привет, {user_name}! Я ChatGpt бот. Чтобы начать общение со мной, отправьте команду /chatgpt, чтобы сгенерировать изображение отправте команду /dalle2 и запрос после,, чтобы удалить переписку команда /chatgptclear!")


@dp.message_handler(commands=['help'])
async def start_command(message: types.Message):
    await message.answer(
        "Привет! Я ChatGpt, чтобы у меня что-то спросить, отправь команду /chatgpt или /dalle2 и запрос после, чтобы сегенерировать изображение. Если хочешь переписку удалить то /chatgptclear. Если что-то ещё помочь, обращайся сюда @AleksFolt.")


@dp.message_handler(commands=['about'])
async def start_command(message: types.Message):
    await message.answer("Создатель: @AleksFolt, Сделано на Python, По вопросам @AleksFolt")


@dp.message_handler(commands=['chatgptclear'])
async def clear_command(message: types.Message):
    chat_id = message.chat.id
    if chat_id in chat_storage:
        chat_storage[chat_id] = messages.copy()
        await message.answer("Переписка удалена!")
    else:
        await message.answer("Переписка пустая. Нет данных для удаления.")


@dp.message_handler(commands=['chatgptclear'])
async def chatgptclear_command(message: types.Message):
    await message.answer("Очистка переписки")


async def generate_image(text):
    try:
        response = openai.Image.create(
            prompt=text,
            n=1,
            size="1024x1024"
        )
        # Сохранение изображения в буфер
        img = await aiohttp.ClientSession().get(response['data'][0]['url'])
        img = io.BytesIO(await img.read())
        return img
    except openai.error.InvalidRequestError:
        logging.exception("Request contains forbidden symbols.")
        return None
    except Exception as e:
        logging.exception(e)
        return None


async def send_image(chat_id, image):
    try:
        # Конвертация буфера изображения в InputFile для отправки в телеграм-бот
        image = InputFile(image)
        await bot.send_photo(chat_id=chat_id, photo=image)
    except Exception as e:
        logging.exception(e)


# Обработчик команды /dalle2
# Обработчик команды /dalle2
# Обработчик команды /dalle2
@dp.message_handler(commands=['dalle2'])
async def dalle2_command(message: types.Message):
    # Получение текста запроса из сообщения
    text = message.text.split("/dalle2 ")[1]
    chat_id = message.chat.id

    # Отправка сообщения "Dalle2 обрабатывает запрос..."
    sent_message = await bot.send_message(chat_id=chat_id, text="Dalle2 обрабатывает запрос...")

    # Отображение действия "загрузка фото"
    await bot.send_chat_action(chat_id=chat_id, action='upload_photo')

    image = await generate_image(text)

    if image:
        # Отправка фотографии
        await bot.send_photo(chat_id=chat_id, photo=image)
    else:
        await bot.send_message(chat_id=chat_id,
                               text="Запрос содержит запрещённые термины 🚫. Попробуйте переформулировать.")

    # Удаление сообщения "Dalle2 обрабатывает запрос..."
    await bot.delete_message(chat_id=chat_id, message_id=sent_message.message_id)


executor.start_polling(dp, skip_updates=True)
