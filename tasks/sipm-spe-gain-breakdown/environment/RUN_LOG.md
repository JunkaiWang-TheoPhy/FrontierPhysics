# SiPM cold-test run log

Cryostat runs, 2023-07-14. Three SiPMs read out simultaneously in a
common-trigger configuration. The cryostat was taken to several setpoints over
the day; at each one the bias voltage and the acquisition threshold were
stepped. The cooldowns were not all carried through to the same extent -- some
were cut short when the schedule slipped.

## Readout chain

| Item | Value |
|---|---|
| Digitizer | CAEN DT5720 (desktop, 4 channel) |
| Sampling rate | 250 MS/s (4 ns per sample) |
| ADC resolution | 12 bit |
| Input range | 2 Vpp |
| Record length | 1024 samples per channel per event |
| Channels acquired | 1, 2, 3 (one SiPM each) |
| Trigger | common trigger across the acquired channels |
| Firmware output | standard DT5720 binary event stream, one file per acquisition segment |

**Device under test for this analysis: channel 3.**

Channels 1 and 2 carry two other SiPMs from the same batch.

## Analog chain

The SiPM signals pass through a cold preamplifier and a warm second-stage
amplifier before the digitizer. **The end-to-end voltage gain of that chain was
not calibrated during this run.** Do not assume any particular ADC-count to volt
conversion, and do not convert the measured single-photoelectron response into
an intrinsic charge or electron gain — the numbers required for that conversion
were not measured here.

Report the single-photoelectron gain as an integrated pulse area in
**ADC counts x ns**, using the digitizer sampling period above.

## Acquisition matrix

The nominal cryostat setpoint of each cooldown appears in the file names, as do
the bias voltage, the threshold setting and the segment index. The bias ladder
was chosen fresh at each setpoint to keep the devices in a sensible operating
range, so it is not the same list of voltages every time.

Each segment is a separate acquisition of the same configuration; segments of a
given (setpoint, bias, threshold) setting are meant to be merged before
analysis. The acquisition threshold was stepped deliberately, though not every
threshold was carried across every bias point in every cooldown.

File names encode the configuration:

```
sipm_group<G>_threshold<THR>_<TEMP>C_<BIAS>V_<NEVT>_<CHANNELS>_raw_b0_seg<S>_<YYYYMMDDThhmmss>.bin
```

`<NEVT>` is the **requested** event count that was programmed into the
acquisition, not the number of events actually written. Runs were stopped by
hand and the files were later truncated to a common length for archiving, so the
true event count must be taken from the files themselves.

`<YYYYMMDDThhmmss>` is the start time of the segment.

## Temperature

The `temp_record_test2_*.csv` files are the raw cryostat logs, with columns
`timestamp, reading_index, temperature_C`. Between them they cover the day's
cooldowns; match them to the acquisitions by time. The setpoint in the file
names is nominal only -- it is what the controller was asked for, not what the
sensor read -- and the sensor drifted during each acquisition, so the
temperature to quote with a calibration is the one actually measured over that
cooldown's acquisition window.
