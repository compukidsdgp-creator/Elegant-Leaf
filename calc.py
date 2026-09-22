"""
Profit arithmetic for a tea lot. No Streamlit here, so it can be tested.

The one decision worth understanding
------------------------------------
GST is not profit. You collect CGST and SGST from the buyer and remit both to
the government; you claim input credit on the GST you paid your supplier. The
money passes through the business without ever belonging to it.

So profit is computed on the **taxable value** — list price less discount —
against the **pre-GST cost**. The tax is shown in full because you need it on
the invoice and you need to know the cash going out, but it never enters the
profit line.

The exception is real and worth keeping: a dealer under the composition scheme,
or one not registered for GST, cannot claim input credit. For them the GST paid
on purchase is a genuine cost. `gst_is_cost` handles that case.

Money and rounding
------------------
Everything is `Decimal`, never `float`. At 0.1 + 0.2 a float is already wrong
in the third decimal, and an invoice that disagrees with the buyer's by a paisa
is an argument nobody needs.

Rounding follows Indian invoicing practice: the taxable value is rounded to two
decimals first, then tax is charged on that rounded figure — not on a longer
intermediate. Half-up, matching how GST portals round.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation

TWO = Decimal("0.01")
HUNDRED = Decimal("100")


def money(value) -> Decimal:
    """Coerce to a 2-decimal Decimal, half-up. Accepts str, int, float, Decimal."""
    try:
        d = value if isinstance(value, Decimal) else Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        d = Decimal("0")
    return d.quantize(TWO, rounding=ROUND_HALF_UP)


def pct(value) -> Decimal:
    """A percentage as an exact Decimal, unrounded (18.5% stays 18.5)."""
    try:
        return value if isinstance(value, Decimal) else Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return Decimal("0")


@dataclass(frozen=True)
class Lot:
    """One line of a sale, exactly as it would appear on the invoice."""
    rate: Decimal                      # list price per unit, before GST
    qty: Decimal
    discount_pct: Decimal
    cgst_pct: Decimal
    sgst_pct: Decimal
    cost_per_unit: Decimal
    cost_includes_gst: bool = False    # is the cost figure GST-inclusive?
    purchase_gst_pct: Decimal = Decimal("5")   # tea is 5% GST
    gst_is_cost: bool = False          # true only without input tax credit

    @staticmethod
    def of(rate, qty, discount_pct, cgst_pct, sgst_pct, cost_per_unit,
           cost_includes_gst=False, purchase_gst_pct=5, gst_is_cost=False) -> "Lot":
        return Lot(
            rate=money(rate), qty=pct(qty), discount_pct=pct(discount_pct),
            cgst_pct=pct(cgst_pct), sgst_pct=pct(sgst_pct),
            cost_per_unit=money(cost_per_unit),
            cost_includes_gst=bool(cost_includes_gst),
            purchase_gst_pct=pct(purchase_gst_pct),
            gst_is_cost=bool(gst_is_cost),
        )


@dataclass(frozen=True)
class Result:
    # What the buyer sees
    gross: Decimal
    discount_amount: Decimal
    taxable_value: Decimal
    cgst_amount: Decimal
    sgst_amount: Decimal
    total_gst: Decimal
    invoice_total: Decimal

    # What it cost you
    cost_ex_gst_per_unit: Decimal
    total_cost: Decimal
    input_gst_credit: Decimal

    # What you keep
    net_profit: Decimal
    profit_per_unit: Decimal
    margin_pct: Decimal              # profit as a share of taxable value
    markup_pct: Decimal              # profit as a share of cost
    net_gst_payable: Decimal         # output GST less input credit

    # Where the floor is
    effective_rate: Decimal          # per-unit price after discount
    breakeven_rate: Decimal          # per-unit price at which profit is zero
    breakeven_discount_pct: Decimal  # discount at which profit is zero
    discount_headroom_pct: Decimal   # how much discount is left before zero

    @property
    def is_loss(self) -> bool:
        return self.net_profit < 0

    def as_rows(self) -> list[tuple[str, Decimal]]:
        """The invoice, in the order it would be printed."""
        return [
            ("Gross value", self.gross),
            (f"Less discount", -self.discount_amount),
            ("Taxable value", self.taxable_value),
            ("CGST", self.cgst_amount),
            ("SGST", self.sgst_amount),
            ("Invoice total", self.invoice_total),
        ]


def compute(lot: Lot) -> Result:
    """Work the lot through to a profit figure."""
    qty = lot.qty if lot.qty > 0 else Decimal("0")

    gross = money(lot.rate * qty)
    discount_amount = money(gross * lot.discount_pct / HUNDRED)
    taxable_value = money(gross - discount_amount)

    # Tax is charged on the rounded taxable value, as the portals do it.
    cgst_amount = money(taxable_value * lot.cgst_pct / HUNDRED)
    sgst_amount = money(taxable_value * lot.sgst_pct / HUNDRED)
    total_gst = money(cgst_amount + sgst_amount)
    invoice_total = money(taxable_value + total_gst)

    # Strip GST out of the cost if the figure entered was tax-inclusive.
    if lot.cost_includes_gst and lot.purchase_gst_pct > 0:
        divisor = Decimal("1") + lot.purchase_gst_pct / HUNDRED
        cost_ex = money(lot.cost_per_unit / divisor)
    else:
        cost_ex = money(lot.cost_per_unit)

    input_gst_per_unit = money(cost_ex * lot.purchase_gst_pct / HUNDRED)
    input_gst_credit = money(input_gst_per_unit * qty)

    # Without input credit the GST paid to the supplier is a real cost.
    cost_basis_per_unit = money(cost_ex + input_gst_per_unit) if lot.gst_is_cost else cost_ex
    total_cost = money(cost_basis_per_unit * qty)

    net_profit = money(taxable_value - total_cost)
    profit_per_unit = money(net_profit / qty) if qty > 0 else Decimal("0.00")

    margin_pct = (money(net_profit / taxable_value * HUNDRED)
                  if taxable_value > 0 else Decimal("0.00"))
    markup_pct = (money(net_profit / total_cost * HUNDRED)
                  if total_cost > 0 else Decimal("0.00"))

    net_gst_payable = money(total_gst - (Decimal("0") if lot.gst_is_cost
                                         else input_gst_credit))

    effective_rate = money(taxable_value / qty) if qty > 0 else Decimal("0.00")
    breakeven_rate = cost_basis_per_unit

    if lot.rate > 0:
        breakeven_discount_pct = money(
            (Decimal("1") - breakeven_rate / lot.rate) * HUNDRED)
    else:
        breakeven_discount_pct = Decimal("0.00")
    headroom = money(breakeven_discount_pct - lot.discount_pct)

    return Result(
        gross=gross, discount_amount=discount_amount, taxable_value=taxable_value,
        cgst_amount=cgst_amount, sgst_amount=sgst_amount, total_gst=total_gst,
        invoice_total=invoice_total,
        cost_ex_gst_per_unit=cost_basis_per_unit, total_cost=total_cost,
        input_gst_credit=input_gst_credit,
        net_profit=net_profit, profit_per_unit=profit_per_unit,
        margin_pct=margin_pct, markup_pct=markup_pct,
        net_gst_payable=net_gst_payable,
        effective_rate=effective_rate, breakeven_rate=breakeven_rate,
        breakeven_discount_pct=breakeven_discount_pct,
        discount_headroom_pct=headroom,
    )


# --------------------------------------------------------------------------
# Indian number formatting
# --------------------------------------------------------------------------
def inr(value, symbol: bool = True) -> str:
    """Format in the Indian grouping: 12,34,567.89 — not 1,234,567.89.

    Lakh-and-crore grouping is what every invoice, bank statement and ledger in
    the country uses. Western thousands grouping on an Indian invoice reads as
    a foreign document.
    """
    d = money(value)
    sign = "-" if d < 0 else ""
    whole, _, frac = str(abs(d)).partition(".")
    frac = (frac + "00")[:2]

    if len(whole) > 3:
        head, tail = whole[:-3], whole[-3:]
        parts = []
        while len(head) > 2:
            parts.insert(0, head[-2:])
            head = head[:-2]
        if head:
            parts.insert(0, head)
        whole = ",".join(parts + [tail])

    return f"{sign}{'₹' if symbol else ''}{whole}.{frac}"


def signed_inr(value) -> str:
    """Same, but a positive figure carries an explicit plus."""
    d = money(value)
    return ("+" if d > 0 else "") + inr(d)
