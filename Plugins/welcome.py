"""
الترحيب والقوانين
أوامر:
  وضع الترحيب / ضع الترحيب → إرسال رسالة الترحيب الجديدة
  الترحيب            → عرض الترحيب الحالي
  مسح الترحيب        → حذف الترحيب المخصص
  وضع قوانين         → تعيين قوانين المجموعة
  مسح القوانين       → حذف القوانين
  القوانين           → عرض القوانين
"""
import re
import pytz
from datetime import datetime
from pyrogram import Client, filters
from pyrogram.types import Message

from config import r, DEV_ID, botkey, botname
from helpers.ranks import is_mod
from helpers.utils import group_enabled, can_speak, resolve_text


DEFAULT_WELCOME = (
    "أهلاً بك في {المجموعه} 🌸\n\n"
    "الاسم ⌯ {الاسم}\n"
    "اليوزر ⌯ {اليوزر}\n"
    "التاريخ ⌯ {التاريخ}"
)

DEFAULT_RULES = (
    "📌 قوانين المجموعة:\n"
    "• ممنوع الإساءة والشتائم\n"
    "• ممنوع نشر الروابط والإعلانات\n"
    "• ممنوع المحتوى غير اللائق\n"
    "• احترم الجميع 🤝"
)


def _build_welcome(template: str, member, chat, rules: str) -> str:
    tz   = pytz.timezone("Asia/Riyadh")
    now  = datetime.now(tz)
    username = f"@{member.username}" if member.username else "—"
    return (
        template
        .replace("{الاسم}",    member.first_name or "")
        .replace("{اليوزر}",   username)
        .replace("{المجموعه}", chat.title or "")
        .replace("{التاريخ}",  now.strftime("%d/%m/%Y"))
        .replace("{الوقت}",    now.strftime("%I:%M %p"))
        .replace("{القوانين}", rules)
    )


# ─────────────── استقبال الأعضاء الجدد ─────────────────────────────────

@Client.on_message(filters.new_chat_members, group=4)
async def on_new_member(c: Client, m: Message):
    cid = m.chat.id
    if not group_enabled(cid):
        return
    if r.get(f"{cid}:disableWelcome:{DEV_ID}"):
        return

    k        = botkey()
    template = r.get(f"{cid}:CustomWelcome:{DEV_ID}") or DEFAULT_WELCOME
    rules    = r.get(f"{cid}:CustomRules:{DEV_ID}")   or DEFAULT_RULES

    for member in m.new_chat_members:
        if member.is_bot:
            continue
        text = _build_welcome(template, member, m.chat, rules)
        photo_id = None
        if not r.get(f"{cid}:disableWelcomep:{DEV_ID}") and member.photo:
            async for ph in c.get_chat_photos(member.id, limit=1):
                photo_id = ph.file_id
                break
        try:
            if photo_id:
                await m.reply_photo(photo_id, caption=text)
            else:
                await m.reply(text, disable_web_page_preview=True)
        except Exception:
            pass


# ─────────────── أوامر الترحيب والقوانين ────────────────────────────────

