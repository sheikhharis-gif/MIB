from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required

from extensions import db
from models import Expense, Vehicle, Trip
from utils import to_float

expenses_bp = Blueprint("expenses", __name__, url_prefix="/expenses")


def parse_date(value):
    if not value:
        return None
    return datetime.strptime(value, "%Y-%m-%d").date()


@expenses_bp.route("/")
@login_required
def index():
    etype = request.args.get("type", "").strip()
    query = Expense.query
    if etype in ("Oil", "Diesel", "Other"):
        query = query.filter_by(expense_type=etype)
    expenses = query.order_by(Expense.id.desc()).all()
    total = sum(e.amount or 0 for e in expenses)
    return render_template("expenses/list.html", expenses=expenses, etype=etype, total=total)


@expenses_bp.route("/new", methods=["GET", "POST"])
@login_required
def new():
    vehicles = Vehicle.query.order_by(Vehicle.reg_no).all()
    trips = Trip.query.order_by(Trip.id.desc()).all()

    if request.method == "POST":
        vehicle_id = request.form.get("vehicle_id") or None
        if not vehicle_id:
            flash("Please select a vehicle", "error")
            return render_template("expenses/form.html", vehicles=vehicles, trips=trips)

        expense_type = request.form.get("expense_type", "Diesel")
        description = request.form.get("description", "").strip()
        if expense_type == "Other":
            other_name = request.form.get("other_expense_name", "").strip()
            if other_name:
                description = f"{other_name}: {description}" if description else other_name

        expense = Expense(
            expense_date=parse_date(request.form.get("expense_date")) or datetime.utcnow().date(),
            expense_type=expense_type,
            vehicle_id=vehicle_id,
            trip_id=request.form.get("trip_id") or None,
            amount=to_float(request.form.get("amount")),
            description=description,
        )
        db.session.add(expense)
        db.session.commit()
        flash("Expense recorded successfully", "success")
        return redirect(url_for("expenses.index"))

    return render_template("expenses/form.html", vehicles=vehicles, trips=trips)


@expenses_bp.route("/<int:expense_id>/delete", methods=["POST"])
@login_required
def delete(expense_id):
    expense = Expense.query.get_or_404(expense_id)
    db.session.delete(expense)
    db.session.commit()
    flash("Expense deleted", "success")
    return redirect(url_for("expenses.index"))
