"""Render repository-derived MediaMTX relationships as PNG and SVG diagrams."""

from __future__ import annotations

import argparse
from html import escape
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


DOCS = Path(__file__).resolve().parents[1]
OUT = DOCS / "images"
INK = "#17324a"
MUTED = "#486079"
BLUE = "#1673ad"
GREEN = "#168069"
ORANGE = "#a96416"
PURPLE = "#7151a5"


class Canvas:
    def __init__(self, size: tuple[int, int], title: str, subtitle: str,
                 regular: Path, bold: Path) -> None:
        self.size, self.regular, self.bold = size, regular, bold
        self.image = Image.new("RGB", size, "white")
        self.draw = ImageDraw.Draw(self.image)
        self.svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{size[0]}" '
                    f'height="{size[1]}" viewBox="0 0 {size[0]} {size[1]}" '
                    'role="img">', f'<title>{escape(title)}</title>',
                    '<rect width="100%" height="100%" fill="white"/>']
        self.text((60, 38), title, 46, INK, bold=True)
        self.text((60, 103), subtitle, 26, MUTED)

    def font(self, size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
        return ImageFont.truetype(str(self.bold if bold else self.regular), size)

    def text(self, pos: tuple[int, int], value: str, size: int = 26,
             color: str = INK, bold: bool = False) -> None:
        font = self.font(size, bold)
        x, y = pos
        bounds = self.draw.textbbox(pos, value, font=font, anchor="lt")
        if bounds[2] > self.size[0] - 20 or bounds[3] > self.size[1] - 10:
            raise ValueError(f"Text exceeds canvas: {value}")
        self.draw.text(pos, value, font=font, fill=color, anchor="lt")
        weight = "700" if bold else "400"
        self.svg.append(f'<text x="{x}" y="{y}" font-family="Segoe UI,DejaVu Sans,sans-serif" '
                        f'font-size="{size}" font-weight="{weight}" fill="{color}" '
                        f'dominant-baseline="text-before-edge">{escape(value)}</text>')

    def panel(self, box: tuple[int, int, int, int], color: str = BLUE,
              fill: str = "#f5f9fc", width: int = 3) -> None:
        x, y, w, h = box
        self.draw.rounded_rectangle((x, y, x+w, y+h), radius=20,
                                    fill=fill, outline=color, width=width)
        self.svg.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="20" '
                        f'fill="{fill}" stroke="{color}" stroke-width="{width}"/>')

    def card(self, box: tuple[int, int, int, int], title: str,
             lines: list[str], color: str = BLUE, size: int = 26) -> None:
        x, y, w, h = box
        self.panel(box, color)
        self.text((x+24, y+20), title, 32, color, bold=True)
        for index, line in enumerate(lines):
            font = self.font(size)
            if self.draw.textlength(line, font=font) > w-48:
                raise ValueError(f"Text exceeds card width: {line}")
            text_y = y+70+index*36
            if text_y+size > y+h-10:
                raise ValueError(f"Text exceeds card height: {line}")
            self.text((x+24, text_y), line, size, MUTED)

    def arrow(self, points: list[tuple[int, int]], color: str = BLUE,
              dashed: bool = False) -> None:
        self.svg.append('<polyline points="' + " ".join(f"{x},{y}" for x,y in points) +
                        f'" fill="none" stroke="{color}" stroke-width="5" '
                        'stroke-linejoin="round"' +
                        (' stroke-dasharray="12 9"' if dashed else '') + '/>')
        for start, end in zip(points, points[1:]):
            length = math.dist(start, end)
            if dashed:
                for offset in range(0, math.ceil(length), 21):
                    a, b = offset/length, min(offset+12, length)/length
                    segment = [(start[0]+(end[0]-start[0])*t,
                                start[1]+(end[1]-start[1])*t) for t in (a,b)]
                    self.draw.line(segment, fill=color, width=5)
            else:
                self.draw.line((start,end), fill=color, width=5)
        tip, prev = points[-1], points[-2]
        angle = math.atan2(tip[1]-prev[1], tip[0]-prev[0])
        triangle = [tip] + [(tip[0]-20*math.cos(angle)+side*9*math.sin(angle),
                            tip[1]-20*math.sin(angle)-side*9*math.cos(angle))
                           for side in (-1,1)]
        self.draw.polygon(triangle, fill=color)
        self.svg.append('<polygon points="' + " ".join(f"{x:.1f},{y:.1f}" for x,y in triangle) +
                        f'" fill="{color}"/>')

    def label(self, pos: tuple[int,int], lines: list[str], color: str = MUTED) -> None:
        widths = [self.draw.textlength(line, font=self.font(24)) for line in lines]
        x,y = pos
        w,h = math.ceil(max(widths))+22, len(lines)*31+14
        self.draw.rectangle((x-11,y-7,x+w-11,y+h-7),fill="white")
        self.svg.append(f'<rect x="{x-11}" y="{y-7}" width="{w}" height="{h}" fill="white"/>')
        for index,line in enumerate(lines):
            self.text((x,y+index*31),line,24,color)

    def save(self, name: str) -> None:
        OUT.mkdir(parents=True,exist_ok=True)
        self.image.save(OUT / f"{name}.png",optimize=True)
        (OUT / f"{name}.svg").write_text("\n".join(self.svg+["</svg>"]),encoding="utf-8")
        print(f"Wrote docs/images/{name}.png and .svg")


