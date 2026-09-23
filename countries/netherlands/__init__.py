"""
Netherlands data and document generators

Dutch teachers verification requirements:
1. Employment contract (Arbeidsovereenkomst)
2. Teacher registration certificate (Registratie Lerarenregister)
3. DUO declaration (Verklaring van DUO)
4. School ID card
"""

from typing import Dict, List
from ..base import CountryGenerator
from ..utils import get_profile_photo, generate_initials_avatar
from PIL import Image, ImageDraw, ImageFont
from ..utils import load_font
from datetime import datetime, timedelta
import random


# Netherlands Schools Database
DEFAULT_NETHERLANDS_SCHOOLS = [
    {"name": "Amsterdam Lyceum", "address": "Valeriusplein 15", "town": "Amsterdam", "postcode": "1075 BL", "phone": "+31 20 644 84 88", "region": "Noord-Holland"},
    {"name": "Erasmiaans Gymnasium", "address": "Wytemaweg 25", "town": "Rotterdam", "postcode": "3015 CN", "phone": "+31 10 436 80 88", "region": "Zuid-Holland"},
    {"name": "Gymnasium Haganum", "address": "Laan van Meerdervoort 167", "town": "Den Haag", "postcode": "2517 BE", "phone": "+31 70 363 57 50", "region": "Zuid-Holland"},
    {"name": "Sint-Jans Lyceum", "address": "Oude Gracht 35", "town": "Utrecht", "postcode": "3511 AL", "phone": "+31 30 231 32 25", "region": "Utrecht"},
    {"name": "Stedelijk Gymnasium Leiden", "address": "Schoolstraat 17", "town": "Leiden", "postcode": "2311 EN", "phone": "+31 71 512 33 30", "region": "Zuid-Holland"},
    {"name": "Christelijk Gymnasium Utrecht", "address": "Spinning 5", "town": "Utrecht", "postcode": "3511 WE", "phone": "+31 30 231 01 44", "region": "Utrecht"},
    {"name": "Stedelijk Gymnasium Haarlem", "address": "Prinsenhof 3", "town": "Haarlem", "postcode": "2011 RD", "phone": "+31 23 531 74 67", "region": "Noord-Holland"},
    {"name": "Maastricht Gymnasium", "address": "Kapoenstraat 2", "town": "Maastricht", "postcode": "6211 KW", "phone": "+31 43 321 24 90", "region": "Limburg"},
    {"name": "Jeroen Bosch College", "address": "Wolput 5", "town": "Den Bosch", "postcode": "5211 HW", "phone": "+31 73 612 36 60", "region": "Noord-Brabant"},
    {"name": "Augustinianum Gymnasium", "address": "Walburgstraat 13", "town": "Eindhoven", "postcode": "5611 BL", "phone": "+31 40 244 01 25", "region": "Noord-Brabant"},
]

# Netherlands Names
NETHERLANDS_FIRST_NAMES = [
    "Jan", "Pieter", "Willem", "Hendrik", "Johannes", "Cornelis", "Dirk", "Gerrit",
    "Thomas", "Lucas", "Tim", "Daan", "Lars", "Sem", "Thijs", "Max",
    "Anna", "Maria", "Emma", "Sophie", "Lisa", "Julia", "Laura", "Eva",
    "Sara", "Lotte", "Sanne", "Fleur", "Isa", "Anne", "Femke", "Nina"
]

NETHERLANDS_LAST_NAMES = [
    "de Jong", "Jansen", "de Vries", "van den Berg", "van Dijk", "Bakker", "Janssen", "Visser",
    "Smit", "Meijer", "de Boer", "Mulder", "de Groot", "Bos", "Vos", "Peters",
    "Hendriks", "van Leeuwen", "Dekker", "Brouwer", "de Wit", "Dijkstra", "Smits", "de Graaf",
    "van der Meer", "van der Linden", "Kok", "Jacobs", "de Haan", "Vermeulen", "van den Heuvel", "van der Heijden"
]

