from functools import wraps
from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from app.models import db, User, Item, Match, Report, Notification

admin_bp = Blueprint('admin', __name__)


def admin_required(f):
    """Decorator to enforce Admin privileges."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            abort(403)
        return f(*args, **kwargs)
    return decorated_function


@admin_bp.before_request
@login_required
@admin_required
def require_admin():
    pass


@admin_bp.route('/')
def dashboard():
    total_users = User.query.count()
    total_lost = Item.query.filter_by(type='lost').count()
    total_found = Item.query.filter_by(type='found').count()
    total_matches = Match.query.count()
    total_resolved = Item.query.filter_by(status='resolved').count()
    pending_reports = Report.query.filter_by(status='pending').count()
    flagged_items = Item.query.filter_by(is_flagged=True).count()

    recent_reports = Report.query.order_by(Report.created_at.desc()).limit(5).all()
    recent_items = Item.query.order_by(Item.created_at.desc()).limit(6).all()

    return render_template(
        'admin/index.html',
        total_users=total_users,
        total_lost=total_lost,
        total_found=total_found,
        total_matches=total_matches,
        total_resolved=total_resolved,
        pending_reports=pending_reports,
        flagged_items=flagged_items,
        recent_reports=recent_reports,
        recent_items=recent_items
    )


@admin_bp.route('/users')
def users():
    all_users = User.query.order_by(User.created_at.desc()).all()
    return render_template('admin/users.html', users=all_users)


@admin_bp.route('/user/<int:user_id>/toggle-role', methods=['POST'])
def toggle_user_role(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash("You cannot change your own admin role.", "warning")
        return redirect(url_for('admin.users'))

    user.role = 'USER' if user.role == 'ADMIN' else 'ADMIN'
    db.session.commit()
    flash(f"User {user.name}'s role updated to {user.role}.", "success")
    return redirect(url_for('admin.users'))


@admin_bp.route('/user/<int:user_id>/delete', methods=['POST'])
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash("You cannot delete your own account from the admin panel.", "warning")
        return redirect(url_for('admin.users'))

    name = user.name
    db.session.delete(user)
    db.session.commit()
    flash(f"User account '{name}' has been permanently removed.", "info")
    return redirect(url_for('admin.users'))


@admin_bp.route('/items')
def items():
    filter_type = request.args.get('type', 'all')
    filter_flagged = request.args.get('flagged', '0')

    query = Item.query
    if filter_type in ['lost', 'found']:
        query = query.filter_by(type=filter_type)
    if filter_flagged == '1':
        query = query.filter_by(is_flagged=True)

    all_items = query.order_by(Item.created_at.desc()).all()
    return render_template('admin/items.html', items=all_items, filter_type=filter_type, filter_flagged=filter_flagged)


@admin_bp.route('/item/<int:item_id>/delete', methods=['POST'])
def delete_item(item_id):
    item = Item.query.get_or_404(item_id)
    item_name = item.item_name
    db.session.delete(item)
    db.session.commit()
    flash(f"Item '{item_name}' removed by administrator.", "info")
    return redirect(url_for('admin.items'))


@admin_bp.route('/item/<int:item_id>/toggle-flag', methods=['POST'])
def toggle_item_flag(item_id):
    item = Item.query.get_or_404(item_id)
    item.is_flagged = not item.is_flagged
    db.session.commit()
    status_str = "flagged as suspicious" if item.is_flagged else "cleared of flags"
    flash(f"Item '{item.item_name}' has been {status_str}.", "success")
    return redirect(request.referrer or url_for('admin.items'))


@admin_bp.route('/reports')
def reports():
    all_reports = Report.query.order_by(Report.created_at.desc()).all()
    return render_template('admin/reports.html', reports=all_reports)


@admin_bp.route('/report/<int:report_id>/resolve', methods=['POST'])
def resolve_report(report_id):
    report = Report.query.get_or_404(report_id)
    report.status = 'reviewed'
    db.session.commit()
    flash("Report marked as reviewed.", "success")
    return redirect(url_for('admin.reports'))
