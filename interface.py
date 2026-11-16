# ============================================================
# interface.py : tri de photos par année, avec interface graphique (tkinter)
# Ordre de recherche de la date d'une photo :
#   1. date de prise de vue (EXIF)        -> dossier  2020
#   2. date écrite dans le nom (WhatsApp)  -> dossier  2020
#   3. rien de fiable                      -> dossier  Autres
# ============================================================

# ---------- IMPORTS ----------
import queue                      # File de messages entre le tri et la fenêtre
import re                         # Chercher un motif dans un texte (dates WhatsApp)
import shutil                     # Copier / déplacer des fichiers
import threading                  # Faire tourner le tri en parallèle de la fenêtre
import tkinter as tk              # L'interface graphique
from datetime import datetime     # Manipuler les dates
from pathlib import Path          # Manipuler les chemins de fichiers
from tkinter import filedialog, messagebox, ttk

from PIL import Image             # Lire les images et leurs informations EXIF

# Extensions des fichiers acceptés
EXTENSIONS = {".jpg", ".jpeg", ".png", ".mp4", ".mov"}

# Communication entre le traitement (thread) et l'interface
messages = queue.Queue()

# Liste des erreurs rencontrées pendant le tri (affichées à la fin)
liste_erreurs = []


# ============================================================
# LECTURE DES DATES
# ============================================================

