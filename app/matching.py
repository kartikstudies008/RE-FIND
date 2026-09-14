import re
import string
from difflib import SequenceMatcher
from datetime import date
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


def normalize_text(text: str) -> str:
    """
    Normalizes text for NLP processing:
    - Lowercase
    - Strip punctuation
    - Remove extra spaces
    """
    if not text:
        return ""
    text = text.lower()
    text = text.translate(str.maketrans("", "", string.punctuation))
    text = re.sub(r"\s+", " ", text).strip()
    return text


def calculate_category_score(lost_cat: str, found_cat: str) -> float:
    """
    Category similarity (Weight: 25%).
    Exact match: 100%.
    Hierarchical / related overlap: 70%.
    Otherwise: 0%.
    """
    if not lost_cat or not found_cat:
        return 0.0

    c1 = lost_cat.strip().lower()
    c2 = found_cat.strip().lower()

    if c1 == c2:
        return 100.0

    # Cross-category semantic hierarchy (e.g. Laptop / Mobile Phone in Electronics)
    tech_categories = {'electronics', 'laptop', 'mobile phone'}
    accessory_categories = {'accessories', 'keys', 'wallet', 'bags'}

    if c1 in tech_categories and c2 in tech_categories:
        return 70.0
    if c1 in accessory_categories and c2 in accessory_categories:
        return 60.0

    return 0.0


def calculate_location_score(lost_loc: str, found_loc: str) -> float:
    """
    Location similarity (Weight: 20%).
    Combines token set overlap and fuzzy sequence matching.
    Handles variations like "Panipat Railway Station" vs "Near Panipat Railway Station".
    """
    l1 = normalize_text(lost_loc)
    l2 = normalize_text(found_loc)

    if not l1 or not l2:
        return 0.0

    if l1 == l2:
        return 100.0

    # Substring containment bonus (e.g. "panipat railway station" in "near panipat railway station")
    if l1 in l2 or l2 in l1:
        # High confidence match for containment
        return 92.0

    tokens1 = set(l1.split())
    tokens2 = set(l2.split())

    # Stop words common in location descriptions
    loc_stops = {'near', 'at', 'in', 'behind', 'front', 'of', 'beside', 'by', 'the', 'opposite', 'inside', 'outside'}
    t1_filtered = tokens1 - loc_stops or tokens1
    t2_filtered = tokens2 - loc_stops or tokens2

    jaccard = 0.0
    if t1_filtered and t2_filtered:
        intersection = t1_filtered.intersection(t2_filtered)
        union = t1_filtered.union(t2_filtered)
        jaccard = (len(intersection) / len(union)) * 100.0

    # Fuzzy sequence ratio
    seq_ratio = SequenceMatcher(None, l1, l2).ratio() * 100.0

    # Weighted blend of token Jaccard and string similarity
    score = max(jaccard * 0.7 + seq_ratio * 0.3, seq_ratio * 0.8)
    return min(100.0, round(score, 1))


def calculate_date_score(lost_date: date, found_date: date) -> float:
    """
    Date similarity (Weight: 15%).
    Temporal proximity decay based on difference in days.
    """
    if not lost_date or not found_date:
        return 50.0  # neutral if date is missing

    delta_days = abs((found_date - lost_date).days)

    if delta_days == 0:
        return 100.0
    elif delta_days == 1:
        return 90.0
    elif delta_days <= 3:
        return 75.0
    elif delta_days <= 7:
        return 50.0
    elif delta_days <= 14:
        return 30.0
    elif delta_days <= 30:
        return 15.0
    else:
        return 0.0


def calculate_color_score(lost_color: str, found_color: str, lost_desc: str = "", found_desc: str = "") -> float:
    """
    Color similarity (Weight: 10%).
    Normalized comparison with fallback inspection in item descriptions.
    """
    c1 = normalize_text(lost_color)
    c2 = normalize_text(found_color)

    if c1 and c2:
        if c1 == c2:
            return 100.0
        # Token overlap e.g., "matte black" vs "black"
        tokens1 = set(c1.split())
        tokens2 = set(c2.split())
        if tokens1.intersection(tokens2):
            return 90.0
        return 0.0

    # If one color is missing, check if color is mentioned in the other's description
    if c1 and not c2:
        if c1 in normalize_text(found_desc):
            return 80.0
        return 40.0  # neutral partial

    if c2 and not c1:
        if c2 in normalize_text(lost_desc):
            return 80.0
        return 40.0

    return 50.0  # Neither specified


