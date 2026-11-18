"use strict";
/* OGIAS — composants de bureau (refonte de l'interface, lot 3, 18/11/2026).

   - Tableau dense : tri par colonne, filtres par colonne, colonnes redimensionnables, sélection multiple
     (clic, Ctrl, Maj, clavier), copie vers Excel (texte tabulé), menu contextuel.
     Amélioration progressive d'un <table data-o-tableau> existant : les lignes sont déplacées, jamais recréées,
     leurs écouteurs restent actifs. Les tableaux de saisie (cases à cocher, champs) ne sont pas concernés.
   - Menu contextuel générique (clic droit, touche Menu ou Maj F10), navigable au clavier.
   - Grille de propriétés : groupes repliables, libellé / valeur, lecture seule distinguée.
   - Registre des raccourcis clavier, affiché par Aide › Raccourcis clavier (Ctrl /).
   Présentation seulement : aucune donnée métier n'est modifiée ici. */
const Composants = (() => {
 const esc = x => String(x ?? "").replace(/[&<>"']/g, c => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"}[c]));
 const norm = s => String(s ?? "").normalize("NFD").replace(/[̀-ͯ]/g, "").toLocaleLowerCase("fr").trim();
 const comparer = new Intl.Collator("fr", {numeric: true, sensitivity: "base"}).compare;

 // ------------------------------------------------------------------ menu contextuel
 function fermerMenu() { document.querySelectorAll(".o-menu.o-contextuel").forEach(m => m.remove()); }
 /** Ouvre un menu à la position (x, y). `entrees` : [{libelle, raccourci?, action, actif?}] ou "-" (séparateur). */
 function menuContextuel(x, y, entrees, retour) {
  fermerMenu();
  const m = document.createElement("div");
  m.className = "o-menu o-contextuel"; m.setAttribute("role", "menu"); m.setAttribute("aria-label", "Menu contextuel");
  m.innerHTML = entrees.map((e, i) => e === "-" ? '<hr role="separator">'
   : `<button type="button" role="menuitem" data-o-ctx="${i}" ${e.actif === false ? "disabled" : ""}><span>${esc(e.libelle)}</span><kbd>${esc(e.raccourci || "")}</kbd></button>`).join("");
  document.body.append(m);
  const r = m.getBoundingClientRect();
  m.style.left = `${Math.max(4, Math.min(x, innerWidth - r.width - 4))}px`;
  m.style.top = `${Math.max(4, Math.min(y, innerHeight - r.height - 4))}px`;
  const items = () => [...m.querySelectorAll("button:not([disabled])")];
  m.addEventListener("click", ev => {
   const b = ev.target.closest("[data-o-ctx]");
   if (!b || b.disabled) return;
   fermerMenu(); entrees[+b.dataset.oCtx].action();
   retour?.focus?.();
  });
  m.addEventListener("keydown", ev => {
   const l = items(), k = l.indexOf(document.activeElement);
   if (ev.key === "ArrowDown") { ev.preventDefault(); l[(k + 1) % l.length]?.focus(); }
   else if (ev.key === "ArrowUp") { ev.preventDefault(); l[(k - 1 + l.length) % l.length]?.focus(); }
   else if (ev.key === "Escape" || ev.key === "Tab") { ev.preventDefault(); fermerMenu(); retour?.focus?.(); }
  });
  items()[0]?.focus();
  return m;
 }
 document.addEventListener("mousedown", ev => { if (!ev.target.closest(".o-contextuel")) fermerMenu(); }, true);
 addEventListener("blur", fermerMenu);

 // ------------------------------------------------------------------ copie vers le presse-papiers
 async function copier(texte) {
  try { await navigator.clipboard.writeText(texte); return true; }
  catch (e) {                                              // repli : sélection d'une zone de texte temporaire
   const z = document.createElement("textarea");
   z.value = texte; z.setAttribute("readonly", ""); z.style.position = "fixed"; z.style.opacity = "0";
   document.body.append(z); z.select();
   let ok = false;
   try { ok = document.execCommand("copy"); } catch (err) { ok = false; }
   z.remove();
   return ok;
  }
 }

 // ------------------------------------------------------------------ tableau dense
 const texteCellule = c => (c?.innerText ?? c?.textContent ?? "").replace(/\s+/g, " ").trim();
 function colonnes(t) { return [...(t.tHead?.rows[0]?.cells || [])]; }
 function lignes(t) { return [...t.tBodies].flatMap(b => [...b.rows]).filter(r => !r.classList.contains("o-filtres")); }
 function visibles(t) { return lignes(t).filter(r => !r.hidden); }
 function selection(t) { return visibles(t).filter(r => r.getAttribute("aria-selected") === "true"); }
 /** Colonnes utiles à la copie : celles qui ont un titre (les colonnes d'actions sont ignorées). */
 function colonnesUtiles(t) { return colonnes(t).map((th, i) => [th, i]).filter(([th]) => texteCellule(th)); }

 function versTexte(t, rangees) {
  const cols = colonnesUtiles(t);
  const ligne = cells => cols.map(([, i]) => texteCellule(cells[i]).replace(/\t/g, " ")).join("\t");
  return [ligne(colonnes(t)), ...rangees.map(r => ligne([...r.cells]))].join("\r\n");
 }
 async function copierLignes(t, toutes) {
  const rangees = toutes ? visibles(t) : (selection(t).length ? selection(t) : visibles(t));
  const ok = await copier(versTexte(t, rangees));
  if (typeof toast === "function")
   toast(ok ? `${rangees.length} ligne(s) copiée(s) : collez-les dans Excel.` : "Copie impossible : le presse-papiers est refusé par le système.", !ok);
  return ok;
 }

 function trier(t, i, sens) {
  const th = colonnes(t)[i];
  colonnes(t).forEach(c => c.removeAttribute("aria-sort"));
  t.tBodies[0] && [...t.tBodies].forEach(corps => {
   const rangs = [...corps.rows].filter(r => !r.classList.contains("o-filtres"));
   rangs.sort((a, b) => {
    if (!sens) return (+a.dataset.oRang) - (+b.dataset.oRang);
    const x = texteCellule(a.cells[i]), y = texteCellule(b.cells[i]);
    if (!x !== !y) return x ? -1 : 1;                     // cellules vides en dernier, quel que soit le sens
    return sens === "asc" ? comparer(x, y) : comparer(y, x);
   }).forEach(r => corps.append(r));
  });
  if (sens) th.setAttribute("aria-sort", sens === "asc" ? "ascending" : "descending");
  t.dataset.oTri = sens ? `${i}:${sens}` : "";
 }
 function basculerTri(t, i) {
  const [col, sens] = (t.dataset.oTri || ":").split(":");
  const suivant = +col !== i || !sens ? "asc" : sens === "asc" ? "desc" : "";
  trier(t, i, suivant);
 }

 function filtrer(t) {
  const champs = [...t.querySelectorAll("thead .o-filtres input")];
  const actifs = champs.map((c, i) => [i, norm(c.value)]).filter(([, v]) => v);
  lignes(t).forEach(r => { r.hidden = actifs.some(([i, v]) => !norm(texteCellule(r.cells[+champs[i].dataset.oCol])).includes(v)); });
  const n = visibles(t).length, total = lignes(t).length;
  t.dataset.oFiltre = actifs.length ? `${n}/${total}` : "";
  const legende = t.parentElement?.querySelector(":scope > .o-tableau-filtre");
  if (legende) legende.textContent = actifs.length ? `${n} ligne(s) affichée(s) sur ${total} (filtre actif)` : "";
 }
 function basculerFiltres(t, afficher) {
  let rang = t.tHead.querySelector(".o-filtres");
  if (afficher === undefined) afficher = !rang;
  if (!afficher) {
   rang?.remove();
   lignes(t).forEach(r => { r.hidden = false; });
   filtrer(t);
   return;
  }
  if (rang) return rang.querySelector("input")?.focus();
  rang = t.tHead.insertRow(-1);
  rang.className = "o-filtres";
  colonnes(t).forEach((th, i) => {
   const c = document.createElement("th");
   if (texteCellule(th)) c.innerHTML = `<input type="search" data-o-col="${i}" aria-label="Filtrer la colonne ${esc(texteCellule(th))}" placeholder="Filtrer">`;
   rang.append(c);
  });
  rang.addEventListener("input", () => filtrer(t));
  if (!t.parentElement.querySelector(":scope > .o-tableau-filtre")) {
   const legende = document.createElement("p");
   legende.className = "o-tableau-filtre"; legende.setAttribute("aria-live", "polite");
   t.after(legende);
  }
  rang.querySelector("input")?.focus();
 }

 function selectionner(t, r, mode) {
  const vis = visibles(t);
  if (mode === "plage" && t.oAncre && vis.includes(t.oAncre)) {
   const [a, b] = [vis.indexOf(t.oAncre), vis.indexOf(r)].sort((x, y) => x - y);
   vis.forEach((x, k) => x.setAttribute("aria-selected", String(k >= a && k <= b)));
  } else if (mode === "ajout") {
   r.setAttribute("aria-selected", String(r.getAttribute("aria-selected") !== "true"));
   t.oAncre = r;
  } else {
   vis.forEach(x => x.setAttribute("aria-selected", String(x === r)));
   t.oAncre = r;
  }
  activer(t, r);
 }
 function activer(t, r) {
  lignes(t).forEach(x => { x.tabIndex = -1; x.classList.toggle("o-actif", x === r); });
  r.tabIndex = 0;
 }

 function menuTableau(t, ev, colonne) {
  const n = selection(t).length;
  const nom = colonne === undefined ? "" : texteCellule(colonnes(t)[colonne]);
  const filtres = !!t.tHead.querySelector(".o-filtres");
  const entrees = [
   {libelle: n ? `Copier la sélection (${n} ligne${n > 1 ? "s" : ""})` : "Copier les lignes affichées", raccourci: "Ctrl C", action: () => copierLignes(t, false)},
   {libelle: "Copier tout le tableau", action: () => copierLignes(t, true)},
   {libelle: "Tout sélectionner", raccourci: "Ctrl A", action: () => { visibles(t).forEach(r => r.setAttribute("aria-selected", "true")); }}, "-"];
  if (nom) entrees.push({libelle: `Trier « ${nom} » par ordre croissant`, action: () => trier(t, colonne, "asc")},
                        {libelle: `Trier « ${nom} » par ordre décroissant`, action: () => trier(t, colonne, "desc")});
  entrees.push({libelle: "Ordre d'origine", actif: !!t.dataset.oTri, action: () => trier(t, 0, "")}, "-",
               {libelle: filtres ? "Masquer les filtres" : "Filtrer les colonnes", action: () => basculerFiltres(t)});
  const cible = ev.target.closest("tr") || t;
  const r = ev.type === "contextmenu" && ev.clientX ? {x: ev.clientX, y: ev.clientY} : (() => { const b = cible.getBoundingClientRect(); return {x: b.left + 24, y: b.bottom}; })();
  menuContextuel(r.x, r.y, entrees, cible);
 }

 /** Rend un <table> existant dense et interactif. Sans effet sur un tableau déjà amélioré. */
 function tableau(t) {
  if (!t || t.dataset.oPret || !t.tHead || !t.tBodies.length) return t;
  t.dataset.oPret = "1";
  t.classList.add("o-tableau");
  t.setAttribute("aria-multiselectable", "true");
  lignes(t).forEach((r, k) => { r.dataset.oRang = k; r.setAttribute("aria-selected", "false"); r.tabIndex = k ? -1 : 0; });
  colonnes(t).forEach((th, i) => {
   if (!texteCellule(th) || th.dataset.oNonTriable !== undefined) return;
   th.classList.add("o-triable");
   th.tabIndex = 0;
   th.title = th.title || `Trier par « ${texteCellule(th)} » (clic droit : autres commandes)`;
   const poignee = document.createElement("span");
   poignee.className = "o-poignee"; poignee.setAttribute("aria-hidden", "true");
   th.append(poignee);
   poignee.addEventListener("mousedown", ev => {                // redimensionner la colonne
    ev.preventDefault(); ev.stopPropagation();
    const depart = ev.clientX, largeur = th.getBoundingClientRect().width;
    const bouger = e => { const w = Math.max(48, Math.round(largeur + e.clientX - depart)); th.style.width = th.style.minWidth = `${w}px`; };
    const lacher = () => { removeEventListener("mousemove", bouger); removeEventListener("mouseup", lacher); document.body.classList.remove("o-redim"); };
    document.body.classList.add("o-redim");
    addEventListener("mousemove", bouger); addEventListener("mouseup", lacher);
   });
   poignee.addEventListener("click", ev => ev.stopPropagation());
   th.addEventListener("click", ev => { if (!ev.target.closest(".o-poignee")) basculerTri(t, i); });
   th.addEventListener("keydown", ev => { if (ev.key === "Enter" || ev.key === " ") { ev.preventDefault(); basculerTri(t, i); } });
  });
  t.addEventListener("click", ev => {
   const r = ev.target.closest("tbody tr");
   if (!r || r.classList.contains("o-filtres") || ev.target.closest("button, a, input, select, textarea, label, summary")) return;
   selectionner(t, r, ev.shiftKey ? "plage" : ev.ctrlKey || ev.metaKey ? "ajout" : "seule");
  });
  t.addEventListener("contextmenu", ev => {
   if (ev.target.closest("input, textarea")) return;
   ev.preventDefault();
   const r = ev.target.closest("tbody tr");
   if (r && r.getAttribute("aria-selected") !== "true") selectionner(t, r, "seule");
   const th = ev.target.closest("thead th");
   menuTableau(t, ev, th ? th.cellIndex : r ? ev.target.closest("td")?.cellIndex : undefined);
  });
  t.addEventListener("keydown", ev => {
   if (ev.target.closest("input, textarea, select")) return;
   const r = ev.target.closest("tbody tr"), vis = visibles(t);
   if ((ev.ctrlKey || ev.metaKey) && ev.key.toLowerCase() === "c") { ev.preventDefault(); copierLignes(t, false); return; }
   if ((ev.ctrlKey || ev.metaKey) && ev.key.toLowerCase() === "a") { ev.preventDefault(); vis.forEach(x => x.setAttribute("aria-selected", "true")); return; }
   if (ev.key === "ContextMenu" || (ev.shiftKey && ev.key === "F10")) { ev.preventDefault(); menuTableau(t, ev, r ? 0 : undefined); return; }
   if (!r) return;
   const k = vis.indexOf(r);
   const aller = cible => { if (!cible) return; ev.preventDefault();
    if (ev.shiftKey) { if (!selection(t).length) t.oAncre = r; selectionner(t, cible, "plage"); } else activer(t, cible);
    cible.focus(); cible.scrollIntoView({block: "nearest"}); };
   if (ev.key === "ArrowDown") aller(vis[k + 1]);
   else if (ev.key === "ArrowUp") aller(vis[k - 1]);
   else if (ev.key === "Home") aller(vis[0]);
   else if (ev.key === "End") aller(vis[vis.length - 1]);
   else if (ev.key === " ") { ev.preventDefault(); selectionner(t, r, "ajout"); }
   else if (ev.key === "Escape") vis.forEach(x => x.setAttribute("aria-selected", "false"));
  });
  return t;
 }
 /** Améliore tous les tableaux marqués data-o-tableau sous `racine`. */
 function ameliorer(racine = document) { racine.querySelectorAll("table[data-o-tableau]:not([data-o-pret])").forEach(tableau); }

 // ------------------------------------------------------------------ grille de propriétés
 /** groupes : [{titre, ouvert?, proprietes: [{libelle, valeur, mono?, lecture?, html?}]}] → HTML. */
 function grille(groupes) {
  return `<div class="o-grille">${groupes.map(g => `<details class="o-grille-groupe" ${g.ouvert === false ? "" : "open"}>
    <summary>${esc(g.titre)}</summary><dl>${(g.proprietes || []).map(p => `<div class="o-prop${p.lecture ? " lecture" : ""}">
      <dt>${esc(p.libelle)}</dt><dd class="${p.mono ? "mono" : ""}">${p.html ?? (p.valeur === undefined || p.valeur === "" ? '<span class="o-sans-valeur">—</span>' : esc(p.valeur))}</dd></div>`).join("")}</dl></details>`).join("")}</div>`;
 }

 // ------------------------------------------------------------------ raccourcis clavier
 const RACCOURCIS = [
  ["Général", [["Ctrl K", "Rechercher un repère, un équipement"], ["Ctrl B", "Afficher ou masquer l'explorateur"],
               ["F1", "Aide d'OGIAS"], ["Ctrl /", "Liste des raccourcis clavier"], ["Échap", "Fermer un menu ou une fenêtre"]]],
  ["Menus", [["Flèches", "Parcourir les menus et leurs commandes"], ["Entrée", "Exécuter la commande"]]],
  ["Tableaux", [["Clic, Ctrl clic, Maj clic", "Sélectionner une ligne, en ajouter, une plage"],
                ["Flèches, Début, Fin", "Changer de ligne (Maj : étendre la sélection)"], ["Espace", "Ajouter ou retirer la ligne"],
                ["Ctrl A", "Tout sélectionner"], ["Ctrl C", "Copier vers Excel (sélection ou lignes affichées)"],
                ["Clic sur un titre", "Trier ; second clic : ordre inverse ; troisième : ordre d'origine"],
                ["Clic droit, touche Menu, Maj F10", "Menu contextuel : copie, tri, filtres"]]],
 ];
 function aideRaccourcis() {
  if (typeof ouvrirModale !== "function") return;
  const m = ouvrirModale(`<div class="boite-tete"><h2>Raccourcis clavier</h2></div><div class="boite-corps o-raccourcis">${RACCOURCIS.map(([g, l]) =>
    `<h3>${esc(g)}</h3><dl>${l.map(([k, d]) => `<div><dt><kbd>${esc(k)}</kbd></dt><dd>${esc(d)}</dd></div>`).join("")}</dl>`).join("")}</div>
    <div class="boite-pied"><button data-fermer>Fermer</button></div>`);
  m.querySelector("[data-fermer]").focus();
 }
 document.addEventListener("keydown", ev => {
  if ((ev.ctrlKey || ev.metaKey) && (ev.key === "/" || ev.key === ":")) { ev.preventDefault(); aideRaccourcis(); }
 });

 // Les écrans sont reconstruits à chaque rendu : les tableaux marqués sont améliorés dès leur apparition.
 function surveiller() {
  const vue = document.getElementById("vue");
  if (!vue) return;
  let prevu = false;
  new MutationObserver(() => { if (prevu) return; prevu = true; requestAnimationFrame(() => { prevu = false; ameliorer(vue); }); })
   .observe(vue, {childList: true, subtree: true});
 }
 if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", surveiller, {once: true}); else surveiller();

 return {tableau, ameliorer, menuContextuel, grille, copier, versTexte, aideRaccourcis, RACCOURCIS};
})();
