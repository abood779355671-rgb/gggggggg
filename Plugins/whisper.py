"""
الهمسة - نظام الرسائل السرية
الطرق:
  1) inline:   @البوت همستك @username
  2) deep link من private_sudos: t.me/bot?start=w_USERNAME
  3) زر "اهمس لـ ." في إشعار الاستلام
"""
import random
import string
import pytz
from datetime import datetime

from pyrogram import Client, filters
from pyrogram.enums import ParseMode
from pyrogram.types import (
    InlineQuery, InlineQueryResultArticle, InputTextMessageContent,
    InlineKeyboardMarkup, InlineKeyboardButton,
    CallbackQuery, Message,
)

from config import ar


# ─────────────────────────────────────────────────────────────────────────
# مساعدات
# ─────────────────────────────────────────────────────────────────────────

def _gen_id(n=8) -> str:
    return "".join(random.choices(string.ascii_letters + string.digits, k=n))


def _time_now(tz_name="Asia/Riyadh") -> str:
    tz  = pytz.timezone(tz_name)
    now = datetime.now(tz)
    return now.strftime("%I:%M %p")


def _is_whisper_query(q: str) -> bool:
    if not q:
        return False
    for marker in ("SOUND", "#AUDIO", "#VOICE", "#MUSIC"):
        if marker in q:
            return False
    if "@" not in q:
        return False
    parts    = q.split("@", 1)
    msg_text = parts[0].strip()
    target   = parts[1].strip()
    if not msg_text or not target or " " in target:
        return False
    return True


def _state_key(uid: int) -> str:
    return f"whisper_state:{uid}"


# ─────────────────────────────────────────────────────────────────────────
# دالة تُستدعى من private_sudos عند deep link w_USERNAME
# ─────────────────────────────────────────────────────────────────────────

async def _whisper_start_private(c: Client, m: Message, target_raw: str):
    uid = m.from_user.id
    try:
        u = await c.get_users(target_raw)
    except Exception:
        await m.reply("❌ اليوزر غير موجود أو خاطئ.")
        return

    display = u.first_name
    # نخزن: "uid_targetid" كمفتاح منفصل لتجنب تعارض : في الاسم
    await ar.set(_state_key(uid), f"await_msg|{u.id}|{display}", ex=300)
    await m.reply(
        f"• تم تحديد الهمسة لـ **{display}** ←\n"
        "• اضغط الزر لكتابة الهمسة",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("• همسة نصيه", callback_data=f"wp_type|{u.id}|{display[:30]}")
        ]])
    )


# ─────────────────────────────────────────────────────────────────────────
# زر "همسة نصية"
# ─────────────────────────────────────────────────────────────────────────

@Client.on_callback_query(filters.regex(r"^wp_type\|"))
async def whisper_type_cb(c: Client, cb: CallbackQuery):
    _, target_id, display = cb.data.split("|", 2)
    uid = cb.from_user.id

    await ar.set(_state_key(uid), f"await_msg|{target_id}|{display}", ex=300)
    await cb.answer("اكتب الهمسة في المحادثة الآن ✍️", show_alert=False)
    await cb.message.edit_text(
        f"• تم تحديد الهمسة لـ **{display}** ←\n"
        "• اكتب الهمسة الآن في المحادثة ✍️",
        parse_mode=ParseMode.MARKDOWN,
    )


# ─────────────────────────────────────────────────────────────────────────
# استقبال نص الهمسة في الخاص
# ─────────────────────────────────────────────────────────────────────────

