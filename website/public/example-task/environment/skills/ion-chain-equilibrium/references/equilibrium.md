# Harmonic ion-chain equilibrium

For identical singly charged ions in a one-dimensional harmonic trap,

\[
V=\sum_i \frac12m\omega_z^2x_i^2
+\sum_{i<j}\frac{e^2}{4\pi\epsilon_0|x_i-x_j|}.
\]

Define

\[
\ell =
\left(
\frac{e^2}{4\pi\epsilon_0m\omega_z^2}
\right)^{1/3},
\qquad x_i=\ell u_i.
\]

Ordered dimensionless positions satisfy

\[
u_i
-\sum_{j<i}\frac{1}{(u_i-u_j)^2}
+\sum_{j>i}\frac{1}{(u_i-u_j)^2}
=0.
\]

Use a nonlinear root solver with an ordered, symmetric initial guess. Sort the
solution before taking differences, because a root solver does not guarantee
ordering. Report adjacent distances

\[
d_i=x_{i+1}-x_i
\]

in the requested unit.

Do not round dimensionless positions before scaling; round only the final
reported distances.
