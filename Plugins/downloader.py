"""
تحميل من يوتيوب / تيك توك / ساوند كلاود + شازام
أوامر:
  بحث [كلمة] / yt [كلمة]     → بحث يوتيوب وتحميل صوت أول نتيجة
  يوت [كلمة]                  → بحث يوتيوب مع قائمة نتائج
  تيك [رابط]                  → تحميل فيديو تيك توك
  ساوند [كلمة]                → بحث ساوند كلاود
  شازام                       → التعرف على صوت (رد على رسالة)
  شازام [كلمة]                → بحث كلمات أغنية
"""
import os
import re
import time
import random
import asyncio

import yt_dlp
import requests
import wget

from pyrogram import Client, filters
from pyrogram.types import (
    Message, InlineKeyboardMarkup, InlineKeyboardButton,
    InlineQueryResultArticle, InputTextMessageContent,
)

from config import r, DEV_ID, botkey
from helpers.ranks import is_admin
from helpers.utils import group_enabled, can_speak, resolve_text

try:
    from pytube import YouTube
    PYTUBE_OK = True
except Exception:
    PYTUBE_OK = False

try:
    from youtube_search import YoutubeSearch as YTSearch
    YTSEARCH_OK = True
except Exception:
    YTSEARCH_OK = False

try:
    from shazamio import Shazam
    shazam = Shazam()
    SHAZAM_OK = True
except Exception:
    SHAZAM_OK = False


# ── helpers ───────────────────────────────────────────────────────────────

def _find_urls(text: str):
    pat = r"(?i)\b((?:https?://|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)(?:[^\s()<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))+(?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|[^\s!()\[\]{};:'\".,<>?«»""'']))"
    return [x[0] for x in re.findall(pat, text)]

def _seconds_to_str(seconds: int) -> str:
    return time.strftime("%M:%S", time.gmtime(seconds))

def _channel_markup(channel: str):
    return InlineKeyboardMarkup([[InlineKeyboardButton("🧚‍♀️", url=f"https://t.me/{channel}")]])


# ── يوتيوب: بحث مع قائمة نتائج ──────────────────────────────────────────

