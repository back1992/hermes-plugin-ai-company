"""Tests for role prompt templates."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


def test_prompts_module_exists():
    """prompts.py should be importable."""
    import prompts
    assert hasattr(prompts, 'ROLE_PROMPTS')


def test_prompts_has_all_seven_roles():
    """ROLE_PROMPTS should have keys for all 7 roles."""
    from prompts import ROLE_PROMPTS
    expected_roles = {
        'brainstormer', 'planner', 'implementer',
        'task_reviewer', 'verifier', 'reviewer', 'fixer'
    }
    assert set(ROLE_PROMPTS.keys()) == expected_roles


def test_prompts_render_with_placeholders():
    """Every prompt should render with the standard placeholders."""
    from prompts import ROLE_PROMPTS
    placeholders = {
        'project_path': '/test/project',
        'feature_name': 'test-feature',
        'previous_context': '(none)',
        'extra_context': '',
    }
    for role, template in ROLE_PROMPTS.items():
        rendered = template.format(**placeholders)
        assert '/test/project' in rendered, f"{role} prompt missing project_path"
        assert 'test-feature' in rendered, f"{role} prompt missing feature_name"


def test_prompts_contain_ponytail_ladder():
    """Every prompt should reference the Ponytail simplification ladder."""
    from prompts import ROLE_PROMPTS
    for role, template in ROLE_PROMPTS.items():
        lower = template.lower()
        has_ponytail = 'ponytail' in lower or 'ladder' in lower or 'rung' in lower
        assert has_ponytail, f"{role} prompt missing Ponytail ladder reference"


def test_implementer_has_iron_law():
    """Implementer prompt must contain the Iron Law TDD requirement."""
    from prompts import ROLE_PROMPTS
    assert 'IRON LAW' in ROLE_PROMPTS['implementer'] or 'Iron Law' in ROLE_PROMPTS['implementer']


def test_implementer_has_anti_rationalization():
    """Implementer prompt must contain anti-rationalization table."""
    from prompts import ROLE_PROMPTS
    assert 'ANTI-RATIONALIZATION' in ROLE_PROMPTS['implementer'] or 'Rationalization' in ROLE_PROMPTS['implementer']


def test_verifier_has_evidence_gate():
    """Verifier prompt must contain evidence-before-claims gate."""
    from prompts import ROLE_PROMPTS
    assert 'EVIDENCE' in ROLE_PROMPTS['verifier'] or 'evidence' in ROLE_PROMPTS['verifier']


def test_fixer_has_systematic_debugging():
    """Fixer prompt must contain systematic debugging phases."""
    from prompts import ROLE_PROMPTS
    assert 'Phase 1' in ROLE_PROMPTS['fixer'] or 'PHASE 1' in ROLE_PROMPTS['fixer']


def test_planner_has_self_review_checklist():
    """Planner prompt must contain self-review checklist."""
    from prompts import ROLE_PROMPTS
    assert 'SELF-REVIEW' in ROLE_PROMPTS['planner'] or 'Self-Review' in ROLE_PROMPTS['planner'] or 'self-review' in ROLE_PROMPTS['planner']
