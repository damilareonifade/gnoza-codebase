# content/constants.py - Extracted constants for loose coupling

# ==========================================
# CATEGORY KEYWORDS (used by CategoryClassifier)
# ==========================================
CATEGORY_KEYWORDS = {
    "technology": [
        "tech", "software", "hardware", "ai", "artificial intelligence", "machine learning",
        "computer", "digital", "internet", "app", "smartphone", "robot", "cyber", "data",
        "cloud", "coding", "programming", "startup", "silicon valley", "gadget", "innovation",
        "apple", "google", "microsoft", "meta", "amazon", "tesla", "nvidia", "chip", "processor",
    ],
    "business": [
        "business", "company", "corporate", "market", "stock", "trade", "economy", "economic",
        "ceo", "executive", "profit", "revenue", "earnings", "investor", "investment", "merger",
        "acquisition", "entrepreneur", "sales", "retail", "consumer", "banking", "finance", "financial",
    ],
    "sport": [
        "sport", "football", "soccer", "basketball", "baseball", "tennis", "cricket", "hockey",
        "olympics", "game", "match", "player", "team", "league", "championship", "coach", "athlete",
        "tournament", "fifa", "nba", "nfl", "premier league", "goal", "score", "win", "defeat",
    ],
    "health": [
        "health", "medical", "medicine", "doctor", "hospital", "patient", "disease", "illness",
        "treatment", "cure", "vaccine", "drug", "pharmaceutical", "healthcare", "wellness", "fitness",
        "nutrition", "diet", "mental health", "therapy", "cancer", "diabetes", "virus", "infection",
    ],
    "science": [
        "science", "research", "study", "scientist", "discovery", "experiment", "laboratory",
        "physics", "chemistry", "biology", "astronomy", "space", "nasa", "universe", "planet",
        "climate", "environment", "nature", "species", "dna", "gene", "evolution", "quantum",
    ],
    "politics": [
        "politics", "political", "government", "president", "minister", "senator", "congress",
        "parliament", "election", "vote", "campaign", "policy", "law", "legislation", "democracy",
        "republican", "democrat", "party", "white house", "capitol", "senate", "diplomatic",
    ],
    "international": [
        "international", "global", "foreign", "world", "country", "embassy", "united nations",
        "conflict", "war", "peace", "treaty", "border", "refugee", "immigration", "crisis",
        "china", "russia", "europe", "asia", "africa", "middle east", "nato", "un",
    ],
    "national": [
        "national", "domestic", "local", "state", "city", "town", "community", "regional",
        "us", "america", "american", "federal", "governor", "mayor", "homeland",
    ],
    "lifestyle": [
        "lifestyle", "beauty", "food", "recipe", "cooking", "restaurant", "dining",
        "travel", "vacation", "hotel", "tourism", "home", "interior", "design", "garden", "pet",
        "relationship", "wedding", "parenting", "family", "entertainment", "movie", "music",
    ],
    "art": [
        "art", "artist", "painting", "sculpture", "gallery", "museum", "exhibition", "artwork",
        "contemporary art", "modern art", "auction", "masterpiece", "canvas", "portrait", "creative",
    ],
    "fashion": [
        "fashion", "style", "designer", "clothing", "apparel", "runway", "model", "vogue",
        "trend", "outfit", "haute couture", "brand", "luxury", "collection", "week",
    ],
}

# ==========================================
# IMAGE CATEGORY QUERIES (for stock photo APIs)
# ==========================================
IMAGE_CATEGORY_QUERIES = {
    "sports": "sports stadium athlete",
    "technology": "technology computer innovation",
    "politics": "government politics capitol",
    "business": "business office meeting",
    "entertainment": "entertainment concert performance",
    "science": "science laboratory research",
    "health": "health medical healthcare",
    "world": "world globe international",
    "africa": "africa landscape culture",
    "nigeria": "nigeria lagos culture",
    "default": "news newspaper information",
}

