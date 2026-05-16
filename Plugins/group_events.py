"""
أحداث المجموعة - تتبع الأحداث وإعلام المطور
"""
from pyrogram import Client, filters
from pyrogram.types import Message, ChatMemberUpdated

from config import r, DEV_ID, botkey
from helpers.ranks import is_dev, get_rank
from helpers.utils import group_enabled


@Client.on_message(filters.left_chat_member, group=6)
async def on_left_member(c: Client, m: Message):
    """عند مغادرة عضو"""
    cid = m.chat.id
    if not group_enabled(cid):
        return
    if not r.get(f"{cid}:trackLeave:{DEV_ID}"):
        return
    k = botkey()
    try:
        await m.reply(
            f"{k} غادر المجموعة: {m.left_chat_member.mention}",
            disable_web_page_preview=True,
        )
    except Exception:
        pass


@Client.on_message(filters.text & filters.group, group=8)
async def group_settings(c: Client, m: Message):
    """إعدادات متعلقة بأحداث المجموعة"""
    if not m.from_user:
        return
    cid, uid = m.chat.id, m.from_user.id
    if not group_enabled(cid):
        return

    text = m.text.strip() if m.text else ""
    k    = botkey()

    if text == "تفعيل مغادرة":
        if not is_dev(uid, cid):
            return await m.reply(f"{k} هذا الأمر للمطور فقط")
        r.set(f"{cid}:trackLeave:{DEV_ID}", 1)
        return await m.reply(f"{k} سيتم الإعلان عن مغادرة الأعضاء ✅")

    if text == "تعطيل مغادرة":
        if not is_dev(uid, cid):
            return await m.reply(f"{k} هذا الأمر للمطور فقط")
        r.delete(f"{cid}:trackLeave:{DEV_ID}")
        return await m.reply(f"{k} تم تعطيل إعلان المغادرة")

    if text == "معلومات":
        rank = get_rank(uid, cid)
        me   = await c.get_me()
        members_count = await c.get_chat_members_count(cid)
        return await m.reply(
            f"{k} **معلومات المجموعة**\n\n"
            f"الاسم: **{m.chat.title}**\n"
            f"الأيدي: `{cid}`\n"
            f"عدد الأعضاء: **{members_count}**\n\n"
            f"{k} **معلوماتك**\n"
            f"الاسم: {m.from_user.mention}\n"
            f"الأيدي: `{uid}`\n"
            f"رتبتك: **{rank}**"
        )


# ─────────────────────────────────────────────────────────────────────────────
# عند طرد البوت - إعلام المطور وحذف البيانات
# ─────────────────────────────────────────────────────────────────────────────

def _dev_notify(c, text: str, reply_markup=None):
    """يُرسل رسالة للمطور أو مجموعة المطورين."""
    import time
    from helpers.ranks import get_devs
    dev_group = r.get(f"DevGroup:{DEV_ID}")
    if dev_group:
        try:
            c.send_message(int(dev_group), text,
                           disable_web_page_preview=True,
                           reply_markup=reply_markup)
        except Exception:
            pass
    else:
        for dev in get_devs():
            try:
                c.send_message(int(dev), text,
                               disable_web_page_preview=True,
                               reply_markup=reply_markup)
                time.sleep(2)
            except Exception:
                pass


@Client.on_message(filters.left_chat_member)
async def kicked_from_group(c: Client, m: Message):
    """عند طرد البوت من مجموعة."""
    if m.left_chat_member.id != (await c.get_me()).id:
        return
    k    = botkey()
    cid  = m.chat.id
    uid  = m.from_user.id if m.from_user else 0
    usr  = m.from_user
    text = (
        f"{k} من「 {usr.mention if usr else uid} 」\n"
        f"{k} يوزره : {'@'+usr.username if usr and usr.username else 'مافيه'}\n"
        f"{k} ايديه : `{uid}`\n\n"
        f"{k} قام بطرد البوت من المجموعة:\n\n"
        f"{k} اسم المجموعة : {m.chat.title}\n"
        f"{k} يوزر المجموعة : {'@'+m.chat.username if m.chat.username else 'مافيه'}\n"
        f"{k} ايدي المجموعة : `{cid}`\n"
        f"{k} تم مسح بيانات المجموعة\n\n☆"
    )
    r.srem(f"enablelist:{DEV_ID}", cid)
    r.delete(f"{cid}:enable:{DEV_ID}")
    groups_count = len(r.smembers(f"enablelist:{DEV_ID}") or set())
    if groups_count:
        text += f"\n{k} عدد المجموعات الآن: {groups_count}"
    try:
        _dev_notify(c, text)
    except Exception:
        pass


