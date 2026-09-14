import sys
import unittest
from datetime import date
from io import BytesIO

if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from app import create_app
from app.models import db, User, Item, Match, Notification, Report
from config import Config


class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False
    SERVER_NAME = 'localhost.localdomain'


class ReFindAITestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestConfig)
        self.app_context = self.app.app_context()
        self.app_context.push()
        self.client = self.app.test_client(use_cookies=True)
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def register_user(self, name, email, phone, password):
        return self.client.post('/auth/register', data={
            'name': name,
            'email': email,
            'phone': phone,
            'password': password,
            'confirm_password': password
        }, follow_redirects=True)

    def login_user(self, email, password):
        return self.client.post('/auth/login', data={
            'email': email,
            'password': password
        }, follow_redirects=True)

    def logout_user(self):
        return self.client.get('/auth/logout', follow_redirects=True)

    # -------------------------------------------------------------
    # 1. Authentication & Security Tests
    # -------------------------------------------------------------
    def test_user_registration_and_duplicate_email(self):
        resp = self.register_user("Alice User", "alice@example.com", "9876543210", "secret123")
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"Welcome to ReFind AI, Alice User!", resp.data)

        user = User.query.filter_by(email="alice@example.com").first()
        self.assertIsNotNone(user)
        self.assertTrue(user.check_password("secret123"))
        self.assertFalse(user.check_password("wrongpassword"))

        # Try registering duplicate email
        self.logout_user()
        dup_resp = self.register_user("Alice Clone", "alice@example.com", "9876543210", "secret123")
        self.assertIn(b"An account with this email already exists.", dup_resp.data)

    def test_invalid_login(self):
        self.register_user("Bob User", "bob@example.com", "9876543210", "secret123")
        self.logout_user()

        resp = self.login_user("bob@example.com", "wrongpassword")
        self.assertIn(b"Invalid email address or password", resp.data)

    # -------------------------------------------------------------
    # 2. Complete End-To-End User Matching & Reunion Flow
    # -------------------------------------------------------------
    def test_end_to_end_matching_and_reunion_workflow(self):
        # Step 1: Register User A
        self.register_user("User A", "usera@example.com", "9900112233", "pass1234")
        user_a = User.query.filter_by(email="usera@example.com").first()

        # Step 2: User A reports Lost Laptop
        resp_lost = self.client.post('/report-lost', data={
            'item_name': 'Black Dell Inspiron 15',
            'category': 'Electronics',
            'description': 'Black Dell laptop with red dragon sticker on top lid and scratches on hinge',
            'color': 'Black',
            'brand': 'Dell',
            'location': 'Panipat Railway Station Platform 1',
            'date': '2026-09-10'
        }, follow_redirects=True)
        self.assertEqual(resp_lost.status_code, 200)

        lost_item = Item.query.filter_by(user_id=user_a.id, type='lost').first()
        self.assertIsNotNone(lost_item)
        self.assertEqual(lost_item.item_name, 'Black Dell Inspiron 15')
        self.assertEqual(lost_item.status, 'active')

        # Step 3: Register User B
        self.logout_user()
        self.register_user("User B", "userb@example.com", "9944556677", "pass1234")
        user_b = User.query.filter_by(email="userb@example.com").first()

        # Step 4: User B reports Found Laptop with matching details
        resp_found = self.client.post('/report-found', data={
            'item_name': 'Dell Laptop',
            'category': 'Electronics',
            'description': 'Found a black Dell laptop having a red sticker on the back cover',
            'color': 'Black',
            'brand': 'Dell',
            'location': 'Near Panipat Railway Station Ticket Counter',
            'date': '2026-09-10'
        }, follow_redirects=True)
        self.assertEqual(resp_found.status_code, 200)

        found_item = Item.query.filter_by(user_id=user_b.id, type='found').first()
        self.assertIsNotNone(found_item)

        # Step 5 & 6: Verify match generated automatically above 60%
        match = Match.query.filter_by(lost_item_id=lost_item.id, found_item_id=found_item.id).first()
        self.assertIsNotNone(match)
        self.assertGreaterEqual(match.match_score, 60.0)
        self.assertEqual(match.status, 'suggested')
        print(f"\n[TEST SUCCESS] Match Score: {match.match_score}% (Confidence: {match.confidence_label})")

        # Step 7: Verify notifications were sent to both users
        notif_a = Notification.query.filter_by(user_id=user_a.id).first()
        notif_b = Notification.query.filter_by(user_id=user_b.id).first()
        self.assertIsNotNone(notif_a)
        self.assertIsNotNone(notif_b)
        self.assertIn("Match", notif_a.title)

        # Step 8: User A logs in, views suggested matches & details
        self.logout_user()
        self.login_user("usera@example.com", "pass1234")

        resp_matches = self.client.get('/matches')
        self.assertEqual(resp_matches.status_code, 200)
        self.assertIn(b"AI Suggested Matches", resp_matches.data)
        self.assertIn(found_item.item_name.encode('utf-8'), resp_matches.data)

        resp_details = self.client.get(f'/item/{lost_item.id}')
        self.assertEqual(resp_details.status_code, 200)
        self.assertIn(b"AI Suggested Matches for this Item", resp_details.data)

        # Step 9: User A contacts User B
        resp_contact = self.client.post(f'/item/{found_item.id}/contact', data={
            'subject': 'Claiming my Dell Laptop',
            'message': 'Hi, that is my laptop! It has my college notes on the desktop. Can we meet at the station?'
        }, follow_redirects=True)
        self.assertEqual(resp_contact.status_code, 200)
        self.assertIn(b"Your inquiry has been sent", resp_contact.data)

        # Step 10: User A accepts the match
        resp_accept = self.client.post(f'/match/{match.id}/action', data={
            'action': 'accept'
        }, follow_redirects=True)
        self.assertEqual(resp_accept.status_code, 200)

        match_updated = Match.query.get(match.id)
        self.assertEqual(match_updated.status, 'accepted')

        # Step 11: Mark as Resolved (Reunited)
        resp_resolve = self.client.post(f'/item/{lost_item.id}/resolve', follow_redirects=True)
        self.assertEqual(resp_resolve.status_code, 200)
        self.assertIn(b"Item Reunited Successfully", resp_resolve.data)

        lost_item_refreshed = Item.query.get(lost_item.id)
        found_item_refreshed = Item.query.get(found_item.id)
        self.assertEqual(lost_item_refreshed.status, 'resolved')
        self.assertEqual(found_item_refreshed.status, 'resolved')

        # Step 12: Verify dashboard counts reflect resolution
        resp_dash = self.client.get('/dashboard')
        self.assertIn(b"Resolved", resp_dash.data)

    # -------------------------------------------------------------
    # 3. Authorization & Permissions
    # -------------------------------------------------------------
    def test_unauthorized_item_deletion(self):
        self.register_user("User One", "one@example.com", "9911223344", "pass1234")
        item1 = Item(
            user_id=1,
            type='lost',
            item_name='Keys',
            category='Keys',
            description='House keys with red keychain',
            location='Bus Stand',
            date=date(2026, 9, 10)
        )
        db.session.add(item1)
        db.session.commit()

        # User Two cannot delete User One's item
        self.logout_user()
        self.register_user("User Two", "two@example.com", "9955667788", "pass1234")
        resp = self.client.post(f'/item/{item1.id}/delete', follow_redirects=True)
        self.assertIn(b"Unauthorized action", resp.data)
        self.assertIsNotNone(Item.query.get(item1.id))

    def test_admin_panel_access_control(self):
        # Regular user should receive 403 Forbidden
        self.register_user("Regular User", "regular@example.com", "9911223344", "pass1234")
        resp_reg = self.client.get('/admin/')
        self.assertEqual(resp_reg.status_code, 403)

        # Admin user should get 200 OK
        self.logout_user()
        admin = User(name="Admin", email="admin@example.com", phone="9999999999", role="ADMIN")
        admin.set_password("adminpass")
        db.session.add(admin)
        db.session.commit()

        self.login_user("admin@example.com", "adminpass")
        resp_admin = self.client.get('/admin/')
        self.assertEqual(resp_admin.status_code, 200)
        self.assertIn(b"Platform Overview &amp; Moderation", resp_admin.data)

    # -------------------------------------------------------------
    # 4. Search, Filter & API Endpoints
    # -------------------------------------------------------------
    def test_search_filter_and_apis(self):
        u = User(name="Test User", email="test@test.com", phone="9988776655", role="USER")
        u.set_password("password")
        db.session.add(u)
        db.session.commit()

        item = Item(
            user_id=u.id,
            type='lost',
            item_name='MacBook Pro M2',
            category='Laptop',
            description='Space gray Apple MacBook Pro 14 inch',
            color='Space Gray',
            brand='Apple',
            location='Library Hall C',
            date=date(2026, 9, 10),
            status='active'
        )
        db.session.add(item)
        db.session.commit()

        # Test Search by keyword
        resp_search = self.client.get('/browse?q=MacBook')
        self.assertEqual(resp_search.status_code, 200)
        self.assertIn(b"MacBook Pro M2", resp_search.data)

        # Test Filter by non-matching keyword
        resp_miss = self.client.get('/browse?q=SamsungGalaxy')
        self.assertNotIn(b"MacBook Pro M2", resp_miss.data)

        # Test API Stats
        resp_api_stats = self.client.get('/api/stats')
        self.assertEqual(resp_api_stats.status_code, 200)
        self.assertIn(b'"total_lost": 1', resp_api_stats.data)

        # Test API Items
        resp_api_items = self.client.get('/api/items')
        self.assertEqual(resp_api_items.status_code, 200)
        self.assertIn(b'MacBook Pro M2', resp_api_items.data)


if __name__ == '__main__':
    unittest.main()
