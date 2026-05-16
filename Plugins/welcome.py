"""
الترحيب والقوانين
أوامر:
  وضع الترحيب / ضع الترحيب → تعيين رسالة ترحيب مخصصة
  الترحيب                   → عرض الترحيب الحالي
  مسح الترحيب               → حذف الترحيب المخصص
  وضع قوانين                → تعيين قوانين المجموعة
  مسح القوانين              → حذف القوانين
  القوانين                  → عرض القوانين

متغيرات الترحيب:
  {الاسم}     {اليوزر}    {المجموعه}
  {التاريخ}   {الوقت}     {القوانين}
"""

import pytz
from datetime import datetime
from pyrogram import Client, filters
from pyrogram.types import Message

from config import r, DEV_ID, botkey, botname
from helpers.ranks import is_mod, is_pre
from helpers.utils import group_enabled, can_speak, resolve_text


DEFAULT_WELCOME = (
    "لا تُسِئ اللفظ وإن ضَاق عليك الرَّد\n\n"
    "ɴᴀᴍᴇ ⌯ {الاسم}\n"
    "ᴜѕᴇʀɴᴀᴍᴇ ⌯ {اليوزر}\n"
    "𝖣𝖺𝗍𝖾 ⌯ {التاريخ}"
)

DEFAULT_RULES = (
    "📌 قوانين المجموعة:\n"
    "• ممنوع نشر الروابط\n"
    "• ممنوع التكلم أو نشر صور إباحية\n"
    "• ممنوع الإعادة التوجيه\n"
    "• ممنوع العنصرية بكل أنواعها\n"
    "• الرجاء احترام المدراء والأدمنية"
)

TIME_ZONE = "Asia/Riyadh"


def _build_welcome(template: str, member, chat, rules_text: str) -> str:
    ZONE = pytz.timezone(TIME_ZONE)
    NOW  = datetime.now(ZONE)
    name     = member.first_name or "عضو"
    username = f"@{member.username}" if member.username else name
    title    = chat.title or ""
    clock    = NOW.strftime("%I:%M %p")
    date     = NOW.strftime("%d/%m/%Y")
    return (
        template
        .replace("{القوانين}", rules_text)
        .replace("{الاسم}",    name)
        .replace("{المجموعه}", title)
        .replace("{الوقت}",    clock)
        .replace("{التاريخ}",  date)
        .replace("{اليوزر}",   username)
    )


# ─────────────────────────────────────────────────────────────────────────
# معالج ضبط الترحيب والقوانين (نصوص)
# ─────────────────────────────────────────────────────────────────────────

