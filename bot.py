import asyncio
import json
import logging
import os
import shlex
import sys
from textwrap import dedent
from aio_get_video_info import get_video_attributes, get_rcode_out_err
import aiofiles
from dotenv import load_dotenv
from pyrogram import Client, filters
from pyrogram.types import Message
import all_web_dl as awdl

load_dotenv()

API_ID = os.environ.get("API_ID")
API_HASH = os.environ.get("API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN")
UTLRA_USER = os.environ.get("UTLRA_USER")
CHANNEL = os.environ.get("CHANNEL")
thumb = os.environ.get("THUMB")

if thumb.startswith("http://") or thumb.startswith("https://"):
    cmd = f"wget '{thumb}' -O 'thumb.jpg'"
    thumb = "thumb.jpg"


bot = Client("server", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

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
        cmd = f"mv '{path}' '{path}.mkv'"
        path = f"{path}.mkv"
        cmd = shlex.split(cmd)
        await get_rcode_out_err(cmd)
        return await bot.send_video(
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
        logger.exception("Error fetching attributes")
        print(path)
        # start_time = time.time()
        return await bot.send_video(
            channel,
            video=path,
            caption=caption,
            thumb=thumb,
            file_name=os.path.basename(path),
            supports_streaming=True,
            # progress=progress_bar,
            # progress_args=(reply,start_time),
        )
        # await reply.delete()



async def download_upload_video(bot: Client, channel, video):
    vid_id, url, vid_format, title, topic, allow_drm = video
    filename, title = await awdl.download_url(
        url, vid_format, title, "", allow_drm=allow_drm
    )
    if not filename:
        msg_text = f"""
        Error:
        \n
        Vid_id: {vid_id}
        Url: {url}
        Title: {title}
        Topic: {topic}
        """
        try:
            dl_msg = await bot.send_message(channel, dedent(msg_text))
        except:
            dl_msg = None
    else:
        caption_text = f"""
        Vid_id: {vid_id}
        Title: {title}
        Topic: {topic}
        """
        try:
            dl_msg = await send_video(bot, channel, filename, dedent(caption_text))
        except:
            dl_msg = None
    try:
        return vid_id, dl_msg.message_id
    except:
        print("Error sending message")
        return vid_id, None


async def download_upload_video_sem(sem, bot: Client, channel, video):
    async with sem:
        return await download_upload_video(bot, channel, video)


async def download_upload_videos(bot: Client, channel, videos):
    sem = asyncio.Semaphore(4)
    dl_up_tasks = [
        download_upload_video_sem(sem, bot, channel, video) for video in videos
    ]
    downloaded_videos = await asyncio.gather(*dl_up_tasks)
    return downloaded_videos


@bot.on_message(filters.document & filters.caption)
async def download(bot: Client, message: Message):
    caption = message.caption
    if caption != "/download":
        return
    json_file = await message.download()
    async with aiofiles.open(json_file, "r", encoding="utf-8") as f:
        json_text = await f.read()

    message_dict = json.loads(json_text)
    channel = message_dict["channel"]
    videos = message_dict["videos"]
    downloaded_videos = await download_upload_videos(bot, CHANNEL, videos)
    done_dict = {"channel": channel, "videos": sorted(downloaded_videos)}
    done_json_file = f"{os.path.dirname(json_file)}/Done_{os.path.basename(json_file)}"
    async with aiofiles.open(done_json_file, "w", encoding="utf-8") as f:
        await f.write(json.dumps(done_dict, indent=4))
    await message.reply_document(done_json_file, caption="/copy")


@bot.on_message(filters.command("start"))
async def start(bot: Client, message: Message):
    await message.reply("Server bot running")
    return


if __name__ == "__main__":

    bot.connect()
    _bot = bot.get_me()
    bot.send_message(CHANNEL, f"Server bot: @{_bot.username} started")
    bot.disconnect()

    bot.run()
