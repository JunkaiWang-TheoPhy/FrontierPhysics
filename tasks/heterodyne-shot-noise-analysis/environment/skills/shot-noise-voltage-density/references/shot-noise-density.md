# Shot-noise voltage spectral density

A photocurrent `I_ph = R*P` carries shot noise with a single-sided current
power spectral density

    S_I = 2*e*I_ph = 2*e*R*P   [A**2/Hz].

A transimpedance gain `Z` (V/A) gives

    S_V = Z**2 * S_I = 2*e*Z**2*R*P   [V**2/Hz].

The amplitude density is

    sqrt(S_V)  [V/sqrt(Hz)].

## Density versus bandwidth-integrated rms

A spectrum analyzer reports an rms voltage integrated over its resolution
bandwidth `RBW`:

    Vrms_bin = sqrt(S_V) * sqrt(RBW).

Therefore compare a density with `Vrms_bin / sqrt(RBW)`, and do not fold `RBW`
into a quantity explicitly requested as a density. Use the responsivity and
transimpedance appropriate to the detector operating point and wavelength.
