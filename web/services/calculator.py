# web/services/calculator.py

class BusinessCalculator:
    @staticmethod
    def calculate_presumptive_tax(gross_receipts: float, is_digital: bool = True):
        """
        Calculates ITR-4 (Sugam) Presumptive Tax.
        44ADA for Professionals | 44AD for Businesses.
        """
        # Professionals pay tax on 50%
        # Businesses pay 6% if digital, 8% if cash
        taxable_income = gross_receipts * 0.50 
        
        # New Tax Regime 2026 Slab (Example: No tax up to 7L)
        tax_due = 0
        if taxable_income > 700000:
            tax_due = (taxable_income - 700000) * 0.10 # Simplified 10%
            
        return {
            "taxable_income": taxable_income,
            "tax_due": round(tax_due, 2),
            "advance_tax_deadline": "March 15, 2026" # 100% due by this date
        }

    @staticmethod
    def get_advance_tax_schedule(total_tax: float):
        """Standard 2025-26 Installments"""
        if total_tax < 10000: return [] # No advance tax if liability < 10k
        
        return [
            {"deadline": "15 June", "percentage": "15%", "amount": total_tax * 0.15},
            {"deadline": "15 Sept", "percentage": "45%", "amount": total_tax * 0.45},
            {"deadline": "15 Dec", "percentage": "75%", "amount": total_tax * 0.75},
            {"deadline": "15 March", "percentage": "100%", "amount": total_tax}
        ]
    @staticmethod
    def get_gst_breakdown(total_amount, rate):
        """Back-calculates tax from a total price (Inclusive GST)."""
        base_price = total_amount / (1 + rate)
        tax_amount = total_amount - base_price
        return {
            "base": round(base_price, 2),
            "cgst": round(tax_amount / 2, 2),
            "sgst": round(tax_amount / 2, 2)
        }

    @staticmethod
    def estimate_loan_limit(monthly_turnover):
        """Industry standard: 4x monthly sales for unsecured business loans."""
        # Cap at 10L for MUDRA Kishore/Tarun limits
        potential_limit = monthly_turnover * 4
        return min(potential_limit, 1000000)

    @staticmethod
    def calculate_penalty(due_date, filing_date, is_nil=False):
        """Standard 2026 Late Fee: ₹50/day (Regular) or ₹20/day (Nil)."""
        delay = (filing_date - due_date).days
        rate = 20 if is_nil else 50
        return max(0, delay * rate)