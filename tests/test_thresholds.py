from camber.domain.models import ThresholdRule, Status

def test_threshold_evaluation():
    rule = ThresholdRule(id=1, metric_type="acceleration",
                         warning_value=0.5, critical_value=1.0, unit="g")
    assert rule.evaluate(0.1) == Status.OK
    assert rule.evaluate(0.7) == Status.WARNING
    assert rule.evaluate(1.5) == Status.CRITICAL
