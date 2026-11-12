"use strict";
/* Interface web OGIAS — aucune règle métier ici : chaque action appelle le serveur (moteur genvar). */

const E = {vue: "accueil", sel: {nature: "ouvrage", valeur: ""}, ouvrage: null, accueil: null, ref: null,
           refType: "", refModele: "", filtreRole: "Toutes", recherche: "", listes: null, ficheDraft: null, ficheDirty: false};
const $ = s => document.querySelector(s);
const esc = v => String(v ?? "").replace(/[&<>"']/g, c => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"}[c]));
const ROLES_ORDRE = ["TS", "DEF", "ALA", "EVI", "TC", "TR", "RTR", "TM", "TMC", "CPT"];
const classeRole = r => ["TS", "DEF", "ALA", "EVI", "TC", "TR", "RTR"].includes(r) ? "r-" + r : "";

/* ------------------------------------------------------------------ échanges */
async function api(chemin, donnees) {
  const opt = donnees === undefined ? {} : {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(donnees)};
  const r = await fetch(chemin, opt);
  const j = await r.json().catch(() => ({erreur: "Réponse illisible du serveur."}));
  if (!r.ok) throw new Error(j.erreur || "Erreur");
  return j;
}
function toast(texte, err) {
  const t = document.createElement("div");
  t.className = "toast" + (err ? " err" : "");
  t.textContent = texte;
  const pile = $("#toasts");
  while (pile.children.length >= 3) pile.firstChild.remove();
  pile.appendChild(t);
  setTimeout(() => t.remove(), err ? 6000 : 3200);
}
async function agir(promesse, succes) {
  try { const r = await promesse; if (succes) toast(succes); return r; }
  catch (e) { toast(e.message, true); e.dejaAffiche = true; throw e; }
}
// Un refus métier déjà affiché (toast) interrompt l'action en cours : ce n'est pas une erreur de l'interface.
window.addEventListener("unhandledrejection", ev => { if (ev.reason && ev.reason.dejaAffiche) ev.preventDefault(); });
function lireFichier(input) {
  return new Promise((ok, ko) => {
    const f = input.files[0];
    if (!f) return ko(new Error("Aucun fichier choisi."));
    const lecteur = new FileReader();
    lecteur.onload = () => ok({nom: f.name, contenu: lecteur.result.split(",")[1]});
    lecteur.onerror = () => ko(new Error("Lecture du fichier impossible."));
    lecteur.readAsDataURL(f);
  });
}

/* ------------------------------------------------------------------ navigation */
/* Jeton de navigation : seule la dernière navigation demandée peut afficher son écran. La réponse tardive
   d'un écran quitté (clic rapide sur une autre étape) est ignorée au lieu de remplacer l'écran demandé. */
let jetonNav = 0;
function perime(j) { return j !== undefined && j !== jetonNav; }
async function _accueil(j) {
  E.ficheDraft = null; E.ficheDirty = false;
  const accueil = await api("/api/accueil");
  if (perime(j)) return;
  E.vue = "accueil"; E.accueil = accueil; rendre();
}
async function _dashboard(j) {
  E.ouvrage = await api("/api/ouvrage");
  if (!E.ouvrage.ouvert) return _accueil(j);
  E.accueil = await api("/api/accueil");
  try { E.recetteDashboard = await api("/api/recette"); } catch (_) { E.recetteDashboard = null; }
  try { E.esDashboard = await api("/api/es"); } catch (_) { E.esDashboard = null; }
  try { E.variablesDashboard = await api("/api/variables"); } catch (_) { E.variablesDashboard = null; }
  if (perime(j)) return;
  E.vue = "dashboard"; rendre();
}
async function _ouvrage(j) {
  E.ouvrage = await api("/api/ouvrage");
  if (!E.ouvrage.ouvert) return sansOuvrage(j);
  E.listes = await api("/api/listes-ouvrage");
  if (perime(j)) return;
  E.vue = "ouvrage"; rendre();
}
function sansOuvrage(j) {
  if (perime(j)) return;
  toast("Aucun ouvrage ouvert : ouvrez ou créez un ouvrage.", true);
  history.replaceState(null, "", "#/ouvrages");
  return _accueil(j);
}
async function recharger() { E.ouvrage = await api("/api/ouvrage"); E.listes = await api("/api/listes-ouvrage"); rendre(); }
async function _es(j) {
  E.ouvrage = await api("/api/ouvrage");
  if (!E.ouvrage.ouvert) return sansOuvrage(j);
  if (E.ouvrage.en_conception) { if (!perime(j)) toast("Confirmez d’abord la création de l’ouvrage.", true); return _ouvrage(j); }
  const aValider = (E.ouvrage.equipements || []).filter(e => !e.valide);
  if (E.ouvrage.identification.mode === 'Neuf' && (aValider.length || !E.ouvrage.equipements.length)) {
    if (perime(j)) return;
    E.sel = aValider.length ? {nature: 'eq', valeur: aValider[0].ident} : {nature:'ouvrage',valeur:''};
    toast(aValider.length ? `Validez le paramétrage des ${aValider.length} équipement(s) avant de construire la liste des E/S.`
      : 'Ajoutez et validez au moins un équipement avant la liste des E/S.', true);
    return _ouvrage(j);
  }
  const es = await api("/api/es");
  if (perime(j)) return;
  E.es = es; E.vue = "es"; rendre();
}
// Étape 3 : matériel calculé depuis les E/S au contenu validé (cartes, racks, implantation, livrables).
async function _materiel(j) {
  E.ouvrage = await api("/api/ouvrage");
  if (!E.ouvrage.ouvert) return sansOuvrage(j);
  if (E.ouvrage.en_conception) { if (!perime(j)) toast("Confirmez d’abord la création de l’ouvrage.", true); return _ouvrage(j); }
  let es;
  try { es = await api("/api/es"); }
  catch (e) { if (!perime(j)) toast(e.message, true); return _ouvrage(j); }          // équipements non validés : retour à l'étape 1
  const mat = await api("/api/materiel");
  if (perime(j)) return;
  E.es = es; E.mat = mat; E.vue = "materiel"; rendre();
}
async function rechargerMateriel() {
  [E.es, E.mat, E.ouvrage] = await Promise.all([api("/api/es"), api("/api/materiel"), api("/api/ouvrage")]); rendre();
}
async function _aVenir(etape, j) {
  E.ouvrage = await api("/api/ouvrage");
  if (!E.ouvrage.ouvert) return sansOuvrage(j);
  if (E.ouvrage.en_conception) { if (!perime(j)) toast("Confirmez d’abord la création de l’ouvrage.", true); return _ouvrage(j); }
  const url = {variables: "/api/variables", supervision: "/api/supervision", recette: "/api/recette", adressage: "/api/adressage"}[etape];
  const detail = await api(url);
  let tele = E.v31Tele;
  if (etape === "variables") { try { tele = await api("/api/supervision"); } catch (_) { tele = {lignes: []}; } }
  if (perime(j)) return;
  E.detailEtape = detail; E.v31Tele = tele; E.vue = etape; rendre();
}
async function rechargerES() { E.es = await api("/api/es"); E.ouvrage = await api("/api/ouvrage"); rendre(); }
async function _referentiel(j) {
  E.ouvrage = await api("/api/ouvrage");
  if (perime(j)) return;
  E.vue = "referentiel";
  await chargerReferentiel();
  if (perime(j)) return;
  rendre();
}
async function chargerReferentiel() {
  E.cycle = await api("/api/referentiel/cycle");
  const source = E.cycle.brouillon && E.refSource !== "publie" ? "brouillon" : "publie";
  E.ref = await api("/api/referentiel/vue?source=" + source);
  if (!E.refType || !E.ref.types.find(t => t.code === E.refType)) E.refType = (E.ref.types[0] || {}).code || "";
}
/* Navigation par adresse (#/…) : chaque écran a son adresse, le bouton « Retour » du navigateur fonctionne,
   et la barre du haut donne accès à tous les écrans depuis n'importe où. */
const ROUTES = {"#/ouvrages": _accueil, "#/dashboard": _dashboard, "#/inventaire": _ouvrage, "#/es": _es, "#/materiel": _materiel, "#/referentiel": _referentiel,
                "#/variables": j => _aVenir("variables", j), "#/supervision": j => _aVenir("supervision", j), "#/adressage": j => _aVenir("adressage", j), "#/recette": j => _aVenir("recette", j),
                "#/controles": j => _aVenir("recette", j), "#/exports": j => _aVenir("recette", j)};
async function naviguer(route) {
  if (route !== "#/inventaire" && E.ficheDirty) {
    if (!window.confirm("Des modifications de la fiche ne sont pas enregistrées. Les abandonner ?")) return;
    E.ficheDirty = false; E.ficheDraft = null;
  }
  if (E.esFormDirty) {
    if (!window.confirm("Des modifications du point E/S ne sont pas enregistrées. Les abandonner ?")) return;
    E.esFormDirty = false;
  }
  if (route !== "#/inventaire" && E.ouvrage?.creation_en_attente) {
    await api("/api/fermer"); E.ouvrage = null;
  }
  E.apresFermeture = null; fermerModale();
  if (location.hash === route) afficher(); else location.hash = route;
}
window.addEventListener("beforeunload", e => {
  if (E.ficheDirty || E.esFormDirty || E.ouvrage?.creation_en_attente) { e.preventDefault(); e.returnValue = ""; }
});
async function afficher() {
  E.apresFermeture = null; fermerModale();
  document.querySelectorAll("#toasts .toast.err, #toasts .err").forEach(t => t.remove());   // une erreur d'un autre écran ne doit pas rester affichée   // une fenêtre ouverte ne doit jamais bloquer un changement d'écran
  const j = ++jetonNav;
  const f = ROUTES[location.hash] || _accueil;
  try { await f(j); } catch (e) { if (!perime(j)) toast(e.message, true); }
  if (!perime(j)) window.scrollTo(0, 0);
}
window.addEventListener("hashchange", afficher);
function allerAccueil() { naviguer("#/ouvrages"); }
function allerOuvrage(sel) { if (sel) E.sel = sel; naviguer("#/inventaire"); }
function allerES() { naviguer("#/es"); }
function allerReferentiel() { naviguer("#/referentiel"); }
// État vide de l'étape 1 (retour d'essai 6) : l'action principale est visible sans ouvrir la structure.
document.addEventListener("click", ev => {
  if (ev.target.closest("#vide-ajout-eq")) return modaleEquipement(null, typeof ufSelectionnee === "function" ? ufSelectionnee() : undefined);
  if (ev.target.closest("#vide-structure")) document.getElementById("v31-tree-trigger")?.click();
});
document.addEventListener("click", ev => {
  const a = ev.target.closest("[data-nav]");
  if (!a) return;
  ev.preventDefault();
  naviguer(a.dataset.nav);
});

/* ------------------------------------------------------------------ rendu général */
// Pied d'étape commun : précédent / état / suivant, ajouté à chaque écran du parcours.
function piedEtape() {
  const o = E.ouvrage, i = ETAPES.findIndex(x => x[1] === vueEtape(E.vue)), zone = document.querySelector("#vue .contenu");
  if (!o || !o.ouvert || i < 0 || !zone || o.en_conception) return;
  zone.querySelector(".pied-etape")?.remove();
  const prec = ETAPES[i - 1], suiv = ETAPES[i + 1], statut = etatEtape(vueEtape(E.vue), o);
  const nonValides = (o.equipements || []).filter(e => !e.valide).length;
  const av = o.avancement || {};
  const note = E.vue === "ouvrage" && nonValides ? `${nonValides} équipement(s) à valider avant la liste des E/S`
             : E.vue === "es" && av.contenu_non_valide ? `${av.contenu_non_valide} E/S à valider avant le calcul du matériel`
             : E.vue === "materiel" && !av.materiel_valide ? "Matériel à valider avant les variables"
             : `Étape ${i + 1} sur ${ETAPES.length} · ${statut}`;
  const bloque = (E.vue === "ouvrage" && nonValides) || (E.vue === "es" && av.contenu_non_valide) || (E.vue === "materiel" && !av.materiel_valide);
  const esSuivantBloque = E.vue === "es" && av.contenu_non_valide > 0;
  const pied = document.createElement("div");
  pied.className = "pied-etape";
  pied.innerHTML = `${prec ? `<button data-nav="${prec[0]}">← ${esc(prec[2])}</button>` : "<span></span>"}
    <span class="etat-etape ${statut === "validée" ? "ok" : bloque ? "al" : ""}">${esc(note)}</span>
    ${suiv ? `<button class="prim" data-nav="${suiv[0]}" ${esSuivantBloque ? 'disabled title="Validez toutes les E/S avant le calcul du matériel"' : ""}>Étape suivante : ${esc(suiv[2])} →</button>` : `<button class="prim" data-nav="#/ouvrages">Terminer et revenir à mes ouvrages</button>`}`;
  zone.appendChild(pied);
  panneauParcours(vueEtape(E.vue), zone);
}
// Parcours guidé (retours 4, 5, 7) : ce qui empêche de passer à l'étape suivante, avec un lien vers l'endroit à corriger.
const ROUTE_VUE = {ouvrage: "#/inventaire", es: "#/es", materiel: "#/materiel", variables: "#/variables", recette: "#/recette"};
async function panneauParcours(vue, zone) {
  let etapes;
  try { etapes = (await api("/api/parcours")).etapes || []; } catch (e) { return; }
  const et = etapes.find(x => x.vue === vue);
  zone.querySelector(".parcours-points")?.remove();
  if (!et || (!et.bloquants.length && !et.a_verifier.length)) return;
  const precedente = etapes.find(x => x.etape < et.etape && !x.pret);
  const ligne = p => `<li><button type="button" class="lien" data-pp-vue="${esc(p.vue)}" data-pp-eq="${esc(p.ident_eq || "")}">${esc(p.message)}</button></li>`;
  const bloc = document.createElement("div");
  bloc.className = "parcours-points";
  bloc.innerHTML = (et.bloquants.length ? `<div class="pp-bloquants"><h3>Pour passer à l'étape suivante (${et.bloquants.length})</h3><ul>${et.bloquants.map(ligne).join("")}</ul></div>`
      : `<div class="pp-pret"><b>${precedente ? "Cette étape est prête ; terminez d'abord l'étape « " + esc(precedente.libelle) + " »." : "Étape prête : vous pouvez passer à la suivante."}</b></div>`)
    + (et.a_verifier.length ? `<details class="pp-verifier"><summary>À vérifier (${et.a_verifier.length})</summary><ul>${et.a_verifier.map(ligne).join("")}</ul></details>` : "");
  zone.querySelector(".pied-etape")?.before(bloc);
  bloc.querySelectorAll("[data-pp-vue]").forEach(b => b.onclick = () => {
    if (b.dataset.ppVue === "ouvrage" && b.dataset.ppEq)
      return allerOuvrage({nature: "eq", valeur: b.dataset.ppEq});
    naviguer(ROUTE_VUE[b.dataset.ppVue] || "#/inventaire");
  });
}
function rendre() {
  enTete();
  requestAnimationFrame(() => { piedEtape(); V31.refresh(E,ETAPES,etatEtape,vueEtape); });
  if (E.vue === "accueil") return vueAccueilV31();
  if (E.vue === "dashboard") return vueDashboardV31();
  if (E.vue === "referentiel") return vueReferentiel();
  if (E.vue === "es") return vueES();
  if (E.vue === "materiel") return vueMateriel();
  if (E.vue === "variables") return vueVariablesV31();
  if (E.vue === "supervision") return vueSupervision();
  if (E.vue === "adressage") return vueAdressage();
  if (E.vue === "recette") return vueRecette();
  vueOuvrage();
}
// Parcours métier ; les écrans pas encore implémentés restent explicitement signalés.
const ETAPES = [["#/inventaire", "ouvrage", "Équipements", "Ouvrage et inventaire des équipements"],
                ["#/es", "es", "Liste des E/S", "Contenu des entrées / sorties physiques"],
                ["#/materiel", "materiel", "Matériel", "Racks, cartes, implantation et liste d'E/S"],
                ["#/variables", "variables", "Variables", "Variables de supervision et télétransmission"],
                ["#/recette", "recette", "Recette", "Contrôles et livrables"]];
// Vue → étape (l'écran Télétransmission appartient à l'étape Variables).
const vueEtape = v => v === "supervision" || v === "adressage" ? "variables" : v;
function etatEtape(v, o) {
  if (!o || !o.ouvert) return 'à faire';
  const av = o.avancement || {};
  if (v === 'es') return !av.es ? 'à faire' : av.contenu_non_valide ? 'en cours' : 'validée';
  if (v === 'materiel') return !av.cartes ? 'à faire' : (av.materiel_valide && !av.voies_non_validees && !av.sans_adresse) ? 'validée' : 'en cours';
  if (v === 'ouvrage') {
    if (o.creation_en_attente || !o.identification.lieu || !o.identification.code_ouvrage || !o.identification.libelle) return 'en cours';
    if (!o.equipements.length || o.equipements.some(e => !e.valide)) return 'en cours';
    return 'validée';
  }
  if (v === 'variables') {
    if (E.vue === 'variables' && E.detailEtape?.lignes)
      return E.detailEtape.lignes.length && E.detailEtape.lignes.every(x => x.validee) ? 'validée' : 'en cours';
    if (E.vue === 'supervision') return 'en cours'; // contrôles métier à faire, export jamais qualifié implicitement
    if (E.vue === 'adressage' && E.detailEtape?.synthese)
      return Object.values(E.detailEtape.synthese).some(x => x.total) ? 'en cours' : 'à faire';
  }
  if (v === 'recette' && E.vue === 'recette') return E.detailEtape?.erreurs ? 'en cours' : 'à qualifier';
  return 'à faire';
}
// Indicateur chiffré des écrans Variables et Recette (non cliquable).
function ind(cle, val, lib, grav) {
  return `<div class="chiffre" data-ind="${esc(cle)}"><b style="${grav ? "color:var(--" + grav + ")" : ""}">${val}</b><span>${esc(lib)}</span></div>`;
}
/* ------------------------------------------------------------------ moteur d'adressage (trois niveaux, deux phases) */
const NIVEAUX_ADR = [["physique", "E/S physiques", "voies des cartes"], ["automate", "Variables automate", "table d'échange %MW"],
                     ["teletransmission", "Télétransmission", "points et adresses protocolaires"]];
