"""
Countries module for Canva Education document generation
Each country has its own data and document generators
"""

from typing import Dict, Type
from .base import CountryGenerator

# Registry for all available countries
COUNTRIES: Dict[str, Type[CountryGenerator]] = {}


def register_country(code: str, generator_class: Type[CountryGenerator]):
    """Register a country generator"""
    COUNTRIES[code] = generator_class


def get_country(code: str) -> Type[CountryGenerator]:
    """Get a country generator by code"""
    if code not in COUNTRIES:
        raise ValueError(f"Country '{code}' not supported. Available: {list(COUNTRIES.keys())}")
    return COUNTRIES[code]


def list_countries() -> list:
    """List all available country codes"""
    return list(COUNTRIES.keys())


# Auto-import all country modules
try:
    from .uk import UKGenerator
    register_country("uk", UKGenerator)
except ImportError:
    pass

try:
    from .france import FranceGenerator
    register_country("france", FranceGenerator)
except ImportError:
    pass

try:
    from .netherlands import NetherlandsGenerator
    register_country("netherlands", NetherlandsGenerator)
except ImportError:
    pass

try:
    from .indonesia import IndonesiaGenerator
    register_country("indonesia", IndonesiaGenerator)
except ImportError:
    pass

try:
    from .australia import AustraliaGenerator
    register_country("australia", AustraliaGenerator)
except ImportError:
    pass

try:
    from .canada import CanadaGenerator
    register_country("canada", CanadaGenerator)
except ImportError:
    pass

try:
    from .spain import SpainGenerator
    register_country("spain", SpainGenerator)
except ImportError:
    pass

try:
    from .argentina import ArgentinaGenerator
    register_country("argentina", ArgentinaGenerator)
except ImportError:
    pass

try:
    from .slovakia import SlovakiaGenerator
    register_country("slovakia", SlovakiaGenerator)
except ImportError:
    pass

try:
    from .mexico import MexicoGenerator
    register_country("mexico", MexicoGenerator)
except ImportError:
    pass

try:
    from .philippines import PhilippinesGenerator
    register_country("philippines", PhilippinesGenerator)
except ImportError:
    pass

try:
    from .thailand import ThailandGenerator
    register_country("thailand", ThailandGenerator)
except ImportError:
    pass

try:
    from .us import USGenerator
    register_country("us", USGenerator)
except ImportError:
    pass
