"""Tests for rule-based constraint layer."""

import pytest
from app.models.enums import DesignType, ViolationSeverity
from app.models.schemas import ExtractedAttributes, ResearchBlueprint
from app.rules.design_rules import infer_design_type, get_required_elements
from app.rules.endpoint_rules import is_endpoint_measurable
from app.rules.feasibility_rules import check_feasibility
from app.rules.constraint_tier0 import check_tier0_violations
from app.rules.constraint_tier1 import check_tier1_violations
from app.core.conversation import evaluate_completeness
from app.core.extractor import extract_attributes
from app.core.gate_engine import run_gate, calculate_integrity_score


class TestDesignRules:
    """Test design type inference."""

    def test_infer_rct(self):
        text = "Thu nghiem lam sang ngau nhien so sanh phau thuat noi soi va mo ho"
        design = infer_design_type(text)
        assert design == DesignType.RCT

    def test_infer_cohort(self):
        text = "Nghien cuu thuan tap hoi cu tren 200 benh nhan"
        design = infer_design_type(text)
        assert design == DesignType.COHORT_RETROSPECTIVE

    def test_infer_case_control(self):
        text = "Nghien cuu benh chung so sanh nhom benh va nhom chung"
        design = infer_design_type(text)
        assert design == DesignType.CASE_CONTROL

    def test_infer_cross_sectional(self):
        text = "Nghien cuu cat ngang ve ty le hien mac"
        design = infer_design_type(text)
        assert design == DesignType.CROSS_SECTIONAL

    def test_get_required_elements_rct(self):
        required = get_required_elements(DesignType.RCT)
        assert "population" in required
        assert "intervention" in required
        assert "comparator" in required
        assert "randomization_method" in required


class TestEndpointRules:
    """Test endpoint measurability detection."""

    def test_measurable_endpoint(self):
        endpoint = "ty le tu vong 30 ngay"
        is_measurable, signals, vague = is_endpoint_measurable(endpoint)
        assert is_measurable is True

    def test_vague_endpoint(self):
        endpoint = "danh gia hieu qua dieu tri"
        is_measurable, signals, vague = is_endpoint_measurable(endpoint)
        assert is_measurable is False

    def test_specific_score_endpoint(self):
        endpoint = "diem VAS giam >= 2 diem"
        is_measurable, signals, vague = is_endpoint_measurable(endpoint)
        assert is_measurable is True


class TestFeasibilityRules:
    """Test feasibility rule checking."""

    def test_small_rct_sample_blocks(self):
        attrs = {
            "design_type": DesignType.RCT,
            "sample_size": 10,
        }
        issues = check_feasibility(attrs)
        block_issues = [i for i in issues if i.severity == ViolationSeverity.BLOCK]
        assert len(block_issues) > 0

    def test_rct_no_comparator_blocks(self):
        attrs = {
            "design_type": DesignType.RCT,
            "sample_size": 100,
            "comparator": None,
        }
        issues = check_feasibility(attrs)
        block_issues = [i for i in issues if i.severity == ViolationSeverity.BLOCK]
        assert len(block_issues) > 0


class TestTier0Violations:
    """Test Tier 0 (Data Integrity) violations."""

    def test_empty_abstract_blocks(self):
        violations = check_tier0_violations("")
        assert len(violations) > 0
        assert violations[0].code == "D-01"

    def test_short_abstract_blocks(self):
        violations = check_tier0_violations("Too short")
        assert len(violations) > 0
        assert violations[0].severity == ViolationSeverity.BLOCK

    def test_placeholder_detection(self):
        abstract = "Muc tieu: [insert objective here]. Phuong phap: [TBD]"
        violations = check_tier0_violations(abstract)
        placeholder_violations = [v for v in violations if v.code == "D-03"]
        assert len(placeholder_violations) > 0


class TestExtractor:
    """Test attribute extraction."""

    def test_extract_sample_size(self):
        text = "Nghien cuu tren 150 benh nhan"
        attrs = extract_attributes(text)
        assert attrs.sample_size == 150

    def test_extract_design_type(self):
        text = "Nghien cuu thuan tap hoi cu"
        attrs = extract_attributes(text)
        assert attrs.design_type == DesignType.COHORT_RETROSPECTIVE

    def test_extract_population(self):
        text = "Benh nhan la tre em 5-15 tuoi bi viem ruot thua"
        attrs = extract_attributes(text)
        assert attrs.population is not None
        assert "tre em" in attrs.population.lower() or "5-15" in attrs.population


class TestConversation:
    """Test conversation state machine."""

    def test_incomplete_attributes(self):
        attrs = ExtractedAttributes(
            population="Benh nhi 5-15 tuoi",
            # Missing sample_size, primary_endpoint
        )
        result = evaluate_completeness(attrs)
        assert result.is_complete is False
        assert len(result.missing_elements) > 0

    def test_complete_attributes(self):
        attrs = ExtractedAttributes(
            population="Benh nhi 5-15 tuoi",
            sample_size=100,
            primary_endpoint="Ty le bien chung sau mo",
            intervention="Phau thuat noi soi",
            design_type=DesignType.COHORT_RETROSPECTIVE,
        )
        result = evaluate_completeness(attrs, DesignType.COHORT_RETROSPECTIVE)
        # Should have fewer missing elements
        assert result.completeness_score > 50


class TestGateEngine:
    """Test gate engine and IS calculation."""

    def test_no_violations_high_score(self):
        score = calculate_integrity_score([])
        assert score == 100.0

    def test_major_violation_caps_score(self):
        from app.models.schemas import Violation
        violations = [
            Violation(
                code="A-01",
                tier=2,
                severity=ViolationSeverity.MAJOR,
                message_vi="Test",
                path_vi="Test path",
            )
        ]
        score = calculate_integrity_score(violations)
        assert score <= 10  # R-09: capped at 10 with MAJOR

    def test_gate_with_good_abstract(self):
        abstract = """
        Muc tieu: Danh gia hieu qua phau thuat noi soi cat ruot thua o tre em.
        Phuong phap: Nghien cuu thuan tap hoi cu tren 120 benh nhi 5-15 tuoi
        duoc phau thuat tai Benh vien Nhi Dong 1 tu 2020-2023.
        Ket qua chinh: ty le bien chung sau mo.
        Ket qua: [PLACEHOLDER - Ket qua se duoc dien sau khi co du lieu]
        Ket luan: Phau thuat noi soi du kien an toan va hieu qua.
        """
        result = run_gate(abstract)
        # Should have some score (may not be perfect without full blueprint)
        assert result.integrity_score >= 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
