"""
Radical Expressions Worksheet Generator — FastAPI Web Service
=============================================================
POST /generate   → returns a worksheet as plain text or LaTeX
GET  /           → serves a simple HTML form UI
"""

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, PlainTextResponse
from pydantic import BaseModel
from typing import List, Optional
import random, math, os
from fractions import Fraction

# ═══════════════════════════════════════════════════════════════
#  Constants
# ═══════════════════════════════════════════════════════════════

RADICAND_POOL  = [2, 3, 5, 6, 7, 10, 11, 13, 15, 17, 19, 21, 22, 23, 26, 30, 33, 35]
NON_PERFECT_SQ = RADICAND_POOL
VARS           = ['x', 'y', 'z']

ROOT_NAMES = {
    2: "Square root  (√  )", 3: "Cube root    (∛  )", 4: "Fourth root  (∜  )",
    5: "Fifth root",  6: "Sixth root",  7: "Seventh root",
    8: "Eighth root", 9: "Ninth root", 10: "Tenth root",
}

def root_label(n):
    return ROOT_NAMES.get(n, f"{n}th root")

# ═══════════════════════════════════════════════════════════════
#  Scaling helpers
# ═══════════════════════════════════════════════════════════════

def _k_max(base_max, index):
    caps = {2: base_max, 3: min(base_max, 5), 4: min(base_max, 4),
            5: 3, 6: 2, 7: 2, 8: 2, 9: 2, 10: 2}
    return caps.get(index, 2)

def _vp_max(base_max, index):
    return max(1, base_max - max(0, index - 2))

def _rem_pool(diff_pool, index):
    out = [r for r in diff_pool if not is_perfect_power(r, index)]
    return out if out else [2]

# ═══════════════════════════════════════════════════════════════
#  Math utilities
# ═══════════════════════════════════════════════════════════════

def extract_root(n, index=2):
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

def tex(expr):           return f"$${expr}$$"
def sqrt_tex(r, idx=2):  return f"\\sqrt{{{r}}}" if idx == 2 else f"\\sqrt[{idx}]{{{r}}}"
def sqrt_plain(r, idx=2):return f"sqrt({r})"    if idx == 2 else f"root[{idx}]({r})"

def var_tex(name, power):
    if power == 0: return ""
    if power == 1: return name
    return f"{name}^{{{power}}}"

def var_plain(name, power):
    if power == 0: return ""
    if power == 1: return name
    return f"{name}^{power}"

def rat_exp_tex(name, frac):
    if frac == 0:             return ""
    if frac == 1:             return name
    if frac.denominator == 1: return f"{name}^{{{frac.numerator}}}"
    return f"{name}^{{\\frac{{{frac.numerator}}}{{{frac.denominator}}}}}"

def rat_exp_plain(name, frac):
    if frac == 0:             return ""
    if frac == 1:             return name
    if frac.denominator == 1: return f"{name}^{frac.numerator}"
    return f"{name}^({frac.numerator}/{frac.denominator})"

def build_radicand(num_coeff, var_powers, mode="tex"):
    vf = var_tex if mode == "tex" else var_plain
    parts = []
    if num_coeff not in (0, 1): parts.append(str(num_coeff))
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
#  Difficulty parameters
# ═══════════════════════════════════════════════════════════════

DIFF_PARAMS = {
    "easy":   {"coeff_max": 4, "var_pow_max": 2, "rem_pool": RADICAND_POOL[:5]},
    "medium": {"coeff_max": 6, "var_pow_max": 3, "rem_pool": RADICAND_POOL[:10]},
    "hard":   {"coeff_max": 8, "var_pow_max": 4, "rem_pool": RADICAND_POOL},
}

DIFF_ROOT_DEFAULTS = {"easy": (2, 2), "medium": (2, 3), "hard": (2, 4)}

def _pick_index(root_range):
    return random.randint(root_range[0], root_range[1])

# ═══════════════════════════════════════════════════════════════
#  Problem generators
# ═══════════════════════════════════════════════════════════════

