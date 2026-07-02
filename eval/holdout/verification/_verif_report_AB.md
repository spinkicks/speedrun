# Independent Verification Report — goldset_A.jsonl + goldset_B.jsonl

**Verifier:** independent re-solve with SymPy 1.14.0 (Python). Every problem was re-solved
from the `question` text without reading the file's `verification` field first, then the
computed answer was matched against the 5 `choices` and compared to `correct_answer`.

**Result: 25 / 25 PASS. No flags.**

## Summary table

| id | my computed answer | their correct_answer | verdict |
|---|---|---|---|
| gold_calc_limits_01 | 6/5 | 6/5 | PASS |
| gold_calc_limits_02 | 5/3 | 5/3 | PASS |
| gold_calc_limits_03 | 1 | 1 | PASS |
| gold_calc_limits_04 | a = 6 | 6 | PASS |
| gold_calc_limits_05 | 1/3 | 1/3 | PASS |
| gold_calc_diff_01 | (3x²+2x)eˣ³ = (3x²+2x)e^{3x} | (3x²+2x)e^{3x} | PASS |
| gold_calc_diff_02 | (1−x²)/(x²+1)² | (1−x²)/(x²+1)² | PASS |
| gold_calc_diff_03 | 24x(3x²+1)³ | 24x(3x²+1)³ | PASS |
| gold_calc_diff_04 | −3/4 | −3/4 | PASS |
| gold_calc_diff_05 | x/(x²+1) | x/(x²+1) | PASS |
| gold_calc_diff_06 | 2 | 2 | PASS |
| gold_calc_diff_07 | 1 | 1 | PASS |
| gold_calc_int_01 | (e−1)/2 ≈ 0.85914 | (e−1)/2 | PASS |
| gold_calc_int_02 | (e²+1)/4 ≈ 2.09726 | (e²+1)/4 | PASS |
| gold_calc_int_03 | 2 | 2 | PASS |
| gold_calc_int_04 | 2/3 | 2/3 | PASS |
| gold_calc_int_05 | x·sin x + cos x (+C) | x sin x + cos x + C | PASS |
| gold_calc_int_06 | π/2 | π/2 | PASS |
| gold_calc_int_07 | 1 | 1 | PASS |
| gold_calc_int_08 | ln 2 ≈ 0.693147 | ln 2 | PASS |
| gold_calc_series_01 | 1 | 1 | PASS |
| gold_calc_series_02 | 3/4 | 3/4 | PASS |
| gold_calc_series_03 | 2 | 2 | PASS |
| gold_calc_series_04 | π/4 ≈ 0.785398 | π/4 | PASS |
| gold_calc_series_05 | R = 3 | 3 | PASS |

## Checks performed for the "≥2 correct / not-in-choices" flags
For every item the unique computed value appears exactly once among the 5 choices, and no
distractor equals the true value:
- Rational/closed-form answers were compared symbolically (`sp.simplify`, `Eq`), not by string.
- `limits_04` was solved as an equation for `a` (single root a=6, and choice "no such value" is false).
- `diff_06` used the second-derivative test to select the genuine local **max** (x=−1 → 2),
  distinguishing it from the local min value −2 (a listed distractor, correctly *not* the answer).
- `int_07` is an improper integral that converges (=1), so the "diverges" distractor is correctly wrong.
- `series_03` converges (=2), so the "diverges" distractor is correctly wrong.
- `series_05` radius of convergence computed as 1/lim|a_{n+1}/a_n| = 3.

## SymPy snippets
No item was flagged, so no per-item correction snippet is required. The full driver used is
`_verif.py` in this folder. Key calls:

```python
import sympy as sp
x, a, n = sp.symbols('x a n')
sp.limit((x**2-9)/(x**2-x-6), x, 3)                 # 6/5
sp.limit(sp.sin(5*x)/sp.sin(3*x), x, 0)             # 5/3
sp.limit(sp.sqrt(4*x**2+3*x)/(2*x+1), x, sp.oo)     # 1
sp.solve(sp.Eq(sp.limit(sp.sin(a*x)/x, x, 0), 6), a)# [6]
sp.limit((sp.tan(x)-x)/x**3, x, 0)                  # 1/3
sp.diff(x**2*sp.exp(3*x), x)                         # (3x^2+2x)e^{3x}
sp.diff(x/(x**2+1), x)                               # (1-x^2)/(x^2+1)^2
sp.diff((3*x**2+1)**4, x)                            # 24x(3x^2+1)^3
# implicit: y'=-x/y at (3,4) -> -3/4
sp.diff(sp.ln(sp.sqrt(x**2+1)), x)                   # x/(x^2+1)
# x^3-3x local max -> f(-1)=2
sp.diff(x**x, x).subs(x,1)                           # 1
sp.integrate(x*sp.exp(x**2),(x,0,1))                 # (e-1)/2
sp.integrate(x*sp.log(x),(x,1,sp.E))                 # (e^2+1)/4
sp.integrate(x**2*sp.exp(-x),(x,0,sp.oo))            # 2
sp.integrate(sp.sin(x)**3,(x,0,sp.pi/2))            # 2/3
sp.integrate(x*sp.cos(x),x)                          # x sin x + cos x
sp.integrate(1/(1+x**2),(x,0,sp.oo))                # pi/2
sp.integrate(x/sp.sqrt(1-x**2),(x,0,1))            # 1
sp.integrate(1/(x*sp.log(x)),(x,sp.E,sp.E**2))     # log(2)
sp.summation(3/sp.Integer(4)**n,(n,1,sp.oo))        # 1
sp.summation(1/(n*(n+2)),(n,1,sp.oo))               # 3/4
sp.summation(n/sp.Integer(2)**n,(n,1,sp.oo))        # 2
sp.summation((-1)**n/(2*n+1),(n,0,sp.oo))           # pi/4
an=1/(n*3**n); 1/sp.limit(sp.Abs(an.subs(n,n+1)/an), n, sp.oo)  # 3
```
