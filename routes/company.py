from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required

from extensions import db
from models import CompanyProfile

company_bp = Blueprint("company", __name__, url_prefix="/company")


def get_profile():
    profile = CompanyProfile.query.first()
    if not profile:
        profile = CompanyProfile()
        db.session.add(profile)
        db.session.commit()
    return profile


@company_bp.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    company = get_profile()

    if request.method == "POST":
        company.company_name = request.form.get("company_name", "").strip()
        company.tagline = request.form.get("tagline", "").strip()
        company.email = request.form.get("email", "").strip()
        company.website = request.form.get("website", "").strip()
        company.lahore_office = request.form.get("lahore_office", "").strip()
        company.lahore_phone = request.form.get("lahore_phone", "").strip()
        company.karachi_office = request.form.get("karachi_office", "").strip()
        company.karachi_phone = request.form.get("karachi_phone", "").strip()
        company.ntn_no = request.form.get("ntn_no", "").strip()
        db.session.commit()
        flash("Company profile updated — it will now appear on your Sales Tax Invoices", "success")
        return redirect(url_for("company.profile"))

    return render_template("company/profile.html", company=company)
