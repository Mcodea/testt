"use strict";
/* Présentation OGIAS 0.31 — hors ligne, sans nouvelles règles industrielles. */
const V31 = (() => {
 // Lucide 0.468.0, ISC : géométries embarquées dans assets/lucide/sprite.svg.
 const icones={home:'house',folder:'folder',layers:'layers',settings:'settings',info:'info',
  search:'search',check:'check',arrow:'arrow-right',close:'x',bolt:'zap',alert:'triangle-alert',
  pie:'chart-pie',cpu:'cpu',list:'list',chevron:'chevron-right',clipboard:'clipboard-list',
  menu:'menu',spark:'sparkles',shield:'shield-check',sun:'sun',moon:'moon'};
 const icon=(name,size=19)=>{
  const id=Object.hasOwn(icones,name)?icones[name]:icones.layers;
  const dimension=Number.isFinite(Number(size))?Math.max(8,Math.min(64,Number(size))):19;
  return `<svg class="v31-icon" data-lucide="${id}" aria-hidden="true" width="${dimension}" height="${dimension}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linejoin="round" stroke-linecap="round"><use href="assets/lucide/sprite.svg#${id}"></use></svg>`;
 };
 const esc=x=>String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 const state={detail:false,navOpen:false,searchOpen:false};
 const steps=[['ouvrage','Équipements','#/inventaire'],['es','Liste des E/S','#/es'],['materiel','Matériel','#/materiel'],['variables','Variables','#/variables'],['recette','Recette','#/recette']];
 function init(){
  const bar=document.createElement('nav');bar.id='v31-sidebar';bar.className='v31-sidebar';bar.setAttribute('aria-label','Navigation principale');
  bar.innerHTML=`<a class="v31-logo" href="#/ouvrages" data-nav="#/ouvrages" title="OGIAS"><img src="assets/ogias-icone-512.png" alt="OGIAS"></a>
   <div class="v31-side-links"><a href="#/dashboard" data-nav="#/dashboard" data-view="dashboard" title="Tableau de bord" aria-label="Tableau de bord">${icon('home')}<span>Tableau de bord</span></a>
   <a href="#/ouvrages" data-nav="#/ouvrages" data-view="accueil" title="Mes ouvrages" aria-label="Mes ouvrages">${icon('folder')}<span>Ouvrages</span></a>
   <a href="#/referentiel" data-nav="#/referentiel" data-view="referentiel" title="Référentiel métier" aria-label="Référentiel métier">${icon('layers')}<span>Référentiel modèles</span></a>
   <a href="#/inventaire" data-nav="#/inventaire" data-view="ouvrage" title="Ouvrages / Équipements" aria-label="Équipements">${icon('folder')}<span>Équipements</span></a>
   <a href="#/es" data-nav="#/es" data-view="es" title="Liste des E/S" aria-label="Liste des E/S">${icon('list')}<span>Liste des E/S</span></a>
   <a href="#/materiel" data-nav="#/materiel" data-view="materiel" title="Configuration matérielle" aria-label="Configuration matérielle">${icon('cpu')}<span>Config. matérielle</span></a>
   <a href="#/variables" data-nav="#/variables" data-view="variables" title="Tags / Variables" aria-label="Tags / Variables">${icon('layers')}<span>Tags / Variables</span></a>
   <a href="#/recette" data-nav="#/recette" data-view="recette" title="Recette / Exports" aria-label="Recette / Exports">${icon('clipboard')}<span>Recette / Exports</span></a></div>
   <div class="v31-side-bottom"><button type="button" id="v31-settings" title="Thème clair / sombre" aria-label="Thème clair / sombre">${icon(document.documentElement.dataset.theme==='dark'?'sun':'moon')}</button>
   <button type="button" id="v31-about" title="À propos" aria-label="À propos">${icon('info')}</button></div>`;
  document.body.prepend(bar);
  const top=document.createElement('div');top.id='v31-top';top.className='v31-top';top.innerHTML=`<div class="v31-page-info"><div id="v31-breadcrumb" class="v31-breadcrumb"></div><h1 id="v31-title"></h1></div>
    <div class="v31-top-actions"><button type="button" id="v31-global-search" class="v31-search-trigger">${icon('search',17)}<span>Rechercher dans OGIAS</span><kbd>Ctrl K</kbd></button>
    <button type="button" id="v31-current" class="v31-current" title="Fiche de l’ouvrage courant"></button></div>`;
  const workspace=document.getElementById('v30-workspace');workspace.parentNode.insertBefore(top,workspace);
  const progress=document.createElement('nav'); progress.className='v31-progress';progress.id='v31-progress';progress.setAttribute('aria-label','Étapes de l’ouvrage'); top.after(progress);
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
   <label for="v31-query">Rechercher un repère, une variable ou un équipement</label><input id="v31-query" autocomplete="off" placeholder="Nom, repère ou mot-clé…">
   <div id="v31-results"></div><button type="button" id="v31-search-close">Fermer</button></div>`;
  document.body.append(overlay);overlay.onclick=e=>{if(e.target===overlay)overlay.remove();};overlay.querySelector('#v31-search-close').onclick=()=>overlay.remove();
  const input=overlay.querySelector('input');input.focus();
  input.oninput=()=>{const q=input.value.toLocaleLowerCase('fr');const eqs=((typeof E !== "undefined" ? E.ouvrage?.equipements : [])||[]);const matches=q.length>1?eqs.filter(x=>`${x.pcf} ${x.libelle} ${x.type}`.toLocaleLowerCase('fr').includes(q)).slice(0,20):[];
   overlay.querySelector('#v31-results').innerHTML=matches.map(x=>`<button type="button" class="v31-result" data-id="${esc(x.ident)}"><b>${esc(x.pcf)}</b> ${esc(x.libelle)}</button>`).join('')||'<p class="v31-muted">Saisissez deux caractères pour chercher dans les équipements de l’ouvrage courant.</p>';
   overlay.querySelectorAll('[data-id]').forEach(b=>b.onclick=()=>{overlay.remove();allerOuvrage({nature:'eq',valeur:b.dataset.id});});};
 }
 function render(E, ETAPES,etatEtape,vueEtape){
  const creation=E.vue==='ouvrage'&&E.ouvrage?.en_conception, has=E.ouvrage?.ouvert&&!creation;
  const titles={accueil:'Mes ouvrages',dashboard:'Tableau de bord de l’ouvrage',ouvrage:creation?'Créer un ouvrage':'Équipements',es:'Liste des E/S',materiel:'Matériel',variables:'Variables',supervision:'Variables',adressage:'Variables',recette:'Recette',referentiel:'Référentiel métier'};
  const title=titles[E.vue]||'OGIAS';document.getElementById('v31-title').textContent=title;
  document.getElementById('v31-breadcrumb').textContent=has?`Ouvrages › ${E.ouvrage.prefixe||E.ouvrage.identification?.code_ouvrage||'Ouvrage'} › ${title}`:E.vue==='referentiel'?'OGIAS › Bibliothèque métier':'OGIAS › Ouvrages';
  const current=document.getElementById('v31-current');current.hidden=!has;
  if(has){const o=E.ouvrage;const id=o.prefixe||o.identification?.code_ouvrage||'Ouvrage';current.innerHTML=`<span class="v31-avatar">${esc(String(id).slice(0,2))}</span><span><b>${esc(o.identification?.libelle||id)}</b><small>${esc(id)} · ${esc(o.identification?.mode||'')}</small></span>`;current.onclick=()=>naviguer('#/dashboard');}
  document.querySelectorAll('[data-view]').forEach(el=>el.classList.toggle('active',el.dataset.view===E.vue));
  const progress=document.getElementById('v31-progress');progress.hidden=!has||E.vue==='referentiel'||E.vue==='accueil';
  let drawer=document.getElementById('v31-tree-trigger');
  if(!drawer){drawer=document.createElement('button');drawer.type='button';drawer.id='v31-tree-trigger';drawer.className='v31-secondary-header';drawer.innerHTML=icon('folder',16)+' Structure / ajouter';
    document.getElementById('v31-top').appendChild(drawer);
    drawer.onclick=()=>document.getElementById('vue').classList.toggle('v31-show-tree');
  }
  drawer.hidden=E.vue!=='ouvrage'||creation;
  if(!progress.hidden){progress.innerHTML=steps.map(([v,label,link],i)=>{const s=etatEtape(v,E.ouvrage),active=vueEtape(E.vue)===v;
    return `<button class="v31-step ${active?'active':''} ${s==='validée'?'done':''}" type="button" data-nav="${link}" title="${esc(label)} : ${esc(s)}"><span class="v31-step-mark">${s==='validée'?icon('check',12):i+1}</span>${label}</button>${i<4?'<span class="v31-step-dots" aria-hidden="true">····</span>':''}`;}).join('');}
  document.querySelector('#v30-workspace').classList.toggle('v31-new-creation',creation);
 }
 function refresh(E,ETAPES,etatEtape,vueEtape){
  render(E,ETAPES,etatEtape,vueEtape);
  const root=document.getElementById('vue');
  // Les commandes métier sont déplacées, jamais dupliquées : leurs événements restent actifs.
  if(E.vue==='es'){
    const target=root.querySelector('.es-compteurs');
    if(target){const bar=document.createElement('div');bar.className='v31-page-actions';
      for(const id of ['x-val-tout','x-val','es-export']){const b=root.querySelector('#'+id);if(b)bar.appendChild(b);}
      target.before(bar);
    }
  }
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
    materiel:{primary:['m-calc','m-valider','m-deval'],extra:['m-cartes','m-impl','x-val-tout','x-val','x-xl','x-ca','x-xsy','x-txt']},
    adressage:{primary:['ad-recalc','ad-app','ad-val'],extra:['ad-res','ad-tpk']},
    recette:{primary:['r-actualiser'],extra:[]},
    referentiel:{primary:['rf-creer','rf-ouvrir-b','rf-pub'],extra:['rf-hist','rf-exp','rf-voir-pub','rf-exp-b','rf-imp','rf-abandon'],inPlace:true}
  };
  if(actionGroups[E.vue]){
    const cfg=actionGroups[E.vue];const host=root.querySelector('.contenu')||root.querySelector('.ref-corps')||root.firstElementChild;
    if(cfg.inPlace){
      // Le bandeau du référentiel possède déjà son menu et ses écouteurs.
      // Garder ces mêmes boutons dans leur conteneur au changement de vue.
      const bar=root.querySelector('.bandeau-ref .actions');
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
