import os, re, requests, json
from keep_alive import keep_alive

import telegram.ext
from telegram import Update, InlineQueryResultPhoto, InlineQueryResultVoice, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CallbackQueryHandler, CallbackContext, InlineQueryHandler, CommandHandler, MessageHandler, Filters


from threading import Thread

from time import sleep, time
import traceback
from random import choice

from replit import db
from io import BytesIO

u = Updater(os.getenv('TG_TOKEN'))
j = u.job_queue


class Phrases:
    '''Шаблоны фраз, возвращает случайный шаблон фразы'''
    new_role_list = [
        "Well done, {0}! You're {1} now.",
        "I see, {0} wants a new role. Well, enjoy being {1}!",
        "Congrats, {0}! Here, {1} is yours."
    ]

    def new_role(name='Denis', role='nice guy', phrases=None):
        try:
            phrases = phrases or db['phrases']['new_role']
            return choice(phrases).format(name, role)
        except:
            return choice(Phrases.new_role_list).format(name, role)


def check_count(count: int, current_role=None):
    roles = db['roles']
    m = 0
    for role, n in roles.items():
        if n > count:
            return current_role
        if n > m:
            m = n
            current_role = role
    return current_role


# -= КОМАНДЫ ОБЛАДАТЕЛЯ БОТА =- #

def start(update: Update, context: CallbackContext):
    msg = update.message
    print(msg.to_dict())
    chat_id = str(msg.chat_id)
    if msg.chat.type == 'private':
        if chat_id in os.getenv('OWNER_ID'):
            if 'chats' not in db:
                msg.reply_text("I'm alive!")
            else:
                return msg.reply_text('Here we go again...')
        else:
            return msg.reply_text('Here we go again...')
    
    if 'chats' not in db:
        db['chats'] = {}
        
    if chat_id not in db['chats']:
        db['chats'][chat_id] = {
            'users': {}, 
            'roles': {},
            'phrases': []
        }
    if 'settings' not in db:
        db['settings'] = {
            'notifications': 1,
            'mentions': 1,
            'delay': 0
        }

def update_roles(update: Update, context: CallbackContext):
    '''Добавление и изменение ролей'''
    msg = update.message
    if str(msg.from_user.id) != os.getenv('OWNER_ID'):
        return 
    if 'roles' not in db:
        db['roles'] = {}
        db['counts'] = {}
    if not msg.reply_to_message:
        return msg.reply_text('Send me message a list of roles. Please, use this format: \n\nrole1 - message count \nrole2 - another message count\n\n then send /update_roles in reply to your message.')
    for line in msg.reply_to_message.text.split('\n'):
        role, count = line.split('-')
        db['roles'][role.strip()] = int(count.strip())
        db['counts'][count.strip()] = role.strip()
    msg.reply_text('Done!')

def delete_roles(update: Update, context: CallbackContext):
    msg = update.message
    if str(msg.from_user.id) != os.getenv('OWNER_ID'):
        return 
    if 'roles' in db:
        db['roles'] = {}
        db['counts'] = {}
        msg.reply_text('Done!')


def update_phrases(update: Update, context: CallbackContext):
    msg = update.message
    chat_id = str(msg.chat_id)
    user_status = msg.chat.get_member(msg.from_user.id).status
    if str(msg.from_user.id) != os.getenv('OWNER_ID') or user_status not in ('administrator', 'creator'):
        return 
    if 'phrases' not in db:
        db['phrases'] = {'new_role': []}
    if not msg.reply_to_message:
        return msg.reply_text('Send me message a list of phrases. Please, use this format:\n\nWay to go, {0}! Now you\'re {1}.\n{0} got role {1}\n\n then send /phrases in reply to your message.\n\nSend /show_phrases to see them/ ({0} is name, {1} is role)')
    if chat_id in db['chats']:
        db['chats'][chat_id]['phrases'] = msg.reply_to_message.text.split('\n')
    else:
        db['phrases']['new_role'] = msg.reply_to_message.text.split('\n')
    msg.reply_text('Done!')

def show_phrases(update: Update, context: CallbackContext):
    msg = update.message
    user_status = msg.chat.get_member(msg.from_user.id).status
    if str(msg.from_user.id) != os.getenv('OWNER_ID') or user_status not in ('administrator', 'creator'):
        return
    phrases = db['chats'].get(str(msg.chat_id), {}).get('phrases', [])
    return msg.reply_text('\n'.join(phrases or db.get('phrases', {}).get('new_role') or Phrases.new_role_list))


