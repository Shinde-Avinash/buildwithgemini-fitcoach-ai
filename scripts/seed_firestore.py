"""Seed script to populate Firestore 'exercises' collection with sample items for FitCoach AI.

Project ID is hardcoded as required.
"""

from google.cloud import firestore

PROJECT_ID = "qwiklabs-gcp-01-426fafba1fca"

SEED_EXERCISES = [
    {
        "name": "Barbell Back Squat",
        "category": "Strength",
        "target_muscle": "Legs",
        "difficulty": "Intermediate",
        "description": "Compound lower body movement targeting quadriceps, hamstrings, and glutes. Keep spine neutral and break parallel.",
    },
    {
        "name": "Push-up Intervals",
        "category": "Bodyweight",
        "target_muscle": "Chest",
        "difficulty": "Beginner",
        "description": "Bodyweight chest and tricep movement. Perform 4 sets of 15-20 reps with 45s rest.",
    },
    {
        "name": "Zone 2 Endurance Run",
        "category": "Cardio",
        "target_muscle": "Full Body",
        "difficulty": "Intermediate",
        "description": "Steady-state aerobic run keeping heart rate between 60-70% max HR (Zone 2) for 45-60 minutes.",
    },
    {
        "name": "Romanian Deadlift",
        "category": "Strength",
        "target_muscle": "Hamstrings",
        "difficulty": "Intermediate",
        "description": "Hinge movement emphasizing posterior chain and glute activation. Soft knee bend with hip hinge.",
    },
    {
        "name": "Plank & Core Circuit",
        "category": "Bodyweight",
        "target_muscle": "Core",
        "difficulty": "Beginner",
        "description": "Isometric core stability exercise combined with mountain climbers and side planks.",
    },
]

def seed_database():
    db = firestore.Client(project=PROJECT_ID)
    collection_ref = db.collection("exercises")

    print(f"Seeding Firestore collection 'exercises' in project '{PROJECT_ID}'...")
    for exercise in SEED_EXERCISES:
        # Query if exercise already exists by name
        existing = collection_ref.where("name", "==", exercise["name"]).get()
        if not list(existing):
            doc_ref = collection_ref.document()
            doc_ref.set(exercise)
            print(f"  + Added: {exercise['name']} (Doc ID: {doc_ref.id})")
        else:
            print(f"  = Skipped existing: {exercise['name']}")

    print("Seeding completed successfully!")

if __name__ == "__main__":
    seed_database()
