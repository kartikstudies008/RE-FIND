import os
import uuid
from datetime import datetime
from flask import (
    Blueprint, render_template, redirect, url_for, flash,
    request, current_app, jsonify
)
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from app.models import db, Item, Match, Report, Notification, User
from app.forms import ItemForm, ReportListingForm, ContactMessageForm
from app.matching import MatchingEngine

main_bp = Blueprint('main', __name__)


def save_image_file(file_storage):
    """Saves uploaded image safely with a unique UUID filename."""
    if not file_storage or file_storage.filename == '':
        return None
    filename = secure_filename(file_storage.filename)
    ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else 'jpg'
    unique_name = f"{uuid.uuid4().hex}_{int(datetime.utcnow().timestamp())}.{ext}"
    upload_path = os.path.join(current_app.config['UPLOAD_FOLDER'], unique_name)
    file_storage.save(upload_path)
    return unique_name


# Convenience Top-Level Redirects
@main_bp.route('/login')
def login_redirect():
    return redirect(url_for('auth.login', **request.args))


@main_bp.route('/register')
def register_redirect():
    return redirect(url_for('auth.register', **request.args))


@main_bp.route('/logout')
def logout_redirect():
    return redirect(url_for('auth.logout'))


# ==========================================
# 1. Landing / Home Page
# ==========================================
@main_bp.route('/')
def index():
    # Platform Statistics
    total_lost = Item.query.filter_by(type='lost').count()
    total_found = Item.query.filter_by(type='found').count()
    total_reunited = Item.query.filter_by(status='resolved').count()
    active_matches = Match.query.filter(Match.match_score >= 60.0).count()

    # Recent items preview
    recent_lost = Item.query.filter_by(type='lost', status='active')\
        .order_by(Item.created_at.desc()).limit(6).all()
    recent_found = Item.query.filter_by(type='found', status='active')\
        .order_by(Item.created_at.desc()).limit(6).all()

    return render_template(
        'index.html',
        total_lost=total_lost,
        total_found=total_found,
        total_reunited=total_reunited,
        active_matches=active_matches,
        recent_lost=recent_lost,
        recent_found=recent_found
    )


# ==========================================
# 2. Browse & Search Items
# ==========================================
@main_bp.route('/browse')
@main_bp.route('/items')
def browse():
    page = request.args.get('page', 1, type=int)
    keyword = request.args.get('q', '', type=str).strip()
    item_type = request.args.get('type', 'all', type=str)
    category = request.args.get('category', 'all', type=str)
    location = request.args.get('location', '', type=str).strip()
    date_filter = request.args.get('date', '', type=str).strip()
    status_filter = request.args.get('status', 'all', type=str)
    sort_by = request.args.get('sort', 'newest', type=str)

    query = Item.query

    # Keyword filter
    if keyword:
        like_expr = f"%{keyword}%"
        query = query.filter(
            db.or_(
                Item.item_name.ilike(like_expr),
                Item.description.ilike(like_expr),
                Item.brand.ilike(like_expr),
                Item.color.ilike(like_expr),
                Item.location.ilike(like_expr)
            )
        )

    # Type filter (lost / found)
    if item_type in ['lost', 'found']:
        query = query.filter(Item.type == item_type)

    # Category filter
    if category and category != 'all':
        query = query.filter(Item.category == category)

    # Location filter
    if location:
        query = query.filter(Item.location.ilike(f"%{location}%"))

    # Date filter
    if date_filter:
        try:
            parsed_date = datetime.strptime(date_filter, '%Y-%m-%d').date()
            query = query.filter(Item.date == parsed_date)
        except ValueError:
            pass

    # Status filter
    if status_filter in ['active', 'matched', 'resolved']:
        query = query.filter(Item.status == status_filter)
    else:
        # By default show active and matched in search
        query = query.filter(Item.status.in_(['active', 'matched']))

    # Sorting
    if sort_by == 'oldest':
        query = query.order_by(Item.created_at.asc())
    else:
        query = query.order_by(Item.created_at.desc())

    pagination = query.paginate(page=page, per_page=9, error_out=False)
    items = pagination.items

    return render_template(
        'items/browse.html',
        items=items,
        pagination=pagination,
        keyword=keyword,
        item_type=item_type,
        category=category,
        location=location,
        date_filter=date_filter,
        status_filter=status_filter,
        sort_by=sort_by
    )


