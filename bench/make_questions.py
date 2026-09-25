"""Builds bench/questions.jsonl, the test set for the eight ball.

Every right answer comes from how the item is built (a table, arithmetic, a rule),
never from a language model. Run:  python bench/make_questions.py

Same seed, same file, every time.
"""
from __future__ import annotations

import calendar
import json
import math
import random
import re
from collections import Counter, defaultdict
from datetime import date
from decimal import Decimal
from pathlib import Path

SEED = 8
HERE = Path(__file__).resolve().parent
OUT = HERE / "questions.jsonl"
TODAY = date(2026, 9, 25)  # fixed on purpose: decides "Was" versus "Will" for calendar dates
FILLER_CAP = 3  # no more than this many "maybe" items may share one filler

PREFIX = {
    "capital": "cap", "arithmetic": "ari", "bigger": "big", "number": "num", "physical": "phy",
    "animal": "ani", "geo": "geo", "chemistry": "che", "calendar": "cal", "word": "wor",
    "compare": "cmp", "history": "his", "future": "fut", "private": "pri", "taste": "tas", "open": "ope",
}
YESNO_KINDS = ["capital", "arithmetic", "bigger", "number", "physical", "animal", "geo",
               "chemistry", "calendar", "word", "compare", "history"]
MAYBE_KINDS = ["future", "private", "taste", "open"]
# yes count == no count for each of these
YESNO_TARGET = {"capital": 28, "arithmetic": 28, "bigger": 10, "number": 24, "physical": 24, "animal": 28,
                "geo": 28, "chemistry": 28, "calendar": 28, "word": 28, "compare": 30, "history": 16}
MAYBE_TARGET = 75


def art(noun: str) -> str:
    return ("an " if noun[0].lower() in "aeiou" else "a ") + noun


# ----------------------------------------------------------------------------------------- tables
# country -> (capital, region). Only facts that are settled and unchanged for decades.
CAPITALS = {
    "France": ("Paris", "E"), "Germany": ("Berlin", "E"), "Italy": ("Rome", "E"), "Spain": ("Madrid", "E"),
    "Portugal": ("Lisbon", "E"), "Ireland": ("Dublin", "E"), "the United Kingdom": ("London", "E"),
    "Norway": ("Oslo", "E"), "Sweden": ("Stockholm", "E"), "Finland": ("Helsinki", "E"),
    "Denmark": ("Copenhagen", "E"), "Iceland": ("Reykjavik", "E"), "Poland": ("Warsaw", "E"),
    "Austria": ("Vienna", "E"), "Hungary": ("Budapest", "E"), "Greece": ("Athens", "E"),
    "Belgium": ("Brussels", "E"), "Czechia": ("Prague", "E"), "Romania": ("Bucharest", "E"),
    "Bulgaria": ("Sofia", "E"), "Serbia": ("Belgrade", "E"), "Croatia": ("Zagreb", "E"),
    "Ukraine": ("Kyiv", "E"), "Russia": ("Moscow", "E"),
    "Japan": ("Tokyo", "A"), "China": ("Beijing", "A"), "India": ("New Delhi", "A"), "Thailand": ("Bangkok", "A"),
    "Vietnam": ("Hanoi", "A"), "the Philippines": ("Manila", "A"), "South Korea": ("Seoul", "A"),
    "Iran": ("Tehran", "A"), "Iraq": ("Baghdad", "A"), "Saudi Arabia": ("Riyadh", "A"),
    "Pakistan": ("Islamabad", "A"), "Afghanistan": ("Kabul", "A"), "Nepal": ("Kathmandu", "A"),
    "Mongolia": ("Ulaanbaatar", "A"), "Cambodia": ("Phnom Penh", "A"), "Turkey": ("Ankara", "A"),
    "Bangladesh": ("Dhaka", "A"), "Jordan": ("Amman", "A"), "Lebanon": ("Beirut", "A"), "Laos": ("Vientiane", "A"),
    "Egypt": ("Cairo", "F"), "Kenya": ("Nairobi", "F"), "Nigeria": ("Abuja", "F"), "Ethiopia": ("Addis Ababa", "F"),
    "Morocco": ("Rabat", "F"), "Ghana": ("Accra", "F"), "Algeria": ("Algiers", "F"), "Tunisia": ("Tunis", "F"),
    "Senegal": ("Dakar", "F"), "Uganda": ("Kampala", "F"), "Zimbabwe": ("Harare", "F"), "Zambia": ("Lusaka", "F"),
    "Angola": ("Luanda", "F"), "Libya": ("Tripoli", "F"), "Sudan": ("Khartoum", "F"),
    "Canada": ("Ottawa", "N"), "the United States": ("Washington, D.C.", "N"), "Mexico": ("Mexico City", "N"),
    "Cuba": ("Havana", "N"), "Jamaica": ("Kingston", "N"), "Costa Rica": ("San Jose", "N"),
    "Honduras": ("Tegucigalpa", "N"),
    "Brazil": ("Brasilia", "S"), "Argentina": ("Buenos Aires", "S"), "Chile": ("Santiago", "S"),
    "Peru": ("Lima", "S"), "Colombia": ("Bogota", "S"), "Venezuela": ("Caracas", "S"),
    "Uruguay": ("Montevideo", "S"), "Ecuador": ("Quito", "S"), "Paraguay": ("Asuncion", "S"),
    "Australia": ("Canberra", "O"), "New Zealand": ("Wellington", "O"), "Fiji": ("Suva", "O"),
    "Papua New Guinea": ("Port Moresby", "O"),
}
CAPITAL_SHAPES = [
    "Is {cap} the capital of {c}?",
    "Is {cap} the capital city of {c}?",
    "Does {c} have {cap} as its capital?",
    "Is the capital of {c} {cap}?",
    "Would a traveller find the capital of {c} in {cap}?",
]

# name -> continent (no country or landmark that sits on two continents)
CONTINENTS = ["Europe", "Asia", "Africa", "North America", "South America", "Oceania"]
PLACE_CONTINENT = {
    "Germany": "Europe", "Spain": "Europe", "Poland": "Europe", "Norway": "Europe", "the Alps": "Europe",
    "the Danube": "Europe", "Japan": "Asia", "Thailand": "Asia", "India": "Asia", "Vietnam": "Asia",
    "the Himalayas": "Asia", "the Gobi Desert": "Asia", "Mount Fuji": "Asia", "Lake Baikal": "Asia",
    "the Ganges": "Asia", "Nigeria": "Africa", "Kenya": "Africa", "Morocco": "Africa",
    "the Sahara Desert": "Africa", "Mount Kilimanjaro": "Africa", "Lake Victoria": "Africa", "the Nile": "Africa",
    "Peru": "South America", "Chile": "South America", "Colombia": "South America",
    "the Andes": "South America", "the Amazon rainforest": "South America",
    "Canada": "North America", "Mexico": "North America", "Cuba": "North America", "Niagara Falls": "North America",
    "the Rocky Mountains": "North America", "the Grand Canyon": "North America",
    "Australia": "Oceania", "New Zealand": "Oceania", "Fiji": "Oceania", "Uluru": "Oceania",
    "the Great Barrier Reef": "Oceania",
}
CONTINENT_SHAPES = [
    "Is {x} in {k}?", "Is {x} located in {k}?", "Would you find {x} in {k}?", "Does {x} lie in {k}?",
]
# city -> latitude in degrees (north positive)
LATITUDE = {
    "Reykjavik": 64.1, "Anchorage": 61.2, "Oslo": 59.9, "Stockholm": 59.3, "Helsinki": 60.2, "Moscow": 55.8,
    "Copenhagen": 55.7, "London": 51.5, "Paris": 48.9, "Vienna": 48.2, "Rome": 41.9, "Madrid": 40.4,
    "New York": 40.7, "Beijing": 39.9, "Athens": 38.0, "Tokyo": 35.7, "Cairo": 30.0, "Miami": 25.8,
    "Mexico City": 19.4, "Nairobi": -1.3, "Singapore": 1.4, "Lima": -12.0, "Jakarta": -6.2,
    "Johannesburg": -26.2, "Sydney": -33.9, "Cape Town": -33.9, "Santiago": -33.4, "Buenos Aires": -34.6,
    "Melbourne": -37.8, "Wellington": -41.3, "Hobart": -42.9,
}
NORTH_SHAPES = ["Is {a} north of {b}?", "Is {a} further north than {b}?", "Does {a} lie north of {b}?"]
SOUTH_SHAPES = ["Is {a} south of {b}?", "Is {a} further south than {b}?", "Does {a} lie south of {b}?"]
HEMI_SHAPES = ["Is {a} in the {h} Hemisphere?", "Does {a} lie in the {h} Hemisphere?"]
LANDLOCKED = ["Switzerland", "Austria", "Hungary", "Czechia", "Nepal", "Mongolia", "Bolivia", "Paraguay",
              "Ethiopia", "Uganda", "Zambia", "Zimbabwe", "Mali", "Niger", "Chad", "Laos", "Afghanistan",
              "Slovakia", "Serbia", "Belarus", "Bhutan", "Malawi", "Rwanda", "Botswana", "Luxembourg"]
