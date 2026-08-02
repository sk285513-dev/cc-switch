import codecs

path = r'C:\LocalAI_Workstation\scripts_v6\kpi_monitor.py'
with codecs.open(path, 'r', 'utf-8') as f:
    content = f.read()

# Fix 1: datetime.datetime.now().strftime -> datetime.datetime.now(datetime.timezone.utc).strftime (or just now(UTC))
content = content.replace(
    'ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")',
    'ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")  # keeping naive for log display'
)

# Fix 2: isoformat
content = content.replace(
    '        "ts": datetime.datetime.now().isoformat(),',
    '        "ts": datetime.datetime.now(datetime.timezone.utc).isoformat(),'
)

# Fix 3: subtraction
old_sub = '''        try:
            t_prev = datetime.datetime.fromisoformat(prev["ts"])
            elapsed = (now - t_prev).total_seconds()'''

new_sub = '''        try:
            t_prev = datetime.datetime.fromisoformat(prev["ts"])
            if t_prev.tzinfo is None:
                t_prev = t_prev.replace(tzinfo=datetime.timezone.utc)
            # Use actual UTC now, not _tw (which is +8h)
            actual_now_utc = datetime.datetime.now(datetime.timezone.utc)
            elapsed = (actual_now_utc - t_prev).total_seconds()'''

if old_sub in content:
    content = content.replace(old_sub, new_sub)

with codecs.open(path, 'w', 'utf-8') as f:
    f.write(content)

print("KPI monitor fixed")
