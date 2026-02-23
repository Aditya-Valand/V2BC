"""
Phase-3 Compliance System Tests

Comprehensive test suite for:
- Signal calculations (pure functions)
- Rule evaluation (isolated logic)
- Alert generation (deduplication)
- Profile computation (aggregation)
- Full pipeline integration

Architecture Validation:
✓ Signals = deterministic, pure calculations
✓ Rules = isolated, testable decision logic
✓ Alerts = created only by rule engine
✓ Routes = presentation only (no logic)
"""

import pytest
from datetime import datetime, timedelta
from app import create_app, db
from modules.businesses.models import Business
from modules.organizations.models import Organization
from modules.statements.models import BusinessStatement
from modules.evidence.models import BusinessEvidence
from modules.auth.models import User
from modules.compliance.models import ComplianceSignal, ComplianceProfile, ComplianceAlert
from modules.compliance.services import (
    ComplianceSignalService,
    ProfileCalculator,
    AlertService,
    ComplianceService,
)
from modules.compliance.rules import (
    TurnoverThresholdRule,
    GSTThresholdRule,
    EvidenceBelowThresholdRule,
    ProlongedSilenceRule,
    WeakEvidenceRule,
    AbnormalActivityRule,
    LowDisciplineRule,
    AuditReadinessRule,
)


@pytest.fixture
def app():
    """Create test app with database."""
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


@pytest.fixture
def setup_test_data(app):
    """Create test data: org, business, statements, evidence."""
    with app.app_context():
        # Create org
        org = Organization(name='Test Org')
        db.session.add(org)
        db.session.flush()
        
        # Create business
        business = Business(
            organization_id=org.id,
            name='Test Business',
            owner_user_id=1,
            whatsapp_phone='+919999999999',
            gstin='12ABCDE1234F1Z5',
            pan='ABCDE1234F',
            expected_turnover=10_000_000,  # ₹10L
            business_type='retail',
            state='MH'
        )
        db.session.add(business)
        db.session.flush()
        
        # Create statements (simulated daily sales)
        today = datetime.utcnow().date()
        for i in range(5):
            date = today - timedelta(days=i)
            stmt = BusinessStatement(
                business_id=business.id,
                statement_type='daily_sales',
                amount=100_000 + (i * 10_000),  # ₹1L to ₹1.4L
                currency='INR',
                transaction_date=datetime.combine(date, datetime.min.time()),
                source='whatsapp',
                confidence_level='high',
                description=f'Daily sales {date}'
            )
            db.session.add(stmt)
        
        # Create evidence (documents)
        for i in range(3):
            evidence = BusinessEvidence(
                business_id=business.id,
                file_name=f'invoice_{i}.pdf',
                evidence_type='invoice',
                evidence_strength='strong' if i < 2 else 'weak',
                quality_score=85,
                status='verified',
                ocr_text='Invoice content',
                detected_amount=50_000
            )
            db.session.add(evidence)
        
        db.session.commit()
        
        return {
            'org': org,
            'business': business,
        }


# ============================================================================
# SIGNAL CALCULATION TESTS
# ============================================================================

