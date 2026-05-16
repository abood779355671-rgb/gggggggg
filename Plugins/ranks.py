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
    is_dev2, is_myth, is_botowner,
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

# رتب Dev² و Myth تُدار عبر set_ranks.py

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


# ─────────────────────────────────────────────────────────────────────────────
# عرض قوائم الرتب التفصيلية + مسح القوائم
# group=12 → get_ranks | group=13 → del_ranks
# ─────────────────────────────────────────────────────────────────────────────

@Client.on_message(filters.text & filters.group, group=12)
async def get_ranks_handler(c: Client, m: Message):
    if not m.from_user:
        return
    cid, uid = m.chat.id, m.from_user.id
    if not group_enabled(cid):
        return
    if not can_speak(uid, cid):
        return

    text = resolve_text(m.text, cid)
    k    = botkey()
    ch   = r.get(f"{DEV_ID}:BotChannel") or "yqyqy66"

    async def _list_members(rkey: str, title: str, min_checker):
        if not min_checker(uid, cid):
            return await m.reply(f"{k} هذا الأمر يخص ( {title} ) بس")
        members = r.smembers(f"{cid}:{rkey}s:{DEV_ID}")
        if not members:
            return await m.reply(f"{k} مافيه {title}")
        txt = f"- {title}:\n\n"
        for i, mid in enumerate(members, 1):
            if i > 100: break
            try:
                user = await c.get_users(int(mid))
                if user.username:
                    txt += f"{i} ➣ @{user.username} ࿓ ( `{user.id}` )\n"
                else:
                    txt += f"{i} ➣ {user.mention} ࿓ ( `{user.id}` )\n"
            except Exception:
                txt += f"{i} ➣ [{mid}](tg://user?id={mid}) ࿓ ( `{mid}` )\n"
        txt += "\n☆"
        return await m.reply(txt)

    if text == "المالكين الاساسيين":
        return await _list_members("rankGOWNER", "المالكين الاساسيين", is_dev)
    if text == "المالكين":
        return await _list_members("rankOWNER", "المالكين", is_gowner)
    if text == "المدراء":
        return await _list_members("rankMOD", "المدراء", is_owner)
    if text == "الادمنيه":
        return await _list_members("rankADMIN", "الادمنيه", is_mod)
    if text == "المميزين":
        return await _list_members("rankPRE", "المميزين", is_admin)
    if text == "المكتومين":
        if not is_mod(uid, cid):
            return await m.reply(f"{k} هذا الأمر يخص ( المدير وفوق ) بس")
        members = r.smembers(f"{cid}:listMUTEs:{DEV_ID}") or r.smembers(f"{cid}:listMUTE:{DEV_ID}")
        if not members:
            return await m.reply(f"{k} مافيه مكتومين")
        txt = "- المكتومين:\n\n"
        for i, mid in enumerate(members, 1):
            if i > 100: break
            try:
                user = await c.get_users(int(mid))
                if user.username:
                    txt += f"{i} ➣ @{user.username} ࿓ ( `{user.id}` )\n"
                else:
                    txt += f"{i} ➣ {user.mention} ࿓ ( `{user.id}` )\n"
            except Exception:
                txt += f"{i} ➣ [{mid}](tg://user?id={mid}) ࿓ ( `{mid}` )\n"
        txt += "\n☆"
        return await m.reply(txt)


@Client.on_message(filters.text & filters.group, group=13)
async def del_ranks_handler(c: Client, m: Message):
    if not m.from_user:
        return
    cid, uid = m.chat.id, m.from_user.id
    if not group_enabled(cid):
        return
    if not can_speak(uid, cid):
        return

    text = resolve_text(m.text, cid)
    k    = botkey()

    DEMOTED = "{} ابشر عيني {}\n{} مسحت ( {} ) من {}\n☆\n"

    async def _clear_list(rkey: str, title: str, list_key: str, min_checker):
        if not min_checker(uid, cid):
            return await m.reply(f"{k} هذا الأمر يخص ( {title} ) بس")
        members = r.smembers(list_key)
        if not members:
            return await m.reply(f"{k} مافيه {title}")
        count = 0
        for mid in list(members):
            try: mid_int = int(mid)
            except: mid_int = mid
            r.srem(list_key, mid)
            r.delete(f"{cid}:{rkey}:{mid_int}:{DEV_ID}")
            count += 1
        return await m.reply(DEMOTED.format(k, get_rank(uid, cid), k, count, title))

    if text == "مسح المالكين الاساسيين":
        return await _clear_list("rankGOWNER", "المالكين الاساسيين",
                                  f"{cid}:rankGOWNERs:{DEV_ID}", is_dev)
    if text == "مسح المالكين":
        return await _clear_list("rankOWNER", "المالكين",
                                  f"{cid}:rankOWNERs:{DEV_ID}", is_gowner)
    if text == "مسح المدراء":
        return await _clear_list("rankMOD", "المدراء",
                                  f"{cid}:rankMODs:{DEV_ID}", is_owner)
    if text in ("مسح الادمنيه", "مسح الادمن"):
        return await _clear_list("rankADMIN", "الادمن",
                                  f"{cid}:rankADMINs:{DEV_ID}", is_mod)
    if text == "مسح المميزين":
        return await _clear_list("rankPRE", "المميزين",
                                  f"{cid}:rankPREs:{DEV_ID}", is_mod)
    if text == "مسح المكتومين":
        if not is_mod(uid, cid):
            return await m.reply(f"{k} هذا الأمر يخص ( المدير وفوق ) بس")
        muted = r.smembers(f"{cid}:listMUTE:{DEV_ID}")
        if not muted:
            return await m.reply(f"{k} مافيه مكتومين")
        count = 0
        for mid in list(muted):
            r.srem(f"{cid}:listMUTE:{DEV_ID}", mid)
            r.delete(f"{mid}:mute:{cid}:{DEV_ID}")
            count += 1
        return await m.reply(DEMOTED.format(k, get_rank(uid, cid), k, count, "المكتومين"))

    if text == "مسح المكتومين عام":
        if not is_dev(uid, cid):
            return await m.reply(f"{k} هذا الأمر يخص ( المطور ) بس")
        muted = r.smembers(f"listMUTE:{DEV_ID}")
        if not muted:
            return await m.reply(f"{k} مافيه مكتومين عام")
        count = 0
        for mid in list(muted):
            r.srem(f"listMUTE:{DEV_ID}", mid)
            r.delete(f"{mid}:mute:{DEV_ID}")
            count += 1
        return await m.reply(DEMOTED.format(k, get_rank(uid, cid), k, count, "المكتومين عام"))

    if text == "مسح المحظورين عام":
        if not is_dev(uid, cid):
            return await m.reply(f"{k} هذا الأمر يخص ( المطور ) بس")
        gbanned = r.smembers(f"listGBAN:{DEV_ID}")
        if not gbanned:
            return await m.reply(f"{k} مافيه محظورين عام")
        count = 0
        for gid in list(gbanned):
            r.srem(f"listGBAN:{DEV_ID}", gid)
            r.delete(f"{gid}:gban:{DEV_ID}")
            count += 1
        return await m.reply(DEMOTED.format(k, get_rank(uid, cid), k, count, "المحظورين عام"))