# -= НАСТРОЙКИ ДЛЯ ОБЛАДАТЕЛЯ БОТА =- #

def notifications(update: Update, context: CallbackContext):
    '''Уведомление о повышении роли'''
    msg = update.message
    if str(msg.from_user.id) != os.getenv('OWNER_ID'):
        return
    if len(msg.text.split()) == 1:
        return msg.reply_text('Value: %d\n\nTo change it, send /notifications message count' % db['settings']['notifications'])
    n = msg.text.split()[1]
    n = db['roles'].get(n, n)
    if n.isdigit():
        db['settings']['notfications'] = int(n)
        return msg.reply_text('Done!')

def mentions(update: Update, context: CallbackContext):
    '''Упоминание обладателей роли'''
    msg = update.message
    if str(msg.from_user.id) != os.getenv('OWNER_ID'):
        return
    if len(msg.text.split()) == 1:
        return msg.reply_text('Value: %d\n\nTo change it, send /mentions message count' % db['settings']['mentions'])
    n = msg.text.split()[1]
    n = db['roles'].get(n, n)
    if n.isdigit():
        db['settings']['mentions'] = int(n)
        return msg.reply_text('Done!')

def delay(update: Update, context: CallbackContext):
    '''Разница между учитываемыми сообщениями'''
    msg = update.message
    if str(msg.from_user.id) != os.getenv('OWNER_ID'):
        return
    if len(msg.text.split()) == 1:
        return msg.reply_text('Value: %d secs\n\nTo change it, send /delay seconds' % db['settings']['delay'])
    n = msg.text.split()[1]
    if n.isdigit():
        db['settings']['delay'] = int(n)
        return msg.reply_text('Done!')

def reset(update: Update, context: CallbackContext):
    msg = update.message
    user_status = msg.chat.get_member(msg.from_user.id).status
    if str(msg.from_user.id) != os.getenv('OWNER_ID') or user_status not in ('administrator', 'creator'):
        return 
    chat_id = str(msg.chat_id)
    if chat_id in db['chats']:
        db['chats'][chat_id] = {'users': {}, 'roles': {}, 'phrases': []}
        msg.reply_text('Reset went well!')


# -= КОМАНДЫ С РОЛЯМИ =- #

def mention(update: Update, context: CallbackContext):
    msg = update.message
    chat_id = str(msg.chat_id)
    role = ' '.join(msg.text.split()[1:]).strip()
    if chat_id not in db['chats']:
        return msg.reply_text('Roles are not enabled for this chat')
    chat = db['chats'][chat_id]
    from_user = chat['users'].get(str(msg.from_user.id), {
        'name': msg.from_user.full_name,
        'count': 0, 
        'role': 'no role',
        'last_message': 0,
    })
    if not role:
        return msg.reply_text('To mention a role, send /mention "your role" without quotes, for example, /mention %s' % from_user['role'])
    if role not in chat['roles']:
        return msg.reply_text('Role <%s> is not found. To see the role list: /roles'%role)

    if db['roles'].get(from_user['role'], 0) > db['roles'][role]:
        msg.reply_text("Your role doesn't have permission to do that.")
    
    return msg.reply_text('role <%s> holders, over here! ' % role + ', '.join(f"[{user['name']}](tg://user?id={user_id})" for user_id, user in chat['users'].items()), parse_mode='Markdown')


# -= ОБЩИЕ КОМАНДЫ =- #

def show_roles(update: Update, context: CallbackContext):
    return update.message.reply_text('\n'.join(role + ' - %d' % count for role, count in sorted(db['roles'].items(), key=lambda item:item[1], reverse=True)) or 'Empty list')


def show_rating(update: Update, context: CallbackContext):
    '''Отображает все роли (или одну, если указать) и каждого пользователя в порядке убываний количества сообщений в'''
    msg = update.message
    chat_id = str(msg.chat_id)
    if chat_id not in db['chats']:
        return msg.reply_text('Roles are not enabled in this chat')
    chat = db['chats'][chat_id]
    users = chat['users']
    rating = '' 
    sorted_users = sorted(users.values(), key=lambda user:user['count'], reverse=True)
    for user in sorted_users:
        user_rating = f"<{user['role']}> {user['name']} | {user['count']}"
        if len(rating + user_rating) < 4096:
            rating += user_rating + '\n'
        if rating.count('\n') == 20:
            break 
    if str(msg.from_user.id) in os.getenv('OWNER_ID'):
        msg.from_user.send_message( '\n'.join(f"<{user['role']}> {user['name']} | {user['count']}" for user in sorted_users))
        

    return msg.reply_text(rating or 'Empty list')

