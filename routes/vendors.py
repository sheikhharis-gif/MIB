from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from sqlalchemy import func

from extensions import db
from models import Vendor, Trip

vendors_bp = Blueprint("vendors", __name__, url_prefix="/vendors")


@vendors_bp.route("/")
@login_required
def index():
    vtype = request.args.get("type", "").strip()
    query = Vendor.query
    if vtype in ("Broker", "Self"):
        query = query.filter_by(vendor_type=vtype)
    vendors = query.order_by(Vendor.name).all()

    totals = {"Broker": 0, "Self": 0}
    for v in Vendor.query.all():
        totals[v.vendor_type] = totals.get(v.vendor_type, 0) + 1

    # amount payable per vendor across all trips, for the "vendor detail" totals view
    payable_by_vendor = dict(
        db.session.query(Trip.vendor_id, func.coalesce(func.sum(Trip.account_payable), 0.0))
        .group_by(Trip.vendor_id).all()
    )

    return render_template(
        "vendors/list.html", vendors=vendors, vtype=vtype, totals=totals,
        payable_by_vendor=payable_by_vendor,
    )


@vendors_bp.route("/new", methods=["GET", "POST"])
@login_required
def new():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        if not name:
            flash("Vendor name is required", "error")
            return render_template("vendors/form.html", vendor=None, form=request.form)

        vendor = Vendor(
            name=name,
            vendor_type=request.form.get("vendor_type", "Self"),
            phone=request.form.get("phone", "").strip(),
            cnic_ntn=request.form.get("cnic_ntn", "").strip(),
            stn_no=request.form.get("stn_no", "").strip(),
            address=request.form.get("address", "").strip(),
            bank_name=request.form.get("bank_name", "").strip(),
            account_no=request.form.get("account_no", "").strip(),
            notes=request.form.get("notes", "").strip(),
            is_active=True,
        )
        db.session.add(vendor)
        db.session.commit()
        flash("Vendor added successfully", "success")
        return redirect(url_for("vendors.index"))

    return render_template("vendors/form.html", vendor=None, form=None)


@vendors_bp.route("/<int:vendor_id>/edit", methods=["GET", "POST"])
@login_required
def edit(vendor_id):
    vendor = Vendor.query.get_or_404(vendor_id)
    if request.method == "POST":
        vendor.name = request.form.get("name", "").strip()
        vendor.vendor_type = request.form.get("vendor_type", "Self")
        vendor.phone = request.form.get("phone", "").strip()
        vendor.cnic_ntn = request.form.get("cnic_ntn", "").strip()
        vendor.stn_no = request.form.get("stn_no", "").strip()
        vendor.address = request.form.get("address", "").strip()
        vendor.bank_name = request.form.get("bank_name", "").strip()
        vendor.account_no = request.form.get("account_no", "").strip()
        vendor.notes = request.form.get("notes", "").strip()
        vendor.is_active = request.form.get("is_active") == "on"
        db.session.commit()
        flash("Vendor updated successfully", "success")
        return redirect(url_for("vendors.index"))

    return render_template("vendors/form.html", vendor=vendor, form=None)


@vendors_bp.route("/<int:vendor_id>/delete", methods=["POST"])
@login_required
def delete(vendor_id):
    vendor = Vendor.query.get_or_404(vendor_id)
    if vendor.trips or vendor.vehicles or vendor.invoices:
        flash("Cannot delete a vendor that already has trips, vehicles or invoices", "error")
        return redirect(url_for("vendors.index"))
    db.session.delete(vendor)
    db.session.commit()
    flash("Vendor deleted", "success")
    return redirect(url_for("vendors.index"))
