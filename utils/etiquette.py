"""Étiquette à coller sur le document papier : QR code + numéro d'accusé.

Deux sorties du même dessin : PDF (vectoriel, pour l'impression) et PNG
(300 dpi, pour coller l'étiquette dans un autre document ou l'envoyer).

Disposition, reprise de l'étiquette patient de LithoExpert :
  - intitulé « Accusé de réception » centré en haut ;
  - QR code à droite ;
  - numéro d'accusé et métadonnées à gauche, le contact passant à la ligne
    plutôt que d'être tronqué ;
  - nom de la structure centré en bas ;
  - corps de texte réduit automatiquement jusqu'à ce que la ligne tienne.

Tout est imprimé en noir plein : une étiquette collée sur un document est
souvent photocopiée, et un gris clair disparaît à la copie.

Largeur fixée à 70 mm, hauteur selon le contenu : c'est la largeur des
planches d'étiquettes autocollantes courantes.
"""

import io
import os

import qrcode
from PIL import Image, ImageDraw, ImageFont
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas

LARGEUR_MM = 70.0
MARGE_MM = 3.5
ECART_MM = 2.0
QR_MM = 24.0

# Polices cherchées pour le rendu image, dans l'ordre. PIL ne sait pas dessiner
# de texte lisible sans fichier de police : ImageFont.load_default() donne une
# bitmap minuscule, illisible sur une étiquette collée. GEC tournant sous Linux,
# Windows Server et macOS, les trois familles sont listées.
POLICES = {
    False: (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/segoeui.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
    ),
    True: (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
        "C:/Windows/Fonts/segoeuib.ttf",
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    ),
}


class PoliceIntrouvable(RuntimeError):
    """Aucune police vectorielle sur le serveur : l'étiquette image serait illisible."""


def chemin_police(gras=False):
    for chemin in POLICES[gras]:
        if os.path.exists(chemin):
            return chemin
    return None


def charger_police(taille, gras=False):
    chemin = chemin_police(gras)
    if not chemin:
        raise PoliceIntrouvable(
            "Aucune police trouvée pour dessiner l'étiquette en image. "
            "Installez une police système (Linux : fonts-dejavu-core) "
            "ou utilisez l'étiquette en PDF."
        )
    return ImageFont.truetype(chemin, taille)


def _decouper(mesurer, texte, largeur_max):
    """Découpe `texte` en lignes qui tiennent dans `largeur_max`."""
    lignes, courante = [], ""
    for mot in (texte or "").split():
        essai = (courante + " " + mot).strip()
        if not courante or mesurer(essai) <= largeur_max:
            courante = essai
        else:
            lignes.append(courante)
            courante = mot
    if courante:
        lignes.append(courante)
    return lignes or [""]


def _taille_qui_tient(mesurer, texte, largeur_max, tailles):
    """Plus grand corps de la liste pour lequel `texte` tient en une ligne."""
    for taille in tailles:
        if mesurer(texte or " ", taille) <= largeur_max:
            return taille
    return tailles[-1]


def donnees_etiquette(courrier, parametres=None, traduire=None):
    """Ce qui est imprimé sur l'étiquette, indépendamment du format de sortie.

    Le QR encode le **numéro d'accusé de réception**, seul numéro porté par
    l'étiquette : lu par n'importe quelle application, il donne le numéro à
    rechercher dans GEC.
    """
    t = traduire or (lambda cle, defaut="": defaut or cle)
    organisation = ""
    if parametres is not None:
        organisation = (getattr(parametres, "titre_pdf", None)
                        or getattr(parametres, "nom_logiciel", None) or "")

    lignes = []
    if courrier.date_enregistrement:
        lignes.append((t("etiquette_enregistre_le", "Enregistré le :"),
                       courrier.date_enregistrement.strftime("%d/%m/%Y")))
    if getattr(courrier, "date_redaction", None):
        lignes.append((t("etiquette_redige_le", "Rédigé le :"),
                       courrier.date_redaction.strftime("%d/%m/%Y")))

    contact = (courrier.get_contact_principal() or "").strip()
    return {
        "organisation": organisation.strip(),
        "intitule": t("etiquette_accuse_titre", "Accusé de réception"),
        "numero": courrier.numero_accuse_reception,
        "qr_texte": courrier.numero_accuse_reception,
        "lignes": lignes,
        "contact_label": (courrier.get_label_contact() + " :") if contact else "",
        "contact": contact,
    }


