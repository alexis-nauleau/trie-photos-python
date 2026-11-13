
"""Range les photos par année/mois, d'après la date de prise de vue (EXIF).
Par défaut : SIMULATION (rien n'est déplacé). Ajouter --appliquer pour de vrai."""

# ---------- IMPORTS : on va chercher des outils déjà écrits par d'autres ----------

import argparse   # lit ce qu'on tape dans le terminal après le nom du script
import shutil     # sert à déplacer des fichiers
from datetime import datetime   # sert à manipuler des dates
from pathlib import Path        # sert à manipuler des chemins de fichiers proprement

# PIL est le nom (historique) de la bibliothèque Pillow
# Image sert à ouvrir une photo et à lire ses informations cachées.
from PIL import Image

# ---------- RÉGLAGE : les types de fichiers qu'on veut ranger ----------

# Les accolades { } créent un "set" : une collection de valeurs sans doublons.
# C'est pratique pour répondre vite à la question "est-ce que cette extension est dans la liste ?"
EXTENSIONS = {".jpg", ".jpeg", ".png", ".mp4", ".mov"}


# ---------- FONCTION 1 : lire la date de prise de vue d'une photo ----------

def date_prise_de_vue(chemin):
    """Renvoie la date de prise de vue lue dans l'EXIF, ou None si elle est absente."""
    # EXIF = les informations cachées dans une photo 

    # "try" : on essaie de lire la photo.
    try:
        # "with ... as image" ouvre le fichier et le REFERME tout seul à la fin du bloc.
        with Image.open(chemin) as image:
            exif = image.getexif()   # récupère toutes les informations cachées
            # Les infos EXIF sont rangées sous des numéros :
            #   36867 = date de prise de vue (elle est dans un sous-bloc, numéro 0x8769)
            #   306   = date générale (un peu moins précise)
            # 0x8769 est un nombre écrit en hexadécimal (base 16). C'est juste un numéro de bloc.
            # "A or B" veut dire : prends A, et si A est vide, prends B.
            texte = exif.get_ifd(0x8769).get(36867) or exif.get(306)
    except Exception:

        return None

    # Si la photo n'avait aucune date, "texte" est vide.
    # "not texte" est vrai quand texte est vide ou None.
    if not texte:
        return None

    # Le texte ressemble à "2024:02:14 10:30:00". On le transforme en vraie date.
    try:
        # strptime = "string parse time" : lit un texte selon un modèle.
        # %Y = année, %m = mois, %d = jour, %H = heure, %M = minute, %S = seconde.
        # str(texte).strip() : on s'assure que c'est du texte, et on enlève les espaces autour.
        return datetime.strptime(str(texte).strip(), "%Y:%m:%d %H:%M:%S")
    except ValueError:
        # ValueError = le texte ne respecte pas le modèle (par exemple "0000:00:00 00:00:00").
        return None


# ---------- FONCTION 2 : trouver un nom de destination qui n'existe pas encore ----------

def destination_libre(chemin):
    """Si le fichier existe déjà, ajoute _1, _2... pour ne JAMAIS écraser."""
    # Si rien n'existe à cet endroit, on peut l'utiliser tel quel.
    if not chemin.exists():
        return chemin

    numero = 1   # on va essayer _1, puis _2, puis _3...
    # "while True" = boucle qui tourne sans fin... jusqu'à ce qu'un "return" l'arrête.
    while True:
        # f"..." est une "f-string" : les {accolades} sont remplacées par leur valeur.
        # chemin.stem   = le nom sans l'extension      (IMG_001)
        # chemin.suffix = l'extension, avec le point   (.jpg)
        # with_name(...) fabrique un chemin identique mais avec un autre nom de fichier.
        candidat = chemin.with_name(f"{chemin.stem}_{numero}{chemin.suffix}")
        if not candidat.exists():
            return candidat      # trouvé : ce nom est libre, on le renvoie et la boucle s'arrête
        numero += 1              # sinon on essaie le numéro suivant (numero = numero + 1)


# ---------- FONCTION 3 : le programme principal ----------

