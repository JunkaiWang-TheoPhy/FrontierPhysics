# Boundary-element pseudopotential method

For a unit-potential RF-electrode solve, FastLap returns
\(\mathbf{E}_1(\mathbf{r})\). At RF amplitude \(V_{\rm RF}\), the field
amplitude is

\[
\mathbf{E}(\mathbf{r}) = V_{\rm RF}\mathbf{E}_1(\mathbf{r}).
\]

For an ion of charge \(Q\), mass \(m\), and RF angular frequency
\(\Omega = 2\pi f_{\rm RF}\), the ponderomotive pseudopotential energy is

\[
U_{\rm ps}(\mathbf{r}) =
\frac{Q^2|\mathbf{E}(\mathbf{r})|^2}{4m\Omega^2}.
\]

Near the RF null, fit

\[
U_{\rm ps}(x,y) =
c+a_x x^2+a_y y^2+a_{xy}xy+b_xx+b_yy.
\]

The Hessian is

\[
H =
\begin{pmatrix}
2a_x & a_{xy}\\
a_{xy} & 2a_y
\end{pmatrix}.
\]

Coordinate secular frequencies are

\[
\omega_x=\sqrt{H_{xx}/m},\qquad
\omega_y=\sqrt{H_{yy}/m}.
\]

Diagonalizing \(H\) gives principal-axis frequencies. For a surface trap whose
rails run along the axial direction, the requested in-plane radial direction
is normally the coordinate perpendicular to the rails, not the surface-normal
coordinate.

## Geometry selection

Colored CAD exports often contain both conductor faces and a watertight
mechanical body. For a surface-electrode boundary solve:

- keep the coplanar top faces associated with electrode color attributes;
- assign the RF color to 1 V and all other electrode colors to 0 V;
- exclude the generic body/substrate color, sidewalls, recessed gap floors, and
  back surface unless the physical model explicitly declares them conductive.

Including the mechanical shell as a grounded conductor changes the boundary
condition and can shift the secular frequency by several percent.

The supplied STL coordinates use millimeters. Preserve that scale through
remeshing: a solver operating in those coordinates returns field in V/mm for a
1 V electrode solve. Multiply by \(10^3\) to obtain V/m, then multiply by the RF
amplitude.

Useful diagnostics:

- fitted RF-null coordinates;
- coordinate and principal frequencies;
- FastLap iteration count and achieved residual tolerance;
- positive Hessian eigenvalues.
