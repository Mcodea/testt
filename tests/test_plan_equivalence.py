"""Le parcours accéléré doit rendre exactement le premier emplacement historique."""
import random
from dataclasses import asdict
from unittest.mock import patch

import pytest

from genvar.catalogue import Catalogue
from genvar.modele import (Equipement, Memoire, Ouvrage, SignalPropre,
                           appliquer_plan, plan_adresses, zone, ORDRE_ZONES)


@pytest.mark.parametrize("seed", range(12))
def test_plan_identique_au_parcours_depuis_le_debut(seed):
    randomizer = random.Random(seed)
    catalogue = Catalogue(types=[{"code": "HV", "designation": "Vanne fictive"}])
    ouvrage = Ouvrage(lieu="XTST", code_ouvrage="RV", numero_ouvrage="01")
    for i in range(25):
        signaux = [SignalPropre("Signal fictif", famille, f"V{j:02d}",
                               randomizer.choice(["BOOL", "INT", "REAL"]) if famille in ("TS", "TC") else "INT")
                   for j, famille in enumerate(randomizer.choices(["TS", "TC", "TM", "CP"], k=12))]
        # Une paire TR/RTR conserve le même code et la même largeur.
        signaux += [SignalPropre("Consigne fictive", f, "CONS", "REAL") for f in ("TR", "RTR")]
        ouvrage.equipements.append(Equipement("00", "HV", f"{i+1:02d}", ajouts=signaux))
    reservations = [(zone(ouvrage, famille)[0] + 4, zone(ouvrage, famille)[0] + 5, "Essai fictif")
                    for famille in ORDRE_ZONES]
    premier_bit = Memoire.premier_bit
    debuts = {zone(ouvrage, f)[1]: zone(ouvrage, f)[0] for f in ORDRE_ZONES}

    def historique(memoire, debut, fin):
        return premier_bit(memoire, debuts[fin], fin)

    def comparer():
        avant = asdict(ouvrage)
        rapide = plan_adresses(ouvrage, catalogue, reservations=reservations)
        with patch.object(Memoire, "premier_bit", historique):
            ancien = plan_adresses(ouvrage, catalogue, reservations=reservations)
        assert rapide == ancien
        assert asdict(ouvrage) == avant
        return rapide

    propositions, erreurs = comparer()
    assert not erreurs
    # Conserver une affectation sur trois, dont plusieurs adresses protégées.
    appliquer_plan(ouvrage, propositions[::3])
    for p in propositions[::9]:
        ouvrage.equipement(p.variable.ident_eq).validees.append(p.variable.cle)
    comparer()
