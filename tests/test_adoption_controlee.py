"""Adoption contrôlée d'une révision du référentiel : aperçu, confirmation, correspondances, retour arrière."""
import copy
import json
import os
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from unittest.mock import patch

from genvar import adoption, chemins
from genvar.catalogue import Catalogue
from genvar.modele import Equipement, suffixe_physique
from genvar.session import RegleMetier, Session


def _ouvrage(types=("GA", "EV")):
    """Ouvrage fictif enregistré avec le référentiel figé « ancien » (= catalogue livré)."""
    s = Session(Catalogue.charger(chemins.fichier_catalogue_origine()))
    s.nouveau(False)
    s.definir("lieu", "XTST"); s.definir("code_ouvrage", "RV"); s.ouvrage.numero_ouvrage = "01"
    s.ajouter_sous_ensemble("00")
    eqs = {}
    for t in types:
        eq = s.ajouter_equipement(Equipement("00", t, "01"))
        s.decider_propositions(eq.ident, "retenir")
        s.valider_equipements([eq.ident])
        eqs[t] = eq
    props, _ = s.plan(); s.appliquer(props)
    s.catalogue = copy.deepcopy(s._catalogue_commun)                      # figé dans l'ouvrage, d'avant V2 :
    for x in s.catalogue.signaux:                                          # fin de course nommée FDC_OUV
        if x["type"] == "EV" and x["code"] == "OUV":
            x["organe"] = "FDC"
    return s, eqs


def _nouveau_referentiel(s, renommer=True, correspondance=True):
    """Révision actuelle : GA.TS_INTR devient GA.TS_INTRUS ; EV.TS_OUV sans organe FDC (référentiel livré V2)."""
    cat = copy.deepcopy(s._catalogue_commun)
    for x in cat.signaux:
        if renommer and x["type"] == "GA" and x["code"] == "INTR":
            x["code"] = "INTRUS"
    assert next(x for x in cat.signaux if x["type"] == "EV" and x["code"] == "OUV")["organe"] == ""
    cat.version = "révision d'essai"
    s._catalogue_commun = cat
    s.modeles["correspondances"] = ([{"type": "GA", "ancienne": "TS_INTR", "nouvelle": "TS_INTRUS"}]
                                    if correspondance else [])


def _contenu(f):
    """Fichier de projet sans l'horodatage d'enregistrement (seule valeur qui change à chaque sauvegarde)."""
    d = json.load(open(f, encoding="utf-8"))
    (d.get("ouvrage", d)).pop("modifie_le", None)
    return d


class Base(unittest.TestCase):
    def setUp(self):
        self.ancien_env = os.environ.get("SOREP_DATA_DIR")
        self.dossier = tempfile.mkdtemp()
        os.environ["SOREP_DATA_DIR"] = self.dossier

    def tearDown(self):
        if self.ancien_env is None:
            os.environ.pop("SOREP_DATA_DIR", None)
        else:
            os.environ["SOREP_DATA_DIR"] = self.ancien_env


class TestApercu(Base):
    def test_renommages_physique_et_fonctionnel_annonces(self):
        s, _ = _ouvrage()
        _nouveau_referentiel(s)
        ap = {x["type"]: x for x in s.apercu_adoption()}
        ga = ap["GA"]["renommages"][0]
        self.assertEqual((ga["ancienne"], ga["nouvelle"]), ("TS_INTR", "TS_INTRUS"))
        self.assertEqual(ga["fonctionnel"], ["TS_<repère>_INTR", "TS_<repère>_INTRUS"])
        ev = next(r for r in ap["EV"]["renommages"] if r["ancienne"] == "TS_OUV")
        self.assertEqual(ev["physique"], ["ET_<repère>_FDC_OUV", "ET_<repère>_OUV"])
        self.assertEqual(ev["fonctionnel"][0], ev["fonctionnel"][1])
        self.assertTrue(ap["GA"]["adoptable"] and ap["EV"]["adoptable"])

    def test_retrait_porteur_de_donnees_sans_correspondance_bloque(self):
        s, _ = _ouvrage(("GA",))
        _nouveau_referentiel(s, correspondance=False)
        ga = s.apercu_adoption()[0]
        self.assertFalse(ga["adoptable"])
        self.assertIn("déclarer une correspondance", ga["bloquants"][0])
        with self.assertRaises(RegleMetier):
            s.adopter_referentiel(["GA"], renommages_confirmes=True)

    def test_type_supprime_ou_change_de_type_bloque(self):
        s, _ = _ouvrage(("GA",))
        cat = copy.deepcopy(s._catalogue_commun)
        cat.types = [t for t in cat.types if t["code"] != "GA"]
        cat.signaux = [x for x in cat.signaux if x["type"] != "GA"]
        s._catalogue_commun = cat
        s.modeles["correspondances"] = [{"type": "GA", "ancienne": "TS_INTR", "type_nouveau": "XT",
                                         "nouvelle": "TS_DEF"}]
        b = s.apercu_adoption()[0]["bloquants"]
        self.assertTrue(any("changement de type" in m for m in b))
        self.assertTrue(any("absent du référentiel actuel" in m for m in b))