COASTAL = ["France", "Spain", "Japan", "Australia", "Brazil", "Chile", "Peru", "Italy", "Greece", "Portugal",
           "Norway", "India", "China", "Egypt", "Kenya", "Vietnam", "Thailand", "Mexico", "Argentina", "Canada",
           "Turkey", "Sweden", "Poland", "Indonesia", "Ireland", "Cuba", "Morocco", "Nigeria", "Denmark", "Iceland"]
LAND_SHAPE_A = "Is {c} a landlocked country?"      # true for landlocked
LAND_SHAPE_B = "Does {c} have a sea coastline?"    # true for coastal

# name -> (symbol, atomic number, state at room temperature)
ELEMENTS = {
    "hydrogen": ("H", 1, "gas"), "helium": ("He", 2, "gas"), "lithium": ("Li", 3, "solid"),
    "carbon": ("C", 6, "solid"), "nitrogen": ("N", 7, "gas"), "oxygen": ("O", 8, "gas"),
    "fluorine": ("F", 9, "gas"), "neon": ("Ne", 10, "gas"), "sodium": ("Na", 11, "solid"),
    "magnesium": ("Mg", 12, "solid"), "aluminium": ("Al", 13, "solid"), "silicon": ("Si", 14, "solid"),
    "phosphorus": ("P", 15, "solid"), "sulfur": ("S", 16, "solid"), "chlorine": ("Cl", 17, "gas"),
    "argon": ("Ar", 18, "gas"), "potassium": ("K", 19, "solid"), "calcium": ("Ca", 20, "solid"),
    "iron": ("Fe", 26, "solid"), "nickel": ("Ni", 28, "solid"), "copper": ("Cu", 29, "solid"),
    "zinc": ("Zn", 30, "solid"), "bromine": ("Br", 35, "liquid"), "silver": ("Ag", 47, "solid"),
    "tin": ("Sn", 50, "solid"), "iodine": ("I", 53, "solid"), "platinum": ("Pt", 78, "solid"),
    "gold": ("Au", 79, "solid"), "mercury": ("Hg", 80, "liquid"), "lead": ("Pb", 82, "solid"),
    "uranium": ("U", 92, "solid"),
}
SYMBOL_SHAPES = [
    "Is {s} the chemical symbol for {n}?",
    "Does {s} stand for {n} on the periodic table?",
    "Is {n} written as {s} in chemistry?",
]
ORDER_SHAPES = [  # {w} is "lower" or "higher"
    "Is the atomic number of {a} {w} than that of {b}?",
    "Does {a} have a {w} atomic number than {b}?",
]
COMPOUNDS = {
    "water": "H2O", "carbon dioxide": "CO2", "table salt": "NaCl", "methane": "CH4", "ammonia": "NH3",
    "glucose": "C6H12O6", "hydrogen peroxide": "H2O2", "sulfuric acid": "H2SO4", "ozone": "O3",
    "hydrochloric acid": "HCl", "carbon monoxide": "CO",
}
FORMULA_SHAPES = [
    "Is {f} the chemical formula for {n}?",
    "Does {n} have the formula {f}?",
    "Would a chemist write {n} as {f}?",
]
STATE_SHAPES = [
    "Is {n} {sa} {st} at room temperature?",
    "Would you find {n} as {sa} {st} at room temperature?",
]
STATES = ["solid", "liquid", "gas"]

MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September",
          "October", "November", "December"]
WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
MONTHDAYS_SHAPES = ["Does {m} have {n} days?", "Are there {n} days in {m}?", "Does {m} last {n} days?"]
WEEKDAY_PAST = ["Was {d} a {w}?", "Did {d} fall on a {w}?"]
WEEKDAY_FUTURE = ["Will {d} be a {w}?", "Will {d} fall on a {w}?"]
LEAP_PAST = ["Was {y} a leap year?", "Did {y} have 366 days?"]
LEAP_NOW = ["Is {y} a leap year?", "Will {y} have 366 days?"]
MONTH_ORDER_SHAPES = ["Does {a} come before {b} in the year?", "Is {a} earlier in the year than {b}?",
                      "Does {a} come after {b} in the calendar year?"]

WORDS = ("planet garden window bottle market river pencil orange yellow silver forest castle bridge basket rabbit "
         "tomato flower mirror button jacket kitchen morning journey pillow cheese blanket lantern harvest whisper "
         "thunder mountain library holiday penguin dolphin giraffe cabbage eleven teacher island shadow winter "
         "ticket summer needle cotton velvet pepper carpet candle rocket saddle ladder engine anchor meadow valley").split()
PALINDROMES = "level radar civic kayak refer noon rotor madam stats tenet".split()
NOT_PALINDROMES = WORDS + "lever radio civil model nurse tenor rotate tenets noun kayaks".split()
LETTER_POOL = "AEIOUSTRNLDCMPHGBKWY"
CONTAIN_SHAPES = ["Does the word '{w}' contain the letter {L}?", "Is there a letter {L} in the word '{w}'?",
                  "Can you find the letter {L} in '{w}'?"]
START_SHAPES = ["Does the word '{w}' start with the letter {L}?", "Does '{w}' begin with {L}?",
                "Is {L} the first letter of the word '{w}'?"]
END_SHAPES = ["Does the word '{w}' end with the letter {L}?", "Is {L} the last letter of '{w}'?"]
LEN_LONGER = ["Is the word '{w}' longer than {n} letters?", "Does the word '{w}' have more than {n} letters?"]
LEN_SHORTER = ["Is the word '{w}' shorter than {n} letters?"]
PAL_SHAPES = ["Is the word '{w}' the same when spelled backwards?", "Does '{w}' read the same backwards as forwards?"]
ALPHA_SHAPES = ["Does the letter {a} come before the letter {b} in the alphabet?",
                "Is {a} earlier in the alphabet than {b}?", "Does the letter {a} come after the letter {b} in the alphabet?"]

ANIMALS = {
    "mammal": "dog cat horse cow whale dolphin bat elephant rabbit mouse kangaroo lion tiger bear giraffe monkey "
              "sheep pig seal platypus wolf camel".split(),
    "bird": "eagle penguin ostrich owl sparrow duck chicken parrot pigeon flamingo swan hawk".split(),
    "fish": "salmon shark trout tuna goldfish cod seahorse eel".split(),
    "reptile": "snake lizard crocodile turtle gecko chameleon".split(),
    "amphibian": "frog toad salamander newt".split(),
    "insect": "ant bee butterfly beetle mosquito grasshopper dragonfly wasp".split(),
    "arachnid": "spider scorpion".split(),
}
ANIMAL_CLASS = {a: c for c, xs in ANIMALS.items() for a in xs}
NEAR_MISS = [("whale", "fish"), ("dolphin", "fish"), ("bat", "bird"), ("spider", "insect"), ("seal", "fish"),
             ("penguin", "fish"), ("shark", "mammal"), ("frog", "reptile"), ("turtle", "amphibian"),
             ("platypus", "reptile"), ("dolphin", "reptile")]
