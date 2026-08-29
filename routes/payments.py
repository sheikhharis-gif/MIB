from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required

from extensions import db
from models import Payment, Vendor, Vehicle
from utils import to_float, next_payment_no

payments_bp = Blueprint("payments", __name__, url_prefix="/payments")


def parse_date(value):
    if not value:
        return None
    return datetime.strptime(value, "%Y-%m-%d").date()


@payments_bp.route("/")
@login_required
def index():
    category = request.args.get("category", "").strip()
    method = request.args.get("method", "").strip()

    query = Payment.query
    if category in ("Payable", "Receivable"):
        query = query.filter_by(category=category)
    if method in ("Cheque", "Cash"):
        query = query.filter_by(method=method)

    payments = query.order_by(Payment.id.desc()).all()
    total = sum(p.amount or 0 for p in payments)

    return render_template("payments/list.html", payments=payments, category=category, method=method, total=total)


@payments_bp.route("/new", methods=["GET", "POST"])
@login_required
def new():
    vendors = Vendor.query.order_by(Vendor.name).all()
    vehicles = Vehicle.query.order_by(Vehicle.reg_no).all()

    if request.method == "POST":
        category = request.form.get("category", "").strip()
        amount = to_float(request.form.get("amount"))
        method = request.form.get("method", "Cash")

        if category not in ("Payable", "Receivable") or amount <= 0:
            flash("Please select Payable/Receivable and enter a valid amount", "error")
            return render_template("payments/form.html", vendors=vendors, vehicles=vehicles, form=request.form)

        payment = Payment(
            payment_no=next_payment_no(),
            payment_date=parse_date(request.form.get("payment_date")) or datetime.utcnow().date(),
            category=category,
            vendor_id=request.form.get("vendor_id") or None,
            vehicle_id=request.form.get("vehicle_id") or None,
            amount=amount,
            method=method,
            bank_name=request.form.get("bank_name", "").strip() if method == "Cheque" else None,
            cheque_no=request.form.get("cheque_no", "").strip() if method == "Cheque" else None,
            notes=request.form.get("notes", "").strip(),
        )
        db.session.add(payment)
        db.session.commit()
        flash(f"Payment {payment.payment_no} recorded successfully", "success")
        return redirect(url_for("payments.index"))

    return render_template("payments/form.html", vendors=vendors, vehicles=vehicles, form=None)


@payments_bp.route("/<int:payment_id>/delete", methods=["POST"])
@login_required
def delete(payment_id):
    payment = Payment.query.get_or_404(payment_id)
    db.session.delete(payment)
    db.session.commit()
    flash("Payment deleted", "success")
    return redirect(url_for("payments.index"))