def _image_qr(texte, module=4):
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=module,
        border=0,
    )
    qr.add_data(texte)
    qr.make(fit=True)
    image = qr.make_image(fill_color="black", back_color="white")
    return image.get_image() if hasattr(image, "get_image") else image


def construire_pdf(courrier, parametres=None, traduire=None):
    """Étiquette en PDF, à la taille réelle : 70 mm de large."""
    d = donnees_etiquette(courrier, parametres, traduire)

    largeur = LARGEUR_MM * mm
    marge = MARGE_MM * mm
    ecart = ECART_MM * mm
    qr = QR_MM * mm
    utile = largeur - 2 * marge

    c_intitule, c_meta, c_org = 8.0, 7.5, 7.5
    qr_x = largeur - marge - qr
    largeur_gauche = qr_x - 2 * mm - marge

    c_num = _taille_qui_tient(lambda x, s_: stringWidth(x, "Helvetica-Bold", s_),
                              d["numero"], largeur_gauche, [13, 12, 11, 10, 9, 8])
    h_num, h_meta = c_num + 5, c_meta + 3

    lignes_contact = []
    if d["contact"]:
        lignes_contact = _decouper(
            lambda x: stringWidth(x, "Helvetica", c_meta),
            f'{d["contact_label"]} {d["contact"]}', largeur_gauche)[:3]
    hauteur_texte = h_num + len(d["lignes"]) * h_meta + len(lignes_contact) * h_meta

    lignes_org = _decouper(lambda x: stringWidth(x, "Helvetica-Bold", c_org),
                           d["organisation"], utile) if d["organisation"] else []
    h_org = (c_org + 3) * len(lignes_org)

    corps = max(qr, hauteur_texte)
    hauteur = marge + (c_intitule + 4) + ecart + corps + (ecart + h_org if h_org else 0) + marge

    tampon = io.BytesIO()
    c = canvas.Canvas(tampon, pagesize=(largeur, hauteur))
    c.setFillGray(0)

    # ── Intitulé centré en haut ───────────────────────────────────────────
    haut = marge
    c.setFont("Helvetica-Bold", c_intitule)
    c.drawCentredString(largeur / 2, hauteur - (haut + c_intitule), d["intitule"].upper())
    haut += c_intitule + 4 + ecart

    # ── QR à droite ───────────────────────────────────────────────────────
    tampon_qr = io.BytesIO()
    _image_qr(d["qr_texte"]).save(tampon_qr, format="PNG")
    tampon_qr.seek(0)
    c.drawImage(ImageReader(tampon_qr), qr_x, hauteur - (haut + qr), width=qr, height=qr)

    # ── Numéro et métadonnées à gauche ────────────────────────────────────
    y = haut
    c.setFont("Helvetica-Bold", c_num)
    c.drawString(marge, hauteur - (y + c_num), d["numero"])
    y += h_num
    c.setFont("Helvetica", c_meta)
    for etiquette, valeur in d["lignes"]:
        c.drawString(marge, hauteur - (y + c_meta), f"{etiquette} {valeur}")
        y += h_meta
    for ligne in lignes_contact:
        c.drawString(marge, hauteur - (y + c_meta), ligne)
        y += h_meta

    # ── Nom de la structure centré en bas ─────────────────────────────────
    if lignes_org:
        y = haut + corps + ecart
        c.setFont("Helvetica-Bold", c_org)
        for ligne in lignes_org:
            c.drawCentredString(largeur / 2, hauteur - (y + c_org), ligne)
            y += c_org + 3

    c.save()
    tampon.seek(0)
    return tampon