@Client.on_message(filters.group & filters.text, group=29)
async def welcome_settings_handler(c: Client, m: Message):
    if not m.from_user:
        return
    cid, uid = m.chat.id, m.from_user.id
    if not group_enabled(cid):
        return
    if not can_speak(uid, cid):
        return

    text = resolve_text(m.text, cid)
    k    = botkey()

    # إلغاء وضع الترحيب
    if text == "الغاء":
        if r.get(f"{cid}:setWelcome:{uid}:{DEV_ID}"):
            r.delete(f"{cid}:setWelcome:{uid}:{DEV_ID}")
            return await m.reply(f"{k} ابشر لغيت وضع الترحيب")
        if r.get(f"{cid}:setRules:{uid}:{DEV_ID}"):
            r.delete(f"{cid}:setRules:{uid}:{DEV_ID}")
            return await m.reply(f"{k} ابشر لغيت وضع القوانين")

    # استلام القوانين
    if r.get(f"{cid}:setRules:{uid}:{DEV_ID}") and is_mod(uid, cid):
        r.set(f"{cid}:CustomRules:{DEV_ID}", m.text.html)
        r.delete(f"{cid}:setRules:{uid}:{DEV_ID}")
        return await m.reply(f"{k} تم حطيتها")

    # استلام الترحيب
    if r.get(f"{cid}:setWelcome:{uid}:{DEV_ID}") and is_mod(uid, cid):
        r.set(f"{cid}:CustomWelcome:{DEV_ID}", m.text.html)
        r.delete(f"{cid}:setWelcome:{uid}:{DEV_ID}")
        return await m.reply(f"{k} تم وسوينا الترحيب ياعيني")

    # مسح القوانين
    if text == "مسح القوانين":
        if not is_mod(uid, cid):
            return await m.reply(f"{k} هذا الامر يخص ( المدير وفوق ) بس")
        r.delete(f"{cid}:CustomRules:{DEV_ID}")
        return await m.reply(f"{k} من عيوني مسحت القوانين")

    # وضع قوانين
    if text == "وضع قوانين":
        if not is_mod(uid, cid):
            return await m.reply(f"{k} هذا الامر يخص ( المدير وفوق ) بس")
        r.set(f"{cid}:setRules:{uid}:{DEV_ID}", 1)
        return await m.reply(f"{k} ارسل القوانين الحين")

    # القوانين (عرض)
    if text == "القوانين":
        rules = r.get(f"{cid}:CustomRules:{DEV_ID}") or DEFAULT_RULES
        return await m.reply(rules, disable_web_page_preview=True)

    # عرض الترحيب الحالي
    if text == "الترحيب":
        if not is_mod(uid, cid):
            return await m.reply(f"{k} هذا الامر يخص ( المدير وفوق ) بس")
        w = r.get(f"{cid}:CustomWelcome:{DEV_ID}") or DEFAULT_WELCOME
        return await m.reply(f"`{w}`")

    # مسح الترحيب
    if text == "مسح الترحيب":
        if not is_mod(uid, cid):
            return await m.reply(f"{k} هذا الامر يخص ( المدير وفوق ) بس")
        r.delete(f"{cid}:CustomWelcome:{DEV_ID}")
        return await m.reply(f"{k} مسحت الترحيب")

    # وضع / ضع الترحيب
    if text in ("وضع الترحيب", "ضع الترحيب"):
        if not is_mod(uid, cid):
            return await m.reply(f"{k} هذا الامر يخص ( المدير وفوق ) بس")
        r.set(f"{cid}:setWelcome:{uid}:{DEV_ID}", 1)
        return await m.reply(
            "⇜ تمام عيني\n"
            "⇜ ارسل رسالة الترحيب الحين\n\n"
            "⇜ ملاحظة تقدر تضيف دوال للترحيب مثلا:\n"
            "⇜ اظهار قوانين المجموعه  ⇠ {القوانين}\n"
            "⇜ اظهار اسم العضو ⇠ {الاسم}\n"
            "⇜ اظهار اليوزر العضو ⇠ {اليوزر}\n"
            "⇜ اظهار اسم المجموعه ⇠ {المجموعه}\n"
            "⇜ اظهار تاريخ دخول العضو ⇠ {التاريخ}\n"
            "⇜ اظهار وقت دخول العضو ⇠ {الوقت}\n☆"
        )

    # تعطيل / تفعيل الترحيب
    if text == "تعطيل الترحيب":
        if not is_mod(uid, cid):
            return await m.reply(f"{k} هذا الامر يخص ( المدير وفوق ) بس")
        r.set(f"{cid}:disableWelcome:{DEV_ID}", 1)
        return await m.reply(f"{k} تم تعطيل الترحيب")

    if text == "تفعيل الترحيب":
        if not is_mod(uid, cid):
            return await m.reply(f"{k} هذا الامر يخص ( المدير وفوق ) بس")
        r.delete(f"{cid}:disableWelcome:{DEV_ID}")
        return await m.reply(f"{k} تم تفعيل الترحيب")


# ─────────────────────────────────────────────────────────────────────────
# إرسال رسالة الترحيب عند دخول عضو جديد
# ─────────────────────────────────────────────────────────────────────────

@Client.on_message(filters.new_chat_members, group=4)
async def welcome_new_member(c: Client, m: Message):
    cid = m.chat.id
    if not group_enabled(cid):
        return
    if r.get(f"{cid}:disableWelcome:{DEV_ID}"):
        return

    k  = botkey()
    ch = r.get(f"{DEV_ID}:BotChannel") or "yqyqy66"

    template = r.get(f"{cid}:CustomWelcome:{DEV_ID}") or DEFAULT_WELCOME
    rules    = r.get(f"{cid}:CustomRules:{DEV_ID}")   or DEFAULT_RULES

    for member in m.new_chat_members:
        if member.is_bot:
            continue
        if member.id == int(DEV_ID):
            continue
        # التحقق من الفيريفاي
        if r.get(f"{cid}:enableVerify:{DEV_ID}") and not is_pre(member.id, cid):
            continue

        text = _build_welcome(template, member, m.chat, rules)

        # صورة البروفايل
        photo = None
        if not r.get(f"{cid}:disableWelcomep:{DEV_ID}") and member.photo:
            try:
                async for p in c.get_chat_photos(member.id, limit=1):
                    photo = p.file_id
                    break
            except Exception:
                pass

        try:
            if photo:
                await m.reply_photo(photo, caption=text)
            else:
                await m.reply(text, disable_web_page_preview=True)
        except Exception:
            pass
