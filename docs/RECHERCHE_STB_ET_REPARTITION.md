# Recherche — gamme Advantys STB et bonnes pratiques de répartition des E/S (12/11/2026)

Demandée par l'utilisateur après l'essai de la 0.32 (retours 8 et 10). Sources consultées le 12/11/2026.

## 1. Gamme Advantys STB (Schneider Electric)

### Statut commercial — point d'attention

Fiche officielle du `STBNIP2212` (se.com, 12/11/2026) : « **Commercialisé avec annonce fin de vie** » ;
**fin de fabrication le 1er décembre 2027** ; service standard jusqu'au 31 décembre 2035 ; remplacement
recommandé : **`NTSNEC1200K`** (Edge I/O NTS, tête de station EtherNet/IP et Modbus TCP, 100 Mbit/s).
Conséquence pour les régies : un **projet neuf** en STB s'expose à une gamme arrêtée dans un an ; la prise en
charge STB dans OGIAS sert surtout **l'existant**. À arbitrer (S1).

### Références confirmées par les pages produit officielles se.com

Désignation telle que publiée par Schneider Electric (le suffixe `K`, `KS`, `KC` désigne un kit
module + embase + connecteurs).

| Rôle | Référence | Désignation officielle (résumé) |
| --- | --- | --- |
| Interface réseau (NIM) | STBNIP2212 | Module d'interface réseau standard, Ethernet 10 Mbit/s ; 1 segment principal + 6 d'extension maxi |
| Distribution d'alimentation | STBPDT3100K | Module standard de distribution 24 VCC (kit) |
| Distribution d'alimentation | STBPDT2100K | Module standard de distribution 115-230 VCA (kit) |
| Entrées TOR | STBDDI3725 | Module de base, 16 entrées 24 VCC, 2/3 fils, IEC type 3 |
| Entrées TOR | STBDDI3425K | Kit d'entrées numériques de base, 24 VCC, 4 E |
| Sorties TOR | STBDDO3705 | Module de base, 16 sorties 24 VCC, 0,5 A, logique positive |
| Sorties TOR | STBDDO3605K | Kit de sorties de base, 24 VCC, 6 S |
| Sorties TOR | STBDDO3230K | Kit de sorties standard, 24 VCC, 2 S |
| Sorties relais | STBDRA3290K | 2 sorties relais 24 VCC / 115-220 VCA, 7 A |
| Entrées analogiques | STBACI1400K | 8 entrées 0(4)-20 mA, 15 bits + signe |
| Entrées analogiques | STBACI0320K | 4 entrées 0(4)-20 mA, 15 bits + signe |
| Entrées analogiques | STBACI8320K | 4 entrées 4-20 mA, 15 bits + signe |
| Entrées analogiques | STBAVI1400K | 8 entrées ±10 V, 15 bits + signe |
| Entrées analogiques | STBAVI1270K | 2 entrées ±10 V, 9 bits + signe |
| Entrées analogiques | STBAVI1255 | 2 entrées 0-10 V, 10 bits, de base |
| Entrées température | STBART0200 | 2 entrées RTD / thermocouple / mV, isolées, 16 bits |
| Sorties analogiques | STBAVO1250K | 2 sorties ±10 V, 12 bits |
| Sorties analogiques | STBACO8220K | 2 sorties 4-20 mA HART, 16 bits |

### Intégré le 12/11/2026 (`genvar/data/materiel_stb.json`)

