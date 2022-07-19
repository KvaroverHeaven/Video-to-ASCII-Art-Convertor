# -*- coding: utf-8 -*-
#
# Copyright (C) 2021, 2022, Perseus Sokolov. All rights reserved.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import platform
import subprocess
import sys
from glob import glob
from pathlib import Path

import av
import imgkit
from PIL import Image
from pymediainfo import MediaInfo

jpgPath = Path("JPG")
htmlPath = Path("HTML")
pngPath = Path("PNG")

if (platform.system() == "Linux"):
    options = {
        "quiet": "",
        "xvfb": ""
    }

elif (platform.system() == "Windows"):
    options = {
        "quiet": ""
    }


def clean():
    for filename in [*jpgPath.glob("*.jpg"), *htmlPath.glob("*.html"), *pngPath.glob("*.png")]:
        filename.unlink()


def videotoJpg(rawInput: str):
    print("Step 1: Video to JPG")
    if not (jpgPath.exists() and jpgPath.is_dir()):
        jpgPath.mkdir()
    container = av.open(Path(rawInput).open("r"))
    container.streams.video[0].thread_type = "AUTO"

    for frame in container.decode(video=0):
        frame.to_image().save(f"JPG/{frame.index:07}.jpg")

    container.close()


def imageToTxT():
    print("Step 2: JPG to TXT (HTML)")
    if not (htmlPath.exists() and htmlPath.is_dir()):
        htmlPath.mkdir()
    for image in sorted(glob("JPG/*.jpg")):
        subprocess.run(args=["img2txt", "-W 128", "-H 36", "-x 3", "-y 5", image, "-f", "html"],
                       stdout=open(f"HTML/{Path(image).stem}.html", "w"))


def htmltoPng():
    print("Step 3: TXT (HTML) to PNG")
    if not (pngPath.exists() and pngPath.is_dir()):
        pngPath.mkdir()

    for html in sorted(glob("HTML/*.html")):
        imgkit.from_file(html, f"PNG/{Path(html).stem}.png", options=options)


def pngtoVideo(rawInput: str):
    print("Step 4: PNG to Video")
    originVideo = av.open(Path(rawInput).open("r"))
    audio = originVideo.streams.audio[0]

    output = av.open("PNG/0000000.png")
    outputContext = output.streams.video[0].codec_context

    container = av.open(
        f"{Path(rawInput).stem}-ascii{Path(rawInput).suffix}", mode="w")

    stream = container.add_stream("h264", rate=24)
    audioStream = container.add_stream(template=audio)

    stream.width = outputContext.width
    stream.height = outputContext.height
    stream.pix_fmt = "yuv420p"
    stream.thread_type = "AUTO"
    stream.options = {
        "movflags": "faststart",
        "preset": "slower",
        "profile": "high",
        "level": "5.1"
    }
    audioStream.thread_type = "AUTO"

    imageList = [Image.open(fname)
                 for fname in sorted(glob("PNG/*.png"))]

    for packet in originVideo.demux(audio):
        if packet.dts is None:
            continue
        # We need to assign the packet to the new stream.
        packet.stream = audioStream
        container.mux(packet)

    for img in imageList:
        frame = av.VideoFrame.from_image(img)
        for packet in stream.encode(frame):
            container.mux(packet)

    # Flush stream
    packet = stream.encode(None)
    container.mux(packet)

    # Close the file
    container.close()
    output.close()
    originVideo.close()


def main():
    Sample = sys.argv[0]
    # fileInfo = MediaInfo.parse("Ayaya.mp4")
    fileInfo = MediaInfo.parse(Sample)

    for track in fileInfo.tracks:
        if track.track_type == "Video":
            # videotoJpg("Ayaya.mp4")
            videotoJpg(Sample)
            imageToTxT()
            htmltoPng()
            # pngtoVideo("Ayaya.mp4")
            pngtoVideo(Sample)
            clean()


if __name__ == "__main__":
    main()
