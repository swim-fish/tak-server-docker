"""Render sanitized NetBird routing and cloud architecture diagrams as SVG/PNG/Mermaid."""
from __future__ import annotations

import argparse
import contextlib
import io
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROUTING = """flowchart LR
    D["Enrolled device<br/>alpha / bravo / charlie / admin"] -->|"Encrypted NetBird peer tunnel"| G["Gateway peer<br/>Management VM"]
    G -->|"TAK-Primary host route /32<br/>FORWARD + masquerade / SNAT"| T["Primary TAK Server<br/>Existing client certificate identity"]
    G -->|"Peer INPUT policy<br/>Original NetBird source address"| L["Local admin / media / voice services"]
    Z["Exact private DNS<br/>TAK to its VPC address<br/>Media / Admin / Voice to Gateway"] -.->|"Group-scoped answers"| D
    D -.->|"Existing public TAK entry retained<br/>Outside the VPN route"| T
    classDef vpn fill:#eaf5fb,stroke:#1673ad,color:#17324a;
    classDef backend fill:#eaf8f3,stroke:#168069,color:#17324a;
    class D,G,Z vpn;
    class T,L backend;
"""
ARCHITECTURE = """flowchart TB
    U["Enrolled devices<br/>ATAK / ICU / browser / admin"]
    PKG["Private package storage / download service<br/>Direct HTTPS download; no VPN route required"]
    subgraph MGMT["Management VM - e2-small - shared availability boundary"]
        N["Public Nginx / NetBird bootstrap<br/>HTTPS 443 / STUN UDP 3478"]
        C["NetBird management / dashboard / relay<br/>HTTP backends: loopback 18080 / 18081"]
        G["NetBird Gateway peer<br/>INPUT service policy / FORWARD host policy"]
        H["Protected Nginx vhosts<br/>Admin 8443: admin peer + Basic Auth<br/>Media 443: approved peer + viewer login"]
        A["Admin 8766 / media viewer 8767<br/>Loopback only"]
        X["MediaMTX private listeners<br/>RTSP 8554 / RTSPS 8322<br/>RTMP 1935 / RTMPS 1936<br/>RTP 8000 / RTCP 8001 / WebRTC 8189 UDP"]
        W["MediaMTX HTTP backends<br/>WebRTC 8889 / API 9997: loopback"]
        Q["Media authorization 8768 - loopback<br/>NetBird group + action + exact active path<br/>Admin isolation toggle / reader rechecks"]
        V["Mumble container<br/>Host TCP+UDP 40000 to container 64738<br/>Voice group / login / channel ACL"]
    end
    subgraph PRIMARY["Primary TAK VM - e2-medium"]
        T["TAK Server<br/>TCP 8089 / 8443<br/>8446 is a policy entry; availability not established"]
        DB["PostgreSQL / PostGIS"]
    end
    U -.->|"Public login and MFA"| N
    N -->|"Loopback proxy"| C
    C -.->|"Registration / policies / signaling"| G
    U -->|"Encrypted peer tunnel<br/>Direct preferred; relay fallback when needed"| G
    G -->|"Local peer INPUT policy"| H
    H -->|"Loopback HTTP"| A
    A -->|"Authenticated WHEP proxy"| W
    G -->|"Publish: credentials on every protocol<br/>Plain RTSP read: no password, authorized peer/path"| X
    X --> W
    X -.->|"HTTP auth callback"| Q
    Q -.->|"Read-only directory API"| C
    H -.->|"Peer ingress authorization"| Q
    A -.->|"Admin isolation setting"| Q
    G -->|"Voice policy for separately assigned voice peers"| V
    G -->|"TAK-Primary /32<br/>Masquerade / SNAT to VPC source"| T
    T --> DB
    T -.->|"CoT / Video metadata, not video bytes"| U
    U -.->|"Preserved public TAK entry"| T
    U -->|"HTTPS outside the overlay"| PKG
    classDef private fill:#eaf8f3,stroke:#168069,color:#17324a;
    classDef control fill:#f2eef9,stroke:#7151a5,color:#17324a;
    classDef client fill:#eaf5fb,stroke:#1673ad,color:#17324a;
    class G,H,A,X,W,Q,V,T,DB private;
    class N,C control;
    class U,PKG client;
"""


