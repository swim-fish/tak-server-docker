#!/usr/bin/env python3
"""Build combined or Vx-only packages from a verified Vx 2.1 mission export."""

import argparse
import copy
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import uuid
import xml.etree.ElementTree as ET
from zipfile import ZIP_DEFLATED, ZipFile


def varint(data, pos):
    value = 0
    for shift in range(0, 70, 7):
        if pos >= len(data):
            raise ValueError('Truncated protobuf varint')
        byte = data[pos]
        pos += 1
        value |= (byte & 127) << shift
        if not byte & 128:
            return value, pos
    raise ValueError('Invalid protobuf varint')


def encode_varint(value):
    if value < 0:
        raise ValueError('Negative protobuf value')
    out = bytearray()
    while value > 127:
        out.append((value & 127) | 128)
        value >>= 7
    out.append(value)
    return bytes(out)


def decode(data):
    fields = []
    pos = 0
    while pos < len(data):
        tag, pos = varint(data, pos)
        number, wire = tag >> 3, tag & 7
        if not number:
            raise ValueError('Invalid protobuf field')
        if wire == 0:
            value, pos = varint(data, pos)
        elif wire in (1, 2, 5):
            if wire == 2:
                size, pos = varint(data, pos)
            else:
                size = 8 if wire == 1 else 4
            if pos + size > len(data):
                raise ValueError('Truncated protobuf field')
            value = data[pos:pos + size]
            pos += size
        else:
            raise ValueError('Unsupported protobuf wire type')
        fields.append((number, wire, value))
    return fields


def encode(fields):
    out = bytearray()
    for number, wire, value in fields:
        out += encode_varint(number << 3 | wire)
        if wire == 0:
            out += encode_varint(value)
        else:
            if wire == 2:
                out += encode_varint(len(value))
            out += value
    return bytes(out)


def field(fields, number, wire=2):
    matches = [v for n, w, v in fields if n == number and w == wire]
    if len(matches) != 1:
        raise ValueError(f'Expected exactly one field {number}/{wire}')
    return matches[0]


def replace(fields, values):
    return [(n, w, values.get(n, v)) for n, w, v in fields]


def replace_repeated(fields, number, values):
    """Replace one repeated message field while retaining unknown wrapper fields."""
    output = []
    inserted = False
    for n, w, value in fields:
        if n == number:
            if w != 2:
                raise ValueError('Unexpected repeated field wire type')
            if not inserted:
                output.extend((number, 2, item) for item in values)
                inserted = True
        else:
            output.append((n, w, value))
    if not inserted:
        raise ValueError('Missing repeated message field')
    return output


def validate_channels(channels):
    required = {'number', 'alias', 'mumble_channel_id', 'mumble_channel_name'}
    if not isinstance(channels, list) or not channels:
        raise ValueError('Channels must be a non-empty JSON array')
    numbers, ids = set(), set()
    for channel in channels:
        if not isinstance(channel, dict) or set(channel) != required:
            raise ValueError('Each channel requires number, alias, mumble_channel_id and mumble_channel_name')
        number, channel_id = channel['number'], channel['mumble_channel_id']
        if type(number) is not int or not 1 <= number <= 99:
            raise ValueError('Channel number must be an integer from 1 to 99')
        if type(channel_id) is not int or not 0 <= channel_id <= 0xFFFFFFFF:
            raise ValueError('Mumble channel ID must be an unsigned 32-bit integer')
        for key in ('alias', 'mumble_channel_name'):
            value = channel[key]
            if not isinstance(value, str) or not value.strip() or any(ord(c) < 32 for c in value):
                raise ValueError(f'Invalid {key}')
        if number in numbers or channel_id in ids:
            raise ValueError('Duplicate channel number or Mumble channel ID')
        numbers.add(number)
        ids.add(channel_id)
    return channels


def read_archive(path):
    with ZipFile(path) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)):
            raise ValueError('Duplicate ZIP entries')
        for name in names:
            p = PurePosixPath(name)
            if p.is_absolute() or '..' in p.parts or '\\' in name or ':' in name:
                raise ValueError('Unsafe ZIP entry')
        if sum(i.file_size for i in archive.infolist()) > 10_000_000:
            raise ValueError('Configuration package exceeds 10 MB')
        if archive.testzip():
            raise ValueError('ZIP CRC failure')
        return {name: archive.read(name) for name in names if not name.endswith('/')}


