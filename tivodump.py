#!/bin/python3 -ttu

import argparse
import dataclasses
import math
import re
import sys
import time
from typing import List, TypedDict, cast
import xml.dom.minidom

import requests
import tqdm
import urllib3

urllib3.disable_warnings()

Recording = TypedDict(
    "Recording", {"size": int, "title": str, "url": str, "eptitle": str}, total=False
)


def main() -> int:
    args = parse_args()
    print(args)

    getTivoList(ip_address=args.ip_address, media_access_key=args.media_access_key)

    return 0


def convert_size(size_bytes: int) -> str:
    if size_bytes == 0:
        return "0B"
    size_name = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return "%s %s" % (s, size_name[i])


def getTivoList(*, ip_address: str, media_access_key: str) -> None:
    session = requests.session()
    session.verify = False
    session.auth = requests.auth.HTTPDigestAuth("tivo", media_access_key)
    tivo_url = f"https://{ip_address}/TiVoConnect"
    params = {
        "Command": "QueryContainer",
        "Container": "/NowPlaying",
        "Recurse": "Yes",
    }

    offset = 0
    recordings: List[Recording] = []
    params["AnchorOffset"] = str(offset)
    response = session.post(tivo_url, params=params)
    dom = cast(xml.dom.minidom.Document, xml.dom.minidom.parseString(response.text))
    xmlData = cast(xml.dom.minidom.Element, dom.documentElement)
    totalXml = xmlData.getElementsByTagName("TotalItems")[0]
    total = int(totalXml.childNodes[0].data)

    readXml(xmlData, recordings)

    if total > 16:
        offset += 16
        limit = total
        if not total % 16:
            limit = total - 16
        while offset <= limit:
            params["AnchorOffset"] = str(offset)
            response = session.post(tivo_url, params=params)
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
        downloadFile(
            session=session,
            url=recordings[i]["url"],
            filename=filename,
            size=recordings[i]["size"],
        )
        print("download complete.")
        i += 1
        time.sleep(10)


def readXml(xmlData: xml.dom.minidom.Element, recordings: List[Recording]) -> None:
    items = xmlData.getElementsByTagName("Item")
    for item in items:
        details = item.getElementsByTagName("Details")[0]
        size = item.getElementsByTagName("SourceSize")[0]
        links = item.getElementsByTagName("Links")[0]
        title = details.getElementsByTagName("Title")[0]
        content = links.getElementsByTagName("Content")[0]
        url = content.getElementsByTagName("Url")[0]

        eptitle = details.getElementsByTagName("EpisodeTitle")

        recordingInfo: Recording = {
            "size": int(size.childNodes[0].data),
            "title": title.childNodes[0].data,
            "url": url.childNodes[0].data,
        }

        if eptitle:
            recordingInfo["eptitle"] = eptitle[0].childNodes[0].data

        recordings.append(recordingInfo)


def downloadFile(
    *, session: requests.Session, url: str, filename: str, size: int
) -> None:
    x = session.get(url, stream=True)
    t = tqdm.tqdm(total=size, unit="B", unit_scale=True, unit_divisor=1024)
    with open(filename, "wb") as f:
        for data in x.iter_content(32 * 1024):
            t.update(len(data))
            f.write(data)
    t.close()


@dataclasses.dataclass
class Arguments:
    ip_address: str
    media_access_key: str


def parse_args() -> Arguments:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "-i", "--ip-address", help="IP address of the TiVo", required=True
    )
    parser.add_argument(
        "-m", "--media-access-key", help="The TiVo's Media Access Key", required=True
    )
    args = parser.parse_args()
    return Arguments(**vars(args))


if "__main__" == __name__:
    sys.exit(main())
