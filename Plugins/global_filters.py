"""
الردود العامة - فلاتر تسري على جميع المجموعات
أوامر (للمطور):
  اضف فلتر عام [كلمة]  → إضافة فلتر عام
  حذف فلتر عام [كلمة]  → حذف فلتر عام
  الفلاتر العامة        → قائمة الفلاتر العامة
"""
import re
from pyrogram import Client, filters
from pyrogram.enums import ParseMode
from pyrogram.types import Message

from config import r, DEV_ID, botkey, cached_smembers
from helpers.ranks import is_dev, is_mod
from helpers.utils import group_enabled, can_speak, resolve_text


async def _send_data(m: Message, data: str):
    try:
        parts = dict(p.split("=", 1) for p in data.split("&") if "=" in p)
    except Exception:
        return
    ftype = parts.get("type", "text")
    cap   = parts.get("caption", None)
    if cap == "None": cap = None

    if ftype == "text":
        await m.reply(parts.get("text", ""), parse_mode=ParseMode.HTML, disable_web_page_preview=True)
    elif ftype == "photo":
        await m.reply_photo(parts["photo"], caption=cap, parse_mode=ParseMode.HTML)
    elif ftype == "video":
        await m.reply_video(parts["video"], caption=cap, parse_mode=ParseMode.HTML)
    elif ftype == "animation":
        await m.reply_animation(parts["animation"], caption=cap, parse_mode=ParseMode.HTML)
    elif ftype == "sticker":
        await m.reply_sticker(parts["sticker"])
    elif ftype == "audio":
        await m.reply_audio(parts["audio"], caption=cap, parse_mode=ParseMode.HTML)
    elif ftype == "voice":
        await m.reply_voice(parts["voice"], caption=cap, parse_mode=ParseMode.HTML)
    elif ftype == "doc":
        await m.reply_document(parts["doc"], caption=cap, parse_mode=ParseMode.HTML)


# ── استقبال محتوى الفلتر العام الجديد ────────────────────────────────────

@Client.on_message(filters.group, group=31)
async def global_filter_input(c: Client, m: Message):
    if not m.from_user:
        return
    cid, uid = m.chat.id, m.from_user.id

    # الفحص المبكر: جلب key_wait مرة واحدة فقط
    # 99.99% من الرسائل تخرج هنا بدون أي استدعاءات إضافية
    key_wait = f"addGlobalFilter2:{uid}:{DEV_ID}"
    word = r.get(key_wait)
    if not word or not is_dev(uid, cid):
        return

    if not group_enabled(cid):
        return

    k = botkey()

    async def _save(data: str):
        r.set(f"GlobalFilter:{DEV_ID}:{word}", data)
        r.sadd(f"GlobalFiltersList:{DEV_ID}", word)
        r.delete(key_wait)
        await m.reply(f"{k} تم إضافة الفلتر العام «{word}» ✅")

    if m.text and m.text != "الغاء":
        await _save(f"type=text&text={m.text.html}")
        return
    if m.text == "الغاء":
        r.delete(key_wait)
        await m.reply(f"{k} تم الإلغاء")
        return

    cap = m.caption.html if m.caption else "None"
    if m.photo:
        await _save(f"type=photo&photo={m.photo.file_id}&caption={cap}")
    elif m.video:
        await _save(f"type=video&video={m.video.file_id}&caption={cap}")
    elif m.animation:
        await _save(f"type=animation&animation={m.animation.file_id}&caption={cap}")
    elif m.sticker:
        await _save(f"type=sticker&sticker={m.sticker.file_id}")
    elif m.audio:
        await _save(f"type=audio&audio={m.audio.file_id}&caption={cap}")
    elif m.voice:
        await _save(f"type=voice&voice={m.voice.file_id}&caption={cap}")
    elif m.document:
        await _save(f"type=doc&doc={m.document.file_id}&caption={cap}")


# ── أوامر الفلاتر العامة ─────────────────────────────────────────────────

@Client.on_message(filters.text & filters.group, group=32)
async def global_filter_commands(c: Client, m: Message):
    if not m.from_user:
        return
    cid, uid = m.chat.id, m.from_user.id
    if not group_enabled(cid):
        return
    if not can_speak(uid, cid):
        return

    text = resolve_text(m.text, cid)
    k    = botkey()

    add_m = re.fullmatch(r"اضف فلتر عام\s+(.+)", text)
    if add_m:
        if not is_dev(uid, cid):
            return await m.reply(f"{k} هذا الأمر للمطور فقط")
        word = add_m.group(1).strip().lower()
        r.set(f"addGlobalFilter2:{uid}:{DEV_ID}", word)
        return await m.reply(
            f"{k} أرسل الرد للكلمة العامة «{word}» الآن\nأرسل **الغاء** للتراجع"
        )

    del_m = re.fullmatch(r"حذف فلتر عام\s+(.+)", text)
    if del_m:
        if not is_dev(uid, cid):
            return await m.reply(f"{k} هذا الأمر للمطور فقط")
        word = del_m.group(1).strip().lower()
        r.delete(f"GlobalFilter:{DEV_ID}:{word}")
        r.srem(f"GlobalFiltersList:{DEV_ID}", word)
        return await m.reply(f"{k} تم حذف الفلتر العام «{word}» ✅")

    if text == "الفلاتر العامة":
        if not is_mod(uid, cid):
            return await m.reply(f"{k} هذا الأمر للمدير وفوق فقط")
        fl = cached_smembers(f"GlobalFiltersList:{DEV_ID}")
        if not fl:
            return await m.reply(f"{k} لا توجد فلاتر عامة")
        return await m.reply(
            f"{k} الفلاتر العامة:\n" +
            "\n".join(f"• `{w}`" for w in sorted(fl))
        )


