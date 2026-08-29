import os
import threading
import webbrowser

from flask import Flask, redirect, url_for
from flask_login import LoginManager, current_user
from sqlalchemy import text

from extensions import db, login_manager
from models import User, CompanyProfile

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = "fleet-management-secret-key-change-me"
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + os.path.join(BASE_DIR, "fleet.db")
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db.init_app(app)
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    from routes.auth import auth_bp
    from routes.dashboard import dashboard_bp
    from routes.vehicles import vehicles_bp
    from routes.vendors import vendors_bp
    from routes.trips import trips_bp
    from routes.expenses import expenses_bp
    from routes.invoices import invoices_bp
    from routes.payments import payments_bp
    from routes.company import company_bp
    from routes.reports import reports_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(vehicles_bp)
    app.register_blueprint(vendors_bp)
    app.register_blueprint(trips_bp)
    app.register_blueprint(expenses_bp)
    app.register_blueprint(invoices_bp)
    app.register_blueprint(payments_bp)
    app.register_blueprint(company_bp)
    app.register_blueprint(reports_bp)

    @app.route("/")
    def index():
        if current_user.is_authenticated:
            return redirect(url_for("dashboard.index"))
        return redirect(url_for("auth.login"))

    @app.template_filter("money")
    def money_filter(value):
        try:
            return "{:,.2f}".format(float(value or 0))
        except (TypeError, ValueError):
            return value

    with app.app_context():
        migrate_legacy_payment_table()
        db.create_all()
        migrate_legacy_route_schema()
        migrate_trip_account_receivable()
        add_column_if_missing("vendor", "stn_no", "VARCHAR(40)")
        add_column_if_missing("trip", "dc_no", "VARCHAR(60)")
        add_column_if_missing("invoice", "segment", "VARCHAR(100)")
        add_column_if_missing("invoice_item", "dc_no", "VARCHAR(60)")
        seed_default_admin()
        seed_company_profile()

    return app


def migrate_legacy_payment_table():
    """An older, incompatible 'payment' table (no vehicle_id column) may
    exist from a previous design. It was never populated with real data, so
    it's safe to drop and let create_all() rebuild it with the current schema."""
    tables = [r[0] for r in db.session.execute(
        text("SELECT name FROM sqlite_master WHERE type='table' AND name='payment'")
    ).fetchall()]
    if not tables:
        return
    columns = db.session.execute(text("PRAGMA table_info(payment)")).fetchall()
    has_vehicle_id = any(col[1] == "vehicle_id" for col in columns)
    if has_vehicle_id:
        return
    row_count = db.session.execute(text("SELECT COUNT(*) FROM payment")).scalar()
    if row_count:
        return
    db.session.execute(text("DROP TABLE payment"))
    db.session.commit()


def add_column_if_missing(table, column, ddl_type):
    columns = db.session.execute(text(f"PRAGMA table_info({table})")).fetchall()
    if any(col[1] == column for col in columns):
        return
    db.session.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {ddl_type}"))
    db.session.commit()


def migrate_legacy_route_schema():
    """Older DBs have a single-destination route.destination column. Move any
    existing value into route_stop as the first stop, then drop the column so
    it matches the current multi-destination Route model."""
    columns = db.session.execute(text("PRAGMA table_info(route)")).fetchall()
    has_destination = any(col[1] == "destination" for col in columns)
    if not has_destination:
        return

    existing = db.session.execute(text("SELECT id, destination FROM route")).fetchall()
    for route_id, destination in existing:
        if not destination:
            continue
        already = db.session.execute(
            text("SELECT 1 FROM route_stop WHERE route_id = :rid"), {"rid": route_id}
        ).first()
        if not already:
            db.session.execute(
                text("INSERT INTO route_stop (route_id, seq, destination) VALUES (:rid, 1, :dest)"),
                {"rid": route_id, "dest": destination},
            )
    db.session.commit()
    db.session.execute(text("ALTER TABLE route DROP COLUMN destination"))
    db.session.commit()


def migrate_trip_account_receivable():
    """Add the account_receivable column to older DBs and backfill it from
    total_freight so existing trips keep the same Receivable figure they had
    before this field existed."""
    columns = db.session.execute(text("PRAGMA table_info(trip)")).fetchall()
    has_receivable = any(col[1] == "account_receivable" for col in columns)
    if has_receivable:
        return

    db.session.execute(text("ALTER TABLE trip ADD COLUMN account_receivable FLOAT DEFAULT 0"))
    db.session.execute(text("UPDATE trip SET account_receivable = total_freight"))
    db.session.commit()


def seed_default_admin():
    if User.query.count() == 0:
        admin = User(username="admin", full_name="Administrator")
        admin.set_password("admin123")
        db.session.add(admin)
        db.session.commit()


def seed_company_profile():
    if CompanyProfile.query.count() == 0:
        db.session.add(CompanyProfile())
        db.session.commit()


app = create_app()


def _open_browser():
    webbrowser.open("http://127.0.0.1:5000/")


if __name__ == "__main__":
    # Only open the browser once: when the reloader is active, this script
    # runs twice (a watcher process + the real server process).
    if os.environ.get("WERKZEUG_RUN_MAIN") == "true" or os.environ.get("FLASK_NO_RELOAD"):
        threading.Timer(1.2, _open_browser).start()
    app.run(debug=True, use_reloader=True)
