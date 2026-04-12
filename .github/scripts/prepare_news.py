import json, re, sys
from datetime import date, timedelta

file_path = sys.argv[1]


def repair_json(text):
    """Attempt to fix common JSON issues: unescaped double quotes inside string values."""
    # Strategy: parse character by character, track string context and escape unescaped quotes
    result = []
    in_string = False
    escaped = False
    for i, ch in enumerate(text):
        if escaped:
            result.append(ch)
            escaped = False
            continue
        if ch == '\\':
            escaped = True
            result.append(ch)
            continue
        if ch == '"':
            if not in_string:
                in_string = True
                result.append(ch)
            else:
                # Peek ahead: if next non-whitespace is , ] } : then this closes the string
                rest = text[i+1:].lstrip()
                if rest and rest[0] in ',]}:':
                    in_string = False
                    result.append(ch)
                else:
                    # Likely an unescaped quote inside string — escape it
                    result.append('\\"')
        else:
            result.append(ch)
    return ''.join(result)


with open(file_path) as f:
    raw = f.read()

try:
    data = json.loads(raw)
except json.JSONDecodeError as e:
    print(f"WARNING: Invalid JSON detected - {e}")
    print("Attempting automatic repair...")
    repaired = repair_json(raw)
    try:
        data = json.loads(repaired)
        print("Repair succeeded. Writing fixed JSON back to file.")
        with open(file_path, 'w') as f:
            f.write(repaired)
    except json.JSONDecodeError as e2:
        print(f"ERROR: Could not repair JSON - {e2}")
        print("Check for unescaped quotes in title/summary fields.")
        sys.exit(1)

file_date = date.fromisoformat(data['date'])
cutoff = file_date - timedelta(days=2)


def get_item_date(item, file_year, file_month, fallback):
    if 'date' in item:
        return date.fromisoformat(item['date'])
    m = re.search(r'/(\d{4})/(\d{2})/(\d{2})/', item.get('url', ''))
    if m:
        return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    m = re.search(r'(\d{1,2})月(\d{1,2})日', item.get('summary', ''))
    if m:
        month, day = int(m.group(1)), int(m.group(2))
        year = file_year if month <= file_month else file_year - 1
        return date(year, month, day)
    return fallback


kept = [
    item for item in data['news']
    if get_item_date(item, file_date.year, file_date.month, file_date) >= cutoff
]

stale = len(data['news']) - len(kept)
if stale:
    print(f"Filtered {stale} stale news item(s) (cutoff: {cutoff})")

data['news'] = kept
with open(file_path, 'w') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
print(f"Ready: {len(kept)} news items for {file_date}")