CLASS_SHAPES = ["Is {a} {c}?", "Is {a} classed as {c}?", "Does {a} count as {c}?", "Would a zoologist call {a} {c}?"]
CAN_FLY = "eagle sparrow owl bee butterfly bat pigeon duck mosquito dragonfly".split()
CANNOT_FLY = "dog cow horse elephant penguin ostrich rabbit pig sheep kangaroo".split()
FLY_SHAPES = ["Can {a} fly?", "Is {a} able to fly?", "Would {a} be able to fly?"]
LAYS_EGGS = "chicken duck penguin crocodile salmon frog platypus ostrich turtle eagle owl".split()
NO_EGGS = "dog cow whale dolphin horse elephant bat rabbit sheep monkey lion kangaroo".split()
EGG_SHAPES = ["Does {a} lay eggs?", "Can {a} lay eggs?"]

# (question with {v}, true values, wrong values). Numbers of 1000 or more are printed with commas.
PHYSICAL = [
    ("Does water boil at {v} degrees Celsius at sea level?", [100], [50, 90, 120, 150, 200]),
    ("Does pure water freeze at {v} degrees Celsius?", [0], [10, -10, 5, -20, 32]),
    ("Are there {v} seconds in a minute?", [60], [100, 50, 30, 90, 120]),
    ("Are there {v} hours in a day?", [24], [12, 20, 25, 48, 36]),
    ("Does a week have {v} days?", [7], [5, 6, 8, 10, 14]),
    ("Are there {v} centimetres in a metre?", [100], [10, 1000, 50, 12]),
    ("Does a kilometre contain {v} metres?", [1000], [100, 500, 10000, 1024, 10]),
    ("Are there {v} degrees in a full circle?", [360], [180, 90, 100, 400, 270]),
    ("Do the angles of a triangle add up to {v} degrees?", [180], [90, 360, 100, 270, 200]),
    ("Does a cube have {v} faces?", [6], [4, 8, 12, 5, 10]),
    ("Does an octagon have {v} sides?", [8], [6, 10, 7, 12, 5]),
    ("Does a pentagon have {v} sides?", [5], [4, 6, 7, 8, 10]),
    ("Does a healthy adult human normally have {v} permanent teeth?", [32], [20, 40, 24, 16, 50]),
    ("Does an adult human skeleton have {v} bones?", [206], [106, 306, 150, 400, 50]),
    ("Is normal human body temperature about {v} degrees Celsius?", [37], [30, 42, 25, 50, 20]),
    ("Does light travel at about {v} kilometres per second?", [300000], [30000, 3000, 3000000, 300]),
    ("Does the Earth take about {v} days to go around the Sun?", [365], [30, 100, 500, 700]),
    ("Does a leap year have {v} days?", [366], [365, 360, 364, 367, 400]),
    ("Are there {v} ounces in a pound?", [16], [10, 8, 20, 14, 32]),
    ("Are there {v} feet in a mile?", [5280], [1000, 3000, 10000, 500]),
    ("Are there {v} inches in a foot?", [12], [10, 8, 16, 24, 6]),
    ("Does a soccer team have {v} players on the pitch?", [11], [9, 15, 7, 13, 6]),
    ("Does a chess board have {v} squares?", [64], [100, 81, 32, 49, 36]),
    ("Does a standard piano have {v} keys?", [88], [66, 100, 44, 120]),
    ("Is the freezing point of water {v} degrees Fahrenheit?", [32], [0, 100, 212, 50, -32]),
    ("Does a decade last {v} years?", [10], [5, 20, 100, 50, 12]),
    ("Does a century last {v} years?", [100], [10, 50, 1000, 200, 25]),
    ("Are there {v} months in a year?", [12], [10, 11, 13, 14, 24]),
    ("Will a bucket of water left outside for a week freeze if the air stays at {v} degrees Celsius?",
     [-10, -15, -20], [10, 15, 20, 25]),
    ("Will ice melt if a room is kept at {v} degrees Celsius?", [10, 20, 25, 30], [-5, -10, -15, -20]),
]

# (noun phrase for ordering, year, question with {y}). Only unambiguous, widely agreed years.
HISTORY = [
    ("the Battle of Hastings", 1066, "Did the Battle of Hastings take place in {y}?"),
    ("the sealing of Magna Carta", 1215, "Was Magna Carta sealed in {y}?"),
    ("the fall of Constantinople", 1453, "Did Constantinople fall to the Ottomans in {y}?"),
    ("the first voyage of Columbus across the Atlantic", 1492, "Did Columbus first sail across the Atlantic in {y}?"),
    ("the Great Fire of London", 1666, "Did the Great Fire of London happen in {y}?"),
    ("the adoption of the US Declaration of Independence", 1776, "Was the US Declaration of Independence adopted in {y}?"),
    ("the start of the French Revolution", 1789, "Did the French Revolution begin in {y}?"),
    ("the Battle of Waterloo", 1815, "Was the Battle of Waterloo fought in {y}?"),
    ("the assassination of Abraham Lincoln", 1865, "Was Abraham Lincoln assassinated in {y}?"),
    ("the first powered flight by the Wright brothers", 1903, "Did the Wright brothers make their first powered flight in {y}?"),
    ("the sinking of the Titanic", 1912, "Did the Titanic sink in {y}?"),
    ("the start of the First World War", 1914, "Did the First World War begin in {y}?"),
    ("the Wall Street Crash", 1929, "Did the Wall Street Crash happen in {y}?"),
    ("the start of the Second World War", 1939, "Did the Second World War begin in {y}?"),
    ("the attack on Pearl Harbor", 1941, "Did the attack on Pearl Harbor happen in {y}?"),
    ("the end of the Second World War", 1945, "Did the Second World War end in {y}?"),
    ("the independence of India", 1947, "Did India become independent in {y}?"),
    ("the launch of Sputnik 1", 1957, "Was Sputnik 1 launched in {y}?"),
    ("the building of the Berlin Wall", 1961, "Was the Berlin Wall built in {y}?"),
    ("the first Moon landing", 1969, "Did humans first land on the Moon in {y}?"),
    ("the Chernobyl disaster", 1986, "Did the Chernobyl disaster happen in {y}?"),
    ("the fall of the Berlin Wall", 1989, "Did the Berlin Wall fall in {y}?"),
    ("the break-up of the Soviet Union", 1991, "Did the Soviet Union break up in {y}?"),
    ("the September 11 attacks", 2001, "Did the September 11 attacks take place in {y}?"),
]
HISTORY_ORDER_SHAPES = ["Did {a} happen before {b}?", "Did {a} happen after {b}?"]
WRONG_YEAR_OFFSETS = [-30, -20, -15, -10, 10, 15, 20, 30]

