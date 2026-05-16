"""
الفلاتر المخصصة
أوامر:
  اضف فلتر [الكلمة]   → إضافة فلتر (يطلب الرد بعدها)
  حذف فلتر [الكلمة]   → حذف فلتر
  الفلاتر             → قائمة الفلاتر
"""
import re
import pytz
from datetime import datetime
from pyrogram import Client, filters
from pyrogram.enums import ParseMode
from pyrogram.types import Message

from config import r, DEV_ID, botkey, cached_smembers
from helpers.ranks import is_mod
from helpers.utils import group_enabled, can_speak, resolve_text


def _date_now() -> str:
    tz  = pytz.timezone("Asia/Riyadh")
    now = datetime.now(tz)
    return now.strftime("%d/%m/%Y %I:%M:%S %p")


# ── إرسال ردّ الفلتر ─────────────────────────────────────────────────────

async def _send_filter(m: Message, data: str):
    """يُحلّل بيانات الفلتر ويُرسل الرد المناسب"""
    try:
        parts = dict(p.split("=", 1) for p in data.split("&") if "=" in p)
    except Exception:
        return

    ftype = parts.get("type", "text")

    if ftype == "text":
        txt = parts.get("text", "")
        await m.reply(txt, parse_mode=ParseMode.HTML, disable_web_page_preview=True)

    elif ftype == "photo":
        fid     = parts.get("photo", "")
        caption = parts.get("caption", "")
        if caption == "None": caption = None
        await m.reply_photo(fid, caption=caption, parse_mode=ParseMode.HTML)

    elif ftype == "video":
        fid     = parts.get("video", "")
        caption = parts.get("caption", "")
        if caption == "None": caption = None
        await m.reply_video(fid, caption=caption, parse_mode=ParseMode.HTML)

    elif ftype == "animation":
        fid     = parts.get("animation", "")
        caption = parts.get("caption", "")
        if caption == "None": caption = None
        await m.reply_animation(fid, caption=caption, parse_mode=ParseMode.HTML)

    elif ftype == "audio":
        fid     = parts.get("audio", "")
        caption = parts.get("caption", "")
        if caption == "None": caption = None
        await m.reply_audio(fid, caption=caption, parse_mode=ParseMode.HTML)

    elif ftype == "voice":
        fid     = parts.get("voice", "")
        caption = parts.get("caption", "")
        if caption == "None": caption = None
        await m.reply_voice(fid, caption=caption, parse_mode=ParseMode.HTML)

    elif ftype == "doc":
        fid     = parts.get("doc", "")
        caption = parts.get("caption", "")
        if caption == "None": caption = None
        await m.reply_document(fid, caption=caption, parse_mode=ParseMode.HTML)

    elif ftype == "sticker":
        fid = parts.get("sticker", "")
        await m.reply_sticker(fid)


# ── مرحلة إضافة الفلتر (استقبال الرد) ───────────────────────────────────

