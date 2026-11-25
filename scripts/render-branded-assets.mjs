import {has,opt,select,byId,exists,resolve,render,writeManifest,templates,brand,publicationId,read,done} from './creative/common.mjs';
const queued=select(['logo','template']);
for(const a of queued){
 const source=byId(a.art_id)?.output;
 if(a.method!=='logo'&&!exists(source)){console.log('Waiting for original art '+a.art_id+' → '+a.id);continue;}
 render(a,source?resolve(source):null);
}
if(has('--catalog')){
 const requested=opt('--type','all'),limit=Number(opt('--limit','10000'));
 if(!Number.isInteger(limit)||limit<0)throw Error('Invalid --limit');
 let count=0;
 for(const [file,kind,label,artId] of templates.catalogs){
  if(requested!=='all'&&kind!==requested)continue;
  if(!exists('data/'+file))continue;
  const rows=read('data/'+file);if(!Array.isArray(rows))continue;
  const source=byId(artId)?.output;
  if(!exists(source)){console.log('Waiting for catalog background '+artId+' / '+kind);continue;}
  const seen=new Set();
  for(const row of rows){
   if(kind==='edition'&&row.status!=='published')continue;
   const name=row.title||row.name||row.product_name;if(!name)continue;
   const id=String(row.id||row.slug||name).toLowerCase().replace(/[^a-z0-9]+/g,'-').replace(/^-|-$/g,'');if(!id||seen.has(id))continue;seen.add(id);
   const a={id,method:'template',title:name,headline:name,subtitle:String(row.description||row.problem||row.category||row.group||label).slice(0,180),cta:String(row.status||label).slice(0,60),theme:brand.default_theme,template:kind==='edition'?'edition-cover':'catalog-card',output:brand.catalog_root+'/'+kind+'/'+id+'.webp',width:1200,height:1200,format:'webp',transparent:false};
   if(done(a)&&!has('--force'))continue;if(count>=limit)break;
   render(a,resolve(source));count++;
  }
 }
 console.log('Rendered '+count+' catalog graphics.');
}
writeManifest();
