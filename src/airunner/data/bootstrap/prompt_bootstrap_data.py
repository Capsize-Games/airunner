prompt_bootstrap_data = {
    "animal": {
        "negative_prompt": "(Unattractive fur/scales/feathers), (Deformed body), (Unappealing coloration)",
        "weights": {
            "animal": 1.0,
            "habitat": 1.0,
            "pattern": 1.0,
            "fur_type": 1.0,
            "behavior": 1.0,
            "weather": 1.0,
            "time": 1.0,
            "size": 1.0,
            "location": 1.0,
            "eye_color": 1.0,
            "emotion": 1.0
        },
        "builder": [
            {
                "text": "A "
            },
            {
                "text": "$size ",
                "cond": "size"
            },
            {
                "text": "$animal ",
                "cond": "animal",
                "else": "animal "
            },
            {
                "text": "in a $habitat ",
                "cond": "habitat"
            },
            {
                "text": "in $location ",
                "cond": "location"
            },
            {
                "text": "in $pattern ",
                "cond": "pattern"
            },
            {
                "text": "$fur_type fur ",
                "cond": "fur_type"
            },
            {
                "text": "$eye_color eyes, ",
                "cond": "eye_color"
            },
            {
                "text": "$behavior behavior, ",
                "cond": "behavior"
            },
            {
                "text": "captured in motion. "
            },
            {
                "cond": "animal,emotion",
                "next": [
                    {
                        "text": "The $animal looks ",
                        "cond": "animal",
                        "else": "The animal looks "
                    },
                    {
                        "text": "$emotion. "
                    }
                ]
            },
            {
                "not_cond": "animal",
                "cond": "emotion",
                "next": [
                    {
                        "text": "The animal looks ",
                        "cond": "animal",
                        "else": "The animal looks "
                    },
                    {
                        "text": "$emotion. "
                    }
                ]
            },
            {
                "text": "The $habitat is ",
                "cond": "habitat",
                "else": "The habitat is "
            },
            {
                "text": "$weather ",
                "cond": "weather"
            },
            {
                "text": "at $time ",
                "cond": "time"
            },
            {
                "text": "vibrant and lively, natural composition, perfect lighting, an amazing sight."
            }
        ],
        "variables": {
            "animal": [
                "dog", "cat", "bird", "fish", "rabbit", "hamster", "turtle", "snake", "lizard", "frog", "mouse",
                "bear", "elephant", "lion", "tiger", "giraffe", "zebra", "monkey", "koala", "panda", "kangaroo",
                "hippopotamus", "rhinoceros", "gorilla", "crocodile", "penguin", "dolphin", "whale", "shark",
                "octopus", "jellyfish", "seahorse", "horse", "cow", "sheep", "goat", "pig", "chicken", "duck",
                "goose", "deer", "fox", "wolf", "squirrel", "beaver", "otter", "bat", "hedgehog", "snail",
                "butterfly", "bee", "ant", "spider"
            ],
            "habitat": [
                "forest", "desert", "ocean", "jungle", "mountain", "grassland", "arctic", "cave", "reef",
                "swamp", "urban", "farm", "tundra", "savannah", "rainforest", "marsh", "volcano", "island",
                "canyon", "lake", "river", "wetland", "coral reef", "estuary", "creek", "meadow", "prairie",
                "valley", "cavern", "oasis", "glacier", "crag", "plateau", "cave system", "fjord", "cove",
                "garden", "orchard", "village", "countryside", "park", "botanical garden", "zoo", "cemetery",
                "graveyard", "underground city", "sewer system"
            ],
            "pattern": [
                "striped", "spotted", "mottled", "marbled", "camouflaged", "speckled", "patchy",
                "tortoiseshell", "dappled", "brindle", "banded", "flecked", "streaked", "frosted", "rosetted",
                "blotched", "barred", "flecked", "swirled", "clouded", "pied", "brindled", "tabby", "calico",
                "leopard", "cheetah", "tiger", "zebra", "giraffe", "snakeskin", "checkerboard", "harlequin",
                "honeycomb", "polka-dotted", "tuxedo", "dalmatian", "leopard", "cow", "zebra", "tortoiseshell",
                "mackerel", "gazelle", "ocelot", "jaguar", "leopard", "mouflon", "okapi", "pinto", "quilted",
                "saddle"
            ],
            "fur_type": [
                "short", "long", "curly", "straight", "wavy", "fluffy", "sleek", "frizzy", "thick", "thin",
                "shaggy", "wire-haired", "silky", "coarse", "soft", "downy", "feathery", "bushy", "woolly",
                "tufted", "plush", "velvety", "crimped", "matted", "tangled", "corded", "tousled", "fuzzy",
                "sparse", "satin", "pelted", "bristly", "hairy", "slick", "glossy", "lustrous", "nappy",
                "unruly", "tawny", "cottony", "kinky", "pomaded", "disheveled", "flecked", "frosted",
                "variegated", "unkept", "ruffled", "greasy", "peppered", "singed"
            ],
            "behavior": [
                "playful", "agile", "docile", "energetic", "affectionate", "intelligent", "curious",
                "gregarious", "territorial", "social", "solitary", "dominant", "submissive", "mischievous",
                "alert", "cautious", "aggressive", "fearful", "bold", "friendly", "shy", "skittish", "calm",
                "determined", "stubborn", "adaptable", "patient", "vocal", "noisy", "quiet", "cooperative",
                "defensive", "graceful", "clumsy", "inquisitive", "bold", "timid", "restless", "playful",
                "aggressive", "elusive", "sociable", "independent", "nocturnal", "diurnal", "migratory",
                "territorial", "courageous", "sly", "gregarious"
            ],
            "weather": [
                "sunny", "cloudy", "rainy", "snowy", "windy"
            ],
            "time": [
                "morning", "afternoon", "evening", "night"
            ],
            "size": [
                "small", "medium", "large", "tiny", "giant", "miniature", "massive",
                "enormous", "huge", "little"
            ],
            "location": [
                "train station", "airport", "beach", "mountain", "park", "forest", "desert", "countryside",
                "city center", "residential area", "office building", "school", "library", "hospital",
                "shopping mall", "restaurant", "coffee shop", "bar", "nightclub", "hotel", "museum", "gallery",
                "theater", "stadium", "amusement park", "zoo", "farm", "harbor", "riverbank", "lake", "bridge",
                "cave", "island", "waterfall", "ruins", "church", "temple", "mosque", "synagogue", "castle",
                "palace", "marketplace", "subway station", "bus stop", "train tracks", "campsite", "campus",
                "skyscraper", "wind farm", "power plant", "construction site", "warehouse", "jungle",
                "cemetery", "underground tunnel", "volcano", "lighthouse", "observatory", "prison", "garden",
                "carnival", "farmhouse", "vineyard", "race track", "skate park", "cemetery", "mine",
                "golf course", "ski resort", "apartment building", "factory", "quarry", "pier", "aquarium",
                "planetarium", "radio tower", "water tower", "playground", "gas station", "highway",
                "cruise ship", "helipad", "space station", "junkyard", "wasteland", "island resort",
                "floating market", "train yard", "bamboo forest", "coral reef", "football stadium",
                "racecourse", "seaside cliffs", "gondola", "prairie", "hot air balloon", "windmill", "outback",
                "carnival", "fairground", "deserted island", "lakeside cabin", "abandoned factory",
                "boardwalk", "bamboo grove", "fishing village", "iceberg", "garden maze", "beachside villa",
                "snowy village", "castle ruins", "cottage", "waterfront", "oasis", "treehouse",
                "floating island", "cliffside village", "shipwreck", "lighthouse", "tropical rainforest",
                "cave dwelling", "apartment balcony", "suspension bridge", "ancient temple", "skydiving",
                "paragliding", "ice cave", "glacier", "board game cafe", "gymnasium", "skating rink",
                "school bus", "bookstore", "vintage shop", "street market", "rooftop garden", "rooftop bar",
                "tea plantation", "rice terrace", "night market", "food court"
            ],
            "eye_color": [
                "brown", "blue", "green", "hazel", "gray"
            ],
            "emotion": [
                "happy", "sad", "angry", "surprised", "disgusted", "scared", "neutral", "confused", "bored",
                "excited", "tired", "calm", "relaxed", "energetic", "stressed", "anxious", "depressed",
                "lonely", "jealous", "proud", "ashamed", "guilty", "embarrassed", "shy", "hopeful",
                "disappointed", "satisfied", "pessimistic", "optimistic", "nostalgic", "amused", "bored",
                "curious", "determined", "frustrated", "grateful"
            ]
        }
    },
    "architecture": {
        "negative_prompt": "(Poorly designed structure), (Dilapidated building), (Unattractive facade)",
        "weights": {
            "architecture": 1.0,
            "material": 1.0,
            "style": 1.0,
            "window_type": 1.0,
            "roof_style": 1.0,
            "color": 1.0,
            "adjective": 1.0,
            "location": 1.0,
            "emotion": 1.0,
            "weather": 1.0
        },
        "builder": [
            {
                "text": "$style ",
                "cond": "style"
            },
            {
                "text": "$architecture ",
                "cond": "architecture",
                "else": "building"
            },
            {
                "text": "in $location ",
                "cond": "location",
                "else": ". "
            },
            {
                "text": "The $architecture is ",
                "cond": "architecture",
                "else": "The building is "
            },
            {
                "text": "$age, ",
                "cond": "age"
            },
            {
                "text": "$material details, ",
                "cond": "material"
            },
            {
                "text": "$window_type windows,  ",
                "cond": "window_type"
            },
            {
                "text": "$roof_style roof,  ",
                "cond": "roof_style"
            },
            {
                "text": "standing tall and proud. "
            },
            {
                "cond": "emotion",
                "next": [
                    {
                        "text": "The $architecture looks ",
                        "else": "The building looks "
                    },
                    {
                        "text": "$emotion. "
                    }
                ]
            },
            {
                "cond": "location",
                "text": "The $location is ",
                "next": [
                    {
                        "text": "$weather ",
                        "cond": "weather"
                    },
                    {
                        "text": "$time. ",
                        "cond": "time"
                    }
                ]
            },
            {
                "var": "$adjective design, ",
                "text": "$adjective design, "
            },
            {
                "var": "impressive symetry, a masterpiece of engineering."
            }
        ],
        "variables": {
            "architecture": [
                "skyscraper", "mansion", "villa", "cottage", "apartment building", "office building",
                "church", "temple", "mosque", "castle", "bungalow", "townhouse", "museum", "library",
                "school", "hospital", "hotel", "shopping mall", "stadium", "theater", "gallery", "bridge",
                "lighthouse", "observatory", "pavilion", "monument", "government building",
                "train station", "airport", "courthouse", "skyscraper", "condominium", "warehouse",
                "factory", "restaurant", "coffee shop", "bank", "houseboat", "farmhouse", "log cabin",
                "cabin", "hut", "tent", "igloo"
            ],
            "material": [
                "brick", "stone", "concrete", "wood", "glass", "steel", "stucco", "aluminum",
                "vinyl", "timber", "bamboo", "marble", "granite", "limestone", "slate", "tile",
                "plaster", "copper", "iron", "fiberglass", "straw", "thatch", "rammed earth",
                "adobe", "cob", "glass fiber", "reclaimed materials", "corrugated metal",
                "composite", "clay", "terra cotta", "sandstone", "porcelain", "plastic",
                "synthetic", "polycarbonate", "concrete block", "poured concrete", "stone veneer",
                "recycled materials"
            ],
            "style": [
                "modern", "minimalist", "contemporary", "traditional", "colonial", "Victorian",
                "Gothic", "Art Deco", "Mediterranean", "Renaissance", "Baroque", "Neoclassical",
                "Bauhaus", "Craftsman", "Tudor", "Greek Revival", "Romanesque", "Art Nouveau",
                "Postmodern", "Futuristic", "Brutalist", "Prairie", "Spanish Revival",
                "Mid-Century Modern", "Georgian", "Islamic", "Chinese", "Japanese", "Thai",
                "Balinese", "Scandinavian", "Industrial", "Farmhouse", "Cottage", "Rustic",
                "Transitional", "International", "French Provincial", "Southwestern", "Coastal",
                "Shaker", "Mission", "Cape Cod", "A-frame", "Split-level"
            ],
            "window_type": [
                "bay", "casement", "double-hung", "picture", "sliding", "awning", "transom",
                "skylight", "fixed", "stained glass", "arched", "palladian", "folding",
                "corner", "clerestory", "jalousie", "louvered", "round", "oval", "diamond",
                "geometric", "frameless", "tilt and turn", "pivot", "hopper", "ribbon",
                "multi-panel", "French", "sash", "floor-to-ceiling", "curved", "dormer",
                "garden"
            ],
            "roof_style": [
                "gable", "hip", "mansard", "flat", "shed", "dome", "gambrel", "saltbox",
                "butterfly", "arched", "mansard", "sawtooth", "clerestory", "pyramid",
                "skillion", "curved", "pavilion", "tented", "butterfly", "green", "parapet",
                "domed", "circular", "turret", "hipped gable", "barn", "split-level", "mansard",
                "gull-wing", "wave", "sloping", "multi-gabled", "half-hipped", "saddleback",
                "mansard hip", "hexagonal", "octagonal"
            ],
            "color": [
                "white", "black", "gray", "brown", "beige", "red", "orange", "yellow", "green", "blue"
            ],
            "adjective": [
                "brilliant", "fierce", "vibrant", "exquisite", "charming", "elegant", "majestic", "captivating",
                "serene", "enchanting", "radiant", "magnificent", "tranquil", "glorious", "spectacular",
                "delightful", "mesmerizing", "mysterious", "breathtaking", "splendid", "harmonious", "graceful",
                "stunning", "wondrous", "sublime", "dazzling", "awe-inspiring", "fantastic", "marvelous",
                "bewitching", "ethereal", "spellbinding", "extraordinary", "picturesque", "phenomenal",
                "impressive", "thrilling", "enigmatic", "spellbinding", "alluring", "transcendent", "riveting",
                "charismatic", "sensational", "spellbinding", "unforgettable", "incredible", "timeless"
            ],
            "location": [
                "train station", "airport", "beach", "mountain", "park", "forest", "desert", "countryside",
                "city center", "residential area", "office building", "school", "library", "hospital",
                "shopping mall", "restaurant", "coffee shop", "bar", "nightclub", "hotel", "museum", "gallery",
                "theater", "stadium", "amusement park", "zoo", "farm", "harbor", "riverbank", "lake", "bridge",
                "cave", "island", "waterfall", "ruins", "church", "temple", "mosque", "synagogue", "castle",
                "palace", "marketplace", "subway station", "bus stop", "train tracks", "campsite", "campus",
                "skyscraper", "wind farm", "power plant", "construction site", "warehouse", "jungle",
                "cemetery", "underground tunnel", "volcano", "lighthouse", "observatory", "prison", "garden",
                "carnival", "farmhouse", "vineyard", "race track", "skate park", "cemetery", "mine",
                "golf course", "ski resort", "apartment building", "factory", "quarry", "pier", "aquarium",
                "planetarium", "radio tower", "water tower", "playground", "gas station", "highway",
                "cruise ship", "helipad", "space station", "junkyard", "wasteland", "island resort",
                "floating market", "train yard", "bamboo forest", "coral reef", "football stadium",
                "racecourse", "seaside cliffs", "gondola", "prairie", "hot air balloon", "windmill", "outback",
                "carnival", "fairground", "deserted island", "lakeside cabin", "abandoned factory",
                "boardwalk", "bamboo grove", "fishing village", "iceberg", "garden maze", "beachside villa",
                "snowy village", "castle ruins", "cottage", "waterfront", "oasis", "treehouse",
                "floating island", "cliffside village", "shipwreck", "lighthouse", "tropical rainforest",
                "cave dwelling", "apartment balcony", "suspension bridge", "ancient temple", "skydiving",
                "paragliding", "ice cave", "glacier", "board game cafe", "gymnasium", "skating rink",
                "school bus", "bookstore", "vintage shop", "street market", "rooftop garden", "rooftop bar",
                "tea plantation", "rice terrace", "night market", "food court"
            ],
            "emotion": [
                "happy", "sad", "angry", "surprised", "disgusted", "scared", "neutral", "confused", "bored",
                "excited", "tired", "calm", "relaxed", "energetic", "stressed", "anxious", "depressed",
                "lonely", "jealous", "proud", "ashamed", "guilty", "embarrassed", "shy", "hopeful",
                "disappointed", "satisfied", "pessimistic", "optimistic", "nostalgic", "amused", "bored",
                "curious", "determined", "frustrated", "grateful"
            ],
            "weather": [
                "sunny", "cloudy", "rainy", "snowy", "windy"]
        },
    },
    "food": {
        "negative_prompt": "(Unappetizing appearance), (Bland coloration), (Spoiled or rotten)",
        "weights": {
            "food": 1.0,
            "color": 1.0,
            "seasoning": 1.0,
            "texture": 1.0,
            "utensil": 1.0,
            "background": 1.0,
            "adjective": 1.0,
            "weather": 1.0,
            "time": 1.0
        },
        "builder": [
            {
                "text": "A "
            },
            {
                "text": "$adjective ",
                "cond": "adjective"
            },
            {
                "text": "$color ",
                "cond": "color"
            },
            {
                "text": "$food ",
                "cond": "food"
            },
            {
                "text": "dish "
            },
            {
                "text": "on a $background ",
                "cond": "background"
            },
            {
                "text": ". "
            },
            {
                "text": "Seasoned with $seasoning, ",
                "cond": "seasoning"
            },
            {
                "text": "$texture texture, ",
                "cond": "texture"
            },
            {
                "text": "Served in a $utensil.",
                "cond": "utensil"
            },
            {
                "text": "Seasoned with $seasoning, ",
                "cond": "seasoning"
            },
            {
                "cond": "adjective",
                "next": [
                    {
                        "text": "The $food looks ",
                        "cond": "food",
                        "else": "The food looks "
                    },
                    {
                        "text": "$adjective "
                    }
                ]
            },
            {
                "text": "The $background is ",
                "cond": "background",
                "else": "The background is "
            },
            {
                "text": "$weather ",
                "cond": "weather"
            },
            {
                "text": "at $time ",
                "cond": "time"
            },
            {
                "text": "enticing presentation, artistic arrangement, "
            },
            {
                "text": "$adjective, ",
                "cond": "adjective"
            },
            {
                "text": "an epicurean delight"
            }
        ],
        "variables": {
            "food": [
                "pizza",
                "burger",
                "sushi",
                "pasta",
                "steak",
                "salad",
                "tacos",
                "sandwich",
                "soup",
                "rice",
                "noodles",
                "curry",
                "barbecue",
                "pancakes",
                "waffles",
                "omelette",
                "fried chicken",
                "burrito",
                "lasagna",
                "grilled cheese",
                "hot dog",
                "lobster",
                "crab",
                "shrimp",
                "salmon",
                "sashimi",
                "ramen",
                "pad thai",
                "chow mein",
                "falafel",
                "gyro",
                "hamburger",
                "fajitas",
                "enchiladas",
                "quesadilla",
                "samosa",
                "tandoori chicken",
                "naan",
                "hummus",
                "pita bread",
                "sushi roll",
                "tempura",
                "miso soup",
                "dim sum",
                "spring rolls",
                "pho",
                "banh mi",
                "bibimbap",
                "chicken tikka masala",
                "biryani",
                "goulash",
                "paella",
                "cr\u00eapes",
                "schnitzel",
                "tiramisu",
                "pierogi",
                "poutine",
                "pav bhaji",
                "sauerbraten",
                "kimchi",
                "couscous",
                "empanada",
                "ceviche",
                "jambalaya",
                "escargot",
                "risotto",
                "beef stew",
                "ph\u1edf",
                "baklava",
                "tofu",
                "souvlaki",
                "masala dosa",
                "peking duck",
                "tikka masala",
                "moussaka",
                "spanakopita",
                "cannoli",
                "haggis",
                "borscht",
                "scones",
                "arepas",
                "tamales",
                "mochi",
                "macaron",
                "gnocchi",
                "cr\u00e8me br\u00fbl\u00e9e",
                "moules frites",
                "pavlova",
                "kimchi jjigae",
                "churros",
                "beignets",
                "cassoulet",
                "gazpacho",
                "tacos al pastor",
                "chiles en nogada",
                "bratwurst",
                "sushi burrito",
                "shakshuka",
                "beef bulgogi",
                "neapolitan pizza",
                "vada pav",
                "croissant",
                "bun bo hue",
                "sauerkraut",
                "lobster bisque",
                "bouillabaisse",
                "tarte tatin",
                "jerk chicken",
                "falafel wrap",
                "nasi goreng",
                "spaghetti carbonara",
                "pastrami sandwich",
                "chimichanga",
                "caesar salad",
                "goulash soup",
                "crab cakes",
                "fish and chips",
                "s'mores",
                "ratatouille",
                "key lime pie",
                "mango sticky rice",
                "stroganoff",
                "strawberry shortcake",
                "red velvet cake",
                "b\u00fan ch\u1ea3",
                "fettuccine alfredo",
                "crab rangoon",
                "tacos de barbacoa",
                "pork adobo",
                "chicken parmigiana",
                "kung pao chicken",
                "mushroom risotto",
                "cajun gumbo",
                "mango lassi",
                "fried rice",
                "fried calamari",
                "chicken satay",
                "garlic naan",
                "katsu curry",
                "tempura udon",
                "baked ziti",
                "gazelle horn",
                "belgian waffle",
                "spanish tortilla",
                "lobster roll",
                "beef wellington",
                "filet mignon",
                "beef bourguignon",
                "grilled octopus",
                "chicken shawarma",
                "beef brisket",
                "sourdough bread",
                "apple pie",
                "mahi-mahi",
                "chicken and waffles",
                "oysters Rockefeller",
                "rack of lamb",
                "beef rendang",
                "crab legs",
                "black forest cake",
                "gyoza",
                "pepperoni pizza",
                "saffron rice",
                "tostones",
                "pulled pork sandwich",
                "garlic shrimp",
                "calzone",
                "beef stroganoff",
                "lobster tail",
                "chicken biryani",
                "chicken korma",
                "lamb kebab",
                "beef teriyaki",
                "caramel flan",
                "enchilada",
                "buffalo wings",
                "lobster mac and cheese",
                "veal parmigiana",
                "beef empanadas",
                "escabeche",
                "coq au vin",
                "shrimp scampi",
                "chicken adobo",
                "chicken tikka",
                "chicken katsu",
                "pumpkin pie",
                "potato latkes",
                "garlic bread",
                "beef kebab",
                "seafood paella",
                "beef and broccoli",
                "hush puppies",
                "fried catfish",
                "chicken fried rice",
                "veal piccata",
                "shrimp gumbo",
                "caramelized onion tart",
                "tres leches cake",
                "beef samosa",
                "beef tamales",
                "coconut shrimp",
                "beef fajitas",
                "shrimp tempura",
                "beef noodle soup",
                "beef pho",
                "chicken pho",
                "lobster pho",
                "seafood gumbo",
                "clam chowder",
                "lobster chowder",
                "chicken chow mein",
                "chicken pad thai",
                "beef pad see ew",
                "mango salad",
                "caprese salad",
                "greek salad",
                "chicken salad",
                "tuna salad",
                "fruit salad",
                "cobb salad",
                "potato salad",
                "pasta salad",
                "coleslaw",
                "tabbouleh",
                "waldorf salad",
                "garden salad",
                "nicoise salad",
                "quinoa salad",
                "spinach salad",
                "beet salad",
                "shrimp salad",
                "salmon salad",
                "cucumber salad",
                "bean salad",
                "couscous salad",
                "soba noodle salad",
                "roast beef sandwich",
                "turkey sandwich",
                "ham sandwich",
                "chicken sandwich",
                "tuna sandwich",
                "BLT sandwich",
                "club sandwich",
                "grilled cheese sandwich",
                "reuben sandwich",
                "philly cheesesteak",
                "cuban sandwich",
                "banh mi sandwich",
                "monte cristo sandwich",
                "gyro sandwich",
                "chicken wrap",
                "taco salad",
                "chicken caesar wrap",
                "taco",
                "nachos",
                "guacamole",
                "salsa",
                "queso dip",
                "tostada",
                "tamale",
                "flautas",
                "pupusa",
                "plantains",
                "pico de gallo",
                "sopes",
                "horchata",
                "chips and dip",
                "salsa verde",
                "tortilla soup",
                "posole",
                "menudo",
                "mole",
                "salsa roja",
                "taco al pastor",
                "taco de barbacoa",
                "taco de carnitas",
                "taco de lengua",
                "salsa picante",
                "enchilada sauce",
                "guajillo sauce",
                "adobo sauce",
                "mexican rice",
                "refried beans",
                "arroz con pollo",
                "flan",
                "butter chicken",
                "naan bread",
                "saag paneer",
                "dal makhani",
                "korma",
                "pakora",
                "papadum",
                "chutney",
                "palak paneer",
                "gulab jamun",
                "rajma",
                "jalebi",
                "kulfi",
                "idli",
                "vada",
                "upma",
                "bhelpuri",
                "chana masala",
                "coconut chutney",
                "indian bread",
                "paneer tikka",
                "ghee",
                "masoor dal",
                "vegetable biryani",
                "malai kofta",
                "butter naan",
                "hyderabadi biryani",
                "rabri",
                "kadai paneer",
                "punjabi samosa",
                "sindhi biryani",
                "dum biryani",
                "paneer butter masala",
                "matar paneer",
                "chicken kebab",
                "butter garlic naan",
                "palak chicken",
                "murg makhani",
                "balti chicken",
                "chicken tandoori",
                "peshawari naan",
                "chicken kofta",
                "mutton biryani",
                "mutton curry",
                "seekh kebab",
                "kashmiri pulao",
                "beef pulao",
                "keema",
                "kashmiri naan",
                "paneer pakora",
                "pav sandwich",
                "cheese garlic naan",
                "paneer bhurji",
                "kheer",
                "mango pickle",
                "chicken 65",
                "samosa chaat",
                "masala chai",
                "lamb curry",
                "kebab",
                "baba ganoush",
                "shawarma",
                "kibbeh",
                "dolma",
                "maqluba",
                "za'atar",
                "manakeesh",
                "kunafa",
                "musakhan",
                "foul medames",
                "majadra",
                "harissa",
                "mint tea",
                "labneh",
                "koshari",
                "knafeh",
                "mloukhieh",
                "loukoumades",
                "shish taouk"
            ],
            "color": [
                "red", "orange", "yellow", "green", "blue", "purple", "pink", "brown", "black", "white", "gray"
            ],
            "seasoning": [
                "salt", "pepper", "garlic powder", "onion powder", "cumin", "paprika", "chili powder",
                "cayenne pepper", "oregano", "thyme", "rosemary", "basil", "coriander", "turmeric",
                "curry powder", "cinnamon", "nutmeg", "ginger", "dill", "parsley", "bay leaves",
                "mustard seeds", "celery salt", "fennel seeds", "caraway seeds", "cloves", "cardamom",
                "allspice", "taco seasoning", "italian seasoning", "garam masala", "five-spice powder",
                "herbes de Provence", "steak seasoning", "poultry seasoning", "cajun seasoning",
                "lemon pepper", "sazon seasoning", "barbecue rub"
            ],
            "texture": [
                "crispy", "smooth", "creamy", "crunchy", "tender", "flaky", "velvety", "gooey", "silky",
                "chewy", "juicy", "gritty", "spongy", "crumbly", "brittle", "tacky", "lumpy", "grainy",
                "jelly-like", "springy", "airy", "fibrous", "slimy", "sticky", "gelatinous", "meaty",
                "stringy", "toothsome", "runny", "thick", "cottony", "syrupy", "waxy", "oily", "dense",
                "foamy", "sandy", "crackling", "sizzling", "frosty", "powdery", "sauce-like", "fleshy",
                "bubbly", "tart", "unctuous"
            ],
            "utensil": [
                "spoon", "fork", "knife", "spatula", "ladle", "whisk", "tongs", "peeler", "grater",
                "can opener", "strainer", "colander", "measuring cups", "measuring spoons", "mixing bowls",
                "cutting board", "chef's knife", "paring knife", "baking sheet", "rolling pin", "oven mitts",
                "pot", "pan", "skillet", "saucepan", "grill pan", "blender", "food processor", "masher",
                "pastry brush", "grill tongs", "salad tongs", "slotted spoon", "wire rack", "vegetable peeler",
                "whisk", "garlic press", "corkscrew", "meat tenderizer", "basting brush", "mortar and pestle",
                "kitchen shears", "can opener", "pizza cutter"
            ],
            "background": [
                "rustic wooden table", "marble countertop", "white ceramic plate",
                "vintage floral tablecloth", "chalkboard backdrop", "earthenware platter",
                "natural stone surface", "colorful mosaic tiles", "bokeh lights", "patterned fabric",
                "kitchen cutting board", "burlap sack", "tiled backdrop", "stainless steel countertop",
                "concrete surface", "woven placemat", "weathered brick wall", "tropical palm leaves",
                "glossy black surface", "corkboard", "glass serving tray", "antique dining table",
                "vibrant textured backdrop", "textured wallpaper", "slate board", "faux fur surface",
                "metallic foil backdrop", "shabby chic backdrop", "vintage wallpaper", "wicker basket",
                "fabric napkin", "bamboo mat", "tarnished silver platter", "aged parchment paper",
                "candlelit setting", "wrought iron table", "artistic mosaic backdrop",
                "vintage lace doily", "polished granite countertop", "herringbone patterned surface",
                "exposed brick wall", "colorful bokeh lights", "linen tablecloth"
            ],
            "adjective": [
                "delicious", "scrumptious", "mouthwatering", "savory", "flavorful",
                "tasty", "appetizing", "delectable", "yummy", "succulent", "tempting",
                "heavenly", "satisfying", "irresistible", "luscious", "divine",
                "mouthwatering", "zingy", "spicy", "sweet", "sour", "creamy", "rich",
                "juicy", "crispy", "fluffy", "tender", "gooey", "refreshing", "nutty",
                "buttery", "sizzling", "wholesome", "homemade", "flavor-packed"
            ],
            "weather": [
                "sunny", "cloudy", "rainy", "snowy", "windy"
            ],
            "time": [
                "morning", "afternoon", "evening", "night"
            ]
        },
    },
    "person": {
        "negative_prompt": "(bad facial features), (indistinct facial features), (mangled hands)",
        "weights": {
            "age": 1.4,
            "gender": 1.2,
            "clothing": 1.1,
            "location": 1.3,
            "ethnicity": 1.1,
            "skin_tone": 0.8,
            "body_type": 1.2,
            "hair_color": 1.0,
            "hair_length": 1.0,
            "facial_hair": 1.1,
            "eye_color": 1.1,
            "height": 1.2,
            "piercings": 1.0,
            "scars": 1.0,
            "tattoos": 1.0,
            "birthmarks": 1.0,
            "disabilities": 1.0,
            "glasses": 1.0,
            "hat": 1.0,
            "shirt": 1.0,
            "pants": 1.0,
            "shoes": 1.0,
            "accessories": 1.0,
            "emotion": 1.2,
            "personality": 1.0,
            "descriptive_traits": 1.2,
            "occupation": 1.0
        },
        "builder": [
            {
                "text": "A "
            },
            {
                "text": "$ethnicity ",
                "cond": "ethnicity"
            },
            {
                "text": "$gender person named $$gender_name ",
                "cond": "gender"
            },
            {
                "text": "person ",
                "not_cond": "ethnicity,gender"
            },
            {
                "text": "at $location. ",
                "cond": "location"
            },
            {
                "text": ". ",
                "not_cond": "location"
            },
            {
                "text": "$$gender_name is $age ",
                "cond": "age,gender"
            },
            {
                "text": "The person is $age ",
                "cond": "age",
                "not_cond": "gender"
            },
            {
                "text": "($hair_length $hair_color hair.) ",
                "cond": "hair_length,hair_color"
            },
            {
                "text": "($hair_length hair.) ",
                "cond": "hair_length",
                "not_cond": "hair_color"
            },
            {
                "text": "$hair_color ",
                "cond": "hair_color",
                "not_cond": "hair_length"
            },
            {
                "text": "($eye_color eyes), ",
                "cond": "eye_color"
            },
            {
                "text": "($skin_tone skin), ",
                "cond": "skin_tone"
            },
            {
                "text": "$$gender_name has ",
                "cond": "gender",
                "or_cond": "body_type,height,facial_hair,glasses,hat,shirt,pants,clothing"
            },
            {
                "text": "The person has ",
                "not_cond": "gender",
                "or_cond": "body_type,height,facial_hair,glasses,hat,shirt,pants,clothing"
            },
            {
                "text": "a ($body_type body-type), ",
                "cond": "body_type"
            },
            {
                "text": "is ($height height), ",
                "cond": "height"
            },
            {
                "text": "(wears $facial_hair), ",
                "cond": "facial_hair"
            },
            {
                "text": "(wears $glasses), ",
                "cond": "glasses"
            },
            {
                "text": "is (wearing a $hat), ",
                "cond": "hat"
            },
            {
                "text": "is (wearing a $shirt), ",
                "cond": "shirt"
            },
            {
                "text": "is (wearing $pants), ",
                "cond": "pants"
            },
            {
                "text": "is (wearing $clothing). ",
                "cond": "clothing"
            },
            {
                "text": "$$gender_name ",
                "cond": "gender",
                "or_cond": "shoes,accessories,tattoos,piercings,scars,occupation,descriptive_traits,emotion,personality,disabilities"
            },
            {
                "text": "the person ",
                "or_cond": "shoes,accessories,tattoos,piercings,scars,occupation,descriptive_traits,emotion,personality,disabilities",
            },
            {
                "text": "(wearing $shoes), ",
                "cond": "shoes"
            },
            {
                "text": "(wearing $accessories), ",
                "cond": "accessories"
            },
            {
                "text": "has ($tattoos tattoos), ",
                "cond": "tattoos"
            },
            {
                "text": "has ($piercings piercings), ",
                "cond": "piercings"
            },
            {
                "text": "has ($scars scars), ",
                "cond": "scars"
            },
            {
                "text": "is (dressed like a $occupation), ",
                "cond": "occupation"
            },
            {
                "text": "is $descriptive_traits, ",
                "cond": "descriptive_traits"
            },
            {
                "text": "is $emotion, ",
                "cond": "emotion"
            },
            {
                "text": "is $personality, ",
                "cond": "personality"
            },
            {
                "text": "has $disabilities disabilities. ",
                "cond": "disabilities"
            }
        ],
        "variables": {
            "age": {
                "type": "range",
                "min": 18,
                "max": 100
            },
            "gender": ["Male", "Female"],
            "location": ["train station", "airport", "beach", "mountain", "park", "forest", "desert", "countryside",
                         "city center", "residential area", "office building", "school", "library", "hospital",
                         "shopping mall", "restaurant", "coffee shop", "bar", "nightclub", "hotel", "museum", "gallery",
                         "theater", "stadium", "amusement park", "zoo", "farm", "harbor", "riverbank", "lake", "bridge",
                         "cave", "island", "waterfall", "ruins", "church", "temple", "mosque", "synagogue", "castle",
                         "palace", "marketplace", "subway station", "bus stop", "train tracks", "campsite", "campus",
                         "skyscraper", "wind farm", "power plant", "construction site", "warehouse", "jungle",
                         "underground tunnel", "volcano", "observatory", "prison", "garden",
                         "farmhouse", "vineyard", "race track", "skate park", "cemetery", "mine",
                         "golf course", "ski resort", "apartment building", "factory", "quarry", "pier", "aquarium",
                         "planetarium", "radio tower", "water tower", "playground", "gas station", "highway",
                         "cruise ship", "helipad", "space station", "junkyard", "wasteland", "island resort",
                         "floating market", "train yard", "bamboo forest", "coral reef", "football stadium",
                         "racecourse", "seaside cliffs", "gondola", "prairie", "hot air balloon", "windmill", "outback",
                         "carnival", "fairground", "deserted island", "lakeside cabin", "abandoned factory",
                         "boardwalk", "bamboo grove", "fishing village", "iceberg", "garden maze", "beachside villa",
                         "snowy village", "castle ruins", "cottage", "waterfront", "oasis", "treehouse",
                         "floating island", "cliffside village", "shipwreck", "lighthouse", "tropical rainforest",
                         "cave dwelling", "apartment balcony", "suspension bridge", "ancient temple", "skydiving",
                         "paragliding", "ice cave", "glacier", "board game cafe", "gymnasium", "skating rink",
                         "school bus", "bookstore", "vintage shop", "street market", "rooftop garden", "rooftop bar",
                         "tea plantation", "rice terrace", "night market", "food court"],
            "hair_color": ["Black", "Brown", "Blonde", "Red", "Gray", "White"],
            "ethnicity": [
                "Alaskan Native",
                "Arab",
                "Ashkenazi Jewish",
                "Asian",
                "Bengali",
                "Berber",
                "Black or African American",
                "Caribbean",
                "Central Asian",
                "Chinese",
                "Filipino",
                "Hispanic or Latino",
                "Hmong",
                "Indian",
                "Indigenous Australian",
                "Indigenous Canadian",
                "Indigenous South American",
                "Indigenous Siberian",
                "Indigenous Pacific Islander",
                "Japanese",
                "Korean",
                "Maori",
                "Melanesian",
                "Middle Eastern",
                "Mixed Race",
                "Native American",
                "North African",
                "Pakistani",
                "Polynesian",
                "Romani",
                "Samoan",
                "South Asian",
                "Southeast Asian",
                "Sub-Saharan African",
                "Taiwanese",
                "Tibetan",
                "Turkic",
                "Vietnamese",
                "White"
            ],
            "eye_color": ["Brown", "Blue", "Green", "Hazel", "Gray"],
            "hair_length": ["Short", "Medium", "Long", "Shaved", "Partially-shaved", "Bald", "Balding", "Hairpiece",
                            "Hair-plugs"],
            "skin_tone": ["Light", "Medium", "Dark"],
            "body_type": ["Thin", "Average", "Athletic", "Muscular", "Overweight"],
            "facial_hair": ["Clean-shaven", "Mustache", "Beard", "Goatee"],
            "clothing": ["a suit", "a dress", "a t-shirt", "a jacket", "a hat", "a tie", "a skirt", "a blouse",
                         "a coat", "a sweater", "a pair of pants", "a pair of shorts", "a pair of shoes",
                         "a pair of boots", "a pair of sandals", "a pair of sneakers", "a pair of high heels",
                         "a pair of loafers", "a pair of slippers", "a pair of flip flops", "a pair of gloves",
                         "a pair of mittens", "a pair of socks", "a pair of stockings", "a pair of leggings",
                         "a pair of tights", "a pair of jeans", "a pair of pajamas",
                         "a pair of glasses", "a pair of sunglasses", "a pair of earrings", "a pair of bracelets",
                         "a pair of rings", "a pair of necklaces", "a pair of suspenders", "a pair of overalls"],
            "glasses": ["Reading-glasses", "Sunglasses"],
            "hat": ["Baseball Cap", "Beanie", "Cowboy Hat", "Fedora", "Hard Hat", "Sombrero", "Top Hat", "Visor",
                    "Headband", "Bandana"],
            "shirt": ["T-Shirt", "Button-Up shirt", "Sweater", "Jacket", "Suit"],
            "pants": ["Shorts", "Jeans", "Slacks", "Sweatpants", "Skirt", "Dress", "Leggings", "Tights", "Pajamas",
                      "Overalls", "Jumpsuit", "Swimsuit"],
            "shoes": ["Sneakers", "Dress Shoes", "Boots"],
            "accessories": ["Necklace", "Watch", "Bracelet", "Ring", "Earrings", "Piercings"],
            "tattoos": ["Arm", "Leg", "Chest", "Back", "Face", "Neck", "Hand", "Foot"],
            "piercings": ["Ear", "Nose", "Eyebrow", "Lip", "Tongue", "Belly Button"],
            "scars": ["Face", "Arm", "Leg", "Chest", "Back", "Neck", "Hand", "Foot"],
            "birthmarks": ["Face", "Arm", "Leg", "Chest", "Back", "Neck", "Hand", "Foot"],
            "disabilities": ["Blind", "Deaf", "Wheelchair", "Missing Limb", "Other"],
            "personality": ["Funny", "Serious", "Happy", "Sad", "Angry", "Calm", "Anxious", "Depressed", "Excited",
                            "Bored", "Tired", "Energetic", "Confident", "Shy", "Friendly", "Unfriendly", "Kind", "Mean",
                            "Generous", "Selfish", "Honest", "Dishonest", "Loyal", "Disloyal", "Optimistic",
                            "Pessimistic", "Religious", "Athiest", "Spiritual", "Agnostic", "Intelligent", "Dumb",
                            "Creative", "Logical", "Emotional", "Introverted", "Extroverted", "Ambiverted",
                            "Hardworking", "Lazy", "Organized", "Disorganized", "Patient", "Impatient", "Responsible",
                            "Irresponsible", "Caring", "Unempathetic", "Open-Minded", "Closed-Minded", "Adventurous",
                            "Cautious", "Courageous", "Cowardly", "Confident", "Insecure", "Humble", "Arrogant"],
            "occupation": ["Accountant", "Actor", "Actress", "Architect", "Artist", "Athlete", "Author", "Baker",
                           "Banker", "Barber", "Bartender", "Blogger", "Bookkeeper", "Bus Driver", "Butcher",
                           "Carpenter", "Cashier", "Chef", "Chemist", "Janitor", "Coach", "Comedian",
                           "Construction Worker", "Consultant", "Counselor", "Dancer", "Dentist", "Designer",
                           "Detective", "Dietician", "Doctor", "Electrician", "Engineer", "Farmer", "Firefighter",
                           "Fisherman", "Fitness Instructor", "Flight Attendant", "Florist", "Gardener", "Hairdresser",
                           "Housekeeper", "Interior Designer", "Journalist", "Judge", "Lawyer", "Librarian",
                           "Lifeguard", "Linguist", "Manager", "Mechanic", "Model", "Musician", "Nurse", "Optician",
                           "Painter", "Paramedic", "Pharmacist", "Photographer", "Physician", "Physicist", "Pilot",
                           "Plumber", "Police Officer", "Politician", "Professor", "Programmer", "Psychologist",
                           "Receptionist", "Salesperson", "Scientist", "Secretary", "Security Guard", "Singer",
                           "Social Worker", "Soldier", "Statistician", "Surgeon", "Tailor", "Teacher", "Technician",
                           "Therapist", "Translator", "Truck Driver", "Veterinarian", "Waiter", "Waitress", "Writer"],
            "descriptive_traits": ["Tall", "Short", "Handsome", "Beautiful", "Ugly", "Pretty", "Cute", "Gorgeous",
                                   "Hot", "Attractive", "Unattractive"],
            "emotion": ["Happy", "Sad", "Angry", "Calm", "Anxious", "Depressed", "Excited", "Bored", "Tired",
                        "Energetic", "Confident", "Shy", "Kind", "Mean"],
            "height": ["Very Short", "Short", "Average", "Tall", "Very Tall"]
        },
    },
    "vehicle": {
        "negative_prompt": "(Poorly maintained exterior), (Uncomfortable interior), (Unreliable performance)",
        "weights": {
            "shape": 1.0,
            "vehicle": 1.0,
            "feature": 1.0,
            "window_color": 1.0,
            "wheel_type": 1.0,
            "engine_sound": 1.0,
            "color": 1.0
        },
        "builder": [
            {
                "text": "The "
            },
            {
                "text": "$vehicle ",
                "cond": "vehicle",
                "else": "vehicle "
            },
            {
                "text": "is $age ",
                "cond": "age"
            },
            {
                "text": "with $feature details, ",
                "cond": "feature"
            },
            {
                "text": "$window_color windows, ",
                "cond": "window_color"
            },
            {
                "text": "$wheel_type wheels, ",
                "cond": "wheel_type"
            },
            {
                "text": "$engine_sound engine sound, ",
                "cond": "engine_sound"
            },
            {
                "text": "driving with $speed. ",
                "cond": "speed"
            },
            {
                "text": "The $vehicle looks ",
                "cond": "vehicle",
                "else": "The vehicle looks "
            },
            {
                "text": "$emotion. ",
                "cond": "emotion",
                "else": "nice. "
            },
            {
                "text": "The $terrain is ",
                "cond": "terrain",
                "else": "The terrain is "
            },
            {
                "text": "$weather ",
                "cond": "weather"
            },
            {
                "text": "at $time, ",
                "cond": "time"
            },
            {
                "text": "picturesque backdrop, dynamic perspective, captured in action, a thrilling moment."
            }
        ],
        "variables": {
            "shape": [
                "circle", "square", "triangle", "rectangle", "pentagon", "hexagon", "octagon", "star", "heart",
                "diamond", "oval", "crescent", "cross", "spiral", "arrow", "parallelogram", "trapezoid",
                "rhombus", "semicircle", "sphere", "cube", "cylinder", "cone", "pyramid", "torus", "ellipsoid",
                "tetrahedron", "dodecahedron", "icosahedron", "trapezium", "heptagon", "decagon", "nonagon",
                "annulus", "spheroid", "quadrilateral", "arrowhead", "teardrop", "cog", "frustum", "oval",
                "oblong", "kite", "arc", "wave", "clover", "pentagram", "hexagram"
            ],
            "vehicle": [
                "car", "motorcycle", "bicycle", "truck", "bus", "van", "scooter", "boat", "yacht", "ship",
                "airplane", "helicopter", "train", "subway", "tram", "gondola", "hot air balloon", "jet ski",
                "sailboat", "canoe", "raft", "hovercraft", "tractor", "forklift", "ambulance", "fire truck",
                "police car", "taxi", "limousine", "RV", "motorhome", "segway", "skateboard", "snowmobile",
                "golf cart", "rickshaw", "bulldozer", "excavator", "ambulance", "fire engine", "cruise ship",
                "tanker", "spaceship", "hoverboard", "hang glider", "dirt bike", "monster truck", "dump truck",
                "bicycle"
            ],
            "feature": [
                "sleek design", "streamlined body", "chrome accents", "dual exhaust", "LED headlights",
                "sporty spoiler", "panoramic sunroof", "alloy wheels", "tinted windows",
                "aggressive front grille", "fog lights", "roof rack", "powerful engine", "rearview camera",
                "touchscreen display", "keyless entry", "premium sound system", "leather seats",
                "heated steering wheel", "adaptive cruise control", "lane departure warning", "parking sensors",
                "smartphone integration", "voice command system", "dual-zone climate control", "memory seats",
                "collision avoidance system", "blind spot monitoring", "remote start", "360-degree camera",
                "power tailgate", "navigation system", "adaptive headlights", "wireless charging",
                "auto-dimming mirrors", "rain-sensing wipers", "ambient lighting", "rear entertainment system",
                "massaging seats", "head-up display", "smart key system", "powered seats",
                "intelligent safety features", "fuel-efficient engine", "eco-friendly technology",
                "advanced suspension system"
            ],
            "window_color": [
                "clear", "transparent", "tinted", "smoked", "frosted", "stained", "reflective", "opaque",
                "matte", "iridescent", "dual-pane", "low-E coated", "bronze", "silver", "blue", "green",
                "gray", "black", "white", "golden", "rose-tinted", "aquamarine", "violet", "copper",
                "amber", "ruby", "sapphire", "emerald", "opal", "pearlescent", "topaz", "teal",
                "crystal clear", "crimson", "charcoal", "turquoise", "ivory", "platinum", "champagne",
                "sunlit", "pastel", "translucent", "prismatic", "dichroic", "rainbow-hued", "smoky"
            ],
            "wheel_type": [
                "steel", "alloy", "chrome", "spoke", "mag", "forged", "multi-spoke", "mesh", "deep dish",
                "split-spoke", "five-spoke", "ten-spoke", "turbine", "blade", "twisted", "directional",
                "concave", "dished", "beadlock", "lace", "knock-off", "wire", "carbon fiber", "hollow",
                "track-ready", "lightweight", "aero", "racing", "off-road", "forged monoblock",
                "forged three-piece", "forged two-piece", "flow-formed", "staggered", "painted", "polished",
                "machined", "diamond-cut", "gunmetal", "bronze", "matte black", "silver", "gold",
                "hyper silver", "hyper black", "anthracite", "copper", "graphite"
            ],
            "engine_sound": [
                "roaring", "rumbling", "purring", "growling", "thunderous", "revving", "screaming",
                "whirring", "vibrant", "powerful", "throaty", "grumbling", "hissing", "burbling",
                "crackling", "sizzling", "snarling", "whining", "racing", "throbbing", "bellowing",
                "howling", "buzzing", "humming", "whistling", "popping", "chugging", "sputtering",
                "stuttering", "murmuring", "droning", "snorting", "swooshing", "pneumatic", "exhilarating",
                "deafening", "mesmerizing", "thumping", "clattering", "fizzing", "booming", "clicking",
                "rattling", "gurgling", "squealing", "yowling", "sizzling", "rustling"
            ],
            "color": [
                "red", "orange", "yellow", "green", "blue", "purple", "pink", "brown",
                "black", "white", "gray"
            ]
        },
    }
}

