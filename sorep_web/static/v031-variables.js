"use strict";
/* OGIAS 0.31 — Tableau de bord et table de variables unifiée.
   Les mutations passent EXCLUSIVEMENT par l'API existante et le moteur d'adressage. */
function vueDashboardV31(){
 const o=E.ouvrage||{}, a=E.accueil||{}, r=E.recetteDashboard, es=E.esDashboard, vs=E.variablesDashboard;
 const equipConnus=Array.isArray(o.equipements), equip=equipConnus?o.equipements:[];
 const esConnues=Array.isArray(es?.points)||(equipConnus&&equip.length===0);
 const variablesConnues=Array.isArray(vs?.lignes);
 const recetteConnue=Number.isFinite(r?.erreurs)&&r.erreurs>=0&&Number.isFinite(r?.alertes)&&r.alertes>=0;
 const points=Array.isArray(es?.points)?es.points:[], variables=variablesConnues?vs.lignes:[];
 const valides=variables.filter(x=>x.validee).length, anomalies=recetteConnue?r.erreurs+r.alertes:null;
 const equipValides=equip.filter(x=>x.valide).length, contenusValides=points.filter(x=>x.contenu_valide).length;
 const stats=[
  ['Équipements',equipConnus?equip.length:null,!equipConnus?'Inventaire indisponible':equipValides?`${equipValides} validé(s)`:equip.length?'Paramétrage à valider':'','cpu','Aucun équipement'],
  ['E/S physiques',esConnues?points.length:null,!esConnues?'Liste des E/S indisponible':contenusValides?`${contenusValides} contenu(s) validé(s)`:points.length?'Contenu à valider':'','bolt','Aucune E/S'],
  ['Variables validées',variablesConnues?valides:null,variablesConnues?(variables.length?`sur ${variables.length}`:''):'Variables indisponibles','list',variables.length?'Aucune variable validée':'Aucune variable'],
  ['Points à traiter',anomalies,recetteConnue?[[r.erreurs,'erreur(s)'],[r.alertes,'alerte(s)']].filter(([n])=>n>0).map(([n,label])=>`${n} ${label}`).join(', '):'Recette indisponible','alert','Aucun point à traiter']
 ];
 const card=(v,i)=>`<section class="v31-kpi ${i===3?'v31-attention':''}"><div class="v31-kpi-label"><span class="v31-kpi-icon">${V31.icon(v[3])}</span><strong>${v[0]}</strong></div>
    ${v[1]===null?'<div class="v31-kpi-empty">Non disponible</div>':v[1]===0?`<div class="v31-kpi-empty">${v[4]}</div>`:`<div class="v31-kpi-value">${v[1]}</div>`}<div class="v31-muted">${v[2]}</div></section>`;
 const recent=(a.ouvrages||[]).slice(0,9).map(x=>`<tr><td><button type="button" class="v31-list-open" data-open="${V31.esc(x.chemin)}"><span class="v31-mini-avatar">${V31.esc((x.repere||'OG').slice(0,2))}</span><span><b>${V31.esc(x.libelle||x.repere)}</b><small>${V31.esc(x.repere)} · ${V31.esc(x.mode)}</small></span></button></td><td><span class="v31-pill info">${x.equipements?`${V31.esc(x.equipements)} équipement(s)`:'Sans équipement'}</span></td><td>${V31.esc(x.date)}</td></tr>`).join('');
 const cats=['ET','ST','EA','SA'];const counts=cats.map(c=>[c,points.filter(p=>p.point===c).length]);const total=points.length||1;
 const issues=(r?.controles||[]).filter(c=>c.niveau==='Erreur'||c.niveau==='Alerte').slice(0,7);
 // L'API Recette actuelle énumère les anomalies, pas les contrôles conformes : aucun taux fictif.
 const pct=recetteConnue&&Number.isFinite(r?.controles_total)&&r.controles_total>0&&Number.isFinite(r?.controles_conformes)&&r.controles_conformes>=0&&r.controles_conformes<=r.controles_total?Math.round(r.controles_conformes/r.controles_total*100):null;
 document.getElementById('vue').innerHTML=`<section class="v31-dashboard" aria-label="Tableau de bord de l'ouvrage">
 <div class="v31-kpi-grid">${stats.map(card).join('')}</div>
 <div class="v31-dash-grid"><section class="v31-card v31-dash-recent"><header><h2>Ouvrages récents</h2><button class="v31-text-button" type="button" data-nav="#/ouvrages">Tout voir ${V31.icon('arrow',14)}</button></header>
 ${recent?`<table class="v31-recent-table"><tbody>${recent}</tbody></table>`:'<div class="v31-blank">Aucun ouvrage enregistré pour le moment.</div>'}</section>
 <section class="v31-card v31-dash-recette"><h2>Avancement de la recette</h2>
 ${pct===null?`<div class="v31-blank">${recetteConnue?'Le taux de conformité est indisponible. Consultez les points à traiter ci-dessous.':'Recette indisponible : ouvrez la recette pour consulter les contrôles.'}</div>`:`<div class="v31-ring" style="--value:${pct}%"><strong>${pct} %</strong><span>${r.controles_conformes} contrôle(s) conformes</span></div>`}
 <h3>Points à traiter</h3>${issues.length?issues.map(c=>`<button type="button" data-nav="#/recette" class="v31-issue"><span class="v31-pill ${c.niveau==='Erreur'?'error':'warning'}">${V31.esc(c.niveau)}</span><span>${V31.esc(c.message)}</span></button>`).join(''):`<div class="v31-muted">${!recetteConnue?'Bilan indisponible tant que la recette ne peut pas être consultée.':anomalies===0?'Aucune anomalie détectée par la recette actuelle.':'Des points restent à traiter : ouvrez la recette pour consulter leur détail.'}</div>`}</section>
 <section class="v31-card v31-dash-activity"><h2>E/S par nature</h2><p class="v31-muted">${!esConnues?'Répartition E/S indisponible':points.length?`${points.length} E/S physiques renseignées`:'Aucune E/S physique renseignée'}</p>
 ${!esConnues?'<div class="v31-blank">Ouvrez la liste des E/S pour consulter les contrôles à résoudre.</div>':points.length? `<div class="v31-stack">${counts.map(([name,n]) => n ? `<div class="v31-stack-piece v31-f-${name}" title="${name}: ${n}" style="width:${(n / total) * 100}%"></div>` : "").join("")}</div><div class="v31-stack-legend">${counts.filter(x=>x[1]).map(([name,n]) => `<span>${name} ${n}</span>`).join("")}</div>` : `<div class="v31-blank">Aucune E/S affectée à l’ouvrage.</div>`}
 <h3>Accès rapides</h3><div class="v31-quick"><button data-nav="#/inventaire">Équipements ${V31.icon('chevron',14)}</button><button data-nav="#/es">Liste des E/S ${V31.icon('chevron',14)}</button><button data-nav="#/variables">Variables ${V31.icon('chevron',14)}</button><button data-nav="#/recette">Recette ${V31.icon('chevron',14)}</button></div></section></div></section>`;
 document.querySelectorAll('[data-open]').forEach(b=>b.onclick=async()=>{try{await agir(api('/api/ouvrir',{chemin:b.dataset.open}));E.ficheDraft=null;E.ficheDirty=false;naviguer('#/dashboard');}catch(e){}});
}
function v31Status(t){const kind=t==='validée'?'success':t==='en conflit'||t==='non résolue'?'error':t==='à valider'?'warning':'info';return `<span class="v31-pill ${kind}">${V31.esc(t||'non résolue')}</span>`;}
function v31VarFilter(rows){const st=E.v31Status||'',q=(E.v31Query||'').toLocaleLowerCase('fr'),view=E.v31VarView||'all';
 return rows.filter(v=>{if(st&&v.etat_adressage!==st)return false;if(q&&!`${v.nom} ${v.source_es} ${v.famille} ${v.regle}`.toLocaleLowerCase('fr').includes(q))return false;
  return true; /* Les vues changent les colonnes, pas les familles. */});}
