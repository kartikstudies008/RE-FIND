# ReFind AI – Intelligent Lost & Found Matching Platform

> **Tagline:** *Lost. Found. Reunited.*  
> **Target Audience:** College final-year / minor projects, smart campus initiatives, public transit authorities, and community lost & found networks.

---

## 1. Project Overview

**ReFind AI** is a centralized full-stack web platform designed to eliminate the friction of lost and found recovery. Rather than relying on static bulletin boards or endless manual scrolling, ReFind AI employs an intelligent machine-learning-inspired matching engine. 

When a user submits a report for a lost or found item, the system automatically compares multi-attribute metadata and applies **Natural Language Processing (TF-IDF vectorization and Cosine Similarity)** to uncover high-confidence matches in real time, notifying both parties and enabling secure communication until the item is reunited.

---

## 2. Core Features

- **User Authentication & Role Management:**
  - Secure registration, login, session persistence, and profile management.
  - Role-Based Access Control (`USER` vs `ADMIN`).
  - Passwords hashed using cryptographic `Werkzeug` PBKDF2 with SHA-256 salts.
- **Intelligent Lost & Found Reporting:**
  - Standardized reporting forms across 11 key categories (*Electronics, Documents, Wallet, Mobile Phone, Laptop, Keys, Bags, Clothing, Accessories, Books, Other*).
  - Secure image uploads (`.jpg`, `.jpeg`, `.png`, `.webp`) stored in `/static/uploads/` with UUID-based obfuscated filenames.
- **Intelligent Multi-Attribute Matching Algorithm:**
  - Dynamic weighted scoring across Category (25%), Location (20%), Date (15%), Color (10%), Brand (10%), and Description (20%).
  - Text normalization, token extraction, and **TF-IDF + Cosine Similarity** (`scikit-learn`).
  - Configurable confidence threshold (default: **60%**) with intuitive classification badges (*Very Strong Match*, *Strong Match*, *Possible Match*).
- **Match Management & In-App Notifications:**
  - Dedicated "AI Suggested Matches" dashboard with visual item pairs and attribute breakdown checklists.
  - Instant notification alerts generated upon pair creation.
  - "Accept Match" and "Reject Match" interactive workflows.
- **Safe Community Contact & Item Resolution:**
  - Privacy-preserving contact modal to send direct inquiries without exposing raw phone numbers publicly.
  - One-click "Mark as Resolved" action that celebrates reunion and updates community statistics.
- **Admin Moderation Console:**
  - Comprehensive platform analytics and reunion success rate metrics.
  - Community listing moderation (view, flag suspicious items, delete inappropriate entries).
  - User management and role switching.
  - Flagged report review and resolution.
- **REST API Endpoints:**
  - `/api/stats`: Live platform metrics.
  - `/api/items`: Filterable JSON listings.
  - `/api/matches`: Top AI suggestions with score breakdowns.

---

## 3. Technology Stack

| Layer | Technology | Purpose |
|---|---|---|
| **Frontend** | HTML5, CSS3, JavaScript (ES6) | Semantic layout, asynchronous fetch calls, live photo preview |
| **Styling** | Bootstrap 5.3, Bootstrap Icons, Custom CSS | Modern startup design system, glassmorphism, responsive cards |
| **Backend** | Python 3.10+, Flask 3.0+ | Modular application architecture using Blueprints |
| **ORM & DB** | Flask-SQLAlchemy 3.1+, PyMySQL | Relational database mapping, parameterized queries |
| **Database** | MySQL 8.0+ *(with graceful SQLite dev fallback)* | Persistent relational storage with foreign keys and indexes |
| **AI / NLP** | `scikit-learn`, `numpy`, `scipy` | TF-IDF Vectorization, Cosine Similarity, token overlap |
| **Forms & Security** | Flask-WTF, WTForms, Werkzeug | CSRF protection, file upload validation, password hashing |

---

## 4. System Architecture

```text
                                  +-----------------------+
                                  |    Client Browser     |
                                  | (Desktop, Tablet, Mob)|
                                  +-----------+-----------+
                                              | HTTP/HTTPS
                                              v
+-----------------------------------------------------------------------------------+
|                                 Flask Backend                                      |
|                                                                                   |
|  +--------------------+   +--------------------+   +---------------------------+  |
|  |    Auth Blueprint  |   |    Main Blueprint  |   |      Admin Blueprint      |  |
|  |  /auth/login       |   |  / (Home)          |   |  /admin/ (Overview)       |  |
|  |  /auth/register    |   |  /browse, /items   |   |  /admin/users             |  |
|  |  /auth/profile     |   |  /report-lost      |   |  /admin/items             |  |
|  |  /auth/logout      |   |  /report-found     |   |  /admin/reports           |  |
|  +--------------------+   |  /dashboard        |   +---------------------------+  |
|                           |  /matches          |                                  |
|                           +---------+----------+                                  |
|                                     |                                             |
|                                     v                                             |
|                     +-------------------------------+                             |
|                     |   Intelligent Matching Engine |                             |
|                     |   (app/matching.py)           |                             |
|                     |   - TF-IDF Vectorizer         |                             |
|                     |   - Cosine Similarity         |                             |
|                     |   - Multi-Attribute Weights   |                             |
|                     +---------------+---------------+                             |
+-------------------------------------|---------------------------------------------+
                                      |
                                      v
                       +-----------------------------+
                       |    Relational Database      |
                       |    (MySQL 8.0 / SQLite)     |
                       |    - users      - items     |
                       |    - matches    - reports   |
                       |    - notifications          |
                       +-----------------------------+
```

