from flask import Blueprint, jsonify, request 
from app.models import Item, Match, User

api_bp = Blueprint('api', __name__)


@api_bp.route('/stats')
def api_stats():
    """Returns platform counters for live dashboard or frontend widgets."""
    return jsonify({
        "status": "success",
        "data": {
            "total_lost": Item.query.filter_by(type='lost').count(),
            "total_found": Item.query.filter_by(type='found').count(),
            "total_reunited": Item.query.filter_by(status='resolved').count(),
            "active_matches": Match.query.filter(Match.match_score >= 60.0).count()
        }
    })


@api_bp.route('/items')
def api_items():
    """Returns paginated or filtered list of items in JSON format."""
    item_type = request.args.get('type')
    category = request.args.get('category')
    limit = request.args.get('limit', 20, type=int)

    query = Item.query.filter(Item.status != 'resolved')
    if item_type in ['lost', 'found']:
        query = query.filter_by(type=item_type)
    if category:
        query = query.filter_by(category=category)

    items = query.order_by(Item.created_at.desc()).limit(limit).all()

    return jsonify({
        "status": "success",
        "count": len(items),
        "items": [{
            "id": i.id,
            "name": i.item_name,
            "type": i.type,
            "category": i.category,
            "location": i.location,
            "date": i.date.isoformat() if i.date else None,
            "color": i.color,
            "brand": i.brand,
            "status": i.status,
            "image_url": i.image_url
        } for i in items]
    })


@api_bp.route('/matches')
def api_matches():
    """Returns top AI matches above threshold."""
    threshold = request.args.get('threshold', 60.0, type=float)
    limit = request.args.get('limit', 20, type=int)

    matches = Match.query.filter(Match.match_score >= threshold)\
        .order_by(Match.match_score.desc()).limit(limit).all()

    return jsonify({
        "status": "success",
        "count": len(matches),
        "matches": [{
            "id": m.id,
            "match_score": m.match_score,
            "label": m.confidence_label,
            "lost_item": {
                "id": m.lost_item.id,
                "name": m.lost_item.item_name,
                "category": m.lost_item.category,
                "location": m.lost_item.location
            },
            "found_item": {
                "id": m.found_item.id,
                "name": m.found_item.item_name,
                "category": m.found_item.category,
                "location": m.found_item.location
            },
            "breakdown": {
                "category": m.category_score,
                "location": m.location_score,
                "date": m.date_score,
                "color": m.color_score,
                "brand": m.brand_score,
                "description": m.description_score
            }
        } for m in matches]
    })
