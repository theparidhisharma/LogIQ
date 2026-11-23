import re, hashlib

def parse_line(line: str):
    m = re.match(r'^\s*(\d{4}-\d\d-\d\d[T ][^ ]+)\s+(TRACE|DEBUG|INFO|WARN|WARNING|ERROR|FATAL)\s+(.*)$', line, re.I)
    if m:
        return m.group(1), m.group(2).upper().replace('WARNING', 'WARN'), m.group(3)
    m = re.match(r'^\s*(TRACE|DEBUG|INFO|WARN|WARNING|ERROR|FATAL)\s+(.*)$', line, re.I)
    if m:
        return None, m.group(1).upper().replace('WARNING', 'WARN'), m.group(2)
    return None, 'INFO', line.strip()

def template_for(message: str):
    tokens = message.split(); params = {}; out = []
    for token in tokens:
        if re.fullmatch(r'\d+(?:\.\d+)?', token) or re.fullmatch(r'[0-9a-fA-F]{8,}', token) or re.fullmatch(r'\d{1,3}(?:\.\d{1,3}){3}', token):
            params[str(len(params))] = token; out.append('<*>')
        else:
            out.append(token)
    template = ' '.join(out)
    return hashlib.sha1(template.encode()).hexdigest()[:12], template, params
