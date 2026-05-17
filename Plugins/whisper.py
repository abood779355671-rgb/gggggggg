"""
الهمسة - نظام الرسائل السرية
الطرق:
  1) inline:   @البوت همستك @username
  2) خاص:     يكتب اليوزر → البوت يطلب منه يكتب الهمسة
  3) deep link: t.me/bot?start=w_USERNAME  (يفتح مباشرة على شخص محدد)
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

from config import r, ar, DEV_ID


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
# /start في الخاص — deep link للهمسة
# group=-90 يعني يشتغل قبل handler الترحيب (-100) لكن بعد أي handler أعلى
# ─────────────────────────────────────────────────────────────────────────

@Client.on_message(filters.command("start") & filters.private, group=-90)
async def whisper_start_handler(c: Client, m: Message):
    args  = m.text.split(None, 1)
    param = args[1].strip() if len(args) > 1 else ""

    # deep link: شرح الهمسة
    if param == "whisper_help":
        await m.reply(
            "🔒 **طريقة استخدام الهمسة:**\n\n"
            "• في أي مجموعة اكتب:\n"
            "  `@البوت همستك @username`\n\n"
            "• أو ابدأ محادثة معي هنا وأخبرني من تريد تهمسه.",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    # deep link: همسة لشخص محدد مثل t.me/bot?start=w_layan
    if param.startswith("w_"):
        target_raw = param[2:]
        uid = m.from_user.id
        try:
            u = await c.get_users(target_raw)
        except Exception:
            await m.reply("❌ اليوزر غير موجود أو خاطئ.")
            return

        display = u.first_name
        await ar.set(_state_key(uid), f"await_msg:{u.id}:{display}", ex=300)
        await m.reply(
            f"• تم تحديد الهمسة لـ **{display}** ←\n"
            "• اضغط الزر لكتابة الهمسة",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("• همسة نصيه", callback_data=f"wp_type:{u.id}:{display}")
            ]])
        )
        return

    # مو deep link للهمسة → نتجاهل ونترك handler آخر يشتغل
    return


# ─────────────────────────────────────────────────────────────────────────
# زر "همسة نصية" — يطلب الكتابة
# ─────────────────────────────────────────────────────────────────────────

@Client.on_callback_query(filters.regex(r"^wp_type:"))
async def whisper_type_cb(c: Client, cb: CallbackQuery):
    parts = cb.data.split(":", 2)
    target_id = parts[1]
    display   = parts[2]
    uid = cb.from_user.id

    await ar.set(_state_key(uid), f"await_msg:{target_id}:{display}", ex=300)
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

    if not state:
        return

    # ── ننتظر نص الهمسة ──
    if state.startswith("await_msg:"):
        _, target_id, display = state.split(":", 2)
        target_id_int = int(target_id)
        msg_text = m.text.strip()

        wid = _gen_id()
        await ar.set(f"w:{wid}", f"{uid}+{target_id}&msg={msg_text}", ex=86400)
        await ar.delete(_state_key(uid))

        # أخبر المرسل
        await m.reply(
            f"• تم ارسال همستك لـ **{display}** . بنجاح",
            parse_mode=ParseMode.MARKDOWN,
        )

        # إشعار للمستلم
        bot_username = (await c.get_me()).username
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
            target_user = await c.get_users(target_id_int)
            await c.send_message(
                target_id_int,
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
        return


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
