import os
import firebase_admin
from firebase_admin import credentials, storage
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

# ייבוא הגדרות מקובץ config.py
from config import BOT_TOKEN, FIREBASE_CREDENTIALS_PATH, FIREBASE_STORAGE_BUCKET, LESSON_TOPICS

# הגדרת Firebase
cred = credentials.Certificate(FIREBASE_CREDENTIALS_PATH)
firebase_admin.initialize_app(cred, {
    'storageBucket': FIREBASE_STORAGE_BUCKET
})
bucket = storage.bucket()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """פקודת התחלה שמציגה את אפשרויות הבוט"""
    await update.message.reply_text(
        "שלום וברוכים הבאים לבוט מערכי שיעור לחינוך גופני!\n"
        "אנא הקלידו נושא לחיפוש (למשל: כדורסל, כדורגל, התעמלות) או השתמשו בפקודה /topics להצגת כל הנושאים הזמינים."
    )

async def show_topics(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """מציג את כל הנושאים הזמינים"""
    topics_text = "הנושאים הזמינים:\n\n"
    for topic in LESSON_TOPICS.keys():
        topics_text += f"• {topic}\n"
    
    topics_text += "\nאנא הקלידו את שם הנושא כדי לראות את מערכי השיעור הזמינים."
    await update.message.reply_text(topics_text)

async def handle_topic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """מטפל בחיפוש נושא וחוזר עם רשימת מערכי השיעור הזמינים"""
    topic = update.message.text.strip()
    
    if topic.lower() in [t.lower() for t in LESSON_TOPICS.keys()]:
        # מציאת המפתח המדויק (עם אותיות גדולות/קטנות)
        exact_topic = next(t for t in LESSON_TOPICS.keys() if t.lower() == topic.lower())
        
        keyboard = []
        for lesson in LESSON_TOPICS[exact_topic]:
            keyboard.append([InlineKeyboardButton(lesson["name"], callback_data=f"file_{lesson['file_path']}")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(f"מערכי שיעור בנושא {exact_topic}:", reply_markup=reply_markup)
    else:
        await update.message.reply_text(
            f"לא נמצאו מערכי שיעור בנושא '{topic}'.\n"
            f"השתמש בפקודה /topics לרשימת הנושאים הזמינים."
        )

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """מטפל בלחיצות על כפתורים ושולח את הקובץ המבוקש"""
    query = update.callback_query
    await query.answer()
    
    if query.data.startswith("file_"):
        file_path = query.data[5:]  # הסרת הקידומת "file_"
        
        try:
            # יצירת URL זמני לקובץ מ-Firebase Storage
            blob = bucket.blob(file_path)
            url = blob.generate_signed_url(expiration=3600)  # URL בתוקף לשעה
            
            # שליחת הקובץ
            file_name = os.path.basename(file_path)
            await query.message.reply_text(f"מוריד את הקובץ: {file_name}")
            await query.message.reply_document(url)
        except Exception as e:
            await query.message.reply_text(f"אירעה שגיאה בהורדת הקובץ: {str(e)}")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """מציג הודעת עזרה"""
    help_text = """פקודות זמינות:
/start - התחל שיחה עם הבוט
/topics - הצג את כל נושאי מערכי השיעור הזמינים
/help - הצג הודעת עזרה זו

לחיפוש מערכי שיעור, פשוט הקלידו את שם הנושא (למשל: "כדורסל").
"""
    await update.message.reply_text(help_text)

def main():
    """הפונקציה הראשית להפעלת הבוט"""
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    
    # הוספת מטפלי פקודות
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("topics", show_topics))
    application.add_handler(CommandHandler("help", help_command))
    
    # מטפל בהודעות טקסט
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_topic))
    
    # מטפל בלחיצות כפתורים
    application.add_handler(CallbackQueryHandler(button_callback))
    
    # הפעלת הבוט
    application.run_polling()

if __name__ == "__main__":
    main()
