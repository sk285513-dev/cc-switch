import json

transcript_full_path = r"C:\Users\temp\.gemini\antigravity\brain\3c092ea4-56b0-4204-8f0d-93b116c3a423\.system_generated\logs\transcript_full.jsonl"
output_path = r"c:\Users\temp\antigravity\LexMind-Omni-法律實務-AI-工作站\scratch\all_app_edits.txt"

with open(output_path, "w", encoding="utf-8") as out_f:
    with open(transcript_full_path, "r", encoding="utf-8") as f:
        for idx, line in enumerate(f, 1):
            if "replace_file_content" in line or "multi_replace_file_content" in line:
                try:
                    obj = json.loads(line)
                    tool_calls = obj.get("tool_calls", [])
                    for tc in tool_calls:
                        if tc.get("name") in ["replace_file_content", "multi_replace_file_content"]:
                            args = tc.get("args", {})
                            target = args.get("TargetFile", "")
                            if "App.tsx" in target:
                                out_f.write(f"=== Line {idx} | Step {obj.get('step_index')} | Tool {tc.get('name')} ===\n")
                                out_f.write(f"Description: {args.get('Description')}\n")
                                out_f.write(f"Instruction: {args.get('Instruction')}\n")
                                if tc.get("name") == "replace_file_content":
                                    out_f.write(f"TargetContent:\n{args.get('TargetContent')}\n\n")
                                    out_f.write(f"ReplacementContent:\n{args.get('ReplacementContent')}\n\n")
                                else:
                                    chunks = args.get("ReplacementChunks", [])
                                    out_f.write(f"Chunks count: {len(chunks)}\n")
                                    for c_idx, chunk in enumerate(chunks):
                                        out_f.write(f"  Chunk {c_idx}:\n")
                                        out_f.write(f"    TargetContent:\n{chunk.get('TargetContent')}\n\n")
                                        out_f.write(f"    ReplacementContent:\n{chunk.get('ReplacementContent')}\n\n")
                                out_f.write("-" * 80 + "\n\n")
                except Exception as e:
                    out_f.write(f"Error parsing line {idx}: {str(e)}\n\n")

print("Done extracting all edits!")