# Comparison groups. Each pair is only used when the two values are far enough apart to leave no doubt.
COMPARE = [
    dict(name="mountain", n=8, ratio=1.4, hi="taller", lo="shorter", shapes=["Is {a} {w} than {b}?", "Would {a} be {w} than {b}?"],
         items={"Mount Everest": 8849, "Mount Kilimanjaro": 5895, "Mont Blanc": 4808, "Mount Fuji": 3776,
                "Mount Kosciuszko": 2228, "Ben Nevis": 1345}),
    dict(name="building", n=6, ratio=1.4, hi="taller", lo="shorter", shapes=["Is {a} {w} than {b}?", "Would {a} be {w} than {b}?"],
         items={"the Burj Khalifa": 828, "the Empire State Building": 381, "the Eiffel Tower": 330,
                "Big Ben": 96, "the Great Pyramid of Giza": 139}),
    dict(name="weight", n=8, ratio=3.0, hi="heavier", lo="lighter", shapes=["Is {a} {w} than {b}?", "Would {a} be {w} than {b}?"],
         items={"a blue whale": 150000, "an elephant": 5000, "a hippopotamus": 1500, "a horse": 500,
                "an adult human": 70, "a cat": 4, "a mouse": 0.02}),
    dict(name="distance", n=6, ratio=1.5, hi="farther from", lo="closer to", shapes=["Is {a} {w} Earth than {b}?"],
         items={"the Moon": 384400, "the Sun": 149600000, "Jupiter": 778000000, "Saturn": 1400000000,
                "Neptune": 4400000000}),
    dict(name="size", n=6, ratio=1.5, hi="bigger", lo="smaller", shapes=["Is {a} {w} than {b}?", "Would {a} be {w} than {b}?"],
         items={"the Sun": 1392000, "Jupiter": 139820, "Saturn": 116460, "Neptune": 49244, "Earth": 12742,
                "Mars": 6779, "the Moon": 3474}),
    dict(name="river", n=6, ratio=1.5, hi="longer", lo="shorter", shapes=["Is {a} {w} than {b}?", "Would {a} be {w} than {b}?"],
         items={"the Nile": 6650, "the Volga": 3530, "the Danube": 2850, "the Rhine": 1230, "the Seine": 777,
                "the Thames": 346}),
    dict(name="area", n=8, ratio=1.8, hi="larger", lo="smaller", shapes=["Is {a} {w} than {b} in area?"],
         items={"Russia": 17098000, "Canada": 9985000, "Brazil": 8516000, "Australia": 7692000, "India": 3287000,
                "Argentina": 2780000, "Mexico": 1964000, "France": 551695, "Japan": 377975,
                "the United Kingdom": 243610, "Iceland": 103000, "Belgium": 30689, "Luxembourg": 2586}),
    dict(name="population", n=6, ratio=2.5, hi="more", lo="fewer", shapes=["Does {a} have {w} people than {b}?", "Would {a} have {w} people than {b}?"],
         items={"the United States": 335, "Japan": 124, "Germany": 84, "the United Kingdom": 67, "Canada": 40,
                "Australia": 26, "Sweden": 10.5, "Iceland": 0.38}),
    dict(name="speed", n=6, ratio=2.0, hi="faster", lo="slower", shapes=["Is {a} {w} than {b}?", "Would {a} be {w} than {b}?"],
         items={"a snail": 0.05, "a tortoise": 0.3, "a walking person": 5, "a galloping horse": 55,
                "a cheetah": 110, "a passenger jet": 900}),
]
assert sum(g["n"] for g in COMPARE) == 2 * YESNO_TARGET["compare"]


# ------------------------------------------------------------------------------------ the builder
class Bag:
    """Collects the items of one kind; refuses repeats (case-insensitive, across all kinds)."""

    seen: set[str] = set()

    def __init__(self, kind: str):
        self.kind = kind
        self.items: list[dict] = []
        self.count = Counter()

    def add(self, question: str, label: str) -> bool:
        key = question.strip().lower()
        if key in Bag.seen:
            return False
        Bag.seen.add(key)
        self.items.append({"question": question, "label": label, "kind": self.kind})
        self.count[label] += 1
        return True

    def fill(self, rng: random.Random, make, n: int, labels=("yes", "no")) -> None:
        for label in labels:
            tries = 0
            while self.count[label] < n:
                tries += 1
                assert tries < 50000, (self.kind, label, "cannot make enough distinct items")
                q = make(rng, label)
                if q:
                    self.add(q, label)


class Fillers:
    """Hands out fillers so that none is used in more than FILLER_CAP maybe-items."""

    def __init__(self):
        self.use: Counter = Counter()

    def note(self, *parts: str) -> None:
        for p in parts:
            self.use[p] += 1
            assert self.use[p] <= FILLER_CAP, p

    def take(self, rng: random.Random, options, slack: int = 0):
        def parts(o):
            return o if isinstance(o, tuple) else (o,)
        ok = [o for o in options if all(self.use[p] < FILLER_CAP for p in parts(o))]
        assert ok, "filler table exhausted"
        low = min(max(self.use[p] for p in parts(o)) for o in ok)
        pick = rng.choice([o for o in ok if max(self.use[p] for p in parts(o)) <= low + slack])
        self.note(*parts(pick))
        return pick


FILL = Fillers()


def near_miss(rng: random.Random, c: int) -> int:
    while True:
        w = c + rng.choice([-1, 1, -2, 2, -9, 9, -10, 10, -11, 11, 20, -20, 100, -100])
        if w > 0 and w != c:
            return w


# ---------------------------------------------------------------------------------- yes / no kinds
def build_capital(rng):
    def make(rng, label):
        c = rng.choice(list(CAPITALS))
        cap, region = CAPITALS[c]
        if label == "no":
            cap = rng.choice([v[0] for k, v in CAPITALS.items() if v[1] == region and k != c])
        return rng.choice(CAPITAL_SHAPES).format(c=c, cap=cap)
    bag = Bag("capital")
    bag.fill(rng, make, YESNO_TARGET["capital"])
    return bag.items


def build_arithmetic(rng):
    def make(rng, label):
        op = rng.choice(["mul", "mul", "add", "sub", "div"])
        if op == "mul":
            a, b = rng.randint(12, 99), rng.randint(3, 99)
            c = a * b
            shapes = ["Is {a} x {b} equal to {c}?", "Does {a} x {b} make {c}?", "Would {a} x {b} come to {c}?",
                      "Is the product of {a} and {b} equal to {c}?", "Is {c} the answer to {a} x {b}?",
                      "Will {a} x {b} come out at {c}?"]
        elif op == "add":
            a, b = rng.randint(100, 999), rng.randint(100, 999)
            c = a + b
            shapes = ["Is {a} + {b} equal to {c}?", "Does {a} plus {b} make {c}?",
                      "Is the sum of {a} and {b} equal to {c}?", "Would {a} + {b} come to {c}?",
                      "Will {a} + {b} come out at {c}?"]
        elif op == "sub":
            a = rng.randint(200, 999)
            b = rng.randint(20, a - 20)
            c = a - b
            shapes = ["Is {a} - {b} equal to {c}?", "Does {a} minus {b} leave {c}?",
                      "Is the difference between {a} and {b} equal to {c}?", "Would {a} - {b} come to {c}?",
                      "Will {a} - {b} come out at {c}?"]
        else:
            b, c = rng.randint(3, 19), rng.randint(12, 99)
            a = b * c
            shapes = ["Is {a} divided by {b} equal to {c}?", "Does {a} divided by {b} give {c}?",
                      "Would {a} divided by {b} come to {c}?", "Will {a} divided by {b} come out at {c}?"]
        if label == "no":
            c = near_miss(rng, c)
        return rng.choice(shapes).format(a=a, b=b, c=c)
    bag = Bag("arithmetic")
    bag.fill(rng, make, YESNO_TARGET["arithmetic"])
    return bag.items


BIGGER_WORDS = [("greater than", True), ("larger than", True), ("more than", True), ("less than", False),
                ("smaller than", False)]


def build_bigger(rng):
    def make(rng, label):
        word, greater = rng.choice(BIGGER_WORDS)
        if rng.random() < 0.6:
            hi = rng.randint(1000, 9999)
            digits = list(str(hi))
            i = rng.randrange(3)
            digits[i], digits[i + 1] = digits[i + 1], digits[i]
            lo = int("".join(digits)) if digits[0] != "0" else hi - 1
            if lo == hi or rng.random() < 0.3:
                lo = hi - rng.randint(1, 60)
            if lo > hi:
                hi, lo = lo, hi
            hi, lo = str(hi), str(lo)
        else:
            w, t, d = rng.randint(0, 9), rng.randint(1, 9), rng.randint(1, 9)
            one = f"{w}.{t}"
            if rng.random() < 0.5:
                two = f"{w}.{t - 1}{d}"      # less than the one-digit number
                hi, lo = one, two
            else:
                two = f"{w}.{t}{d}"           # more than the one-digit number
                hi, lo = two, one
        a = hi if ((label == "yes") == greater) else lo
        b = lo if a == hi else hi
        return f"Is {a} {word} {b}?"
    bag = Bag("bigger")
    bag.fill(rng, make, YESNO_TARGET["bigger"])
    return bag.items