@Client.on_message(filters.group, group=21)
async def filter_input_handler(c: Client, m: Message):
    if not m.from_user:
        return
    cid, uid = m.chat.id, m.from_user.id
    if not group_enabled(cid):
        return
    if not can_speak(uid, cid):
        return

    key_wait = f"{cid}:addFilter2:{uid}:{DEV_ID}"
    if not r.get(key_wait) or not is_mod(uid, cid):
        return

    filter_word = r.get(key_wait)
    date        = _date_now()
    k           = botkey()

    async def _save(data: str, ftype_label: str):
        r.set(f"{filter_word}:filter:{DEV_ID}:{cid}", data)
        r.set(f"{filter_word}:filtertype:{cid}:{DEV_ID}", ftype_label)
        r.set(f"{filter_word}:filterInfo:{cid}:{DEV_ID}", f"by={uid}&date={date}")
        r.sadd(f"{cid}:FiltersList:{DEV_ID}", filter_word)
        r.delete(key_wait)
        await m.reply(f"({filter_word})\n{k} تم حفظ الفلتر ✅", parse_mode=ParseMode.HTML)

    if m.text and m.text != "الغاء":
        await _save(f"type=text&text={m.text.html}", "نص")
        return

    if m.text == "الغاء":
        r.delete(key_wait)
        await m.reply(f"{k} تم إلغاء إضافة الفلتر")
        return

    cap = m.caption.html if m.caption else "None"

    if m.photo:
        await _save(f"type=photo&photo={m.photo.file_id}&caption={cap}", "صورة")
    elif m.video:
        await _save(f"type=video&video={m.video.file_id}&caption={cap}", "فيديو")
    elif m.animation:
        await _save(f"type=animation&animation={m.animation.file_id}&caption={cap}", "GIF")
    elif m.audio:
        await _save(f"type=audio&audio={m.audio.file_id}&caption={cap}", "صوت")
    elif m.voice:
        await _save(f"type=voice&voice={m.voice.file_id}&caption={cap}", "بصمة")
    elif m.document:
        await _save(f"type=doc&doc={m.document.file_id}&caption={cap}", "ملف")
    elif m.sticker:
        await _save(f"type=sticker&sticker={m.sticker.file_id}", "ستيكر")


# ── أوامر الفلاتر الرئيسية ────────────────────────────────────────────────

@Client.on_message(filters.text & filters.group, group=22)
async def filters_commands(c: Client, m: Message):
    if not m.from_user:
        return
    cid, uid = m.chat.id, m.from_user.id
    if not group_enabled(cid):
        return
    if not can_speak(uid, cid):
        return

    text = resolve_text(m.text, cid)
    k    = botkey()

    # اضف فلتر [كلمة]
    add_m = re.fullmatch(r"اضف فلتر\s+(.+)", text)
    if add_m:
        if not is_mod(uid, cid):
            return await m.reply(f"{k} هذا الأمر للمدير وفوق فقط")
        word = add_m.group(1).strip().lower()
        r.set(f"{cid}:addFilter2:{uid}:{DEV_ID}", word)
        return await m.reply(
            f"{k} أرسل الرد للكلمة «{word}» الآن\n"
            "(نص، صورة، فيديو، ستيكر ...)\n"
            "أرسل **الغاء** للتراجع"
        )

    # حذف فلتر [كلمة]
    del_m = re.fullmatch(r"حذف فلتر\s+(.+)", text)
    if del_m:
        if not is_mod(uid, cid):
            return await m.reply(f"{k} هذا الأمر للمدير وفوق فقط")
        word = del_m.group(1).strip().lower()
        fkey = f"{word}:filter:{DEV_ID}:{cid}"
        if not r.get(fkey):
            return await m.reply(f"{k} لا يوجد فلتر بهذه الكلمة")
        r.delete(fkey)
        r.delete(f"{word}:filtertype:{cid}:{DEV_ID}")
        r.delete(f"{word}:filterInfo:{cid}:{DEV_ID}")
        r.srem(f"{cid}:FiltersList:{DEV_ID}", word)
        return await m.reply(f"{k} تم حذف فلتر «{word}» ✅")

    # قائمة الفلاتر
    if text == "الفلاتر":
        fl = cached_smembers(f"{cid}:FiltersList:{DEV_ID}")
        if not fl:
            return await m.reply(f"{k} لا توجد فلاتر في هذه المجموعة")
        lines = [f"{k} الفلاتر المضافة:\n"]
        for i, word in enumerate(sorted(fl), 1):
            ftype = r.get(f"{word}:filtertype:{cid}:{DEV_ID}") or "—"
            lines.append(f"{i}. `{word}` — {ftype}")
        return await m.reply("\n".join(lines))


# ── تطبيق الفلاتر على كل رسالة ───────────────────────────────────────────

