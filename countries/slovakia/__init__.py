"""
Slovakia data and document generators

Slovak teacher verification requirements:
1. Payslip (Výplatná páska)
2. Employment Letter (Pracovné potvrdenie)
3. Signed School Letter (Potvrdenie zo školy)
"""

from typing import Dict, List
from ..base import CountryGenerator
from ..utils import get_profile_photo, generate_initials_avatar, load_font
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime
import random


# Slovakia Schools Database
DEFAULT_SLOVAKIA_SCHOOLS = [
    {"name": "Gymnázium Jána Kollára", "address": "Kollárovo námestie 4", "city": "Bratislava", "region": "Bratislavský kraj", "postcode": "81106", "phone": "+421 2 5441 4207", "domain": "gjk.sk"},
    {"name": "Gymnázium Pavla Horova", "address": "Seberíniho 1", "city": "Michalovce", "region": "Košický kraj", "postcode": "07101", "phone": "+421 56 642 2490", "domain": "gphmi.sk"},
    {"name": "Gymnázium Mikuláša Galandu", "address": "Gorazdova 12", "city": "Banská Bystrica", "region": "Banskobystrický kraj", "postcode": "97401", "phone": "+421 48 414 5025", "domain": "gymbb.sk"},
    {"name": "Obchodná akadémia", "address": "Hlboká cesta 23", "city": "Žilina", "region": "Žilinský kraj", "postcode": "01008", "phone": "+421 41 562 4411", "domain": "oaza.sk"},
    {"name": "Gymnázium Jozefa Gregora Tajovského", "address": "Nálepkova 1", "city": "Banská Bystrica", "region": "Banskobystrický kraj", "postcode": "97411", "phone": "+421 48 415 5555", "domain": "tajovske.sk"},
    {"name": "Gymnázium Poštová", "address": "Poštová 9", "city": "Košice", "postcode": "04012", "region": "Košický kraj", "phone": "+421 55 622 0914", "domain": "gymposta.sk"},
    {"name": "Gymnázium Grösslingová", "address": "Grösslingová 18", "city": "Bratislava", "region": "Bratislavský kraj", "postcode": "81109", "phone": "+421 2 5249 5078", "domain": "gymgros.sk"},
    {"name": "Gymnázium sv. Tomáša Akvinského", "address": "Spišská Kapitula 16", "city": "Spišské Podhradie", "region": "Prešovský kraj", "postcode": "05304", "phone": "+421 53 454 1354", "domain": "gymta.sk"},
    {"name": "Gymnázium Ladislava Sáru", "address": "Sládkovičova 6", "city": "Lučenec", "region": "Banskobystrický kraj", "postcode": "98401", "phone": "+421 47 433 1243", "domain": "gymlc.sk"},
    {"name": "Bilingválne gymnázium", "address": "Metodova 2", "city": "Nitra", "region": "Nitriansky kraj", "postcode": "94901", "phone": "+421 37 652 2486", "domain": "bilingvanr.sk"},
]

# Slovak Names
SLOVAKIA_FIRST_NAMES = [
    "Peter", "Jana", "Martin", "Eva", "Ján", "Mária", "Tomáš", "Anna",
    "Michal", "Katarína", "Lukáš", "Zuzana", "Marek", "Lenka", "Pavol", "Petra",
    "Andrej", "Veronika", "Matej", "Lucia", "Miroslav", "Monika", "Juraj", "Martina",
    "Vladimír", "Andrea", "Radoslav", "Iveta", "Milan", "Barbora", "Filip", "Simona"
]

SLOVAKIA_LAST_NAMES = [
    "Horváth", "Kováč", "Varga", "Tóth", "Nagy", "Baláž", "Szabó", "Molnár",
    "Novák", "Lukáč", "Fekete", "Papp", "Oláh", "Kiss", "Farkas", "Bodnár",
    "Takáč", "Hudák", "Gál", "Soták", "Urban", "Vrábel", "Polák", "Krajčí",
    "Nemeth", "Dudáš", "Balogh", "Marcin", "Žák", "Rác", "Lakatoš", "Čech"
]

# Slovak Teaching Positions
SLOVAKIA_TEACHING_POSITIONS = [
    "Učiteľ/ka matematiky",
    "Učiteľ/ka slovenčiny",
    "Učiteľ/ka angličtiny",
    "Učiteľ/ka prírodopisu",
    "Učiteľ/ka fyziky",
    "Učiteľ/ka chémie",
    "Učiteľ/ka dejepisu",
    "Učiteľ/ka zemepisu",
    "Učiteľ/ka telesnej výchovy",
    "Učiteľ/ka hudby",
    "Učiteľ/ka informatiky",
    "Vedúci/a predmetovej komisie",
]