@Client.on_message(
    filters.text & filters.private & ~filters.command(["start", "cancel"]),
    group=20
)
async def whisper_private_text(c: Client, m: Message):
    uid   = m.from_user.id
    state = await ar.get(_state_key(uid))

    if not state or not state.startswith("await_msg|"):
        return

    parts      = state.split("|", 2)
    target_id  = int(parts[1])
    display    = parts[2]
    msg_text   = m.text.strip()

    # احفظ الهمسة
    wid = _gen_id()
    await ar.set(f"w:{wid}", f"{uid}+{target_id}&msg={msg_text}", ex=86400)
    await ar.delete(_state_key(uid))

    # أخبر المرسل
    await m.reply(
        f"• تم ارسال همستك لـ **{display}** . بنجاح",
        parse_mode=ParseMode.MARKDOWN,
    )

    # إشعار للمستلم
    bot_me       = await c.get_me()
    bot_username = bot_me.username
    sender_name  = m.from_user.first_name
    sender_uname = m.from_user.username or str(uid)

    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("رؤية الهمسة", callback_data=f"w:{wid}")],
        [InlineKeyboardButton(
            f"اهمس لـ {sender_name} .",
            url=f"https://t.me/{bot_username}?start=w_{sender_uname}"
        )],
    ])

    try:
        target_user = await c.get_users(target_id)
        await c.send_message(
            target_id,
            f"• الهمسه لـ {target_user.first_name} ←\n"
            f"• من ←  {sender_name}\n"
            f"-",
            reply_markup=markup,
        )
    except Exception:
        await m.reply(
            f"⚠️ تعذّر إيصال الهمسة لـ **{display}** مباشرةً.\n"
            "(ربما لم يبدأ المحادثة مع البوت)",
            parse_mode=ParseMode.MARKDOWN,
        )


# ─────────────────────────────────────────────────────────────────────────
# همسة داخل القروب — يكتب "اهمس" رداً على رسالة شخص
# ─────────────────────────────────────────────────────────────────────────

@Client.on_message(
    filters.text & filters.group & filters.reply,
    group=15
)
async def group_whisper_trigger(c: Client, m: Message):
    txt = m.text.strip()
    # يشتغل فقط إذا الرسالة هي كلمة "اهمس" بالضبط
    if txt != "اهمس":
        return

    # لازم يكون رداً على رسالة شخص ثاني (مو على نفسه)
    replied = m.reply_to_message
    if not replied or not replied.from_user:
        return

    target    = replied.from_user
    sender    = m.from_user
    chat_id   = m.chat.id

    # احذف رسالة "اهمس" من القروب فوراً
    try:
        await m.delete()
    except Exception:
        pass

    bot_me       = await c.get_me()
    bot_username = bot_me.username
    sender_uname = sender.username or str(sender.id)
    target_uname = target.username or str(target.id)

    # أرسل رسالة في القروب مع زر "اهمس هنا"
    markup = InlineKeyboardMarkup([[
        InlineKeyboardButton(
            "🛡️ اهمس هنا",
            url=f"https://t.me/{bot_username}?start=w_{target_uname}"
        )
    ]])

    sent = await c.send_message(
        chat_id,
        f"• تم تحديد الهمسه لـ **{target.first_name}** ←\n"
        f"• اضغط الزر لكتابة الهمسة\n"
        f"-",
        reply_markup=markup,
        parse_mode=ParseMode.MARKDOWN,
    )

    # احذف رسالة البوت من القروب بعد 30 ثانية
    import asyncio
    async def _delete_later():
        await asyncio.sleep(30)
        try:
            await sent.delete()
        except Exception:
            pass
    asyncio.get_event_loop().create_task(_delete_later())


# ─────────────────────────────────────────────────────────────────────────
# inline query — همسة
# ─────────────────────────────────────────────────────────────────────────

@Client.on_inline_query(group=0)
async def inline_router(c: Client, query: InlineQuery):
    q = query.query.strip()
    if _is_whisper_query(q):
        await _handle_whisper(c, query, q)
    else:
        await _handle_help(c, query, q)


