# web/services/calculator.py

class BusinessCalculator:
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