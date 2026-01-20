import sys
import telebot
from telebot import types
import io
import tokenize
import requests
import time
from threading import Thread
import subprocess
import string
from collections import defaultdict
from datetime import datetime
import psutil
import random
import re
import chardet
# إعدادات البوتات
from concurrent.futures import ThreadPoolExecutor 
import os
import logging
import telebot
from telebot import types
import threading
# إعدادات البوتات
BOT_TOKEN = '8551673947:AAEQn81w94n2EPALeGM82FDAMhPv38xqkP8'  # token 
ADMIN_ID = '7675784912'  # id
VIRUSTOTAL_API_KEY = 'a0df84fb7e065c823f5eeb12c000359863118f946b4733f8dbab049285ef7db7'  # هتحط هنا ال api
ADMIN_CHANNEL = '@kimo_store_ly'   # هنا هتحط قناتك اشتراك اجباري !!

bot_scripts1 = defaultdict(lambda: {'processes': [], 'name': '', 'path': '', 'uploader': ''})  # لإدارة العمليات
user_files = {} 
lock = threading.Lock()
executor = ThreadPoolExecutor(max_workers=3000) 


bot = telebot.TeleBot(BOT_TOKEN)
bot_scripts = {}
uploaded_files_dir = "uploaded_files"
banned_users = set()
user_chats = {}
# إعدادات تسجيل الدخول
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

#################### حذف أي webhook نشط لضمان استخدام polling ############

bot.remove_webhook()

#################### إنشاء مجلد uploaded_files إذا لم يكن موجوداً####################


if not os.path.exists(uploaded_files_dir):
    os.makedirs(uploaded_files_dir)

#################### تحقق من الاشتراك في القناه ###########################


def check_subscription(user_id):
    try:
        # تحقق مما إذا كان المستخدم مشتركًا في القناة
        member_status = bot.get_chat_member(ADMIN_CHANNEL, user_id).status
        return member_status in ['member', 'administrator', 'creator']
    except Exception as e:
        logging.error(f"Error checking subscription: {e}")
        return False


##################### بدايه حظر اشاء معينه وحمايه ########################



def is_safe_file(file_path):
    """دالة للتحقق من أن الملف لا يحتوي على تعليمات لإنشاء أرشيفات أو إرسالها عبر بوت"""
    try:
        with open(file_path, 'rb') as f:
            raw_content = f.read()
            
            # تحقق من ترميز الملف
            encoding_info = chardet.detect(raw_content)
            encoding = encoding_info['encoding']
            
            if encoding is None:
                logging.warning("Unable to detect encoding, file may be binary or encrypted.")
                return "لم يتم رفع الملف فيه اوامر غير مسموح بها"

            # تحويل المحتوى إلى نص باستخدام الترميز المكتشف
            content = raw_content.decode(encoding)
            
            # الأنماط الخطرة
            dangerous_patterns = [
                r'\bshutil\.make_archive\b',  # إنشاء أرشيف
                r'bot\.send_document\b',  # إرسال ملفات عبر بوت
                r'\bopen\s*\(\s*.*,\s*[\'\"]w[\'\"]\s*\)',  # فتح ملف للكتابة
                r'\bopen\s*\(\s*.*,\s*[\'\"]a[\'\"]\s*\)',  # فتح ملف للإلحاق
                r'\bopen\s*\(\s*.*,\s*[\'\"]wb[\'\"]\s*\)',  # فتح ملف للكتابة الثنائية
                r'\bopen\s*\(\s*.*,\s*[\'\"]ab[\'\"]\s*\)',  # فتح ملف للإلحاق الثنائي
            ]

            for pattern in dangerous_patterns:
                if re.search(pattern, content):
                    return "لم يتم رفع الملف فيه اوامر غير مسموح بها"

            # تحقق من أن المحتوى نصي وليس مشفرًا
            if not is_text(content):
                return "لم يتم رفع الملف فيه اوامر غير مسموح بها"

        return "الملف آمن"
    except Exception as e:
        logging.error(f"Error checking file safety: {e}")
        return "لم يتم رفع الملف فيه اوامر غير مسموح بها"

def is_text(content):
    """دالة للتحقق مما إذا كان المحتوى نصيًا"""
    # تحقق من وجود أي بايتات غير قابلة للطباعة
    for char in content:
        if char not in string.printable:
            return False
    return True

    





    
####################### بدايه الدوال #######################

### حفظ id شات



def save_chat_id(chat_id):
    """دالة لحفظ chat_id للمستخدمين الذين يتفاعلون مع البوت."""
    if chat_id not in user_chats:
        user_chats[chat_id] = True  # يمكنك تخزين معلومات إضافية هنا إذا لزم الأمر
        print(f"تم حفظ chat_id: {chat_id}")
    else:
        print(f"chat_id: {chat_id} موجود بالفعل.")


################################################################## داله البدأ 


@bot.message_handler(commands=['start'])
def start(message):
    # حفظ chat_id عند بدء التفاعل
    save_chat_id(message.chat.id)

    if message.from_user.username in banned_users:
        bot.send_message(message.chat.id, "تم حظرك من البوت. تواصل مع المطور @kimo_ly_bot")
        return

    # تحقق من الاشتراك
    if not check_subscription(message.from_user.id):
        markup = types.InlineKeyboardMarkup()
        subscribe_button = types.InlineKeyboardButton("اشترك في القناة", url='https://t.me/kimo_store_ly')
        markup.add(subscribe_button)

        bot.send_message(
            message.chat.id,
            "⚠️ يجب عليك الاشتراك في قناة المطور لاستخدام البوت.\n\n"
            "🔗 اضغط على الزر أدناه للاشتراك:",
            reply_markup=markup
        )
        return

    # إضافة المستخدم إلى bot_scripts
    bot_scripts[message.chat.id] = {
        'name': message.from_user.username,
        'uploader': message.from_user.username,
    }

    markup = types.InlineKeyboardMarkup()
    upload_button = types.InlineKeyboardButton("رفع ملف 📤", callback_data='upload')
    developer_button = types.InlineKeyboardButton("قناة مطور البوت", url='https://t.me/M1telegramM1')
    
    markup.row(upload_button)
    markup.row(developer_button)

    bot.send_message(
        message.chat.id,
        "مرحبًا بك في بوت رفع وتشغيل ملفات بايثون.\n"
        "استخدم الزر بالأسفل لرفع الملفات.\n"
        "للحصول على جميع الأوامر والتعليمات، يمنع تماماً رفع ملفات غير بايثون حتى لا يتم حظرك /help.\n"
        "الاوامر /cmd",
        reply_markup=markup
    )