# ==========================================
# 3. Report Lost Item
# ==========================================
@main_bp.route('/report-lost', methods=['GET', 'POST'])
@login_required
def report_lost():
    form = ItemForm()
    if form.validate_on_submit():
        image_file = save_image_file(form.image.data)

        item = Item(
            user_id=current_user.id,
            type='lost',
            item_name=form.item_name.data.strip(),
            category=form.category.data,
            description=form.description.data.strip(),
            color=form.color.data.strip() if form.color.data else None,
            brand=form.brand.data.strip() if form.brand.data else None,
            location=form.location.data.strip(),
            date=form.date.data,
            time=form.time.data if form.time.data else None,
            image_path=image_file,
            status='active'
        )
        db.session.add(item)
        db.session.commit()

        # Run AI matching against existing active found items
        matches = MatchingEngine.sync_item_matches(item, db.session, threshold=current_app.config['MATCH_THRESHOLD'])

        if matches:
            top_match = max(matches, key=lambda m: m.match_score)
            flash(
                f"🎉 Report submitted! ReFind AI found {len(matches)} potential match(es)! Top match: {top_match.match_score}%.",
                "success"
            )
            return redirect(url_for('main.item_details', item_id=item.id, match_highlight=1))
        else:
            flash("Lost item report submitted successfully! ReFind AI will monitor incoming reports 24/7.", "success")
            return redirect(url_for('main.item_details', item_id=item.id))

    return render_template('items/report_lost.html', form=form)


# ==========================================
# 4. Report Found Item
# ==========================================
@main_bp.route('/report-found', methods=['GET', 'POST'])
@login_required
def report_found():
    form = ItemForm()
    if form.validate_on_submit():
        image_file = save_image_file(form.image.data)

        item = Item(
            user_id=current_user.id,
            type='found',
            item_name=form.item_name.data.strip(),
            category=form.category.data,
            description=form.description.data.strip(),
            color=form.color.data.strip() if form.color.data else None,
            brand=form.brand.data.strip() if form.brand.data else None,
            location=form.location.data.strip(),
            date=form.date.data,
            time=form.time.data if form.time.data else None,
            image_path=image_file,
            status='active'
        )
        db.session.add(item)
        db.session.commit()

        # Run AI matching against existing active lost items
        matches = MatchingEngine.sync_item_matches(item, db.session, threshold=current_app.config['MATCH_THRESHOLD'])

        if matches:
            top_match = max(matches, key=lambda m: m.match_score)
            flash(
                f"🎉 Thank you for reporting! ReFind AI matched this with {len(matches)} lost item(s)! Top match: {top_match.match_score}%.",
                "success"
            )
            return redirect(url_for('main.item_details', item_id=item.id, match_highlight=1))
        else:
            flash("Found item report saved. If an owner files a matching report, both will be notified instantly.", "success")
            return redirect(url_for('main.item_details', item_id=item.id))

    return render_template('items/report_found.html', form=form)


# ==========================================
# 5. Item Details Page
# ==========================================
@main_bp.route('/item/<int:item_id>')
def item_details(item_id):
    item = Item.query.get_or_404(item_id)
    report_form = ReportListingForm()
    contact_form = ContactMessageForm()

    # Retrieve related matches for this item
    if item.type == 'lost':
        matches = Match.query.filter_by(lost_item_id=item.id)\
            .order_by(Match.match_score.desc()).all()
    else:
        matches = Match.query.filter_by(found_item_id=item.id)\
            .order_by(Match.match_score.desc()).all()

    top_match = matches[0] if matches else None

    return render_template(
        'items/details.html',
        item=item,
        matches=matches,
        top_match=top_match,
        report_form=report_form,
        contact_form=contact_form,
        match_highlight=request.args.get('match_highlight', False)
    )


