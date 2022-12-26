import argparse
import asyncio
import json
import os
import time


async def getDuration(file):
    # print(file)
    cmd2 = [
        "ffprobe",
        "-print_format",
        "json",
        "-show_format",
        "-show_streams",
        "-select_streams",
        "v",
        file,
    ]

    process = await asyncio.create_subprocess_exec(
        *cmd2,
        # stdout must a pipe to be accessible as process.stdout
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    # Wait for the subprocess to finish
    stdout, stderr = await process.communicate()
    st1 = stderr.decode().strip()
    out1 = stdout.decode().strip()
    # print(out1, st1)
    data = json.loads(str(out1))
    width, height, duration = (
        int(data["streams"][0]["width"]),
        int(data["streams"][0]["height"]),
        int(float(data["format"]["duration"])),
    )
    # print(duration)
    return duration


async def splitVideoSize(input_file, fsize=1_975_000):
    rSize = fsize * 1000
    fSize = os.path.getsize(input_file)
    # print(fSize)
    rDurationInit = 0
    fDuration = await getDuration(input_file)
    i = 0
    files = []
    for x in range(0, fSize, rSize):
        output_file = f"{input_file}_{i}.mkv"
        # print(output_file)
        if os.path.exists(output_file):
            os.remove(output_file)

        # print(rSize)
        cmd = [
            "ffmpeg",
            "-ss",
            str(rDurationInit),
            "-i",
            input_file,
            "-fs",
            str(rSize),
            # "2000000",
            "-map",
            "0",
            "-c",
            "copy",
            output_file,
        ]
        process = await asyncio.create_subprocess_exec(
            *cmd,
            # stdout must a pipe to be accessible as process.stdout
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        # Wait for the subprocess to finish
        stdout, stderr = await process.communicate()
        rDurationInit += await getDuration(output_file)
        i += 1
        files.append(output_file)
    return files


async def real_main():
    """
    Run from command line
    """
    parser = argparse.ArgumentParser(description="Split videos", allow_abbrev=True)
    parser.add_argument("path", type=str, help="Path of video")
    parser.add_argument(
        "size",
        type=int,
        nargs="?",
        help="Max size for split videos in KB",
        default=1_975_000,
    )
    args = parser.parse_args()
    # print(await getDuration(args.path))
    files = await splitVideoSize(args.path, args.size)
    for file in files:
        print(file, os.path.getsize(file) // 1000)


def main():
    loop = asyncio.get_event_loop()
    loop.run_until_complete(real_main())
    loop.close()


if __name__ == "__main__":
    main()
