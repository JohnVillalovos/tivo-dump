#!/bin/python3
import urllib3
import urllib3.request
import requests
from requests.auth import HTTPDigestAuth
import xml.dom.minidom
import math
import time
import re
from tqdm import tqdm

# toilet -F border -f big TiVo Dump!
# ┌────────────────────────────────────────────────────────┐
# │ _______ ___      __     _____                        _ │
# │|__   __(_) \    / /    |  __ \                      | |│
# │   | |   _ \ \  / /__   | |  | |_   _ _ __ ___  _ __ | |│
# │   | |  | | \ \/ / _ \  | |  | | | | | '_ ` _ \| '_ \| |│
# │   | |  | |  \  / (_) | | |__| | |_| | | | | | | |_) |_|│
# │   |_|  |_|   \/ \___/  |_____/ \__,_|_| |_| |_| .__/(_)│
# │                                               | |      │
# │                                               |_|      │
# └────────────────────────────────────────────────────────┘

urllib3.disable_warnings()

user = "tivo"
password = "your tivo media access key"
tivo_ip = "your tivo ip address"
tivo_url = "/TiVoConnect?Command=QueryContainer&Container=%2FNowPlaying&Recurse=Yes&AnchorOffset="

session = requests.session()
session.verify = False
session.auth = HTTPDigestAuth(user, password)


def convert_size(size_bytes):
    if size_bytes == 0:
        return "0B"
    size_name = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return "%s %s" % (s, size_name[i])


def getTivoList():
    offset = 0
    recordings = []
    response = session.post("https://" + tivo_ip + tivo_url + str(offset))
    dom = xml.dom.minidom.parseString(response.text)
    xmlData = dom.documentElement
    totalXml = xmlData.getElementsByTagName("TotalItems")[0]
    total = int(totalXml.childNodes[0].data)

    readXml(xmlData, recordings)

    if total > 16:
        offset += 16
        limit = total
        if not total % 16:
            limit = total - 16
        while offset <= limit:
            response = session.post("https://" + tivo_ip + tivo_url + str(offset))
            dom = xml.dom.minidom.parseString(response.text)
            xmlData = dom.documentElement
            readXml(xmlData, recordings)
            offset += 16

    totalsize = 0
    recordings.sort(key=lambda x: x["title"])
    for item in recordings:
        totalsize += item["size"]
        # if 'eptitle' in item.keys():
        # 	print(convert_size(item['size']), " \t ", item['title'], "-", re.sub(r'(?u)[^-\s\w.]', '', item['eptitle']))
        # else:
        # 	print(convert_size(item['size']), " \t ", item['title'])
    print("Total Recordings:", len(recordings))
    print("Total Size", convert_size(totalsize))
    i = 51
    while i < len(recordings):
        numstr = str(i).zfill(4)
        print("#" + numstr)
        filename = ""
        if "eptitle" in recordings[i].keys():
            filename = re.sub(
                r"(?u)[^-\s\w.]",
                "",
                (
                    recordings[i]["title"]
                    + " - "
                    + recordings[i]["eptitle"]
                    + " - "
                    + numstr
                    + ".TiVo"
                ),
            )
            print(convert_size(recordings[i]["size"]), " \t ", filename)
        else:
            filename = re.sub(
                r"(?u)[^-\s\w.]",
                "",
                (recordings[i]["title"] + " - " + numstr + ".TiVo"),
            )
            print(convert_size(recordings[i]["size"]), " \t ", filename)
        downloadFile(recordings[i]["url"], filename, recordings[i]["size"])
        print("download complete.")
        i += 1
        time.sleep(10)


def readXml(xmlData, recordings):
    items = xmlData.getElementsByTagName("Item")
    for item in items:
        details = item.getElementsByTagName("Details")[0]
        size = item.getElementsByTagName("SourceSize")[0]
        links = item.getElementsByTagName("Links")[0]
        title = details.getElementsByTagName("Title")[0]
        content = links.getElementsByTagName("Content")[0]
        url = content.getElementsByTagName("Url")[0]

        eptitle = details.getElementsByTagName("EpisodeTitle")

        recordingInfo = {
            "size": int(size.childNodes[0].data),
            "title": title.childNodes[0].data,
            "url": url.childNodes[0].data,
        }

        if eptitle:
            recordingInfo["eptitle"] = eptitle[0].childNodes[0].data

        recordings.append(recordingInfo)


def downloadFile(url, filename, size):
    x = session.get(url, stream=True)
    t = tqdm(total=size, unit="B", unit_scale=True, unit_divisor=1024)
    with open(filename, "wb") as f:
        for data in x.iter_content(32 * 1024):
            t.update(len(data))
            f.write(data)
    t.close()


getTivoList()