const ETAT_ADR = {"validée": "b-ok", "à valider": "b-al", "proposée": "b-n", "non résolue": "b-al", "en conflit": "b-err"};
function vueAdressage() {
  const d = E.detailEtape, s = d.synthese, niv = E.nivAdr || "physique", f = E.filtreAdr || "";
  const s4w = /S4W/i.test(d.automate || "") || d.affectations.some(a => a.plateforme === "S4W");
  const niveaux = s4w ? NIVEAUX_ADR.map(x => x[0] === "automate"
    ? ["automate", "Identification S4W-Tools", "identification non connue : aucune adresse mémoire proposée"] : x) : NIVEAUX_ADR;
  const nav = ongletsVariables();
  const prop = d.affectations.filter(a => a.etat === "proposée" && a.niveau !== "teletransmission").length;
  const touchees = d.affectations.filter(a => a.etat === "proposée" && a.actuelle).length;   // impact sur l'existant : doit rester 0
  const lignes = d.affectations.filter(a => a.niveau === niv && (!f || a.etat === f));
  const carte = ([k, lib, sous]) => { const x = s[k]; const bad = x.conflits ? "err" : x.non_resolues ? "al" : x.proposees || x.a_valider ? "n" : "ok";
    return `<button type="button" class="carte-niv ${niv === k ? "on" : ""} ${bad}" data-niv="${k}"><b>${esc(lib)}</b><small>${esc(sous)}</small>
      <span>${x.total} à affecter · <i class="c-ok">${x.validees} validée(s)</i> · ${x.a_valider} à valider · ${x.proposees} proposée(s) · <i class="c-al">${x.non_resolues} non résolue(s)</i> · <i class="c-err">${x.conflits} conflit(s)</i></span></button>`; };
  $("#vue").innerHTML = `<section class="contenu v29-page">${rubanVariables("adressage")}${nav}
   <div class="titre"><div><h1>Adressage automatique</h1><div class="sous">Plateforme ${esc(d.automate || "non renseignée")} · ${esc(d.mode)} · calcul déterministe : rien n'est modifié avant « Appliquer ». Une adresse existante n'est jamais déplacée ; une donnée manquante laisse l'affectation non résolue.</div></div>
     <div class="actions"><button id="ad-recalc" title="Recalcul en lecture seule (aucune adresse écrite)">Recalculer l’aperçu</button><button id="ad-tpk">Exporter TOPKAPI (non qualifié)</button>
     <button class="prim" id="ad-app" ${prop && !d.conflits.length ? "" : "disabled"}>Appliquer ${prop} proposition(s)</button></div></div>
   <div class="niveaux-adr">${niveaux.map(carte).join("")}</div>
   ${d.conflits.length ? `<div class="bloc"><div class="bloc-tete"><h2>Conflits bloquants</h2><span class="aide">l'application est refusée tant qu'il en reste</span></div><ul class="liste-controles">${d.conflits.map(([n, m]) => `<li class="c-err"><b>${esc((niveaux.find(x => x[0] === n) || [, n])[1])}</b> — ${esc(m)}</li>`).join("")}</ul></div>` : ""}
   ${d.besoins.length ? `<div class="avert"><b>Simulation matérielle (rien n'est ajouté) :</b> ${d.besoins.map(b => `${b.manquantes} ${esc(b.nature)} sans voie → ${b.cartes} × ${esc(b.reference)}`).join(" ; ")}. <button class="lien" data-nav="#/materiel">Ouvrir l'étape Matériel</button></div>` : ""}
   ${d.alertes.length ? `<div class="avert">${d.alertes.map(esc).join("<br>")}</div>` : ""}
   <div class="note">Impact sur les données validées : <b>${touchees}</b> adresse existante modifiée (le moteur n'en déplace aucune) · ${d.reservations.length} réservation(s) respectée(s) · empreinte du plan <span class="mono">${esc(d.empreinte)}</span></div>
   <div class="bloc"><div class="bloc-tete"><h2>${esc(niveaux.find(x => x[0] === niv)[1])}</h2>
     <span class="aide">${lignes.length} affectation(s)</span>
     <div class="droite"><select id="ad-filtre" aria-label="Filtrer"><option value="">Tous les états</option>${Object.keys(ETAT_ADR).map(k => `<option ${k === f ? "selected" : ""}>${k}</option>`).join("")}</select>
     ${niv !== "teletransmission" ? `<button id="ad-val" ${lignes.some(a => a.etat === "à valider") ? "" : "disabled"}>Valider les ${lignes.filter(a => a.etat === "à valider").length} affichée(s) à valider</button>` : ""}</div></div>
   ${lignes.length ? `<div class="defile"><table class="t-adr"><thead><tr><th>État</th><th>Repère</th><th>Signal</th><th>Nature</th>${niv === "physique" ? "<th>Carte · voie</th>" : ""}<th>Actuelle</th><th>Proposée</th><th>Origine</th><th>Justification / donnée manquante</th></tr></thead><tbody>
     ${lignes.map(a => `<tr><td><span class="badge ${ETAT_ADR[a.etat] || "b-n"}">${esc(a.etat)}</span></td><td class="mono">${esc(a.repere)}</td><td class="mono">${esc(a.nom)}</td><td><span class="tag">${esc(a.nature)}</span>${a.type_logique ? " " + esc(a.type_logique) : ""}</td>
       ${niv === "physique" ? `<td class="mono">${esc(a.module ? a.module + " · " + a.voie : "—")}</td>` : ""}<td class="mono">${esc(a.actuelle || "—")}</td><td class="mono">${esc(a.proposee || "—")}</td>
       <td>${esc(a.origine || "—")}${a.validee_par ? `<br><small>validée ${esc(a.validee_le)} par ${esc(a.validee_par)}</small>` : ""}</td><td class="justif">${esc(a.motif || a.regle || "")}</td></tr>`).join("")}</tbody></table></div>`
     : '<div class="vide-bloc">Aucune affectation pour ce filtre.</div>'}</div>
   <div class="grille-2">
    <div class="bloc"><div class="bloc-tete"><h2>Réservations</h2><span class="aide">jamais utilisées sans décision explicite</span></div>
     ${d.reservations.length ? `<table><tbody>${d.reservations.map(r => `<tr><td>${esc(r.niveau)}</td><td class="mono">${esc(r.cible)}</td><td>${esc(r.motif)}</td><td><small>${esc(r.par || "")} ${esc(r.le || "")}</small></td><td><button class="lien ad-lib" data-n="${esc(r.niveau)}" data-c="${esc(r.cible)}">Libérer</button></td></tr>`).join("")}</tbody></table>` : '<div class="vide-bloc">Aucune réservation.</div>'}
     <div class="formulaire-ligne"><select id="ad-rn"><option value="voie">Voie (0.3:12-15)</option>${s4w ? "" : `<option value="memoire">Mémoire (%MW1200-%MW1215)</option>`}<option value="protocole">Point / registre</option></select>
      <input id="ad-rc" placeholder="Cible"><input id="ad-rm" placeholder="Motif"><button id="ad-res">Réserver</button></div></div>
    <div class="bloc"><div class="bloc-tete"><h2>Conventions de l'ouvrage</h2><span class="aide">déclarées par l'automaticien, jamais déduites</span></div>
     ${s4w ? `<div class="avert">SOFREL S4W : l'identification des points et des adresses dans S4W-Tools n'est pas connue. Aucun %MW ni registre Schneider n'est proposé.</div>` : `
     <label class="case"><input type="checkbox" id="ad-proto" ${d.protocole_declare ? "checked" : ""}> Registre protocolaire = numéro du mot %MW + décalage</label>
     <label class="case">Décalage <select id="ad-dec"><option value="0" ${d.decalage == 0 ? "selected" : ""}>0</option><option value="1" ${d.decalage == 1 ? "selected" : ""}>1</option></select></label>
     ${d.mode === "Existant" ? `<label class="case"><input type="checkbox" id="ad-dispo" ${d.disponibilite_verifiee ? "checked" : ""}> L'import couvre toute la mémoire utilisée (disponibilité vérifiée)</label>` : ""}`}
     ${d.journal.length ? `<p class="aide">Dernières applications : ${d.journal.slice(-3).reverse().map(j => `${esc(j.le)} (${esc(j.par || "?")}) : ${j.physique || 0} voie(s), ${j.automate || 0} adresse(s)`).join(" · ")}</p>` : ""}</div>
   </div></section>`;
  const recharge = async () => { E.detailEtape = await api("/api/adressage"); vueAdressage(); };
  const act = async (corps, msg) => { await agir(api("/api/adressage/action", corps), msg); await recharge(); };
  document.querySelectorAll("[data-niv]").forEach(b => b.onclick = () => { E.nivAdr = b.dataset.niv; E.filtreAdr = ""; vueAdressage(); });
  $("#ad-filtre").onchange = ev => { E.filtreAdr = ev.target.value; vueAdressage(); };
  $("#ad-recalc").onclick = recharge;
  $("#v29-apercu").onclick = recharge;
  $("#v29-controle").onclick = () => naviguer("#/recette");
  $("#ad-tpk").onclick = () => confirmer("Export TOPKAPI non qualifié", "Fichier .$$t au format relevé sur un projet TOPKAPI réel, jamais encore importé dans TOPKAPI 6.3 : à essayer sur une COPIE d'application.", "Exporter", () => telecharger("topkapi"));
  $("#ad-app").onclick = () => confirmer(`Appliquer ${prop} proposition(s) ?`, "Seules les affectations proposées sont écrites, à l'état « à valider ». Le fichier de l'ouvrage est sauvegardé avant l'opération ; en cas d'erreur, rien n'est modifié.", "Appliquer",
    () => act({action: "appliquer", empreinte: d.empreinte}, "Affectations appliquées : à contrôler puis valider."));
  if ($("#ad-val")) $("#ad-val").onclick = () => { const paires = lignes.filter(a => a.etat === "à valider").map(a => ({ident_eq: a.ident_eq, cle: a.cle}));
    confirmer(`Valider ${paires.length} affectation(s) ?`, "Vous attestez ces adresses ; elles ne seront plus déplacées par le moteur.", "Valider", () => act({action: "valider", niveau: niv, paires}, "Affectations validées.")); };
  document.querySelectorAll(".ad-lib").forEach(b => b.onclick = () => act({action: "liberer", niveau: b.dataset.n, cible: b.dataset.c}, "Réservation libérée."));
  $("#ad-res").onclick = () => act({action: "reserver", niveau: $("#ad-rn").value, cible: $("#ad-rc").value, motif: $("#ad-rm").value}, "Réservation enregistrée.");
  if($("#ad-proto")) $("#ad-proto").onchange = ev => act({action: "protocole", declare: ev.target.checked, decalage: $("#ad-dec").value}, "Convention enregistrée.");
  if($("#ad-dec")) $("#ad-dec").onchange = ev => act({action: "protocole", declare: $("#ad-proto").checked, decalage: ev.target.value}, "Décalage enregistré.");
  if ($("#ad-dispo")) $("#ad-dispo").onchange = ev => act({action: "disponibilite", verifiee: ev.target.checked}, "Disponibilité enregistrée.");
  piedEtape();
}
/* OGIAS V0.29 — Étape 4 : les voies physiques ne sont jamais des variables d'échange. */
function ongletsVariables() {
  return `<nav class="onglets-etape onglets-v29" aria-label="Étape 4 : Variables / Adressage">
   <a href="#/variables" data-nav="#/variables" class="${E.vue === "variables" ? "on" : ""}">Table d'échange</a>
   <a href="#/supervision" data-nav="#/supervision" class="${E.vue === "supervision" ? "on" : ""}">Télétransmission</a>
   <a href="#/adressage" data-nav="#/adressage" class="${E.vue === "adressage" ? "on" : ""}">Adressage automatique</a></nav>`;
}
function rubanVariables(action, exportable=false) {
  return `<div class="v29-ruban" aria-label="Ruban : variables et adressage">
    <div class="v29-ruban-tabs"><b>Général</b><span>Affichage</span><span>Outils</span><span>Variables</span></div>
    <div class="v29-ruban-commands">
      <div class="v29-group"><button type="button" class="v29-action" id="v29-apercu" title="Calcul de prévisualisation sans écriture"><strong>◇</strong> Proposer l'adressage</button><button type="button" class="v29-action" id="v29-controle"><strong>✓</strong> Contrôler</button><small>Ingénierie</small></div>
      ${exportable ? `<div class="v29-group"><button type="button" class="v29-action" id="v29-export"><strong>⇩</strong> Exporter Excel</button><small>Livrables non qualifiés</small></div>` : ""}
      <div class="v29-group"><span class="v29-ruban-hint">Aucune proposition n'est appliquée sans confirmation.</span><small>Sécurité</small></div>
    </div>
  </div>`;
}
function bEtatVariable(etat) {
  const cls=ETAT_ADR[etat]||"b-n";
  return `<span class="badge ${cls}">${esc(etat || "non résolue")}</span>`;
}
function etatsVariable(lignes) {
  const types=["validée", "à valider", "proposée", "non résolue", "en conflit"];
  return `<div class="v29-etats">${types.map(k=>`<button type="button" class="v29-etat" data-vstat="${esc(k)}"><span>${esc(k)}</span><b>${lignes.filter(x=>x.etat_adressage===k).length}</b></button>`).join("")}</div>`;
}
function largeurVueVariable(v) { return `${esc(v.type||"—")}${v.largeur ? ` (${esc(v.largeur)})` : ""}`; }
function filtrerTableV29(prefix, lignes) {
  const recherche=(E[prefix+'Recherche']||'').toLocaleLowerCase('fr');
  const etat=E[prefix+'Statut']||'';
  const famille=E[prefix+'Famille']||'';
  const equip=E[prefix+'Equip']||'';
  let nb=0;
  document.querySelectorAll('.v29-data-row').forEach(tr=>{
    const v=lignes[Number(tr.dataset.vid)];
    const oui=(!etat||v.etat_adressage===etat)&&(!famille||v.famille===famille)&&
      (!equip||(v.repere||v.ident_eq)===equip)&&
      (!recherche||[v.nom,v.famille,v.repere,v.libelle,v.adresse,v.adresse_proposee,
        v.adresse_protocole_proposee,v.information].some(x=>String(x||'').toLocaleLowerCase('fr').includes(recherche)));
    tr.hidden=!oui;
    if(oui)nb++;
  });
  const compte=$('#v29-visible'); if(compte)compte.textContent=`${nb} ligne(s) affichée(s)`;
  const vider=$('#v29-empty'); if(vider)vider.hidden=nb>0;
  document.querySelectorAll('[data-vstat]').forEach(b=>b.classList.toggle('on',!!etat&&b.dataset.vstat===etat));
}
function brancherFiltresV29(prefix,lignes,refresh) {
  const input=$('#v29-search');
  if(input)input.oninput=e=>{E[prefix+'Recherche']=e.target.value;filtrerTableV29(prefix,lignes);};
  for(const [id,key] of [['v29-family','Famille'],['v29-equip','Equip']]) {
    const sel=$('#'+id);
    if(sel)sel.onchange=e=>{E[prefix+key]=e.target.value;filtrerTableV29(prefix,lignes);};
  }
  document.querySelectorAll('[data-vstat]').forEach(b=>b.onclick=()=>{
    E[prefix+'Statut']=E[prefix+'Statut']===b.dataset.vstat?'':b.dataset.vstat;
    filtrerTableV29(prefix,lignes);
  });
  if($('#v29-reset'))$('#v29-reset').onclick=()=>{
    E[prefix+'Recherche']='';E[prefix+'Statut']='';E[prefix+'Famille']='';E[prefix+'Equip']='';refresh();
  };
  filtrerTableV29(prefix,lignes);
}
function filtresV29(prefix,lignes) {
  const familles=[...new Set(lignes.map(v=>v.famille).filter(Boolean))].sort();
  const equips=[...new Set(lignes.map(v=>v.repere||v.ident_eq).filter(Boolean))].sort();
  const opts=(arr,val)=>arr.map(x=>`<option value="${esc(x)}" ${val===x?'selected':''}>${esc(x)}</option>`).join('');
  return `<div class="v29-filtres">
    <label>Rechercher<input id="v29-search" type="search" autocomplete="off" value="${esc(E[prefix+'Recherche']||'')}" placeholder="Nom, variable, adresse, équipement…"></label>
    <label>Famille<select id="v29-family"><option value="">Toutes</option>${opts(familles,E[prefix+'Famille'])}</select></label>
    <label>Équipement<select id="v29-equip"><option value="">Tous</option>${opts(equips,E[prefix+'Equip'])}</select></label>
    <button type="button" id="v29-reset">Effacer les filtres</button></div>`;
}
function vueVariables() {
  const d=E.detailEtape,neuf=d.mode==='Neuf',lignes=d.lignes||[], prefix='var';
  const selected = Number.isInteger(E.varSel) && E.varSel >= 0 && E.varSel < lignes.length ? E.varSel : 0;
  E.varSel=selected;
  const v=lignes[selected];
  const ouvrir=E.varDetail!==false;
  const details=v && ouvrir ? `<aside class="v29-detail" aria-label="Détail de la variable">
    <div class="v29-detail-head"><h2>Détail de la variable</h2><button id="v29-close" aria-label="Replier le détail">×</button></div>
    <div class="v29-detail-inner"><p class="mono v29-strong">${esc(v.nom)}</p><p>${bEtatVariable(v.etat_adressage)}</p>
    <dl><dt>Équipement</dt><dd>${esc(v.repere||'—')}</dd><dt>Famille</dt><dd>${esc(v.famille||'—')}</dd>
    <dt>Type / largeur</dt><dd>${largeurVueVariable(v)}</dd>
    <dt>Adresse actuelle</dt><dd class="mono">${esc(v.adresse||'—')}</dd>
    <dt>Adresse proposée</dt><dd class="mono">${esc(v.adresse_proposee||'—')}</dd>
    <dt>Origine de l'adresse</dt><dd>${esc(v.origine_adressage||v.origine||'—')}</dd>
    <dt>Règle</dt><dd>${esc(v.regle||'—')}</dd><dt>Motif</dt><dd>${esc(v.motif||'—')}</dd>
    <dt>Source E/S (lecture seule)</dt><dd>${esc(v.source_es||'Aucune source E/S directe')}</dd>
    <dt>Voie physique</dt><dd>${esc(v.source_es?(v.voie_es||'voie non placée — étape Matériel'):'Sans objet')}</dd>
    <dt>Validation</dt><dd>${esc(v.validee_le||'Non validée')} ${v.validee_par?`par ${esc(v.validee_par)}`:''}</dd></dl>
    <div class="v29-detail-buttons">${neuf?'<button id="v29-edit-var">Contrôler / Éditer</button>':''}
    ${v.ident_eq?'<button id="v29-open-eq">Ouvrir la fiche équipement</button>':''}</div></div>
  </aside>`:'';
  $("#vue").innerHTML=`<section class="contenu v29-page">${rubanVariables('variables',true)}
    ${ongletsVariables()}<div class="v29-title"><div><h1>Table d'échange</h1><p>${esc(d.note)}</p></div>
    <button id="v29-toggle-detail" aria-expanded="${ouvrir}">${ouvrir?'Masquer':'Afficher'} le détail</button></div>
    ${!neuf?'<div class="avert">Projet existant : adresses historiques en lecture seule. Disponibilité non vérifiée tant qu’elle n’est pas attestée.</div>':''}
    ${etatsVariable(lignes)}${filtresV29(prefix,lignes)}
    <div class="v29-layout ${ouvrir?'with-detail':''}"><div class="bloc v29-tablebox">
    <div class="v29-tablehead"><h2>Variables et adresses d'échange</h2><span id="v29-visible"></span></div>
    <div class="v29-table-scroll"><table class="v29-table"><thead><tr><th>Variable</th><th>Famille</th><th>Type / largeur</th><th>Adresse actuelle</th><th>Adresse proposée</th><th>Origine</th><th>Règle</th><th>État</th></tr></thead><tbody>
    ${lignes.map((x,i)=>`<tr class="v29-data-row ${selected===i&&ouvrir?'v29-sel':''}" data-vid="${i}" tabindex="0" aria-label="Ouvrir ${esc(x.nom)}">
     <td class="mono">${esc(x.nom)}</td><td>${esc(x.famille||'—')}</td><td>${largeurVueVariable(x)}</td>
     <td class="mono">${esc(x.adresse||'—')}</td><td class="mono">${esc(x.adresse_proposee||'—')}</td>
     <td>${esc(x.origine_adressage||x.origine||'—')}</td><td title="${esc(x.regle||x.motif||'')}">${esc(x.regle||x.motif||'—')}</td>
     <td>${bEtatVariable(x.etat_adressage)}</td></tr>`).join('')}
    </tbody></table></div><div class="vide-bloc" id="v29-empty" hidden>Aucune ligne pour ces filtres.</div></div>${details}</div>
    <p class="note">Une E/S physique (ET/ST/EA/SA) n'est jamais une ligne de télétransmission : son nom et sa voie ne sont consultables que dans la source de la variable. Les adresses proposées ne sont pas appliquées.</p>
    <p class="note">Export Control Expert / XSY : non qualifié en environnement industriel.</p></section>`;
  $('#v29-toggle-detail').onclick=()=>{E.varDetail=!ouvrir;vueVariables();};
  if($('#v29-close'))$('#v29-close').onclick=()=>{E.varDetail=false;vueVariables();};
  brancherFiltresV29(prefix,lignes,vueVariables);
  document.querySelectorAll('.v29-data-row').forEach(tr=>{
    const select=()=>{E.varSel=Number(tr.dataset.vid);E.varDetail=true;vueVariables();};
    tr.onclick=select;tr.onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();select();}}
  });
  $('#v29-apercu').onclick=()=>naviguer('#/adressage');
  $('#v29-controle').onclick=()=>naviguer('#/recette');
  $('#v29-export').onclick=()=>telecharger('variables');
  if($('#v29-open-eq'))$('#v29-open-eq').onclick=()=>allerOuvrage({nature:'eq',valeur:v.ident_eq});
  if($('#v29-edit-var'))$('#v29-edit-var').onclick=()=>editerVariableV29(v);
  piedEtape();
}
function editerVariableV29(v) {
  const m=ouvrirModale(`<div class="boite-tete"><h2>Contrôler ${esc(v.nom)}</h2></div><div class="boite-corps"><div class="champs">
    <label>Adresse table d'échange</label><input id="v-adr" value="${esc(v.adresse)}" placeholder="%MW...">
    <label>Commentaire</label><input id="v-com" value="${esc(v.commentaire)}">
    <label>Libellé TOPKAPI</label><input id="v-lib" value="${esc(v.libelle)}"></div>
    <p class="note">L'adresse proposée dans l'aperçu n'est pas appliquée automatiquement. Une adresse validée ne change qu'après confirmation.</p>
    <div class="erreur-form" id="m-err"></div></div><div class="boite-pied"><button data-fermer>Annuler</button>
    <button id="v-save">Enregistrer</button><button class="prim" id="v-valid">Valider l'adresse</button></div>`);
  const refresh=async()=>{fermerModale();E.detailEtape=await api('/api/variables');vueVariables();};
  m.querySelector('#v-save').onclick=async()=>{try{
    const adresse=m.querySelector('#v-adr').value;
    if(adresse!==v.adresse){
      if(v.validee&&!window.confirm('Cette adresse est validée. Retirer sa validation et la modifier ?'))return;
      await api('/api/variables/action',{action:'adresse',ident_eq:v.ident_eq,cle:v.cle,adresse,confirmer_changement:v.validee});
    }
    await api('/api/variables/action',{action:'textes',ident_eq:v.ident_eq,cle:v.cle,
      commentaire:m.querySelector('#v-com').value,libelle:m.querySelector('#v-lib').value});
    await refresh();
  }catch(e){m.querySelector('#m-err').textContent=e.message;}};
  m.querySelector('#v-valid').onclick=async()=>{try{
    if(m.querySelector('#v-adr').value!==v.adresse){m.querySelector('#m-err').textContent='Enregistrez d’abord les modifications.';return;}
    const r=await api('/api/variables/action',{action:'valider',paires:[{ident_eq:v.ident_eq,cle:v.cle}]});
    if(r.refus.length){m.querySelector('#m-err').textContent=r.refus.join(' | ');return;}
    await refresh();
  }catch(e){m.querySelector('#m-err').textContent=e.message;}};
}
function vueSupervision() {
  const d=E.detailEtape,lignes=d.lignes||[],prefix='tel';
  const selected=Number.isInteger(E.telSel)&&E.telSel>=0&&E.telSel<lignes.length?E.telSel:0;
  E.telSel=selected;
  const v=lignes[selected],ouvrir=E.telDetail!==false;
  const details=v&&ouvrir?`<aside class="v29-detail" aria-label="Détail du point">
    <div class="v29-detail-head"><h2>Détail de la télétransmission</h2><button id="v29-close" aria-label="Replier le détail">×</button></div>
    <div class="v29-detail-inner"><p class="mono v29-strong">${esc(v.identifiant_point||v.nom)}</p>
    <p>${bEtatVariable(v.etat_adressage)}</p><dl><dt>Équipement</dt><dd>${esc(v.repere||'—')}</dd>
    <dt>Variable source</dt><dd class="mono">${esc(v.variable_source||v.nom)}</dd>
    <dt>Adresse de la source</dt><dd class="mono">${esc(v.adresse||'—')}</dd>
    <dt>Adresse protocolaire actuelle</dt><dd>${esc(v.adresse_protocole_actuelle||'—')}</dd>
    <dt>Adresse protocolaire proposée</dt><dd>${esc(v.adresse_protocole_proposee||'—')}</dd>
    <dt>Correspondance TR ↔ RTR</dt><dd>${esc(v.correspondance||'Sans objet / à vérifier')}</dd>
    <dt>Origine</dt><dd>${esc(v.origine_adressage||'—')}</dd>
    <dt>Règle</dt><dd>${esc(v.regle||'—')}</dd><dt>Motif</dt><dd>${esc(v.motif||'—')}</dd>
    <dt>Validation</dt><dd>${esc(v.validee_le||'Non renseignée')} ${v.validee_par?`par ${esc(v.validee_par)}`:''}</dd></dl>
    <div class="v29-detail-buttons">${v.ident_eq?'<button id="v29-open-eq">Ouvrir la fiche équipement</button>':''}</div></div></aside>`:'';
  $('#vue').innerHTML=`<section class="contenu v29-page">${rubanVariables('supervision',false)}${ongletsVariables()}
    <div class="v29-title"><div><h1>Télétransmission</h1><p>${esc(d.note)}</p></div>
    <button id="v29-toggle-detail" aria-expanded="${ouvrir}">${ouvrir?'Masquer':'Afficher'} le détail</button></div>
    <div class="avert">${esc(d.statut||'À rapprocher')} — Aucun format S4W-Tools ou TOPKAPI 6.3 n'est industriellement qualifié.</div>
    ${etatsVariable(lignes)}${filtresV29(prefix,lignes)}
    <div class="v29-layout ${ouvrir?'with-detail':''}"><div class="bloc v29-tablebox">
    <div class="v29-tablehead"><h2>Points et correspondances</h2><span id="v29-visible"></span></div>
    <div class="v29-table-scroll"><table class="v29-table"><thead><tr><th>Point</th><th>Famille</th><th>Variable source</th><th>Adresse source</th><th>Protocole (actuelle)</th><th>Protocole (proposée)</th><th>TR ↔ RTR</th><th>État</th></tr></thead><tbody>
    ${lignes.map((x,i)=>`<tr class="v29-data-row ${selected===i&&ouvrir?'v29-sel':''}" data-vid="${i}" tabindex="0" aria-label="Voir le point ${esc(x.nom)}">
    <td class="mono">${esc(x.identifiant_point||x.nom)}</td><td>${esc(x.famille)}</td>
    <td class="mono">${esc(x.variable_source||'—')}</td><td class="mono">${esc(x.adresse||'—')}</td>
    <td>${esc(x.adresse_protocole_actuelle||'—')}</td><td>${esc(x.adresse_protocole_proposee||'—')}</td>
    <td class="mono">${esc(x.correspondance||'—')}</td><td>${bEtatVariable(x.etat_adressage)}</td></tr>`).join('')}
    </tbody></table></div><div class="vide-bloc" id="v29-empty" hidden>Aucun point pour ces filtres.</div></div>${details}</div>
    <p class="note">Le point de télétransmission et son adresse protocolaire sont distincts de la variable source ; aucune adresse n'est inventée lorsque la convention est inconnue.</p></section>`;
  $('#v29-toggle-detail').onclick=()=>{E.telDetail=!ouvrir;vueSupervision();};
  if($('#v29-close'))$('#v29-close').onclick=()=>{E.telDetail=false;vueSupervision();};
  brancherFiltresV29(prefix,lignes,vueSupervision);
  document.querySelectorAll('.v29-data-row').forEach(tr=>{
    const select=()=>{E.telSel=Number(tr.dataset.vid);E.telDetail=true;vueSupervision();};
    tr.onclick=select;tr.onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();select();}};
  });
  $('#v29-apercu').onclick=()=>naviguer('#/adressage');
  $('#v29-controle').onclick=()=>naviguer('#/recette');
  if($('#v29-open-eq'))$('#v29-open-eq').onclick=()=>allerOuvrage({nature:'eq',valeur:v.ident_eq});
  piedEtape();
}

const ROUTE_ETAPE = {"Ouvrage": "#/inventaire", "Équipements": "#/inventaire", "Liste des E/S et matériel": "#/materiel", "Variables": "#/variables"};
function vueRecette() {
  const d = E.detailEtape, f = E.filtreRecette || "";
  const etapes = [...new Set(d.controles.map(c => c.etape))];
  const nb = (et, niv) => d.controles.filter(c => c.etape === et && (!niv || c.niveau === niv)).length;
  const vis = d.controles.filter(c => !f || c.etape === f);
  $("#vue").innerHTML = `<section class="contenu"><div class="titre"><div><h1>Recette et livrables</h1><div class="sous">Révision ${esc(d.revision)} · ${esc(d.note)}</div></div><div class="actions"><button id="r-actualiser">Actualiser les contrôles</button><button class="prim" id="r-dossier" title="Zip : sommaire imprimable en PDF, équipements, E/S, cartes, variables et formats cibles">Dossier de recette</button></div></div>
   <div class="chiffres">${d.erreurs?ind('ERR', d.erreurs, 'erreurs', 'err'):''}${d.alertes?ind('ALT', d.alertes, 'alertes', 'al'):''}</div>
   <div class="bloc"><div class="bloc-tete"><h2>Contrôles consolidés</h2><span class="aide">classés par étape du parcours : chaque constat se corrige à l'endroit indiqué</span></div>
   ${etapes.length ? `<div class="compteurs"><span class="chip ${f ? "" : "on"}" data-et="">Toutes<b>${d.controles.length}</b></span>${etapes.map(et => `<span class="chip ${f === et ? "on" : ""}" data-et="${esc(et)}">${esc(et)}<b>${nb(et)}</b>${nb(et, "Erreur") ? `<i class="pt-etat pt-err" style="margin-left:6px"></i>` : ""}</span>`).join("")}</div>` : ""}
   ${vis.length ? `<table><thead><tr><th style="width:90px">Niveau</th><th style="width:190px">Étape</th><th>Constat</th><th style="width:110px"></th></tr></thead><tbody>${vis.map((c, i) => `<tr><td><span class="badge ${c.niveau === 'Erreur' ? 'b-err' : 'b-al'}">${esc(c.niveau)}</span></td><td>${esc(c.etape)}</td><td>${esc(c.message)}</td>
     <td style="text-align:right"><button class="lien r-corr" data-i="${d.controles.indexOf(c)}">${c.ident && ["Équipements", "Ouvrage"].includes(c.etape) ? "Ouvrir la fiche" : "Aller à l'étape"}</button></td></tr>`).join('')}</tbody></table>`
     : '<div class="vide-bloc">Aucune anomalie détectée par les contrôles automatisés.</div>'}
   ${d.tronque ? '<div class="avert">Affichage limité aux 500 premiers contrôles.</div>' : ''}</div>
   <div class="avert">Statut industriel : NON QUALIFIÉ. Une recette locale sans erreur ne vaut pas validation des fichiers dans Control Expert, SOFREL ou TOPKAPI.</div></section>`;
  $("#r-actualiser").onclick = async () => { E.detailEtape = await api('/api/recette'); rendre(); };
  $("#r-dossier").onclick = () => confirmer("Constituer le dossier de recette ?", "Archive zip des livrables à partir des exports existants, avec un sommaire imprimable en PDF (empreintes, pièces non produites et leur motif, points restant à traiter). Exports non qualifiés : à vérifier dans les logiciels cibles.", "Télécharger le dossier", () => telecharger("dossier_recette"));
  document.querySelectorAll("[data-et]").forEach(x => x.onclick = () => { E.filtreRecette = x.dataset.et; vueRecette(); });
  document.querySelectorAll(".r-corr").forEach(b => b.onclick = () => {
    const c = d.controles[+b.dataset.i];
    if (c.ident && (c.etape === "Équipements" || c.etape === "Ouvrage")) { E.sel = {nature: "eq", valeur: c.ident}; location.hash = "#/inventaire"; }
    else location.hash = ROUTE_ETAPE[c.etape] || "#/inventaire";
  });
}
function enTete() { V31.render(E, ETAPES, etatEtape, vueEtape); }
/* ------------------------------------------------------------------ accueil */
function vueAccueil() {
  const a = E.accueil;
  const lignes = a.ouvrages.map(f => `<tr class="cliquable" data-chemin="${esc(f.chemin)}">
      <td class="mono"><b>${esc(f.repere)}</b></td><td>${esc(f.libelle)}</td><td>${esc(f.mode)}</td>
      <td>${f.equipements}</td><td>${esc(f.date)}</td>
      <td style="text-align:right"><button data-ouvrir="${esc(f.chemin)}">Ouvrir</button>
      <button class="danger" data-supprimer="${esc(f.chemin)}" data-nom="${esc(f.repere)}">Supprimer</button></td></tr>`).join("");
  $("#vue").innerHTML = `<div class="accueil">
    <h1>Mes ouvrages</h1><p class="intro">Créez un ouvrage après vérification de sa fiche, ou reprenez un ouvrage enregistré.</p>
    <div class="cartes">
      <div class="carte-choix" data-nouveau="Neuf"><div class="pastille">+</div><div><h3>Projet neuf</h3>
        <p>Créer la fiche de l’ouvrage, puis construire les équipements, E/S et variables.</p></div></div>
      <div class="carte-choix" data-nouveau="Existant"><div class="pastille">↻</div><div><h3>Projet existant</h3>
        <p>Inventaire de l'ouvrage, puis lecture du programme en place, sans jamais le modifier.</p></div></div>
    </div>
    <div class="bloc"><div class="bloc-tete"><h2>Ouvrages enregistrés</h2><span class="aide">${a.ouvrages.length} ouvrage(s) · ${esc(a.dossier)}</span></div>
    ${a.ouvrages.length ? `<table><thead><tr><th>Repère</th><th>Libellé</th><th>Mode</th><th>Équipements</th><th>Modifié le</th><th></th></tr></thead><tbody>${lignes}</tbody></table>`
      : `<div class="vide-bloc">Aucun ouvrage pour l'instant. Choisissez « Projet neuf » ou « Projet existant ».</div>`}</div>
    <div class="note">Version ${esc(a.version)} · Un ouvrage supprimé part dans la corbeille du dossier Projets (${a.corbeille} élément(s)).</div></div>`;
  document.querySelectorAll("[data-nouveau]").forEach(c => c.onclick = async () => {
    await agir(api("/api/nouveau", {mode: c.dataset.nouveau}));
    E.ficheDraft = null; E.ficheDirty = false;
    allerOuvrage({nature: "ouvrage", valeur: ""});
  });
  const ouvrir = async chemin => { await agir(api("/api/ouvrir", {chemin})); E.ficheDraft = null; E.ficheDirty = false; naviguer("#/dashboard"); };
  document.querySelectorAll("tr[data-chemin]").forEach(tr => tr.onclick = ev => { if (!ev.target.closest("button")) ouvrir(tr.dataset.chemin); });
  document.querySelectorAll("[data-ouvrir]").forEach(b => b.onclick = () => ouvrir(b.dataset.ouvrir));
  document.querySelectorAll("[data-supprimer]").forEach(b => b.onclick = () => confirmer(
    `Supprimer l'ouvrage ${b.dataset.nom} ?`, "Il disparaît de la liste. Le fichier n'est pas effacé : il est rangé dans la corbeille du dossier Projets.",
    "Supprimer", async () => { await agir(api("/api/supprimer_ouvrage", {chemin: b.dataset.supprimer}), "Ouvrage supprimé (corbeille)."); allerAccueil(); }));
}

/* ------------------------------------------------------------------ ouvrage : explorateur */
function eqParIdent(i) { return E.ouvrage.equipements.find(e => e.ident === i); }
function vueOuvrage() {
  if (E.ouvrage.en_conception) {
    $("#vue").innerHTML = `<section class="creation-page"><div class="creation-intro"><div class="creation-fil">Mes ouvrages &nbsp;›&nbsp; Création</div><h1>Créer un ouvrage</h1><p>Renseignez l'identité de l'installation avant de commencer le projet.</p></div><section class="contenu creation-contenu" id="contenu"></section></section>`;
    contenu();
    return;
  }
  $("#vue").innerHTML = `<aside><div class="aside-tete"><h2>Ouvrage → UF → équipements</h2>
      ${E.ouvrage.en_conception ? `<p class="aide-champs">Validez d’abord la création de l’ouvrage avant d’ajouter des équipements.</p>` : `<input id="recherche" placeholder="Rechercher un repère, un libellé, un type…" value="${esc(E.recherche)}">`}
      <div class="aside-btns" ${E.ouvrage.en_conception ? "hidden" : ""}><button id="b-uf">+ Unité fonctionnelle</button><button class="prim" id="b-eq">+ Équipement</button>
      <button id="b-import">Importer une liste…</button></div></div><div class="arbre" id="arbre"></div></aside>
    <section class="contenu" id="contenu"></section>`;
  if (!E.ouvrage.en_conception) {
    $("#recherche").oninput = ev => { E.recherche = ev.target.value; arbre(); };
    $("#b-uf").onclick = () => modaleUF();
    $("#b-eq").onclick = () => modaleEquipement(null, ufSelectionnee());
    $("#b-import").onclick = modaleImport;
  }
  arbre(); contenu();
}
function ufSelectionnee() {
  const s = E.sel;
  if (s.nature === "uf") return s.valeur;
  if (s.nature === "eq") { const e = eqParIdent(s.valeur); return e ? e.uf : ""; }
  return "";
}
function arbre() {
  const o = E.ouvrage, q = E.recherche.toLowerCase();
  const visibles = o.equipements.filter(e => !q || (e.pcf + " " + e.libelle + " " + e.type + " " + e.designation).toLowerCase().includes(q));
  const sel = (n, v) => E.sel.nature === n && E.sel.valeur === v ? " sel" : "";
  const charte = o.format_repere === "12";        // charte ESB/RESO : repère sans sous-ensemble
  const listeEq = (eqs, sansUf) => {
    let h = "", se = null;
    eqs.forEach(e => {
      if (e.se !== se) { se = e.se; const lib = (o.sous_ensembles.find(x => x.code === se) || {}).libelle;
        if (!(charte && se === "00" && !lib)) h += `<div class="separateur-se${sansUf ? " sans-uf" : ""}">${esc(se)}${lib ? " · " + esc(lib) : ""}</div>`; }
      h += `<div class="noeud eq${sansUf ? " sans-uf" : ""}${sel("eq", e.ident)}" data-n="eq" data-v="${e.ident}">
        <span class="tag ${e.etat === "à coder" ? "acoder" : ""}">${esc(e.type.replace(/--$/, ""))}</span>
        <span class="mono">${esc(e.pcf.slice(charte ? 8 : 6))}</span><span class="lib">${esc(e.libelle || e.designation)}</span>${pointEtat(e)}</div>`;
    });
    return h;
  };
  let h = `<div class="noeud racine${sel("ouvrage", "")}" data-n="ouvrage" data-v="">▾ ${esc(o.prefixe || "Nouvel ouvrage")}
    <span class="lib" style="font-weight:400">${esc(o.identification.libelle)}</span><span class="nb">${o.equipements.length}</span></div>`;
  if (o.unites.length) {
    o.unites.forEach(u => {
      const eqs = visibles.filter(e => e.uf === u.code);
      h += `<div class="noeud uf${sel("uf", u.code)}" data-n="uf" data-v="${esc(u.code)}">▾ ${esc(u.code)} — ${esc(u.libelle || "sans libellé")}
        <span class="nb">${o.equipements.filter(e => e.uf === u.code).length}</span></div>${listeEq(eqs, false)}
        <div class="ajout" data-ajout-uf="${esc(u.code)}">+ Ajouter un équipement dans ${esc(u.code)}</div>`;
    });
    const codes = new Set(o.unites.map(u => u.code)), communs = visibles.filter(e => !codes.has(e.uf));
    if (communs.length) h += `<div class="noeud uf${sel("commun", "")}" data-n="commun" data-v="">▾ ${esc(o.libelle_communs)}
        <span class="nb">${communs.length}</span></div>${listeEq(communs, false)}`;
  } else {
    h += listeEq(visibles, true);
  }
  if (!o.en_conception) h += `<div class="ajout" style="padding-left:22px" data-ajout-uf-nouvelle="1">+ Ajouter une unité fonctionnelle</div>`;
  if (!o.equipements.length) h += `<div class="vide-bloc">${o.en_conception ? "Confirmez la fiche ouvrage avant de construire l’inventaire." : "Aucun équipement.<br>« + Équipement » ou « Importer une liste… »."}</div>`;
  $("#arbre").innerHTML = h;
  document.querySelectorAll("#arbre .noeud").forEach(n => {
    n.onclick = () => { E.sel = {nature: n.dataset.n, valeur: n.dataset.v}; E.filtreRole = "Toutes"; arbre(); contenu(); };
    if (n.dataset.n === "eq") n.ondblclick = () => modaleEquipement(eqParIdent(n.dataset.v));
  });
  document.querySelectorAll("[data-ajout-uf]").forEach(a => a.onclick = () => modaleEquipement(null, a.dataset.ajoutUf));
  const ajouterUF = document.querySelector("[data-ajout-uf-nouvelle]");
  if (ajouterUF) ajouterUF.onclick = () => modaleUF();
}