class SlovakiaGenerator(CountryGenerator):
    """Slovakia-specific document generator"""
    
    def get_country_name(self) -> str:
        return "Slovakia"
    
    def get_country_code(self) -> str:
        return "slovakia"
    
    def get_schools_data(self) -> List[Dict]:
        return DEFAULT_SLOVAKIA_SCHOOLS
    
    def get_first_names(self) -> List[str]:
        return SLOVAKIA_FIRST_NAMES
    
    def get_last_names(self) -> List[str]:
        return SLOVAKIA_LAST_NAMES
    
    def get_positions(self) -> List[str]:
        return SLOVAKIA_TEACHING_POSITIONS
    
    def get_document_types(self) -> List[str]:
        return ["payslip", "employment_letter", "signed_school_letter"]
    
    def generate_document(self, doc_type: str, first: str, last: str, 
                         school: Dict, position: str, dob: str) -> bytes:
        """Generate Slovakia document"""
        if doc_type == "payslip":
            return self._generate_payslip(first, last, school, position)
        elif doc_type == "employment_letter":
            return self._generate_employment_letter(first, last, school, position, dob)
        elif doc_type == "signed_school_letter":
            return self._generate_signed_school_letter(first, last, school, position)
        else:
            raise ValueError(f"Unknown document type: {doc_type}")
    
    def _generate_payslip(self, first: str, last: str, school: Dict, position: str) -> bytes:
        """Generate Payslip (Výplatná páska)"""
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
        
        # Slovak flag colors header
        draw.rectangle([(0, 0), (w, 50)], fill=(255, 255, 255))
        draw.rectangle([(0, 50), (w, 100)], fill=(11, 78, 162))
        draw.rectangle([(0, 100), (w, 150)], fill=(238, 28, 37))
        
        # Title
        y = 220
        draw.text((w//2, y), "VÝPLATNÁ PÁSKA", fill=(11, 78, 162), font=font_title, anchor="mm")
        
        # School info box
        y = 320
        draw.rectangle([(150, y), (w-150, y+280)], fill=(250, 250, 255), outline=(11, 78, 162), width=4)
        
        y += 40
        draw.text((w//2, y), school["name"].upper(), fill=(0, 0, 0), font=font_header, anchor="mm")
        y += 55
        draw.text((w//2, y), school["address"], fill=(80, 80, 80), font=font_normal, anchor="mm")
        y += 50
        draw.text((w//2, y), f"{school['postcode']} {school['city']}", 
                 fill=(80, 80, 80), font=font_normal, anchor="mm")
        y += 50
        draw.text((w//2, y), f"Tel: {school['phone']}", fill=(100, 100, 100), font=font_small, anchor="mm")
        
        # Period info
        y += 120
        months_sk = ["január", "február", "marec", "apríl", "máj", "jún", 
                    "júl", "august", "september", "október", "november", "december"]
        current_month = f"{months_sk[datetime.now().month-1]} {datetime.now().year}"
        payslip_number = f"VP-{random.randint(1000, 9999)}"
        
        info_items = [
            ("Číslo výplatnej pásky:", payslip_number),
            ("Obdobie:", current_month),
            ("", ""),
        ]
        
        for label, value in info_items:
            if label:
                draw.text((250, y), label, fill=(100, 100, 100), font=font_bold)
                draw.text((750, y), value, fill=(0, 0, 0), font=font_normal)
                y += 60
            else:
                y += 30
        
        # Employee data
        y += 20
        draw.rectangle([(150, y), (w-150, y+60)], fill=(11, 78, 162))
        draw.text((w//2, y+30), "ÚDAJE O ZAMESTNANCOVI", fill=(255, 255, 255), font=font_header, anchor="mm")
        
        y += 100
        rodne_cislo = f"{random.randint(700101, 991231)}/{random.randint(1000, 9999)}"
        
        employee_data = [
            ("Meno a priezvisko", f"{first} {last}"),
            ("Rodné číslo", rodne_cislo),
            ("Pozícia", position),
            ("Platová trieda", f"{random.randint(8, 12)}. trieda"),
        ]
        
        for label, value in employee_data:
            draw.text((250, y), label, fill=(100, 100, 100), font=font_bold)
            draw.text((750, y), value, fill=(0, 0, 0), font=font_normal)
            y += 60
        
        # Salary details
        y += 60
        draw.rectangle([(150, y), (w-150, y+60)], fill=(11, 78, 162))
        draw.text((w//2, y+30), "PRÍJMY", fill=(255, 255, 255), font=font_header, anchor="mm")
        
        y += 100
        base_salary = random.randint(1100, 1800)
        
        # Income section
        income_items = [
            ("Tarifný plat", f"{base_salary:,} €"),
            ("Príplatok za výkon", f"{int(base_salary * 0.20):,} €"),
            ("Odmena", f"{int(base_salary * 0.10):,} €"),
        ]
        
        for label, value in income_items:
            draw.text((250, y), label, fill=(0, 0, 0), font=font_normal)
            draw.text((w-300, y), value, fill=(0, 0, 0), font=font_normal, anchor="ra")
            y += 55
        
        total_gross = int(base_salary * 1.30)
        
        # Total
        y += 30
        draw.line([(200, y), (w-200, y)], fill=(11, 78, 162), width=4)
        y += 50
        draw.text((250, y), "HRUBÁ MZDA", fill=(0, 0, 0), font=font_bold)
        draw.text((w-300, y), f"{total_gross:,} €", fill=(11, 78, 162), font=font_bold, anchor="ra")
        
        # Deductions
        y += 100
        draw.rectangle([(150, y), (w-150, y+60)], fill=(100, 100, 100))
        draw.text((w//2, y+30), "ZRÁŽKY", fill=(255, 255, 255), font=font_header, anchor="mm")
        
        y += 100
        deduction_items = [
            ("Sociálne poistenie (9,4%)", f"{int(total_gross * 0.094):,} €"),
            ("Zdravotné poistenie (4%)", f"{int(total_gross * 0.04):,} €"),
            ("Daň z príjmu", f"{int(total_gross * 0.15):,} €"),
        ]
        
        for label, value in deduction_items:
            draw.text((250, y), label, fill=(0, 0, 0), font=font_normal)
            draw.text((w-300, y), value, fill=(0, 0, 0), font=font_normal, anchor="ra")
            y += 55
        
        total_deduction = int(total_gross * 0.284)
        net_salary = total_gross - total_deduction
        
        # Net salary
        y += 30
        draw.line([(200, y), (w-200, y)], fill=(100, 100, 100), width=4)
        y += 50
        draw.text((250, y), "ČISTÁ MZDA", fill=(0, 0, 0), font=font_bold)
        draw.text((w-300, y), f"{net_salary:,} €", fill=(0, 128, 0), font=font_bold, anchor="ra")
        
        # Signature
        y = h - 550
        draw.text((w//2, y), f"{school['city']}, {datetime.now().strftime('%d. %m. %Y')}", 
                 fill=(80, 80, 80), font=font_normal, anchor="mm")
        
        y += 100
        draw.text((w-600, y), "Ekonomické oddelenie", fill=(0, 0, 0), font=font_bold, anchor="mm")
        
        y += 150
        draw.line([(w-800, y), (w-400, y)], fill=(0, 0, 0), width=2)
        y += 40
        draw.text((w-600, y), "Podpis zodpovednej osoby", fill=(80, 80, 80), font=font_small, anchor="mm")
        
        # Footer
        y = h - 150
        draw.line([(150, y), (w-150, y)], fill=(11, 78, 162), width=3)
        y += 40
        draw.text((w//2, y), "Elektronický dokument - platný bez podpisu", 
                 fill=(120, 120, 120), font=font_small, anchor="mm")
        
        from io import BytesIO
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        return buffer.getvalue()
    
    def _generate_employment_letter(self, first: str, last: str, school: Dict, position: str, dob: str) -> bytes:
        """Generate Employment Letter (Pracovné potvrdenie)"""
        w, h = 2480, 3508
        img = Image.new('RGB', (w, h), (255, 255, 255))
        draw = ImageDraw.Draw(img)
        
        try:
            font_title = load_font("arialbd", 52)
            font_header = load_font("arialbd", 44)
            font_normal = load_font("arial", 38)
            font_bold = load_font("arialbd", 38)
            font_small = load_font("arial", 32)
        except:
            font_title = font_header = font_normal = font_bold = font_small = ImageFont.load_default()
        
        # Header with Slovak colors
        draw.rectangle([(0, 0), (w, 50)], fill=(255, 255, 255))
        draw.rectangle([(0, 50), (w, 100)], fill=(11, 78, 162))
        draw.rectangle([(0, 100), (w, 150)], fill=(238, 28, 37))
        
        # School header
        y = 220
        draw.text((w//2, y), school["name"].upper(), fill=(0, 0, 0), font=font_title, anchor="mm")
        y += 65
        draw.text((w//2, y), school["address"], fill=(80, 80, 80), font=font_normal, anchor="mm")
        y += 50
        draw.text((w//2, y), f"{school['postcode']} {school['city']}", 
                 fill=(80, 80, 80), font=font_normal, anchor="mm")
        y += 45
        draw.text((w//2, y), f"Tel: {school['phone']}", fill=(100, 100, 100), font=font_small, anchor="mm")
        
        # Decorative line
        y += 60
        draw.rectangle([(200, y), (w-200, y+6)], fill=(11, 78, 162))
        
        # Document title
        y += 100
        draw.rectangle([(150, y), (w-150, y+100)], fill=(250, 250, 255))
        draw.text((w//2, y+50), "PRACOVNÉ POTVRDENIE", fill=(11, 78, 162), font=font_header, anchor="mm")
        
        # Reference number
        y += 150
        ref_number = f"Č. {random.randint(100, 999)}/{datetime.now().year}"
        draw.text((w//2, y), ref_number, fill=(0, 0, 0), font=font_bold, anchor="mm")
        
        # Content
        y += 120
        content_lines = [
            f"Riaditeľstvo {school['name']}",
            "týmto potvrdzuje, že:",
        ]
        
        for line in content_lines:
            draw.text((w//2, y), line, fill=(60, 60, 60), font=font_normal, anchor="mm")
            y += 55
        
        y += 50
        rodne_cislo = f"{random.randint(700101, 991231)}/{random.randint(1000, 9999)}"
        
        teacher_data = [
            ("Meno a priezvisko", f": {first} {last}"),
            ("Rodné číslo", f": {rodne_cislo}"),
            ("Dátum narodenia", f": {dob}"),
            ("Funkcia", f": {position}"),
            ("Pracovný pomer od", f": {datetime.now().year - random.randint(3, 12)}"),
        ]
        
        for label, value in teacher_data:
            draw.text((500, y), label, fill=(0, 0, 0), font=font_bold)
            draw.text((1000, y), value, fill=(0, 0, 0), font=font_normal)
            y += 65
        
        y += 80
        cert_text = [
            f"je zamestnancom/zamestnankyňou našej školy, kde vykonáva funkciu",
            f"{position}. Počas celého obdobia plní pracovné úlohy",
            "s vysokou mierou zodpovednosti a profesionality.",
            "",
            "Toto potvrdenie sa vydáva na žiadosť zamestnanca/zamestnankyne",
            "na použitie pre úradné účely.",
        ]
        
        for line in cert_text:
            draw.text((w//2, y), line, fill=(60, 60, 60), font=font_normal, anchor="mm")
            y += 55 if line else 30
        
        # Signature
        y += 100
        draw.text((w//2, y), f"V {school['city']}, dňa {datetime.now().strftime('%d. %m. %Y')}", 
                 fill=(80, 80, 80), font=font_normal, anchor="mm")
        
        y += 80
        draw.text((w-600, y), "Riaditeľstvo školy", fill=(0, 0, 0), font=font_bold, anchor="mm")
        
        # Stamp placeholder
        stamp_x = w - 600
        stamp_y = y + 120
        draw.ellipse([(stamp_x-90, stamp_y-90), (stamp_x+90, stamp_y+90)], outline=(11, 78, 162), width=8)
        draw.text((stamp_x, stamp_y), "PEČIATKA", fill=(11, 78, 162), font=font_header, anchor="mm")
        
        y += 200
        draw.line([(w-800, y), (w-400, y)], fill=(0, 0, 0), width=3)
        y += 45
        draw.text((w-600, y), "Riaditeľ/ka školy", fill=(0, 0, 0), font=font_small, anchor="mm")
        y += 40
        draw.text((w-600, y), school['name'], fill=(80, 80, 80), font=font_small, anchor="mm")
        
        # Footer
        y = h - 120
        draw.line([(150, y), (w-150, y)], fill=(11, 78, 162), width=3)
        y += 45
        draw.text((w//2, y), f"Oficiálny dokument {school['name']}", 
                 fill=(120, 120, 120), font=font_small, anchor="mm")
        
        from io import BytesIO
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        return buffer.getvalue()
    
    def _generate_signed_school_letter(self, first: str, last: str, school: Dict, position: str) -> bytes:
        """Generate Signed School Letter (Potvrdenie zo školy)"""
        w, h = 2480, 3508
        img = Image.new('RGB', (w, h), (255, 255, 255))
        draw = ImageDraw.Draw(img)
        
        try:
            font_title = load_font("arialbd", 52)
            font_header = load_font("arialbd", 44)
            font_normal = load_font("arial", 38)
            font_bold = load_font("arialbd", 38)
            font_small = load_font("arial", 32)
        except:
            font_title = font_header = font_normal = font_bold = font_small = ImageFont.load_default()
        
        # Slovak flag header
        draw.rectangle([(0, 0), (w, 60)], fill=(255, 255, 255))
        draw.rectangle([(0, 60), (w, 110)], fill=(11, 78, 162))
        draw.rectangle([(0, 110), (w, 160)], fill=(238, 28, 37))
        
        # School header
        y = 230
        draw.text((w//2, y), school["name"].upper(), fill=(11, 78, 162), font=font_title, anchor="mm")
        y += 65
        draw.text((w//2, y), school["address"], fill=(80, 80, 80), font=font_normal, anchor="mm")
        y += 50
        draw.text((w//2, y), f"{school['postcode']} {school['city']}", 
                 fill=(80, 80, 80), font=font_normal, anchor="mm")
        y += 45
        draw.text((w//2, y), f"Tel: {school['phone']} | Web: {school['domain']}", 
                 fill=(100, 100, 100), font=font_small, anchor="mm")
        
        # Decorative line
        y += 70
        draw.rectangle([(200, y), (w-200, y+6)], fill=(11, 78, 162))
        
        # Title
        y += 100
        draw.text((w//2, y), "POTVRDENIE", fill=(11, 78, 162), 
                 font=font_header, anchor="mm")
        
        # Date
        y += 100
        draw.text((w-300, y), datetime.now().strftime("%d. %m. %Y"), 
                 fill=(80, 80, 80), font=font_normal, anchor="rm")
        
        # Salutation
        y += 100
        draw.text((250, y), "Komu sa to týka,", fill=(40, 40, 40), font=font_bold)
        
        # Body
        y += 100
        content_lines = [
            f"Týmto potvrdzujeme, že pán/pani {first} {last}",
            f"je zamestnancom/zamestnankyňou {school['name']}",
            f"na pozícii {position}.",
            "",
            f"Pán/pani {last} pracuje v našej škole od roku",
            f"{datetime.now().year - random.randint(3, 10)} a počas celého obdobia vykonáva",
            "svoje pracovné povinnosti na vysokej profesionálnej úrovni.",
            "",
            "Medzi jeho/jej úlohy patria:",
            "• Vyučovanie podľa schváleného učebného plánu",
            "• Hodnotenie a sledovanie pokroku žiakov",
            "• Triednictvo a pedagogická starostlivosť",
            "• Účasť na školských aktivitách",
            "",
            f"Pán/pani {last} spĺňa všetky požiadavky stanovené",
            "platnou legislatívou a má všetky potrebné kvalifikácie",
            "na výkon pedagogickej činnosti.",
            "",
            "Toto potvrdenie vydávame na žiadosť zamestnanca/zamestnankyne.",
        ]
        
        for line in content_lines:
            if line.startswith("•"):
                draw.text((350, y), line, fill=(60, 60, 60), font=font_normal)
                y += 55
            elif line:
                draw.text((250, y), line, fill=(60, 60, 60), font=font_normal)
                y += 55
            else:
                y += 30
        
        # Signature section
        y += 80
        draw.text((250, y), "S pozdravom,", fill=(40, 40, 40), font=font_normal)
        
        y += 120
        draw.line([(250, y), (850, y)], fill=(11, 78, 162), width=3)
        y += 45
        draw.text((250, y), "Riaditeľ/ka školy", fill=(0, 0, 0), font=font_bold)
        y += 50
        draw.text((250, y), school['name'], fill=(80, 80, 80), font=font_small)
        
        # School stamp
        stamp_x, stamp_y = 1800, y - 120
        draw.ellipse([(stamp_x-80, stamp_y-80), (stamp_x+80, stamp_y+80)], 
                    outline=(11, 78, 162), width=8)
        draw.text((stamp_x, stamp_y), "PEČIATKA", fill=(11, 78, 162), font=font_bold, anchor="mm")
        
        # Footer
        y = h - 120
        draw.line([(150, y), (w-150, y)], fill=(11, 78, 162), width=3)
        y += 45
        draw.text((w//2, y), f"Oficiálna korešpondencia {school['name']}", 
                 fill=(120, 120, 120), font=font_small, anchor="mm")
        
        from io import BytesIO
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        return buffer.getvalue()
