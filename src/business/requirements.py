"""
Business Requirements - Complete
"""

from dataclasses import dataclass, field
from enum import Enum


class BusinessPriority(Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class BusinessRequirement:
    id: str
    description: str
    priority: BusinessPriority
    stakeholders: list[str]
    success_criteria: list[str]


@dataclass
class ProjectRequirements:
    project_name: str = "Customer Demand Forecasting"
    project_description: str = """
    Build a production-grade demand forecasting system that predicts customer demand
    for retail products with 95% accuracy, enabling optimized inventory management,
    reduced stockouts, and improved supply chain efficiency.
    """
    requirements: list[BusinessRequirement] = field(
        default_factory=lambda: [
            BusinessRequirement(
                id="REQ-001",
                description="Predict product demand at store level for next 30 days",
                priority=BusinessPriority.CRITICAL,
                stakeholders=["Supply Chain", "Operations", "Finance"],
                success_criteria=[
                    "RMSE < 0.15",
                    "MAPE < 10%",
                    "Forecast accuracy > 90% at 7-day horizon",
                ],
            ),
            BusinessRequirement(
                id="REQ-002",
                description="Handle 2M+ daily inference requests with < 100ms latency",
                priority=BusinessPriority.CRITICAL,
                stakeholders=["Engineering", "Operations"],
                success_criteria=["P95 latency < 100ms", "Throughput > 500 req/s", "99.9% uptime"],
            ),
            BusinessRequirement(
                id="REQ-003",
                description="Automated retraining pipeline with drift detection",
                priority=BusinessPriority.HIGH,
                stakeholders=["Data Science", "ML Engineering"],
                success_criteria=[
                    "Daily drift detection",
                    "Weekly automated retraining",
                    "Model performance degradation < 5%",
                ],
            ),
        ]
    )