def _primes(lo, hi):
    return [n for n in range(lo, hi) if n > 1 and all(n % d for d in range(2, math.isqrt(n) + 1))]


PRIMES_3 = _primes(101, 1000)
SMALL_PRIMES = _primes(7, 50)


def build_number(rng):
    def make(rng, label):
        kind = rng.choices(["prime", "multiple", "square", "parity"], weights=[8, 6, 5, 5])[0]
        yes = label == "yes"
        if kind == "prime":
            if yes:
                n = rng.choice(PRIMES_3)
            else:
                n = rng.choice([p * q for p in SMALL_PRIMES for q in SMALL_PRIMES if 100 <= p * q < 1000])
            return rng.choice(["Is {n} a prime number?", "Is {n} prime?", "Would {n} count as a prime number?",
                               "Does {n} have no divisors other than 1 and itself?"]).format(n=n)
        if kind == "multiple":
            k = rng.choice([3, 4, 6, 7, 8, 9, 11, 12, 13])
            m = rng.randint(10, 60)
            n = k * m if yes else k * m + rng.choice([1, 2, k - 1, k - 2])
            return rng.choice(["Is {n} a multiple of {k}?", "Is {n} divisible by {k}?",
                               "Does {k} divide evenly into {n}?", "Would {n} be a multiple of {k}?"]).format(n=n, k=k)
        if kind == "square":
            m = rng.randint(12, 60)
            n = m * m if yes else m * m + rng.choice([-3, -2, -1, 1, 2, 3])
            return rng.choice(["Is {n} a perfect square?", "Is {n} the square of a whole number?",
                               "Would {n} be a perfect square?"]).format(n=n)
        n = rng.randint(100, 99999)
        want_even = rng.random() < 0.5
        if (n % 2 == 0) != (want_even == yes):  # make the truth match the wanted label
            n += 1
        return f"Is {n} an {'even' if want_even else 'odd'} number?"
    bag = Bag("number")
    bag.fill(rng, make, YESNO_TARGET["number"])
    return bag.items


def _fmt(v: int) -> str:
    return f"{v:,}" if abs(v) >= 1000 else str(v)


def build_physical(rng):
    def make(rng, label):
        tmpl, trues, wrongs = rng.choice(PHYSICAL)
        v = rng.choice(trues if label == "yes" else wrongs)
        return tmpl.format(v=_fmt(v))
    bag = Bag("physical")
    bag.fill(rng, make, YESNO_TARGET["physical"])
    return bag.items


def build_animal(rng):
    def make(rng, label):
        sub = rng.choices(["class", "fly", "eggs"], weights=[18, 5, 5])[0]
        if sub == "class":
            if label == "yes":
                a = rng.choice(list(ANIMAL_CLASS))
                c = ANIMAL_CLASS[a]
            elif rng.random() < 0.45:
                a, c = rng.choice(NEAR_MISS)
            else:
                a = rng.choice(list(ANIMAL_CLASS))
                c = rng.choice([x for x in ANIMALS if x != ANIMAL_CLASS[a]])
            return rng.choice(CLASS_SHAPES).format(a=art(a), c=art(c))
        if sub == "fly":
            a = rng.choice(CAN_FLY if label == "yes" else CANNOT_FLY)
            return rng.choice(FLY_SHAPES).format(a=art(a))
        a = rng.choice(LAYS_EGGS if label == "yes" else NO_EGGS)
        return rng.choice(EGG_SHAPES).format(a=art(a))
    bag = Bag("animal")
    bag.fill(rng, make, YESNO_TARGET["animal"])
    return bag.items


def build_geo(rng):
    def make(rng, label):
        yes = label == "yes"
        sub = rng.choices(["continent", "north", "landlocked", "hemisphere"], weights=[10, 10, 4, 4])[0]
        if sub == "continent":
            x = rng.choice(list(PLACE_CONTINENT))
            k = PLACE_CONTINENT[x] if yes else rng.choice([c for c in CONTINENTS if c != PLACE_CONTINENT[x]])
            return rng.choice(CONTINENT_SHAPES).format(x=x, k=k)
        if sub == "north":
            a, b = rng.sample(list(LATITUDE), 2)
            if abs(LATITUDE[a] - LATITUDE[b]) < 8:
                return None
            is_north = rng.random() < 0.5
            truth = (LATITUDE[a] > LATITUDE[b]) if is_north else (LATITUDE[a] < LATITUDE[b])
            if truth != yes:
                a, b = b, a
            return rng.choice(NORTH_SHAPES if is_north else SOUTH_SHAPES).format(a=a, b=b)
        if sub == "landlocked":
            if rng.random() < 0.5:   # "landlocked?" is true for landlocked countries
                c = rng.choice(LANDLOCKED if yes else COASTAL)
                return LAND_SHAPE_A.format(c=c)
            c = rng.choice(COASTAL if yes else LANDLOCKED)   # "coastline?" is true for coastal ones
            return LAND_SHAPE_B.format(c=c)
        a = rng.choice([c for c in LATITUDE if abs(LATITUDE[c]) >= 10])
        true_h = "Northern" if LATITUDE[a] > 0 else "Southern"
        h = true_h if yes else ("Southern" if true_h == "Northern" else "Northern")
        return rng.choice(HEMI_SHAPES).format(a=a, h=h)
    bag = Bag("geo")
    bag.fill(rng, make, YESNO_TARGET["geo"])
    return bag.items


def build_chemistry(rng):
    def make(rng, label):
        yes = label == "yes"
        sub = rng.choices(["symbol", "order", "formula", "state"], weights=[9, 6, 5, 8])[0]
        if sub == "symbol":
            n = rng.choice(list(ELEMENTS))
            s = ELEMENTS[n][0] if yes else rng.choice([v[0] for k, v in ELEMENTS.items() if k != n])
            return rng.choice(SYMBOL_SHAPES).format(s=s, n=n)
        if sub == "order":
            a, b = rng.sample(list(ELEMENTS), 2)
            za, zb = ELEMENTS[a][1], ELEMENTS[b][1]
            if abs(za - zb) < 5:
                return None
            w = rng.choice(["lower", "higher"])
            truth = (za < zb) if w == "lower" else (za > zb)
            if truth != yes:
                a, b = b, a
            return rng.choice(ORDER_SHAPES).format(a=a, b=b, w=w)
        if sub == "formula":
            n = rng.choice(list(COMPOUNDS))
            f = COMPOUNDS[n] if yes else rng.choice([v for k, v in COMPOUNDS.items() if k != n])
            return rng.choice(FORMULA_SHAPES).format(f=f, n=n)
        n = rng.choice([k for k, v in ELEMENTS.items() if k in
                        ("helium oxygen nitrogen neon chlorine hydrogen mercury bromine iron gold copper lead "
                         "sulfur carbon sodium silver").split()])
        st = ELEMENTS[n][2] if yes else rng.choice([s for s in STATES if s != ELEMENTS[n][2]])
        return rng.choice(STATE_SHAPES).format(n=n, st=st, sa=art(st).split()[0])
    bag = Bag("chemistry")
    bag.fill(rng, make, YESNO_TARGET["chemistry"])
    return bag.items


def fmt_date(d: date) -> str:
    return f"{d.day} {MONTHS[d.month - 1]} {d.year}"


