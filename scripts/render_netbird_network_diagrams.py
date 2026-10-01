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
        V["Mumble container<br/>Host TCP+UDP 40000 to container 64738<br/>Team ingress / login / channel ACL"]
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
    G -->|"Team voice TCP/UDP policy"| V
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
        'Voice: team ingress policy + Mumble identity / channel ACL'], canvas.GREEN, 22)
    c.label((465, 280), ['NetBird tunnel'], canvas.BLUE)
    c.label((1140, 252), ['Host route /32', 'SNAT -> VPC'], canvas.GREEN)
    c.label((1245, 515), ['Peer INPUT', 'No route SNAT'], canvas.GREEN)
    c.label((272, 482), ['Private DNS'], canvas.PURPLE)
    c.label((840, 146), ['Existing public TAK entry retained'], '#687788')
    c.text((50, 945), 'Solid: VPN data path | Dashed: DNS or preserved public entry | Return traffic follows each connection', 23)
    c.text((50, 992), 'Only one TAK host route is advertised. No full-VPC subnet route and no Internet exit node.', 24, canvas.MUTED)
    c.text((50, 1037), 'TCP 8446 is allowed by policy; the previous service probe was unreachable. Team voice channel ACL rollout remains pending.', 23, canvas.MUTED)
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
        'ATAK / ICU / browser / admin', 'alpha / bravo / charlie / admin', 'Peer-to-peer data is preferred', 'Relay fallback is network-dependent', 'Team peers have voice ingress policy'], canvas.BLUE, 22)
    c.card((780, 640, 630, 330), 'Gateway peer', [
        'INPUT: access to services on this VM', 'FORWARD: TAK-Primary single-host route', 'TAK forwarding uses masquerade / SNAT', 'Local services retain the peer source', 'No default route / full-VPC route', 'Primary TAK login / firewall stay unchanged'], canvas.GREEN, 23)
    c.card((1700, 505, 540, 190), 'Protected HTTPS sites', [
        'Admin 8443: admin peer + Basic Auth', 'Media 443: approved peer + viewer login', 'Apps: loopback 8766 / 8767'], canvas.GREEN, 23)
    c.card((1700, 810, 540, 300), 'MediaMTX', [
        'NetBird-only RTSP / RTSPS / RTMP / RTMPS', 'TCP 8554 / 8322 / 1935 / 1936', 'UDP 8000 / 8001 / 8189', 'RTSP read: approved peer, no password', 'Publish + protected reads: credentials', 'HTTP WebRTC / API: loopback 8889 / 9997'], canvas.GREEN, 21)
    c.card((780, 1050, 630, 185), 'Media authorization | loopback 8768', [
        'Read-only NetBird group lookup; exact path/action grants', 'Admin isolation control; active reader rechecks', 'Own team + assigned shared streams while isolation is on'], canvas.PURPLE, 21)
    c.card((1700, 1170, 540, 195), 'Mumble', [
        'Host TCP+UDP 40000 -> container 64738', 'Team ingress, login, and channel ACLs', 'Team voice ACL rollout remains pending'], canvas.GREEN, 23)
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
    c.text((60, 1610), 'Team ingress permits transport; Mumble login and channel ACLs still apply.', 24, canvas.MUTED)
    c.text((60, 1672), 'The existing public TAK endpoint remains reachable under its original rules. Private media does not use that public entry.', 24, canvas.MUTED)
    c.save('network-architecture')


DUAL_PATH = """flowchart LR
    U["Field / desktop clients<br/>ATAK / ICU / Vx / browser<br/>Wi-Fi or cellular"]
    O(("NetBird overlay<br/>Direct peer tunnel / relay fallback"))
    I(("Public Internet<br/>Direct access from approved source IPs"))
    F["Source IP allowlist<br/>Specific approved IP/CIDR only<br/>Other sources denied<br/>Service authentication retained"]
    subgraph MANAGEMENT["Management VM - e2-small"]
        C["NetBird control / dashboard / relay<br/>Public HTTPS 443 / STUN UDP 3478<br/>Local account + MFA"]
        G["Gateway peer<br/>INPUT service policy<br/>FORWARD TAK host policy"]
        X["Same MediaMTX<br/>Planned: NetBird + restricted public media entry<br/>All publication requires credentials"]
        H["Protected admin / media viewer<br/>Admin 8443 / viewer 443<br/>NetBird peer + service login"]
        M["Same Mumble container<br/>Host TCP+UDP 40000 to 64738<br/>Service identity / channel ACL"]
    end
    subgraph PRIMARY["Primary TAK VM - e2-medium"]
        T["Same TAK Server<br/>TCP 8089 / 8443<br/>Existing client certificate"]
        DB["PostgreSQL / PostGIS<br/>Private database service"]
    end
    U -.->|"Public bootstrap before VPN login"| C
    C -.->|"Enrollment / DNS / policies / signaling"| G
    U -->|"VPN connected / eligible peer"| O
    O -->|"Encrypted overlay"| G
    G -->|"INPUT: original peer source<br/>Publish requires credentials<br/>RTSP read: approved peer/path, no password"| X
    G -->|"Approved web peer + service login"| H
    G -->|"INPUT: team TCP/UDP 40000<br/>Original peer source"| M
    G -->|"FORWARD: single TAK host /32<br/>VPC route + masquerade / SNAT"| T
    U -->|"Public service endpoint"| I
    I --> F
    F -->|"Planned public media entry<br/>Source allowlist + service authorization"| X
    F -->|"Restricted public voice entry<br/>Source allowlist + service login"| M
    F -->|"Restricted public TAK entry<br/>Source allowlist + client certificate<br/>No Gateway hop"| T
    T --> DB
    classDef vpn fill:#edf7fd,stroke:#1673ad,color:#17324a;
    classDef legacy fill:#fff6eb,stroke:#a96416,color:#17324a;
    classDef service fill:#eff9f5,stroke:#168069,color:#17324a;
    classDef control fill:#f3effa,stroke:#7151a5,color:#17324a;
    class U,O,G vpn;
    class I,F legacy;
    class X,H,M,T,DB service;
    class C control;
"""


