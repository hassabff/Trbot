import os
import fitz  # PyMuPDF
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes, CommandHandler
from deep_translator import GoogleTranslator
import arabic_reshaper
from bidi.algorithm import get_display

# --- Basic Settings ---
TOKEN = '7673577330:AAEeJrtmG6bA5a7fhr3N4eZunKV-qoOEwZM' 
ADMIN_ID = 5859773894  # Replace with your Telegram ID

def fix_arabic(text):
    if not text or not text.strip(): return ""
    reshaped = arabic_reshaper.reshape(text)
    return get_display(reshaped)

# 1. Start command and Admin notification
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    print(f"👤 New user started the bot: {user.first_name} (ID: {user.id})")
    
    welcome_text = f"Welcome {user.first_name} to the PDF Translation Bot! 📚\n\nJust send me any PDF file and I will translate it for you."
    await update.message.reply_text(welcome_text)
    
    # Notify Admin
    try:
        await context.bot.send_message(chat_id=ADMIN_ID, text=f"🔔 New User: {user.first_name}\nID: {user.id}")
    except Exception as e:
        print(f"❌ Could not send notification to admin: {e}")

# 2. PDF Handling and Translation
async def handle_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    print(f"📩 Received file from: {user.first_name}")
    
    # Notify Admin
    try:
        await context.bot.send_message(chat_id=ADMIN_ID, text=f"📩 {user.first_name} started translating a file.")
    except: pass

    translator = GoogleTranslator(source='auto', target='ar')
    tg_file = await update.message.document.get_file()
    chat_id = update.effective_chat.id
    input_path = f"in_{chat_id}.pdf"
    output_path = f"out_{chat_id}.pdf"
    
    await update.message.reply_text(" Processing...⏳")
    
    try:
        await tg_file.download_to_drive(input_path)
        doc = fitz.open(input_path)
        font_path = os.path.join(os.getcwd(), "arial.ttf")
        
        total_pages = len(doc)
        print(f"--- Processing file ({total_pages} pages) ---")

        for page in doc:
            current_page = page.number + 1
            print(f" Translating Page 🔄 [{current_page}/{total_pages}]...") 
            
            font_name = "f_ar"
            page.insert_font(fontname=font_name, fontfile=font_path)
            
            blocks = page.get_text("dict")["blocks"]
            for b in blocks:
                if "lines" in b:
                    for line in b["lines"]:
                        for span in line["spans"]:
                            txt = span["text"].strip()
                            if len(txt) > 2 and not txt.isdigit():
                                try:
                                    translation = translator.translate(txt)
                                    ready_text = fix_arabic(translation)
                                    rect = fitz.Rect(span["bbox"])
                                    # White-out original text
                                    page.draw_rect(rect, color=(1, 1, 1), fill=(1, 1, 1), overlay=True)
                                    # Insert Arabic text
                                    page.insert_text((rect.x0, rect.y1 - 1), ready_text, fontname=font_name, fontsize=span["size"]-1, color=(0, 0, 0))
                                except: continue
            
        doc.save(output_path)
        doc.close()
        print(f"✅ Finished translating {user.first_name}'s file.")

        with open(output_path, 'rb') as f:
            await update.message.reply_document(f, caption=" Translation Completed!✅")
            
    except Exception as e:
        print(f"❌ Processing Error: {e}")
        await update.message.reply_text(f"❌ An error occurred: {e}")
    finally:
        if os.path.exists(input_path): os.remove(input_path)
        if os.path.exists(output_path): os.remove(output_path)

def main():
    app = ApplicationBuilder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.Document.PDF, handle_pdf))
    
    print("🚀 Bot is running... Waiting for files.")
    app.run_polling()

if __name__=='__main__':
    main()