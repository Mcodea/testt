"use strict";
/* Les objets appartiennent au dépôt commun. Seule son API de brouillon écrit. */
function navigationObjetsReferentiel() {
 return `<nav class="ref-objets" aria-label="Objets du référentiel">${[
  ["types","Types et modèles"], ["lexique","Lexique"], ["dictionnaire_es","Dictionnaire des E/S"], ["correspondances","Correspondances"]
 ].map(([cle,nom])=>`<button type="button" data-ref-objet="${cle}" aria-pressed="${(E.refObjet||'types')===cle}">${nom}</button>`).join('')}</nav>`;
}
function brancherNavigationReferentiel() {
 document.querySelectorAll('[data-ref-objet]').forEach(b=>b.onclick=()=>{
  E.refObjet=b.dataset.refObjet; E.refCodeQuery=''; E.refCodePage=0; E.refCodeForm=null; vueReferentiel();
 });
}
function vueCodesReferentiel() {
 const lex=E.refObjet==='lexique', corr=E.refObjet==='correspondances';
 const titre=lex?'Lexique':corr?'Correspondances':'Dictionnaire des E/S', ed=E.ref.source==='brouillon';
 const lignes=E.ref[E.refObjet]||[], q=(E.refCodeQuery||'').toLocaleLowerCase('fr');
 const filtre=lignes.filter(r=>Object.values(r).join(' ').toLocaleLowerCase('fr').includes(q));
 const page=Math.max(0,Math.min(E.refCodePage||0,Math.max(0,Math.ceil(filtre.length/100)-1)));
 const visibles=filtre.slice(page*100,(page+1)*100), form=E.refCodeForm;
 const selection=form&&!form.nouveau?lignes.find(r=>r.cle===form.cle):null;
 if(form&&!form.nouveau&&!selection){E.refCodeForm=null;return vueCodesReferentiel();}
 const colonnes=lex?['Mot ou expression','Abréviation','Nature','Code du dictionnaire']:corr?['Type d’origine','Ancienne clé','Type cible','Nouvelle clé','Motif']:['Nature','Code','Libellé standard','Catégorie','Télétransmission'];
 const cellules=r=>lex?[r.mot,r.abreviation,r.nature,r.dictionnaire_es?'Oui':'']:corr?[r.type,r.ancienne,r.type_nouveau||r.type,r.nouvelle,r.motif]:[r.nature,r.code,r.libelle,r.categorie,r.teletransmission];
 document.querySelector('#vue').innerHTML=`${bandeauReferentiel()}${navigationObjetsReferentiel()}
 <section class="ref-codes-layout ${form?'avec-detail':''}" aria-label="${titre}">
  <div class="ref-codes-table v31-card"><header><h2>${titre}</h2>
   <label class="v31-search-field">${V31.icon('search',16)}<input id="ref-codes-query" type="search" aria-label="${corr?'Rechercher dans les correspondances':'Rechercher dans le '+(lex?'lexique':'dictionnaire')}" placeholder="Rechercher…" value="${esc(E.refCodeQuery||'')}"></label>
   <button type="button" id="ref-codes-add" ${ed?'':'disabled title="Créer un brouillon pour ajouter une entrée"'}>Ajouter</button></header>
  <div class="ref-codes-scroll"><table><thead><tr>${colonnes.map(n=>`<th scope="col">${n}</th>`).join('')}</tr></thead><tbody>
   ${visibles.map(r=>`<tr tabindex="0" data-ref-code="${esc(r.cle)}" aria-selected="${selection?.cle===r.cle}" aria-label="${esc(lex?r.mot:r.cle)}">${cellules(r).map((v,i)=>`<td class="${i===1?'mono':''}">${esc(v||'—')}</td>`).join('')}</tr>`).join('')||`<tr><td colspan="${colonnes.length}" class="vide">Aucune entrée pour cette recherche.</td></tr>`}
  </tbody></table></div>
  <footer>${filtre.length?`<span>${filtre.length} entrée(s) · page ${page+1}/${Math.ceil(filtre.length/100)}</span>`:'<span>Aucun résultat</span>'}
   <div><button id="ref-codes-prev" ${page?'':'disabled'} aria-label="Page précédente">Précédent</button><button id="ref-codes-next" ${(page+1)*100<filtre.length?'':'disabled'} aria-label="Page suivante">Suivant</button></div></footer></div>
  ${form?detailCodeReferentiel(selection,lex,ed,form.nouveau,corr):''}</section>`;
 brancherReferentiel(null,ed);
 const recherche=document.querySelector('#ref-codes-query');
 recherche.oninput=()=>{E.refCodeQuery=recherche.value;E.refCodePage=0;vueCodesReferentiel();document.querySelector('#ref-codes-query').focus();};
 document.querySelector('#ref-codes-prev').onclick=()=>{E.refCodePage=page-1;vueCodesReferentiel();};
 document.querySelector('#ref-codes-next').onclick=()=>{E.refCodePage=page+1;vueCodesReferentiel();};
 const ouvrir=(cle,nouveau=false)=>{E.refCodeForm={cle,nouveau};vueCodesReferentiel();document.querySelector('#ref-code-close').focus();};
 document.querySelector('#ref-codes-add').onclick=()=>ouvrir('',true);
 document.querySelectorAll('[data-ref-code]').forEach(row=>{
  row.onclick=()=>ouvrir(row.dataset.refCode);
  row.onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();ouvrir(row.dataset.refCode);}};
 });
 if(form) brancherDetailCode(selection,lex,ed,form.nouveau,corr);
}
function detailCodeReferentiel(row,lex,ed,nouveau,corr=false) {
 const r=row||{}, lecture=!ed||(corr&&!nouveau);
 const input=(nom,label,value,immuable=false)=>`<label for="ref-code-${nom}">${label}</label><input id="ref-code-${nom}" name="${nom}" value="${esc(value||'')}" ${lecture||immuable?'disabled':''} ${['mot','abreviation','code','libelle','type','ancienne','nouvelle','motif'].includes(nom)?'required':''}>`;
 const select=(nom,label,values,value,immuable=false)=>`<label for="ref-code-${nom}">${label}</label><select id="ref-code-${nom}" name="${nom}" ${lecture||immuable?'disabled':''}>${values.map(v=>`<option ${v===value?'selected':''}>${esc(v)}</option>`).join('')}</select>`;
 return `<aside class="ref-code-detail" aria-labelledby="ref-code-title"><header><h2 id="ref-code-title">${nouveau?'Ajouter une entrée':esc(lex?r.mot:r.cle)}</h2><button id="ref-code-close" type="button" aria-label="Fermer le détail">${V31.icon('close',16)}</button></header>
  <form id="ref-code-form"><div class="ref-code-fields">${lex?
   input('mot','Mot ou expression',r.mot,!nouveau)+input('abreviation','Abréviation',r.abreviation)+select('nature','Nature',['Mot','Expression'],r.nature||'Mot')+
   `<label class="case"><input type="checkbox" name="dictionnaire_es" ${r.dictionnaire_es?'checked':''} ${lecture?'disabled':''}> Code du dictionnaire des E/S</label>`:corr?
   input('type','Type d’origine',r.type)+input('ancienne','Ancienne clé',r.ancienne)+input('type_nouveau','Type cible (vide = même type)',r.type_nouveau)+input('nouvelle','Nouvelle clé',r.nouvelle)+input('motif','Motif',r.motif):
   input('code','Code',r.code,!nouveau)+select('nature','Nature',['ET','ST','EA','SA'],r.nature||'ET',!nouveau)+input('libelle','Libellé standard',r.libelle)+input('categorie','Catégorie',r.categorie)+input('teletransmission','Télétransmission',r.teletransmission)+input('types','Types (séparés par ;)',(r.types||[]).join('; '))}</div>
   <div class="erreur-form" id="ref-code-error" role="alert"></div>
   ${ed?`<div class="ref-code-actions">${!corr||nouveau?'<button class="prim" id="ref-code-save" type="submit">Enregistrer dans le brouillon</button>':''}${nouveau?'':'<button class="danger" id="ref-code-delete" type="button">Supprimer</button>'}</div>`:
   `<p>Révision publiée en lecture seule.</p><button id="ref-code-draft" type="button">${E.cycle.brouillon?'Reprendre le brouillon':'Modifier : créer un brouillon'}</button>`}
  </form></aside>`;
}
function brancherDetailCode(row,lex,ed,nouveau,corr=false) {
 const fermer=()=>{const cle=E.refCodeForm?.cle;E.refCodeForm=null;vueCodesReferentiel();const ligne=[...document.querySelectorAll('[data-ref-code]')].find(r=>r.dataset.refCode===cle);(ligne||document.querySelector('#ref-codes-add')).focus();};
 document.querySelector('#ref-code-close').onclick=fermer;
 const form=document.querySelector('#ref-code-form'), erreur=document.querySelector('#ref-code-error');
 if(!ed){document.querySelector('#ref-code-draft').onclick=async()=>{E.refSource='';if(E.cycle.brouillon){await chargerReferentiel();vueReferentiel();}else await actionRef({action:'creer_brouillon'},'Brouillon créé.');};return;}
 const lire=()=>{
  const donnees=new FormData(form), champs={};
  for(const [k,v] of donnees)champs[k]=v;
  if(lex)champs.dictionnaire_es=form.elements.dictionnaire_es.checked;
  return champs;
 };
 const valider=()=>{
  const champs=lire();let message='';
  if(lex&&!/^[A-Z0-9]+(?:_[A-Z0-9]+)*$/.test(champs.abreviation||''))message='Utilisez des majuscules, chiffres et des mots séparés par _ pour l’abréviation.';
  if(!lex&&!corr&&nouveau&&!/^[A-Z0-9_]{2,9}$/.test(champs.code||''))message='Le code doit contenir 2 à 9 caractères : A–Z, 0–9 ou _.';
  if(corr&&nouveau&&!String(champs.motif||'').trim())message='Le motif de la correspondance est obligatoire.';
  erreur.textContent=message;return !message;
 };
 form.oninput=valider;
 form.onsubmit=async e=>{
  e.preventDefault();if(corr&&!nouveau)return;if(!valider()||!form.reportValidity())return;
  const bouton=document.querySelector('#ref-code-save');bouton.disabled=true;erreur.textContent='';
  try{await api('/api/referentiel/cycle/action',{action:'editer',modification:(nouveau?'ajouter_':'modifier_')+(corr?'correspondance':lex?'lexique':'code_es'),cible:row?.cle||'',champs:lire()});
   E.refCodeForm=null;await chargerReferentiel();vueReferentiel();toast('Entrée enregistrée dans le brouillon.');
  }catch(error){erreur.textContent=error.message;}finally{bouton.disabled=false;}
 };
 document.querySelector('#ref-code-delete')?.addEventListener('click',()=>confirmer('Supprimer cette entrée du brouillon ?',lex?row.mot:row.cle,'Supprimer',async()=>{
  try{await api('/api/referentiel/cycle/action',{action:'editer',modification:'supprimer_'+(corr?'correspondance':lex?'lexique':'code_es'),cible:row.cle});E.refCodeForm=null;await chargerReferentiel();vueReferentiel();toast('Entrée supprimée du brouillon.');}
  catch(error){toast(error.message,true);}
 }));
}
document.addEventListener('keydown',e=>{
 if(e.key==='Escape'&&!e.defaultPrevented&&document.querySelector('#modale')?.hidden!==false&&document.querySelector('.ref-code-detail')){
  e.preventDefault();document.querySelector('#ref-code-close').click();
 }
},true);
