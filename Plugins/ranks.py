"""
نظام إدارة الرتب
أوامر:
  رتبة / ررتبة / رتبتي       → عرض رتبة المستخدم
  قائمة الرتب                → عرض جميع الرتب المعينة
  ادمن @user / اضف ادمن (رد) → تعيين ادمن
  مدير @user / اضف مدير (رد) → تعيين مدير
  مالك @user / اضف مالك (رد) → تعيين مالك
  مالك اساسي (رد)            → تعيين مالك أساسي
  شيل ادمن / شيل مدير / شيل مالك (رد أو @user)
  تغيير اسم رتبة ادمن [الاسم] → تخصيص اسم الرتبة
"""
import re
from pyrogram import Client, filters
from pyrogram.types import Message

from config import r, DEV_ID, botkey
from helpers.ranks import (
    get_rank, is_admin, is_mod, is_owner, is_gowner, is_dev,
)
from helpers.utils import group_enabled, can_speak, resolve_text


RANK_KEYS = {
    "ادمن":       "rankADMIN",
    "مدير":       "rankMOD",
    "مالك":       "rankOWNER",
    "مالك اساسي": "rankGOWNER",
    "مميز":       "rankPRE",
}

RANK_LABEL_KEYS = {
    "ادمن":       "RankAdm",
    "مدير":       "RankMod",
    "مالك":       "RankOwner",
    "مالك اساسي": "RankGowner",
    "مميز":       "RankPre",
    "عضو":        "RankMem",
}

# الحد الأدنى المطلوب لتعيين كل رتبة
ASSIGN_REQUIRES = {
    "rankADMIN":  is_mod,
    "rankMOD":    is_owner,
    "rankOWNER":  is_gowner,
    "rankGOWNER": is_dev,
    "rankPRE":    is_admin,
}


async def _resolve_target(c: Client, m: Message, raw: str | None):
    if raw is None:
        if m.reply_to_message and m.reply_to_message.from_user:
            u = m.reply_to_message.from_user
            return u.id, u.mention
        return None, None
    try:
        uid = int(raw)
    except ValueError:
        uid = raw.lstrip("@")
    try:
        u = await c.get_users(uid)
        return u.id, u.mention
    except Exception:
        return None, None


@Client.on_message(filters.text & filters.group, group=20)
async def ranks_handler(c: Client, m: Message):
    if not m.from_user:
        return
    cid, uid = m.chat.id, m.from_user.id
    if not group_enabled(cid):
        return
    if not can_speak(uid, cid):
        return

    text = resolve_text(m.text, cid)
    k    = botkey()

    # ── عرض الرتبة ────────────────────────────────────────────────────────
    if text in ("رتبة", "ررتبة", "رتبتي"):
        target = m.reply_to_message.from_user if m.reply_to_message and m.reply_to_message.from_user else m.from_user
        rank = get_rank(target.id, cid)
        return await m.reply(f"「 {target.mention} 」\n{k} رتبته: **{rank}**")

    # ── قائمة الرتب الكاملة ───────────────────────────────────────────────
    if text == "قائمة الرتب":
        if not is_admin(uid, cid):
            return await m.reply(f"{k} هذا الأمر للادمن وفوق فقط")
        lines = [f"{k} الرتب المعينة في المجموعة:\n"]
        for label, rkey in RANK_KEYS.items():
            members = r.smembers(f"{cid}:{rkey}s:{DEV_ID}")
            if members:
                lines.append(f"**{label}:**")
                for mid in members:
                    lines.append(f"  • `{mid}`")
        if len(lines) == 1:
            lines.append("لا توجد رتب مخصصة بعد")
        return await m.reply("\n".join(lines))

    # ── تعيين رتبة ────────────────────────────────────────────────────────
    for label, rkey in RANK_KEYS.items():
        # اضف / تعيين بالردّ
        cmd_reply = re.fullmatch(rf"(?:اضف\s+)?{label}", text)
        # تعيين بذكر
        cmd_mention = re.fullmatch(rf"(?:اضف\s+)?{label}\s+(@?\S+)", text)

        raw_target = cmd_mention.group(1) if cmd_mention else (None if cmd_reply else None)
        matched = bool(cmd_reply or cmd_mention)

        if not matched:
            continue

        checker = ASSIGN_REQUIRES.get(rkey, is_gowner)
        if not checker(uid, cid):
            return await m.reply(f"{k} ليس لديك صلاحية تعيين {label}")

        target_id, target_mention = await _resolve_target(c, m, raw_target)
        if target_id is None:
            return await m.reply(f"{k} حدد المستخدم برد أو ذكر")
        if target_id == uid:
            return await m.reply(f"{k} ما تقدر تعيّن نفسك 😅")

        key = f"{cid}:{rkey}:{target_id}:{DEV_ID}"
        if r.get(key):
            return await m.reply(f"「 {target_mention} 」\n{k} لديه رتبة {label} مسبقاً")
        r.set(key, 1)
        r.sadd(f"{cid}:{rkey}s:{DEV_ID}", target_id)
        rank_name = r.get(f"{cid}:{RANK_LABEL_KEYS.get(label, '')}:{DEV_ID}") or label
        return await m.reply(f"「 {target_mention} 」\n{k} تم تعيينه **{rank_name}** ✅")

    # ── إزالة رتبة ────────────────────────────────────────────────────────
    for label, rkey in RANK_KEYS.items():
        cmd_reply   = re.fullmatch(rf"شيل\s+{label}", text)
        cmd_mention = re.fullmatch(rf"شيل\s+{label}\s+(@?\S+)", text)

        raw_target = cmd_mention.group(1) if cmd_mention else (None if cmd_reply else None)
        matched = bool(cmd_reply or cmd_mention)
        if not matched:
            continue

        checker = ASSIGN_REQUIRES.get(rkey, is_gowner)
        if not checker(uid, cid):
            return await m.reply(f"{k} ليس لديك صلاحية إزالة {label}")

        target_id, target_mention = await _resolve_target(c, m, raw_target)
        if target_id is None:
            return await m.reply(f"{k} حدد المستخدم برد أو ذكر")

        key = f"{cid}:{rkey}:{target_id}:{DEV_ID}"
        if not r.get(key):
            return await m.reply(f"「 {target_mention} 」\n{k} ليس لديه رتبة {label}")
        r.delete(key)
        r.srem(f"{cid}:{rkey}s:{DEV_ID}", target_id)
        return await m.reply(f"「 {target_mention} 」\n{k} تم إزالة رتبة {label} ✅")

    # ── تغيير اسم رتبة ────────────────────────────────────────────────────
    m_rename = re.fullmatch(r"تغيير اسم رتبة\s+(\S+)\s+(.+)", text)
    if m_rename:
        if not is_gowner(uid, cid):
            return await m.reply(f"{k} هذا الأمر للمالك الأساسي وفوق فقط")
        rank_label = m_rename.group(1)
        new_name   = m_rename.group(2).strip()
        lkey = RANK_LABEL_KEYS.get(rank_label)
        if not lkey:
            return await m.reply(f"{k} اسم الرتبة غير صحيح")
        r.set(f"{cid}:{lkey}:{DEV_ID}", new_name)
        return await m.reply(f"{k} تم تغيير اسم رتبة ({rank_label}) إلى **{new_name}** ✅")
