THE BACKROOMS: GENESIS
======================
An endless, self-copying, procedurally evolving Backrooms game. Runs in a browser, single file.

START
  Single player:  double-click index.html (Chrome / Edge / Firefox).
  Multiplayer (LAN, up to 8 players):
    1. One player runs the server:  start-server.bat (Windows) / start-server.sh (Linux, macOS)
       or:  python server.py [port]      (Python 3.8+, no extra packages, default port 3000)
    2. Everyone opens the address the server prints (e.g. http://192.168.1.5:3000)
       -> MULTIPLAYER -> CONNECT -> START GAME.
    If it will not connect, allow Python / the port in your firewall.

CONTROLS
  WASD move · Shift run · mouse look · F flashlight · E action (doors, hammer on walls)
  C (hold) crouch · V VHS tape · M map · I inventory (1-8 use item) · Tab pause / DNA / codex
  ` (backtick) terminal

CLASSES (CHARACTER screen)
  Survivor  - ordinary stats.
  Builder   - starts with a hammer (24 hits), walks 1.5% slower.
  Scientist - entities near him are slower, spots noclip walls, sanity drains faster on dangerous levels.
  Speedster - 25% faster, almond water gives a speed burst, very low health.
  Avatars are customizable (name, jacket, pants, skin tone, headwear) and other players see them
  from 8 directions with a walking animation.

TERMINAL
  For everyone: /help /login <password> /logout /levels /genome /vhs /shader /say <text> /goto <name>
  Admin (after /login Backrooms): /level <id> /heal /ghost /dark /spawn <type> /tp x y /seed n /mutate /copy /reset
  In single player, admins get -/+ buttons next to the DNA bars (5% per click).

NOTES
  - Walls can only be broken with the hammer.
  - Every seed contains exactly 2 weird rooms.
  - Monsters appear only on their own levels (the bacteria: Level 0 only).
  - Cassettes and notes are in Russian on purpose.
  - Music: put files into the music/ folder and list them in const MUSIC at the start of the music
    block in index.html, or add files for the session in Pause -> MUSIC.
