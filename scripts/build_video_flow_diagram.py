"""Render the local media flow diagram used by the console task manual."""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs/images/console-task-07b-viewing-flow.png"
FONT = Path("C:/Windows/Fonts/msjh.ttc")
BOLD_FONT = Path("C:/Windows/Fonts/msjhbd.ttc")

BACKGROUND = "#ffffff"
PANEL = "#f7fafc"
TEXT = "#17324a"
MUTED = "#344e60"
SOURCE = "#0078a7"
CORE = "#168057"
ATAK = "#a56b00"
PUBLIC = "#4b5fae"
PREVIEW = "#2c629c"
SNAPSHOT = "#745092"


def font(size: int, *, bold: bool = False) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(BOLD_FONT if bold else FONT), size)


def card(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], color: str,
         title: str, details: list[str]) -> None:
    draw.rounded_rectangle(box, radius=24, fill=PANEL, outline=color, width=5)
    x, y, _, _ = box
    draw.text((x + 28, y + 18), title, font=font(42, bold=True), fill=TEXT)
    for index, detail in enumerate(details):
        draw.text((x + 28, y + 74 + index * 40), detail, font=font(29), fill=MUTED)


def arrow(draw: ImageDraw.ImageDraw, points: list[tuple[int, int]], color: str) -> None:
    draw.line(points, fill=color, width=9, joint="curve")
    x, y = points[-1]
    draw.polygon([(x, y), (x - 24, y - 14), (x - 24, y + 14)], fill=color)


def main() -> None:
    image = Image.new("RGB", (2000, 1180), BACKGROUND)
    draw = ImageDraw.Draw(image)
    draw.text((70, 47), "影像處理與流向｜takbox.local 本機部署",
              font=font(55, bold=True), fill=SOURCE)
    draw.text((70, 120), "來源推流 → MediaMTX 驗證與轉送 → ATAK／WebRTC／靜態縮圖",
              font=font(30), fill=MUTED)

    card(draw, (70, 210, 510, 385), SOURCE, "TAK ICU", [
        "相機影像 → 裝置端編碼", "RTSPS :8322（TLS）"])
    card(draw, (70, 450, 510, 675), SOURCE, "無人機／編碼器", [
        "RTSPS :8322（TLS）", "RTSP :8554（無 TLS）", "指定 live/... 路徑"])
    card(draw, (70, 740, 510, 925), SOURCE, "其他影像來源", [
        "RTSPS :8322（TLS）", "RTSP :8554（無 TLS）"])

    card(draw, (620, 245, 1170, 880), CORE, "MediaMTX 主串流", [
        "驗證發布帳密與 live/ 路徑", "接收來源影像並供讀取", "", "ICU：live/<小隊>/<隊員>/", "         VIDEO_1", "設備：指定的 live/... 路徑", "", "獨立讀取帳密供播放端存取", "TAK Server 交付影像別名"])

    card(draw, (1290, 180, 1930, 385), ATAK, "ATAK Video Alias", [
        "RTSP :8554／TCP（無 TLS）", "讀取帳密；Reliable P2P", "ATAK 直接從 MediaMTX 取流"])
    card(draw, (1290, 425, 1930, 635), PUBLIC, "公開 WebRTC 觀看", [
        "內部 RTSP → media-viewer", "HTTP :8889 信令（無 TLS）", "ICE :8189；媒體 DTLS-SRTP"])
    card(draw, (1290, 675, 1930, 885), PREVIEW, "控制台預覽／監視器", [
        "內部 RTSP → media-preview", "本機 HTTP :10066 信令", "ICE :8190；媒體 DTLS-SRTP"])
    card(draw, (1290, 925, 1930, 1100), SNAPSHOT, "管理頁靜態縮圖", [
        "內部 RTSP → FFmpeg", "擷取一個影格 → JPEG"])

    for y in (298, 562, 832):
        arrow(draw, [(516, y), (614, y)], SOURCE)
    for y, target, color in ((310, 282, ATAK), (500, 530, PUBLIC),
                             (740, 780, PREVIEW), (835, 1012, SNAPSHOT)):
        arrow(draw, [(1176, y), (1228, y), (1228, target), (1284, target)], color)

    draw.text((70, 1119), "ICU 的 Use SSL? 代表 RTSPS／TLS；WebRTC 的 HTTP 信令沒有 TLS，但媒體使用 DTLS-SRTP。",
              font=font(29), fill=MUTED)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    image.save(OUTPUT, optimize=True)
    print(f"Wrote {OUTPUT}")


if __name__ == "__main__":
    main()
