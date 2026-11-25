import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {spawnSync} from 'node:child_process';
export const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../..');
export const args=process.argv.slice(2);
export const has=k=>args.includes(k);
export function opt(k,d){const i=args.indexOf(k);if(i<0)return d;if(!args[i+1]||args[i+1].startsWith('--'))throw Error('Missing value for '+k);return args[i+1];}
export function resolve(p){const f=path.resolve(root,p);if(f!==root&&!f.startsWith(root+path.sep))throw Error('Path outside repository: '+p);return f;}
export const read=p=>JSON.parse(fs.readFileSync(resolve(p),'utf8').replace(/^\uFEFF/,''));
export const config=read('data/creative-publications.json');
export const publicationId=opt('--publication','fab');
export const brand=config.publications[publicationId];
if(!brand)throw Error('Unknown publication '+publicationId);
export const registry=read(brand.registry).entries;
export const themes=read('data/image-design-themes.json').themes;
export const templates=read('data/image-templates.json');
export const byId=id=>registry.find(a=>a.id===String(id).padStart(2,'0'));
export const exists=p=>!!p&&fs.existsSync(resolve(p));
export const output=a=>{if(!a.output.startsWith(brand.output_root+'/'))throw Error('Output outside publication asset root');return resolve(a.output);};
export const done=a=>fs.existsSync(output(a));
export const raw=a=>'.creative-cache/'+publicationId+'/'+a.id+'.png';
export function select(methods){const id=opt('--id',null);const rows=id?[byId(id)]:registry;if(rows.some(a=>!a))throw Error('Unknown asset ID');return rows.filter(a=>methods.includes(a.method)).filter(a=>has('--force')||!done(a));}
export function python(action,payload){const p=spawnSync(process.env.CREATIVE_PYTHON||'python',[resolve('scripts/creative/render.py'),action],{input:JSON.stringify(payload),encoding:'utf8',maxBuffer:4*1024*1024});if(p.error||p.status!==0)throw Error(p.error?.message||p.stderr||'Python renderer failed');if(p.stdout.trim())console.log(p.stdout.trim());}
export function optimize(a,source){python('optimize',{source,dest:output(a),width:a.width,height:a.height,format:a.format,transparent:a.transparent,quality:config.defaults.webp_quality,force:has('--force')});}
export function writeManifest(){const rows=registry.filter(done).map(a=>({id:a.id,title:a.title,src:a.output,alt:a.alt,route:a.route,aspect_ratio:a.aspect_ratio,width:a.width,height:a.height,collection:a.collection}));const f=resolve(brand.manifest);fs.mkdirSync(path.dirname(f),{recursive:true});fs.writeFileSync(f,JSON.stringify({publication:publicationId,assets:rows},null,2)+'\n');console.log(rows.length+' completed registry assets in '+brand.manifest);}
export function render(a,source){const theme=themes[a.theme||brand.default_theme];const layout=templates.layouts[a.template||'catalog-card'];if(!theme||!layout)throw Error('Unknown theme/layout');python(a.method==='logo'?'logo':'poster',{...a,source:source||null,dest:output(a),palette:theme.palette,layout,brand,quality:config.defaults.webp_quality,force:has('--force')});}