# ==========================================
# SOURCE CREDIBILITY TIERS
# ==========================================
SOURCE_TIERS = {
    "tier1": {
        "sources": [
            "bbc", "reuters", "associated press", "ap news", "the guardian",
            "new york times", "nyt", "washington post", "wall street journal", "wsj",
            "financial times", "ft.com", "the economist", "nature", "science", "lancet",
            "bloomberg", "cnbc", "forbes",
        ],
        "score": 0.95,
    },
    "tier2": {
        "sources": [
            "cnn", "fox news", "techcrunch", "wired", "the verge", "ars technica",
            "npr", "pbs", "al jazeera", "aljazeera", "times of india",
            "punch", "vanguard", "premium times", "channels tv", "daily trust",
            "guardian nigeria", "thisday", "leadership", "the nation",
        ],
        "score": 0.80,
    },
    "tier3": {
        "sources": [
            "the football faithful", "sb nation", "espn", "sky sports",
            "fortune", "business insider", "marketwatch", "seeking alpha",
            "psypost", "sciencedaily", "phys.org",
        ],
        "score": 0.70,
    },
    "tier4": {
        "sources": ["reddit", "youtube", "twitter", "facebook"],
        "score": 0.65,
    },
}

SOURCE_TYPE_SCORES = {
    "newsapi": 0.75,
    "guardian": 0.75,
    "rss": 0.75,
    "gemini": 0.75,
    "youtube": 0.65,
    "reddit": 0.65,
}

