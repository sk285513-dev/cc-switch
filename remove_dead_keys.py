import yaml

dead_keys = set([
    'key_040','key_041','key_042','key_043','key_046','key_048',
    'key_050','key_051','key_052','key_053','key_054','key_055',
    'key_056','key_057','key_058','key_059','key_060','key_061',
    'key_062','key_063','key_064','key_065','key_066','key_067',
    'key_068','key_069','key_070','key_071','key_072','key_073',
    'key_074','key_075','key_076','key_077','key_078','key_079',
    'key_090','key_091','key_092','key_093','key_094','key_095',
    'key_096','key_097','key_098','key_099','key_100','key_101',
    'key_102','key_103','key_104','key_105'
])

with open('config/keys.yaml', 'r', encoding='utf-8') as f:
    data = yaml.safe_load(f)

original = data.get('keys', [])
surviving = [k for k in original if k['name'] not in dead_keys]
removed = [k['name'] for k in original if k['name'] in dead_keys]

data['keys'] = surviving

with open('config/keys.yaml', 'w', encoding='utf-8') as f:
    yaml.dump(data, f, allow_unicode=True, sort_keys=False)

print(f'原始: {len(original)} 個')
print(f'移除: {len(removed)} 個死亡 key')
print(f'剩餘: {len(surviving)} 個有效 key')
print()
print('移除清單:', removed)
