import re
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

def parse_statement_text(text: str) -> Dict[str, Any]:
    """
    Parse business statement text from WhatsApp messages.
    
    Handles:
    - Various number formats (1000, 1,000, 1000.50, 1,000.50, ₹1000, Rs 1000)
    - Currency symbols and prefixes
    - Date references (today, yesterday, specific dates)
    - Transaction type keywords
    
    Args:
        text: Raw message text to parse
        
    Returns:
        Dictionary with: {'amount': float, 'date': datetime, 'type': str, 'description': str}
    """
    if not text:
        return {'amount': None, 'date': None, 'type': None}
    
    text_lower = text.lower()
    result = {
        'amount': None,
        'date': None,
        'type': None,
        'description': text,
        'raw_numbers': []  # Debug: all numbers found
    }
    
    # Extract all numbers with various formats
    # Matches: 1000, 1,000, 1000.50, 1,000.50, ₹1000, Rs 1000, $1000
    number_patterns = [
        r'(?:₹|rs|rupees?)\s*([0-9]{1,3}(?:,?[0-9]{3})*(?:\.[0-9]{2})?)',  # ₹1000 or Rs 1000
        r'([0-9]{1,3}(?:,?[0-9]{3})*(?:\.[0-9]{2})?)\s*(?:₹|rs|rupees?)',  # 1000 ₹
        r'([0-9]{5,}(?:\.[0-9]{2})?)',  # 5+ digits (likely amount)
    ]
    
    found_amounts = []
    for pattern in number_patterns:
        matches = re.finditer(pattern, text, re.IGNORECASE)
        for match in matches:
            try:
                # Clean the number: remove commas and convert to float
                num_str = match.group(1).replace(',', '')
                amount = float(num_str)
                found_amounts.append((amount, match.start()))
            except (ValueError, IndexError):
                continue
    
    # Find the largest 5-digit+ number (most likely to be the transaction amount)
    # This avoids picking up "100 customers" in "Sale 8200 but 100 customers"
    large_amounts = [a for a in found_amounts if a[0] >= 1000]
    if large_amounts:
        # Take the first occurrence of the largest number >= 1000
        large_amounts.sort(key=lambda x: -x[1] if x[0] >= 10000 else x[0], reverse=False)
        result['amount'] = large_amounts[0][0]
    elif found_amounts:
        # Fall back to any found amount
        result['amount'] = found_amounts[0][0]
    
    # Detect transaction type
    type_keywords = {
        'daily_sales': ['today', 'sale', 'sold', 'collection', 'received', 'income'],
        'expense': ['expense', 'paid', 'paid out', 'spent', 'cost', 'bill'],
        'purchase': ['purchase', 'bought', 'buy', 'inventory', 'stock'],
        'refund': ['refund', 'returned', 'return']
    }
    
    for ttype, keywords in type_keywords.items():
        if any(kw in text_lower for kw in keywords):
            result['type'] = ttype
            break
    
    if not result['type']:
        result['type'] = 'unknown'
    
    # Try to detect date
    result['date'] = parse_date(text_lower)
    
    return result


def parse_statement(text: str) -> Dict[str, Any]:
    """Legacy function name - calls parse_statement_text"""
    parsed = parse_statement_text(text)
    return {
        'statement_type': parsed.get('type'),
        'amount': parsed.get('amount'),
        'date': parsed.get('date'),
        'description': parsed.get('description')
    }


def parse_date(text_lower: str) -> Optional[datetime]:
    """
    Extract date reference from text.
    Supports: today, yesterday, specific dates (1st, 2nd, etc)
    """
    today = datetime.now()
    
    # Handle relative dates
    if 'today' in text_lower:
        return today
    elif 'yesterday' in text_lower:
        return today - timedelta(days=1)
    elif 'day before' in text_lower or 'day before yesterday' in text_lower:
        return today - timedelta(days=2)
    
    # Handle specific dates: "1st", "2nd", "15th", etc
    date_match = re.search(r'(\d{1,2})(?:st|nd|rd|th)?', text_lower)
    if date_match:
        try:
            day = int(date_match.group(1))
            # Assume current month
            if 1 <= day <= 31:
                return today.replace(day=day, hour=0, minute=0, second=0)
        except (ValueError, TypeError):
            pass
    
    return None
