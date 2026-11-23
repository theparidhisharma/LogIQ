from shared.parsing import parse_line, template_for

def test_parse_severity():
    ts, sev, msg = parse_line('ERROR database connection failed')
    assert sev == 'ERROR' and msg == 'database connection failed'

def test_template_masks_numbers():
    tid, tpl, params = template_for('request 123 completed in 42')
    assert tpl == 'request <*> completed in <*>' and len(params) == 2 and len(tid) == 12
