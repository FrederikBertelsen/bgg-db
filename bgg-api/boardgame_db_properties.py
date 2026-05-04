from __future__ import annotations

import os

import pandas as pd

from recommender import _ensure_list


WANTED_FAMILIES = {
    "animals": "Animals",
    "Safari Parks": "Animals",
    "zoos": "Animals",
    "Aquaria": "Animals",
    "adventure": "Adventure",
    "Creatures": "Creatures",
    "Crowdfunding": "Crowdfunded",
    "Digital Implementation": "Digital Implementation",
    "vehicles": "Vehicles",
    "automotive": "Vehicles",
    "cars": "Vehicles",
    "airline": "Vehicles",
    "Trains": "Vehicles",
    "Trucks": "Vehicles",
    "Tropical": "Nature",
    "Nature": "Nature",
    "trees": "Nature",
    "wildlife": "Nature",
    "Forest": "Nature",
    "Weather": "Nature",
    "Swamps": "Nature",
    "bogs": "Nature",
    "Wetlands": "Nature",
    "Witches": "Magic",
    "magic": "Magic",
    "Wizards": "Magic",
    "Spells": "Magic",
    "Sorcery": "Magic",
    "disney": "Fairy Tales",
    "Folk Tales & Fairy Tales": "Fairy Tales",
    "Storytelling": "Fairy Tales",
    "Tableau Building": "Tableau Building",
    "Food": "Food",
    "Restaurant": "Food",
    "Café": "Food",
    "cafe": "Food",
    "ocean": "Ocean",
    "Under the Sea": "Ocean",
    "sea": "Ocean",
    "history": "History",
    "History": "History",
    "Vikings": "History",
    "card game": "Card Game",
    "Playing Card": "Card Game",
    "simulation": "Simulation",
    "crossword": "Word Game",
    "Word Games": "Word Game",
    "words": "Word Game",
    "dungeon Crawler": "Dungeon Crawler",
    "escape Room": "Escape Room",
    "two-player": "Two-Player",
    "Two Player": "Two-Player",
    "fighting": "Fighting",
    "cities": "Location",
    "City": "Location",
    "Continent": "Location",
    "Country": "Location",
    "ancient": "Location",
    "Islands": "Location",
    "Mountains": "Location",
    "Region": "Location",
    "Rivers": "Location",
    "States:": "Location",
    "Sports": "Sports",
    "Space": "Science Fiction",
    "Cyberpunk": "Science Fiction",
    "Robots": "Science Fiction",
    "Sci-Fi": "Science Fiction",
    "Steampunk": "Science Fiction",
    "Spooky": "Horror",
    "Horror": "Horror",
    "scary": "Horror",
    "Mythology": "Mythology",
    "Religious": "Mythology",
    "Cryptids": "Mythology",
    "Cthulhu": "Mythology",
    "Pirates": "Ocean",
    "Sealife": "Ocean",
    "Post-Apocalyptic": "Post-Apocalyptic",
    "4X": "4X",
    "Bluffing": "Bluffing",
    "Campaign": "Campaign",
    "Trading Game": "Trading",
    "trading": "Trading",
    "Medical": "Science",
    "doctors": "Science",
    "Scientist": "Science",
    "Biology": "Science",
    "science": "Science",
    "Crime": "Crime",
    "burglary": "Crime",
    "Heist": "Crime",
    "Detective": "Murder / Mystery",
    "Cooperative": "Cooperative",
    "Hidden Movement": "Hidden Movement",
    "Deckbuilding": "Deckbuilding",
    "Roll-and-Write": "Roll-and-Write",
    "roll and write": "Roll-and-Write",
    "Construction": "Construction",
    "collectible": "Collectible",
    "grid": "Grid",
    "Hex": "Hexagonal",
    "Polyominoes": "Polyominoes",
    "Timer": "Timer",
    "Meeples": "Meeples",
    "Standees": "Meeples",
    "Miniature": "Miniatures",
    "3d": "3D",
    "3 dimensional": "3D",
    "3-dimensional": "3D",
    "dice": "Dice",
    "Drop Tower": "Dice",
    "War games": "War Game",
    "war game": "War Game",
    "war-game": "War Game",
    "war ": "War Game",
    "war-": "War Game",
    "warfare": "War Game",
    "drawing": "Drawing",
    "Crayons": "Drawing",
    "Dry Erase Markers": "Drawing",
    "Digital Hybrid": "Digital Hybrid",
    "Trivia": "Trivia",
    "Quiz": "Trivia",
}

PRE_REMOVE_CONTAINS = ["Hall of Fame"]


