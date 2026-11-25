import fs from 'node:fs';
import path from 'node:path';
import {opt,has,byId,registry,exists,done,resolve,raw,optimize,writeManifest} from './creative/common.mjs';
const id=opt('--id',null),file=opt('--file',null);
if(file&&!id)throw Error('--file requires --id');
if(id&&!byId(id))throw Error('Unknown ID');
for(const a of id?[byId(id)]:registry){
 if(done(a)&&!has('--force'))continue;
 const source=file?path.resolve(file):[raw(a),a.output.replace(/\.webp$/i,'.png')].filter(x=>x!==a.output).find(exists);
 if(!source)continue;
 optimize(a,file?source:resolve(source));
}
writeManifest();