async def _handle_whisper(c: Client, query: InlineQuery, raw: str):
    parts      = raw.split("@", 1)
    msg_text   = parts[0].strip()
    target_raw = parts[1].strip()
    sender_id  = query.from_user.id

    if target_raw.lower() == "all":
        target_id = "all"
        display   = "الجميع 🎊"
        label     = "🎊 مفاجأة للجميع"
    else:
        try:
            u         = await c.get_users(target_raw)
            target_id = u.id
            display   = u.first_name
            label     = f"همسة لـ {display}"
        except Exception:
            await query.answer(
                results=[],
                switch_pm_text="❌ يوزر غير موجود",
                switch_pm_parameter="whisper_help",
                cache_time=1,
            )
            return

    wid = _gen_id()
    await ar.set(f"w:{wid}", f"{sender_id}+{target_id}&msg={msg_text}", ex=86400)

    card_text = (
        "🎊 همسة للجميع — اضغط لعرضها"
        if target_id == "all"
        else f"🔒 همسة سرية لـ {display} — فقط هو يقدر يشوفها 🕵️"
    )

    markup  = InlineKeyboardMarkup([[
        InlineKeyboardButton("📪 عرض الهمسة", callback_data=f"w:{wid}")
    ]])
    timenow = "🕐 " + _time_now()

    await query.answer(
        switch_pm_text="• كيف أستخدم الهمسة؟",
        switch_pm_parameter="whisper_help",
        results=[
            InlineQueryResultArticle(
                title=label,
                description=timenow,
                input_message_content=InputTextMessageContent(
                    card_text, parse_mode=ParseMode.MARKDOWN
                ),
                reply_markup=markup,
                thumb_url="https://i.imgur.com/7UaXuJt.png",
                thumb_width=64,
                thumb_height=64,
            )
        ],
        cache_time=1,
    )


async def _handle_help(c: Client, query: InlineQuery, q: str):
    for marker in ("SOUND", "#AUDIO", "#VOICE"):
        if marker in q:
            return

    await query.answer(
        switch_pm_text="• اكتب همستك + @username",
        switch_pm_parameter="whisper_help",
        results=[
            InlineQueryResultArticle(
                title="🔒 طريقة الاستخدام",
                description="@البوت  همستك  @username",
                input_message_content=InputTextMessageContent(
                    "`@البوت  همستك  @username`",
                    parse_mode=ParseMode.MARKDOWN,
                ),
                thumb_url="https://i.imgur.com/7UaXuJt.png",
                thumb_width=64,
                thumb_height=64,
            )
        ],
        cache_time=60,
    )


# ─────────────────────────────────────────────────────────────────────────
# callback: عرض الهمسة
# ─────────────────────────────────────────────────────────────────────────

@Client.on_callback_query(filters.regex(r"^w:"))
async def show_whisper(c: Client, cb: CallbackQuery):
    wid  = cb.data.split(":", 1)[1]
    data = await ar.get(f"w:{wid}")
    if not data:
        return await cb.answer("⏰ انتهت صلاحية الهمسة", show_alert=True)

    ids_part, msg_part = data.split("&msg=", 1)
    sender_id, target_id = ids_part.split("+", 1)
    viewer = cb.from_user.id

    if target_id == "all":
        await ar.delete(f"w:{wid}")
        return await cb.answer(f"🎊 {msg_part[:200]}", show_alert=True)

    if str(viewer) == sender_id or str(viewer) == target_id:
        if str(viewer) == target_id:
            await ar.delete(f"w:{wid}")
            try:
                await cb.message.edit_reply_markup(
                    InlineKeyboardMarkup([[
                        InlineKeyboardButton("📭 تم فتح الهمسة", callback_data=f"wx:{wid}")
                    ]])
                )
            except Exception:
                pass
        try:
            sender = await c.get_users(int(sender_id))
            sender_name = sender.first_name
        except Exception:
            sender_name = "."
        return await cb.answer(
            f"• تمت قراءة الهمسة .. بنجاح\n• من قبل ← {sender_name}\n\n{msg_part[:180]}",
            show_alert=True,
        )

    return await cb.answer("🔒 هذه الهمسة مو لك", show_alert=True)


@Client.on_callback_query(filters.regex(r"^wx:"))
async def whisper_opened_noop(c: Client, cb: CallbackQuery):
    await cb.answer("📭 تمت القراءة", show_alert=False)
