import asyncio
import json
import logging
import os
import shlex
import sys
import traceback
import urllib
import urllib.parse
import urllib.request
import urllib3
from textwrap import dedent
import shutil

if not shutil.which("mp4decrypt"):
    print("Install mp4decrypt first")
    exit()

from pyrogram.enums.parse_mode import ParseMode
from aio_get_video_info import get_video_attributes, get_rcode_out_err
import aiofiles
import aiofiles.os
from dotenv import load_dotenv
from pyrogram import Client, filters, idle
from pyrogram.types import Message, ChatPrivileges
import all_web_dl as awdl

load_dotenv()

API_ID = os.environ.get("API_ID")
API_HASH = os.environ.get("API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CLIENT_BOT = os.environ.get("CLIENT_BOT")
DUMP_CHANNEL = int(os.environ.get("DUMP_CHANNEL"))
INTERACTION_CHANNEL = int(os.environ.get("INTERACTION_CHANNEL"))
DL_NUM = int(os.environ.get("DL_NUM"))
thumb = os.environ.get("THUMB")

if thumb.startswith("http://") or thumb.startswith("https://"):
    cmd = f"wget '{thumb}' -O 'thumb.jpg'"
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
        duration, width, height = await get_video_attributes(path)
        # start_time = time.time()

        if not path.endswith(".mkv"):
            try:
                await aiofiles.os.rename(path, f"{path}.mkv")
            except:
                pass
            else:
                path = f"{path}.mkv"
        if os.path.exists(path):
            pass
        elif os.path.exists(path[:-4]):
            path = path[:-4]

        msg = await bot.send_video(
            channel,
            video=path,
            caption=caption,
            duration=duration,
            width=width,
            height=height,
            thumb=thumb,
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
            if not path.endswith(".mkv"):
                try:
                    await aiofiles.os.rename(path, f"{path}.mkv")
                except:
                    pass
                else:
                    path = f"{path}.mkv"
            if os.path.exists(path):
                pass
            elif os.path.exists(path[:-4]):
                path = path[:-4]
            msg = await bot.send_video(
                channel,
                video=path,
                caption=caption,
                thumb=thumb,
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
                thumb=thumb,
                file_name=os.path.basename(path),
            )
        # await reply.delete()
    return msg, path


async def download_upload_video(bot: Client, channel, video, name):
    vid_id, url, vid_format, title, topic, allow_drm = video
    success = False
    filename = None
    for i in range(5):
        try:
            filename, title_ = await awdl.download_url(
                url, vid_format, title, "", allow_drm=allow_drm
            )
        except Exception as error:
            logger.exception(("In downloading", error, url, vid_id, title))
            continue
        if filename:
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
                if os.path.exists(filename):
                    await aiofiles.os.remove(filename)
                success = True
                break
        logger.error(("No filename", url, vid_id, title))
    if not filename:
        logger.error(("Not Downloaded: ", url, vid_id, title))
        try:
            parts = urllib.parse.urlparse(url)
            queries = urllib.parse.parse_qsl(parts.query)
            uq = urllib.parse.urlencode(queries)
            up = urllib.parse.quote(parts.path)
            url = parts._replace(query=uq, path=up).geturl()
        except:
            pass
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
        Url: {url}
        Title: {title}
        Topic: {topic}
        Name: {name}
        """
        for i in range(5):
            try:
                dl_msg = await bot.send_message(channel, dedent(msg_text))
            except Exception as error:
                logger.exception(("In sending error msg", error, url, vid_id, title))
                continue
            if dl_msg:
                break
    try:
        return vid_id, dl_msg.id, success
    except Exception as error:
        logger.exception(("After return", error, url, vid_id, title))
        try:
            parts = urllib.parse.urlparse(url)
            queries = urllib.parse.parse_qsl(parts.query)
            uq = urllib.parse.urlencode(queries)
            up = urllib.parse.quote(parts.path)
            url = parts._replace(query=uq, path=up).geturl()
        except:
            pass
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
        Url: {url}
        Title: {title}
        Topic: {topic}
        Name: {name}
        """
        while True:
            try:
                dl_msg = await bot.send_message(channel, dedent(msg_text))
            except Exception as error:
                logger.exception(
                    ("After return: sending msg", error, url, vid_id, title)
                )
                continue
            if dl_msg:
                try:
                    msg_id = dl_msg.id
                except Exception as error:
                    logger.exception(
                        ("After return: msg_id", error, url, vid_id, title, dl_msg)
                    )
                    continue
                break
        return vid_id, dl_msg.id, success


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
        bot_cmd, bot_index = caption.split()
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
            caption=f"/copy{CLIENT_BOT} {bot_index} @{bot_username}".lower(),
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
