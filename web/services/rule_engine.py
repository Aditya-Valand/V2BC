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

BUSINESS_MAP = {
    # --- GROUP 1: FOOD & EATERY (Micro-Businesses & Gig) ---
    'tea_shop': {
        'label': 'Tea Shop / Dhaba',
        'sector': 'Micro-Food',
        'gst_rate': 0.05,  # Standalone restaurant rate
        'threshold': 2000000,
        'licenses': ['FSSAI Basic', 'Shop Act'],
        'is_food_biz': True,
        'jargon_free_tip': "Keep your FSSAI updated to avoid ₹2L fines. No GST needed if sales < ₹20L.",
        'loan_hint': "Eligible for MUDRA Shishu loans up to ₹50,000 for kitchen tools."
    },
    'cloud_kitchen': {
        'label': 'Cloud Kitchen',
        'sector': 'Gig/Food',
        'gst_rate': 0.05,
        'threshold': 0,  # Mandatory GST for e-commerce/platform sellers
        'licenses': ['FSSAI State', 'Udyam Registration'],
        'jargon_free_tip': "Selling on Swiggy/Zomato? GST is mandatory from Day 1 even with ₹0 sales.",
        'loan_hint': "Use your platform sales history to get pre-approved digital loans."
    },
    'small_restaurant': {
        'label': 'Dhaba / Small Restaurant',
        'sector': 'Service',
        'gst_rate': 0.05,
        'threshold': 2000000,
        'licenses': ['FSSAI State License', 'Shop Act', 'Trade License'],
        'jargon_free_tip': "As a standalone restaurant, you pay a flat 5% GST. Keep your 'Health License' updated.",
        'loan_hint': "MUDRA Kishore loans (up to ₹5L) can help you buy better kitchen equipment."
    },

    # --- GROUP 2: RETAIL & MANUFACTURING (Small Traders) ---
    'kirana_store': {
        'label': 'Kirana / Grocery Store',
        'sector': 'Retail Trade',
        'gst_rate': 0.05,  # 0% for loose, 5% for branded
        'threshold': 4000000,  # Higher limit for goods
        'licenses': ['Shop Act', 'Udyam Registration'],
        'jargon_free_tip': "Most loose items (milk/eggs) are 0%. Branded packets are 5%. Threshold is ₹40L.",
        'loan_hint': "Priority Sector Lending ensures banks must prioritize your loan application."
    },
    'boutique': {
        'label': 'Boutique / Garments',
        'sector': 'Retail Trade',
        'gst_rate': 0.05,
        'threshold': 4000000,
        'licenses': ['Shop Act', 'Udyam Registration'],
        'jargon_free_tip': "Cloth pieces below ₹2500 are 5%. Use Udyam to get a bank loan at 2% lower interest.",
        'loan_hint': "Special Stand-Up India subsidies available for women entrepreneurs."
    },
    'handicraft_maker': {
        'label': 'Handicraft / Artist',
        'sector': 'Manufacturing',
        'gst_rate': 0.05,
        'threshold': 4000000,
        'licenses': ['Artisan Card', 'Udyam Registration', 'Pollution NOC'],
        'jargon_free_tip': "The government loves makers! You get a 50% subsidy on Patent/Trademark fees.",
        'loan_hint': "Apply for the PMEGP scheme for a 15-35% subsidy on workshop setup."
    },

    # --- GROUP 3: SKILLED SERVICES (Freelancers & Pros) ---
    'web_developer': {
        'label': '💻 Web & App Developer',
        'sector': 'Freelance Professional',
        'gst_rate': 0.18,  # Standard for IT
        'threshold': 2000000,
        'licenses': ['Udyam Registration', 'Current Account'],
        'jargon_free_tip': "You qualify for Sec 44ADA. Only pay tax on 50% of your income! No audit needed if income < ₹75L.",
        'loan_hint': "Professional loans available for high-end equipment like MacBooks/Servers."
    },
    'mobile_repair': {
        'label': 'Mobile & Electronics Repair',
        'sector': 'Service',
        'gst_rate': 0.18,  # Appliances and repairs
        'threshold': 2000000,
        'licenses': ['Trade License', 'Shop Act'],
        'jargon_free_tip': "Electronics and repair services are in the high-tax 18% slab. Keep digital bills.",
        'loan_hint': "Your UPI transaction volume can act as proof of creditworthiness for loans."
    },
    'salon': {
        'label': 'Salon / Spa',
        'sector': 'Personal Service',
        'gst_rate': 0.18,  # 5% for basic, 18% for luxury facials
        'threshold': 2000000,
        'licenses': ['Health License', 'Trade License', 'Shops Act'],
        'jargon_free_tip': "Basic cuts are 5%. Luxury facials are 18%. Threshold for services is ₹20L.",
        'loan_hint': "MUDRA Kishore loans can help you upgrade salon chairs and equipment."
    },
    'coaching': {
        'label': 'Coaching Center',
        'sector': 'Education Services',
        'gst_rate': 0.00,  # Education is exempt
        'threshold': 2000000,
        'licenses': ['Udyam Registration', 'Local Govt. Registration'],
        'jargon_free_tip': "Education is a 'Noble Service' - it is GST exempt! Focus on student growth.",
        'loan_hint': "Education-sector MSMEs get special lower interest rates from banks."
    },

    # --- GROUP 4: MICRO-VENDORS & GIG WORKERS ---
    'street_vendor': {
        'label': 'Street Vendor',
        'sector': 'Micro-Vendor',
        'gst_rate': 0.00,
        'threshold': 2000000,
        'licenses': ['PM-SVANidhi ID'],
        'jargon_free_tip': "You are safe. Use your Vendor ID to get a ₹10,000 collateral-free loan.",
        'loan_hint': "Timely repayment of PM-SVANidhi loans unlocks limits up to ₹50,000."
    },
    'delivery_gig': {
        'label': '🛵 Delivery / Quick-Commerce',
        'sector': 'Gig Economy',
        'gst_rate': 0.00,  # Handled by platform
        'threshold': 2000000,
        'licenses': ['e-Shram UAN', 'Welfare Board ID'],
        'welfare_fund_rate': 0.02, # 1-2% of turnover
        'min_engagement_days': 90, # 90 days needed to qualify for benefits
        'jargon_free_tip': "Your platform handles the GST. Focus on your e-Shram benefits for insurance.",
        'loan_hint': "Eligible for PM-SVANidhi micro-loans based on platform ratings."
    }
}

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

