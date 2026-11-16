# ============================================================
# ranger_photos.py : range les photos par année
# - Avec un dossier en argument : fonctionne dans le terminal (simulation par défaut).
# - Sans argument (double-clic sur l'exe) : choisis le dossier dans une fenêtre,
#   regarde la simulation, puis confirme.
# ============================================================

# ---------- IMPORTS ----------
import argparse                  # Lire les arguments écrits dans le terminal
import re                        # Chercher un motif dans un texte (dates WhatsApp)
import shutil                    # Déplacer des fichiers
from datetime import datetime    # Manipuler les dates
from pathlib import Path         # Manipuler les chemins de fichiers
from PIL import Image            # Lire les images et leurs informations EXIF

# Extensions des fichiers que l'on souhaite ranger
EXTENSIONS = {".jpg", ".jpeg", ".png", ".mp4", ".mov"}

# Les deux façons dont WhatsApp écrit la date dans le nom d'un fichier
MOTIFS_WHATSAPP = [
    re.compile(r"-(\d{4})(\d{2})(\d{2})-WA\d+"),                      # IMG-20200314-WA0012.jpg
    re.compile(r"WhatsApp (?:Image|Video) (\d{4})-(\d{2})-(\d{2})"),  # WhatsApp Image 2020-03-14 at ...
]


# ---------- FONCTIONS DE LECTURE DES DATES ----------
def date_prise_de_vue(chemin):
    """Date de prise de vue lue dans l'EXIF, ou None."""
    try:
        with Image.open(chemin) as image:
            exif = image.getexif()
            # 36867 = date de prise de vue ; 306 = date de modification EXIF (secours)
            date = exif.get_ifd(0x8769).get(36867) or exif.get(306)
            if date:
                return datetime.strptime(str(date).strip(), "%Y:%m:%d %H:%M:%S")
    except Exception:
        pass    # vidéo, image abîmée, date mal formée... : on continue sans date
    return None


def date_whatsapp(nom):
    """Date écrite dans un nom de fichier WhatsApp, ou None."""
    for motif in MOTIFS_WHATSAPP:
        trouve = motif.search(nom)
        if trouve:
            annee, mois, jour = (int(x) for x in trouve.groups())
            try:
                return datetime(annee, mois, jour)
            except ValueError:
                return None     # date impossible (par exemple mois 13)
    return None


def trouver_date(chemin):
    """Renvoie (date, source) : EXIF d'abord, puis nom WhatsApp, sinon (None, ...)."""
    date = date_prise_de_vue(chemin)
    if date:
        return date, "EXIF"
    date = date_whatsapp(chemin.name)
    if date:
        return date, "nom WhatsApp"
    return None, "aucune date"


def destination_libre(chemin):
    """Trouve un nom disponible : photo.jpg, puis photo_1.jpg, photo_2.jpg..."""
    original = chemin
    numero = 1
    while chemin.exists():
        chemin = original.with_name(f"{original.stem}_{numero}{original.suffix}")
        numero += 1
    return chemin


# ---------- LE RANGEMENT ----------
def ranger(dossier, appliquer):
    """Parcourt le dossier, affiche ce qui est prévu, et déplace si appliquer est True.
    Renvoie le nombre de fichiers trouvés (0 s'il n'y a rien à ranger)."""
    fichiers = sorted(
        fichier for fichier in dossier.iterdir()
        if fichier.is_file() and fichier.suffix.lower() in EXTENSIONS
    )
    if not fichiers:
        print("Aucun fichier trouvé.")
        return 0

    compteurs = {"EXIF": 0, "nom WhatsApp": 0, "aucune date": 0}
    print("MODE :", "DÉPLACEMENT RÉEL" if appliquer else "SIMULATION")
    print()

    for fichier in fichiers:
        date, source = trouver_date(fichier)
        compteurs[source] += 1

        # Un seul dossier par année ; sans date : Sans_date
        sous_dossier = Path(str(date.year)) if date else Path("Autre")
        cible = destination_libre(dossier / sous_dossier / fichier.name)
        print(f"{fichier.name} -> {cible.relative_to(dossier)}  [{source}]")

        if appliquer:
            cible.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(fichier), str(cible))

    print()
    print(f"{len(fichiers)} fichiers traités.")
    print(f"{compteurs['EXIF']} avec date EXIF (date de prise de vue).")
    print(f"{compteurs['nom WhatsApp']} avec date lue dans le nom (WhatsApp).")
    print(f"{compteurs['aucune date']} sans date (dossier Sans_date).")
    return len(fichiers)


# ---------- MODE INTERACTIF (double-clic) ----------
def choisir_dossier():
    """Ouvre une fenêtre de choix de dossier. Renvoie le chemin, ou "" si annulé."""
    # tkinter n'est importé qu'ici : le mode terminal n'en a pas besoin
    import tkinter as tk
    from tkinter import filedialog

    fenetre = tk.Tk()
    fenetre.withdraw()                        # cache la petite fenêtre vide de tkinter
    fenetre.attributes("-topmost", True)      # la fenêtre de choix passe au premier plan
    chemin = filedialog.askdirectory(title="Choisis le dossier de photos à ranger")
    fenetre.destroy()
    return chemin


def attendre():
    """Garde la fenêtre noire ouverte pour que l'utilisateur ait le temps de lire."""
    input("\nAppuie sur Entrée pour fermer...")


# ---------- PROGRAMME PRINCIPAL ----------
def main():
    parser = argparse.ArgumentParser(description="Ranger les photos par année.")
    # nargs="?" : le dossier devient facultatif
    parser.add_argument("dossier", nargs="?",
                        help="Dossier contenant les photos (sinon, une fenêtre te le demande)")
    parser.add_argument("--appliquer", action="store_true",
                        help="Déplace vraiment les fichiers (sinon : simulation)")
    args = parser.parse_args()

    # --- Mode terminal : comme avant ---
    if args.dossier:
        dossier = Path(args.dossier)
        if not dossier.is_dir():
            print("Dossier introuvable.")
            return
        ranger(dossier, args.appliquer)
        if not args.appliquer:
            print("Simulation terminée. Ajoute --appliquer pour déplacer les fichiers.")
        return

    # --- Mode interactif : pour quelqu'un qui double-clique sur l'exe ---
    print("=== RANGEMENT DE PHOTOS PAR ANNÉE ===")
    print("Attention : les fichiers sont DÉPLACÉS (pas copiés).")
    print("Pense à faire une copie de sauvegarde avant de continuer.\n")

    choix = choisir_dossier()
    if not choix:
        print("Aucun dossier choisi.")
        attendre()
        return

    dossier = Path(choix)
    nombre = ranger(dossier, appliquer=False)       # 1) d'abord la simulation
    if nombre:
        reponse = input("\nDéplacer vraiment ces fichiers ? (o/n) : ").strip().lower()
        if reponse == "o":
            print()
            ranger(dossier, appliquer=True)         # 2) puis le vrai déplacement
            print("\nTerminé.")
        else:
            print("Annulé : rien n'a été déplacé.")
    attendre()


if __name__ == "__main__":
    main()