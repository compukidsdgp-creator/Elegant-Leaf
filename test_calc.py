"""
Tests for the profit arithmetic.

The ones worth having are the cases where a plausible-looking implementation
gets it wrong: GST leaking into profit, a GST-inclusive cost taken at face
value, and float rounding drifting off the invoice by a paisa.

    python test_calc.py
"""
from decimal import Decimal

from calc import Lot, compute, inr, money


def check(label, got, want):
    got, want = money(got), money(want)
    status = "ok  " if got == want else "FAIL"
    print(f"  {status} {label:<44} got {got:>12}  want {want:>12}")
    return got == want


def test_plain_lot():
    """200 packs at ₹450, 10% off, 2.5+2.5% GST, costing ₹380 each."""
    print("\nA straightforward lot")
    r = compute(Lot.of(rate=450, qty=200, discount_pct=10,
                       cgst_pct=2.5, sgst_pct=2.5, cost_per_unit=380))
    ok = [
        check("gross", r.gross, "90000.00"),
        check("discount", r.discount_amount, "9000.00"),
        check("taxable value", r.taxable_value, "81000.00"),
        check("CGST at 2.5%", r.cgst_amount, "2025.00"),
        check("SGST at 2.5%", r.sgst_amount, "2025.00"),
        check("invoice total", r.invoice_total, "85050.00"),
        check("total cost", r.total_cost, "76000.00"),
        check("net profit", r.net_profit, "5000.00"),
        check("profit per unit", r.profit_per_unit, "25.00"),
        check("margin %", r.margin_pct, "6.17"),
        check("markup %", r.markup_pct, "6.58"),
    ]
    return all(ok)


def test_gst_never_enters_profit():
    """Raising GST changes the invoice, never the profit.

    This is the single most likely thing to be got wrong, so it gets a test of
    its own: run the same lot at 5% and at 18% and assert profit is identical.
    """
    print("\nGST does not move the profit line")
    base = dict(rate=450, qty=200, discount_pct=10, cost_per_unit=380)
    low = compute(Lot.of(cgst_pct=2.5, sgst_pct=2.5, **base))
    high = compute(Lot.of(cgst_pct=9, sgst_pct=9, **base))
    ok = [
        check("profit at 5% GST", low.net_profit, "5000.00"),
        check("profit at 18% GST", high.net_profit, "5000.00"),
        check("invoice total moves at 18%", high.invoice_total, "95580.00"),
    ]
    return all(ok)


def test_gst_inclusive_cost():
    """A cost of ₹399 including 5% GST is really ₹380 of cost."""
    print("\nGST-inclusive cost is stripped back")
    r = compute(Lot.of(rate=450, qty=200, discount_pct=10,
                       cgst_pct=2.5, sgst_pct=2.5, cost_per_unit=399,
                       cost_includes_gst=True, purchase_gst_pct=5))
    ok = [
        check("cost per unit ex-GST", r.cost_ex_gst_per_unit, "380.00"),
        check("net profit", r.net_profit, "5000.00"),
        check("input credit claimable", r.input_gst_credit, "3800.00"),
    ]
    return all(ok)


def test_no_input_credit():
    """Without input credit, the GST paid on purchase is a genuine cost."""
    print("\nComposition scheme: GST paid becomes a cost")
    r = compute(Lot.of(rate=450, qty=200, discount_pct=10,
                       cgst_pct=2.5, sgst_pct=2.5, cost_per_unit=380,
                       purchase_gst_pct=5, gst_is_cost=True))
    ok = [
        check("cost basis per unit", r.cost_ex_gst_per_unit, "399.00"),
        check("net profit falls", r.net_profit, "1200.00"),
        check("no credit set off", r.net_gst_payable, "4050.00"),
    ]
    return all(ok)


