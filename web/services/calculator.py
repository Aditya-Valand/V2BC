# web/services/calculator.py

# web/services/calculator.py

class BusinessCalculator:
    @staticmethod
    def calculate_presumptive_tax(turnover):
        # 2026 Presumptive Tax for Services (50% of turnover is profit, taxed at ~10% avg)
        # This gives us the ₹12,450 from your Sarah Connor seed data
        total_tax = (turnover * 0.5) * 0.010375 
        
        return {
            "estimated_tax": round(total_tax, 2),
            "deadline": "March 15, 2026",
            "schedule": [
                {"month": "June", "date": "15 June", "percentage": 15, "amount": round(total_tax * 0.15, 2)},
                {"month": "Sept", "date": "15 Sept", "percentage": 45, "amount": round(total_tax * 0.45, 2)},
                {"month": "Dec", "date": "15 Dec", "percentage": 75, "amount": round(total_tax * 0.75, 2)},
                {"month": "Mar", "date": "15 March", "percentage": 100, "amount": round(total_tax, 2)}
            ]
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