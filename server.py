#!/usr/bin/env python3
"""THE BACKROOMS: GENESIS — local network server. Python 3.8+ standard library only.
Run:  python server.py   (port: python server.py 4000  or  PORT=4000)
Friends open  http://<IP-of-this-computer>:3000  in a browser"""
import asyncio, base64, hashlib, json, mimetypes, os, re, socket, struct, sys

PORT = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else int(os.environ.get('PORT', 3000))
MAXP = 8
GUID = '258EAFA5-E914-47DA-95CA-C5AB0DC85B11'
ROOT = os.path.dirname(os.path.abspath(__file__))
CLS = ['survivor', 'builder', 'scientist', 'speedster']
HATS = ['none', 'hardhat', 'cap', 'beanie', 'hood', 'mask', 'glasses', 'antenna']
MIME = {'.html': 'text/html; charset=utf-8', '.mp3': 'audio/mpeg', '.ogg': 'audio/ogg', '.wav': 'audio/wav',
        '.m4a': 'audio/mp4', '.flac': 'audio/flac', '.aac': 'audio/aac', '.txt': 'text/plain; charset=utf-8'}

players = {}      # id -> Player
world = None
cells = []
next_id = 1


class Player:
    def __init__(self, pid, writer):
        self.id, self.w = pid, writer
        self.n, self.c, self.s, self.joined = 'Player', 'survivor', {}, False
        self.alive = True

    def pub(self):
        return {'id': self.id, 'n': self.n, 'c': self.c, 's': self.s}


def frame(data: bytes, op=0x1):
    n = len(data)
    if n < 126:
        h = struct.pack('!BB', 0x80 | op, n)
    elif n < 65536:
        h = struct.pack('!BBH', 0x80 | op, 126, n)
    else:
        h = struct.pack('!BBQ', 0x80 | op, 127, n)
    return h + data


def send(p, obj):
    try:
        p.w.write(frame(json.dumps(obj, ensure_ascii=False).encode()))
    except Exception:
        pass


def bcast(obj, except_p=None):
    fr = frame(json.dumps(obj, ensure_ascii=False).encode())
    for p in list(players.values()):
        if p is not except_p:
            try:
                p.w.write(fr)
            except Exception:
                pass


def hexc(s):
    return s if isinstance(s, str) and re.fullmatch(r'#[0-9a-fA-F]{6}', s) else '#888888'


def clean_skin(s):
    s = s if isinstance(s, dict) else {}
    return {'body': hexc(s.get('body')), 'pants': hexc(s.get('pants')), 'tone': hexc(s.get('tone')),
            'hat': s.get('hat') if s.get('hat') in HATS else 'none'}


def clean_name(v, default):
    v = re.sub(r'[<>&]', '', str(v if v is not None else default))[:12]
    return v or default


def num(v):
    try:
        return float(v)
    except Exception:
        return 0.0


def on_msg(p, m):
    global world, cells
    if not isinstance(m, dict) or not isinstance(m.get('t'), str):
        return
    t = m['t']
    if t == 'join':
        if p.joined:
            return
        if len(players) >= MAXP:
            send(p, {'t': 'full'})
            p.w.close()
            return
        p.n = clean_name(m.get('n'), 'Player')
        p.c = m.get('c') if m.get('c') in CLS else 'survivor'
        p.s = clean_skin(m.get('s'))
        w = m.get('w')
        if world is None and isinstance(w, dict) and isinstance(w.get('genes'), dict) and isinstance(w.get('seed'), (int, float)):
            world = {'seed': w['seed'], 'genes': w['genes'], 'gen': w.get('gen') or 0}
        p.joined = True
        send(p, {'t': 'welcome', 'id': p.id, 'world': world,
                 'players': [q.pub() for q in players.values() if q is not p and q.joined], 'cells': cells})
        players[p.id] = p
        bcast({'t': 'pj', 'p': p.pub()}, p)
        print(f'+ {p.n} ({p.c}) — players: {len(players)}')
    elif not p.joined:
        return
    elif t == 's':
        bcast({'t': 's', 'id': p.id, 'l': str(m.get('l'))[:8], 'x': num(m.get('x')), 'y': num(m.get('y')),
               'a': num(m.get('a')), 'hp': num(m.get('hp')), 'cr': 1 if m.get('cr') else 0}, p)
    elif t == 'cell':
        c = [str(m.get('l'))[:8], int(num(m.get('x'))), int(num(m.get('y'))), int(num(m.get('v')))]
        if len(cells) < 40000:
            cells.append(c)
        bcast({'t': 'cell', 'l': c[0], 'x': c[1], 'y': c[2], 'v': c[3]}, p)
    elif t == 'chat':
        bcast({'t': 'chat', 'id': p.id, 'm': re.sub(r'[<>]', '', str(m.get('m') or ''))[:120]}, p)
    elif t == 'prof':
        p.n = clean_name(m.get('n'), p.n)
        if m.get('c') in CLS:
            p.c = m['c']
        p.s = clean_skin(m.get('s'))
        bcast({'t': 'prof', 'p': p.pub()}, p)


