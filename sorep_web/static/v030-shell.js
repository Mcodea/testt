"use strict";
/* OGIAS 0.30 — couche de présentation uniquement ; le moteur et les API restent inchangés.
   Icônes SVG cohérentes construites à partir de tracés simples, en local, sans police distante. */
const V30 = (() => {
 const paths={
  home:'<path d="m3 10 9-7 9 7v10a1 1 0 0 1-1 1h-5v-7H9v7H4a1 1 0 0 1-1-1z"/>',
  grid:'<rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/>',
  layers:'<path d="m12 2 9 5-9 5-9-5zM3 12l9 5 9-5M3 17l9 5 9-5"/>',
  file:'<path d="M6 2h8l6 6v13H6a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2zM14 2v6h6"/>',
  folder:'<path d="M3 7V5a2 2 0 0 1 2-2h5l2 3h7a2 2 0 0 1 2 2v11H3z"/>',
  plus:'<path d="M12 5v14M5 12h14"/>',
  pencil:'<path d="m3 17-1 5 5-1L20 8a3 3 0 0 0-4-4zM14 6l4 4"/>',
  copy:'<rect x="8" y="8" width="13" height="13" rx="2"/><path d="M16 8V5a2 2 0 0 0-2-2H5a2 2 0 0 0-2 2v9a2 2 0 0 0 2 2h3"/>',
  trash:'<path d="M3 6h18M8 6V4h8v2M6 6l1 15h10l1-15M10 10v7M14 10v7"/>',
  download:'<path d="M12 3v13m-5-5 5 5 5-5M4 18v3h16v-3"/>',
  upload:'<path d="M12 17V4m-5 5 5-5 5 5M4 17v4h16v-4"/>',
  check:'<path d="M20 6 9 17l-5-5"/>',
  shield:'<path d="m12 2 9 4v7c0 5-4 8-9 10-5-2-9-5-9-10V6zM8 12l3 3 5-5"/>',
  alert:'<path d="m12 3 10 18H2L12 3zm0 7v4m0 4h.01"/>',
  info:'<circle cx="12" cy="12" r="10"/><path d="M12 11v6m0-10h.01"/>',
  bell:'<path d="M18 8a6 6 0 0 0-12 0c0 7-3 8-3 9h18c0-1-3-2-3-9M10 21h4"/>',
  help:'<circle cx="12" cy="12" r="10"/><path d="M9 9a3 3 0 0 1 6 0c0 2-3 2-3 5m0 3h.01"/>',
  search:'<circle cx="10" cy="10" r="7"/><path d="m15 15 6 6"/>',
  settings:'<circle cx="12" cy="12" r="3"/><path d="m9 2 1 3h4l1-3 3 2-1 3 2 3 3 1v3l-3 1-2 3 1 3-3 2-1-3h-4l-1 3-3-2 1-3-2-3-3-1v-3l3-1 2-3-1-3z"/>',
  database:'<ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M3 5v14c0 4 18 4 18 0V5M3 12c0 4 18 4 18 0"/>',
  monitor:'<rect x="2" y="3" width="20" height="15" rx="2"/><path d="M8 22h8m-4-4v4"/>',
  cpu:'<rect x="5" y="5" width="14" height="14" rx="2"/><path d="M9 9h6v6H9zM9 1v4m6-4v4M9 19v4m6-4v4M1 9h4m-4 6h4m14-6h4m-4 6h4"/>',
  network:'<rect x="9" y="2" width="6" height="6" rx="1"/><rect x="2" y="16" width="6" height="6" rx="1"/><rect x="16" y="16" width="6" height="6" rx="1"/><path d="M12 8v4M5 16v-4h14v4"/>',
  sliders:'<path d="M3 6h18M3 12h18M3 18h18"/><circle cx="8" cy="6" r="2" fill="var(--card)"/><circle cx="16" cy="12" r="2" fill="var(--card)"/><circle cx="10" cy="18" r="2" fill="var(--card)"/>',
  table:'<rect x="2" y="3" width="20" height="18" rx="2"/><path d="M2 9h20M9 9v12M16 9v12"/>',
  history:'<path d="M3 12a9 9 0 1 1 3 7M3 4v6h6M12 7v6l4 2"/>',
  compare:'<path d="M4 7h16m-6-4 6 4-6 4M20 17H4m6-4-6 4 6 4"/>',
  book:'<path d="M3 4h8a4 4 0 0 1 4 4v13H7a4 4 0 0 0-4 1zM21 4h-3a4 4 0 0 0-4 4"/>',
  pin:'<path d="M12 22s8-8 8-13a8 8 0 0 0-16 0c0 5 8 13 8 13z"/><circle cx="12" cy="9" r="3"/>',
  chevronDown:'<path d="m6 9 6 6 6-6"/>',chevronRight:'<path d="m9 6 6 6-6 6"/>',
  chevronLeft:'<path d="m15 6-6 6 6 6"/>',close:'<path d="M5 5l14 14M19 5 5 19"/>',
  moon:'<path d="M21 12.6A9 9 0 0 1 11.4 3 9 9 0 1 0 21 12.6Z"/>',
  sun:'<circle cx="12" cy="12" r="4"/><path d="M12 2v2m0 16v2M4 4l2 2m12 12 2 2M2 12h2m16 0h2M4 20l2-2M18 6l2-2"/>',
  wand:'<path d="m4 20 14-14M14 3l1-2 1 2 2 1-2 1-1 2-1-2-2-1zM3 10l1-2 1 2 2 1-2 1-1 2-1-2-2-1z"/>',
  arrow:'<path d="M3 12h18m-7-7 7 7-7 7"/>',
  list:'<path d="M9 6h13M9 12h13M9 18h13M3 6h.01M3 12h.01M3 18h.01"/>',
  printer:'<path d="M6 9V2h12v7M6 18H3V9h18v9h-3M6 15h12v7H6z"/>',
  bars:'<path d="M3 21V10h4v11M10 21V3h4v18M17 21v-7h4v7"/>',
  maximize:'<path d="M8 3H3v5M16 3h5v5M3 16v5h5M21 16v5h-5"/>',
  eye:'<path d="M2 12s4-7 10-7 10 7 10 7-4 7-10 7-10-7-10-7z"/><circle cx="12" cy="12" r="3"/>',
  lock:'<rect x="5" y="10" width="14" height="11" rx="2"/><path d="M8 10V7a4 4 0 0 1 8 0v3"/>',
  link:'<path d="M10 13a5 5 0 0 0 8 0l2-2a5 5 0 0 0-7-7l-2 2M14 11a5 5 0 0 0-8 0l-2 2a5 5 0 0 0 7 7l2-2"/>'
 };
 const icon=(name,size=22)=>`<svg class="v30-icon" aria-hidden="true" width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">${paths[name]||paths.grid}</svg>`;
 const esc2=x=>String(x??'').replace(/[&<>"']/g,ch=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
 const stage=[['#/inventaire','Équipements'],['#/es','Liste des E/S'],['#/materiel','Matériel'],['#/variables','Variables'],['#/recette','Recette']];
 const contexts=['Accueil','Ouvrage','Équipements','Automatisme','Versionning','Affichage'];
 const mode=()=>document.documentElement.dataset.theme||'light';
 const state={ribbon:'',inspectorOpen:true,treeOpen:true,refreshQueued:false,tabTrail:[],name:'',lastView:''};
 function setTheme(v){document.documentElement.dataset.theme=v;try{localStorage.setItem('ogias-ui-theme',v);}catch(e){} schedule();}
 try{const t=localStorage.getItem('ogias-ui-theme');if(t==='dark')document.documentElement.dataset.theme='dark';}catch(e){}
 function routeOf(v){return v==='accueil'?'#/ouvrages':v==='ouvrage'?'#/inventaire':v==='referentiel'?'#/referentiel':['supervision','adressage'].includes(v)?'#/variables':'#/'+v;}
 function createSpec(iconName,label,id,group,reason){return {iconName,label,id,group,reason};}
 function specs(E){
   const r=E.vue, o=E.ouvrage||{}, creation=r==='ouvrage'&&o.en_conception;
   let a=[];
   if(r==='accueil')return [createSpec('database','Référentiel','route:#/referentiel','Ressources')];
   if(creation)return [createSpec('home','Mes ouvrages','route:#/ouvrages','Navigation'),createSpec('database','Référentiel','route:#/referentiel','Ressources')];
   if(r==='ouvrage')a=[createSpec('plus','Ajouter un équipement','b-eq','Inventaire'),createSpec('folder','Nouvelle UF','b-uf','Inventaire'),createSpec('upload','Importer','b-import','Échanges'),createSpec('pencil','Modifier la fiche','e-mod','Équipement'),createSpec('check','Valider','e-val','Équipement'),createSpec('trash','Supprimer','e-sup','Équipement')];
   else if(r==='es')a=[createSpec('check','Valider la sélection','x-val','Validation'),createSpec('shield','Valider les affichées','x-val-tout','Validation'),createSpec('download','Exporter Excel','es-export','Échanges')];
   else if(r==='materiel')a=[createSpec('cpu','Calculer le matériel','m-calc','Architecture'),createSpec('grid','Ajuster les cartes','m-cartes','Architecture'),createSpec('wand','Implanter les voies','m-impl','Affectation'),createSpec('check','Valider le matériel','m-valider','Validation'),createSpec('shield','Valider les voies','x-val-tout','Validation'),createSpec('download','Liste E/S','x-xl','Livrables'),createSpec('download','Export XSY','x-xsy','Livrables'),createSpec('file','Export TXT','x-txt','Livrables')];
   else if(r==='variables'||r==='supervision')a=[createSpec('wand','Aperçu adressage','v29-apercu','Adressage'),createSpec('shield','Contrôler','v29-controle','Validation'),createSpec('download','Exporter','v29-export','Échanges')];
   else if(r==='adressage')a=[createSpec('wand','Recalculer l’aperçu','ad-recalc','Adressage'),createSpec('check','Appliquer le plan','ad-app','Adressage'),createSpec('shield','Valider les affectations','ad-val','Validation'),createSpec('download','Export TOPKAPI','ad-tpk','Échanges')];
   else if(r==='recette')a=[createSpec('shield','Actualiser les contrôles','r-actualiser','Contrôles'),createSpec('cpu','Consulter le matériel','route:#/materiel','Livrables'),createSpec('database','Référentiel','route:#/referentiel','Traçabilité')];
   else if(r==='referentiel'){
     // Le référentiel dispose de trois écrans exclusifs. N'afficher que les
     // commandes appartenant au véritable écran métier actif.
     if(E.refEcran==='publication')a=[createSpec('check','Valider le brouillon','rf-valider','Cycle de vie'),createSpec('layers','Publier','rf-publier','Cycle de vie'),createSpec('chevronLeft','Retour au brouillon','rf-retour','Navigation')];
     else if(E.refEcran==='historique')a=[createSpec('chevronLeft','Retour au référentiel','rf-retour','Navigation')];
     else if(E.ref?.source==='brouillon')a=[createSpec('eye','Voir la révision publiée','rf-voir-pub','Référentiel'),createSpec('upload','Importer Excel','rf-imp','Échanges'),createSpec('download','Exporter le brouillon','rf-exp-b','Échanges'),createSpec('compare','Contrôler / comparer','rf-pub','Cycle de vie'),createSpec('trash','Supprimer le brouillon','rf-abandon','Cycle de vie')];
     else a=[createSpec('pencil',E.cycle?.brouillon?'Reprendre le brouillon':'Nouveau brouillon',E.cycle?.brouillon?'rf-ouvrir-b':'rf-creer','Édition'),createSpec('download','Exporter Excel','rf-exp','Échanges'),createSpec('history','Historique','rf-hist','Traçabilité')];
   }
   return a;
 }
 function activeRibbon(E){return ['variables','supervision','adressage','es','materiel','recette'].includes(E.vue)?'Automatisme':E.vue==='referentiel'?'Versionning':E.vue==='ouvrage'&&!E.ouvrage?.en_conception?'Équipements':E.vue==='ouvrage'?'Ouvrage':'Accueil';}
 function commandHTML(s){const internal=['route:','new:','theme:','panel:','tree:'].some(p=>s.id.startsWith(p));const target=internal?null:document.getElementById(s.id);const disabled=target?!!target.disabled:!internal;
  // Garder l'action visible, mais inactive si le moteur interdit son utilisation.
  // La justification apparaît dans l'infobulle, sans créer de faux bouton actif.
  return `<button type="button" class="v30-command" data-shell-action="${esc2(s.id)}" title="${esc2(disabled?(target?.title||s.reason||'Action non disponible à cette étape'):(target?.title||s.label))}" ${disabled?'disabled aria-disabled="true"':''}>${icon(s.iconName,26)}<span>${esc2(s.label)}</span></button>`;}
 function renderRibbon(E){
  const tab=state.ribbon||activeRibbon(E);
  document.getElementById('v30-ribbon-tabs').innerHTML=contexts.map(x=>`<button type="button" class="v30-ribbon-tab ${tab===x?'active':''}" data-shell-tab="${esc2(x)}" aria-pressed="${tab===x}">${esc2(x)}</button>`).join('');
  let arr=specs(E);
  if(tab==='Affichage')arr=[createSpec('moon',mode()==='light'?'Mode sombre':'Mode clair','theme:toggle','Personnalisation'),createSpec('maximize','Replier le panneau','panel:toggle','Disposition'),createSpec('layers','Replier l’arbre','tree:toggle','Disposition')];
  else if(tab==='Versionning'&&E.vue!=='referentiel')arr=[createSpec('database','Ouvrir le référentiel','route:#/referentiel','Référentiel'),createSpec('history','Historique du référentiel','route:#/referentiel','Historique')];
  else if(tab==='Accueil'&&E.vue!=='accueil')arr=[createSpec('home','Mes ouvrages','route:#/ouvrages','Accueil'),createSpec('plus','Nouvel ouvrage','new:Neuf','Création')];
  else if(tab==='Équipements'&&E.vue!=='ouvrage')arr=[createSpec('folder','Inventaire','route:#/inventaire','Navigation'),...arr.filter(x=>x.id.startsWith('route:'))];
  else if(tab==='Ouvrage'&&E.vue!=='ouvrage')arr=[createSpec('file','Identification','route:#/inventaire','Ouvrage')];
  else if(tab==='Automatisme'&&!['es','materiel','variables','supervision','adressage','recette'].includes(E.vue))arr=[createSpec('table','Liste des E/S','route:#/es','Équipements'),createSpec('cpu','Matériel','route:#/materiel','Automatisme'),createSpec('database','Variables','route:#/variables','Automatisme')];
  const groups=new Map();for(const v of arr){const html=commandHTML(v);if(html)groups.set(v.group,(groups.get(v.group)||'')+html);}
  const el=document.getElementById('v30-ribbon-actions');el.innerHTML=[...groups].map(([name,html])=>`<div class="v30-ribbon-group"><div class="v30-ribbon-buttons">${html}</div><span class="v30-group-label">${esc2(name)}</span></div>`).join('')||`<div class="v30-ribbon-empty">${icon('info',20)} Sélectionnez un élément pour afficher ses commandes.</div>`;
 }
 function runAction(id,E){
  if(id.startsWith('route:'))return naviguer(id.slice(6));
  if(id.startsWith('new:'))return api('/api/nouveau',{mode:id.slice(4)}).then(()=>{E.ficheDraft=null;E.ficheDirty=false;allerOuvrage({nature:'ouvrage',valeur:''});}).catch(e=>toast(e.message,true));
  if(id==='theme:toggle')return setTheme(mode()==='light'?'dark':'light');
  if(id==='panel:toggle'){state.inspectorOpen=!state.inspectorOpen;schedule();return;}
  if(id==='tree:toggle'){state.treeOpen=!state.treeOpen;schedule();return;}
  const btn=document.getElementById(id);if(btn&&!btn.disabled)btn.click();
 }
 function tabHTML(E){const arr=[{route:'#/ouvrages',label:'Accueil',iconName:'home',close:false}];const open=E.ouvrage?.ouvert&&E.ouvrage?.prefixe;
  if(open)arr.push({route:'#/inventaire',label:E.ouvrage.prefixe,iconName:'file',close:true});
  if(E.vue==='referentiel'||state.tabTrail.includes('#/referentiel'))arr.push({route:'#/referentiel',label:'Référentiel métier',iconName:'database',close:true});
  if(!arr.some(x=>x.route===routeOf(E.vue))&&open&&E.vue!=='ouvrage')arr.push({route:routeOf(E.vue),label:stage.find(x=>x[0]===routeOf(E.vue))?.[1]||'Variables',iconName:'table',close:true});
  return arr.map(x=>`<div class="v30-doc ${routeOf(E.vue)===x.route?'current':''}"><button type="button" data-shell-route="${esc2(x.route)}" title="${esc2(x.label)}">${icon(x.iconName,17)}<span>${esc2(x.label)}</span></button>${x.close?`<button class="v30-close-tab" data-close-tab="${esc2(x.route)}" title="Fermer cet onglet" aria-label="Fermer ${esc2(x.label)}">${icon('close',14)}</button>`:''}</div>`).join('');}
 function stats(E){const o=E.ouvrage||{};if(E.vue==='referentiel')return [{label:'Types',value:E.cycle?.compteurs?.types??0,style:'neutral'},{label:'Signaux',value:E.cycle?.compteurs?.signaux??0,style:'neutral'},{label:'Règles',value:E.cycle?.compteurs?.regles??0,style:'neutral'},{label:'Modèles',value:E.cycle?.compteurs?.modeles??0,style:'neutral'}];return [
  {label:'Équipements',value:o.equipements?.length??0,style:'neutral'},
  {label:'À valider',value:o.equipements?.filter(x=>!x.valide).length??0,style:'warn'},
  ...(E.vue==='es'&&E.es?[{label:'Points physiques',value:E.es.points?.length??0,style:'neutral'},{label:'E/S non validées',value:E.es.points?.filter(x=>!x.contenu_valide).length??0,style:'warn'}]:[]),
  ...(E.vue==='materiel'&&E.mat?[{label:'Cartes installées',value:E.mat.modules?.length??0,style:'neutral'}]:[]),
  ...(['variables','supervision'].includes(E.vue)&&E.detailEtape?[{label:'Informations',value:E.detailEtape.lignes?.length??0,style:'neutral'}]:[]),
  ...(E.vue==='recette'&&E.detailEtape?[{label:'Erreurs',value:E.detailEtape.erreurs??0,style:'danger'},{label:'Alertes',value:E.detailEtape.alertes??0,style:'warn'}]:[])
 ];}
 function issues(E){const out=[];
  if(E.vue==='es'){(E.es?.points||[]).filter(x=>!x.contenu_valide).slice(0,4).forEach(x=>out.push({msg:(x.pcf||'')+' · '+(x.cle||'')+' à valider',route:'#/es',color:'warn'}));}
  else if(E.vue==='ouvrage'){(E.ouvrage?.equipements||[]).filter(x=>!x.valide).slice(0,4).forEach(x=>out.push({msg:x.pcf+' · équipement à valider',ident:x.ident,route:'#/inventaire',color:'warn'}));}
  else if(E.vue==='recette'){(E.detailEtape?.controles||[]).slice(0,5).forEach(x=>out.push({msg:x.message,ident:x.ident,route:'#/recette',color:x.niveau==='Erreur'?'danger':'warn'}));}
  else if(E.vue==='referentiel'){(E.cycle?.controles?.erreurs||[]).slice(0,3).forEach(x=>out.push({msg:x,route:'#/referentiel',color:'danger'}));(E.cycle?.controles?.alertes||[]).slice(0,2).forEach(x=>out.push({msg:x,route:'#/referentiel',color:'warn'}));}
  return out;}
 function timeline(E,etatEtape,vueEtape){return stage.map(([route,label],i)=>{const mapping=['ouvrage','es','materiel','variables','recette'][i];const stat=etatEtape(mapping,E.ouvrage||{});const current=vueEtape(E.vue)===mapping;return `<button type="button" class="v30-step ${current?'active':''} ${stat==='validée'?'done':''}" data-shell-route="${route}" title="${label} : ${stat}"><span class="v30-step-circle">${stat==='validée'?icon('check',15):i+1}</span><span>${esc2(label)}</span></button>`;}).join('');}
 function heading(E,etatEtape,vueEtape){const n=document.getElementById('v30-work-heading'),o=E.ouvrage||{};
  if(E.vue==='accueil'||E.vue==='ouvrage'&&o.en_conception){n.hidden=true;return;}
  n.hidden=false;
  if(E.vue==='referentiel'){
   const published=E.cycle?.revision??0, draft=!!E.cycle?.brouillon, source=E.ref?.source||'publié';
   n.innerHTML=`<div class="v30-head-line"><div class="v30-tile">${icon('database',22)}</div><div class="v30-head-text"><div class="v30-kicker">BIBLIOTHÈQUE D'INGÉNIERIE</div><h1>Référentiel métier</h1></div><span class="v30-badge ${draft?'warn':'success'}">${draft?'Brouillon actif':'Référentiel publié'}</span><span class="v30-revision">R${String(published).padStart(4,'0')}</span></div>
   <div class="v30-lifecycle"><span class="${draft?'active':''}">${icon('file',16)} Brouillon</span>${icon('arrow',15)}<span>${icon('shield',16)} Prêt à publier</span>${icon('arrow',15)}<span class="${!draft?'active':''}">${icon('check',16)} Publié</span></div>`;
  }else{let title=E.vue==='ouvrage'?'Équipements':E.vue==='es'?'Liste des E/S':E.vue==='materiel'?'Matériel et architecture':['variables','supervision','adressage'].includes(E.vue)?'Variables et adressage':'Recette et livrables';
   n.innerHTML=`<div class="v30-head-line"><div class="v30-tile">${icon(E.vue==='materiel'?'cpu':E.vue==='es'?'table':E.vue==='recette'?'shield':'layers',22)}</div><div class="v30-head-text"><div class="v30-kicker">OUVRAGE · ${esc2(o.prefixe||'Non enregistré')}</div><h1>${esc2(title)}</h1></div><span class="v30-badge neutral">${esc2(o.identification?.mode||'Projet')}</span></div><div class="v30-stepper">${timeline(E,etatEtape,vueEtape)}</div>`;
  }
 }
 function tree(E){const el=document.getElementById('v30-tree');// Le référentiel utilise sa véritable arborescence (nœuds et écouteurs existants),
 // déplacée dans la zone commune à gauche pour ne pas dupliquer les contrôles.
 if(E.vue==='referentiel'){
  const source=document.querySelector('#vue .ref-types') || el.querySelector('.ref-types');
  const usable=!!source && !['publication','historique'].includes(E.refEcran);
  el.hidden=!usable||!state.treeOpen;
  if(usable){
   if(source.parentNode!==el){el.replaceChildren(source);}
   el.setAttribute('aria-label','Types et modèles du référentiel');
   el.classList.add('v30-reference-tree');
  }
  return;
 }
 el.classList.remove('v30-reference-tree');
 const has=E.ouvrage?.ouvert && !E.ouvrage?.en_conception && !['accueil','ouvrage'].includes(E.vue);
 el.hidden=!has||!state.treeOpen;if(!has)return;const o=E.ouvrage;
 const units=o.unites||[];const nodes=units.map(u=>{const elems=(o.equipements||[]).filter(x=>x.uf===u.code);return `<div class="v30-tree-group"><button type="button" class="v30-tree-unit" data-shell-uf="${esc2(u.code)}">${icon('folder',16)} ${esc2(u.code)} · ${esc2(u.libelle||'UF')}<span>${elems.length}</span></button>${elems.map(x=>`<button type="button" class="v30-tree-equip" data-shell-equip="${esc2(x.ident)}" title="${esc2(x.pcf+' '+(x.libelle||''))}"><i class="v30-status-dot ${x.valide?'success':'warn'}"></i><span class="v30-mono">${esc2(x.pcf?.slice(-4)||x.ident)}</span><span class="v30-tree-name">${esc2(x.libelle||x.designation||'')}</span></button>`).join('')}</div>`;}).join('');
 const unassigned=(o.equipements||[]).filter(x=>!units.some(u=>u.code===x.uf));
 const common=unassigned.length?`<div class="v30-tree-group"><div class="v30-tree-unit">${icon('folder',16)} Équipements hors UF <span>${unassigned.length}</span></div>${unassigned.map(x=>`<button type="button" class="v30-tree-equip" data-shell-equip="${esc2(x.ident)}" title="${esc2(x.pcf+' '+(x.libelle||''))}"><i class="v30-status-dot ${x.valide?'success':'warn'}"></i><span class="v30-mono">${esc2(x.pcf?.slice(-4)||x.ident)}</span><span class="v30-tree-name">${esc2(x.libelle||x.designation||'')}</span></button>`).join('')}</div>`:'';
 el.innerHTML=`<div class="v30-tree-head"><strong>${icon('layers',17)} Structure de l'ouvrage</strong><button type="button" data-shell-action="tree:toggle" title="Replier">${icon('chevronLeft',16)}</button></div><label class="v30-tree-search"><span>${icon('search',16)}</span><input id="v30-tree-search" type="search" placeholder="Rechercher un équipement" aria-label="Rechercher un équipement"></label><div class="v30-tree-scroll">${nodes}${common}${!nodes&&!common?'<div class="v30-empty">Aucun équipement</div>':''}</div>`;
 }
 function panel(E){const el=document.getElementById('v30-inspector');const area=document.getElementById('v30-workspace');const show=state.inspectorOpen&&!['accueil'].includes(E.vue)&&!(E.vue==='ouvrage'&&E.ouvrage?.en_conception);
 el.hidden=!show;area.classList.toggle('no-inspector',!show);if(!show)return;
 const st=stats(E),it=issues(E),body=document.getElementById('v30-inspector-body');
 let detail='';let selected=null;
 if(E.vue==='variables'){const ls=E.detailEtape?.lignes||[];selected=ls[E.varSel||0];}
 if(E.vue==='supervision'){const ls=E.detailEtape?.lignes||[];selected=ls[E.telSel||0];}
 if(selected)detail=`<section class="v30-side-card"><div class="v30-side-card-head">${icon('info',17)} Détail sélectionné</div><div class="v30-side-card-body"><strong class="v30-mono">${esc2(selected.nom)}</strong><dl><dt>Source</dt><dd>${esc2(selected.source_es||selected.variable_source||'Non renseignée')}</dd><dt>Adresse</dt><dd class="v30-mono">${esc2(selected.adresse||'—')}</dd><dt>Règle</dt><dd title="${esc2(selected.regle||'')}">${esc2(selected.regle||'—')}</dd><dt>État</dt><dd>${esc2(selected.etat_adressage||'Non renseigné')}</dd></dl>${selected.ident_eq?`<button type="button" class="v30-small-btn" data-shell-equip="${esc2(selected.ident_eq)}">${icon('link',15)} Fiche équipement</button>`:''}</div></section>`;
 if(E.vue==='es'&&E.esPanneauOuvert)detail=`<section class="v30-side-card"><div class="v30-side-card-head">${icon('pencil',17)} Paramétrage de l’E/S</div><p class="v30-side-hint">Le formulaire d'édition reste accessible dans la vue E/S.</p><button class="v30-small-btn" data-shell-action="panel:toggle">Agrandir la table</button></section>`;
 body.innerHTML=`<div class="v30-side-head"><strong>Analyse du projet</strong><button type="button" data-shell-action="panel:toggle" title="Replier le panneau">${icon('chevronRight',18)}</button></div>
 ${st.length?`<section class="v30-side-card"><div class="v30-side-card-head">${icon('bars',17)} Synthèse</div><div class="v30-kpi-list">${st.map(x=>`<div class="v30-kpi"><strong class="${x.style}">${x.value}</strong><span>${esc2(x.label)}</span></div>`).join('')}</div></section>`:''}
 <section class="v30-side-card"><div class="v30-side-card-head">${icon('shield',17)} Validation</div><div class="v30-side-card-body">${it.length?it.map(x=>`<button class="v30-issue ${x.color}" data-shell-issue="${esc2(x.route)}" data-shell-ident="${esc2(x.ident||'')}" title="${esc2(x.msg)}"><i class="v30-status-dot ${x.color}"></i>${esc2(x.msg)}</button>`).join(''):'<p class="v30-muted">Aucune anomalie remontée dans cet écran. Ce statut ne vaut pas qualification industrielle.</p>'}</div></section>${detail}
 <button class="v30-panel-toggle" data-shell-action="panel:toggle">${icon('chevronRight',16)} Masquer le panneau</button>`;
 }
 function footer(E){const el=document.getElementById('v30-status');const o=E.ouvrage||{};const ref=E.cycle?.revision?`R${String(E.cycle.revision).padStart(4,'0')}`:'non publié';
 el.innerHTML=`<span>${icon('database',14)} ${esc2(o.ouvert?o.prefixe||'Ouvrage':'Aucun ouvrage ouvert')}</span><span class="v30-status-separator"></span><span>Référentiel : ${esc2(ref)}</span><span class="v30-status-separator"></span><span>${icon('lock',14)} Adresses validées protégées</span><span class="v30-status-right">${icon('info',14)} Exports industriels non qualifiés · Version 0.32</span>`;
 }
 function schedule(){if(state.refreshQueued)return;state.refreshQueued=true;requestAnimationFrame(()=>{state.refreshQueued=false;try{refresh(window.E||E,ETAPES,etatEtape,vueEtape);}catch(err){console.warn('OGIAS affichage',err);}});}
 function render(E,etapes,etatEtape,vueEtape){state.ribbon=activeRibbon(E);const tab=routeOf(E.vue);if(!state.tabTrail.includes(tab))state.tabTrail.push(tab);
  document.body.dataset.view=E.vue;document.body.classList.toggle('v30-creation',E.vue==='ouvrage'&&E.ouvrage?.en_conception);document.body.classList.toggle('v30-home',E.vue==='accueil');
  document.getElementById('v30-documents').innerHTML=tabHTML(E);heading(E,etatEtape,vueEtape);footer(E);renderRibbon(E);
 }
 function refresh(E,etapes,etatEtape,vueEtape){document.body.dataset.view=E.vue;document.body.classList.toggle('v30-creation',E.vue==='ouvrage'&&E.ouvrage?.en_conception);
  renderRibbon(E);tree(E);panel(E);heading(E,etatEtape,vueEtape);footer(E);
  const summary=issues(E);const badge=document.getElementById('v30-notifications');badge.innerHTML=`${icon('bell',18)}${summary.length?`<span class="v30-notif-count">${summary.length}</span>`:''}`;badge.title=summary.length?summary.length+' anomalie(s) visibles dans cet écran':'Aucune anomalie signalée sur cet écran';
  const f=document.getElementById('vue');
 // Chaque commande globale n'apparaît qu'au ruban : le bouton métier original
 // reste dans le DOM (listeners/API inchangés) mais est masqué visuellement.
 specs(E).filter(x=>!x.id.includes(':')).forEach(x=>{const b=document.getElementById(x.id);if(b)b.classList.add('v30-source-command');});
 f?.querySelectorAll('th').forEach(th=>{if(!th.hasAttribute('title'))th.title=th.textContent.trim();});
  f?.querySelectorAll('td').forEach(td=>{if(!td.hasAttribute('title')&&td.textContent.trim().length>42)td.title=td.textContent.trim()});
  const footerEl=f?.querySelector('.pied-etape');if(footerEl)footerEl.classList.add('v30-original-step-footer');
 }
 document.addEventListener('click',ev=>{
  const action=ev.target.closest('[data-shell-action]');if(action){ev.preventDefault();runAction(action.dataset.shellAction,E);return;}
  const tab=ev.target.closest('[data-shell-tab]');if(tab){ev.preventDefault();state.ribbon=tab.dataset.shellTab;renderRibbon(E);return;}
  const route=ev.target.closest('[data-shell-route]');if(route){ev.preventDefault();naviguer(route.dataset.shellRoute);return;}
  const close=ev.target.closest('[data-close-tab]');if(close){ev.preventDefault();state.tabTrail=state.tabTrail.filter(x=>x!==close.dataset.closeTab);if(close.dataset.closeTab===routeOf(E.vue))naviguer('#/ouvrages');else render(E,ETAPES,etatEtape,vueEtape);return;}
  const equip=ev.target.closest('[data-shell-equip]');if(equip){ev.preventDefault();E.sel={nature:'eq',valeur:equip.dataset.shellEquip};allerOuvrage(E.sel);return;}
  const uf=ev.target.closest('[data-shell-uf]');if(uf){ev.preventDefault();E.sel={nature:'uf',valeur:uf.dataset.shellUf};allerOuvrage(E.sel);return;}
  const issue=ev.target.closest('[data-shell-issue]');if(issue){ev.preventDefault();if(issue.dataset.shellIdent)E.sel={nature:'eq',valeur:issue.dataset.shellIdent};naviguer(issue.dataset.shellIssue);return;}
 },true);
 document.addEventListener('input',ev=>{if(ev.target?.id==='v30-tree-search'){const q=ev.target.value.toLocaleLowerCase('fr');document.querySelectorAll('.v30-tree-equip').forEach(n=>{n.hidden=!n.textContent.toLocaleLowerCase('fr').includes(q)});}},true);
 document.addEventListener('keydown',ev=>{if(ev.key==='Escape'&&document.getElementById('modale')&&!document.getElementById('modale').hidden){document.querySelector('#modale [data-fermer]')?.click();}});
 function initV30(){document.getElementById('v30-help')?.addEventListener('click',()=>{window.open('aide.html','_blank','noopener');});
 document.getElementById('v30-notifications')?.addEventListener('click',()=>{state.inspectorOpen=true;schedule();});
 fetch('/api/session-locale').then(r=>r.ok?r.json():{}).then(x=>{const n=document.getElementById('v30-user');if(x.utilisateur){n.textContent=x.utilisateur;n.hidden=false;}}).catch(()=>{});
 // Avec la présentation V31, ses render/refresh pilotent déjà chaque vue.
 // Reconstruire le ruban et l'inspecteur V30 masqués à chaque frappe multiplie
 // les parcours du DOM sans ajouter de commande accessible.
 if(typeof V31==='undefined'){
  const observer=new MutationObserver(()=>schedule());observer.observe(document.getElementById('vue'),{childList:true,subtree:true});
 }
 }
 if(document.readyState==='complete')initV30();
 else window.addEventListener('load',initV30,{once:true});
 return {icon,render,refresh,theme:setTheme,schedule};
})();
