// Node 18+; no dependencies. Run: node scripts/generate-public-registry.mjs
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const read=p=>fs.readFileSync(path.join(root,p),'utf8');
const write=(p,v)=>fs.writeFileSync(path.join(root,p),v);
function makePublic(master,manifest){
const byId=new Map(master.assets.map(x=>[x.id,x]));
const allowed=new Set(["/","/editions/","/blueprint/","/playbooks/","/ai-lab/","/automations/","/tools/","/partners/","/resources/","/field-notes/","/start/","/about/"]);
function safeUrl(s){if(typeof s!=="string")return false;if(/^\/(?!\/)[a-z0-9/_\-.]*$/i.test(s)&&!s.includes("..")&&!s.startsWith("/registry"))return true;const m=s.match(/^https:\/\/([a-z0-9.-]+)(?:\/[^\s]*)?$/i);if(!m)return false;const h=m[1].toLowerCase();return !/[?&](?:token|signature|x-amz-credential)=/i.test(s)&&(["www.linkedin.com","tally.so","chatgpt.com","youtu.be","www.distilledfunding.com","tools.distilledfunding.com"].includes(h)||h.endsWith(".vercel.app"))}
const project=e=>({id:e.id,title:e.title,description:e.description,kind:e.kind,routes:e.routes,label:e.label,url:e.url});
const assets=[...manifest.entries.map(e=>{const s=byId.get(e.id);if(!s)throw Error("Unknown master record "+e.id);if(!e.local&&(!s.live_url||["internal","private","restricted"].includes(s.access_level)))throw Error("Restricted or missing URL "+e.id);return project({...e,url:e.local||s.live_url})}),...manifest.supplements.map(project)];
const seen=new Set();for(const a of assets){if(seen.has(a.id)||!safeUrl(a.url)||!a.routes.every(r=>allowed.has(r)))throw Error("Invalid public record "+a.id);seen.add(a.id)}
for(const u of Object.values(manifest.publication))if(!safeUrl(u))throw Error("Invalid publication link");
return {version:manifest.version,publication:{...manifest.publication},assets};
}
function renderPage(html,route,data){
const prefix=route==="/"?"./":"../";
const esc=s=>String(s).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;");
const href=s=>esc(s.startsWith("/")?prefix+s.slice(1):s);
const ext=s=>s.startsWith("https://")?' target="_blank" rel="noopener noreferrer"':"";
const titles={"/":"READ. BUILD. EXECUTE.","/editions/":"THE EDITORIAL DESK.","/blueprint/":"BUILD WITH THE EXISTING STACK.","/playbooks/":"OPERATING PLAYBOOKS IN PRACTICE.","/ai-lab/":"OPEN THE AI TOOLKIT.","/automations/":"WORKFLOWS IN THE WILD.","/tools/":"OPEN THE TOOLBOX.","/partners/":"PARTNER INFRASTRUCTURE.","/resources/":"THE CONNECTED RESOURCE VAULT.","/field-notes/":"THE BUILD LOG.","/start/":"TAKE THE NEXT STEP.","/about/":"FOLLOW THE PUBLICATION."};
const cards=data.assets.filter(a=>a.routes.includes(route)).map(a=>`<a class="tile" href="${href(a.url)}"${ext(a.url)}><span class="tile-kicker">${esc(a.label)}</span><h3>${esc(a.title)}</h3><p>${esc(a.description)}</p><span class="tile-arrow">${a.kind==="edition"?"COMPANION ↗":"OPEN ↗"}</span></a>`).join("");
const section=`<!-- registry:begin --><section class="content-section" id="registry-catalog"><div class="section-cap"><span>THE BLUEPRINT / CONNECTED RESOURCES</span><h2>${titles[route]}</h2></div><div class="grid thirds">${cards}</div><p class="fineprint">External application availability and features may change. Educational resources are not funding offers or guaranteed outcomes.</p></section><!-- registry:end -->`;
const marker=/<!-- registry:begin -->[\s\S]*?<!-- registry:end -->/;
const placeholder={"/":"CURRENT EDITORIAL DESK.","/editions/":"THE ARCHIVE, MINUS THE FAKE ISSUES.","/tools/":"MORE UTILITIES TO CONNECT.","/resources/":"OTHER KNOWLEDGE SOURCES TO INVENTORY.","/field-notes/":"BUILD IN PUBLIC. WITHOUT PRETENDING THE BUILD IS DONE."};
let out=html;
if(marker.test(out))out=out.replace(marker,()=>section);else{const hit=[...out.matchAll(/<section class="content-section"[^>]*>[\s\S]*?<\/section>/g)].find(m=>placeholder[route]&&m[0].includes("<h2>"+placeholder[route]+"</h2>"));out=hit?out.replace(hit[0],()=>section):out.replace("</main>",`<div class="shell">${section}</div></main>`);}
const sub=`<!-- newsletter:begin --><a class="button outline" href="${href(data.publication.subscribe)}"${ext(data.publication.subscribe)}>SUBSCRIBE ON LINKEDIN ↗</a><!-- newsletter:end -->`;
const subMarker=/<!-- newsletter:begin -->[\s\S]*?<!-- newsletter:end -->/;
if(subMarker.test(out))out=out.replace(subMarker,()=>sub);else if(route==="/")out=out.replace('<div class="hero-stamp">',sub+'<div class="hero-stamp">');else out=out.replace('<div class="footer-links">','<div class="footer-links">'+sub);
return out.replaceAll("All three design studies","All six design studies");
}
const data=makePublic(JSON.parse(read('registry/blueprint-assets.master.json')),JSON.parse(read('registry/public-release.json')));
const extractConcepts=function(master){return master.assets.filter(a=>["tool","funnel","portal"].includes(a.asset_type)&&!a.live_url).map(a=>({id:a.id,title:a.title,kind:a.asset_type,status:"concept",description:"Development concept — no working application is linked yet."}));};
const renderCatalog=function(title,kicker,rows){
const e=s=>String(s??"").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;");
const cat=a=>Array.isArray(a.category)?a.category:[a.category||a.status||"Other"];
const cats=[...new Set(rows.flatMap(cat).filter(Boolean))].sort();
return `<section class="content-section" data-catalog><div class="section-cap"><span>${e(kicker)}</span><h2>${e(title)}</h2></div><div class="filter-bar"><input type="search" aria-label="Search catalog" placeholder="Search catalog…"><select aria-label="Filter category"><option value="all">All categories</option>${cats.map(c=>`<option>${e(c)}</option>`).join("")}</select></div><p data-count aria-live="polite">${rows.length} records</p><div class="grid thirds">${rows.map(a=>`<article class="tile" data-record data-category="${e(cat(a).join("|"))}"><span class="tile-kicker">${e(a.status)}</span><h3>${e(a.title)}</h3><p>${e(a.description||a.problem||"")}</p>${a.persona?`<p><strong>For:</strong> ${e(a.persona)}</p>`:""}${a.output?`<p><strong>Proposed output:</strong> ${e(a.output)}</p>`:""}${a.core_logic?`<details><summary>Concept logic</summary><p>${e(a.core_logic)}</p></details>`:""}${a.outputs?.length?`<p>Outputs: ${e(a.outputs.join(" · "))}</p>`:""}${a.url?`<a href="${e(a.url)}" target="_blank" rel="noopener noreferrer">Open GPT ↗</a>`:""}</article>`).join("")}</div></section>`;
};
const renderConcepts=data=>{const rows=JSON.parse(read('data/calculators.json'));const key=s=>String(s).toLowerCase().replace(/[^a-z0-9]/g,'').replace(/^the/,'');const names=new Set(rows.map(a=>key(a.title)));const all=[...rows,...data.toolConcepts.filter(a=>!names.has(key(a.title))).map(a=>({id:a.id,title:a.title,status:'Concept',category:a.kind,description:a.description}))];return '<!-- concepts:begin -->'+renderCatalog('THE FUNDING TOOL BUILD CATALOG.','CONCEPTS / SPECIFICATIONS',all)+'<!-- concepts:end -->';};
const patchConcepts=function(html,data){const block=renderConcepts(data),marker=/<!-- concepts:begin -->[\s\S]*?<!-- concepts:end -->/;return marker.test(html)?html.replace(marker,()=>block):html.replace("</main>",'<div class="shell">'+block+'</div></main>');};
data.toolConcepts=JSON.parse(read('registry/public-release.json')).includeToolConcepts?extractConcepts(JSON.parse(read('registry/blueprint-assets.master.json'))):[];
const output={ 'data/blueprint-public.json':JSON.stringify(data,null,2)+'\n' };
for(const r of ["/","/editions/","/blueprint/","/playbooks/","/ai-lab/","/automations/","/tools/","/partners/","/resources/","/field-notes/","/start/","/about/"]){const p=r==='/'?'index.html':r.slice(1)+'index.html';output[p]=renderPage(read(p),r,data);}
output['tools/index.html']=patchConcepts(output['tools/index.html'],data);
if(process.argv.includes('--check')){for(const [p,v] of Object.entries(output))if(read(p)!==v)throw Error('Generated file is stale: '+p);console.log('Registry is current.');}else{for(const [p,v] of Object.entries(output))write(p,v);console.log('Generated '+data.assets.length+' public records across 12 routes.');}