/* ------------------------------------------------------------------ ouvrage : détail */
async function contenu() { await contenuDetail(); piedEtape(); }
async function contenuDetail() {
  const c = $("#contenu"), s = E.sel;
  if (s.nature === "eq" && eqParIdent(s.valeur)) {
    const fiche = await api("/api/equipement?ident=" + s.valeur);
    if (!document.body.contains(c) || E.sel !== s) return;    // l'écran a changé pendant le chargement
    return detailEquipement(fiche);
  }
  if (s.nature === "uf" || s.nature === "commun") return detailGroupe();
  E.sel = {nature: "ouvrage", valeur: ""};
  detailOuvrage(c);
}
function champ(id, label, valeur, attrs = "") { return `<label for="${id}">${label}</label><input id="${id}" data-champ="${id}" value="${esc(valeur)}" ${attrs}>`; }
function selectListe(id, label, valeur, options, vide = "— Non défini —") {
  const entries = options.map(o => typeof o === "string" ? {code: o, libelle: o} : o);
  const ancien = valeur && !entries.some(o => o.code === valeur) ? `<option value="${esc(valeur)}" selected>${esc(valeur)} (valeur historique)</option>` : "";
  const opt = o => `<option value="${esc(o.code)}" ${o.code === valeur ? "selected" : ""}>${esc(o.code)}${o.libelle && o.libelle !== o.code ? " — " + esc(o.libelle) : ""}</option>`;
  // Les 15 communes restent classées par régie, sans introduire de fausses données d'ouvrage.
  const choix = id === "lieu"
    ? [["ESB", "Régie Eau Seine & Bièvre (ESB)"], ["RESO", "Régie RESO"], ["AUTRE", "Autres lieux"]]
        .map(([code, nom]) => {
          const lignes = entries.filter(o => (o.regie || "AUTRE").toUpperCase() === code);
          return lignes.length ? `<optgroup label="${esc(nom)}">${lignes.map(opt).join("")}</optgroup>` : "";
        }).join("")
    : entries.map(opt).join("");
  return `<label for="${id}">${esc(label)}</label><div class="select-avec-aide"><select id="${id}" data-choix="${id}">
    <option value="">${esc(vide)}</option>${choix}${ancien}</select></div>`;
}
function detailOuvrage(c) {
  const o = E.ouvrage, i = E.ficheDraft || o.identification, l = E.listes || {lieux:[], types_ouvrage:[], automates:[], protocoles:[]};
  const okLieu = /^[A-Z0-9]{4}$/.test(i.lieu), okCode = /^[A-Z]{2}$/.test(i.code_ouvrage);
  const actuelNumero = i.numero_ouvrage || "";
  const parDomaine = {};
  o.equipements.forEach(e => parDomaine[e.domaine || "Non classé"] = (parDomaine[e.domaine || "Non classé"] || 0) + 1);
  const acoder = o.equipements.filter(e => e.etat === "à coder").length;
  const typeActuel = l.types_ouvrage.find(t => t.code === i.code_ouvrage);
  const ancienType = i.code_ouvrage && !typeActuel ? `<option value="${esc(i.code_ouvrage)}" selected>${esc(i.code_ouvrage)} — ${esc(i.type_ouvrage || "Ancien type hors référentiel")}</option>` : "";
  c.innerHTML = `<div class="fil">${esc(o.prefixe || "Nouvel ouvrage")} · ${o.en_conception ? (o.creation_en_attente ? "Création non confirmée" : "Brouillon") : "Fiche enregistrée"}</div>
   ${(o.referentiel && o.referentiel.ecarts.length) ? `<div class="avert"><b>Référentiel figé dans cet ouvrage :</b> ${esc(o.referentiel.version_ouvrage || "version antérieure")}.
     L'outil propose ${esc(o.referentiel.version_outil)}, qui modifie ${o.referentiel.ecarts.length} type(s) utilisé(s) ici
     (${o.referentiel.ecarts.map(x => `<b>${esc(x.type)}</b>${x.ajoutees.length ? " +" + esc(x.ajoutees.join(", +")) : ""}${x.regles.length ? " · règles " + esc(x.regles.join(", ")) : ""}`).join(" ; ")}).
     Rien n'est appliqué sans votre accord. <button class="lien" id="ref-adopter">Examiner et appliquer…</button></div>` : ""}
   ${o.referentiel?.sauvegarde_adoption ? `<div class="note adoption-retour"><b>Sauvegarde avant adoption</b>
     <a id="ref-sauvegarde" href="/api/export?quoi=sauvegarde_adoption" download>Télécharger la sauvegarde du projet</a>
     ${o.referentiel.adoption_annulable ? `<button id="ref-annuler-adoption">Annuler l'adoption</button>` : ""}
     ${o.referentiel.sauvegarde_annulation_adoption ? `<a href="/api/export?quoi=sauvegarde_annulation_adoption" download>Télécharger l'état avant annulation</a>` : ""}</div>` : ""}
   ${!o.en_conception && (!okLieu || !okCode) ? `<div class="avert" id="fiche-identification-avert">Pour commencer : sélectionnez un lieu (4 caractères) et un type d'ouvrage (code à 2 lettres). Vous pouvez enrichir ces listes avec « Gérer les listes ».</div>` : ""}
   <div class="bloc"><div class="bloc-tete"><h2>Identification de l'ouvrage</h2><span class="aide">${esc(i.mode === "Existant" ? "Projet existant" : "Projet neuf")}</span><div class="droite"><button id="gerer-listes" type="button">${V31.icon("settings",14)} Gérer les listes…</button></div></div>
     ${o.en_conception ? `<div class="creation-identite">
       <div class="creation-projet">${esc(i.mode === "Existant" ? "Projet existant — conservation des adresses" : "Projet neuf — génération et adressage")}</div>
       <div class="creation-grille">
        <div class="creation-champ">${selectListe("lieu", "Lieu *", i.lieu, l.lieux, "— Sélectionner un lieu —")}</div>
        <div class="creation-champ"><label for="type_ouvrage">Type d'ouvrage *</label><select id="type_ouvrage"><option value="">— Sélectionner un type —</option>${l.types_ouvrage.map(t => `<option value="${esc(t.code)}" ${t.code === i.code_ouvrage ? "selected" : ""}>${esc(t.libelle)} (${esc(t.code)})</option>`).join("")}${ancienType}</select></div>
        <div class="creation-champ">${champ("libelle", "Libellé de l'ouvrage *", i.libelle, 'placeholder="Désignation de l’ouvrage"')}</div>
        <div class="creation-champ"><label for="numero_ouvrage">Numéro d'ouvrage *</label><div class="numero-ouvrage-choix"><input id="numero_ouvrage" data-champ="numero_ouvrage" value="${esc(E.ficheDraft?.numero_ouvrage ?? actuelNumero)}" maxlength="2" inputmode="numeric" placeholder="01 à 99" title="Proposé automatiquement et modifiable"><button type="button" id="proposer-numero">Proposer</button></div></div>
        <div class="creation-champ"><label for="code-ouvrage-affiche">Code généré</label><div class="code-ouvrage-affiche" id="code-ouvrage-affiche" aria-live="polite"></div><input id="code_ouvrage" type="hidden" value="${esc(i.code_ouvrage)}"></div>
        <div class="creation-champ">${champ("localisation", "Localisation précise", i.localisation, 'placeholder="Adresse, site ou précision géographique"')}</div>
       </div>
       <details class="creation-avance"><summary>Paramètres du projet <span>facultatifs au démarrage</span></summary>
        <div class="creation-grille">
          <div class="creation-champ">${selectListe("automate", "Automate / télégestion", i.automate, l.automates)}</div>
          <div class="creation-champ"><label for="communication-choix">Communication</label><button class="selection-multiple" id="communication-choix" data-valeur="${esc(i.communication || "")}" type="button">${esc(i.communication || "— Choisir les protocoles —")} <span aria-hidden="true">▾</span></button></div>
          <div class="creation-champ">${champ("revision", "Révision", i.revision, 'maxlength="4" title="Règle documentaire conservée"')}</div>
        </div>
       </details>
      </div>` : `<div class="formulaire formulaire-ouvrage">
       ${selectListe("lieu", "Lieu", i.lieu, l.lieux, "— Sélectionner un lieu —")}
       <label for="type_ouvrage">Type d'ouvrage</label><select id="type_ouvrage"><option value="">— Sélectionner un type —</option>${l.types_ouvrage.map(t => `<option value="${esc(t.code)}" ${t.code === i.code_ouvrage ? "selected" : ""}>${esc(t.libelle)} (${esc(t.code)})</option>`).join("")}${ancienType}</select>
       ${champ("libelle", "Libellé de l’ouvrage", i.libelle, 'placeholder="Désignation de l’ouvrage"')}
       <label for="numero_ouvrage">Numéro d’ouvrage</label><div class="numero-ouvrage-choix"><input id="numero_ouvrage" data-champ="numero_ouvrage" value="${esc(E.ficheDraft?.numero_ouvrage ?? actuelNumero)}" maxlength="2" inputmode="numeric" placeholder="01 à 99" title="Proposé automatiquement et modifiable"><button type="button" id="proposer-numero">Proposer</button></div>
       <label for="code-ouvrage-affiche">Code généré</label><div class="code-ouvrage-affiche" id="code-ouvrage-affiche" aria-live="polite"></div>
       <input id="code_ouvrage" type="hidden" value="${esc(i.code_ouvrage)}">
       ${champ("localisation", "Localisation précise", i.localisation, 'placeholder="Adresse, site ou précision géographique"')}
       ${selectListe("automate", "Automate", i.automate, l.automates)}
       <label for="communication-choix">Communication</label><button class="selection-multiple" id="communication-choix" data-valeur="${esc(i.communication || "")}" type="button">${esc(i.communication || "— Choisir les protocoles —")} <span aria-hidden="true">▾</span></button>
       ${champ("revision", "Révision", i.revision, 'maxlength="4" title="Règle documentaire à valider : non modifiée automatiquement"')}
</div>`}
     <p class="aide-champs">Code : lieu (4) + type (2) + numéro (2). Le numéro est proposé automatiquement et peut être modifié ; aucune modification n'est enregistrée sans confirmation.</p>
     <div id="fiche-erreur" class="erreur-form" role="alert"></div>
     <div class="fiche-actions">
       <span id="fiche-etat" class="etat-fiche">${o.creation_en_attente ? "Non enregistré — complétez puis confirmez" : (o.en_conception ? "Brouillon enregistré" : "Fiche enregistrée")}</span>
       <button type="button" id="fiche-annuler">Annuler</button>
       ${o.en_conception ? `<button type="button" id="fiche-brouillon">Enregistrer brouillon</button><button type="button" class="prim" id="fiche-creer">Créer l'ouvrage</button>`
         : `<button type="button" class="prim" id="fiche-modifier" disabled>Enregistrer les modifications</button>`}
     </div>
     ${o.en_conception ? "" : `<div class="repere-live">${texteRepere(i.lieu || "????", i.code_ouvrage || "??", actuelNumero || "--", okLieu, okCode)}</div>`}
   </div>
   ${o.en_conception ? "" : `   <div class="chiffres">
     <div class="chiffre"><b>${o.equipements.length}</b><span>équipements</span></div>
     <div class="chiffre"><b>${o.unites.length}</b><span>unités fonctionnelles</span></div>
     <div class="chiffre"><b>${o.sous_ensembles.length}</b><span>sous-ensembles</span></div>
     <div class="chiffre"><b style="color:${o.equipements.every(e => e.valide) && o.equipements.length ? "var(--ok)" : "var(--al)"}">${o.equipements.filter(e => e.valide).length} / ${o.equipements.length}</b><span>équipements validés${acoder ? ` · ${acoder} à coder` : ""}</span></div>
   </div>
   ${o.equipements.some(e => !e.valide) ? `<div class="bloc"><div class="bloc-tete"><h2>Reste à faire sur les équipements</h2>
     <span class="aide">${["erreur", "incomplet", "configuré"].map(k => `${o.equipements.filter(e => e.etat_param === k).length} ${ETATS_EQ[k][1]}`).join(" · ")}</span></div>
     <table><thead><tr><th>Repère</th><th>Libellé</th><th>État</th><th>Ce qui manque</th></tr></thead><tbody>
     ${o.equipements.filter(e => !e.valide).sort((x, y) => ["erreur", "incomplet", "configuré"].indexOf(x.etat_param) - ["erreur", "incomplet", "configuré"].indexOf(y.etat_param))
       .map(e => `<tr class="cliquable" data-eq="${e.ident}"><td class="mono">${esc(e.pcf)}</td><td>${esc(e.libelle || e.designation)}</td><td>${badgeEtat(e)}</td><td>${esc(e.detail_etat || "")}</td></tr>`).join("")}</tbody></table></div>` : ""}
   <div class="bloc"><div class="bloc-tete"><h2>Répartition par domaine</h2></div>
     ${o.equipements.length ? `<table><thead><tr><th>Domaine</th><th>Équipements</th></tr></thead><tbody>${Object.entries(parDomaine).sort().map(([d, n]) => `<tr><td>${esc(d)}</td><td>${n}</td></tr>`).join("")}</tbody></table>`
       : `<div class="etat-vide"><h3>Aucun équipement pour l'instant</h3><p>Commencez l'inventaire : ajoutez le premier équipement, ou importez la liste de l'ouvrage.</p>
          <div class="boutons-ligne"><button class="prim" type="button" id="vide-ajout-eq">+ Ajouter le premier équipement</button><button type="button" id="vide-structure">Structure / ajouter…</button></div></div>`}
   </div>` }`;
  function recueillir() {
    const donnees = {};
    for (const nom of ["lieu", "libelle", "type_ouvrage", "numero_ouvrage", "automate", "localisation", "revision"]) {
      donnees[nom] = c.querySelector("#" + nom).value;
    }
    donnees.code_ouvrage = c.querySelector("#code_ouvrage").value;
    donnees.type_ouvrage = l.types_ouvrage.find(t => t.code === donnees.code_ouvrage)?.libelle || i.type_ouvrage || "";
    donnees.communication = c.querySelector("#communication-choix").dataset.valeur || "";
    return donnees;
  }
  function miseAJour() {
    E.ficheDraft = {...recueillir(), mode: o.identification.mode, statut: o.identification.statut};
    E.ficheDirty = ["lieu", "code_ouvrage", "numero_ouvrage", "libelle", "automate", "localisation", "communication", "revision"].some(
      cle => String(E.ficheDraft[cle] || "") !== String(o.identification[cle] || ""));
    if (o.creation_en_attente) E.ficheDirty = true;
    c.querySelector("#fiche-etat").textContent = E.ficheDirty ? "Modifications non enregistrées" : (o.en_conception ? "Brouillon enregistré" : "Fiche enregistrée");
    const avertissement = c.querySelector("#fiche-identification-avert");
    if (avertissement) avertissement.style.display = /^[A-Z0-9]{4}$/.test(E.ficheDraft.lieu) && /^[A-Z]{2}$/.test(E.ficheDraft.code_ouvrage) ? "none" : "";
    const bouton = c.querySelector("#fiche-modifier"); if (bouton) bouton.disabled = !E.ficheDirty;
    const code = E.ficheDraft.code_ouvrage || "??", lieu = E.ficheDraft.lieu || "????", numero = E.ficheDraft.numero_ouvrage || "--";
    const numValide = /^(0[1-9]|[1-9][0-9])$/.test(numero);
    const complet = /^[A-Z0-9]{4}$/.test(lieu) && /^[A-Z]{2}$/.test(code) && numValide;
    const codeAffiche = c.querySelector("#code-ouvrage-affiche");
    codeAffiche.textContent = complet ? lieu + code + numero : "Choisissez le lieu, le type et le numéro";
    codeAffiche.classList.toggle("en-attente", !complet);
    const apercuRepere = c.querySelector(".repere-live"); if (apercuRepere) apercuRepere.innerHTML = texteRepere(lieu, code, numero, true, true);
  }
  c.querySelectorAll("[data-champ], [data-choix]").forEach(inp => {
    inp.oninput = miseAJour; inp.onchange = miseAJour;
  });
  async function suggererNumero(force = false) {
    const lieu = c.querySelector("#lieu").value;
    const type = c.querySelector("#code_ouvrage").value;
    const inp = c.querySelector("#numero_ouvrage");
    if (!/^[A-Z0-9]{4}$/.test(lieu) || !/^[A-Z]{2}$/.test(type) || (!force && inp.value)) return;
    const attendu = lieu + type;
    try {
      const r = await api("/api/numero-ouvrage?lieu=" + encodeURIComponent(lieu) + "&type=" + encodeURIComponent(type));
      if (c.querySelector("#lieu").value + c.querySelector("#code_ouvrage").value !== attendu) return;
      if (r.numero && (force || !inp.value)) { inp.value = r.numero; miseAJour(); }
      else if (!r.disponible) toast("Tous les numéros de 01 à 99 sont déjà attribués pour ce lieu et ce type.", true);
    } catch(e) { toast(e.message, true); }
  }
  c.querySelector("#proposer-numero").onclick = () => suggererNumero(true);
  c.querySelector("#lieu").addEventListener("change", () => {
    if (o.en_conception) { c.querySelector("#numero_ouvrage").value = ""; suggererNumero(); }
  });
  c.querySelector("#type_ouvrage").onchange = ev => {
    c.querySelector("#code_ouvrage").value = ev.target.value;
    if (o.en_conception) { c.querySelector("#numero_ouvrage").value = ""; suggererNumero(); }
    miseAJour();
  };
  if (o.en_conception && !actuelNumero && !E.ficheDraft?.numero_ouvrage) suggererNumero();
  miseAJour();
  c.querySelector("#gerer-listes").onclick = () => { E.ficheDraft = recueillir(); modaleListes("lieux"); };
  c.querySelector("#communication-choix").onchange = miseAJour;
  c.querySelector("#communication-choix").onclick = ev => deroulantCommunications(ev.currentTarget, () => { E.ficheDraft = recueillir(); });
  c.querySelector("#fiche-annuler").onclick = async () => {
    if (E.ficheDirty && !window.confirm("Abandonner les modifications non enregistrées ?")) return;
    E.ficheDirty = false; E.ficheDraft = null;
    if (o.en_conception) {
      await api("/api/fermer"); E.ouvrage = null;
      allerAccueil();
    } else await recharger();
  };
  async function enregistrerFiche(action) {
    const donnees = recueillir();
    const changeRepere = donnees.lieu !== o.identification.lieu || donnees.code_ouvrage !== o.identification.code_ouvrage || donnees.numero_ouvrage !== o.identification.numero_ouvrage;
    let confirmer_changement = false;
    if (changeRepere && o.equipements.length) {
      if (!window.confirm("Ce changement modifiera les repères de tous les équipements. Confirmer ?")) return;
      confirmer_changement = true;
    }
    const boutons = [...c.querySelectorAll(".fiche-actions button")];
    boutons.forEach(b => b.disabled = true);
    try {
      await api("/api/fiche-ouvrage", {action, identification: donnees, confirmer_changement});
      E.ficheDraft = null; E.ficheDirty = false;
      E.sel = {nature: "ouvrage", valeur: ""};
      await recharger();
      toast(action === "creer" ? "Ouvrage créé. Vous pouvez construire les UF et les équipements."
        : action === "brouillon" ? "Brouillon enregistré." : "Modifications de la fiche enregistrées.");
    } catch (e) {
      const zone = c.querySelector("#fiche-erreur");
      zone.textContent = e.message;
      // Un code ouvrage déjà attribué n'est pas une panne : aider à retrouver
      // l'ouvrage concerné, sans créer de doublon ni perdre le brouillon sans accord.
      if (action === "creer" && e.message.includes("utilise déjà le code")) {
        try {
          const accueil = await api("/api/accueil");
          const repere = donnees.lieu + donnees.code_ouvrage + donnees.numero_ouvrage;
          const existant = (accueil.ouvrages || []).find(x => x.repere === repere &&
            x.statut !== "Brouillon" && !x.erreur);
          if (existant) {
            zone.appendChild(document.createTextNode(" Ouvrage existant : « " + existant.libelle + " ». "));
            const ouvrir = document.createElement("button");
            ouvrir.type = "button";
            ouvrir.className = "ouvrir-doublon";
            ouvrir.textContent = "Ouvrir cet ouvrage";
            ouvrir.onclick = async () => {
              if (!window.confirm("Abandonner la fiche non enregistrée et ouvrir l’ouvrage existant ?")) return;
              try {
                await api("/api/ouvrir", {chemin: existant.chemin});
                E.ficheDraft = null; E.ficheDirty = false;
                E.sel = {nature: "ouvrage", valeur: ""};
                await recharger();
              } catch (erreur) { toast(erreur.message, true); }
            };
            zone.appendChild(ouvrir);
          }
        } catch (_) { /* Message métier conservé même si le registre est inaccessible. */ }
      }
      boutons.forEach(b => b.disabled = false);
      toast(e.message, true);
    }
  }
  c.querySelectorAll("tr[data-eq]").forEach(tr => tr.onclick = () => { E.sel = {nature: "eq", valeur: tr.dataset.eq}; arbre(); contenu(); });
  if (c.querySelector("#ref-adopter")) c.querySelector("#ref-adopter").onclick = () => adoptionControlee(o.referentiel);
  if (c.querySelector("#ref-annuler-adoption")) c.querySelector("#ref-annuler-adoption").onclick = () => confirmer(
    "Annuler l'adoption du référentiel ?",
    "Le projet reviendra à son état avant la dernière adoption, y compris les modifications effectuées ensuite. L'état courant sera sauvegardé séparément. Disponible dans cette session seulement.",
    "Annuler l'adoption", async () => {
      await agir(api("/api/referentiel/annuler-adoption", {}), "Adoption annulée : le fichier d'origine est restauré.");
      await recharger();
    });
  if (c.querySelector("#fiche-brouillon")) c.querySelector("#fiche-brouillon").onclick = () => enregistrerFiche("brouillon");
  if (c.querySelector("#fiche-creer")) c.querySelector("#fiche-creer").onclick = () => enregistrerFiche("creer");
  if (c.querySelector("#fiche-modifier")) c.querySelector("#fiche-modifier").onclick = () => enregistrerFiche("modifier");
}

// État de paramétrage d'un équipement (calculé par le serveur) : un seul vocabulaire partout.
const ETATS_EQ = {"validé": ["b-ok", "validé"], "configuré": ["b-n", "prêt à valider"],
                  "incomplet": ["b-al", "incomplet"], "erreur": ["b-err", "en erreur"]};
function badgeEtat(e) {
  const [cl, txt] = ETATS_EQ[e.etat_param] || (e.valide ? ETATS_EQ["validé"] : ["b-al", "à valider"]);
  return `<span class="badge ${cl}" title="${esc(e.detail_etat || "")}">${txt}</span>`;
}
function pointEtat(e) {
  const k = e.etat_param || (e.valide ? "validé" : "incomplet");
  return `<span class="pt-etat pt-${k === "validé" ? "ok" : k === "erreur" ? "err" : k === "incomplet" ? "al" : "n"}" title="${esc((ETATS_EQ[k] || [, k])[1] + (e.detail_etat ? " — " + e.detail_etat : ""))}"></span>`;
}
function tableEquipements(eqs) {
  if (!eqs.length) return `<div class="vide-bloc">Aucun équipement dans ce groupe.</div>`;
  return `<table><thead><tr><th>Repère</th><th>Type</th><th>Libellé</th><th>Modèle</th><th>E/S</th><th>À décider</th><th>État</th></tr></thead><tbody>
    ${eqs.map(e => `<tr class="cliquable" data-eq="${e.ident}"><td class="mono">${esc(e.pcf)}</td><td><span class="tag">${esc(e.type.replace(/--$/, ""))}</span> ${esc(e.designation)}</td>
      <td>${esc(e.libelle)}</td><td>${esc(e.modele) || '<span class="vide">aucun</span>'}</td><td>${e.nb_es}</td>
      <td>${e.a_decider ? `<span class="badge b-al">${e.a_decider}</span>` : '<span class="vide">—</span>'}</td><td>${badgeEtat(e)}</td></tr>`).join("")}</tbody></table>`;
}
function detailGroupe() {
  const o = E.ouvrage, s = E.sel, c = $("#contenu");
  const u = o.unites.find(x => x.code === s.valeur), codes = new Set(o.unites.map(x => x.code));
  const eqs = s.nature === "uf" ? o.equipements.filter(e => e.uf === s.valeur) : o.equipements.filter(e => !codes.has(e.uf));
  c.innerHTML = `<div class="fil">${esc(o.prefixe)} › ${s.nature === "uf" ? esc(s.valeur) : "équipements hors UF"}</div>
    <div class="bloc"><div class="titre"><div><h1>${s.nature === "uf" ? esc(u.code + " — " + (u.libelle || "sans libellé")) : esc(o.libelle_communs)}</h1>
      <div class="sous">${s.nature === "uf" ? `Unité fonctionnelle · sous-ensemble proposé aux nouveaux équipements : <b>${esc(u.se || "aucun")}</b>` : "Équipements rattachés à aucune UF (armoire, automate…)"}</div></div>
      <div class="actions">${s.nature === "uf" ? `<button id="g-mod">Modifier l'UF…</button><button class="danger" id="g-sup">Supprimer l'UF</button>` : `<button id="g-ren">Renommer…</button>`}
      ${eqs.some(e => !e.valide) ? `<button id="g-val">Valider les ${eqs.filter(e => !e.valide).length} équipement(s)</button>` : ""}
      <button class="prim" id="g-eq">+ Équipement</button></div></div></div>
    <div class="bloc"><div class="bloc-tete"><h2>Équipements</h2><span class="aide">${eqs.length}</span></div>${tableEquipements(eqs)}</div>`;
  c.querySelectorAll("tr[data-eq]").forEach(tr => tr.onclick = () => { E.sel = {nature: "eq", valeur: tr.dataset.eq}; arbre(); contenu(); });
  $("#g-eq").onclick = () => modaleEquipement(null, s.nature === "uf" ? s.valeur : "");
  if ($("#g-val")) $("#g-val").onclick = () => { const ids = eqs.filter(e => !e.valide).map(e => e.ident);
    confirmer(`Valider ${ids.length} équipement(s) ?`, "Vous attestez qu'ils existent sur le terrain et que leurs lignes sont justes.", "Valider",
      async () => { await agir(api("/api/equipement/valider", {idents: ids, valide: true}), `${ids.length} équipement(s) validé(s).`); recharger(); }); };
  if (s.nature === "uf") {
    $("#g-mod").onclick = () => modaleUF(u);
    $("#g-sup").onclick = () => confirmer(`Supprimer l'UF ${u.code} ?`, `Ses ${eqs.length} équipement(s) sont conservés, hors UF.`, "Supprimer",
      async () => { await agir(api("/api/uf", {action: "supprimer", code: u.code}), "UF supprimée."); E.sel = {nature: "ouvrage", valeur: ""}; recharger(); });
  } else {
    $("#g-ren").onclick = () => modaleSaisie("Renommer le groupe", "Nom du groupe des équipements hors UF", o.libelle_communs,
      async v => { await agir(api("/api/uf", {action: "renommer_communs", libelle: v})); recharger(); });
  }
}
function detailEquipement(e) {
  const c = $("#contenu"), o = E.ouvrage;
  const roles = {}; e.informations.forEach(i => roles[i.role] = (roles[i.role] || 0) + 1);
  const liste = Object.keys(roles).sort((a, b) => ((ROLES_ORDRE.indexOf(a) + 99) % 99) - ((ROLES_ORDRE.indexOf(b) + 99) % 99));
  const vis = e.informations.filter(i => E.filtreRole === "Toutes" || i.role === E.filtreRole);
  const uf = o.unites.find(u => u.code === e.uf);
  const se = o.sous_ensembles.find(x => x.code === e.se) || {};
  const badgeOrigine = x => x === "ajoutée" ? '<span class="badge b-ok">ajoutée</span>' : x === "modifiée" ? '<span class="badge b-al">modifiée</span>' : '<span class="badge b-n">modèle</span>';
  c.innerHTML = `<div class="fil">${esc(o.prefixe)} › ${esc(uf ? uf.code : (o.unites.length ? "hors UF" : "équipements"))} › ${esc(e.pcf)}</div>
   <div class="bloc"><div class="titre"><div><h1 class="mono">${esc(e.pcf)} ${badgeEtat(e)}</h1><div class="sous">${esc(e.libelle || "libellé à renseigner")}</div></div>
     <div class="actions"><button id="e-dep">Ranger dans une UF…</button><button id="e-mod">Modifier…</button><button class="danger" id="e-sup">Supprimer</button>
     ${e.valide ? '<button id="e-val" data-v="0">Repasser à contrôler</button>' : '<button class="prim" id="e-val" data-v="1">Valider le paramétrage</button>'}</div></div>
     <div class="props">
       <div><small>Type</small><b>${esc(e.type.replace(/--$/, ""))}</b> — ${esc(e.designation)}</div>
       <div><small>Modèle</small><b>${esc(e.modele) || "aucun"}</b></div>
       <div><small>Sous-ensemble</small><b>${esc(e.se)}</b>${se.libelle ? " — " + esc(se.libelle) : ""}</div>
       <div><small>Domaine</small><b>${esc(e.domaine || "non classé")}</b> · ${e.nb_es} E/S physique(s)</div>
     </div></div>
   ${e.alerte_modele ? `<div class="avert"><b>Référentiel à contrôler :</b> ${esc(e.alerte_modele)} <button class="lien" data-nav="#/referentiel">Consulter le référentiel</button></div>` : ""}
   ${!e.modele_a_jour ? `<div class="avert">Le modèle « ${esc(e.modele)} » a changé dans le référentiel depuis l'ajout de cet équipement. <button class="lien" id="e-act">Reprendre la nouvelle version</button></div>` : ""}
   ${(e.erreurs || []).length || (e.alertes || []).length ? `<div class="bloc controles-eq"><div class="bloc-tete"><h2>Contrôles de cet équipement</h2>
     <span class="aide">${(e.erreurs || []).length} erreur(s) · ${(e.alertes || []).length} alerte(s)</span></div>
     <ul class="liste-controles">${(e.erreurs || []).map(m => `<li class="c-err">${esc(m)}</li>`).join("")}${(e.alertes || []).map(m => `<li class="c-al">${esc(m)}</li>`).join("")}</ul></div>` : ""}
   ${!e.valide && e.etat_param === "incomplet" ? `<div class="avert"><b>Avant validation :</b> ${esc(e.detail_etat)}</div>` : ""}`;
  const blocLignes = `   <div class="bloc"><div class="bloc-tete"><h2>Lignes du modèle de supervision</h2><span class="aide">libellés et mnémoniques du modèle choisi · ${e.informations.length} ligne(s)${e.adapte ? " · adaptées pour cet équipement" : ""}</span>
     <div class="droite">${e.adapte ? '<button id="l-ret">Revenir au modèle</button>' : ""}<button class="danger" id="l-sup" disabled>Supprimer la sélection</button><button class="prim" id="l-add">+ Ajouter une ligne</button></div></div>
   ${e.informations.length ? `<div class="compteurs"><span class="chip ${E.filtreRole === "Toutes" ? "on" : ""}" data-r="Toutes">Toutes<b>${e.informations.length}</b></span>
     ${liste.map(r => `<span class="chip ${E.filtreRole === r ? "on" : ""}" data-r="${r}">${r}<b>${roles[r]}</b></span>`).join("")}</div>
   <table><thead><tr><th style="width:28px"><input type="checkbox" id="l-tout"></th><th>Rôle</th><th>Libellé</th><th>Mnémonique</th><th>Format</th><th>Unité</th><th>Origine</th><th style="width:90px"></th></tr></thead><tbody>
   ${vis.map(i => `<tr><td><input type="checkbox" class="l-coche" value="${i.id}"></td><td><span class="role ${classeRole(i.role)}">${esc(i.role)}</span></td>
     <td>${esc(i.libelle)}</td><td class="mono">${esc(i.mnemonique)}</td><td>${esc(i.format)}</td><td>${esc(i.unite)}</td><td>${badgeOrigine(i.origine)}</td>
     <td style="text-align:right"><button class="lien" data-lmod="${i.id}">Modifier</button></td></tr>`).join("")}</tbody></table>`
   : `<div class="vide-bloc">${e.modele ? "Ce modèle n'a pas encore de ligne." : "Aucun modèle choisi pour cet équipement."}<br>
      Ajoutez les lignes ici (« + Ajouter une ligne ») ou choisissez un modèle (« Modifier… »). Les modèles se créent dans « Référentiel ».</div>`}</div>`;
  // Configuration des E/S physiques : partie intégrante de la fiche du modèle d'équipement.
  const choixES = e.signaux_es || [], extrasES = e.es_personnalisees || [], optionsES = e.options_es || [], portees = e.es_portees || [];
  const pointsAnal = choixES.filter(x => x.retenu && ['EA','SA'].includes(x.point))
    .concat(extrasES.filter(x => ['EA','SA'].includes(x.point))).concat(portees.filter(x => ['EA','SA'].includes(x.point)));
  c.insertAdjacentHTML('beforeend', `<div class="bloc" id="configuration-es">
    <div class="bloc-tete"><h2>Paramétrage des entrées / sorties de l'équipement</h2>
      <div class="droite"><button id="e-add-es">+ E/S personnalisée</button></div></div>
    <p class="aide" style="padding:0 14px">Le modèle propose les E/S physiques possibles. Les contacts de défaut, de sens et les impulsions ne sont retenus que si le débitmètre ou l'équipement les possède réellement.
      Choisissez les options, puis renseignez les échelles analogiques. La validation ci-dessus confirme ce paramétrage, pas les adresses physiques.</p>
    ${optionsES.length ? `<div style="padding:12px 14px"><b>Options de l'équipement</b><div class="choix-protocoles" style="margin-top:8px">${optionsES.map(o => `<label><input type="checkbox" class="e-option" data-option="${esc(o.nom)}" ${o.active ? 'checked' : ''}> ${esc(o.nom)}</label>`).join('')}</div></div>` : ''}
    ${choixES.length || portees.length ? `<table><thead><tr><th>Retenue</th><th>Point</th><th>Information physique proposée</th><th>Présence</th><th>Configuration</th></tr></thead><tbody>
     ${choixES.map(x => `<tr><td><input type="checkbox" class="e-es-choix" data-cle="${esc(x.cle)}" ${x.retenu ? 'checked' : ''} ${x.presence === 'Obligatoire' || !x.disponible ? 'disabled' : ''}></td>
     <td><span class="tag">${esc(x.point)}</span></td><td>${esc(x.information)}</td><td>${esc(x.presence === 'Option' ? x.option : x.presence)}</td>
     <td>${['EA','SA'].includes(x.point) && x.retenu ? `<button class="lien e-analogique" data-cle="${esc(x.cle)}">${x.analogique ? 'Modifier l’échelle' : 'Définir l’échelle 4–20 mA'}</button>` : (x.retenu && x.cle === 'ES_IMP' ? `<button class="lien e-impulsion" data-cle="${esc(x.cle)}">${x.impulsion ? 'Modifier les impulsions' : 'Paramétrer les impulsions'}</button>` : (x.retenu ? '<span class="aide">Signal retenu</span>' : '—'))}</td></tr>`).join('')}
     ${portees.map(x => `<tr><td><input type="checkbox" checked disabled title="Contact câblé porté par l'information ${esc(x.cle)}"></td><td><span class="tag">${esc(x.point)}</span></td>
       <td>${esc(x.information)} <span class="aide">· câblée, portée par <span class="mono">${esc(x.cle)}</span></span></td><td>Modèle</td>
       <td>${['EA','SA'].includes(x.point) ? `<button class="lien e-analogique" data-cle="${esc(x.cle)}">${x.analogique ? 'Modifier l’échelle' : 'Définir l’échelle 4–20 mA'}</button>` : '<span class="aide">Signal retenu</span>'}</td></tr>`).join('')}</tbody></table>`
      : '<div class="avert">Aucune E/S prédéfinie pour ce type dans le catalogue : créez une E/S personnalisée si nécessaire.</div>'}
    ${extrasES.length ? `<div style="padding:12px 14px"><b>E/S personnalisées</b><table><tbody>${extrasES.map(x => `<tr><td><span class="tag">${esc(x.point)}</span></td><td>${esc(x.nom)}</td><td>${['EA','SA'].includes(x.point) ? `<button class="lien e-analogique" data-cle="${esc(x.cle)}">${x.analogique ? 'Modifier l’échelle' : 'Définir l’échelle'}</button>` : ''}</td><td><button class="lien e-sup-es" data-cle="${esc(x.cle)}">Retirer</button></td></tr>`).join('')}</tbody></table></div>` : ''}
    ${pointsAnal.length ? `<div class="avert">${pointsAnal.filter(x => !x.analogique).length} échelle(s) analogique(s) restent à configurer avant de valider cet équipement.</div>` : ''}
    <div class="bloc-tete"><span class="aide">E/S physiques sélectionnées : ${choixES.filter(x => x.retenu).length + extrasES.length + portees.length}. Les TS, TM, TC et CP du modèle restent des informations fonctionnelles distinctes ; aucune ST pour initialiser le compteur d’un débitmètre.</span>
      <div class="droite"><button class="prim" id="e-fin-config" ${e.valide ? 'disabled' : ''}>${e.valide ? 'Paramétrage validé' : 'Valider le paramétrage'}</button></div></div>
  </div>`);
  c.insertAdjacentHTML('beforeend', blocFonctionnelles(e) + blocLignes);
  brancherFonctionnelles(e, c);
  c.querySelectorAll('.e-option').forEach(x => x.onchange = async () => {
    try { await api('/api/equipement/configurer', {action:'option',ident_eq:e.ident,option:x.dataset.option,active:x.checked}); await recharger(); }
    catch(err){toast(err.message,true); x.checked=!x.checked;}
  });
  c.querySelectorAll('.e-es-choix').forEach(x => x.onchange = async () => {
    try { await api('/api/equipement/configurer', {action:'selection_es',ident_eq:e.ident,cle:x.dataset.cle,retenu:x.checked}); await recharger(); }
    catch(err){toast(err.message,true); x.checked=!x.checked;}
  });
  c.querySelectorAll('.e-analogique').forEach(x => x.onclick = () => {
    const pt = [...choixES, ...extrasES, ...portees].find(z => z.cle === x.dataset.cle);
    modaleEchelleAnalogique(e, pt);
  });
  c.querySelectorAll('.e-impulsion').forEach(x => x.onclick = () => {
    const pt = choixES.find(z => z.cle === x.dataset.cle);
    modaleComptageImpulsions(e, pt);
  });
  c.querySelectorAll('.e-sup-es').forEach(x => x.onclick = () => confirmer('Retirer cette E/S personnalisée ?', 'Ses paramètres et son adressage seront supprimés.', 'Retirer', async () => {
    await agir(api('/api/equipement/configurer',{action:'retirer_es',ident_eq:e.ident,cle:x.dataset.cle}), 'E/S retirée.'); recharger();
  }));
  c.querySelector('#e-add-es').onclick = () => modaleESPersonnalisee(e);
  c.querySelector('#e-fin-config').onclick = async () => {
    try { await api('/api/equipement/valider',{idents:[e.ident],valide:true});
      toast('Paramétrage de l’équipement validé. Il restera à adresser et valider les voies physiques.'); await recharger(); }
    catch(err){toast(err.message,true);}
  };
  c.querySelectorAll(".chip").forEach(ch => ch.onclick = () => { E.filtreRole = ch.dataset.r; detailEquipement(e); });
  const recharge = async () => { await recharger(); };
  $("#e-val").onclick = async () => { const v = $("#e-val").dataset.v === "1";
    await agir(api("/api/equipement/valider", {idents: [e.ident], valide: v}), v ? "Équipement validé." : "Équipement repassé à valider."); recharge(); };
  $("#e-mod").onclick = () => modaleEquipement(eqParIdent(e.ident));
  $("#e-sup").onclick = () => confirmer(`Supprimer ${e.pcf} ?`, "L'équipement est retiré de l'ouvrage avec ses lignes.", "Supprimer",
    async () => { await agir(api("/api/equipement/supprimer", {idents: [e.ident]}), "Équipement supprimé."); E.sel = {nature: "ouvrage", valeur: ""}; recharger(); });
  $("#e-dep").onclick = () => modaleChoix("Ranger dans une UF", `UF de ${e.pcf}`,
    [["", "— aucune (hors UF) —"]].concat(o.unites.map(u => [u.code, u.code + " — " + u.libelle])), e.uf,
    async v => { await agir(api("/api/equipement/deplacer", {idents: [e.ident], uf: v})); recharger(); });
  const coches = () => [...c.querySelectorAll(".l-coche:checked")].map(x => x.value);
  const majSup = () => { const n = coches().length; $("#l-sup").disabled = !n; $("#l-sup").textContent = n ? `Supprimer la sélection (${n})` : "Supprimer la sélection"; };
  c.querySelectorAll(".l-coche").forEach(x => x.onchange = majSup);
  if ($("#l-tout")) $("#l-tout").onchange = ev => { c.querySelectorAll(".l-coche").forEach(x => x.checked = ev.target.checked); majSup(); };
  $("#l-sup").onclick = () => { const ids = coches(); confirmer(`Supprimer ${ids.length} ligne(s) ?`, "Seul cet équipement est concerné : le modèle du référentiel n'est pas modifié.", "Supprimer",
    async () => { await agir(api("/api/equipement/ligne", {action: "supprimer", ident_eq: e.ident, ids}), "Ligne(s) supprimée(s)."); recharge(); }); };
  $("#l-add").onclick = () => modaleLigne(e.roles, e.formats, null, o.prefixe ? e.pcf.slice(4) : "", async champs => {
    await api("/api/equipement/ligne", {action: "ajouter", ident_eq: e.ident, champs}); toast("Ligne ajoutée."); recharge(); });
  c.querySelectorAll("[data-lmod]").forEach(b => b.onclick = () => {
    const l = e.informations.find(x => x.id === b.dataset.lmod);
    modaleLigne(e.roles, e.formats, l, e.pcf.slice(4), async champs => {
      await api("/api/equipement/ligne", {action: "modifier", ident_eq: e.ident, id: l.id, champs}); toast("Ligne modifiée."); recharge(); });
  });
  if ($("#l-ret")) $("#l-ret").onclick = () => confirmer("Revenir au modèle ?", "Les lignes ajoutées, modifiées ou supprimées pour cet équipement sont annulées.", "Revenir au modèle",
    async () => { await agir(api("/api/equipement/ligne", {action: "retablir", ident_eq: e.ident}), "Lignes du modèle rétablies."); recharge(); });
  if ($("#e-act")) $("#e-act").onclick = () => confirmer("Actualiser le modèle dans cet ouvrage ?",
    "Tous les équipements qui partagent ce modèle dans cet ouvrage seront remis à valider. Les repères et adresses restent conservés ; aucune migration automatique des anciens projets.",
    "Actualiser", async () => { await agir(api("/api/equipement/ligne", {action: "actualiser", ident_eq: e.ident}), "Modèle actualisé : équipements à revalider."); recharge(); });
}
/* Informations fonctionnelles (TS, TM, CP, TC, TR, RTR) : ce que l'automate calcule ou reçoit, distinct
   des E/S câblées. Une information proposée par une règle se retient ou s'écarte avec un motif : rien
   n'est oublié en silence (ex. discordance d'une vanne à deux fins de course). */
const ORDRE_ETATS_F = {"proposée": 0, "retenue": 1, "écartée": 2, "non retenue": 3};
function blocFonctionnelles(e) {
  const f = (e.fonctionnelles || []).slice().sort((a, b) => ORDRE_ETATS_F[a.etat] - ORDRE_ETATS_F[b.etat]);
  const nb = k => f.filter(x => x.etat === k).length;
  const visibles = f.filter(x => x.etat !== "non retenue"), autres = f.filter(x => x.etat === "non retenue");
  const etat = x => x.etat === "proposée" ? '<span class="badge b-al">à décider</span>'
    : x.etat === "retenue" ? '<span class="badge b-ok">retenue</span>' : x.etat === "écartée" ? '<span class="badge b-n">écartée</span>'
    : '<span class="badge b-n">non retenue</span>';
  const justif = x => [x.sources.length ? `<div><small>Si</small> ${x.sources.map(s => `<span class="mono">${esc(s)}</span>`).join(" + ")}</div>` : "",
    x.logique ? `<div class="logique">${esc(x.logique)}</div>` : "", x.motif ? `<div><small>Motif</small> ${esc(x.motif)}</div>` : ""].join("");
  const action = x => x.etat === "proposée" ? `<button class="prim f-ret" data-cle="${esc(x.cle)}">Retenir</button> <button class="f-eca" data-cle="${esc(x.cle)}">Écarter…</button>`
    : x.decidable && x.etat === "retenue" ? `<button class="lien f-eca" data-cle="${esc(x.cle)}">Écarter…</button>`
    : x.decidable && x.etat === "écartée" ? `<button class="lien f-rou" data-cle="${esc(x.cle)}">Revoir</button>` : "";
  const ligne = x => `<tr class="${x.etat === "proposée" ? "a-decider" : ""}"><td>${etat(x)}</td>
    <td><span class="role">${esc(x.famille)}</span> <span class="mono">${esc(x.code)}</span></td><td>${esc(x.information)}${x.alarme ? ' <span class="tag">alarme</span>' : ""}</td>
    <td>${esc(x.origine)}</td><td class="justif">${justif(x)}</td><td style="text-align:right;white-space:nowrap">${action(x)}</td></tr>`;
  return `<div class="bloc" id="infos-fonctionnelles"><div class="bloc-tete"><h2>Informations fonctionnelles</h2>
    <span class="aide">${nb("retenue")} retenue(s) · ${nb("proposée")} à décider · ${nb("écartée")} écartée(s)</span>
    <div class="droite">${nb("proposée") ? `<button id="f-tout">Retenir les ${nb("proposée")} proposée(s)</button>` : ""}</div></div>
    <p class="aide" style="padding:0 14px">Informations calculées par l'automate ou échangées avec la supervision (TS, TM, CP, TC, TR, RTR), déduites des E/S retenues par les règles du référentiel.
      Une information <b>proposée</b> demande une logique automate : retenez-la, ou écartez-la en écrivant pourquoi. La validation de l'équipement attend ces décisions.</p>
    ${visibles.length ? `<table class="t-fonctionnelles"><thead><tr><th style="width:96px">État</th><th style="width:120px">Information</th><th>Libellé</th><th>Provenance</th><th>Justification</th><th></th></tr></thead>
      <tbody>${visibles.map(ligne).join("")}</tbody></table>` : '<div class="vide-bloc">Aucune information fonctionnelle retenue pour ce paramétrage.</div>'}
    ${autres.length ? `<details class="non-retenues"><summary>${autres.length} information(s) prévue(s) par le modèle mais non retenue(s) (option non choisie ou conditions non réunies)</summary>
      <table class="t-fonctionnelles"><tbody>${autres.map(ligne).join("")}</tbody></table></details>` : ""}</div>`;
}
function brancherFonctionnelles(e, c) {
  const decider = async (corps, msg) => { try { await api("/api/equipement/proposition", {ident_eq: e.ident, ...corps}); toast(msg); await recharger(); } catch (err) { toast(err.message, true); } };
  c.querySelectorAll(".f-ret").forEach(b => b.onclick = () => decider({cle: b.dataset.cle, decision: "retenir"}, `${b.dataset.cle} retenue : elle sera générée.`));
  c.querySelectorAll(".f-rou").forEach(b => b.onclick = () => decider({cle: b.dataset.cle, decision: "reouvrir"}, `${b.dataset.cle} de nouveau à décider.`));
  c.querySelectorAll(".f-eca").forEach(b => b.onclick = () => modaleSaisie(`Écarter ${b.dataset.cle}`, "Motif (obligatoire, ex. « traité par le poste local »)", "",
    async v => { await api("/api/equipement/proposition", {ident_eq: e.ident, cle: b.dataset.cle, decision: "ecarter", motif: v}); toast(`${b.dataset.cle} écartée.`); await recharger(); }));
  c.querySelectorAll(".t-fonctionnelles .logique").forEach(x => { x.title = "Cliquer pour lire toute la logique"; x.onclick = () => x.classList.toggle("ouverte"); });
  const tout = c.querySelector("#f-tout");
  if (tout) tout.onclick = () => decider({decision: "retenir"}, "Informations proposées retenues.");
}
function modaleEchelleAnalogique(eq, p) {
  const a = p.analogique || {}, m = ouvrirModale(`<div class="boite-tete"><h2>Échelle analogique — ${esc(p.information || p.nom || p.cle)}</h2>
    <p>Deux points de correspondance courant/mesure physique. Aucun décompte brut n'est supposé : il dépend du module et de sa configuration.</p></div>
    <div class="boite-corps"><div class="champs">
      <label>Courant du point bas (mA)</label><input id="an-smin" inputmode="decimal" value="${esc(a.signal_min ?? 4)}">
      <label>Valeur physique à ce point</label><input id="an-pmin" inputmode="decimal" value="${esc(a.phys_min ?? '')}" placeholder="ex. 0">
      <label>Courant du point haut (mA)</label><input id="an-smax" inputmode="decimal" value="${esc(a.signal_max ?? 20)}">
      <label>Valeur physique à ce point</label><input id="an-pmax" inputmode="decimal" value="${esc(a.phys_max ?? '')}" placeholder="ex. 500">
      <label>Unité physique</label><input id="an-uni" value="${esc(a.unite ?? '')}" placeholder="ex. m³/h">
      <label>Valeur brute automate au point bas</label><input id="an-bmin" inputmode="decimal" value="${esc(a.brut_min ?? '')}" placeholder="facultatif — dépend du module">
      <label>Valeur brute automate au point haut</label><input id="an-bmax" inputmode="decimal" value="${esc(a.brut_max ?? '')}" placeholder="facultatif — dépend du module">
    </div><div class="aide">Adresse physique, rack et voie : à l'étape « Liste des E/S », après validation du paramétrage.</div><div class="erreur-form" id="an-err"></div></div>
    <div class="boite-pied"><button data-fermer>Annuler</button><button id="an-save" class="prim">Enregistrer l’échelle</button></div>`);
  const q = x => m.querySelector(x);
  q('#an-save').onclick = async () => {
    const params = {signal_min:q('#an-smin').value,signal_max:q('#an-smax').value,
      phys_min:q('#an-pmin').value,phys_max:q('#an-pmax').value,unite:q('#an-uni').value,
      brut_min:q('#an-bmin').value,brut_max:q('#an-bmax').value};
    try { await api('/api/equipement/configurer',{action:'analogique',ident_eq:eq.ident,cle:p.cle,params});
      fermerModale(); toast('Échelle enregistrée. Revalidez le paramétrage de l’équipement.'); recharger(); }
    catch(err){q('#an-err').textContent=err.message;}
  };
}
function modaleComptageImpulsions(eq, p) {
  const a = p.impulsion || {}, m = ouvrirModale(`<div class="boite-tete"><h2>Paramétrage des impulsions — ${esc(eq.pcf)}</h2>
    <p>Valeurs constructeur / câblage à confirmer. Ne pas inventer le poids d'une impulsion.</p></div>
    <div class="boite-corps"><div class="champs">
      <label>Volume par impulsion</label><input id="im-poids" inputmode="decimal" value="${esc(a.poids ?? '')}" placeholder="ex. 0,1">
      <label>Unité de volume</label><input id="im-uni" value="${esc(a.unite ?? 'm³')}" placeholder="m³">
      <label>Front de comptage</label><select id="im-front"><option value="">— À définir —</option>
        <option value="Montant" ${a.front === 'Montant' ? 'selected' : ''}>Montant</option>
        <option value="Descendant" ${a.front === 'Descendant' ? 'selected' : ''}>Descendant</option></select>
    </div><div class="erreur-form" id="im-err"></div></div>
    <div class="boite-pied"><button data-fermer>Annuler</button><button class="prim" id="im-save">Enregistrer</button></div>`);
  m.querySelector('#im-save').onclick = async () => {
    const q = x => m.querySelector(x);
    const poids = q('#im-poids').value.replace(',', '.');
    try { await api('/api/equipement/configurer', {action:'impulsion',ident_eq:eq.ident,cle:p.cle,
      params:{poids,unite:q('#im-uni').value,front:q('#im-front').value}});
      fermerModale(); toast('Comptage enregistré. Revalidez l’équipement.'); recharger();
    } catch(err){q('#im-err').textContent=err.message;}
  };
}
function modaleESPersonnalisee(eq) {
  const m = ouvrirModale(`<div class="boite-tete"><h2>Ajouter une E/S à ${esc(eq.pcf)}</h2><p>Ajoutez uniquement un signal physique réellement prévu sur l'équipement.</p></div>
  <div class="boite-corps"><div class="champs"><label>Nature de l'E/S</label><select id="pe-point"><option>ET</option><option>ST</option><option>EA</option><option>SA</option></select>
  <label>Code</label><input id="pe-code" placeholder="ex. IMP_BIS"><label>Désignation</label><input id="pe-des" placeholder="ex. Sortie impulsion de comptage"></div><div class="erreur-form" id="pe-err"></div></div>
  <div class="boite-pied"><button data-fermer>Annuler</button><button class="prim" id="pe-add">Ajouter l'E/S</button></div>`);
  m.querySelector('#pe-add').onclick=async()=>{try{
    await api('/api/equipement/configurer',{action:'ajouter_es',ident_eq:eq.ident,
      point:m.querySelector('#pe-point').value,code:m.querySelector('#pe-code').value.toUpperCase().trim(),designation:m.querySelector('#pe-des').value});
    fermerModale();toast('E/S ajoutée. Pensez à valider le paramétrage.');recharger();
  }catch(err){m.querySelector('#pe-err').textContent=err.message;}};
}
function modaleLigne(roles, formats, l, repereNom, action) {
  const m = ouvrirModale(`<div class="boite-tete"><h2>${l ? "Modifier la ligne" : "Nouvelle ligne"}</h2>
    <p>Le mnémonique est calculé : rôle + repère + suffixe.</p></div>
    <div class="boite-corps"><div class="champs">
      <label>Rôle</label><select id="l-role">${roles.map(r => `<option ${l && l.role === r ? "selected" : ""}>${r}</option>`).join("")}</select>
      <label>Libellé</label><input id="l-lib" value="${esc(l ? l.libelle : "")}" placeholder="ex. Vanne ouverte">
      <label>Suffixe</label><input id="l-suf" value="${esc(l ? l.suffixe : "")}" placeholder="ex. OUV" style="text-transform:uppercase">
      <label>Format</label><select id="l-fmt">${formats.map(f => `<option ${l && l.format === f ? "selected" : ""}>${f}</option>`).join("")}</select>
      <label>Unité</label><input id="l-uni" value="${esc(l ? l.unite : "")}" placeholder="m, bar, m3/h…">
      <label>Commentaire</label><input id="l-com" value="${esc(l ? l.commentaire : "")}">
      <label>Mnémonique</label><div class="mono" id="l-mn" style="font-weight:600"></div>
    </div><div class="erreur-form" id="m-err"></div></div>
    <div class="boite-pied"><button data-fermer>Annuler</button><button class="prim" id="m-ok">${l ? "Enregistrer" : "Ajouter la ligne"}</button></div>`);
  const q = x => m.querySelector(x);
  const maj = () => q("#l-mn").textContent = repereNom ? `${q("#l-role").value}_${repereNom}_${q("#l-suf").value.toUpperCase() || "…"}` : `${q("#l-role").value}_<repère>_${q("#l-suf").value.toUpperCase() || "…"}`;
  q("#l-role").onchange = maj; q("#l-suf").oninput = maj; maj();
  q("#m-ok").onclick = async () => {
    const champs = {role: q("#l-role").value, libelle: q("#l-lib").value, suffixe: q("#l-suf").value.toUpperCase(),
                    format: q("#l-fmt").value, unite: q("#l-uni").value, commentaire: q("#l-com").value};
    try { await action(champs); fermerModale(); } catch (err) { q("#m-err").textContent = err.message; }
  };
}
/* ------------------------------------------------------------------ modales */
function ouvrirModale(html, large) {
  const m = $("#modale");
  E.apresFermeture = null;                         // chaque fenêtre déclare elle-même ce qui suit sa fermeture
  m.innerHTML = `<div class="boite${large ? " large" : ""}">${html}</div>`;
  m.hidden = false;
  m.onclick = ev => { if (ev.target === m) fermerModale(); };
  const premier = m.querySelector("input,select");
  if (premier) premier.focus();
  m.querySelectorAll("[data-fermer]").forEach(b => b.onclick = fermerModale);
  return m;
}
function fermerModale() {
  const ouverte = !$("#modale").hidden;
  $("#modale").hidden = true; $("#modale").innerHTML = "";
  const suite = E.apresFermeture; E.apresFermeture = null;
  if (ouverte && suite) suite();                 // ex. rafraîchir la liste des E/S après les cartes, quelle que soit la façon de fermer
}
document.addEventListener("keydown", ev => { if (ev.key === "Escape" && !$("#modale").hidden) fermerModale(); });
// Adoption contrôlée du référentiel : type par type, renommages affichés et décochés par défaut.
function adoptionControlee(ref) {
  const types = ref.adoption || [];
  const paire = (label, noms) => noms[0] !== noms[1] ? `<div><b>${label}</b> <code>${esc(noms[0] || "—")}</code> → <code>${esc(noms[1] || "—")}</code></div>` : "";
  const equipement = (e, type) => `<details class="adoption-equipement" data-adoption-eq="${esc(e.ident)}" open>
    <summary><b>${esc(e.repere)}</b>${e.modele ? ` · ${esc(e.modele)}` : ""}</summary>
    ${e.modele_fige ? `<p class="aide">Modèle figé conservé : cette adoption du catalogue ne met pas ses signaux à jour.</p>` : ""}
    ${e.ajoutees.length ? `<p>Ajouts au catalogue : <code>${esc(e.ajoutees.join(", "))}</code></p>` : ""}
    ${e.retirees.length ? `<p>Retraits du catalogue : <code>${esc(e.retirees.join(", "))}</code></p>` : ""}
    ${e.modifiees.length ? `<p class="aide">Définitions modifiées : <code>${esc(e.modifiees.join(", "))}</code></p>` : ""}
    ${e.renommages.map(r => `<label class="adoption-renommage"><input type="checkbox" data-confirmation="${esc(r.id)}" data-confirmation-type="${esc(type.type)}" ${type.adoptable ? "" : "disabled"}>
      <span>${paire("Physique", r.physique)}${paire("Fonctionnel", r.fonctionnel)}
      <span class="aide">Adresse d'échange : <code>${esc(r.adresse || "non renseignée")}</code> · voie physique : <code>${esc(r.adresse_es || "non renseignée")}</code> — conservées</span></span></label>`).join("") || `<p class="aide">Aucun renommage pour cet équipement.</p>`}</details>`;
  const ligne = x => {
    const bloc = x.bloquants.map(b => `<li class="erreur-form">${esc(b)}</li>`).join("");
    return `<fieldset class="adoption-type"><legend><label><input type="checkbox" data-type="${esc(x.type)}" ${x.adoptable ? "" : "disabled"}>
      ${esc(x.type)} (${x.equipements.length} équipement(s))</label></legend>
      <p>Catalogue : ${x.ajoutees.length} ajout(s), ${x.retirees.length} retrait(s), ${x.modifiees.length} définition(s) modifiée(s), ${x.regles.length} règle(s) modifiée(s).
      ${(x.details_equipements || []).reduce((n, e) => n + e.renommages.length, 0)} renommage(s) à confirmer par équipement.</p>
      ${x.regles.length ? `<p class="aide">Règles : ${esc(x.regles.join(", "))}</p>` : ""}
      ${(x.details_equipements || []).map(e => equipement(e, x)).join("")}
      ${bloc ? `<ul>${bloc}</ul>` : ""}</fieldset>`;
  };
  const m = ouvrirModale(`<div class="boite-tete"><h2>Adopter le référentiel actuel</h2>
    <p>Choisissez les types, puis confirmez chaque renommage par équipement. Les adresses et correspondances restent conservées ; les équipements adoptés seront à revalider.</p>
    <p>Une sauvegarde du fichier précède l'adoption. Son téléchargement et « Annuler l'adoption » seront accessibles sur la fiche de l'ouvrage, dans cette session.</p></div>
    <div class="boite-corps">${types.map(ligne).join("") || "<p>Aucun écart.</p>"}
    <div class="erreur-form" id="m-err" role="alert"></div></div>
    <div class="boite-pied"><button data-fermer>Annuler</button><button class="prim" id="m-ok">Adopter les types cochés</button></div>`, true);
  const boite = m.querySelector(".boite");
  boite.classList.add("adoption-boite");
  boite.setAttribute("role", "dialog"); boite.setAttribute("aria-modal", "true");
  boite.setAttribute("aria-label", "Adopter le référentiel actuel");
  boite.addEventListener("keydown", ev => {
    if (ev.key !== "Tab") return;
    const focusables = [...boite.querySelectorAll("button,input,summary,a[href]")].filter(e => !e.disabled && e.getClientRects().length);
    const premier = focusables[0], dernier = focusables.at(-1);
    if (ev.shiftKey && document.activeElement === premier) { ev.preventDefault(); dernier.focus(); }
    else if (!ev.shiftKey && document.activeElement === dernier) { ev.preventDefault(); premier.focus(); }
  });
  (m.querySelector("input:not(:disabled)") || m.querySelector("[data-fermer]")).focus();
  E.apresFermeture = () => document.querySelector("#ref-adopter")?.focus();
  m.querySelector("#m-ok").onclick = async () => {
    const choisis = [...m.querySelectorAll("input[data-type]:checked")].map(i => i.dataset.type);
    if (!choisis.length) { m.querySelector("#m-err").textContent = "Cochez au moins un type."; return; }
    const lignes = [...m.querySelectorAll("[data-confirmation]")].filter(i => choisis.includes(i.dataset.confirmationType));
    if (lignes.some(i => !i.checked)) { m.querySelector("#m-err").textContent = "Confirmez chaque renommage des équipements des types cochés."; return; }
    const bouton = m.querySelector("#m-ok"); bouton.disabled = true;
    try {
      await api("/api/referentiel/adopter", {types: choisis, renommages_confirmes: true,
        confirmations: lignes.map(i => i.dataset.confirmation), empreinte: ref.empreinte_adoption});
      fermerModale(); toast("Référentiel adopté pour " + choisis.join(", ") + " : équipements à revalider."); await recharger();
    } catch (e) { if (m.querySelector("#m-err")) m.querySelector("#m-err").textContent = e.message; bouton.disabled = false; }
  };
}
function confirmer(titre, texte, bouton, action) {
  const m = ouvrirModale(`<div class="boite-tete"><h2>${esc(titre)}</h2><p>${esc(texte)}</p></div>
    <div class="boite-pied"><button data-fermer>Annuler</button><button class="prim" id="m-ok">${esc(bouton)}</button></div>`);
  m.querySelector("#m-ok").onclick = async () => { fermerModale(); try { await action(); } catch (e) { /* toast déjà affiché */ } };
}
function modaleSaisie(titre, label, valeur, action) {
  const m = ouvrirModale(`<div class="boite-tete"><h2>${esc(titre)}</h2></div><div class="boite-corps"><div class="champs">
    <label>${esc(label)}</label><input id="m-v" value="${esc(valeur)}"></div><div class="erreur-form" id="m-err"></div></div>
    <div class="boite-pied"><button data-fermer>Annuler</button><button class="prim" id="m-ok">Valider</button></div>`);
  m.querySelector("#m-ok").onclick = async () => { try { await action(m.querySelector("#m-v").value); fermerModale(); } catch (e) { m.querySelector("#m-err").textContent = e.message; } };
}
function modaleChoix(titre, label, options, valeur, action) {
  const m = ouvrirModale(`<div class="boite-tete"><h2>${esc(titre)}</h2></div><div class="boite-corps"><div class="champs">
    <label>${esc(label)}</label><select id="m-v">${options.map(([v, t]) => `<option value="${esc(v)}" ${v === valeur ? "selected" : ""}>${esc(t)}</option>`).join("")}</select></div>
    <div class="erreur-form" id="m-err"></div></div><div class="boite-pied"><button data-fermer>Annuler</button><button class="prim" id="m-ok">Valider</button></div>`);
  m.querySelector("#m-ok").onclick = async () => { try { await action(m.querySelector("#m-v").value); fermerModale(); } catch (e) { m.querySelector("#m-err").textContent = e.message; } };
}
/* ------------------------------------------------------------------ listes d'identification, indépendantes des projets */
const GROUPES_LISTES = [["lieux", "Lieux"], ["types_ouvrage", "Types d'ouvrages"], ["automates", "Automates"], ["protocoles", "Communications"]];
// Explication du repère d'équipement selon le format de l'ouvrage (charte du 9 novembre : 12 caractères).
function texteRepere(lieu, code, numero, okLieu, okCode) {
  const charte = (E.ouvrage || {}).format_repere === "12";
  const se = charte ? "" : ` + <b>SE</b> sous-ensemble (2)`;
  const exemple = (/^[A-Z0-9]{4}$/.test(lieu) ? lieu : "XXXX") + (/^[A-Z]{2}$/.test(code) ? code : "YY") + (/^\d{2}$/.test(numero) ? numero : "01") + (charte ? "" : "11") + "HV01";
  return `Repère d'un équipement = <b class="${okLieu ? "ok" : "ko"}">${esc(lieu)}</b> lieu + <b class="${okCode ? "ok" : "ko"}">${esc(code)}</b> type d'ouvrage + <b>${esc(numero)}</b> numéro d’ouvrage${se} + <b>type et numéro</b> d'équipement (4) — exemple : <span class="mono">${esc(exemple)}</span>`;
}
function modaleListes(groupe = "lieux", edition = "") {
  const l = E.listes || {lieux:[], types_ouvrage:[], automates:[], protocoles:[]};
  const tab = l[groupe] || [], codeLibelle = groupe === "lieux" || groupe === "types_ouvrage";
  const enEdition = tab.find(x => (codeLibelle ? x.code : x) === edition);
  const old = enEdition ? (codeLibelle ? enEdition.code : enEdition) : "";
  const m = ouvrirModale(`<div class="boite-tete"><h2>Référentiel — identification de l'ouvrage</h2><p>Les changements de liste ne modifient jamais les ouvrages déjà enregistrés.</p></div>
    <div class="boite-corps"><div class="onglets-listes">${GROUPES_LISTES.map(([id, nom]) => `<button class="${groupe === id ? "active" : ""}" data-liste="${id}">${nom}</button>`).join("")}</div>
    <div class="liste-config">${tab.length ? `<table><thead><tr><th>${codeLibelle ? "Code" : "Valeur"}</th>${codeLibelle ? `<th>${groupe === "lieux" ? "Commune" : "Libellé"}</th>` : ""}${groupe === "lieux" ? "<th>Régie</th>" : ""}<th>Actions</th></tr></thead><tbody>
      ${tab.map(x => { const v = codeLibelle ? x.code : x; return `<tr><td class="mono">${esc(v)}</td>${codeLibelle ? `<td>${esc(x.libelle)}</td>` : ""}${groupe === "lieux" ? `<td>${esc(x.regie || "Autre")}</td>` : ""}<td><button data-edit-ref="${esc(v)}">Modifier</button> <button class="danger" data-sup-ref="${esc(v)}">Retirer</button></td></tr>`; }).join("")}</tbody></table>` : `<div class="vide-bloc">Liste vide : ajoutez la première valeur.</div>`}</div>
    <h3>${enEdition ? "Modifier une valeur" : "Ajouter une valeur"}</h3><div class="champs">
      ${groupe === "lieux" ? `<label for="ref-libelle">Commune</label><input id="ref-libelle" value="${esc(enEdition ? enEdition.libelle : "")}" maxlength="100" placeholder="ex. Athis-Mons">` : ""}
      <label for="ref-code">${codeLibelle ? "Code" : "Valeur"}</label><div class="code-lieu"><input id="ref-code" value="${esc(old)}" ${groupe === "lieux" ? 'maxlength="4" style="text-transform:uppercase" placeholder="4 lettres"' : groupe === "types_ouvrage" ? 'maxlength="2" style="text-transform:uppercase"' : 'maxlength="100"'}>${groupe === "lieux" ? '<span class="aide" id="ref-prop">Le code est proposé par la charte à partir du nom de la commune.</span>' : ""}</div>
      ${groupe === "types_ouvrage" ? `<label for="ref-libelle">Libellé</label><input id="ref-libelle" value="${esc(enEdition ? enEdition.libelle : "")}" maxlength="100">` : ""}
      ${groupe === "lieux" ? `<label>Régie</label><select id="ref-regie"><option value="ESB" ${(enEdition?.regie || "AUTRE").toUpperCase() === "ESB" ? "selected" : ""}>ESB</option><option value="RESO" ${(enEdition?.regie || "AUTRE").toUpperCase() === "RESO" ? "selected" : ""}>RESO</option><option value="AUTRE" ${(enEdition?.regie || "AUTRE").toUpperCase() === "AUTRE" ? "selected" : ""}>Autre</option></select>` : ""}
    </div><div class="erreur-form" id="ref-err"></div></div>
    <div class="boite-pied"><span class="gauche">Les anciennes valeurs restent dans les projets.</span>${enEdition ? '<button id="ref-annuler">Annuler la modification</button>' : ""}<button data-fermer>Fermer</button><button id="ref-ok" class="prim">${enEdition ? "Enregistrer" : "Ajouter"}</button></div>`, true);
  const actualiser = async () => { E.listes = await api("/api/listes-ouvrage"); if (E.vue === "ouvrage") await recharger(); modaleListes(groupe); };
  m.querySelectorAll("[data-liste]").forEach(b => b.onclick = () => modaleListes(b.dataset.liste));
  m.querySelectorAll("[data-edit-ref]").forEach(b => b.onclick = () => modaleListes(groupe, b.dataset.editRef));
  m.querySelectorAll("[data-sup-ref]").forEach(b => b.onclick = () => confirmer("Retirer du référentiel ?", `« ${b.dataset.supRef} » ne sera plus proposé dans la liste. Les projets existants ne seront pas modifiés.`, "Retirer", async () => {
    try { await api("/api/listes-ouvrage/action", {action:"supprimer", groupe, ancien:b.dataset.supRef}); await actualiser(); }
    catch (e) { toast(e.message, true); }
  }));
  if (m.querySelector("#ref-annuler")) m.querySelector("#ref-annuler").onclick = () => modaleListes(groupe);
  if (groupe === "lieux") proposerCodeLieu(m, old);
  m.querySelector("#ref-ok").onclick = async () => {
    const payload = {action: enEdition ? "modifier" : "ajouter", groupe, ancien: old, code:m.querySelector("#ref-code").value, libelle:codeLibelle ? m.querySelector("#ref-libelle").value : "", regie:groupe === "lieux" ? m.querySelector("#ref-regie").value : ""};
    try { await api("/api/listes-ouvrage/action", payload); await actualiser(); toast("Référentiel mis à jour."); }
    catch (e) { m.querySelector("#ref-err").textContent = e.message; }
  };
}
// Proposition du code lieu selon la charte (règle d'abréviation, exceptions, doublons refusés).
function proposerCodeLieu(m, ancien) {
  const lib = m.querySelector("#ref-libelle"), code = m.querySelector("#ref-code"), aide = m.querySelector("#ref-prop");
  let auto = "", minuterie = null, demande = 0;
  const afficher = r => {
    if (!r.code) { aide.className = "aide"; aide.textContent = r.message || "Saisissez le nom de la commune."; return; }
    if (!code.value || code.value.toUpperCase() === auto) { code.value = r.code; auto = r.code; }
    const origine = r.origine === "exception" ? "exception validée de la charte" : "règle de la charte";
    if (r.conflit) {
      aide.className = "aide al";
      aide.innerHTML = `${esc(r.code)} (${origine}) est déjà utilisé. Codes libres : ${r.variantes.map(v => `<button type="button" class="lien" data-var="${esc(v)}">${esc(v)}</button>`).join(" ") || "aucun, saisissez un code"}`;
      aide.querySelectorAll("[data-var]").forEach(b => b.onclick = () => { code.value = b.dataset.var; auto = b.dataset.var; });
    } else { aide.className = "aide ok"; aide.textContent = `${r.code} : ${origine}.`; }
  };
  const demander = async () => {
    const n = ++demande;
    try { const r = await api(`/api/lieu-proposition?nom=${encodeURIComponent(lib.value)}&ancien=${encodeURIComponent(ancien || "")}`); if (n === demande) afficher(r); }
    catch (e) { aide.textContent = e.message; }
  };
  lib.addEventListener("input", () => { clearTimeout(minuterie); minuterie = setTimeout(demander, 200); });
  if (ancien) auto = ""; else if (lib.value) demander();
}
// Retour d'essai 3 : choix des protocoles dans une liste déroulante à cases à cocher, sans fenêtre.
// Une ancienne valeur hors référentiel reste cochée et grisée : elle n'est jamais effacée en silence.
function deroulantCommunications(bouton, avantGestion) {
  const ouvert = document.querySelector(".deroulant-protocoles");
  if (ouvert) { ouvert.remove(); if (ouvert.dataset.pour === bouton.id) return; }
  const refs = (E.listes || {}).protocoles || [];
  const actuels = (bouton.dataset.valeur || "").split(",").map(x => x.trim()).filter(Boolean);
  const inconnus = actuels.filter(x => !refs.includes(x));
  const d = document.createElement("div");
  d.className = "deroulant-protocoles"; d.dataset.pour = bouton.id; d.setAttribute("role", "listbox"); d.setAttribute("aria-multiselectable", "true");
  d.innerHTML = (refs.length || inconnus.length ? [...refs, ...inconnus].map(x => `<label><input type="checkbox" value="${esc(x)}" ${actuels.includes(x) ? "checked" : ""} ${inconnus.includes(x) ? "disabled" : ""}> ${esc(x)}${inconnus.includes(x) ? " <small>(hors référentiel, conservé)</small>" : ""}</label>`).join("")
      : `<div class="vide">Aucun protocole déclaré.</div>`) + `<div class="pied"><button type="button" class="lien" data-gerer>Gérer les protocoles…</button><button type="button" data-fermer-liste>Fermer</button></div>`;
  document.body.appendChild(d);
  const r = bouton.getBoundingClientRect();
  d.style.left = r.left + "px"; d.style.top = (r.bottom + 4) + "px"; d.style.minWidth = Math.max(260, r.width) + "px";
  const maj = () => {
    const choix = [...d.querySelectorAll("input:checked")].map(x => x.value);
    bouton.dataset.valeur = choix.join(", ");
    bouton.innerHTML = `${esc(bouton.dataset.valeur || "— Choisir les protocoles —")} <span aria-hidden="true">▾</span>`;
    bouton.dispatchEvent(new Event("change"));
  };
  d.querySelectorAll("input").forEach(x => x.onchange = maj);
  d.querySelector("[data-gerer]").onclick = () => { d.remove(); avantGestion?.(); modaleListes("protocoles"); };
  d.querySelector("[data-fermer-liste]").onclick = () => d.remove();
  setTimeout(() => document.addEventListener("click", function hors(ev) {
    if (!d.isConnected) return document.removeEventListener("click", hors);
    if (!d.contains(ev.target) && ev.target !== bouton) { d.remove(); document.removeEventListener("click", hors); }
  }), 0);
}
function modaleCommunications() {
  const i = E.ficheDraft || E.ouvrage.identification, refs = (E.listes || {}).protocoles || [];
  const actuels = i.communication ? i.communication.split(",").map(x => x.trim()).filter(Boolean) : [];
  const inconnus = actuels.filter(x => !refs.includes(x));
  const valeurs = [...refs, ...inconnus];
  const m = ouvrirModale(`<div class="boite-tete"><h2>Protocoles de communication</h2><p>Sélectionnez les protocoles utilisés sur l'ouvrage. Aucun n'est imposé.</p></div>
    <div class="boite-corps"><div class="choix-protocoles">${valeurs.length ? valeurs.map(x => `<label><input type="checkbox" value="${esc(x)}" ${actuels.includes(x) ? "checked" : ""} ${inconnus.includes(x) ? "disabled" : ""}>${esc(x)}${inconnus.includes(x) ? " (ancien libellé : à ajouter au référentiel)" : ""}</label>`).join("") : "Aucun protocole déclaré."}</div>
    ${inconnus.length ? '<div class="avert">Ancienne valeur non référencée. Elle ne sera pas supprimée sans action de votre part : ajoutez-la au référentiel ou remplacez-la explicitement.</div>' : ""}
    <div class="erreur-form" id="comm-err"></div></div><div class="boite-pied"><button id="comm-gerer">Gérer les protocoles…</button><button data-fermer>Annuler</button><button class="prim" id="comm-ok">Enregistrer</button></div>`);
  m.querySelector("#comm-gerer").onclick = () => modaleListes("protocoles");
  m.querySelector("#comm-ok").onclick = async () => {
    const choix = [...m.querySelectorAll("input[type=checkbox]:checked:not(:disabled)")].map(x => x.value);
    // Ne pas effacer une ancienne valeur qui n'appartient pas au référentiel par accident.
    if (inconnus.length && !window.confirm("Des protocoles historiques sont hors référentiel. Les remplacer par votre sélection ?")) return;
    try {
      if (E.vue === "ouvrage" && E.sel.nature === "ouvrage") {
        const b = $("#communication-choix");
        if (!b) throw new Error("La fiche ouvrage n’est plus affichée.");
        b.dataset.valeur = choix.join(", ");
        b.innerHTML = `${esc(b.dataset.valeur || "— Choisir les protocoles —")} <span aria-hidden="true">▾</span>`;
        b.dispatchEvent(new Event("change"));
        fermerModale();
      } else {
        await api("/api/identification/selection", {champ:"communication", valeurs:choix}); fermerModale(); await recharger();
      }
    } catch (e) { m.querySelector("#comm-err").textContent = e.message; }
  };
}