def me(update: Update, context: CallbackContext):
    msg = update.message
    chat_id = str(msg.chat_id)
    if chat_id not in db['chats']:
        return msg.reply_text('Roles are not enabled in this chat')
    user = db['chats'][chat_id]['users'].get(str(msg.from_user.id))
    return update.message.reply_text(f"{user['name']}\nRole: <{user['role']}>\nMessage count: {user['count']}")

def help(update: Update, context: CallbackContext):
    msg = update.message
    return msg.reply_text(help_message_owner*(str(msg.chat_id) in os.getenv('OWNER_ID'))+help_message)
    

# -= ОБРАБОТКА СООБЩЕНИЙ =-

def new_message(update: Update, context: CallbackContext):
    msg = update.message
    if not msg:
        return
    print(msg.chat_id, msg.text)
    chat_id = str(msg.chat_id)
    from_id = str(msg.from_user.id)
    if msg.chat.type == 'private' or chat_id not in db['chats']:
        if from_id in os.getenv('OWNER_ID'):
            msg.reply_text('Send /start to enable roles in this chat.')
        return
    
    if msg.new_chat_members and hello[db['chats'][chat_id]['lang']]:
        for user in msg.new_chat_members:
            msg.chat.send_message(hello[db['chats'][chat_id]['lang']]%f'{msg.from_user.first_name} @{msg.from_user.username or " "}'.replace(' @ ', ''), reply_markup=keyboard)
        return msg.delete()
    user = db['chats'][chat_id]['users'].get(from_id, {
        'id': from_id,
        'name': msg.from_user.full_name,
        'count': 0, 
        'role': '',
        'last_message': 0,
    })

    # если сообщение отправлено слишком быстро, его не нужно считать
    if msg.date.timestamp() - user['last_message'] < db['settings']['delay']:
        return

    user['last_message'] = msg.date.timestamp()

    user['count'] += 1

    role = check_count(user['count'], user['role'])
    if role != user['role']:
        if user['count'] >= db['settings']['notifications']:
            pass
            # context.bot.send_message(chat_id, Phrases.new_role(msg.from_user.full_name, role, db['chats'][chat_id]['phrases']))
        if user['role'] in db['chats'][chat_id]['roles']:
            db['chats'][chat_id]['roles'][user['role']].remove(from_id)
        user['role'] = role
        if role not in db['chats'][chat_id]['roles']:
            db['chats'][chat_id]['roles'][role] = []
        db['chats'][chat_id]['roles'][role].append(from_id)
        
    db['chats'][chat_id]['users'][from_id] = user

def error_handler(update: Update, context: CallbackContext):
    if isinstance(context.error, telegram.error.RetryAfter):
        sleep(context.error.retry_after)
        u.dispatcher.process_update(update)
    else:
        print(update.to_dict())
        raise context.error


help_message_owner = '''
Hold a command to add something to it

/start - enables roles in current chat (not private one)

/update_roles - adds new roles to the list or/and change message counts
/delete_roles - deletes all roles

/phrases - changes phrases

/notifications count - shows or changes message count about reaching a new role
/mentions count - shows or changes message count for permission to mention
/delay n - shows or changes delay in secs between messages that will be count

/reset - reset chat history for bot
'''

help_message = '''
/mention role - tags people with this role

/roles - shows role list
/rating - shows the overall rating
/me - shows your rating
'''

hello = ['''
👋 Добро пожаловать, %s!

😄 Рады приветствовать тебя в русскоязычном сообществе Bohemian Bulldogs!

✅ Пожалуйста, соблюдай правила /rules
''', '''
👋 Welcome, %s!

😄 We're glad to see you in Bohemian Bulldogs chat!

✅ Please, follow the /rules
''', '''
👋 Hoş geldin %s!

😄 Sizi Bohemian Bulldogs'un türkçe konuşan topluluğunda gördüğümüze sevindik!

✅ Lütfen kurallara uyun /rules
''', '''
👋 ¡Bienvenido, %s!

😄 ¡Nos alegra verte en la comunidad de habla hispana de Bohemian Bulldogs!

✅ Por favor, siga las reglas /rules
'''
]