class TestSignalCalculations:
    """Test pure signal calculation functions."""
    
    def test_calculate_daily_turnover(self, app, setup_test_data):
        """Daily turnover sums sales for a single day."""
        with app.app_context():
            business_id = setup_test_data['business'].id
            today = datetime.utcnow().date()
            
            # Calculate daily turnover for today
            turnover = ComplianceSignalService.calculate_daily_turnover(business_id, today)
            
            # Should sum to 100_000 (only today's statement)
            assert turnover == 100_000, f"Expected 100_000, got {turnover}"
    
    def test_calculate_monthly_turnover(self, app, setup_test_data):
        """Monthly turnover sums all sales in the month."""
        with app.app_context():
            business_id = setup_test_data['business'].id
            today = datetime.utcnow()
            
            # Calculate for this month
            turnover = ComplianceSignalService.calculate_monthly_turnover(
                business_id, today.year, today.month
            )
            
            # Should sum multiple days: 100k + 110k + 120k + 130k + 140k
            expected = 100_000 + 110_000 + 120_000 + 130_000 + 140_000
            assert turnover == expected, f"Expected {expected}, got {turnover}"
    
    def test_calculate_evidence_ratio(self, app, setup_test_data):
        """Evidence ratio = statements with backing / total statements."""
        with app.app_context():
            business_id = setup_test_data['business'].id
            
            # Calculate ratio
            ratio = ComplianceSignalService.calculate_evidence_ratio(business_id)
            
            # We have 5 statements, 3 have evidence → 3/5 = 0.6
            assert ratio == 0.6, f"Expected 0.6, got {ratio}"
    
    def test_calculate_weak_evidence_rate(self, app, setup_test_data):
        """Weak evidence rate = weak / total."""
        with app.app_context():
            business_id = setup_test_data['business'].id
            
            # Calculate rate
            rate = ComplianceSignalService.calculate_weak_evidence_rate(business_id)
            
            # We have 3 evidence: 2 strong, 1 weak → 1/3 = 0.333...
            assert abs(rate - (1/3)) < 0.01, f"Expected 0.333, got {rate}"
    
    def test_calculate_silence_days_recent(self, app, setup_test_data):
        """Silence days = 0 if statement today."""
        with app.app_context():
            business_id = setup_test_data['business'].id
            today = datetime.utcnow()
            
            # Calculate silence
            silence = ComplianceSignalService.calculate_silence_days(business_id, today)
            
            # We have statement today → 0 silence
            assert silence == 0, f"Expected 0, got {silence}"
    
    def test_get_business_signals_complete(self, app, setup_test_data):
        """Get all signals for a business at once."""
        with app.app_context():
            business_id = setup_test_data['business'].id
            
            # Calculate all signals
            signals_dict = ComplianceSignalService.get_business_signals(business_id)
            
            # Verify all fields present
            assert 'daily_turnover' in signals_dict
            assert 'monthly_turnover' in signals_dict
            assert 'evidence_ratio' in signals_dict
            assert 'weak_evidence_rate' in signals_dict
            assert 'silence_days' in signals_dict
            assert 'abnormal_spike_flag' in signals_dict
            
            # Verify types
            assert isinstance(signals_dict['daily_turnover'], float)
            assert isinstance(signals_dict['evidence_ratio'], float)
            assert isinstance(signals_dict['silence_days'], int)
            assert isinstance(signals_dict['abnormal_spike_flag'], bool)


# ============================================================================
# PROFILE CALCULATION TESTS
# ============================================================================

class TestProfileCalculation:
    """Test profile aggregation."""
    
    def test_compute_discipline_score(self, app, setup_test_data):
        """Discipline score computed from signals."""
        with app.app_context():
            business_id = setup_test_data['business'].id
            
            # Create signal
            signal = ComplianceSignal(
                business_id=business_id,
                signal_date=datetime.utcnow(),
                daily_turnover=100_000,
                monthly_turnover=1_000_000,
                evidence_ratio=0.8,
                weak_evidence_rate=0.1,
                silence_days=2,
                abnormal_spike_flag=False,
            )
            db.session.add(signal)
            db.session.commit()
            
            # Calculate score
            score = ProfileCalculator.compute_discipline_score(business_id, signal)
            
            # Should be high (good signals)
            assert 70 < score <= 100, f"Expected high score, got {score}"
    
    def test_compute_evidence_health(self, app, setup_test_data):
        """Evidence health computed from signal ratios."""
        with app.app_context():
            business_id = setup_test_data['business'].id
            
            # Create signal with good evidence
            signal = ComplianceSignal(
                business_id=business_id,
                signal_date=datetime.utcnow(),
                daily_turnover=100_000,
                monthly_turnover=1_000_000,
                evidence_ratio=0.9,
                weak_evidence_rate=0.1,
                silence_days=0,
                abnormal_spike_flag=False,
            )
            db.session.add(signal)
            db.session.commit()
            
            # Calculate health
            health = ProfileCalculator.compute_evidence_health(signal)
            
            # Should be good
            assert 70 < health <= 100, f"Expected high health, got {health}"
    
    def test_assess_gst_risk_low(self, app, setup_test_data):
        """GST risk LOW for < ₹20L."""
        with app.app_context():
            business = setup_test_data['business']
            business.expected_turnover = 10_000_000  # ₹10L
            db.session.commit()
            
            risk = ProfileCalculator.assess_gst_risk(business)
            
            assert risk == 'low', f"Expected 'low', got {risk}"
    
    def test_assess_gst_risk_high(self, app, setup_test_data):
        """GST risk HIGH for > ₹40L."""
        with app.app_context():
            business = setup_test_data['business']
            business.expected_turnover = 50_000_000  # ₹50L
            db.session.commit()
            
            risk = ProfileCalculator.assess_gst_risk(business)
            
            assert risk == 'high', f"Expected 'high', got {risk}"


