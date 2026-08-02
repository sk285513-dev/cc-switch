import os

plan_path = r'C:\Users\temp\.gemini\antigravity\brain\090c45c8-c66c-443a-b0a9-ac871eca1570\implementation_plan.md'

with open(plan_path, 'r', encoding='utf-8') as f:
    text = f.read()

# Fix 1: watchdog.py pythonw -> python + Redirect
text = text.replace(
    '''$wdProc = Start-Process pythonw `
        -ArgumentList "scripts_v6\\\\watchdog.py" `
        -WorkingDirectory $root `
        -WindowStyle Hidden `
        -PassThru''',
    '''$wdProc = Start-Process python `
        -ArgumentList "scripts_v6\\\\watchdog.py" `
        -WorkingDirectory $root `
        -WindowStyle Hidden `
        -RedirectStandardOutput $stdoutLog `
        -RedirectStandardError $stderrLog `
        -PassThru'''
)

# Fix 2: Out-File ErrorAction
text = text.replace(
    ''''{"exhausted_keys":[]}' | Out-File $quotaState -Encoding UTF8 -NoNewline''',
    ''''{"exhausted_keys":[]}' | Out-File $quotaState -Encoding UTF8 -NoNewline -ErrorAction SilentlyContinue'''
)

# Fix 3: timeout=120.0 in call_gemini_api for MAP
text = text.replace(
    '''cleaned_chunk = call_gemini_api(
                    PROMPT_CLEAN.format(text=chunk_content),
                    current_model,
                    api_key,
                    qm
                )''',
    '''cleaned_chunk = call_gemini_api(
                    PROMPT_CLEAN.format(text=chunk_content),
                    current_model,
                    api_key,
                    qm,
                    timeout=120.0
                )'''
)

# Fix 3: timeout=120.0 in call_gemini_api for REDUCE
text = text.replace(
    '''refined_gap = call_gemini_api(
                            PROMPT_GAP_REFINE.format(text=raw_gap),
                            current_model,
                            api_key,
                            qm
                        )''',
    '''refined_gap = call_gemini_api(
                            PROMPT_GAP_REFINE.format(text=raw_gap),
                            current_model,
                            api_key,
                            qm,
                            timeout=120.0
                        )'''
)

# Fix 3: timeout=120.0 in call_gemini_api for SUMMARY
text = text.replace(
    '''summary_text = call_gemini_api(
                PROMPT_SUMMARY.format(text=safe_cleaned_text),
                current_model,
                api_key,
                qm,
                use_search_grounding=True
            )''',
    '''summary_text = call_gemini_api(
                PROMPT_SUMMARY.format(text=safe_cleaned_text),
                current_model,
                api_key,
                qm,
                use_search_grounding=True,
                timeout=120.0
            )'''
)

with open(plan_path, 'w', encoding='utf-8') as f:
    f.write(text)

print('Plan patched with subagent fixes successfully.')
