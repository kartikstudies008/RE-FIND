import sys
from datetime import date, time

if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from app import create_app
from app.models import db, User, Item, Match, Report, Notification
from app.matching import MatchingEngine

app = create_app()

def seed_database():
    with app.app_context():
        print("[*] Seeding database for ReFind AI...")

        # Create all tables if not exist
        db.create_all()

        # Clean existing data to ensure clean state
        Notification.query.delete()
        Report.query.delete()
        Match.query.delete()
        Item.query.delete()
        User.query.delete()
        db.session.commit()

        # 1. Seed Users
        admin_user = User(
            name="System Administrator",
            email="admin@refind.com",
            phone="+91 9999900000",
            role="ADMIN"
        )
        admin_user.set_password("admin123")

        user1 = User(
            name="Rahul Sharma",
            email="user1@refind.com",
            phone="+91 9876543210",
            role="USER"
        )
        user1.set_password("password123")

        user2 = User(
            name="Priya Verma",
            email="user2@refind.com",
            phone="+91 9811223344",
            role="USER"
        )
        user2.set_password("password123")

        user3 = User(
            name="Aman Gupta",
            email="user3@refind.com",
            phone="+91 9755443322",
            role="USER"
        )
        user3.set_password("password123")

        db.session.add_all([admin_user, user1, user2, user3])
        db.session.commit()
        print(f"✓ Created 4 demo users (admin@refind.com, user1@refind.com, user2@refind.com, user3@refind.com)")

        # 2. Seed Items

        # Scenario A (From Prompt Specifications):
        # Lost: Black Dell Laptop at Panipat Railway Station
        lost_laptop = Item(
            user_id=user1.id,
            type="lost",
            item_name="Black Dell Laptop",
            category="Electronics",
            description="Black Dell laptop with red sticker on the back",
            color="Black",
            brand="Dell",
            location="Panipat Railway Station",
            date=date(2026, 9, 10),
            time=time(14, 30),
            status="active"
        )

        # Found: Dell Laptop near Panipat Railway Station
        found_laptop = Item(
            user_id=user2.id,
            type="found",
            item_name="Dell Laptop",
            category="Electronics",
            description="Dell black laptop having a red sticker",
            color="Black",
            brand="Dell",
            location="Near Panipat Railway Station",
            date=date(2026, 9, 10),
            time=time(16, 0),
            status="active"
        )

        # Scenario B:
        # Lost: Titan Brown Leather Wallet
        lost_wallet = Item(
            user_id=user2.id,
            type="lost",
            item_name="Brown Leather Wallet",
            category="Wallet",
            description="Men's brown genuine leather Titan wallet with college ID card inside",
            color="Brown",
            brand="Titan",
            location="Central Metro Station Platform 1",
            date=date(2026, 9, 8),
            time=time(9, 15),
            status="active"
        )

        # Found: Brown Wallet
        found_wallet = Item(
            user_id=user3.id,
            type="found",
            item_name="Titan Brown Wallet",
            category="Wallet",
            description="Brown Titan leather wallet picked up from seating bench",
            color="Brown",
            brand="Titan",
            location="Central Metro Station Gate 2",
            date=date(2026, 9, 8),
            time=time(10, 30),
            status="active"
        )

        # Scenario C:
        # Blue Apple iPhone 14
        lost_phone = Item(
            user_id=user3.id,
            type="lost",
            item_name="iPhone 14 Blue",
            category="Mobile Phone",
            description="Apple iPhone 14 blue color in transparent silicone case with cracked screen protector",
            color="Blue",
            brand="Apple",
            location="University Central Library 2nd Floor",
            date=date(2026, 9, 9),
            time=time(11, 45),
            status="active"
        )

        found_phone = Item(
            user_id=user1.id,
            type="found",
            item_name="Blue Apple iPhone",
            category="Mobile Phone",
            description="Found an iPhone in blue color with clear case on library study desk",
            color="Blue",
            brand="Apple",
            location="University Library Reading Hall",
            date=date(2026, 9, 9),
            time=time(13, 0),
            status="active"
        )

        # Scenario D (Resolved Reunion Example):
        reunited_bag_lost = Item(
            user_id=user1.id,
            type="lost",
            item_name="Wildcraft Black Backpack",
            category="Bags",
            description="Black water-resistant college backpack with water bottle pocket",
            color="Black",
            brand="Wildcraft",
            location="Engineering Block Cafeteria",
            date=date(2026, 9, 5),
            status="resolved"
        )

        reunited_bag_found = Item(
            user_id=user3.id,
            type="found",
            item_name="Wildcraft Backpack",
            category="Bags",
            description="Wildcraft black backpack left behind at cafeteria table",
            color="Black",
            brand="Wildcraft",
            location="Campus Cafeteria",
            date=date(2026, 9, 5),
            status="resolved"
        )

        db.session.add_all([
            lost_laptop, found_laptop,
            lost_wallet, found_wallet,
            lost_phone, found_phone,
            reunited_bag_lost, reunited_bag_found
        ])
        db.session.commit()
        print("[+] Created demo lost and found items across 4 scenarios")

        # 3. Trigger Matching Engine across all items
        print("[AI] Running AI Matching Engine on seeded items...")
        for itm in [lost_laptop, lost_wallet, lost_phone]:
            matches = MatchingEngine.sync_item_matches(itm, db.session, threshold=60.0)
            print(f"  Matched Item #{itm.id} ({itm.item_name}) -> Found {len(matches)} match(es)")

        # Create a sample report for admin moderation showcase
        report = Report(
            item_id=found_phone.id,
            reported_by=user2.id,
            reason="Suspected duplicate listing filed earlier.",
            status="pending"
        )
        db.session.add(report)
        db.session.commit()
        print("[+] Created sample report for admin moderation")

        # Display Top Match Score for Scenario A
        target_match = Match.query.filter_by(
            lost_item_id=lost_laptop.id,
            found_item_id=found_laptop.id
        ).first()

        if target_match:
            print("=" * 60)
            print("[TARGET MATCH] VERIFIED SCENARIO A MATCH (Dell Laptop at Panipat):")
            print(f"   Final Match Score: {target_match.match_score}% ({target_match.confidence_label})")
            print(f"   - Category Score:    {target_match.category_score}% (weight: 25%)")
            print(f"   - Location Score:    {target_match.location_score}% (weight: 20%)")
            print(f"   - Date Score:        {target_match.date_score}% (weight: 15%)")
            print(f"   - Color Score:       {target_match.color_score}% (weight: 10%)")
            print(f"   - Brand Score:       {target_match.brand_score}% (weight: 10%)")
            print(f"   - Description Score: {target_match.description_score}% (weight: 20%)")
            print("=" * 60)

        print("[SUCCESS] Database successfully initialized and seeded with demo data!")

if __name__ == '__main__':
    seed_database()