##



################ دالة cmd #####################







####################### الادمن 
# داله مساعده


@bot.message_handler(commands=['help'])
def instructions(message):
    if message.from_user.username in banned_users:
        bot.send_message(message.chat.id, "تم حظرك من البوت تواصل مع المطور @kimo_ly_bot")
        return

    bot.send_message(
        message.chat.id,
        "الأوامر المتاحة:\n"
        "/start - بدء البوت والحصول على الأزرار.\n"
        "/developer - التواصل مع المطور.\n"
        "/help - عرض هذه التعليمات.\n"
        "/rck [رسالة] - إرسال رسالة إلى جميع المستخدمين.\n"
        "/ban [معرف] - حظر مستخدم.\n"
        "/uban [معرف] - فك حظر مستخدم.\n"
        "/del [اسم الملف] - حذف ملف.\n"
        "/stp [اسم الملف] - إيقاف ملف.\n"
        "/str [اسم الملف] - تشغيل ملف.\n"
        "/rr [معرف] [رسالة] - إرسال رسالة لمستخدم معين.\n"
        "قم برفع ملف البايثون الخاص بك عبر الزر المخصص.\n"
        "بعد الرفع، يمكنك التحكم في التشغيل، الإيقاف، أو الحذف باستخدام الأزرار الظاهرة."
    )

@bot.message_handler(commands=['ban'])
def ban_user(message):
    if str(message.from_user.id) != ADMIN_ID:
        bot.reply_to(message, "ليس لديك صلاحية استخدام هذا الأمر.")
        return

    try:
        username = message.text.split(' ', 1)[1].strip('@')
        if username in banned_users:
            bot.reply_to(message, f"المستخدم @{username} محظور بالفعل.")
        else:
            banned_users.add(username)
            bot.reply_to(message, f"تم حظر المستخدم @{username}.")
    except IndexError:
        bot.reply_to(message, "يرجى كتابة معرف المستخدم بعد الأمر.")

@bot.message_handler(commands=['uban'])
def unban_user(message):
    if str(message.from_user.id) != ADMIN_ID:
        bot.reply_to(message, "ليس لديك صلاحية استخدام هذا الأمر.")
        return

    try:
        username = message.text.split(' ', 1)[1].strip('@')
        if username not in banned_users:
            bot.reply_to(message, f"المستخدم @{username} ليس محظور.")
        else:
            banned_users.remove(username)
            bot.reply_to(message, f"تم فك حظر المستخدم @{username}.")
    except IndexError:
        bot.reply_to(message, "يرجى كتابة معرف المستخدم بعد الأمر.")


@bot.message_handler(commands=['rck'])
def broadcast_message(message):
    if str(message.from_user.id) != ADMIN_ID:
        bot.reply_to(message, "ليس لديك صلاحية استخدام هذا الأمر.")
        return

    try:
        msg = message.text.split(' ', 1)[1]  # الحصول على الرسالة
        print("محتوى bot_scripts:", bot_scripts)  # طباعة محتوى bot_scripts

        sent_count = 0
        failed_count = 0

        for chat_id in bot_scripts.keys():
            try:
                bot.send_message(chat_id, msg)
                sent_count += 1
            except Exception as e:
                logging.error(f"Error sending message to {chat_id}: {e}")
                failed_count += 1

        total_users = len(bot_scripts)
        bot.reply_to(message, f"تم إرسال الرسالة بنجاح إلى {sent_count} من {total_users} مستخدمين.\n"
                              f"فشلت الرسالة في إرسالها إلى {failed_count} مستخدمين.")
    except IndexError:
        bot.reply_to(message, "يرجى كتابة الرسالة بعد الأمر.")




            
@bot.message_handler(commands=['del'])
def delete_file(message):
    if str(message.from_user.id) != ADMIN_ID:
        bot.reply_to(message, "ليس لديك صلاحية استخدام هذا الأمر.")
        return

    try:
        if message.reply_to_message:
            script_name = message.reply_to_message.text.strip()
        else:
            script_name = message.text.split(' ', 1)[1].strip()

        script_path = os.path.join(uploaded_files_dir, script_name)
        stop_bot(script_path, message.chat.id, delete=True)
        bot.reply_to(message, f"تم حذف ملف {script_name} بنجاح.")
        with open(script_path, 'rb') as file:
            bot.send_document(ADMIN_ID, file, caption=f"ملف محذوف: {script_name}")
    except IndexError:
        bot.reply_to(message, "يرجى كتابة اسم الملف بعد الأمر أو الرد على رسالة.")
    except Exception as e:
        bot.reply_to(message, f"حدث خطأ: {e}")

@bot.message_handler(commands=['stp'])
def stop_file_command(message):
    if str(message.from_user.id) != ADMIN_ID:
        bot.reply_to(message, "ليس لديك صلاحية استخدام هذا الأمر.")
        return

    try:
        if message.reply_to_message:
            script_name = message.reply_to_message.text.strip()
        else:
            script_name = message.text.split(' ', 1)[1].strip()

        script_path = os.path.join(uploaded_files_dir, script_name)
        stop_bot(script_path, message.chat.id)
        bot.reply_to(message, f"تم إيقاف ملف {script_name} بنجاح.")
    except IndexError:
        bot.reply_to(message, "يرجى كتابة اسم الملف بعد الأمر أو الرد على رسالة.")
    except Exception as e:
        bot.reply_to(message, f"حدث خطأ: {e}")




@bot.message_handler(commands=['rr'])
def send_private_message(message):
    if str(message.from_user.id) != ADMIN_ID:
        bot.reply_to(message, "ليس لديك صلاحية استخدام هذا الأمر.")
        return

    try:
        parts = message.text.split(' ', 2)
        if len(parts) < 3:
            bot.reply_to(message, "يرجى كتابة معرف المستخدم والرسالة بعد الأمر.")
            return

        username = parts[1].strip('@')
        msg = parts[2]

        user_found = False  # متغير لتتبع ما إذا تم العثور على المستخدم

        for chat_id, script_info in bot_scripts.items():
            # تحقق من تطابق اسم المستخدم مع الحروف الكبيرة والصغيرة
            if script_info.get('uploader', '').lower() == username.lower():
                bot.send_message(chat_id, msg)
                user_found = True
                break

        if user_found:
            bot.reply_to(message, "تم إرسال الرسالة بنجاح.")
        else:
            bot.reply_to(message, f"تعذر العثور على المستخدم @{username}. تأكد من إدخال الاسم بشكل صحيح.")
    except Exception as e:
        logging.error(f"Error in /rr command: {e}")
        bot.reply_to(message, "حدث خطأ أثناء معالجة الأمر. يرجى المحاولة مرة أخرى.")



