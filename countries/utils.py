"""
Utility functions shared across all countries
"""

from PIL import Image, ImageFont
from pathlib import Path
import os
import random


def load_font(size_or_name, size=None, bold: bool = False) -> ImageFont.FreeTypeFont:
    """
    Load font with cross-platform support (Linux/Windows)
    
    Supports both old and new signature:
    - Old: load_font('arial', 24) or load_font('arialbd', 24)
    - New: load_font(24, bold=True) or load_font(24)
    
    Args:
        size_or_name: Font size (int) or font name (str) for backward compatibility
        size: Font size when first arg is font name (backward compatibility)
        bold: Whether to use bold font (default: False)
        
    Returns:
        ImageFont object
    """
    # Detect old vs new signature
    if isinstance(size_or_name, str):
        # Old signature: load_font('arial', 24)
        font_name = size_or_name
        font_size = size if size is not None else 24
        # Determine if bold based on font name
        is_bold = 'bd' in font_name.lower() or 'bold' in font_name.lower()
    else:
        # New signature: load_font(24, bold=True)
        font_size = size_or_name
        is_bold = bold
    
    # Bundled fonts (package data) — deterministic across all OSes
    bundled_dir = Path(__file__).parent / "fonts"
    bundled_bold = bundled_dir / "DejaVuSans-Bold.ttf"
    bundled_regular = bundled_dir / "DejaVuSans.ttf"

    # Font paths based on bold (bundled first, then system fonts)
    if is_bold:
        font_paths = [
            str(bundled_bold),
            '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
            '/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf',
            'C:/Windows/Fonts/arialbd.ttf',
            'C:/Windows/Fonts/Arial-Bold.ttf',
            'arialbd.ttf'
        ]
    else:
        font_paths = [
            str(bundled_regular),
            '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
            '/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf',
            'C:/Windows/Fonts/arial.ttf',
            'arial.ttf'
        ]
    
    # Try each path
    for path in font_paths:
        try:
            return ImageFont.truetype(path, font_size)
        except:
            continue
    
    # Ultimate fallback
    return ImageFont.load_default()


# Global cache for photos per session (name-based)
_PHOTO_CACHE = {}

def get_profile_photo(size: tuple = (280, 340), person_id: str = None, gender: str = "Random") -> Image.Image:
    """
    Load a profile photo from foto folder
    Falls back to generated avatar if no photos found
    
    Args:
        size: Tuple of (width, height)
        person_id: Optional identifier for person (e.g., "john_doe") to cache photo
        gender: Gender filter - "Male", "Female", or "Random" (default)
    
    Returns:
        PIL Image or None
    """
    # Check cache first if person_id provided
    if person_id and person_id in _PHOTO_CACHE:
        cached_photo = _PHOTO_CACHE[person_id]
        if cached_photo:
            return cached_photo.resize(size, Image.Resampling.LANCZOS)
        return None
    
    try:
        # Foto directory: override via YOWES_FOTO_DIR, else bundled with the package
        foto_dir = Path(os.environ.get("YOWES_FOTO_DIR", "")) if os.environ.get("YOWES_FOTO_DIR") else Path(__file__).parent / "foto"
        
        if foto_dir.exists() and foto_dir.is_dir():
            # Get all image files
            image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']
            all_photos = [f for f in foto_dir.iterdir() if f.is_file() and f.suffix.lower() in image_extensions]
            
            # Filter by gender prefix if specified
            if gender == "Male":
                photos = [p for p in all_photos if p.stem.startswith('p')]
            elif gender == "Female":
                photos = [p for p in all_photos if p.stem.startswith('w')]
            else:  # Random
                photos = all_photos
            
            if photos:
                # Random select a photo (use hash of person_id for consistency)
                if person_id:
                    # Use hash to consistently select same photo for same person
                    photo_index = hash(person_id) % len(photos)
                    selected_photo = photos[photo_index]
                else:
                    selected_photo = random.choice(photos)
                    
                photo = Image.open(selected_photo)
                
                # Convert to RGB if needed (for PNG with alpha)
                if photo.mode != 'RGB':
                    photo = photo.convert('RGB')
                
                # Cache the photo if person_id provided
                if person_id:
                    _PHOTO_CACHE[person_id] = photo.copy()
                
                # Resize to requested size
                photo = photo.resize(size, Image.Resampling.LANCZOS)
                return photo
    except Exception as e:
        pass
    
    # Cache None if person_id provided and no photo found
    if person_id:
        _PHOTO_CACHE[person_id] = None
    
    # Fallback: return None to indicate no photo available
    return None

def clear_photo_cache():
    """Clear the photo cache (call at start of new generation session)"""
    global _PHOTO_CACHE
    _PHOTO_CACHE.clear()


def generate_initials_avatar(first: str, last: str, size: tuple = (280, 340), 
                             bg_color: tuple = (70, 130, 180)) -> Image.Image:
    """Generate simple avatar with initials as fallback"""
    photo = Image.new('RGB', size, bg_color)
    
    try:
        from PIL import ImageDraw
        draw = ImageDraw.Draw(photo)
        
        font = load_font('arial', 72)
        
        initials = f"{first[0]}{last[0]}"
        draw.text((size[0]//2, size[1]//2), initials, fill=(255, 255, 255), font=font, anchor="mm")
    except:
        pass
    
    return photo