def test_breakeven():
    """Where the discount stops paying."""
    print("\nBreakeven discount")
    r = compute(Lot.of(rate=450, qty=200, discount_pct=10,
                       cgst_pct=2.5, sgst_pct=2.5, cost_per_unit=380))
    ok = [
        check("breakeven discount %", r.breakeven_discount_pct, "15.56"),
        check("headroom left", r.discount_headroom_pct, "5.56"),
        check("effective rate", r.effective_rate, "405.00"),
    ]
    # At the breakeven discount the profit should be ~zero.
    at_be = compute(Lot.of(rate=450, qty=200,
                           discount_pct=r.breakeven_discount_pct,
                           cgst_pct=2.5, sgst_pct=2.5, cost_per_unit=380))
    near_zero = abs(at_be.profit_per_unit) <= Decimal("0.05")
    print(f"  {'ok  ' if near_zero else 'FAIL'} "
          f"{'profit at breakeven discount ≈ 0':<44} "
          f"got {at_be.profit_per_unit:>12}")
    return all(ok) and near_zero


def test_loss_is_reported():
    """Selling below cost must come back negative, not clamped at zero."""
    print("\nA loss stays a loss")
    r = compute(Lot.of(rate=450, qty=100, discount_pct=30,
                       cgst_pct=2.5, sgst_pct=2.5, cost_per_unit=380))
    ok = [
        check("net profit", r.net_profit, "-6500.00"),
        check("per unit", r.profit_per_unit, "-65.00"),
    ]
    print(f"  {'ok  ' if r.is_loss else 'FAIL'} {'flagged as a loss':<44}")
    return all(ok) and r.is_loss


def test_edge_cases():
    """Zero quantity and zero rate must not raise."""
    print("\nEdges")
    z = compute(Lot.of(rate=0, qty=0, discount_pct=0, cgst_pct=0,
                       sgst_pct=0, cost_per_unit=0))
    full = compute(Lot.of(rate=450, qty=10, discount_pct=100, cgst_pct=2.5,
                          sgst_pct=2.5, cost_per_unit=380))
    ok = [
        check("zero lot profit", z.net_profit, "0.00"),
        check("zero lot per unit", z.profit_per_unit, "0.00"),
        check("100% discount taxable", full.taxable_value, "0.00"),
        check("100% discount profit", full.net_profit, "-3800.00"),
    ]
    return all(ok)


def test_rounding_holds():
    """Awkward figures must still reconcile exactly.

    A float implementation drifts here. The parts must sum to the whole with
    no residue, because the buyer will add them up.
    """
    print("\nRounding reconciles")
    r = compute(Lot.of(rate="333.33", qty=7, discount_pct="7.5",
                       cgst_pct="2.5", sgst_pct="2.5", cost_per_unit="299.99"))
    ok = [
        check("taxable = gross - discount",
              r.taxable_value, r.gross - r.discount_amount),
        check("invoice = taxable + GST",
              r.invoice_total, r.taxable_value + r.total_gst),
        check("profit = taxable - cost",
              r.net_profit, r.taxable_value - r.total_cost),
    ]
    return all(ok)


def test_formatting():
    """Indian grouping, not Western."""
    print("\nNumber formatting")
    cases = [
        ("1234567.891", "₹12,34,567.89"),
        ("100000", "₹1,00,000.00"),
        ("999", "₹999.00"),
        ("-4500.5", "-₹4,500.50"),
        ("12345678.9", "₹1,23,45,678.90"),
    ]
    ok = True
    for raw, want in cases:
        got = inr(raw)
        good = got == want
        ok = ok and good
        print(f"  {'ok  ' if good else 'FAIL'} {raw:<44} got {got:>16}  want {want}")
    return ok


if __name__ == "__main__":
    tests = [test_plain_lot, test_gst_never_enters_profit, test_gst_inclusive_cost,
             test_no_input_credit, test_breakeven, test_loss_is_reported,
             test_edge_cases, test_rounding_holds, test_formatting]
    results = [t() for t in tests]
    passed, total = sum(results), len(results)
    print(f"\n{'─' * 70}\n{passed}/{total} groups passed")
    raise SystemExit(0 if passed == total else 1)