function modaleUF(u) {
  const o = E.ouvrage;
  const m = ouvrirModale(`<div class="boite-tete"><h2>${u ? "Modifier l'unité fonctionnelle" : "Nouvelle unité fonctionnelle"}</h2>
    <p>Une UF regroupe des équipements (ex. UF01 Stockage). Son code n'entre pas dans les repères.</p></div>
    <div class="boite-corps"><div class="champs">
      <label>Code</label><input id="u-code" maxlength="6" value="${esc(u ? u.code : "UF" + String(o.unites.length + 1).padStart(2, "0"))}" style="text-transform:uppercase">
      <label>Libellé</label><input id="u-lib" value="${esc(u ? u.libelle : "")}" placeholder="ex. Stockage, Pompage, Électricité">
      <label>Sous-ensemble</label><input id="u-se" maxlength="2" value="${esc(u ? u.se : "")}" placeholder="ex. 11" style="text-transform:uppercase" list="liste-se">
      <div class="aide">Facultatif : proposé aux équipements créés dans cette UF (2 caractères du repère). Créé s'il n'existe pas.</div>
    </div><datalist id="liste-se">${o.sous_ensembles.map(x => `<option value="${esc(x.code)}">${esc(x.libelle)}</option>`).join("")}</datalist>
    <div class="erreur-form" id="m-err"></div></div>
    <div class="boite-pied"><button data-fermer>Annuler</button><button class="prim" id="m-ok">${u ? "Enregistrer" : "Créer l'UF"}</button></div>`);
  m.querySelector("#m-ok").onclick = async () => {
    const d = {code: u ? u.code : m.querySelector("#u-code").value.toUpperCase(), nouveau_code: m.querySelector("#u-code").value.toUpperCase(),
               libelle: m.querySelector("#u-lib").value, se: m.querySelector("#u-se").value.toUpperCase(), action: u ? "modifier" : "ajouter"};
    try { await api("/api/uf", d); fermerModale(); toast(u ? "UF modifiée." : "UF créée."); E.sel = {nature: "uf", valeur: d.nouveau_code}; recharger(); }
    catch (e) { m.querySelector("#m-err").textContent = e.message; }
  };
}
function modaleEquipement(eq, ufDefaut) {
  const o = E.ouvrage;
  if (!eq && !(o.identification.lieu && o.identification.code_ouvrage)) {
    toast("Renseignez d'abord le lieu et le code de l'ouvrage (identification).", true);
    E.sel = {nature: "ouvrage", valeur: ""}; return rendre();
  }
  const uf = eq ? eq.uf : (ufDefaut || "");
  const seUf = (o.unites.find(u => u.code === uf) || {}).se || "";
  const m = ouvrirModale(`<div class="boite-tete"><h2>${eq ? "Modifier " + esc(eq.pcf) : "Nouvel équipement"}</h2>
    <p>Choisir le type puis le modèle d’équipement : ses E/S physiques et ses informations de télétransmission en découlent.</p></div>
    <div class="boite-corps"><div class="champs">
      <label>Type</label><select id="q-type"><option value="">— choisir —</option>${o.types.map(t => `<option value="${esc(t.code)}">${esc(t.code.replace(/--$/, ""))} — ${esc(t.designation)}${t.domaine ? " (" + esc(t.domaine) + ")" : ""}</option>`).join("")}</select>
      <label>Modèle</label><select id="q-modele"></select>
      <label>Unité fonctionnelle</label><select id="q-uf"><option value="">— aucune (hors UF) —</option>${o.unites.map(u => `<option value="${esc(u.code)}">${esc(u.code)} — ${esc(u.libelle)}</option>`).join("")}</select>
      <label>Sous-ensemble</label><input id="q-se" maxlength="2" list="liste-se2" style="text-transform:uppercase" placeholder="${o.format_repere === "12" ? "facultatif" : "ex. P1"}">
      ${o.format_repere === "12" ? '<span class="aide">Regroupement dans l’inventaire : n’entre pas dans le repère (charte ESB / RESO).</span>' : ""}
      <label>Numéro</label><input id="q-num" maxlength="2" placeholder="01">
      <label>Libellé</label><input id="q-lib" maxlength="32" placeholder="32 caractères au plus">
      <label>Repère</label><div class="mono" id="q-rep" style="font-size:15px;font-weight:600"></div>
    </div><datalist id="liste-se2">${o.sous_ensembles.map(x => `<option value="${esc(x.code)}">${esc(x.libelle)}</option>`).join("")}</datalist>
    <div class="erreur-form" id="m-err"></div></div>
    <div class="boite-pied"><button data-fermer>Annuler</button><button class="prim" id="m-ok">${eq ? "Enregistrer" : "Ajouter l'équipement"}</button></div>`);
  const q = s => m.querySelector(s);
  q("#q-type").value = eq ? eq.type : ""; q("#q-uf").value = uf; q("#q-se").value = eq ? eq.se : seUf;
  q("#q-num").value = eq ? eq.numero : ""; q("#q-lib").value = eq ? eq.libelle : "";
  const majModeles = garder => {
    const t = o.types.find(x => x.code === q("#q-type").value);
    const mods = t ? t.modeles : [];
    q("#q-modele").innerHTML = mods.length ? mods.map(n => `<option value="${esc(n)}">${esc(n)}</option>`).join("") : `<option value="">— aucun modèle pour ce type —</option>`;
    if (garder && eq) q("#q-modele").value = eq.modele;
  };
  const majRepere = () => {
    const t = q("#q-type").value, n = q("#q-num").value.padStart(2, "0"), se = q("#q-se").value.toUpperCase() || "??";
    const fin = t ? (t.includes("--") ? t : t + "--").replace("--", n) : "????";
    q("#q-rep").textContent = (o.prefixe || "??????") + (o.format_repere === "12" ? "" : se) + fin;
  };
  const numeroLibre = async () => {
    if (eq || !q("#q-type").value || (!q("#q-se").value && o.format_repere !== "12")) return majRepere();
    const r = await api(`/api/numero?type=${encodeURIComponent(q("#q-type").value)}&se=${encodeURIComponent(q("#q-se").value.toUpperCase())}`);
    q("#q-num").value = r.numero; majRepere();
  };
  majModeles(true); majRepere();
  q("#q-type").onchange = () => { majModeles(false); numeroLibre(); };
  q("#q-se").oninput = numeroLibre; q("#q-num").oninput = majRepere;
  q("#q-uf").onchange = () => { const s = (o.unites.find(u => u.code === q("#q-uf").value) || {}).se; if (s && !eq) { q("#q-se").value = s; numeroLibre(); } };
  q("#m-ok").onclick = async () => {
    const d = {type: q("#q-type").value, modele: q("#q-modele").value, uf: q("#q-uf").value, se: q("#q-se").value.toUpperCase(),
               numero: q("#q-num").value, libelle: q("#q-lib").value};
    if (!d.type) return q("#m-err").textContent = "Choisissez le type.";
    try {
      const r = await api(eq ? "/api/equipement/modifier" : "/api/equipement/ajouter", eq ? {...d, ident: eq.ident} : d);
      fermerModale(); toast(eq ? "Équipement modifié." : "Équipement ajouté.");
      E.sel = {nature: "eq", valeur: r.ident}; recharger();
    } catch (e) { q("#m-err").textContent = e.message; }
  };
}
function modaleImport(natureInitiale = "inventaire") {
  const types = [
    ["inventaire", "Inventaire des équipements"],
    ["variables_existantes", "Variables automate existantes"],
    ["liste_es_existante", "Liste d’E/S existante"]
  ];
  const m = ouvrirModale(`<div class="boite-tete"><h2>Importer et vérifier des données</h2>
    <p>OGIAS analyse toutes les lignes avant intégration. Un doublon ou une erreur bloque l'import ; les données du projet ne changent pas pendant l'aperçu.</p></div>
    <div class="boite-corps">
      <div class="champs"><label>Nature des données</label><select id="i-nature">${types.map(([v,l]) => `<option value="${v}">${l}</option>`).join("")}</select>
      <label>Fichier source</label><input type="file" id="i-f" accept=".xlsx,.xlsm,.ods,.csv,.txt,.scy"></div>
      <div id="i-res" style="margin-top:14px" aria-live="polite"></div>
      <div class="erreur-form" id="m-err" role="alert"></div></div>
    <div class="boite-pied"><span class="gauche" id="i-bilan"></span><button data-fermer>Annuler</button>
      <button class="prim" id="m-ok" disabled>Confirmer l’import</button></div>`, true);
  const select = m.querySelector("#i-nature"), file = m.querySelector("#i-f");
  const output = m.querySelector("#i-res"), errors = m.querySelector("#m-err");
  const action = m.querySelector("#m-ok"), summary = m.querySelector("#i-bilan");
  select.value = types.some(x => x[0] === natureInitiale) ? natureInitiale : "inventaire";
  let token = "";
  const reset = () => { token = ""; action.disabled = true; summary.innerHTML = ""; output.innerHTML = ""; errors.textContent = ""; };
  const dessinerLignes = lignes => lignes.map(r => {
    const id = r.donnees.repere || r.donnees.nom || "—";
    const msg = r.diagnostics.map(d => `${d.code} : ${d.message}`).join(" ; ");
    const cls = {a_creer:"b-ok", deja_present:"b-n", refuse:"b-err", ligne_vide:"b-n"};
    const labels = {a_creer:"À créer", deja_present:"Déjà présent", refuse:"Refusé", ligne_vide:"Vide"};
    return `<tr><td>${r.ligne}</td><td class="mono">${esc(id)}</td>
      <td><span class="badge ${cls[r.action] || 'b-al'}">${labels[r.action] || esc(r.action)}</span></td>
      <td>${esc(msg || "—")}</td></tr>`;
  }).join("");
  let pageActive = 1;
  let pagesTotal = 1;
  const etatPages = () => {
    const precedent = output.querySelector("#i-prec"), suivant = output.querySelector("#i-suiv");
    if (!precedent || !suivant) return;
    precedent.disabled = pageActive <= 1;
    suivant.disabled = pageActive >= pagesTotal;
    output.querySelector("#i-page-label").textContent = `Page ${pageActive} / ${pagesTotal}`;
  };
  const changerPage = async nouvellePage => {
    if (!token || nouvellePage < 1 || nouvellePage > pagesTotal) return;
    const ancienToken = token;
    const precedent = output.querySelector("#i-prec"), suivant = output.querySelector("#i-suiv");
    precedent.disabled = true; suivant.disabled = true;
    try {
      const result = await api(`/api/inbound/lignes?jeton=${encodeURIComponent(ancienToken)}&page=${nouvellePage}`);
      if (ancienToken !== token) return;
      output.querySelector("#i-lignes").innerHTML = dessinerLignes(result.lignes_affichees);
      pageActive = result.pagination.page;
    } catch (e) { errors.textContent = e.message; }
    finally { if (ancienToken === token) etatPages(); }
  };
  select.onchange = reset;
  file.onchange = async () => {
    reset();
    if (!file.files.length) return;
    output.innerHTML = '<div class="vide">Analyse et validation du fichier…</div>';
    try {
      const source = await lireFichier(file);
      const report = await api("/api/inbound/apercu", {...source, nature: select.value});
      token = report.jeton;
      const stats = report.statistiques;
      pageActive = report.pagination.page;
      pagesTotal = report.pagination.pages;
      summary.textContent = `${stats.total} lignes · ${stats.erreurs} erreur(s) · ${stats.avertissements} avertissement(s)`;
      output.innerHTML = `<div class="note">${esc(report.fichier.split(/[\\/]/).pop())} · Feuille : ${esc(report.feuille)} · ${stats.a_creer} à créer · ${stats.deja_present} inchangées · ${stats.refuse} refusées.</div>
        ${report.diagnostics_globaux.map(d => `<div class="note">${esc(d.gravite)} : ${esc(d.message)}</div>`).join("")}
        <div style="max-height:340px;overflow:auto"><table><thead><tr><th>Ligne</th><th>Identifiant</th><th>État</th><th>Diagnostic</th></tr></thead>
        <tbody id="i-lignes">${dessinerLignes(report.lignes_affichees)}</tbody></table></div>
        ${pagesTotal > 1 ? `<div class="ligne-actions" style="display:flex;align-items:center;justify-content:space-between;gap:10px;margin-top:10px">
          <button type="button" id="i-prec">← Précédent</button>
          <span id="i-page-label" aria-live="polite">Page ${pageActive} / ${pagesTotal}</span>
          <button type="button" id="i-suiv">Suivant →</button></div>` : ""}
        ${stats.erreurs ? '<div class="note" style="color:#ad3030">Import bloqué : corrigez les erreurs dans le fichier puis relancez l’analyse.</div>' : ""}`;
      if (pagesTotal > 1) {
        output.querySelector("#i-prec").onclick = () => changerPage(pageActive - 1);
        output.querySelector("#i-suiv").onclick = () => changerPage(pageActive + 1);
        etatPages();
      }
      action.disabled = !report.integrable;
      action.textContent = report.integrable ? `Confirmer ${stats.a_creer} ajout(s)` : "Import indisponible";
    } catch (e) { token = ""; output.innerHTML = ""; errors.textContent = e.message; }
  };
  action.onclick = async () => {
    if (!token) return;
    action.disabled = true;
    try {
      const result = await api("/api/inbound/appliquer", {jeton:token, confirmer:true});
      token = "";
      fermerModale();
      toast(`${result.crees} donnée(s) intégrée(s).`);
      E.sel = {nature:"ouvrage", valeur:""};
      await recharger();
    } catch (e) { token = ""; errors.textContent = e.message + " Relancez l’analyse du fichier."; }
  };
}