def file_contains_input_or_eval(content):
    for token_type, token_string, _, _, _ in tokenize.generate_tokens(io.StringIO(content).readline):
        if token_string in {"input", "eval"}:
            return True
    return False

####################
### تجربه اقتراح


current_chat_session = None  # لتعقب المحادثة الحالية

@bot.message_handler(commands=['cmd'])
def display_commands(message):
    if message.from_user.username in banned_users:
        bot.send_message(message.chat.id, "تم حظرك من البوت. تواصل مع المطور @kimo_ly_bot")
        return

    markup = types.InlineKeyboardMarkup()
    report_button = types.InlineKeyboardButton("إرسال مشكلة للمطور", callback_data='report_issue')
    suggestion_button = types.InlineKeyboardButton("اقتراح تعديل", callback_data='suggest_modification')
    chat_button = types.InlineKeyboardButton("فتح محادثة مع المطور", callback_data='open_chat')

    markup.row(report_button)
    markup.row(suggestion_button)
    markup.row(chat_button)

    bot.send_message(
        message.chat.id,
        "📜 الأوامر المتاحة:\nاختر أحد الخيارات أدناه:",
        reply_markup=markup
    )

# دالة بدء محادثة مع المطور
# تعريف متغيرات الحالة
current_chat_session = None

