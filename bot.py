import asyncio
import json
import logging
import os
import shlex
import shutil
import sys
import traceback
import urllib
import urllib.parse
import urllib.request
from textwrap import dedent

import aiofiles
import aiofiles.os
import aiohttp
import all_web_dl as awdl
import urllib3
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorCollection
from pyrogram import Client, filters, idle
from pyrogram.enums.parse_mode import ParseMode
from pyrogram.types import ChatPrivileges, Message

import realurls
from aio_get_video_info import get_video_attributes, get_video_thumb, to_mkv
from splitter import splitVideoSize

load_dotenv()

API_ID = os.environ.get("API_ID")
API_HASH = os.environ.get("API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CLIENT_BOT = os.environ.get("CLIENT_BOT")
DB_URL = os.environ.get("DB_URL")
DEBUG = os.environ.get("DEBUG", True) != "false"
DUMP_CHANNEL = int(os.environ.get("DUMP_CHANNEL"))
INTERACTION_CHANNEL = int(os.environ.get("INTERACTION_CHANNEL"))
DL_NUM = int(os.environ.get("DL_NUM"))
thumb = os.environ.get("THUMB")

if thumb.startswith("http://") or thumb.startswith("https://"):
    cmd = f"wget '{thumb}' -O 'thumb.jpg'"
    os.system(cmd)
    thumb = "thumb.jpg"


bot = Client(
    "server", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN, sleep_threshold=120
)

file_handler = logging.FileHandler(filename="bot.log", mode="w")
stdout_handler = logging.StreamHandler(sys.stdout)
handlers = [file_handler, stdout_handler]
logging.basicConfig(
    format="%(name)s - %(levelname)s - %(message)s\n",
    level=logging.WARNING,
    handlers=handlers,
)
logger = logging.getLogger(__name__)


async def send_video(bot: Client, channel, path, caption):
    global thumb

    # reply = await bot.send_message(CHANNEL, "Uploading Video")

    try:
        if not thumb:
            thumb_to_send = await get_video_thumb(path)
        else:
            thumb_to_send = thumb
    except:
        # logger.exception("Error generating thumbnail")
        thumb_to_send = "thumb.jpg"

    try:
        duration, width, height = await get_video_attributes(path)
        # start_time = time.time()

        msg = await bot.send_video(
            channel,
            video=path,
            caption=caption,
            duration=duration,
            width=width,
            height=height,
            thumb=thumb_to_send,
            file_name=os.path.basename(path),
            supports_streaming=True,
            # progress=progress_bar,
            # progress_args=(reply,start_time),
        )
        # await reply.delete()
    except:
        # logger.exception("Error fetching attributes")
        # print(path)
        # start_time = time.time()
        if path.endswith((".mp4", ".mkv", ".avi", ".mov")):
            msg = await bot.send_video(
                channel,
                video=path,
                caption=caption,
                thumb=thumb_to_send,
                file_name=os.path.basename(path),
                supports_streaming=True,
                # progress=progress_bar,
                # progress_args=(reply,start_time),
            )
        else:
            msg = await bot.send_document(
                channel,
                document=path,
                caption=caption,
                thumb=thumb_to_send,
                file_name=os.path.basename(path),
            )
        # await reply.delete()
    return msg, path


async def get_msg_from_db(url, vid_format):
    client = AsyncIOMotorClient(DB_URL)
    db_name = "downloaded"
    if DEBUG:
        db_name += "_test"
    db = client[db_name]
    collection = db["videos"]
    url, vid_format = realurls.real_url(url, vid_format)
    video = await collection.find_one({"url": url, "vid_format": vid_format})
    if not video:
        return
    return video["msg"]


async def add_msg_to_db(url, vid_format, msg_id):
    client = AsyncIOMotorClient(DB_URL)
    db_name = "downloaded"
    if DEBUG:
        db_name += "_test"
    db = client[db_name]
    collection = db["videos"]
    url, vid_format = realurls.real_url(url, vid_format)
    result = await collection.insert_one(
        {"url": url, "vid_format": vid_format, "msg": [DUMP_CHANNEL, msg_id]}
    )
    return result.acknowledged


async def download_upload_video(bot: Client, channel, video, name):
    vid_id, url, vid_format, title, topic, allow_drm, keys = video
    prev_msg = await get_msg_from_db(url, vid_format)
    # print(prev_msg)
    # prev_msg_id = None
    if prev_msg:
        prev_chat, prev_msg_id = prev_msg
        if isinstance(prev_msg_id, list):
            msg_id = []
            for part, prev_part_msg_id in enumerate(prev_msg_id, 1):
                while True:
                    caption_text = f"""
                    Part: {part}
                    Vid_id: {vid_id}
                    Title: {title}
                    Topic: {topic}
                    Name: {name}
                    """
                    try:
                        dl_msg = await bot.copy_message(
                            channel,
                            prev_chat,
                            prev_part_msg_id,
                            caption=dedent(caption_text),
                        )
                    except Exception as error:
                        logging.exception(
                            ("In copying", error, url, vid_format, vid_id, title, prev_part_msg_id, part)
                        )
                        continue
                    if dl_msg:
                        try:
                            part_msg_id = dl_msg.id
                        except Exception as error:
                            logging.exception(
                                (
                                    "In copying: msg_id",
                                    error,
                                    url,
                                    vid_format,
                                    vid_id,
                                    title,
                                    prev_part_msg_id,
                                    part,
                                )
                            )
                            continue
                        msg_id.append(part_msg_id)
                        break
        else:
            while True:
                caption_text = f"""
                Vid_id: {vid_id}
                Title: {title}
                Topic: {topic}
                Name: {name}
                """
                try:
                    dl_msg = await bot.copy_message(
                        channel,
                        prev_chat,
                        prev_msg_id,
                        caption=dedent(caption_text),
                    )
                except Exception as error:
                    logging.exception(
                        ("In copying", error, url, vid_format, vid_id, title, prev_msg_id)
                    )
                    continue
                if dl_msg:
                    try:
                        msg_id = dl_msg.id
                    except Exception as error:
                        logging.exception(
                            (
                                "In copying: msg_id",
                                error,
                                url,
                                vid_format,
                                vid_id,
                                title,
                                prev_msg_id,
                            )
                        )
                        continue
                    break
        return vid_id, (channel, msg_id), True
    success = False
    filename = None
    for i in range(5):
        try:
            filename, title_ = await awdl.download_url(
                url,
                vid_format,
                title,
                dl_path=f"./downloads/{vid_id}",
                allow_drm=allow_drm,
                keys=keys,
            )
        except Exception as error:
            logger.exception(("In downloading", error, url, vid_id, title))
            continue
        if filename and os.path.exists(filename) and os.stat(filename).st_size:
            filename = await to_mkv(filename)
            file_size = os.stat(filename).st_size
            if file_size > 2_000_000_000:
                files = await splitVideoSize(filename)
                msg_id = []
                for part, file in enumerate(files, 1):
                    while True:
                        caption_text = f"""
                        Part: {part}
                        Vid_id: {vid_id}
                        Title: {title}
                        Topic: {topic}
                        Name: {name}
                        """
                        try:
                            dl_msg, file = await send_video(
                                bot, channel, file, dedent(caption_text)
                            )
                        except Exception as error:
                            logger.exception(
                                ("In Uploading", error, url, vid_id, title, part)
                            )
                            continue
                        if dl_msg:
                            try:
                                part_msg_id = dl_msg.id
                            except Exception as error:
                                logging.exception(
                                    (
                                        "In uploading: msg_id",
                                        error,
                                        url,
                                        vid_id,
                                        title,
                                        part,
                                    )
                                )
                                continue
                            msg_id.append(part_msg_id)
                            break
                    if os.path.exists(file):
                        await aiofiles.os.remove(file)
                if os.path.exists(filename):
                    await aiofiles.os.remove(filename)
                success = True
                break
            else:
                while True:
                    caption_text = f"""
                    Vid_id: {vid_id}
                    Title: {title}
                    Topic: {topic}
                    Name: {name}
                    """
                    try:
                        dl_msg, filename = await send_video(
                            bot, channel, filename, dedent(caption_text)
                        )
                    except Exception as error:
                        logger.exception(("In Uploading", error, url, vid_id, title))
                        continue
                    if dl_msg:
                        try:
                            msg_id = dl_msg.id
                        except Exception as error:
                            logging.exception(
                                ("In uploading: msg_id", error, url, vid_id, title)
                            )
                            continue
                        break
                if os.path.exists(filename):
                    await aiofiles.os.remove(filename)
                success = True
                break
        elif not filename:
            logger.error(("No filename", url, vid_id, title))
        elif not os.path.exists(filename):
            filename = None
            logger.error(("File don't exists", url, vid_id, title))
        elif not os.stat(filename).st_size:
            filename = None
            logger.error(("File size 0", url, vid_id, title))
    if not filename:
        logger.error(("Not Downloaded: ", url, vid_id, title))
        try:
            parts = urllib.parse.urlparse(url)
            queries = urllib.parse.parse_qsl(parts.query)
            uq = urllib.parse.urlencode(queries)
            up = urllib.parse.quote(parts.path)
            url_ = parts._replace(query=uq, path=up).geturl()
        except:
            url_ = url
        # try:
        #     first = url.split("/")[:-1]
        #     last = url.split("/")[-1]
        #     last_encoded = urllib.parse.quote(last)
        #     url = "/".join(first) + "/" + last_encoded
        # except:
        #     pass
        msg_text = f"""
        Error:
        \n
        Vid_id: {vid_id}
        Url: {url_}
        Title: {title}
        Topic: {topic}
        Name: {name}
        """
        while True:
            try:
                dl_msg = await bot.send_message(channel, dedent(msg_text))
            except Exception as error:
                logger.exception(("In sending error msg", error, url, vid_id, title))
                continue
            if dl_msg:
                try:
                    msg_id = dl_msg.id
                except Exception as error:
                    logging.exception(
                        ("In sending error msg: msg_id", error, url, vid_id, title)
                    )
                    continue
                break
    if success:
        await add_msg_to_db(url, vid_format, msg_id)
    return vid_id, (DUMP_CHANNEL, msg_id), success


async def download_upload_video_sem(sem, bot: Client, channel, video, name):
    async with sem:
        return await download_upload_video(bot, channel, video, name)


async def download_upload_videos(bot: Client, channel, videos, name):
    sem = asyncio.Semaphore(DL_NUM)
    dl_up_tasks = [
        download_upload_video_sem(sem, bot, channel, video, name) for video in videos
    ]
    downloaded_videos = await asyncio.gather(*dl_up_tasks)
    return downloaded_videos


@bot.on_message(filters.document & filters.caption & filters.chat(INTERACTION_CHANNEL))
async def download(bot: Client, message: Message):
    global bot_username
    caption = message.caption
    try:
        bot_cmd, bot_index, download_id, retry_num = caption.split()
    except:
        return
    if bot_cmd.lower() != f"/download@{bot_username}".lower():
        return
    json_file = await message.download()
    async with aiofiles.open(json_file, "r", encoding="utf-8") as f:
        json_text = await f.read()

    message_dict = json.loads(json_text)
    chat = message_dict["chat"]
    videos = message_dict["videos"]
    name = message_dict["name"]
    downloaded_videos = await download_upload_videos(bot, DUMP_CHANNEL, videos, name)
    done_dict = {"chat": chat, "videos": sorted(downloaded_videos)}
    done_json_file = f"{os.path.dirname(json_file)}/Done_{os.path.basename(json_file)}"
    # print(done_json_file)
    async with aiofiles.open(done_json_file, "w", encoding="utf-8") as f:
        await f.write(json.dumps(done_dict, indent=4))
    while True:
        dl_json_msg = await message.reply_document(
            done_json_file,
            caption=f"/copy{CLIENT_BOT} {bot_index} @{bot_username} {download_id} {retry_num}".lower(),
        )
        if dl_json_msg:
            break
    try:
        await aiofiles.os.remove(json_file)
    except:
        pass
    try:
        await aiofiles.os.remove(done_json_file)
    except:
        pass


@bot.on_message(filters.command("start"))
async def start(bot: Client, message: Message):
    await message.reply("DL Server bot running")


if __name__ == "__main__":
    global bot_username
    bot.start()
    _bot = bot.get_me()
    bot_username = _bot.username
    start_msg = f"DL Server bot: @{bot_username} started"
    logger.warning(start_msg)
    bot.send_message(INTERACTION_CHANNEL, start_msg)
    bot.set_parse_mode(ParseMode.DISABLED)
    idle()
    bot.stop()