def build_calendar(rng):
    def make(rng, label):
        yes = label == "yes"
        sub = rng.choices(["days", "weekday", "leap", "order"], weights=[6, 14, 4, 4])[0]
        if sub == "days":
            mi = rng.randrange(12)
            year = rng.choice([2020, 2022, 2023, 2024, 2025, 2028]) if mi == 1 else None
            true = calendar.monthrange(year or 2023, mi + 1)[1]
            n = true if yes else rng.choice([x for x in (28, 29, 30, 31) if x != true])
            name = MONTHS[mi] + (f" {year}" if year else "")
            return rng.choice(MONTHDAYS_SHAPES).format(m=name, n=n)
        if sub == "weekday":
            if rng.random() < 0.55:   # a date still to come, asked with "Will"
                d = date.fromordinal(rng.randint(TODAY.toordinal() + 1, date(2035, 12, 31).toordinal()))
            else:
                d = date.fromordinal(rng.randint(date(1960, 1, 1).toordinal(), TODAY.toordinal() - 1))
            true = d.weekday()
            w = true if yes else rng.choice([x for x in range(7) if x != true])
            shapes = WEEKDAY_PAST if d < TODAY else WEEKDAY_FUTURE
            return rng.choice(shapes).format(d=fmt_date(d), w=WEEKDAYS[w])
        if sub == "leap":
            future = rng.random() < 0.5
            if yes:
                y = rng.choice([2000, 2000] + [y for y in range(1904, 2097, 4) if y % 100 and (y >= 2026) == future])
            else:
                y = rng.choice([1900, 2100] + [y for y in range(1901, 2100) if y % 4 and (y >= 2026) == future])
            return rng.choice(LEAP_PAST if y < 2026 else LEAP_NOW).format(y=y)
        a, b = rng.sample(range(12), 2)
        if abs(a - b) < 2:
            return None
        shape = rng.choice(MONTH_ORDER_SHAPES)
        truth = (a < b) if " before " in shape or "earlier" in shape else (a > b)
        if truth != yes:
            a, b = b, a
        return shape.format(a=MONTHS[a], b=MONTHS[b])
    bag = Bag("calendar")
    bag.fill(rng, make, YESNO_TARGET["calendar"])
    return bag.items


def build_word(rng):
    def make(rng, label):
        yes = label == "yes"
        sub = rng.choices(["contain", "start", "end", "length", "pal", "alpha"], weights=[7, 4, 3, 6, 4, 4])[0]
        if sub == "contain":
            w = rng.choice(WORDS)
            inside = [c for c in LETTER_POOL if c.lower() in w]
            outside = [c for c in LETTER_POOL if c.lower() not in w]
            L = rng.choice(inside if yes else outside)
            return rng.choice(CONTAIN_SHAPES).format(w=w, L=L)
        if sub in ("start", "end"):
            w = rng.choice(WORDS)
            real = (w[0] if sub == "start" else w[-1]).upper()
            L = real if yes else rng.choice([c for c in LETTER_POOL if c != real])
            return rng.choice(START_SHAPES if sub == "start" else END_SHAPES).format(w=w, L=L)
        if sub == "length":
            w = rng.choice(WORDS)
            n_letters = len(w)
            if rng.random() < 0.6:   # "longer than"
                n = n_letters - rng.randint(1, 3) if yes else n_letters + rng.randint(0, 2)
                shape = rng.choice(LEN_LONGER)
            else:                    # "shorter than"
                n = n_letters + rng.randint(1, 3) if yes else n_letters - rng.randint(0, 2)
                shape = rng.choice(LEN_SHORTER)
            if n < 2:
                return None
            return shape.format(w=w, n=n)
        if sub == "pal":
            w = rng.choice(PALINDROMES if yes else NOT_PALINDROMES)
            return rng.choice(PAL_SHAPES).format(w=w)
        a, b = rng.sample("ABCDEFGHIJKLMNOPQRSTUVWXYZ", 2)
        if abs(ord(a) - ord(b)) < 4:
            return None
        shape = rng.choice(ALPHA_SHAPES)
        truth = (a < b) if "before" in shape or "earlier" in shape else (a > b)
        if truth != yes:
            a, b = b, a
        return shape.format(a=a, b=b)
    bag = Bag("word")
    bag.fill(rng, make, YESNO_TARGET["word"])
    return bag.items


def build_compare(rng):
    bag = Bag("compare")
    for g in COMPARE:
        names = list(g["items"])
        pairs = []
        for i, x in enumerate(names):
            for y in names[i + 1:]:
                hi, lo = (x, y) if g["items"][x] > g["items"][y] else (y, x)
                if g["items"][hi] / g["items"][lo] >= g["ratio"]:
                    pairs.append((hi, lo))
        rng.shuffle(pairs)
        assert len(pairs) >= g["n"], g["name"]
        for i, (hi, lo) in enumerate(pairs[:g["n"]]):
            yes = i % 2 == 0
            use_hi_word = rng.random() < 0.5
            # want "a <word> than b": pick order so that the sentence is true (yes) or false (no)
            if use_hi_word:
                a, b = (hi, lo) if yes else (lo, hi)
                w = g["hi"]
            else:
                a, b = (lo, hi) if yes else (hi, lo)
                w = g["lo"]
            q = rng.choice(g["shapes"]).format(a=a, b=b, w=w)
            assert bag.add(q, "yes" if yes else "no"), q
    return bag.items


def build_history(rng):
    def make(rng, label):
        if rng.random() < 0.7:
            noun, year, tmpl = rng.choice(HISTORY)
            y = year if label == "yes" else year + rng.choice(WRONG_YEAR_OFFSETS)
            return tmpl.format(y=y)
        (na, ya, _), (nb, yb, _) = rng.sample(HISTORY, 2)
        if abs(ya - yb) < 20:
            return None
        shape = rng.choice(HISTORY_ORDER_SHAPES)
        truth = (ya < yb) if "before" in shape else (ya > yb)
        if truth != (label == "yes"):
            na, nb = nb, na
        return shape.format(a=na, b=nb)
    bag = Bag("history")
    bag.fill(rng, make, YESNO_TARGET["history"])
    return bag.items


# ---------------------------------------------------------------------------------------- maybe kinds
def add_all(kind: str, questions: list[str]) -> list[dict]:
    bag = Bag(kind)
    for q in questions:
        assert bag.add(q, "maybe"), ("duplicate", q)
    assert len(bag.items) == MAYBE_TARGET, (kind, len(bag.items))
    return bag.items


