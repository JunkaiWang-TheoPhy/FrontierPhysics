---
name: spectrum-analyzer-parsing
description: Parse a spectrum-analyzer trace export and convert logarithmic power readings to rms voltage for a stated input load.
---

# Spectrum-analyzer trace parsing

Use this when a trace export stores frequency and power in dBm. Read
`references/anritsu-format.md` when the supplied file uses that layout, then
write a small parser that preserves the trace order and frequency units.

## Workflow

1. Locate the actual trace data block and ignore metadata, markers, and blank
   rows. Confirm which field is frequency and which is dBm from the export
   format or headers.
2. For load `R_load`, convert each point with

       Vrms = sqrt(10**((dBm - 30)/10) * R_load)

3. Preserve all trace points required by the task and emit the requested
   frequency and voltage columns. Check that the conversion uses power in watts
   and RMS voltage, not peak voltage.
