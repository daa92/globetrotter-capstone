"""
app/cameroon_places_seed.py

A curated list of real, well-documented Cameroon destinations — cross-
checked against multiple current travel sources (Lonely Planet, Trip
Master, educba.com, thecrazytourist.com, and others) as of Aug 2026, not
invented. Coordinates are landmark/town-level accuracy from general
geography, not GPS-survey precision — good enough for a travel app to
place a pin and compute rough directions, but an admin should spot-check
before treating these as authoritative for, say, a hiking trailhead.

Deliberately conservative on `avg_cost_fcfa`: left as None wherever I
don't have a real, current figure to point to, rather than inventing one
— "respect the description" means not fabricating numbers either.
`description` here is a short, factual seed; the import script tries
Wikipedia first via app/enrichment.py and only falls back to this text
if Wikipedia has nothing for that exact place.

This is a starting catalogue, not exhaustive — OpenTripMap's bbox/radius
search (once OPENTRIPMAP_API_KEY is set) can surface many more POIs
automatically around these same coordinates; this list is the reliable
"skeleton" of well-known places to seed first.
"""

PLACES = [
    # --- Coastal / beaches ---
    {"name": "Kribi", "region": "South", "tags": ["beach", "relaxation", "food"], "latitude": 2.9394, "longitude": 9.9101,
     "description": "A coastal town in southern Cameroon known for its fine sandy beaches along the Atlantic and fresh seafood."},
    {"name": "Chutes de la Lobé", "region": "South", "tags": ["waterfall", "nature", "photography"], "latitude": 2.8814, "longitude": 9.8996,
     "description": "One of the few waterfalls in the world that empties directly into the ocean, a few kilometers south of Kribi."},
    {"name": "Grand Batanga Beach", "region": "South", "tags": ["beach", "relaxation"], "latitude": 2.8500, "longitude": 9.8700,
     "description": "A quieter beach south of Kribi, largely untouched by mass tourism."},
    {"name": "Limbe", "region": "Southwest", "tags": ["beach", "nature", "wildlife"], "latitude": 4.0163, "longitude": 9.2136,
     "description": "A coastal town known for black volcanic-sand beaches, with Mount Cameroon rising behind the Atlantic."},
    {"name": "Limbe Wildlife Centre", "region": "Southwest", "tags": ["wildlife", "eco-tourism"], "latitude": 4.0180, "longitude": 9.2150,
     "description": "A primate rescue and rehabilitation centre in Limbe, focused on chimpanzees, gorillas, and drills."},
    {"name": "Bimbia Historical Site", "region": "Southwest", "tags": ["history", "culture"], "latitude": 3.9700, "longitude": 9.2050,
     "description": "A former slave-trade port near Limbe, now a heritage site documenting that history."},

    # --- Mountains / hiking ---
    {"name": "Mount Cameroon", "region": "Southwest", "tags": ["mountain", "hiking", "adventure"], "latitude": 4.2140, "longitude": 9.1710,
     "description": "West Africa's highest peak (4,095m), an active volcano near Limbe popular for guided multi-day hikes."},
    {"name": "Rhumsiki", "region": "Far North", "tags": ["mountain", "scenery", "photography"], "latitude": 10.9667, "longitude": 13.7333,
     "description": "A village in the Mandara Mountains known for its dramatic volcanic rock spires and panoramic views."},
    {"name": "Bamenda Highlands", "region": "Northwest", "tags": ["mountain", "scenery", "culture"], "latitude": 5.9631, "longitude": 10.1591,
     "description": "Rolling highlands with waterfalls and traditional villages, home to the Kom and Bafut peoples."},

    # --- National parks / wildlife ---
    {"name": "Waza National Park", "region": "Far North", "tags": ["wildlife", "adventure", "nature"], "latitude": 11.1667, "longitude": 14.6000,
     "description": "One of Cameroon's premier wildlife parks, home to elephants, lions, giraffes, and antelope."},
    {"name": "Korup National Park", "region": "Southwest", "tags": ["rainforest", "wildlife", "eco-tourism"], "latitude": 5.2000, "longitude": 8.8500,
     "description": "One of Africa's oldest rainforests, spanning 126,000 hectares with well-marked trails and rich birdlife."},
    {"name": "Dja Faunal Reserve", "region": "South", "tags": ["rainforest", "wildlife", "eco-tourism"], "latitude": 3.2000, "longitude": 12.7500,
     "description": "A UNESCO World Heritage rainforest reserve, home to gorillas, chimpanzees, and elephants."},
    {"name": "Campo Ma'an National Park", "region": "South", "tags": ["rainforest", "wildlife", "nature"], "latitude": 2.3667, "longitude": 10.1000,
     "description": "A coastal-forest national park in southern Cameroon, preserving mangrove swamps and rainforest."},
    {"name": "Mefou National Park", "region": "Centre", "tags": ["wildlife", "eco-tourism"], "latitude": 3.6500, "longitude": 11.4667,
     "description": "Home to the Mefou Primate Sanctuary run by Ape Action Africa, caring for rescued endangered primates."},
    {"name": "Lake Ossa Wildlife Reserve", "region": "Littoral", "tags": ["nature", "wildlife", "eco-tourism"], "latitude": 3.8000, "longitude": 9.9500,
     "description": "A protected lake reserve known for birdlife and endangered African manatees."},

    # --- Waterfalls ---
    {"name": "Ekom-Nkam Waterfalls", "region": "Littoral", "tags": ["waterfall", "nature", "photography"], "latitude": 5.0333, "longitude": 9.8333,
     "description": "An 80-meter waterfall on the Nkam River, dropping through dense rainforest canopy in western Cameroon."},

    # --- Culture / history ---
    {"name": "Foumban", "region": "West", "tags": ["culture", "history", "art"], "latitude": 5.7267, "longitude": 10.9000,
     "description": "Home to the Sultan's Palace and a long-standing tradition of bronze and wood craftwork."},
    {"name": "Bafut Palace", "region": "Northwest", "tags": ["culture", "history"], "latitude": 6.0833, "longitude": 10.1000,
     "description": "A historic royal palace in Bafut, showcasing Cameroon's traditional chiefdom heritage."},
    {"name": "Bandjoun Chefferie", "region": "West", "tags": ["culture", "history", "museum"], "latitude": 5.3667, "longitude": 10.4167,
     "description": "A traditional chiefdom and museum in the West Region, preserving Bamileke cultural heritage."},

    # --- Cities ---
    {"name": "Yaoundé", "region": "Centre", "tags": ["city", "culture"], "latitude": 3.8480, "longitude": 11.5021,
     "description": "Cameroon's political capital, built across seven hills, with government buildings and museums."},
    {"name": "Douala", "region": "Littoral", "tags": ["city", "food", "shopping"], "latitude": 4.0511, "longitude": 9.7679,
     "description": "Cameroon's economic capital and largest city, and the country's main port."},
    {"name": "Bafoussam", "region": "West", "tags": ["city", "culture"], "latitude": 5.4737, "longitude": 10.4176,
     "description": "The main city of the Western Highlands, a gateway to the region's scenic landscapes."},
    {"name": "Bamenda", "region": "Northwest", "tags": ["city", "culture", "scenery"], "latitude": 5.9631, "longitude": 10.1591,
     "description": "The largest city in the Northwest Region, set among the Bamenda Highlands."},
    {"name": "Ngaoundéré", "region": "Adamawa", "tags": ["city", "culture"], "latitude": 7.3167, "longitude": 13.5833,
     "description": "A city in the Adamawa Region offering a glimpse into traditional plateau lifestyles, and a base for exploring the surrounding highlands."},

    # --- Yaoundé landmarks ---
    {"name": "Reunification Monument", "region": "Centre", "tags": ["history", "city"], "latitude": 3.8712, "longitude": 11.5213,
     "description": "A monument in Yaoundé commemorating the 1961 reunification of French and British Cameroon."},
    {"name": "Mvog-Betsi Zoo", "region": "Centre", "tags": ["wildlife", "eco-tourism"], "latitude": 3.8580, "longitude": 11.4950,
     "description": "A zoo and primate rescue centre in Yaoundé, home to gorillas, chimpanzees, and other native wildlife."},

    # --- Botanic garden ---
    {"name": "Limbe Botanic Garden", "region": "Southwest", "tags": ["nature", "relaxation", "photography"], "latitude": 4.0163, "longitude": 9.2136,
     "description": "Founded in 1892, a botanical garden showcasing Cameroon's plant biodiversity above Limbe's black-sand coastline."},
]