# ── تطبيق الفلاتر العامة ─────────────────────────────────────────────────

@Client.on_message(filters.text & filters.group, group=33)
async def apply_global_filters(c: Client, m: Message):
    if not m.from_user or not m.text:
        return
    cid = m.chat.id
    if not group_enabled(cid):
        return
    if r.get(f"addGlobalFilter2:{m.from_user.id}:{DEV_ID}"):
        return

    fl = cached_smembers(f"GlobalFiltersList:{DEV_ID}")
    if not fl:
        return

    msg_lower = m.text.lower()
    for word in fl:
        if word in msg_lower:
            data = r.get(f"GlobalFilter:{DEV_ID}:{word}")
            if data:
                try:
                    await _send_data(m, data)
                except Exception:
                    pass
            break


# ─────────────────────────────────────────────────────────────────────────────
# ميزات إضافية: تعطيل/تفعيل ردود المطور، مسح الردود العامة
# ─────────────────────────────────────────────────────────────────────────────

@Client.on_message(filters.text & filters.group, group=24)
async def global_filter_extra(c: Client, m: Message):
    if not m.from_user:
        return
    cid, uid = m.chat.id, m.from_user.id
    if not group_enabled(cid):
        return
    if not can_speak(uid, cid):
        return

    from helpers.ranks import is_owner, is_dev as _is_dev
    text = resolve_text(m.text, cid)
    k    = botkey()

    # ── تعطيل / تفعيل ردود المطور ───────────────────────────────────────
    if text == "تعطيل ردود المطور":
        if not is_owner(uid, cid):
            return await m.reply(f"{k} هذا الأمر للمالك وفوق فقط")
        if r.get(f"{cid}:lock_global:{DEV_ID}"):
            return await m.reply(f"{k} ردود المطور معطلة مسبقاً")
        r.set(f"{cid}:lock_global:{DEV_ID}", 1)
        return await m.reply(f"{k} من「 {m.from_user.mention} 」\n{k} تم تعطيل ردود المطور\n☆")

    if text == "تفعيل ردود المطور":
        if not is_owner(uid, cid):
            return await m.reply(f"{k} هذا الأمر للمالك وفوق فقط")
        if not r.get(f"{cid}:lock_global:{DEV_ID}"):
            return await m.reply(f"{k} ردود المطور مفعلة مسبقاً")
        r.delete(f"{cid}:lock_global:{DEV_ID}")
        return await m.reply(f"{k} من「 {m.from_user.mention} 」\n{k} تم تفعيل ردود المطور\n☆")

    # ── الردود العامه (قائمة مع النوع) ──────────────────────────────────
    if text in ("الردود العامه", "الردود العامة"):
        if not _is_dev(uid, cid):
            return await m.reply(f"{k} هذا الأمر للمطور فقط")
        fl = r.smembers(f"GlobalFiltersList:{DEV_ID}")
        if not fl:
            return await m.reply(f"{k} مافيه ردود عامة مضافة")
        txt = "ردود البوت:\n"
        for i, word in enumerate(fl, 1):
            ftype = "نص"
            data  = r.get(f"GlobalFilter:{DEV_ID}:{word}")
            if data:
                import re as _re
                m_type = _re.search(r"type=([^&]+)", data)
                if m_type:
                    _t = m_type.group(1)
                    ftype = {"text":"نص","photo":"صورة","video":"فيديو","animation":"متحركة",
                             "audio":"صوت","voice":"بصمة","doc":"ملف","sticker":"ملصق"}.get(_t, _t)
            txt += f"\n{i} - ( {word} ) ࿓ ( {ftype} )"
        txt += "\n☆"
        return await m.reply(txt)

    # ── مسح الردود العامه ───────────────────────────────────────────────
    if text in ("مسح الردود العامه", "مسح الردود العامة"):
        if not _is_dev(uid, cid):
            return await m.reply(f"{k} هذا الأمر للمطور فقط")
        fl = r.smembers(f"GlobalFiltersList:{DEV_ID}")
        if not fl:
            return await m.reply(f"{k} مافيه ردود عامة مضافة")
        count = 0
        for word in list(fl):
            r.delete(f"GlobalFilter:{DEV_ID}:{word}")
            r.srem(f"GlobalFiltersList:{DEV_ID}", word)
            count += 1
        return await m.reply(f"{k} ابشر مسحت ( {count} ) من الردود العامة")
