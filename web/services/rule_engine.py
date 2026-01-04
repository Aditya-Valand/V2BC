"""
BharatCompliance Master Rule Engine (v2026.FINAL)
Covers: Micro-biz, Traders, Freelancers, and Gig Workers.
"""

# AUTHORITATIVE BUSINESS MAPPING FOR 2026
# web/services/rule_engine.py

"""
BharatCompliance Master Rule Engine (v2026.FINAL)
Integrated Mapping: Micro-biz, Traders, Freelancers, and Gig Workers.
"""

LINK_MAP = {
    # General Compliance
    'gst_reg': "https://reg.gst.gov.in/registration/",
    'gst_login': "https://services.gst.gov.in/services/login",
    'itr': "https://www.incometax.gov.in/iec/foportal/help/e-filing-itr4-form-sugam-faq",

    # Sector Specific
    'eshram': "https://eshram.gov.in/",
    'pmjay': "https://nha.gov.in/PM-JAY",

    # Licenses (Mapped by the keys you use in BUSINESS_LICENSES)
    'fssai_basic': "https://foscos.fssai.gov.in/",
    'fssai_state': "https://foscos.fssai.gov.in/",
    'shop_act': "https://www.nsws.gov.in/",
    'trade_license': "https://www.nsws.gov.in/",
    'udyam_registration': "https://udyamregistration.gov.in/",
    'pm_svanidhi_id': "https://pmsvanidhi.mohua.gov.in/",
    'e_shram_uan': "https://eshram.gov.in/",
    'pollution_noc': "https://cpcb.nic.in/"
}