def network_cloud(c, box, title, lines, color):
    """Draw the same cloud silhouette in PNG and SVG."""
    from html import escape
    x, y, w, h = box
    commands = [
        ((0.03, .53), (.03, .32), (.18, .26), (.26, .34)),
        ((.26, .34), (.28, .05), (.56, .04), (.64, .27)),
        ((.64, .27), (.84, .15), (.98, .34), (.92, .53)),
        ((.92, .53), (1.03, .75), (.85, .94), (.70, .87)),
        ((.70, .87), (.47, 1.04), (.28, .91), (.26, .86)),
        ((.26, .86), (.03, .94), (-.02, .71), (.03, .53)),
    ]
    points = []
    path = f'M {x+w*.03} {y+h*.53}'
    for start, a, b, end in commands:
        path += f' C {x+w*a[0]} {y+h*a[1]} {x+w*b[0]} {y+h*b[1]} {x+w*end[0]} {y+h*end[1]}'
        for i in range(25):
            t = i / 24
            px = (1-t)**3*start[0]+3*(1-t)**2*t*a[0]+3*(1-t)*t*t*b[0]+t**3*end[0]
            py = (1-t)**3*start[1]+3*(1-t)**2*t*a[1]+3*(1-t)*t*t*b[1]+t**3*end[1]
            points.append((x+w*px, y+h*py))
    fill = '#edf7fd' if color == '#1673ad' else '#fff6eb'
    c.draw.polygon(points, fill=fill)
    c.draw.line(points+[points[0]], fill=color, width=3)
    c.svg.append(f'<path d="{escape(path)} Z" fill="{fill}" stroke="{color}" stroke-width="3"/>')
    c.text((x+68, y+75), title, 30, color, True)
    for i, line in enumerate(lines):
        c.text((x+68, y+117+i*31), line, 22, color)


