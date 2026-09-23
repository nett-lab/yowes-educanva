"""
France data and document generators

French teachers need different documents:
1. Installation statement extract (Arrêté d'affectation)
2. iProf screenshot (Teacher administrative file)
3. Collective by-laws extract
4. Teaching certificate from head of school
"""

from typing import Dict, List
from ..base import CountryGenerator
from ..utils import get_profile_photo, generate_initials_avatar
from PIL import Image, ImageDraw, ImageFont
from ..utils import load_font
from datetime import datetime
import random


# France Schools Database
DEFAULT_FRANCE_SCHOOLS = [
    {"name": "Lycée Louis-le-Grand", "address": "123 Rue Saint-Jacques", "town": "Paris", "postcode": "75005", "phone": "+33 1 44 32 16 00", "region": "Île-de-France", "academie": "Académie de Paris"},
    {"name": "Lycée Henri-IV", "address": "23 Rue Clovis", "town": "Paris", "postcode": "75005", "phone": "+33 1 44 41 80 80", "region": "Île-de-France", "academie": "Académie de Paris"},
    {"name": "Lycée du Parc", "address": "1 Boulevard Anatole France", "town": "Lyon", "postcode": "69006", "phone": "+33 4 37 51 15 51", "region": "Auvergne-Rhône-Alpes", "academie": "Académie de Lyon"},
    {"name": "Lycée Sainte-Geneviève", "address": "2 Rue de l'École des Postes", "town": "Versailles", "postcode": "78000", "phone": "+33 1 39 23 23 23", "region": "Île-de-France", "academie": "Académie de Versailles"},
    {"name": "Lycée Masséna", "address": "2 Avenue Félix Faure", "town": "Nice", "postcode": "06000", "phone": "+33 4 93 62 30 30", "region": "Provence-Alpes-Côte d'Azur", "academie": "Académie de Nice"},
    {"name": "Lycée Thiers", "address": "5 Place du Lycée", "town": "Marseille", "postcode": "13001", "phone": "+33 4 91 18 92 18", "region": "Provence-Alpes-Côte d'Azur", "academie": "Académie d'Aix-Marseille"},
    {"name": "Lycée Faidherbe", "address": "9 Rue Armand Carrel", "town": "Lille", "postcode": "59000", "phone": "+33 3 20 55 34 40", "region": "Hauts-de-France", "academie": "Académie de Lille"},
    {"name": "Lycée Pierre de Fermat", "address": "Parvis des Jacobins", "town": "Toulouse", "postcode": "31000", "phone": "+33 5 62 27 90 15", "region": "Occitanie", "academie": "Académie de Toulouse"},
    {"name": "Lycée Clemenceau", "address": "130 Rue Abbé de l'Épée", "town": "Nantes", "postcode": "44000", "phone": "+33 2 55 11 10 00", "region": "Pays de la Loire", "academie": "Académie de Nantes"},
    {"name": "Lycée Hoche", "address": "73 Avenue de Saint-Cloud", "town": "Versailles", "postcode": "78000", "phone": "+33 1 39 24 13 65", "region": "Île-de-France", "academie": "Académie de Versailles"},
]

# France Names
FRANCE_FIRST_NAMES = [
    "Jean", "Pierre", "Michel", "André", "Philippe", "Alain", "Jacques", "François",
    "Nicolas", "Laurent", "Olivier", "Julien", "Maxime", "Alexandre", "Thomas", "Antoine",
    "Marie", "Sophie", "Isabelle", "Nathalie", "Catherine", "Françoise", "Céline", "Julie",
    "Camille", "Claire", "Émilie", "Charlotte", "Léa", "Manon", "Amélie", "Lucie"
]

FRANCE_LAST_NAMES = [
    "Martin", "Bernard", "Dubois", "Thomas", "Robert", "Richard", "Petit", "Durand",
    "Leroy", "Moreau", "Simon", "Laurent", "Lefebvre", "Michel", "Garcia", "David",
    "Bertrand", "Roux", "Vincent", "Fournier", "Morel", "Girard", "André", "Mercier",
    "Dupont", "Lambert", "Bonnet", "François", "Martinez", "Rousseau", "Blanc", "Guerin"
]

