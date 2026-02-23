"""
Signal Calculation Service

Pure calculation functions for compliance signals.
No side effects. No database writes except signal storage.
All calculations are deterministic: same input → same output.

Signals computed:
- daily_turnover: Sum of sales today
- monthly_turnover: Sum of sales this month
- evidence_ratio: Statements with backing / total statements
- weak_evidence_rate: Weak evidence / total evidence
- silence_days: Days since last statement
- abnormal_spike_flag: Today's sales > 2.5x monthly average
"""

from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple
from sqlalchemy import and_, func, extract
from core.extensions import db
from modules.businesses.models import Business
from modules.statements.models import BusinessStatement
from modules.evidence.models import BusinessEvidence
from modules.compliance.models import ComplianceSignal


class ComplianceSignalService:
    """
    Pure calculation service for compliance signals.
    
    All methods are static and deterministic.
    No side effects except creating signal records.
    """
    
    # Constants for signal calculations
    SPIKE_THRESHOLD_MULTIPLIER = 2.5  # Sales > 2.5x average = spike
    SILENCE_THRESHOLD_DAYS = 30  # No statement for 30+ days = alert
    
    @staticmethod
    def calculate_daily_turnover(business_id: int, target_date: Optional[datetime] = None) -> float:
        """
        Calculate daily turnover (sum of sales for the day).
        
        Args:
            business_id: Business ID
            target_date: Date to calculate for (defaults to today)
        
        Returns:
            Total sales amount for the day in ₹
        """
        if target_date is None:
            target_date = datetime.utcnow().date()
        elif isinstance(target_date, datetime):
            target_date = target_date.date()
        
        # Sum all statements for this business on this date
        # that are marked as daily_sales (statement_type = 'daily_sales')
        result = db.session.query(
            func.sum(BusinessStatement.amount)
        ).filter(
            and_(
                BusinessStatement.business_id == business_id,
                func.date(BusinessStatement.transaction_date) == target_date,
                BusinessStatement.statement_type == 'daily_sales'
            )
        ).scalar()
        
        return float(result) if result else 0.0
    
    @staticmethod
    def calculate_monthly_turnover(business_id: int, year: int, month: int) -> float:
        """
        Calculate monthly turnover (sum of daily sales for the month).
        
        Args:
            business_id: Business ID
            year: Year (YYYY)
            month: Month (1-12)
        
        Returns:
            Total sales amount for the month in ₹
        """
        result = db.session.query(
            func.sum(BusinessStatement.amount)
        ).filter(
            and_(
                BusinessStatement.business_id == business_id,
                extract('year', BusinessStatement.transaction_date) == year,
                extract('month', BusinessStatement.transaction_date) == month,
                BusinessStatement.statement_type == 'daily_sales'
            )
        ).scalar()
        
        return float(result) if result else 0.0
    
    @staticmethod
    def calculate_evidence_ratio(business_id: int) -> float:
        """
        Calculate evidence backing ratio.
        
        Ratio = (statements with at least one evidence) / (total statements)
        
        Args:
            business_id: Business ID
        
        Returns:
            Float 0-1 representing percentage of backed statements
        """
        # Total statements
        total_statements = db.session.query(
            func.count(BusinessStatement.id)
        ).filter(
            BusinessStatement.business_id == business_id
        ).scalar() or 0
        
        if total_statements == 0:
            return 0.0
        
        # Statements with at least one evidence
        backed_statements = db.session.query(
            func.count(func.distinct(BusinessStatement.id))
        ).select_from(BusinessStatement).join(
            BusinessEvidence,
            BusinessStatement.id == BusinessEvidence.business_statement_id,
            isouter=True
        ).filter(
            BusinessStatement.business_id == business_id,
            BusinessEvidence.id.isnot(None)
        ).scalar() or 0
        
        return float(backed_statements) / float(total_statements)
    
    @staticmethod
    def calculate_weak_evidence_rate(business_id: int) -> float:
        """
        Calculate rate of weak evidence.
        
        Ratio = (evidence marked as weak) / (total evidence)
        
        Args:
            business_id: Business ID
        
        Returns:
            Float 0-1 representing percentage of weak evidence
        """
        # Total evidence for this business
        total_evidence = db.session.query(
            func.count(BusinessEvidence.id)
        ).filter(
            BusinessEvidence.business_id == business_id
        ).scalar() or 0
        
        if total_evidence == 0:
            return 0.0
        
        # Weak evidence count
        weak_evidence = db.session.query(
            func.count(BusinessEvidence.id)
        ).filter(
            and_(
                BusinessEvidence.business_id == business_id,
                BusinessEvidence.evidence_strength == 'weak'
            )
        ).scalar() or 0
        
        return float(weak_evidence) / float(total_evidence)
    
    @staticmethod
    def calculate_silence_days(business_id: int, as_of_date: Optional[datetime] = None) -> int:
        """
        Calculate days since last statement.
        
        Args:
            business_id: Business ID
            as_of_date: Date to calculate as of (defaults to now)
        
        Returns:
            Number of days since last statement (0 if statement today)
        """
        if as_of_date is None:
            as_of_date = datetime.utcnow()
        
        # Get latest statement date
        latest_statement = db.session.query(
            func.max(BusinessStatement.transaction_date)
        ).filter(
            BusinessStatement.business_id == business_id
        ).scalar()
        
        if latest_statement is None:
            # No statements ever - return large number
            return 999
        
        # Convert to datetime if it's a date
        if not isinstance(latest_statement, datetime):
            latest_statement = datetime.combine(latest_statement, datetime.min.time())
        
        # Calculate days difference
        delta = as_of_date - latest_statement
        return max(0, delta.days)
    
    @staticmethod
    def detect_abnormal_spike(business_id: int, target_date: Optional[datetime] = None) -> bool:
        """
        Detect abnormal turnover spike.
        
        Compare today's turnover against 30-day average.
        Spike = today > (30-day_avg * SPIKE_THRESHOLD_MULTIPLIER)
        
        Args:
            business_id: Business ID
            target_date: Date to check (defaults to today)
        
        Returns:
            True if spike detected, False otherwise
        """
        if target_date is None:
            target_date = datetime.utcnow().date()
        elif isinstance(target_date, datetime):
            target_date = target_date.date()
        
        # Get today's turnover
        today_turnover = ComplianceSignalService.calculate_daily_turnover(business_id, target_date)
        
        # Get 30-day average (excluding today)
        thirty_days_ago = target_date - timedelta(days=30)
        
        monthly_avg = db.session.query(
            func.avg(BusinessStatement.amount)
        ).filter(
            and_(
                BusinessStatement.business_id == business_id,
                func.date(BusinessStatement.transaction_date) >= thirty_days_ago,
                func.date(BusinessStatement.transaction_date) < target_date,
                BusinessStatement.statement_type == 'daily_sales'
            )
        ).scalar()
        
        if monthly_avg is None or monthly_avg == 0:
            # Not enough history - can't detect spike
            return False
        
        # Check if today exceeds threshold
        threshold = float(monthly_avg) * ComplianceSignalService.SPIKE_THRESHOLD_MULTIPLIER
        return today_turnover > threshold
    
    @staticmethod
    def get_business_signals(business_id: int, target_date: Optional[datetime] = None) -> Dict[str, any]:
        """
        Calculate all signals for a business on a given date.
        
        Pure calculation - returns dict of all metrics.
        Does NOT create database records.
        
        Args:
            business_id: Business ID
            target_date: Date to calculate signals for (defaults to today)
        
        Returns:
            Dictionary with all signal metrics
        """
        if target_date is None:
            target_date = datetime.utcnow()
        
        if isinstance(target_date, datetime):
            calc_date = target_date.date()
        else:
            calc_date = target_date
        
        # Calculate all metrics
        daily_turnover = ComplianceSignalService.calculate_daily_turnover(business_id, calc_date)
        monthly_turnover = ComplianceSignalService.calculate_monthly_turnover(
            business_id, calc_date.year, calc_date.month
        )
        evidence_ratio = ComplianceSignalService.calculate_evidence_ratio(business_id)
        weak_evidence_rate = ComplianceSignalService.calculate_weak_evidence_rate(business_id)
        silence_days = ComplianceSignalService.calculate_silence_days(business_id, target_date)
        abnormal_spike = ComplianceSignalService.detect_abnormal_spike(business_id, calc_date)
        
        return {
            'business_id': business_id,
            'signal_date': target_date,
            'daily_turnover': daily_turnover,
            'monthly_turnover': monthly_turnover,
            'evidence_ratio': evidence_ratio,
            'weak_evidence_rate': weak_evidence_rate,
            'silence_days': silence_days,
            'abnormal_spike_flag': abnormal_spike,
        }
    
    @staticmethod
    def store_signal(signals_dict: Dict) -> ComplianceSignal:
        """
        Store calculated signals in database.
        
        Creates or updates ComplianceSignal record.
        Called after all calculations complete.
        
        Args:
            signals_dict: Dictionary from get_business_signals()
        
        Returns:
            ComplianceSignal model instance
        """
        # Check if signal already exists for this business on this date
        existing = ComplianceSignal.query.filter_by(
            business_id=signals_dict['business_id'],
            signal_date=signals_dict['signal_date']
        ).first()
        
        if existing:
            # Update existing (should be rare - signals are immutable, but allow one-time update)
            signal = existing
        else:
            # Create new signal
            signal = ComplianceSignal(
                business_id=signals_dict['business_id'],
                signal_date=signals_dict['signal_date'],
            )
        
        # Set all metric fields
        signal.daily_turnover = signals_dict['daily_turnover']
        signal.monthly_turnover = signals_dict['monthly_turnover']
        signal.evidence_ratio = signals_dict['evidence_ratio']
        signal.weak_evidence_rate = signals_dict['weak_evidence_rate']
        signal.silence_days = signals_dict['silence_days']
        signal.abnormal_spike_flag = signals_dict['abnormal_spike_flag']
        
        db.session.add(signal)
        db.session.commit()
        
        return signal