def gen_simplify(num_vars, difficulty, root_range=(2, 2)):
    p = DIFF_PARAMS[difficulty]; index = _pick_index(root_range)
    K = random.randint(2, _k_max(p["coeff_max"], index))
    pool = _rem_pool(p["rem_pool"], index); R = random.choice(pool)
    var_names = VARS[:num_vars]
    outer_var_pows, inner_var_pows, total_var_pows = [], [], []
    vp_max = _vp_max(p["var_pow_max"], index)
    for v in var_names:
        out_p = random.randint(1, vp_max); in_p = random.randint(0, index - 1)
        outer_var_pows.append((v, out_p)); inner_var_pows.append((v, in_p))
        total_var_pows.append((v, index * out_p + in_p))
    radicand_coeff = (K ** index) * R
    outer_vars_nonzero = [(v, pw) for v, pw in outer_var_pows if pw > 0]
    inner_vars_nonzero = [(v, pw) for v, pw in inner_var_pows if pw > 0]
    return {
        "type": "simplify", "index": index,
        "problem_rad_tex":   build_radicand(radicand_coeff, total_var_pows, "tex"),
        "problem_rad_plain": build_radicand(radicand_coeff, total_var_pows, "plain"),
        "K": K, "outer_vars": outer_vars_nonzero, "R": R, "inner_vars": inner_vars_nonzero,
        "simplified_rad_tex":
            build_radicand(R, inner_vars_nonzero, "tex")   if inner_vars_nonzero or R != 1 else None,
        "simplified_rad_plain":
            build_radicand(R, inner_vars_nonzero, "plain") if inner_vars_nonzero or R != 1 else None,
    }

def gen_rewrite(num_vars, difficulty, root_range=(2, 2)):
    p = DIFF_PARAMS[difficulty]; index = _pick_index(root_range)
    direction = random.choice(["rad_to_exp", "exp_to_rad"])
    n_vars = max(1, num_vars); var_names = VARS[:n_vars]
    vp_max = _vp_max(p["var_pow_max"], index)
    var_pows = []
    for v in var_names:
        pw = random.randint(1, index * vp_max)
        while pw % index == 0: pw = random.randint(1, index * vp_max)
        var_pows.append((v, pw))
    coeff = random.choice([1, 1, 2, 3]) if difficulty != "easy" else 1

    def build_rad_form(mode):
        vf = var_tex if mode == "tex" else var_plain
        sf = sqrt_tex if mode == "tex" else sqrt_plain
        inside_parts = []
        if coeff > 1:
            inside_parts.append(f"{coeff}^{{{index}}}" if mode == "tex" else f"{coeff}^{index}")
        for v, pw in var_pows: inside_parts.append(vf(v, pw))
        return sf("".join(inside_parts), index)

    def build_exp_form(mode):
        ff = frac_tex if mode == "tex" else frac_plain
        parts = []
        if coeff > 1: parts.append(str(coeff))
        for v, pw in var_pows:
            exp_str = ff(pw, index)
            parts.append(f"{v}^{{{exp_str}}}" if mode == "tex" else f"{v}^({exp_str})")
        return " \\cdot ".join(parts) if mode == "tex" else " * ".join(parts)

    return {
        "type": "rewrite", "direction": direction, "index": index, "coeff": coeff, "var_pows": var_pows,
        "radical_tex": build_rad_form("tex"), "radical_plain": build_rad_form("plain"),
        "exponent_tex": build_exp_form("tex"), "exponent_plain": build_exp_form("plain"),
    }