# ==========================================
# 6. Mark as Resolved / Reunited
# ==========================================
@main_bp.route('/item/<int:item_id>/resolve', methods=['POST'])
@login_required
def mark_resolved(item_id):
    item = Item.query.get_or_404(item_id)

    # Only item owner or admin can mark resolved
    if item.user_id != current_user.id and not current_user.is_admin:
        flash("You do not have permission to modify this item.", "danger")
        return redirect(url_for('main.item_details', item_id=item.id))

    item.status = 'resolved'

    # If item has an accepted match, mark partner resolved too
    if item.type == 'lost':
        accepted_match = Match.query.filter_by(lost_item_id=item.id, status='accepted').first()
        if accepted_match and accepted_match.found_item:
            accepted_match.found_item.status = 'resolved'
    else:
        accepted_match = Match.query.filter_by(found_item_id=item.id, status='accepted').first()
        if accepted_match and accepted_match.lost_item:
            accepted_match.lost_item.status = 'resolved'

    db.session.commit()
    flash("🎉 Item Reunited Successfully! The status has been updated to Resolved.", "success")
    return redirect(url_for('main.dashboard'))


# ==========================================
# 7. Delete Item
# ==========================================
@main_bp.route('/item/<int:item_id>/delete', methods=['POST'])
@login_required
def delete_item(item_id):
    item = Item.query.get_or_404(item_id)
    if item.user_id != current_user.id and not current_user.is_admin:
        flash("Unauthorized action.", "danger")
        return redirect(url_for('main.item_details', item_id=item.id))

    db.session.delete(item)
    db.session.commit()
    flash("Item listing has been removed.", "info")
    return redirect(url_for('main.dashboard'))


# ==========================================
# 8. User Dashboard
# ==========================================
@main_bp.route('/dashboard')
@login_required
def dashboard():
    # User's items
    my_lost_items = Item.query.filter_by(user_id=current_user.id, type='lost')\
        .order_by(Item.created_at.desc()).all()
    my_found_items = Item.query.filter_by(user_id=current_user.id, type='found')\
        .order_by(Item.created_at.desc()).all()

    # Statistics
    lost_count = len(my_lost_items)
    found_count = len(my_found_items)
    resolved_count = sum(1 for i in my_lost_items + my_found_items if i.status == 'resolved')

    # Get matches involving the user's items
    my_lost_ids = [i.id for i in my_lost_items]
    my_found_ids = [i.id for i in my_found_items]

    all_matches_query = Match.query.filter(
        db.or_(
            Match.lost_item_id.in_(my_lost_ids) if my_lost_ids else False,
            Match.found_item_id.in_(my_found_ids) if my_found_ids else False
        )
    ).order_by(Match.match_score.desc())

    suggested_matches = all_matches_query.limit(10).all()
    potential_matches_count = all_matches_query.count()

    # User notifications
    recent_notifications = Notification.query.filter_by(user_id=current_user.id)\
        .order_by(Notification.created_at.desc()).limit(5).all()

    return render_template(
        'dashboard/dashboard.html',
        lost_items=my_lost_items,
        found_items=my_found_items,
        matches=suggested_matches,
        lost_count=lost_count,
        found_count=found_count,
        potential_matches_count=potential_matches_count,
        resolved_count=resolved_count,
        recent_notifications=recent_notifications
    )


# ==========================================
# 9. AI Suggested Matches Page
# ==========================================
@main_bp.route('/matches')
@login_required
def matches_dashboard():
    item_id = request.args.get('item_id', type=int)

    # Items owned by current user
    my_lost_ids = [i.id for i in Item.query.filter_by(user_id=current_user.id, type='lost').all()]
    my_found_ids = [i.id for i in Item.query.filter_by(user_id=current_user.id, type='found').all()]

    if item_id:
        matches = Match.query.filter(
            db.or_(
                Match.lost_item_id == item_id,
                Match.found_item_id == item_id
            )
        ).order_by(Match.match_score.desc()).all()
    else:
        matches = Match.query.filter(
            db.or_(
                Match.lost_item_id.in_(my_lost_ids) if my_lost_ids else False,
                Match.found_item_id.in_(my_found_ids) if my_found_ids else False
            )
        ).order_by(Match.match_score.desc()).all()

    return render_template('dashboard/matches.html', matches=matches, filter_item_id=item_id)


