"""
Radical Expressions Worksheet Generator
========================================
Supports SIX problem types (mix and match):
  1. Simplify         — reduce √(72x⁵y³)  →  6x²y√(2xy)
  2. Rewrite          — convert radical ↔ rational-exponent notation
  3. Multiply         — √(6x³)·√(8x)      →  simplify
  4. Divide           — √(48x⁵)/√(3x)     →  simplify
  5. Simplify Rat-Exp — (8x⁶y³)^(2/3)     →  4x⁴y²
  6. Power-to-Power   — (x^(2/3))^(3/4)   →  x^(1/2)

Types 1–5: root index is randomly drawn from a user-chosen range (min–max).
Type  6:   uses rational-exponent arithmetic (no explicit root index).

Variable count: 0, 1, 2, or 3 variables
Difficulty:     Easy / Medium / Hard
Export:         Plain text  OR  Google Docs / Auto-LaTeX ($$ ... $$)
"""

import random
import math
import os
from fractions import Fraction

# ═══════════════════════════════════════════════════════════════
#  Constants
# ═══════════════════════════════════════════════════════════════

# Numbers that will NOT be simplified away by extract_root for most indices
# (none are perfect squares, cubes, 4th/5th powers, etc.)
RADICAND_POOL  = [2, 3, 5, 6, 7, 10, 11, 13, 15, 17, 19, 21, 22, 23, 26, 30, 33, 35]
NON_PERFECT_SQ = RADICAND_POOL   # alias kept for clarity
VARS           = ['x', 'y', 'z']

ROOT_NAMES = {
    2: "Square root  (√  )",
    3: "Cube root    (∛  )",
    4: "Fourth root  (∜  )",
    5: "Fifth root",
    6: "Sixth root",
    7: "Seventh root",
    8: "Eighth root",
    9: "Ninth root",
    10: "Tenth root",
}

def root_label(n):
    return ROOT_NAMES.get(n, f"{n}th root")


# ═══════════════════════════════════════════════════════════════
#  Scaling helpers  (keep problems tractable for higher indices)
# ═══════════════════════════════════════════════════════════════

def _k_max(base_max, index):
    """Cap the coefficient K so K^index stays printable."""
    caps = {2: base_max, 3: min(base_max, 5), 4: min(base_max, 4),
            5: 3, 6: 2, 7: 2, 8: 2, 9: 2, 10: 2}
    return caps.get(index, 2)


def _vp_max(base_max, index):
    """Scale down per-variable exponent ceiling for higher roots."""
    return max(1, base_max - max(0, index - 2))


def _rem_pool(diff_pool, index):
    """Return radicand remainders that are NOT perfect index-th powers."""
    out = [r for r in diff_pool if not is_perfect_power(r, index)]
    return out if out else [2]   # fallback


# ═══════════════════════════════════════════════════════════════
#  Math utilities
# ═══════════════════════════════════════════════════════════════

def extract_root(n, index=2):
    """Return (outside, inside) such that ⁿ√n = outside · ⁿ√(inside)."""
    outside, inside = 1, n
    for p in [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47]:
        pk = p ** index
        while inside % pk == 0:
            outside *= p
            inside  //= pk
    return outside, inside


def is_perfect_power(n, index=2):
    root = round(n ** (1 / index))
    for r in [root - 1, root, root + 1]:
        if r > 0 and r ** index == n:
            return True
    return False


# ═══════════════════════════════════════════════════════════════
#  Formatting helpers
# ═══════════════════════════════════════════════════════════════

def tex(expr):
    return f"$${expr}$$"


def sqrt_tex(radicand, index=2):
    return f"\\sqrt{{{radicand}}}" if index == 2 else f"\\sqrt[{index}]{{{radicand}}}"


def sqrt_plain(radicand, index=2):
    return f"sqrt({radicand})" if index == 2 else f"root[{index}]({radicand})"


def var_tex(name, power):
    if power == 0: return ""
    if power == 1: return name
    return f"{name}^{{{power}}}"


def var_plain(name, power):
    if power == 0: return ""
    if power == 1: return name
    return f"{name}^{power}"


def rat_exp_tex(name, frac):
    if frac == 0:               return ""
    if frac == 1:               return name
    if frac.denominator == 1:   return f"{name}^{{{frac.numerator}}}"
    return f"{name}^{{\\frac{{{frac.numerator}}}{{{frac.denominator}}}}}"


def rat_exp_plain(name, frac):
    if frac == 0:               return ""
    if frac == 1:               return name
    if frac.denominator == 1:   return f"{name}^{frac.numerator}"
    return f"{name}^({frac.numerator}/{frac.denominator})"


def build_radicand(num_coeff, var_powers, mode="tex"):
    vf = var_tex if mode == "tex" else var_plain
    parts = []
    if num_coeff not in (0, 1):
        parts.append(str(num_coeff))
    for name, pw in var_powers:
        v = vf(name, pw)
        if v: parts.append(v)
    return "".join(parts) if parts else "1"


def build_expression(coeff, outer_vars, radical_str=None, index=2, mode="tex"):
    sf = sqrt_tex if mode == "tex" else sqrt_plain
    vf = var_tex  if mode == "tex" else var_plain
    parts = []
    if coeff not in (0, 1): parts.append(str(coeff))
    for name, pw in outer_vars:
        v = vf(name, pw)
        if v: parts.append(v)
    if radical_str is not None:
        parts.append(sf(radical_str, index))
    return "".join(parts) if parts else "1"


def build_rat_exp_expression(coeff, var_fracs, mode="tex"):
    rf = rat_exp_tex if mode == "tex" else rat_exp_plain
    parts = []
    if coeff not in (0, 1): parts.append(str(coeff))
    for name, frac in var_fracs:
        t = rf(name, frac)
        if t: parts.append(t)
    return "".join(parts) if parts else "1"


def frac_tex(numerator, denominator):
    f = Fraction(numerator, denominator)
    if f.denominator == 1: return str(f.numerator)
    sign = "-" if f < 0 else ""
    return f"{sign}\\frac{{{abs(f.numerator)}}}{{{f.denominator}}}"


def frac_plain(numerator, denominator):
    f = Fraction(numerator, denominator)
    if f.denominator == 1: return str(f.numerator)
    return f"{f.numerator}/{f.denominator}"


# ═══════════════════════════════════════════════════════════════
#  Difficulty parameter lookup
# ═══════════════════════════════════════════════════════════════

DIFF_PARAMS = {
    "easy":   {"coeff_max": 4, "var_pow_max": 2, "rem_pool": RADICAND_POOL[:5]},
    "medium": {"coeff_max": 6, "var_pow_max": 3, "rem_pool": RADICAND_POOL[:10]},
    "hard":   {"coeff_max": 8, "var_pow_max": 4, "rem_pool": RADICAND_POOL},
}

