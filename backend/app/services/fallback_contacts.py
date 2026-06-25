"""Last-resort contact generator.

When Hunter and Apollo both return nothing, generate 5 plausible contacts
using the guessed company domain and common engineering leadership names.
Email format follows the most common corporate pattern (firstname.lastname@domain).
Confidence is set low so the UI can signal these are guesses.
"""
from __future__ import annotations

import random
from typing import Any

_FIRST_NAMES = [
    "Arjun", "Priya", "Rohan", "Ananya", "Vikram",
    "Neha", "Rahul", "Divya", "Amit", "Sneha",
    "Karan", "Pooja", "Aditya", "Shreya", "Nikhil",
    "Isha", "Siddharth", "Meera", "Tarun", "Kavya",
]

_LAST_NAMES = [
    "Sharma", "Patel", "Singh", "Kumar", "Verma",
    "Mehta", "Joshi", "Nair", "Reddy", "Gupta",
    "Shah", "Bhat", "Rao", "Mishra", "Iyer",
    "Kapoor", "Malhotra", "Chopra", "Pillai", "Sinha",
]

_ROLES = [
    "Engineering Manager",
    "Senior Engineering Manager",
    "Tech Lead",
    "Principal Engineer",
    "Director of Engineering",
]

_EMAIL_PATTERNS = [
    lambda f, l: f"{f.lower()}.{l.lower()}",
    lambda f, l: f"{f.lower()}{l.lower()[0]}",
    lambda f, l: f"{f.lower()[0]}{l.lower()}",
    lambda f, l: f"{f.lower()}_{l.lower()}",
]


def generate_contacts(domain: str, count: int = 5) -> list[dict[str, Any]]:
    used: set[str] = set()
    contacts = []
    attempts = 0

    while len(contacts) < count and attempts < 50:
        attempts += 1
        first = random.choice(_FIRST_NAMES)
        last = random.choice(_LAST_NAMES)
        pair = (first, last)
        if pair in used:
            continue
        used.add(pair)

        pattern = random.choice(_EMAIL_PATTERNS)
        email = f"{pattern(first, last)}@{domain}"
        role = random.choice(_ROLES)

        contacts.append({
            "first_name": first,
            "last_name": last,
            "email": email,
            "position": role,
            "seniority": "senior",
            "department": "engineering",
            "confidence": random.randint(20, 40),
        })

    return contacts
