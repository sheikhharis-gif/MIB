from datetime import date, datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from sqlalchemy import func

from extensions import db
from models import Vehicle, Vendor, Route, Trip, Expense
from utils import to_float, next_trip_no, next_hm_ref

dashboard_bp = Blueprint("dashboard", __name__, url_prefix="/dashboard")


def parse_date(value):
    if not value:
        return None
    return datetime.strptime(value, "%Y-%m-%d").date()


@dashboard_bp.route("/")
@login_required
def index():
    today = date.today()
    month_start = today.replace(day=1)

    total_vehicles = Vehicle.query.count()
    active_vehicles = Vehicle.query.filter_by(status="Active").count()
    total_vendors = Vendor.query.count()
    active_trips = Trip.query.filter(Trip.status.in_(["Pending", "Assigned"])).count()

    month_receivable = db.session.query(func.coalesce(func.sum(Trip.account_receivable), 0.0)) \
        .filter(Trip.trip_date >= month_start).scalar()
    month_payable = db.session.query(func.coalesce(func.sum(Trip.account_payable), 0.0)) \
        .filter(Trip.trip_date >= month_start).scalar()
    month_expense = db.session.query(func.coalesce(func.sum(Expense.amount), 0.0)) \
        .filter(Expense.expense_date >= month_start).scalar()

    net_income = (month_receivable or 0) - (month_payable or 0) - (month_expense or 0)

    recent_trips = Trip.query.order_by(Trip.id.desc()).limit(6).all()

    vehicles = Vehicle.query.filter_by(status="Active").order_by(Vehicle.reg_no).all()
    vendors = Vendor.query.filter_by(is_active=True).order_by(Vendor.name).all()
    routes = Route.query.order_by(Route.origin).all()

    return render_template(
        "dashboard.html",
        total_vehicles=total_vehicles,
        active_vehicles=active_vehicles,
        total_vendors=total_vendors,
        active_trips=active_trips,
        month_receivable=month_receivable or 0,
        month_payable=month_payable or 0,
        month_expense=month_expense or 0,
        net_income=net_income,
        recent_trips=recent_trips,
        vehicles=vehicles,
        vendors=vendors,
        routes=routes,
    )


@dashboard_bp.route("/quick-entry", methods=["POST"])
@login_required
def quick_entry():
    vehicle_id = request.form.get("vehicle_id") or None
    vendor_id = request.form.get("vendor_id") or None
    customer_name = request.form.get("customer_name", "").strip()

    if not vehicle_id or not vendor_id or not customer_name:
        flash("Vehicle, Vendor and Customer Name are required for a new entry", "error")
        return redirect(url_for("dashboard.index"))

    trip = Trip(
        trip_no=next_trip_no(),
        hm_ref=next_hm_ref(),
        trip_date=parse_date(request.form.get("trip_date")) or date.today(),
        route_id=request.form.get("route_id") or None,
        vehicle_id=vehicle_id,
        vendor_id=vendor_id,
        customer_name=customer_name,
        dc_no=request.form.get("dc_no", "").strip(),
        dc_date=parse_date(request.form.get("dc_date")),
        bilty_no=request.form.get("bilty_no", "").strip(),
        bilty_date=parse_date(request.form.get("bilty_date")),
        delivery_location=request.form.get("delivery_location", "").strip(),
        vehicle_type=request.form.get("vehicle_type", "").strip(),
        weight=to_float(request.form.get("weight")),
        freight=to_float(request.form.get("freight")),
        dtn=to_float(request.form.get("dtn")),
        halting=to_float(request.form.get("halting")),
        account_payable=to_float(request.form.get("account_payable")),
        status="Assigned",
    )
    trip.recalc_total()
    trip.account_receivable = to_float(request.form.get("account_receivable")) or trip.total_freight
    db.session.add(trip)
    db.session.flush()

    expense_type = request.form.get("expense_type", "").strip()
    expense_amount = to_float(request.form.get("expense_amount"))
    if expense_type and expense_amount > 0:
        description = f"Logged from Quick Entry for {trip.trip_no}"
        if expense_type == "Other":
            other_name = request.form.get("other_expense_name", "").strip()
            if other_name:
                description = f"{other_name} — {description}"
        expense = Expense(
            expense_date=trip.trip_date,
            expense_type=expense_type,
            vehicle_id=vehicle_id,
            trip_id=trip.id,
            amount=expense_amount,
            description=description,
        )
        db.session.add(expense)

    db.session.commit()
    flash(
        f"Entry saved: {trip.trip_no} (HM Ref {trip.hm_ref}) — vehicle & vendor assigned, "
        f"Account Payable Rs {trip.account_payable:,.2f} recorded, income updated.",
        "success",
    )
    return redirect(url_for("dashboard.index"))
