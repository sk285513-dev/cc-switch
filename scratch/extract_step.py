import json

transcript_full_path = r"C:\Users\temp\.gemini\antigravity\brain\3c092ea4-56b0-4204-8f0d-93b116c3a423\.system_generated\logs\transcript_full.jsonl"
output_path = r"c:\Users\temp\antigravity\LexMind-Omni-法律實務-AI-工作站\scratch\extracted_steps.txt"

lines_to_extract = [1134, 1135, 1169, 1340, 1342, 1345, 1421, 1456, 1471]

with open(output_path, "w", encoding="utf-8") as out_f:
    with open(transcript_full_path, "r", encoding="utf-8") as f:
        for idx, line in enumerate(f, 1):
            if idx in lines_to_extract:
                try:
                    obj = json.loads(line)
                    out_f.write(f"--- Line {idx} | Step {obj.get('step_index')} | Type {obj.get('type')} ---\n")
                    tool_calls = obj.get("tool_calls", [])
                    out_f.write(f"Tool Calls count: {len(tool_calls)}\n")
                    for tc_idx, tc in enumerate(tool_calls):
                        out_f.write(f"  Tool {tc_idx}: {tc.get('name')}\n")
                        args = tc.get("args", {})
                        for k, v in args.items():
                            if k in ["TargetFile", "CommandLine", "Instruction", "Description", "ReplacementContent", "ReplacementChunks"]:
                                out_f.write(f"    {k}: {json.dumps(v, ensure_ascii=False, indent=2)}\n")
                    content = obj.get("content", "")
                    if content:
                        out_f.write(f"  Content preview: {content[:2000]}\n")
                    out_f.write("\n")
                except Exception as e:
                    out_f.write(f"Error parsing line {idx}: {str(e)}\n\n")

print("Done extracting!")