def construire_image(courrier, parametres=None, traduire=None, dpi=300):
    """Même étiquette en PNG, à la taille réelle (70 mm de large à `dpi`)."""
    d = donnees_etiquette(courrier, parametres, traduire)

    px = dpi / 25.4
    pt = px / 2.83                      # 1 point typographique en pixels
    largeur = int(LARGEUR_MM * px)
    marge = int(MARGE_MM * px)
    ecart = int(ECART_MM * px)
    taille_qr = int(QR_MM * px)
    utile = largeur - 2 * marge

    mesure = ImageDraw.Draw(Image.new("RGB", (4, 4)))
    p_intitule = charger_police(int(8.0 * pt), gras=True)
    p_meta = charger_police(int(7.5 * pt))
    p_org = charger_police(int(7.5 * pt), gras=True)
    h_intitule = int(12.0 * pt)
    h_meta = int(10.5 * pt)
    h_org_ligne = int(10.5 * pt)

    qr_x = largeur - marge - taille_qr
    largeur_gauche = qr_x - int(2 * px) - marge
    c_num = _taille_qui_tient(
        lambda x, s_: mesure.textlength(x, font=charger_police(s_, gras=True)),
        d["numero"], largeur_gauche, [int(c * pt) for c in (13, 12, 11, 10, 9, 8)])
    p_num = charger_police(c_num, gras=True)
    h_num = int(c_num * 1.4)

    lignes_contact = []
    if d["contact"]:
        lignes_contact = _decouper(
            lambda x: mesure.textlength(x, font=p_meta),
            f'{d["contact_label"]} {d["contact"]}', largeur_gauche)[:3]
    hauteur_texte = h_num + (len(d["lignes"]) + len(lignes_contact)) * h_meta

    lignes_org = _decouper(lambda x: mesure.textlength(x, font=p_org),
                           d["organisation"], utile) if d["organisation"] else []
    h_org = h_org_ligne * len(lignes_org)

    corps = max(taille_qr, hauteur_texte)
    haut = marge + h_intitule + ecart
    hauteur = haut + corps + (ecart + h_org if h_org else 0) + marge

    image = Image.new("RGB", (largeur, hauteur), "white")
    dessin = ImageDraw.Draw(image)

    intitule = d["intitule"].upper()
    dessin.text(((largeur - dessin.textlength(intitule, font=p_intitule)) / 2, marge),
                intitule, font=p_intitule, fill="black")

    qr = _image_qr(d["qr_texte"]).convert("RGB").resize(
        (taille_qr, taille_qr), Image.NEAREST)
    image.paste(qr, (qr_x, haut))

    y = haut
    dessin.text((marge, y), d["numero"], font=p_num, fill="black")
    y += h_num
    for etiquette, valeur in d["lignes"]:
        dessin.text((marge, y), f"{etiquette} {valeur}", font=p_meta, fill="black")
        y += h_meta
    for ligne in lignes_contact:
        dessin.text((marge, y), ligne, font=p_meta, fill="black")
        y += h_meta

    if lignes_org:
        y = haut + corps + ecart
        for ligne in lignes_org:
            dessin.text(((largeur - dessin.textlength(ligne, font=p_org)) / 2, y),
                        ligne, font=p_org, fill="black")
            y += h_org_ligne

    tampon = io.BytesIO()
    image.save(tampon, format="PNG", dpi=(dpi, dpi))
    tampon.seek(0)
    return tampon


def bloc_etiquette_accuse(courrier, parametres=None, style_texte=None):
    """L'étiquette, en éléments ReportLab, pour l'accusé de réception.

    Rendue comme une image à sa taille réelle : le dessin reste identique à
    celui de l'étiquette téléchargée, et la découpe se fait aux pointillés.
    """
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.platypus import Image as ImageFlowable
    from reportlab.platypus import KeepTogether, Paragraph, Spacer, Table, TableStyle

    consigne = ParagraphStyle(
        "ConsigneEtiquette",
        parent=style_texte,
        fontSize=7.5,
        textColor=colors.grey,
        alignment=TA_CENTER,
        spaceAfter=4,
    )

    # Le PNG est rendu à 300 dpi puis replacé à sa taille physique : il sort net
    # à l'impression, alors qu'une image placée à sa taille en pixels serait floue.
    tampon = construire_image(courrier, parametres, dpi=300)
    vignette = ImageFlowable(tampon, width=LARGEUR_MM * mm,
                             height=_hauteur_image_mm(tampon) * mm)

    cadre = Table([[vignette]], colWidths=[(LARGEUR_MM + 6) * mm])
    cadre.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.7, colors.grey, None, (3, 3)),  # trait de découpe
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    cadre.hAlign = "CENTER"

    # KeepTogether : sans lui, la consigne reste en bas d'une page et l'étiquette
    # bascule seule sur la suivante — constaté sur l'accusé de réception.
    return [
        KeepTogether([
            Paragraph("Étiquette à découper et à coller sur le document", consigne),
            cadre,
        ]),
        Spacer(1, 6),
    ]


def _hauteur_image_mm(tampon, dpi=300):
    """Hauteur réelle en millimètres de l'étiquette image, sans la déformer."""
    position = tampon.tell()
    tampon.seek(0)
    with Image.open(tampon) as image:
        hauteur_px = image.size[1]
    tampon.seek(position)
    return hauteur_px * 25.4 / dpi
