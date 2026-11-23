"use strict";
/* Présentation OGIAS 0.31 — hors ligne, sans nouvelles règles industrielles. */
const V31 = (() => {
 // Lucide 0.468.0, ISC : géométries embarquées dans assets/lucide/sprite.svg.
 const icones={home:'house',folder:'folder',layers:'layers',settings:'settings',info:'info',
  search:'search',check:'check',arrow:'arrow-right',close:'x',bolt:'zap',alert:'triangle-alert',
  pie:'chart-pie',cpu:'cpu',list:'list',chevron:'chevron-right',clipboard:'clipboard-list',
  menu:'menu',spark:'sparkles',shield:'shield-check',sun:'sun',moon:'moon'};
 // Arborescence des équipements : ancrée à gauche au-delà de 1280 px (le bouton la masque),
 // tiroir au-dessous (le bouton l'ouvre). Seul l'affichage change : aucun événement métier.
 const ARBRE_ANCRE=typeof matchMedia==='function'?matchMedia('(min-width:1280px)'):{matches:false};
 function majArbre(){
  const b=document.getElementById('v31-tree-trigger'),vue=document.getElementById('vue');if(!b||!vue)return;
  const ouverte=ARBRE_ANCRE.matches?!vue.classList.contains('v31-show-tree'):vue.classList.contains('v31-show-tree');
  b.setAttribute('aria-pressed',String(ouverte));
  b.title=ouverte?"Masquer l'arborescence de l'ouvrage":"Afficher l'arborescence de l'ouvrage (UF, équipements, ajout et import)";
 }
 if(ARBRE_ANCRE.addEventListener)ARBRE_ANCRE.addEventListener('change',majArbre);
 const icon=(name,size=19)=>{
  const id=Object.hasOwn(icones,name)?icones[name]:icones.layers;
  const dimension=Number.isFinite(Number(size))?Math.max(8,Math.min(64,Number(size))):19;
  return `<svg class="v31-icon" data-lucide="${id}" aria-hidden="true" width="${dimension}" height="${dimension}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linejoin="round" stroke-linecap="round"><use href="assets/lucide/sprite.svg#${id}"></use></svg>`;
 };
 const esc=x=>String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 const state={detail:false,navOpen:false,searchOpen:false};
 const steps=[['ouvrage','Équipements','#/inventaire'],['es','Liste des E/S','#/es'],['materiel','Matériel','#/materiel'],['variables','Variables','#/variables'],['recette','Recette','#/recette']];
 function init(){
  // Refonte, lot 2a : barre de titre (menus, recherche, ouvrage courant, thème), explorateur et onglets de
  // documents remplacent la barre latérale, l'en-tête et la frise des étapes (voir ogias-coque.js).
  Coque.init();
  document.getElementById('v31-global-search').onclick=()=>globalSearch();
  const boutonTheme=document.getElementById('v31-settings');
  boutonTheme.onclick=()=>{const dark=document.documentElement.dataset.theme==='dark';document.documentElement.dataset.theme=dark?'light':'dark';try{localStorage.setItem('ogias-ui-theme',dark?'light':'dark');}catch(e){}boutonTheme.innerHTML=icon(dark?'moon':'sun');boutonTheme.title=dark?'Passer au thème sombre':'Passer au thème clair';};
  document.getElementById('v31-about').onclick=()=>{
   const m=ouvrirModale(`<div class="boite-tete"><h2>À propos d'OGIAS</h2></div><div class="boite-corps">
    <p>OGIAS 0.32 — préparation des données industrielles · Exports non qualifiés.</p>
    <h3>Licences des ressources graphiques</h3><ul>
    <li><a data-licence href="assets/fonts/LICENSE-Inter.txt" target="_blank" rel="noopener">Inter 4.1 — SIL Open Font License 1.1</a></li>
    <li><a data-licence href="assets/fonts/LICENSE-JetBrainsMono.txt" target="_blank" rel="noopener">JetBrains Mono 2.304 — SIL Open Font License 1.1</a></li>
    <li><a data-licence href="assets/lucide/LICENSE.txt" target="_blank" rel="noopener">Lucide 0.468.0 — ISC</a></li></ul></div>
    <div class="boite-pied"><button data-fermer>Fermer</button></div>`);
   m.querySelector('[data-fermer]').focus();
   E.apresFermeture=()=>document.getElementById('v31-about').focus();
  };
  document.addEventListener('keydown',e=>{if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==='k'){e.preventDefault();globalSearch();}if(e.key==='Escape')document.querySelector('#v31-search-dialog')?.remove();});
 }
 function globalSearch(){
  document.querySelector('#v31-search-dialog')?.remove();const overlay=document.createElement('div');overlay.id='v31-search-dialog';overlay.className='v31-overlay';overlay.innerHTML=`<div class="v31-search-box" role="dialog" aria-modal="true" aria-label="Rechercher dans OGIAS">
   <label for="v31-query">Rechercher un repère, une variable, une adresse ou un libellé</label><input id="v31-query" autocomplete="off" placeholder="Nom, repère ou mot-clé…">
   <div id="v31-results"></div><button type="button" id="v31-search-close">Fermer</button></div>`;
  document.body.append(overlay);overlay.onclick=e=>{if(e.target===overlay)overlay.remove();};overlay.querySelector('#v31-search-close').onclick=()=>overlay.remove();
  const input=overlay.querySelector('input');input.focus();
  // V1-5-06 : la recherche porte sur les repères, les variables, les adresses et les libellés (serveur, ouvrage ouvert).
  const zone=overlay.querySelector('#v31-results');let seq=0;
  zone.innerHTML='<p class="v31-muted">Saisissez deux caractères pour chercher un repère, une variable, une adresse ou un libellé.</p>';
  input.oninput=async()=>{const q=input.value.trim();const mon=++seq;
   if(q.length<2){zone.innerHTML='<p class="v31-muted">Saisissez deux caractères pour chercher un repère, une variable, une adresse ou un libellé.</p>';return;}
   let r;try{r=await api('/api/recherche?q='+encodeURIComponent(q));}catch(e){if(mon===seq)zone.innerHTML=`<p class="v31-muted">${esc(e.message)}</p>`;return;}
   if(mon!==seq)return;
   zone.innerHTML=(r.resultats.map((x,i)=>`<button type="button" class="v31-result" data-i="${i}" data-nature="${x.nature}"><b>${esc(x.titre)}</b> <span class="v31-muted">${esc(x.detail||'')}</span> <small>${x.nature==='equipement'?'équipement':'variable'} · ${esc(x.critere)}</small></button>`).join('')||'<p class="v31-muted">Aucun résultat.</p>')
    +(r.complet?'':`<p class="v31-muted">${r.total} résultats : précisez la recherche.</p>`);
   zone.querySelectorAll('[data-i]').forEach(b=>b.onclick=()=>{const x=r.resultats[+b.dataset.i];overlay.remove();
    if(x.nature==='equipement')return allerOuvrage({nature:'eq',valeur:x.ident_eq});
    E.v31Selected=x.titre;E.v31VarDetail=true;E.v31Query=x.titre;naviguer('#/variables');});};
 }
 // Barre d'état inférieure : uniquement des informations réelles de la session (ouvrage, étape, référentiel).
 function barreEtat(E,ETAPES,etatEtape,vueEtape,has){
  const el=document.getElementById('v30-status');if(!el)return;
  const o=E.ouvrage||{};const etape=(ETAPES||[]).find(x=>x[1]===vueEtape(E.vue));
  const rev=E.cycle?.revision?`R${String(E.cycle.revision).padStart(4,'0')}`:'non publié';
  const sep='<span class="v30-status-separator" aria-hidden="true"></span>';
  el.innerHTML=[`<span title="Ouvrage actif">${icon('folder',13)} ${has?esc(o.prefixe||'Ouvrage')+' · '+esc(o.identification?.mode||''):'Aucun ouvrage ouvert'}</span>`,
   has&&etape?`<span title="Étape du parcours">${icon('list',13)} ${esc(etape[2])} : ${esc(etatEtape(etape[1],o))}</span>`:'',
   `<span title="Révision du référentiel métier">${icon('layers',13)} Référentiel ${esc(rev)}</span>`,
   `<span>${icon('shield',13)} Adresses validées protégées</span>`].filter(Boolean).join(sep)
   +`<span class="v30-status-right">${icon('info',13)} Exports industriels non qualifiés · OGIAS 0.32</span>`;
 }
 function render(E, ETAPES,etatEtape,vueEtape){
  const creation=E.vue==='ouvrage'&&E.ouvrage?.en_conception, has=E.ouvrage?.ouvert&&!creation;
  // Écran courant exposé au CSS (attribut propre à cette couche : les anciennes règles data-view restent inactives).
  document.body.dataset.ecran=E.vue||'';
  barreEtat(E,ETAPES,etatEtape,vueEtape,has);
  const titles={accueil:'Mes ouvrages',dashboard:'Tableau de bord de l’ouvrage',ouvrage:creation?'Créer un ouvrage':'Équipements',es:'Liste des E/S',materiel:'Matériel',variables:'Variables',supervision:'Variables',adressage:'Variables',recette:'Recette',referentiel:'Référentiel métier',standards:'Standards d’ingénierie',apprentissage:'Apprentissage des formats',rapprochement:'Rapprochement',grille:'Grille d’ingénierie'};
  Coque.render(E,ETAPES,etatEtape,vueEtape);
  const title=titles[E.vue]||'OGIAS';const h1=document.getElementById('v31-title');if(h1)h1.textContent=title;
  const current=document.getElementById('v31-current');current.hidden=!has;
  if(has){const o=E.ouvrage;const id=o.prefixe||o.identification?.code_ouvrage||'Ouvrage';current.innerHTML=`<b>${esc(id)}</b><span>${esc(o.identification?.libelle||'')}</span>`;current.title=`${o.identification?.libelle||id} · ${o.identification?.mode||''} — tableau de bord`;current.onclick=()=>naviguer('#/dashboard');}
  document.querySelectorAll('[data-view]').forEach(el=>el.classList.toggle('active',el.dataset.view===E.vue));
  let drawer=document.getElementById('v31-tree-trigger');
  if(!drawer){drawer=document.createElement('button');drawer.type='button';drawer.id='v31-tree-trigger';drawer.className='v31-secondary-header';drawer.innerHTML=icon('folder',16)+' Structure / ajouter';
    Coque.actions().appendChild(drawer);
    // Au-delà de 1280 px l'arborescence est ancrée à gauche : le bouton la masque ou la réaffiche.
    drawer.onclick=()=>{const vue=document.getElementById('vue');vue.classList.toggle('v31-show-tree');majArbre();};
  }
  drawer.hidden=E.vue!=='ouvrage'||creation;
  majArbre();
  document.querySelector('#v30-workspace').classList.toggle('v31-new-creation',creation);
 }
 function refresh(E,ETAPES,etatEtape,vueEtape){
  render(E,ETAPES,etatEtape,vueEtape);
  const root=document.getElementById('vue');
  // Les commandes métier sont déplacées, jamais dupliquées : leurs événements restent actifs.
  // Liste des E/S : commandes au ruban de l'écran depuis la refonte (lot 5b, rubanES dans app.js).
  if(E.vue==='supervision'){
    const target=root.querySelector('.v29-title')||root.querySelector('.titre');
    if(target){const bar=document.createElement('div');bar.className='v31-page-actions';
      for(const id of ['v29-apercu','v29-controle','v29-export']){const b=root.querySelector('#'+id);if(b)bar.appendChild(b);}
      target.before(bar);
    }
  }
  // Les actions historiques encore disponibles sont redistribuées sans recréation de bouton.
  // La validation reste confiée à leurs événements/API et aux états disabled d'origine.
  const actionGroups={
    // materiel : commandes au ruban de l'écran depuis la refonte (lot 5c, rubanMateriel dans app.js).
    adressage:{primary:['ad-recalc','ad-app','ad-val'],extra:['ad-res','ad-tpk']},
    recette:{primary:['r-dossier'],extra:['r-actualiser'],inPlace:true,bar:'.rc-hero-actions'},
    referentiel:{primary:['rf-creer','rf-ouvrir-b','rf-pub'],extra:['rf-hist','rf-exp','rf-voir-pub','rf-exp-b','rf-imp','rf-abandon'],inPlace:true}
  };
  if(actionGroups[E.vue]){
    const cfg=actionGroups[E.vue];const host=root.querySelector('.contenu')||root.querySelector('.ref-corps')||root.firstElementChild;
    if(cfg.inPlace){
      // Le bandeau du référentiel possède déjà son menu et ses écouteurs.
      // Garder ces mêmes boutons dans leur conteneur au changement de vue.
      const bar=root.querySelector(cfg.bar||'.bandeau-ref .actions');
      if(bar){bar.classList.add('v31-page-actions');
        cfg.primary.forEach(id=>root.querySelector('#'+id)?.classList.add('v31-primary-action'));
        cfg.extra.forEach(id=>root.querySelector('#'+id)?.classList.remove('prim'));
      }
    }else if(host){const bar=document.createElement('div');bar.className='v31-page-actions';bar.setAttribute('aria-label','Actions de '+E.vue);
      const primaries=cfg.primary.map(id=>root.querySelector('#'+id)).filter(Boolean);
      primaries.forEach((b,i)=>{if(i===0)b.classList.add('v31-primary-action');else b.classList.remove('prim');bar.appendChild(b)});
      const extras=cfg.extra.map(id=>root.querySelector('#'+id)).filter(Boolean);
      if(extras.length){const more=document.createElement('details');more.className='v31-actions-more';
        more.innerHTML='<summary title="Autres commandes">Autres actions</summary>';
        const area=document.createElement('div');area.className='v31-actions-menu';extras.forEach(b=>area.appendChild(b));more.appendChild(area);bar.appendChild(more);
      }
      if(bar.childElementCount)host.insertBefore(bar,host.firstChild);
    }
  }
  // Aide en infobulle uniquement si la note ne contient pas de commande.
  root.querySelectorAll('p.note').forEach(el=>{
    if(el.querySelector('button,a,input,select'))return;
    const button=document.createElement('button');button.type='button';button.className='v31-help-note';
    button.title=el.textContent.trim();button.setAttribute('aria-label','Information : '+el.textContent.trim());button.innerHTML=icon('info',15);
    el.replaceWith(button);
  });
}
 return {init,render,refresh,icon,esc};
})();
V31.init();
