from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required

from extensions import db
from models import Trip, Route, RouteStop, Vehicle, Vendor
from utils import to_float, next_trip_no, next_hm_ref

trips_bp = Blueprint("trips", __name__, url_prefix="/trips")


def parse_date(value):
    if not value:
        return None
    return datetime.strptime(value, "%Y-%m-%d").date()


# ---------- Routes ----------

@trips_bp.route("/routes")
@login_required
def routes_index():
    routes = Route.query.order_by(Route.id.desc()).all()
    return render_template("trips/routes.html", routes=routes)


@trips_bp.route("/routes/new", methods=["POST"])
@login_required
def routes_new():
    origin = request.form.get("origin", "").strip()
    destinations = [d.strip() for d in request.form.getlist("destinations[]") if d.strip()]

    if not origin or not destinations:
        flash("Origin and at least one destination are required", "error")
        return redirect(url_for("trips.routes_index"))

    route = Route(origin=origin, distance_km=to_float(request.form.get("distance_km")))
    db.session.add(route)
    db.session.flush()

    for seq, destination in enumerate(destinations, start=1):
        db.session.add(RouteStop(route_id=route.id, seq=seq, destination=destination))

    db.session.commit()
    flash(f"Route added: {route.full_path}", "success")
    return redirect(url_for("trips.routes_index"))


@trips_bp.route("/routes/<int:route_id>/delete", methods=["POST"])
@login_required
def routes_delete(route_id):
    route = Route.query.get_or_404(route_id)
    if route.trips:
        flash("Cannot delete a route that has trips assigned to it", "error")
        return redirect(url_for("trips.routes_index"))
    db.session.delete(route)
    db.session.commit()
    flash("Route deleted", "success")
    return redirect(url_for("trips.routes_index"))


# ---------- Trips ----------

@trips_bp.route("/")
@login_required
def index():
    status = request.args.get("status", "").strip()
    query = Trip.query
    if status:
        query = query.filter_by(status=status)
    trips = query.order_by(Trip.id.desc()).all()
    return render_template("trips/list.html", trips=trips, status=status)


@trips_bp.route("/new", methods=["GET", "POST"])
@login_required
def new():
    routes = Route.query.order_by(Route.origin).all()

    if request.method == "POST":
        route_id = request.form.get("route_id") or None
        customer_name = request.form.get("customer_name", "").strip()
        if not customer_name:
            flash("Customer name is required", "error")
            return render_template("trips/form.html", routes=routes, trip=None, form=request.form)

        trip = Trip(
            trip_no=next_trip_no(),
            hm_ref=next_hm_ref(),
            trip_date=parse_date(request.form.get("trip_date")) or datetime.utcnow().date(),
            route_id=route_id,
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
            status="Pending",
        )
        trip.recalc_total()
        trip.account_receivable = trip.total_freight
        db.session.add(trip)
        db.session.commit()
        flash(f"Trip {trip.trip_no} created (HM Ref {trip.hm_ref}). Now run Load Assessment to assign a vehicle.", "success")
        return redirect(url_for("trips.index"))

    return render_template("trips/form.html", routes=routes, trip=None, form=None)


@trips_bp.route("/<int:trip_id>/edit", methods=["GET", "POST"])
@login_required
def edit(trip_id):
    trip = Trip.query.get_or_404(trip_id)
    routes = Route.query.order_by(Route.origin).all()

    if request.method == "POST":
        trip.route_id = request.form.get("route_id") or None
        trip.customer_name = request.form.get("customer_name", "").strip()
        trip.trip_date = parse_date(request.form.get("trip_date")) or trip.trip_date
        trip.dc_no = request.form.get("dc_no", "").strip()
        trip.dc_date = parse_date(request.form.get("dc_date"))
        trip.bilty_no = request.form.get("bilty_no", "").strip()
        trip.bilty_date = parse_date(request.form.get("bilty_date"))
        trip.delivery_location = request.form.get("delivery_location", "").strip()
        trip.vehicle_type = request.form.get("vehicle_type", "").strip()
        trip.weight = to_float(request.form.get("weight"))
        trip.freight = to_float(request.form.get("freight"))
        trip.dtn = to_float(request.form.get("dtn"))
        trip.halting = to_float(request.form.get("halting"))
        trip.recalc_total()
        db.session.commit()
        flash("Trip updated successfully", "success")
        return redirect(url_for("trips.index"))

    return render_template("trips/form.html", routes=routes, trip=trip, form=None)


@trips_bp.route("/<int:trip_id>/delete", methods=["POST"])
@login_required
def delete(trip_id):
    trip = Trip.query.get_or_404(trip_id)
    if trip.invoice_items:
        flash("Cannot delete a trip that has already been invoiced", "error")
        return redirect(url_for("trips.index"))
    db.session.delete(trip)
    db.session.commit()
    flash("Trip deleted", "success")
    return redirect(url_for("trips.index"))


# ---------- Load Assessment ----------

@trips_bp.route("/load-assessment")
@login_required
def load_assessment_index():
    trips = Trip.query.order_by(Trip.id.desc()).all()
    return render_template("trips/load_assessment_list.html", trips=trips)


@trips_bp.route("/<int:trip_id>/assess", methods=["GET", "POST"])
@login_required
def assess(trip_id):
    trip = Trip.query.get_or_404(trip_id)
    vehicles = Vehicle.query.filter_by(status="Active").order_by(Vehicle.reg_no).all()
    vendors = Vendor.query.filter_by(is_active=True).order_by(Vendor.name).all()

    if request.method == "POST":
        vehicle_id = request.form.get("vehicle_id") or None
        vendor_id = request.form.get("vendor_id") or None
        if not vehicle_id or not vendor_id:
            flash("Please select both a vehicle and a vendor", "error")
            return render_template("trips/load_assessment_form.html", trip=trip, vehicles=vehicles, vendors=vendors)

        trip.vehicle_id = vehicle_id
        trip.vendor_id = vendor_id
        trip.account_payable = to_float(request.form.get("account_payable"))
        trip.status = "Assigned"
        db.session.commit()
        flash(f"Load assessed: vehicle assigned and Account Payable set for {trip.trip_no}", "success")
        return redirect(url_for("trips.load_assessment_index"))

    return render_template("trips/load_assessment_form.html", trip=trip, vehicles=vehicles, vendors=vendors)