def calculate_brand_score(lost_brand: str, found_brand: str, lost_name: str = "", found_name: str = "", lost_desc: str = "", found_desc: str = "") -> float:
    """
    Brand similarity (Weight: 10%).
    Normalized comparison with name & description fallback.
    """
    b1 = normalize_text(lost_brand)
    b2 = normalize_text(found_brand)

    if b1 and b2:
        if b1 == b2:
            return 100.0
        if b1 in b2 or b2 in b1:
            return 95.0
        ratio = SequenceMatcher(None, b1, b2).ratio()
        if ratio >= 0.8:
            return 85.0
        return 0.0

    # Cross-check brand token in title or description
    target_brand = b1 or b2
    target_context = normalize_text(f"{lost_name} {found_name} {lost_desc} {found_desc}")
    if target_brand:
        if target_brand in target_context:
            return 85.0
        return 35.0

    return 50.0  # Neither brand provided


def calculate_description_score(lost_desc: str, found_desc: str, lost_name: str = "", found_name: str = "") -> float:
    """
    Description similarity (Weight: 20%).
    Uses TF-IDF + Cosine Similarity with scikit-learn.
    Combines item name + description for rich contextual vectors.
    """
    text1 = normalize_text(f"{lost_name} {lost_desc}")
    text2 = normalize_text(f"{found_name} {found_desc}")

    if not text1 or not text2:
        return 0.0

    if text1 == text2:
        return 100.0

    try:
        vectorizer = TfidfVectorizer(stop_words='english', token_pattern=r'(?u)\b\w+\b')
        tfidf_matrix = vectorizer.fit_transform([text1, text2])
        sim = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
        score = float(sim) * 100.0
        return min(100.0, max(0.0, round(score, 1)))
    except Exception:
        # Fallback to token Jaccard if vocabulary is empty or only stopwords
        t1 = set(text1.split())
        t2 = set(text2.split())
        if not t1 or not t2:
            return 0.0
        jaccard = (len(t1.intersection(t2)) / len(t1.union(t2))) * 100.0
        return round(jaccard, 1)


def calculate_final_match_score(lost_item, found_item) -> dict:
    """
    Calculates weighted match score between a LOST item and a FOUND item:
    - Category: 25%
    - Location: 20%
    - Date: 15%
    - Color: 10%
    - Brand: 10%
    - Description: 20%
    Total: 100%
    """
    cat_score = calculate_category_score(lost_item.category, found_item.category)
    loc_score = calculate_location_score(lost_item.location, found_item.location)
    date_score = calculate_date_score(lost_item.date, found_item.date)
    color_score = calculate_color_score(lost_item.color, found_item.color, lost_item.description, found_item.description)
    brand_score = calculate_brand_score(
        lost_item.brand, found_item.brand,
        lost_item.item_name, found_item.item_name,
        lost_item.description, found_item.description
    )
    desc_score = calculate_description_score(
        lost_item.description, found_item.description,
        lost_item.item_name, found_item.item_name
    )

    final_score = (
        (0.25 * cat_score) +
        (0.20 * loc_score) +
        (0.15 * date_score) +
        (0.10 * color_score) +
        (0.10 * brand_score) +
        (0.20 * desc_score)
    )
    final_score = round(final_score, 1)

    # Classification labels
    if final_score >= 80.0:
        label = "Very Strong Match"
        badge_class = "success"
    elif final_score >= 60.0:
        label = "Strong Match"
        badge_class = "primary"
    elif final_score >= 40.0:
        label = "Possible Match"
        badge_class = "warning"
    else:
        label = "Weak Match"
        badge_class = "secondary"

    return {
        "final_score": final_score,
        "category_score": cat_score,
        "location_score": loc_score,
        "date_score": date_score,
        "color_score": color_score,
        "brand_score": brand_score,
        "description_score": desc_score,
        "label": label,
        "badge_class": badge_class,
        "is_recommended": final_score >= 60.0
    }


