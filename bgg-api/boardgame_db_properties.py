from __future__ import annotations

import os

import pandas as pd

from recommender_v2 import _ensure_list


WANTED_FAMILIES = {
    "3 dimensional": "3D",
    "3-dimensional": "3D",
    "3d": "3D",
    "4X": "4X",
    "adventure": "Adventure",
    "airline": "Vehicles",
    "ancient": "Location",
    "animal": "Animals",
    "Aquaria": "Animals",
    "automotive": "Vehicles",
    "Helicopters": "Vehicles",
    "Hot Air Balloons": "Vehicles",
    "Biology": "Science",
    "Evolution": "Science",
    "Genealogy": "Science",
    "Ecology": "Science",
    "Gardening": "Gardening",
    "Fishing": "Fishing",
    "Flowers": "Flowers",
    "Bluffing": "Bluffing",
    "bogs": "Nature",
    "Warhammer": "Warhammer",
    "burglary": "Crime",
    "cafe": "Food",
    "Café": "Food",
    "Campaign": "Campaign",
    "card game": "Card Game",
    "cars": "Vehicles",
    "Airships": "Vehicles",
    "Anime": "Anime",
    "Theme Parks": "Theme Park",
    "cities": "Location",
    "City": "Location",
    "collectible": "Collectible",
    "Construction": "Construction",
    "Builder": "Construction",
    "Architect": "Construction",
    "One versus Many": "One versus Many",
    "Continent": "Location",
    "Cooperative": "Cooperative",
    "Country": "Location",
    "Crayons": "Drawing",
    "Creatures": "Creatures",
    "Crime": "Crime",
    "crossword": "Word Game",
    "Crowdfunding": "Crowdfunded",
    "Cryptids": "Mythology",
    "Cthulhu": "Mythology",
    "Cyberpunk": "Science Fiction",
    "Solarpunk": "Science Fiction",
    "Future": "Science Fiction",
    "UFOs": "Science Fiction",
    "Superheroes": "Superheroes",
    "Survival": "Survival",
    "Deckbuilding": "Deckbuilding",
    "Detective": "Murder / Mystery",
    "dice": "Dice",
    "Digital Hybrid": "Digital Hybrid",
    "Digital Implementation": "Digital Implementation",
    "disney": "Fairy Tales",
    "doctor": "Medical",
    "Medic": "Medical",
    "Nurse": "Medical",
    "Medical": "Medical",
    "drawing": "Drawing",
    "Drop Tower": "Dice",
    "Dry Erase Markers": "Drawing",
    "dungeon Crawler": "Dungeon Crawler",
    "Engineer": "Engineering",
    "escape Room": "Escape Room",
    "fighting": "Fighting",
    "Folk Tales & Fairy Tales": "Fairy Tales",
    "Food": "Food",
    "Forest": "Nature",
    "grid": "Grid",
    "Heist": "Crime",
    "Hex": "Hexagonal",
    "Hidden Movement": "Hidden Movement",
    "Medieval": "History",
    "history": "History",
    "Camelot": "History",
    "Knights": "History",
    "Love": "Love",
    "Horror": "Horror",
    "Islands": "Location",
    "magic": "Magic",
    "Meeples": "Meeples",
    "Miniature": "Miniatures",
    "Mountains": "Location",
    "Mythology": "Mythology",
    "Nature": "Nature",
    "ocean": "Ocean",
    "Pirates": "Ocean",
    "Playing Card": "Card Game",
    "Polyominoes": "Polyominoes",
    "Post-Apocalyptic": "Post-Apocalyptic",
    "Quiz": "Trivia",
    "Region": "Location",
    "Religious": "Mythology",
    "Restaurant": "Food",
    "Rivers": "Location",
    "Robots": "Science Fiction",
    "Android": "Science Fiction",
    "Time Travel": "Science Fiction",
    "roll and write": "Roll-and-Write",
    "Roll-and-Write": "Roll-and-Write",
    "Safari Parks": "Safari Parks",
    "Extinct species"
    "scary": "Horror",
    "Sci-Fi": "Science Fiction",
    "science": "Science",
    "Scientist": "Science",
    "sea": "Ocean",
    "Sealife": "Ocean",
    "simulation": "Simulation",
    "Sorcery": "Magic",
    "Space": "Space",
    "Astronomy": "Space",
    "astronaut": "Space",
    "Interstellar": "Space",
    "Clowns": "Circus",
    "Circus": "Circus",
    "Colonial": "History",
    "Spells": "Magic",
    "Spooky": "Horror",
    "Nightmares": "Horror",
    "Sports": "Sports",
    "Standees": "Meeples",
    "States:": "Location",
    "Steampunk": "Science Fiction",
    "Computer": "Science Fiction",
    "Nuclear option": "Science Fiction",
    "Storytelling": "Fairy Tales",
    "Swamps": "Nature",
    "Tableau Building": "Tableau Building",
    "Timer": "Timer",
    "Trading Game": "Trading",
    "trading": "Trading",
    "Trains": "Vehicles",
    "Aviator": "Vehicles",
    "Motorcycles": "Vehicles",
    "Driving": "Vehicles",
    "Mining": "Mining",
    "trees": "Nature",
    "Trivia": "Trivia",
    "Tropical": "Nature",
    "Trucks": "Vehicles",
    "Two Player": "Two-Player",
    "two-player": "Two-Player",
    "Under the Sea": "Ocean",
    "vehicles": "Vehicles",
    "Vikings": "History",
    "war ": "War Game",
    "war game": "War Game",
    "War games": "War Game",
    "war-": "War Game",
    "war-game": "War Game",
    "warfare": "War Game",
    "Weather": "Nature",
    "Wetlands": "Nature",
    "wildlife": "Nature",
    "Witches": "Magic",
    "Wizards": "Magic",
    "Druids": "Magic",
    "Word Games": "Word Game",
    "words": "Word Game",
    "zoos": "Animals",
    "Safaris": "Animals",
    "Block Wargames": "War Game",
    "Tower Defense": "Tower Defense",
    "n in a row": "n in a Row",
    "4 in a Row": "n in a Row",
    "Deduction": "Deduction",
    "Book as Board": "Book as Board",
    "Control Boards": "Control Boards",
    "Gems": "Gems",
    "Magnets": "Magnets",
    "Map": "Map",
    "Marbles": "Marbles",
    "Multi-Use Cards": "Multi-Use Cards",
    "Player Screens": "Player Screens",
    "Historical": "Historical",
    "Finger Flicking": "Finger Flicking",
    "Flip-and-Write": "Flip-and-Write",
    "Give a Clue / Get a Clue": "Give a Clue / Get a Clue",
    "Judging Games": "Judging Games",
    "Music": "Music",
    "Wargames": "War Game",
    "Games with Solitaire Rules": "Solitaire",
    "Solitaire Only Games": "Solitaire",
    "Combinatorial": "Math",
}

