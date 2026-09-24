"""
MCP server exposing the Yowes document generator as agent-callable tools.

Run (stdio transport):
    python mcp_server.py

Tools:
  - list_countries          -> available countries + document types
  - list_schools            -> schools for a country
  - generate_documents      -> render one or more documents to PNG files
"""

from pathlib import Path
from typing import List, Optional

from mcp.server.mcpserver import MCPServer

from countries import get_country, list_countries
from countries.utils import clear_photo_cache

mcp = MCPServer("yowes-doc-generator")

# Base output directory (project_root/output)
BASE_DIR = Path(__file__).parent
DEFAULT_OUTPUT_DIR = BASE_DIR / "output"


@mcp.tool()
def list_countries_tool() -> List[dict]:
    """List all available countries, their display names, and the document types each can generate."""
    result = []
    for code in list_countries():
        gen = get_country(code)()
        result.append({
            "code": code,
            "name": gen.get_country_name(),
            "document_types": gen.get_document_types(),
        })
    return result


@mcp.tool()
def list_schools(country: str) -> List[dict]:
    """List all schools for a given country code (e.g. 'us', 'uk'). Each entry has name/address/town/postcode/state/phone/lea."""
    gen = get_country(country)()
    return gen.schools


@mcp.tool()
def generate_documents(
    country: str,
    first_name: str,
    last_name: str,
    school_name: str,
    position: str,
    date_of_birth: str,
    gender: str = "Random",
    document_types: Optional[List[str]] = None,
    output_dir: str = "",
) -> dict:
    """Generate teacher verification documents (employment letter, teacher ID, teaching license).

    Args:
        country: Country code from list_countries (e.g. 'us', 'uk').
        first_name / last_name: The teacher's name.
        school_name: Exact or partial school name (matched against that country's school list).
        position: Teaching position/title.
        date_of_birth: Display date of birth string (shown on the teacher ID).
        gender: 'Random', 'Male', or 'Female' — selects which photo pool is used.
        document_types: Which documents to render. Omit for all. e.g. ['employment_letter', 'teacher_id'].
        output_dir: Where to save PNGs (relative to project root). Defaults to 'output'.

    Returns:
        Dict with 'files' (absolute paths), 'count', and 'output_dir'.
    """
    gen = get_country(country)()

    school = gen.search_school(school_name)
    if school is None:
        names = [s["name"] for s in gen.schools[:8]]
        suggestion = ", ".join(names)
        raise ValueError(
            f"School '{school_name}' was not found for '{country}'. Please choose a school from the list or type a close match. Examples: {suggestion}."
        )

    types = document_types or gen.get_document_types()
    if "all" in types:
        types = gen.get_document_types()

    supported_types = gen.get_document_types()
    invalid_types = [doc_type for doc_type in types if doc_type not in supported_types]
    if invalid_types:
        raise ValueError(
            f"Unsupported document type(s) for '{country}': {', '.join(invalid_types)}. "
            f"Available types: {', '.join(supported_types)}."
        )

    # Consistent photo per person (same mechanism as the GUI)
    gen._current_person_id = f"{first_name}_{last_name}".lower()
    gen._current_gender = gender
    clear_photo_cache()

    out_dir = (BASE_DIR / output_dir) if output_dir else DEFAULT_OUTPUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    from datetime import datetime
    import random

    files = []
    for dtype in types:
        data = gen.generate_document(
            doc_type=dtype,
            first=first_name,
            last=last_name,
            school=school,
            position=position,
            dob=date_of_birth,
        )
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{country}_{dtype}_{first_name.lower()}_{last_name.lower()}_{stamp}.png"
        path = out_dir / filename
        path.write_bytes(data)
        files.append(str(path))

    return {
        "country": country,
        "school": school["name"],
        "document_types": types,
        "files": files,
        "count": len(files),
        "output_dir": str(out_dir),
    }


def main() -> None:
    """Entry point for the MCP server (stdio transport)."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
