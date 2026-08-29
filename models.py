from datetime import datetime, date
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from extensions import db


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    full_name = db.Column(db.String(120), default="Administrator")
    password_hash = db.Column(db.String(255), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Vendor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    vendor_type = db.Column(db.String(20), nullable=False, default="Self")  # Broker / Self
    phone = db.Column(db.String(40))
    cnic_ntn = db.Column(db.String(40))
    stn_no = db.Column(db.String(40))
    address = db.Column(db.String(255))
    bank_name = db.Column(db.String(120))
    account_no = db.Column(db.String(60))
    notes = db.Column(db.String(255))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    vehicles = db.relationship("Vehicle", backref="owner_vendor", lazy=True)
    trips = db.relationship("Trip", backref="vendor", lazy=True)


class Vehicle(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    reg_no = db.Column(db.String(40), unique=True, nullable=False)
    vehicle_type = db.Column(db.String(60), nullable=False)
    make_model = db.Column(db.String(120))
    capacity_weight = db.Column(db.Float, default=0)
    owner_vendor_id = db.Column(db.Integer, db.ForeignKey("vendor.id"))
    status = db.Column(db.String(20), default="Active")  # Active / Inactive
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    trips = db.relationship("Trip", backref="vehicle", lazy=True)
    expenses = db.relationship("Expense", backref="vehicle", lazy=True)


class Route(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    origin = db.Column(db.String(120), nullable=False)
    distance_km = db.Column(db.Float, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    trips = db.relationship("Trip", backref="route", lazy=True)
    stops = db.relationship(
        "RouteStop", backref="route", order_by="RouteStop.seq",
        lazy=True, cascade="all, delete-orphan",
    )

    @property
    def destination_chain(self):
        return " → ".join(s.destination for s in self.stops)

    @property
    def full_path(self):
        chain = self.destination_chain
        return f"{self.origin} → {chain}" if chain else self.origin

    @property
    def final_destination(self):
        return self.stops[-1].destination if self.stops else ""


class RouteStop(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    route_id = db.Column(db.Integer, db.ForeignKey("route.id"), nullable=False)
    seq = db.Column(db.Integer, nullable=False, default=1)
    destination = db.Column(db.String(120), nullable=False)


class Trip(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    trip_no = db.Column(db.String(30), unique=True, nullable=False)
    hm_ref = db.Column(db.String(30), unique=True, nullable=False)
    trip_date = db.Column(db.Date, default=date.today)

    route_id = db.Column(db.Integer, db.ForeignKey("route.id"))
    vehicle_id = db.Column(db.Integer, db.ForeignKey("vehicle.id"))
    vendor_id = db.Column(db.Integer, db.ForeignKey("vendor.id"))

    customer_name = db.Column(db.String(150), nullable=False)
    dc_no = db.Column(db.String(60))
    dc_date = db.Column(db.Date)
    bilty_no = db.Column(db.String(60))
    bilty_date = db.Column(db.Date)
    delivery_location = db.Column(db.String(150))
    vehicle_type = db.Column(db.String(60))
    weight = db.Column(db.Float, default=0)

    freight = db.Column(db.Float, default=0)
    dtn = db.Column(db.Float, default=0)
    halting = db.Column(db.Float, default=0)
    total_freight = db.Column(db.Float, default=0)

    account_payable = db.Column(db.Float, default=0)
    account_receivable = db.Column(db.Float, default=0)

    status = db.Column(db.String(20), default="Pending")  # Pending / Assigned / Invoiced / Completed
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    expenses = db.relationship("Expense", backref="trip", lazy=True)
    invoice_items = db.relationship("InvoiceItem", backref="trip", lazy=True)

    def recalc_total(self):
        self.total_freight = (self.freight or 0) + (self.dtn or 0) + (self.halting or 0)


class Expense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    expense_date = db.Column(db.Date, default=date.today)
    expense_type = db.Column(db.String(20), nullable=False)  # Oil / Diesel
    vehicle_id = db.Column(db.Integer, db.ForeignKey("vehicle.id"), nullable=False)
    trip_id = db.Column(db.Integer, db.ForeignKey("trip.id"))
    amount = db.Column(db.Float, default=0)
    description = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class CompanyProfile(db.Model):
    """Singleton settings row used for the invoice letterhead."""
    id = db.Column(db.Integer, primary_key=True)
    company_name = db.Column(db.String(150), default="")
    tagline = db.Column(db.String(150), default="")
    email = db.Column(db.String(120), default="")
    website = db.Column(db.String(120), default="")
    lahore_office = db.Column(db.String(255), default="")
    lahore_phone = db.Column(db.String(40), default="")
    karachi_office = db.Column(db.String(255), default="")
    karachi_phone = db.Column(db.String(40), default="")
    ntn_no = db.Column(db.String(40), default="")


class Invoice(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    invoice_no = db.Column(db.String(30), unique=True, nullable=False)
    invoice_type = db.Column(db.String(20), nullable=False)  # Individual / VendorTotal
    vendor_id = db.Column(db.Integer, db.ForeignKey("vendor.id"), nullable=False)
    invoice_date = db.Column(db.Date, default=date.today)
    segment = db.Column(db.String(100), default="")

    total_freight = db.Column(db.Float, default=0)
    srb_amount = db.Column(db.Float, default=0)          # 15% of total_freight
    total_invoice_amount = db.Column(db.Float, default=0)  # total_freight + srb_amount

    status = db.Column(db.String(20), default="Issued")  # Issued / Paid
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    vendor = db.relationship("Vendor", backref="invoices")
    items = db.relationship("InvoiceItem", backref="invoice", lazy=True, cascade="all, delete-orphan")

    def recalc_totals(self):
        self.total_freight = sum((i.line_total or 0) for i in self.items)
        self.srb_amount = round(self.total_freight * 0.15, 2)
        self.total_invoice_amount = round(self.total_freight + self.srb_amount, 2)


class InvoiceItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey("invoice.id"), nullable=False)
    trip_id = db.Column(db.Integer, db.ForeignKey("trip.id"), nullable=False)

    hm_ref = db.Column(db.String(30))
    vehicle_reg = db.Column(db.String(40))
    customer_name = db.Column(db.String(150))
    dc_no = db.Column(db.String(60))
    dc_date = db.Column(db.Date)
    bilty_no = db.Column(db.String(60))
    bilty_date = db.Column(db.Date)
    delivery_location = db.Column(db.String(150))
    vehicle_type = db.Column(db.String(60))
    weight = db.Column(db.Float, default=0)
    freight = db.Column(db.Float, default=0)
    dtn = db.Column(db.Float, default=0)
    halting = db.Column(db.Float, default=0)
    line_total = db.Column(db.Float, default=0)


class InvoiceReceipt(db.Model):
    """Records the 2-cheque payment received against a Sales Tax Invoice,
    after Income Tax (7% of Total Invoice Amount) and SRB Withholding
    (20% of the 15% SRB amount) are deducted."""
    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey("invoice.id"), unique=True, nullable=False)

    total_invoice_amount = db.Column(db.Float, default=0)
    income_tax_7pct = db.Column(db.Float, default=0)        # 7% of total_invoice_amount
    srb_withholding_20pct = db.Column(db.Float, default=0)  # 20% of the invoice's SRB (15%) amount
    net_receivable = db.Column(db.Float, default=0)         # total_invoice_amount - both deductions

    cheque1_amount = db.Column(db.Float, default=0)
    cheque1_bank = db.Column(db.String(120))
    cheque1_no = db.Column(db.String(60))
    cheque1_date = db.Column(db.Date)

    cheque2_amount = db.Column(db.Float, default=0)
    cheque2_bank = db.Column(db.String(120))
    cheque2_no = db.Column(db.String(60))
    cheque2_date = db.Column(db.Date)

    received_date = db.Column(db.Date, default=date.today)
    notes = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    invoice = db.relationship("Invoice", backref=db.backref("receipt", uselist=False, cascade="all, delete-orphan"))


class Payment(db.Model):
    """General Add Payment ledger: Account Payable (money we pay a vendor)
    or Account Receivable (money we receive), by Cash or Cheque."""
    id = db.Column(db.Integer, primary_key=True)
    payment_no = db.Column(db.String(30), unique=True, nullable=False)
    payment_date = db.Column(db.Date, default=date.today)
    category = db.Column(db.String(20), nullable=False)  # Payable / Receivable
    vendor_id = db.Column(db.Integer, db.ForeignKey("vendor.id"))
    vehicle_id = db.Column(db.Integer, db.ForeignKey("vehicle.id"))
    amount = db.Column(db.Float, default=0)
    method = db.Column(db.String(20), nullable=False, default="Cash")  # Cheque / Cash
    bank_name = db.Column(db.String(120))
    cheque_no = db.Column(db.String(60))
    notes = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    vendor = db.relationship("Vendor", backref="payments")
    vehicle = db.relationship("Vehicle", backref="payments")

