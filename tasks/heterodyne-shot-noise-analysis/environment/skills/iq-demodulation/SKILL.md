---
name: iq-demodulation
description: Demodulate a sampled periodic beat-note trace into an I/Q cloud, estimate its noise variance, and infer the operating point from monitor or calibration channels.
---

# IQ demodulation

Use this when a real-valued sampled trace contains a periodic carrier or beat
note and the requested result is a demodulated noise statistic. Read
`references/iq-demodulation.md` for the conventions, then implement the
calculation for the supplied sampling rate and reference frequency.

## Method

1. Choose a window containing an integer number of carrier periods. Partition
   the trace into consecutive complete windows and drop any partial remainder.
   Reset time at the start of each window.
2. Integrate the samples against sine and cosine at the reference frequency.
   Preserve the requested normalization and units; an un-normalized integral
   includes the sample interval.
3. Treat the resulting `(I, Q)` pairs as a cloud. Form its covariance matrix,
   inspect the principal-axis variances, and use the statistic requested by the
   task. Check that the estimate is stable to reasonable window choices.
4. If an operating point must be recovered from monitor channels, use the
   instrument calibration in the supplied documentation. State the calibration
   and units in any durable analysis code or notes; do not infer it from expected
   output values.

Use a phase convention consistently across records. For isotropic noise, the
principal standard deviations should be similar; a large mismatch is a useful
diagnostic for leakage, drift, or an incorrect reference frequency.