def gen_multiply(num_vars, difficulty, root_range=(2, 2)):
    p = DIFF_PARAMS[difficulty]; index = _pick_index(root_range)
    var_names = VARS[:num_vars]; pool = _rem_pool(p["rem_pool"], index)
    vp_max = _vp_max(p["var_pow_max"], index); K_max = _k_max(p["coeff_max"], index)

    def rand_factor():
        coeff = random.randint(1, max(1, K_max // 2)); rem = random.choice(pool)
        vpows = [(v, random.randint(0, vp_max)) for v in var_names]
        return coeff, rem, vpows

    c1, r1, vp1 = rand_factor(); c2, r2, vp2 = rand_factor()
    combined_num = r1 * r2
    combined_var_pows = [(v, vp1[i][1] + vp2[i][1]) for i, v in enumerate(var_names)]
    out_n, in_n = extract_root(combined_num, index)
    final_coeff = c1 * c2 * out_n
    final_outer_vars, final_inner_vars = [], []
    for v, total_pw in combined_var_pows:
        out_p = total_pw // index; in_p = total_pw % index
        if out_p: final_outer_vars.append((v, out_p))
        if in_p:  final_inner_vars.append((v, in_p))

    def single_rad_str(coeff, rem, vpows, mode):
        num_part = (coeff ** index) * rem
        rad_str = build_radicand(num_part, vpows, mode)
        sf = sqrt_tex if mode == "tex" else sqrt_plain
        return sf(rad_str, index)

    fin_inner_tex   = build_radicand(in_n, final_inner_vars, "tex")   if in_n != 1 or final_inner_vars else None
    fin_inner_plain = build_radicand(in_n, final_inner_vars, "plain") if in_n != 1 or final_inner_vars else None

    return {
        "type": "multiply", "index": index,
        "fac1_tex": single_rad_str(c1, r1, vp1, "tex"), "fac2_tex": single_rad_str(c2, r2, vp2, "tex"),
        "fac1_plain": single_rad_str(c1, r1, vp1, "plain"), "fac2_plain": single_rad_str(c2, r2, vp2, "plain"),
        "combined_coeff_out": c1 * c2,
        "combined_rad_tex": build_radicand(combined_num, combined_var_pows, "tex"),
        "combined_rad_plain": build_radicand(combined_num, combined_var_pows, "plain"),
        "answer_tex": build_expression(final_coeff, final_outer_vars, fin_inner_tex,   index, "tex"),
        "answer_plain": build_expression(final_coeff, final_outer_vars, fin_inner_plain, index, "plain"),
    }

def gen_divide(num_vars, difficulty, root_range=(2, 2)):
    p = DIFF_PARAMS[difficulty]; index = _pick_index(root_range)
    var_names = VARS[:num_vars]; pool = _rem_pool(p["rem_pool"], index)
    vp_max = _vp_max(p["var_pow_max"], index); K_max = _k_max(p["coeff_max"], index)
    c_den = random.randint(1, max(1, K_max // 2)); r_den = random.choice(pool)
    vp_den = [(v, random.randint(0, max(0, vp_max - 1))) for v in var_names]
    extra_c = random.randint(2, max(2, K_max // 2))
    extra_r = 1 if random.random() < 0.5 else r_den
    vp_extra = [(v, random.randint(0, vp_max)) for v in var_names]
    c_num = c_den * extra_c; r_num = r_den * extra_r
    vp_num = [(v, vp_den[i][1] + vp_extra[i][1]) for i, v in enumerate(var_names)]

    def rad_str(coeff, rem, vpows, mode):
        num_part = (coeff ** index) * rem
        rad = build_radicand(num_part, vpows, mode)
        sf = sqrt_tex if mode == "tex" else sqrt_plain
        return sf(rad, index)

    num_tex, den_tex   = rad_str(c_num, r_num, vp_num, "tex"),   rad_str(c_den, r_den, vp_den, "tex")
    num_plain, den_plain = rad_str(c_num, r_num, vp_num, "plain"), rad_str(c_den, r_den, vp_den, "plain")
    quot_num = r_num * (c_num ** index); quot_den = r_den * (c_den ** index)
    g = math.gcd(quot_num, quot_den); quot_num //= g; quot_den //= g
    combined_var_pows = [(v, vp_num[i][1] - vp_den[i][1]) for i, v in enumerate(var_names)]
    out_n, in_n = extract_root(quot_num, index); out_d, in_d = extract_root(quot_den, index)
    final_outer_vars, final_inner_vars = [], []
    for v, pw in combined_var_pows:
        out_p = pw // index; in_p = pw % index
        if out_p: final_outer_vars.append((v, out_p))
        if in_p:  final_inner_vars.append((v, in_p))

    def combined_frac_str(qn, qd, vpows, mode):
        vf = var_tex if mode == "tex" else var_plain
        num_parts = [str(qn)] if qn != 1 else []
        for v, pw in vpows:
            vt = vf(v, pw)
            if vt: num_parts.append(vt)
        num_str = "".join(num_parts) or "1"
        inside = (f"\\frac{{{num_str}}}{{{qd}}}" if qd != 1 and mode == "tex"
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
        ans_tex = f"\\frac{{{num_ans}}}{{{den_str}}}"
        num_p   = build_expression(out_n, final_outer_vars, fin_inner_plain, index, "plain")
        den_p   = str(out_d) if in_d == 1 else build_expression(
                      out_d, [], build_radicand(in_d, [], "plain"), index, "plain")
        ans_plain = f"({num_p})/({den_p})"

    return {
        "type": "divide", "index": index,
        "num_tex": num_tex, "den_tex": den_tex,
        "num_plain": num_plain, "den_plain": den_plain,
        "combined_str_tex":   combined_frac_str(quot_num, quot_den, combined_var_pows, "tex"),
        "combined_str_plain": combined_frac_str(quot_num, quot_den, combined_var_pows, "plain"),
        "answer_tex": ans_tex, "answer_plain": ans_plain,
    }

def gen_simplify_rat_exp(num_vars, difficulty, root_range=(2, 2)):
    p = DIFF_PARAMS[difficulty]; q = _pick_index(root_range)
    K_max = _k_max(p["coeff_max"], q); vp_max = _vp_max(p["var_pow_max"], q)
    candidates = [n for n in range(1, q + 2) if math.gcd(n, q) == 1 and n != q]
    pw_num = random.choice(candidates[:4]); outer_frac = Fraction(pw_num, q)
    K = random.randint(2, K_max); base_coeff = K ** q; ans_coeff = K ** pw_num
    var_names = VARS[:num_vars]; var_pows_inner = []
    for v in var_names:
        a = random.randint(1, q * vp_max); var_pows_inner.append((v, a))
    ans_var_fracs = [(v, Fraction(a * pw_num, q)) for v, a in var_pows_inner]

    def base_str(mode):
        vf = var_tex if mode == "tex" else var_plain
        parts = [str(base_coeff)] if base_coeff != 1 else []
        for v, a in var_pows_inner: parts.append(vf(v, a))
        return "".join(parts) or "1"

    def outer_exp_str(mode):
        ff = frac_tex if mode == "tex" else frac_plain
        return ff(pw_num, q)

    def problem_str(mode):
        b = base_str(mode); exp = outer_exp_str(mode)
        return (f"\\left({b}\\right)^{{{exp}}}" if mode == "tex" else f"({b})^({pw_num}/{q})")

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
            parts.append(f"{v}^{{{ff(a * pw_num, q)}}}" if mode == "tex" else f"{v}^({a * pw_num}/{q})")
        return (" \\cdot ".join(parts) if mode == "tex" else " * ".join(parts))

    return {
        "type": "simplify_rat_exp", "q": q, "pw_num": pw_num, "K": K,
        "ans_coeff": ans_coeff, "base_coeff": base_coeff,
        "var_pows_inner": var_pows_inner, "ans_var_fracs": ans_var_fracs,
        "problem_tex": problem_str("tex"), "problem_plain": problem_str("plain"),
        "answer_tex": answer_str("tex"), "answer_plain": answer_str("plain"),
        "distribute_tex": distribute_step("tex"), "distribute_plain": distribute_step("plain"),
    }

def gen_power_to_power(num_vars, difficulty, root_range=(2, 2)):
    p = DIFF_PARAMS[difficulty]
    outer_choices = [Fraction(1,2),Fraction(1,3),Fraction(2,3),Fraction(3,2),Fraction(3,4),
                     Fraction(4,3),Fraction(2,1),Fraction(3,1),Fraction(4,1),Fraction(6,1)]
    if difficulty == "easy":
        outer_choices = [Fraction(2,1),Fraction(3,1),Fraction(1,2),Fraction(1,3)]
    outer = random.choice(outer_choices)
    include_coeff = difficulty != "easy" and random.random() < 0.6
    if include_coeff:
        K_c = random.randint(2, p["coeff_max"] // 2 + 1)
        c_base = K_c ** outer.denominator; c_ans = K_c ** outer.numerator
    else:
        c_base, c_ans = 1, 1
    n_vars = max(1, num_vars); var_names = VARS[:n_vars]
    inner_denoms = [2, 3, 4, 6]; var_inner_fracs, ans_var_fracs = [], []
    for v in var_names:
        denom = random.choice(inner_denoms); numer = random.randint(1, denom * p["var_pow_max"])
        while numer % denom == 0 and difficulty == "easy":
            numer = random.randint(1, denom * p["var_pow_max"])
        inner_frac = Fraction(numer, denom); result_frac = inner_frac * outer
        var_inner_fracs.append((v, inner_frac)); ans_var_fracs.append((v, result_frac))

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
        inner = inner_expr(mode); exp = outer_exp_str(mode)
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
        "type": "power_to_power", "outer": outer, "c_base": c_base, "c_ans": c_ans,
        "var_inner_fracs": var_inner_fracs, "ans_var_fracs": ans_var_fracs,
        "problem_tex": problem_str("tex"), "problem_plain": problem_str("plain"),
        "answer_tex": answer_str("tex"), "answer_plain": answer_str("plain"),
        "mult_step_tex": mult_step("tex"), "mult_step_plain": mult_step("plain"),
    }

# ═══════════════════════════════════════════════════════════════
#  Problem → text lines
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
                f"{K}^{{{q} \\cdot \\frac{{{pw_num}}}{{{q}}}}} = {K}^{{{pw_num}}} = {ans_c}"
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
        outer = prob["outer"]; ff = frac_tex if latex_mode else frac_plain
        rule = (wrap(f"\\left(x^{{a}}\\right)^{{b}} = x^{{a \\cdot b}}") if latex_mode
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
    return {2:"square",3:"cube",4:"fourth",5:"fifth",6:"sixth",7:"seventh",8:"eighth"}.get(n,f"{n}th")

# ═══════════════════════════════════════════════════════════════
#  Registry & worksheet builder
# ═══════════════════════════════════════════════════════════════

TYPE_GENERATORS = {
    "simplify": gen_simplify, "rewrite": gen_rewrite, "multiply": gen_multiply,
    "divide": gen_divide, "simplify_rat_exp": gen_simplify_rat_exp, "power_to_power": gen_power_to_power,
}
TYPE_LABELS = {
    "simplify": "Simplifying Radicals", "rewrite": "Rewriting Radicals",
    "multiply": "Multiplying Radicals", "divide": "Dividing Radicals",
    "simplify_rat_exp": "Simplifying with Rational Exponents", "power_to_power": "Power to a Power",
}
ROOT_RANGE_TYPES = {"simplify", "rewrite", "multiply", "divide", "simplify_rat_exp"}

def _distribute(total, n_buckets):
    base, extra = divmod(total, n_buckets)
    return [base + (1 if i < extra else 0) for i in range(n_buckets)]

def generate_worksheet(num_problems=10, problem_types=None, num_vars=1,
                       difficulty="medium", show_solutions=True,
                       title=None, latex_mode=False, root_range=None):
    if problem_types is None: problem_types = ["simplify"]
    if root_range is None:    root_range = DIFF_ROOT_DEFAULTS[difficulty]
    lines = []; sep = "=" * 68; sec_sep = "-" * 68
    heading = title or "RADICAL EXPRESSIONS — PRACTICE WORKSHEET"
    var_label = {0:"No Variables",1:"1 Variable (x)",2:"2 Variables (x, y)",3:"3 Variables (x, y, z)"}[num_vars]
    types_str = ", ".join(TYPE_LABELS[t] for t in problem_types)
    uses_root_range = any(t in ROOT_RANGE_TYPES for t in problem_types)
    root_info = (f"Root range: index {root_range[0]}–{root_range[1]}" if uses_root_range else "")
    lines += [sep, heading, sep,
              f"Topics:     {types_str}",
              f"Variables:  {var_label}",
              f"Difficulty: {difficulty.capitalize()}   |   Problems: {num_problems}"]
    if root_info: lines.append(root_info)
    lines += ["", "Instructions: Simplify each expression completely.",
              "  • Assume all variables represent non-negative real numbers.",
              "  • Write all answers using positive exponents.", sep, ""]
    counts = _distribute(num_problems, len(problem_types))
    groups = []
    for ptype, count in zip(problem_types, counts):
        group_probs = [TYPE_GENERATORS[ptype](num_vars, difficulty, root_range=root_range) for _ in range(count)]
        groups.append((ptype, group_probs))
    global_num = 1
    for sec_idx, (ptype, group_probs) in enumerate(groups, 1):
        label = TYPE_LABELS[ptype]
        lines += [sec_sep, f"  SECTION {sec_idx} — {label.upper()}", sec_sep, ""]
        for prob in group_probs:
            lines += problem_lines(prob, global_num, latex_mode)
            global_num += 1
    if show_solutions:
        lines += ["", sep, "A N S W E R   K E Y", sep]
        key_num = 1
        for sec_idx, (ptype, group_probs) in enumerate(groups, 1):
            label = TYPE_LABELS[ptype]
            lines += ["", sec_sep, f"  SECTION {sec_idx} — {label.upper()}", sec_sep, ""]
            for prob in group_probs:
                lines += solution_lines(prob, key_num, latex_mode)
                key_num += 1
    lines += [sep, "End of Worksheet", sep]
    return lines

# ═══════════════════════════════════════════════════════════════
#  FastAPI app
# ═══════════════════════════════════════════════════════════════

app = FastAPI(title="Radical Expressions Worksheet Generator")

VALID_TYPES = list(TYPE_GENERATORS.keys())
VALID_DIFFICULTIES = ["easy", "medium", "hard"]

class WorksheetRequest(BaseModel):
    num_problems:   int          = 10
    problem_types:  List[str]    = ["simplify"]
    num_vars:       int          = 1
    difficulty:     str          = "medium"
    show_solutions: bool         = True
    title:          Optional[str]= None
    latex_mode:     bool         = False
    root_min:       int          = 2
    root_max:       int          = 3

@app.post("/generate", response_class=PlainTextResponse)
def generate(req: WorksheetRequest):
    # Validate
    for t in req.problem_types:
        if t not in VALID_TYPES:
            return PlainTextResponse(f"Invalid problem type: '{t}'. Valid: {VALID_TYPES}", status_code=400)
    if req.difficulty not in VALID_DIFFICULTIES:
        return PlainTextResponse(f"Invalid difficulty. Choose: {VALID_DIFFICULTIES}", status_code=400)
    if not (1 <= req.num_problems <= 60):
        return PlainTextResponse("num_problems must be between 1 and 60.", status_code=400)
    if not (2 <= req.root_min <= 10) or not (req.root_min <= req.root_max <= 10):
        return PlainTextResponse("root_min must be 2–10 and root_max >= root_min.", status_code=400)
    if not (0 <= req.num_vars <= 3):
        return PlainTextResponse("num_vars must be 0, 1, 2, or 3.", status_code=400)

    lines = generate_worksheet(
        num_problems   = req.num_problems,
        problem_types  = req.problem_types,
        num_vars       = req.num_vars,
        difficulty     = req.difficulty,
        show_solutions = req.show_solutions,
        title          = req.title,
        latex_mode     = req.latex_mode,
        root_range     = (req.root_min, req.root_max),
    )
    return "\n".join(lines)


@app.get("/", response_class=HTMLResponse)
def ui():
    return """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>Radical Expressions Worksheet Generator</title>
  <style>
    *{box-sizing:border-box;margin:0;padding:0}
    body{font-family:'Segoe UI',sans-serif;background:#f0f4f8;color:#1a202c;min-height:100vh}
    header{background:linear-gradient(135deg,#4f46e5,#7c3aed);color:white;padding:2rem;text-align:center}
    header h1{font-size:1.8rem;margin-bottom:.4rem}
    header p{opacity:.85;font-size:.95rem}
    main{max-width:860px;margin:2rem auto;padding:0 1rem}
    .card{background:white;border-radius:12px;padding:1.8rem;margin-bottom:1.5rem;box-shadow:0 2px 8px rgba(0,0,0,.08)}
    .card h2{font-size:1rem;font-weight:700;color:#4f46e5;text-transform:uppercase;letter-spacing:.05em;margin-bottom:1.2rem;border-bottom:2px solid #e0e7ff;padding-bottom:.5rem}
    .grid{display:grid;grid-template-columns:1fr 1fr;gap:1rem}
    @media(max-width:560px){.grid{grid-template-columns:1fr}}
    label{display:block;font-size:.85rem;font-weight:600;color:#374151;margin-bottom:.35rem}
    select,input[type=number],input[type=text]{width:100%;padding:.55rem .75rem;border:1.5px solid #d1d5db;border-radius:8px;font-size:.9rem;transition:border-color .2s}
    select:focus,input:focus{outline:none;border-color:#4f46e5;box-shadow:0 0 0 3px rgba(79,70,229,.15)}
    .types-grid{display:grid;grid-template-columns:1fr 1fr;gap:.5rem}
    .type-option{display:flex;align-items:flex-start;gap:.6rem;padding:.6rem .8rem;border:1.5px solid #e5e7eb;border-radius:8px;cursor:pointer;transition:all .15s}
    .type-option:hover{border-color:#a5b4fc;background:#f5f3ff}
    .type-option input[type=checkbox]{margin-top:.15rem;accent-color:#4f46e5;width:15px;height:15px}
    .type-option .label{font-size:.83rem;font-weight:600;color:#374151}
    .type-option .sub{font-size:.75rem;color:#9ca3af;margin-top:.1rem}
    .toggle-row{display:flex;align-items:center;gap:.75rem;margin-top:.2rem}
    .toggle-row label{margin:0;font-weight:500;color:#374151;font-size:.9rem}
    .toggle{position:relative;width:44px;height:24px;flex-shrink:0}
    .toggle input{opacity:0;width:0;height:0}
    .slider{position:absolute;inset:0;background:#d1d5db;border-radius:34px;cursor:pointer;transition:.3s}
    .slider:before{content:"";position:absolute;height:18px;width:18px;left:3px;bottom:3px;background:white;border-radius:50%;transition:.3s}
    input:checked+.slider{background:#4f46e5}
    input:checked+.slider:before{transform:translateX(20px)}
    .btn{width:100%;padding:.85rem;background:linear-gradient(135deg,#4f46e5,#7c3aed);color:white;border:none;border-radius:10px;font-size:1rem;font-weight:700;cursor:pointer;transition:opacity .2s;margin-top:.5rem}
    .btn:hover{opacity:.9}
    .btn:active{opacity:.8}
    .btn:disabled{opacity:.5;cursor:default}
    #output-section{display:none}
    #output-box{background:#1e1e2e;color:#cdd6f4;font-family:'Courier New',monospace;font-size:.82rem;padding:1.5rem;border-radius:10px;white-space:pre;overflow-x:auto;max-height:520px;overflow-y:auto;line-height:1.6}
    .actions{display:flex;gap:.75rem;margin-top:1rem}
    .btn-secondary{flex:1;padding:.7rem;background:#4f46e5;color:white;border:none;border-radius:8px;font-size:.88rem;font-weight:600;cursor:pointer;transition:opacity .2s}
    .btn-secondary:hover{opacity:.85}
    .btn-outline{flex:1;padding:.7rem;background:white;color:#4f46e5;border:2px solid #4f46e5;border-radius:8px;font-size:.88rem;font-weight:600;cursor:pointer;transition:all .2s}
    .btn-outline:hover{background:#f5f3ff}
    .spinner{display:none;border:3px solid #e0e7ff;border-top:3px solid #4f46e5;border-radius:50%;width:22px;height:22px;animation:spin .7s linear infinite;margin:0 auto}
    @keyframes spin{to{transform:rotate(360deg)}}
    .note{font-size:.78rem;color:#6b7280;margin-top:.4rem}
  </style>
</head>
<body>
<header>
  <h1>📐 Radical Expressions Worksheet Generator</h1>
  <p>Generate customised practice worksheets with full answer keys</p>
</header>
<main>

  <div class="card">
    <h2>Problem Types</h2>
    <div class="types-grid">
      <label class="type-option"><input type="checkbox" name="ptype" value="simplify" checked>
        <div><div class="label">Simplify Radicals</div><div class="sub">e.g. √(72x⁵y³)</div></div></label>
      <label class="type-option"><input type="checkbox" name="ptype" value="rewrite">
        <div><div class="label">Rewrite Radicals</div><div class="sub">Radical ↔ rational exponent</div></div></label>
      <label class="type-option"><input type="checkbox" name="ptype" value="multiply">
        <div><div class="label">Multiply Radicals</div><div class="sub">e.g. √(6x) · √(2x³)</div></div></label>
      <label class="type-option"><input type="checkbox" name="ptype" value="divide">
        <div><div class="label">Divide Radicals</div><div class="sub">e.g. √(48x⁵) / √(3x)</div></div></label>
      <label class="type-option"><input type="checkbox" name="ptype" value="simplify_rat_exp">
        <div><div class="label">Rational Exponents</div><div class="sub">e.g. (8x⁶)^(2/3) → 4x⁴</div></div></label>
      <label class="type-option"><input type="checkbox" name="ptype" value="power_to_power">
        <div><div class="label">Power to a Power</div><div class="sub">e.g. (x^(2/3))^(3/4)</div></div></label>
    </div>
  </div>

  <div class="card">
    <h2>Settings</h2>
    <div class="grid">
      <div>
        <label for="num_problems">Number of Problems</label>
        <input type="number" id="num_problems" value="10" min="1" max="60"/>
      </div>
      <div>
        <label for="difficulty">Difficulty</label>
        <select id="difficulty">
          <option value="easy">Easy — small numbers, powers ≤ 2</option>
          <option value="medium" selected>Medium — moderate numbers, powers ≤ 3</option>
          <option value="hard">Hard — larger numbers, powers ≤ 4</option>
        </select>
      </div>
      <div>
        <label for="num_vars">Variables</label>
        <select id="num_vars">
          <option value="0">None (numbers only)</option>
          <option value="1" selected>1 variable (x)</option>
          <option value="2">2 variables (x, y)</option>
          <option value="3">3 variables (x, y, z)</option>
        </select>
      </div>
      <div>
        <label>Root Index Range</label>
        <div style="display:flex;gap:.5rem;align-items:center">
          <input type="number" id="root_min" value="2" min="2" max="10" style="width:80px"/>
          <span style="color:#9ca3af;font-size:.85rem">to</span>
          <input type="number" id="root_max" value="3" min="2" max="10" style="width:80px"/>
        </div>
        <p class="note">Min and max root index (2=square, 3=cube, etc.)</p>
      </div>
      <div>
        <label for="title">Custom Title (optional)</label>
        <input type="text" id="title" placeholder="Leave blank for default"/>
      </div>
      <div style="display:flex;flex-direction:column;gap:.75rem;padding-top:.3rem">
        <div class="toggle-row">
          <label class="toggle"><input type="checkbox" id="show_solutions" checked><span class="slider"></span></label>
          <label for="show_solutions">Include answer key</label>
        </div>
        <div class="toggle-row">
          <label class="toggle"><input type="checkbox" id="latex_mode"><span class="slider"></span></label>
          <label for="latex_mode">LaTeX / Google Docs mode</label>
        </div>
      </div>
    </div>
  </div>

  <div class="card">
    <button class="btn" id="generate-btn" onclick="generateWorksheet()">Generate Worksheet</button>
    <div class="spinner" id="spinner" style="margin-top:1rem"></div>
  </div>

  <div class="card" id="output-section">
    <h2>Your Worksheet</h2>
    <div id="output-box"></div>
    <div class="actions">
      <button class="btn-secondary" onclick="copyWorksheet()">📋 Copy to Clipboard</button>
      <button class="btn-outline" onclick="downloadWorksheet()">💾 Download .txt</button>
    </div>
  </div>

</main>
<script>
  let lastOutput = "";

  async function generateWorksheet() {
    const ptypes = [...document.querySelectorAll('input[name="ptype"]:checked')].map(el => el.value);
    if (ptypes.length === 0) { alert("Please select at least one problem type."); return; }

    const btn = document.getElementById("generate-btn");
    const spinner = document.getElementById("spinner");
    btn.disabled = true; spinner.style.display = "block";

    const payload = {
      num_problems:   parseInt(document.getElementById("num_problems").value),
      problem_types:  ptypes,
      num_vars:       parseInt(document.getElementById("num_vars").value),
      difficulty:     document.getElementById("difficulty").value,
      show_solutions: document.getElementById("show_solutions").checked,
      title:          document.getElementById("title").value || null,
      latex_mode:     document.getElementById("latex_mode").checked,
      root_min:       parseInt(document.getElementById("root_min").value),
      root_max:       parseInt(document.getElementById("root_max").value),
    };

    try {
      const res = await fetch("/generate", {
        method: "POST", headers: {"Content-Type":"application/json"}, body: JSON.stringify(payload)
      });
      const text = await res.text();
      lastOutput = text;
      document.getElementById("output-box").textContent = text;
      document.getElementById("output-section").style.display = "block";
      document.getElementById("output-section").scrollIntoView({behavior:"smooth"});
    } catch(e) {
      alert("Error generating worksheet: " + e.message);
    } finally {
      btn.disabled = false; spinner.style.display = "none";
    }
  }

  function copyWorksheet() {
    navigator.clipboard.writeText(lastOutput).then(() => alert("Copied to clipboard!"));
  }

  function downloadWorksheet() {
    const blob = new Blob([lastOutput], {type:"text/plain"});
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = "radical_worksheet.txt";
    a.click();
  }
</script>
</body>
</html>"""


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
