from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required

from extensions import db
from models import Vehicle, Vendor
from utils import to_float

vehicles_bp = Blueprint("vehicles", __name__, url_prefix="/vehicles")


@vehicles_bp.route("/")
@login_required
def index():
    q = request.args.get("q", "").strip()
    query = Vehicle.query
    if q:
        query = query.filter(Vehicle.reg_no.ilike(f"%{q}%"))
    vehicles = query.order_by(Vehicle.id.desc()).all()
    return render_template("vehicles/list.html", vehicles=vehicles, q=q)


@vehicles_bp.route("/new", methods=["GET", "POST"])
@login_required
def new():
    vendors = Vendor.query.filter_by(is_active=True).order_by(Vendor.name).all()
    if request.method == "POST":
        reg_no = request.form.get("reg_no", "").strip()
        if not reg_no:
            flash("Registration number is required", "error")
            return render_template("vehicles/form.html", vendors=vendors, vehicle=None, form=request.form)
        if Vehicle.query.filter_by(reg_no=reg_no).first():
            flash("A vehicle with this registration number already exists", "error")
            return render_template("vehicles/form.html", vendors=vendors, vehicle=None, form=request.form)

        vehicle = Vehicle(
            reg_no=reg_no,
            vehicle_type=request.form.get("vehicle_type", "").strip(),
            make_model=request.form.get("make_model", "").strip(),
            capacity_weight=to_float(request.form.get("capacity_weight")),
            owner_vendor_id=request.form.get("owner_vendor_id") or None,
            status=request.form.get("status", "Active"),
        )
        db.session.add(vehicle)
        db.session.commit()
        flash("Vehicle registered successfully", "success")
        return redirect(url_for("vehicles.index"))

    return render_template("vehicles/form.html", vendors=vendors, vehicle=None, form=None)


@vehicles_bp.route("/<int:vehicle_id>/edit", methods=["GET", "POST"])
@login_required
def edit(vehicle_id):
    vehicle = Vehicle.query.get_or_404(vehicle_id)
    vendors = Vendor.query.filter_by(is_active=True).order_by(Vendor.name).all()

    if request.method == "POST":
        reg_no = request.form.get("reg_no", "").strip()
        existing = Vehicle.query.filter(Vehicle.reg_no == reg_no, Vehicle.id != vehicle_id).first()
        if existing:
            flash("A vehicle with this registration number already exists", "error")
            return render_template("vehicles/form.html", vendors=vendors, vehicle=vehicle, form=request.form)

        vehicle.reg_no = reg_no
        vehicle.vehicle_type = request.form.get("vehicle_type", "").strip()
        vehicle.make_model = request.form.get("make_model", "").strip()
        vehicle.capacity_weight = to_float(request.form.get("capacity_weight"))
        vehicle.owner_vendor_id = request.form.get("owner_vendor_id") or None
        vehicle.status = request.form.get("status", "Active")
        db.session.commit()
        flash("Vehicle updated successfully", "success")
        return redirect(url_for("vehicles.index"))

    return render_template("vehicles/form.html", vendors=vendors, vehicle=vehicle, form=None)


@vehicles_bp.route("/<int:vehicle_id>/delete", methods=["POST"])
@login_required
def delete(vehicle_id):
    vehicle = Vehicle.query.get_or_404(vehicle_id)
    if vehicle.trips or vehicle.expenses:
        flash("Cannot delete a vehicle that has trips or expenses recorded", "error")
        return redirect(url_for("vehicles.index"))
    db.session.delete(vehicle)
    db.session.commit()
    flash("Vehicle deleted", "success")
    return redirect(url_for("vehicles.index"))
