"""
Base classes for country-specific document generators
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Tuple
from pathlib import Path
import random
import re


class CountryGenerator(ABC):
    """Base class for country-specific document generators"""
    
    def __init__(self):
        self.schools = self._load_schools()
        self.first_names = self.get_first_names()
        self.last_names = self.get_last_names()
        self.positions = self.get_positions()
    
    @abstractmethod
    def get_country_name(self) -> str:
        """Return the country name"""
        pass
    
    @abstractmethod
    def get_country_code(self) -> str:
        """Return the country code (e.g., 'uk', 'france')"""
        pass
    
    @abstractmethod
    def get_schools_data(self) -> List[Dict]:
        """Return list of schools"""
        pass
    
    @abstractmethod
    def get_first_names(self) -> List[str]:
        """Return list of first names"""
        pass
    
    @abstractmethod
    def get_last_names(self) -> List[str]:
        """Return list of last names"""
        pass
    
    @abstractmethod
    def get_positions(self) -> List[str]:
        """Return list of teaching positions"""
        pass
    
    @abstractmethod
    def get_document_types(self) -> List[str]:
        """Return list of available document types"""
        pass
    
    @abstractmethod
    def generate_document(self, doc_type: str, first: str, last: str, 
                         school: Dict, position: str, dob: str) -> bytes:
        """Generate a specific document type"""
        pass
    
    def _load_schools(self) -> List[Dict]:
        """Load schools from JSON or return default data"""
        data_dir = Path(__file__).parent.parent.parent / "data"
        json_path = data_dir / f"{self.get_country_code()}_schools.json"
        
        if json_path.exists():
            try:
                import json
                return json.loads(json_path.read_text())
            except:
                pass
        
        return self.get_schools_data()
    
    def random_school(self) -> Dict:
        """Get a random school"""
        return random.choice(self.schools)
    
    def search_school(self, query: str) -> Dict:
        """Search for a school by name with a tolerant fallback for partial matches and typos."""
        if query is None:
            return None

        q = str(query).strip()
        if not q:
            return None

        def normalize(value: str) -> str:
            value = value.lower()
            value = re.sub(r"[^a-z0-9]+", " ", value)
            return " ".join(value.split())

        q_norm = normalize(q)

        for school in self.schools:
            school_name = school.get("name", "")
            if normalize(school_name) == q_norm:
                return school

        for school in self.schools:
            school_name = school.get("name", "")
            if q_norm in normalize(school_name):
                return school

        q_tokens = set(q_norm.split())
        best_school = None
        best_score = 0

        for school in self.schools:
            school_name = school.get("name", "")
            school_norm = normalize(school_name)
            school_tokens = set(school_norm.split())
            if not school_tokens:
                continue

            common = q_tokens & school_tokens
            score = len(common) * 4
            if q_norm and q_norm in school_norm:
                score += 10
            if school_norm and school_norm in q_norm:
                score += 10

            if score > best_score:
                best_score = score
                best_school = school

        if best_score >= 2:
            return best_school

        return None
    
    def list_schools(self) -> List[str]:
        """List all school names"""
        return [s["name"] for s in self.schools]
    
    def generate_name(self) -> Tuple[str, str]:
        """Generate a random name"""
        return random.choice(self.first_names), random.choice(self.last_names)
    
    def random_position(self) -> str:
        """Get a random teaching position"""
        return random.choice(self.positions)
