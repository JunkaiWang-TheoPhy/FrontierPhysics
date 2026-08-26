# Output schema

Exact formats for the files requested in the task. Headers as written, one row
per entity, full precision in the machine-readable files.

## `result.md`

Key-value lines. The coefficient is the slope of breakdown voltage against
measured temperature, in mV per kelvin.

```md
breakdown_voltage_temperature_coefficient_mv_per_k: <number>
breakdown_voltage_temperature_coefficient_err_mv_per_k: <number>
n_campaigns_calibrated: <integer>
```

## `campaigns.csv`

One row per cooldown you were able to calibrate, and none for any you were not.

```csv
campaign_setpoint_c,measured_temperature_mean_c,measured_temperature_std_c,breakdown_voltage_v,breakdown_voltage_err_v,spacing_slope_adcns_per_v,spacing_fit_chi2_per_dof
```

- `campaign_setpoint_c` — the nominal temperature as it appears in the file names.
- `breakdown_voltage_err_v` — your real measurement uncertainty on the
  breakdown voltage, statistical and systematic combined, derived from your
  own analysis. Quote what your error budget supports — neither a bare fit
  covariance if you know of systematics it omits, nor a blanket safety
  factor: a value above 0.25 V no longer describes a measurement of this
  extrapolation and will be rejected as non-credible.
- `spacing_slope_adcns_per_v` — slope of the charge separation against bias.
- The two measured-temperature columns are **defined for you**, so they mean the
  same thing next time we cool down rather than depending on the analysis: take
  every cryostat-log reading whose timestamp lies between the earliest and the
  latest acquisition timestamp among **all** delivered files of that cooldown,
  inclusive, and report the arithmetic mean and standard deviation of those
  readings. That window is fixed by the delivered files, not by whichever subset
  you end up analysing.

## `gain_vs_voltage.csv`

One row per bias point per calibrated cooldown.

```csv
campaign_setpoint_c,voltage_v,spe_charge_spacing_adcns,spe_charge_spacing_err_adcns
```

## `spe_fits.csv`

The per-setting numbers behind the table above.

```csv
campaign_setpoint_c,voltage_v,threshold,n_events,baseline_adc,spe_charge_spacing_adcns,spe_peak_sigma_adcns
```

- `n_events` — the number of recorded events that survive your data-quality
  selection for that setting (out of those delivered in its files). Count
  events you kept, not just the ones inside a fit window — a spectrum fit only
  ever uses part of the charge range, and that is not a discard.
- `spe_peak_sigma_adcns` — width of the first-photoelectron population on your own fit.
- `baseline_adc` — mean raw DC level of the channel you analysed for that
  setting, in ADC counts, before any baseline subtraction. The usual noise
  column, so I can see at a glance which channel a row came from.

## `decode_check.csv`

So I can check your reader against mine before trusting anything downstream.
For the **first 200 events** of

```
sipm_group1_threshold30_-58.0C_53.0V_2000_123_raw_b0_seg0_20230714T190127.bin
```

```csv
event_index,event_counter,trigger_time_tag,ch1_raw_min,ch1_raw_max,ch2_raw_min,ch2_raw_max,ch3_raw_min,ch3_raw_max,ch3_raw_sum,ch3_raw_first,ch3_raw_last
```

`event_index` counts from 0 in file order. `event_counter` and
`trigger_time_tag` are the values carried in the event itself, as stored, with
no rollover correction. The `*_raw_*` columns are over the raw, unmodified
samples of that event — minimum, maximum, and for channel 3 also the sum of all
its samples and its first and last sample, in acquisition order.

## `average_waveform.csv`

The event-averaged, baseline-subtracted channel-3 waveform for the −58.0 C
cooldown at 53 V, threshold 30, merging that setting's segments, in ADC counts.

```csv
sample_index,amplitude_adc
```

## `paper.pdf`

The write-up, as a PDF. This is the deliverable a colleague would read: it
should state what was measured and on what data, how the charge observable was
built and why, which cooldowns were calibrated and on what grounds, how the
breakdown voltage was extrapolated and what was assumed about the shape of that
fit, where the temperatures came from, and where the quoted uncertainties come
from. Figures carry as much of that as text does — the tables above hold
everything needed to plot the pulse, the separation against bias with its
extrapolation, and the breakdown voltage against temperature.

There is no page count, no template and no required section list. `matplotlib`
is available in the environment and can write a multi-page PDF directly; any
other route that produces a real PDF is fine. The deterministic checks only
confirm that the file exists and is a PDF — everything about its content is
judged by a reviewer.
