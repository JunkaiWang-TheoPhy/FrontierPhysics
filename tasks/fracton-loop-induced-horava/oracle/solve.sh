#!/usr/bin/env bash
set -euo pipefail
mkdir -p /root/figures
cat > /root/result.json <<'JSON'
{"branch":"quadrupole-z3-weak-ADM","assumptions":["Euclidean one-loop expansion around flat ADM background","hard momentum cutoff","local mode count excludes global and boundary sectors"],"ward_tests":{"lapse_response":"undetermined","spatial_response":"undetermined"},"constraint_class":"undetermined","local_mode_count":null,"stability":"undetermined","poles":"undetermined","first_failed_gate":"undetermined","evidence":["Oracle supplies only the frozen model specification; the evaluated agent must perform the research calculation."]}
JSON
python - <<'PY'
import matplotlib.pyplot as plt
import numpy as np
k=np.linspace(0,5,200)
plt.plot(k,k**6+0.1*k**2)
plt.xlabel('momentum k'); plt.ylabel('reference dispersion scale'); plt.tight_layout()
plt.savefig('/root/figures/reference-dispersion.png',dpi=160)
PY
if [ -f /root/paper.pdf ]; then exit 0; fi
python - <<'PY'
from matplotlib.backends.backend_pdf import PdfPages
import matplotlib.pyplot as plt
with PdfPages('/root/paper.pdf') as pdf:
 fig=plt.figure(); fig.text(.1,.8,'Reference placeholder: evaluated agent must provide paper.pdf'); pdf.savefig(fig); plt.close(fig)
PY
