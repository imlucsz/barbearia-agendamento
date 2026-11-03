import http from 'node:http';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { readFile } from 'node:fs/promises';
import { stat } from 'node:fs/promises';
import { createReadStream } from 'node:fs';

const labRoot=fileURLToPath(new URL('./',import.meta.url));
const projectRoot=path.resolve(labRoot,'../../..');
const frontendRoot=path.join(projectRoot,'frontend');
const base='/frontend/e2e/motion-lab/';
const types={'.html':'text/html','.css':'text/css','.js':'text/javascript','.mjs':'text/javascript','.json':'application/json','.png':'image/png','.svg':'image/svg+xml','.gif':'image/gif','.mp3':'audio/mpeg','.webm':'video/webm','.mp4':'video/mp4','.webp':'image/webp'};
export function createLabServer() {
  return http.createServer(async(request,response)=>{
    let pathname;
    try{pathname=decodeURIComponent(new URL(request.url,'http://localhost').pathname);}catch{response.writeHead(400).end();return;}
    if(pathname==='/'){response.writeHead(302,{Location:base}).end();return;}
    let filename;
    if(pathname==='/reference')filename=path.join(projectRoot,'Temaki House Corte.html');
    else if(pathname.startsWith('/frontend/')){
      filename=path.resolve(frontendRoot,`.${pathname.slice('/frontend'.length)}`);
      const relative=path.relative(frontendRoot,filename);
      if(relative.startsWith('..')||path.isAbsolute(relative)||relative.split(path.sep).some(part=>part.startsWith('.'))){response.writeHead(403).end();return;}
      if(pathname.endsWith('/'))filename=path.join(filename,'index.html');
    }else{response.writeHead(404).end();return;}
    try{
      const extension=path.extname(filename);
      if(extension==='.webm'||extension==='.mp4'){
        const info=await stat(filename);if(!info.isFile()){response.writeHead(404).end();return;}
        const headers={'Content-Type':types[extension],'Accept-Ranges':'bytes','Cache-Control':'no-store','X-Content-Type-Options':'nosniff'};
        let start=0,end=info.size-1,status=200;
        if(request.headers.range){
          const match=/^bytes=(\d*)-(\d*)$/.exec(request.headers.range);
          if(!match||(!match[1]&&!match[2])){response.writeHead(416,{'Content-Range':`bytes */${info.size}`}).end();return;}
          if(match[1]){start=Number(match[1]);if(match[2])end=Math.min(end,Number(match[2]));}
          else{const suffix=Number(match[2]);if(suffix<=0){response.writeHead(416,{'Content-Range':`bytes */${info.size}`}).end();return;}start=Math.max(0,info.size-suffix);}
          if(!Number.isSafeInteger(start)||!Number.isSafeInteger(end)||start>end||start>=info.size){response.writeHead(416,{'Content-Range':`bytes */${info.size}`}).end();return;}
          status=206;headers['Content-Range']=`bytes ${start}-${end}/${info.size}`;
        }
        headers['Content-Length']=end-start+1;response.writeHead(status,headers);
        if(request.method==='HEAD'){response.end();return;}
        const stream=createReadStream(filename,{start,end});stream.on('error',()=>response.destroy());response.on('close',()=>stream.destroy());stream.pipe(response);return;
      }
      const data=await readFile(filename);response.writeHead(200,{'Content-Type':`${types[extension]||'application/octet-stream'}; charset=utf-8`,'Content-Length':data.length,'Cache-Control':'no-store','X-Content-Type-Options':'nosniff'}).end(request.method==='HEAD'?undefined:data);
    }catch{response.writeHead(404).end();}
  });
}
if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url)){
  const server=createLabServer();const port=Number(process.env.MOTION_LAB_PORT||4197);
  server.on('error',error=>{console.error(`Motion Lab: ${error.message}`);process.exitCode=1;});
  server.listen(port,'127.0.0.1',()=>console.log(`Motion Lab: http://127.0.0.1:${port}${base}\nComparação: http://127.0.0.1:${port}${base}compare.html`));
}