class TestAdoption(Base):
    def test_sans_choix_seuls_les_types_sans_renommage(self):
        s, eqs = _ouvrage()
        _nouveau_referentiel(s)
        self.assertEqual(s.adopter_referentiel(), [])                    # GA et EV renomment : rien d'appliqué
        with self.assertRaises(RegleMetier):
            s.adopter_referentiel(["GA"])                                  # confirmation exigée
        self.assertTrue(eqs["GA"].valide)

    def test_adresses_reportees_et_aucun_nouveau_mw(self):
        s, eqs = _ouvrage()
        ga = eqs["GA"]
        ga.adresses_es["TS_INTR"] = "%I0.1.3"
        ga.commentaires["TS_INTR"] = "commentaire saisi"
        avant = {v.nom: v.adresse for v in s.variables()}
        mw_avant = sorted(a for a in avant.values() if a)
        _nouveau_referentiel(s)
        s.adopter_referentiel(["GA"], renommages_confirmes=True)
        apres = {v.nom: v for v in s.variables()}
        nom = next(n for n in avant if n.startswith("TS_") and n.endswith("_INTR"))
        nouveau = nom[:-len("INTR")] + "INTRUS"
        self.assertEqual(apres[nouveau].adresse, avant[nom])
        self.assertEqual(apres[nouveau].adresse_es, "%I0.1.3")
        self.assertEqual(ga.commentaires, {"TS_INTRUS": "commentaire saisi"})
        self.assertEqual(sorted(v.adresse for v in apres.values() if v.adresse), mw_avant)
        self.assertFalse(ga.valide)
        self.assertIn("adoption partielle", s.catalogue.version)            # EV garde son référentiel figé
        self.assertEqual(suffixe_physique(next(x for x in s.catalogue.signaux
                                               if x["type"] == "EV" and x["code"] == "OUV")), "FDC_OUV")

    def test_sauvegarde_et_retour_arriere_a_l_octet(self):
        s, _ = _ouvrage()
        f = os.path.join(self.dossier, "essai.json")
        s.enregistrer(f)
        original, octets = _contenu(f), open(f, "rb").read()
        _nouveau_referentiel(s)
        s.adopter_referentiel(["GA", "EV"], renommages_confirmes=True)
        self.assertTrue(s.sauvegarde_adoption and open(s.sauvegarde_adoption, "rb").read() == octets)
        s.annuler_adoption()
        s.enregistrer(f)
        self.assertEqual(_contenu(f), original)
        with self.assertRaises(RegleMetier):
            s.annuler_adoption()

    def test_adoption_refusee_projet_inchange(self):
        s, _ = _ouvrage(("GA",))
        f = os.path.join(self.dossier, "essai.json")
        s.enregistrer(f)
        original = _contenu(f)
        _nouveau_referentiel(s, correspondance=False)
        with self.assertRaises(RegleMetier):
            s.adopter_referentiel(["GA"], renommages_confirmes=True)
        s.enregistrer(f)
        self.assertEqual(_contenu(f), original)

    def test_type_inconnu_refuse(self):
        s, _ = _ouvrage(("GA",))
        with self.assertRaises(RegleMetier):
            s.adopter_referentiel(["PM"])

    def test_nouvel_ouvrage_ne_peut_pas_annuler_l_adoption_du_precedent(self):
        s, _ = _ouvrage()
        _nouveau_referentiel(s)
        s.adopter_referentiel(["EV"], renommages_confirmes=True)
        s.nouveau(False)
        with self.assertRaisesRegex(RegleMetier, "Aucune adoption"):
            s.annuler_adoption()
        self.assertEqual(s.ouvrage.equipements, [])

    def test_autre_ouvrage_ne_peut_pas_annuler_l_adoption_du_precedent(self):
        s, _ = _ouvrage()
        autre, _ = _ouvrage(("GA",))
        fichier = os.path.join(self.dossier, "autre.json")
        autre.enregistrer(fichier)
        avant = open(fichier, "rb").read()
        _nouveau_referentiel(s)
        s.adopter_referentiel(["EV"], renommages_confirmes=True)
        s.ouvrir(fichier)
        with self.assertRaisesRegex(RegleMetier, "Aucune adoption"):
            s.annuler_adoption()
        self.assertEqual(open(fichier, "rb").read(), avant)

    def test_annulation_enregistree_restaure_les_octets_originaux(self):
        s, _ = _ouvrage()
        fichier = os.path.join(self.dossier, "fictif.json")
        s.enregistrer(fichier)
        avant = open(fichier, "rb").read()
        _nouveau_referentiel(s)
        s.adopter_referentiel(["EV"], renommages_confirmes=True)
        s.enregistrer(fichier)
        self.assertNotEqual(open(fichier, "rb").read(), avant)
        s.annuler_adoption(enregistrer=True)
        self.assertEqual(open(fichier, "rb").read(), avant)

    def test_sauvegardes_ne_s_ecrasent_jamais(self):
        fichier = os.path.join(self.dossier, "fictif.json")
        with open(fichier, "wb") as f:
            f.write(b"premier etat fictif")
        with patch('genvar.adoption.datetime') as horloge:
            horloge.now.return_value.strftime.return_value = 'date-identique'
            premiere = adoption.sauvegarder(fichier)
            with open(fichier, "wb") as f:
                f.write(b"deuxieme etat fictif")
            seconde = adoption.sauvegarder(fichier)
        self.assertNotEqual(premiere, seconde)
        self.assertEqual(open(premiere, "rb").read(), b"premier etat fictif")
        self.assertEqual(open(seconde, "rb").read(), b"deuxieme etat fictif")

    def test_enregistrer_sous_ne_transporte_pas_l_annulation(self):
        s, _ = _ouvrage()
        s.enregistrer(os.path.join(self.dossier, "avant.json"))
        _nouveau_referentiel(s)
        s.adopter_referentiel(["EV"], renommages_confirmes=True)
        autre = os.path.join(self.dossier, "copie.json")
        s.enregistrer(autre)
        octets = open(autre, "rb").read()
        with self.assertRaisesRegex(RegleMetier, "Aucune adoption"):
            s.annuler_adoption(enregistrer=True)
        self.assertEqual(open(autre, "rb").read(), octets)

    def test_ouverture_invalide_conserve_le_retour_arriere_courant(self):
        s, _ = _ouvrage()
        _nouveau_referentiel(s)
        s.adopter_referentiel(["EV"], renommages_confirmes=True)
        with self.assertRaises(OSError):
            s.ouvrir(os.path.join(self.dossier, "absent.json"))
        self.assertTrue(s.annuler_adoption())

    def test_sauvegarde_absente_annulation_refusee_sans_mutation(self):
        s, _ = _ouvrage()
        fichier = os.path.join(self.dossier, "fictif.json")
        s.enregistrer(fichier)
        _nouveau_referentiel(s)
        s.adopter_referentiel(["EV"], renommages_confirmes=True)
        s.enregistrer(fichier)
        avant = open(fichier, "rb").read()
        ouvrage = s.ouvrage.vers_dict()
        os.unlink(s.sauvegarde_adoption)
        with self.assertRaisesRegex(RegleMetier, "introuvable"):
            s.annuler_adoption(enregistrer=True)
        self.assertEqual(s.ouvrage.vers_dict(), ouvrage)
        self.assertEqual(open(fichier, "rb").read(), avant)

    def test_echec_de_restauration_conserve_le_projet_et_permet_de_reessayer(self):
        s, _ = _ouvrage()
        fichier = os.path.join(self.dossier, "fictif.json")
        s.enregistrer(fichier)
        original = open(fichier, "rb").read()
        _nouveau_referentiel(s)
        s.adopter_referentiel(["EV"], renommages_confirmes=True)
        s.enregistrer(fichier)
        adopte = open(fichier, "rb").read()
        catalogue_adopte = copy.deepcopy(s.catalogue.signaux)
        with patch('genvar.adoption.os.replace', side_effect=PermissionError("Essai fictif de fichier verrouillé")):
            with self.assertRaises(PermissionError):
                s.annuler_adoption(enregistrer=True)
        self.assertEqual(open(fichier, "rb").read(), adopte)
        self.assertEqual(s.catalogue.signaux, catalogue_adopte)
        self.assertTrue(s.annuler_adoption(enregistrer=True))
        self.assertEqual(open(fichier, "rb").read(), original)