async def ws_loop(reader, writer, p):
    global world, cells
    try:
        while True:
            h = await reader.readexactly(2)
            op, masked, ln = h[0] & 15, bool(h[1] & 128), h[1] & 127
            if ln == 126:
                ln = struct.unpack('!H', await reader.readexactly(2))[0]
            elif ln == 127:
                ln = struct.unpack('!Q', await reader.readexactly(8))[0]
            if ln > 65536:
                break
            key = await reader.readexactly(4) if masked else b''
            data = await reader.readexactly(ln) if ln else b''
            if masked:
                data = bytes(b ^ key[i & 3] for i, b in enumerate(data))
            if op == 8:
                break
            if op == 9:
                writer.write(frame(data, 0xA))
            elif op == 10:
                p.alive = True
            elif op == 1:
                try:
                    on_msg(p, json.loads(data.decode('utf-8')))
                except Exception:
                    pass
    except (asyncio.IncompleteReadError, ConnectionError, OSError):
        pass
    finally:
        if players.pop(p.id, None) is not None:
            bcast({'t': 'pl', 'id': p.id})
            print(f'- {p.n} — players: {len(players)}')
        if not players:
            world = None
            cells = []
        try:
            writer.close()
        except Exception:
            pass


def http_response(status, body=b'', ctype='text/plain; charset=utf-8'):
    reason = {200: 'OK', 404: 'Not Found', 400: 'Bad Request'}.get(status, 'OK')
    head = (f'HTTP/1.1 {status} {reason}\r\nContent-Type: {ctype}\r\nContent-Length: {len(body)}\r\n'
            'Access-Control-Allow-Origin: *\r\nCache-Control: no-store\r\nConnection: close\r\n\r\n')
    return head.encode() + body


async def handle(reader, writer):
    global next_id
    try:
        raw = await asyncio.wait_for(reader.readuntil(b'\r\n\r\n'), 10)
    except Exception:
        writer.close()
        return
    lines = raw.decode('latin-1').split('\r\n')
    try:
        method, target, _ = lines[0].split(' ', 2)
    except ValueError:
        writer.close()
        return
    headers = {}
    for ln in lines[1:]:
        if ':' in ln:
            k, v = ln.split(':', 1)
            headers[k.strip().lower()] = v.strip()
    path = target.split('?', 1)[0]
    if path == '/ws' and 'websocket' in headers.get('upgrade', '').lower() and headers.get('sec-websocket-key'):
        acc = base64.b64encode(hashlib.sha1((headers['sec-websocket-key'] + GUID).encode()).digest()).decode()
        writer.write(('HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n'
                      f'Sec-WebSocket-Accept: {acc}\r\n\r\n').encode())
        await writer.drain()
        sock = writer.get_extra_info('socket')
        if sock is not None:
            try:
                sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            except Exception:
                pass
        p = Player(next_id, writer)
        next_id += 1
        await ws_loop(reader, writer, p)
        return
    # static files
    from urllib.parse import unquote
    u = unquote(path)
    f = None
    if u in ('/', '/index.html'):
        f = os.path.join(ROOT, 'index.html')
    elif u.startswith('/music/'):
        cand = os.path.normpath(os.path.join(ROOT, u.lstrip('/')))
        if cand.startswith(os.path.join(ROOT, 'music') + os.sep):
            f = cand
    if method not in ('GET', 'HEAD') or not f or not os.path.isfile(f):
        writer.write(http_response(404, b'not found'))
    else:
        with open(f, 'rb') as fh:
            body = fh.read()
        ext = os.path.splitext(f)[1].lower()
        ctype = MIME.get(ext) or mimetypes.guess_type(f)[0] or 'application/octet-stream'
        writer.write(http_response(200, body if method == 'GET' else b'', ctype) if method == 'GET'
                     else http_response(200, b'', ctype))
    try:
        await writer.drain()
    except Exception:
        pass
    writer.close()


async def pinger():
    while True:
        await asyncio.sleep(20)
        for p in list(players.values()):
            if not p.alive:
                try:
                    p.w.close()
                except Exception:
                    pass
                continue
            p.alive = False
            try:
                p.w.write(frame(b'', 0x9))
            except Exception:
                pass


def lan_ips():
    ips = set()
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('10.255.255.255', 1))
        ips.add(s.getsockname()[0])
        s.close()
    except Exception:
        pass
    try:
        for ai in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            ips.add(ai[4][0])
    except Exception:
        pass
    return sorted(i for i in ips if not i.startswith('127.'))


async def main():
    server = await asyncio.start_server(handle, '0.0.0.0', PORT)
    print('\n THE BACKROOMS: GENESIS — server started')
    print(f' Open on this computer:      http://localhost:{PORT}')
    for ip in lan_ips():
        print(f' Friends on the local network: http://{ip}:{PORT}')
    print(f'\n If it will not connect, allow Python / port {PORT} in your firewall. Stop: Ctrl+C\n')
    asyncio.ensure_future(pinger())
    async with server:
        await server.serve_forever()


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print('\nServer stopped.')