@Client.on_message(filters.text & filters.group, group=34)
async def welcome_commands(c: Client, m: Message):
    if not m.from_user:
        return
    cid, uid = m.chat.id, m.from_user.id
    if not group_enabled(cid):
        return
    if not can_speak(uid, cid):
        return

    text = resolve_text(m.text, cid)
    k    = botkey()

    # ── إلغاء وضع الترحيب/القوانين في منتصف الإدخال ─────────────────────
    if text == "الغاء":
        if r.delete(f"{cid}:setWelcome:{uid}:{DEV_ID}"):
            return await m.reply(f"{k} تم إلغاء وضع الترحيب")
        if r.delete(f"{cid}:setRules:{uid}:{DEV_ID}"):
            return await m.reply(f"{k} تم إلغاء وضع القوانين")
        return

    # ── استقبال نص الترحيب الجديد ──────────────────────────────────────
    if r.get(f"{cid}:setWelcome:{uid}:{DEV_ID}") and is_mod(uid, cid):
        r.set(f"{cid}:CustomWelcome:{DEV_ID}", m.text.html)
        r.delete(f"{cid}:setWelcome:{uid}:{DEV_ID}")
        return await m.reply(f"{k} تم حفظ رسالة الترحيب ✅")

    # ── استقبال نص القوانين الجديدة ────────────────────────────────────
    if r.get(f"{cid}:setRules:{uid}:{DEV_ID}") and is_mod(uid, cid):
        r.set(f"{cid}:CustomRules:{DEV_ID}", m.text.html)
        r.delete(f"{cid}:setRules:{uid}:{DEV_ID}")
        return await m.reply(f"{k} تم حفظ القوانين ✅")

    # ── الأوامر المباشرة ────────────────────────────────────────────────
    if text in ("وضع الترحيب", "ضع الترحيب"):
        if not is_mod(uid, cid):
            return await m.reply(f"{k} هذا الأمر للمدير وفوق فقط")
        r.set(f"{cid}:setWelcome:{uid}:{DEV_ID}", 1)
        return await m.reply(
            f"{k} أرسل رسالة الترحيب الآن\n\n"
            "متغيرات يمكنك استخدامها:\n"
            "• `{الاسم}` — اسم العضو\n"
            "• `{اليوزر}` — يوزر العضو\n"
            "• `{المجموعه}` — اسم المجموعة\n"
            "• `{التاريخ}` — تاريخ الدخول\n"
            "• `{الوقت}` — وقت الدخول\n"
            "• `{القوانين}` — قوانين المجموعة\n"
            "أرسل **الغاء** للتراجع"
        )

    if text == "الترحيب":
        if not is_mod(uid, cid):
            return await m.reply(f"{k} هذا الأمر للمدير وفوق فقط")
        welcome = r.get(f"{cid}:CustomWelcome:{DEV_ID}") or DEFAULT_WELCOME
        return await m.reply(f"`{welcome}`")

    if text == "مسح الترحيب":
        if not is_mod(uid, cid):
            return await m.reply(f"{k} هذا الأمر للمدير وفوق فقط")
        r.delete(f"{cid}:CustomWelcome:{DEV_ID}")
        return await m.reply(f"{k} تم مسح الترحيب المخصص ✅")

    if text == "وضع قوانين":
        if not is_mod(uid, cid):
            return await m.reply(f"{k} هذا الأمر للمدير وفوق فقط")
        r.set(f"{cid}:setRules:{uid}:{DEV_ID}", 1)
        return await m.reply(f"{k} أرسل القوانين الآن (أرسل **الغاء** للتراجع)")

    if text == "القوانين":
        rules = r.get(f"{cid}:CustomRules:{DEV_ID}") or DEFAULT_RULES
        return await m.reply(rules, disable_web_page_preview=True)

    if text == "مسح القوانين":
        if not is_mod(uid, cid):
            return await m.reply(f"{k} هذا الأمر للمدير وفوق فقط")
        r.delete(f"{cid}:CustomRules:{DEV_ID}")
        return await m.reply(f"{k} تم مسح القوانين المخصصة ✅")

    if text in ("تعطيل الترحيب", "ايقاف الترحيب"):
        if not is_mod(uid, cid):
            return await m.reply(f"{k} هذا الأمر للمدير وفوق فقط")
        r.set(f"{cid}:disableWelcome:{DEV_ID}", 1)
        return await m.reply(f"{k} تم إيقاف الترحيب")

    if text in ("تفعيل الترحيب", "تشغيل الترحيب"):
        if not is_mod(uid, cid):
            return await m.reply(f"{k} هذا الأمر للمدير وفوق فقط")
        r.delete(f"{cid}:disableWelcome:{DEV_ID}")
        return await m.reply(f"{k} تم تفعيل الترحيب ✅")