BUSINESS_LICENSES = {
    'fssai_basic': {
        'label': 'FSSAI Basic License',
        'validity_years': 1,
        'renewal_type': 'annual',
        'penalty': 'Rs. 100 per day of delay after expiry.'
    },
    'fssai_state': {
        'label': 'FSSAI State License',
        'validity_years': "1 - 5 Years (Based on Fee)",
        'renewal_type': 'periodic',
        'penalty': 'Rs. 100 per day of delay; Working without license can attract fines up to Rs. 5 Lakhs and imprisonment.'
    },
    'shop_act': {
        'label': 'Shops & Establishment Act',
        'validity_years': 'state_dependent',
        'renewal_type': 'periodic',
        'penalty': 'State dependent (Typically Rs. 1000 - Rs. 5000 + Rs. 50/day late fees).'
    },
    'trade_license': {
        'label': 'Trade License',
        'validity_years': 1,
        'renewal_type': 'annual',
        'penalty': '50% surcharge on license fee if renewed after 30 days of expiry; Heavy fines for operating without one.'
    },
    'health_license': {
        'label': 'Health License',
        'validity_years': 1,
        'renewal_type': 'annual',
        'penalty': 'Fine varies by Municipality (Approx. Rs. 2000 - Rs. 5000); Risk of business closure.'
    },
    'udyam_registration': {
        'label': 'Udyam Registration',
        'validity_years': None,
        'renewal_type': 'none',
        'penalty': 'No direct penalty, but loss of MSME benefits and subsidies.'
    },
    'artisan_card': {
        'label': 'Artisan Card',
        'validity_years': None,
        'renewal_type': 'none',
        'penalty': 'No direct monetary penalty; Ineligibility for government artisan schemes.'
    },
    'pollution_noc': {
        'label': 'Pollution Control NOC',
        'validity_years': 1,
        'renewal_type': 'periodic',
        'penalty': 'Extremely high fines (up to Rs. 1 Lakh) and imprisonment up to 5 years; Power/Water disconnection.'
    },
    'current_account': {
        'label': 'Current Account',
        'validity_years': None,
        'renewal_type': 'none',
        'penalty': 'Bank charges for non-maintenance of Minimum Average Balance (MAB).'
    },
    'local_govt_registration': {
        'label': 'Local Government Registration',
        'validity_years': 'state_dependent',
        'renewal_type': 'periodic',
        'penalty': 'State dependent fines; Seizure of goods/street cart for vendors.'
    },
    'pm_svanidhi_id': {
        'label': 'PM-SVANidhi ID',
        'validity_years': None,
        'renewal_type': 'none',
        'penalty': 'No penalty; Loss of interest subsidy and eligibility for higher loan tranches.'
    },
    'e_shram_uan': {
        'label': 'e-Shram UAN',
        'validity_years': None,
        'renewal_type': 'none',
        'penalty': 'No penalty; Loss of social security benefits.'
    },
    'welfare_board_id': {
        'label': 'Welfare Board ID',
        'validity_years': None,
        'renewal_type': 'none',
        'penalty': 'No penalty; Ineligibility for specific welfare schemes (education, health, marriage assistance).'
    }
}
BUSINESS_MAP = {

    # --- FOOD & EATERY ---
    'tea_shop': {
        'label': 'Tea Shop / Dhaba',
        'sector': 'Micro-Food',
        'gst_rate': 0.05,
        'threshold': 2000000,
        'licenses': ['fssai_basic', 'shop_act'],
        'is_food_biz': True,
        'jargon_free_tip': "Keep your FSSAI updated to avoid ₹2L fines. No GST needed if sales < ₹20L.",
        'loan_hint': "Eligible for MUDRA Shishu loans up to ₹50,000 for kitchen tools."
    },

    'cloud_kitchen': {
        'label': 'Cloud Kitchen',
        'sector': 'Gig/Food',
        'gst_rate': 0.05,
        'threshold': 0,
        'licenses': ['fssai_state', 'udyam_registration'],
        'jargon_free_tip': "Selling on Swiggy/Zomato? GST is mandatory from Day 1 even with ₹0 sales.",
        'loan_hint': "Use your platform sales history to get pre-approved digital loans."
    },

    'small_restaurant': {
        'label': 'Dhaba / Small Restaurant',
        'sector': 'Service',
        'gst_rate': 0.05,
        'threshold': 2000000,
        'licenses': ['fssai_state', 'shop_act', 'trade_license'],
        'jargon_free_tip': "As a standalone restaurant, you pay a flat 5% GST. Keep your Health License updated.",
        'loan_hint': "MUDRA Kishore loans (up to ₹5L) can help you buy better kitchen equipment."
    },

    # --- RETAIL & MANUFACTURING ---
    'kirana_store': {
        'label': 'Kirana / Grocery Store',
        'sector': 'Retail Trade',
        'gst_rate': 0.05,
        'threshold': 4000000,
        'licenses': ['shop_act', 'udyam_registration'],
        'jargon_free_tip': "Most loose items (milk/eggs) are 0%. Branded packets are 5%. Threshold is ₹40L.",
        'loan_hint': "Priority Sector Lending ensures banks must prioritize your loan application."
    },

    'boutique': {
        'label': 'Boutique / Garments',
        'sector': 'Retail Trade',
        'gst_rate': 0.05,
        'threshold': 4000000,
        'licenses': ['shop_act', 'udyam_registration'],
        'jargon_free_tip': "Cloth pieces below ₹2500 are 5%. Use Udyam to get lower-interest bank loans.",
        'loan_hint': "Special Stand-Up India subsidies available for women entrepreneurs."
    },

    'handicraft_maker': {
        'label': 'Handicraft / Artist',
        'sector': 'Manufacturing',
        'gst_rate': 0.05,
        'threshold': 4000000,
        'licenses': ['artisan_card', 'udyam_registration', 'pollution_noc'],
        'jargon_free_tip': "The government supports makers. Get subsidies on patents & trademarks.",
        'loan_hint': "Apply for PMEGP for 15–35% subsidy on workshop setup."
    },

    # --- SKILLED SERVICES ---
    'web_developer': {
        'label': 'Web & App Developer',
        'sector': 'Freelance Professional',
        'gst_rate': 0.18,
        'threshold': 2000000,
        'licenses': ['udyam_registration', 'current_account'],
        'jargon_free_tip': "Use Sec 44ADA. Pay tax on only 50% of income. No audit below ₹75L.",
        'loan_hint': "Professional loans available for laptops and servers."
    },

    'mobile_repair': {
        'label': 'Mobile & Electronics Repair',
        'sector': 'Service',
        'gst_rate': 0.18,
        'threshold': 2000000,
        'licenses': ['trade_license', 'shop_act'],
        'jargon_free_tip': "Repair services fall under 18% GST. Keep digital bills.",
        'loan_hint': "UPI transaction history helps in loan approvals."
    },

    'salon': {
        'label': 'Salon / Spa',
        'sector': 'Personal Service',
        'gst_rate': 0.18,
        'threshold': 2000000,
        'licenses': ['health_license', 'trade_license', 'shop_act'],
        'jargon_free_tip': "Basic services are 5%, luxury services 18%. Threshold ₹20L.",
        'loan_hint': "MUDRA Kishore loans can help upgrade equipment."
    },

    'coaching': {
        'label': 'Coaching Center',
        'sector': 'Education Services',
        'gst_rate': 0.00,
        'threshold': 2000000,
        'licenses': ['udyam_registration', 'local_govt_registration'],
        'jargon_free_tip': "Education services are GST-exempt. Focus on compliance basics.",
        'loan_hint': "Education MSMEs get lower interest loans."
    },

    # --- MICRO & GIG ---
    'street_vendor': {
        'label': 'Street Vendor',
        'sector': 'Micro-Vendor',
        'gst_rate': 0.00,
        'threshold': 2000000,
        'licenses': ['pm_svanidhi_id'],
        'jargon_free_tip': "Use PM-SVANidhi to get collateral-free loans.",
        'loan_hint': "Good repayment increases loan limits up to ₹50,000."
    },

    'delivery_gig': {
        'label': 'Delivery / Quick-Commerce',
        'sector': 'Gig Economy',
        'gst_rate': 0.00,
        'threshold': 2000000,
        'licenses': ['e_shram_uan', 'welfare_board_id'],
        'welfare_fund_rate': 0.02,
        'min_engagement_days': 90,
        'jargon_free_tip': "Platforms handle GST. Register on e-Shram for insurance benefits.",
        'loan_hint': "Platform ratings help unlock micro-loans."
    }
}

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

