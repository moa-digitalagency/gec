"""Étiquette à coller sur le document : contenu, dimensions et QR lisible.

Le QR encode le numéro d'accusé de réception, seul numéro porté par l'étiquette.
Les contrôles portent sur le fichier produit, pas sur le code qui le produit :
une étiquette dont le QR ne se décode pas ou dont le texte déborde ne se voit
pas autrement.
"""

import importlib.util
import io
import os
from datetime import date, datetime

import pytest

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LARGEUR_ATTENDUE_MM = 70.0


def _module_etiquette():
    """Chargé par son chemin : utils/__init__ importe Flask, pas ce module."""
    chemin = os.path.join(RACINE, "utils", "etiquette.py")
    spec = importlib.util.spec_from_file_location("etiquette_sous_test", chemin)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class CourrierFactice:
    numero_accuse_reception = "GEC-2026-00147"
    date_enregistrement = datetime(2026, 10, 22, 9, 15)
    date_redaction = date(2026, 10, 18)
    type_courrier = "ENTRANT"
    expediteur = "Ministère des Mines — Secrétariat Général, Direction des Études"

    def get_contact_principal(self):
        return self.expediteur

    def get_label_contact(self):
        return "Expéditeur"


class ParametresFactices:
    titre_pdf = "Ministère des Mines"
    nom_logiciel = "GEC"


def _decoder_qr(donnees_png):
    zxingcpp = pytest.importorskip("zxingcpp", reason="décodeur QR absent")
    from PIL import Image

    resultats = zxingcpp.read_barcodes(Image.open(io.BytesIO(donnees_png)))
    return resultats[0].text if resultats else None


def test_pdf_a_la_taille_d_une_etiquette_et_contient_les_bonnes_mentions():
    from pypdf import PdfReader

    etq = _module_etiquette()
    lecteur = PdfReader(etq.construire_pdf(CourrierFactice(), ParametresFactices()))
    assert len(lecteur.pages) == 1

    boite = lecteur.pages[0].mediabox
    largeur_mm = float(boite.width) * 25.4 / 72
    assert abs(largeur_mm - LARGEUR_ATTENDUE_MM) < 0.5, f"largeur {largeur_mm:.1f} mm"
    assert float(boite.height) < float(boite.width), "l'étiquette doit rester en paysage"

    texte = lecteur.pages[0].extract_text()
    assert "GEC-2026-00147" in texte
    assert "22/10/2026" in texte, "date d'enregistrement absente"
    assert "18/10/2026" in texte, "date de rédaction absente"
    assert "Expéditeur" in texte
    assert "Ministère des Mines" in texte, "nom de la structure absent"
    assert "Suivi" not in texte, "l'étiquette ne doit plus porter de numéro de suivi"


def test_le_qr_encode_le_numero_d_accuse():
    etq = _module_etiquette()
    donnees = etq.construire_image(CourrierFactice(), ParametresFactices()).read()
    assert _decoder_qr(donnees) == "GEC-2026-00147"


def test_le_qr_reste_lisible_une_fois_reduit_et_flou():
    """Une étiquette est photographiée de travers, pas scannée à plat."""
    from PIL import Image, ImageFilter

    etq = _module_etiquette()
    image = Image.open(etq.construire_image(CourrierFactice(), ParametresFactices()))
    reduite = image.resize((image.size[0] // 3, image.size[1] // 3), Image.LANCZOS)
    floue = reduite.filter(ImageFilter.GaussianBlur(0.8))
    tampon = io.BytesIO()
    floue.save(tampon, format="PNG")
    assert _decoder_qr(tampon.getvalue()) == "GEC-2026-00147"


def test_image_a_la_bonne_taille_physique():
    from PIL import Image

    etq = _module_etiquette()
    image = Image.open(etq.construire_image(CourrierFactice(), ParametresFactices(), dpi=300))
    largeur_mm = image.size[0] * 25.4 / 300
    assert abs(largeur_mm - LARGEUR_ATTENDUE_MM) < 0.5, f"largeur {largeur_mm:.1f} mm"
    # Le PNG enregistre la résolution en pixels par mètre (entier) : 300 dpi en
    # ressort à 299,9994. On vérifie donc la valeur à l'unité près.
    assert round(image.info.get("dpi", (0,))[0]) == 300, "résolution non déclarée dans le PNG"


def test_un_contact_tres_long_passe_a_la_ligne_sans_deborder():
    """Un expéditeur long doit être replié, pas écrit par-dessus le QR."""
    etq = _module_etiquette()

    class ContactLong(CourrierFactice):
        expediteur = ("Direction Générale des Recettes Administratives, Judiciaires, "
                      "Domaniales et de Participation de la Province du Haut-Katanga")

        def get_contact_principal(self):
            return self.expediteur

    donnees = etq.donnees_etiquette(ContactLong(), ParametresFactices())
    assert donnees["contact"] == ContactLong.expediteur

    from pypdf import PdfReader

    lecteur = PdfReader(etq.construire_pdf(ContactLong(), ParametresFactices()))
    texte = lecteur.pages[0].extract_text()
    assert "Direction" in texte
    # Le dessin ne doit pas pousser l'étiquette au-delà d'une hauteur raisonnable.
    hauteur_mm = float(lecteur.pages[0].mediabox.height) * 25.4 / 72
    assert hauteur_mm < 60, f"étiquette trop haute : {hauteur_mm:.1f} mm"


def test_sans_police_vectorielle_l_image_echoue_clairement(monkeypatch):
    """Plutôt qu'une image illisible, un message qui renvoie vers le PDF."""
    etq = _module_etiquette()
    monkeypatch.setattr(etq, "POLICES", {False: ("/introuvable.ttf",),
                                         True: ("/introuvable.ttf",)})
    with pytest.raises(etq.PoliceIntrouvable):
        etq.construire_image(CourrierFactice(), ParametresFactices())

    # Le PDF, lui, utilise les polices intégrées de ReportLab : il reste possible.
    from pypdf import PdfReader

    lecteur = PdfReader(etq.construire_pdf(CourrierFactice(), ParametresFactices()))
    assert "GEC-2026-00147" in lecteur.pages[0].extract_text()