class TestAdoptionHTTP(Base):
    def setUp(self):
        super().setUp()
        from sorep_web.serveur import demarrer
        serveur, self.url, self.app = demarrer(ouvrir_navigateur=False, port=0)
        self.url = f"http://127.0.0.1:{serveur.server_address[1]}/"
        thread = threading.Thread(target=serveur.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(serveur.server_close)
        self.addCleanup(thread.join, 5)
        self.addCleanup(serveur.shutdown)
        self.app.s, _ = _ouvrage()
        self.fichier = os.path.join(self.dossier, "fictif.json")
        self.app.s.enregistrer(self.fichier)
        self.original = open(self.fichier, "rb").read()
        _nouveau_referentiel(self.app.s)
        self.app.ouvert = True

    def appel(self, route, donnees=None):
        req = urllib.request.Request(self.url + route.lstrip("/"),
                                     data=None if donnees is None else json.dumps(donnees).encode(),
                                     headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req) as r:
                return r.status, json.load(r)
        except urllib.error.HTTPError as e:
            return e.code, json.load(e)

    def choix(self):
        ref = self.appel("/api/ouvrage")[1]["referentiel"]
        ev = next(t for t in ref["adoption"] if t["type"] == "EV")
        return {"types": ["EV"], "renommages_confirmes": True, "empreinte": ref["empreinte_adoption"],
                "confirmations": [r["id"] for e in ev["details_equipements"] for r in e["renommages"]]}

    def test_confirmation_individuelle_verifiee_par_le_serveur(self):
        choix = self.choix()
        self.assertTrue(choix["confirmations"])
        choix["confirmations"] = []
        code, erreur = self.appel("/api/referentiel/adopter", choix)
        self.assertEqual(code, 400)
        self.assertIn("chaque renommage", erreur["erreur"])
        self.assertEqual(open(self.fichier, "rb").read(), self.original)
        self.assertIsNone(self.app.s._avant_adoption)

    def test_apercu_perime_refuse_sans_ecriture(self):
        choix = self.choix()
        self.app.s.ouvrage.libelle = "Autre modification fictive"
        code, erreur = self.appel("/api/referentiel/adopter", choix)
        self.assertEqual(code, 400)
        self.assertIn("a changé", erreur["erreur"])
        self.assertEqual(open(self.fichier, "rb").read(), self.original)

    def test_sans_selection_pas_d_enregistrement_implicite(self):
        self.assertEqual(self.appel("/api/referentiel/adopter", {"types": []})[0], 200)
        self.assertEqual(open(self.fichier, "rb").read(), self.original)

    def test_parametres_malformes_refuses_sans_ecriture(self):
        for champs in ({"types": "EV"}, {"types": [{}]},
                       {"types": ["EV"], "confirmations": [{}], "renommages_confirmes": True}):
            with self.subTest(champs=champs):
                self.assertEqual(self.appel("/api/referentiel/adopter", champs)[0], 400)
                self.assertEqual(open(self.fichier, "rb").read(), self.original)

    def test_ouvrage_non_enregistre_refuse_pour_garantir_la_sauvegarde(self):
        choix = self.choix()
        self.app.creation_en_attente = True
        code, erreur = self.appel("/api/referentiel/adopter", choix)
        self.assertEqual(code, 400)
        self.assertIn("Enregistrez", erreur["erreur"])
        self.assertEqual(open(self.fichier, "rb").read(), self.original)

    def test_sauvegarde_telechargeable_et_annulation_exacte(self):
        self.assertEqual(self.appel("/api/referentiel/adopter", self.choix())[0], 200)
        adopte = open(self.fichier, "rb").read()
        self.assertNotEqual(adopte, self.original)
        # Un paramètre chemin ne permet pas de sélectionner un autre fichier.
        url = self.url + "api/export?quoi=sauvegarde_adoption&chemin=/etc/passwd"
        with urllib.request.urlopen(url) as r:
            self.assertEqual(r.headers.get_content_type(), "application/json")
            self.assertEqual(r.read(), self.original)
        self.assertEqual(self.appel("/api/referentiel/annuler-adoption", {})[0], 200)
        self.assertEqual(open(self.fichier, "rb").read(), self.original)
        with urllib.request.urlopen(self.url + "api/export?quoi=sauvegarde_annulation_adoption") as r:
            self.assertEqual(r.read(), adopte)
        self.assertFalse(self.appel("/api/ouvrage")[1]["referentiel"]["adoption_annulable"])

    def test_modele_fige_ne_promet_pas_un_renommage_inexistant(self):
        eq = next(e for e in self.app.s.ouvrage.equipements if e.type == "EV")
        eq.modele = "Modèle fictif figé"
        self.app.s.ouvrage.modeles_snapshot[eq.modele] = {
            "type": "EV", "signaux": copy.deepcopy(self.app.s.catalogue.signaux_du_type("EV"))}
        ev = next(t for t in self.appel("/api/ouvrage")[1]["referentiel"]["adoption"] if t["type"] == "EV")
        self.assertTrue(ev["details_equipements"][0]["modele_fige"])
        self.assertEqual(ev["details_equipements"][0]["renommages"], [])

    def test_modele_fige_avec_changement_de_cle_bloque(self):
        eq = next(e for e in self.app.s.ouvrage.equipements if e.type == "GA")
        eq.modele = "Modèle fictif figé"
        self.app.s.ouvrage.modeles_snapshot[eq.modele] = {
            "type": "GA", "signaux": copy.deepcopy(self.app.s.catalogue.signaux_du_type("GA"))}
        code, erreur = self.appel("/api/referentiel/adopter", {"types": ["GA"], "renommages_confirmes": True})
        self.assertEqual(code, 400)
        self.assertIn("migration de clé dédiée", erreur["erreur"])
        self.assertEqual(open(self.fichier, "rb").read(), self.original)


class TestCorrespondances(unittest.TestCase):
    def setUp(self):
        self.cat = Catalogue.charger(chemins.fichier_catalogue_origine())

    def test_controles(self):
        ok = [{"type": "GA", "ancienne": "TS_ANCIEN", "nouvelle": "TS_INTR"}]
        self.assertEqual(adoption.controler_correspondances(ok, self.cat), [])
        erreurs = adoption.controler_correspondances(
            [{"type": "GA", "ancienne": "TS_INTR", "nouvelle": "TS_INTR"},       # ancienne encore en service
             {"type": "GA", "ancienne": "TS_X", "nouvelle": "TS_ABSENT"},        # nouvelle absente
             {"type": "GA", "ancienne": "TS_X", "nouvelle": "TS_PORTE"},         # ancienne citée deux fois
             {"type": "GA", "ancienne": "TS_Y", "nouvelle": "TS_PORTE"},         # nouvelle visée deux fois
             {"type": "GA"}], self.cat)
        self.assertEqual(len(erreurs), 5)
        self.assertEqual(adoption.controler_correspondances("x", self.cat), ["Correspondances : liste attendue."])
