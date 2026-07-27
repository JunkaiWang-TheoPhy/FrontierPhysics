# Anritsu spectrum-analyzer CSV layout

Some Anritsu CSV exports contain a metadata header followed by a trace block
bounded by markers such as:

    # Begin TRACE A Data
    P_0, -52.808000 , 0.000001 , MHz
    # Data Done

For this layout, data starts after the start marker and ends before the end
marker. Skip blank or nonnumeric rows. In the common four-field form, field
index 1 is the amplitude in dBm and field index 2 is the frequency in MHz;
confirm this against the supplied export before relying on it.

## dBm to Vrms

For a load `R_load`:

    P_watt = 10**((dBm - 30)/10)
    Vrms   = sqrt(P_watt * R_load)

This is the per-bin rms voltage; it is not divided by the resolution bandwidth.