def auth(regular: Path, bold: Path) -> None:
    c=Canvas((2100,1400),"MediaMTX | authInternalUsers",
             "Current repository policy: identity + action + source IP + path, independently on each node",regular,bold)
    identities=[
        (200,"icu-<squad>",["publish: registered member paths", "named squad: VIDEO_1 path regex"]),
        (380,"device-<generated-id>",["publish: one exact device path", "independent generated credential"]),
        (560,"atak-publisher",["publish: live/* + test", "retained legacy shared credential"]),
        (740,"atak-viewer",["read: live/* + test", "ATAK, downstream nodes, thumbnails"]),
        (920,"tak-console",["api: management operations", "no publish or read permission"]),
    ]
    for y,title,lines in identities:
        c.card((60,y,580,145),title,lines)
    c.card((755,340,570,590),"mediamtx authorization",[
        "authMethod: internal",
        "1. Validate username / password",
        "2. Match the requested action",
        "3. Check ips (currently [])",
        "4. Match exact or regex path",
        "",
        "Disabled dynamic users are omitted.",
        "Active sessions are kicked separately.",
        "Host firewall is a separate boundary.",
    ],GREEN,24)
    for y,target in ((200,420),(380,490),(560,600),(740,790),(920,870)):
        c.arrow([(640,y+72),(695,y+72),(695,target),(755,target)])
    c.card((1460,235,580,195),"publish",[
        "Create a stream on an allowed path.",
        "Squad regex or exact device grant.",
        "Legacy shared publisher stays broad.",
    ],GREEN,24)
    c.card((1460,600,580,195),"read",[
        "Read a published stream.",
        "atak-viewer covers live/* + test.",
        "No per-team media read isolation.",
    ],BLUE,24)
    c.card((1460,960,580,160),"api",[
        "Internal management endpoint :9997.",
        "Grant does not authorize video reads.",
    ],ORANGE,24)
    c.arrow([(1325,420),(1390,420),(1390,332),(1460,332)],GREEN)
    c.arrow([(1325,697),(1460,697)],BLUE)
    c.arrow([(1325,870),(1390,870),(1390,1040),(1460,1040)],ORANGE)
    c.text((60,1127),"DOWNSTREAM NODES LOAD THEIR OWN AUTHORIZATION LISTS",26,INK,bold=True)
    c.card((60,1190,965,155),"media-viewer / viewer-public.yml",[
        "any: read live/* (anonymous) | tak-console: api",
        "Upstream pull uses atak-viewer; LAN gateway supplies the public switch.",
    ],PURPLE,24)
    c.card((1075,1190,965,155),"media-preview / viewer-preview.yml",[
        "admin: read live/* | API disabled",
        "Upstream pull uses atak-viewer; share-admin relays admin credentials.",
    ],PURPLE,24)
    c.text((60,1362),"Source: mediamtx.yml.template / provision_mediamtx.py / media_registry.py",23,MUTED)
    c.save("mediamtx-auth-internal-users")


