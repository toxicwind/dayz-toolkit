import random

ADJECTIVES = [
    "Neon",
    "Shadow",
    "Crimson",
    "Azure",
    "Ghost",
    "Iron",
    "Silent",
    "Rapid",
    "Feral",
    "Toxic",
    "Radioactive",
    "Vengeful",
    "Dark",
    "Solar",
    "Lunar",
    "Cyber",
    "Rogue",
    "Elite",
    "Prime",
    "Lost",
    "Wandering",
    "Savage",
    "Echo",
    "Phantom",
    "Cobalt",
    "Hidden",
    "Mystic",
    "Fallen",
    "Rising",
]

NOUNS = [
    "Viper",
    "Fox",
    "Wolf",
    "Eagle",
    "Bear",
    "Shark",
    "Raven",
    "Hawk",
    "Tiger",
    "Lion",
    "Cobra",
    "Dragon",
    "Phoenix",
    "Spectre",
    "Stalker",
    "Nomad",
    "Hunter",
    "Scout",
    "Ranger",
    "Survivor",
    "Bandit",
    "Medic",
    "Sniper",
    "Pilot",
    "Driver",
    "Operator",
    "Agent",
    "Ghost",
    "Soul",
]


def generate_codename() -> str:
    """Generates a random codename (e.g., 'Neon Viper')."""
    adj = random.choice(ADJECTIVES)
    noun = random.choice(NOUNS)
    return f"{adj} {noun}"


if __name__ == "__main__":
    print(generate_codename())