@Client.on_message(filters.text & filters.group, group=32)
async def downloader_handler(c: Client, m: Message):
    if not m.from_user:
        return
    cid, uid = m.chat.id, m.from_user.id
    if not group_enabled(cid):
        return
    if not can_speak(uid, cid):
        return

    text    = resolve_text(m.text, cid)
    k       = botkey()
    channel = r.get(f"{DEV_ID}:BotChannel") or "t.me"

    # ── يوت [بحث] → قائمة نتائج ─────────────────────────────────────────
    if text.startswith("يوت ") and YTSEARCH_OK:
        if r.get(f"{cid}:disableYT:{DEV_ID}") or r.get(f":disableYT:{DEV_ID}"):
            return
        query = text.split(None, 1)[1]
        results = YTSearch(query, max_results=4).to_dict()
        keyboard = []
        for res in results:
            keyboard.append([InlineKeyboardButton(
                res["title"][:60],
                callback_data=f"{uid}GET{res['id']}"
            )])
        sent = await m.reply(
            f"{k} البحث ~ {query}",
            reply_markup=InlineKeyboardMarkup(keyboard),
            disable_web_page_preview=True,
        )
        r.set(f"{sent.id}:one_minute:{uid}", 1, ex=60)
        return

    # ── بحث [كلمة] / yt [كلمة] → أول نتيجة صوت ──────────────────────────
    if (text.startswith("بحث ") or text.startswith("yt ")) and YTSEARCH_OK and PYTUBE_OK:
        if r.get(f"{cid}:disableYT:{DEV_ID}") or r.get(f":disableYT:{DEV_ID}"):
            return
        query = text.split(None, 1)[1]
        results = YTSearch(query, max_results=1).to_dict()
        if not results:
            return await m.reply(f"{k} ما لقيت نتائج")
        res = results[0]
        vid_id = res["id"]
        url = f"https://youtu.be/{vid_id}"

        # تحقق من الكاش
        cached = r.get(f"ytaudio:{vid_id}")
        if cached:
            dur = r.get(f"ytaudio:{vid_id}:dur") or "?"
            return await m.reply_audio(
                cached,
                caption=f"@{channel} ~ ⏳ {dur}",
                reply_markup=_channel_markup(channel),
            )

        yt = YouTube(url)
        if yt.length > 1500:
            return await m.reply(f"{k} الصوت أكثر من 25 دقيقة ما أقدر أنزله")

        dur_str = _seconds_to_str(yt.length)
        ydl_ops = {
            "format": "bestaudio[ext=m4a]",
            "forceduration": True,
            "outtmpl": "%(id)s.%(ext)s",
        }
        with yt_dlp.YoutubeDL(ydl_ops) as ydl:
            info = ydl.extract_info(url, download=True)
            audio_file = ydl.prepare_filename(info)

        mp3_file = audio_file.replace(".m4a", ".mp3")
        if os.path.exists(audio_file):
            os.rename(audio_file, mp3_file)

        thumb = None
        try:
            thumb = wget.download(yt.thumbnail_url)
        except Exception:
            pass

        sent = await m.reply_audio(
            mp3_file,
            title=yt.title,
            thumb=thumb,
            duration=yt.length,
            performer=yt.author,
            caption=f"@{channel} ~ ⏳ {dur_str}",
            reply_markup=_channel_markup(channel),
        )
        r.set(f"ytaudio:{vid_id}", sent.audio.file_id)
        r.set(f"ytaudio:{vid_id}:dur", dur_str)

        try:
            os.remove(mp3_file)
        except Exception:
            pass
        if thumb:
            try:
                os.remove(thumb)
            except Exception:
                pass
        return

    # ── تيك [رابط] → فيديو تيك توك ──────────────────────────────────────
    if text.startswith("تيك "):
        if r.get(f"{cid}:disableTik:{DEV_ID}") or r.get(f":disableYT:{DEV_ID}"):
            return
        urls = _find_urls(text)
        if not urls:
            return
        url = urls[0]
        try:
            with yt_dlp.YoutubeDL({}) as ytdl:
                vid_data = ytdl.extract_info(url, download=False)
        except Exception:
            return await m.reply(f"{k} فشل التحميل")
        title    = vid_data.get("fulltitle", "")
        duration = int(vid_data.get("duration", 0))
        dur_str  = _seconds_to_str(duration)
        file_url = vid_data.get("url", "")
        views    = vid_data.get("view_count", 0)
        likes    = vid_data.get("like_count", 0)
        comments = vid_data.get("comment_count", 0)
        reposts  = vid_data.get("repost_count", 0)
        uploader = vid_data.get("uploader", "")
        creator  = vid_data.get("creator", uploader)
        uploader_url = vid_data.get("uploader_url", "")
        caption = (
            f"`{title}`\n{k} الطول: {dur_str}\n{k} المشاهدات: {views:,}\n"
            f"{k} اللايكات: {likes:,}\n{k} الكومنت: {comments:,}\n"
            f"{k} الاكسبلور: {reposts:,}\n\n~ @{channel}"
        )
        reply_markup = InlineKeyboardMarkup(
            [[InlineKeyboardButton(f"{creator} - @{uploader}", url=uploader_url)]]
        ) if uploader_url else None
        try:
            await m.reply_video(file_url, caption=caption, reply_markup=reply_markup)
        except Exception:
            with yt_dlp.YoutubeDL({"outtmpl": "%(id)s.%(ext)s"}) as ytdl:
                vid_data2 = ytdl.extract_info(url, download=True)
                fn = ytdl.prepare_filename(vid_data2)
            await m.reply_video(fn, caption=caption, reply_markup=reply_markup)
            try:
                os.remove(fn)
            except Exception:
                pass
        return

    # ── ساوند [كلمة] → بحث ساوند كلاود ─────────────────────────────────
    if text.startswith("ساوند "):
        if r.get(f"{cid}:disableSound:{DEV_ID}") or r.get(f":disableYT:{DEV_ID}"):
            return
        query = text.split(None, 1)[1]
        try:
            data = requests.get(f"https://m.soundcloud.com/search?q={query}", timeout=8)
            urls_sc = re.findall(r'data-testid="cell-entity-link" href="([^"]+)', data.text)
            names   = re.findall(r'<div class="Information_CellTitle__2KitR">([^<]+)', data.text)
        except Exception:
            return await m.reply(f"{k} فشل البحث في ساوند كلاود")
        buttons = []
        for i in range(min(5, len(urls_sc))):
            buttons.append([InlineKeyboardButton(
                names[i] if i < len(names) else urls_sc[i],
                switch_inline_query_current_chat=f"{urls_sc[i]}#SOUND",
            )])
        await m.reply(f"{k} بحث الساوند ~ {query}", reply_markup=InlineKeyboardMarkup(buttons))
        return

    # ── رابط ساوند كلاود مباشر ───────────────────────────────────────────
    found = _find_urls(text)
    if found and "soundcloud" in found[0]:
        if r.get(f"{cid}:disableSound:{DEV_ID}") or r.get(f":disableYT:{DEV_ID}"):
            return
        sc_id = found[0].split("soundcloud.com")[1]
        return await m.reply(
            f"@{channel} - ☁️",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(
                    "اضغط هنا لاختيار صيغة التحميل",
                    switch_inline_query_current_chat=f"{sc_id}#SOUND",
                )],
                [InlineKeyboardButton("☁️", url=f"t.me/{channel}")],
            ]),
        )

    # ── تحميل صوت / بصمة ساوند كلاود (#AUDIO / #VOICE) ─────────────────
    if text.endswith("#AUDIO") or text.endswith("#VOICE"):
        found = _find_urls(text)
        if found and "soundcloud" in found[0]:
            if r.get(f"{cid}:disableSound:{DEV_ID}") or r.get(f":disableYT:{DEV_ID}"):
                return
            is_voice = text.endswith("#VOICE")
            url = found[0]
            sc_key = url.split("soundcloud.com/")[1] if "soundcloud.com/" in url else url
            cache_k = f"{sc_key}:soundVoice" if is_voice else f"{sc_key}:sound"
            if r.get(cache_k):
                if is_voice:
                    return await m.reply_voice(r.get(cache_k))
                return await m.reply_audio(r.get(cache_k))
            try:
                with yt_dlp.YoutubeDL({}) as ytdl:
                    info = ytdl.extract_info(url, download=False)
                    if int(info.get("duration", 0)) > 1500:
                        return await m.reply(f"{k} مقطع أكثر من 25 دقيقة ما أقدر أنزله")
                with yt_dlp.YoutubeDL({"outtmpl": "%(id)s.%(ext)s"}) as ytdl:
                    info = ytdl.extract_info(url, download=True)
                    fn = ytdl.prepare_filename(info)
            except Exception:
                return await m.reply(f"{k} فشل التحميل")
            if is_voice:
                rid = random.randint(1, 100000)
                ogg = f"voice{rid}.ogg"
                os.system(f'ffmpeg -i "{fn}" -ac 1 -strict -2 -codec:a libopus -b:a 128k -vbr off -ar 24000 "{ogg}" -y -loglevel quiet')
                sent = await m.reply_voice(ogg)
                r.set(cache_k, sent.voice.file_id)
                for f in [fn, ogg]:
                    try: os.remove(f)
                    except: pass
            else:
                title = info.get("title", "صوت")
                dur   = int(info.get("duration", 0))
                sent  = await m.reply_audio(fn, title=title, performer=f"@{channel}", duration=dur)
                r.set(cache_k, sent.audio.file_id)
                try:
                    os.remove(fn)
                except Exception:
                    pass
            return