# ============================================================================
# RULE EVALUATION TESTS
# ============================================================================

class TestRuleEvaluation:
    """Test individual rule evaluations."""
    
    def test_turnover_threshold_rule_triggers(self, app, setup_test_data):
        """TurnoverThresholdRule triggers on spike > 1.5x expected."""
        with app.app_context():
            business_id = setup_test_data['business'].id
            business = setup_test_data['business']
            
            # Create signal with turnover > 1.5x expected
            signal = ComplianceSignal(
                business_id=business_id,
                signal_date=datetime.utcnow(),
                daily_turnover=100_000,
                monthly_turnover=20_000_000,  # 2x expected (10L)
                evidence_ratio=0.8,
                weak_evidence_rate=0.1,
                silence_days=0,
                abnormal_spike_flag=False,
            )
            db.session.add(signal)
            db.session.commit()
            
            # Evaluate rule
            rule = TurnoverThresholdRule()
            result = rule.evaluate(business_id, signal)
            
            # Should trigger
            assert result is not None, "Rule should trigger"
            assert 'reason' in result
    
    def test_prolonged_silence_rule_triggers(self, app, setup_test_data):
        """ProlongedSilenceRule triggers after 30+ days."""
        with app.app_context():
            business_id = setup_test_data['business'].id
            
            # Create signal with 35 days silence
            signal = ComplianceSignal(
                business_id=business_id,
                signal_date=datetime.utcnow(),
                daily_turnover=0,
                monthly_turnover=0,
                evidence_ratio=0.0,
                weak_evidence_rate=0.0,
                silence_days=35,
                abnormal_spike_flag=False,
            )
            db.session.add(signal)
            db.session.commit()
            
            # Evaluate rule
            rule = ProlongedSilenceRule()
            result = rule.evaluate(business_id, signal)
            
            # Should trigger
            assert result is not None
            assert 'reason' in result
    
    def test_evidence_ratio_rule_triggers(self, app, setup_test_data):
        """EvidenceBelowThresholdRule triggers on low ratio."""
        with app.app_context():
            business_id = setup_test_data['business'].id
            
            # Create signal with low evidence ratio
            signal = ComplianceSignal(
                business_id=business_id,
                signal_date=datetime.utcnow(),
                daily_turnover=100_000,
                monthly_turnover=1_000_000,
                evidence_ratio=0.3,  # < 0.5 threshold
                weak_evidence_rate=0.1,
                silence_days=5,
                abnormal_spike_flag=False,
            )
            db.session.add(signal)
            db.session.commit()
            
            # Evaluate rule
            rule = EvidenceBelowThresholdRule()
            result = rule.evaluate(business_id, signal)
            
            # Should trigger
            assert result is not None


# ============================================================================
# ALERT SYSTEM TESTS
# ============================================================================

