/* THE BACKROOMS: ГЕНЕЗИС — сервер локальной сети. Без зависимостей. Нужен Node.js 14+.
   Запуск:  node server.js   (порт можно сменить: PORT=4000 node server.js)
   Друзья открывают в браузере  http://<IP-этого-компьютера>:3000 */
const http=require('http'),fs=require('fs'),path=require('path'),crypto=require('crypto'),os=require('os');
const PORT=+process.env.PORT||3000,MAXP=8,GUID='258EAFA5-E914-47DA-95CA-C5AB0DC85B11';
const CLS=['survivor','builder','scientist','speedster'];
const MIME={'.html':'text/html; charset=utf-8','.mp3':'audio/mpeg','.ogg':'audio/ogg','.wav':'audio/wav','.m4a':'audio/mp4','.flac':'audio/flac','.aac':'audio/aac','.txt':'text/plain; charset=utf-8'};
const players=new Map();let world=null,cells=[],nid=1;
const server=http.createServer((req,res)=>{
  const u=decodeURIComponent((req.url||'/').split('?')[0]);
  res.setHeader('Access-Control-Allow-Origin','*');
  let f=null;
  if(u==='/'||u==='/index.html')f=path.join(__dirname,'index.html');
  else if(u.startsWith('/music/')){const p=path.normalize(path.join(__dirname,u));if(p.startsWith(path.join(__dirname,'music')))f=p;}
  if(!f||!fs.existsSync(f)||fs.statSync(f).isDirectory()){res.writeHead(404);res.end('not found');return;}
  res.writeHead(200,{'Content-Type':MIME[path.extname(f).toLowerCase()]||'application/octet-stream','Cache-Control':'no-store'});
  fs.createReadStream(f).pipe(res);
});
function frame(str){const b=Buffer.from(str),l=b.length;let h;
  if(l<126)h=Buffer.from([0x81,l]);else if(l<65536){h=Buffer.alloc(4);h[0]=0x81;h[1]=126;h.writeUInt16BE(l,2);}else{h=Buffer.alloc(10);h[0]=0x81;h[1]=127;h.writeUInt32BE(0,2);h.writeUInt32BE(l,6);}
  return Buffer.concat([h,b]);}
