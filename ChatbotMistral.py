import os
import requests
from dotenv import load_dotenv
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.constants import ChatAction
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ContextTypes, ConversationHandler, filters
)

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")

(
    CHOOSE_LANG, QUIZ, NEXT_STEP,
    CHOOSE_DIRECTION, CHOOSE_TEST_TYPE,
    HANDLE_TEST, HANDLE_FREE_QUESTION
) = range(7)

LANGUAGES = {
    "🇰🇬 Кыргызча": "ky",
    "🇷🇺 Русский": "ru",
    "🇬🇧 English": "en"
}

INTRO_MESSAGES = {
    "ru": "Привет! Я твой личный HR-бот 🤖 Готов помочь с подготовкой к собеседованиям и тестам.",
    "ky": "Салам! Мен сенин жеке HR-ботуң 🤖 Мен интервью жана тестке даярданууга жардам берем.",
    "en": "Hey there! I'm your personal HR Bot 🤖 I'm here to help you prepare for interviews and tests."
}

QUESTIONS = [
    {"key": "about_you", "question": {"ru": "Расскажи о себе.", "ky": "Өзүң тууралуу айтып бер.", "en": "Tell me about yourself."}},
    {"key": "weaknesses", "question": {"ru": "Твои слабые стороны?", "ky": "Алсыз жактарың?", "en": "Your weaknesses?"}},
    {"key": "interview_look", "question": {"ru": "Что наденешь на интервью?", "ky": "Интервьюга эмне кийесиң?", "en": "What will you wear to the interview?"}}
]

NEXT_STEPS = {
    "ru": "Что хочешь сделать дальше?",
    "ky": "Эми эмне кылабыз?",
    "en": "What would you like to do next?"
}

OPTIONS = {
    "ru": ["🧠 Пройти тест", "📋 Получить советы", "💬 Задать вопрос", "🔁 Начать заново"],
    "ky": ["🧠 Тест", "📋 Кеңеш", "💬 Суроо берүү", "🔁 Башынан баштоо"],
    "en": ["🧠 Take quiz", "📋 Get advice", "💬 Ask a question", "🔁 Restart"]
}

DIRECTIONS = {
    "ru": ["💻 Frontend", "🖥 Backend", "📱 Mobile", "🧠 Data Science"],
    "ky": ["💻 Фронтенд", "🖥 Бэкенд", "📱 Мобилдик", "🧠 Дата Сайенс"],
    "en": ["💻 Frontend", "🖥 Backend", "📱 Mobile", "🧠 Data Science"]
}

TEST_TYPES = {
    "ru": ["📚 Теория", "🛠 Практика"],
    "ky": ["📚 Теория", "🛠 Практика"],
    "en": ["📚 Theory", "🛠 Practice"]
}

def typing_action(func):
    async def command_func(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        await update.message.chat.send_action(action=ChatAction.TYPING)
        return await func(update, context, *args, **kwargs)
    return command_func

@typing_action
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[k] for k in LANGUAGES.keys()]
    markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text("Выбери язык / Choose language / Тилди танда:", reply_markup=markup)
    return CHOOSE_LANG