variable_bootstrap_data = {
    "time": ["morning", "afternoon", "evening", "night"],
    "emotion": ["happy", "sad", "angry", "surprised", "disgusted", "scared", "neutral", "confused", "bored",
                "excited", "tired", "calm", "relaxed", "energetic", "stressed", "anxious", "depressed",
                "lonely", "jealous", "proud", "ashamed", "guilty", "embarrassed", "shy", "hopeful",
                "disappointed", "satisfied", "pessimistic", "optimistic", "nostalgic", "amused", "bored",
                "curious", "determined", "frustrated", "grateful"],
    "location": ["train station", "airport", "beach", "mountain", "park", "forest", "desert", "countryside",
                 "city center", "residential area", "office building", "school", "library", "hospital",
                 "shopping mall", "restaurant", "coffee shop", "bar", "nightclub", "hotel", "museum", "gallery",
                 "theater", "stadium", "amusement park", "zoo", "farm", "harbor", "riverbank", "lake", "bridge",
                 "cave", "island", "waterfall", "ruins", "church", "temple", "mosque", "synagogue", "castle",
                 "palace", "marketplace", "subway station", "bus stop", "train tracks", "campsite", "campus",
                 "skyscraper", "wind farm", "power plant", "construction site", "warehouse", "jungle",
                 "cemetery", "underground tunnel", "volcano", "lighthouse", "observatory", "prison", "garden",
                 "carnival", "farmhouse", "vineyard", "race track", "skate park", "cemetery", "mine",
                 "golf course", "ski resort", "apartment building", "factory", "quarry", "pier", "aquarium",
                 "planetarium", "radio tower", "water tower", "playground", "gas station", "highway",
                 "cruise ship", "helipad", "space station", "junkyard", "wasteland", "island resort",
                 "floating market", "train yard", "bamboo forest", "coral reef", "football stadium",
                 "racecourse", "seaside cliffs", "gondola", "prairie", "hot air balloon", "windmill", "outback",
                 "carnival", "fairground", "deserted island", "lakeside cabin", "abandoned factory",
                 "boardwalk", "bamboo grove", "fishing village", "iceberg", "garden maze", "beachside villa",
                 "snowy village", "castle ruins", "cottage", "waterfront", "oasis", "treehouse",
                 "floating island", "cliffside village", "shipwreck", "lighthouse", "tropical rainforest",
                 "cave dwelling", "apartment balcony", "suspension bridge", "ancient temple", "skydiving",
                 "paragliding", "ice cave", "glacier", "board game cafe", "gymnasium", "skating rink",
                 "school bus", "bookstore", "vintage shop", "street market", "rooftop garden", "rooftop bar",
                 "tea plantation", "rice terrace", "night market", "food court"],
    "artist": [
        "van gogh", "picasso", "monet", "da vinci", "michelangelo", "rembrandt", "renoir", "degas", "cezanne",
        "gauguin", "munch", "klimt", "kandinsky", "matisse", "botticelli", "vermeer", "seurat", "caravaggio",
        "tony moore", "alex ross", "bob ross", "jim lee", "frank miller", "joe madureira", "scott campbell"
    ],
    "cities": [
        "New York", "Los Angeles", "Chicago", "Houston", "Phoenix", "Philadelphia", "San Antonio",
        "San Diego", "Dallas", "San Jose", "Austin", "Jacksonville", "San Francisco", "Columbus",
        "Fort Worth", "Indianapolis", "Charlotte", "Seattle", "Denver", "Washington", "Boston", "El Paso",
        "Detroit", "Nashville", "Portland", "Memphis", "Oklahoma City", "Las Vegas", "Louisville",
        "Baltimore", "Milwaukee", "Albuquerque", "Tucson", "Fresno", "Sacramento", "Mesa", "Kansas City",
        "Atlanta", "Long Beach", "Colorado Springs", "Raleigh", "Miami", "Virginia Beach", "Omaha",
        "Oakland", "Minneapolis", "Tulsa", "Arlington", "New Orleans", "Wichita", "Cleveland", "Tampa",
        "Bakersfield", "Aurora", "Honolulu", "Anaheim", "Santa Ana", "Corpus Christi", "Riverside",
        "St. Louis", "Lexington", "Stockton", "Pittsburgh", "Anchorage", "Cincinnati", "Saint Paul",
        "Greensboro", "Toledo", "Newark", "Plano", "Henderson", "Lincoln", "Orlando", "Jersey City",
        "Chula Vista", "Buffalo", "Fort Wayne", "Chandler", "St. Petersburg", "Laredo", "Durham", "Irvine",
        "Madison", "Norfolk", "Lubbock", "Gilbert", "Winston–Salem", "Glendale", "Reno", "Hialeah",
        "Garland", "Chesapeake", "Irving", "North Las Vegas", "Scottsdale", "Baton Rouge", "Fremont",
        "Richmond", "Boise", "San Bernardino"],
    "mediums": ["oil", "acrylic", "watercolor", "pencil", "charcoal", "ink", "pastel"],
    "image_subjects": ["landscape", "portrait", "still life", "abstract"],
    "male_name": ["Liam", "Noah", "Oliver", "William", "Elijah", "James", "Benjamin", "Lucas", "Henry", "Alexander",
                  "Michael", "Daniel", "Matthew", "Joseph", "David", "Andrew", "Jackson", "Anthony", "Joshua",
                  "Christopher"],
    "female_name": ["Emma", "Olivia", "Ava", "Isabella", "Sophia", "Mia", "Charlotte", "Amelia", "Harper", "Evelyn",
                    "Abigail", "Emily", "Elizabeth", "Sofia", "Avery", "Ella", "Scarlett", "Grace", "Chloe",
                    "Victoria"],
    "background": ["mountain range", "city skyline", "beach", "forest", "meadow", "desert", "ocean", "sunset",
                   "night sky", "countryside", "waterfall", "urban street", "winter landscape", "tropical island",
                   "country road", "historic building", "skyline", "farmland", "coastline", "jungle", "lake",
                   "autumn foliage", "starlit sky", "village", "snow-capped peaks", "safari", "ruins", "garden",
                   "cliffside", "park", "canyon", "river", "sunrise", "cottage", "pasture", "volcano", "island",
                   "valley", "underwater", "sky", "prairie", "castle", "moorland", "glacier"],
    "weather": ["sunny", "cloudy", "rainy", "snowy", "windy"],
    "eye_color": ["brown", "blue", "green", "hazel", "gray"],
    "composition_category": [
        "animal",
        "architecture",
        "food",
        "person",
        "vehicle"
    ],
    "composition_color": ["colorful", "black and white", "monochromatic", "sepia", "grayscale", "pastel", "neon",
                          "vibrant", "muted", "dark", "light", "warm", "cool", "bright", "pale", "bold", "subtle",
                          "contrasting", "complementary", "analogous", "triadic", "split-complementary",
                          "monochromatic", "tetradic", "square", "rectangular", "triangular", "circular", "linear",
                          "diagonal", "horizontal", "vertical", "asymmetrical", "symmetrical", "radial", "geometric",
                          "organic", "minimalist", "busy", "simple", "complex", "detailed", "abstract", "realistic",
                          "cartoonish", "stylized", "gritty", "smooth", "textured", "flat", "layered", "collage",
                          "collaborative", "interactive", "immersive", "multimedia", "multidisciplinary",
                          "multisensory", "multifaceted", "multifunctional", "multifarious"],
    "composition_genre": ["modern", "traditional", "contemporary", "realistic", "abstract", "impressionist",
                          "expressionist", "surrealist", "cubist", "minimalist", "fauvist", "pointillist",
                          "post-impressionist", "post-modern", "baroque", "rococo", "romantic", "renaissance",
                          "neoclassical", "art nouveau", "art deco", "gothic", "classical", "acade"],
    "composition_style": [
        "realistic",
        "artistic",
        "cartoon",
        "illustration"
    ]
}