# France Teaching Positions
FRANCE_TEACHING_POSITIONS = [
    "Professeur Agrégé - Mathématiques",
    "Professeur Agrégé - Lettres Modernes",
    "Professeur Agrégé - Histoire-Géographie",
    "Professeur Agrégé - Anglais",
    "Professeur Agrégé - Philosophie",
    "Professeur Certifié - Sciences Physiques",
    "Professeur Certifié - SVT",
    "Professeur Certifié - Espagnol",
    "Professeur des Écoles",
    "Chef de Travaux",
]


class FranceGenerator(CountryGenerator):
    """France-specific document generator"""
    
    def get_country_name(self) -> str:
        return "France"
    
    def get_country_code(self) -> str:
        return "france"
    
    def get_schools_data(self) -> List[Dict]:
        return DEFAULT_FRANCE_SCHOOLS
    
    def get_first_names(self) -> List[str]:
        return FRANCE_FIRST_NAMES
    
    def get_last_names(self) -> List[str]:
        return FRANCE_LAST_NAMES
    
    def get_positions(self) -> List[str]:
        return FRANCE_TEACHING_POSITIONS
    
    def get_document_types(self) -> List[str]:
        return ["installation_statement", "iprof_screenshot", "bylaws_extract", "teaching_certificate"]
    
    def generate_document(self, doc_type: str, first: str, last: str, 
                         school: Dict, position: str, dob: str) -> bytes:
        """Generate France document"""
        if doc_type == "installation_statement":
            return self._generate_installation_statement(first, last, school, position)
        elif doc_type == "iprof_screenshot":
            return self._generate_iprof_screenshot(first, last, school, position)
        elif doc_type == "bylaws_extract":
            return self._generate_bylaws_extract(first, last, school, position)
        elif doc_type == "teaching_certificate":
            return self._generate_teaching_certificate(first, last, school, position)
        else:
            raise ValueError(f"Unknown document type: {doc_type}")
    
    def _generate_installation_statement(self, first: str, last: str, school: Dict, position: str) -> bytes:
        """Generate Arrêté d'affectation (Installation Statement Extract)"""
        w, h = 2480, 3508  # A4 at 300 DPI
        img = Image.new('RGB', (w, h), (255, 255, 255))
        draw = ImageDraw.Draw(img)
        
        try:
            font_title = load_font("arialbd", 52)
            font_header = load_font("arialbd", 40)
            font_normal = load_font("arial", 35)
            font_bold = load_font("arialbd", 35)
            font_small = load_font("arial", 28)
        except:
            font_title = font_header = font_normal = font_bold = font_small = ImageFont.load_default()
        
        # French Republic Header
        y = 100
        draw.text((w//2, y), "RÉPUBLIQUE FRANÇAISE", fill=(0, 35, 102), font=font_title, anchor="mm")
        y += 70
        draw.text((w//2, y), "Ministère de l'Éducation Nationale", fill=(0, 35, 102), font=font_header, anchor="mm")
        y += 60
        draw.text((w//2, y), school.get("academie", "Académie de Paris"), fill=(60, 60, 60), font=font_bold, anchor="mm")
        
        # Decorative line
        y += 50
        draw.rectangle([(w//2 - 600, y), (w//2 + 600, y+5)], fill=(200, 16, 46))  # French flag red
        
        # Document title
        y += 100
        draw.rectangle([(150, y-20), (w-150, y+80)], fill=(240, 240, 250))
        draw.text((w//2, y+30), "ARRÊTÉ D'AFFECTATION", fill=(0, 35, 102), font=font_title, anchor="mm")
        
        # Reference number
        y += 150
        ref_num = f"ARR-{random.randint(2020, 2025)}-{random.randint(10000, 99999)}"
        draw.text((200, y), f"Référence: {ref_num}", fill=(0, 0, 0), font=font_bold)
        
        # Date
        current_date = datetime.now().strftime("%d/%m/%Y")
        draw.text((w-200, y), f"Date: {current_date}", fill=(60, 60, 60), font=font_normal, anchor="ra")
        
        # Body
        y += 120
        lines = [
            "Le Recteur de l'Académie,",
            "",
            f"ARRÊTE:",
            "",
            f"Article 1 - Madame/Monsieur {first.upper()} {last.upper()}",
            f"est affecté(e) à compter du 1er septembre {datetime.now().year - random.randint(1, 5)}",
            f"à l'établissement suivant:",
            "",
            f"    {school['name']}",
            f"    {school['address']}",
            f"    {school['postcode']} {school['town']}",
            "",
            f"En qualité de: {position}",
            "",
            f"Article 2 - Le présent arrêté sera notifié à l'intéressé(e)",
            f"et prendra effet à la date indiquée ci-dessus.",
            "",
            "",
            f"Fait à {school['town']}, le {current_date}",
        ]
        
        for line in lines:
            draw.text((200, y), line, fill=(40, 40, 40), font=font_normal)
            y += 52
        
        # Signature
        y += 80
        draw.text((w - 500, y), "Le Recteur d'Académie", fill=(0, 0, 0), font=font_bold, anchor="mm")
        
        # Official stamp
        stamp_x = w - 500
        stamp_y = y + 100
        draw.ellipse([(stamp_x-70, stamp_y-70), (stamp_x+70, stamp_y+70)], outline=(200, 16, 46), width=6)
        draw.text((stamp_x, stamp_y), "OFFICIEL", fill=(200, 16, 46), font=font_small, anchor="mm")
        
        from io import BytesIO
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        return buffer.getvalue()
    
    def _generate_iprof_screenshot(self, first: str, last: str, school: Dict, position: str) -> bytes:
        """Generate iProf Platform Screenshot"""
        w, h = 1920, 1080  # Standard screenshot size
        img = Image.new('RGB', (w, h), (245, 245, 250))
        draw = ImageDraw.Draw(img)
        
        try:
            font_title = load_font("arialbd", 40)
            font_header = load_font("arialbd", 32)
            font_normal = load_font("arial", 28)
            font_bold = load_font("arialbd", 28)
        except:
            font_title = font_header = font_normal = font_bold = ImageFont.load_default()
        
        # Header bar (like a website)
        draw.rectangle([(0, 0), (w, 100)], fill=(0, 35, 102))
        draw.text((30, 50), "i-Prof", fill=(255, 255, 255), font=font_title, anchor="lm")
        draw.text((w-30, 50), f"Connecté: {first} {last}", fill=(255, 255, 255), font=font_normal, anchor="rm")
        
        # Main content area
        y = 150
        
        # Profile section
        draw.rectangle([(50, y), (w-50, y+600)], fill=(255, 255, 255), outline=(200, 200, 200), width=2)
        
        # Section title
        draw.rectangle([(50, y), (w-50, y+60)], fill=(0, 35, 102))
        draw.text((70, y+30), "DOSSIER ADMINISTRATIF - ENSEIGNANT", fill=(255, 255, 255), font=font_header, anchor="lm")
        
        y += 80
        
        # Add profile photo
        photo_size = (150, 180)
        photo_x = 80
        photo_y = y + 10
        
        person_id = getattr(self, '_current_person_id', None)
        gender = getattr(self, '_current_gender', 'Random')
        photo = get_profile_photo(photo_size, person_id=person_id, gender=gender)
        if photo is None:
            photo = generate_initials_avatar(first, last, photo_size, bg_color=(0, 35, 102))
        
        img.paste(photo, (photo_x, photo_y))
        draw.rectangle([(photo_x-2, photo_y-2), (photo_x+photo_size[0]+2, photo_y+photo_size[1]+2)], 
                      outline=(0, 35, 102), width=3)
        
        # Personal info (shifted to right of photo)
        info_start_x = photo_x + photo_size[0] + 50
        y += 20
        
        # Personal info
        info_lines = [
            ("Nom:", last.upper()),
            ("Prénom:", first),
            ("Grade:", position),
            ("Établissement:", school["name"]),
            ("Adresse:", school["address"]),
            ("Ville:", f"{school['postcode']} {school['town']}"),
            ("Académie:", school.get("academie", "Académie de Paris")),
            ("Statut:", "Titulaire"),
            ("Ancienneté:", f"{random.randint(5, 20)} ans"),
        ]
        
        for label, value in info_lines:
            draw.text((info_start_x, y), label, fill=(80, 80, 80), font=font_bold)
            draw.text((info_start_x + 300, y), value, fill=(0, 0, 0), font=font_normal)
            y += 50
        
        # Footer
        y = h - 80
        draw.rectangle([(0, y), (w, h)], fill=(230, 230, 235))
        draw.text((w//2, y+40), "Document généré depuis i-Prof - Ministère de l'Éducation Nationale", 
                 fill=(100, 100, 100), font=font_normal, anchor="mm")
        
        from io import BytesIO
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        return buffer.getvalue()
    
    def _generate_bylaws_extract(self, first: str, last: str, school: Dict, position: str) -> bytes:
        """Generate Collective By-laws Extract"""
        w, h = 2480, 3508
        img = Image.new('RGB', (w, h), (255, 255, 255))
        draw = ImageDraw.Draw(img)
        
        try:
            font_title = load_font("arialbd", 56)
            font_header = load_font("arialbd", 42)
            font_normal = load_font("arial", 36)
            font_bold = load_font("arialbd", 36)
            font_small = load_font("arial", 30)
        except:
            font_title = font_header = font_normal = font_bold = font_small = ImageFont.load_default()
        
        # French flag colors border
        draw.rectangle([(0, 0), (30, h)], fill=(0, 35, 102))  # Blue
        draw.rectangle([(30, 0), (60, h)], fill=(255, 255, 255))  # White
        draw.rectangle([(60, 0), (90, h)], fill=(200, 16, 46))  # Red
        
        # Header
        y = 150
        draw.text((w//2, y), "RÉPUBLIQUE FRANÇAISE", fill=(0, 35, 102), font=font_title, anchor="mm")
        y += 80
        draw.text((w//2, y), "EXTRAIT DU REGISTRE", fill=(0, 35, 102), font=font_header, anchor="mm")
        y += 60
        draw.text((w//2, y), "DU PERSONNEL ENSEIGNANT", fill=(0, 35, 102), font=font_header, anchor="mm")
        
        # Decorative line
        y += 70
        draw.rectangle([(200, y), (w-200, y+8)], fill=(200, 16, 46))
        
        # School section
        y += 100
        draw.rectangle([(150, y), (w-150, y+200)], fill=(245, 245, 250), outline=(0, 35, 102), width=3)
        
        y += 50
        draw.text((w//2, y), "ÉTABLISSEMENT", fill=(100, 100, 100), font=font_bold, anchor="mm")
        y += 60
        draw.text((w//2, y), school["name"], fill=(0, 0, 0), font=font_header, anchor="mm")
        y += 55
        draw.text((w//2, y), f"{school['address']}, {school['postcode']} {school['town']}", 
                 fill=(80, 80, 80), font=font_normal, anchor="mm")
        
        # Content
        y += 150
        ref_number = f"REG-{datetime.now().year}-{random.randint(1000, 9999)}"
        
        content_lines = [
            ("Référence du registre:", ref_number),
            ("", ""),
            ("NOM ET PRÉNOM:", f"{last.upper()}, {first}"),
            ("", ""),
            ("FONCTION:", position),
            ("", ""),
            ("DATE D'ENTRÉE:", f"01/09/{datetime.now().year - random.randint(2, 8)}"),
            ("", ""),
            ("STATUT:", "Personnel titulaire de l'Éducation Nationale"),
            ("", ""),
            ("CATÉGORIE:", "Enseignant certifié / Agrégé"),
            ("", ""),
            ("AFFECTATION:", f"{school.get('academie', 'Académie de Paris')}"),
        ]
        
        for label, value in content_lines:
            if label:
                draw.text((250, y), label, fill=(100, 100, 100), font=font_bold)
                y += 50
                if value:
                    draw.text((250, y), value, fill=(0, 0, 0), font=font_normal)
                    y += 65
            else:
                y += 30
        
        # Certification section
        y += 80
        draw.rectangle([(150, y), (w-150, y+250)], fill=(255, 250, 245), outline=(200, 16, 46), width=3)
        
        y += 50
        cert_lines = [
            "CERTIFICATION",
            "",
            f"Le présent extrait certifie l'inscription de {first} {last}",
            f"au registre du personnel enseignant de l'établissement.",
            "",
            "Cet extrait peut être utilisé à des fins administratives",
            "conformément aux dispositions légales en vigueur.",
        ]
        
        for line in cert_lines:
            if line == "CERTIFICATION":
                draw.text((w//2, y), line, fill=(200, 16, 46), font=font_header, anchor="mm")
                y += 70
            elif line:
                draw.text((w//2, y), line, fill=(60, 60, 60), font=font_normal, anchor="mm")
                y += 50
            else:
                y += 20
        
        # Signature and stamp
        y = h - 500
        draw.text((w//2, y), f"Fait à {school['town']}, le {datetime.now().strftime('%d/%m/%Y')}", 
                 fill=(80, 80, 80), font=font_normal, anchor="mm")
        
        y += 120
        draw.text((w//2 - 500, y), "Le Chef d'Établissement", fill=(0, 0, 0), font=font_bold)
        
        # Official stamp
        stamp_x = w//2 + 400
        stamp_y = y + 80
        draw.ellipse([(stamp_x-90, stamp_y-90), (stamp_x+90, stamp_y+90)], outline=(200, 16, 46), width=8)
        draw.ellipse([(stamp_x-70, stamp_y-70), (stamp_x+70, stamp_y+70)], outline=(0, 35, 102), width=4)
        draw.text((stamp_x, stamp_y-20), "CACHET", fill=(200, 16, 46), font=font_bold, anchor="mm")
        draw.text((stamp_x, stamp_y+20), "OFFICIEL", fill=(0, 35, 102), font=font_bold, anchor="mm")
        
        # Footer
        y = h - 200
        draw.line([(150, y), (w-150, y)], fill=(0, 35, 102), width=3)
        y += 50
        draw.text((w//2, y), f"{school['name']} - {school.get('academie', 'Académie de Paris')}", 
                 fill=(120, 120, 120), font=font_small, anchor="mm")
        y += 45
        draw.text((w//2, y), f"Document officiel - Référence: {ref_number}", 
                 fill=(150, 150, 150), font=font_small, anchor="mm")
        
        from io import BytesIO
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        return buffer.getvalue()
    
    def _generate_teaching_certificate(self, first: str, last: str, school: Dict, position: str) -> bytes:
        """Generate Teaching Certificate from Head of School"""
        w, h = 2480, 3508
        img = Image.new('RGB', (w, h), (255, 255, 255))
        draw = ImageDraw.Draw(img)
        
        try:
            font_title = load_font("arialbd", 52)
            font_header = load_font("arialbd", 40)
            font_normal = load_font("arial", 35)
            font_bold = load_font("arialbd", 35)
        except:
            font_title = font_header = font_normal = font_bold = ImageFont.load_default()
        
        # School header
        y = 100
        draw.text((w//2, y), school["name"].upper(), fill=(0, 35, 102), font=font_title, anchor="mm")
        y += 70
        draw.text((w//2, y), school["address"], fill=(60, 60, 60), font=font_normal, anchor="mm")
        y += 50
        draw.text((w//2, y), f"{school['postcode']} {school['town']}", fill=(60, 60, 60), font=font_normal, anchor="mm")
        
        # Document title
        y += 120
        draw.rectangle([(200, y-20), (w-200, y+70)], fill=(240, 240, 250))
        draw.text((w//2, y+25), "ATTESTATION D'EXERCICE", fill=(0, 35, 102), font=font_header, anchor="mm")
        
        # Body
        y += 150
        current_date = datetime.now().strftime("%d %B %Y")
        
        lines = [
            f"Je soussigné(e), Proviseur du {school['name']},",
            f"",
            f"certifie que Madame/Monsieur {first} {last}",
            f"",
            f"exerce les fonctions de {position}",
            f"au sein de notre établissement depuis le 1er septembre {datetime.now().year - random.randint(1, 5)}.",
            f"",
            f"Cette attestation est délivrée pour servir et valoir ce que de droit.",
            f"",
            f"",
            f"Fait à {school['town']}, le {current_date}",
        ]
        
        for line in lines:
            draw.text((200, y), line, fill=(40, 40, 40), font=font_normal)
            y += 65
        
        # Signature
        y += 100
        draw.text((w - 500, y), "Le Proviseur", fill=(0, 0, 0), font=font_bold, anchor="mm")
        
        # Stamp
        stamp_x = w - 500
        stamp_y = y + 120
        draw.ellipse([(stamp_x-60, stamp_y-60), (stamp_x+60, stamp_y+60)], outline=(200, 16, 46), width=5)
        draw.text((stamp_x, stamp_y), school["name"][:3].upper(), fill=(200, 16, 46), font=font_bold, anchor="mm")
        
        from io import BytesIO
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        return buffer.getvalue()
