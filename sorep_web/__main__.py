import sys

from .serveur import demarrer

serveur, url, _ = demarrer(ouvrir_navigateur="--sans-navigateur" not in sys.argv)
print(f"OGIAS est ouvert dans votre navigateur : {url}")
print("Laissez cette fenêtre ouverte pendant le travail ; fermez-la pour quitter OGIAS.", flush=True)
try:
    serveur.serve_forever()
except KeyboardInterrupt:
    pass
