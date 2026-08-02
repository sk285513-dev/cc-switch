import sys
sys.path.insert(0, 'C:/LocalAI_Workstation')
try:
    from scripts.agent_core_pro import LocalLegalAgent
    agent = LocalLegalAgent(context_role="申訴人/律師時效防禦")
    print("SUCCESS")
except Exception as e:
    import traceback
    traceback.print_exc()
