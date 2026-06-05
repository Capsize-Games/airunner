"""Constants for premise scoring and evidence selection."""

PREMISE_PLOT_MARKERS = (
    "body",
    "corpse",
    "detective",
    "investigat",
    "killed",
    "murder",
    "murderer",
    "mystery",
)

PREMISE_ATMOSPHERE_MARKERS = ("dead", "death")

PREMISE_CONTEXT_MARKERS = (
    "cemetery",
    "graveyard",
    "halloween",
    "hollywood",
    "studio",
)

PREMISE_GROUNDED_MYSTERY_MARKERS = (
    "accident",
    "apparently",
    "ally",
    "corruption",
    "disguise",
    "effects",
    "fake",
    "guest",
    "hoax",
    "hotel",
    "illusion",
    "illusions",
    "investigation",
    "investigat",
    "island",
    "killer",
    "makeup",
    "murder",
    "murderer",
    "mystery",
    "noir",
    "photograph",
    "photo",
    "snapshot",
    "return",
    "resort",
    "roller skates",
    "remember",
    "scheme",
    "schemes",
    "special effects",
    "supposedly",
    "trick",
    "wall",
)

PREMISE_SCENE_MARKERS = (
    "beach",
    "dining room",
    "guest",
    "guests",
    "hotel",
    "island",
    "pool",
    "resort",
    "room",
    "shore",
    "staying",
    "terrace",
    "verandah",
)

PREMISE_BACKSTORY_MARKERS = (
    "another country",
    "doctor's story",
    "had once",
    "old recollections",
    "once",
    "overseas",
    "recollection",
    "recollections",
    "reminiscence",
    "reminiscences",
    "story about",
    "told him",
    "told me",
    "told her",
    "used to",
    "years ago",
)

PREMISE_DIALOGUE_MARKERS = (
    " asked ",
    " cried ",
    " said ",
    " says ",
    " shouted ",
    " yelled ",
    " you ",
    " your ",
)

PREMISE_DIALOGUE_SCENE_MARKERS = (
    "career",
    "drink",
    "drunk",
    "lifestyle",
)

PREMISE_ROLE_LIMITS = {"Current setting": 1}

PREMISE_PREFIX_MARKERS = frozenset({"investigat"})