def main():
    # --- 1. Lire ce que l'utilisateur a tapé dans le terminal ---
    # argparse crée la "porte d'entrée" du script. Quand tu écris :
    #     python ranger_photos.py testphotos --appliquer
    # argparse comprend que "testphotos" est le dossier et que "--appliquer" est une option.
    parser = argparse.ArgumentParser(description="Range les photos par date de prise de vue.")
    parser.add_argument("dossier", help="dossier contenant les photos")
    # action="store_true" : l'option est False par défaut, et devient True si on l'écrit.
    # C'est ce qui fait que, sans --appliquer, on reste en simulation.
    parser.add_argument("--appliquer", action="store_true",
                        help="déplace vraiment les fichiers (sinon : simulation)")
    args = parser.parse_args()   # lit vraiment la ligne tapée ; "args" contient les réponses

    # --- 2. Vérifier que le dossier existe ---
    dossier = Path(args.dossier)      # transforme le texte tapé en vrai chemin
    if not dossier.is_dir():          # is_dir() = "est-ce un dossier qui existe ?"
        print(f"Dossier introuvable : {dossier}")
        return                        # "return" sans valeur = on arrête la fonction ici

    # --- 3. Lister les fichiers à ranger ---
    # dossier.iterdir() donne tout ce qui se trouve dans le dossier.
    # On garde seulement ce qui est un fichier (is_file) ET dont l'extension est dans notre liste.
    # suffix donne ".JPG" : lower() le met en minuscules pour que ".JPG" et ".jpg" soient traités pareil.
    # sorted(...) range le résultat par ordre alphabétique.
    fichiers = sorted(p for p in dossier.iterdir()
                      if p.is_file() and p.suffix.lower() in EXTENSIONS)
    if not fichiers:    # la liste est vide
        print("Aucune photo ou vidéo trouvée dans ce dossier.")
        return

    # --- 4. Annoncer le mode ---
    # Cette ligne est une condition sur une seule ligne :
    #   print( texte_A  if condition  else  texte_B )
    print("MODE : DÉPLACEMENT RÉEL" if args.appliquer else "MODE : SIMULATION (rien n'est déplacé)")
    print()   # une ligne vide, pour aérer

    # --- 5. Traiter chaque fichier ---
    avec_date = 0    # compteur : combien de photos ont une date
    sans_date = 0    # compteur : combien n'en ont pas

    # "for ... in ..." répète le bloc pour chaque fichier de la liste, un par un.
    for fichier in fichiers:
        date = date_prise_de_vue(fichier)   # on appelle la fonction écrite plus haut

        # Si "date" contient quelque chose (donc pas None), on a une vraie date.
        if date:
            # Construction du sous-dossier, par exemple : 2024 / 2024-02
            # Le symbole "/" entre deux Path colle les morceaux avec le bon séparateur Windows (\).
            # date.year  = l'année (2024)
            # date.month = le mois (2). Dans f"{...:02d}", ":02d" veut dire "toujours 2 chiffres" -> 02
            sous_dossier = Path(str(date.year)) / f"{date.year}-{date.month:02d}"
            avec_date += 1       # même chose que : avec_date = avec_date + 1
        else:
            # Pas de date : on ne devine pas, on met dans un dossier à part.
            sous_dossier = Path("Sans_date")
            sans_date += 1

        # Chemin final du fichier : dossier choisi / sous-dossier / nom du fichier.
        # destination_libre garantit qu'on n'écrasera aucun fichier existant.
        cible = destination_libre(dossier / sous_dossier / fichier.name)

        # On affiche toujours ce qui va se passer (ou ce qui se passe).
        # relative_to(dossier) raccourcit l'affichage : on enlève le début du chemin.
        print(f"{fichier.name}  ->  {cible.relative_to(dossier)}")

        # Le déplacement réel n'a lieu QUE si on a écrit --appliquer.
        if args.appliquer:
            # Crée les dossiers qui manquent (parents=True : tous les niveaux ;
            # exist_ok=True : pas d'erreur s'ils existent déjà).
            cible.parent.mkdir(parents=True, exist_ok=True)
            # Déplace le fichier. str(...) transforme les chemins en texte, ce que shutil attend.
            shutil.move(str(fichier), str(cible))

    # --- 6. Résumé final ---
    print()
    # len(fichiers) = le nombre d'éléments dans la liste
    print(f"{len(fichiers)} fichier(s) : {avec_date} avec date EXIF, {sans_date} sans date.")
    if not args.appliquer:
        print("Simulation terminée. Relance avec --appliquer pour déplacer.")


# ---------- DÉMARRAGE ----------

# Cette ligne veut dire : "lance main() seulement si on exécute CE fichier directement"
# (et pas si un autre fichier l'importe pour utiliser ses fonctions).
if __name__ == "__main__":
    main()