À la demande de l'utilisateur (page de gamme se.com), le catalogue a été établi à partir des **guides de
référence Schneider** : [31002947 (E/S TOR)](https://download.se.com/files?p_Doc_Ref=31002947K01000&p_File_Name=31002947K01000.pdf&p_enDocType=User+guide)
et [31002948 (E/S analogiques)](https://download.se.com/files?p_Doc_Ref=31002948K01000), et de la
[fiche STBNIP2212](https://bpx.ie/dbdocument/105659/STBNIP2212.pdf) : 31 modules (voies, embase, courant du bus
logique de 0 à 60 °C), NIM (1 200 mA, 32 modules d'E/S, 6 segments d'extension, Modbus TCP 10 Mbit/s), PDM
`STB PDT 3100` sur embase `STB XBA 2200`, plaque `STB XMP 1100`, extension `STB XBE 1000` / `1200`.
`STB DDO 3410` : **4 sorties** 0,5 A (le titre « 2 S » d'une page se.com est une erreur). La page de gamme
se.com ne liste pas les références sans JavaScript : la liste vient des guides. Reste à confirmer : courant
logique fourni par un module BOS ; correspondance des voies d'un îlot avec les mots de l'automate maître
(scrutation Modbus TCP), sans laquelle OGIAS ne propose aucune adresse.

### Paramétrage dans le logiciel Advantys (précision de l'utilisateur, 12/11/2026)

Le paramétrage d'un îlot se fait dans le **logiciel Advantys** (capture fournie : îlot STBNIP2212, STBPDT3100,
STBDDO3600, STBDDI3610, STBXMP1100, téléchargé dans le NIM ; automate maître M340 avec BMX NOC). Numérotation
affichée « emplacement / nœud » : `1/127` NIM, `2/-` PDM, `3/1`, `4/2` modules d'E/S, `5/-` terminaison. OGIAS
propose la composition dans cet ordre et avec ces numéros (`racks[i].composition`). La lecture des E/S par le
BMX NOC (scrutation Modbus TCP vers %MW) dépend de l'image d'E/S de l'îlot affichée par Advantys : document
attendu (image d'E/S d'un îlot réel anonymisé, et scrutation correspondante dans Control Expert) avant toute
proposition d'adresse.

### Image d'E/S de l'îlot (capture Advantys de l'utilisateur et guide STB NIP 2212)

Capture de l'utilisateur : `STBDAI5230`, segment 1, logement 3, nœud 1, « Données d'entrée » en **45392**
(voies 1 et 2 dans ce registre). Concorde avec le [guide STB NIP 2212 (31003688)](https://www.mroelectric.com/static/app/product/pdfs/31003688_K01_000_11.pdf) :
image de sortie à partir de **40001**, image d'entrée à partir de **45392**, dans l'ordre des nœuds ; entrée TOR
= donnée + état, sortie TOR = 1 registre de sortie + écho et état en entrée, entrée analogique = donnée + état
par voie, sortie analogique = 1 registre par voie + état par voie. OGIAS calcule ces registres
(`materiel.image_ilot`, `racks[i].image_es`) pour les 8 modules dont le guide donne le format ; pour tout autre
module, le calcul s'arrête (rien n'est deviné). À confirmer : rang du bit de chaque voie TOR ; format d'image
des autres modules (onglet « Image d'E/S » d'Advantys, un module par capture suffit) ; table de scrutation du
BMX NOC (registre lu → %MW) pour aller jusqu'à l'adresse automate.

Captures complémentaires de l'utilisateur (12/11/2026, 14 h 13) : `STB DDI 3725` (1/3/1) : 16 voies dans
45392, sans état ; `STB DDO 3705` (1/3/1) : sortie 40001, aucun registre d'entrée ; `STB ACI 1400` (1/4/2) :
45392 à 45407, donnée puis état par voie ; `STB ACO 0220` (1/5/3) : états 45408 et 45409, sorties 40002 et
40003. Recoupement : dans le même îlot, le `DDO 3705` (nœud 1) n'occupe aucun registre d'entrée, l'`ACI 1400`
commence donc en 45392 et les sorties de l'`ACO 0220` suivent 40001. Le profil proposé par défaut est donc
entièrement calculable, voie par voie (`image_es[].voies`). Restent : rang du bit d'une voie TOR, table de
scrutation du BMX NOC.

### Décision de l'utilisateur (12/11/2026, 15 h 24)

**Périmètre STB arrêté aux registres Modbus de l'îlot** : OGIAS ne va pas jusqu'aux adresses %MW de l'automate
maître (scrutation BMX NOC) ni au rang du bit des voies TOR. Aucune capture supplémentaire n'est attendue ;
ne pas relancer l'utilisateur sur ce point.

### À vérifier sur les fiches techniques avant toute intégration (état initial)

- **Incohérence relevée** : une page se.com (Canada) titre `STBDDO3410` « 2 S » alors que la numérotation
  suggère 4 sorties : à contrôler sur la fiche technique ; ne pas intégrer avant.
- Embases (`STBXBA1000`, `2000`, `3000`), plaque de terminaison (`STBXMP1100`), consommation sur le bus
  logique (FAQ Schneider FA198272), limites de l'îlot (nombre de modules, courant par segment), modules
  `STBDDI3230`, `3420`, `3610` et `STBDDO3200`, `3410`, `3600` : non confirmés à ce jour.
- Règle : **aucune caractéristique n'est intégrée sans fiche constructeur citée** ; à défaut, statut
  « à confirmer » visible dans OGIAS.

Sources : [STBNIP2212 (se.com)](https://www.se.com/fr/fr/product/STBNIP2212/) ·
[STBDDI3725](https://www.se.com/be/fr/product/STBDDI3725/modicon-stb-module-de-base-entr%C3%A9es-tor-+-connecteurs-16-entr%C3%A9es-24vcc-2-3-fils-iec-type3/) ·
[STBDDO3705](https://www.se.com/be/fr/product/STBDDO3705/modicon-stb-module-de-base-sorties-tor-16-sorties-24vcc-05a-logique-positive/) ·
[STBACI1400K](https://www.se.com/be/fr/product/STBACI1400K/modicon-stb-8-entr%C3%A9es-analogiques-0420-ma-15-bit-+-signe-kit-module-embase-connecteurs/) ·
[STBACI0320K](https://www.se.com/be/fr/product/STBACI0320K/modicon-stb-4-entr%C3%A9es-analogiques-0420ma-15-bit-+-signe-kit-module-embase-connecteurs/) ·
[STBACO8220K](https://www.se.com/be/fr/product/STBACO8220K/modicon-stb-2-sorties-analogiques-hart-420ma-16-bits-kit-module-embase-connecteurs/) ·
[STBDRA3290K](https://www.se.com/be/fr/product/STBDRA3290K/modicon-stb-module-de-sorties-tor-+-connecteurs-2-sorties-relais-24vcc-115220vca-7a/) ·
[STBPDT3100K](https://se.com/be/fr/product/STBPDT3100K) · [STBPDT2100K](https://se.com/be/fr/product/STBPDT2100K) ·
[STBART0200](https://www.se.com/fr/fr/product/STBART0200/analog-in-2ch-rtd-tc-mv-iso-16-bit) ·
[STBAVI1255](https://www.se.com/fr/fr/product/STBAVI1255/analog-v-in-2ch-010v-sglend-10bit-bsc) ·
[STBAVI1270K](https://se.com/be/fr/product/STBAVI1270K) ·
[STBAVO1250K](https://www.se.com/us/en/product/STBAVO1250K/analog-output-kit-modicon-stb-standard-+-10v-2-o-12bits/) ·
[STBACI8320K](https://www.se.com/us/en/product/STBACI8320K/analog-input-kit-modicon-stb-standard-420ma-4-i-15bits-with-sign/) ·
[STBDDI3425K](https://www.se.com/ca/fr/product/STBDDI3425K/trousse-dentr%C3%A9e-num%C3%A9rique-modicon-stb-de-base-24-vcc-4-e/) ·
[STBDDO3605K](https://www.se.com/au/en/product/STBDDO3605K/digital-output-kit-modicon-stb-basic-24v-dc-6-o/) ·
[STBDDO3230K](https://www.se.com/fr/fr/product/STBDDO3230K/advantys-stb---kit-de-sorties-numériques-standard---24vcc---2-s/) ·
[FAQ FA198272 (consommation bus logique)](https://www.se.com/uk/en/faqs/FA198272).

## 2. Bonnes pratiques de répartition des E/S

Synthèse des pratiques d'ingénierie couramment admises. **Aucune norme n'impose la ségrégation** des E/S
sur les cartes : ce sont des choix de conception (sources : [Stream-wise segregation](https://industrialmonitordirect.com/blogs/knowledgebase/io-card-sizing-stream-wise-segregation-requirements),
[I/O reserve practices](https://industrialmonitordirect.com/blogs/knowledgebase/plc-io-reserve-calculation-methods-and-industry-best-practices) ;
normes citées : IEC 61131-2, ISA-84 / IEC 61511 pour la séparation des fonctions de sécurité).

| N° | Pratique | Règle retenue pour OGIAS (lot M5) |
| --- | --- | --- |
| B1 | Cartes homogènes par type de signal (ET, ST, EA, SA, température, comptage), niveaux de tension séparés | Déjà appliqué (une carte = une nature) ; 24 VCC et 230 VCA jamais sur la même carte |
| B2 | Réserve de 15 à 20 % de voies libres par carte ; infrastructure 15 à 20 % | Réserve par carte paramétrable, **20 % par défaut** (déjà en place) |
| B3 | Emplacements libres dans le rack (au moins 1 à 3) ou nœuds réservés en E/S distantes | **Nouveau** : emplacements libres par rack paramétrables (proposé : 2), signalés s'ils manquent |
| B4 | Ségrégation par file / équipement redondant : une panne de carte ne doit pas arrêter un équipement **et** son secours | **Nouveau, activé par défaut, désactivable par ouvrage** : les équipements d'un même **groupe de secours** (marche / secours, n+1, files parallèles) sur des **cartes distinctes**, et si possible des racks / alimentations distincts |
| B5 | Regroupement par équipement : lisibilité, maintenance, câblage | Conservé : les E/S d'un équipement restent groupées sur une carte, voies contiguës, ordre stable |
| B6 | Fonctions de sécurité (SIS) physiquement séparées du contrôle de procédé | Hors périmètre d'OGIAS ; alerte si une E/S marquée sécurité est mêlée aux autres |
| B7 | Extension / rétrofit : conserver l'organisation existante | Déjà appliqué : une E/S validée sur sa voie ne bouge plus ; aucune réaffectation silencieuse |
| B8 | Documenter la logique de répartition | Motif de chaque affectation visible (règle appliquée) et repris dans le dossier de recette |

**Groupe de secours (B4)** : OGIAS ne le devine pas en silence. Il **propose** les groupes probables
(équipements de même type dans le même sous-ensemble, par exemple PM01 / PM02) ; l'automaticien les confirme,
les corrige ou les refuse ; la répartition n'utilise que les groupes confirmés.

Ordre de priorité des règles en cas de conflit : B7 (ne jamais déplacer l'existant validé) > B1 > B4 > B5 >
B2 > B3. Un conflit non résoluble est signalé, jamais tranché silencieusement.
