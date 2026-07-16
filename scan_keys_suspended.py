import yaml, json, urllib.request, urllib.error, time, sys

data = yaml.safe_load(open('config/keys.yaml', encoding='utf-8'))
keys = data.get('keys', [])
print('Total keys:', len(keys))

suspended_keys = []
other_bad = []
for k in keys:
    name = k['name']
    val = k['value']
    url = 'https://generativelanguage.googleapis.com/v1beta/models?key=' + val
    try:
        req = urllib.request.Request(url)
        resp = urllib.request.urlopen(req, timeout=10)
        # 200 OK - skip
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8', errors='replace')
        status = e.code
        if status in (403, 401):
            if 'suspended' in body.lower() or '0536090658' in body or 'PROJECT_DELETED' in body or 'ACCOUNT_DELETED' in body:
                print('SUSPENDED:', name, '->', body[:200])
                suspended_keys.append(name)
            else:
                print(str(status) + ': ' + name + ' -> ' + body[:100])
                other_bad.append(name)
        else:
            print(str(status) + ': ' + name)
    except Exception as ex:
        print('ERR: ' + name + ' -> ' + str(ex))
    time.sleep(0.3)

print()
print('Suspended:', suspended_keys)
print('Other bad:', other_bad)
