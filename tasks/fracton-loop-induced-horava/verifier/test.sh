#!/usr/bin/env bash
set -u
mkdir -p /logs/verifier
for f in paper.pdf result.json; do [ -f "/root/$f" ] && cp "/root/$f" "/logs/verifier/$f" || exit 1; done
[ -d /root/figures ] && find /root/figures -type f -maxdepth 1 -exec cp {} /logs/verifier/ \; || exit 1
python - <<'PY'
import json
d=json.load(open('/root/result.json'))
required=['branch','assumptions','ward_tests','constraint_class','local_mode_count','stability','poles','first_failed_gate','evidence']
assert all(k in d for k in required)
assert isinstance(d['evidence'],list) and d['evidence']
PY
echo 1 > /logs/verifier/reward.txt
exit 0