@Client.on_message(filters.text & filters.group, group=23)
async def apply_filters(c: Client, m: Message):
    if not m.from_user or not m.text:
        return
    cid, uid = m.chat.id, m.from_user.id
    if not group_enabled(cid):
        return
    # لا نطبّق الفلاتر إذا المستخدم في وضع إضافة فلتر
    if r.get(f"{cid}:addFilter2:{uid}:{DEV_ID}"):
        return

    fl = cached_smembers(f"{cid}:FiltersList:{DEV_ID}")
    if not fl:
        return

    msg_text = m.text.lower()
    for word in fl:
        if word in msg_text:
            data = r.get(f"{word}:filter:{DEV_ID}:{cid}")
            if data:
                try:
                    await _send_filter(m, data)
                except Exception:
                    pass
            break


# ─────────────────────────────────────────────────────────────────────────────
# الردود المميزة (المتعددة/العشوائية) - group=23B
# ─────────────────────────────────────────────────────────────────────────────

@Client.on_message(filters.group & filters.text, group=28)
async def random_filters_handler(c: Client, m: Message):
    if not m.from_user:
        return
    cid, uid = m.chat.id, m.from_user.id
    if not group_enabled(cid):
        return
    if not can_speak(uid, cid):
        return

    text = resolve_text(m.text, cid)
    k    = botkey()

    import random as _random

    # ── إلغاء ────────────────────────────────────────────────────────────
    if text == "الغاء":
        if r.delete(f"{cid}:addFilterR:{uid}:{DEV_ID}"):
            return await m.reply(f"{k} تم إلغاء إضافة الرد المميز")
        if r.get(f"{cid}:addFilterR2:{uid}:{DEV_ID}"):
            rep = r.get(f"{cid}:addFilterR2:{uid}:{DEV_ID}")
            r.delete(f"{cid}:addFilterR2:{uid}:{DEV_ID}")
            r.delete(f"{rep}:randomfilter:{cid}:{DEV_ID}")
            return await m.reply(f"{k} تم إلغاء إضافة الرد المميز")
        if r.delete(f"{cid}:delFilterR:{uid}:{DEV_ID}"):
            return await m.reply(f"{k} تم إلغاء مسح الرد المميز")
        return

    # ── تم (حفظ الرد المميز) ─────────────────────────────────────────────
    if text == "تم" and r.get(f"{cid}:addFilterR2:{uid}:{DEV_ID}"):
        word  = r.get(f"{cid}:addFilterR2:{uid}:{DEV_ID}")
        count = len(r.smembers(f"{word}:randomfilter:{cid}:{DEV_ID}"))
        r.set(f"{word}:randomFilter:{cid}:{DEV_ID}", 1)
        r.sadd(f"{cid}:RFiltersList:{DEV_ID}", word)
        r.delete(f"{cid}:addFilterR2:{uid}:{DEV_ID}")
        return await m.reply(f"{k} تم إضافة الرد المميز ( {word} )\n{k} بـ ( {count} ) جواب رد\n☆")

    # ── مرحلة إضافة الأجوبة ──────────────────────────────────────────────
    if r.get(f"{cid}:addFilterR2:{uid}:{DEV_ID}") and is_mod(uid, cid):
        word = r.get(f"{cid}:addFilterR2:{uid}:{DEV_ID}")
        r.sadd(f"{word}:randomfilter:{cid}:{DEV_ID}", m.text.html if hasattr(m.text, "html") else m.text)
        return await m.reply(f"{k} تم إضافة هذا الجواب\n{k} بس تخلص أرسل **تم**")

    # ── مرحلة تلقّي اسم الرد المميز الجديد ──────────────────────────────
    if r.get(f"{cid}:addFilterR:{uid}:{DEV_ID}") and is_mod(uid, cid):
        r.delete(f"{cid}:addFilterR:{uid}:{DEV_ID}")
        r.set(f"{cid}:addFilterR2:{uid}:{DEV_ID}", text)
        return await m.reply(f"{k} الآن أرسل أجوبة الرد\n{k} بس تخلص أرسل **تم**")

    # ── حذف رد مميز (مرحلة تلقّي الاسم) ─────────────────────────────────
    if r.get(f"{cid}:delFilterR:{uid}:{DEV_ID}") and is_mod(uid, cid):
        if not r.get(f"{text}:randomFilter:{cid}:{DEV_ID}"):
            r.delete(f"{cid}:delFilterR:{uid}:{DEV_ID}")
            return await m.reply(f"{k} هذا الرد غير مضاف")
        r.delete(f"{text}:randomFilter:{cid}:{DEV_ID}")
        r.delete(f"{text}:randomfilter:{cid}:{DEV_ID}")
        r.delete(f"{cid}:delFilterR:{uid}:{DEV_ID}")
        r.srem(f"{cid}:RFiltersList:{DEV_ID}", text)
        return await m.reply(f"{k} تم مسح الرد المميز ✅")

    # ── أوامر الردود المميزة ─────────────────────────────────────────────
    if text == "اضف رد مميز":
        if not is_mod(uid, cid):
            return await m.reply(f"{k} هذا الأمر للمدير وفوق فقط")
        r.set(f"{cid}:addFilterR:{uid}:{DEV_ID}", 1)
        return await m.reply(f"{k} أرسل الكلمة التي تريدها")

    if text == "مسح رد مميز":
        if not is_mod(uid, cid):
            return await m.reply(f"{k} هذا الأمر للمدير وفوق فقط")
        r.set(f"{cid}:delFilterR:{uid}:{DEV_ID}", 1)
        return await m.reply(f"{k} أرسل الرد الذي تريد مسحه")

    if text == "الردود المميزه":
        if not is_mod(uid, cid):
            return await m.reply(f"{k} هذا الأمر للمدير وفوق فقط")
        rfl = r.smembers(f"{cid}:RFiltersList:{DEV_ID}")
        if not rfl:
            return await m.reply(f"{k} مافيه ردود مميزة مضافة")
        txt = "الردود المميزة:\n"
        for i, word in enumerate(rfl, 1):
            count = len(r.smembers(f"{word}:randomfilter:{cid}:{DEV_ID}"))
            txt += f"\n{i} - ( {word} ) ☆ ( {count} )"
        txt += "\n☆"
        return await m.reply(txt)

    if text == "مسح الردود المميزه":
        if not is_mod(uid, cid):
            return await m.reply(f"{k} هذا الأمر للمدير وفوق فقط")
        rfl = r.smembers(f"{cid}:RFiltersList:{DEV_ID}")
        if not rfl:
            return await m.reply(f"{k} مافيه ردود مميزة مضافة")
        count = 0
        for word in list(rfl):
            r.delete(f"{word}:randomFilter:{cid}:{DEV_ID}")
            r.delete(f"{word}:randomfilter:{cid}:{DEV_ID}")
            r.srem(f"{cid}:RFiltersList:{DEV_ID}", word)
            count += 1
        return await m.reply(f"{k} تم مسح ( {count} ) رد مميز ✅")


@Client.on_message(filters.text & filters.group, group=29)
async def apply_random_filters(c: Client, m: Message):
    """تطبيق الردود المميزة العشوائية."""
    import random as _random
    if not m.from_user or not m.text:
        return
    cid, uid = m.chat.id, m.from_user.id
    if not group_enabled(cid):
        return

    text = resolve_text(m.text, cid)

    rfl = r.smembers(f"{cid}:RFiltersList:{DEV_ID}")
    if not rfl:
        return

    for word in rfl:
        if text == word:
            options = r.smembers(f"{word}:randomfilter:{cid}:{DEV_ID}")
            if options:
                chosen = _random.choice(list(options))
                try:
                    await m.reply(chosen, disable_web_page_preview=True)
                except Exception:
                    pass
            return