@dataclass
class ComplianceResult:
    status: str
    message: str
    color: str
    checklist: List[Dict[str, str]] # Changed to list of dicts: {message, link}
    loan_eligible: bool
    score: int        # Add this
    penalty: float

class ComplianceEngine:
    @staticmethod
    def validate_business(biz_key: str, turnover: float, state: str = "General") -> ComplianceResult:
        biz = BUSINESS_MAP.get(biz_key)

        checklist = []

        if not biz or turnover < 0:
            return ComplianceResult("Invalid Input", "Enter valid business data.", "gray", [], False, 0, 0.0)

        # 2026 Special State Logic
        special_states = ["Manipur", "Mizoram", "Nagaland", "Tripura", "Arunachal", "Meghalaya", "Sikkim", "Puducherry"]
        threshold = 1000000 if state in special_states and biz['sector'] in ['Service', 'Gig Economy'] else biz['threshold']

        is_above = turnover > threshold

        # 1. Limit Status Link
        checklist.append({
            "message": f"Limit Status: {'Crossed' if is_above else 'Within safe limit'}",
            "link": LINK_MAP['gst_login'] if is_above else LINK_MAP['gst_reg']
        })

        # 2. Gig Economy Logic
        if biz.get('sector') == 'Gig Economy':
            checklist.append({
                "message": f"Aggregator must contribute {biz['welfare_fund_rate']*100:.0f}% to Welfare Fund.",
                "link": LINK_MAP['eshram']
            })
            checklist.append({
                "message": "Port your benefits via Aadhaar-linked e-Shram ID.",
                "link": LINK_MAP['eshram']
            })
            checklist.append({
                "message": "Sync e-Shram ID for free health cover (AB-PMJAY).",
                "link": LINK_MAP['pmjay']
            })

        # 3. Food Biz Logic
        if biz.get('is_food_biz'):
            fssai_tier = "Basic (₹100)" if turnover <= 1200000 else "State (₹2000+)"
            checklist.append({
                "message": f"Required License: FSSAI {fssai_tier}",
                "link": LINK_MAP['fssai_basic']
            })

        # 4. GST Logic
        if is_above:
            checklist.extend([
                {"message": "Register for GST immediately", "link": LINK_MAP['gst_reg']},
                {"message": "Issue GST Invoices", "link": LINK_MAP['gst_login']}
            ])
        else:
            checklist.append({
                "message": f"Stay below ₹{threshold/100000}L to remain GST-Exempt.",
                "link": LINK_MAP['gst_reg']
            })

        # 5. Freelance Logic
        if biz['sector'] == 'Freelance Professional':
            checklist.append({
                "message": "Use ITR-4 Sugam for 50% presumptive profit claim.",
                "link": LINK_MAP['itr']
            })

        # 6. License Loop (Uses external LINK_MAP to find URL)
        for lic in biz['licenses']:
            # We assume lic (the key) exists in LINK_MAP. If not, default to #
            url = LINK_MAP.get(lic, "#")
            checklist.append({
                "message": f"Renew/Obtain: {BUSINESS_LICENSES[lic]['label']}",
                "link": url
            })

        # Calculation Logic
        if threshold > 0:
            usage_ratio = turnover / threshold
            calc_score = int(max(0, (1 - usage_ratio) * 100)) if not is_above else 60
        else:
            calc_score = 100

        calc_penalty = round((turnover - threshold) * 0.18, 2) if is_above else 0.0

        return ComplianceResult(
            status="ACTION REQUIRED" if is_above else "SAFE",
            message=biz['jargon_free_tip'],
            color="red" if is_above else "green",
            checklist=checklist,
            loan_eligible=True,
            score=min(calc_score, 100),
            penalty=calc_penalty
        )

class LoanEligibilityEngine:
    @staticmethod
    def get_readiness_score(user_data: dict, tx_count: int) -> Tuple[int, List[str]]:
        """Calculates 2026 Digital Credit Readiness (0-100)."""
        score = 0
        reasons = []

        # 1. Digital Documentation (60 points)
        if user_data.get('has_udyam'):
            score += 20
            reasons.append("Udyam Registration Verified (+20)")
        if user_data.get('has_itr'):
            score += 20
            reasons.append("ITR Filing History (+20)")
        if user_data.get('has_gst'):
            score += 20
            reasons.append("GST Compliance Active (+20)")

        # 2. Digital Traction (40 points)
        if tx_count > 30:
            score += 40
            reasons.append("High Transaction Volume (+40)")
        elif tx_count > 10:
            score += 20
            reasons.append("Moderate Transaction Volume (+20)")

        return min(score, 100), reasons
