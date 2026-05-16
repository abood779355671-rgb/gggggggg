"""
الهمسة - نظام الرسائل السرية عبر inline
الاستخدام: @البوت همستك @username
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
    CallbackQuery,
)

from config import r, DEV_ID, botkey


def _gen_id(n=8) -> str:
    return "".join(random.choices(string.ascii_letters + string.digits, k=n))


def _time_now(tz_name="Asia/Riyadh") -> str:
    tz  = pytz.timezone(tz_name)
    now = datetime.now(tz)
    return now.strftime("%I:%M %p")


# ─────────────── inline query ────────────────────────────────────────────

# ✅ إصلاح: نستخدم group=-1 لأولوية أعلى
@Client.on_inline_query(filters.regex(r".+@\S+"), group=-1)
async def send_whisper(c: Client, query: InlineQuery):
    # تجاهل SOUND queries (خاصة بالساوند كلاود)
    if "SOUND" in query.query or "#AUDIO" in query.query or "#VOICE" in query.query:
        return

    raw   = query.query
    parts = raw.split("@", 1)
    if len(parts) < 2:
        return
    msg_text, target_raw = parts[0].strip(), parts[1].strip()
    if not msg_text or " " in target_raw:
        return

    sender_id = query.from_user.id

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
            return

    wid = _gen_id()
    r.set(f"w:{wid}", f"{sender_id}+{target_id}&msg={msg_text}", ex=86400)

    if target_id == "all":
        card_text = "🎊 همسة للجميع — اضغط لعرضها"
    else:
        card_text = f"🔒 همسة سرية لـ {display} — فقط هو يقدر يشوفها 🕵️"

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


# ✅ إصلاح: الـ fallback يتجاهل SOUND و queries الفارغة
@Client.on_inline_query(group=-1)
async def whisper_help_inline(c: Client, query: InlineQuery):
    """رد افتراضي عند فتح inline بدون صياغة صحيحة"""
    q = query.query.strip()

    # تجاهل أي شيء خاص بالساوند كلاود أو اليوتيوب
    if "SOUND" in q or "#AUDIO" in q or "#VOICE" in q:
        return

    # لو القيمة فيها @ بالفعل → معناها send_whisper يعالجها
    if "@" in q:
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


# ─────────────── callback: عرض الهمسة ───────────────────────────────────

@Client.on_callback_query(filters.regex(r"^w:"))
async def show_whisper(c: Client, cb: CallbackQuery):
    wid  = cb.data.split(":", 1)[1]
    data = r.get(f"w:{wid}")
    if not data:
        return await cb.answer("⏰ انتهت صلاحية الهمسة", show_alert=True)

    ids_part, msg_part = data.split("&msg=", 1)
    sender_id, target_id = ids_part.split("+", 1)

    viewer = cb.from_user.id

    if target_id == "all":
        r.delete(f"w:{wid}")
        return await cb.answer(f"🎊 {msg_part[:200]}", show_alert=True)

    if str(viewer) == sender_id or str(viewer) == target_id:
        if str(viewer) == target_id:
            r.delete(f"w:{wid}")
            try:
                await cb.message.edit_reply_markup(
                    InlineKeyboardMarkup([[
                        InlineKeyboardButton("📭 تم فتح الهمسة", callback_data=f"w:{wid}")
                    ]])
                )
            except Exception:
                pass
        return await cb.answer(f"🔓 {msg_part[:200]}", show_alert=True)

    return await cb.answer("🔒 هذه الهمسة مو لك", show_alert=True)
