"""
Unit tests for Business Requirements module
"""

from src.business.requirements import BusinessPriority, BusinessRequirement, ProjectRequirements


class TestBusinessPriority:
    """Test BusinessPriority enum"""

    def test_priority_values(self):
        """Test priority enum values"""
        assert BusinessPriority.CRITICAL.value == "critical"
        assert BusinessPriority.HIGH.value == "high"
        assert BusinessPriority.MEDIUM.value == "medium"
        assert BusinessPriority.LOW.value == "low"

    def test_priority_enum_members(self):
        """Test all enum members exist"""
        priorities = [p.value for p in BusinessPriority]
        assert "critical" in priorities
        assert "high" in priorities
        assert "medium" in priorities
        assert "low" in priorities


class TestBusinessRequirement:
    """Test BusinessRequirement dataclass"""

    def test_requirement_creation(self):
        """Test creating a business requirement"""
        req = BusinessRequirement(
            id="REQ-001",
            description="Test requirement",
            priority=BusinessPriority.CRITICAL,
            stakeholders=["Team A", "Team B"],
            success_criteria=["Metric 1", "Metric 2"],
        )

        assert req.id == "REQ-001"
        assert req.description == "Test requirement"
        assert req.priority == BusinessPriority.CRITICAL
        assert len(req.stakeholders) == 2
        assert len(req.success_criteria) == 2

    def test_requirement_with_different_priority(self):
        """Test requirement with different priority levels"""
        req = BusinessRequirement(
            id="REQ-002",
            description="Low priority requirement",
            priority=BusinessPriority.LOW,
            stakeholders=["Team C"],
            success_criteria=["Metric X"],
        )

        assert req.priority == BusinessPriority.LOW
        assert req.priority.value == "low"


class TestProjectRequirements:
    """Test ProjectRequirements dataclass"""

    def test_project_requirements_creation(self):
        """Test creating project requirements"""
        project = ProjectRequirements()

        assert project.project_name == "Customer Demand Forecasting"
        assert "production-grade" in project.project_description
        assert len(project.requirements) == 3

    def test_project_requirements_has_critical_requirements(self):
        """Test project has critical requirements"""
        project = ProjectRequirements()

        critical_reqs = [r for r in project.requirements if r.priority == BusinessPriority.CRITICAL]

        assert len(critical_reqs) >= 2
        assert any(r.id == "REQ-001" for r in critical_reqs)
        assert any(r.id == "REQ-002" for r in critical_reqs)

    def test_requirement_req001_details(self):
        """Test REQ-001 details"""
        project = ProjectRequirements()
        req = next((r for r in project.requirements if r.id == "REQ-001"), None)

        assert req is not None
        assert req.priority == BusinessPriority.CRITICAL
        assert "Supply Chain" in req.stakeholders
        assert "RMSE < 0.15" in req.success_criteria

    def test_requirement_req002_details(self):
        """Test REQ-002 details"""
        project = ProjectRequirements()
        req = next((r for r in project.requirements if r.id == "REQ-002"), None)

        assert req is not None
        assert req.priority == BusinessPriority.CRITICAL
        assert "Engineering" in req.stakeholders
        assert "P95 latency < 100ms" in req.success_criteria

    def test_requirement_req003_details(self):
        """Test REQ-003 details"""
        project = ProjectRequirements()
        req = next((r for r in project.requirements if r.id == "REQ-003"), None)

        assert req is not None
        assert req.priority == BusinessPriority.HIGH
        assert "Data Science" in req.stakeholders
        assert "Daily drift detection" in req.success_criteria

    def test_all_requirements_have_stakeholders(self):
        """Test all requirements have stakeholders"""
        project = ProjectRequirements()

        for req in project.requirements:
            assert len(req.stakeholders) > 0, f"{req.id} has no stakeholders"

    def test_all_requirements_have_success_criteria(self):
        """Test all requirements have success criteria"""
        project = ProjectRequirements()

        for req in project.requirements:
            assert len(req.success_criteria) > 0, f"{req.id} has no success criteria"

    def test_requirements_unique_ids(self):
        """Test all requirements have unique IDs"""
        project = ProjectRequirements()
        ids = [r.id for r in project.requirements]
        assert len(ids) == len(set(ids)), "Duplicate requirement IDs found"


class TestBusinessRequirementsIntegration:
    """Integration tests for business requirements"""

    def test_requirements_cover_all_priorities(self):
        """Test requirements cover all priority levels"""
        project = ProjectRequirements()
        priorities = [r.priority for r in project.requirements]

        assert BusinessPriority.CRITICAL in priorities
        assert BusinessPriority.HIGH in priorities

    def test_requirements_summary(self):
        """Test generating a summary of requirements"""
        project = ProjectRequirements()

        summary = {
            "total": len(project.requirements),
            "critical": len(
                [r for r in project.requirements if r.priority == BusinessPriority.CRITICAL]
            ),
            "high": len([r for r in project.requirements if r.priority == BusinessPriority.HIGH]),
        }

        assert summary["total"] == 3
        assert summary["critical"] == 2
        assert summary["high"] == 1
        assert summary["critical"] + summary["high"] == summary["total"]

    def test_project_description_not_empty(self):
        """Test project description is not empty"""
        project = ProjectRequirements()
        assert project.project_description is not None
        assert len(project.project_description.strip()) > 0
        assert "production-grade" in project.project_description.lower()
