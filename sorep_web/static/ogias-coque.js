"use strict";
/* OGIAS — coque de bureau (refonte de l'interface, lot 2a, 18/11/2026).

   Barre de titre avec menus, explorateur (navigation et parcours de l'ouvrage), onglets de documents.
   Couche de présentation seulement : chaque commande appelle une fonction ou une route qui existait déjà
   (naviguer, api('/api/nouveau'), recherche globale…). Aucune règle métier ici. */
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
 };
 const ico = (nom, t = 16) => `<svg class="o-ico" width="${t}" height="${t}" viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">${TRACES[nom] || ""}</svg>`;
 const ETAPES_PARCOURS = [["ouvrage", "Équipements", "#/inventaire"], ["es", "Liste des E/S", "#/es"],
   ["materiel", "Matériel", "#/materiel"], ["variables", "Variables", "#/variables"], ["recette", "Recette", "#/recette"]];
 const TITRES_ROUTE = {"#/ouvrages": "Mes ouvrages", "#/dashboard": "Tableau de bord", "#/inventaire": "Équipements",
   "#/es": "Liste des E/S", "#/materiel": "Matériel", "#/variables": "Variables", "#/recette": "Recette",
   "#/referentiel": "Référentiel métier"};
 const ROUTE_VUE = {accueil: "#/ouvrages", dashboard: "#/dashboard", ouvrage: "#/inventaire", es: "#/es", materiel: "#/materiel",
   variables: "#/variables", supervision: "#/variables", adressage: "#/variables", recette: "#/recette", referentiel: "#/referentiel"};
 const etat = {documents: [], explorateur: true, menuOuvert: ""};
 try { etat.explorateur = localStorage.getItem("ogias-explorateur") !== "masque"; } catch (e) { /* stockage indisponible */ }

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
  ["Outils", [["Référentiel métier", "", () => naviguer("#/referentiel")]]],
  ["Aide", [["Aide d'OGIAS", "F1", () => window.open("aide.html", "_blank", "noopener")],
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
       <span class="o-pastille ${cls}">${s === "validée" ? ico("coche", 12) : i + 1}</span><span class="o-etape-lib">${esc(lib)}</span><small>${esc(comptes[v] || s)}</small></a></li>`;
   }).join("")}</ol>`;
  }
  el.innerHTML = `<div class="o-panneau-tete">Explorateur<button type="button" class="o-replier" title="Masquer l'explorateur (Ctrl B)" aria-label="Masquer l'explorateur">${ico("replier", 14)}</button></div>
   <div class="o-section">OGIAS</div>${lien("#/ouvrages", "dossier", "Mes ouvrages")}${lien("#/referentiel", "referentiel", "Référentiel métier")}
   ${ouvert ? `<div class="o-section">Ouvrage</div>${lien("#/dashboard", "bord", "Tableau de bord", `<span class="o-code">${esc(o.prefixe || "")}</span>`)}${parcours}`
            : '<p class="o-vide-texte">Ouvrez un ouvrage pour suivre son parcours.</p>'}`;
  el.querySelector(".o-replier").onclick = basculerExplorateur;
 }
 function ongletsDocuments(E) {
  const route = ROUTE_VUE[E.vue] || "#/ouvrages";
  const ouvert = !!E.ouvrage?.ouvert;
  if (!ouvert) etat.documents = etat.documents.filter(x => ["#/ouvrages", "#/referentiel"].includes(x));
  if (!etat.documents.includes(route)) etat.documents.push(route);
  if (etat.documents.length > 8) etat.documents = etat.documents.slice(-8);
  const creation = E.vue === "ouvrage" && E.ouvrage?.en_conception;
  const titre = r => r === route && creation ? "Créer un ouvrage" : TITRES_ROUTE[r] || "OGIAS";
  document.querySelector("#o-documents .o-onglets").innerHTML = etat.documents.map(r => {
   const on = r === route;
   return `<div class="o-onglet ${on ? "on" : ""}" role="tab" aria-selected="${on}">
     ${on ? `<h1 id="v31-title">${esc(titre(r))}</h1>` : `<a href="${r}" data-nav="${r}">${esc(titre(r))}</a>`}
     ${etat.documents.length > 1 ? `<button type="button" class="o-fermer" data-o-fermer="${r}" title="Fermer « ${esc(titre(r))} »" aria-label="Fermer ${esc(titre(r))}">${ico("fermer", 12)}</button>` : ""}</div>`;
  }).join("");
 }
 function render(E, ETAPES, etatEtape, vueEtape) {
  explorateur(E, etatEtape, vueEtape);
  ongletsDocuments(E);
  const theme = document.getElementById("v31-settings");
  if (theme) theme.innerHTML = document.documentElement.dataset.theme === "dark" ? V31.icon("sun", 15) : V31.icon("moon", 15);
 }
 return {init, render, actions: () => document.querySelector("#o-documents .o-documents-actions")};
})();