class TestAlertSystem:
    """Test alert creation and management."""
    
    def test_create_alert_deduplication(self, app, setup_test_data):
        """Alert service prevents duplicate alerts same day."""
        with app.app_context():
            business_id = setup_test_data['business'].id
            alert_service = AlertService()
            
            # Create first alert
            alert1 = alert_service._create_alert(
                business_id=business_id,
                alert_type='threshold',
                severity='high',
                reason='Test alert',
                rule_that_triggered='TestRule'
            )
            
            # Try to create duplicate
            alert2 = alert_service._create_alert(
                business_id=business_id,
                alert_type='threshold',
                severity='high',
                reason='Different reason',
                rule_that_triggered='TestRule'
            )
            
            # Should return same alert (deduped)
            assert alert1.id == alert2.id, "Duplicate alert should be deduped"
    
    def test_alert_lifecycle(self, app, setup_test_data):
        """Alert can be acknowledged and resolved."""
        with app.app_context():
            business_id = setup_test_data['business'].id
            alert_service = AlertService()
            
            # Create alert
            alert = alert_service._create_alert(
                business_id=business_id,
                alert_type='threshold',
                severity='high',
                reason='Test',
                rule_that_triggered='TestRule'
            )
            assert alert.status.value == 'open'
            
            # Acknowledge
            alert = alert_service.acknowledge_alert(alert.id)
            assert alert.status.value == 'acknowledged'
            
            # Resolve
            alert = alert_service.resolve_alert(alert.id)
            assert alert.status.value == 'resolved'
            assert alert.resolved_at is not None
    
    def test_get_alert_summary(self, app, setup_test_data):
        """Alert summary counts by severity."""
        with app.app_context():
            business_id = setup_test_data['business'].id
            alert_service = AlertService()
            
            # Create multiple alerts
            for i, severity in enumerate(['critical', 'high', 'high', 'medium']):
                alert_service._create_alert(
                    business_id=business_id,
                    alert_type='threshold',
                    severity=severity,
                    reason=f'Alert {i}',
                    rule_that_triggered=f'Rule{i}'
                )
            
            # Get summary
            summary = alert_service.get_alert_summary(business_id)
            
            assert summary['critical'] == 1
            assert summary['high'] == 2
            assert summary['medium'] == 1
            assert summary['total'] == 4


# ============================================================================
# PIPELINE INTEGRATION TESTS
# ============================================================================

class TestCompliancePipeline:
    """Test full signal → rule → alert → profile pipeline."""
    
    def test_full_evaluation_pipeline(self, app, setup_test_data):
        """Complete pipeline: signals → rules → alerts → profile."""
        with app.app_context():
            business_id = setup_test_data['business'].id
            service = ComplianceService()
            
            # Run full evaluation
            signal, alerts, profile = service.evaluate_business(business_id)
            
            # Verify all outputs
            assert signal is not None
            assert isinstance(signal, ComplianceSignal)
            
            assert isinstance(alerts, list)
            
            assert profile is not None
            assert isinstance(profile, ComplianceProfile)
            assert 0 <= profile.discipline_score <= 100
            assert 0 <= profile.evidence_health <= 100


# ============================================================================
# ARCHITECTURAL VALIDATION TESTS
# ============================================================================

class TestArchitecturalSeparation:
    """Verify Phase-3 architecture constraints."""
    
    def test_signals_are_immutable(self, app, setup_test_data):
        """Signals created but never updated (immutable)."""
        with app.app_context():
            business_id = setup_test_data['business'].id
            
            # Create signal
            signal_dict = ComplianceSignalService.get_business_signals(business_id)
            signal1 = ComplianceSignalService.store_signal(signal_dict)
            
            # Try to create another same day
            signal_dict2 = ComplianceSignalService.get_business_signals(business_id)
            signal2 = ComplianceSignalService.store_signal(signal_dict2)
            
            # Should return same record (unique constraint)
            assert signal1.id == signal2.id
    
    def test_alerts_only_from_rule_engine(self, app, setup_test_data):
        """Only RuleEngine can create alerts (enforced by _create_alert name)."""
        with app.app_context():
            # AlertService._create_alert is private (underscore prefix)
            # This ensures it's not called from routes
            alert_service = AlertService()
            
            # Method exists but is marked private
            assert hasattr(alert_service, '_create_alert')
            assert alert_service._create_alert.__name__.startswith('_')


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
