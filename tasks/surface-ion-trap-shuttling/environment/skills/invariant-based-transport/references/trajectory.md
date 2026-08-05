# Invariant-based transport trajectory

For a harmonic trap with fixed angular frequency \(\omega_0\), the classical
trajectory obeys

\[
\ddot q_c+\omega_0^2(q_c-q_0)=0.
\]

Impose rest-to-rest boundary conditions on position, velocity, and acceleration
at \(t=0\) and \(t=T\). With \(s=t/T\), a quintic interpolation is

\[
\frac{q_c(t)}{d}=10s^3-15s^4+6s^5.
\]

The physical trap-center trajectory follows from the equation of motion:

\[
q_0(t)=q_c(t)+\frac{\ddot q_c(t)}{\omega_0^2}.
\]

Therefore,

\[
q_0(t)=d\left[
10s^3-15s^4+6s^5+
\frac{60}{\omega_0^2T^2}(s-3s^2+2s^3)
\right].
\]

This is the harmonic-transport inverse-engineering result in E. Torrontegui
et al., "Fast atomic transport without vibrational heating,"
Phys. Rev. A 83, 013415 (2011).

For stage \(i\), with distance \(d_i\), move duration \(T\), dwell duration
\(\tau\), and cumulative prior offset \(D_i=\sum_{j<i}d_j\):

\[
q(t)=D_i+q_{0,i}(t-i(T+\tau))
\]

during the move, and \(q(t)=D_i+d_i\) during the dwell. Use one global uniform
time grid for the final CSV and evaluate the correct piece at every sample.
