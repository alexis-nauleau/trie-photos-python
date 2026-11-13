"""Affiche les informations contenues dans une photo (EXIF) et les dates du fichier."""
import sys
from datetime import datetime
from pathlib import Path

from PIL import Image
from PIL.ExifTags import TAGS   # dictionnaire : numéro de champ -> nom lisible


def main():
    # sys.argv = ce qu'on a tapé dans le terminal ; [0] est le nom du script, [1] le fichier
    if len(sys.argv) < 2:
        print("Usage : python diagnostic_exif.py chemin\\vers\\photo.jpg")
        return
    chemin = Path(sys.argv[1])

    infos = chemin.stat()   # informations du système de fichiers (dates, taille)
    print("Date de modification du fichier :", datetime.fromtimestamp(infos.st_mtime))
    print("Date de création du fichier     :", datetime.fromtimestamp(infos.st_ctime))

    with Image.open(chemin) as image:
        print("Dimensions de l'image           :", image.size)
        exif = image.getexif()
        if not exif:
            print("\nAucune donnée EXIF dans ce fichier.")
            return

        donnees = dict(exif)                        # champs généraux
        donnees.update(exif.get_ifd(0x8769))        # + champs détaillés (dont les dates)
        print("\nChamps EXIF présents :")
        for numero, valeur in donnees.items():
            nom = TAGS.get(numero, numero)          # le nom lisible, sinon le numéro
            print(f"  {nom} : {str(valeur)[:60]}")


if __name__ == "__main__":
    main()