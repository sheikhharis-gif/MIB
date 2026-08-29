from datetime import datetime, date
from flask import Blueprint, render_template, request
from flask_login import login_required
from sqlalchemy import func

from extensions import db
from models import Trip, Expense

reports_bp = Blueprint("reports", __name__, url_prefix="/reports")


def parse_date(value):
    if not value:
        return None
    return datetime.strptime(value, "%Y-%m-%d").date()


@reports_bp.route("/income-statement")
@login_required
def income_statement():
    today = date.today()
    date_from = parse_date(request.args.get("date_from")) or today.replace(day=1)
    date_to = parse_date(request.args.get("date_to")) or today

    receivable = db.session.query(func.coalesce(func.sum(Trip.account_receivable), 0.0)) \
        .filter(Trip.trip_date.between(date_from, date_to)).scalar() or 0
    payable = db.session.query(func.coalesce(func.sum(Trip.account_payable), 0.0)) \
        .filter(Trip.trip_date.between(date_from, date_to)).scalar() or 0
    expense = db.session.query(func.coalesce(func.sum(Expense.amount), 0.0)) \
        .filter(Expense.expense_date.between(date_from, date_to)).scalar() or 0

    oil_expense = db.session.query(func.coalesce(func.sum(Expense.amount), 0.0)) \
        .filter(Expense.expense_date.between(date_from, date_to), Expense.expense_type == "Oil").scalar() or 0
    diesel_expense = db.session.query(func.coalesce(func.sum(Expense.amount), 0.0)) \
        .filter(Expense.expense_date.between(date_from, date_to), Expense.expense_type == "Diesel").scalar() or 0
    other_expense = db.session.query(func.coalesce(func.sum(Expense.amount), 0.0)) \
        .filter(Expense.expense_date.between(date_from, date_to), Expense.expense_type == "Other").scalar() or 0

    net_income = receivable - payable - expense

    return render_template(
        "reports/income_statement.html",
        date_from=date_from, date_to=date_to,
        receivable=receivable, payable=payable, expense=expense,
        oil_expense=oil_expense, diesel_expense=diesel_expense, other_expense=other_expense,
        net_income=net_income,
    )
