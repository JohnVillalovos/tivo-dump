#!/bin/python3 -ttu

import argparse
import dataclasses
import re
import sys
import time
from typing import Dict, List, Optional
import xml.etree.ElementTree

import requests
import tqdm  # type: ignore[import]
import urllib3

urllib3.disable_warnings()  # type: ignore[no-untyped-call]


TIVO_NAMESPACE = "http://www.tivo.com/developer/calypso-protocol-1.6/"
NAMESPACES = {"": TIVO_NAMESPACE}


def main() -> int:
    args = parse_args()

    # So it doesn't put 'ns0:' in front of each XML element
    xml.etree.ElementTree.register_namespace("", TIVO_NAMESPACE)

    get_tivo_list(
        ip_address=args.ip_address,
        media_access_key=args.media_access_key,
        download=args.download,
    )

    return 0


def convert_size(size_bytes: int) -> str:
    return tqdm.tqdm.format_sizeof(size_bytes, suffix="B", divisor=1024)


@dataclasses.dataclass(kw_only=True)
class Recording:
    size: int
    title: str
    url: str
    eptitle: Optional[str] = None

    def filename(self, *, index: int) -> str:
        numstr = f"{index:04d}"
        if self.eptitle is not None:
            filename = f"{self.title} - {self.eptitle} - {numstr}.TiVo"
        else:
            filename = f"{self.title} - {numstr}.TiVo"
        filename = re.sub(r"[^-\s\w.]", "", filename)
        return filename


def get_tivo_list(
    *, ip_address: str, media_access_key: str, download: bool = False
) -> None:
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
    root = xml.etree.ElementTree.fromstring(response.text)

    total_recordings = int(find_return_text(element=root, match="Details/TotalItems"))

    read_xml(xml_data=root, recordings=recordings)

    if total_recordings > 16:
        offset += 16
        limit = total_recordings
        if not total_recordings % 16:
            limit = total_recordings - 16
        while offset <= limit:
            params["AnchorOffset"] = str(offset)
            response = session.post(tivo_url, params=params)
            root = xml.etree.ElementTree.fromstring(response.text)
            read_xml(xml_data=root, recordings=recordings)
            offset += 16

    assert len(recordings) == total_recordings

    totalsize = 0
    recordings.sort(key=lambda x: x.title)
    for item in recordings:
        totalsize += item.size
    print("Total Recordings:", len(recordings))
    print("Total Size", convert_size(totalsize))
    for index, recording in enumerate(recordings, start=1):
        numstr = f"{index:04d}"
        print(f"#{numstr}")
        filename = recording.filename(index=index)
        print(convert_size(recording.size), " \t ", filename)
        if download:
            download_file(
                session=session,
                url=recording.url,
                filename=filename,
                size=recording.size,
            )
            print("download complete.")
            time.sleep(10)
        else:
            print(f"Not downloading {filename!r}")
        print()
    if not download:
        print("Did not download files as the `--download` argument wasn't specified.")


def find_return_text(
    element: xml.etree.ElementTree.Element,
    match: str,
    namespaces: Optional[Dict[str, str]] = None,
) -> str:
    if namespaces is None:
        namespaces = NAMESPACES
    found_element = element.find(match, namespaces=namespaces)
    assert found_element is not None
    found_text = found_element.text
    assert found_text is not None
    return found_text


def read_xml(
    *, xml_data: xml.etree.ElementTree.Element, recordings: List[Recording]
) -> None:
    items = xml_data.findall("Item", namespaces=NAMESPACES)
    for item in items:
        size = int(find_return_text(element=item, match="Details/SourceSize"))
        title = find_return_text(element=item, match="Details/Title")
        url = find_return_text(element=item, match="Links/Content/Url")

        eptitle_element = item.find("Details/EpisodeTitle", namespaces=NAMESPACES)
        eptitle = None
        if eptitle_element is not None:
            eptitle = eptitle_element.text

        recording_info = Recording(size=size, title=title, url=url, eptitle=eptitle)
        print("Found:", title, f" - {eptitle}" if eptitle is not None else "")
        recordings.append(recording_info)


def download_file(
    *, session: requests.Session, url: str, filename: str, size: int
) -> None:
    response = session.get(url, stream=True)
    t = tqdm.tqdm(total=size, unit="B", unit_scale=True, unit_divisor=1024)
    with open(filename, "wb") as f:
        for data in response.iter_content(32 * 1024):
            t.update(len(data))
            f.write(data)
    t.close()


@dataclasses.dataclass
class Arguments:
    download: bool
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
    parser.add_argument(
        "-d", "--download", help="Download the TiVo files", action="store_true"
    )
    args = parser.parse_args()
    return Arguments(**vars(args))


if "__main__" == __name__:
    sys.exit(main())
