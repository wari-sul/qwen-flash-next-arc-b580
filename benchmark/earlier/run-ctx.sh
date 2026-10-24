#!/bin/bash
# usage: run-ctx.sh <ctx> <label> [yarn_factor]
set -u
C=$1; L=$2; Y=${3:-}
B=/etc/strata/davidau-iq3s-32k.json.base; CF=/etc/strata/davidau-iq3s-32k.json
[ -f $B ] || cp $CF $B
python3 - "$C" "$Y" <<'PY'
import json,sys
C,Y=sys.argv[1],sys.argv[2]
d=json.load(open('/etc/strata/davidau-iq3s-32k.json.base')); a=d['args']
def setf(k,v):
    if k in a: a[a.index(k)+1]=v
    else: a.extend([k,v])
setf('--max-context',C); setf('--kv-resident','32768'); setf('--vram-reserve-mib','2048'); setf('--prefill','4096')
if Y: setf('--rope-scaling','yarn'); setf('--rope-scale',Y)
d['idle_unload_s']=7200
json.dump(d,open('/etc/strata/davidau-iq3s-32k.json','w'),indent=2); print('ARGS',' '.join(a[a.index('--max-context'):]))
PY
KEY=$(python3 -c "import json;print(json.load(open('$CF'))['api_key'])")
systemctl restart strata; sleep 3; P=$(stat -c %s /var/log/strata-engine.log)
curl -s -m 900 -X POST -H "Authorization: Bearer $KEY" -H 'Content-Type: application/json' localhost:8080/load; echo
tail -c +$((P+1)) /var/log/strata-engine.log | grep -aE "expert cache [0-9]+ slots|mirrored in pinned|VRAM free with|KV|kv|rope|yarn|error|ERROR|refus" | cut -c1-220
echo "MEM $(free -m | awk '/Mem/{print "ct_used="$3"M"}')"
python3 /root/bench/ctxtest.py $C $L
python3 /root/bench/qbench.py ctx-$L 2 | tail -1
echo "DONE $L"