function send(p,o){if(p.socket.destroyed)return;try{p.socket.write(frame(JSON.stringify(o)));}catch(e){}}
function bcast(o,except){const f=frame(JSON.stringify(o));for(const p of players.values())if(p!==except&&!p.socket.destroyed)try{p.socket.write(f);}catch(e){}}
const hex=s=>typeof s==='string'&&/^#[0-9a-fA-F]{6}$/.test(s)?s:'#888888';
function cleanSkin(s){s=s||{};return{body:hex(s.body),pants:hex(s.pants),tone:hex(s.tone),hat:['none','hardhat','cap','beanie','hood','mask','glasses','antenna'].includes(s.hat)?s.hat:'none'};}
const pub=p=>({id:p.id,n:p.n,c:p.c,s:p.s});
function onMsg(p,m){
  if(!m||typeof m.t!=='string')return;
  if(m.t==='join'){
    if(p.joined)return;
    if(players.size>=MAXP){send(p,{t:'full'});p.socket.destroy();return;}
    p.n=String(m.n||'Игрок').replace(/[<>&]/g,'').slice(0,12)||'Игрок';p.c=CLS.includes(m.c)?m.c:'survivor';p.s=cleanSkin(m.s);
    if(!world&&m.w&&m.w.genes&&typeof m.w.seed==='number')world={seed:m.w.seed,genes:m.w.genes,gen:+m.w.gen||0};
    p.joined=true;
    send(p,{t:'welcome',id:p.id,world,players:[...players.values()].filter(q=>q!==p&&q.joined).map(pub),cells});
    players.set(p.id,p);bcast({t:'pj',p:pub(p)},p);
    console.log('+ '+p.n+' ('+p.c+') — игроков: '+players.size);
  }else if(!p.joined)return;
  else if(m.t==='s'){bcast({t:'s',id:p.id,l:String(m.l).slice(0,8),x:+m.x||0,y:+m.y||0,a:+m.a||0,hp:+m.hp||0,cr:m.cr?1:0},p);}
  else if(m.t==='cell'){const c=[String(m.l).slice(0,8),m.x|0,m.y|0,m.v|0];if(cells.length<40000)cells.push(c);bcast({t:'cell',l:c[0],x:c[1],y:c[2],v:c[3]},p);}
  else if(m.t==='chat'){bcast({t:'chat',id:p.id,m:String(m.m||'').replace(/[<>]/g,'').slice(0,120)},p);}
  else if(m.t==='prof'){p.n=String(m.n||p.n).replace(/[<>&]/g,'').slice(0,12);p.c=CLS.includes(m.c)?m.c:p.c;p.s=cleanSkin(m.s);bcast({t:'prof',p:pub(p)},p);}
}
server.on('upgrade',(req,socket)=>{
  const key=req.headers['sec-websocket-key'];
  if(!key||(req.url||'').split('?')[0]!=='/ws'){socket.destroy();return;}
  const acc=crypto.createHash('sha1').update(key+GUID).digest('base64');
  socket.write('HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Accept: '+acc+'\r\n\r\n');
  socket.setNoDelay(true);
  const p={id:nid++,socket,buf:Buffer.alloc(0),joined:false,alive:true};
  socket.on('data',d=>{
    p.buf=Buffer.concat([p.buf,d]);
    for(;;){
      const b=p.buf;if(b.length<2)return;
      const op=b[0]&15,masked=!!(b[1]&128);let len=b[1]&127,off=2;
      if(len===126){if(b.length<4)return;len=b.readUInt16BE(2);off=4;}
      else if(len===127){if(b.length<10)return;len=b.readUInt32BE(6);off=10;}
      if(len>65536){socket.destroy();return;}
      const need=off+(masked?4:0)+len;if(b.length<need)return;
      let payload=b.slice(off+(masked?4:0),need);
      if(masked){const k=b.slice(off,off+4);payload=Buffer.from(payload);for(let i=0;i<payload.length;i++)payload[i]^=k[i&3];}
      p.buf=b.slice(need);
      if(op===8){socket.end();return;}
      if(op===9){const pg=Buffer.concat([Buffer.from([0x8a,payload.length]),payload]);try{socket.write(pg);}catch(e){}continue;}
      if(op===10){p.alive=true;continue;}
      if(op===1){let m=null;try{m=JSON.parse(payload.toString('utf8'));}catch(e){}onMsg(p,m);}
    }
  });
  const gone=()=>{
    if(!players.has(p.id)&&!p.joined)return;
    if(players.delete(p.id)){bcast({t:'pl',id:p.id});console.log('- '+(p.n||'?')+' — игроков: '+players.size);}
    if(!players.size){world=null;cells=[];}
  };
  socket.on('close',gone);socket.on('error',()=>{try{socket.destroy();}catch(e){}});
});
setInterval(()=>{for(const p of players.values()){if(!p.alive){p.socket.destroy();continue;}p.alive=false;try{p.socket.write(Buffer.from([0x89,0]));}catch(e){}}},20000);
server.listen(PORT,'0.0.0.0',()=>{
  console.log('\n THE BACKROOMS: ГЕНЕЗИС — сервер запущен\n Открой на этом компьютере:  http://localhost:'+PORT);
  const ifs=os.networkInterfaces();for(const n in ifs)for(const i of ifs[n])if(i.family==='IPv4'&&!i.internal)console.log(' Друзьям в локальной сети:    http://'+i.address+':'+PORT);
  console.log('\n Если не подключается — разреши Node.js / порт '+PORT+' в брандмауэре.\n');
});