# ==========================================
# YOUTUBE CHANNEL MAP
# ==========================================
YOUTUBE_CHANNEL_MAP = {
    "technology": [
        "UCXuqSBlHAE6Xw-yeJA0Tunw",  # Linus Tech Tips
        "UCBJycsmduvYEL83R_U4_riQ",  # MKBHD
        "UCMiJRAwDNSNzuYeN2uWa0pA",  # Mrwhosetheboss
        "UCtinbF-Q-fVthA0qrFQTgXQ",  # Unbox Therapy
        "UCsTcErHg8oDvUnTzoixD2nQ",  # Austin Evans
        "UCeeF0aO5G7u5d9V4hLAZ0qw",  # Dave2D
        "UCXGgr3Nh8r3WmVanvdGfnMw",  # The Verge
        "UCOmcA3f_RrH6b9NmcNa4bqg",  # CNET
        "UCBa659QWEk1AI4wT56bhtEQ",  # Jonathan Morrison
        "UC6nSFpj9HTCZ5twv8QssACg",  # iJustine
        "UCddiUEpeqJcYeBxX1IVBKvQ",  # JerryRigEverything
        "UCq6VFHwMzcMXbOle2fw1WKw",  # MrMobile
        "UCVYamHliCI9rw1tHR1NbTPQ",  # ShortCircuit
        "UCkHvGfN2qceimG4d8kF9uRw",  # TechChap
        "UCl2mFZoRqjw_ELax4Yisf6w",  # Louis Rossmann
        "UC7YOGHUfC1Tb6E4pudI9STA",  # Mental Outlaw
        "UCbiGcwDWZjz05njNPrJU7jA",  # Snazzy Labs
        "UCRBGZKSdgFYAB7mPVuM9JQQ",  # Hardware Canucks
        "UC2eYFnH61tmytImy1mTYvhA",  # Luke Miani
        "UCXQc4OtNa2ApVYGjKJD1z_A",  # TechSource
    ],
    "science": [
        "UCsXVk37bltHxD1rDPwtNM8Q",  # Kurzgesagt
        "UCHnyfMqiRRG1u-2MsSQLbXA",  # Veritasium
        "UC6nSFpj9HTCZ5t-N3Rm3-HA",  # Vsauce
        "UCZYTClx2T1of7BRZ86-8fow",  # SciShow
        "UCtESv1e7ntJaLJYKIO1FoYw",  # Real Science
        "UC9-y-6csu5WGm29I7JiwpnA",  # Computerphile
        "UC2C_jShtL725hvbm1arSV9w",  # CGP Grey
        "UCBbnbBWJtwsf0jLGUwX5Q3g",  # NASA
        "UCsooa4yRKGN_zEE8iknghZA",  # TED-Ed
        "UCUHW94eEFW7hkUMVaZz4eDg",  # minutephysics
        "UCYO_jab_esuFRV4b17AJtAw",  # 3Blue1Brown
        "UC6107grRI4m0o2-emgoDnAA",  # SmarterEveryDay
        "UCivA7_KLKWo43tFcCkFvydw",  # Physics Girl
        "UCR1IuLEqb6UEA_zQ81kwXfg",  # Real Engineering
        "UCdBK94H6oZT2Q7l0-b0xmMg",  # Nerdwriter1
    ],
    "business_finance": [
        "UCIALMKvObZNtJ6AmdCLP7Lg",  # Bloomberg Television
        "UCfe_znKY1ukrqlGActlFmaQ",  # Financial Times
        "UCK7tptUDHh-RYDsdxO1-5QQ",  # Wall Street Journal
        "UCEAZeUIeJs0IjQiqTCdVSIg",  # Yahoo Finance
        "UCV6KDgJskWaEckne5aPA0aQ",  # Graham Stephan
        "UCnMn36GT_H0X-w5_ckLtlgQ",  # Meet Kevin
        "UCGP7NY2i__OBKhcJOkJT2Yw",  # Minority Mindset
        "UC8wZnXYK_CGKlBcZp-GxYPA",  # Andrei Jikh
        "UCfMJ2MchTzic11ACzpKED8Q",  # Ryan Scribner
        "UCVS1r-fmPj8WnYfqrJfp2KA",  # Everything Money
        "UCqK8ko0a6jevIc0dV2dTUjQ",  # CNBC Television
        "UCcO9mGJEPYXSWJKyxbvpWMQ",  # The Plain Bagel
        "UCnzjNfDBh3o4qNCb5Vr6BLQ",  # Alux.com
    ],
    "sports": [
        "UCiWLfSweyRNmLpgEHekhoAg",  # ESPN
        "UCWJ2lWNubArHWmf3FIHbfcQ",  # NBA
        "UCG5qGWdu8nIRZqJ_GgDwQ-w",  # Premier League
        "UCBJeMCIeLQos7wacox4hmLQ",  # Sky Sports Football
        "UCB_qr75-ydFVKSF9Dmo6izg",  # Formula 1
        "UC_0CVCfC_3iuCGvrFbPG9DA",  # NFL
        "UCpHZDNukgUyHBchSotfNGIA",  # NFL UK
        "UCvIyqfpPNp2P-qbmD7i-r6A",  # SkySportsNews
        "UCN3KhfpyaM4SURm0_mhDfcw",  # BT Sport
        "UCZS46xnQkN1BuaGwQf8v4CQ",  # LaLiga
        "UC-5vLTY9hrA13mDDt70VZHw",  # UEFA Champions League
        "UCQ7YHk_y_wqREw3iZ9rXI_A",  # FIFA
        "UCjbp04NgAOQ4-tZ0C4xLR7g",  # WWE
        "UCEzDdNqNkT-7rSfSGSr1hWg",  # UFC
        "UCGz6SN8i4x9LjBuE6XN4Pkw",  # Bleacher Report
    ],
    "lifestyle": [
        "UC78cxCAcp7JfQPgKxYdyGrg",  # Emma Chamberlain
        "UCIJwWYOfsCfz6PjxbONYXSg",  # Blogilates
        "UCpQ34afVgk8cRQBjSJ1xuJQ",  # MadFit
        "UCehUd77lCxVA1WXSh_xPgIQ",  # Jubilee
        "UC0v-tlzsn0QZwJnkiaUSJVQ",  # Yes Theory
        "UCEgdi0XIXXZ-qJOFPf4JSKw",  # Sports Illustrated Swimsuit
        "UC1usFRN4LCMcfIV7UjHNuQg",  # Naomi Campbell
        "UC295-Dw_tDNtZXFeAPAW6Aw",  # GQ
        "UCL7IHDMCW1w6vHFBe4FnGyg",  # Vogue
        "UCs4gx-MpC5tJfONTuoVTFLg",  # Cut
        "UCWegIHpJ16_oG-9eqMOUF6A",  # Matt D'Avella
        "UCNCTxLq1V8xjpnbCrw0cClQ",  # Pick Up Limes
    ],
    "entertainment": [
        "UCVtFOytbRpEvzLjvqGG5gxQ",  # Sidemen
        "UC-lHJZR3Gqxm24_Vd_AJ5Yw",  # PewDiePie
        "UCX6OQ3DkcsbYNE6H8uQQuVA",  # MrBeast
        "UCANLZYMidaCbLQFWXBC95Jg",  # jacksepticeye
        "UCkQX1tChV7lrewriPhf2g1Q",  # h3h3Productions
        "UCpko_-a4wgz2u_DgDgd9fqA",  # penguinz0
        "UC4USoIAL9qcsx5nCZV_QRnA",  # Saturday Night Live
        "UC8-Th83bH_thdKZDJCrn88g",  # The Tonight Show
        "UCi7GJNg51C3jgmYTUwqoUXA",  # The Late Show
        "UC9CoTjkIYi9p-LFWWhbFAYQ",  # Good Mythical Morning
        "UCtxJFU9DgUhfr2J2bMjYILQ",  # Dude Perfect
        "UCkvK_5omS-42Ovgah8KRKtg",  # Smosh
        "UCchi-5eddfXajKmUqD5o6-lQ",  # Rhett & Link
        "UCrBJLYi0_QjjlhyEWYYL_Zw",  # The Try Guys
        "UCCsj3Uk-cuVQejdoX-Pc_Lg",  # Viva La Dirt League
    ],
    "music": [
        "UCkBV3nBa0iRdxEGc4DUS3xA",  # Davido
        "UCq7NZGQeoH4K5eVU2z0oY3g",  # Wizkid
        "UCHGF6zfD2gwLuke95X3CKFQ",  # Rema
        "UCmK7CRsQX_Rwa5BHxpeKNtg",  # Ayra Starr
        "UCg8Uo1sSx0Q2a6a_R6taDYA",  # Tems
        "UCnz8toDw0rMZQXiS-0dykDg",  # Asake
        "UC-OazvvKjKfFsQzl0IxCj6w",  # Olamide
        "UCAI5rW1yFqK0UQh6M8Q07gA",  # Taylor Swift
        "UCOmHUn--16B90oW2L6FRR3A",  # BLACKPINK
        "UC4fjYmxtvPFm9FYUw7_UWOA",  # Ed Sheeran
        "UCedvOgsKFzcK3hA5taf3KoQ",  # Billie Eilish
        "UC-Q02NnqnJHKxB5A-BDrLeQ",  # Dua Lipa
        "UC2pmfLm7iq6Ov1UwYrWYkZA",  # The Weeknd
        "UCN1hnUccO4FD5WfM7ithXaw",  # BTS
        "UCnxQ8o9RpqxGF2oLHcCn9VQ",  # Justin Bieber
        "UCZkURf9tDolFSgx4VXGPNBA",  # Drake
        "UCtGY2wqU5u7qY7lgORIolhA",  # Post Malone
    ],
    "health": [
        "UCP6HGa63vWi8K5LkwLlO9Hg",  # Dr. Eric Berg DC
        "UCFKE7WVJfvaHW5q283SxchA",  # Yoga With Adriene
        "UCIJwWYOfsCfz6PjxbONYXSg",  # Blogilates
        "UCpQ34afVgk8cRQBjSJ1xuJQ",  # MadFit
        "UCe0TLA0EsQbE-MjuHXevj2A",  # ATHLEAN-X
        "UChVRfsT_ASBZk10o0An7Ucg",  # FitnessBlender
        "UC2o_PCDDZePRWJAVj1IQwhw",  # Chloe Ting
        "UCDtWjqBgJu_G2p9MWKyq7sA",  # Pamela Reif
        "UCAxW1XT0iEJo0TYlRfn6rYQ",  # Thomas DeLauer
        "UCwMzXcsHG9GJbJZqHQP-kTw",  # Dr. Mike
        "UC6wBxaVWRCd9BxODZBYI_Aw",  # BRIGHT SIDE
        "UCqe0WvZufWMDqLpgT-PaHmQ",  # HASfit
        "UCIhYqKpxEHF5Y0HtlG7gQIQ",  # HealthyGamerGG
        "UC0mRARWl9kCYHvdJ8xvBzGQ",  # What I've Learned
    ],
    "world_news": [
        "UC16niRr50-MSBwiO3YDb3RA",  # BBC News
        "UCNye-wNBqNL5ZzHSJj3l8Bg",  # Al Jazeera English
        "UCknLrEdhRCp1aegoMqRaCZg",  # DW News
        "UC-8Q-hLdECwQmaWNwXitYDw",  # NBC News
        "UCeY0bbntWzzVIaj2z3QigXg",  # NBC News
        "UCupvZG-5ko_eiXAupbDfxWw",  # CNN
        "UCaXkIU1QidjPwiAYu6GcHjg",  # MSNBC
        "UCoMdktPbSTixAyNGwb-UYkQ",  # Sky News
        "UCqnbDFdCpuN8CMEg0VuEBqA",  # ABC News
        "UCHpw8xwDNhU9gdohEcJu4aA",  # Times of India
        "UCrwPV1HjgGgJVTsePQX_Axw",  # WION
    ],
    "nigeria_sports": [
        "UCcxDWBD0LUq0uKqNxwh3y-w",  # Complete Sports Nigeria
        "UCwxgnDON02BFKmwyDyTRPDQ",  # Brila.net
        "UCd-xKjOGVDiowlEhePbXE0g",  # Goal Nigeria
        "UCY6w_Y-_0YSPC7rXpYLUFhw",  # SportsGrid Nigeria
        "UC5UAwBUum7CPN5buc-_N1Fw",  # Pulse Sports
        "UCXzPqULS5DPcHrWf4d6zrQg",  # ESPN Africa
        "UCvIyqfpPNp2P-qbmD7i-r6A",  # SuperSport
        "UCQbp0sZwyLx8iE1LD4Qpaog",  # Nigeria Football Federation
    ],
    "nigeria": [
        "UCoUM-UJ7v1yoTOWHVYpzLvw",  # MarkAngelComedy
        "UCG6orNVuXIICv9_ifH6msIA",  # Broda Shaggi
        "UCxyb0darxVM-h7I4xYWrb4A",  # Brain Jotter
        "UCxAkiUiL3KnMl0BIFBv6xxA",  # Mr Macaroni
        "UCvG_RH3tAekGN5rPUVUmcIg",  # Taaooma
        "UCkBV3nBa0iRdxEGc4DUS3xA",  # Davido
        "UCq7NZGQeoH4K5eVU2z0oY3g",  # Wizkid
        "UC-S4gWR1dqQ5ot1f5_JCYvg",  # Sydney Talker
        "UCwOi8DgFOXGzqmT6AwDV1Tg",  # Lasisi Elenu
        "UCLwL73xHM7Wm9HJyg_PFHEA",  # Xploit Comedy
        "UCPmZKoYyg45b8OVMKvMbPvQ",  # Sir Balo
        "UCfQwnF92vdWq16HfnP-fVXQ",  # MC Lively
        "UCYvLqKmXqg_bUQxMk0XbCAQ",  # Maraji
        "UCkWE4rJHQs1Y9qoR8rqGdGw",  # Sabinus
        "UCKEt6VTKRpQ6hKJZZZqKqwg",  # Nasty Blaq
        "UC2fFLRNdZg5_BU8JqBiMd4g",  # Broda Shaggi Music
        "UCqp-6qVbVpg-WZQkxBCDvqA",  # Remote TV
        "UC8-F68N3A3q_4MXyqUqj_Gw",  # Channels TV
    ],
    "uk": [
        "UCVtFOytbRpEvzLjvqGG5gxQ",  # Sidemen
        "UCBJeMCIeLQos7wacox4hmLQ",  # Sky Sports
        "UCMiJRAwDNSNzuYeN2uWa0pA",  # Mrwhosetheboss
        "UCqFzWxSCi39LnW1JKFR3efg",  # KSI
        "UCCij6ulN4b_gyYTOrnj7R8w",  # Miniminter
        "UC7lk7G5cZ6Hgo0GQQJvXp6g",  # TommyInnit
        "UCoMdktPbSTixAyNGwb-UYkQ",  # Sky News
        "UC3IZKseVpdzPSBaWxBxundA",  # BBC
        "UCq-Fj5jknLsUf-MWSy4_brA",  # Tom Scott
        "UCvBqzzvUBLCs8Y7Axb-jZew",  # The Royal Family Channel
        "UCmGSJVG3mCRXVOP4yZrU1Dw",  # Johnny Harris
    ],
    "us": [
        "UCWJ2lWNubArHWmf3FIHbfcQ",  # NBA
        "UC78cxCAcp7JfQPgKxYdyGrg",  # Emma Chamberlain
        "UCP6HGa63vWi8K5LkwLlO9Hg",  # Dr. Eric Berg
        "UCtxJFU9DgUhfr2J2bMjYILQ",  # Dude Perfect
        "UCX6OQ3DkcsbYNE6H8uQQuVA",  # MrBeast
        "UCuAXFkgsw1L7xaCfnd5JJOw",  # Rick Beato
        "UC8-Th83bH_thdKZDJCrn88g",  # The Tonight Show
        "UCi7GJNg51C3jgmYTUwqoUXA",  # The Late Show
        "UC4USoIAL9qcsx5nCZV_QRnA",  # Saturday Night Live
        "UCupvZG-5ko_eiXAupbDfxWw",  # CNN
        "UCeY0bbntWzzVIaj2z3QigXg",  # NBC News
        "UCaXkIU1QidjPwiAYu6GcHjg",  # MSNBC
        "UCBJycsmduvYEL83R_U4_riQ",  # MKBHD
        "UCXuqSBlHAE6Xw-yeJA0Tunw",  # Linus Tech Tips
    ],
}

