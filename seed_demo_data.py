"""One-off script to populate the app with sample data for testing.
Run with: venv\\Scripts\\python.exe seed_demo_data.py
Safe to re-run; it only adds new rows (uses the same auto-numbering as the app).
"""
from datetime import date, timedelta

from app import app
from extensions import db
from models import Vehicle, Vendor, Trip, Invoice, InvoiceItem
from utils import next_trip_no, next_hm_ref, next_invoice_no

VEHICLES = [
    ("LES-4521", "22 Wheeler", "Hino FM", 25000),
    ("TLA-7788", "Container 40FT", "Nissan UD", 30000),
    ("KHI-3390", "10 Wheeler", "Isuzu FVR", 15000),
    ("LHR-9012", "Mazda", "Mazda Titan", 8000),
]

VENDORS = [
    ("Ali Transport Company", "Broker", "0300-1234567", "1112223-4", "0501234567890"),
    ("Malik Goods Carriers", "Self", "0321-9876543", "2223334-5", "0502345678901"),
    ("Sindh Logistics Pvt Ltd", "Broker", "0345-5556677", "3334445-6", "0503456789012"),
    ("Bilal Cargo Services", "Self", "0333-1112233", "4445556-7", "0504567890123"),
    ("Khan Brothers Transport", "Broker", "0312-7778899", "5556667-8", "0505678901234"),
]

CUSTOMERS = [
    "Lucky Cement Limited", "Engro Foods", "Nishat Mills", "Service Industries",
    "Al-Karam Textile Mills", "Fauji Fertilizer Company", "Interloop Limited",
    "Stallion Pharma", "Ghani Glass Limited", "Highnoon Laboratories",
]

DELIVERY_LOCATIONS = [
    "MLT Road LHR", "Sheikhupura Road LHR", "Ferozpur Road LHR",
    "Multan Bypass", "Korangi Industrial Area KHI", "SITE Area KHI",
]

VEHICLE_TYPES = ["40 FT", "22 Wheeler", "10 Wheeler", "Mazda"]


def run():
    with app.app_context():
        vehicles = []
        for reg_no, vtype, make, cap in VEHICLES:
            existing = Vehicle.query.filter_by(reg_no=reg_no).first()
            if existing:
                vehicles.append(existing)
                continue
            v = Vehicle(reg_no=reg_no, vehicle_type=vtype, make_model=make, capacity_weight=cap, status="Active")
            db.session.add(v)
            vehicles.append(v)
        db.session.commit()

        vendors = []
        for name, vtype, phone, ntn, stn in VENDORS:
            existing = Vendor.query.filter_by(name=name).first()
            if existing:
                vendors.append(existing)
                continue
            v = Vendor(name=name, vendor_type=vtype, phone=phone, cnic_ntn=ntn, stn_no=stn,
                       address="Industrial Area, Lahore", bank_name="HBL", account_no="01234567890", is_active=True)
            db.session.add(v)
            vendors.append(v)
        db.session.commit()

        base_date = date.today() - timedelta(days=30)
        freights = [95000, 140000, 210000, 320000, 175000, 88000, 260000, 132000, 305000, 198000, 250000]

        created_trips = []
        for i, freight in enumerate(freights):
            vehicle = vehicles[i % len(vehicles)]
            vendor = vendors[i % len(vendors)]
            customer = CUSTOMERS[i % len(CUSTOMERS)]
            trip_date = base_date + timedelta(days=i * 2)

            trip = Trip(
                trip_no=next_trip_no(),
                hm_ref=next_hm_ref(),
                trip_date=trip_date,
                vehicle_id=vehicle.id,
                vendor_id=vendor.id,
                customer_name=customer,
                dc_no=str(13600000 + i * 137),
                dc_date=trip_date,
                bilty_no=str(4400 + i),
                bilty_date=trip_date + timedelta(days=1),
                delivery_location=DELIVERY_LOCATIONS[i % len(DELIVERY_LOCATIONS)],
                vehicle_type=VEHICLE_TYPES[i % len(VEHICLE_TYPES)],
                weight=18 + (i % 6),
                freight=freight,
                dtn=0,
                halting=0,
                account_payable=round(freight * 0.88, 2),
                status="Assigned",
            )
            trip.recalc_total()
            trip.account_receivable = trip.total_freight
            db.session.add(trip)
            created_trips.append(trip)
        db.session.commit()

        # The exact-250,000 trip is the last one (freight=250000, dtn=0, halting=0)
        exact_trip = created_trips[-1]

        exact_invoice = Invoice(
            invoice_no=next_invoice_no(),
            invoice_type="Individual",
            vendor_id=exact_trip.vendor_id,
            invoice_date=date.today(),
            segment="Finished Goods",
        )
        db.session.add(exact_invoice)
        db.session.flush()

        item = InvoiceItem(
            invoice_id=exact_invoice.id,
            trip_id=exact_trip.id,
            hm_ref=exact_trip.hm_ref,
            vehicle_reg=exact_trip.vehicle.reg_no,
            customer_name=exact_trip.customer_name,
            dc_no=exact_trip.dc_no,
            dc_date=exact_trip.dc_date,
            bilty_no=exact_trip.bilty_no,
            bilty_date=exact_trip.bilty_date,
            delivery_location=exact_trip.delivery_location,
            vehicle_type=exact_trip.vehicle_type,
            weight=exact_trip.weight,
            freight=exact_trip.freight,
            dtn=exact_trip.dtn,
            halting=exact_trip.halting,
            line_total=exact_trip.total_freight,
        )
        db.session.add(item)
        exact_invoice.items = [item]
        exact_invoice.recalc_totals()
        exact_trip.status = "Invoiced"
        db.session.commit()

        print(f"Vehicles: {len(vehicles)} | Vendors: {len(vendors)} | Trips created: {len(created_trips)}")
        print(f"Exact 250,000 invoice: {exact_invoice.invoice_no} "
              f"(Total Freight Rs {exact_invoice.total_freight:,.2f} -> "
              f"SRB Rs {exact_invoice.srb_amount:,.2f} -> "
              f"Total Invoice Amount Rs {exact_invoice.total_invoice_amount:,.2f})")
        print(f"View it at: /invoices/{exact_invoice.id}")


if __name__ == "__main__":
    run()