@Client.on_chat_member_updated(filters.group, group=5)
async def chat_member_updated(c: Client, m: ChatMemberUpdated):
    """تفعيل تلقائي عند ترقية البوت، تعطيل عند تنزيله."""
    from pyrogram.enums import ChatMemberStatus
    from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    from config import botname as _botname
    import time

    k = botkey()
    try:
        if not m.new_chat_member:
            return
        bot_id = (await c.get_me()).id
        if m.new_chat_member.user.id != bot_id:
            return

        cid = m.chat.id
        adder_id = m.from_user.id if m.from_user else 0
        adder_mention = m.from_user.mention if m.from_user else str(adder_id)

        status = m.new_chat_member.status

        # ── البوت أصبح عضواً عادياً → تعطيل ──────────────────────────────
        if status == ChatMemberStatus.MEMBER:
            if r.get(f"{cid}:enable:{DEV_ID}"):
                await c.send_message(cid, f"{k} من「 {adder_mention} 」\n{k} تم تعطيل المجموعة تلقائياً\n☆")
                r.delete(f"{cid}:enable:{DEV_ID}")
                r.srem(f"enablelist:{DEV_ID}", cid)

        # ── البوت أصبح أدمن ──────────────────────────────────────────────
        elif status == ChatMemberStatus.ADMINISTRATOR:
            priv = m.new_chat_member.privileges
            full_priv = (priv and priv.can_manage_chat and priv.can_delete_messages
                         and priv.can_restrict_members and priv.can_pin_messages
                         and priv.can_invite_users)

            if not full_priv:
                # صلاحيات ناقصة → تعطيل
                if r.get(f"{cid}:enable:{DEV_ID}"):
                    await c.send_message(cid, f"{k} من「 {adder_mention} 」\n{k} تم تعطيل المجموعة - الصلاحيات غير كاملة\n☆")
                    r.delete(f"{cid}:enable:{DEV_ID}")
                    r.srem(f"enablelist:{DEV_ID}", cid)
            else:
                if not r.get(f"{cid}:enable:{DEV_ID}"):
                    if r.get(f"DisableBot:{DEV_ID}"):
                        return await c.send_message(cid, f"{k} تم تعطيل البوت الخدمي من المطور")
                    # تفعيل تلقائي
                    r.set(f"{cid}:enable:{DEV_ID}", 1)
                    r.sadd(f"enablelist:{DEV_ID}", cid)
                    # تعيين من أضافه مالكاً
                    r.set(f"{cid}:rankOWNER:{adder_id}:{DEV_ID}", 1)
                    r.sadd(f"{cid}:rankOWNERs:{DEV_ID}", adder_id)
                    # رفع الأدمن الحاليين
                    from pyrogram.enums import ChatMembersFilter
                    async for member in c.get_chat_members(cid, filter=ChatMembersFilter.ADMINISTRATORS):
                        if not member.user.is_bot and not member.user.is_deleted:
                            if member.status == ChatMemberStatus.OWNER:
                                r.set(f"{cid}:rankGOWNER:{member.user.id}:{DEV_ID}", 1)
                                r.sadd(f"{cid}:rankGOWNERs:{DEV_ID}", member.user.id)
                            elif member.status == ChatMemberStatus.ADMINISTRATOR:
                                r.set(f"{cid}:rankADMIN:{member.user.id}:{DEV_ID}", 1)
                                r.sadd(f"{cid}:rankADMINs:{DEV_ID}", member.user.id)

                    bot_username = (await c.get_me()).username or ""
                    await c.send_message(
                        cid,
                        f"{k} من「 {adder_mention} 」\n{k} تم تفعيل المجموعة تلقائياً ✅\n☆",
                        reply_markup=InlineKeyboardMarkup([[
                            InlineKeyboardButton("Commands", url=f"https://t.me/{bot_username}?start=Commands")
                        ]]) if bot_username else None,
                    )
                    # إعلام المطور
                    chat = await c.get_chat(cid)
                    groups_count = len(r.smembers(f"enablelist:{DEV_ID}") or set())
                    notify_text = (
                        f"{k} من「 {adder_mention} 」\n"
                        f"{k} يوزره : {'@'+m.from_user.username if m.from_user and m.from_user.username else 'مافيه'}\n"
                        f"{k} ايديه : `{adder_id}`\n\n"
                        f"{k} تم تفعيل البوت بمجموعة جديدة:\n\n"
                        f"{k} اسم المجموعة : {m.chat.title}\n"
                        f"{k} يوزر المجموعة : {'@'+m.chat.username if m.chat.username else 'مافيه'}\n"
                        f"{k} ايدي المجموعة : `{cid}`\n"
                        f"{k} عدد المجموعات الآن : {groups_count}\n\n☆"
                    )
                    markup = None
                    if chat.invite_link:
                        markup = InlineKeyboardMarkup([[InlineKeyboardButton(m.chat.title, url=chat.invite_link)]])
                    _dev_notify(c, notify_text, markup)
    except Exception:
        pass
