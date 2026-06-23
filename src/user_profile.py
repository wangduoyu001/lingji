# User Capability Profile
PROFILE_PATH = None  # will be loaded from vault on startup

def load_profile(vault_path):
    import os, re
    pf = os.path.join(str(vault_path), 'PEMIS', 'dashboard', '\u6211\u7684\u80fd\u529b.md')  
    if not os.path.exists(pf):
        return None
    with open(pf, 'r', encoding='utf-8') as f:
        text = f.read()
    profile = {}
    for line in text.splitlines():
        m = re.match(r'^- \*\*(.+?)\*\*:\s*(.+)$', line)
        if m:
            profile[m.group(1).strip()] = m.group(2).strip()
    return profile

def calc_capability_match(profile, opportunity):
    if not profile:
        return 0.5  # neutral if no profile
    match = 0.5
    diff = opportunity.get('difficulty', 3)
    exec_ability = {'1': 0.9, '2': 0.8, '3': 0.6, '4': 0.4, '5': 0.2}
    return max(0.1, min(1.0, match))