# Netherlands Teaching Positions
NETHERLANDS_TEACHING_POSITIONS = [
    "Docent Nederlands",
    "Docent Wiskunde",
    "Docent Engels",
    "Docent Geschiedenis",
    "Docent Biologie",
    "Docent Scheikunde",
    "Docent Natuurkunde",
    "Docent Economie",
    "Mentor",
    "Teamleider",
]


class NetherlandsGenerator(CountryGenerator):
    """Netherlands-specific document generator"""
    
    def get_country_name(self) -> str:
        return "Netherlands"
    
    def get_country_code(self) -> str:
        return "netherlands"
    
    def get_schools_data(self) -> List[Dict]:
        return DEFAULT_NETHERLANDS_SCHOOLS
    
    def get_first_names(self) -> List[str]:
        return NETHERLANDS_FIRST_NAMES
    
    def get_last_names(self) -> List[str]:
        return NETHERLANDS_LAST_NAMES
    
    def get_positions(self) -> List[str]:
        return NETHERLANDS_TEACHING_POSITIONS
    
    def get_document_types(self) -> List[str]:
        return ["employment_contract", "teacher_registration", "duo_declaration", "school_id"]
    
    def generate_document(self, doc_type: str, first: str, last: str, 
                         school: Dict, position: str, dob: str) -> bytes:
        """Generate Netherlands document"""
        if doc_type == "employment_contract":
            return self._generate_employment_contract(first, last, school, position)
        elif doc_type == "teacher_registration":
            return self._generate_teacher_registration(first, last, position)
        elif doc_type == "duo_declaration":
            return self._generate_duo_declaration(first, last, school)
        elif doc_type == "school_id":
            return self._generate_school_id(first, last, school, position, dob)
        else:
            raise ValueError(f"Unknown document type: {doc_type}")
    
    def _generate_employment_contract(self, first: str, last: str, school: Dict, position: str) -> bytes:
        """Generate Arbeidsovereenkomst (Employment Contract)"""
        w, h = 2480, 3508
        img = Image.new('RGB', (w, h), (255, 255, 255))
        draw = ImageDraw.Draw(img)
        
        try:
            font_title = load_font("arialbd", 60)
            font_header = load_font("arialbd", 44)
            font_normal = load_font("arial", 36)
            font_bold = load_font("arialbd", 36)
            font_small = load_font("arial", 30)
        except:
            font_title = font_header = font_normal = font_bold = font_small = ImageFont.load_default()
        
        # Dutch orange border
        draw.rectangle([(0, 0), (w, 40)], fill=(230, 126, 34))
        draw.rectangle([(0, 40), (w, 50)], fill=(255, 255, 255))
        draw.rectangle([(0, 50), (w, 90)], fill=(0, 51, 153))
        
        # Header
        y = 150
        draw.text((w//2, y), "ARBEIDSOVEREENKOMST", fill=(230, 126, 34), font=font_title, anchor="mm")
        y += 70
        draw.text((w//2, y), "VOOR ONBEPAALDE TIJD", fill=(100, 100, 100), font=font_header, anchor="mm")
        
        # Decorative line
        y += 60
        draw.rectangle([(w//2 - 600, y), (w//2 + 600, y+6)], fill=(230, 126, 34))
        
        # School info box
        y += 80
        draw.rectangle([(150, y), (w-150, y+250)], fill=(250, 245, 240), outline=(0, 51, 153), width=4)
        
        y += 40
        draw.text((w//2, y), "WERKGEVER", fill=(0, 51, 153), font=font_bold, anchor="mm")
        y += 60
        draw.text((w//2, y), school["name"], fill=(0, 0, 0), font=font_header, anchor="mm")
        y += 55
        draw.text((w//2, y), school["address"], fill=(80, 80, 80), font=font_normal, anchor="mm")
        y += 50
        draw.text((w//2, y), f"{school['postcode']} {school['town']}", fill=(80, 80, 80), font=font_normal, anchor="mm")
        
        # Employee section
        y += 120
        contract_number = f"AO-{datetime.now().year}-{random.randint(10000, 99999)}"
        current_date = datetime.now().strftime("%d-%m-%Y")
        start_date = f"01-09-{datetime.now().year - random.randint(1, 6)}"
        
        sections = [
            ("Contractnummer:", contract_number),
            ("Datum:", current_date),
            ("", ""),
            ("WERKNEMER", ""),
            (f"Naam: {first} {last}", ""),
            ("", ""),
            ("ARTIKEL 1 - FUNCTIE EN WERKZAAMHEDEN", ""),
            (f"De werknemer wordt aangesteld in de functie van:", ""),
            (f"{position}", ""),
            ("", ""),
            ("De werknemer verplicht zich de aan deze functie verbonden", ""),
            ("werkzaamheden naar beste kunnen te vervullen en zich te gedragen", ""),
            ("naar de regels die gelden binnen de onderwijsinstelling.", ""),
            ("", ""),
            ("ARTIKEL 2 - INGANGSDATUM EN DUUR", ""),
            (f"Deze arbeidsovereenkomst gaat in op: {start_date}", ""),
            ("De overeenkomst is aangegaan voor onbepaalde tijd.", ""),
            ("", ""),
            ("ARTIKEL 3 - WERKTIJDEN", ""),
            ("De werknemer is werkzaam voor 1,0 FTE (voltijds).", ""),
            ("", ""),
            ("ARTIKEL 4 - SALARIS", ""),
            ("Het salaris is conform de CAO Voortgezet Onderwijs,", ""),
            (f"schaal {random.choice(['LB', 'LC', 'LD'])}, trede {random.randint(5, 12)}.", ""),
            ("", ""),
            ("ARTIKEL 5 - PROEFTIJD", ""),
            ("Een proeftijd van twee maanden is van toepassing.", ""),
        ]
        
        for line, _ in sections:
            if "ARTIKEL" in line or "WERKNEMER" in line:
                y += 40
                draw.text((200, y), line, fill=(0, 51, 153), font=font_bold)
                y += 60
            elif line:
                draw.text((200, y), line, fill=(40, 40, 40), font=font_normal)
                y += 52
            else:
                y += 25
        
        # Signature section
        y += 100
        draw.text((w//2, y), f"Getekend te {school['town']}, {current_date}", 
                 fill=(80, 80, 80), font=font_normal, anchor="mm")
        
        y += 120
        draw.line([(300, y), (1000, y)], fill=(0, 51, 153), width=3)
        draw.line([(w-1000, y), (w-300, y)], fill=(0, 51, 153), width=3)
        
        y += 40
        draw.text((650, y), "De werkgever", fill=(0, 0, 0), font=font_bold, anchor="mm")
        draw.text((w-650, y), "De werknemer", fill=(0, 0, 0), font=font_bold, anchor="mm")
        
        y += 50
        draw.text((650, y), school["name"], fill=(100, 100, 100), font=font_small, anchor="mm")
        draw.text((w-650, y), f"{first} {last}", fill=(100, 100, 100), font=font_small, anchor="mm")
        
        # Footer
        y = h - 180
        draw.line([(150, y), (w-150, y)], fill=(230, 126, 34), width=4)
        y += 50
        draw.text((w//2, y), f"{school['name']} - Onderwijsinstelling geregistreerd bij de Inspectie van het Onderwijs", 
                 fill=(120, 120, 120), font=font_small, anchor="mm")
        y += 45
        draw.text((w//2, y), f"Contractreferentie: {contract_number}", 
                 fill=(150, 150, 150), font=font_small, anchor="mm")
        
        from io import BytesIO
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        return buffer.getvalue()
    
    def _generate_teacher_registration(self, first: str, last: str, position: str) -> bytes:
        """Generate Lerarenregister Certificate"""
        w, h = 2480, 3508
        img = Image.new('RGB', (w, h), (255, 255, 255))
        draw = ImageDraw.Draw(img)
        
        try:
            font_title = load_font("arialbd", 56)
            font_header = load_font("arialbd", 42)
            font_normal = load_font("arial", 36)
            font_bold = load_font("arialbd", 36)
        except:
            font_title = font_header = font_normal = font_bold = ImageFont.load_default()
        
        # Border
        draw.rectangle([(100, 100), (w-100, h-100)], outline=(230, 126, 34), width=15)
        draw.rectangle([(120, 120), (w-120, h-120)], outline=(230, 126, 34), width=3)
        
        # Title
        y = 300
        draw.text((w//2, y), "LERARENREGISTER", fill=(230, 126, 34), font=font_title, anchor="mm")
        y += 80
        draw.text((w//2, y), "Registerleraar Certificaat", fill=(100, 100, 100), font=font_header, anchor="mm")
        
        # Content
        y += 150
        reg_number = f"LR-{random.randint(100000, 999999)}"
        
        info_lines = [
            ("Naam:", f"{first} {last}"),
            ("Registratienummer:", reg_number),
            ("Functie:", position),
            ("Status:", "Bevoegd"),
            ("Geldig tot:", datetime.now().strftime("%d-%m-%Y")),
        ]
        
        for label, value in info_lines:
            draw.text((400, y), label, fill=(80, 80, 80), font=font_bold)
            draw.text((1000, y), value, fill=(0, 0, 0), font=font_normal)
            y += 80
        
        # Footer
        y = h - 400
        draw.text((w//2, y), "Dit certificaat bevestigt de registratie in het", fill=(100, 100, 100), font=font_normal, anchor="mm")
        y += 50
        draw.text((w//2, y), "Lerarenregister van de Nederlandse overheid", fill=(100, 100, 100), font=font_normal, anchor="mm")
        
        from io import BytesIO
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        return buffer.getvalue()
    
    def _generate_duo_declaration(self, first: str, last: str, school: Dict) -> bytes:
        """Generate DUO Declaration"""
        w, h = 2480, 3508
        img = Image.new('RGB', (w, h), (255, 255, 255))
        draw = ImageDraw.Draw(img)
        
        try:
            font_title = load_font("arialbd", 54)
            font_header = load_font("arialbd", 42)
            font_normal = load_font("arial", 36)
            font_bold = load_font("arialbd", 36)
            font_small = load_font("arial", 30)
        except:
            font_title = font_header = font_normal = font_bold = font_small = ImageFont.load_default()
        
        # DUO header
        draw.rectangle([(0, 0), (w, 180)], fill=(0, 51, 153))
        
        y = 90
        draw.text((w//2, y), "DUO - DIENST UITVOERING ONDERWIJS", 
                 fill=(255, 255, 255), font=font_title, anchor="mm")
        
        # Document title section
        y = 250
        draw.rectangle([(150, y), (w-150, y+120)], fill=(245, 248, 255), outline=(0, 51, 153), width=4)
        
        y += 60
        draw.text((w//2, y), "VERKLARING VAN INSCHRIJVING", fill=(0, 51, 153), font=font_header, anchor="mm")
        
        # Reference number
        y += 150
        ref_number = f"DUO-{datetime.now().year}-{random.randint(1000000, 9999999)}"
        brin_number = f"{''.join([str(random.randint(0, 9)) for _ in range(2)])}{chr(random.randint(65, 90))}{chr(random.randint(65, 90))}"
        
        draw.text((250, y), "Referentienummer:", fill=(100, 100, 100), font=font_bold)
        draw.text((800, y), ref_number, fill=(0, 0, 0), font=font_normal)
        y += 70
        
        draw.text((250, y), "Datum uitgifte:", fill=(100, 100, 100), font=font_bold)
        draw.text((800, y), datetime.now().strftime("%d-%m-%Y"), fill=(0, 0, 0), font=font_normal)
        
        # Content box
        y += 120
        draw.rectangle([(150, y), (w-150, y+700)], fill=(255, 255, 255), outline=(230, 126, 34), width=5)
        
        y += 60
        draw.text((w//2, y), "GEGEVENS ONDERWIJSPERSONEEL", fill=(230, 126, 34), font=font_header, anchor="mm")
        
        y += 100
        info_sections = [
            ("PERSOONLIJKE GEGEVENS", [
                ("Naam:", f"{last.upper()}, {first}"),
                ("", ""),
            ]),
            ("ONDERWIJSINSTELLING", [
                ("Naam instelling:", school["name"]),
                ("Adres:", school["address"]),
                ("Plaats:", f"{school['postcode']} {school['town']}"),
                ("BRIN-nummer:", brin_number),
                ("Regio:", school.get("region", "Noord-Holland")),
                ("", ""),
            ]),
            ("STATUS REGISTRATIE", [
                ("Status:", "Actief geregistreerd"),
                ("Type benoeming:", "Vaste benoeming"),
                ("Datum indiensttreding:", f"01-09-{datetime.now().year - random.randint(1, 7)}"),
                ("", ""),
            ]),
        ]
        
        for section_title, items in info_sections:
            draw.text((250, y), section_title, fill=(0, 51, 153), font=font_bold)
            y += 70
            
            for label, value in items:
                if label:
                    draw.text((300, y), label, fill=(100, 100, 100), font=font_bold)
                    if value:
                        draw.text((800, y), value, fill=(0, 0, 0), font=font_normal)
                    y += 55
                else:
                    y += 30
        
        # Certification text
        y += 50
        draw.rectangle([(150, y), (w-150, y+300)], fill=(250, 250, 255))
        
        y += 50
        cert_text = [
            "CERTIFICERING",
            "",
            "DUO verklaart hierbij dat bovengenoemde persoon",
            "is geregistreerd in het onderwijspersonenbestand",
            "van de Nederlandse overheid.",
            "",
            "Deze verklaring is geldig voor administratieve doeleinden",
            "en kan worden gebruikt voor verificatie van de",
            "onderwijsbevoegdheid.",
        ]
        
        for line in cert_text:
            if line == "CERTIFICERING":
                draw.text((w//2, y), line, fill=(0, 51, 153), font=font_bold, anchor="mm")
                y += 70
            elif line:
                draw.text((w//2, y), line, fill=(60, 60, 60), font=font_normal, anchor="mm")
                y += 50
            else:
                y += 20
        
        # Signature area
        y = h - 450
        draw.text((w//2, y), "Namens DUO", fill=(80, 80, 80), font=font_normal, anchor="mm")
        
        y += 100
        # Digital stamp
        stamp_x = w//2
        stamp_y = y + 60
        draw.rectangle([(stamp_x-150, stamp_y-50), (stamp_x+150, stamp_y+50)], 
                      outline=(0, 51, 153), width=6)
        draw.text((stamp_x, stamp_y), "DIGITAAL ONDERTEKEND", fill=(0, 51, 153), font=font_bold, anchor="mm")
        
        # Footer
        y = h - 200
        draw.line([(0, y), (w, y)], fill=(0, 51, 153), width=8)
        
        y += 50
        footer_lines = [
            "Dienst Uitvoering Onderwijs (DUO)",
            "Ministerie van Onderwijs, Cultuur en Wetenschap",
            f"Verificatiecode: {ref_number}",
        ]
        
        for line in footer_lines:
            draw.text((w//2, y), line, fill=(120, 120, 120), font=font_small, anchor="mm")
            y += 40
        
        from io import BytesIO
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        return buffer.getvalue()
    
    def _generate_school_id(self, first: str, last: str, school: Dict, position: str, dob: str) -> bytes:
        """Generate School ID Card"""
        w, h = 1280, 800
        img = Image.new('RGB', (w, h), (255, 255, 255))
        draw = ImageDraw.Draw(img)
        
        try:
            font_title = load_font("arialbd", 38)
            font_school = load_font("arialbd", 32)
            font_name = load_font("arialbd", 36)
            font_label = load_font("arial", 20)
            font_value = load_font("arialbd", 24)
            font_small = load_font("arial", 16)
        except:
            font_title = font_school = font_name = font_label = font_value = font_small = ImageFont.load_default()
        
        # Dutch flag header
        draw.rectangle([(0, 0), (w, 30)], fill=(200, 16, 46))  # Red
        draw.rectangle([(0, 30), (w, 60)], fill=(255, 255, 255))  # White
        draw.rectangle([(0, 60), (w, 90)], fill=(0, 51, 153))  # Blue
        
        # Orange accent bar
        draw.rectangle([(0, 90), (w, 110)], fill=(230, 126, 34))
        
        # Title
        draw.text((w//2, 130), "PERSONEELSPAS", fill=(230, 126, 34), font=font_title, anchor="mm")
        
        # Border
        draw.rectangle([(15, 15), (w-15, h-15)], outline=(0, 51, 153), width=6)
        draw.rectangle([(20, 20), (w-20, h-20)], outline=(230, 126, 34), width=2)
        
        # School name
        y = 180
        school_name_short = school["name"][:30]
        draw.text((w//2, y), school_name_short, fill=(0, 51, 153), font=font_school, anchor="mm")
        
        # Photo with border
        photo_size = (220, 280)
        photo_x, photo_y = 50, 230
        
        # Try to get real photo from foto folder
        person_id = getattr(self, '_current_person_id', None)
        gender = getattr(self, '_current_gender', 'Random')
        photo = get_profile_photo(photo_size, person_id=person_id, gender=gender)
        if photo is None:
            # Fallback to initials avatar
            photo = generate_initials_avatar(first, last, photo_size, bg_color=(200, 200, 220))
        
        img.paste(photo, (photo_x, photo_y))
        draw.rectangle([(photo_x-2, photo_y-2), (photo_x+photo_size[0]+2, photo_y+photo_size[1]+2)], 
                      outline=(0, 51, 153), width=4)
        
        # Information
        info_x = 300
        y = 250
        
        staff_id = f"NL-{random.randint(100000, 999999)}"
        issue_date = datetime.now().strftime("%d-%m-%Y")
        expiry_date = (datetime.now() + timedelta(days=5*365)).strftime("%d-%m-%Y")
        
        info_items = [
            ("NAAM", f"{first} {last}"),
            ("FUNCTIE", position[:25]),
            ("PERSONEELSNUMMER", staff_id),
            ("GEBOORTEDATUM", dob.replace("/", "-")),
            ("UITGIFTEDATUM", issue_date),
            ("GELDIG TOT", expiry_date),
        ]
        
        for label, value in info_items:
            draw.text((info_x, y), label, fill=(100, 100, 100), font=font_label)
            y += 28
            draw.text((info_x, y), value, fill=(0, 0, 0), font=font_value)
            y += 55
        
        # QR code placeholder
        qr_size = 100
        qr_x, qr_y = w - 130, 240
        draw.rectangle([(qr_x, qr_y), (qr_x+qr_size, qr_y+qr_size)], 
                      outline=(0, 51, 153), width=3)
        
        # Create simple QR-like pattern
        for i in range(0, qr_size, 10):
            for j in range(0, qr_size, 10):
                if random.random() > 0.5:
                    draw.rectangle([(qr_x+i, qr_y+j), (qr_x+i+8, qr_y+j+8)], fill=(0, 0, 0))
        
        draw.text((qr_x + qr_size//2, qr_y + qr_size + 20), "Verificatie", 
                 fill=(80, 80, 80), font=font_small, anchor="mm")
        
        # Bottom section
        bottom_y = 560
        draw.line([(30, bottom_y), (w-30, bottom_y)], fill=(230, 126, 34), width=4)
        
        # Barcode
        barcode_y = bottom_y + 25
        for i in range(70):
            x = 50 + i * 16
            if random.random() > 0.3:
                width = random.choice([3, 4, 5, 6])
                draw.rectangle([(x, barcode_y), (x+width, barcode_y+70)], fill=(0, 0, 0))
        
        # Footer text
        y = barcode_y + 100
        draw.text((w//2, y), f"Eigendom van {school['name']}", 
                 fill=(100, 100, 100), font=font_small, anchor="mm")
        y += 25
        draw.text((w//2, y), "Bij verlies a.u.b. inleveren bij de receptie", 
                 fill=(120, 120, 120), font=font_small, anchor="mm")
        
        # Security hologram indicator
        holo_x, holo_y = w - 100, 560
        draw.ellipse([(holo_x-40, holo_y-40), (holo_x+40, holo_y+40)], 
                    outline=(230, 126, 34), width=4)
        draw.text((holo_x, holo_y), "✓", fill=(230, 126, 34), font=font_title, anchor="mm")
        
        from io import BytesIO
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        return buffer.getvalue()