# ==========================================
# 10. Match Actions (Accept / Reject)
# ==========================================
@main_bp.route('/match/<int:match_id>/action', methods=['POST'])
@login_required
def match_action(match_id):
    action = request.form.get('action')
    match = Match.query.get_or_404(match_id)

    # Verify authorization
    lost_owner = match.lost_item.user_id
    found_owner = match.found_item.user_id

    if current_user.id not in [lost_owner, found_owner] and not current_user.is_admin:
        flash("Unauthorized match modification.", "danger")
        return redirect(url_for('main.matches_dashboard'))

    if action == 'accept':
        match.status = 'accepted'
        match.lost_item.status = 'matched'
        match.found_item.status = 'matched'

        # Notify the counterparty
        counter_id = found_owner if current_user.id == lost_owner else lost_owner
        counter_notif = Notification(
            user_id=counter_id,
            title="🤝 Match Accepted!",
            message=f"{current_user.name} accepted the match for '{match.lost_item.item_name}'. You can now exchange details!",
            link=f"/item/{match.lost_item_id if current_user.id == found_owner else match.found_item_id}"
        )
        db.session.add(counter_notif)
        db.session.commit()
        flash("Match accepted! Contact details are now accessible to coordinate reunion.", "success")
    elif action == 'reject':
        match.status = 'rejected'
        db.session.commit()
        flash("Match dismissed.", "info")

    return redirect(request.referrer or url_for('main.matches_dashboard'))


# ==========================================
# 11. Contact Owner / Finder
# ==========================================
@main_bp.route('/item/<int:item_id>/contact', methods=['POST'])
@login_required
def contact_owner(item_id):
    item = Item.query.get_or_404(item_id)
    form = ContactMessageForm()

    if form.validate_on_submit():
        if item.user_id == current_user.id:
            flash("You cannot send a contact inquiry to your own listing.", "warning")
            return redirect(url_for('main.item_details', item_id=item.id))

        # Send notification to the item poster
        notif = Notification(
            user_id=item.user_id,
            title=f"📩 Message regarding '{item.item_name}'",
            message=f"From {current_user.name} ({current_user.email} / {current_user.phone}):\n\"{form.message.data.strip()}\"",
            link=f"/item/{item.id}"
        )
        db.session.add(notif)
        db.session.commit()
        flash(f"Your inquiry has been sent to the poster of '{item.item_name}'.", "success")
    else:
        flash("Could not send inquiry. Please provide all required message details.", "danger")

    return redirect(url_for('main.item_details', item_id=item.id))


# ==========================================
# 12. Report Item Listing
# ==========================================
@main_bp.route('/item/<int:item_id>/report', methods=['POST'])
@login_required
def report_item(item_id):
    item = Item.query.get_or_404(item_id)
    form = ReportListingForm()

    if form.validate_on_submit():
        report = Report(
            item_id=item.id,
            reported_by=current_user.id,
            reason=form.reason.data.strip(),
            status='pending'
        )
        item.is_flagged = True
        db.session.add(report)
        db.session.commit()
        flash("Thank you. This listing has been flagged for admin review.", "info")
    else:
        flash("Please provide a valid reason for reporting this item.", "warning")

    return redirect(url_for('main.item_details', item_id=item.id))


# ==========================================
# 13. Notifications Center
# ==========================================
@main_bp.route('/notifications')
@login_required
def notifications():
    notifs = Notification.query.filter_by(user_id=current_user.id)\
        .order_by(Notification.created_at.desc()).all()
    return render_template('dashboard/notifications.html', notifications=notifs)


@main_bp.route('/notifications/read-all', methods=['POST'])
@login_required
def mark_all_notifications_read():
    Notification.query.filter_by(user_id=current_user.id, is_read=False).update({'is_read': True})
    db.session.commit()
    flash("All notifications marked as read.", "success")
    return redirect(url_for('main.notifications'))


@main_bp.route('/notification/<int:notif_id>/read', methods=['POST'])
@login_required
def mark_notification_read(notif_id):
    notif = Notification.query.get_or_404(notif_id)
    if notif.user_id == current_user.id:
        notif.is_read = True
        db.session.commit()
    return jsonify({"success": True})