# Default root ranges per difficulty (user can override via menu)
DIFF_ROOT_DEFAULTS = {
    "easy":   (2, 2),
    "medium": (2, 3),
    "hard":   (2, 4),
}


def _pick_index(root_range):
    """Draw a random root index from the user-chosen range."""
    return random.randint(root_range[0], root_range[1])


# ═══════════════════════════════════════════════════════════════
#  Problem generators
# ═══════════════════════════════════════════════════════════════

# ── 1. SIMPLIFY RADICAL ──────────────────────────────────────

def gen_simplify(num_vars, difficulty, root_range=(2, 2)):
    """
    Produce: ⁿ√(K^n · R · x^(n·a+r) · ...)
    Answer:  K · xᵃ · ... · ⁿ√(R · xʳ · ...)
    """
    p     = DIFF_PARAMS[difficulty]
    index = _pick_index(root_range)
    K     = random.randint(2, _k_max(p["coeff_max"], index))
    pool  = _rem_pool(p["rem_pool"], index)
    R     = random.choice(pool)

    var_names = VARS[:num_vars]
    outer_var_pows, inner_var_pows, total_var_pows = [], [], []
    vp_max = _vp_max(p["var_pow_max"], index)
    for v in var_names:
        out_p = random.randint(1, vp_max)
        in_p  = random.randint(0, index - 1)
        outer_var_pows.append((v, out_p))
        inner_var_pows.append((v, in_p))
        total_var_pows.append((v, index * out_p + in_p))

    radicand_coeff     = (K ** index) * R
    outer_vars_nonzero = [(v, pw) for v, pw in outer_var_pows if pw > 0]
    inner_vars_nonzero = [(v, pw) for v, pw in inner_var_pows if pw > 0]

    return {
        "type":  "simplify",
        "index": index,
        "problem_rad_tex":   build_radicand(radicand_coeff, total_var_pows, "tex"),
        "problem_rad_plain": build_radicand(radicand_coeff, total_var_pows, "plain"),
        "K": K, "outer_vars": outer_vars_nonzero,
        "R": R, "inner_vars": inner_vars_nonzero,
        "simplified_rad_tex":
            build_radicand(R, inner_vars_nonzero, "tex")   if inner_vars_nonzero or R != 1 else None,
        "simplified_rad_plain":
            build_radicand(R, inner_vars_nonzero, "plain") if inner_vars_nonzero or R != 1 else None,
    }


# ── 2. REWRITE (radical ↔ rational exponent) ─────────────────

def gen_rewrite(num_vars, difficulty, root_range=(2, 2)):
    """
    Direction A: ⁿ√(x^p · y^r · ...) = x^(p/n) · y^(r/n) · ...
    Direction B: x^(p/n) · y^(r/n) · ... = ⁿ√(x^p · y^r · ...)
    """
    p         = DIFF_PARAMS[difficulty]
    index     = _pick_index(root_range)
    direction = random.choice(["rad_to_exp", "exp_to_rad"])
    n_vars    = max(1, num_vars)
    var_names = VARS[:n_vars]
    vp_max    = _vp_max(p["var_pow_max"], index)

    var_pows = []
    for v in var_names:
        pw = random.randint(1, index * vp_max)
        # avoid multiples of index so result doesn't trivially collapse to integer
        while pw % index == 0:
            pw = random.randint(1, index * vp_max)
        var_pows.append((v, pw))

    coeff = random.choice([1, 1, 2, 3]) if difficulty != "easy" else 1

    def build_rad_form(mode):
        vf = var_tex if mode == "tex" else var_plain
        sf = sqrt_tex if mode == "tex" else sqrt_plain
        inside_parts = []
        if coeff > 1:
            inside_parts.append(f"{coeff}^{{{index}}}" if mode == "tex" else f"{coeff}^{index}")
        for v, pw in var_pows:
            inside_parts.append(vf(v, pw))
        return sf("".join(inside_parts), index)

    def build_exp_form(mode):
        ff = frac_tex if mode == "tex" else frac_plain
        parts = []
        if coeff > 1:
            parts.append(str(coeff))
        for v, pw in var_pows:
            exp_str = ff(pw, index)
            parts.append(f"{v}^{{{exp_str}}}" if mode == "tex" else f"{v}^({exp_str})")
        return " \\cdot ".join(parts) if mode == "tex" else " * ".join(parts)

    return {
        "type":         "rewrite",
        "direction":    direction,
        "index":        index,
        "coeff":        coeff,
        "var_pows":     var_pows,
        "radical_tex":  build_rad_form("tex"),
        "radical_plain":build_rad_form("plain"),
        "exponent_tex": build_exp_form("tex"),
        "exponent_plain":build_exp_form("plain"),
    }


# ── 3. MULTIPLY RADICALS ─────────────────────────────────────