# ── ساوند كلاود Inline ───────────────────────────────────────────────────

@Client.on_inline_query(filters.regex("SOUND"))
async def soundcloud_inline(c: Client, query):
    url_part = query.query.split("#SOUND")[0]
    channel  = r.get(f"{DEV_ID}:BotChannel") or "t.me"
    prefix   = "https://soundcloud.com" if url_part.count("/") > 1 else "https://on.soundcloud.com"
    full_url = f"{prefix}{url_part}"
    await query.answer(
        results=[
            InlineQueryResultArticle(
                title="اضغط للتحميل - صوت",
                description="~ ساوند كلاود",
                url=f"https://t.me/{channel}",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🧚‍♀️", url=f"t.me/{channel}")]]),
                input_message_content=InputTextMessageContent(f"{full_url} #AUDIO", disable_web_page_preview=True),
            ),
            InlineQueryResultArticle(
                title="اضغط للتحميل - بصمة",
                description="~ ساوند كلاود",
                url=f"https://t.me/{channel}",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🧚‍♀️", url=f"t.me/{channel}")]]),
                input_message_content=InputTextMessageContent(f"{full_url} #VOICE", disable_web_page_preview=True),
            ),
        ],
        cache_time=1,
    )


# ── يوتيوب Callback: قائمة نتائج → اختيار نوع ───────────────────────────

