import os
import requests
from dotenv import load_dotenv
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ContextTypes, ConversationHandler, filters
)

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")

CHOOSE_LANG, QUIZ, NEXT_STEP = range(3)

LANGUAGES = {
    "🇰🇬 Кыргызча": "ky",
    "🇷🇺 Русский": "ru",
    "🇬🇧 English": "en"
}

INTRO_MESSAGES = {
    "ru": "Привет! Я твой личный HR-бот 🤖...",
    "ky": "Салам! Мен сенин жеке HR-ботуң 🤖...",
    "en": "Hey there! I'm your personal HR Bot 🤖..."
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
    "ru": ["🧠 Пройти тест", "📋 Получить советы", "🔁 Начать заново"],
    "ky": ["🧠 Тест", "📋 Кеңеш", "🔁 Башынан баштоо"],
    "en": ["🧠 Take quiz", "📋 Get advice", "🔁 Restart"]
}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[k] for k in LANGUAGES.keys()]
    markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text("Выбери язык / Choose language / Тилди танда:", reply_markup=markup)
    return CHOOSE_LANG

async def choose_lang(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = LANGUAGES.get(update.message.text, "ru")
    context.user_data.update({'lang': lang, 'answers': {}, 'quiz_index': 0})
    await update.message.reply_text(INTRO_MESSAGES[lang])
    return await ask_question(update, context)

async def ask_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    i = context.user_data['quiz_index']
    if i >= len(QUESTIONS):
        return await analyze_answers(update, context)
    lang = context.user_data['lang']
    q = QUESTIONS[i]['question'][lang]
    await update.message.reply_text(q)
    return QUIZ

async def handle_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    i = context.user_data['quiz_index']
    key = QUESTIONS[i]['key']
    context.user_data['answers'][key] = update.message.text
    context.user_data['quiz_index'] += 1
    return await ask_question(update, context)

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
            result = response.json()
            feedback = result['choices'][0]['message']['content']
        else:
            feedback = f"❌ Ошибка: {response.text}"
    except Exception as e:
        feedback = f"🚫 Ошибка подключения: {str(e)}"

    await update.message.reply_text("📋 Фидбек:\n" + feedback)

    buttons = [[KeyboardButton(opt)] for opt in OPTIONS[lang]]
    markup = ReplyKeyboardMarkup(buttons, resize_keyboard=True, one_time_keyboard=True)
    await update.message.reply_text(NEXT_STEPS[lang], reply_markup=markup)
    return NEXT_STEP

async def handle_next_step(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = context.user_data.get("lang", "ru")
    text = update.message.text
    if "🔁" in text:
        return await choose_lang(update, context)
    elif "📋" in text:
        return await analyze_answers(update, context)
    elif "🧠" in text:
        await update.message.reply_text("🚧 Квиз в разработке.")
        return NEXT_STEP
    else:
        await update.message.reply_text("Выбери вариант из меню.")
        return NEXT_STEP

app = ApplicationBuilder().token(BOT_TOKEN).build()

conv_handler = ConversationHandler(
    entry_points=[CommandHandler("start", start)],
    states={
        CHOOSE_LANG: [MessageHandler(filters.TEXT & ~filters.COMMAND, choose_lang)],
        QUIZ: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_answer)],
        NEXT_STEP: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_next_step)]
    },
    fallbacks=[]
)

app.add_handler(conv_handler)

print("🚀 HR Бот (Mistral AI) запущен!")
app.run_polling()
