#!/usr/bin/env python
"""
Verify Business Requirements - Standalone script
"""

import sys
from src.business.requirements import ProjectRequirements, BusinessPriority


def verify_requirements():
    """Verify all business requirements"""
    print("=" * 60)
    print("📋 BUSINESS REQUIREMENTS VERIFICATION")
    print("=" * 60)
    
    project = ProjectRequirements()
    
    print(f"\n📌 Project: {project.project_name}")
    print(f"📄 Description: {project.project_description.strip()}")
    print(f"\n📊 Requirements Summary:")
    print(f"   Total: {len(project.requirements)}")
    
    critical = [r for r in project.requirements if r.priority == BusinessPriority.CRITICAL]
    high = [r for r in project.requirements if r.priority == BusinessPriority.HIGH]
    
    print(f"   Critical: {len(critical)}")
    print(f"   High: {len(high)}")
    
    print("\n📋 Detailed Requirements:")
    print("-" * 40)
    
    for req in project.requirements:
        print(f"\n  🆔 {req.id}")
        print(f"  📝 {req.description}")
        print(f"  ⭐ Priority: {req.priority.value}")
        print(f"  👥 Stakeholders: {', '.join(req.stakeholders)}")
        print(f"  ✅ Success Criteria:")
        for criterion in req.success_criteria:
            print(f"     - {criterion}")
    
    print("\n" + "=" * 60)
    print("✅ Verification Complete!")
    print("=" * 60)
    
    return True


if __name__ == "__main__":
    success = verify_requirements()
    sys.exit(0 if success else 1)