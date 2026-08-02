import sys
sys.path.append('C:\\LocalAI_Workstation\\scripts')
from setup_wizard import update_config, get_current_strategy_status

update_config('stt_engine', 'gemini')
update_config('merge_engine', 'vertexai')
update_config('gemini_model_high_accuracy', 'gemini-2.5-flash')

print(get_current_strategy_status())
