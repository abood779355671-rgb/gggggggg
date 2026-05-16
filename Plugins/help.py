"""
أمر الاوامر - يعرض جميع أوامر البوت بحسب رتبة المستخدم
"""
from pyrogram import Client, filters
from pyrogram.types import (
    Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
)
from pyrogram.enums import ParseMode

from config import r, DEV_ID, botkey, botname
from helpers.ranks import (
    get_rank, is_pre, is_admin, is_mod, is_owner,
    is_gowner, is_dev,
)
from helpers.utils import group_enabled, resolve_text, can_speak


# ═══════════════════════════════════════════════════════════════
#  تعريف الأوامر لكل فئة
# ═══════════════════════════════════════════════════════════════

SECTIONS = {
    "general": {
        "emoji": "🌐",
        "title": "العامة",
        "min_rank": 0,
        "commands": [
            ("رتبة / رتبتي",         "عرض رتبتك أو رتبة شخص بالرد عليه"),
            ("معلومات",              "معلومات المجموعة ورتبتك"),
            ("الاوامر",              "عرض هذه القائمة"),
        ],
    },
    "games": {
        "emoji": "🎮",
        "title": "الألعاب",
        "min_rank": 0,
        "commands": [
            ("العاب",              "قائمة الألعاب المتاحة"),
            ("لعبة [اسم]",         "بدء لعبة (ارقام، كلمات، دول، اعلام...)"),
            ("انهاء",             "إنهاء اللعبة الجارية (ادمن+)"),
            ("نقاطي",             "عرض نقاطك في الألعاب"),
            ("الترتيب",           "ترتيب المجموعة في الألعاب"),
            ("مسح النقاط",        "مسح جميع النقاط (مدير+)"),
        ],
    },
    "media": {
        "emoji": "🎵",
        "title": "الميديا",
        "min_rank": 0,
        "commands": [
            ("بحث [كلمة] / yt [كلمة]", "تحميل صوت من يوتيوب"),
            ("يوت [كلمة]",             "بحث يوتيوب مع قائمة نتائج"),
            ("تيك [رابط]",             "تحميل فيديو تيك توك"),
            ("ساوند [كلمة]",           "بحث في ساوند كلاود"),
            ("شازام",                  "التعرف على صوت (رد على رسالة)"),
            ("شازام [كلمة]",           "بحث كلمات أغنية"),
            ("سورة [اسم]",             "الاستماع لسورة قرآنية"),
            ("ميمز",                   "مقطع ميمز عشوائي"),
        ],
    },
    "filters": {
        "emoji": "💬",
        "title": "الردود والفلاتر",
        "min_rank": 1,   # مميز وفوق
        "commands": [
            ("الردود",               "عرض ردود المجموعة"),
            ("اضف ردي",              "إضافة رد خاص بك (للأعضاء)"),
            ("مسح ردي",              "مسح ردك الخاص"),
        ],
    },
    "admin": {
        "emoji": "🛡️",
        "title": "الإدارة",
        "min_rank": 2,   # ادمن وفوق
        "commands": [
            ("كتم (رد/@user)",        "كتم مستخدم في المجموعة"),
            ("الغاء الكتم (رد/@user)", "رفع الكتم"),
            ("الفلاتر العامة",        "عرض قائمة ردود المطور"),
        ],
    },
    "mod": {
        "emoji": "⚙️",
        "title": "المدير",
        "min_rank": 3,   # مدير وفوق
        "commands": [
            ("اضف رد [كلمة]",        "إضافة رد للمجموعة"),
            ("مسح رد [كلمة]",        "مسح رد من المجموعة"),
            ("الردود",               "قائمة ردود المجموعة"),
            ("مسح الردود",           "مسح جميع الردود"),
            ("اضف رد مميز",          "إضافة رد عشوائي متعدد"),
            ("مسح رد مميز",          "مسح رد مميز"),
            ("الردود المميزه",        "قائمة الردود المميزة"),
            ("تعطيل الردود",         "تعطيل ردود المجموعة"),
            ("تفعيل الردود",         "تفعيل ردود المجموعة"),
            ("المكتومين",            "قائمة المكتومين"),
            ("مسح المكتومين",        "مسح جميع المكتومين"),
        ],
    },
    "owner": {
        "emoji": "👑",
        "title": "المالك",
        "min_rank": 4,   # مالك وفوق
        "commands": [
            ("اضف امر / تغيير امر",  "إضافة أمر مخصص"),
            ("مسح امر [أمر]",        "مسح أمر مخصص"),
            ("الاوامر المضافة",       "قائمة الأوامر المخصصة"),
            ("مسح الاوامر",          "مسح جميع الأوامر المخصصة"),
            ("المدراء",              "قائمة المدراء"),
            ("الادمنيه",             "قائمة الادمن"),
            ("المميزين",             "قائمة المميزين"),
            ("مسح المدراء",          "مسح جميع المدراء"),
            ("مسح الادمنيه",         "مسح جميع الادمن"),
            ("مسح المميزين",         "مسح جميع المميزين"),
            ("تعطيل ردود المطور",    "إيقاف الردود العامة للمطور"),
            ("تفعيل ردود المطور",    "تفعيل الردود العامة للمطور"),
        ],
    },
    "gowner": {
        "emoji": "💎",
        "title": "المالك الأساسي",
        "min_rank": 5,
        "commands": [
            ("المالكين",             "قائمة المالكين"),
            ("مسح المالكين",         "مسح جميع المالكين"),
            ("قفل امر [أمر]",        "قفل أمر بصلاحية معينة"),
            ("فتح امر [أمر]",        "فتح أمر مقفول"),
            ("الاوامر المقفوله",      "قائمة الأوامر المقفولة"),
            ("مسح الاوامر المقفوله", "مسح جميع الأوامر المقفولة"),
        ],
    },
    "dev": {
        "emoji": "⚡",
        "title": "المطور",
        "min_rank": 6,
        "commands": [
            ("كتم عام (رد/@user)",           "كتم مستخدم في جميع المجموعات"),
            ("الغاء الكتم العام (رد/@user)", "رفع الكتم العام"),
            ("حظر عام (رد/@user)",           "حظر مستخدم من جميع المجموعات"),
            ("الغاء الحظر العام (رد/@user)", "رفع الحظر العام"),
            ("حظر عام من الالعاب",           "حظر من ألعاب البوت"),
            ("الغاء الحظر العام من الالعاب", "رفع حظر الألعاب"),
            ("مسح المكتومين عام",            "مسح جميع المكتومين عاماً"),
            ("مسح المحظورين عام",            "مسح جميع المحظورين عاماً"),
            ("المالكين الاساسيين",           "قائمة المالكين الأساسيين"),
            ("مسح المالكين الاساسيين",       "مسح جميع المالكين الأساسيين"),
            ("اضف فلتر عام [كلمة]",          "إضافة رد عام للمطور"),
            ("حذف فلتر عام [كلمة]",          "حذف رد عام"),
            ("الردود العامه",                "قائمة الردود العامة"),
            ("مسح الردود العامه",            "مسح جميع الردود العامة"),
        ],
    },
}


