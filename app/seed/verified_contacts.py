"""Access LA contacts verified against Rider's Guide 2026 + accessla.org.

Used by horizontal/vertical tests so seed drift is caught.
"""

from __future__ import annotations

# Official public numbers (dot format as spoken/printed by Access).
CUSTOMER_SERVICE = "1.800.827.0829"
CUSTOMER_SERVICE_TDD = "1.800.827.1359"
RESERVATIONS = "1.800.883.1295"
RESERVATIONS_TDD = "1.800.826.7280"
OMC_TEXT = "1.800.827.4588"
WMR_HOTLINE = "1.213.270.6099"
TRAVEL_TRAINING_MMP = "1.888.667.7003"
MOBILITY_MGMT = "1.213.270.6066"
ADA_COORDINATOR = "1.213.270.6000"
OUTSIDE_SOCAL = "1.213.488.1748"

# id -> required phone (and optional tdd)
REQUIRED_PHONES: dict[str, str] = {
    "dept_customer_service": CUSTOMER_SERVICE,
    "dept_reservations": RESERVATIONS,
    "dept_omc": CUSTOMER_SERVICE,  # Option 2 on same CS number
    "dept_eligibility": CUSTOMER_SERVICE,  # Option 3
    "dept_lost_found": RESERVATIONS,  # Option 2 on reservations
    "dept_wmr_support": WMR_HOTLINE,
    "dept_travel_training": TRAVEL_TRAINING_MMP,
    "dept_civil_rights": ADA_COORDINATOR,
    "dept_mobility_management": MOBILITY_MGMT,
    "dept_billing": CUSTOMER_SERVICE,
}

REQUIRED_TDD: dict[str, str] = {
    "dept_customer_service": CUSTOMER_SERVICE_TDD,
    "dept_reservations": RESERVATIONS_TDD,
    "dept_omc": CUSTOMER_SERVICE_TDD,
    "dept_eligibility": CUSTOMER_SERVICE_TDD,
    "dept_lost_found": RESERVATIONS_TDD,
    "dept_billing": CUSTOMER_SERVICE_TDD,
}

# need keyword -> department id that must appear in filtered results
NEED_TO_DEPT: dict[str, str] = {
    "lost": "dept_lost_found",
    "lost item": "dept_lost_found",
    "reservation": "dept_reservations",
    "standing order": "dept_reservations",
    "eligibility": "dept_eligibility",
    "omc": "dept_omc",
    "urgent": "dept_omc",
    "late vehicle": "dept_omc",
    "wmr": "dept_wmr_support",
    "where's my ride": "dept_wmr_support",
    "travel training": "dept_travel_training",
    "title vi": "dept_civil_rights",
    "ada": "dept_civil_rights",
    "beyond the curb": "dept_mobility_management",
    "fare": "dept_billing",
    "complaint": "dept_customer_service",
    "access id": "dept_customer_service",
}
