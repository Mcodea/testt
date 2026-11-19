"use strict";
/* OGIAS — coque de bureau (refonte de l'interface, lot 2a, 18/11/2026).

   Barre de titre avec menus, explorateur (navigation et parcours de l'ouvrage), onglets de documents.
   Couche de présentation seulement : chaque commande appelle une fonction ou une route qui existait déjà
   (naviguer, api('/api/nouveau'), recherche globale…). Aucune règle métier ici. */
// Thème mémorisé, appliqué avant le premier rendu (repris de l'ancienne coque V30, retirée au lot 7c)
try { if (localStorage.getItem("ogias-ui-theme") === "dark") document.documentElement.dataset.theme = "dark"; } catch (e) { /* stockage indisponible */ }
const Coque = (() => {
 const esc = x => String(x ?? "").replace(/[&<>"']/g, c => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"}[c]));
 // Tracés simples dessinés pour OGIAS (24 × 24, trait) : aucune ressource distante.
 const TRACES = {
  dossier: '<path d="M3 7V5a2 2 0 0 1 2-2h5l2 3h7a2 2 0 0 1 2 2v11H3z"/>',
  bord: '<rect x="3" y="3" width="7" height="9" rx="1"/><rect x="14" y="3" width="7" height="5" rx="1"/><rect x="14" y="12" width="7" height="9" rx="1"/><rect x="3" y="16" width="7" height="5" rx="1"/>',
  referentiel: '<path d="m12 3 9 5-9 5-9-5zM3 13l9 5 9-5"/>',
  chercher: '<circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/>',
  fermer: '<path d="M6 6l12 12M18 6 6 18"/>',
  coche: '<path d="m6 12 4 4 8-8"/>',
  replier: '<path d="m15 6-6 6 6 6"/>',
  bas: '<path d="m6 9 6 6 6-6"/>',
  // Symboles OGIAS des maillons du fil de l'information (lot 4), dérivés du motif du logo : nœud – bloc – nœud.
  fil: '<circle cx="4" cy="12" r="2.5"/><rect x="9.5" y="9.5" width="5" height="5" rx="1"/><circle cx="20" cy="12" r="2.5"/><path d="M6.5 12h3M14.5 12h3"/>',
  equipement: '<rect x="4" y="4" width="16" height="16" rx="3"/><circle cx="12" cy="12" r="4"/><path d="M12 8v-4"/>',
  es: '<circle cx="3.5" cy="12" r="1.5"/><path d="M5 12h4"/><rect x="9" y="6" width="12" height="12" rx="2"/><path d="M13 10v4M17 10v4"/>',
  carte: '<rect x="5" y="3" width="14" height="15" rx="1.5"/><path d="M8 18v3M12 18v3M16 18v3M8 7.5h8M8 11.5h5"/>',
  variable: '<path d="M8 4H6a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h2M16 4h2a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2h-2"/><path d="M9 12h6M12 9v6"/>',
  supervision: '<rect x="3" y="4" width="18" height="12" rx="1.5"/><path d="M8 20h8M12 16v4"/><path d="m6.5 12 3-3 2.5 2 5-4.5"/>',
  recette: '<path d="M9 4h6v3H9z"/><path d="M9 5.5H6a1 1 0 0 0-1 1V20a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1V6.5a1 1 0 0 0-1-1h-3"/><path d="m8.5 14 2.5 2.5 4.5-5"/>',
  alerte: '<path d="M12 3 2 20h20z"/><path d="M12 10v4M12 17h.01"/>',
  erreur: '<circle cx="12" cy="12" r="9"/><path d="M12 8v5M12 16h.01"/>',
  info: '<circle cx="12" cy="12" r="9"/><path d="M12 11v5M12 8h.01"/>',
  // Commandes du ruban (lot 5)
  plus: '<path d="M12 5v14M5 12h14"/>',
  importer: '<path d="M12 4v11M8 11l4 4 4-4M5 20h14"/>',
  valider: '<circle cx="12" cy="12" r="9"/><path d="m8 12 3 3 5-6"/>',
  modifier: '<path d="m4 20 1-4L16 5l3 3L8 19z"/><path d="m14 7 3 3"/>',
  ranger: '<path d="M3 7V5a2 2 0 0 1 2-2h5l2 3h7a2 2 0 0 1 2 2v11H3z"/><path d="M9 13h6M12 10v6"/>',
  supprimer: '<path d="M4 7h16M9 7V4h6v3M6 7l1 13h10l1-13"/>',
  groupe: '<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M3 9h18M8 13h8M8 16h5"/>',
 };
 const ico = (nom, t = 16) => `<svg class="o-ico" width="${t}" height="${t}" viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">${TRACES[nom] || ""}</svg>`;
 const ETAPES_PARCOURS = [["ouvrage", "Équipements", "#/inventaire"], ["es", "Liste des E/S", "#/es"],
   ["materiel", "Matériel", "#/materiel"], ["variables", "Variables", "#/variables"], ["recette", "Recette", "#/recette"]];
 const SYMBOLE_ETAPE = {ouvrage: "equipement", es: "es", materiel: "carte", variables: "variable", recette: "recette"};
 const SYMBOLE_ROUTE = {"#/ouvrages": "dossier", "#/dashboard": "bord", "#/inventaire": "equipement", "#/es": "es",
   "#/materiel": "carte", "#/variables": "variable", "#/recette": "recette", "#/referentiel": "referentiel", "#/standards": "bord"};
 const TITRES_ROUTE = {"#/ouvrages": "Mes ouvrages", "#/dashboard": "Tableau de bord", "#/inventaire": "Équipements",
   "#/es": "Liste des E/S", "#/materiel": "Matériel", "#/variables": "Variables", "#/recette": "Recette",
   "#/referentiel": "Référentiel métier", "#/standards": "Standards d'ingénierie"};
 const ROUTE_VUE = {accueil: "#/ouvrages", dashboard: "#/dashboard", ouvrage: "#/inventaire", es: "#/es", materiel: "#/materiel",
   variables: "#/variables", supervision: "#/variables", adressage: "#/variables", recette: "#/recette", referentiel: "#/referentiel", standards: "#/standards"};
 const etat = {documents: [], explorateur: true, menuOuvert: "", sortieOuverte: true, journal: []};
 try {
  etat.explorateur = localStorage.getItem("ogias-explorateur") !== "masque";
  etat.sortieOuverte = localStorage.getItem("ogias-sortie") !== "pliee";
 } catch (e) { /* stockage indisponible */ }

 // ------------------------------------------------------------------ menus
 // Chaque entrée : [libellé, raccourci affiché, action] ; "-" = séparateur. Les actions réutilisent l'existant.
 const MENUS = [
  ["Fichier", [["Mes ouvrages", "", () => naviguer("#/ouvrages")],
               ["Nouvel ouvrage neuf…", "", () => nouveau("Neuf")],
               ["Reprendre un projet existant…", "", () => nouveau("Existant")], "-",
               ["Fermer l'ouvrage", "", () => fermer(), () => !!E.ouvrage?.ouvert]]],
  ["Édition", [["Rechercher…", "Ctrl K", () => document.getElementById("v31-global-search")?.click()]]],
  ["Affichage", [["Thème clair ou sombre", "", () => document.getElementById("v31-settings")?.click()],
                 ["Afficher ou masquer l'explorateur", "Ctrl B", () => basculerExplorateur()]]],
  ["Ouvrage", [["Tableau de bord", "", () => naviguer("#/dashboard"), () => !!E.ouvrage?.ouvert], "-",
               ...ETAPES_PARCOURS.map(([, lib, route], i) => [`${i + 1}. ${lib}`, "", () => naviguer(route), () => !!E.ouvrage?.ouvert])]],
  ["Outils", [["Référentiel métier", "", () => naviguer("#/referentiel")], ["Standards d'ingénierie", "", () => naviguer("#/standards")]]],
  ["Aide", [["Aide d'OGIAS", "F1", () => window.open("aide.html", "_blank", "noopener")],
            ["Raccourcis clavier", "Ctrl /", () => Composants.aideRaccourcis()],
            ["À propos d'OGIAS", "", () => document.getElementById("v31-about")?.click()]]],
 ];
 function nouveau(mode) {
  api("/api/nouveau", {mode}).then(() => { E.ficheDraft = null; E.ficheDirty = false; allerOuvrage({nature: "ouvrage", valeur: ""}); })
   .catch(e => toast(e.message, true));
 }
 function fermer() { api("/api/fermer", {}).then(() => { E.ouvrage = null; etat.documents = []; naviguer("#/ouvrages"); }).catch(e => toast(e.message, true)); }
 function fermerMenus() {
  etat.menuOuvert = "";
  document.querySelectorAll(".o-menu").forEach(m => m.remove());   // menus ajoutés au corps de page
  document.querySelectorAll("#o-menus > button").forEach(b => b.setAttribute("aria-expanded", "false"));
 }
 function ouvrirMenu(i, focus) {
  fermerMenus();
  const bouton = document.querySelectorAll("#o-menus > button")[i];
  const [nom, entrees] = MENUS[i];
  etat.menuOuvert = nom;
  bouton.setAttribute("aria-expanded", "true");
  const m = document.createElement("div");
  m.className = "o-menu"; m.setAttribute("role", "menu"); m.setAttribute("aria-label", nom);
  m.innerHTML = entrees.map((x, k) => x === "-" ? '<hr role="separator">'
   : `<button type="button" role="menuitem" data-o-entree="${k}" ${x[3] && !x[3]() ? "disabled" : ""}><span>${esc(x[0])}</span><kbd>${esc(x[1])}</kbd></button>`).join("");
  const r = bouton.getBoundingClientRect();
  m.style.left = `${Math.round(r.left)}px`;
  document.body.append(m);
  m.querySelectorAll("[data-o-entree]").forEach(b => b.onclick = () => { fermerMenus(); entrees[+b.dataset.oEntree][2](); });
  if (focus) m.querySelector("button:not([disabled])")?.focus();
 }

 // ------------------------------------------------------------------ construction
 function init() {
  document.body.classList.add("o-coque");
  const titre = document.createElement("header");
  titre.id = "o-titre"; titre.className = "o-titre";
  titre.innerHTML = `<a class="o-marque" href="#/ouvrages" data-nav="#/ouvrages" title="OGIAS — Mes ouvrages"><img src="assets/ogias-icone-512.png" alt="">OGIAS</a>
   <nav id="o-menus" class="o-menus" role="menubar" aria-label="Menus">${MENUS.map(([nom], i) => `<button type="button" role="menuitem" aria-haspopup="true" aria-expanded="false" data-o-menu="${i}">${esc(nom)}</button>`).join("")}</nav>
   <span class="o-vide"></span>
   <button type="button" id="v31-global-search" class="o-commande">${ico("chercher", 14)}<span>Rechercher un repère, un équipement…</span><kbd>Ctrl K</kbd></button>
   <span class="o-vide"></span>
   <button type="button" id="v31-current" class="o-courant" title="Tableau de bord de l'ouvrage courant" hidden></button>
   <button type="button" id="v31-settings" class="o-titre-bouton" title="Thème clair / sombre" aria-label="Thème clair / sombre"></button>
   <button type="button" id="v31-about" class="o-titre-bouton" title="À propos" aria-label="À propos">?</button>`;
  document.body.prepend(titre);

  const expl = document.createElement("nav");
  expl.id = "o-explorateur"; expl.className = "o-explorateur"; expl.setAttribute("aria-label", "Explorateur");
  expl.hidden = !etat.explorateur;
  document.body.classList.toggle("o-sans-explorateur", !etat.explorateur);
  titre.after(expl);

  const docs = document.createElement("div");
  docs.id = "o-documents"; docs.className = "o-documents";
  docs.innerHTML = `<div class="o-onglets" role="tablist" aria-label="Documents ouverts"></div><div class="o-documents-actions"></div>`;
  const zone = document.getElementById("v30-workspace");
  zone.parentNode.insertBefore(docs, zone);

  // Ruban de l'écran (lot 5) : les commandes de l'écran, groupées par tâche, sous les onglets de documents.
  const ruban = document.createElement("section");
  ruban.id = "o-ruban"; ruban.className = "o-ruban"; ruban.hidden = true;
  ruban.setAttribute("role", "toolbar"); ruban.setAttribute("aria-label", "Ruban : commandes de l'écran");
  docs.after(ruban);

  // Fil de l'information (lot 4) : chaîne de l'équipement sélectionné, sous les onglets de documents.
  const fil = document.createElement("nav");
  fil.id = "o-fil"; fil.className = "o-fil"; fil.hidden = true;
  ruban.after(fil);
  fil.addEventListener("click", ev => { const m = ev.target.closest("[data-o-maillon]"); if (m) allerMaillon(m.dataset.oMaillon); });

  // Panneau de sortie (lot 2b) : contrôles de l'étape et journal des messages, sous la zone de travail.
  const sortie = document.createElement("section");
  sortie.id = "o-sortie"; sortie.className = "o-sortie"; sortie.setAttribute("aria-label", "Panneau de sortie");
  sortie.innerHTML = `<div class="o-sortie-tete" role="tablist" aria-label="Panneau de sortie">
     <button type="button" role="tab" data-o-sortie="controles" aria-selected="true">Contrôles <span class="o-compte" data-o-compte="controles"></span></button>
     <button type="button" role="tab" data-o-sortie="journal" aria-selected="false">Journal <span class="o-compte" data-o-compte="journal"></span></button>
     <span class="o-sortie-resume" aria-live="polite"></span>
     <button type="button" class="o-sortie-plier" aria-expanded="true" title="Réduire le panneau de sortie" aria-label="Réduire le panneau de sortie">${ico("bas", 14)}</button></div>
   <div class="o-sortie-corps" data-o-sortie-panneau="controles" role="tabpanel"><p class="o-sortie-vide">Aucun contrôle pour cet écran.</p></div>
   <div class="o-sortie-corps" data-o-sortie-panneau="journal" role="tabpanel" hidden><ol class="o-journal"></ol><p class="o-sortie-vide">Aucun message depuis l'ouverture d'OGIAS.</p></div>`;
  zone.after(sortie);
  sortie.classList.toggle("plie", !etat.sortieOuverte);
  sortie.querySelector(".o-sortie-plier").setAttribute("aria-expanded", String(etat.sortieOuverte));
  sortie.addEventListener("click", ev => {
   const o = ev.target.closest("[data-o-sortie]");
   if (o) { ongletSortie(o.dataset.oSortie); if (!etat.sortieOuverte) plierSortie(); return; }
   if (ev.target.closest(".o-sortie-plier")) plierSortie();
  });

  titre.addEventListener("click", ev => {
   const b = ev.target.closest("[data-o-menu]");
   if (!b) return;
   const i = +b.dataset.oMenu;
   if (etat.menuOuvert === MENUS[i][0]) fermerMenus(); else ouvrirMenu(i, false);
  });
  titre.addEventListener("mouseover", ev => {             // menu ouvert : survoler un autre titre l'ouvre
   const b = ev.target.closest("[data-o-menu]");
   if (b && etat.menuOuvert && etat.menuOuvert !== MENUS[+b.dataset.oMenu][0]) ouvrirMenu(+b.dataset.oMenu, false);
  });
  document.addEventListener("click", ev => { if (etat.menuOuvert && !ev.target.closest(".o-menu, #o-menus")) fermerMenus(); });
  document.addEventListener("keydown", ev => {
   if (etat.menuOuvert) {
    const m = document.querySelector(".o-menu");
    const items = m ? [...m.querySelectorAll("button:not([disabled])")] : [];
    const k = items.indexOf(document.activeElement);
    const i = MENUS.findIndex(x => x[0] === etat.menuOuvert);
    if (ev.key === "Escape") { ev.preventDefault(); fermerMenus(); document.querySelectorAll("#o-menus > button")[i]?.focus(); }
    else if (ev.key === "ArrowDown") { ev.preventDefault(); items[(k + 1) % items.length]?.focus(); }
    else if (ev.key === "ArrowUp") { ev.preventDefault(); items[(k - 1 + items.length) % items.length]?.focus(); }
    else if (ev.key === "ArrowRight") { ev.preventDefault(); ouvrirMenu((i + 1) % MENUS.length, true); }
    else if (ev.key === "ArrowLeft") { ev.preventDefault(); ouvrirMenu((i - 1 + MENUS.length) % MENUS.length, true); }
    return;
   }
   if (ev.target.closest?.("[data-o-menu]") && (ev.key === "ArrowDown" || ev.key === "Enter" || ev.key === " ")) {
    ev.preventDefault(); ouvrirMenu(+ev.target.closest("[data-o-menu]").dataset.oMenu, true); return;
   }
   if ((ev.ctrlKey || ev.metaKey) && ev.key.toLowerCase() === "b") { ev.preventDefault(); basculerExplorateur(); }
   if (ev.key === "F1") { ev.preventDefault(); window.open("aide.html", "_blank", "noopener"); }
  });
  docs.addEventListener("click", ev => {
   const f = ev.target.closest("[data-o-fermer]");
   if (!f) return;
   ev.preventDefault(); ev.stopPropagation();
   const route = f.dataset.oFermer, actif = route === ROUTE_VUE[E.vue];
   const i = etat.documents.indexOf(route);
   etat.documents = etat.documents.filter(x => x !== route);
   if (actif) naviguer(etat.documents[Math.max(0, i - 1)] || "#/ouvrages");
   else ongletsDocuments(E);
  });
 }
 function basculerExplorateur() {
  etat.explorateur = !etat.explorateur;
  try { localStorage.setItem("ogias-explorateur", etat.explorateur ? "visible" : "masque"); } catch (e) { /* stockage indisponible */ }
  document.getElementById("o-explorateur").hidden = !etat.explorateur;
  document.body.classList.toggle("o-sans-explorateur", !etat.explorateur);
 }

 // ------------------------------------------------------------------ ruban de l'écran (lot 5)
 /** Range les commandes EXISTANTES de l'écran dans le ruban. Les boutons sont déplacés, jamais recréés : leurs
     écouteurs, identifiants et états (désactivé, infobulle) restent ceux posés par l'écran.
     groupes : [{nom, commandes: [{el, icone, grand?, libelle?}]}] ; null ou vide : ruban masqué. */
 function ranger(groupes) {
  const r = document.getElementById("o-ruban");
  if (!r) return;
  const garder = (groupes || []).flatMap(g => g.commandes.map(c => c.el)).filter(Boolean);
  garder.forEach(el => el.remove());
  r.replaceChildren();
  const utiles = (groupes || []).map(g => ({...g, commandes: g.commandes.filter(c => c.el)})).filter(g => g.commandes.length);
  r.hidden = !utiles.length;
  document.body.classList.toggle("o-avec-ruban", !r.hidden);
  for (const g of utiles) {
   const groupe = document.createElement("div");
   groupe.className = "o-rb-groupe"; groupe.setAttribute("role", "group"); groupe.setAttribute("aria-label", g.nom);
   const cmds = document.createElement("div");
   cmds.className = "o-rb-cmds";
   for (const c of g.commandes) {
    const el = c.el;
    el.classList.add("o-cmd", c.grand ? "o-cmd-grand" : "o-cmd-petit");
    el.classList.remove("prim", "danger", "lien");
    if (c.danger) el.classList.add("o-cmd-danger");
    if (!el.dataset.oCmd) {                                 // une seule fois par bouton : icône et libellé court
     el.dataset.oCmd = "1";
     if (c.libelle) { if (!el.title) el.title = el.textContent.trim(); el.textContent = c.libelle; }
     el.insertAdjacentHTML("afterbegin", ico(c.icone || "plus", c.grand ? 22 : 15));
    }
    cmds.append(el);
   }
   groupe.append(cmds);
   groupe.insertAdjacentHTML("beforeend", `<span class="o-rb-nom">${esc(g.nom)}</span>`);
   r.append(groupe);
  }
 }

 // ------------------------------------------------------------------ fil de l'information (lot 4)
 const MAILLONS = [["equipement", "equipement", "Équipement"], ["es", "es", "E/S physiques"], ["carte", "carte", "Carte et voies"],
   ["variables", "variable", "Variables"], ["supervision", "supervision", "Supervision"]];
 const MAILLON_VUE = {ouvrage: "equipement", es: "es", materiel: "carte", variables: "variables", supervision: "variables", adressage: "variables"};
 let jetonFil = 0, filCourant = null;
 /** Équipement dont on affiche le fil : sélection de l'arborescence (Équipements) ou variable ouverte (Variables). */
 function identFil(E) {
  if (!E.ouvrage?.ouvert || E.ouvrage?.en_conception) return "";
  if (E.vue === "ouvrage" && E.sel?.nature === "eq") return E.sel.valeur || "";
  if (["variables", "supervision", "adressage"].includes(E.vue) && E.v31VarDetail && E.v31Selected)
   return (E.detailEtape?.lignes || []).find(x => x.nom === E.v31Selected)?.ident_eq || "";
  return "";
 }
 async function majFil() {
  const el = document.getElementById("o-fil");
  if (!el) return;
  const ident = identFil(E), j = ++jetonFil;
  if (!ident) { el.hidden = true; filCourant = null; return; }
  let f;
  try { f = await api(`/api/fil?ident=${encodeURIComponent(ident)}`); } catch (e) { if (j === jetonFil) el.hidden = true; return; }
  if (j !== jetonFil) return;                               // une sélection plus récente a pris le relais
  filCourant = f;
  const courant = MAILLON_VUE[E.vue];
  el.setAttribute("aria-label", `Fil de l'information de ${f.repere}`);
  el.innerHTML = `<span class="o-fil-titre">${ico("fil", 16)}<span class="mono">${esc(f.repere)}</span></span>`
   + MAILLONS.filter(([cle]) => f[cle]).map(([cle, symbole, nom], i) => {
     const m = f[cle];
     return `${i ? '<span class="o-fil-lien" aria-hidden="true"></span>' : ""}<button type="button" class="o-maillon ${m.etat} ${courant === cle ? "cur" : ""}"
       data-o-maillon="${cle}" ${courant === cle ? 'aria-current="true"' : ""} title="${esc(nom)} : ${esc(m.detail)} — ouvrir">
       <span class="o-maillon-sym">${ico(symbole, 16)}</span><span class="o-maillon-txt"><b>${esc(m.titre)}</b><small>${esc(m.detail)}</small></span></button>`;
   }).join("") + (f.note ? `<span class="o-fil-note">${esc(f.note)}</span>` : "");
  el.hidden = false;
 }
 function allerMaillon(cle) {
  const f = filCourant;
  if (!f) return;
  if (cle === "equipement") return allerOuvrage({nature: "eq", valeur: f.ident});
  if (cle === "es") { E.esEquip = f.repere; E.esUF = ""; E.filtreES = ""; return naviguer("#/es"); }
  if (cle === "carte") { E.rechercheES = f.repere; return naviguer("#/materiel"); }
  E.v31Query = f.nom_court; E.v31Page = 0; E.v31Status = "";       // variables et supervision : variables de l'équipement
  naviguer("#/variables");
 }

 // ------------------------------------------------------------------ panneau de sortie
 function plierSortie() {
  etat.sortieOuverte = !etat.sortieOuverte;
  try { localStorage.setItem("ogias-sortie", etat.sortieOuverte ? "ouverte" : "pliee"); } catch (e) { /* stockage indisponible */ }
  const s = document.getElementById("o-sortie");
  s.classList.toggle("plie", !etat.sortieOuverte);
  const b = s.querySelector(".o-sortie-plier");
  b.setAttribute("aria-expanded", String(etat.sortieOuverte));
  b.title = b.ariaLabel = etat.sortieOuverte ? "Réduire le panneau de sortie" : "Afficher le panneau de sortie";
 }
 function ongletSortie(nom) {
  const s = document.getElementById("o-sortie");
  s.querySelectorAll("[data-o-sortie]").forEach(b => b.setAttribute("aria-selected", String(b.dataset.oSortie === nom)));
  s.querySelectorAll("[data-o-sortie-panneau]").forEach(p => { p.hidden = p.dataset.oSortiePanneau !== nom; });
 }
 /** Contrôles de l'étape : `bloc` = élément à afficher (ou null : aucun contrôle pour cet écran), `n` = nombre de
     points, `resume` = phrase courte affichée dans l'en-tête même quand le panneau est réduit. */
 function controles(bloc, n = 0, resume = "", bloquant = false) {
  const s = document.getElementById("o-sortie");
  if (!s) return;
  const corps = s.querySelector('[data-o-sortie-panneau="controles"]');
  corps.replaceChildren(...(bloc ? [bloc] : []));
  if (!bloc) corps.innerHTML = '<p class="o-sortie-vide">Aucun contrôle pour cet écran.</p>';
  const c = s.querySelector('[data-o-compte="controles"]');
  c.textContent = n || "";
  c.className = "o-compte" + (n ? (bloquant ? " al" : " n") : "");
  const r = s.querySelector(".o-sortie-resume");
  r.textContent = resume;
  r.className = "o-sortie-resume" + (bloquant ? " al" : resume ? " ok" : "");
 }
 /** Journal : chaque message affiché (succès ou refus) y reste consultable pendant la session. */
 function journal(texte, erreur) {
  const heure = new Date().toLocaleTimeString("fr-FR", {hour: "2-digit", minute: "2-digit", second: "2-digit"});
  etat.journal.unshift({heure, texte: String(texte ?? ""), erreur: !!erreur});
  etat.journal = etat.journal.slice(0, 200);
  const s = document.getElementById("o-sortie");
  if (!s) return;
  s.querySelector(".o-journal").innerHTML = etat.journal.map(x =>
   `<li class="${x.erreur ? "err" : ""}">${ico(x.erreur ? "erreur" : "info", 14)}<time>${x.heure}</time><span>${esc(x.texte)}</span></li>`).join("");
  s.querySelector('[data-o-sortie-panneau="journal"] .o-sortie-vide').hidden = true;
  const erreurs = etat.journal.filter(x => x.erreur).length;
  const c = s.querySelector('[data-o-compte="journal"]');
  c.textContent = etat.journal.length;
  c.className = "o-compte" + (erreurs ? " err" : " n");
 }

 // ------------------------------------------------------------------ rendu
 function explorateur(E, etatEtape, vueEtape) {
  const el = document.getElementById("o-explorateur");
  const o = E.ouvrage || {}, ouvert = !!o.ouvert && !(E.vue === "ouvrage" && o.en_conception);
  const actif = route => ROUTE_VUE[E.vue] === route ? "on" : "";
  const lien = (route, icone, lib, extra = "") =>
   `<a href="${route}" data-nav="${route}" class="o-lien ${actif(route)}" ${actif(route) ? 'aria-current="page"' : ""}>${ico(icone)}<span>${esc(lib)}</span>${extra}</a>`;
  let parcours = "";
  if (ouvert) {
   const eqs = o.equipements || [], av = o.avancement || {};
   const comptes = {ouvrage: eqs.length ? `${eqs.filter(x => x.valide).length} / ${eqs.length}` : "",
                    es: av.contenu_non_valide ? `${av.contenu_non_valide} à valider` : ""};
   parcours = `<div class="o-section">Parcours</div><ol class="o-parcours" id="o-parcours">${ETAPES_PARCOURS.map(([v, lib, route], i) => {
     const s = etatEtape(v, o), cur = vueEtape(E.vue) === v;
     const cls = s === "validée" ? "ok" : s === "en cours" ? "al" : "";
     return `<li><a href="${route}" data-nav="${route}" class="o-etape ${cur ? "on" : ""}" ${cur ? 'aria-current="step"' : ""} title="${esc(lib)} : ${esc(s)}">
       <span class="o-pastille ${cls}">${s === "validée" ? ico("coche", 12) : i + 1}</span>${ico(SYMBOLE_ETAPE[v], 14)}<span class="o-etape-lib">${esc(lib)}</span><small>${esc(comptes[v] || s)}</small></a></li>`;
   }).join("")}</ol>`;
  }
  el.innerHTML = `<div class="o-panneau-tete">Explorateur<button type="button" class="o-replier" title="Masquer l'explorateur (Ctrl B)" aria-label="Masquer l'explorateur">${ico("replier", 14)}</button></div>
   <div class="o-section">OGIAS</div>${lien("#/ouvrages", "dossier", "Mes ouvrages")}${lien("#/referentiel", "referentiel", "Référentiel métier")}${lien("#/standards", "bord", "Standards d'ingénierie")}
   ${ouvert ? `<div class="o-section">Ouvrage</div>${lien("#/dashboard", "bord", "Tableau de bord", `<span class="o-code">${esc(o.prefixe || "")}</span>`)}${parcours}`
            : '<p class="o-vide-texte">Ouvrez un ouvrage pour suivre son parcours.</p>'}`;
  el.querySelector(".o-replier").onclick = basculerExplorateur;
 }
 function ongletsDocuments(E) {
  const route = ROUTE_VUE[E.vue] || "#/ouvrages";
  const ouvert = !!E.ouvrage?.ouvert;
  if (!ouvert) etat.documents = etat.documents.filter(x => ["#/ouvrages", "#/referentiel", "#/standards"].includes(x));
  if (!etat.documents.includes(route)) etat.documents.push(route);
  if (etat.documents.length > 8) etat.documents = etat.documents.slice(-8);
  const creation = E.vue === "ouvrage" && E.ouvrage?.en_conception;
  const titre = r => r === route && creation ? "Créer un ouvrage" : TITRES_ROUTE[r] || "OGIAS";
  document.querySelector("#o-documents .o-onglets").innerHTML = etat.documents.map(r => {
   const on = r === route;
   return `<div class="o-onglet ${on ? "on" : ""}" role="tab" aria-selected="${on}">
     ${ico(SYMBOLE_ROUTE[r] || "dossier", 14)}${on ? `<h1 id="v31-title">${esc(titre(r))}</h1>` : `<a href="${r}" data-nav="${r}">${esc(titre(r))}</a>`}
     ${etat.documents.length > 1 ? `<button type="button" class="o-fermer" data-o-fermer="${r}" title="Fermer « ${esc(titre(r))} »" aria-label="Fermer ${esc(titre(r))}">${ico("fermer", 12)}</button>` : ""}</div>`;
  }).join("");
 }
 function render(E, ETAPES, etatEtape, vueEtape) {
  explorateur(E, etatEtape, vueEtape);
  ongletsDocuments(E);
  if (E.vue !== etat.vueRuban) { ranger(null); etat.vueRuban = E.vue; }
  const etape = ETAPES_PARCOURS.some(([v]) => v === vueEtape(E.vue)) && E.ouvrage?.ouvert && !E.ouvrage?.en_conception;
  if (!etape) controles(null);
  majFil();
  const theme = document.getElementById("v31-settings");
  if (theme) theme.innerHTML = document.documentElement.dataset.theme === "dark" ? V31.icon("sun", 15) : V31.icon("moon", 15);
 }
 return {init, render, controles, journal, majFil, ruban: ranger, symbole: ico, sortie: () => { if (!etat.sortieOuverte) plierSortie(); ongletSortie("controles"); },
         actions: () => document.querySelector("#o-documents .o-documents-actions")};
})();