class MatchingEngine:
    """
    High-level service class for executing matching passes and database persistence.
    """

    @staticmethod
    def evaluate_pair(lost_item, found_item):
        return calculate_final_match_score(lost_item, found_item)

    @staticmethod
    def find_potential_matches(target_item, candidate_items, threshold=60.0):
        results = []
        for candidate in candidate_items:
            # Prevent matching items belonging to the exact same post or invalid pairing
            if target_item.id == candidate.id:
                continue

            if target_item.type == 'lost' and candidate.type == 'found':
                lost = target_item
                found = candidate
            elif target_item.type == 'found' and candidate.type == 'lost':
                lost = candidate
                found = target_item
            else:
                continue

            score_data = calculate_final_match_score(lost, found)
            if score_data["final_score"] >= threshold:
                results.append({
                    "target_item": target_item,
                    "candidate_item": candidate,
                    "lost_item": lost,
                    "found_item": found,
                    "scores": score_data
                })

        # Sort highest score first
        results.sort(key=lambda x: x["scores"]["final_score"], reverse=True)
        return results

    @staticmethod
    def sync_item_matches(target_item, db_session, threshold=60.0):
        """
        Runs matching against all active opposing items in the database.
        Inserts or updates records in the `Match` table and creates notifications.
        Returns list of newly created or updated Match records.
        """
        from app.models import Item, Match, Notification

        opposing_type = 'found' if target_item.type == 'lost' else 'lost'
        candidates = Item.query.filter(
            Item.type == opposing_type,
            Item.status != 'resolved',
            Item.id != target_item.id
        ).all()

        saved_matches = []

        for candidate in candidates:
            lost = target_item if target_item.type == 'lost' else candidate
            found = candidate if target_item.type == 'lost' else target_item

            score_data = calculate_final_match_score(lost, found)

            # Look for existing match record
            existing_match = Match.query.filter_by(
                lost_item_id=lost.id,
                found_item_id=found.id
            ).first()

            if score_data["final_score"] >= threshold:
                if existing_match:
                    existing_match.match_score = score_data["final_score"]
                    existing_match.category_score = score_data["category_score"]
                    existing_match.location_score = score_data["location_score"]
                    existing_match.date_score = score_data["date_score"]
                    existing_match.color_score = score_data["color_score"]
                    existing_match.brand_score = score_data["brand_score"]
                    existing_match.description_score = score_data["description_score"]
                    saved_matches.append(existing_match)
                else:
                    new_match = Match(
                        lost_item_id=lost.id,
                        found_item_id=found.id,
                        match_score=score_data["final_score"],
                        category_score=score_data["category_score"],
                        location_score=score_data["location_score"],
                        date_score=score_data["date_score"],
                        color_score=score_data["color_score"],
                        brand_score=score_data["brand_score"],
                        description_score=score_data["description_score"],
                        status='suggested'
                    )
                    db_session.add(new_match)
                    db_session.flush()  # assign ID

                    # Notify Lost Item Owner
                    notif_lost = Notification(
                        user_id=lost.user_id,
                        title="New Potential Match Found!",
                        message=f"ReFind AI found a {score_data['final_score']}% match for your lost '{lost.item_name}'.",
                        link=f"/matches?match_id={new_match.id}"
                    )
                    db_session.add(notif_lost)

                    # Notify Found Item Reporter (if different user)
                    if found.user_id != lost.user_id:
                        notif_found = Notification(
                            user_id=found.user_id,
                            title="Potential Owner Identified!",
                            message=f"ReFind AI found a {score_data['final_score']}% match for the '{found.item_name}' you reported.",
                            link=f"/matches?match_id={new_match.id}"
                        )
                        db_session.add(notif_found)

                    saved_matches.append(new_match)

        db_session.commit()
        return saved_matches