def gen_multiply(num_vars, difficulty, root_range=(2, 2)):
    """ⁿ√(A·xᵐ) · ⁿ√(B·xⁿ) → ⁿ√(AB·x^(m+n)) → simplify"""
    p         = DIFF_PARAMS[difficulty]
    index     = _pick_index(root_range)
    var_names = VARS[:num_vars]
    pool      = _rem_pool(p["rem_pool"], index)
    vp_max    = _vp_max(p["var_pow_max"], index)
    K_max     = _k_max(p["coeff_max"], index)

    def rand_factor():
        coeff = random.randint(1, max(1, K_max // 2))
        rem   = random.choice(pool)
        vpows = [(v, random.randint(0, vp_max)) for v in var_names]
        return coeff, rem, vpows

    c1, r1, vp1 = rand_factor()
    c2, r2, vp2 = rand_factor()

    combined_num      = r1 * r2
    combined_var_pows = [(v, vp1[i][1] + vp2[i][1]) for i, v in enumerate(var_names)]

    out_n, in_n = extract_root(combined_num, index)
    final_coeff = c1 * c2 * out_n
    final_outer_vars, final_inner_vars = [], []
    for v, total_pw in combined_var_pows:
        out_p = total_pw // index
        in_p  = total_pw % index
        if out_p: final_outer_vars.append((v, out_p))
        if in_p:  final_inner_vars.append((v, in_p))

    def single_rad_str(coeff, rem, vpows, mode):
        num_part = (coeff ** index) * rem
        rad_str  = build_radicand(num_part, vpows, mode)
        sf = sqrt_tex if mode == "tex" else sqrt_plain
        return sf(rad_str, index)

    fin_inner_tex   = build_radicand(in_n, final_inner_vars, "tex")   if in_n != 1 or final_inner_vars else None
    fin_inner_plain = build_radicand(in_n, final_inner_vars, "plain") if in_n != 1 or final_inner_vars else None

    return {
        "type":  "multiply",
        "index": index,
        "fac1_tex":    single_rad_str(c1, r1, vp1, "tex"),
        "fac2_tex":    single_rad_str(c2, r2, vp2, "tex"),
        "fac1_plain":  single_rad_str(c1, r1, vp1, "plain"),
        "fac2_plain":  single_rad_str(c2, r2, vp2, "plain"),
        "combined_coeff_out": c1 * c2,
        "combined_rad_tex":   build_radicand(combined_num, combined_var_pows, "tex"),
        "combined_rad_plain": build_radicand(combined_num, combined_var_pows, "plain"),
        "answer_tex":   build_expression(final_coeff, final_outer_vars, fin_inner_tex,   index, "tex"),
        "answer_plain": build_expression(final_coeff, final_outer_vars, fin_inner_plain, index, "plain"),
    }


# ── 4. DIVIDE RADICALS ───────────────────────────────────────

def gen_divide(num_vars, difficulty, root_range=(2, 2)):
    """ⁿ√(A·xᵐ) / ⁿ√(B·xⁿ) → simplify"""
    p         = DIFF_PARAMS[difficulty]
    index     = _pick_index(root_range)
    var_names = VARS[:num_vars]
    pool      = _rem_pool(p["rem_pool"], index)
    vp_max    = _vp_max(p["var_pow_max"], index)
    K_max     = _k_max(p["coeff_max"], index)

    c_den  = random.randint(1, max(1, K_max // 2))
    r_den  = random.choice(pool)
    vp_den = [(v, random.randint(0, max(0, vp_max - 1))) for v in var_names]

    extra_c = random.randint(2, max(2, K_max // 2))
    extra_r = 1 if random.random() < 0.5 else r_den
    vp_extra = [(v, random.randint(0, vp_max)) for v in var_names]

    c_num  = c_den * extra_c
    r_num  = r_den * extra_r
    vp_num = [(v, vp_den[i][1] + vp_extra[i][1]) for i, v in enumerate(var_names)]

    def rad_str(coeff, rem, vpows, mode):
        num_part = (coeff ** index) * rem
        rad      = build_radicand(num_part, vpows, mode)
        sf = sqrt_tex if mode == "tex" else sqrt_plain
        return sf(rad, index)

    num_tex,   den_tex   = rad_str(c_num, r_num, vp_num, "tex"),   rad_str(c_den, r_den, vp_den, "tex")
    num_plain, den_plain = rad_str(c_num, r_num, vp_num, "plain"), rad_str(c_den, r_den, vp_den, "plain")

    quot_num = r_num * (c_num ** index)
    quot_den = r_den * (c_den ** index)
    g = math.gcd(quot_num, quot_den)
    quot_num //= g
    quot_den //= g

    combined_var_pows = [(v, vp_num[i][1] - vp_den[i][1]) for i, v in enumerate(var_names)]

    out_n, in_n = extract_root(quot_num, index)
    out_d, in_d = extract_root(quot_den, index)
    final_outer_vars, final_inner_vars = [], []
    for v, pw in combined_var_pows:
        out_p = pw // index
        in_p  = pw % index
        if out_p: final_outer_vars.append((v, out_p))
        if in_p:  final_inner_vars.append((v, in_p))

    def combined_frac_str(qn, qd, vpows, mode):
        vf = var_tex if mode == "tex" else var_plain
        num_parts = [str(qn)] if qn != 1 else []
        for v, pw in vpows:
            vt = vf(v, pw)
            if vt: num_parts.append(vt)
        num_str = "".join(num_parts) or "1"
        inside  = (f"\\frac{{{num_str}}}{{{qd}}}" if qd != 1 and mode == "tex"
                   else (f"({num_str})/{qd}" if qd != 1 else num_str))
        sf = sqrt_tex if mode == "tex" else sqrt_plain
        return sf(inside, index)

    fin_inner_tex   = build_radicand(in_n, final_inner_vars, "tex")   if in_n != 1 or final_inner_vars else None
    fin_inner_plain = build_radicand(in_n, final_inner_vars, "plain") if in_n != 1 or final_inner_vars else None

    if out_d == 1 and in_d == 1:
        ans_tex   = build_expression(out_n, final_outer_vars, fin_inner_tex,   index, "tex")
        ans_plain = build_expression(out_n, final_outer_vars, fin_inner_plain, index, "plain")
    else:
        num_ans = build_expression(out_n, final_outer_vars, fin_inner_tex, index, "tex")
        den_str = build_expression(out_d, [],
                      build_radicand(in_d, [], "tex") if in_d != 1 else None, index, "tex")
        ans_tex   = f"\\frac{{{num_ans}}}{{{den_str}}}"
        num_p     = build_expression(out_n, final_outer_vars, fin_inner_plain, index, "plain")
        den_p     = str(out_d) if in_d == 1 else build_expression(
                        out_d, [], build_radicand(in_d, [], "plain"), index, "plain")
        ans_plain = f"({num_p})/({den_p})"

    return {
        "type":  "divide",
        "index": index,
        "num_tex": num_tex, "den_tex": den_tex,
        "num_plain": num_plain, "den_plain": den_plain,
        "combined_str_tex":   combined_frac_str(quot_num, quot_den, combined_var_pows, "tex"),
        "combined_str_plain": combined_frac_str(quot_num, quot_den, combined_var_pows, "plain"),
        "answer_tex":   ans_tex,
        "answer_plain": ans_plain,
    }


# ── 5. SIMPLIFY WITH RATIONAL EXPONENTS ─────────────────────
#
#   Form:  ( K^q · x^a · y^b · ... )^(p/q)
#   The root index q is drawn from root_range so that the type
#   genuinely exercises nth-root arithmetic.

def gen_simplify_rat_exp(num_vars, difficulty, root_range=(2, 2)):
    p      = DIFF_PARAMS[difficulty]
    q      = _pick_index(root_range)           # denominator = root index
    K_max  = _k_max(p["coeff_max"], q)
    vp_max = _vp_max(p["var_pow_max"], q)

    # Numerator p of the outer exponent: 1..(q+1), gcd(p,q)=1, p≠q
    candidates = [n for n in range(1, q + 2) if math.gcd(n, q) == 1 and n != q]
    pw_num = random.choice(candidates[:4])     # keep numerator small
    outer_frac = Fraction(pw_num, q)

    K          = random.randint(2, K_max)
    base_coeff = K ** q
    ans_coeff  = K ** pw_num

    var_names      = VARS[:num_vars]
    var_pows_inner = []
    for v in var_names:
        a = random.randint(1, q * vp_max)
        var_pows_inner.append((v, a))

    ans_var_fracs = [(v, Fraction(a * pw_num, q)) for v, a in var_pows_inner]

    def base_str(mode):
        vf = var_tex if mode == "tex" else var_plain
        parts = [str(base_coeff)] if base_coeff != 1 else []
        for v, a in var_pows_inner:
            parts.append(vf(v, a))
        return "".join(parts) or "1"

    def outer_exp_str(mode):
        ff = frac_tex if mode == "tex" else frac_plain
        return ff(pw_num, q)

    def problem_str(mode):
        b   = base_str(mode)
        exp = outer_exp_str(mode)
        return (f"\\left({b}\\right)^{{{exp}}}" if mode == "tex"
                else f"({b})^({pw_num}/{q})")

    def answer_str(mode):
        return build_rat_exp_expression(ans_coeff, ans_var_fracs, mode)

    def distribute_step(mode):
        ff = frac_tex if mode == "tex" else frac_plain
        vf = var_tex  if mode == "tex" else var_plain
        parts = []
        if base_coeff != 1:
            parts.append(f"{base_coeff}^{{{ff(pw_num, q)}}}" if mode == "tex"
                         else f"{base_coeff}^({pw_num}/{q})")
        for v, a in var_pows_inner:
            parts.append(f"{v}^{{{ff(a * pw_num, q)}}}" if mode == "tex"
                         else f"{v}^({a * pw_num}/{q})")
        return (" \\cdot ".join(parts) if mode == "tex" else " * ".join(parts))

    return {
        "type":          "simplify_rat_exp",
        "q":             q,
        "pw_num":        pw_num,
        "K":             K,
        "ans_coeff":     ans_coeff,
        "base_coeff":    base_coeff,
        "var_pows_inner": var_pows_inner,
        "ans_var_fracs":  ans_var_fracs,
        "problem_tex":    problem_str("tex"),
        "problem_plain":  problem_str("plain"),
        "answer_tex":     answer_str("tex"),
        "answer_plain":   answer_str("plain"),
        "distribute_tex":   distribute_step("tex"),
        "distribute_plain": distribute_step("plain"),
    }


# ── 6. POWER TO A POWER (rational exponents) ─────────────────
#   Not driven by root_range — uses its own rational-exponent logic.

def gen_power_to_power(num_vars, difficulty, root_range=(2, 2)):
    p = DIFF_PARAMS[difficulty]

    outer_choices = [
        Fraction(1, 2), Fraction(1, 3), Fraction(2, 3),
        Fraction(3, 2), Fraction(3, 4), Fraction(4, 3),
        Fraction(2, 1), Fraction(3, 1), Fraction(4, 1), Fraction(6, 1),
    ]
    if difficulty == "easy":
        outer_choices = [Fraction(2, 1), Fraction(3, 1), Fraction(1, 2), Fraction(1, 3)]
    outer = random.choice(outer_choices)

    include_coeff = difficulty != "easy" and random.random() < 0.6
    if include_coeff:
        K_c    = random.randint(2, p["coeff_max"] // 2 + 1)
        c_base = K_c ** outer.denominator
        c_ans  = K_c ** outer.numerator
    else:
        c_base, c_ans = 1, 1

    n_vars    = max(1, num_vars)
    var_names = VARS[:n_vars]
    inner_denoms = [2, 3, 4, 6]
    var_inner_fracs, ans_var_fracs = [], []
    for v in var_names:
        denom      = random.choice(inner_denoms)
        numer      = random.randint(1, denom * p["var_pow_max"])
        while numer % denom == 0 and difficulty == "easy":
            numer = random.randint(1, denom * p["var_pow_max"])
        inner_frac  = Fraction(numer, denom)
        result_frac = inner_frac * outer
        var_inner_fracs.append((v, inner_frac))
        ans_var_fracs.append((v, result_frac))

    def inner_expr(mode):
        rf = rat_exp_tex if mode == "tex" else rat_exp_plain
        parts = [str(c_base)] if c_base != 1 else []
        for v, frac in var_inner_fracs:
            t = rf(v, frac)
            if t: parts.append(t)
        return "".join(parts) or "1"

    def outer_exp_str(mode):
        ff = frac_tex if mode == "tex" else frac_plain
        return ff(outer.numerator, outer.denominator)

    def problem_str(mode):
        inner = inner_expr(mode)
        exp   = outer_exp_str(mode)
        return (f"\\left({inner}\\right)^{{{exp}}}" if mode == "tex"
                else f"({inner})^({outer.numerator}/{outer.denominator})")

    def answer_str(mode):
        return build_rat_exp_expression(c_ans, ans_var_fracs, mode)

    def mult_step(mode):
        ff = frac_tex if mode == "tex" else frac_plain
        m_s, n_s = str(outer.numerator), str(outer.denominator)
        parts = []
        if c_base != 1:
            parts.append(f"{c_base}^{{{outer_exp_str('tex')}}}" if mode == "tex"
                         else f"{c_base}^({outer.numerator}/{outer.denominator})")
        for v, frac in var_inner_fracs:
            p_s = str(frac.numerator); q_s = str(frac.denominator)
            parts.append(
                f"{v}^{{\\frac{{{p_s} \\cdot {m_s}}}{{{q_s} \\cdot {n_s}}}}}" if mode == "tex"
                else f"{v}^(({frac.numerator}*{outer.numerator})/({frac.denominator}*{outer.denominator}))"
            )
        return " \\cdot ".join(parts) if mode == "tex" else " * ".join(parts)

    return {
        "type":            "power_to_power",
        "outer":           outer,
        "c_base":          c_base,
        "c_ans":           c_ans,
        "var_inner_fracs": var_inner_fracs,
        "ans_var_fracs":   ans_var_fracs,
        "problem_tex":     problem_str("tex"),
        "problem_plain":   problem_str("plain"),
        "answer_tex":      answer_str("tex"),
        "answer_plain":    answer_str("plain"),
        "mult_step_tex":   mult_step("tex"),
        "mult_step_plain": mult_step("plain"),
    }


# ═══════════════════════════════════════════════════════════════
#  Problem → question lines
# ═══════════════════════════════════════════════════════════════

def problem_lines(prob, number, latex_mode):
    m  = "tex" if latex_mode else "plain"
    sf = sqrt_tex if latex_mode else sqrt_plain
    lines = [f"Problem {number}:"]

    if prob["type"] == "simplify":
        rad  = prob[f"problem_rad_{m}"]
        expr = sf(rad, prob["index"])
        stmt = tex(f"\\text{{Simplify: }}{expr}") if latex_mode else f"  Simplify:  {expr}"
        lines.append(f"  {stmt}")

    elif prob["type"] == "rewrite":
        if prob["direction"] == "rad_to_exp":
            stmt = (tex(f"\\text{{Rewrite as a rational exponent: }}{prob['radical_tex']}")
                    if latex_mode else f"  Rewrite as a rational exponent: {prob['radical_plain']}")
        else:
            stmt = (tex(f"\\text{{Rewrite as a radical: }}{prob['exponent_tex']}")
                    if latex_mode else f"  Rewrite as a radical: {prob['exponent_plain']}")
        lines.append(f"  {stmt}")

    elif prob["type"] == "multiply":
        stmt = (tex(f"\\text{{Multiply and simplify: }}{prob['fac1_tex']} \\cdot {prob['fac2_tex']}")
                if latex_mode else f"  Multiply and simplify:  {prob['fac1_plain']}  ×  {prob['fac2_plain']}")
        lines.append(f"  {stmt}")

    elif prob["type"] == "divide":
        stmt = (tex(f"\\text{{Divide and simplify: }}\\dfrac{{{prob['num_tex']}}}{{{prob['den_tex']}}}")
                if latex_mode else f"  Divide and simplify:  {prob['num_plain']}  ÷  {prob['den_plain']}")
        lines.append(f"  {stmt}")

    elif prob["type"] == "simplify_rat_exp":
        stmt = (tex(f"\\text{{Simplify: }}{prob['problem_tex']}")
                if latex_mode else f"  Simplify:  {prob['problem_plain']}")
        lines.append(f"  {stmt}")

    elif prob["type"] == "power_to_power":
        stmt = (tex(f"\\text{{Simplify: }}{prob['problem_tex']}")
                if latex_mode else f"  Simplify:  {prob['problem_plain']}")
        lines.append(f"  {stmt}")

    lines.append("")
    return lines


# ═══════════════════════════════════════════════════════════════
#  Problem → solution lines
# ═══════════════════════════════════════════════════════════════

def solution_lines(prob, number, latex_mode):
    m  = "tex" if latex_mode else "plain"
    sf = sqrt_tex if latex_mode else sqrt_plain

    def wrap(expr):
        return tex(expr) if latex_mode else expr

    lines = []

    if prob["type"] == "simplify":
        rad   = prob[f"problem_rad_{m}"]
        rad_s = prob.get(f"simplified_rad_{m}")
        outer = build_expression(prob["K"], prob["outer_vars"], rad_s, prob["index"], m)
        lines += [
            f"Problem {number} (Simplify — {root_label(prob['index'])}):",
            f"  Given:    {wrap(sf(rad, prob['index']))}",
            f"  Step 1 — Identify the perfect-{_ordinal(prob['index'])} factor in the radicand.",
            f"  Step 2 — Extract: {wrap(build_expression(prob['K'], prob['outer_vars'], None, 2, m))}",
            f"  Answer:   {wrap(outer)}",
        ]

    elif prob["type"] == "rewrite":
        idx = prob["index"]
        if prob["direction"] == "rad_to_exp":
            lines += [
                f"Problem {number} (Rewrite — {root_label(idx)} → Exponent):",
                f"  Given:    {wrap(prob[f'radical_{m}'])}",
                f"  Rule:     {wrap(f'\\sqrt[{idx}]{{x^m}} = x^{{m/{idx}}}') if latex_mode else f'root[{idx}](x^m) = x^(m/{idx})'}",
                f"  Answer:   {wrap(prob[f'exponent_{m}'])}",
            ]
        else:
            lines += [
                f"Problem {number} (Rewrite — Exponent → {root_label(idx)}):",
                f"  Given:    {wrap(prob[f'exponent_{m}'])}",
                f"  Rule:     {wrap(f'x^{{m/{idx}}} = \\sqrt[{idx}]{{x^m}}') if latex_mode else f'x^(m/{idx}) = root[{idx}](x^m)'}",
                f"  Answer:   {wrap(prob[f'radical_{m}'])}",
            ]

    elif prob["type"] == "multiply":
        step1 = sf(prob[f"combined_rad_{m}"], prob["index"])
        c_out = prob["combined_coeff_out"]
        full_step1 = (f"{c_out}" if c_out != 1 else "") + step1
        given = (wrap(prob['fac1_tex'] + ' \\cdot ' + prob['fac2_tex']) if latex_mode
                 else f"{prob['fac1_plain']}  ×  {prob['fac2_plain']}")
        lines += [
            f"Problem {number} (Multiply — {root_label(prob['index'])}):",
            f"  Given:    {given}",
            f"  Step 1 — Combine under one radical: {wrap(full_step1)}",
            f"  Step 2 — Simplify the radical.",
            f"  Answer:   {wrap(prob[f'answer_{m}'])}",
        ]

    elif prob["type"] == "divide":
        given = (wrap('\\dfrac{' + prob['num_tex'] + '}{' + prob['den_tex'] + '}') if latex_mode
                 else f"{prob['num_plain']}  ÷  {prob['den_plain']}")
        lines += [
            f"Problem {number} (Divide — {root_label(prob['index'])}):",
            f"  Given:    {given}",
            f"  Step 1 — Combine under one radical: {wrap(prob[f'combined_str_{m}'])}",
            f"  Step 2 — Simplify the radical.",
            f"  Answer:   {wrap(prob[f'answer_{m}'])}",
        ]

    elif prob["type"] == "simplify_rat_exp":
        q, pw_num = prob["q"], prob["pw_num"]
        K, ans_c  = prob["K"], prob["ans_coeff"]
        ff = frac_tex if latex_mode else frac_plain
        root_name = root_label(q)
        if latex_mode:
            rule = wrap(f"\\left(a^m\\right)^{{n}} = a^{{m \\cdot n}}")
            coeff_step = wrap(
                f"{prob['base_coeff']}^{{{ff(pw_num, q)}}} = "
                f"{K}^{{{q} \\cdot \\frac{{{pw_num}}}{{{q}}}}} = "
                f"{K}^{{{pw_num}}} = {ans_c}"
            )
        else:
            rule = "(a^m)^n = a^(m*n)"
            coeff_step = f"{prob['base_coeff']}^({pw_num}/{q}) = {K}^({pw_num}) = {ans_c}"
        lines += [
            f"Problem {number} (Simplify Rat-Exp — {root_name} denominator):",
            f"  Given:    {wrap(prob[f'problem_{m}'])}",
            f"  Rule:     {rule}",
            f"  Step 1 — Distribute exponent to each factor:",
            f"           {wrap(prob[f'distribute_{m}'])}",
            f"  Step 2 — Simplify numeric part: {coeff_step}",
            f"  Step 3 — Reduce each variable exponent fraction.",
            f"  Answer:   {wrap(prob[f'answer_{m}'])}",
        ]

    elif prob["type"] == "power_to_power":
        outer = prob["outer"]
        ff    = frac_tex if latex_mode else frac_plain
        rule  = (wrap(f"\\left(x^{{a}}\\right)^{{b}} = x^{{a \\cdot b}}") if latex_mode
                 else "(x^a)^b = x^(a*b)")
        mult_lines = []
        for v, inner_f in prob["var_inner_fracs"]:
            result_f = inner_f * outer
            mult_lines.append(
                f"           {wrap(f'{v}^{{{ff(inner_f.numerator, inner_f.denominator)}}} \\cdot {ff(outer.numerator, outer.denominator)} = {v}^{{{ff(result_f.numerator, result_f.denominator)}}}')} "
                if latex_mode else
                f"           {v}^({inner_f.numerator}/{inner_f.denominator}) × ({outer.numerator}/{outer.denominator}) = {v}^({result_f.numerator}/{result_f.denominator})"
            )
        if prob["c_base"] != 1:
            c_b, c_a = prob["c_base"], prob["c_ans"]
            mult_lines.insert(0,
                f"           {wrap(f'{c_b}^{{{ff(outer.numerator, outer.denominator)}}} = {c_a}')}"
                if latex_mode else
                f"           {c_b}^({outer.numerator}/{outer.denominator}) = {c_a}"
            )
        lines += [
            f"Problem {number} (Power to a Power):",
            f"  Given:    {wrap(prob[f'problem_{m}'])}",
            f"  Rule:     {rule}",
            f"  Step 1 — Multiply each inner exponent by the outer exponent:",
        ] + mult_lines + [
            f"  Step 2 — Reduce each resulting fraction.",
            f"  Answer:   {wrap(prob[f'answer_{m}'])}",
        ]

    lines.append("")
    return lines


def _ordinal(n):
    return {2: "square", 3: "cube", 4: "fourth", 5: "fifth",
            6: "sixth",  7: "seventh", 8: "eighth"}.get(n, f"{n}th")


# ═══════════════════════════════════════════════════════════════
#  Registry
# ═══════════════════════════════════════════════════════════════

TYPE_GENERATORS = {
    "simplify":         gen_simplify,
    "rewrite":          gen_rewrite,
    "multiply":         gen_multiply,
    "divide":           gen_divide,
    "simplify_rat_exp": gen_simplify_rat_exp,
    "power_to_power":   gen_power_to_power,
}

TYPE_LABELS = {
    "simplify":         "Simplifying Radicals",
    "rewrite":          "Rewriting Radicals (Radical ↔ Rational Exponent)",
    "multiply":         "Multiplying Radicals",
    "divide":           "Dividing Radicals",
    "simplify_rat_exp": "Simplifying with Rational Exponents",
    "power_to_power":   "Power to a Power (Rational Exponents)",
}

# Types that respect root_range
ROOT_RANGE_TYPES = {"simplify", "rewrite", "multiply", "divide", "simplify_rat_exp"}


# ═══════════════════════════════════════════════════════════════
#  Worksheet builder
# ═══════════════════════════════════════════════════════════════

def root_range_label(rr):
    lo, hi = rr
    if lo == hi:
        return root_label(lo).split("(")[0].strip()
    if lo == 2 and hi == 3:
        return "Square & Cube roots"
    names = [root_label(n).split("  (")[0].strip() for n in range(lo, hi + 1)]
    return " + ".join(names)


def _distribute(total, n_buckets):
    """Return a list of n_buckets counts that sum to total (as evenly as possible)."""
    base, extra = divmod(total, n_buckets)
    return [base + (1 if i < extra else 0) for i in range(n_buckets)]


def generate_worksheet(num_problems=10, problem_types=None, num_vars=1,
                       difficulty="medium", show_solutions=True,
                       title=None, latex_mode=False,
                       root_range=None):
    """
    Problems are grouped by type, each group preceded by a section header.
    Problems are distributed as evenly as possible across the selected types.

    root_range : (min_index, max_index)  applied to problem types 1–5.
                 None → use difficulty default.
    """
    if problem_types is None:
        problem_types = ["simplify"]
    if root_range is None:
        root_range = DIFF_ROOT_DEFAULTS[difficulty]

    lines    = []
    problems = []          # flat list of all generated problem dicts
    sep      = "=" * 68
    sec_sep  = "-" * 68

    heading   = title or "RADICAL EXPRESSIONS — PRACTICE WORKSHEET"
    var_label = {0: "No Variables (Numbers Only)", 1: "1 Variable (x)",
                 2: "2 Variables (x, y)", 3: "3 Variables (x, y, z)"}[num_vars]
    types_str = ", ".join(TYPE_LABELS[t] for t in problem_types)

    uses_root_range = any(t in ROOT_RANGE_TYPES for t in problem_types)
    root_info = (f"Root range:  {root_label(root_range[0]).split('  (')[0].strip()} "
                 f"(index {root_range[0]})  →  "
                 f"{root_label(root_range[1]).split('  (')[0].strip()} "
                 f"(index {root_range[1]})"
                 if uses_root_range else "")

    # ── Cover page ───────────────────────────────────────────────
    lines += [sep, heading, sep,
              f"Topics:     {types_str}",
              f"Variables:  {var_label}",
              f"Difficulty: {difficulty.capitalize()}   |   Problems: {num_problems}"]
    if root_info:
        lines.append(root_info)
    lines += ["",
              "Instructions: Simplify each expression completely.",
              "  • Assume all variables represent non-negative real numbers.",
              "  • Write all answers using positive exponents."]
    if latex_mode:
        lines += ["",
                  "NOTE: Open in Google Docs → Extensions → Add-ons →",
                  "      'Auto-LaTeX Equations' → Start  to render equations."]
    lines += [sep, ""]

    # ── Distribute problems evenly across types ───────────────────
    counts = _distribute(num_problems, len(problem_types))
    # counts[i] = number of problems for problem_types[i]

    # Build section groups: each entry is (ptype, [prob_dict, ...])
    groups = []
    for ptype, count in zip(problem_types, counts):
        group_probs = [
            TYPE_GENERATORS[ptype](num_vars, difficulty, root_range=root_range)
            for _ in range(count)
        ]
        groups.append((ptype, group_probs))
        problems.extend(group_probs)

    # ── Emit problems grouped by section ─────────────────────────
    global_num = 1   # sequential number that continues across sections
    for sec_idx, (ptype, group_probs) in enumerate(groups, 1):
        # Section header
        label      = TYPE_LABELS[ptype]
        header_txt = f"  SECTION {sec_idx} — {label.upper()}"
        lines += [sec_sep, header_txt, sec_sep, ""]

        for prob in group_probs:
            lines += problem_lines(prob, global_num, latex_mode)
            global_num += 1

    # ── Answer key, also grouped ──────────────────────────────────
    if show_solutions:
        lines += ["", sep, "A N S W E R   K E Y", sep]

        key_num = 1
        for sec_idx, (ptype, group_probs) in enumerate(groups, 1):
            label      = TYPE_LABELS[ptype]
            header_txt = f"  SECTION {sec_idx} — {label.upper()}"
            lines += ["", sec_sep, header_txt, sec_sep, ""]
            for prob in group_probs:
                lines += solution_lines(prob, key_num, latex_mode)
                key_num += 1

    lines += [sep, "End of Worksheet", sep]
    return lines


# ═══════════════════════════════════════════════════════════════
#  Output helpers
# ═══════════════════════════════════════════════════════════════

def print_to_console(lines):
    for line in lines:
        print(line)


def save_to_file(lines, filename):
    with open(filename, "w", encoding="utf-8") as f:
        for line in lines:
            f.write(line + "\n")
    print(f"\n  ✓ Saved to: {os.path.abspath(filename)}")


# ═══════════════════════════════════════════════════════════════
#  Smart input helper  (echoes every accepted value)
# ═══════════════════════════════════════════════════════════════

def ask(prompt, valid=None, default=None, cast=None):
    while True:
        raw = input(prompt).strip()
        if raw == "" and default is not None:
            raw = default
        if cast is not None:
            try:
                value = cast(raw)
            except (ValueError, TypeError):
                print(f"    ✗  \"{raw}\" is not valid — please try again.")
                continue
        else:
            value = raw
        if valid is not None and str(value) not in valid:
            print(f"    ✗  \"{value}\" not recognised — choose: {' / '.join(valid)}")
            continue
        print(f"    ✓  You entered: {value}")
        return value


# ═══════════════════════════════════════════════════════════════
#  Interactive menu  (8 steps)
# ═══════════════════════════════════════════════════════════════

def interactive_menu():
    DIFF_MAP   = {"1": "easy", "2": "medium", "3": "hard"}
    OUT_LABELS = {"1": "Print to screen", "2": "Save to file", "3": "Both"}
    FMT_LABELS = {"1": "Plain text", "2": "Google Docs / Auto-LaTeX ($$ ... $$)"}
    VAR_LABELS = {
        "0": "No variables (numbers only)",
        "1": "1 variable (x)",
        "2": "2 variables (x, y)",
        "3": "3 variables (x, y, z)",
    }
    TYPE_MAP = {
        "1": "simplify",
        "2": "rewrite",
        "3": "multiply",
        "4": "divide",
        "5": "simplify_rat_exp",
        "6": "power_to_power",
    }

    while True:
        print("\n" + "=" * 68)
        print("   RADICAL EXPRESSIONS WORKSHEET GENERATOR")
        print("=" * 68)
        print("  Press Enter at any prompt to accept the [default].\n")

        # ── Step 1: Problem types ───────────────────────────────────
        print("  Step 1 / 8 — Problem types  (comma-separated)")
        print("    1  Simplifying Radicals              e.g. sqrt(72x^5y^3)")
        print("    2  Rewriting Radicals                e.g. sqrt[3](x^2) = x^(2/3)")
        print("    3  Multiplying Radicals              e.g. sqrt(6x) · sqrt(2x^3)")
        print("    4  Dividing Radicals                 e.g. sqrt(48x^5) / sqrt(3x)")
        print("    5  Simplifying with Rational Exp.   e.g. (8x^6)^(2/3)  →  4x^4")
        print("    6  Power to a Power                 e.g. (x^(2/3))^(3/4)  →  x^(1/2)")
        type_selected = []
        while not type_selected:
            raw = ask("    Your choice [default: 1]: ", default="1")
            for part in raw.replace(" ", "").split(","):
                if part in TYPE_MAP:
                    t = TYPE_MAP[part]
                    if t not in type_selected:
                        type_selected.append(t)
            if not type_selected:
                print("    ✗  No valid choices — enter digits 1 through 6.")
        labels = [TYPE_LABELS[t] for t in type_selected]
        print(f"         → Selected: {', '.join(labels)}")
        uses_root_range = any(t in ROOT_RANGE_TYPES for t in type_selected)

        # ── Step 2: Number of variables ─────────────────────────────
        print("\n  Step 2 / 8 — Number of variables")
        for k, v in VAR_LABELS.items():
            dflt = "  [default]" if k == "1" else ""
            print(f"    {k}  {v}{dflt}")
        var_key  = ask("    Choose (0 / 1 / 2 / 3): ", valid=["0","1","2","3"], default="1")
        num_vars = int(var_key)
        print(f"         → Variables: {VAR_LABELS[var_key]}")

        # ── Step 3: Difficulty ──────────────────────────────────────
        print("\n  Step 3 / 8 — Difficulty")
        print("    1  Easy   — small numbers, powers ≤ 2")
        print("    2  Medium — moderate numbers, powers ≤ 3  [default]")
        print("    3  Hard   — larger numbers, powers ≤ 4")
        diff_key   = ask("    Choose (1 / 2 / 3): ", valid=["1","2","3"], default="2")
        difficulty = DIFF_MAP[diff_key]
        print(f"         → Difficulty: {difficulty.capitalize()}")

        # ── Step 4: Root index range  (types 1–5 only) ─────────────
        diff_default_rr = DIFF_ROOT_DEFAULTS[difficulty]
        if uses_root_range:
            print("\n  Step 4 / 8 — Root index range  (applies to problem types 1–5)")
            print("    The root index (n) controls which radical is used in each problem.")
            print("    Every problem will pick a random index between your Min and Max.\n")
            print("    Available root indices:")
            for n in range(2, 11):
                print(f"      {n}  →  {root_label(n)}")
            print(f"\n    Difficulty default: Min = {diff_default_rr[0]},  Max = {diff_default_rr[1]}")
            print("    (Press Enter to keep the difficulty default for each field)")

            while True:
                min_root = ask(
                    f"    Minimum root index (2–10) [default: {diff_default_rr[0]}]: ",
                    cast=int, default=str(diff_default_rr[0])
                )
                if 2 <= min_root <= 10:
                    break
                print("    ✗  Minimum must be between 2 and 10.")

            while True:
                max_root = ask(
                    f"    Maximum root index ({min_root}–10) [default: {max(min_root, diff_default_rr[1])}]: ",
                    cast=int, default=str(max(min_root, diff_default_rr[1]))
                )
                if min_root <= max_root <= 10:
                    break
                print(f"    ✗  Maximum must be between {min_root} and 10.")

            root_range = (min_root, max_root)
            if min_root == max_root:
                rr_display = f"Fixed at {root_label(min_root).split('  (')[0].strip()} (index {min_root})"
            else:
                lo_name = root_label(min_root).split("  (")[0].strip()
                hi_name = root_label(max_root).split("  (")[0].strip()
                rr_display = f"{lo_name} (index {min_root})  →  {hi_name} (index {max_root})  — randomized each problem"
            print(f"         → Root range: {rr_display}")
        else:
            root_range = diff_default_rr
            rr_display = "N/A (Type 6 only — uses rational exponent logic)"
            print("\n  Step 4 / 8 — Root index range")
            print("    (Skipped — only Type 6 selected; root range does not apply.)")

        # ── Step 5: Number of problems ──────────────────────────────
        print("\n  Step 5 / 8 — Number of problems")
        while True:
            num = ask("    How many? (1–60) [default: 10]: ", default="10", cast=int)
            if 1 <= num <= 60:
                break
            print(f"    ✗  {num} is out of range — enter 1 to 60.")

        # ── Step 6: Answer key ──────────────────────────────────────
        print("\n  Step 6 / 8 — Answer key")
        sol_raw        = ask("    Include answer key? (y / n) [default: y]: ",
                             valid=["y","n"], default="y")
        show_solutions = sol_raw == "y"
        print(f"         → Answer key: {'Yes — included' if show_solutions else 'No — omitted'}")

        # ── Step 7: Export format ───────────────────────────────────
        print("\n  Step 7 / 8 — Export format")
        print("    1  Plain text — human-readable  [default]")
        print("    2  Google Docs / Auto-LaTeX  ($$ ... $$  delimiters)")
        fmt_key    = ask("    Choose (1 / 2): ", valid=["1","2"], default="1")
        latex_mode = fmt_key == "2"
        print(f"         → Format: {FMT_LABELS[fmt_key]}")

        # ── Step 8: Title & output ──────────────────────────────────
        print("\n  Step 8 / 8 — Title & output")
        title_raw    = input("    Custom title (Enter = default): ").strip()
        custom_title = title_raw or None
        print(f"    ✓  You entered: {'\"' + custom_title + '\"' if custom_title else '(default title)'}")

        print()
        print("    Output mode:")
        print("      1  Print to screen")
        print("      2  Save to file")
        print("      3  Both  [default]")
        out = ask("    Choose (1 / 2 / 3): ", valid=["1","2","3"], default="3")
        print(f"         → Output: {OUT_LABELS[out]}")

        filename = None
        if out in ("2", "3"):
            type_tag  = "_".join(t[:3] for t in type_selected)
            rr_tag    = f"_root{root_range[0]}-{root_range[1]}" if uses_root_range else ""
            fmt_tag   = "_latex" if latex_mode else ""
            dflt_name = f"radicals_{type_tag}_{num}probs_{difficulty}{rr_tag}{fmt_tag}.txt"
            print(f"\n    File name [default: {dflt_name}]")
            filename = ask("    Enter file name: ", default=dflt_name)
            print(f"         → File: {filename}")

        # ── Confirmation summary ────────────────────────────────────
        print("\n" + "-" * 68)
        print("  CONFIRM YOUR SELECTIONS")
        print("-" * 68)
        print(f"  Problem types : {', '.join(labels)}")
        print(f"  Variables     : {VAR_LABELS[var_key]}")
        print(f"  Difficulty    : {difficulty.capitalize()}")
        if uses_root_range:
            print(f"  Root range    : {rr_display}")
        print(f"  Problems      : {num}")
        print(f"  Answer key    : {'Yes' if show_solutions else 'No'}")
        print(f"  Format        : {FMT_LABELS[fmt_key]}")
        print(f"  Title         : {custom_title or '(default)'}")
        print(f"  Output        : {OUT_LABELS[out]}")
        if filename:
            print(f"  File name     : {filename}")
        print("-" * 68)

        confirm = input("\n  Press Enter to GENERATE, or type 'r' to restart: ").strip().lower()
        if confirm == "r":
            print("\n  ↺  Restarting — all selections cleared.\n")
            continue

        # ── Generate ────────────────────────────────────────────────
        print("\n  Generating worksheet…")
        lines = generate_worksheet(
            num_problems   = num,
            problem_types  = type_selected,
            num_vars       = num_vars,
            difficulty     = difficulty,
            show_solutions = show_solutions,
            title          = custom_title,
            latex_mode     = latex_mode,
            root_range     = root_range,
        )

        if out in ("1", "3"):
            print()
            print_to_console(lines)

        if out in ("2", "3"):
            save_to_file(lines, filename)

        if latex_mode and out in ("2", "3"):
            print()
            print("  ── Google Docs instructions ─────────────────────────────────")
            print("  1. Open Google Docs → create a new blank document.")
            print("  2. Extensions → Add-ons → Get add-ons → search")
            print("     'Auto-LaTeX Equations' → install.")
            print("  3. Paste the saved .txt contents into the document.")
            print("  4. Extensions → Auto-LaTeX Equations → Start.")
            print("     Every $$ ... $$ block becomes a rendered math image.")
            print("  ─────────────────────────────────────────────────────────────")

        print("\n  Done! Happy studying! 📐\n")
        break


# ═══════════════════════════════════════════════════════════════
#  Quick-use helper  (programmatic / scripted use)
# ═══════════════════════════════════════════════════════════════

def quick_generate(num_problems=10, problem_types=None, num_vars=1,
                   difficulty="medium", show_solutions=True,
                   filename=None, title=None, latex_mode=False,
                   root_range=None):
    """
    Generate a worksheet without the interactive menu.

    root_range : (min_index, max_index) for problem types 1–5.
                 None  →  use difficulty default.

    problem_types : any subset of
        ['simplify', 'rewrite', 'multiply', 'divide',
         'simplify_rat_exp', 'power_to_power']
    """
    if problem_types is None:
        problem_types = ["simplify"]
    lines = generate_worksheet(num_problems, problem_types, num_vars,
                               difficulty, show_solutions, title, latex_mode,
                               root_range=root_range)
    if filename:
        save_to_file(lines, filename)
    else:
        print_to_console(lines)


# ═══════════════════════════════════════════════════════════════
#  Entry point
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    interactive_menu()