/* ------------------------------------------------------------------ référentiel */
/* ------------------------------------------------------------------ référentiel : un seul cycle publié → brouillon → publication
   Maquette validée le 9 novembre 2026 : consultation en lecture seule de la révision publiée ; toute modification
   dans un brouillon (écran, éditeur des modèles ou classeur Excel) ; contrôle, comparaison, publication motivée. */
const ONGLETS_REF = [["es", "E/S physiques"], ["fonct", "Informations fonctionnelles"], ["regles", "Règles"],
                     ["modeles", "Modèles et lignes"], ["usage", "Utilisation"], ["audit", "Contrôle de conception"]];
const presenceBadge = p => `<span class="badge ${p === "Règle" ? "b-al" : p === "Obligatoire" ? "b-ok" : "b-n"}">${esc(p)}</span>`;
function bandeauReferentiel() {
  const c = E.cycle, b = c.brouillon, enBrouillon = E.ref.source === "brouillon";
  const compteurs = [[c.compteurs.types,'types'],[c.compteurs.signaux,'signaux'],[c.compteurs.regles,'règles'],[c.compteurs.modeles,'modèles']].filter(([n])=>n>0).map(([n,nom])=>`${n} ${nom}`).join(' · ');
  if (enBrouillon) return `<section class="bandeau-ref brouillon"><div class="txt"><div class="ligne"><h1>Brouillon du référentiel</h1>
      <span class="pilule al">Brouillon · basé sur R${String(b.base_revision).padStart(4, "0")}${b.restauration_de ? " · reprise de R" + String(b.restauration_de).padStart(4, "0") : ""}</span>
      ${b.etat === "validé" ? '<span class="pilule ok">validé, prêt à publier</span>' : ""}</div>
      ${E.ref.nb_modifications?`<div class="sous">${E.ref.nb_modifications} modification(s) depuis la révision publiée</div>`:''}
      ${b.perime ? '<p class="c-err">La révision publiée a changé : recréez le brouillon avant de publier.</p>' : ""}</div>
    <div class="actions"><button id="rf-voir-pub">Voir la révision publiée</button>
      <details class="v31-actions-more"><summary>Autres actions</summary><div class="v31-actions-menu"><button id="rf-exp-b">Exporter le brouillon vers Excel</button><button id="rf-imp">Importer un classeur…</button><button class="danger" id="rf-abandon">Supprimer le brouillon</button></div></details>
      <button class="prim" id="rf-pub">Contrôler et publier</button></div></section>`;
  return `<section class="bandeau-ref"><div class="txt"><div class="ligne"><h1>Référentiel métier</h1>
      <span class="pilule ok">${c.revision ? "Révision R" + String(c.revision).padStart(4, "0") + " publiée" : "Référentiel livré"}</span>
      <span tabindex="0" role="img" aria-label="Informations sur la révision" title="${esc((c.publie_le?c.publie_le+' · ':'')+'Empreinte : '+c.empreinte+' · Toute modification passe par un brouillon.')}">${V31.icon('info',16)}</span></div>
      ${compteurs?`<div class="sous">${compteurs}</div>`:''}${c.incoherence ? `<p class="c-err">${esc(c.incoherence)}</p>` : ""}</div>
    <div class="actions"><button id="rf-hist">Historique des révisions</button><button id="rf-exp">Exporter vers Excel</button>
      ${!b && (c.brouillons_supprimes || []).length ? '<button id="rf-recuperer">Récupérer un brouillon supprimé</button>' : ""}
      ${b ? '<button class="prim" id="rf-ouvrir-b">Reprendre le brouillon en cours</button>' : '<button class="prim" id="rf-creer">Modifier : créer un brouillon</button>'}</div></section>`;
}
async function vueReferentiel() {
  if (E.refEcran === "publication" && E.cycle.brouillon) return vuePublicationReferentiel();
  if (E.refEcran === "historique") return vueHistoriqueReferentiel();
  if (["lexique", "dictionnaire_es", "correspondances"].includes(E.refObjet)) return vueCodesReferentiel();
  const r = E.ref, ed = r.source === "brouillon", q = (E.refQ || "").toLowerCase();
  const t = r.types.find(x => x.code === E.refType);
  const onglet = E.refOnglet || "fonct";
  const types = r.types.filter(x => !q || (x.code + " " + x.designation + " " + x.es.concat(x.fonctionnelles).map(s => s.code + " " + s.information).join(" ")).toLowerCase().includes(q))
                       .filter(x => !E.refFiltre || (E.refFiltre === "audit" ? x.audit.length : x.modifie));
  $("#vue").innerHTML = `${bandeauReferentiel()}${navigationObjetsReferentiel()}<div class="ref-corps">
    <aside class="ref-types"><div class="ref-types-tete"><label for="rf-q">Types d'équipement</label>
      <input id="rf-q" type="search" placeholder="Rechercher un type, un signal…" value="${esc(E.refQ || "")}">
      <div class="puces"><button class="${!E.refFiltre ? "on" : ""}" data-f="">Tous ${r.types.length}</button>
        <button class="${E.refFiltre === "audit" ? "on" : ""}" data-f="audit">À arbitrer ${r.types.filter(x => x.audit.length).length}</button>
        ${ed ? `<button class="${E.refFiltre === "modif" ? "on" : ""}" data-f="modif">Modifiés ${r.types.filter(x => x.modifie).length}</button>` : ""}</div></div>
      ${types.map(x => `<button type="button" class="ref-type${x.code === E.refType ? " sel" : ""}" data-t="${esc(x.code)}" title="${esc(x.code + " — " + (x.designation || "sans désignation"))}"><span class="tag">${esc(x.code)}</span>
        <span class="nom">${esc(x.designation || "sans désignation")}</span>${x.modifie ? '<span class="badge b-al" title="modifié dans le brouillon">modifié</span>' : ""}
        ${x.audit.length ? '<span class="pt-etat pt-al" title="point de conception à arbitrer"></span>' : ""}<span class="nb">${x.modeles.length}</span></button>`).join("")}
      ${types.length ? "" : '<div class="vide-bloc">Aucun type pour ce filtre.</div>'}</aside>
    <main class="ref-detail">${t ? detailTypeReferentiel(t, onglet, ed) : '<div class="vide-bloc">Référentiel vide.</div>'}</main></div>`;
  brancherReferentiel(t, ed);
}
function detailTypeReferentiel(t, onglet, ed) {
  const nbF = t.fonctionnelles.filter(s => s.famille !== "ES").length;
  const tete = `<div class="bloc ref-type-tete"><div><small>Type ${esc(t.code)} · ${esc(t.domaine || t.categorie || "")}</small><h2>${esc(t.designation)}</h2>
      <div class="sous">Options : ${t.options.length ? t.options.map(esc).join(" · ") : "aucune"}${ed ? ' · <button class="lien" id="rf-type-mod">Modifier le type</button>' : ""}
      ${ed&&t.archivable?`<button class="lien" id="rf-type-archive">${t.archive?'Réactiver le type':'Archiver le type'}</button>`:''}${t.archive?'<span class="badge b-n">Type de modèles archivé</span>':''}</div></div>
    <div class="compteurs-ref"><span><b>${t.es.length}</b> E/S physiques</span><span><b>${nbF}</b> informations</span><span><b>${t.regles.length}</b> règles</span><span><b>${t.modeles.length}</b> modèles</span></div></div>
    <nav class="onglets-ref" aria-label="Vues du type">${ONGLETS_REF.map(([k, n]) => `<button type="button" data-o="${k}" class="${k === onglet ? "on" : ""}">${n}${k === "audit" && t.audit.length ? ` <span class="badge b-al">${t.audit.length}</span>` : ""}</button>`).join("")}</nav>`;
  const marque = s => s.modifie ? ' class="modifie"' : "";
  const actionSig = s => ed ? `<td class="act"><button class="lien rf-sig" data-id="${esc(s.id)}">Modifier</button><button class="lien danger rf-sig-sup" data-id="${esc(s.id)}">Supprimer</button></td>` : "";
  let corps = "";
  if (onglet === "es") corps = `<div class="bloc"><table><thead><tr><th>Identifiant</th><th>Nature</th><th>Information</th><th>Présence</th><th>Type</th><th>Paramètres d'installation</th>${ed ? "<th></th>" : ""}</tr></thead><tbody>
      ${t.es.map(s => `<tr${marque(s)}><td class="mono">${esc(s.id)}</td><td><span class="tag p-${esc(s.es)}">${esc(s.es)}</span></td><td>${esc(s.information)}${s.famille !== "ES" ? ` <span class="aide">· contact câblé porté par ${esc(s.famille)}_${esc(s.code)}</span>` : ""}</td>
        <td>${presenceBadge(s.presence)}${s.option ? ` <small>${esc(s.option)}</small>` : ""}</td><td>${esc(s.type_logique)}</td><td class="aide">dans la fiche de l'équipement</td>${actionSig(s)}</tr>`).join("") || '<tr><td colspan="7" class="vide">Aucune E/S physique déclarée pour ce type.</td></tr>'}</tbody></table>
      ${ed ? '<div class="pied-bloc"><button id="rf-add-es">+ Ajouter une E/S physique</button></div>' : ""}</div>`;
  if (onglet === "fonct") corps = `<div class="bloc"><table><thead><tr><th>Information</th><th>Famille</th><th>Libellé</th><th>Présence</th><th>Source</th><th>Logique à programmer</th>${ed ? "<th></th>" : ""}</tr></thead><tbody>
      ${t.fonctionnelles.filter(s => s.famille !== "ES").map(s => `<tr${marque(s)}><td class="mono">${esc(s.famille)}_${esc(s.code)}</td><td><span class="role">${esc(s.famille)}</span></td><td>${esc(s.information)}${s.alarme ? ' <span class="tag">alarme</span>' : ""}</td>
        <td>${presenceBadge(s.presence)}${s.option ? ` <small>${esc(s.option)}</small>` : ""}</td><td class="mono">${esc(s.source || (s.es && s.es !== "Interne" ? "câblée (" + s.es + ")" : "—"))}</td><td class="justif">${esc(s.logique || "")}</td>${actionSig(s)}</tr>`).join("")}</tbody></table>
      ${ed ? '<div class="pied-bloc"><button id="rf-add-f">+ Ajouter une information</button></div>' : ""}</div>`;
  if (onglet === "regles") corps = `${t.regles.map(g => `<div class="bloc regle${g.modifie ? " modifie" : ""}"><div class="ligne"><b class="mono">${esc(g.id)}</b><span>${esc(g.libelle || "")}</span>
      <span class="badge ${g.mode === "auto" ? "b-ok" : "b-al"}">${g.mode === "auto" ? "automatique" : "proposition, à décider par équipement"}</span>
      ${ed && g.type !== "*" ? `<span class="droite"><button class="lien rf-reg" data-id="${esc(g.id)}">Modifier</button><button class="lien danger rf-reg-sup" data-id="${esc(g.id)}">Supprimer</button></span>` : ""}</div>
      <div class="aide">Si <span class="mono">${esc((g.si || []).join(" + "))}</span> → propose <span class="mono">${esc((g.propose || []).join(", "))}</span>${g.type === "*" ? " · règle commune à tous les types" : ""}</div>
      <div>${esc(g.logique || "")}</div></div>`).join("") || '<div class="vide-bloc">Aucune règle pour ce type.</div>'}
      ${ed ? '<div class="pied-bloc"><button id="rf-add-r">+ Ajouter une règle</button></div>' : ""}
      <p class="aide">Une règle décrit ce que l'automaticien doit programmer ; elle n'est jamais exécutée depuis Excel. Un nouvel algorithme se développe et se teste dans OGIAS.</p>`;
  if (onglet === "modeles") corps = `${t.modeles.map(m => `<div class="bloc"><div class="bloc-tete"><h3>${esc(m.nom)}</h3><span class="badge ${m.statut === "validé" ? "b-ok" : "b-al"}">${esc(m.statut)}</span>
        <span class="aide">${m.lignes.length} ligne(s) de supervision${m.signaux_propres ? " · signaux propres au modèle" : " · signaux du type"}</span>
        ${ed ? `<div class="droite"><button class="rf-mval" data-n="${esc(m.nom)}" data-v="${m.statut === "validé" ? 0 : 1}">${m.statut === "validé" ? "Repasser à valider" : "Valider le modèle"}</button><button class="rf-ladd" data-n="${esc(m.nom)}">+ Ligne</button><button class="rf-mdup" data-n="${esc(m.nom)}">Dupliquer</button><button class="rf-marc" data-n="${esc(m.nom)}" data-a="${m.statut === "archivé" ? 0 : 1}">${m.statut === "archivé" ? "Désarchiver" : "Archiver"}</button><button class="danger rf-msup" data-n="${esc(m.nom)}">Supprimer</button></div>` : ""}</div>
      <table><tbody>${m.lignes.map(l => `<tr><td><span class="role">${esc(l.role)}</span></td><td>${esc(l.libelle)}</td><td class="mono">${esc(l.suffixe)}</td><td>${esc(l.format)}</td><td>${esc(l.unite || "")}</td>
        ${ed ? `<td class="act"><button class="lien rf-lmod" data-n="${esc(m.nom)}" data-id="${esc(l.id)}">Modifier</button><button class="lien danger rf-lsup" data-n="${esc(m.nom)}" data-id="${esc(l.id)}">Supprimer</button></td>` : ""}</tr>`).join("") || '<tr><td class="vide">Aucune ligne.</td></tr>'}</tbody></table></div>`).join("") || '<div class="vide-bloc">Aucun modèle pour ce type.</div>'}
      ${ed ? '<div class="pied-bloc"><button id="rf-madd">+ Nouveau modèle pour ce type</button></div>' : ""}`;
  if (onglet === "usage") corps = `<div class="bloc"><table><thead><tr><th>Ouvrage</th><th>Équipements</th><th>Référentiel figé</th></tr></thead><tbody>
      ${t.usages.map(u => `<tr><td class="mono">${esc(u.repere)}</td><td>${u.equipements}</td><td>${esc(u.revision)}</td></tr>`).join("") || '<tr><td colspan="3" class="vide">Aucun ouvrage enregistré n\'utilise ce type.</td></tr>'}</tbody></table>
      <p class="aide" style="padding:0 14px">Un ouvrage garde son référentiel figé ; il adopte une nouvelle révision depuis sa propre fiche, sur décision.</p></div>`;
  if (onglet === "audit") corps = `<div class="bloc">${t.audit.length ? `<ul class="liste-controles">${t.audit.map(x => `<li class="${x.gravite === "Erreur" ? "c-err" : "c-al"}"><b>${esc(x.code)}</b> — ${esc(x.message)}${x.cles.length ? ` <span class="mono">${esc(x.cles.join(", "))}</span>` : ""}</li>`).join("")}</ul>`
      : '<p class="c-ok" style="padding:12px 14px">Aucun point de conception à arbitrer pour ce type.</p>'}</div>`;
  return tete + corps;
}
const actionRef = async (corps, msg) => { await agir(api("/api/referentiel/cycle/action", corps), msg); await chargerReferentiel(); vueReferentiel(); };
const editionModeles = async (corps, msg) => { await agir(api("/api/referentiel/action", corps), msg); await chargerReferentiel(); vueReferentiel(); };
function brancherReferentiel(t, ed) {
  const v = $("#vue");
  brancherNavigationReferentiel();
  v.querySelectorAll("[data-t]").forEach(b => b.onclick = () => { E.refType = b.dataset.t; vueReferentiel(); });
  v.querySelectorAll("[data-o]").forEach(b => b.onclick = () => { E.refOnglet = b.dataset.o; vueReferentiel(); });
  v.querySelectorAll(".puces [data-f]").forEach(b => b.onclick = () => { E.refFiltre = b.dataset.f; vueReferentiel(); });
  if ($("#rf-q")) $("#rf-q").oninput = ev => { E.refQ = ev.target.value; vueReferentiel(); $("#rf-q").focus(); $("#rf-q").setSelectionRange(99, 99); };
  const on = (id, f) => { const x = v.querySelector(id); if (x) x.onclick = f; };
  on("#rf-creer", () => { E.refSource = ""; actionRef({action: "creer_brouillon"}, "Brouillon créé : la révision publiée reste en service."); });
  on("#rf-ouvrir-b", async () => { E.refSource = ""; await chargerReferentiel(); vueReferentiel(); });
  on("#rf-voir-pub", async () => { E.refSource = "publie"; await chargerReferentiel(); vueReferentiel(); });
  on("#rf-abandon", () => confirmer("Supprimer le brouillon ?", "Le brouillon est retiré ; une copie est gardée (5 au plus) et peut être récupérée. La révision publiée n'est pas touchée.", "Supprimer le brouillon", () => actionRef({action: "abandonner"}, "Brouillon supprimé : copie gardée, récupérable.")));
  on("#rf-recuperer", () => {
    const noms = E.cycle.brouillons_supprimes || [];
    const lib = n => n.replace(/^brouillon-(\d{4})(\d{2})(\d{2})-(\d{2})(\d{2})(\d{2}).*$/, "supprimé le $3/$2/$1 à $4:$5:$6");
    modaleChoix("Récupérer un brouillon supprimé", "Copie", noms.map(n => [n, lib(n)]), noms[0], nom => actionRef({action: "recuperer_brouillon", nom}, "Brouillon récupéré."));
  });
  on("#rf-exp", () => telecharger("referentiel&source=publie"));
  on("#rf-exp-b", () => telecharger("referentiel&source=brouillon"));
  on("#rf-imp", modaleImportReferentiel);
  on("#rf-hist", () => { E.refEcran = "historique"; vueReferentiel(); });
  on("#rf-pub", () => { E.refEcran = "publication"; vueReferentiel(); });
  if (!t || !ed) return;
  on("#rf-type-mod", () => modaleTypeCatalogue(t));
  on("#rf-type-archive", () => confirmer(t.archive?'Réactiver ce type ?':'Archiver ce type ?',
    'Les ouvrages existants conservent leurs données. Le changement reste dans le brouillon jusqu’à sa publication.',
    t.archive?'Réactiver':'Archiver',()=>editionModeles({action:'archiver_type',code:t.code,archive:!t.archive},'Statut du type enregistré dans le brouillon.')));
  v.querySelectorAll(".rf-sig").forEach(b => b.onclick = () => modaleSignalRef(t, [...t.es, ...t.fonctionnelles].find(s => s.id === b.dataset.id)));
  v.querySelectorAll(".rf-sig-sup").forEach(b => b.onclick = () => confirmer(`Supprimer ${b.dataset.id} ?`, "Les ouvrages existants ne sont pas modifiés ; seuls les nouveaux l'ignoreront après publication.", "Supprimer",
    () => actionRef({action: "editer", modification: "supprimer_signal", cible: b.dataset.id}, "Signal supprimé du brouillon.")));
  on("#rf-add-es", () => modaleSignalRef(t, null, "ES"));
  on("#rf-add-f", () => modaleSignalRef(t, null, "TS"));
  v.querySelectorAll(".rf-reg").forEach(b => b.onclick = () => modaleRegleRef(t, t.regles.find(g => g.id === b.dataset.id)));
  v.querySelectorAll(".rf-reg-sup").forEach(b => b.onclick = () => confirmer(`Supprimer la règle ${b.dataset.id} ?`, "Les informations qu'elle proposait ne seront plus proposées aux nouveaux équipements.", "Supprimer",
    () => actionRef({action: "editer", modification: "supprimer_regle", cible: b.dataset.id}, "Règle supprimée du brouillon.")));
  on("#rf-add-r", () => modaleRegleRef(t, null));
  v.querySelectorAll(".rf-mval").forEach(b => b.onclick = () => editionModeles({action: "valider_modele", nom: b.dataset.n, valide: b.dataset.v === "1"}, "Statut du modèle modifié dans le brouillon."));
  v.querySelectorAll(".rf-msup").forEach(b => b.onclick = () => confirmer(`Supprimer le modèle « ${b.dataset.n} » ?`, "Les équipements déjà créés gardent leur copie.", "Supprimer", () => editionModeles({action: "supprimer_modele", nom: b.dataset.n}, "Modèle supprimé du brouillon.")));
  v.querySelectorAll(".rf-mdup").forEach(b => b.onclick = () => {
    const m = ouvrirModale(`<div class="boite-tete"><h2>Dupliquer « ${esc(b.dataset.n)} »</h2><p>La copie reçoit de nouvelles lignes et repasse « à valider » ; l'original n'est pas modifié.</p></div>
      <div class="boite-corps"><label>Nom du nouveau modèle</label><input id="m-nom" value="${esc(b.dataset.n)} (copie)"><div class="erreur-form" id="m-err"></div></div>
      <div class="boite-pied"><button data-fermer>Annuler</button><button class="prim" id="m-ok">Dupliquer</button></div>`);
    m.querySelector("#m-ok").onclick = async () => {
      try { await api("/api/referentiel/action", {action: "dupliquer_modele", nom: b.dataset.n, nouveau_nom: m.querySelector("#m-nom").value}); fermerModale(); toast("Modèle dupliqué dans le brouillon."); await chargerReferentiel(); vueReferentiel(); }
      catch (e) { m.querySelector("#m-err").textContent = e.message; }
    };
  });
  v.querySelectorAll(".rf-marc").forEach(b => b.onclick = () => editionModeles({action: "archiver_modele", nom: b.dataset.n, archive: b.dataset.a === "1"},
    b.dataset.a === "1" ? "Modèle archivé : plus proposé aux nouveaux équipements." : "Modèle désarchivé (à valider)."));
  const modele = n => t.modeles.find(m => m.nom === n);
  v.querySelectorAll(".rf-ladd").forEach(b => b.onclick = () => modaleLigne(E.ref.roles, E.ref.formats, null, "", champs => editionModeles({action: "ajouter_ligne", nom: b.dataset.n, champs}, "Ligne ajoutée au brouillon.")));
  v.querySelectorAll(".rf-lmod").forEach(b => b.onclick = () => { const l = modele(b.dataset.n).lignes.find(x => x.id === b.dataset.id);
    modaleLigne(E.ref.roles, E.ref.formats, l, "", champs => editionModeles({action: "modifier_ligne", nom: b.dataset.n, id: l.id, champs}, "Ligne modifiée dans le brouillon.")); });
  v.querySelectorAll(".rf-lsup").forEach(b => b.onclick = () => editionModeles({action: "supprimer_lignes", nom: b.dataset.n, ids: [b.dataset.id]}, "Ligne supprimée du brouillon."));
  on("#rf-madd", () => modaleSaisie(`Nouveau modèle pour ${t.code}`, "Nom du modèle", "", nom => editionModeles({action: "creer_modele", type: t.code, nom, depuis_catalogue: true}, "Modèle créé dans le brouillon.")));
}
function modaleSignalRef(t, s, famille) {
  const nouveau = !s, opt = t.options;
  const sel = (id, val, liste) => `<select id="${id}">${liste.map(x => `<option ${x === val ? "selected" : ""}>${esc(x)}</option>`).join("")}</select>`;
  const m = ouvrirModale(`<div class="boite-tete"><h2>${nouveau ? "Nouveau signal pour " + esc(t.code) : "Modifier " + esc(s.id)}</h2>
    <p>Modification du brouillon seulement. Les identifiants ne se renomment pas : supprimez puis recréez.</p></div>
    <div class="boite-corps"><div class="champs">
      ${nouveau ? `<label>Famille</label>${sel("s-fam", famille, ["ES", "TS", "TM", "TC", "TR", "RTR", "CP"])}<label>Code</label><input id="s-code" style="text-transform:uppercase" placeholder="ex. DEFIMP">` : ""}
      <label>Information</label><input id="s-info" value="${esc(s ? s.information : "")}">
      <label>Nature E/S</label>${sel("s-es", s ? s.es : (famille === "ES" ? "ET" : "Interne"), ["ET", "ST", "EA", "SA", "Interne"])}
      <label>Type logique</label>${sel("s-tl", s ? s.type_logique : "BOOL", ["BOOL", "EBOOL", "INT", "DINT", "REAL"])}
      <label>Présence</label>${sel("s-pres", s ? s.presence : "Option", ["Obligatoire", "Par défaut", "Option", "Règle"])}
      <label>Option</label><select id="s-opt"><option value="">—</option>${opt.map(o => `<option ${s && s.option === o ? "selected" : ""}>${esc(o)}</option>`).join("")}</select>
      <label>Alarme</label><label style="text-align:left"><input type="checkbox" id="s-al" ${s && s.alarme ? "checked" : ""}> alarme</label>
      <label>Source physique</label><input id="s-src" value="${esc(s ? s.source : "")}" placeholder="ex. ES_FDC_OUV">
      <label>Logique à programmer</label><textarea id="s-log" rows="3">${esc(s ? s.logique : "")}</textarea>
    </div><div class="erreur-form" id="m-err"></div></div>
    <div class="boite-pied"><button data-fermer>Annuler</button><button class="prim" id="m-ok">${nouveau ? "Ajouter au brouillon" : "Enregistrer dans le brouillon"}</button></div>`);
  const q = x => m.querySelector(x);
  q("#m-ok").onclick = async () => {
    const champs = {information: q("#s-info").value, es: q("#s-es").value, type_logique: q("#s-tl").value, presence: q("#s-pres").value,
                    option: q("#s-opt").value, alarme: q("#s-al").checked, source: q("#s-src").value, logique: q("#s-log").value};
    try {
      await api("/api/referentiel/cycle/action", nouveau ? {action: "editer", modification: "ajouter_signal", champs: {...champs, type: t.code, famille: q("#s-fam").value, code: q("#s-code").value}}
                                                       : {action: "editer", modification: "modifier_signal", cible: s.id, champs});
      fermerModale(); toast(nouveau ? "Signal ajouté au brouillon." : "Signal modifié dans le brouillon."); await chargerReferentiel(); vueReferentiel();
    } catch (e) { q("#m-err").textContent = e.message; }
  };
}
function modaleRegleRef(t, g) {
  const nouveau = !g;
  const m = ouvrirModale(`<div class="boite-tete"><h2>${nouveau ? "Nouvelle règle pour " + esc(t.code) : "Modifier la règle " + esc(g.id)}</h2>
    <p>Une règle « proposition » fait proposer des informations que l'automaticien retient ou écarte, équipement par équipement.</p></div>
    <div class="boite-corps"><div class="champs">
      ${nouveau ? `<label>Identifiant</label><input id="g-id" value="${esc(t.code)}-" style="text-transform:uppercase">` : ""}
      <label>Libellé</label><input id="g-lib" value="${esc(g ? g.libelle : "")}">
      <label>Si (toutes présentes, séparées par ;)</label><input id="g-si" value="${esc(g ? (g.si || []).join("; ") : "")}" placeholder="ES_FDC_OUV; ES_FDC_FER">
      <label>Propose (séparées par ;)</label><input id="g-pr" value="${esc(g ? (g.propose || []).join("; ") : "")}" placeholder="TS_DISC">
      <label>Mode</label><select id="g-mode"><option value="proposition" ${!g || g.mode !== "auto" ? "selected" : ""}>proposition (à décider)</option><option value="auto" ${g && g.mode === "auto" ? "selected" : ""}>automatique</option></select>
      <label>Logique à programmer</label><textarea id="g-log" rows="4">${esc(g ? g.logique : "")}</textarea>
    </div><div class="erreur-form" id="m-err"></div></div>
    <div class="boite-pied"><button data-fermer>Annuler</button><button class="prim" id="m-ok">Enregistrer dans le brouillon</button></div>`);
  const q = x => m.querySelector(x);
  q("#m-ok").onclick = async () => {
    const champs = {libelle: q("#g-lib").value, si: q("#g-si").value, propose: q("#g-pr").value, mode: q("#g-mode").value, logique: q("#g-log").value};
    try {
      await api("/api/referentiel/cycle/action", nouveau ? {action: "editer", modification: "ajouter_regle", champs: {...champs, id: q("#g-id").value, type: t.code}}
                                                       : {action: "editer", modification: "modifier_regle", cible: g.id, champs});
      fermerModale(); toast("Règle enregistrée dans le brouillon."); await chargerReferentiel(); vueReferentiel();
    } catch (e) { q("#m-err").textContent = e.message; }
  };
}
function modaleTypeCatalogue(t) {
  const m = ouvrirModale(`<div class="boite-tete"><h2>Modifier le type ${esc(t.code)}</h2></div>
    <div class="boite-corps"><div class="champs"><label>Désignation</label><input id="ty-des" value="${esc(t.designation)}">
      <label>Domaine</label><input id="ty-dom" value="${esc(t.domaine || "")}">
      <label>Options (séparées par ;)</label><input id="ty-opt" value="${esc(t.options.join("; "))}"></div><div class="erreur-form" id="m-err"></div></div>
    <div class="boite-pied"><button data-fermer>Annuler</button><button class="prim" id="m-ok">Enregistrer dans le brouillon</button></div>`);
  const q = x => m.querySelector(x);
  q("#m-ok").onclick = async () => {
    try { await api("/api/referentiel/cycle/action", {action: "editer", modification: "modifier_type", cible: t.code, champs: {designation: q("#ty-des").value, domaine: q("#ty-dom").value, options: q("#ty-opt").value}});
      fermerModale(); toast("Type modifié dans le brouillon."); await chargerReferentiel(); vueReferentiel(); }
    catch (e) { q("#m-err").textContent = e.message; }
  };
}
const ACTION_DIFF = {ajout: ["b-ok", "ajout"], suppression: ["b-err", "suppression"], modification: ["b-n", "modification"], ordre: ["b-n", "ordre"]};
const champsDiff = d => Object.entries(d.champs || {}).map(([c, [a, b]]) => `<div><small>${esc(c)}</small> <s>${esc(JSON.stringify(a))}</s> → <b>${esc(JSON.stringify(b))}</b></div>`).join("");
function tableDifferences(diffs) {
  return diffs.length ? `<table><thead><tr><th>Changement</th><th>Élément</th><th>Détail</th><th>Conséquence</th></tr></thead><tbody>${diffs.map(d => `<tr>
    <td><span class="badge ${(ACTION_DIFF[d.action] || ["b-n"])[0]}">${esc(d.action)}</span></td><td><small>${esc(d.objet)}</small><br><span class="mono">${esc(d.id)}</span></td>
    <td>${champsDiff(d)}</td><td class="justif">${esc(d.consequence || "")}</td></tr>`).join("")}</tbody></table>` : '<div class="vide-bloc">Aucune différence.</div>';
}
function vuePublicationReferentiel() {
  const c = E.cycle, b = c.brouillon, ctl = c.controles || {erreurs: [], alertes: []};
  $("#vue").innerHTML = `<section class="contenu publication-ref">
    <div class="fil"><button class="lien" id="rf-retour">Brouillon (basé sur R${String(b.base_revision).padStart(4, "0")})</button> › Contrôle et publication</div>
    <h1>Comparer la révision publiée et le brouillon, puis publier R${String(c.revision + 1).padStart(4, "0")}</h1>
    <div class="grille-pub"><div>
      <div class="bloc"><div class="bloc-tete"><h2>1. Contrôles du brouillon</h2><span class="aide">${ctl.erreurs.length} erreur(s) bloquante(s) · ${ctl.alertes.length} point(s) à arbitrer</span></div>
        <ul class="liste-controles">${ctl.erreurs.map(m => `<li class="c-err">${esc(m)}</li>`).join("")}
        ${ctl.erreurs.length ? "" : '<li class="c-ok">Structure, identifiants, sources des règles, types logiques : aucun blocage. Aucun paramètre d\'installation dans un modèle.</li>'}
        ${ctl.alertes.slice(0, 12).map(m => `<li class="c-al">${esc(m)}</li>`).join("")}${ctl.alertes.length > 12 ? `<li class="aide">… ${ctl.alertes.length - 12} autre(s)</li>` : ""}</ul></div>
      <div class="bloc"><div class="bloc-tete"><h2>2. Différences avec R${String(c.revision).padStart(4, "0")}</h2><span class="aide">${(c.differences || []).length} changement(s)</span></div>${tableDifferences(c.differences || [])}</div>
      <div class="bloc"><div class="bloc-tete"><h2>3. Conséquences sur les ouvrages</h2></div><p style="padding:0 14px">Aucun ouvrage n'est modifié à la publication. Chacun garde son référentiel figé ; sa fiche signalera la nouvelle révision et ne l'appliquera qu'après accord (équipements concernés à revalider, adresses conservées).</p></div>
    </div><aside>
      <div class="bloc formulaire-pub"><h2>4. Valider puis publier</h2>
        ${b.etat === "validé" ? '<p class="c-ok">Brouillon validé. Toute modification annule la validation.</p>' : `<button id="rf-valider" ${ctl.erreurs.length || b.perime ? "disabled" : ""}>Valider le brouillon</button>`}
        <label for="rf-motif">Motif de la révision (obligatoire)</label><textarea id="rf-motif" rows="3"></textarea>
        <label class="case"><input type="checkbox" id="rf-relu"> J'ai relu les différences et leurs conséquences sur les ouvrages.</label>
        <button class="prim" id="rf-publier" ${b.etat === "validé" ? "" : "disabled"}>Publier R${String(c.revision + 1).padStart(4, "0")}</button>
        <p class="aide">La publication est refusée si le brouillon a changé depuis sa validation (empreinte).</p></div>
      ${blocHistorique(c.revisions)}
    </aside></div></section>`;
  $("#rf-retour").onclick = () => { E.refEcran = ""; vueReferentiel(); };
  if ($("#rf-valider")) $("#rf-valider").onclick = () => actionRef({action: "valider"}, "Brouillon validé.");
  $("#rf-publier").onclick = () => {
    if (!$("#rf-motif").value.trim()) return toast("Indiquez le motif de la révision.", true);
    if (!$("#rf-relu").checked) return toast("Confirmez avoir relu les différences et leurs conséquences.", true);
    confirmer(`Publier R${String(c.revision + 1).padStart(4, "0")} ?`, "La révision publiée actuelle est archivée et reste consultable. Les ouvrages ne changent pas.", "Publier",
      async () => { await agir(api("/api/referentiel/cycle/action", {action: "publier", motif: $("#rf-motif").value, empreinte: b.empreinte_validee}), "Révision publiée.");
        E.refEcran = ""; E.refSource = ""; await chargerReferentiel(); vueReferentiel(); });
  };
  brancherHistorique();
}
function blocHistorique(revs) {
  return `<div class="bloc"><div class="bloc-tete"><h2>Historique des révisions</h2></div>
    ${revs.map(r => `<div class="rev"><b class="mono">R${String(r.numero).padStart(4, "0")}</b><span>${esc(r.motif)}<br><small>${esc(r.date)}${r.auteur ? " · " + esc(r.auteur) : ""}</small></span>
      <span class="droite"><button class="lien rf-rexp" data-n="${r.numero}">Excel</button><button class="lien rf-rest" data-n="${r.numero}">Restaurer en brouillon</button></span></div>`).join("") || '<div class="vide-bloc">Aucune révision : la première est créée avec le premier brouillon.</div>'}
    <p class="aide" style="padding:0 14px 10px">Restaurer crée un nouveau brouillon : l'historique n'est jamais réécrit.</p></div>`;
}
function brancherHistorique() {
  document.querySelectorAll(".rf-rexp").forEach(b => b.onclick = () => telecharger("referentiel&source=R" + b.dataset.n));
  document.querySelectorAll(".rf-rest").forEach(b => b.onclick = () => confirmer(`Restaurer R${String(b.dataset.n).padStart(4, "0")} en brouillon ?`, "Un nouveau brouillon reprend son contenu ; il faudra le contrôler et le publier.", "Restaurer",
    async () => { await agir(api("/api/referentiel/cycle/action", {action: "restaurer", numero: Number(b.dataset.n)}), "Brouillon créé à partir de la révision."); E.refEcran = ""; E.refSource = ""; await chargerReferentiel(); vueReferentiel(); }));
}
function vueHistoriqueReferentiel() {
  $("#vue").innerHTML = `<section class="contenu"><div class="fil"><button class="lien" id="rf-retour">Référentiel</button> › Historique</div><h1>Historique des révisions</h1>
    ${E.cycle.brouillon ? '<div class="avert">Un brouillon est en cours : terminez-le ou abandonnez-le avant une restauration.</div>' : ""}${blocHistorique(E.cycle.revisions)}</section>`;
  $("#rf-retour").onclick = () => { E.refEcran = ""; vueReferentiel(); };
  brancherHistorique();
}
/* ------------------------------------------------------------------ étape 2 : liste des E/S */
/* ------------------------------------------------------------------ étape 2 : liste des E/S (contenu) */
// Pastille d'indicateur cliquable (filtre) commune aux écrans E/S et Matériel.
function pastille(cle, val, lib, grav, filtre) {
  return `<button type="button" class="chiffre cliquable ${filtre === cle ? "on" : ""}" data-f="${esc(cle)}"><b class="${grav || ""}">${val}</b><span>${esc(lib)}</span></button>`;
}
function texteSens(p) {
  if (!["EA", "SA"].includes(p.point)) return esc(p.sens);
  const a = p.analogique;
  return a ? `${esc(a.signal_min)}–${esc(a.signal_max)} mA → ${esc(a.phys_min)}–${esc(a.phys_max)} ${esc(a.unite)}` : '<span class="vide">échelle à renseigner</span>';
}
// Validation groupée (contenu à l'étape 2, voie à l'étape 3) avec confirmation.
async function validerES(points, niveau, valide = true) {
  if (!points.length) return;
  if (niveau === "contenu" && valide) {
    const errones = points.filter(erreurContenuES);
    if (errones.length) { toast(`${errones.length} E/S ont un sens de contact ou une échelle manquants : corrigez-les avant validation.`, true); return; }
  }
  const r = await agir(api("/api/es/valider", {niveau, valide, paires: points.map(p => ({ident_eq: p.ident_eq, cle: p.cle}))}));
  toast(`${r.n} E/S ${valide ? "validée(s)" : "repassée(s) à valider"}.`);
  if (E.esSelection instanceof Set) E.esSelection.clear();
  E.vue === "materiel" ? rechargerMateriel() : rechargerES();
}
// Étape 2 — la nature, le sens, l'échelle et les désignations précèdent l'affectation des voies.
// La liste reste une vue des points réels fournis par /api/es : aucune adresse n'est calculée ici.
const cleVueES = p => `${p.ident_eq}|${p.cle}`;
const typesTOR = new Set(["ET", "ST"]);
const typesANA = new Set(["EA", "SA"]);
function erreurContenuES(p) {
  if (typesTOR.has(p.point) && !String(p.sens || "").trim()) return "Sens du contact non renseigné";
  if (typesANA.has(p.point) && p.raccordement !== "Communication" && !p.analogique)
    return "Échelle analogique non renseignée";
  return "";
}
function etatContenuES(p) {
  const erreur = erreurContenuES(p);
  if (erreur) return `<span class="badge b-err" title="${esc(erreur)}">erreur</span>`;
  return p.contenu_valide ? '<span class="badge b-ok">validé</span>' : '<span class="badge b-al">à valider</span>';
}
function localisationES(p) {
  if (p.raccordement === "Communication") return "Point par communication";
  return p.adresse ? `${esc(p.module || "Carte non précisée")} · voie ${esc(p.voie || "?")} · ${esc(p.adresse)}`
                   : "À l’étape Matériel";
}
function filtreVueES(points) {
  const q = (E.rechercheES || "").trim().toLocaleLowerCase("fr");
  return points.filter(p => (!q || [p.nom, p.pcf, p.cle, p.designation, p.commentaire, p.information, p.uf]
      .some(x => String(x || "").toLocaleLowerCase("fr").includes(q)))
    && (!E.filtreES || (E.filtreES === "VAL" ? !p.contenu_valide : E.filtreES === "OK" ? p.contenu_valide
      : E.filtreES === "ERR" ? !!erreurContenuES(p) : p.point === E.filtreES))
    && (!E.esUF || (p.uf || "Sans UF") === E.esUF)
    && (!E.esEquip || p.pcf === E.esEquip));
}
function vueES() {
  const d = E.es, b = d.bilan, tous = d.points;
  if (!(E.esSelection instanceof Set)) E.esSelection = new Set();
  const visibles = filtreVueES(tous);
  const eqs = [...new Map(tous.filter(p => !E.esUF || (p.uf || "Sans UF") === E.esUF)
    .map(p => [p.pcf, {pcf: p.pcf, uf: p.uf || "Sans UF"}])).values()];
  const ufs = [...new Set(tous.map(p => p.uf || "Sans UF"))].sort((a, b) => a.localeCompare(b));
  const actif = E.esSelectionPoint ? tous.find(p => cleVueES(p) === E.esSelectionPoint) : null;
  const p = actif && (visibles.includes(actif) || E.esPanneauOuvert) ? actif : null;
  const nb = n => b.par_point[n] || 0;
  const indices = new Map(tous.map((p, i) => [cleVueES(p), i]));
  const invalides = tous.filter(x => !x.contenu_valide).length;
  const erreurs = tous.filter(erreurContenuES).length;
  const compteurs = [
    ["ET", nb("ET"), "Entrées TOR", ""], ["ST", nb("ST"), "Sorties TOR", ""],
    ["EA", nb("EA"), "Entrées ANA", ""], ["SA", nb("SA"), "Sorties ANA", ""],
    ["VAL", invalides, "À valider", invalides ? "al" : "ok"],
    ["OK", tous.length - invalides, "Validées", "ok"]
  ].filter(x => x[1] > 0);
  // Le compteur d'erreurs est distinct du compteur "à valider" : la nature est une information fonctionnelle.
  if (erreurs) compteurs.push(["ERR", erreurs, "Erreurs", "err"]);
  const a = p && p.analogique;
  const analogique = p && typesANA.has(p.point);
  $("#vue").innerHTML = `<section class="contenu es-page">
    <div class="titre"><div><div class="fil">Ouvrage › Étape 2 / 5</div><h1>Liste des E/S physiques</h1>
      <div class="sous">Contrôlez chaque signal avant la configuration du matériel ; la voie ne se renseigne pas ici.</div></div>
      <span class="es-progression ${invalides ? "al" : "ok"}">${invalides ? `${invalides} E/S à valider` : "Contenu validé"}</span></div>
    <div class="es-ruban" aria-label="Outils de la liste des E/S">
      <div class="es-ruban-onglets"><span class="on">Général</span><span>Affichage</span><span>Outils</span></div>
      <div class="es-ruban-actions"><div class="es-ruban-groupe"><button type="button" id="x-val-tout" ${visibles.some(x => !x.contenu_valide) ? "" : "disabled"} title="Valider les E/S visibles après contrôle">${V31.icon("check",14)} Valider les affichées</button>
        <button type="button" id="x-val" class="prim" disabled>${V31.icon("check",14)} Valider la sélection</button><span>Validation du contenu</span></div>
        <div class="es-ruban-groupe"><button type="button" id="es-export">⇩ Exporter la liste</button><span>Échanges de données</span></div>
        <div class="es-ruban-groupe"><button type="button" data-nav="#/materiel" ${invalides ? "disabled title=\"Validez le contenu avant le calcul du matériel\"" : ""}>▣ Matériel</button><span>Étape suivante</span></div></div>
    </div>
    <div class="es-compteurs" role="group" aria-label="Filtres par nature et par validation">
      ${compteurs.map(([code, nb, label, grav]) => pastille(code, nb, label, grav, E.filtreES)).join("")}</div>
    ${d.sans_es.length ? `<div class="avert">${d.sans_es.length} équipement(s) sans E/S physique (ex. ${esc(d.sans_es.slice(0, 4).join(", "))}).</div>` : ""}
    <div class="es-filtres"><label class="es-recherche">Rechercher<input id="x-q" type="search" placeholder="Repère, nom automate, clé, désignation…" value="${esc(E.rechercheES || "")}" aria-label="Rechercher un signal E/S"></label>
      <label>Unité fonctionnelle<select id="x-uf" data-uf="1" aria-label="Filtrer par unité fonctionnelle"><option value="">Toutes les UF</option>
        ${ufs.map(x => `<option value="${esc(x)}" ${E.esUF === x ? "selected" : ""}>${esc(x)}</option>`).join("")}</select></label>
      <label>Équipement<select id="x-equip" aria-label="Filtrer par équipement"><option value="">Tous les équipements</option>
        ${eqs.map(x => `<option value="${esc(x.pcf)}" ${E.esEquip === x.pcf ? "selected" : ""}>${esc(x.pcf)}</option>`).join("")}</select></label>
      <button id="es-effacer" type="button" class="lien">Effacer les filtres</button>
    </div>
    <div class="es-corps"><div class="bloc es-table"><div class="bloc-tete es-table-tete"><h2>Points physiques</h2><span class="aide">${visibles.length} / ${tous.length} E/S · ${invalides} à valider</span>
       ${p ? '<button type="button" id="es-detail-toggle">' + (E.esPanneauOuvert ? 'Masquer le détail' : 'Afficher le détail') + '</button>' : ''}</div>
       <div class="es-scroll"><table class="t-es" aria-label="Liste des E/S physiques"><thead><tr>
       <th><input type="checkbox" id="x-coche-tout" aria-label="Sélectionner les E/S affichées"></th>
       <th>Équipement / variable automate</th><th>Point</th><th>Désignation</th><th>Sens / Échelle</th><th>Raccordement</th><th>Voie</th><th>État</th></tr></thead><tbody>
       ${visibles.map(x => {const sid = cleVueES(x), i = indices.get(sid);return `<tr data-i="${i}" role="button" tabindex="0" aria-label="Ouvrir le détail de ${esc(x.nom)}" class="es-ligne ${p && p === x ? "es-active" : ""}">
         <td><input type="checkbox" class="x-coche" value="${i}" ${E.esSelection.has(sid) ? "checked" : ""} aria-label="Sélectionner ${esc(x.nom)}"></td>
         <td><strong class="mono es-pc">${esc(x.pcf)}</strong><small class="mono es-nom">${esc(x.nom)}</small><small class="mono es-code">${esc(x.cle)}</small></td>
         <td><span class="tag p-${esc(x.point)}">${esc(x.point)}</span></td>
         <td>${esc(x.designation || x.commentaire || x.information)}</td><td>${texteSens(x)}</td>
         <td>${esc(x.raccordement === "Communication" ? "Communication" : "Câblé")}</td><td class="es-voie">${localisationES(x)}</td>
         <td>${etatContenuES(x)}</td></tr>`;}).join("")}</tbody></table>
       ${!visibles.length ? '<div class="vide-bloc">Aucune E/S correspondant aux filtres.</div>' : ''}</div></div>
    ${p && E.esPanneauOuvert ? `<aside class="es-panneau" aria-label="Détail du signal sélectionné"><div class="es-panneau-tete"><div><small>${esc(p.pcf)} · ${esc(p.cle)}</small><h2 class="mono">${esc(p.nom)}</h2></div>
       <button type="button" id="es-fermer-detail" aria-label="Fermer le panneau">${V31.icon("close",14)}</button></div>
       <form id="es-form" class="es-form"><div class="es-form-meta"><span class="tag p-${esc(p.point)}">${esc(p.point)}</span> ${etatContenuES(p)}</div>
       <label>Désignation<input id="es-designation" value="${esc(p.designation || "")}" placeholder="${esc(p.commentaire || p.information)}" maxlength="200"></label>
       ${typesTOR.has(p.point) ? `<label>Sens du contact<input id="es-sens" value="${esc(p.sens || "")}" placeholder="ex. 1 = Ouvert"></label>` : ""}
       ${analogique ? `<fieldset class="es-echelle"><legend>Échelle analogique (mA → unité physique)</legend>
         <div><label>Courant min. (mA)<input id="es-signal-min" inputmode="decimal" type="number" step="any" value="${esc(a?.signal_min ?? "")}" placeholder="4"></label>
              <label>Courant max. (mA)<input id="es-signal-max" inputmode="decimal" type="number" step="any" value="${esc(a?.signal_max ?? "")}" placeholder="20"></label></div>
         <div><label>Physique min.<input id="es-phys-min" inputmode="decimal" type="number" step="any" value="${esc(a?.phys_min ?? "")}"></label>
              <label>Physique max.<input id="es-phys-max" inputmode="decimal" type="number" step="any" value="${esc(a?.phys_max ?? "")}"></label></div>
         <label>Unité<input id="es-unite" value="${esc(a?.unite || "")}" maxlength="24" placeholder="m³/h, bar…"></label>
         <p>Valeurs brutes du module : renseignées dans le paramétrage de l’équipement, conservées ici sans modification.</p></fieldset>` : ""}
       <label>Raccordement<select id="es-rac"><option value="Câblé" ${p.raccordement === "Câblé" ? "selected" : ""}>Câblé</option><option value="Communication" ${p.raccordement === "Communication" ? "selected" : ""}>Communication</option></select></label>
       <label>Commentaire<textarea id="es-note" rows="3" maxlength="500" placeholder="Note de conception…">${esc(p.note || "")}</textarea></label>
       <div class="es-lecture-seule"><b>Voie / Adresse (lecture seule)</b><span>${localisationES(p)}</span></div>
       <div class="erreur-form" id="es-erreur" aria-live="polite"></div><div class="es-actions">
       <button type="button" id="es-enregistrer">Enregistrer</button><button type="submit" class="prim" id="es-valider">Valider le contenu</button>
       ${p.contenu_valide ? '<button type="button" id="es-invalider" class="lien">Repasser à valider</button>' : ''}</div></form></aside>` : ""}</div></section>`;
  brancherVueES(visibles, p);
}
function brancherVueES(visibles, actif) {
  const d = E.es;
  const rerendre = () => vueES();
  const avantPerteES = () => {
    if (!E.esFormDirty) return true;
    if (!window.confirm("Les modifications du point E/S ne sont pas enregistrées. Les abandonner ?")) return false;
    E.esFormDirty = false;
    return true;
  };
  const selectionActuelle = () => visibles.filter(p => E.esSelection.has(cleVueES(p)));
  const majBouton = () => {
    const n = selectionActuelle().length, b = $("#x-val");
    b.disabled = !n || !selectionActuelle().some(p => !p.contenu_valide);
    b.textContent = n ? `Valider la sélection (${n})` : "Valider la sélection";
    const tout = $("#x-coche-tout");
    if (tout) { tout.checked = !!visibles.length && n === visibles.length; tout.indeterminate = n > 0 && n < visibles.length; }
  };
  const filtrer = () => {
    E.esSelection.clear();
    if (E.esSelectionPoint && !filtreVueES(d.points).some(p => cleVueES(p) === E.esSelectionPoint)) {
      E.esSelectionPoint = "";
      E.esPanneauOuvert = false;
    }
    rerendre();
  };
  const texte = $("#x-q");
  texte.oninput = ev => { if (!avantPerteES()) { ev.target.value = E.rechercheES || ""; return; }
    const pos = ev.target.selectionStart; E.rechercheES = ev.target.value; filtrer();
    const n = $("#x-q"); n.focus(); n.setSelectionRange(pos, pos); };
  $("#x-uf").onchange = ev => { if (!avantPerteES()) { ev.target.value = E.esUF || ""; return; } E.esUF = ev.target.value; E.esEquip = ""; filtrer(); };
  $("#x-equip").onchange = ev => { if (!avantPerteES()) { ev.target.value = E.esEquip || ""; return; } E.esEquip = ev.target.value; filtrer(); };
  $("#es-effacer").onclick = () => { if (!avantPerteES()) return; E.rechercheES = ""; E.esUF = ""; E.esEquip = ""; E.filtreES = ""; filtrer(); };
  document.querySelectorAll(".es-compteurs [data-f]").forEach(x => x.onclick = () => {
    if (!avantPerteES()) return;
    E.filtreES = E.filtreES === x.dataset.f ? "" : x.dataset.f; filtrer();
  });
  document.querySelectorAll(".es-ligne").forEach(tr => {
    const p = d.points[+tr.dataset.i], ouvrir = () => { if (!avantPerteES()) return; E.esSelectionPoint = cleVueES(p); E.esPanneauOuvert = true; rerendre(); $("#es-designation")?.focus(); };
    tr.onclick = ev => { if (!ev.target.closest('input[type="checkbox"]')) ouvrir(); };
    tr.onkeydown = ev => { if (ev.target === tr && (ev.key === "Enter" || ev.key === " ")) { ev.preventDefault(); ouvrir(); } };
  });
  document.querySelectorAll(".x-coche").forEach(c => {
    c.onclick = ev => ev.stopPropagation();
    c.onchange = ev => { const p = d.points[+ev.target.value]; if (ev.target.checked) E.esSelection.add(cleVueES(p));
                       else E.esSelection.delete(cleVueES(p)); majBouton(); };
  });
  $("#x-coche-tout").onchange = ev => { visibles.forEach(p => {
    if (ev.target.checked) E.esSelection.add(cleVueES(p)); else E.esSelection.delete(cleVueES(p));
  }); document.querySelectorAll(".x-coche").forEach(x => x.checked = ev.target.checked); majBouton(); };
  $("#x-val").onclick = () => {
    const points = selectionActuelle().filter(p => !p.contenu_valide);
    confirmer(`Valider ${points.length} E/S sélectionnées ?`, "Vous attestez leur nature, leur sens, leur échelle et leur désignation.", "Valider", () => validerES(points, "contenu"));
  };
  $("#x-val-tout").onclick = () => {
    const points = visibles.filter(p => !p.contenu_valide);
    confirmer(`Valider ${points.length} E/S affichées ?`, "Seules les E/S visibles après filtrage seront validées. Vérifiez leur contenu.", "Valider", () => validerES(points, "contenu"));
  };
  $("#es-export").onclick = () => telecharger("liste_es");
  if ($("#es-detail-toggle")) $("#es-detail-toggle").onclick = () => { E.esPanneauOuvert = !E.esPanneauOuvert; rerendre(); };
  if ($("#es-fermer-detail")) $("#es-fermer-detail").onclick = () => { if (!avantPerteES()) return; E.esPanneauOuvert = false; rerendre(); };
  if (actif && E.esPanneauOuvert) {
    $("#es-form").addEventListener("input", () => { E.esFormDirty = true; });
    $("#es-form").addEventListener("change", () => { E.esFormDirty = true; });
    const demander = async (validation) => {
      const val = id => $("#" + id)?.value ?? "";
      const données = {ident_eq: actif.ident_eq, cle: actif.cle, designation: val("es-designation"),
        note: val("es-note"), raccordement: val("es-rac")};
      if (typesTOR.has(actif.point)) données.sens = val("es-sens");
      if (typesANA.has(actif.point)) {
        const champs = ["es-signal-min", "es-signal-max", "es-phys-min", "es-phys-max", "es-unite"];
        const remplis = champs.filter(x => String(val(x)).trim() !== "").length;
        if (remplis && remplis !== champs.length) { $("#es-erreur").textContent = "Renseignez les cinq champs de l’échelle analogique."; return; }
        if (remplis) données.analogique = {signal_min: val("es-signal-min"), signal_max: val("es-signal-max"),
          phys_min: val("es-phys-min"), phys_max: val("es-phys-max"), unite: val("es-unite"),
          ...(actif.analogique?.brut_min !== undefined ? {brut_min: actif.analogique.brut_min, brut_max: actif.analogique.brut_max} : {})};
        if (validation && données.raccordement !== "Communication" && !remplis && !actif.analogique) {
          $("#es-erreur").textContent = "L’échelle analogique doit être renseignée avant validation."; return;
        }
      }
      if (validation && typesTOR.has(actif.point) && !données.sens.trim()) {
        $("#es-erreur").textContent = "Précisez le sens du contact avant validation."; return;
      }
      if (validation && !données.designation.trim() && !String(actif.commentaire || actif.information).trim()) {
        $("#es-erreur").textContent = "Précisez la désignation avant validation."; return;
      }
      if (actif.adresse && données.raccordement !== actif.raccordement &&
          !window.confirm("Changer le raccordement peut libérer une adresse ou une voie déjà affectée. Confirmer ?")) return;
      if (validation) données.valider_contenu = true;
      const boutons = [$("#es-enregistrer"), $("#es-valider")]; boutons.forEach(x => x.disabled = true);
      try { await api("/api/es/definir", données); toast(validation ? "Contenu validé." : "Contenu enregistré : à valider.");
            E.esFormDirty = false; E.esSelection.clear(); await rechargerES(); }
      catch (e) { $("#es-erreur").textContent = e.message; boutons.forEach(x => x.disabled = false); }
    };
    $("#es-form").onsubmit = ev => { ev.preventDefault(); demander(true); };
    $("#es-enregistrer").onclick = () => demander(false);
    if ($("#es-invalider")) $("#es-invalider").onclick = () => { if (avantPerteES()) validerES([actif], "contenu", false); };
  }
  majBouton();
}

// Recherche, filtres, sélection et validation : communs aux tableaux des étapes 2 et 3.
function brancherListeES(pts, niveau) {
  const d = E.es, vue = niveau === "contenu" ? vueES : vueMateriel, fait = p => niveau === "contenu" ? p.contenu_valide : p.validee;
  $("#x-q").oninput = ev => { E.rechercheES = ev.target.value; vue(); $("#x-q").focus(); $("#x-q").setSelectionRange(99, 99); };
  document.querySelectorAll("#vue [data-f]").forEach(x => x.onclick = () => { E.filtreES = E.filtreES === x.dataset.f ? "" : x.dataset.f; vue(); });
  if ($("#x-tout")) $("#x-tout").onclick = () => { E.filtreES = ""; vue(); };
  const coches = () => [...document.querySelectorAll(".x-coche:checked")].map(x => d.points[+x.value]);
  const maj = () => { const n = coches().length; $("#x-val").disabled = !n; $("#x-val").textContent = n ? `Valider la sélection (${n})` : "Valider la sélection"; };
  document.querySelectorAll(".x-coche").forEach(x => { x.onchange = maj; x.onclick = ev => ev.stopPropagation(); });
  if ($("#x-coche-tout")) $("#x-coche-tout").onchange = ev => { document.querySelectorAll(".x-coche").forEach(x => x.checked = ev.target.checked); maj(); };
  $("#x-val").onclick = () => validerES(coches(), niveau);
  $("#x-val-tout").onclick = () => { const a = pts.filter(p => !fait(p) && (niveau === "contenu" || p.adresse));
    confirmer(`Valider ${a.length} E/S ?`, niveau === "contenu" ? "Vous attestez que leur nature, leur sens et leur désignation correspondent à l'installation prévue."
      : "Vous attestez leur carte, leur voie et leur adresse. Une E/S validée ne sera plus déplacée.", "Valider", () => validerES(a, niveau)); };
  document.querySelectorAll("#vue tr[data-i]").forEach(tr => tr.onclick = ev => { if (!ev.target.closest("input")) modaleES(d.points[+tr.dataset.i], niveau); });
}

/* ------------------------------------------------------------------ étape 3 : matériel */
function racksAffiches(m, modules) {
  // Racks retenus ; à défaut (cartes déclarées à la main), racks déduits des cartes.
  if (m.racks && m.racks.length) return m.racks;
  const parRack = {};
  modules.forEach(x => { const [r, pos] = x.module.split(".").map(Number); parRack[r] = Math.max(parRack[r] ?? 0, pos + 1); });
  return Object.entries(parRack).map(([r, n]) => ({numero: +r, reference: "rack déclaré", positions: n, cpu: []}));
}
function vueRack(rack, modules, plusieurs) {
  const cases = [];
  const occ = Object.fromEntries((rack.occupation || []).map(o => [o.position, o]));
  const poste = String(rack.reference).startsWith("S4W");
  if (!poste && rack.alimentation !== undefined) {
    const choisie = rack.alimentation && !/à choisir/.test(rack.alimentation);
    cases.push(`<div class="emplacement alim ${choisie ? "" : "a-choisir"}" title="Emplacement CPS : alimentation"><span class="pos">CPS</span><b>${esc(choisie ? rack.alimentation : "Alimentation")}</b><small>${choisie ? "alimentation" : "à choisir"}</small></div>`);
  }
  for (let pos = 0; pos < rack.positions; pos++) {
    const carte = modules.find(x => x.module === `${rack.numero}.${pos}`);
    const o = occ[pos];
    if (o) { const role = o.role === "processeur" ? "Processeur" : "Communication";
      cases.push(`<div class="emplacement ${o.role === "processeur" ? "cpu" : "com"} ${/à choisir/.test(o.reference) ? "a-choisir" : ""}" title="Emplacement ${pos} : ${role.toLowerCase()}"><span class="pos">${pos}</span><b>${esc(/à choisir/.test(o.reference) ? role : o.reference)}</b><small>${/à choisir/.test(o.reference) ? "à choisir" : role.toLowerCase()}</small></div>`); continue; }
    if (rack.cpu.includes(pos)) { cases.push(`<div class="emplacement cpu" title="Position ${pos} : processeur"><span class="pos">${pos}</span><b>CPU</b></div>`); continue; }
    if (!carte) { cases.push(`<div class="emplacement libre" title="Position ${pos} libre"><span class="pos">${pos}</span><span>libre</span></div>`); continue; }
    const taux = carte.voies ? carte.occupees / carte.voies : 0;
    const etat = carte.occupees > carte.voies ? "err" : carte.sous_seuil && carte.occupees ? "al" : "ok";
    cases.push(`<button type="button" class="emplacement carte n-${carte.nature}" data-carte="${esc(carte.module)}" title="${esc(carte.reference)} — ${carte.occupees}/${carte.voies} voies occupées, réserve ${carte.reserve}">
      <span class="pos">${pos}</span><span class="tag p-${carte.nature}">${carte.nature}</span><b>${esc(carte.reference || "carte " + carte.nature)}</b>
      <span class="jauge ${etat}"><i style="width:${Math.min(100, Math.round(taux * 100))}%"></i></span><small>${carte.occupees}/${carte.voies} voies · réserve ${Math.round(carte.taux * 100)} %</small></button>`);
  }
  if (!poste && plusieurs) cases.push(`<div class="emplacement ext" title="Emplacement XBE : module d'extension de rack"><span class="pos">XBE</span><b>BMX XBE 1000</b><small>extension</small></div>`);
  return `<div class="rack"><div class="rack-tete"><b>${poste ? "Poste de télégestion" : "Rack " + rack.numero}</b><span>${esc(rack.reference)} · ${poste ? `voies intégrées + ${Math.max(0, modules.filter(x => x.reference.startsWith("Module")).length)} module(s) d'extension` : `${rack.positions} positions${rack.numero === 0 ? " · rack local" : " · extension"}`}</span></div>
    <div class="rack-corps" style="grid-template-columns:repeat(${cases.length},minmax(96px,1fr))">${cases.join("")}</div></div>`;
}
// Composition de l'automate (M340 / M580) : alimentation, processeur, communication, carte par nature.
function blocComposition(m) {
  if (!["M340", "M580"].includes(m.plateforme)) return "";
  const c = m.config || {}, cartes = c.cartes || {};
  const opt = (liste, val, vide) => `<option value="">${vide}</option>` + liste.map(x => `<option value="${esc(x.reference)}" ${x.reference === val ? "selected" : ""}>${esc(x.reference)} — ${esc(x.description || ((x.entree || "") + (x.puissance_w ? ", " + x.puissance_w + " W" : "") + (x.redondante ? ", redondante" : "")))}</option>`).join("");
  const parNature = n => m.cartes_catalogue.filter(x => x.nature === n);
  const nat = {ET: "Entrées TOR", ST: "Sorties TOR", EA: "Entrées analogiques", SA: "Sorties analogiques"};
  return `<div class="bloc"><div class="bloc-tete"><h2>Composition de l'automate</h2><span class="aide">vos choix ; ce qui n'est pas choisi reste « à choisir », jamais deviné</span></div>
    <div class="grille-compo">
      <label>Alimentation (emplacement CPS)<select data-cfg="alimentation">${opt(m.alimentations || [], c.alimentation, "— à choisir —")}</select></label>
      <label>Processeur<select data-cfg="processeur">${opt(m.processeurs || [], c.processeur, "— d'après la fiche ouvrage —")}</select></label>
      <fieldset><legend>Modules de communication</legend>${(m.communications || []).length ? m.communications.map(x => `<label class="case"><input type="checkbox" data-cfg-com value="${esc(x.reference)}" ${(c.communication || []).includes(x.reference) ? "checked" : ""}> <span class="mono">${esc(x.reference)}</span> <small>${esc(x.description)}</small></label>`).join("") : '<small>Aucun module décrit pour cette gamme.</small>'}</fieldset>
      ${["ET", "ST", "EA", "SA"].map(n => `<label>${nat[n]}<select data-cfg-carte="${n}"><option value="">Selon la densité choisie</option>${parNature(n).map(x => `<option value="${esc(x.reference)}" ${cartes[n] === x.reference ? "selected" : ""}>${esc(x.reference)} — ${esc(x.description)}</option>`).join("")}</select></label>`).join("")}
    </div>
    <details class="catalogue-cartes"><summary>Catalogue des cartes (${m.cartes_catalogue.length} + ${(m.cartes_speciales || []).length} spéciales)</summary>
      <table><thead><tr><th>Référence</th><th>Nature</th><th>Voies</th><th>Signal</th><th>Raccordement</th></tr></thead><tbody>
      ${m.cartes_catalogue.map(x => `<tr><td class="mono">${esc(x.reference)}</td><td>${esc(x.nature)}</td><td>${x.voies}</td><td>${esc(x.signal || x.description)}</td><td>${esc(x.raccordement || "")}${/à confirmer/.test(x.source || "") ? ' <span class="badge b-al">à confirmer</span>' : ""}</td></tr>`).join("")}
      ${(m.cartes_speciales || []).map(x => `<tr><td class="mono">${esc(x.reference)}</td><td>mixte / comptage</td><td>—</td><td>${esc(x.description)}</td><td>${esc(x.raccordement || "")}</td></tr>`).join("")}</tbody></table>
      <p class="aide-bloc">${esc(m.remarque_speciales || "")}</p></details></div>`;
}
function blocNomenclature(m) {
  if (!(m.nomenclature || []).length) return "";
  return `<div class="bloc"><div class="bloc-tete"><h2>Nomenclature de commande</h2><span class="aide">matériel retenu · références à confirmer à la commande</span><div class="droite"><button id="m-nomenclature">Exporter (Excel)</button></div></div>
    <table><thead><tr><th>Référence</th><th>Désignation</th><th class="num">Quantité</th><th>Rôle</th></tr></thead><tbody>
    ${m.nomenclature.map(x => `<tr><td class="mono">${esc(x.reference)}</td><td>${esc(x.designation)}</td><td class="num">${x.quantite}</td><td>${esc(x.role)}</td></tr>`).join("")}</tbody></table></div>`;
}
function liaisonsComposition() {
  const envoyer = corps => agir(api("/api/materiel/action", {action: "config", ...corps}), "Choix enregistré : recalculez le matériel pour l'appliquer.").then(rechargerMateriel);
  document.querySelectorAll("[data-cfg]").forEach(x => x.onchange = () => envoyer({[x.dataset.cfg]: x.value}));
  document.querySelectorAll("[data-cfg-com]").forEach(x => x.onchange = () => envoyer({communication: [...document.querySelectorAll("[data-cfg-com]:checked")].map(y => y.value)}));
  document.querySelectorAll("[data-cfg-carte]").forEach(x => x.onchange = () => {
    const cartes = {}; document.querySelectorAll("[data-cfg-carte]").forEach(y => { if (y.value) cartes[y.dataset.cfgCarte] = y.value; });
    envoyer({cartes});
  });
  if ($("#m-nomenclature")) $("#m-nomenclature").onclick = () => telecharger("nomenclature");
}
// Îlot Advantys STB : composition dans l'ordre du logiciel Advantys (emplacement / nœud) et image d'E/S.
function blocIlotsSTB(prop) {
  return prop.racks.map(r => {
    const img = Object.fromEntries((r.image_es || []).map(x => [x.noeud, x]));
    const regs = x => !x ? "—" : !x.connu ? "format d'image non documenté" : [x.entree.length ? "entrées " + x.entree[0] + (x.entree.length > 1 ? "–" + x.entree[x.entree.length - 1] : "") : "", x.sortie.length ? "sorties " + x.sortie[0] + (x.sortie.length > 1 ? "–" + x.sortie[x.sortie.length - 1] : "") : ""].filter(Boolean).join(" · ") || "aucun registre";
    return `<div class="bloc"><div class="bloc-tete"><h2>Îlot ${r.numero} — ${esc(r.nim)}</h2><span class="aide">à saisir dans Advantys dans cet ordre, puis à télécharger dans le NIM</span></div>
      <table><thead><tr><th>Emplacement / nœud</th><th>Référence</th><th>Rôle</th><th>Embase</th><th>Registres Modbus (image d'E/S)</th></tr></thead><tbody>
      ${(r.composition || []).map(c => `<tr><td class="mono">${c.emplacement}/${c.noeud == null ? "-" : c.noeud}</td><td class="mono">${esc(c.reference)}</td><td>${esc(c.role)}</td><td class="mono">${esc(c.embase || "—")}</td><td class="mono">${c.noeud && c.noeud !== 127 ? esc(regs(img[c.noeud])) : "—"}</td></tr>`).join("")}</tbody></table>
      <p class="aide-bloc">Proposition indicative : la correspondance des registres avec les %MW de l'automate maître (scrutation BMX NOC) reste à établir ; aucune adresse n'est proposée.</p></div>`;
  }).join("");
}
// Règles de répartition (B3, B4) : groupes de secours proposés puis confirmés, rien n'est appliqué sans confirmation.
function blocRepartition(r) {
  const membres = g => g.map(x => `<span class="mono">${esc(x.repere)}</span>`).join(" / ");
  return `<div class="bloc"><div class="bloc-tete"><h2>Répartition des E/S</h2><span class="aide">bonnes pratiques : continuité de service et extension</span></div>
    <div class="champs-ligne"><label><input type="checkbox" id="rp-sep" ${r.separation_secours ? "checked" : ""}> Équipements secourus sur cartes distinctes</label>
      <label>Emplacements libres par rack <input type="number" id="rp-libres" min="0" max="6" value="${r.emplacements_libres_rack}" style="width:60px"></label></div>
    ${r.separation_secours ? `${r.groupes_secours.length ? `<h3>Groupes de secours confirmés</h3><ul class="rp-liste">${r.groupes_secours.map(g => `<li>${membres(g)} <button class="lien" data-rp-retirer="${esc(JSON.stringify(g.map(x => x.ident)))}">Retirer</button></li>`).join("")}</ul>` : `<p class="aide-bloc">Aucun groupe de secours confirmé.</p>`}
    ${r.groupes_secours_proposes.length ? `<h3>Groupes probables à confirmer</h3><ul class="rp-liste">${r.groupes_secours_proposes.map(g => `<li>${membres(g.membres)} <small>${esc(g.designation || g.type)}</small>
        <button data-rp-confirmer="${esc(JSON.stringify(g.membres.map(x => x.ident)))}">Confirmer</button><button class="lien" data-rp-refuser="${esc(JSON.stringify(g.membres.map(x => x.ident)))}">Refuser</button></li>`).join("")}</ul>` : ""}` : `<p class="aide-bloc">Séparation désactivée pour cet ouvrage.</p>`}
    <p class="aide-bloc">Les E/S déjà placées et validées ne sont jamais déplacées ; recalculez le matériel ou implantez les E/S sans voie pour appliquer les règles.</p></div>`;
}
function liaisonsRepartition() {
  const act = (corps, msg) => agir(api("/api/materiel/action", corps), msg).then(rechargerMateriel);
  if ($("#rp-sep")) $("#rp-sep").onchange = ev => act({action: "regles_repartition", separation_secours: ev.target.checked});
  if ($("#rp-libres")) $("#rp-libres").onchange = ev => act({action: "regles_repartition", emplacements_libres_rack: Number(ev.target.value)});
  document.querySelectorAll("[data-rp-confirmer]").forEach(b => b.onclick = () => act({action: "confirmer_groupe_secours", membres: JSON.parse(b.dataset.rpConfirmer)}, "Groupe de secours confirmé."));
  document.querySelectorAll("[data-rp-refuser]").forEach(b => b.onclick = () => act({action: "refuser_groupe_secours", membres: JSON.parse(b.dataset.rpRefuser)}, "Proposition écartée."));
  document.querySelectorAll("[data-rp-retirer]").forEach(b => b.onclick = () => act({action: "retirer_groupe_secours", membres: JSON.parse(b.dataset.rpRetirer)}, "Groupe retiré."));
}
function vueMateriel() {
  const d = E.es, m = E.mat, b = d.bilan, prop = m.proposition, f = E.filtreES, q = (E.rechercheES || "").toLowerCase();
  const cables = d.points.filter(p => p.raccordement !== "Communication");
  const places = cables.filter(p => p.adresse), aValider = places.filter(p => !p.validee);
  const pts = cables.filter(p => !q || (p.nom + " " + p.pcf + " " + (p.adresse || "")).toLowerCase().includes(q))
                    .filter(p => !f || (f === "PLACER" ? !p.adresse : f === "VOIE" ? (p.adresse && !p.validee) : p.point === f));
  const rien = !d.modules.length;
  const nature = n => ({ET: "entrées TOR", ST: "sorties TOR", EA: "entrées analogiques", SA: "sorties analogiques"})[n];
  const besoins = prop ? prop.besoins.filter(x => x.es) : [];
  const s4w = m.plateforme === "S4W";
  const differe = prop && prop.applicable && d.modules.length && JSON.stringify(prop.modules.map(x => `${x.rack}.${x.position}:${x.reference}`)) !== JSON.stringify(d.modules.map(x => `${x.module}:${x.reference}`));
  $("#vue").innerHTML = `<section class="contenu">
   <div class="titre"><div><h1>Matériel automate</h1><div class="sous">Racks et cartes calculés à partir des E/S validées, avec ${Math.round(m.reserve_min * 100)} % de réserve par carte. OGIAS propose, vous ajustez et validez.</div></div>
     <div class="actions">${m.materiel_valide ? '<span class="badge b-ok grand">Matériel validé</span><button id="m-deval">Repasser à valider</button>'
       : `<button class="${rien ? "" : "prim"}" id="m-valider" ${rien ? "disabled" : ""}>Valider le matériel</button>`}</div></div>
   <div class="bandeau-materiel">
     <div><span class="etiq">Plateforme</span><b>${esc(m.plateforme)}</b><small>${m.automate ? "fiche ouvrage : " + esc(m.automate) : "automate non renseigné"}</small></div>
     ${s4w ? `<div><span class="etiq">Poste de télégestion</span><b>${esc(prop && prop.racks[0] ? prop.racks[0].reference : "—")}</b><small>boîtier proposé</small></div>`
       : `<div><span class="etiq">Densité des cartes</span><select id="m-profil" aria-label="Densité des cartes">${m.profils.map(x => `<option value="${esc(x.code)}" ${x.code === m.profil ? "selected" : ""}>${esc(x.libelle)}</option>`).join("")}</select></div>`}
     <div><span class="etiq">Réserve minimale</span><b>${Math.round(m.reserve_min * 100)} %</b><small>par carte</small></div>
     <div class="droite"><button class="${rien ? "prim" : ""}" id="m-calc" ${prop && prop.applicable ? "" : "disabled"} title="${s4w ? "Proposition indicative pour un poste S4W" : ""}">${rien ? "Calculer le matériel" : "Recalculer le matériel"}</button><button id="m-cartes">Ajuster les cartes…</button></div>
   </div>
   ${m.remarque_plateforme ? `<div class="avert">${esc(m.remarque_plateforme)}</div>` : ""}
   ${m.blocage ? `<div class="alerte-bloc"><b>Calcul impossible :</b> ${esc(m.blocage)} <button class="lien" data-nav="#/es">Aller à la liste des E/S</button></div>` : ""}
   ${differe ? `<div class="avert">Les cartes retenues diffèrent de la proposition actuelle (densité ou E/S modifiées). « Recalculer le matériel » applique la proposition.</div>` : ""}
   <div class="grille-2">
     <div class="bloc"><div class="bloc-tete"><h2>Besoin calculé</h2><span class="aide">${cables.length} E/S câblées · ${b.communication || 0} par communication</span></div>
     ${besoins.length ? `<table><thead><tr><th>Nature</th><th class="num">E/S</th><th>Carte proposée</th><th class="num">Voies utiles</th><th class="num">Cartes</th><th class="num">Réserve</th></tr></thead><tbody>
       ${besoins.map(x => `<tr><td><span class="tag p-${x.nature}">${x.nature}</span> ${nature(x.nature)}</td><td class="num">${x.es}</td><td>${esc(x.reference)}</td><td class="num">${x.utilisables} / ${x.voies}</td><td class="num"><b>${x.cartes}</b></td><td class="num">${Math.round(x.reserve * 100)} %</td></tr>`).join("")}</tbody></table>`
       : `<div class="vide-bloc">${m.blocage ? "Validez la liste des E/S pour obtenir le besoin." : "Aucune E/S câblée."}</div>`}
     ${prop && prop.remarques.length ? `<ul class="remarques">${prop.remarques.map(r => `<li>${esc(r)}</li>`).join("")}</ul>` : ""}</div>
     <div class="bloc"><div class="bloc-tete"><h2>Implantation</h2><span class="aide">voies et adresses des E/S câblées</span></div>
       <div class="chiffres c3">${cables.length > places.length ? pastille("PLACER", cables.length - places.length, "E/S sans voie", "al", f) : ""}${aValider.length ? pastille("VOIE", aValider.length, "voies à valider", "al", f) : ""}${places.length > aValider.length ? pastille("", places.length - aValider.length, "voies validées", "ok", "x") : ""}</div>
       <div class="boutons-ligne"><button class="prim" id="m-impl" ${rien || !(cables.length - places.length) ? "disabled" : ""}>Implanter les E/S sans voie</button><button id="m-lib" ${aValider.length ? "" : "disabled"}>Libérer les voies non validées</button></div>
       <p class="aide-bloc">Les E/S d'un même équipement restent groupées sur une carte. Une E/S validée sur sa voie ne bouge plus.</p></div>
   </div>
   ${blocComposition(m)}
   ${m.plateforme === "STB" && prop ? blocIlotsSTB(prop) : ""}
   ${m.repartition ? blocRepartition(m.repartition) : ""}
   <div class="bloc"><div class="bloc-tete"><h2>Racks</h2><span class="aide">${rien ? "aucune carte retenue" : `${d.modules.length} carte(s) · cliquez une carte pour la modifier`}</span>
     <span class="legende"><i class="l-ok"></i>réserve respectée <i class="l-al"></i>sous la réserve <i class="l-err"></i>dépassement</span></div>
     ${s4w && prop && prop.racks.length ? `<p class="aide-bloc"><b>Proposition indicative S4W</b> — voies intégrées au boîtier puis modules d'extension (la CPU est intégrée au boîtier).</p>`
         + prop.racks.map(r => vueRack(r, prop.modules.map(x => ({module: `${x.rack}.${x.position}`, nature: x.nature, voies: x.voies, reference: x.reference, occupees: 0, reserve: x.voies, taux: 1, sous_seuil: false})))).join("") : ""}
     ${rien ? (s4w ? "" : `<div class="vide-bloc">${prop ? "Cliquez sur « Calculer le matériel » : OGIAS propose les racks et les cartes à partir du besoin ci-dessus." : "Le matériel sera proposé une fois la liste des E/S validée."}</div>`)
       : (s4w ? `<p class="aide-bloc"><b>Matériel actuellement retenu</b></p>` : "") + racksAffiches(m, d.modules).map((r, _i, t) => vueRack(r, d.modules, t.length > 1)).join("")}
     <p class="note">${esc(m.statut_catalogue)}</p></div>
   ${blocNomenclature(m)}
   <div class="bloc"><div class="bloc-tete"><h2>Liste des E/S par voie</h2><input id="x-q" type="search" placeholder="Rechercher une E/S, une adresse…" value="${esc(E.rechercheES || "")}" style="width:260px" aria-label="Rechercher">
     ${f ? '<button class="lien" id="x-tout">Tout afficher</button>' : ""}<span class="aide">${pts.length} / ${cables.length}</span>
     <div class="droite"><button id="x-val-tout" ${pts.some(p => p.adresse && !p.validee) ? "" : "disabled"}>Valider les voies affichées</button><button class="prim" id="x-val" disabled>Valider la sélection</button></div></div>
   ${cables.length ? `<div class="defile"><table class="t-es"><thead><tr><th style="width:28px"><input type="checkbox" id="x-coche-tout" aria-label="Tout sélectionner"></th><th>Repère</th><th>Point</th><th>Nom de l'E/S</th><th>Carte.voie</th><th>Adresse</th><th>Voie</th></tr></thead><tbody>
   ${pts.map(p => { const i = d.points.indexOf(p); return `<tr class="cliquable" data-i="${i}"><td><input type="checkbox" class="x-coche" value="${i}" ${p.adresse ? "" : "disabled"} aria-label="Sélectionner ${esc(p.nom)}"></td><td class="mono">${esc(p.pcf)}</td>
     <td><span class="tag p-${p.point}">${p.point}</span></td><td class="mono">${esc(p.nom)}</td><td class="mono">${p.module ? esc(p.module + "." + String(p.voie).padStart(2, "0")) : '<span class="vide">—</span>'}</td>
     <td class="mono">${p.adresse ? esc(p.adresse) : '<span class="vide">à placer</span>'}</td>
     <td>${!p.adresse ? '<span class="badge b-n">sans voie</span>' : p.validee ? '<span class="badge b-ok">validée</span>' : '<span class="badge b-al">proposée</span>'}</td></tr>`; }).join("")}</tbody></table></div>` : '<div class="vide-bloc">Aucune E/S câblée.</div>'}
   </div>
   <div class="bloc livrables"><div class="bloc-tete"><h2>Livrables matériel</h2><span class="aide">XSY et TXT au format des exports Control Expert V14.1 fournis : import dans Control Expert à essayer</span></div>
     <div class="boutons-ligne"><button id="x-xl" ${cables.length ? "" : "disabled"}>Liste d'E/S (Excel)</button><button id="x-ca" ${rien ? "disabled" : ""}>Cartes d'E/S (Excel)</button>
     <button id="x-xsy" ${places.length ? "" : "disabled"} title="Format de l'export des variables de Control Expert V14.1, voies de réserve comprises">E/S pour Control Expert (XSY)</button><button id="x-txt" ${places.length ? "" : "disabled"}>E/S pour Control Expert (TXT)</button>
     <span class="aide">${places.length < cables.length ? `${cables.length - places.length} E/S n'ont pas encore de voie : elles figureront sans adresse.` : "Toutes les E/S câblées ont une voie."}</span></div></div>
  </section>`;
  brancherListeES(pts, "voie");
  const appliquer = () => agir(api("/api/materiel/action", {action: "appliquer"})).then(() => { toast("Matériel proposé appliqué : à vérifier puis valider."); rechargerMateriel(); });
  $("#m-calc").onclick = () => rien ? appliquer() : confirmer("Recalculer le matériel ?", "Les cartes actuelles sont remplacées par la proposition. C'est refusé si des E/S occupent déjà des voies : libérez-les d'abord.", "Recalculer", appliquer);
  if ($("#m-profil")) $("#m-profil").onchange = ev => agir(api("/api/materiel/action", {action: "profil", profil: ev.target.value})).then(rechargerMateriel);
  $("#m-cartes").onclick = () => modaleModules();
  document.querySelectorAll("[data-carte]").forEach(x => x.onclick = () => modaleVoiesCarte(x.dataset.carte));
  if ($("#m-valider")) $("#m-valider").onclick = () => agir(api("/api/materiel/action", {action: "valider"})).then(() => { toast("Matériel validé."); rechargerMateriel(); });
  if ($("#m-deval")) $("#m-deval").onclick = () => agir(api("/api/materiel/action", {action: "valider", valide: false})).then(rechargerMateriel);
  $("#m-impl").onclick = async () => {
    const a = await agir(api("/api/modules", {action: "apercu"}));
    const manq = Object.entries(a.manquantes).map(([k, v]) => `${v} ${k}`).join(", ");
    confirmer(`Implanter ${a.affectees} E/S ?`, `Chaque E/S câblée sans voie reçoit une voie proposée, équipement par équipement, en gardant la réserve.` + (manq ? ` Sans voie possible : ${manq} — ajoutez des cartes.` : ""),
      "Implanter", async () => { const r = await agir(api("/api/modules", {action: "implanter"})); toast(`${r.affectees} E/S placée(s).`); rechargerMateriel(); });
  };
  $("#m-lib").onclick = () => confirmer("Libérer les voies non validées ?", "Les E/S dont la voie n'est pas validée perdent leur carte, leur voie et leur adresse. Les voies validées restent.", "Libérer",
    async () => { const r = await agir(api("/api/modules", {action: "liberer"})); toast(`${r.liberees} voie(s) libérée(s).`); rechargerMateriel(); });
  liaisonsRepartition();
  liaisonsComposition();
  $("#x-xl").onclick = () => telecharger("liste_es");
  $("#x-ca").onclick = () => telecharger("cartes");
  $("#x-xsy").onclick = () => telecharger("es_xsy");
  $("#x-txt").onclick = () => telecharger("es_txt");
}
/* Import du référentiel depuis Excel : contrôle, aperçu des différences, application avec motif. */
function modaleImportReferentiel() {
  const m = ouvrirModale(`<div class="boite-tete"><h2>Importer un classeur dans le brouillon</h2>
    <p>Classeur exporté depuis OGIAS puis modifié. Il est contrôlé et comparé au brouillon : rien n'est modifié avant
    « Intégrer au brouillon ». La révision publiée et les ouvrages ne changent qu'à la publication.</p></div>
    <div class="boite-corps"><div class="v30-file-select"><label for="rx-f" class="v30-file-button">Choisir un classeur Excel…</label><input type="file" id="rx-f" accept=".xlsx" aria-label="Sélectionner un classeur Excel"><span id="rx-file-name" role="status" aria-live="polite">Aucun fichier sélectionné</span></div><div id="rx-res" style="margin-top:14px"></div><div class="erreur-form" id="m-err"></div></div>
    <div class="boite-pied"><span class="gauche" id="rx-bilan"></span><button data-fermer>Annuler</button><button class="prim" id="m-ok" disabled>Intégrer au brouillon</button></div>`, true);
  let analyse = null;
  m.querySelector("#rx-f").onchange = async ev => {
    m.querySelector("#rx-file-name").textContent = ev.target.files[0]?.name || "Aucun fichier sélectionné";
    m.querySelector("#m-err").textContent = ""; m.querySelector("#m-ok").disabled = true;
    m.querySelector("#rx-res").innerHTML = '<div class="vide">Lecture et contrôle du classeur…</div>';
    try {
      analyse = await api("/api/referentiel/cycle/action", {action: "importer_apercu", ...(await lireFichier(ev.target))});
      const n = {}; analyse.differences.forEach(d => n[d.action] = (n[d.action] || 0) + 1);
      m.querySelector("#rx-bilan").innerHTML = analyse.erreurs.length ? `<span class="badge b-err">${analyse.erreurs.length} erreur(s) bloquante(s)</span>`
        : Object.entries(n).map(([k, v]) => `<span class="badge ${(ACTION_DIFF[k] || ["b-n"])[0]}">${v} ${k}(s)</span>`).join(" ") || '<span class="badge b-n">aucune différence</span>';
      m.querySelector("#rx-res").innerHTML = (analyse.erreurs.length ? `<div class="bloc"><div class="bloc-tete"><h3>Erreurs bloquantes</h3><span class="aide">corrigez le classeur puis réimportez-le</span></div><ul class="liste-controles">${analyse.erreurs.map(x => `<li class="c-err">${esc(x)}</li>`).join("")}</ul></div>` : "")
        + (analyse.alertes.length ? `<ul class="liste-controles">${analyse.alertes.map(x => `<li class="c-al">${esc(x)}</li>`).join("")}</ul>` : "")
        + ((analyse.erreurs_brouillon || []).length ? `<div class="avert">Après intégration, le brouillon aura ${analyse.erreurs_brouillon.length} erreur(s) à corriger avant validation (ex. ${esc(analyse.erreurs_brouillon[0])}).</div>` : "")
        + (analyse.erreurs.length ? "" : tableDifferences(analyse.differences));
      m.querySelector("#m-ok").disabled = !analyse.integrable || analyse.erreurs.length > 0;
    } catch (e) { m.querySelector("#rx-res").innerHTML = ""; m.querySelector("#m-err").textContent = e.message; }
  };
  m.querySelector("#m-ok").onclick = async () => {
    try { await api("/api/referentiel/cycle/action", {action: "importer_appliquer", empreinte: analyse.empreinte});
      fermerModale(); toast("Classeur intégré au brouillon : contrôlez puis publiez."); await chargerReferentiel(); vueReferentiel(); }
    catch (e) { m.querySelector("#m-err").textContent = e.message; }
  };
}
async function telecharger(quoi) {
  const r = await fetch("/api/export?quoi=" + quoi);
  if (!r.ok) { const j = await r.json().catch(() => ({})); return toast(j.erreur || "Export impossible.", true); }
  const nom = (r.headers.get("Content-Disposition") || "").match(/filename="([^"]+)"/)?.[1] || quoi + ".xlsx";
  const url = URL.createObjectURL(await r.blob());
  const a = document.createElement("a"); a.href = url; a.download = nom; document.body.appendChild(a); a.click(); a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 2000);
  toast(`Fichier ${nom} téléchargé.`);
}
function modaleES(p, niveau = "contenu") {
  const voie = niveau === "voie";
  const m = ouvrirModale(`<div class="boite-tete"><h2 class="mono">${esc(p.nom)}</h2><p>${esc(p.pcf)} · ${esc(p.point)} · ${esc(p.information)}</p></div>
    <div class="boite-corps"><div class="champs">
      <label>Désignation</label><input id="s-des" value="${esc(p.designation)}" placeholder="${esc(p.commentaire)}">
      ${['ET','ST'].includes(p.point) ? `<label>Sens du bit</label><input id="s-sens" value="${esc(p.sens)}" placeholder="ex. 1 = Défaut">` : `<label>Échelle analogique</label><div>${p.analogique ? esc(p.analogique.signal_min + '–' + p.analogique.signal_max + ' mA → ' + p.analogique.phys_min + '–' + p.analogique.phys_max + ' ' + p.analogique.unite) : 'Non définie — retour à la fiche équipement'}</div>`}
      <label>Raccordement</label><select id="s-rac"><option ${p.raccordement === "Câblé" ? "selected" : ""}>Câblé</option><option ${p.raccordement === "Communication" ? "selected" : ""}>Communication</option></select>
      ${voie ? `<label>Carte</label><input id="s-mod" value="${esc(p.module)}" placeholder="rack.position, ex. 0.3">
      <label>Voie</label><input id="s-voie" value="${esc(p.voie)}" placeholder="ex. 5">
      <label>Adresse</label><div class="mono" id="s-adr">${esc(p.adresse || "—")}</div>
      <label></label><label style="text-align:left;color:var(--texte)"><input type="checkbox" id="s-val" ${p.validee ? "checked" : ""}> Voie validée</label>`
      : `<label></label><label style="text-align:left;color:var(--texte)"><input type="checkbox" id="s-val" ${p.contenu_valide ? "checked" : ""}> Contenu validé</label>`}
    </div><div class="erreur-form" id="m-err"></div></div>
    <div class="boite-pied"><button data-fermer>Annuler</button><button class="prim" id="m-ok">Enregistrer</button></div>`);
  const q = x => m.querySelector(x);
  const prefixe = {ET: "%I", ST: "%Q", EA: "%IW", SA: "%QW"}[p.point];
  const maj = () => { if (!voie) return; const mo = q("#s-mod").value.trim(), v = q("#s-voie").value.trim();
    q("#s-adr").textContent = q("#s-rac").value === "Communication" ? "par communication (pas d'adresse)" : (mo && v ? `${prefixe}${mo.includes(".") ? mo : "0." + mo}.${+v}` : "—"); };
  if (voie) { ["#s-mod", "#s-voie"].forEach(x => q(x).oninput = maj); q("#s-rac").onchange = maj; maj(); }
  q("#m-ok").onclick = async () => {
    const com = q("#s-rac").value === "Communication";
    const champs = {ident_eq: p.ident_eq, cle: p.cle, designation: q("#s-des").value, raccordement: q("#s-rac").value};
    if (q("#s-sens")) champs.sens = q("#s-sens").value;
    if (voie) Object.assign(champs, {module: com ? "" : q("#s-mod").value, voie: com ? "" : q("#s-voie").value, validee: q("#s-val").checked});
    try { await api("/api/es/definir", champs);
          if (!voie) await api("/api/es/valider", {niveau: "contenu", valide: q("#s-val").checked, paires: [{ident_eq: p.ident_eq, cle: p.cle}]});
          fermerModale(); toast("E/S enregistrée."); voie ? rechargerMateriel() : rechargerES(); }
    catch (err) { q("#m-err").textContent = err.message; }
  };
}
// Retour d'essai 10 : vue des voies d'une carte, avec déplacement d'une E/S vers une voie libre de même nature
// ou placement d'une E/S sans voie. Une E/S validée qui bouge repasse « à valider » (confirmation demandée).
function placeES(p) {
  if (p.module && p.voie !== "" && p.voie != null) return [p.module.includes(".") ? p.module : "0." + p.module, +p.voie];
  const m = /^%(?:I|Q|IW|QW)(\d{1,2})\.(\d{1,2})\.(\d{1,3})$/i.exec(p.adresse || "");
  return m ? [`${+m[1]}.${+m[2]}`, +m[3]] : [null, null];
}
function modaleVoiesCarte(cleCarte) {
  const d = E.es, carte = d.modules.find(x => x.module === cleCarte);
  if (!carte) return modaleModules(cleCarte);
  const cables = d.points.filter(p => p.raccordement !== "Communication");
  const occupant = {}, occupees = {};
  cables.forEach(p => { const [k, v] = placeES(p); if (k) { (occupees[k] ||= new Set()).add(v); if (k === cleCarte) occupant[v] = p; } });
  const libres = d.modules.filter(x => x.nature === carte.nature)
    .flatMap(x => Array.from({length: x.voies}, (_, v) => [x.module, v]).filter(([k, v]) => !(occupees[k] || new Set()).has(v)));
  const sansVoie = cables.filter(p => p.point === carte.nature && !placeES(p)[0]);
  const optLibres = `<option value="">Déplacer vers…</option>` + libres.map(([k, v]) => `<option value="${k}|${v}">${k} voie ${v}</option>`).join("");
  const lignes = Array.from({length: carte.voies}, (_, v) => {
    const p = occupant[v];
    return p ? `<tr><td class="mono">${v}</td><td class="mono">${esc(p.nom)}</td><td>${esc(p.pcf)}</td><td>${p.validee ? '<span class="badge b-ok">validée</span>' : '<span class="badge b-al">à valider</span>'}</td>
        <td><select class="cv-deplacer" data-eq="${esc(p.ident_eq)}" data-cle="${esc(p.cle)}" data-validee="${p.validee ? 1 : ""}" aria-label="Déplacer ${esc(p.nom)}">${optLibres}</select></td></tr>`
      : `<tr class="libre"><td class="mono">${v}</td><td colspan="3" class="sec">libre</td>
        <td>${sansVoie.length ? `<select class="cv-placer" data-voie="${v}" aria-label="Placer une E/S sur la voie ${v}"><option value="">Placer une E/S sans voie…</option>${sansVoie.map(p => `<option value="${esc(p.ident_eq)}|${esc(p.cle)}">${esc(p.nom)}</option>`).join("")}</select>` : ""}</td></tr>`;
  }).join("");
  const m = ouvrirModale(`<div class="boite-tete"><h2>Carte ${esc(cleCarte)} — ${esc(carte.reference)}</h2>
      <p>${carte.voies} voies ${esc(carte.nature)} · ${carte.occupees} occupée(s) · réserve ${carte.reserve} (${Math.round(carte.taux * 100)} %)${carte.sous_seuil && carte.occupees ? " · sous le seuil" : ""}</p></div>
    <div class="boite-corps"><table class="voies-carte"><thead><tr><th>Voie</th><th>E/S</th><th>Équipement</th><th>État</th><th>Réaffecter</th></tr></thead><tbody>${lignes}</tbody></table>
    <div class="erreur-form" id="m-err"></div></div>
    <div class="boite-pied"><button id="cv-carte">Modifier la carte…</button><button class="prim" data-fermer>Fermer</button></div>`, true);
  const q = x => m.querySelector(x);
  const deplacer = async (ident_eq, cle, cible) => {
    const [module, voie] = cible.split("|");
    try { await api("/api/es/definir", {ident_eq, cle, module, voie}); E.es = await api("/api/es"); toast(`E/S placée sur ${module} voie ${voie} : à valider.`); modaleVoiesCarte(cleCarte); rechargerMateriel(); }
    catch (e) { q("#m-err").textContent = e.message; }
  };
  m.querySelectorAll(".cv-deplacer").forEach(s => s.onchange = () => {
    if (!s.value) return;
    if (s.dataset.validee && !window.confirm("Cette E/S est validée sur sa voie. La déplacer la repasse « à valider ». Continuer ?")) { s.value = ""; return; }
    deplacer(s.dataset.eq, s.dataset.cle, s.value);
  });
  m.querySelectorAll(".cv-placer").forEach(s => s.onchange = () => {
    if (!s.value) return;
    const [ident_eq, cle] = s.value.split("|");
    deplacer(ident_eq, cle, `${cleCarte}|${s.dataset.voie}`);
  });
  q("#cv-carte").onclick = () => modaleModules(cleCarte);
}
function modaleModules(edition) {
  const d = E.es, x0 = edition ? d.modules.find(x => x.module === edition) : null;
  const posLibre = d.modules.length ? Math.max(...d.modules.map(x => +x.module.split(".")[1])) + 1 : 2;
  const m = ouvrirModale(`<div class="boite-tete"><h2>Cartes d'E/S</h2><p>Ajustez les cartes proposées : référence, nombre de voies, rack, position. Toute modification remet le matériel « à valider ».</p></div>
    <div class="boite-corps">
    ${d.modules.length ? `<table><thead><tr><th>Rack.position</th><th>Nature</th><th>Référence</th><th>Voies</th><th>Occupées</th><th>Réserve</th><th></th></tr></thead><tbody>
      ${d.modules.map(x => `<tr class="${x.module === edition ? "sel-ligne" : ""}"><td class="mono">${esc(x.module)}</td><td>${esc(x.nature)}</td><td>${esc(x.reference)}</td><td>${x.voies}</td><td>${x.occupees}</td>
        <td>${x.reserve} (${Math.round(x.taux * 100)} %)${x.sous_seuil && x.occupees ? ' <span class="badge b-al">sous le seuil</span>' : ""}</td>
        <td style="text-align:right;white-space:nowrap"><button class="lien" data-mmod="${esc(x.module)}">Modifier</button><button class="lien" data-msup="${esc(x.module)}">Supprimer</button></td></tr>`).join("")}</tbody></table>`
      : '<div class="vide-bloc">Aucune carte déclarée.</div>'}
    <div class="bloc-tete" style="margin-top:16px"><h2>${x0 ? "Modifier la carte " + esc(x0.module) : "Ajouter une carte"}</h2></div>
    <div class="champs">
      <label>Modèle de carte</label><select id="c-carte"><option value="">— autre (saisie libre) —</option>${d.cartes.map((c, i) => `<option value="${i}">${esc(c.reference)} — ${c.voies} ${c.nature}</option>`).join("")}</select>
      <label>Référence</label><input id="c-ref" value="${esc(x0 ? x0.reference : "")}" placeholder="ex. BMX DDI 1602">
      <label>Nature</label><select id="c-nat">${["ET", "ST", "EA", "SA"].map(n => `<option ${x0 && x0.nature === n ? "selected" : ""}>${n}</option>`).join("")}</select>
      <label>Nombre de voies</label><input id="c-voies" value="${x0 ? x0.voies : 16}">
      <label>Rack</label><input id="c-rack" value="${x0 ? x0.module.split(".")[0] : 0}">
      <label>Position</label><input id="c-pos" value="${x0 ? x0.module.split(".")[1] : posLibre}">
      <label>Réserve minimale</label><div><input id="c-res" value="${Math.round(d.reserve_min * 100)}" style="width:80px"> % des voies de chaque carte</div>
    </div><div class="erreur-form" id="m-err"></div></div>
    <div class="boite-pied"><button data-fermer>Fermer</button>${x0 ? '<button id="m-annul">Annuler la modification</button>' : ""}
      <button class="prim" id="m-ok">${x0 ? "Enregistrer la carte" : "Ajouter la carte"}</button></div>`, true);
  const q = x => m.querySelector(x);
  const recharge = async ed => { E.es = await api("/api/es"); modaleModules(ed); };
  q("#c-carte").onchange = () => { const c = d.cartes[+q("#c-carte").value]; if (q("#c-carte").value !== "" && c) { q("#c-ref").value = c.reference; q("#c-nat").value = c.nature; q("#c-voies").value = c.voies; } };
  if (!x0) { q("#c-carte").value = "0"; q("#c-carte").onchange(); }
  q("#m-ok").onclick = async () => {
    const champs = {rack: q("#c-rack").value, position: q("#c-pos").value, nature: q("#c-nat").value, voies: q("#c-voies").value, reference: q("#c-ref").value};
    try { await api("/api/modules", x0 ? {action: "modifier", cle: x0.module, ...champs} : {action: "ajouter", ...champs});
          toast(x0 ? "Carte modifiée." : "Carte ajoutée."); recharge(); }
    catch (err) { q("#m-err").textContent = err.message; }
  };
  if (q("#m-annul")) q("#m-annul").onclick = () => modaleModules();
  q("#c-res").onchange = async () => { try { await api("/api/modules", {action: "reserve", taux: (+q("#c-res").value) / 100}); toast("Réserve minimale enregistrée."); recharge(edition); } catch (err) { q("#m-err").textContent = err.message; } };
  m.querySelectorAll("[data-mmod]").forEach(bt => bt.onclick = () => modaleModules(bt.dataset.mmod));
  m.querySelectorAll("[data-msup]").forEach(bt => bt.onclick = async () => { try { await api("/api/modules", {action: "supprimer", cle: bt.dataset.msup}); toast("Carte supprimée."); recharge(); } catch (err) { q("#m-err").textContent = err.message; } });
  E.apresFermeture = () => { if (E.vue === "materiel") rechargerMateriel(); else if (E.vue === "es") rechargerES(); };
}

/* ------------------------------------------------------------------ démarrage */
(async () => {
  try {
    const a = await api("/api/accueil");
    if (!location.hash || !ROUTES[location.hash]) history.replaceState(null, "", a.ouvert ? "#/inventaire" : "#/ouvrages");
    await afficher();
  } catch (e) { document.body.innerHTML = `<p style="padding:30px">Le serveur OGIAS ne répond pas : ${esc(e.message)}</p>`; }
})();
