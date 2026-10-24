import json,urllib.request,time,re,os
cfg=json.load(open('/etc/strata/davidau-iq3s-256k.json')); K=cfg['api_key']; LOG=cfg['log']
U='http://127.0.0.1:8080/v1/chat/completions'
sysmsg="You are a Proxmox and Linux infrastructure assistant. "+" ".join(f"Rule {i}: always explain commands, prefer read-only checks first, never assume storage pools, and cite the relevant config file paths." for i in range(1,120))
def ask(q):
    pos=os.path.getsize(LOG); t=time.time()
    b={"model":"x","messages":[{"role":"system","content":sysmsg},{"role":"user","content":q}],"reasoning_effort":"low","max_tokens":120}
    d=json.load(urllib.request.urlopen(urllib.request.Request(U,json.dumps(b).encode(),{"Authorization":"Bearer "+K,"Content-Type":"application/json"}),timeout=600))
    time.sleep(0.5); new=open(LOG,'rb').read()[pos:].decode('utf-8','replace')
    m=re.findall(r'prompt (\d+) tokens = (\d+) reused \+ (\d+) read in (\d+) ms',new)
    print(f"{q[:40]!r}: wall {time.time()-t:.1f}s usage.cached={d['usage'].get('prompt_tokens_details',{}).get('cached_tokens')} engine={m[-1] if m else None}")
ask("How do I list LXC containers?"); ask("How do I check storage pool usage?"); ask("How do I see a CT's config?")
