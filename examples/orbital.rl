@ANCHOR
[A gravitationally bound two-body system. The derivations below are independent
of the bodies' composition. Content is neutral and used to illustrate form.]

@FORMAL [kepler_third]
T² = (4π² / GM) · a³

@FORMAL [newton_gravitation]
F = G · m₁ · m₂ / r²

@LOGIC [energy] basis: AXIOM
∀S: closed(S) → d/dt E(S) = 0

@SCOPE [two_body]
in_scope: point masses, Newtonian regime, negligible external perturbation
excluded: relativistic corrections, n-body effects
enforcement: out-of-scope claims are marked OUT_OF_SCOPE, not wrong

@DERIVE [circular_velocity]
(1) For a circular orbit, gravity supplies the centripetal force
(2) From @FORMAL[newton_gravitation]: G·M·m / r² = m·v² / r
(3) From (2): v² = G·M / r
→→ v = sqrt(G·M / r)

@TAXONOMY [orbit_properties]
bound_orbit: confirmed
orbital_period_known: confirmed
exact_eccentricity: open
parabolic_escape: denied

@VERIFY [§circular_velocity]
(1): holds
(2): holds
(3): holds
→→: holds

@PROVENANCE [chain]
  hop_1: model_A → model_B | loaded+full_verify

@OUTPUT
mode: report
include: [@STATE, @VERIFY[§circular_velocity]]
