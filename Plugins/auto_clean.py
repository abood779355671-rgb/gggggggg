"""
ملف auto_clean.py - نظام التنظيف التلقائي للوسائط
الأوامر المتاحة:
  تفعيل التنظيف              → تفعيل حذف الوسائط تلقائياً بعد المدة المحددة (مالك أساسي+)
  تعطيل التنظيف              → إيقاف التنظيف التلقائي (مالك أساسي+)
  وضع وقت التنظيف [ثواني]   → تحديد مدة الانتظار قبل الحذف (60-3600 ثانية) (مالك أساسي+)
  وقت التنظيف                → عرض المدة الحالية المضبوطة (مالك أساسي+)
"""

import asyncio
import re
from datetime import datetime, timedelta

from pyrogram import Client, filters
from pyrogram.errors import FloodWait
from pyrogram.types import Message

from config import r, DEV_ID, botkey
from helpers.ranks import is_gowner
from helpers.utils import group_enabled, resolve_text

# { chat_id: [{"id": msg_id, "time": datetime}, ...] }
_pending: dict = {}


# ────────────────────────────────────────────────────────────
# جمع الرسائل الواردة
# ────────────────────────────────────────────────────────────

@Client.on_message(filters.group & filters.media, group=1)
async def _collect_media(c: Client, m: Message):
    if not group_enabled(m.chat.id):
        return

    # تخطي الصوت والفويس والألعاب
    if m.audio or m.voice or m.game:
        return

    # مفتاح Redis: DEVID:CHATID:ena-clean  (نفس مفتاح أوامر التحكم)
    if not r.get(f"{DEV_ID}:{m.chat.id}:ena-clean"):
        return

    secs = int(r.get(f"{DEV_ID}:{m.chat.id}:clean-secs") or "60")
    delete_at = datetime.now() + timedelta(seconds=secs)

    if m.chat.id not in _pending:
        _pending[m.chat.id] = []

    if m.media_group_id:
        try:
            group_msgs = await c.get_media_group(m.chat.id, m.id)
            for gm in group_msgs:
                _pending[m.chat.id].append({"id": gm.id, "time": delete_at})
        except Exception:
            _pending[m.chat.id].append({"id": m.id, "time": delete_at})
    else:
        _pending[m.chat.id].append({"id": m.id, "time": delete_at})


# ────────────────────────────────────────────────────────────
# حلقة الحذف التلقائي
# ────────────────────────────────────────────────────────────

async def _auto_clean_loop(client: Client):
    """
    تدور كل 1.7 ثانية عند وجود رسائل منتظرة،
    وتنام 10 ثوانٍ إذا كانت القائمة فارغة لتوفير CPU.
    """
    print("[auto_clean] ✅ الحلقة تعمل")
    while True:
        try:
            if not _pending:
                # لا يوجد شيء ينتظر — نام طويلاً لتوفير CPU
                await asyncio.sleep(10)
                continue

            await asyncio.sleep(1.7)
            now = datetime.now()
            for chat_id in list(_pending.keys()):
                to_delete = []
                remaining = []
                for entry in _pending[chat_id]:
                    if now > entry["time"]:
                        to_delete.append(entry["id"])
                    else:
                        remaining.append(entry)
                _pending[chat_id] = remaining
                if not remaining:
                    del _pending[chat_id]  # تنظيف: احذف المفتاح إذا فرغت القائمة
                if to_delete:
                    try:
                        await client.delete_messages(chat_id, to_delete)
                        print(f"[auto_clean] حذف {len(to_delete)} رسالة من {chat_id}")
                    except FloodWait as fw:
                        await asyncio.sleep(fw.value)
                    except Exception as e:
                        print(f"[auto_clean] خطأ حذف: {e}")
        except Exception as e:
            print(f"[auto_clean] خطأ عام: {e}")


# ────────────────────────────────────────────────────────────
# أوامر التحكم
# ────────────────────────────────────────────────────────────

@Client.on_message(filters.group & filters.text, group=29)
async def clean_commands(c: Client, m: Message):
    if not m.from_user:
        return
    if not group_enabled(m.chat.id):
        return

    text = resolve_text(m.text, m.chat.id)
    k = botkey()
    uid = m.from_user.id
    cid = m.chat.id
    mention = m.from_user.mention

    async def need_gowner():
        if not is_gowner(uid, cid):
            await m.reply(f"{k} هذا الأمر يخص ( المالك الأساسي وفوق ) بس")
            return True
        return False

    # ── تعطيل التنظيف ──
    if text == "تعطيل التنظيف":
        if await need_gowner(): return
        if not r.get(f"{DEV_ID}:{cid}:ena-clean"):
            return await m.reply(f"{k} من 「 {mention} 」\n{k} التنظيف معطّل من قبل\n☆")
        r.delete(f"{DEV_ID}:{cid}:ena-clean")
        _pending.pop(cid, None)
        return await m.reply(f"{k} من 「 {mention} 」\n{k} ابشر عطّلت التنظيف\n☆")

    # ── تفعيل التنظيف ──
    if text == "تفعيل التنظيف":
        if await need_gowner(): return
        if r.get(f"{DEV_ID}:{cid}:ena-clean"):
            return await m.reply(f"{k} من 「 {mention} 」\n{k} التنظيف مفعّل من قبل\n☆")
        r.set(f"{DEV_ID}:{cid}:ena-clean", 1)
        return await m.reply(f"{k} من 「 {mention} 」\n{k} ابشر فعّلت التنظيف\n☆")

    # ── وضع وقت التنظيف [ثواني] ──
    if re.search(r"^وضع وقت التنظيف \d+$", text):
        if await need_gowner(): return
        secs = int(text.split()[-1])
        if secs < 60 or secs > 3600:
            return await m.reply(f"{k} عليك تحديد وقت التنظيف بالثواني من 60 إلى 3600 ثانية")
        r.set(f"{DEV_ID}:{cid}:clean-secs", secs)
        return await m.reply(f"{k} تم تعيين وقت التنظيف ( {secs} ) ثانية")

    # ── وقت التنظيف ──
    if text == "وقت التنظيف":
        if await need_gowner(): return
        secs = r.get(f"{DEV_ID}:{cid}:clean-secs") or "60"
        status = "مفعّل ✅" if r.get(f"{DEV_ID}:{cid}:ena-clean") else "معطّل ❌"
        return await m.reply(
            f"{k} إعدادات التنظيف:\n"
            f"الحالة: {status}\n"
            f"مدة الانتظار: `{secs}` ثانية"
        )