def normalize_families(df_games: pd.DataFrame) -> set[str]:
    """Filter and canonicalize family names in-place, returning the unique set."""
    print("\nCaching and converting unique families...")

    df_games["families"] = df_games["families"].apply(
        lambda fams: [
            family
            for family in _ensure_list(fams)
            if not any(substring.lower() in family.lower() for substring in PRE_REMOVE_CONTAINS)
        ] if fams is not None else fams
    )
    df_games["families"] = df_games["families"].apply(
        lambda fams: list({
            WANTED_FAMILIES[key]
            for family in _ensure_list(fams)
            for key in WANTED_FAMILIES
            if key.lower() in family.lower()
        }) if fams is not None else fams
    )

    unique_families: set[str] = set()
    for families in df_games["families"].dropna():
        unique_families.update(_ensure_list(families))

    return unique_families


def load_or_create_property_mappings(
    unique_mechanics: set[str],
    unique_categories: set[str],
    unique_types: set[str],
    unique_families: set[str],
    unique_subdomains: set[str],
    mapping_file: str = "data/property_metadata/property_mappings.csv",
) -> pd.DataFrame:
    """Load or extend the property mapping table and return it indexed by property."""
    if os.path.exists(mapping_file):
        property_mappings = pd.read_csv(mapping_file)
        property_mappings["name"] = property_mappings["name"].apply(lambda x: _ensure_list(x) if pd.notna(x) else [])
    else:
        property_mappings = pd.DataFrame(columns=["property", "name"])

    existing_properties = set(property_mappings["property"])
    all_properties = set()
    for prop_set in [unique_mechanics, unique_categories, unique_types, unique_families, unique_subdomains]:
        all_properties.update(prop_set)

    missing_properties = all_properties - existing_properties
    if missing_properties:
        print(f"\nAdding {len(missing_properties)} missing properties to mapping...")
        new_rows = pd.DataFrame({"property": list(missing_properties), "name": [None] * len(missing_properties)})
        property_mappings = pd.concat([property_mappings, new_rows], ignore_index=True)
        property_mappings.to_csv(mapping_file, index=False)

    return property_mappings.set_index("property")


def collect_and_translate_properties(df_games: pd.DataFrame, property_mappings: pd.DataFrame) -> None:
    """Build the unified properties column in-place using the mapping table."""
    def translate_property(prop: str) -> list[str]:
        if prop in property_mappings.index:
            name = property_mappings.loc[prop, "name"]
            if isinstance(name, str) and len(name) > 0:
                return [name]
            if isinstance(name, list) and len(name) > 0:
                return name
        return [prop]

    df_games["properties"] = df_games.apply(
        lambda row: list(
            set(
                name
                for prop in (
                    _ensure_list(row["mechanics"])
                    + _ensure_list(row["categories"])
                    + _ensure_list(row["types"])
                    + _ensure_list(row["families"])
                )
                if pd.notna(prop)
                for name in translate_property(prop)
            )
        ),
        axis=1,
    )


def load_or_create_property_categorizations(
    df_games: pd.DataFrame,
    categorization_file: str = "data/property_metadata/property_categorizations.csv",
) -> pd.DataFrame:
    """Load or extend the categorization table and add p_* columns in-place."""
    if os.path.exists(categorization_file):
        property_categorizations = pd.read_csv(categorization_file)
    else:
        property_categorizations = pd.DataFrame(columns=["property", "category"])

    existing_properties = set(property_categorizations["property"])
    all_properties = set()
    for props in df_games["properties"].dropna():
        all_properties.update(props)

    missing_properties = all_properties - existing_properties
    if missing_properties:
        print(f"\nAdding {len(missing_properties)} missing properties to categorization...")
        new_rows = pd.DataFrame({"property": list(missing_properties), "category": [None] * len(missing_properties)})
        property_categorizations = pd.concat([property_categorizations, new_rows], ignore_index=True)
        property_categorizations.to_csv(categorization_file, index=False)

    property_categorizations = property_categorizations.set_index("property")

    def _categorize_properties(props, category):
        if props is None or props is pd.NA:
            return []
        if isinstance(props, float) and pd.isna(props):
            return []
        if not isinstance(props, (list, tuple, set, pd.Index)):
            return []
        return [
            prop
            for prop in props
            if prop in property_categorizations.index and property_categorizations.loc[prop, "category"] == category
        ]

    df_games["p_mechanics"] = df_games["properties"].apply(lambda props: _categorize_properties(props, "Mechanic"))
    df_games["p_types"] = df_games["properties"].apply(lambda props: _categorize_properties(props, "Type"))
    df_games["p_components"] = df_games["properties"].apply(lambda props: _categorize_properties(props, "Component"))
    df_games["p_themes"] = df_games["properties"].apply(lambda props: _categorize_properties(props, "Theme"))
    df_games["p_tags"] = df_games["properties"].apply(lambda props: _categorize_properties(props, "Tag"))

    return property_categorizations