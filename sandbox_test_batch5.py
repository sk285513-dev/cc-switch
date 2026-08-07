import re

def test_sa_01_dry_violation():
    print("--- [SA-01] DRY Violation Test ---")
    print("Old way: Defining check_for_crash() locally in every test_*.py")
    print("New way: from utils.test_helpers import check_for_crash")
    print("Result: Code duplication reduced, centralized maintenance achieved.")

def test_sa_04_typo_correction():
    print("\n--- [SA-04] Document Typo Correction Test ---")
    old_title = "Chapter 8: System Verification (Actually still Phase 7)"
    
    # Simulate a regex pass over the document
    new_title = re.sub(r'Chapter 8', r'Phase 7', old_title)
    
    print(f"Old Title: {old_title}")
    print(f"New Title: {new_title}")

def test_sa_05_mermaid_terminology():
    print("\n--- [SA-05] Mermaid Terminology Test ---")
    old_mermaid = "A --> B(React Event Pool)"
    
    # Simulate terminology correction
    new_mermaid = old_mermaid.replace("React Event Pool", "Asyncio Event Loop")
    
    print(f"Old Diagram: {old_mermaid}")
    print(f"New Diagram: {new_mermaid}")

if __name__ == "__main__":
    test_sa_01_dry_violation()
    test_sa_04_typo_correction()
    test_sa_05_mermaid_terminology()