def dual_path_topology(canvas, regular, bold):
    c = canvas.Canvas((2500, 1980), 'Planned topology | NetBird + source-restricted public access',
        'Two independent paths to the same TAK, MediaMTX and Mumble services | 2026-10-01', regular, bold)
    c.panel((1150, 190, 1290, 1160), '#168069', '#f8fcfa')
    c.text((1180, 207), 'Management VM | e2-small', 29, canvas.GREEN, True)
    c.panel((1150, 1450, 1290, 300), '#168069', '#f8fcfa')
    c.text((1180, 1464), 'Primary TAK VM | e2-medium', 29, canvas.GREEN, True)
    # Route lines are drawn before nodes to keep endpoint labels readable.
    c.arrow([(420, 550), (570, 550)], canvas.BLUE)
    c.arrow([(1060, 550), (1210, 550)], canvas.BLUE)
    c.arrow([(1680, 525), (1790, 525)], canvas.BLUE)
    c.arrow([(1680, 650), (1700, 650), (1700, 935), (1790, 935)], canvas.BLUE)
    c.arrow([(1680, 730), (1740, 730), (1740, 1160), (1790, 1160)], canvas.BLUE)
    c.arrow([(1620, 790), (1620, 900), (1175, 900), (1175, 1410), (1740, 1410), (1740, 1540), (1790, 1540)], canvas.BLUE)
    c.arrow([(420, 850), (480, 850), (480, 1130), (570, 1130)], canvas.ORANGE)
    c.arrow([(1060, 1130), (1210, 1130)], canvas.ORANGE)
    c.arrow([(1680, 1040), (1725, 1040), (1725, 600), (1790, 600)], canvas.ORANGE)
    c.arrow([(1680, 1135), (1760, 1135), (1760, 1240), (1790, 1240)], canvas.ORANGE)
    c.arrow([(1445, 1200), (1445, 1380), (2460, 1380), (2460, 1665), (2410, 1665)], canvas.ORANGE)
    c.arrow([(240, 540), (240, 290), (1210, 290)], canvas.PURPLE, True)
    c.arrow([(1450, 400), (1450, 465)], canvas.PURPLE, True)
    c.arrow([(1790, 1600), (1680, 1600)], canvas.GREEN)
    c.card((60, 540, 360, 390), 'Client devices', [
        'ATAK / ICU / Vx', 'Browser / admin', 'Wi-Fi or cellular', '',
        'TAK certificate retained', 'DNS selects endpoint', 'Policies authorize access', 'Vx: select VPN interface'], canvas.BLUE, 21)
    network_cloud(c, (570, 440, 490, 240), 'NetBird overlay', ['Encrypted peer tunnel', 'Direct / relay fallback'], canvas.BLUE)
    network_cloud(c, (570, 1000, 490, 260), 'Public Internet', ['Approved source IPs only', 'Direct service access'], canvas.ORANGE)
    c.card((1210, 250, 1200, 150), 'NetBird control / dashboard / relay', [
        'Public login + MFA before VPN use | HTTPS 443 / STUN UDP 3478',
        'Enrollment, exact private DNS, group policies and signaling'], canvas.PURPLE, 24)
    c.card((1210, 465, 470, 325), 'Gateway peer', [
        'NetBird interface on management', 'INPUT: media / admin / voice',
        'FORWARD: TAK host /32 only', 'TAK route: masquerade / SNAT',
        'No Internet exit / full-VPC route', 'INPUT retains original peer source'], canvas.BLUE, 22)
    c.card((1790, 465, 620, 390), 'Same MediaMTX', [
        'NetBird + restricted public media entry',
        'RTSP 8554 / RTSPS 8322',
        'RTMP 1935 / RTMPS 1936',
        'RTP 8000 / RTCP 8001 / WebRTC 8189 UDP',
        'HTTP 8889 / API 9997: loopback backends',
        'Publish: credentials on every protocol',
        'VPN RTSP read: approved peer/path, no password',
        'Public: source allowlist + service authorization'], canvas.GREEN, 22)
    c.card((1790, 885, 620, 190), 'Admin / media viewer', [
        'Admin 8443: admin peer + service login',
        'Viewer 443: approved peer + viewer login',
        'NetBird ingress; no new public web grant'], canvas.GREEN, 22)
    c.card((1790, 1105, 620, 220), 'Same Mumble Server', [
        'Host TCP+UDP 40000 -> container 64738',
        'VPN: team peer policy + service login',
        'Public: approved source + service login',
        'Channel ACLs are service permissions'], canvas.GREEN, 23)
    c.card((1210, 980, 470, 220), 'Source IP allowlist', [
        'Specific approved IP/CIDR only', 'Other sources denied',
        'Service authentication retained', 'Direct TAK / media / voice entry'], canvas.ORANGE, 21)
    c.card((1210, 1505, 470, 210), 'Database service', [
        'PostgreSQL / PostGIS', 'Private database connection', 'No public DB path shown'], canvas.GREEN, 23)
    c.card((1790, 1505, 620, 210), 'Same TAK Server', [
        'TCP 8089 / 8443 | existing certificate',
        'VPN source: Gateway VPC after SNAT',
        'Public source: approved client IP / NAT'], canvas.GREEN, 23)
    c.label((580, 250), ['Public bootstrap / control'], canvas.PURPLE)
    c.label((595, 377), ['NETBIRD PATH'], canvas.BLUE)
    c.label((595, 940), ['SOURCE-RESTRICTED PUBLIC PATH'], canvas.ORANGE)
    c.label((750, 1340), ['TAK /32 via VPC', 'Gateway SNAT'], canvas.BLUE)
    c.label((1870, 1350), ['Restricted public TAK entry', 'No NetBird Gateway hop'], canvas.ORANGE)
    c.text((60, 1785), 'BLUE: NetBird data path   |   AMBER: source-restricted public access   |   PURPLE DASHED: control / bootstrap', 25, canvas.INK)
    c.text((60, 1830), 'Both paths reach the same TAK, MediaMTX and Mumble services. DNS selects the endpoint; there is no automatic failover.', 25, canvas.MUTED)
    c.text((60, 1875), 'Plan only: public MediaMTX access still requires listener, authorization and firewall configuration.', 25, canvas.MUTED)
    c.text((60, 1920), 'CoT carries Video metadata; video bytes go directly to MediaMTX. Service authentication remains required.', 24, canvas.MUTED)
    c.save('netbird-dual-path-topology')


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
    for name, source in [('netbird-routing', ROUTING), ('network-architecture', ARCHITECTURE), ('netbird-dual-path-topology', DUAL_PATH)]:
        (args.output_dir / (name + '.mmd')).write_text(source, encoding='utf-8')
    with contextlib.redirect_stdout(io.StringIO()):
        routing(canvas, regular, bold)
        architecture(canvas, regular, bold)
        dual_path_topology(canvas, regular, bold)
    for name in ('netbird-routing', 'network-architecture', 'netbird-dual-path-topology'):
        print(f'Wrote {args.output_dir / name} (.mmd, .svg, .png)')


if __name__ == '__main__':
    main()