@dataclass
class ComplianceResult:
    status: str
    message: str
    color: str
    checklist: List[str]
    loan_eligible: bool

class ComplianceEngine:
    @staticmethod
    def validate_business(biz_key: str, turnover: float, state: str = "General") -> ComplianceResult:
        biz = BUSINESS_MAP.get(biz_key)
        if not biz or turnover < 0:
            return ComplianceResult("Invalid Input", "Enter valid business data.", "gray", [], False)
        if biz.get('sector') == 'Gig Economy':
            checklist.append(f"🔴 Aggregator must contribute {biz['welfare_fund_rate']*100}% to Welfare Fund.")
            checklist.append("🔹 Port your benefits via Aadhaar-linked e-Shram ID.")
        if biz.get('is_food_biz'):
            fssai_tier = "Basic (₹100)" if turnover <= 1200000 else "State (₹2000+)"
            checklist.append(f"🍔 Required License: FSSAI {fssai_tier}")    
        # 2026 Special State Logic (Northeast/Hills)
        special_states = ["Manipur", "Mizoram", "Nagaland", "Tripura", "Arunachal", "Meghalaya", "Sikkim", "Puducherry"]
        threshold = 1000000 if state in special_states and biz['sector'] in ['Service', 'Gig Economy'] else biz['threshold']

        is_above = turnover > threshold
        checklist = [f"Limit Status: {'🚨 Crossed' if is_above else '✅ Within safe limit'}"]

        if is_above:
            checklist.extend(["Register for GST immediately", "Issue GST Invoices"])
        else:
            checklist.append(f"Stay below ₹{threshold/100000}L to remain GST-Exempt.")

        # Sector-specific Logic
        if biz['sector'] == 'Gig Economy':
            checklist.append("Sync e-Shram ID for free health cover (AB-PMJAY).")
        elif biz['sector'] == 'Freelance Professional':
            checklist.append("Use ITR-4 Sugam for 50% presumptive profit claim.")

        for lic in biz['licenses']:
            checklist.append(f"Renew/Obtain: {lic}")

        return ComplianceResult(
            status="🔴 ACTION REQUIRED" if is_above else "🟢 SAFE",
            message=biz['jargon_free_tip'],
            color="red" if is_above else "green",
            checklist=checklist,
            loan_eligible=True
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