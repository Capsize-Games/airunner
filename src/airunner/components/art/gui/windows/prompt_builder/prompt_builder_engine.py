"""Deterministic madlibs-style prompt builder for image generation.

This module recreates the classic AI Runner "Prompt Builder" concept (a
template with named slots filled from curated word lists) but rebuilds the
output around the prompt structures recommended for the two generators
this app supports:

* Z-Image Turbo — a 6-part single positive prompt (no negative prompt, no
  CFG, so every constraint must be phrased positively).
* Stable Diffusion XL (SDXL) — a layered positive prompt plus a negative
  "bug list" prompt.

No LLM is involved anywhere in this pipeline. Every value is picked from a
local, deterministic vocabulary, so generation is fast, offline, and fully
reproducible for a given seed.

Randomization notes
-------------------
Repetitive output was a real complaint, and it had three root causes that
this implementation addresses directly:

1. The seed never advanced — every build reused the same seed, producing
   byte-identical prompts. ``PromptBuilderState.seed is None`` now means
   "draw a fresh seed every build", and the UI advances the seed after each
   generate.
2. Every slot drew from an independent ``random.Random(seed)`` seeded with
   the *same* seed, so all slots returned the value at the same index in
   their lists (index clumping/correlation). This build uses a single shared
   ``random.Random`` instance for the whole build so slot choices are
   uncorrelated.
3. Vocabularies were tiny (10-15 entries), so repeats were guaranteed. The
   lists below are several times larger.

Seed semantics
--------------
* ``state.seed is None``  -> a fresh seed is drawn for every build, so
  repeated Generate actions always differ (this is what the UI uses when
  "Random seed" is enabled).
* ``state.seed == int``   -> fully reproducible: the same seed always
  produces the same prompt. The UI uses this for the live preview (a stable
  preview seed) and for pinned-seed mode.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional

# ---------------------------------------------------------------------------
# Vocabularies (shared between generators where possible)
# ---------------------------------------------------------------------------

SUBJECT_ATTRIBUTES = {
    "age": [
        "young",
        "middle-aged",
        "elderly",
        "in their twenties",
        "in their thirties",
        "in their forties",
        "in their fifties",
        "in their sixties",
        "in their seventies",
        "a grizzled veteran of many years",
        "a fresh-faced newcomer",
        "a wise old soul",
        "a rugged outdoorsman",
        "an elegant, well-kept older person",
    ],
    "skin": [
        "smooth porcelain skin",
        "sun-worn, deeply wrinkled skin",
        "freckled skin",
        "warm olive skin",
        "weathered leathery skin",
        "glowing dewy skin",
        "pale alabaster skin",
        "rich mahogany skin",
        "bronzed sun-kissed skin",
        "parchment-dry, creased skin",
        "dusted with faint age spots",
        "with a faint map of fine lines",
    ],
    "hair": [
        "short black hair",
        "long flowing red hair",
        "curly brown hair",
        "silver-grey hair",
        "braided dark hair",
        "buzzed platinum hair",
        "wavy auburn hair",
        "wild untamed curls",
        "a slicked-back jet-black pompadour",
        "thin wisps of white hair",
        "a shaggy salt-and-pepper mane",
        "tightly coiled natural hair",
        "a neat short crop with a side part",
        "hair streaked with copper highlights",
    ],
    "wardrobe": [
        "a heavy yellow rain slicker",
        "a tailored charcoal suit",
        "a knitted wool sweater",
        "a flowing linen dress",
        "a weathered leather jacket",
        "a crisp white chef's uniform",
        "an embroidered silk robe",
        "a patched denim work coat",
        "a waxed canvas barn jacket",
        "a formal black tailcoat",
        "a hand-knitted cardigan",
        "a military surplus parka",
        "a vintage trench coat",
        "a colorful woven poncho",
        "a simple linen smock",
    ],
    "expression": [
        "a calm, knowing smile",
        "an intense, focused gaze",
        "a warm, genuine laugh",
        "a pensive, distant stare",
        "a confident, poised posture",
        "a gentle, compassionate look",
        "a wry, mischievous grin",
        "a stoic, unreadable expression",
        "a look of quiet determination",
        "a soft, contented sigh",
        "a knowing, half-lidded glance",
        "an earnest, open expression",
    ],
    "accessory": [
        "wearing round tortoiseshell glasses",
        "holding a steaming cup of coffee",
        "carrying a worn leather satchel",
        "wearing a silver pocket watch",
        "holding a single red rose",
        "wearing a wide-brimmed sun hat",
        "wearing thin wire-rimmed spectacles",
        "with a brass sextant at their side",
        "carrying a battered violin case",
        "wearing a woven friendship bracelet",
        "with an old film camera slung over one shoulder",
        "holding a carved wooden walking stick",
        "wearing a ring with a dark green stone",
    ],
}

SUBJECT_NOUNS = [
    "a 60-year-old fisherman",
    "a young street musician",
    "an elderly gardener",
    "a professional chef",
    "a deep-sea diver",
    "a mountain climber",
    "a ballet dancer",
    "a vintage car mechanic",
    "a lighthouse keeper",
    "a beekeeper",
    "a woodcarver",
    "a bookbinder",
    "a potter",
    "a sailor",
    "a blacksmith",
    "a watchmaker",
    "a glassblower",
    "a taxidermist",
    "a violinist",
    "a cartographer",
    "an astronomer",
    "a botanist",
    "an entomologist",
    "a paleontologist",
    "a detective",
    "a lighthouse keeper's daughter",
    "a wandering poet",
    "a traveling photographer",
    "a retired circus performer",
    "a ferry boat captain",
    "a coal miner",
    "a sheep herder",
    "an apprentice stonemason",
    "a bell tower keeper",
    "a mushroom forager",
    "a falconer",
    "a lighthouse attendant",
    "a steam train conductor",
    "a telegraph operator",
    "a deep-sea coral researcher",
]

SUBJECT_ACTIONS = [
    "pulling a thick hemp rope",
    "carefully painting a canvas",
    "tuning an old acoustic guitar",
    "pruning a rose bush",
    "reading a weathered novel",
    "sharpening a carving knife",
    "adjusting brass instruments",
    "sewing a patch onto a jacket",
    "writing in a leather journal",
    "winding an antique clock",
    "arranging fresh flowers",
    "mending a fishing net",
    "grinding coffee beans",
    "polishing a brass lantern",
    "tying intricate knots in a rope",
    "stoking a small iron stove",
    "folding origami cranes from old paper",
    "counting coins into a brass scale",
    "waxing a worn leather boot",
    "filing down a metal gear",
    "rolling a cigarette with tobacco leaves",
    "playing a hand-cranked music box",
    "sketching a passing bird",
    "repairing a torn sail",
    "sorting dried herbs into jars",
    "hand-stamping leather with a pattern",
    "carving a whistle from a branch",
    "braiding a leather cord",
    "mixing pigments on a stone slab",
    "trimming the wick of an oil lamp",
    "checking a brass barometer",
    "feeding a small fire with driftwood",
    "inlaying mother-of-pearl into wood",
    "restoring a faded photograph",
]

SUBJECT_OBJECTS = [
    "a thick hemp rope",
    "a hand-painted ceramic vase",
    "a vintage brass camera",
    "a bundle of dried lavender",
    "an antique pocket watch",
    "a stack of yellowed letters",
    "a hand-carved wooden bowl",
    "a brass compass",
    "a leather-bound journal",
    "a glass terrarium",
    "a woven basket",
    "a silver tea set",
    "a worn leather violin case",
    "a brass telescope on a tripod",
    "a bundle of dried tobacco leaves",
    "a delicate music box",
    "a battered copper kettle",
    "a hand-forged iron hook",
    "a glass jar of honey",
    "a rusted ship's bell",
    "a set of ivory dominoes",
    "a carved totem of a raven",
    "a brass oil lamp",
    "a wooden toy sailboat",
    "a rolled parchment map",
    "a pair of well-worn leather gloves",
    "a string of dried chilies",
    "a glass-stoppered apothecary bottle",
]

SCENE_LOCATIONS = [
    "the deck of a weathered wooden boat",
    "a sunlit cobblestone market square",
    "a misty pine forest at dawn",
    "a cozy candlelit workshop",
    "a windswept coastal cliff",
    "an old library with towering shelves",
    "a rain-soaked city street at night",
    "a lavender field in late summer",
    "a snow-covered alpine village",
    "a quiet greenhouse full of orchids",
    "a desert canyon at golden hour",
    "a bustling farmers market",
    "a derelict lighthouse interior",
    "a salt-crusted fishing harbor",
    "a fog-shrouded mountain pass",
    "a sun-dappled orchard",
    "an overgrown castle courtyard",
    "a cramped attic studio",
    "a mossy stone bridge over a creek",
    "a windswept moor with stone circles",
    "a crumbling desert outpost",
    "a steamy railway station",
    "a dark, dusty archive vault",
    "a rooftop garden above the city",
    "a tidal pool at low tide",
    "a cherry blossom avenue",
    "a volcanic black-sand beach",
    "a hidden valley with a waterfall",
    "a labyrinthine old town alley",
    "a botanical garden's iron-framed glasshouse",
]

SCENE_TIMES = [
    "during a turbulent storm at dawn",
    "in the soft light of late afternoon",
    "at golden hour just before sunset",
    "under a full moon at midnight",
    "in the quiet hours of early morning",
    "as the first snow begins to fall",
    "during a light spring drizzle",
    "in the hazy heat of midday",
    "just after a summer rain",
    "in the fading light of dusk",
    "during a blood-red sunrise",
    "in the blue hour before dawn",
    "under a canopy of stars",
    "during a sudden squall",
    "in the crisp air of an autumn morning",
    "as thunder rolls in from the distance",
]

SCENE_WEATHER = [
    "with crashing dark grey waves in the background",
    "with dramatic storm clouds gathering overhead",
    "with soft morning fog rolling through",
    "with warm sunlight streaming through the windows",
    "with snow dusting every surface",
    "with a gentle breeze stirring the leaves",
    "with a clear starry sky above",
    "with golden light filtering through the trees",
    "with mist hanging low over the water",
    "with a rainbow arching across the sky",
    "with a fine mist beading on every surface",
    "with low clouds brushing the hilltops",
    "with heat shimmer rising from the ground",
    "with ice crystals glittering in the air",
    "with heavy rain drumming on every surface",
    "with dust motes drifting through the light",
    "with the first rays of sun breaking through",
    "with a bank of fog rolling in from the sea",
    "with leaves caught in a playful swirl of wind",
    "with distant lightning flickering on the horizon",
]

SHOT_TYPES = [
    "Close-up shot",
    "Medium shot",
    "Wide shot",
    "Extreme close-up",
    "Full-body shot",
    "Over-the-shoulder shot",
    "Top-down shot",
    "Low-angle shot",
    "Three-quarter view",
    "Straight-on view",
    "Dutch angle",
    "Bird's-eye view",
    "POV shot",
    "Two-shot",
    "Profile shot",
]

LENSES = [
    "a 35mm lens",
    "a 50mm lens",
    "an 85mm lens",
    "a 24mm wide-angle lens",
    "a 135mm telephoto lens",
    "a macro lens",
    "a 28mm lens",
    "a 70-200mm zoom lens",
    "a 16mm ultra-wide lens",
    "a 100mm lens",
    "a tilt-shift lens",
    "a 40mm pancake lens",
]

COMPOSITIONS = [
    "perfectly centered composition",
    "rule-of-thirds composition",
    "asymmetric composition with negative space on the left",
    "centered product composition with wide margins",
    "leading lines drawing the eye to the subject",
    "framed composition with natural elements in the foreground",
    "symmetrical composition",
    "dynamic diagonal composition",
    "S-curve composition winding through the frame",
    "repetitive pattern composition",
    "minimalist composition with vast negative space",
    "layered composition with foreground, midground and background",
    "triangular composition anchoring the subject",
    "radial composition focusing on a central point",
    "golden-spiral composition",
    "stacked horizontal bands of interest",
]

LIGHTING = [
    "cinematic rim lighting with deep shadows",
    "soft key light from the left with gentle rim light",
    "volumetric lighting through atmospheric haze",
    "dramatic chiaroscuro lighting",
    "warm golden-hour backlighting",
    "cool moonlight with deep blue shadows",
    "soft diffused daylight with minimal contrast",
    "hard directional sunlight with crisp shadows",
    "neon accent lighting reflecting off wet surfaces",
    "candlelight with warm flickering shadows",
    "single-source top lighting casting long shadows",
    "lightning-illuminated scene with stark highlights",
    "practical tungsten lamps with amber glow",
    "cool blue window light from the north",
    "firelight with deep orange flicker",
    "overcast wrap-around lighting with soft gradients",
    "greenhouse light dappled through glass panes",
    "backlit silhouette with a glowing halo",
    "dual-source cross lighting",
    "moody low-key lighting with pools of shadow",
]

STYLES = {
    "Photorealistic": [
        "hyper-detailed photorealistic photography style",
        "award-winning National Geographic photography style",
        "premium editorial commercial photography",
        "documentary photography style with natural color grading",
        "Hasselblad X1D medium-format photography",
        "Leica M10 rangefinder photography",
        "large-format film photography with incredible depth",
        "street photography with authentic candid framing",
        "vintage Kodachrome slide film look",
        "black-and-white fine-art photography",
        "architectural digest photography style",
        "behind-the-scenes documentary style",
    ],
    "Cinematic": [
        "1980s sci-fi film still aesthetic",
        "cinematic film still with anamorphic lens flare",
        "vintage 35mm film grain aesthetic",
        "noir film aesthetic with high contrast",
        "blockbuster concept art with cinematic framing",
        "Wes Anderson symmetrical pastel aesthetic",
        "grimy 1970s crime-thriller palette",
        "epic fantasy film still with sweeping scale",
        "muted indie film color grade",
        "expressionist German cinema lighting",
    ],
    "Artistic": [
        "hyper-detailed oil painting",
        "watercolor illustration with soft edges",
        "charcoal sketch with expressive strokes",
        "art nouveau illustration with flowing lines",
        "gouache painting with rich flat colors",
        "impressionist painting with visible brushstrokes",
        "renaissance oil portrait technique",
        "ukiyo-e woodblock print style",
        "colored pencil illustration",
        "gold-leaf illuminated manuscript style",
        "surrealist dream-painting style",
        "folk-art mural style",
    ],
    "Digital": [
        "hyperrealistic concept art style",
        "3D render with physically based materials",
        "isometric game asset render",
        "digital matte painting",
        "pixel art with crisp edges",
        "low-poly 3D stylized render",
        "octane render with subsurface scattering",
        "graphic novel cel-shaded style",
        "vector flat illustration",
        "8-bit retro game sprite style",
        "holographic sci-fi UI concept art",
        "hand-painted stylized game art",
    ],
}

COLOR_PALETTES = [
    "warm beige color palette",
    "muted earth tones",
    "cool blue and teal palette",
    "vibrant complementary colors",
    "monochromatic grey scale",
    "soft pastel palette",
    "rich autumn tones",
    "icy blue and white palette",
    "deep emerald and gold palette",
    "faded vintage color palette",
    "sepia-toned vintage palette",
    "high-contrast black and white",
    "desaturated documentary tones",
    "neon magenta and cyan palette",
    "sun-bleached desert tones",
    "deep forest greens and moss",
    "crimson and charcoal palette",
    "buttery cream and slate palette",
    "iridescent oil-slick colors",
    "cobalt and rust palette",
]

QUALITY_TERMS = [
    "highly detailed skin texture, sharp focus, accurate human anatomy",
    "crisp details, sharp focus, completely uncluttered background",
    "extremely detailed textures, sharp focus, clean edges",
    "fine detail rendering, precise focus, natural proportions",
    "intricate surface textures, tack-sharp focus, realistic proportions",
    "razor-sharp focus, meticulous micro-detail, balanced composition",
    "photorealistic material rendering, precise color accuracy",
    "exceptional clarity, no motion blur, crisp line work",
]

# SDXL-specific negative-prompt vocabulary ("bug list")
SDXL_NEGATIVE_TERMS = [
    "text",
    "watermark",
    "extra fingers",
    "fused fingers",
    "deformed hands",
    "blurry face",
    "duplicate",
    "mutation",
    "bad anatomy",
    "worst quality",
    "low quality",
    "jpeg artifacts",
]

SDXL_STYLE_NEGATIVES = {
    "Photorealistic": "CGI, plastic skin, 3d render, anime, overexposed",
    "Cinematic": "flat lighting, lens distortion, frame artifacts, oversaturated",
    "Artistic": "photorealistic, 3d render, messy lines, low contrast",
    "Digital": "photorealistic, blurry, low contrast, noisy, sketchy",
}

# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass
class PromptBuilderResult:
    """The outcome of one build operation."""

    prompt: str = ""
    negative_prompt: str = ""
    word_count: int = 0


@dataclass
class PromptBuilderState:
    """Mutable state captured from the builder UI."""

    subject: str = ""
    attributes: Dict[str, str] = field(default_factory=dict)
    scene: str = ""
    time_of_day: str = ""
    weather: str = ""
    shot_type: str = ""
    lens: str = ""
    composition: str = ""
    lighting: str = ""
    style_group: str = "Photorealistic"
    style_detail: str = ""
    color_palette: str = ""
    quality: str = ""
    # Free-form fields the user can type directly.
    custom_subject: str = ""
    custom_scene: str = ""
    custom_style: str = ""
    custom_negative: str = ""
    prefix: str = ""
    suffix: str = ""
    # ``True``: slots still set to "Random" draw a fresh random value on every
    # build. ``False``: "Random" resolves to the literal word "Random".
    randomize: bool = True
    # ``None`` means "draw a fresh seed for this build" (recommended for the
    # UI flow, which advances the seed after each generate anyway).
    seed: Optional[int] = None
    target_generator: str = "zimage"  # "zimage" | "stablediffusion"


class PromptBuilderEngine:
    """Builds Z-Image and SDXL prompts from a :class:`PromptBuilderState`.

    A single shared :class:`random.Random` instance is used for the whole
    build so every "Random" slot draws from the same uncorrelated stream.
    """

    def __init__(self, target_generator: str = "zimage"):
        self.target_generator = target_generator
        self._rng: random.Random = random.Random()

    # -- public API ----------------------------------------------------------

    def build(self, state: PromptBuilderState) -> PromptBuilderResult:
        """Build the positive (and where relevant negative) prompts."""
        if state.seed is None:
            # Fresh seed per build so repeated Generates differ.
            self._rng = random.Random()
        else:
            self._rng = random.Random(state.seed)
        if state.target_generator == "stablediffusion":
            prompt, negative = self._build_sdxl(state)
        else:
            prompt, negative = self._build_zimage(state)
        prompt = self._apply_prefix_suffix(prompt, state)
        result = PromptBuilderResult(
            prompt=prompt,
            negative_prompt=negative,
            word_count=len(prompt.split()),
        )
        return result

    # -- internal slot resolution --------------------------------------------

    def _pick(
        self,
        options: List[str],
        state: PromptBuilderState,
        key: str,
    ) -> str:
        """Resolve one slot to a concrete value.

        An explicit (non-"Random") value is honored verbatim. A "Random"
        value draws from ``options`` using the shared per-build RNG so
        different slots are uncorrelated.
        """
        existing = (getattr(state, key, "") or "").strip()
        if existing and not (state.randomize and existing == "Random"):
            return existing
        if not options:
            return ""
        if not state.randomize:
            # Randomization disabled: emit the literal word.
            return existing or "Random"
        return self._rng.choice(options)

    def _pick_attribute(
        self,
        name: str,
        options: List[str],
        state: PromptBuilderState,
    ) -> str:
        """Resolve one subject-attribute slot from the shared RNG."""
        value = (state.attributes.get(name, "") or "").strip()
        if value and not (state.randomize and value == "Random"):
            return value
        if not options:
            return ""
        if not state.randomize:
            return value or "Random"
        return self._rng.choice(options)

    # -- Z-Image (6-part single prompt) --------------------------------------

    def _build_zimage(self, state: PromptBuilderState) -> tuple[str, str]:
        parts: List[str] = []

        # 1. Subject (anchor)
        parts.append(self._subject(state))

        # 2. Scene & environment
        scene = self._scene(state)
        if scene:
            parts.append(scene)

        # 3. Composition & framing
        composition = self._composition(state)
        if composition:
            parts.append(composition)

        # 4. Lighting
        lighting = self._pick(LIGHTING, state, "lighting")
        if lighting:
            parts.append(lighting)

        # 5. Style & medium
        style = self._style(state)
        if style:
            parts.append(style)

        # 6. Constraints & polish (positively framed)
        polish = self._pick(QUALITY_TERMS, state, "quality")
        if polish:
            parts.append(polish)

        # Fold custom style into the style section. Custom subject is already
        # emitted as part 1 by ``_subject``.
        if state.custom_style:
            parts.append(state.custom_style.strip().rstrip(","))

        prompt = ", ".join(part for part in parts if part)
        # Z-Image Turbo ignores negative prompts entirely.
        return prompt, ""

    # -- SDXL (layered prompt + negative bug list) ---------------------------

    def _build_sdxl(self, state: PromptBuilderState) -> tuple[str, str]:
        parts: List[str] = []

        # 1. Layout & core scene
        parts.append(self._subject(state))

        # 2. Environment
        scene = self._scene(state)
        if scene:
            parts.append(scene)

        # 3. Composition
        composition = self._composition(state)
        if composition:
            parts.append(composition)

        # 4. Texture & style (includes lighting cues)
        lighting = self._pick(LIGHTING, state, "lighting")
        if lighting:
            parts.append(lighting)
        style = self._style(state)
        if style:
            parts.append(style)
        if state.custom_style:
            parts.append(state.custom_style.strip().rstrip(","))

        # 5. Negative prompt (bug list)
        negatives: List[str] = []
        if state.style_group in SDXL_STYLE_NEGATIVES:
            negatives.append(SDXL_STYLE_NEGATIVES[state.style_group])
        negatives.extend(SDXL_NEGATIVE_TERMS)
        if state.custom_negative:
            negatives.append(state.custom_negative.strip().rstrip(","))
        # De-duplicate while preserving order.
        negative = ", ".join(dict.fromkeys(negatives))

        prompt = ", ".join(part for part in parts if part)
        return prompt, negative

    # -- shared fragment builders --------------------------------------------

    def _subject(self, state: PromptBuilderState) -> str:
        if state.custom_subject:
            # Free-form subject text is used verbatim; don't stack default
            # attribute phrases on top of something the user already wrote.
            return state.custom_subject.strip().rstrip(",")
        base = self._pick(SUBJECT_NOUNS, state, "subject")
        fragments: List[str] = [base]
        for key, options in SUBJECT_ATTRIBUTES.items():
            value = self._pick_attribute(key, options, state)
            if value and value != "Random":
                fragments.append(value)
        action = self._pick(SUBJECT_ACTIONS, state, "action")
        obj = self._pick(SUBJECT_OBJECTS, state, "object")
        if action:
            fragments.append(action)
        if obj and obj not in action:
            fragments.append(obj)
        return ", ".join(fragments)

    def _scene(self, state: PromptBuilderState) -> str:
        if state.custom_scene:
            return state.custom_scene.strip().rstrip(",")
        scene = self._pick(SCENE_LOCATIONS, state, "scene")
        time_of_day = self._pick(SCENE_TIMES, state, "time_of_day")
        weather = self._pick(SCENE_WEATHER, state, "weather")
        fragments = [scene]
        if time_of_day:
            fragments.append(time_of_day)
        if weather:
            fragments.append(weather)
        return ", ".join(fragments)

    def _composition(self, state: PromptBuilderState) -> str:
        shot = self._pick(SHOT_TYPES, state, "shot_type")
        lens = self._pick(LENSES, state, "lens")
        composition = self._pick(COMPOSITIONS, state, "composition")
        fragments = []
        if shot:
            fragments.append(shot)
        if lens:
            # The lens vocabulary embeds the correct article ("a 35mm lens",
            # "an 85mm lens") so the phrase reads naturally.
            fragments.append(f"shot on {lens}")
        if composition:
            fragments.append(composition)
        return ", ".join(fragments)

    def _style(self, state: PromptBuilderState) -> str:
        group = state.style_group or "Photorealistic"
        options = STYLES.get(group, STYLES["Photorealistic"])
        detail = state.style_detail or self._pick(
            options, state, "style_detail"
        )
        palette = self._pick(COLOR_PALETTES, state, "color_palette")
        fragments = [detail] if detail else []
        if palette:
            fragments.append(palette)
        return ", ".join(fragments)

    def _apply_prefix_suffix(
        self, prompt: str, state: PromptBuilderState
    ) -> str:
        if state.prefix:
            prompt = f"{state.prefix.strip()}, {prompt}"
        if state.suffix:
            prompt = f"{prompt}, {state.suffix.strip()}"
        return prompt