---

## 5. Database Design

The schema is defined in `schema.sql` and mapped via `app/models.py`:

```
+------------------+         +-------------------------+         +-----------------------+
|      users       |         |          items          |         |        matches        |
+------------------+         +-------------------------+         +-----------------------+
| id (PK)          |<---+    | id (PK)                 |<---+    | id (PK)               |
| name             |    +----| user_id (FK)            |    +----| lost_item_id (FK)     |
| email (Unique)   |         | type (lost/found)       |    +----| found_item_id (FK)    |
| phone            |         | item_name               |         | match_score           |
| password_hash    |         | category                |         | category_score        |
| role (USER/ADMIN)|         | description             |         | location_score        |
| created_at       |         | color, brand, location  |         | date_score            |
+------------------+         | date, time, image_path  |         | color_score           |
         |                   | status, is_flagged      |         | brand_score           |
         |                   | created_at              |         | description_score     |
         |                   +-------------------------+         | status, created_at    |
         |                                |                      +-----------------------+
         |                                v
         |                   +-------------------------+
         |                   |         reports         |
         |                   +-------------------------+
         |                   | id (PK)                 |
         +------------------>| reported_by (FK)        |
                             | item_id (FK)            |
                             | reason, status, date    |
                             +-------------------------+
```

---

## 6. Intelligent Matching Algorithm

The matching service calculates a normalized composite similarity score $S_{total} \in [0, 100]$ between a **Lost Item** and a **Found Item** according to the following formula:

$$S_{total} = (0.25 \times S_{cat}) + (0.20 \times S_{loc}) + (0.15 \times S_{date}) + (0.10 \times S_{color}) + (0.10 \times S_{brand}) + (0.20 \times S_{desc})$$

### Attribute Score Breakdown:

1. **Category Similarity ($S_{cat}$ – 25%):**
   - Exact string match = $100\%$.
   - Cross-category compatible hierarchy (e.g. *Laptop* vs *Electronics*) = $70\%$.
   - Mismatch = $0\%$.

2. **Location Similarity ($S_{loc}$ – 20%):**
   - Combines normalized token set Jaccard similarity and substring containment bonus:
     $$\text{Jaccard}(A, B) = \frac{|A \cap B|}{|A \cup B|} \times 100$$
   - Variations like *"Panipat Railway Station"* vs *"Near Panipat Railway Station"* yield $\ge 92\%$.

3. **Date Proximity ($S_{date}$ – 15%):**
   - Temporal decay function based on difference $\Delta d = |d_{lost} - d_{found}|$:
     - $\Delta d = 0$ days $\rightarrow 100\%$
     - $\Delta d = 1$ day $\rightarrow 90\%$
     - $\Delta d \le 3$ days $\rightarrow 75\%$
     - $\Delta d \le 7$ days $\rightarrow 50\%$
     - $\Delta d \le 14$ days $\rightarrow 30\%$
     - $\Delta d > 30$ days $\rightarrow 0\%$

4. **Color & Brand Similarity ($S_{color}, S_{brand}$ – 10% each):**
   - Normalized token intersection with fallback inspection into item names and descriptions.

5. **Description Similarity via TF-IDF + Cosine Similarity ($S_{desc}$ – 20%):**
   - Both descriptions and item titles are normalized (lowercased, punctuation removed, stopwords pruned).
   - Term Frequency-Inverse Document Frequency vectors $\vec{v}_{lost}, \vec{v}_{found}$ are fitted using `scikit-learn`.
   - Cosine angle similarity is computed:
     $$\text{Cosine Sim} = \frac{\vec{v}_{lost} \cdot \vec{v}_{found}}{\|\vec{v}_{lost}\|_2 \|\vec{v}_{found}\|_2} \times 100$$

### Match Confidence Tiers:
- **$\ge 80\%$**: *Very Strong Match* (Top recommendation)
- **$60\% - 79\%$**: *Strong Match* (Recommended pairing)
- **$40\% - 59\%$**: *Possible Match*
- **$< 40\%$**: Weak (filtered out by default threshold)

