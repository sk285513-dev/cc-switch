import sys
sys.path.append('C:\\LocalAI_Workstation\\scripts')
from duplicate_guard import check_name_duplicate, is_already_ingested

f_path = r"J:\民法\ch15\預約 15 2024-10-20 01-28-14-345.mp4"
print("check_name_duplicate:", check_name_duplicate(f_path))
print("is_already_ingested:", is_already_ingested(f_path))