def routing(canvas, regular, bold):
    c = canvas.Canvas((1800, 1120), 'NetBird | Current routing',
        'Host routing to TAK and direct peer access to co-hosted services are separate policies', regular, bold)
    c.arrow([(440, 325), (670, 325)])
    c.arrow([(1115, 325), (1370, 325)], canvas.GREEN)
    c.arrow([(1115, 405), (1230, 405), (1230, 745), (1370, 745)], canvas.GREEN)
    c.arrow([(245, 550), (245, 445)], canvas.PURPLE, True)
    c.arrow([(245, 215), (245, 178), (1555, 178), (1555, 205)], '#687788', True)
    c.card((50, 215, 390, 230), 'Enrolled device', [
        'alpha / bravo / charlie / admin', 'Existing TAK client certificate', 'Assigned media / voice roles'], canvas.BLUE, 22)
    c.card((670, 215, 445, 250), 'Gateway peer', [
        'Management VM / NetBird client', 'FORWARD: selected TAK host route', 'INPUT: local service access', 'SNAT only on the TAK route'], canvas.BLUE, 22)
    c.card((1370, 205, 380, 265), 'Primary TAK Server', [
        'VPC private host /32', 'TCP 8089 / 8443', 'No NetBird agent required', 'Sees Gateway VPC source', 'Authenticates TAK certificate'], canvas.GREEN, 22)
    c.card((1370, 615, 380, 270), 'Local services', [
        'Admin / media / Mumble', 'Direct Gateway NetBird address', 'Original peer source is visible', 'Peer group + service auth', 'Media isolation is enabled'], canvas.GREEN, 21)
    c.card((50, 550, 390, 270), 'Private DNS', [
        'TAK -> private TAK address', 'Media / Admin / Voice -> Gateway', 'Admin answers: admin peers only', 'Public NetBird control unchanged', 'No parent-domain override'], canvas.PURPLE, 20)
    c.card((540, 570, 660, 310), 'Identity at each boundary', [
        'TAK: existing certificate identity + Gateway VPC source',
        'Media: NetBird peer group + operation + exact path',
        'RTSP read: no password for approved peers and paths',
        'Publish / protected read: credentials remain required',
        'Voice: separate voice assignment + Mumble channel ACL'], canvas.GREEN, 22)
    c.label((465, 280), ['NetBird tunnel'], canvas.BLUE)
    c.label((1140, 252), ['Host route /32', 'SNAT -> VPC'], canvas.GREEN)
    c.label((1245, 515), ['Peer INPUT', 'No route SNAT'], canvas.GREEN)
    c.label((272, 482), ['Private DNS'], canvas.PURPLE)
    c.label((840, 146), ['Existing public TAK entry retained'], '#687788')
    c.text((50, 945), 'Solid: VPN data path | Dashed: DNS or preserved public entry | Return traffic follows each connection', 23)
    c.text((50, 992), 'Only one TAK host route is advertised. No full-VPC subnet route and no Internet exit node.', 24, canvas.MUTED)
    c.text((50, 1037), 'TCP 8446 is allowed by policy; the previous service probe was unreachable. Voice onboarding is separate.', 23, canvas.MUTED)
    c.save('netbird-routing')