def show_rules(update: Update, context: CallbackContext):
    rules = ['❗️ _В нашем телеграмм сообществе запрещены_ ❗️\n\n*1️⃣ - Ругательства\n2️⃣ - Реклама и спам\n3️⃣ - Обсуждение порнографии и наркотиков\n4️⃣ - Оскорбления и неуважение к другим участникам\n5️⃣ - Религиозные и политические темы*', '❗️ _In our telegram community are prohibited_ ❗️\n\n*1️⃣ - Swearing\n2️⃣ - Advertising and Spam\n3️⃣ - Discussion of porn and drugs\n4️⃣ - Insults and disrespect to other participants\n5️⃣ - Religious and political topics*', '❗️ _Telegram topluluğumuzda bu şeyler yasaklandı_ ❗️\n\n*1️⃣ - Yemin etme\n2️⃣ - Reklam ve Spam\n3️⃣ - Porno ve uyuşturucu tartışması\n4️⃣ - Diğer katılımcılara hakaret ve saygısızlık\n5️⃣ - Dini ve siyasi konular*', '❗️ _En nuestra comunidad de telegram están prohibidos_ ❗️\n\n*1️⃣ - Jurar\n2️⃣ - Publicidad y Spam\n3️⃣ - Discusión de porno y drogas\n4️⃣ - Insultos y falta de respeto a otros participantes\n5️⃣ - Temas religiosos y políticos*']
    msg = update.message
    if msg.chat.type == 'private':
        if str(msg.from_user.id) in os.getenv('OWNER_ID'):
            return msg.reply_text('\n\n\n'.join(rules), 'Markdown')
        return msg.delete()
    chat_id = str(msg.chat_id)
    if chat_id in db['chats']:
        return msg.chat.send_message(rules[db['chats'][chat_id]['lang']], 'Markdown')

def say_hello(update: Update, context: CallbackContext):
    msg = update.message
    if str(msg.chat_id) in os.getenv('OWNER_ID'):
        msg.reply_text('\n\n'.join(hello)%(('имя @ник',)*4))

keyboard = InlineKeyboardMarkup([
    [
    InlineKeyboardButton('🖼 Instagram', 'https://www.instagram.com/bohemianbulldogz/'),
    InlineKeyboardButton('🔷 Twitter', 'https://twitter.com/BohemianDogs'),
    InlineKeyboardButton('✈️ Telegram', 'https://t.me/BohemianBulldogs_channel')
    ],[
    InlineKeyboardButton('🌐 Website', 'https://bohemian-bulldogs.com/'),
    InlineKeyboardButton('👾 Discord', 'https://discord.com/invite/bohemian-bulldogs'),
    InlineKeyboardButton('💧 Opensea', 'https://opensea.io/collection/bb-bohemian-bulldogs')
]])

u.dispatcher.add_handler(CommandHandler('start', start))
u.dispatcher.add_handler(CommandHandler('update_roles', update_roles))
u.dispatcher.add_handler(CommandHandler('delete_roles', delete_roles))
u.dispatcher.add_handler(CommandHandler('update_phrases', update_phrases))
u.dispatcher.add_handler(CommandHandler('phrases', show_phrases))
u.dispatcher.add_handler(CommandHandler('notifications', notifications))
u.dispatcher.add_handler(CommandHandler('mentions', mentions))
u.dispatcher.add_handler(CommandHandler('mention', mention))
u.dispatcher.add_handler(CommandHandler('roles', show_roles))
u.dispatcher.add_handler(CommandHandler('me', me))
u.dispatcher.add_handler(CommandHandler('rating', show_rating))
u.dispatcher.add_handler(CommandHandler('rules', show_rules))
u.dispatcher.add_handler(CommandHandler('hello', say_hello))
u.dispatcher.add_handler(CommandHandler('help', help))
u.dispatcher.add_handler(CommandHandler('reset', reset))
u.dispatcher.add_handler(MessageHandler(Filters.all, new_message))

u.dispatcher.add_error_handler(error_handler)

keep_alive()

u.start_polling()

u.idle()