@Client.on_callback_query(filters.regex("GET"))
async def yt_get_info(c: Client, query):
    if not PYTUBE_OK:
        return
    user_id, vid_id = query.data.split("GET")
    if str(query.from_user.id) != user_id:
        return
    if not r.get(f"{query.message.id}:one_minute:{user_id}"):
        k = botkey()
        await query.answer(f"{k} مرّت أكثر من دقيقة، ابحث مرة أخرى", show_alert=True)
        return await query.message.delete()
    if r.get(f"{query.message.chat.id}:disableYT:{DEV_ID}"):
        return
    await query.message.delete()
    channel = r.get(f"{DEV_ID}:BotChannel") or "t.me"
    yt  = YouTube(f"https://youtu.be/{vid_id}")
    url = f"https://youtu.be/{vid_id}"
    await query.message.reply_to_message.reply_photo(
        yt.thumbnail_url,
        caption=f"@{channel} ~ {url}",
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton("♫ صوت", callback_data=f"{user_id}AUDIO{vid_id}"),
                InlineKeyboardButton("❖ فيديو", callback_data=f"{user_id}VIDEO{vid_id}"),
            ],
            [InlineKeyboardButton("🧚‍♀️", url=f"https://t.me/{channel}")],
        ]),
    )


@Client.on_callback_query(filters.regex("^[0-9]+AUDIO"))
async def yt_audio_download(c: Client, query):
    if not PYTUBE_OK:
        return
    user_id, vid_id = query.data.split("AUDIO")
    if str(query.from_user.id) != user_id:
        return
    if r.get(f"{query.message.chat.id}:disableYT:{DEV_ID}"):
        return
    channel = r.get(f"{DEV_ID}:BotChannel") or "t.me"
    rep = _channel_markup(channel)
    url = f"https://youtu.be/{vid_id}"

    cached = r.get(f"ytaudio:{vid_id}")
    if cached:
        dur_str = r.get(f"ytaudio:{vid_id}:dur") or "?"
        await query.edit_message_caption(f"@{channel} :)", reply_markup=rep)
        return await query.message.reply_audio(cached, caption=f"@{channel} ~ ⏳ {dur_str}")

    await query.edit_message_caption("جاري التحميل ..", reply_markup=rep)
    ydl_ops = {"format": "bestaudio[ext=m4a]", "forceduration": True, "outtmpl": "%(id)s.%(ext)s"}
    with yt_dlp.YoutubeDL(ydl_ops) as ydl:
        info = ydl.extract_info(url, download=True)
        audio_file = ydl.prepare_filename(info)
    mp3_file = audio_file.replace(".m4a", ".mp3")
    if os.path.exists(audio_file):
        os.rename(audio_file, mp3_file)
    dur     = int(info["duration"])
    dur_str = _seconds_to_str(dur)
    await query.edit_message_caption("✈️✈️✈️✈️✈️", reply_markup=rep)
    sent = await query.message.reply_audio(
        mp3_file,
        title=info["title"],
        duration=dur,
        performer=info.get("channel", ""),
        caption=f"@{channel} ~ ⏳ {dur_str}",
    )
    await query.edit_message_caption(f"@{channel} :)", reply_markup=rep)
    r.set(f"ytaudio:{vid_id}", sent.audio.file_id)
    r.set(f"ytaudio:{vid_id}:dur", dur_str)
    try:
        os.remove(mp3_file)
    except Exception:
        pass