function v31EmptyColumns(){
 const cell=document.querySelector('.v31-table tbody td[colspan]');
 if(!cell)return;
 const headers=cell.closest('table').tHead.rows[0].cells;
 cell.colSpan=[...headers].filter(h=>getComputedStyle(h).display!=='none').length||1;
}
window.addEventListener('resize',v31EmptyColumns);
function v31CloseVariableDetail(){
 const selected=E.v31Selected;
 E.v31VarDetail=false;vueVariablesV31();
 const row=[...document.querySelectorAll('.v31-variable-row')].find(r=>r.dataset.variable===selected);
 (row||document.querySelector('#v31-var-search'))?.focus();
}
document.addEventListener('keydown',ev=>{
 if(ev.key!=='Escape'||document.querySelector('#modale:not([hidden])')||document.querySelector('#v31-search-dialog'))return;
 const close=document.querySelector('#v31-close-detail');
 if(close){ev.preventDefault();close.click();}
},true); // Lire l'état des fenêtres avant leur fermeture par les gestionnaires en phase de bulle.
function vueVariablesV31(){
 const d=E.detailEtape||{}, rows=d.lignes||[], neuf=d.mode==='Neuf',selected=E.v31Selected||'', opened=!!E.v31VarDetail;
 const shown=v31VarFilter(rows);const page=Math.max(0,Math.min(E.v31Page||0,Math.floor(Math.max(shown.length-1,0)/150)));E.v31Page=page;const pageRows=shown.slice(page*150,(page+1)*150);const selectedVar=rows.find(x=>x.nom===selected)||null;
 const counts=['proposée','à valider','en conflit','validée','non résolue'].map(status=>[status,rows.filter(x=>x.etat_adressage===status).length]).filter(x=>x[1]);
 const view=E.v31VarView||'all';const withDetail=opened&&!!selectedVar;
 const teleMap=new Map((E.v31Tele?.lignes||[]).map(x=>[x.nom,x]));
 const body=pageRows.map(v=>{const t=teleMap.get(v.nom)||{}, current=v.adresse||'',proposed=v.adresse_proposee||'',protocol=t.adresse_protocole_actuelle||t.adresse_protocole_proposee||'';
   return `<tr class="v31-variable-row ${withDetail&&v.nom===selected?'selected':''}" tabindex="0" data-variable="${V31.esc(v.nom)}" title="Ouvrir le détail de ${V31.esc(v.nom)}">
     <td><input type="checkbox" class="v31-choose" data-ident="${V31.esc(v.ident_eq||'')}" data-cle="${V31.esc(v.cle||'')}" aria-label="Sélectionner ${V31.esc(v.nom)}" ${!neuf?'disabled':''}></td>
     <td class="mono" title="${V31.esc(v.nom)}">${V31.esc(v.nom)}</td><td><span class="v31-family">${V31.esc(v.famille)}</span></td>
     <td class="mono v31-source" title="${V31.esc(v.source_es||v.origine||'Règle fonctionnelle')}">${V31.esc(v.source_es||v.origine||'Calcul')}</td>
     <td class="mono" title="${V31.esc(current||proposed||'Non attribuée')}">${V31.esc(current||proposed||'—')}${v.validee?` <span title="Adresse validée et protégée">${V31.icon('shield',13)}</span>`:''}</td>
     <td class="mono v31-col-tele ${view==='exchange'?'v31-hide-in-exchange':''}">${V31.esc(protocol||'—')}</td><td>${v31Status(v.etat_adressage)}</td>
     <td class="v31-rule ${view==='tele'?'v31-hide-in-tele':''}" title="${V31.esc(v.motif||v.regle||'')}">${V31.esc(v.motif||v.regle||'—')}</td></tr>`;}).join('');
 const available=rows.filter(x=>x.etat_adressage==='proposée'&&!x.validee).length;
 const validable=rows.filter(x=>x.etat_adressage==='à valider'&&!x.validee).length;
 const blocked=!neuf||rows.some(x=>x.etat_adressage==='en conflit')||(!available&&!validable);
 const filter=(key,label)=>`<button type="button" class="v31-tab ${view===key?'active':''}" data-var-view="${key}">${label}</button>`;
 const statuses=counts.map(([name,n])=>`<button type="button" class="v31-filter ${E.v31Status===name?'active':''}" data-var-status="${V31.esc(name)}">${V31.esc(name)} ${n}</button>`).join('');
 const detail=withDetail?`<aside class="v31-variable-detail" aria-label="Variable sélectionnée"><div class="v31-detail-heading"><span>Variable sélectionnée</span><button type="button" id="v31-close-detail" aria-label="Fermer le détail">${V31.icon('close',18)}</button></div>
 <h2 class="mono">${V31.esc(selectedVar.nom)}</h2><p>${V31.esc(selectedVar.commentaire||selectedVar.libelle||selectedVar.repere||'')}</p><div class="v31-detail-badges">${v31Status(selectedVar.etat_adressage)} <span class="v31-pill neutral">${V31.esc(selectedVar.famille)} · ${V31.esc(selectedVar.type)}</span></div>
 <dl><dt>Source</dt><dd class="mono">${V31.esc(selectedVar.source_es||'Fonction calculée')}</dd>
 <dt>Voie physique</dt><dd class="mono">${V31.esc(selectedVar.source_es?(selectedVar.voie_es||'Non placée — Matériel'):'Sans objet')}</dd>
 <dt>Adresse automate</dt><dd class="mono">${V31.esc(selectedVar.adresse||selectedVar.adresse_proposee||'—')}</dd>
 <dt>Télétransmission</dt><dd class="mono">${V31.esc((teleMap.get(selectedVar.nom)||{}).adresse_protocole_actuelle||(teleMap.get(selectedVar.nom)||{}).adresse_protocole_proposee||'—')}</dd>
 <dt>Origine</dt><dd>${V31.esc(selectedVar.origine_adressage||'—')}</dd>
 <dt>Règle appliquée</dt><dd>${V31.esc(selectedVar.regle||selectedVar.motif||'Non définie')}</dd>
 <dt>Validation</dt><dd>${V31.esc(selectedVar.validee_le||'Non validée')}${selectedVar.validee_par?' · '+V31.esc(selectedVar.validee_par):''}</dd></dl>
 <div class="v31-detail-actions"><button type="button" id="v31-validate-single" class="v31-primary" ${!neuf||!selectedVar.adresse||selectedVar.validee?'disabled':''} title="Une proposition doit d’abord être appliquée avec l’empreinte du plan">${V31.icon('check',16)} Valider l'adresse</button>
 <button type="button" id="v31-edit-single" ${!neuf?'disabled':''}>Saisir / éditer</button></div>
 ${selectedVar.ident_eq?'<button type="button" class="v31-text-button" id="v31-source-equip">Ouvrir la fiche équipement</button>':''}</aside>`:'';
 const errCount=rows.filter(x=>['en conflit','non résolue'].includes(x.etat_adressage)).length;
 document.getElementById('vue').innerHTML=`<section class="v31-variable-screen ${withDetail?'has-detail':''}"><div class="v31-card v31-main-table">
 <div class="v31-table-toolbar"><div class="v31-view-switch">${filter('all','Toutes')}${filter('exchange','Adresses automate')}${filter('tele','Télétransmission')}</div>
 <label class="v31-search-field">${V31.icon('search',16)}<input id="v31-var-search" value="${V31.esc(E.v31Query||'')}" aria-label="Filtrer les variables" placeholder="Filtrer"></label>
 <div class="v31-status-filters">${statuses}</div>
 <div class="v31-actions"><button type="button" class="v31-secondary" id="v31-calculate" ${!neuf?'disabled':''} title="Calculer un aperçu sans appliquer les adresses">${V31.icon('spark',15)} Calculer</button>
 <button type="button" class="v31-primary" id="v31-validate-proposed" ${blocked?'disabled':''} title="${blocked?(!neuf?'Adresses historiques conservées':errCount?'Résoudre les conflits avant validation':'Aucune proposition à valider'):'Aperçu, application contrôlée puis validation explicite'}">${V31.icon('check',16)} ${available?`Valider les propositions · ${available}`:`Valider les adresses · ${validable}`}</button>
 <button type="button" class="v31-menu-button" id="v31-var-more" aria-label="Autres actions" title="Autres actions">···</button></div></div>
 ${!neuf?'<div class="v31-inform">Projet existant : les adresses historiques sont conservées, sans réaffectation automatique.</div>':''}
 ${errCount?`<div class="v31-inform warning">${errCount} point(s) bloquant(s) ou non résolu(s). Les conflits doivent être corrigés avant la validation.</div>`:''}
 <div class="v31-table-area"><table class="v31-table"><thead><tr><th><input type="checkbox" id="v31-select-all" aria-label="Tout sélectionner" ${!neuf?'disabled':''}></th><th>Variable</th><th>Famille</th><th class="v31-source">Source</th><th>Adresse automate</th><th class="v31-col-tele ${view==='exchange'?'v31-hide-in-exchange':''}">Télétransmission</th><th>Statut</th><th class="v31-rule ${view==='tele'?'v31-hide-in-tele':''}">Règle</th></tr></thead><tbody>
 ${body||`<tr><td colspan="${view==='all'?8:7}"><div class="v31-blank">Aucune variable à afficher avec ces filtres.</div></td></tr>`}</tbody></table></div>
 <footer class="v31-table-footer"><span>${rows.length?`${rows.length} variable(s) · ${shown.length?`${shown.length} filtrée(s)`:'Aucun résultat'}`:'Aucune variable'} · page ${page+1}/${Math.max(1,Math.ceil(shown.length/150))}</span><div class="v31-page-controls"><button type="button" id="v31-prev-page" ${page===0?'disabled':''}>Précédent</button><button type="button" id="v31-next-page" ${(page+1)*150>=shown.length?'disabled':''}>Suivant</button></div>
 <button type="button" id="v31-adr-settings" class="v31-text-button">Paramètres d’adressage</button></footer></div>${detail}</section>`;
 v31EmptyColumns();
 document.querySelectorAll('[data-var-view]').forEach(el=>el.onclick=()=>{E.v31VarView=el.dataset.varView;E.v31Page=0;vueVariablesV31();});
 document.querySelectorAll('[data-var-status]').forEach(el=>el.onclick=()=>{E.v31Status=E.v31Status===el.dataset.varStatus?'':el.dataset.varStatus;E.v31Page=0;vueVariablesV31();});
 document.getElementById('v31-var-search').oninput=e=>{E.v31Query=e.target.value;E.v31Page=0;vueVariablesV31();const inp=document.getElementById('v31-var-search');inp.focus();inp.setSelectionRange(inp.value.length,inp.value.length);};
 document.querySelectorAll('.v31-variable-row').forEach(row=>{const pick=()=>{E.v31Selected=row.dataset.variable;E.v31VarDetail=true;vueVariablesV31();};row.onclick=ev=>{if(!ev.target.closest('input'))pick();};row.onkeydown=ev=>{if(ev.target===row&&(ev.key==='Enter'||ev.key===' ')){ev.preventDefault();pick();}};});
 document.querySelector('#v31-close-detail')?.addEventListener('click',v31CloseVariableDetail);
 document.querySelector('#v31-select-all')?.addEventListener('change',ev=>{document.querySelectorAll('.v31-choose:not(:disabled)').forEach(c=>c.checked=ev.target.checked);});
 document.querySelector('#v31-validate-single')?.addEventListener('click',async()=>{try{const v=selectedVar;if(!v||!v.adresse||!neuf)return;
   const res=await api('/api/variables/action',{action:'valider',paires:[{ident_eq:v.ident_eq,cle:v.cle}]});if(res.refus?.length)throw Error(res.refus.join(' | '));toast('Adresse validée et protégée.');await v31ReloadVariables();}catch(e){toast(e.message,true);}});
 document.querySelector('#v31-edit-single')?.addEventListener('click',()=>{if(neuf&&selectedVar)editerVariableV29(selectedVar);});
 document.querySelector('#v31-source-equip')?.addEventListener('click',()=>allerOuvrage({nature:'eq',valeur:selectedVar.ident_eq}));
 document.getElementById('v31-calculate').onclick=async()=>{try{const plan=await api('/api/adressage');E.v31Plan=plan;toast(`Aperçu recalculé : ${(plan.affectations||[]).filter(a=>a.niveau==='automate'&&a.etat==='proposée').length} proposition(s), ${(plan.conflits||[]).length} conflit(s).`);await v31ReloadVariables();}catch(e){toast(e.message,true);}};
 document.getElementById('v31-validate-proposed').onclick=()=>v31ValidateProposals();
 document.getElementById('v31-adr-settings').onclick=()=>naviguer('#/adressage');
 document.getElementById('v31-var-more').onclick=()=>v31VariableMenu();
 document.getElementById('v31-prev-page').onclick=()=>{E.v31Page--;vueVariablesV31();};
 document.getElementById('v31-next-page').onclick=()=>{E.v31Page++;vueVariablesV31();};
}
async function v31ReloadVariables(){E.detailEtape=await api('/api/variables');try{E.v31Tele=await api('/api/supervision');}catch(_){E.v31Tele={lignes:[]};}vueVariablesV31();}
async function v31ValidateProposals(){
 try{
  if(E.detailEtape?.mode!=='Neuf')throw Error('Projet existant : adressage historique en lecture seule.');
  const plan=await api('/api/adressage');const conflicts=plan.conflits||[];
  if(conflicts.length)throw Error(`${conflicts.length} conflit(s) bloquant(s) : corrigez-les avant de valider.`);
  const affected=(plan.affectations||[]).filter(a=>a.niveau==='automate'&&a.etat==='proposée');
  const pending=(plan.affectations||[]).filter(a=>a.niveau==='automate'&&a.etat==='à valider');
  const pairs=[...new Map([...affected,...pending].map(a=>[`${a.ident_eq}|${a.cle}`,{ident_eq:a.ident_eq,cle:a.cle}])).values()];
  if(!pairs.length)throw Error('Aucune adresse disponible pour validation.');
  const msg=`${affected.length} adresse(s) seront appliquées avec l'empreinte du plan, puis ${pairs.length} adresse(s) seront soumises à validation. Les adresses déjà validées ne changent pas.`;
  confirmer(`Valider ${pairs.length} adresse(s) ?`,msg,'Appliquer et valider',async()=>{
   try{
    if(affected.length)await api('/api/adressage/action',{action:'appliquer',empreinte:plan.empreinte,niveaux:['automate']});
    const result=await api('/api/adressage/action',{action:'valider',niveau:'automate',paires:pairs});
    toast(`${result.n||0} adresse(s) validée(s).`);await v31ReloadVariables();
   }catch(e){toast('Validation interrompue : '+e.message,true);await v31ReloadVariables();}
  });
 }catch(e){toast(e.message,true);}
}
function v31VariableMenu(){
 const m=ouvrirModale(`<div class="boite-tete"><h2>Actions sur les variables</h2></div><div class="boite-corps"><p>Les commandes utilisent le moteur OGIAS et conservent les adresses validées.</p>
 <div class="v31-action-list"><button id="v31-menu-selected">Valider les adresses de la sélection</button><button id="v31-menu-reserve">Réserver une plage / convention</button><button id="v31-menu-export">Exporter la table de télétransmission</button></div></div><div class="boite-pied"><button data-fermer>Fermer</button></div>`);
 m.querySelector('#v31-menu-selected').onclick=async()=>{const pairs=[...document.querySelectorAll('.v31-choose:checked')].map(x=>({ident_eq:x.dataset.ident,cle:x.dataset.cle}));fermerModale();if(!pairs.length)return toast('Sélectionnez d’abord une ou plusieurs variables.',true);
  confirmer(`Valider ${pairs.length} adresse(s) ?`,'Seules les adresses déjà attribuées, contrôlées et non conflictuelles seront validées.','Valider',async()=>{try{const r=await api('/api/variables/action',{action:'valider',paires:pairs});if(r.refus?.length)toast(r.refus.join(' | '),true);else toast(`${r.validees} adresse(s) validée(s).`);await v31ReloadVariables();}catch(e){toast(e.message,true);}});};
 m.querySelector('#v31-menu-reserve').onclick=()=>{fermerModale();naviguer('#/adressage');};
 m.querySelector('#v31-menu-export').onclick=()=>{fermerModale();telecharger('variables');};
}
function vueAccueilV31(){
 const a=E.accueil||{},ouvrages=a.ouvrages||[];
 const recent=ouvrages.slice().sort((x,y)=>String(y.date||'').localeCompare(String(x.date||'')));
 const cards=recent.map(f=>`<article class="v31-project-card" data-project="${V31.esc(f.chemin)}" tabindex="0" aria-label="Ouvrir ${V31.esc(f.libelle||f.repere)}">
   <div class="v31-project-symbol">${V31.icon('folder',20)}</div><div class="v31-project-body"><b>${V31.esc(f.libelle||f.repere)}</b><span class="mono">${V31.esc(f.repere)}</span>
   <small>${V31.esc(f.mode)}${f.equipements?` · ${f.equipements} équipement(s)`:''}</small></div>
   <div class="v31-project-foot"><small>${V31.esc(f.date||'')}</small><button type="button" class="v31-project-delete" data-delete="${V31.esc(f.chemin)}" data-repere="${V31.esc(f.repere)}" title="Déplacer à la corbeille">${V31.icon('close',14)}</button></div>
 </article>`).join('');
 document.querySelector('#vue').innerHTML=`<div class="v31-home"><div class="v31-home-actions"><button type="button" class="v31-primary" id="v31-new-project">${V31.icon('folder',17)} Créer un ouvrage neuf</button>
   <button type="button" class="v31-secondary" id="v31-import-project">Ouvrir un projet existant</button><button type="button" class="v31-text-button" id="v31-ref-open">Référentiel métier</button></div>
 <div class="v31-project-header"><h2>Ouvrages enregistrés</h2>${ouvrages.length?`<label class="v31-search-field">${V31.icon('search',16)} <input id="v31-filter-projects" placeholder="Rechercher un ouvrage" aria-label="Rechercher parmi les ouvrages"></label>`:''}</div>
 ${recent.length?`<div class="v31-project-grid">${cards}</div>`:`<section class="v31-home-empty"><div class="v31-empty-symbol">${V31.icon('folder',34)}</div><h2>Votre espace est prêt</h2>
 <p>Créez votre premier ouvrage ou reprenez les données d'une installation existante.</p><button type="button" class="v31-primary" id="v31-first-project">Créer un ouvrage</button></section>`}</div>`;
 const create=async mode=>{try{await agir(api('/api/nouveau',{mode}));E.ficheDraft=null;E.ficheDirty=false;allerOuvrage({nature:'ouvrage',valeur:''});}catch(_){}};
 document.querySelector('#v31-new-project').onclick=()=>create('Neuf');
 document.querySelector('#v31-first-project')?.addEventListener('click',()=>create('Neuf'));
 document.querySelector('#v31-import-project').onclick=()=>create('Existant');
 document.querySelector('#v31-ref-open').onclick=()=>allerReferentiel();
 const open=async f=>{try{await agir(api('/api/ouvrir',{chemin:f}));E.ficheDraft=null;E.ficheDirty=false;naviguer('#/dashboard');}catch(_){}};
 document.querySelectorAll('[data-project]').forEach(c=>{c.onclick=e=>{if(!e.target.closest('[data-delete]'))open(c.dataset.project);};c.onkeydown=e=>{if(e.key==='Enter'){e.preventDefault();open(c.dataset.project);}};});
 document.querySelectorAll('[data-delete]').forEach(b=>b.onclick=()=>confirmer(`Supprimer ${b.dataset.repere} ?`,'L’ouvrage sera placé dans la corbeille du dossier Projets.','Déplacer à la corbeille',async()=>{await agir(api('/api/supprimer_ouvrage',{chemin:b.dataset.delete}),'Ouvrage déplacé vers la corbeille.');allerAccueil();}));
 document.querySelector('#v31-filter-projects')?.addEventListener('input',e=>{const q=e.target.value.toLocaleLowerCase('fr');document.querySelectorAll('[data-project]').forEach(card=>{card.hidden=!card.textContent.toLocaleLowerCase('fr').includes(q);});});
}
