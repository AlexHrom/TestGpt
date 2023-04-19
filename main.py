import openai
from aiogram import Bot, types
from aiogram.dispatcher import Dispatcher
from aiogram.utils import executor
import json

file = open('config.json', 'r')
config = json.load(file)

openai.api_key = config['openai']
bot = Bot(config['token'])
dp = Dispatcher(bot)

messages = [
    {"role": "system", "content": "You are chatgpt"},
    {"role": "user", "content": "Привет, как дела?"}
]


def update(messages, role, content):
    messages.append({"role": role, "content": content})
    return messages


@dp.message_handler()
async def send(message: types.Message):
    bot_info = await message.bot.get_me()
    if f'@{bot_info.username}' in message.text:
        update(messages, "user", message.text)
        responce = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=messages
        )

        await message.answer(responce['choices'][0]['message']['content'])


executor.start_polling(dp, skip_updates=True)
