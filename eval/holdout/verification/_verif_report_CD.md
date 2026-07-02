# Independent Verification Report — goldset_C & goldset_D

Verifier method: every problem re-solved from scratch with SymPy 1.14.0 (Python), without reading the file's `verification` field before forming an independent answer. Choices then matched against the computed truth and compared to the file's `correct_answer`.

**Result: 25 / 25 PASS. 0 FLAGGED.**

## Summary table

| id | my computed answer | their correct_answer | verdict | reason |
|---|---|---|---|---|
| gold_calc_multivar_01 | 16 | 16 | PASS | ∂f/∂x = 2xy+3y² at (1,2) = 4+12 = 16 |
| gold_calc_multivar_02 | 1 | 1 | PASS | f_xy = 6x²y+cos y at (1,0) = 0+1 = 1 |
| gold_calc_multivar_03 | 16/5 | 16/5 | PASS | ⟨4,1⟩·⟨3/5,4/5⟩ = 12/5+4/5 = 16/5 |
| gold_calc_multivar_04 | 3 | 3 | PASS | ∫₀¹∫₀²(x+y)dy dx = 3 |
| gold_calc_multivar_05 | (e−1)/2 | (e−1)/2 | PASS | reversed order → ∫₀¹ y e^{y²}dy = (e−1)/2 |
| gold_calc_multivar_06 | 0 | 0 | PASS | dz/dt = cos 2t; at π/4 = cos(π/2) = 0 |
| gold_calc_multivar_07 | 1 minimum | 1 | PASS | (1,0): D=12>0,f_xx>0 min; (−1,0): D=−12 saddle |
| gold_calc_multivar_08 | 2 | 2 | PASS | conservative, φ=x²y; φ(1,2)−φ(0,0)=2 |
| gold_la_vspaces_01 | {x+y+z=0} | {x+y+z=0} | PASS | only kernel-of-linear-map set; others fail 0/closure |
| gold_la_vspaces_02 | 2 | 2 | PASS | rank([[1,2,3],[2,4,6],[1,0,0]]) = 2 |
| gold_la_vspaces_03 | independent, basis | independent, basis | PASS | det = 2 ≠ 0, rank 3 |
| gold_la_vspaces_04 | 6 | 6 | PASS | n(n+1)/2 = 6 for n=3 |
| gold_la_matrices_01 | −1 | −1 | PASS | det = −1 |
| gold_la_matrices_02 | (1,2,3) | (1,2,3) | PASS | unique solve → {x:1,y:2,z:3} |
| gold_la_matrices_03 | −7/10 | −7/10 | PASS | A⁻¹[0,1] = −7/10 (det=10) |
| gold_la_matrices_04 | 7 | 7 | PASS | det = k−7; singular ⇔ k=7 |
| gold_la_eigen_01 | 1 and 3 | 1 and 3 | PASS | eigenvals {1,3} |
| gold_la_eigen_02 | λ²−3λ−4 | λ²−3λ−4 | PASS | charpoly = λ²−3λ−4 |
| gold_la_eigen_03 | (1,1) | (1,1) | PASS | eigvect for λ=5 is (1,1) |
| gold_la_eigen_04 | single λ=5, geom mult 1, not diagonalizable | same | PASS | eigenvects → (5, alg 2, one vector) |
| gold_la_eigen_05 | 4 and 9 | 4 and 9 | PASS | (A²) eigenvals {4,9} |
| gold_la_maps_01 | 2 | 2 | PASS | rank-nullity: 5−3 = 2 |
| gold_la_maps_02 | 2 | 2 | PASS | rank 2 → nullity 4−2 = 2 (nullspace len 2) |
| gold_la_maps_03 | "injective but not surjective" | same | PASS | rank ≤ 2 < 3 so never surjective; rank-2 map injective |
| gold_la_maps_04 | 2 | 2 | PASS | det = 0, rank = 2 |

## Notes on conceptual (non-numeric) items — checked for MULTIPLE-CORRECT / BAD-DISTRACTOR

- **gold_la_vspaces_01**: Only `{x+y+z=0}` is a subspace. `{x+y+z=1}` excludes 0; `{x²+y²=z}` nonlinear (e.g. 2·(1,0,1)=(2,0,2) not in set); `{x≥0}` not closed under −1 scaling; `{xyz=0}` not closed under addition ((1,0,0)+(0,1,1)=(1,1,1)). Exactly one correct. ✓
- **gold_la_eigen_04**: A=[[5,1],[0,5]] gives eigenvects [(5, 2, [(1,0)ᵀ])] → alg mult 2, geom mult 1 → defective/not diagonalizable. Distractors all false (det=25≠0, no second eigenvalue, no 2nd independent eigenvector). ✓
- **gold_la_maps_03**: For T:ℝ²→ℝ³, image dim ≤ 2 < 3 ⇒ never surjective; a rank-2 map has trivial kernel ⇒ can be injective. All other options false. Exactly one correct. ✓

## SymPy snippets
No FLAGGED items, so no per-item snippets are required. The full driver used for all 25 checks is `scratch/goldset/_verify_cd.py`; representative core:

```python
import sympy as sp
x,y,z,t,k,lam = sp.symbols('x y z t k lambda')
sp.diff(x**2*y+3*x*y**2, x).subs({x:1,y:2})            # 16
sp.diff(x**3*y**2+x*sp.sin(y), x, y).subs({x:1,y:0})    # 1
sp.integrate(y*sp.exp(y**2),(y,0,1))                    # (e-1)/2
sp.Matrix([[1,2,3],[2,4,6],[1,0,0]]).rank()            # 2
sp.Matrix([[2,1,3],[1,0,2],[4,1,8]]).det()            # -1
sp.Matrix([[4,7],[2,6]]).inv()[0,1]                    # -7/10
sp.expand(sp.Matrix([[1,1,1],[1,2,3],[1,4,k]]).det())  # k-7
sp.Matrix([[1,2],[3,2]]).charpoly(lam).as_expr()       # lambda**2-3*lambda-4
sp.Matrix([[5,1],[0,5]]).eigenvects()                  # [(5,2,[(1,0)])]
A=sp.Matrix([[0,6],[1,-1]]); (A*A).eigenvals()         # {4:1,9:1}
```
