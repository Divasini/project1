"""
Seed script — inserts the 4 hardcoded "Trending Ideas" from index.html
into the real database so they also appear on ideas.html.

Run this from inside your backend folder:
    python seed_ideas.py
"""

from database import SessionLocal
from models import User, Idea

db = SessionLocal()

# 1. Make sure we have an author to attach these ideas to.
#    Uses/creates a demo system user called "StartupSphere Team".
author = db.query(User).filter(User.email == "team@startupsphere.com").first()
if not author:
    author = User(
        name="StartupSphere Team",
        email="team@startupsphere.com",
        password_hash="not_a_real_login",   # placeholder, this account is not meant to log in
        bio="Official StartupSphere seed account",
        is_verified=True,
    )
    db.add(author)
    db.commit()
    db.refresh(author)
    print(f"Created author user id={author.id}")
else:
    print(f"Using existing author user id={author.id}")

# 2. The 4 trending ideas from index.html
seed_ideas = [
    {
        "title": "AI Tutor App",
        "category": "AI",
        "problem": "Students often lack access to affordable, personalized academic support.",
        "solution": "Smart AI learning assistant that adapts to each student's pace and learning style.",
        "views": 1200,
    },
    {
        "title": "Smart Farming",
        "category": "IoT",
        "problem": "Farmers struggle to optimize water, soil, and crop conditions in real time.",
        "solution": "IoT agriculture system that monitors farm conditions and automates irrigation/alerts.",
        "views": 900,
    },
    {
        "title": "Freelance Hub",
        "category": "Marketplace",
        "problem": "Freelancers and startups find it hard to discover and vet each other efficiently.",
        "solution": "A marketplace that connects freelancers & startups with verified profiles and reviews.",
        "views": 2100,
    },
    {
        "title": "Eco Delivery",
        "category": "Green",
        "problem": "Traditional last-mile delivery has a heavy carbon footprint.",
        "solution": "Green logistics platform using electric vehicles and optimized eco-friendly routes.",
        "views": 650,
    },
]

for item in seed_ideas:
    exists = db.query(Idea).filter(Idea.title == item["title"]).first()
    if exists:
        print(f"Skipping (already exists): {item['title']}")
        continue

    idea = Idea(
        title=item["title"],
        category=item["category"],
        problem=item["problem"],
        solution=item["solution"],
        views=item["views"],
        status="published",
        author_id=author.id,
    )
    db.add(idea)
    print(f"Added idea: {item['title']}")

db.commit()
db.close()
print("Done. Refresh ideas.html to see them.")