# دالة بدء محادثة مع المطور
@bot.message_handler(commands=['developer'])
def contact_developer(message):
    if message.from_user.username in banned_users:
        bot.send_message(message.chat.id, "تم حظرك من البوت. تواصل مع المطور @kimo_ly_bot")
        return

    markup = types.InlineKeyboardMarkup()
    open_chat_button = types.InlineKeyboardButton("فتح محادثة مع المطور", callback_data='open_chat')
    markup.add(open_chat_button)
    bot.send_message(message.chat.id, "للتواصل مع مطور البوت، اختر الخيار أدناه:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == 'open_chat')
def initiate_chat(call):
    global current_chat_session
    user_id = call.from_user.id

    # التحقق إذا كانت محادثة مفتوحة بالفعل
    if current_chat_session is not None:
        bot.send_message(call.message.chat.id, "يرجى الانتظار، هناك محادثة جارية مع المطور.")
        return

    # إعلام المستخدم بأنه تم إرسال الطلب
    bot.send_message(call.message.chat.id, "تم إرسال طلب فتح محادثة، الرجاء انتظار المطور.")

    # إعلام المطور بطلب فتح المحادثة
    bot.send_message(ADMIN_ID, f"طلب فتح محادثة من @{call.from_user.username}.")
    markup = types.InlineKeyboardMarkup()
    accept_button = types.InlineKeyboardButton("قبول المحادثة", callback_data=f'accept_chat_{user_id}')
    reject_button = types.InlineKeyboardButton("رفض المحادثة", callback_data=f'reject_chat_{user_id}')
    markup.add(accept_button, reject_button)
    bot.send_message(ADMIN_ID, "لديك طلب محادثة جديد:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('accept_chat_'))
def accept_chat_request(call):
    global current_chat_session
    user_id = int(call.data.split('_')[2])

    # التحقق إذا كان هناك محادثة مفتوحة مع مستخدم آخر
    if current_chat_session is not None and current_chat_session != user_id:
        bot.send_message(call.message.chat.id, "يرجى إغلاق المحادثة الحالية أولاً قبل قبول محادثة جديدة.")
        return

    # تعيين المستخدم الحالي كمستخدم في المحادثة
    current_chat_session = user_id
    bot.send_message(user_id, f"تم قبول محادثتك من المطور @{call.from_user.username}.")

    # إضافة زر لإنهاء المحادثة لكل من المطور والمستخدم
    markup = types.InlineKeyboardMarkup()
    close_button = types.InlineKeyboardButton("إنهاء المحادثة", callback_data='close_chat')
    markup.add(close_button)
    
    # إرسال زر إنهاء المحادثة للمستخدم
    bot.send_message(user_id, "لإنهاء المحادثة، اضغط هنا:", reply_markup=markup)
    
    # إرسال زر إنهاء المحادثة للمطور
    bot.send_message(ADMIN_ID, "لإنهاء المحادثة، اضغط هنا:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('reject_chat_'))
def reject_chat_request(call):
    global current_chat_session
    user_id = int(call.data.split('_')[2])
    
    # إذا كانت المحادثة مخصصة للمستخدم المرفوض، قم بإغلاقها
    if current_chat_session == user_id:
        current_chat_session = None

    bot.send_message(user_id, "تم رفض محادثتك من قبل المطور.")
    bot.send_message(call.message.chat.id, f"تم رفض المحادثة مع المستخدم @{call.from_user.username}.")
@bot.callback_query_handler(func=lambda call: call.data == 'close_chat')
def close_chat_session(call):
    global current_chat_session
    user_id = call.from_user.id

    # تحقق مما إذا كانت المحادثة مغلقة
    if current_chat_session is not None:
        # إرسال رسالة للمستخدم الذي كان في المحادثة
        bot.send_message(current_chat_session, "تم إغلاق المحادثة من قبل المطور.")
        current_chat_session = None
        bot.send_message(call.message.chat.id, "تم إغلاق المحادثة.")
        bot.send_message(ADMIN_ID, f"تم إغلاق محادثة من @{call.from_user.username}.")
    else:
        bot.send_message(call.message.chat.id, "لا توجد محادثة مفتوحة.")

@bot.message_handler(commands=['ch'])
def close_chat_command(message):
    global current_chat_session
    if str(message.from_user.id) != ADMIN_ID:
        return

    # إغلاق المحادثة إذا كانت مفتوحة
    if current_chat_session is not None:
        user_id = current_chat_session
        current_chat_session = None
        bot.send_message(user_id, "تم إغلاق المحادثة من قبل المطور.")
        bot.send_message(message.chat.id, "تم إغلاق المحادثة الحالية.")
    else:
        bot.send_message(message.chat.id, "لا توجد محادثة مفتوحة لإغلاقها.")

@bot.message_handler(func=lambda message: True)
def handle_user_messages(message):
    global current_chat_session
    if message.from_user.id == current_chat_session:
        # رسالة من المستخدم إلى المطور
        bot.send_message(ADMIN_ID, message.text)
    elif str(message.from_user.id) == ADMIN_ID and current_chat_session is not None:
        # رسالة من المطور إلى المستخدم
        bot.send_message(current_chat_session, message.text)



# دالة لإرسال مشكلة إلى المطور
@bot.callback_query_handler(func=lambda call: call.data == 'report_issue')
def report_issue(call):
    bot.send_message(call.message.chat.id, "🛠️ ارسل مشكلتك الآن، وسيحلها المطور في أقرب وقت.")
    bot.register_next_step_handler(call.message, handle_report)

def handle_report(message):
    if message.text:
        bot.send_message(ADMIN_ID, f"🛠️ تم الإبلاغ عن مشكلة من @{message.from_user.username}:\n\n{message.text}")
        bot.send_message(message.chat.id, "✅ تم إرسال مشكلتك بنجاح! سيتواصل معك المطور قريبًا.")
    else:
        bot.send_message(message.chat.id, "❌ لم يتم تلقي أي نص. يرجى إرسال المشكلة مرة أخرى.")

# دالة لإرسال اقتراح إلى المطور
@bot.callback_query_handler(func=lambda call: call.data == 'suggest_modification')
def suggest_modification(call):
    bot.send_message(call.message.chat.id, "💡 اكتب اقتراحك الآن، أو أرسل صورة أو ملف وسأرسله للمطور.")
    bot.register_next_step_handler(call.message, handle_suggestion)

def handle_suggestion(message):
    if message.text:
        bot.send_message(ADMIN_ID, f"💡 اقتراح من @{message.from_user.username}:\n\n{message.text}")
        bot.send_message(message.chat.id, "✅ تم إرسال اقتراحك بنجاح للمطور!")
    elif message.photo:
        photo_id = message.photo[-1].file_id  # الحصول على أكبر صورة
        bot.send_photo(ADMIN_ID, photo_id, caption=f"💡 اقتراح من @{message.from_user.username} (صورة)")
        bot.send_message(message.chat.id, "✅ تم إرسال اقتراحك كصورة للمطور!")
    elif message.document:
        file_id = message.document.file_id
        bot.send_document(ADMIN_ID, file_id, caption=f"💡 اقتراح من @{message.from_user.username} (ملف)")
        bot.send_message(message.chat.id, "✅ تم إرسال اقتراحك كملف للمطور!")
    else:
        bot.send_message(message.chat.id, "❌ لم يتم تلقي أي محتوى. يرجى إرسال الاقتراح مرة أخرى.")

        




############# 


def scan_file_for_viruses(file_content, file_name):
    files = {'file': (file_name, file_content)}
    headers = {'x-apikey': VIRUSTOTAL_API_KEY}

    try:
        response = requests.post('https://www.virustotal.com/api/v3/files', files=files, headers=headers)
        response_data = response.json()

        if response.status_code == 200:
            analysis_id = response_data['data']['id']
            time.sleep(30)  # الانتظار قليلاً قبل التحقق من النتيجة

            analysis_url = f'https://www.virustotal.com/api/v3/analyses/{analysis_id}'
            analysis_response = requests.get(analysis_url, headers=headers)
            analysis_result = analysis_response.json()

            if analysis_response.status_code == 200:
                malicious = analysis_result['data']['attributes']['stats']['malicious']
                return malicious == 0  # رجوع True إذا لم يكن هناك اكتشافات ضارة
        return False
    except Exception as e:
        print(f"Error scanning file for viruses: {e}")
        return False






##### رفع ملفات ###############################




def get_bot_username(token):
    # هنا نستخدم معرف البوت لإرجاع اسم المستخدم
    bot_id = token.split(':')[0]
    return f"@{bot_id}"

@bot.message_handler(content_types=['document'])
def handle_file(message):
    try:
        if message.from_user.username in banned_users:
            bot.send_message(message.chat.id, "تم حظرك من البوت تواصل مع المطور @kimo_ly_bot")
            return

        file_id = message.document.file_id
        file_info = bot.get_file(file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        bot_script_name = message.document.file_name

        # فحص أن الملف هو ملف بايثون
        if not bot_script_name.endswith('.py'):
            bot.reply_to(message, "هذا بوت خاص برفع ملفات بايثون فقط.")
            return

        # تأكد من أن الملف ليس فارغًا
        if len(downloaded_file) == 0:
            bot.reply_to(message, "الملف فارغ، لن يتم رفعه.")
            return

        # تحميل محتوى الملف
        file_content = downloaded_file.decode('utf-8')

        # فحص المحتوى للبحث عن أنماط ضارة
        if file_contains_disallowed_patterns(file_content):
            bot.reply_to(message, "الملف يحتوي على أنماط ضارة وغير مسموح بها.")
            return

        # فحص الفيروسات
        if not scan_file_for_viruses(file_content, bot_script_name):
            bot.reply_to(message, "❌ الملف يحتوي على فيروسات. تم رفض رفع الملف.")
            bot.send_message(ADMIN_ID, f"❌ محاولة رفع ملف يحتوي على فيروسات من المستخدم @{message.from_user.username}")
            banned_users.add(message.from_user.username)
            bot.reply_to(message, "تم حظرك من البوت تواصل مع المطور @kimo_ly_bot")
            return

        # حفظ الملف
        script_path = os.path.join(uploaded_files_dir, bot_script_name)
        bot_scripts[message.chat.id] = {
            'name': bot_script_name,
            'uploader': message.from_user.username,
            'path': script_path,
            'process': None
        }

        with open(script_path, 'wb') as new_file:
            new_file.write(downloaded_file)

        bot_token = get_bot_token(script_path)  # الحصول على توكن البوت
        line_count = file_content.count('\n') + 1  # حساب عدد السطور
        current_time = datetime.now()
        hour = current_time.hour
        day = current_time.day
        month = current_time.month

        # جلب معرف البوت من التوكن
        try:
            bot_id = get_bot_id_from_token(bot_token)  # جلب معرف البوت
            bot_username = get_bot_username(bot_token)  # جلب اسم المستخدم للبوت
        except Exception as e:
            bot_id = f"خطأ في الحصول على معرف البوت: {e}"
            bot_username = "غير متوفر"

        markup = types.InlineKeyboardMarkup()
        delete_button = types.InlineKeyboardButton(f"حذف {bot_script_name} 🗑", callback_data=f'delete_{message.chat.id}_{bot_script_name}')
        stop_button = types.InlineKeyboardButton(f"إيقاف {bot_script_name} 🔴", callback_data=f'stop_{message.chat.id}_{bot_script_name}')
        start_button = types.InlineKeyboardButton(f"تشغيل {bot_script_name} 🟢", callback_data=f'start_{message.chat.id}_{bot_script_name}')
        markup.row(delete_button, stop_button, start_button)

        bot.reply_to(
            message,
            f"تم رفع ملف بوتك بنجاح ✅\n\n"
            f"اسم الملف المرفوع: بوت : {bot_script_name}\n"
            f"توكن البوت المرفوع: {bot_token}\n"  # عرض توكن البوت
            f"معرف بوتك: {bot_username}\n"  # عرض اسم مستخدم البوت
            f"رفعه المستخدم: @{message.from_user.username}\n"
            f"عدد سطور الملف المرفوع: {line_count}\n"
            f"الساعة: {hour}\n"
            f"اليوم: {day}\n"
            f"الشهر: {month}\n\n"
            "يمكنك التحكم في الملف باستخدام الأزرار الموجودة.",
            reply_markup=markup
        )
        send_to_admin(script_path, message.from_user.username)
        install_and_run_uploaded_file(script_path, message.chat.id)
    except Exception as e:
        bot.reply_to(message, f"حدث خطأ: {e}")

######### حمايه ##############


def file_contains_disallowed_patterns(content):
    """دالة للتحقق مما إذا كان المحتوى يحتوي على أنماط ضارة."""
    dangerous_patterns = [
        r'\bshutil\.copy\b',  # نسخ ملفات
        r'\bshutil\.move\b',  # نقل ملفات
        r'\bshutil\.rmtree\b',  # حذف ملفات ومجلدات
        r'\bimport\s+shutil\b',  # استيراد مكتبة shutil
        r'\bgetcwd\b',  # الحصول على مسار العمل الحالي
        r'\bchdir\b',  # تغيير مسار العمل الحالي
        r'\bpathlib\.Path\b',  # استخدام pathlib


    ]
    
    for pattern in dangerous_patterns:
        if re.search(pattern, content):
            return True
    return False

def handle_file_upload(file_content, message):
    # فحص المحتوى
    if file_contains_disallowed_patterns(file_content):
        bot.reply_to(message, "الملف يحتوي على دوال غير مسموح بها.")
        return

def get_bot_token(script_path):
    # دالة استخراج التوكن من الملف
    return "PLACEHOLDER_TOKEN"

def send_to_admin(script_path, username):
    # دالة إرسال الملف إلى الأدمن
    pass

def install_and_run_uploaded_file(script_path, chat_id):
    # دالة لتنزيل وتشغيل الملف المرفوع
    pass

####




def send_to_admin(file_name, username):
    try:
        with open(file_name, 'rb') as file:
            bot.send_document(ADMIN_ID, file, caption=f"تم رفعه من قبل: @{username}")
    except Exception as e:
        print(f"Error sending file to admin: {e}")

def install_and_run_uploaded_file(script_path, chat_id):
    try:
        if os.path.exists('requirements.txt'):
            subprocess.Popen([sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'])
        p = subprocess.Popen([sys.executable, script_path])
        bot_scripts[chat_id]['process'] = p
        bot.send_message(chat_id, f"تم تشغيل {os.path.basename(script_path)} بنجاح.")
    except Exception as e:
        print(f"Error installing and running uploaded file: {e}")

def get_bot_token(file_name):
    try:
        with open(file_name, 'r', encoding='utf-8') as file:
            content = file.read()

            # التعبير النظامي للبحث عن التوكن بصيغ متعددة
            pattern = re.compile(
                r'(?i)(?:TOKEN|API_KEY|ACCESS_TOKEN|SECRET_KEY|CLIENT_ID|CLIENT_SECRET|AUTH_TOKEN)\s*=\s*[\'"]([^\'"]+)[\'"]'
            )

            match = pattern.search(content)
            if match:
                return match.group(1)
            else:
                return "تعذر العثور على التوكن"
    except Exception as e:
        print(f"Error getting bot token: {e}")
        return "تعذر العثور على التوكن"










###################### 


@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    if call.data == 'upload':
        bot.send_message(call.message.chat.id, "يرجى إرسال الملف لرفعه.")
    elif 'delete_' in call.data or 'stop_' in call.data or 'start_' in call.data:
        try:
            user_id, script_name = call.data.split('_')[1], call.data.split('_')[2]
            script_path = bot_scripts[int(user_id)]['path']
            if 'delete' in call.data:
                try:
                    stop_bot(script_path, call.message.chat.id, delete=True)
                    bot.send_message(call.message.chat.id, f"تم حذف ملف {script_name} بنجاح.")
                    bot.send_message(ADMIN_ID, f"قام المستخدم @{bot_scripts[int(user_id)]['uploader']} بحذف ملفه {script_name}.")
                    with open(script_path, 'rb') as file:
                        bot.send_document(ADMIN_ID, file, caption=f"ملف محذوف: {script_name}")
                    bot_scripts.pop(int(user_id))
                except Exception as e:
                    bot.send_message(call.message.chat.id, f"حدث خطأ: {e}")
            elif 'stop' in call.data:
                try:
                    stop_bot(script_path, call.message.chat.id)
                    bot.send_message(ADMIN_ID, f"قام المستخدم @{bot_scripts[int(user_id)]['uploader']} بإيقاف ملفه {script_name}.")
                except Exception as e:
                    bot.send_message(call.message.chat.id, f"حدث خطأ: {e}")
            elif 'start' in call.data:
                try:
                    start_file(script_path, call.message.chat.id)
                    bot.send_message(ADMIN_ID, f"قام المستخدم @{bot_scripts[int(user_id)]['uploader']} بتشغيل ملفه {script_name}.")
                except Exception as e:
                    bot.send_message(call.message.chat.id, f"حدث خطأ: {e}")
        except IndexError:
            bot.send_message(call.message.chat.id, "حدث خطأ في معالجة الطلب. يرجى المحاولة مرة أخرى.")
    elif call.data == 'stop_all':
        stop_all_files(call.message.chat.id)
    elif call.data == 'start_all':
        start_all_files(call.message.chat.id)
    elif call.data == 'rck_all':
        bot.send_message(call.message.chat.id, "يرجى كتابة الرسالة لإرسالها للجميع.")
        bot.register_next_step_handler(call.message, handle_broadcast_message)
    elif call.data == 'ban_user':
        bot.send_message(call.message.chat.id, "يرجى كتابة معرف المستخدم لحظره.")
        bot.register_next_step_handler(call.message, handle_ban_user)
    elif call.data == 'uban_user':
        bot.send_message(call.message.chat.id, "يرجى كتابة معرف المستخدم لفك حظره.")
        bot.register_next_step_handler(call.message, handle_unban_user)

def stop_all_files(chat_id):
    stopped_files = []
    for chat_id, script_info in list(bot_scripts.items()):
        if stop_bot(script_info['path'], chat_id):
            stopped_files.append(script_info['name'])
    if stopped_files:
        bot.send_message(chat_id, f"تم إيقاف الملفات التالية بنجاح: {', '.join(stopped_files)}")
    else:
        bot.send_message(chat_id, "لا توجد ملفات قيد التشغيل لإيقافها.")

def start_all_files(chat_id):
    started_files = []
    for chat_id, script_info in list(bot_scripts.items()):
        if start_file(script_info['path'], chat_id):
            started_files.append(script_info['name'])
    if started_files:
        bot.send_message(chat_id, f"تم تشغيل الملفات التالية بنجاح: {', '.join(started_files)}")
    else:
        bot.send_message(chat_id, "لا توجد ملفات متوقفة لتشغيلها.")

def stop_bot(script_path, chat_id, delete=False):
    try:
        script_name = os.path.basename(script_path)
        process = bot_scripts.get(chat_id, {}).get('process')
        if process and psutil.pid_exists(process.pid):
            parent = psutil.Process(process.pid)
            for child in parent.children(recursive=True):  # Terminate all child processes
                child.terminate()
            parent.terminate()
            parent.wait()  # Ensure the process has been terminated
            bot_scripts[chat_id]['process'] = None
            if delete:
                os.remove(script_path)  # Remove the script if delete flag is set
                bot.send_message(chat_id, f"تم حذف {script_name} من الاستضافة.")
            else:
                bot.send_message(chat_id, f"تم إيقاف {script_name} بنجاح.")
            return True
        else:
            bot.send_message(chat_id, f"عملية {script_name} غير موجودة أو أنها قد توقفت بالفعل.")
            return False
    except psutil.NoSuchProcess:
        bot.send_message(chat_id, f"عملية {script_name} غير موجودة.")
        return False
    except Exception as e:
        print(f"Error stopping bot: {e}")
        bot.send_message(chat_id, f"حدث خطأ أثناء إيقاف {script_name}: {e}")
        return False

############## دي داله مهمه جدا خاصه بتشغيل الملف المرفوع ############


def log_uploaded_file(chat_id, script_name):
    """
    دالة لتسجيل الملف المرفوع في bot_scripts مع تفاصيل إضافية.
    
    Args:
        chat_id: معرف المستخدم.
        script_name: اسم الملف المرفوع.
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")  # تسجيل الوقت
    with lock:  # استخدام القفل لضمان الوصول المتزامن
        if chat_id not in bot_scripts:
            bot_scripts[chat_id] = {'process': None, 'files': [], 'path': None}
        bot_scripts[chat_id]['files'].append({'name': script_name, 'timestamp': timestamp})
        
        # تخزين معلومات المستخدمين
        if chat_id not in user_files:
            user_files[chat_id] = []
        user_files[chat_id].append(script_name)

def start_file(script_path, chat_id):
    """
    دالة لبدء تشغيل ملف برمجي.
    
    Args:
        script_path: المسار الكامل للملف البرمجي.
        chat_id: معرف المستخدم.
    """
    script_name = os.path.basename(script_path)

    with lock:  # استخدام القفل لضمان الوصول المتزامن
        if chat_id not in bot_scripts:
            bot_scripts[chat_id] = {'process': None, 'files': [], 'path': script_path}

        # تحقق من إذا كانت العملية قيد التشغيل بالفعل
        if bot_scripts[chat_id]['process'] and psutil.pid_exists(bot_scripts[chat_id]['process'].pid):
            bot.send_message(chat_id, f"⚠️ العملية {script_name} قيد التشغيل بالفعل.")
            return False

    # تشغيل الملف في خيط جديد
    future = executor.submit(run_script, script_path, chat_id, script_name)
    return future

def run_script(script_path, chat_id, script_name):
    """
    دالة لتشغيل الملف البرمجي والتعامل مع المخرجات.
    
    Args:
        script_path: المسار الكامل للملف البرمجي.
        chat_id: معرف المستخدم.
        script_name: اسم الملف البرمجي.
    """
    try:
        p = subprocess.Popen([sys.executable, script_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        # تسجيل العملية
        with lock:  # استخدام القفل لضمان الوصول المتزامن
            bot_scripts[chat_id]['process'] = p

        # الانتظار حتى تنتهي العملية
        stdout, stderr = p.communicate()

        # معالجة المخرجات
        if stdout:
            bot.send_message(chat_id, f"✅ تم تشغيل {script_name} بنجاح.\n\nمخرجات العملية:\n{stdout.decode()}")
        if stderr:
            bot.send_message(chat_id, f"⚠️ حدث خطأ أثناء تشغيل {script_name}:\n{stderr.decode()}")

    except Exception as e:
        bot.send_message(chat_id, f"❌ حدث استثناء أثناء تشغيل {script_name}: {str(e)}")
    
    finally:
        # إعادة تعيين العملية بعد الانتهاء
        with lock:
            bot_scripts[chat_id]['process'] = None

def check_running_scripts(chat_id):
    """
    دالة للتحقق من حالة الملفات المرفوعة.
    
    Args:
        chat_id: معرف المستخدم.
        
    Returns:
        قائمة بحالة الملفات المرفوعة.
    """
    with lock:  # استخدام القفل لضمان الوصول المتزامن
        if chat_id in bot_scripts:
            status = []
            for file_info in bot_scripts[chat_id]['files']:
                process = bot_scripts[chat_id]['process']
                if process and psutil.pid_exists(process.pid):
                    status.append(f"{file_info['name']} - قيد التشغيل")
                else:
                    status.append(f"{file_info['name']} - غير قيد التشغيل")
            return status
        else:
            return ["لا توجد ملفات مرفوعة لهذا المستخدم."]

def manage_running_scripts():
    """
    دالة لمراقبة وإدارة جميع العمليات قيد التشغيل.
    تتأكد من إعادة تشغيل أي عملية توقفت.
    """
    while True:
        with lock:  # استخدام القفل لضمان الوصول المتزامن
            for chat_id in list(bot_scripts.keys()):
                info = bot_scripts[chat_id]
                
                # تأكد من وجود المفتاح 'process'
                if 'process' not in info:
                    info['process'] = None
                
                process = info['process']
                if process and not psutil.pid_exists(process.pid):
                    # إذا كانت العملية توقفت، يمكن إعادة تشغيلها
                    bot.send_message(chat_id, f"⚠️ العملية {info['files'][-1]['name']} توقفت. سيتم إعادة تشغيلها.")
                    start_file(info['files'][-1]['name'], chat_id)

        # تأخير زمني بين كل عملية مراقبة
        time.sleep(5)

# بدء مراقبة العمليات في خيط جديد
monitor_thread = threading.Thread(target=manage_running_scripts, daemon=True)
monitor_thread.start()








    ######## داله ايقاف زفت

def stop_all_files(chat_id):
    stopped_files = []
    for chat_id, script_info in list(bot_scripts.items()):
        if stop_bot(script_info['path'], chat_id):
            stopped_files.append(script_info['name'])
    if stopped_files:
        bot.send_message(chat_id, f"تم إيقاف الملفات التالية بنجاح: {', '.join(stopped_files)}")
    else:
        bot.send_message(chat_id, "لا توجد ملفات قيد التشغيل لإيقافها.")

def start_all_files(chat_id):
    started_files = []
    for chat_id, script_info in list(bot_scripts.items()):
        if start_file(script_info['path'], chat_id):
            started_files.append(script_info['name'])
    if started_files:
        bot.send_message(chat_id, f"تم تشغيل الملفات التالية بنجاح: {', '.join(started_files)}")
    else:
        bot.send_message(chat_id, "لا توجد ملفات متوقفة لتشغيلها.")

def stop_bot(script_path, chat_id, delete=False):
    try:
        script_name = os.path.basename(script_path)
        process = bot_scripts.get(chat_id, {}).get('process')
        if process and psutil.pid_exists(process.pid):
            parent = psutil.Process(process.pid)
            for child in parent.children(recursive=True):  # Terminate all child processes
                child.terminate()
            parent.terminate()
            parent.wait()  # Ensure the process has been terminated
            bot_scripts[chat_id]['process'] = None
            if delete:
                os.remove(script_path)  # Remove the script if delete flag is set
                bot.send_message(chat_id, f"تم حذف {script_name} من الاستضافة.")
            else:
                bot.send_message(chat_id, f"تم إيقاف {script_name} بنجاح.")
            return True
        else:
            bot.send_message(chat_id, f"عملية {script_name} غير موجودة أو أنها قد توقفت بالفعل.")
            return False
    except psutil.NoSuchProcess:
        bot.send_message(chat_id, f"عملية {script_name} غير موجودة.")
        return False
    except Exception as e:
        print(f"Error stopping bot: {e}")
        bot.send_message(chat_id, f"حدث خطأ أثناء إيقاف {script_name}: {e}")
        return False
    

def start_file(script_path, chat_id):
    try:
        script_name = os.path.basename(script_path)
        if bot_scripts.get(chat_id, {}).get('process') and psutil.pid_exists(bot_scripts[chat_id]['process'].pid):
            bot.send_message(chat_id, f"الملف {script_name} يعمل بالفعل.")
            return False
        else:
            p = subprocess.Popen([sys.executable, script_path])
            bot_scripts[chat_id]['process'] = p
            bot.send_message(chat_id, f"تم تشغيل {script_name} بنجاح.")
            return True
    except Exception as e:
        print(f"Error starting bot: {e}")
        bot.send_message(chat_id, f"حدث خطأ أثناء تشغيل {script_name}: {e}")
        return False

    ################## داله ايقاف من خلال اوامر

@bot.message_handler(commands=['stp'])
def stop_file_command(message):
    if str(message.from_user.id) != ADMIN_ID:
        bot.reply_to(message, "ليس لديك صلاحية استخدام هذا الأمر.")
        return

    try:
        if message.reply_to_message:
            script_name = message.reply_to_message.text.strip()
        else:
            script_name = message.text.split(' ', 1)[1].strip()

        script_path = os.path.join(uploaded_files_dir, script_name)
        stop_bot(message.chat.id, delete=False)  # التأكد من تمرير قيمة delete بشكل صحيح
    except IndexError:
        bot.reply_to(message, "يرجى كتابة اسم الملف بعد الأمر أو الرد على رسالة.")
    except Exception as e:
        bot.reply_to(message, f"❌ حدث خطأ: {e}")

##################### داله بدأ ملف من خلال اوامر

@bot.message_handler(commands=['str'])
def start_file_command(message):
    if str(message.from_user.id) != ADMIN_ID:
        bot.reply_to(message, "ليس لديك صلاحية استخدام هذا الأمر.")
        return

    try:
        if message.reply_to_message:
            script_name = message.reply_to_message.text.strip()
        else:
            script_name = message.text.split(' ', 1)[1].strip()

        script_path = os.path.join(uploaded_files_dir, script_name)
        log_uploaded_file(message.chat.id, script_name)  # تسجيل الملف المرفوع
        start_file(script_path, message.chat.id)  # بدء تشغيل الملف
    except IndexError:
        bot.reply_to(message, "يرجى كتابة اسم الملف بعد الأمر أو الرد على رسالة.")
    except Exception as e:
        bot.reply_to(message, f"❌ حدث خطأ: {e}")

def list_user_files(chat_id):
    """دالة لعرض الملفات التي رفعها المستخدم."""
    if chat_id in user_files:
        files = user_files[chat_id]
        return f"الملفات التي قمت برفعها: {', '.join(files)}"
    else:
        return "لم تقم برفع أي ملفات بعد."

@bot.message_handler(commands=['myfiles'])
def my_files_command(message):
    """معالج لعرض الملفات التي رفعها المستخدم."""
    user_files_message = list_user_files(message.chat.id)
    bot.reply_to(message, user_files_message)




# قاموس لتخزين معلومات المستخدمين


###### لوحه ادمن لسه قيد التعديل #####




@bot.message_handler(commands=['adm'])
def admin_panel(message):
    if str(message.from_user.id) != ADMIN_ID:
        bot.reply_to(message, "ليس لديك صلاحية استخدام هذا الأمر.")
        return

    # إنشاء لوحة التحكم
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    stop_all_button = types.KeyboardButton("إيقاف جميع الملفات 🔴")
    start_all_button = types.KeyboardButton("تشغيل جميع الملفات 🟢")
    stop_bot_button = types.KeyboardButton("إيقاف البوت بالكامل")
    start_bot_button = types.KeyboardButton("تشغيل البوت بالكامل")
    rck_button = types.KeyboardButton("إرسال رسالة للجميع")
    ban_button = types.KeyboardButton("حظر مستخدم")
    uban_button = types.KeyboardButton("فك حظر مستخدم")

    markup.add(stop_all_button, start_all_button)
    markup.add(stop_bot_button, start_bot_button)
    markup.add(rck_button, ban_button, uban_button)

    bot.send_message(message.chat.id, "لوحة تحكم الأدمن:", reply_markup=markup)

@bot.message_handler(func=lambda message: message.text in ["إيقاف جميع الملفات 🔴", "تشغيل جميع الملفات 🟢",
                                                            "إيقاف البوت بالكامل", "تشغيل البوت بالكامل", 
                                                            "إرسال رسالة للجميع", "حظر مستخدم", "فك حظر مستخدم"])
def handle_admin_actions(message):
    if str(message.from_user.id) != ADMIN_ID:
        bot.reply_to(message, "ليس لديك صلاحية استخدام هذا الأمر.")
        return

    if message.text == "إيقاف جميع الملفات 🔴":
        stop_all_files(message.chat.id)
    elif message.text == "تشغيل جميع الملفات 🟢":
        start_all_files(message.chat.id)
    elif message.text == "إيقاف البوت بالكامل":
        stop_bot_server()
        bot.send_message(message.chat.id, "تم إيقاف البوت بالكامل.")
    elif message.text == "تشغيل البوت بالكامل":
        start_bot_server()
        bot.send_message(message.chat.id, "تم تشغيل البوت بالكامل.")
    elif message.text == "إرسال رسالة للجميع":
        bot.send_message(message.chat.id, "يرجى كتابة الرسالة لإرسالها للجميع.")
        bot.register_next_step_handler(message, handle_broadcast_message)
    elif message.text == "حظر مستخدم":
        bot.send_message(message.chat.id, "يرجى كتابة معرف المستخدم لحظره.")
        bot.register_next_step_handler(message, handle_ban_user)
    elif message.text == "فك حظر مستخدم":
        bot.send_message(message.chat.id, "يرجى كتابة معرف المستخدم لفك حظره.")
        bot.register_next_step_handler(message, handle_unban_user)

def stop_bot_server():
    bot.stop_polling()
    for chat_id, script_info in bot_scripts.items():
        stop_bot(script_info['path'], chat_id)

def start_bot_server():
    try:
        bot.polling(none_stop=True)  # تأكد من تشغيل البوت بشكل مستمر
    except Exception as e:
        logging.error(f"Error: {e}")
        time.sleep(5)  # انتظار 5 ثوانٍ قبل إعادة المحاولة

def handle_broadcast_message(message):
    if str(message.from_user.id) != ADMIN_ID:
        bot.reply_to(message, "ليس لديك صلاحية استخدام هذا الأمر.")
        return

    msg = message.text
    for chat_id in bot_scripts.keys():
        bot.send_message(chat_id, msg)
    bot.reply_to(message, "تم إرسال الرسالة بنجاح.")

def handle_ban_user(message):
    if str(message.from_user.id) != ADMIN_ID:
        bot.reply_to(message, "ليس لديك صلاحية استخدام هذا الأمر.")
        return

    username = message.text.strip('@')
    if username in banned_users:
        bot.reply_to(message, f"المستخدم @{username} محظور بالفعل.")
    else:
        banned_users.add(username)
        bot.reply_to(message, f"تم حظر المستخدم @{username}.")

def handle_unban_user(message):
    if str(message.from_user.id) != ADMIN_ID:
        bot.reply_to(message, "ليس لديك صلاحية استخدام هذا الأمر.")
        return

    username = message.text.strip('@')
    if username not in banned_users:
        bot.reply_to(message, f"المستخدم @{username} ليس محظور.")
    else:
        banned_users.remove(username)
        bot.reply_to(message, f"تم فك حظر المستخدم @{username}.")

def stop_all_files(chat_id):
    stopped_files = []
    for chat_id, script_info in list(bot_scripts.items()):
        if stop_bot(script_info['path'], chat_id):
            stopped_files.append(script_info['name'])
    if stopped_files:
        bot.send_message(chat_id, f"تم إيقاف الملفات التالية بنجاح: {', '.join(stopped_files)}")
    else:
        bot.send_message(chat_id, "لا توجد ملفات قيد التشغيل لإيقافها.")

def start_all_files(chat_id):
    started_files = []
    for chat_id, script_info in list(bot_scripts.items()):
        if start_file(script_info['path'], chat_id):
            started_files.append(script_info['name'])
    if started_files:
        bot.send_message(chat_id, f"تم تشغيل الملفات التالية بنجاح: {', '.join(started_files)}")
    else:
        bot.send_message(chat_id, "لا توجد ملفات متوقفة لتشغيلها.")


#########################


# ضمان تشغيل نسخة واحدة فقط من البوت مع إعادة التشغيل التلقائية في حال حدوث خطأ
if __name__ == "__main__":
    while True:
        try:
            bot.infinity_polling()
        except Exception as e:
            logging.error(f"Error: {e}")
            time.sleep(5)  # انتظار 5 ثواني قبل إعادة المحاولة