---

## 7. Installation & Setup Instructions

### Prerequisites
- Python 3.10+ installed
- MySQL Server 8.0+ (Optional: SQLite fallback works automatically out-of-the-box)
- pip package manager

### Step 1: Clone or Navigate to Project Directory
```bash
cd c:\Users\karti\OneDrive\Desktop\REFIND
```

### Step 2: Install Required Dependencies
```bash
pip install -r requirements.txt
```

### Step 3: Configure Environment Variables
Copy `.env.example` to `.env`:
```bash
copy .env.example .env
```
Inside `.env`, configure your database credentials:
```ini
SECRET_KEY=refind-ai-dev-secret-key-9a8f237bc8104e76a
FLASK_ENV=development
FLASK_DEBUG=1

# MySQL Configuration
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=your_mysql_password
MYSQL_DATABASE=refind_db

# Matching Threshold
MATCH_THRESHOLD=60.0
```

> **Note on Zero-Configuration Local Testing:**  
> If MySQL server is not currently running on your local machine, ReFind AI's connection health check will automatically and gracefully fall back to a local SQLite database (`refind.db`) without throwing errors.

---

## 8. MySQL Database Setup (Optional)

If running MySQL Server directly:
1. Open MySQL Workbench or MySQL Shell:
   ```bash
   mysql -u root -p
   ```
2. Import the schema script:
   ```sql
   source schema.sql;
   ```

---

## 9. Seeding Demo Data & Testing Scenarios

ReFind AI comes with a built-in demo data generator that populates realistic lost and found scenarios (including the **Dell Laptop at Panipat** test case):

```bash
python seed_data.py
```

### Output Preview:
```text
[*] Seeding database for ReFind AI...
✓ Created 4 demo users (admin@refind.com, user1@refind.com, user2@refind.com, user3@refind.com)
[+] Created demo lost and found items across 4 scenarios
[AI] Running AI Matching Engine on seeded items...
  Matched Item #1 (Black Dell Laptop) -> Found 1 match(es)
  Matched Item #3 (Brown Leather Wallet) -> Found 1 match(es)
  Matched Item #5 (iPhone 14 Blue) -> Found 1 match(es)
============================================================
[TARGET MATCH] VERIFIED SCENARIO A MATCH (Dell Laptop at Panipat):
   Final Match Score: 96.2% (Very Strong Match)
   - Category Score:    100.0% (weight: 25%)
   - Location Score:    92.0% (weight: 20%)
   - Date Score:        100.0% (weight: 15%)
   - Color Score:       100.0% (weight: 10%)
   - Brand Score:       100.0% (weight: 10%)
   - Description Score: 89.0% (weight: 20%)
============================================================
[SUCCESS] Database successfully initialized and seeded with demo data!
```

---

## 10. How to Run the Application

Start the Flask server:
```bash
python run.py
```

Open your browser and navigate to:
```
http://127.0.0.1:5000
```

---

## 11. Demo User Credentials

| Role | Email | Password | Access Details |
|---|---|---|---|
| **Regular User 1** | `user1@refind.com` | `password123` | Reported lost Dell Laptop; has active match & dashboard notifications |
| **Regular User 2** | `user2@refind.com` | `password123` | Reported found Dell Laptop & lost wallet |
| **Regular User 3** | `user3@refind.com` | `password123` | Reported found wallet & lost iPhone |
| **Administrator** | `admin@refind.com` | `admin123` | Full access to `/admin` dashboard, moderation, user roles |

---

## 12. Automated Verification & Testing

To run the automated test suite covering registration, matching, permissions, and API endpoints:

```bash
python test_refind.py
```

All 6 test suites execute in ~3 seconds and verify:
- User registration and duplicate email protection
- Invalid credential rejection
- Automatic pair matching $>60\%$ score calculation
- Mutual notifications generation
- Contact inquiry delivery
- Resolution status update (*Item Reunited Successfully*)
- Unauthorized item deletion prevention
- Role-based admin access control
- Keyword search and API data serialization

---

## 13. Future Enhancements

1. **Computer Vision Matching:** Integrating OpenCV / ResNet embeddings to compare image feature vectors in addition to text metadata.
2. **SMS & WhatsApp Gateway:** Integrating Twilio / WhatsApp Business API for instant SMS notifications to users.
3. **Geo-fencing & Map Visualization:** Interactive Leaflet / Google Maps integration showing clustered lost and found pins.
4. **Blockchain-backed Proof of Ownership:** Storing serial number hashes for high-value items (smartphones, jewelry, IDs) on-chain.

---

## 14. License & Credits

Built as a college final-year project demonstration for **ReFind AI – Lost. Found. Reunited.**  
Created with Python, Flask, scikit-learn, and Bootstrap 5.
