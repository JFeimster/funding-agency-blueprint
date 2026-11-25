import fs from 'node:fs';
import path from 'node:path';
import {has,opt,select,config,brand,themes,byId,exists,resolve,raw,optimize,writeManifest} from './creative/common.mjs';
const queue=select(['ai']);
const limit=Number(opt('--limit',String(queue.length)));
if(!Number.isInteger(limit)||limit<0)throw Error('Invalid --limit');
const selected=queue.slice(0,limit);
const model=opt('--model',process.env.OPENAI_IMAGE_MODEL||config.defaults.model);
const quality=opt('--quality',config.defaults.quality);
console.log('AI queue: '+selected.length+' assets; '+model+' / '+quality);
for(const a of selected)console.log(a.id+' '+a.output+(exists(raw(a))?' [cached]':''));
if(!has('--execute')){console.log('Dry run. Add --execute to make billable API requests.');process.exit(0);}
for(const a of selected){
 if(exists(raw(a))&&!has('--force')){optimize(a,resolve(raw(a)));continue;}
 const sibling=a.output.replace(/\.webp$/i,'.png');
 if(sibling!==a.output&&exists(sibling)&&!has('--force')){optimize(a,resolve(sibling));continue;}
 if(!process.env.OPENAI_API_KEY)throw Error('OPENAI_API_KEY is required for new art. Set it locally; never commit it.');
 const ref=byId(a.reference_id)?.output;
 const reference=has('--no-reference')?null:[ref,a.reference_file,brand.reference].find(exists);
 const prompt=themes[a.theme].art_direction+'\n'+a.prompt+'\nTarget aspect ratio '+a.aspect_ratio+'. Keep essential subjects inside the central safe area for exact final crop. '+(a.transparent?'Genuine transparent background, entire object visible.':'Full bleed.');
 const size=a.width===a.height?'1024x1024':a.width>a.height?'1536x1024':'1024x1536';
 const body={model,prompt,size,quality,n:1,output_format:'png',background:a.transparent?'transparent':'opaque'};
 let request;
 if(reference){const form=new FormData();for(const [k,v] of Object.entries(body))form.append(k,String(v));const f=resolve(reference);form.append('image',new Blob([fs.readFileSync(f)],{type:/\.webp$/i.test(f)?'image/webp':/\.jpe?g$/i.test(f)?'image/jpeg':'image/png'}),path.basename(f));request={endpoint:'edits',body:form,headers:{}};}
 else request={endpoint:'generations',body:JSON.stringify(body),headers:{'Content-Type':'application/json'}};
 console.log('Generating '+a.id+' '+a.title);
 const res=await fetch('https://api.openai.com/v1/images/'+request.endpoint,{method:'POST',headers:{Authorization:'Bearer '+process.env.OPENAI_API_KEY,...request.headers},body:request.body,signal:AbortSignal.timeout(300000)});
 const data=await res.json();
 if(!res.ok||!data.data?.[0]?.b64_json)throw Error('Image request stopped: '+(data.error?.message||res.status));
 const f=resolve(raw(a));fs.mkdirSync(path.dirname(f),{recursive:true});fs.writeFileSync(f,Buffer.from(data.data[0].b64_json,'base64'));
 optimize(a,f);
 writeManifest();
}
writeManifest();