def architecture(canvas, regular, bold):
    c = canvas.Canvas((2300, 1740), 'Network architecture | NetBird-integrated cloud deployment',
        'Observed configuration: two VMs; public bootstrap, private service entry, and an unchanged public TAK path', regular, bold)
    c.panel((720, 180, 1550, 1230), canvas.GREEN, '#f8fcfa')
    c.text((750, 192), 'Management VM | e2-small | one shared availability boundary', 27, canvas.GREEN, True)
    c.arrow([(525, 310), (780, 310)], canvas.PURPLE, True)
    c.arrow([(525, 785), (780, 785)], canvas.BLUE)
    c.arrow([(1095, 440), (1095, 640)], canvas.PURPLE, True)
    c.arrow([(1410, 710), (1525, 710), (1525, 590), (1700, 590)], canvas.GREEN)
    c.arrow([(1410, 820), (1590, 820), (1590, 930), (1700, 930)], canvas.GREEN)
    c.arrow([(1410, 935), (1525, 935), (1525, 1265), (1700, 1265)], canvas.GREEN)
    c.arrow([(1700, 1000), (1455, 1000), (1455, 1125), (1410, 1125)], canvas.PURPLE, True)
    c.arrow([(780, 900), (620, 900), (620, 1450), (1605, 1450), (1605, 1570), (1700, 1570)], canvas.GREEN)
    c.arrow([(290, 930), (290, 1240)], canvas.BLUE)
    c.card((60, 240, 465, 190), 'Before VPN login', [
        'Public control hostname', 'Local accounts + MFA', 'HTTPS 443 / STUN UDP 3478'], canvas.PURPLE, 23)
    c.card((780, 240, 630, 200), 'NetBird control / relay', [
        'Existing Nginx public bootstrap endpoint', 'Management + dashboard: loopback 18080 / 18081', 'Policy and signaling; relay fallback when needed'], canvas.PURPLE, 23)
    c.card((60, 640, 465, 290), 'Enrolled service devices', [
        'ATAK / ICU / browser / admin', 'alpha / bravo / charlie / admin', 'Peer-to-peer data is preferred', 'Relay fallback is network-dependent', 'Voice peers are separately assigned'], canvas.BLUE, 22)
    c.card((780, 640, 630, 330), 'Gateway peer', [
        'INPUT: access to services on this VM', 'FORWARD: TAK-Primary single-host route', 'TAK forwarding uses masquerade / SNAT', 'Local services retain the peer source', 'No default route / full-VPC route', 'Primary TAK login / firewall stay unchanged'], canvas.GREEN, 23)
    c.card((1700, 505, 540, 190), 'Protected HTTPS sites', [
        'Admin 8443: admin peer + Basic Auth', 'Media 443: approved peer + viewer login', 'Apps: loopback 8766 / 8767'], canvas.GREEN, 23)
    c.card((1700, 810, 540, 300), 'MediaMTX', [
        'NetBird-only RTSP / RTSPS / RTMP / RTMPS', 'TCP 8554 / 8322 / 1935 / 1936', 'UDP 8000 / 8001 / 8189', 'RTSP read: approved peer, no password', 'Publish + protected reads: credentials', 'HTTP WebRTC / API: loopback 8889 / 9997'], canvas.GREEN, 21)
    c.card((780, 1050, 630, 185), 'Media authorization | loopback 8768', [
        'Read-only NetBird group lookup; exact path/action grants', 'Admin isolation control; active reader rechecks', 'Own team + assigned shared streams while isolation is on'], canvas.PURPLE, 21)
    c.card((1700, 1170, 540, 195), 'Mumble', [
        'Host TCP+UDP 40000 -> container 64738', 'Voice group, login, and channel ACLs', 'Team voice ACL rollout remains pending'], canvas.GREEN, 23)
    c.card((1700, 1480, 540, 180), 'Primary TAK VM | e2-medium', [
        'VPC TAK 8089 / 8443 + PostgreSQL/PostGIS', 'CoT / Video metadata; video does not transit TAK', 'Existing TAK client certificate authentication'], canvas.GREEN, 21)
    c.card((60, 1240, 465, 230), 'Package downloads', [
        'GCS / download service', 'Direct HTTPS outside the overlay', 'Signed URL expiry is independent', 'No Gateway download route required'], canvas.BLUE, 21)
    c.label((550, 270), ['Public bootstrap'], canvas.PURPLE)
    c.label((550, 720), ['Encrypted tunnel', 'direct or relay'], canvas.BLUE)
    c.label((1118, 520), ['Policy / signaling'], canvas.PURPLE)
    c.label((1465, 1045), ['HTTP auth'], canvas.PURPLE)
    c.label((800, 1468), ['TAK-Primary /32', 'SNAT -> VPC'], canvas.GREEN)
    c.label((310, 1060), ['Direct HTTPS'], canvas.BLUE)
    c.text((60, 1550), 'Solid: data path | Dashed: control / authorization', 25)
    c.text((60, 1610), 'Service-group rules do not assign Mumble voice rights automatically.', 24, canvas.MUTED)
    c.text((60, 1672), 'The existing public TAK endpoint remains reachable under its original rules. Private media does not use that public entry.', 24, canvas.MUTED)
    c.save('network-architecture')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, default=ROOT / 'docs/network/diagrams')
    parser.add_argument('--font-dir', type=Path)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    spec = importlib.util.spec_from_file_location('network_canvas', ROOT / 'docs/mediamtx/render_auth_node_diagrams.py')
    canvas = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(canvas)
    canvas.OUT = args.output_dir
    regular = (args.font_dir / 'DejaVuSans.ttf') if args.font_dir else Path('C:/Windows/Fonts/segoeui.ttf')
    bold = (args.font_dir / 'DejaVuSans-Bold.ttf') if args.font_dir else Path('C:/Windows/Fonts/segoeuib.ttf')
    if not regular.is_file() or not bold.is_file():
        parser.error('Provide --font-dir containing DejaVuSans.ttf and DejaVuSans-Bold.ttf')
    for name, source in [('netbird-routing', ROUTING), ('network-architecture', ARCHITECTURE)]:
        (args.output_dir / (name + '.mmd')).write_text(source, encoding='utf-8')
    with contextlib.redirect_stdout(io.StringIO()):
        routing(canvas, regular, bold)
        architecture(canvas, regular, bold)
    for name in ('netbird-routing', 'network-architecture'):
        print(f'Wrote {args.output_dir / name} (.mmd, .svg, .png)')


if __name__ == '__main__':
    main()