# ═══════════════════════════════════════════════════════════════
#  دالة بناء الرسالة
# ═══════════════════════════════════════════════════════════════

def _rank_level(uid: int, cid: int) -> int:
    if is_dev(uid, cid):    return 6
    if is_gowner(uid, cid): return 5
    if is_owner(uid, cid):  return 4
    if is_mod(uid, cid):    return 3
    if is_admin(uid, cid):  return 2
    if is_pre(uid, cid):    return 1
    return 0


def _build_page(uid: int, cid: int, section_key: str, k: str) -> tuple[str, InlineKeyboardMarkup]:
    """يبني نص + كيبورد لصفحة معينة."""
    level = _rank_level(uid, cid)
    rank  = get_rank(uid, cid)
    name  = botname()

    sec   = SECTIONS[section_key]
    keys  = list(SECTIONS.keys())
    idx   = keys.index(section_key)

    # ── فلترة الأقسام المتاحة للمستخدم ─────────────────────────
    available = [k2 for k2, v in SECTIONS.items() if level >= v["min_rank"]]
    if section_key not in available:
        section_key = available[0]
        sec = SECTIONS[section_key]
        idx = keys.index(section_key)

    # ── بناء النص ───────────────────────────────────────────────
    lines = []
    lines.append(f"<b>✦ {name} — {sec['emoji']} {sec['title']}</b>")
    lines.append(f"<i>رتبتك: {rank}</i>")
    lines.append("─" * 22)

    for cmd, desc in sec["commands"]:
        lines.append(f"  <code>{cmd}</code>")
        lines.append(f"  <i>↳ {desc}</i>")
        lines.append("")

    lines.append("─" * 22)
    lines.append(f"<i>الصفحة {available.index(section_key)+1} من {len(available)}</i>")

    text = "\n".join(lines)

    # ── بناء الكيبورد ────────────────────────────────────────────
    # صف التنقل بين الأقسام المتاحة (حتى 4 في صف)
    nav_buttons = []
    for sk in available:
        sv = SECTIONS[sk]
        is_cur = "•" if sk == section_key else ""
        nav_buttons.append(
            InlineKeyboardButton(
                f"{is_cur}{sv['emoji']}{is_cur}",
                callback_data=f"help:{uid}:{sk}"
            )
        )

    # تقسيم أزرار التنقل على صفوف (4 في كل صف)
    rows = [nav_buttons[i:i+4] for i in range(0, len(nav_buttons), 4)]

    # زر الإغلاق
    rows.append([InlineKeyboardButton("✖ إغلاق", callback_data=f"help:{uid}:close")])

    return text, InlineKeyboardMarkup(rows)


