from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required

from extensions import db
from models import Invoice, InvoiceItem, Trip, Vendor
from utils import next_invoice_no
from routes.company import get_profile

invoices_bp = Blueprint("invoices", __name__, url_prefix="/invoices")


def parse_date(value):
    if not value:
        return None
    return datetime.strptime(value, "%Y-%m-%d").date()


def make_item_from_trip(trip):
    return InvoiceItem(
        trip_id=trip.id,
        hm_ref=trip.hm_ref,
        vehicle_reg=trip.vehicle.reg_no if trip.vehicle else "",
        customer_name=trip.customer_name,
        dc_no=trip.dc_no,
        dc_date=trip.dc_date,
        bilty_no=trip.bilty_no,
        bilty_date=trip.bilty_date,
        delivery_location=trip.delivery_location,
        vehicle_type=trip.vehicle_type,
        weight=trip.weight,
        freight=trip.freight,
        dtn=trip.dtn,
        halting=trip.halting,
        line_total=trip.total_freight,
    )


@invoices_bp.route("/")
@login_required
def index():
    itype = request.args.get("type", "").strip()
    query = Invoice.query
    if itype in ("Individual", "VendorTotal"):
        query = query.filter_by(invoice_type=itype)
    invoices = query.order_by(Invoice.id.desc()).all()
    return render_template("invoices/list.html", invoices=invoices, itype=itype)


@invoices_bp.route("/new/individual", methods=["GET", "POST"])
@login_required
def new_individual():
    eligible_trips = Trip.query.filter_by(status="Assigned").order_by(Trip.id.desc()).all()
    eligible_trips = [t for t in eligible_trips if not t.invoice_items and t.vendor_id]

    if request.method == "POST":
        trip_id = request.form.get("trip_id")
        trip = Trip.query.get_or_404(trip_id) if trip_id else None
        if not trip:
            flash("Please select a trip", "error")
            return render_template("invoices/new_individual.html", trips=eligible_trips)

        invoice = Invoice(
            invoice_no=next_invoice_no(),
            invoice_type="Individual",
            vendor_id=trip.vendor_id,
            invoice_date=datetime.utcnow().date(),
            segment=request.form.get("segment", "").strip(),
        )
        db.session.add(invoice)
        db.session.flush()

        item = make_item_from_trip(trip)
        item.invoice_id = invoice.id
        db.session.add(item)
        invoice.items = [item]
        invoice.recalc_totals()

        trip.status = "Invoiced"
        db.session.commit()
        flash(f"Sales tax invoice {invoice.invoice_no} generated", "success")
        return redirect(url_for("invoices.view", invoice_id=invoice.id))

    return render_template("invoices/new_individual.html", trips=eligible_trips)


@invoices_bp.route("/new/vendor-total", methods=["GET", "POST"])
@login_required
def new_vendor_total():
    vendors = Vendor.query.order_by(Vendor.name).all()
    vendor_id = request.values.get("vendor_id") or None
    date_from = request.values.get("date_from") or ""
    date_to = request.values.get("date_to") or ""

    eligible_trips = []
    if vendor_id:
        query = Trip.query.filter_by(status="Assigned", vendor_id=vendor_id)
        if date_from:
            query = query.filter(Trip.trip_date >= parse_date(date_from))
        if date_to:
            query = query.filter(Trip.trip_date <= parse_date(date_to))
        eligible_trips = [t for t in query.order_by(Trip.trip_date).all() if not t.invoice_items]

    if request.method == "POST":
        trip_ids = request.form.getlist("trip_ids")
        if not vendor_id or not trip_ids:
            flash("Please select a vendor and at least one trip", "error")
            return render_template(
                "invoices/new_vendor_total.html", vendors=vendors, vendor_id=vendor_id,
                date_from=date_from, date_to=date_to, trips=eligible_trips,
            )

        trips = Trip.query.filter(Trip.id.in_(trip_ids)).all()

        invoice = Invoice(
            invoice_no=next_invoice_no(),
            invoice_type="VendorTotal",
            vendor_id=vendor_id,
            invoice_date=datetime.utcnow().date(),
            segment=request.form.get("segment", "").strip(),
        )
        db.session.add(invoice)
        db.session.flush()

        items = []
        for trip in trips:
            item = make_item_from_trip(trip)
            item.invoice_id = invoice.id
            db.session.add(item)
            items.append(item)
            trip.status = "Invoiced"

        invoice.items = items
        invoice.recalc_totals()
        db.session.commit()
        flash(f"Sales tax invoice {invoice.invoice_no} generated for {len(items)} trip(s)", "success")
        return redirect(url_for("invoices.view", invoice_id=invoice.id))

    return render_template(
        "invoices/new_vendor_total.html", vendors=vendors, vendor_id=vendor_id,
        date_from=date_from, date_to=date_to, trips=eligible_trips,
    )


@invoices_bp.route("/<int:invoice_id>")
@login_required
def view(invoice_id):
    invoice = Invoice.query.get_or_404(invoice_id)
    company = get_profile()
    return render_template("invoices/view.html", invoice=invoice, company=company)


@invoices_bp.route("/<int:invoice_id>/delete", methods=["POST"])
@login_required
def delete(invoice_id):
    invoice = Invoice.query.get_or_404(invoice_id)
    for item in invoice.items:
        trip = Trip.query.get(item.trip_id)
        if trip:
            trip.status = "Assigned"
    db.session.delete(invoice)
    db.session.commit()
    flash("Invoice deleted and its trips released back to Assigned", "success")
    return redirect(url_for("invoices.index"))