def date_exif(chemin):
    """Date de prise de vue lue dans les informations EXIF de la photo, ou None."""
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
    # Format 1 :  WhatsApp Image 2026-10-03 at 16.08.27.jpeg   (ou 16-08-27)
    resultat = re.search(
        r"(\d{4}-\d{2}-\d{2}) at (\d{2})[.-](\d{2})[.-](\d{2})",
        nom,
        re.IGNORECASE
    )
    if resultat:
        # group(1) = "2026-10-03" ; groups()[1:] = ("16", "08", "27") -> "16:08:27"
        texte = resultat.group(1) + " " + ":".join(resultat.groups()[1:])
        try:
            return datetime.strptime(texte, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            pass

    # Format 2 :  IMG-20261003-WA0001.jpg   ou   VID-20261003-WA0001.mp4
    resultat = re.search(r"(?:IMG|VID)-(\d{4})(\d{2})(\d{2})-WA", nom, re.IGNORECASE)
    if resultat:
        try:
            return datetime.strptime("".join(resultat.groups()), "%Y%m%d")
        except ValueError:
            pass

    return None


def trouver_date(chemin):
    """Renvoie (date, origine). L'origine est : "exif", "whatsapp" ou "aucune"."""
    date = date_exif(chemin)
    if date:
        return date, "exif"
    date = date_whatsapp(chemin.name)
    if date:
        return date, "whatsapp"
    return None, "aucune"


# ============================================================
# TRI
# ============================================================

def sous_dossier_pour(date, origine):
    """Photos avec une date sûre : un dossier par année. Le reste : Autres."""
    if origine in ("exif", "whatsapp"):
        return Path(str(date.year))        # ex : 2020
    return Path("Autres")


def destination_libre(chemin):
    """Trouve un nom disponible : photo.jpg, puis photo_1.jpg, photo_2.jpg..."""
    original = chemin       # on garde le chemin de départ intact
    numero = 1
    while chemin.exists():
        # On repart toujours de "original" (sinon les noms s'empilent : photo_1_2_3.jpg)
        chemin = original.with_name(f"{original.stem}_{numero}{original.suffix}")
        numero += 1
    return chemin


def effectuer_tri(source, destination, copier):
    """Exécuté dans un thread : trie les photos et envoie sa progression dans 'messages'."""
    fichiers = sorted(
        fichier for fichier in source.iterdir()
        if fichier.is_file() and fichier.suffix.lower() in EXTENSIONS
    )

    # Dossier sans photos : on prévient la fenêtre et on s'arrête
    if not fichiers:
        messages.put(("vide",))
        return

    messages.put(("debut", len(fichiers)))

    compteurs = {"exif": 0, "whatsapp": 0, "aucune": 0}
    erreurs = 0

    for numero, fichier in enumerate(fichiers, start=1):
        date, origine = trouver_date(fichier)
        cible = destination_libre(destination / sous_dossier_pour(date, origine) / fichier.name)

        try:
            cible.parent.mkdir(parents=True, exist_ok=True)
            if copier:
                shutil.copy2(str(fichier), str(cible))     # copie en gardant les dates
            else:
                shutil.move(str(fichier), str(cible))      # déplace (l'original disparaît)
            compteurs[origine] += 1       # compté seulement si l'opération a réussi
        except Exception as erreur:
            erreurs += 1
            messages.put(("erreur", f"{fichier.name} : {erreur}"))

        messages.put(("progression", numero, len(fichiers), fichier.name))

    messages.put(("termine", compteurs, erreurs))


# ============================================================
# ACTIONS DE L'INTERFACE
# ============================================================

def reinitialiser_bouton():
    """Remet le bouton principal dans son état de départ."""
    bouton_tri.config(bg="#2563EB", text="TRIER LES PHOTOS")


def choisir_source():
    dossier = filedialog.askdirectory(title="Choisir le dossier des photos")
    if dossier:
        entree_source.delete(0, tk.END)
        entree_source.insert(0, dossier)
        reinitialiser_bouton()


def choisir_destination():
    dossier = filedialog.askdirectory(title="Choisir le dossier de destination")
    if dossier:
        entree_destination.delete(0, tk.END)
        entree_destination.insert(0, dossier)
        reinitialiser_bouton()


def lancer_tri():
    texte_source = entree_source.get().strip()
    texte_destination = entree_destination.get().strip()

    # Un champ vide ne doit JAMAIS être traité : Path("") désigne le dossier courant !
    if not texte_source or not Path(texte_source).is_dir():
        messagebox.showwarning("Attention", "Choisis un dossier contenant les photos.")
        return
    if not texte_destination or not Path(texte_destination).is_dir():
        messagebox.showwarning("Attention", "Choisis un dossier de destination existant.")
        return

    source = Path(texte_source)
    destination = Path(texte_destination)

    # Les deux dossiers doivent être différents
    if source.resolve() == destination.resolve():
        messagebox.showwarning("Attention", "Les deux dossiers doivent être différents.")
        return

    # La destination ne doit pas être à l'intérieur de la source
    if source.resolve() in destination.resolve().parents:
        messagebox.showwarning(
            "Attention",
            "Le dossier de destination ne doit pas être à l'intérieur du dossier source."
        )
        return

    # Si on va DÉPLACER les photos, on demande confirmation
    if not copier.get():
        if not messagebox.askyesno(
            "Confirmer",
            "Les photos vont être DÉPLACÉES : elles disparaîtront du dossier d'origine.\n\n"
            "Continuer ?"
        ):
            return

    # Préparer l'interface
    bouton_tri.config(state="disabled", bg="#999999", text="TRI EN COURS...")
    statut.config(text="Préparation du tri...", fg="#2563EB")
    progression["value"] = 0
    liste_erreurs.clear()

    # Lancer le tri dans un autre thread : la fenêtre reste réactive.
    # copier.get() est lu ICI (thread principal) : on ne touche jamais aux widgets depuis le thread.
    thread = threading.Thread(
        target=effectuer_tri,
        args=(source, destination, copier.get()),
        daemon=True
    )
    thread.start()
    fenetre.after(100, verifier_messages)


def verifier_messages():
    """Appelée toutes les 100 ms : lit les messages du thread et met l'interface à jour."""
    try:
        while True:
            message = messages.get_nowait()
            genre = message[0]

            if genre == "debut":
                total = message[1]
                progression["maximum"] = total
                statut.config(text=f"{total} fichier(s) à traiter...", fg="#2563EB")

            elif genre == "progression":
                numero, total, nom = message[1:]
                progression["value"] = numero
                statut.config(text=f"Traitement ({numero}/{total}) : {nom}")

            elif genre == "erreur":
                liste_erreurs.append(message[1])

            elif genre == "vide":
                bouton_tri.config(state="normal", bg="#2563EB", text="TRIER LES PHOTOS")
                statut.config(text="Aucun fichier à trier dans ce dossier.", fg="#cc8800")
                return

            elif genre == "termine":
                compteurs, erreurs = message[1], message[2]
                bouton_tri.config(state="normal", bg="#249B55", text="TRI TERMINÉ ✓")
                statut.config(text="Le tri est terminé !", fg="#249B55")

                texte = (
                    f"Date de prise de vue (EXIF) : {compteurs['exif']}\n"
                    f"Date lue dans le nom (WhatsApp) : {compteurs['whatsapp']}\n"
                    f"Rangées dans Autres : {compteurs['aucune']}\n"
                    f"Erreurs : {erreurs}"
                )
                if liste_erreurs:
                    texte += "\n\n" + "\n".join(liste_erreurs[:5])
                messagebox.showinfo("Tri terminé", texte)
                return
    except queue.Empty:
        pass

    # Continuer à vérifier les messages
    fenetre.after(100, verifier_messages)


# ============================================================
# CRÉATION DE L'INTERFACE GRAPHIQUE
# ============================================================

fenetre = tk.Tk()
fenetre.title("Tri de photos")
fenetre.geometry("620x430")
fenetre.resizable(False, False)
fenetre.configure(bg="#F4F5F7")

# ---------- TITRE ----------
tk.Label(
    fenetre,
    text="TRI DE PHOTOS",
    font=("Arial", 20, "bold"),
    bg="#F4F5F7",
    fg="#222222"
).pack(pady=20)

# ---------- DOSSIER SOURCE ----------
tk.Label(
    fenetre,
    text="1. Dossier contenant les photos",
    font=("Arial", 11, "bold"),
    bg="#F4F5F7"
).pack(anchor="w", padx=35)

cadre_source = tk.Frame(fenetre, bg="#F4F5F7")
cadre_source.pack(fill="x", padx=35, pady=8)

entree_source = tk.Entry(cadre_source, font=("Arial", 10))
entree_source.pack(side="left", fill="x", expand=True, ipady=6)

tk.Button(cadre_source, text="Parcourir", command=choisir_source).pack(side="right", padx=(8, 0))

# ---------- DOSSIER DE DESTINATION ----------
tk.Label(
    fenetre,
    text="2. Emplacement du résultat",
    font=("Arial", 11, "bold"),
    bg="#F4F5F7"
).pack(anchor="w", padx=35, pady=(15, 0))

cadre_destination = tk.Frame(fenetre, bg="#F4F5F7")
cadre_destination.pack(fill="x", padx=35, pady=8)

entree_destination = tk.Entry(cadre_destination, font=("Arial", 10))
entree_destination.pack(side="left", fill="x", expand=True, ipady=6)

tk.Button(
    cadre_destination, text="Parcourir", command=choisir_destination
).pack(side="right", padx=(8, 0))

# ---------- COPIER OU DÉPLACER ----------
# BooleanVar : une variable tkinter qui vaut True (case cochée) ou False
copier = tk.BooleanVar(value=True)
tk.Checkbutton(
    fenetre,
    text="Copier les photos (décocher pour les DÉPLACER)",
    variable=copier,
    bg="#F4F5F7"
).pack(anchor="w", padx=35)

# ---------- BARRE DE PROGRESSION ----------
progression = ttk.Progressbar(fenetre, length=550, mode="determinate")
progression.pack(pady=(20, 10))

# ---------- TEXTE DE STATUT ----------
statut = tk.Label(
    fenetre,
    text="En attente",
    font=("Arial", 10),
    bg="#F4F5F7",
    fg="#666666"
)
statut.pack(pady=5)

# ---------- BOUTON DE TRI ----------
bouton_tri = tk.Button(
    fenetre,
    text="TRIER LES PHOTOS",
    font=("Arial", 12, "bold"),
    bg="#2563EB",
    fg="white",
    activebackground="#1D4ED8",
    activeforeground="white",
    relief="flat",
    cursor="hand2",
    command=lancer_tri
)
bouton_tri.pack(fill="x", padx=35, pady=15, ipady=12)

# ---------- LANCEMENT DE L'APPLICATION ----------
fenetre.mainloop()