# ═══════════════════════════════════════════════════════════════
#  المعالج الرئيسي
# ═══════════════════════════════════════════════════════════════

@Client.on_message(filters.text & filters.group, group=50)
async def help_handler(c: Client, m: Message):
    if not m.from_user:
        return
    cid, uid = m.chat.id, m.from_user.id
    if not group_enabled(cid):
        return

    text = resolve_text(m.text, cid)
    k    = botkey()

    if text not in ("الاوامر", "اوامر", "المساعدة", "مساعدة", "help"):
        return

    content, markup = _build_page(uid, cid, "general", k)
    await m.reply(
        content,
        parse_mode=ParseMode.HTML,
        reply_markup=markup,
        disable_web_page_preview=True,
    )


# ═══════════════════════════════════════════════════════════════
#  معالج الأزرار
# ═══════════════════════════════════════════════════════════════

@Client.on_callback_query(filters.regex(r"^help:"))
async def help_callback(c: Client, query: CallbackQuery):
    parts = query.data.split(":")
    # help:{uid}:{section}
    if len(parts) < 3:
        return await query.answer()

    owner_id   = int(parts[1])
    section_key = parts[2]

    # فقط صاحب الرسالة يتحكم
    if query.from_user.id != owner_id:
        return await query.answer("هذه الرسالة ليست لك 😅", show_alert=True)

    k   = botkey()
    cid = query.message.chat.id
    uid = query.from_user.id

    if section_key == "close":
        try:
            await query.message.delete()
        except Exception:
            pass
        return await query.answer()

    if section_key not in SECTIONS:
        return await query.answer()

    level = _rank_level(uid, cid)
    if level < SECTIONS[section_key]["min_rank"]:
        return await query.answer("ما عندك صلاحية لهذا القسم", show_alert=True)

    content, markup = _build_page(uid, cid, section_key, k)
    try:
        await query.edit_message_text(
            content,
            parse_mode=ParseMode.HTML,
            reply_markup=markup,
            disable_web_page_preview=True,
        )
    except Exception:
        pass
    await query.answer()
