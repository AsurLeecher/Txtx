""" Get video attributes and thumbnail """

from __future__ import annotations
import asyncio
from asyncio.subprocess import PIPE
import os
import shlex
import tempfile
from subprocess import getstatusoutput


async def get_rcode_out_err(cmd: list[str]):
    """
    Run subprocess and get rcode, out and err
    """
    process = await asyncio.create_subprocess_exec(*cmd, stdout=PIPE, stderr=PIPE)
    out, err = [x.decode().strip() for x in await process.communicate()]
    rcode = process.returncode
    return rcode, out, err


async def get_video_attributes(file: str):
    """Returns video duration, width, height"""

    class FFprobeAttributesError(Exception):
        """Exception if ffmpeg fails to generate attributes"""

    cmd = (
        "ffprobe -v error -show_entries format=duration "
        + "-of default=noprint_wrappers=1:nokey=1 "
        + "-select_streams v:0 -show_entries stream=width,height "
        + f" -of default=nw=1:nk=1 {shlex.quote(file)}"
    )
    cmd = shlex.split(cmd)
    rcode, out, err = await get_rcode_out_err(cmd)
    if rcode != 0:
        raise FFprobeAttributesError(err)
    width, height, dur = out.split("\n")
    return (int(float(dur)), int(width), int(height))


async def get_video_thumb(file: str):
    """Returns path to video thumbnail"""

    class FFprobeThumbnailError(Exception):
        """Exception if ffmpeg fails to generate thumbnail"""

    thumb_file = tempfile.NamedTemporaryFile(suffix=".jpg").name
    duration, width, height = await get_video_attributes(file)
    dur = str(int(duration / 2))
    size = f"{width}x{height}"
    cmd = (
        f"ffmpeg -v error -ss {dur} -i {shlex.quote(file)}  -vframes 1 "
        + f"-s {size} {thumb_file}"
    )
    cmd = shlex.split(cmd)
    rcode, out, err = await get_rcode_out_err(cmd)
    if rcode != 0:
        raise FFprobeThumbnailError(err)
    if not os.path.exists(thumb_file):
        for i in range(1, 11, 100):
            cmd = f"ffmpeg -v error -ss {i*100} -i {shlex.quote(file)}  -vframes 1 -s {size} {thumb_file}"
            cmd = shlex.split(cmd)
            rcode, out, err = await get_rcode_out_err(cmd)
            if rcode != 0:
                raise FFprobeThumbnailError(err)
            if os.path.exists(thumb_file):
                return thumb_file
        raise FFprobeThumbnailError("Couldn't generate thumbnail.")
    return thumb_file