style_bootstrap_data = {
    "realistic": {
        "styles": [
            "photograph",
            "professional photograph",
            "amateur photograph",
            "candid photograph",
            "portrait",
            "street photography",
            "photo journalism",
            "cctv footage",
            "bodycam footage",
            "found footage",
            "grainy vhs footage",
            "claymation"
        ],
        "negative_prompt": "not real, cartoon, comic, illustration, anime, drawing, art, painting, cgi, bad facial features, indistinct facial features"
    },
    "artistic": {
        "styles": [
            "landscape",
            "still life",
            "painting",
            "mixed media",
            "sculpture",
            "drawing"
        ],
        "negative_prompt": "real, cartoon, comic, anime, cgi, photograph, real photo, picture, bad facial features, indistinct facial features"
    },
    "cartoon": {
        "styles": [
            "caricature drawing",
            "cartoon illustration",
            "anime illustration",
            "comic book illustration",
            "graphic novel illustration",
            "manga illustration",
            "cel animation",
            "digital animation"
        ],
        "negative_prompt": "real, painting, masterpiece, cgi, photograph, real photo, picture, bad facial features, indistinct facial features"
    },
    "illustration": {
        "styles": [
            "illustration",
            "digital art",
            "digital painting",
            "vector art",
            "pixel art",
            "concept art",
            "graphic design"
        ],
        "negative_prompt": "real, photograph, video, picture, real human, painting, cgi, bad facial features, indistinct facial features"
    }
}