@typing_action
async def choose_lang(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = LANGUAGES.get(update.message.text, "ru")
    context.user_data.update({'lang': lang, 'answers': {}, 'quiz_index': 0})
    await update.message.reply_text(INTRO_MESSAGES[lang])
    return await ask_question(update, context)

@typing_action
async def ask_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    i = context.user_data['quiz_index']
    if i >= len(QUESTIONS):
        return await analyze_answers(update, context)
    lang = context.user_data['lang']
    q = QUESTIONS[i]['question'][lang]
    await update.message.reply_text(q)
    return QUIZ

@typing_action
async def handle_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    i = context.user_data['quiz_index']
    key = QUESTIONS[i]['key']
    context.user_data['answers'][key] = update.message.text
    context.user_data['quiz_index'] += 1
    return await ask_question(update, context)

@typing_action
async def analyze_answers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = context.user_data['lang']
    answers = context.user_data.get('answers', {})
    if not any(answers.values()):
        await update.message.reply_text("❗ Сначала ответь на вопросы.")
        return NEXT_STEP

    prompt = {
        "ru": "Проанализируй ответы и дай советы кандидату:",
        "ky": "Жоопторду анализдеп кеңеш бер:",
        "en": "Analyze the answers and give advice:"
    }[lang] + "\n" + "\n".join(answers.values())

    feedback = await generate_response(prompt, lang)
    await update.message.reply_text("📋 Фидбек:\n" + feedback)

    buttons = [[KeyboardButton(opt)] for opt in OPTIONS[lang]]
    markup = ReplyKeyboardMarkup(buttons, resize_keyboard=True, one_time_keyboard=True)
    await update.message.reply_text(NEXT_STEPS[lang], reply_markup=markup)
    return NEXT_STEP

@typing_action
async def handle_next_step(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = context.user_data.get("lang", "ru")
    text = update.message.text
    if "🔁" in text:
        return await choose_lang(update, context)
    elif "📋" in text:
        return await analyze_answers(update, context)
    elif "🧠" in text:
        buttons = [[KeyboardButton(d)] for d in DIRECTIONS[lang]]
        markup = ReplyKeyboardMarkup(buttons, resize_keyboard=True, one_time_keyboard=True)
        await update.message.reply_text("Выбери IT-направление:", reply_markup=markup)
        return CHOOSE_DIRECTION
    elif "💬" in text:
        await update.message.reply_text("✍️ Напиши свой вопрос, и я помогу:")
        return HANDLE_FREE_QUESTION
    else:
        await update.message.reply_text("Выбери вариант из меню.")
        return NEXT_STEP

@typing_action
async def choose_direction(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['direction'] = update.message.text
    lang = context.user_data['lang']
    buttons = [[KeyboardButton(t)] for t in TEST_TYPES[lang]]
    markup = ReplyKeyboardMarkup(buttons, resize_keyboard=True, one_time_keyboard=True)
    await update.message.reply_text("Выбери тип теста:", reply_markup=markup)
    return CHOOSE_TEST_TYPE

@typing_action
async def choose_test_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['test_type'] = update.message.text
    lang = context.user_data['lang']
    direction = context.user_data['direction']
    test_type = context.user_data['test_type']

    prompt = {
        "ru": f"Составь {test_type.lower()} по направлению {direction} на русском языке и ожидай ответы от пользователя.",
        "ky": f"{direction} багыты боюнча {test_type.lower()} тест түз жана колдонуучунун жоопторун күт.",
        "en": f"Create a {test_type.lower()} quiz for the {direction} field in English and wait for user's answers."
    }[lang]

    test = await generate_response(prompt, lang)
    context.user_data['test'] = test
    await update.message.reply_text("🧠 Тест:\n" + test)
    return HANDLE_TEST

@typing_action
async def handle_test(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['user_test_answers'] = update.message.text
    lang = context.user_data['lang']
    test = context.user_data['test']
    user_answers = context.user_data['user_test_answers']

    prompt = {
        "ru": f"Анализируй ответы пользователя на тест по теме:\n{test}\nОтветы:\n{user_answers}\nДай подробный анализ и советы.",
        "ky": f"Тест жана жоопторду анализдеп, кеңеш бер:\n{test}\nЖооптор:\n{user_answers}",
        "en": f"Analyze the user's test answers:\n{test}\nAnswers:\n{user_answers}\nGive detailed analysis and suggestions."
    }[lang]

    feedback = await generate_response(prompt, lang)
    await update.message.reply_text("📊 Результат теста:\n" + feedback)

    buttons = [[KeyboardButton(opt)] for opt in OPTIONS[lang]]
    markup = ReplyKeyboardMarkup(buttons, resize_keyboard=True, one_time_keyboard=True)
    await update.message.reply_text(NEXT_STEPS[lang], reply_markup=markup)
    return NEXT_STEP

@typing_action
async def handle_free_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = context.user_data.get("lang", "ru")
    question = update.message.text

    prompt = {
        "ru": f"Ответь на вопрос пользователя и дай советы:\n{question}",
        "ky": f"Колдонуучунун суроосуна жооп берип, кеңеш бер:\n{question}",
        "en": f"Answer the user's question and give advice:\n{question}"
    }[lang]

    answer = await generate_response(prompt, lang)
    await update.message.reply_text("🧠 Ответ:\n" + answer)

    buttons = [[KeyboardButton(opt)] for opt in OPTIONS[lang]]
    markup = ReplyKeyboardMarkup(buttons, resize_keyboard=True, one_time_keyboard=True)
    await update.message.reply_text(NEXT_STEPS[lang], reply_markup=markup)
    return NEXT_STEP

async def generate_response(prompt, lang):
    headers = {
        "Authorization": f"Bearer {MISTRAL_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "mistral-small",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7
    }
    try:
        response = requests.post("https://api.mistral.ai/v1/chat/completions", headers=headers, json=data)
        if response.ok:
            return response.json()['choices'][0]['message']['content']
        else:
            return f"❌ Ошибка API: {response.text}"
    except Exception as e:
        return f"🚫 Ошибка подключения: {str(e)}"

app = ApplicationBuilder().token(BOT_TOKEN).build()

conv_handler = ConversationHandler(
    entry_points=[CommandHandler("start", start)],
    states={
        CHOOSE_LANG: [MessageHandler(filters.TEXT & ~filters.COMMAND, choose_lang)],
        QUIZ: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_answer)],
        NEXT_STEP: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_next_step)],
        CHOOSE_DIRECTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, choose_direction)],
        CHOOSE_TEST_TYPE: [MessageHandler(filters.TEXT & ~filters.COMMAND, choose_test_type)],
        HANDLE_TEST: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_test)],
        HANDLE_FREE_QUESTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_free_question)],
    },
    fallbacks=[]
)

app.add_handler(conv_handler)

print("🚀 HR Бот запущен!")
app.run_polling()