# Maps user topic preferences → YouTube channel group keys
TOPIC_TO_CHANNEL_KEYS = {
    "technology": ["technology"],
    "sport": ["sports", "nigeria_sports"],
    "sports": ["sports", "nigeria_sports"],
    "lifestyle": ["lifestyle", "entertainment"],
    "business": ["business_finance"],
    "health": ["health"],
    "fashion": ["lifestyle", "entertainment"],
    "science": ["science"],
    "art": ["entertainment", "music"],
    "politics": ["world_news"],
    "national": ["nigeria", "us", "uk"],
    "international": ["world_news", "uk", "us"],
    "entertainment": ["entertainment"],
    "music": ["music"],
    "finance": ["business_finance"],
    "travel": ["lifestyle"],
    "world": ["world_news", "uk", "us"],
    "local": ["nigeria", "us", "uk"],
    "nation": ["nigeria", "us", "uk"],
}

# ==========================================
# TICKETMASTER LOCATION MAPPING
# ==========================================
TICKETMASTER_PRIORITY_COUNTRIES = ["NG", "GH", "KE", "ZA", "TZ", "UG", "SN", "CI"]
TICKETMASTER_FALLBACK_COUNTRIES = ["US", "GB", "CA", "DE", "FR"]

TICKETMASTER_LOCATION_MAP = {
    "Nigeria": "NG", "Lagos": "NG", "Abuja": "NG", "Port Harcourt": "NG",
    "Ghana": "GH", "Accra": "GH",
    "Kenya": "KE", "Nairobi": "KE",
    "South Africa": "ZA", "Johannesburg": "ZA", "Cape Town": "ZA",
    "Tanzania": "TZ", "Dar es Salaam": "TZ",
    "Uganda": "UG", "Kampala": "UG",
    "Senegal": "SN", "Dakar": "SN",
    "Ivory Coast": "CI", "Abidjan": "CI",
    "United Kingdom": "GB", "London": "GB",
    "United States": "US", "New York": "US", "Los Angeles": "US",
}