def build(tak_path, native_path, output, host, port, mission_name, vx_only=False,
          channels=None, package_name=None):
    if not 1 <= port <= 65535 or not host or any(c in host for c in '/\\: '):
        raise ValueError('Expected a DNS name or IPv4 address and a valid port')
    if output.resolve() in (tak_path.resolve(), native_path.resolve()):
        raise ValueError('Output must not overwrite an input package')
    native = read_archive(native_path)
    manifest = ET.fromstring(native['MANIFEST/manifest.xml'])
    config = manifest.find('Configuration')
    contents = manifest.find('Contents')
    if manifest.get('version') != '2' or config is None or contents is None or len(contents) != 2:
        raise ValueError('Expected native Vx manifest with exactly two payloads')
    action = config.find("Parameter[@name='onReceiveAction']")
    if action is None or action.get('value') != 'com.atakmap.android.gbr.multicastvoice.sharing.downloaded':
        raise ValueError('Missing native Vx callback')
    entries = [c.get('zipEntry') for c in contents]
    proto_path = next(n for n in entries if n.endswith('_proto'))
    json_path = next(n for n in entries if not n.endswith('_proto'))
    legacy = json.loads(native[json_path])
    if not isinstance(legacy.get('channels'), list) or not legacy['channels']:
        raise ValueError('Expected a Vx mission with Mumble channels')

    root = decode(native[proto_path])
    channel_wrapper, connection_wrapper = decode(field(root, 3)), decode(field(root, 4))
    encoded_channels = [value for number, wire, value in channel_wrapper if number == 1 and wire == 2]
    if len(encoded_channels) != len(legacy['channels']):
        raise ValueError('Native JSON/protobuf channel count mismatch')
    connection = decode(field(connection_wrapper, 1))
    old_id = field(root, 1).decode()
    expected = legacy['missionId']['uuid'] == old_id and legacy['name'] == field(root, 2).decode()
    templates = []
    for old, encoded_channel in zip(legacy['channels'], encoded_channels):
        channel = decode(encoded_channel)
        mumble = decode(field(channel, 6))
        expected = expected and (
            old['isMumble'] is True and old['missionId'] == old_id
            and old['id'] == field(channel, 1).decode()
            and old['name'] == field(channel, 2).decode()
            and old['subtitle'] == field(mumble, 2).decode()
            and old['serverChannelId'] == field(mumble, 1, 0)
            and old['host'] == f'{field(connection, 2).decode()}:{field(connection, 3, 0)}'
            and field(channel, 4) == field(connection, 1))
        templates.append((old, channel, mumble))
    if not expected or encode(root) != native[proto_path]:
        raise ValueError('Native JSON/protobuf mismatch or unsupported encoding')

    # Preserve each existing channel's unknown fields; clone the first for new IDs.
    mission_id, connection_id = [str(uuid.uuid4()) for _ in range(2)]
    legacy['missionId']['uuid'] = mission_id
    legacy['name'] = mission_name
    if channels is None:
        channels = [{'number': field(channel, 3, 0), 'alias': old['name'],
                     'mumble_channel_id': old['serverChannelId'],
                     'mumble_channel_name': old['subtitle']}
                    for old, channel, _ in templates]
    validate_channels(channels)
    templates_by_id = {template[0]['serverChannelId']: template for template in templates}
    legacy_channels, proto_channels = [], []
    for spec in channels:
        old, channel, mumble = templates_by_id.get(spec['mumble_channel_id'], templates[0])
        channel_id = str(uuid.uuid4())
        item = copy.deepcopy(old)
        item.update(id=channel_id, missionId=mission_id, host=f'{host}:{port}',
                    name=spec['alias'], subtitle=spec['mumble_channel_name'],
                    serverChannelId=spec['mumble_channel_id'])
        legacy_channels.append(item)
        mumble_fields = replace(mumble, {1: spec['mumble_channel_id'],
                                        2: spec['mumble_channel_name'].encode()})
        proto_channels.append(encode(replace(channel, {
            1: channel_id.encode(), 2: spec['alias'].encode(), 3: spec['number'],
            4: connection_id.encode(), 6: encode(mumble_fields)})))
    legacy['channels'] = legacy_channels
    connection = replace(connection, {1: connection_id.encode(), 2: host.encode(), 3: port})
    root = replace(root, {1: mission_id.encode(), 2: mission_name.encode(),
        3: encode(replace_repeated(channel_wrapper, 1, proto_channels)),
        4: encode(replace(connection_wrapper, {1: encode(connection)}))})
    payload = {}
    for c in contents:
        original = c.get('zipEntry')
        new_path = original.replace(old_id, mission_id)
        c.set('zipEntry', new_path)
        for p in list(c):
            if p.get('name') == 'uid':
                p.set('value', str(uuid.uuid4()))
            else:
                raise ValueError('Unexpected native Content metadata')
        payload[new_path] = encode(root) if original == proto_path else json.dumps(legacy).encode()

    for p in config:
        if p.get('name') == 'uid': p.set('value', str(uuid.uuid4()))
        elif p.get('name') == 'name':
            p.set('value', package_name or (
                'ATAK Local Voice' if vx_only else 'ATAK Local TAK and Voice Test'))
        elif p.get('name') not in ('onReceiveImport', 'onReceiveDelete', 'onReceiveAction'):
            raise ValueError('Unexpected native Configuration metadata')

    if not vx_only:
        tak = read_archive(tak_path)
        tak_manifest = ET.fromstring(tak['MANIFEST/manifest.xml'])
        allowed = {'config/servers.pref', 'cert/caCert.p12', 'cert/clientCert.p12'}
        for c in tak_manifest.findall('./Contents/Content'):
            path = c.get('zipEntry')
            if path not in allowed or path not in tak:
                raise ValueError('Unexpected TAK payload')
            contents.append(copy.deepcopy(c))
            payload[path] = tak[path]
        if not allowed.issubset(payload):
            raise ValueError('Missing TAK preference or certificate')
        prefs = ET.fromstring(payload['config/servers.pref'])
        endpoint = prefs.find("./preference[@name='cot_streams']/entry[@key='connectString0']")
        if endpoint is None or endpoint.text != f'{host}:8089:ssl':
            raise ValueError('TAK endpoint does not match the target host')
    payload['MANIFEST/manifest.xml'] = ET.tostring(manifest, encoding='utf-8', xml_declaration=True)
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + '.new')
    with ZipFile(temporary, 'w', ZIP_DEFLATED) as archive:
        for name, data in payload.items(): archive.writestr(name, data)
    read_archive(temporary)
    os.replace(temporary, output)
    digest = hashlib.sha256(output.read_bytes()).hexdigest()
    output.with_suffix('.sha256').write_text(f'{digest}  {output.name}\n', encoding='ascii')
    print(f'Created {output}\nMission: {mission_name}\nMumble: {host}:{port}\nSHA-256: {digest}')


if __name__ == '__main__':
    project = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tak-package', type=Path, default=project / 'runtime/packages/atak/atak-local-test.dpk')
    parser.add_argument('--vx-package', type=Path, required=True)
    parser.add_argument('--vx-only', action='store_true', help='Include only native Vx JSON and protobuf payloads')
    parser.add_argument('--output', type=Path)
    parser.add_argument('--host', default='takbox.local')
    parser.add_argument('--port', type=int, default=40000)
    parser.add_argument('--mission-name')
    parser.add_argument('--package-name', help='Display name in the TAK Server package list')
    parser.add_argument('--channels-file', type=Path,
                        help='JSON channel array for one Mumble endpoint; use verified server IDs')
    args = parser.parse_args()
    output = args.output or project / 'runtime/packages/atak' / (
        'atak-local-vx.dpk' if args.vx_only else 'atak-local-tak-vx.dpk')
    mission_name = args.mission_name or ('vx-local' if args.vx_only else 'a-dpk-test')
    channels = json.loads(args.channels_file.read_text(encoding='utf-8-sig')) if args.channels_file else None
    build(args.tak_package, args.vx_package, output, args.host, args.port, mission_name,
          args.vx_only, channels, args.package_name)