PRE_REMOVE_CONTAINS = [
    "Hall of Fame",
    "Organizations:", 
    "Misc:", 
    "Admin:",
    "Authors:",
    "Books:",
    "Brands:",
    "Celebrities:",
    "Characters:",
    "Comic Books:",
    "Comic Strips:",
    "Comics:",
    "Containers:",
    "Contests:",
    "Decades:",
    "Fictional Events:",
    "Game:",
    "Holidays:",
    "Magazine:",
    "Movies:",
    "Promotional:",
    "Series:",
    "Series :",
    "TV Shows:",
    "Toys:",
    "Traditional Games:",
    "Versions & Editions:",
    "Video Game Theme:",
    "Webcomics:",
    "expansions",
]


def normalize_families(df_games: pd.DataFrame) -> set[str]:
    """Filter and canonicalize family names in-place, returning the unique set."""
    print("\nconverting unique families...")

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
    unique_components: set[str],
    unique_categories: set[str],
    unique_types: set[str],
    unique_families: set[str],
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
    for prop_set in [unique_mechanics, unique_components, unique_categories, unique_types, unique_families]:
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

    df_games["mechanics"] = df_games["properties"].apply(lambda props: _categorize_properties(props, "Mechanic"))
    df_games["types"] = df_games["properties"].apply(lambda props: _categorize_properties(props, "Type"))
    df_games["components"] = df_games["properties"].apply(lambda props: _categorize_properties(props, "Component"))
    df_games["themes"] = df_games["properties"].apply(lambda props: _categorize_properties(props, "Theme"))
    df_games["tags"] = df_games["properties"].apply(lambda props: _categorize_properties(props, "Tag"))

    return property_categorizations



if __name__ == "__main__":
    # Example usage
    # df_games = pd.read_csv("data/final/final_20260506.csv")

    # unique_families = normalize_families(df_games)

    df_games = pd.read_csv("data/final/final_20260506.csv")

    # print families not saved in the mapping
    unique_families_in_df = set()
    family_counts = {}
    for fams in df_games["families"].dropna():
        for family in _ensure_list(fams):
            unique_families_in_df.add(family)
            family_counts[family] = family_counts.get(family, 0) + 1
    
    if unique_families_in_df:
        print(f"\nFound {len(unique_families_in_df)} missing families in the mapping:")
        
        # sort unique_families_in_df by count descending
        unique_families_in_df = sorted(unique_families_in_df, key=lambda f: family_counts.get(f, 0), reverse=True)

        count = 0
        for family in unique_families_in_df:
            if not any(key.lower() in family.lower() for key in WANTED_FAMILIES) and not any(substring.lower() in family.lower() for substring in PRE_REMOVE_CONTAINS):
                # Use pre-computed counts
                print(f"{family}: {family_counts[family]}")
                count += 1
        print(f"\nTotal missing families: {count}")