# ==========================================
# NIGERIAN EVENT SCRAPING SITES
# ==========================================
NIGERIAN_EVENT_SITES = [
    {
        "name": "shows_ng",
        "url": "https://shows.ng/events",
        "source": "shows_ng",
        "selectors": [
            "div.event-card", "div.show-card", "article.event",
            "div[class*='event']", "a[href*='/event/']",
        ],
    },
    {
        "name": "tix_africa",
        "url": "https://tix.africa/discover",
        "source": "tix_africa",
        "selectors": [
            "div.event-card", "div.discover-card", "article.event",
            "div[class*='event']", "a[href*='/event/']",
        ],
    },
    {
        "name": "ariiya",
        "url": "https://www.ariiyatickets.com/events/",
        "source": "ariiyatickets",
        "selectors": [
            "div.event-item", "div.event-card", "article.event",
            "div.tribe-events-list-event", "a[href*='/event/']",
        ],
    },
    {
        "name": "tickethub",
        "url": "https://tickethub.ng/",
        "source": "tickethub_ng",
        "selectors": [
            "div.event-card", "div.event-item", "article.event",
            "div[class*='event']", "a[href*='/event/']",
        ],
    },
]

# Default topics for content fetching
DEFAULT_TOPICS = [
    "Nigeria politics today",
    "West Africa economy news",
    "African tech startups",
    "Nigeria elections update",
    "Climate change Africa",
    "Nigerian entertainment news",
    "ECOWAS latest news",
    "African Union developments",
    "Nigeria security situation",
    "Global news affecting Nigeria",
]

EVENTBRITE_DEFAULT_LOCATIONS = [
    "nigeria--lagos", "nigeria--abuja", "nigeria",
    "ghana--accra", "kenya--nairobi", "south-africa--johannesburg",
]
