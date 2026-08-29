from extensions import db
from models import Trip, Invoice, Payment


def next_sequence(model, column_name, prefix, pad=4):
    """Return the next PREFIX-0001 style code for a model column."""
    count = db.session.query(model).count()
    return f"{prefix}-{count + 1:0{pad}d}"


def next_trip_no():
    return next_sequence(Trip, "trip_no", "TRIP")


def next_hm_ref():
    return next_sequence(Trip, "hm_ref", "HM")


def next_invoice_no():
    return next_sequence(Invoice, "invoice_no", "INV")


def next_payment_no():
    return next_sequence(Payment, "payment_no", "PMT")


def to_float(value, default=0.0):
    try:
        if value in (None, ""):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default