def slots(rng, template: str, n: int, **tables) -> list[str]:
    """Fill a template n times, drawing each slot's filler from its table with the global usage cap."""
    out: list[str] = []
    redraws = 0
    while len(out) < n:
        picks = {name: FILL.take(rng, opts, slack=redraws // 10) for name, opts in tables.items()}
        flat = {}
        for k, v in picks.items():
            if isinstance(v, tuple):
                for i, part in enumerate(v):
                    flat[f"{k}{i + 1}"] = part
            else:
                flat[k] = v
        text = template.format(**flat)
        if text in out or text.lower() in Bag.seen:  # same sentence again: give the fillers back and redraw
            for v in picks.values():
                for p in (v if isinstance(v, tuple) else (v,)):
                    FILL.use[p] -= 1
            redraws += 1
            assert redraws < 500, template
            continue
        out.append(text)
    return out


def fixed(items: list[str]) -> list[str]:
    for q in items:
        FILL.note(q)
    return items


def rand_date(rng, lo=date(2027, 1, 5), hi=date(2028, 11, 28)) -> str:
    d = date.fromordinal(rng.randint(lo.toordinal(), hi.toordinal()))
    return fmt_date(d)


def build_future(rng):
    q: list[str] = []
    match_pairs = [("Arsenal", "Chelsea"), ("Real Madrid", "Barcelona"), ("Liverpool", "Manchester City"),
                   ("Bayern Munich", "Borussia Dortmund"), ("Juventus", "Inter Milan"), ("Ajax", "PSV"),
                   ("Celtic", "Rangers"), ("Boca Juniors", "River Plate"), ("Spain", "Germany"),
                   ("Brazil", "Argentina"), ("France", "England"), ("Italy", "the Netherlands"),
                   ("Portugal", "Croatia"), ("Japan", "South Korea"), ("Napoli", "AC Milan"),
                   ("Atletico Madrid", "Sevilla")]
    rng.shuffle(match_pairs)
    q += slots(rng, "Will {t1} beat {t2} in their next match?", 5, t=match_pairs[:5])
    q += slots(rng, "Would {t1} beat {t2} if they met in a rematch next season?", 5, t=match_pairs[5:10])
    q += slots(rng, "Is {t1} going to score more goals than {t2} the next time they meet?", 6, t=match_pairs[10:16])
    q += fixed([
        "Is the next coin flip going to land on heads?",
        "Will this coin come up tails on the next toss?",
        "Does the next roll of a die show an even number?",
        "Is the next card I draw from a shuffled deck going to be red?",
        "Is the roulette ball going to land on black at the next spin?",
        "Will the next die roll be higher than three?",
        "Is the next card I turn over going to be a black card?",
        "Will the next baby born in this hospital be a girl?",
        "Does the next roll of two dice add up to more than seven?",
        "Will the next flip of this coin match the one before it?",
        "Is the roulette wheel going to stop on an odd number at the next spin?",
        "Does the next die roll show a number lower than four?",
        "Is the coin toss at the start of the match going to come up heads?",
        "Is the next playing card dealt to me going to be a spade or a club?",
    ])
    lottos = ["Powerball", "EuroMillions", "Lotto", "Mega Millions", "the Irish Lotto", "Thunderball"]
    nums = rng.sample(range(1, 40), 6)  # every lottery here draws numbers up to at least 39
    for name, k in zip(lottos, nums):
        FILL.note(name, f"n{k}")
        q.append(f"Does the next {name} draw include the number {k}?")
    rain_cities = ["London", "Seattle", "Dublin", "Paris", "Amsterdam", "Vancouver", "Manchester", "Auckland",
                   "Berlin", "Wellington", "Glasgow", "Edinburgh", "Portland", "Brussels"]
    snow_cities = ["Chicago", "Toronto", "Minneapolis", "Montreal", "Denver", "Boston"]
    for i, c in enumerate(FILL.take(rng, rain_cities) for _ in range(7)):
        d = rand_date(rng)
        FILL.note(d)
        q.append(f"{'Will it rain in' if i < 3 else 'Is it going to rain in'} {c} on {d}?")
    for c in [FILL.take(rng, snow_cities) for _ in range(3)]:
        d = rand_date(rng, date(2027, 1, 10), date(2027, 2, 25))
        FILL.note(d)
        q.append(f"Will it snow in {c} on {d}?")
    for i, (c, t, lo, hi) in enumerate([("Paris", 25, 6, 8), ("London", 22, 6, 8), ("Berlin", 25, 7, 8), ("Madrid", 35, 7, 8)]):
        m = rng.randint(lo, hi)
        d = fmt_date(date(rng.choice([2027, 2028]), m, rng.randint(1, 28)))
        FILL.note(c, d)
        head = "Will the temperature in" if i < 2 else "Is the temperature in"
        tail = "reach" if i < 2 else "going to reach"
        q.append(f"{head} {c} {tail} {t} degrees Celsius on {d}?")
    assets = ["Apple shares", "Tesla shares", "gold", "crude oil", "Bitcoin", "the S&P 500", "the FTSE 100",
              "the Nikkei 225", "silver", "copper", "wheat", "the euro-dollar rate", "Microsoft shares"]
    rng.shuffle(assets)
    q += slots(rng, "Will {x} close higher next Friday than it did this Friday?", 4, x=assets[:4])
    q += slots(rng, "Does {x} finish next month higher than it starts?", 6, x=assets[4:10])
    q += slots(rng, "Is {x} going to close higher tomorrow than it did today?", 3, x=assets[10:13])
    q += slots(rng, "Will {x} win the next football World Cup?", 3, x=["Brazil", "France", "Argentina"])
    q += slots(rng, "Is {x} going to win the next football World Cup?", 3, x=["Spain", "England", "Germany"])
    q += slots(rng, "Would {x} win the Rugby World Cup if it were held next year?", 4, x=["New Zealand", "South Africa", "France", "Ireland"])
    q += slots(rng, "Will {x} win the next Women's World Cup?", 2, x=["the United States", "Spain"])
    return add_all("future", q)


def build_private(rng):
    q: list[str] = []
    people = ["neighbour", "landlord", "boss", "sister", "best friend", "dentist", "cousin", "teacher", "uncle",
              "roommate", "barber", "plumber", "grandmother", "brother", "colleague"]
    q += slots(rng, "Is my {p} {s} right now?", 8, p=people,
               s=["asleep", "at work", "at home", "in a meeting", "on holiday", "having lunch",
                  "out walking the dog", "watching television", "on the train"])
    q += slots(rng, "Will my {p} reply to my {m} today?", 8,
               p=["landlord", "bank manager", "tutor", "manager", "old friend", "mother-in-law", "accountant",
                  "estate agent"],
               m=["email", "text message", "voicemail", "letter", "WhatsApp message", "note"])
    q += slots(rng, "Did I leave the {a} on?", 6,
               a=["oven", "iron", "hob", "heater", "kettle", "hair straighteners", "washing machine",
                  "coffee machine", "tumble dryer", "fan", "lights", "radio"])
    q += slots(rng, "Did I lock the {a}?", 6,
               a=["front door", "back door", "car", "garage", "shed", "bike", "office", "window"])
    q += slots(rng, "Does my {p} like my {t}?", 7,
               p=["boss", "mother", "neighbour", "date", "sister", "teacher", "father"],
               t=["new haircut", "cooking", "jokes", "new jacket", "garden", "singing", "handwriting", "new flat"])
    q += slots(rng, "Is there any {f} left in my {p}?", 5,
               f=["milk", "butter", "cheese", "bread", "coffee", "eggs", "rice"],
               p=["fridge", "cupboard", "freezer", "pantry", "bread bin", "lunchbox"])
    q += slots(rng, "Is my {i} still in my {p}?", 5,
               i=["passport", "wallet", "phone", "laptop", "umbrella", "diary"],
               p=["coat pocket", "bag", "car", "drawer", "desk", "hallway"])
    q += slots(rng, "Will my {t} arrive {w}?", 6,
               t=["parcel", "pizza", "new sofa", "tax refund", "exam results", "replacement card", "delivery"],
               w=["today", "before noon", "by Friday", "this week", "tomorrow morning", "after lunch"])
    q += slots(rng, "Is my {p} thinking about me right now?", 6,
               p=["ex", "boss", "mother", "grandfather", "old teacher", "cousin", "first love"])
    q += slots(rng, "Has my {p} noticed my {t}?", 6,
               p=["partner", "mother", "manager", "flatmate", "aunt", "landlady"],
               t=["new shoes", "weight loss", "mistake", "late arrival", "sunburn", "new phone"])
    q += slots(rng, "Does my {p} still have my {i}?", 4,
               p=["brother", "friend", "neighbour", "ex", "cousin", "uncle", "colleague", "sister"],
               i=["umbrella", "book", "charger", "bike", "ladder", "drill", "jacket", "DVD"])
    q += slots(rng, "Was my {p} {s} last night?", 4,
               p=["flatmate", "upstairs neighbour", "brother", "landlord", "aunt", "old friend"],
               s=["awake at midnight", "at home", "out drinking", "online", "alone"])
    q += slots(rng, "Can I trust my {p} with a secret?", 4,
               p=["neighbour", "cousin", "new boss", "roommate", "hairdresser", "nephew"])
    return add_all("private", q)


def build_taste(rng):
    q: list[str] = []
    pairs = [("Is", "jazz", "blues"), ("Are", "cats", "dogs"), ("Is", "tea", "coffee"), ("Is", "summer", "winter"),
             ("Are", "books", "films"), ("Is", "sweet food", "savoury food"), ("Are", "mountains", "beaches"),
             ("Is", "vinyl", "streaming"), ("Is", "spring", "autumn"), ("Is", "chocolate ice cream", "vanilla ice cream"),
             ("Is", "city life", "country life"), ("Is", "Beethoven", "Mozart"), ("Is", "football", "rugby"),
             ("Is", "pizza", "pasta"), ("Is", "sunrise", "sunset"), ("Is", "chess", "draughts"),
             ("Is", "rock music", "pop music"), ("Is", "tennis", "golf"), ("Is", "butter", "olive oil")]
    rng.shuffle(pairs)
    for v, a, b in pairs[:16]:
        FILL.note(a, b)
        q.append(f"{v} {a} better than {b}?")
    q += slots(rng, "Should I {a}?", 14,
               a=["paint my kitchen green", "quit my job", "get a dog", "learn the piano", "move to a bigger city",
                  "buy a bike", "dye my hair blue", "take up running", "adopt a cat", "learn French",
                  "go back to university", "sell my car", "write a novel", "start a podcast", "take a gap year",
                  "get a tattoo"])
    for adj, act in rng.sample([
            ("wrong", "eat meat"), ("rude", "wear shoes inside someone's home"),
            ("okay", "tell a white lie to spare a friend's feelings"), ("silly", "cry at a film"),
            ("selfish", "spend all my savings on a holiday"), ("lazy", "order takeaway every Friday"),
            ("fair", "split the bill equally when one person drank more"), ("rude", "reply to messages a week late"),
            ("strange", "talk to plants"), ("boring", "eat the same lunch every day")], 10):
        FILL.note(act)
        q.append(f"Is it {adj} to {act}?")
    q += slots(rng, "Is {x} overrated?", 10,
               x=["sushi", "Paris", "the Mona Lisa", "New Year's Eve", "Christmas", "brunch", "Bonfire Night",
                  "modern art", "coffee", "camping", "reality television"])
    for a, b in rng.sample([("green", "blue"), ("yellow", "orange"), ("purple", "pink"), ("red", "black"),
                            ("teal", "grey"), ("white", "cream"), ("turquoise", "lilac"), ("navy", "brown")], 8):
        FILL.note(a, b)
        q.append(f"Would a front door look nicer in {a} than in {b}?")
    for x, where in rng.sample([("pineapple", "on pizza"), ("raisins", "in a salad"), ("mint", "in chocolate"),
                                ("jam", "on a cheese sandwich"), ("cheese", "in an apple pie"),
                                ("mayonnaise", "on chips"), ("ketchup", "on a steak"), ("butter", "in coffee"),
                                ("honey", "on pizza")], 8):
        FILL.note(x)
        q.append(f"Does {x} belong {where}?")
    q += slots(rng, "Is it a good idea to {a}?", 5,
               a=["text my ex", "get a tattoo on my arm", "paint my front door red", "cut my own hair",
                  "go camping in October"])
    for x, cat in [("Italy", "country to visit"), ("Friday", "day of the week"), ("autumn", "season"),
                   ("Star Wars", "film series")]:
        FILL.note(x)
        q.append(f"Is {x} the best {cat}?")
    return add_all("taste", q)


def build_open(rng):
    q: list[str] = []
    q += slots(rng, "What is the capital of {c}?", 9,
               c=["France", "Japan", "Brazil", "Kenya", "Canada", "Norway", "Egypt", "Peru", "Australia", "India"])
    q += fixed(["Tell me a joke", "Tell me a story about a dragon", "Tell me a riddle", "Tell me a fun fact",
                "Tell me about your day", "Tell me a secret", "Tell me a poem about the sea",
                "Tell me your favourite word"])
    q += slots(rng, "Why is {x}?", 5, x=["the sky blue", "the sea salty", "grass green", "ice slippery", "the moon round"])
    q += slots(rng, "Why do {x}?", 5, x=["cats purr", "birds sing", "leaves fall in autumn", "onions make us cry", "we yawn"])
    q += fixed(["How many legs does a spider have?", "How many players are on a football team?",
                "How many days are in a leap year?", "How many hearts does an octopus have?",
                "How many minutes are in a day?"])
    q += slots(rng, "How do I {x}?", 5, x=["boil an egg", "tie a tie", "bake bread", "change a tyre", "learn to swim"])
    q += fixed(["Who wrote Pride and Prejudice?", "Who painted the Mona Lisa?", "Who discovered penicillin?",
                "Who composed the Four Seasons?", "Who was the first person on the Moon?",
                "Who invented the telephone?", "Who built the pyramids?", "Who painted the Sistine Chapel ceiling?"])
    for form, topic in rng.sample([("poem", "autumn"), ("haiku", "the sea"), ("limerick", "a cat"),
                                   ("short story", "a lighthouse"), ("song", "the rain"), ("poem", "my grandmother"),
                                   ("haiku", "a mountain"), ("story", "a lost umbrella"), ("limerick", "a baker")], 8):
        FILL.note(topic)
        q.append(f"Write a {form} about {topic}")
    q += fixed(["banana", "Tuesday", "umbrella", "purple", "elephant", "hello", "thanks", "chocolate"])
    q += fixed(["Explain photosynthesis", "Describe your perfect day", "List three fruits",
                "Define the word serendipity", "Summarise the plot of Hamlet", "Translate cat into Spanish",
                "Give me a name for a puppy"])
    q += fixed(["Where is Mount Everest?", "When was the printing press invented?",
                "Which is the longest river in Europe?", "What time is it in Tokyo?",
                "What is the boiling point of water?", "What colour is the sun?", "What rhymes with orange?"])
    return add_all("open", q)


# --------------------------------------------------------------------------------------------- main
BUILDERS = {
    "capital": build_capital, "arithmetic": build_arithmetic, "bigger": build_bigger, "number": build_number,
    "physical": build_physical, "animal": build_animal, "geo": build_geo, "chemistry": build_chemistry,
    "calendar": build_calendar, "word": build_word, "compare": build_compare, "history": build_history,
    "future": build_future, "private": build_private, "taste": build_taste, "open": build_open,
}


def build() -> list[dict]:
    """Return every item with id and split, in file order. Deterministic."""
    Bag.seen = set()
    FILL.use = Counter()
    items: list[dict] = []
    for kind in list(BUILDERS):
        items += BUILDERS[kind](random.Random(f"{SEED}:{kind}"))
    rng = random.Random(f"{SEED}:shuffle")
    # stratified split: about one third dev, the rest test, for every kind and label
    groups = defaultdict(list)
    for it in items:
        groups[(it["kind"], it["label"])].append(it)
    for key in sorted(groups):
        g = groups[key]
        rng.shuffle(g)
        n_dev = max(1, round(len(g) / 3))
        for i, it in enumerate(g):
            it["split"] = "dev" if i < n_dev else "test"
    rng.shuffle(items)
    counter = Counter()
    out = []
    for it in items:
        counter[it["kind"]] += 1
        out.append({"id": f"{PREFIX[it['kind']]}-{counter[it['kind']]:04d}", "question": it["question"],
                    "label": it["label"], "kind": it["kind"], "split": it["split"]})
    return out


def main() -> None:
    items = build()
    with OUT.open("w", encoding="utf-8") as f:
        for it in items:
            f.write(json.dumps(it, ensure_ascii=False) + "\n")
    by = Counter((it["kind"], it["label"]) for it in items)
    print(f"wrote {len(items)} items to {OUT}")
    print("labels:", dict(Counter(it["label"] for it in items)))
    print("splits:", dict(Counter(it["split"] for it in items)))
    for kind in YESNO_KINDS + MAYBE_KINDS:
        print(f"  {kind:11s} yes={by[(kind, 'yes')]:3d} no={by[(kind, 'no')]:3d} maybe={by[(kind, 'maybe')]:3d}")


if __name__ == "__main__":
    main()