def topology(regular: Path, bold: Path) -> None:
    c=Canvas((2460,1540),"Docker Compose | three MediaMTX nodes",
             "One ingress + two independent on-demand WebRTC readers; separate configs, sessions and auth lists",regular,bold)
    c.panel((570,170,1280,1235),"#b8cbd9","#f7fafc",2)
    c.text((600,190),"Media services on tak-edge | service-name DNS",27,MUTED,bold=True)
    c.card((60,250,450,170),"ICU / drone / encoder",[
        "RTSPS :8322 or RTSP :8554",
        "Publisher identity + path grant",
    ],GREEN,24)
    c.card((740,250,940,195),"mediamtx | ingress and direct reading",[
        "mediamtx.yml | RTSP :8554 / RTSPS :8322",
        "Dynamic publishers + atak-viewer + tak-console API :9997",
        "RTMP / HLS / WebRTC / SRT / MoQ disabled",
    ],GREEN,24)
    c.card((1920,250,480,170),"ATAK Video playback",[
        "RTSP :8554 (verified locally)",
        "atak-viewer read credential",
    ],BLUE,24)
    c.card((1920,490,480,150),"TAK Server",[
        "Also connected to tak-edge",
        "Video Alias + visibility groups",
    ],ORANGE,24)
    c.arrow([(510,335),(740,335)],GREEN)
    c.arrow([(1680,335),(1920,335)],BLUE)
    c.arrow([(2160,490),(2160,420)],ORANGE,True)
    c.label((2200,443),["Metadata"],ORANGE)
    c.card((640,650,545,220),"media-viewer",[
        "viewer-public.yml | any: read live/*",
        "WebRTC :8889 | ICE :8189 TCP/UDP",
        "API :9997 | tak-console",
        "RTSP serving disabled",
    ],PURPLE,24)
    c.card((1240,650,545,220),"media-preview",[
        "viewer-preview.yml | admin: read live/*",
        "WebRTC :8889 | ICE :8190 TCP/UDP",
        "API disabled | RTSP serving disabled",
        "HTTP host access: loopback :8890",
    ],PURPLE,24)
    c.arrow([(970,445),(970,550),(910,550),(910,650)])
    c.arrow([(1450,445),(1450,550),(1510,550),(1510,650)])
    c.label((745,480),["On-demand RTSP/TCP :8554", "atak-viewer / same live/... path"])
    c.label((1300,480),["On-demand RTSP/TCP :8554", "atak-viewer / same live/... path"])
    c.card((640,1010,545,160),"media-viewer-gateway",[
        "HTTP/WHEP relay :8889",
        "viewer_state.json switch; no viewer login",
    ],ORANGE,24)
    c.card((1240,1010,545,160),"share-admin",[
        "Console admin login + preview relay",
        "Injects admin credential into preview",
    ],ORANGE,24)
    c.card((60,1010,450,160),"LAN browser",[
        "HTTP signaling: host :8889",
        "WebRTC media: ICE :8189",
    ],BLUE,24)
    c.card((1920,1010,480,160),"Local console browser",[
        "Loopback console host port*",
        "WebRTC media: ICE :8190",
    ],BLUE,24)
    c.arrow([(510,1090),(640,1090)],ORANGE,True)
    c.arrow([(1920,1090),(1785,1090)],ORANGE,True)
    c.arrow([(910,1010),(910,870)],ORANGE,True)
    c.arrow([(1510,1010),(1510,870)],ORANGE,True)
    c.label((930,915),["HTTP/WHEP"],ORANGE)
    c.label((1530,915),["HTTP/WHEP"],ORANGE)
    c.arrow([(640,740),(540,740),(540,965),(280,965),(280,1010)],BLUE)
    c.arrow([(1785,740),(1880,740),(1880,965),(2160,965),(2160,1010)],BLUE)
    c.label((65,795),["Direct ICE :8189", "DTLS-SRTP media"],BLUE)
    c.label((1950,795),["Direct ICE :8190", "DTLS-SRTP media"],BLUE)
    c.card((640,1230,1145,145),"Configuration and control",[
        "share-admin -> main/viewer API :9997 with tak-console (no host API mapping)",
        "Public stop = state-file gate + kick viewer sessions; preview is independent.",
    ],ORANGE,24)
    c.text((60,1435),"Solid arrows: media flow | Dashed arrows: signaling / metadata | Pulls are initiated by downstream nodes",25,MUTED)
    c.text((60,1478),"* Compose fallback :8766; documented workstation override :10066. HTTP signaling uses no HTTPS in this local stack.",25,MUTED)
    c.save("mediamtx-compose-nodes")


def main() -> None:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--font-dir",type=Path)
    args=parser.parse_args()
    if args.font_dir:
        regular=args.font_dir/"DejaVuSans.ttf"
        bold=args.font_dir/"DejaVuSans-Bold.ttf"
    else:
        regular=Path("C:/Windows/Fonts/segoeui.ttf")
        bold=Path("C:/Windows/Fonts/segoeuib.ttf")
    if not regular.is_file() or not bold.is_file():
        parser.error("Provide --font-dir with DejaVuSans.ttf and DejaVuSans-Bold.ttf")
    auth(regular,bold)
    topology(regular,bold)


if __name__=="__main__":
    main()