@Client.on_callback_query(filters.regex("^[0-9]+VIDEO"))
async def yt_video_download(c: Client, query):
    if not PYTUBE_OK:
        return
    user_id, vid_id = query.data.split("VIDEO")
    if str(query.from_user.id) != user_id:
        return
    if r.get(f"{query.message.chat.id}:disableYT:{DEV_ID}"):
        return
    channel = r.get(f"{DEV_ID}:BotChannel") or "t.me"
    rep = _channel_markup(channel)
    url = f"https://youtu.be/{vid_id}"

    cached = r.get(f"ytvideo:{vid_id}")
    if cached:
        dur_str = r.get(f"ytvideo:{vid_id}:dur") or "?"
        await query.edit_message_caption(f"@{channel} :)", reply_markup=rep)
        return await query.message.reply_video(cached, caption=f"@{channel} ~ ⏳ {dur_str}")

    await query.edit_message_caption("جاري التحميل ..", reply_markup=rep)
    ydl_opts = {
        "format": "best",
        "outtmpl": "%(id)s.%(ext)s",
        "geo_bypass": True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        if int(info["duration"]) > 1500:
            return await query.edit_message_caption("فيديو أكثر من 25 دقيقة ما أقدر أنزله", reply_markup=rep)
        ydl.extract_info(url, download=True)
        fn = ydl.prepare_filename(info)
    dur     = int(info["duration"])
    dur_str = _seconds_to_str(dur)
    await query.edit_message_caption("✈️✈️✈️✈️✈️", reply_markup=rep)
    sent = await query.message.reply_video(
        fn,
        duration=dur,
        caption=f"@{channel} ~ ⏳ {dur_str}",
    )
    await query.edit_message_caption(f"@{channel} :)", reply_markup=rep)
    r.set(f"ytvideo:{vid_id}", sent.video.file_id)
    r.set(f"ytvideo:{vid_id}:dur", dur_str)
    try:
        os.remove(fn)
    except Exception:
        pass


# ── شازام ─────────────────────────────────────────────────────────────────

@Client.on_message(filters.regex("^شازام$") & filters.group)
async def shazam_identify(c: Client, m: Message):
    if not SHAZAM_OK:
        return
    if r.get(f"{m.chat.id}:disableShazam:{DEV_ID}"):
        return
    if not m.reply_to_message:
        return await m.reply("🧚‍♀️ ردّ على رسالة صوت / صوتية / فيديو")
    rep = m.reply_to_message
    media = rep.audio or rep.voice or rep.video
    if not media:
        return await m.reply("🧚‍♀️ ردّ على رسالة صوت / صوتية / فيديو")
    if media.duration and media.duration > 300:
        return await m.reply("🧚‍♀️ مدة المقطع أكثر من 5 دقائق")
    if media.file_size and media.file_size > 26214400:
        return await m.reply("🧚‍♀️ حجم المقطع أكثر من 25 ميجابايت")

    rid = random.randint(1, 100000)
    fn  = f"shazam{rid}.ogg"
    msg = await m.reply("جاري المعالجة ...")
    await rep.download(fn)
    out = await shazam.recognize_song(fn)
    try:
        os.remove(fn)
    except Exception:
        pass
    await msg.delete()

    if not out.get("matches"):
        return await m.reply("فشل التعرف على الصوت")

    k       = botkey()
    channel = r.get(f"{DEV_ID}:BotChannel") or "t.me"
    title   = out["track"]["title"]
    author  = out["track"]["subtitle"]
    url     = out["track"]["url"]
    try:
        photo = out["track"]["images"]["background"]
    except Exception:
        photo = None

    text = f"{k} اسم الصوت: [{title}]({url})\n{k} الفنان: {author}"
    key  = InlineKeyboardMarkup([[InlineKeyboardButton("🧚‍♀️", url=f"t.me/{channel}")]])
    if photo:
        await m.reply_photo(photo, caption=text, reply_markup=key)
    else:
        await m.reply(text, reply_markup=key)


@Client.on_message(filters.regex("^شازام .+") & filters.group)
async def shazam_lyrics(c: Client, m: Message):
    if not SHAZAM_OK:
        return
    if r.get(f"{m.chat.id}:disableShazam:{DEV_ID}"):
        return
    query = m.text.split(None, 1)[1]
    out   = await shazam.search_track(query=query, limit=1)
    if not out:
        return await m.reply("فشل العثور")
    try:
        key     = int(out["tracks"]["hits"][0]["key"])
        title   = out["tracks"]["hits"][0]["heading"]["title"][:35]
        author  = out["tracks"]["hits"][0]["heading"]["subtitle"]
        url     = out["tracks"]["hits"][0]["url"]
        about   = await shazam.track_about(track_id=key)
        texts   = about["sections"][1]["text"]
        lyrics  = "\n".join(texts)
        await m.reply(
            lyrics[:4096],
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton(f"{title} - {author}", url=url)]]
            ),
        )
    except Exception:
        await m.reply("فشل العثور")
