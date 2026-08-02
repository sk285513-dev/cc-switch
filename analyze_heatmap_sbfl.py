import json
import collections
import os

def generate_error_correlation():
    json_path = r"C:\LocalAI_Workstation\crawler_dump_real.json"
    
    if not os.path.exists(json_path):
        print(f"錯誤：找不到軌跡檔案 {json_path}。請先執行爬蟲。")
        return
        
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            state_dump = json.load(f)
    except Exception as e:
        print(f"讀取 JSON 發生錯誤: {e}")
        return
        
    crash_counts = collections.defaultdict(int)
    total_counts = collections.defaultdict(int)
    
    print("\n=== 多維度錯誤特徵關聯分析 (SBFL) ===")
    print(f"總共讀取了 {len(state_dump)} 筆狀態紀錄\n")
    
    for state in state_dump:
        truth_table = state.get("ui_truth_table", {})
        is_crashed = state.get("crash_detected", False)
        
        # 針對這一個狀態截圖，將打勾的特徵納入統計
        for feature, is_checked in truth_table.items():
            if is_checked:
                total_counts[feature] += 1
                if is_crashed:
                    crash_counts[feature] += 1
                    
    for feature in total_counts:
        crash_rate = crash_counts[feature] / total_counts[feature]
        # 篩選出崩潰率異常偏高的危險特徵 (大於 50%)
        if crash_rate > 0.5:
            print(f"   [🚨 高危特徵] {feature}: 出現次數 {total_counts[feature]} | 導致崩潰機率: {crash_rate:.2%}")
        else:
            print(f"   [✅ 安全特徵] {feature}: 出現次數 {total_counts[feature]} | 崩潰機率: {crash_rate:.2%}")
            
    print("\n分析完畢。")

if __name__ == "__main__":
    generate_error_correlation()
