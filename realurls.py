import urllib.parse
import vigenere
import os

KEY = os.environ.get("KEY")


get_without_queries = lambda url: urllib.parse.urljoin(
    url, urllib.parse.urlparse(url).path
)


def get_real_drive(url: str):
    parse_res = urllib.parse.urlparse(url)
    if "id=" in url:
        queries = urllib.parse.parse_qs(parse_res.query)
        video_id = queries["id"][0]
    elif "folders" in url:
        video_id = parse_res.path.split("/")[3]
    elif "file" in url:
        try:
            video_id = parse_res.path.split("/")[3]
        except Exception:
            return ""
    else:
        return url
    url = f"https://drive.google.com/open?id={video_id}"
    return url


def get_real_yt(url: str):
    parse_res = urllib.parse.urlparse(url)
    if "youtu.be" in parse_res.netloc:
        video_id = parse_res.path.strip("/")
    elif "youtube.com" in parse_res.netloc:
        queries = urllib.parse.parse_qs(parse_res.query)
        video_id = queries["v"][0]
    url = f"/youtube/{video_id}"
    url = get_without_queries(url)
    return url


def get_real_vimeo(url: str):
    parse_res = urllib.parse.urlparse(url)
    video_id = parse_res.path.split("/")[2].split(".")[0]
    url = f"/vimeo/{video_id}"
    return url


def get_real_jw(url: str):
    parse_res = urllib.parse.urlparse(url)
    video_id = parse_res.path.split("/")[2].split(".")[0]
    url = f"/jw/{video_id}"
    return url


def get_real_classplus(url):
    parse_res = urllib.parse.urlparse(url)
    video_id = parse_res.path.split("/")[2]
    if video_id.isnumeric():
        pass
    elif len(video_id) == 8:
        url = f"/jw/{video_id}"
    else:
        pass
    return url


def dec_str(link):
    try:
        dec_link = vigenere.decode(KEY, link)
    except Exception:
        url = link
        pass
    else:
        enc_link = vigenere.encode(KEY, dec_link)
        if enc_link == link:
            url = dec_link
        else:
            url = link
    return url


def get_real_player(url: str):
    parse_res = urllib.parse.urlparse(url)
    if parse_res.path.startswith(
        (
            "/jw",
            "/youtube",
            "/brightcove",
            "/stiq",
            "/vimeo",
            "/stiq_pdf",
            "/videos",
            "/encryptvdo",
            "/apdf",
        )
    ):
        _, service, video_id = parse_res.path.split("/")
        video_id = dec_str(video_id)
        url = f"/{service}/{video_id}"
        url = get_without_queries(url)
    elif parse_res.path.startswith(("/m3u8", "/mpd", "/video", "/audio", "/html")):
        queries = urllib.parse.parse_qs(parse_res.query)
        link = queries["url"][0]
        url = dec_str(link)
        if "videos.classplus" in url:
            url = get_real_classplus(url)
        elif any(
            x in url
            for x in [
                "manifest.prod.boltdns.net",
                "mediacloudfront.zee5.com",
                "601cae6cca4e7.streamlock.net",
            ]
        ):
            url = get_without_queries(url)
        else:
            pass
    elif parse_res.path.startswith(("/pdf")):
        queries = urllib.parse.parse_qs(parse_res.query)
        if "url=" in url:
            link = queries["url"][0]
            url = dec_str(link)
        elif "id=" in url:
            _id = queries["id"][0]
            _id = dec_str(_id)
            url = f"https://drive.google.com/open?id={_id}"
    elif parse_res.path.startswith(("/utk")):
        _, service, video_id = parse_res.path.split("/")
        video_id = dec_str(video_id)
        video_id = video_id.split("_")[0]
        url = f"/jw/{video_id}"
    elif parse_res.path.startswith(("/_utk")):
        _, service, video_id = parse_res.path.split("/")
        video_id = dec_str(video_id)
        url = f"/_utk/{video_id}"
    else:
        pass
    return url


def real_url(url: str, vid_format: str):
    try:
        parse_res = urllib.parse.urlparse(url)
        if any(
            x in parse_res.netloc
            for x in ["hippotv.me", "tech9light.tech", "solution.novano.me"]
        ):
            if parse_res.path.startswith(("/pdf", "/html")):
                vid_format = ""
            url = get_real_player(url)
            pass
        elif parse_res.scheme == "text":
            vid_format = ""
            pass
        elif "drive.google" in parse_res.netloc:
            vid_format = ""
            url = get_real_drive(url)
            pass
        elif any(x in parse_res.netloc for x in ["youtu.be", "youtube.com"]):
            url = get_real_yt(url)

        elif any(
            x in parse_res.netloc
            for x in [
                "manifest.prod.boltdns.net",
                "mediacloudfront.zee5.com",
                "601cae6cca4e7.streamlock.net",
            ]
        ):
            url = get_without_queries(url)
        elif "player.vimeo" in parse_res.netloc:
            url = get_real_vimeo(url)
        elif "videos.classplus" in parse_res.netloc:
            url = get_real_classplus(url)
        elif "jwplayer" in parse_res.netloc:
            url = get_real_jw(url)
        elif url.endswith(
            (
                ".pdf",
                ".PDF",
                ".png",
                ".php",
                ".ws",
                ".pdf",
                ".doc",
                ".docx",
                ".ppt",
                ".pptx",
                ".zip",
                ".vtt",
            )
        ):
            vid_format = ""
            pass
        elif parse_res.path.endswith((".mp4", "mkv", "m4v")):
            pass
        elif parse_res.path.endswith((".m3u8")):
            pass
        elif parse_res.path.endswith((".mpd")):
            pass
        # elif url.endswith((".m4v")):
        #     if any(x in url for x in []):
        #         pass
        #     else:
        #         print(url)
        #         sleep(0.1)
        #     pass
        else:
            pass
    except Exception:
        pass
    return url, vid_format
