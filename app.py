"""
Elegant Leaf — lot profit calculator.

Enter a sale, see what the lot actually earns and what one packet earns.

    streamlit run app.py
"""
from __future__ import annotations

import time
from decimal import Decimal

import streamlit as st

from calc import Lot, compute, inr, money, signed_inr

st.set_page_config(page_title="Elegant Leaf — lot profit",
                   page_icon="🍃", layout="wide")

# --------------------------------------------------------------------------
# Visual language
#
# Drawn from the trade rather than from a dashboard kit: tea-garden mist for
# the paper, deep leaf for ink, brewed Assam brown for structure, and brass —
# the scale pan — reserved for the one figure that matters. Fraunces carries
# the money; Archivo, narrow and plain, runs the invoice rows.
# --------------------------------------------------------------------------
CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,600;9..144,700&family=Archivo:wght@400;500;600&display=swap');

:root {
  --mist:   #E9EEE1;
  --paper:  #F5F8F0;
  --leaf:   #1B2A1C;
  --stem:   #4A5C48;
  --brew:   #6B3410;
  --brass:  #A8791F;
  --moss:   #3B6B36;
  --rust:   #92291A;
  --rule:   #C8D2BD;
}

.stApp { background: var(--mist); }

html, body, [class*="css"], .stMarkdown, label, input, button {
  font-family: 'Archivo', system-ui, sans-serif;
  color: var(--leaf);
}

#MainMenu, footer, header { visibility: hidden; }
.block-container { padding-top: 2.2rem; max-width: 1180px; }

/* ---- masthead ---- */
.mast { border-bottom: 2px solid var(--leaf); padding-bottom: .9rem; margin-bottom: 1.6rem; }
.mast h1 {
  font-family: 'Fraunces', Georgia, serif;
  font-weight: 600; font-size: 2.45rem; line-height: 1;
  margin: 0; color: var(--leaf); letter-spacing: -.015em;
}
.mast p { margin: .35rem 0 0; color: var(--stem); font-size: .95rem; max-width: 56ch; }

/* ---- the brass plate: the one bold thing on the page ---- */
.plate {
  background: linear-gradient(168deg, #B8871F 0%, #9A6E18 46%, #7E5814 100%);
  border-radius: 3px; padding: 1.8rem 1.9rem 1.5rem;
  box-shadow: inset 0 1px 0 rgba(255,245,210,.55), 0 10px 26px rgba(40,28,6,.26);
  color: #FFF8E4;
}
.plate.loss { background: linear-gradient(168deg, #9E3020 0%, #7E2417 52%, #5F1A11 100%); }
.plate .cap { font-size: .8rem; letter-spacing: .05em; color: rgba(255,248,228,.82); }
.plate .fig {
  font-family: 'Fraunces', Georgia, serif; font-weight: 700;
  font-size: 3.3rem; line-height: 1.02; margin: .3rem 0 0;
  font-variant-numeric: tabular-nums; letter-spacing: -.02em;
}
.plate .sub {
  margin-top: .85rem; padding-top: .8rem;
  border-top: 1px solid rgba(255,248,228,.3);
  display: flex; justify-content: space-between; align-items: baseline; gap: 1rem;
}
.plate .sub b {
  font-family: 'Fraunces', Georgia, serif; font-size: 1.45rem; font-weight: 600;
  font-variant-numeric: tabular-nums;
}

/* ---- ledger ---- */
.ledger { background: var(--paper); border: 1px solid var(--rule); border-radius: 3px; padding: 1.25rem 1.4rem; }
.ledger h3 {
  font-family: 'Fraunces', Georgia, serif; font-size: 1.1rem; font-weight: 600;
  margin: 0 0 .85rem; padding-bottom: .5rem; border-bottom: 1px solid var(--rule);
}
.row { display: flex; justify-content: space-between; gap: 1rem; padding: .44rem 0; font-size: .94rem; }
.row + .row { border-top: 1px dotted var(--rule); }
.row span:last-child { font-variant-numeric: tabular-nums; font-weight: 500; }
.row.total {
  border-top: 1.5px solid var(--leaf); margin-top: .35rem; padding-top: .6rem;
  font-weight: 600; font-size: 1.02rem;
}
.row.credit span:last-child { color: var(--moss); }
.row.debit  span:last-child { color: var(--brew); }
.note { color: var(--stem); font-size: .85rem; line-height: 1.5; margin-top: .9rem; }

/* ---- discount headroom meter ---- */
.meter-wrap { background: var(--paper); border: 1px solid var(--rule); border-radius: 3px; padding: 1.25rem 1.4rem; }
.meter { height: 26px; background: #DCE3D3; border-radius: 2px; position: relative; overflow: hidden; margin: .9rem 0 .5rem; }
.meter .used { position: absolute; inset: 0 auto 0 0; background: repeating-linear-gradient(135deg, #6B3410, #6B3410 7px, #7C3F15 7px, #7C3F15 14px); }
.meter .mark { position: absolute; top: -4px; bottom: -4px; width: 2px; background: var(--leaf); }
.meter-legend { display: flex; justify-content: space-between; font-size: .82rem; color: var(--stem); }

/* ---- process bar ---- */
.proc { background: var(--paper); border: 1px solid var(--rule); border-radius: 3px; padding: 1.5rem 1.6rem; }
.proc .stage {
  font-family: 'Fraunces', Georgia, serif; font-size: 1.3rem; font-weight: 600; margin: 0 0 .1rem;
}
.proc .meta { color: var(--stem); font-size: .86rem; margin-bottom: 1rem; }
.track { height: 12px; background: #DCE3D3; border-radius: 99px; overflow: hidden; }
.fill {
  height: 100%; border-radius: 99px;
  background: linear-gradient(90deg, #4A5C48 0%, #6B3410 42%, #A8791F 78%, #C9A13C 100%);
  box-shadow: 0 0 14px rgba(168,121,31,.5);
  transition: width .32s cubic-bezier(.4,0,.2,1);
}
.pips { display: flex; justify-content: space-between; margin-top: .85rem; }
.pip { font-size: .78rem; color: #A9B4A0; display: flex; align-items: center; gap: .32rem; }
.pip.done { color: var(--brew); }
.pip.now  { color: var(--brass); font-weight: 600; }
.dot { width: 7px; height: 7px; border-radius: 99px; background: currentColor; }

/* ---- verdict ---- */
.verdict { border-left: 3px solid var(--moss); padding: .75rem 0 .75rem 1rem; margin-top: 1.1rem; font-size: .95rem; line-height: 1.55; }
.verdict.warn { border-left-color: var(--brass); }
.verdict.bad  { border-left-color: var(--rust); }

@media (prefers-reduced-motion: reduce) { .fill { transition: none; } }
@media (max-width: 640px) { .plate .fig { font-size: 2.5rem; } .mast h1 { font-size: 1.9rem; } }
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

st.markdown(
    '<div class="mast"><h1>Elegant Leaf</h1>'
    '<p>Price a tea lot and see what it earns — for the whole consignment '
    'and for a single packet.</p></div>',
    unsafe_allow_html=True)


# --------------------------------------------------------------------------
# Entry
# --------------------------------------------------------------------------
left, right = st.columns([1, 1.25], gap="large")

with left:
    with st.form("lot"):
        st.markdown("#### The sale")
        product = st.text_input("Product", "Assam CTC — 250 g",
                                help="For your records; it appears on the download.")

        c1, c2 = st.columns(2)
        rate = c1.number_input("Rate per unit (₹)", min_value=0.0, value=450.0,
                               step=5.0, format="%.2f",
                               help="List price before GST.")
        qty = c2.number_input("Quantity", min_value=0.0, value=200.0, step=1.0,
                              format="%.0f")

        discount = st.slider("Discount given (%)", 0.0, 100.0, 10.0, 0.5)

        st.markdown("#### Tax")
        g1, g2 = st.columns(2)
        cgst = g1.number_input("CGST (%)", min_value=0.0, max_value=50.0,
                               value=2.5, step=0.5, format="%.2f")
        sgst = g2.number_input("SGST (%)", min_value=0.0, max_value=50.0,
                               value=2.5, step=0.5, format="%.2f")
        st.caption("Tea is normally 5% GST — 2.5% CGST plus 2.5% SGST.")

        st.markdown("#### What it cost you")
        cost = st.number_input("Cost price per unit (₹)", min_value=0.0,
                               value=380.0, step=5.0, format="%.2f")
        cost_incl = st.checkbox("This cost includes GST", value=False,
                                help="Tick if you entered the figure from a "
                                     "tax-inclusive purchase bill.")
        purchase_gst = st.number_input("GST paid on purchase (%)", min_value=0.0,
                                       max_value=50.0, value=5.0, step=0.5,
                                       format="%.2f")

        with st.expander("If you cannot claim input credit"):
            gst_is_cost = st.checkbox(
                "Treat GST paid as a cost", value=False,
                help="For the composition scheme or an unregistered dealer.")
            st.caption(
                "Normally GST is money passing through — you collect it from "
                "the buyer and claim back what you paid your supplier, so it "
                "never touches profit. Without input credit, the GST you paid "
                "is genuinely gone, and profit falls accordingly.")

        go = st.form_submit_button("Calculate profit", use_container_width=True,
                                   type="primary")


# --------------------------------------------------------------------------
# The staged process bar
# --------------------------------------------------------------------------
STAGES = [
    ("Reading the docket", "rate × quantity"),
    ("Applying the discount", f"taking it off the gross"),
    ("Charging CGST and SGST", "on the taxable value"),
    ("Weighing against cost", "stripping GST from the purchase"),
    ("Settling the lot", "profit for the consignment and per packet"),
]


def render_progress(slot, index: int) -> None:
    """Draw the bar at stage `index`. Called in a loop over a placeholder."""
    stage, meta = STAGES[index]
    width = (index + 1) / len(STAGES) * 100
    pips = "".join(
        f'<div class="pip {"done" if i < index else "now" if i == index else ""}">'
        f'<span class="dot"></span>{name.split()[0]}</div>'
        for i, (name, _) in enumerate(STAGES))
    slot.markdown(
        f'<div class="proc">'
        f'<p class="stage">{stage}</p>'
        f'<p class="meta">{meta}</p>'
        f'<div class="track"><div class="fill" style="width:{width:.0f}%"></div></div>'
        f'<div class="pips">{pips}</div></div>',
        unsafe_allow_html=True)


# --------------------------------------------------------------------------
# Result
# --------------------------------------------------------------------------
with right:
    if not go:
        st.markdown(
            '<div class="ledger"><h3>Nothing priced yet</h3>'
            '<p class="note">Fill in the sale on the left and calculate. '
            'You will get the profit on the whole lot, the profit on one '
            'packet, the full invoice breakdown, and the discount at which '
            'this lot stops making money.</p></div>',
            unsafe_allow_html=True)
        st.stop()

    slot = st.empty()
    for i in range(len(STAGES)):
        render_progress(slot, i)
        time.sleep(0.34)
    time.sleep(0.15)
    slot.empty()

    lot = Lot.of(rate=rate, qty=qty, discount_pct=discount,
                 cgst_pct=cgst, sgst_pct=sgst, cost_per_unit=cost,
                 cost_includes_gst=cost_incl, purchase_gst_pct=purchase_gst,
                 gst_is_cost=gst_is_cost)
    r = compute(lot)

    if qty <= 0:
        st.markdown(
            '<div class="ledger"><h3>Quantity is zero</h3>'
            '<p class="note">Set a quantity above zero to price the lot.</p>'
            '</div>', unsafe_allow_html=True)
        st.stop()

    # ---- the brass plate ----
    st.markdown(
        f'<div class="plate{" loss" if r.is_loss else ""}">'
        f'<div class="cap">{"Loss on the lot" if r.is_loss else "Net profit on the lot"}'
        f' · {product}</div>'
        f'<p class="fig">{inr(r.net_profit)}</p>'
        f'<div class="sub"><span>Per unit, across {money(qty):,.0f} units</span>'
        f'<b>{inr(r.profit_per_unit)}</b></div></div>',
        unsafe_allow_html=True)

    m1, m2, m3 = st.columns(3)
    m1.metric("Margin on sale", f"{r.margin_pct}%")
    m2.metric("Markup on cost", f"{r.markup_pct}%")
    m3.metric("Buyer pays", inr(r.invoice_total))

    # ---- discount headroom ----
    be = float(r.breakeven_discount_pct)
    used = float(discount)
    span = max(be, used, 1.0) * 1.12
    st.markdown(
        f'<div class="meter-wrap"><h3 style="font-family:Fraunces,Georgia,serif;'
        f'font-size:1.05rem;margin:0 0 .2rem;">Discount headroom</h3>'
        f'<div class="meter">'
        f'<div class="used" style="width:{min(used / span * 100, 100):.1f}%"></div>'
        f'<div class="mark" style="left:{min(max(be, 0) / span * 100, 100):.1f}%"></div>'
        f'</div><div class="meter-legend">'
        f'<span>Giving {used:.1f}%</span>'
        f'<span>Breaks even at {be:.2f}%</span></div></div>',
        unsafe_allow_html=True)

    head = r.discount_headroom_pct
    if r.is_loss:
        cls, msg = "bad", (
            f"This lot loses {inr(abs(r.net_profit))}. At a cost of "
            f"{inr(r.breakeven_rate)} a unit you cannot discount past "
            f"{be:.2f}% — you are at {used:.1f}%. Cut the discount by "
            f"{abs(head):.2f} points to get back to level.")
    elif head < 3:
        cls, msg = "warn", (
            f"This works, but only just. You have {head:.2f} points of "
            f"discount left before the lot stops paying. One more concession "
            f"and it is gone.")
    else:
        cls, msg = "", (
            f"Comfortable. You could go to {be:.2f}% discount before this lot "
            f"stops earning — {head:.2f} points of room from where you are.")
    st.markdown(f'<div class="verdict {cls}">{msg}</div>', unsafe_allow_html=True)

    # ---- the ledger ----
    lc, rc = st.columns(2, gap="medium")

    with lc:
        rows = "".join(
            f'<div class="row"><span>{label}</span>'
            f'<span>{inr(value)}</span></div>'
            for label, value in [
                ("Gross value", r.gross),
                (f"Less discount at {discount:g}%", -r.discount_amount),
            ])
        rows += (f'<div class="row total"><span>Taxable value</span>'
                 f'<span>{inr(r.taxable_value)}</span></div>')
        rows += "".join(
            f'<div class="row"><span>{label}</span><span>{inr(value)}</span></div>'
            for label, value in [
                (f"CGST at {cgst:g}%", r.cgst_amount),
                (f"SGST at {sgst:g}%", r.sgst_amount),
            ])
        rows += (f'<div class="row total"><span>Invoice total</span>'
                 f'<span>{inr(r.invoice_total)}</span></div>')
        st.markdown(f'<div class="ledger"><h3>What the buyer is billed</h3>'
                    f'{rows}</div>', unsafe_allow_html=True)

    with rc:
        cost_label = ("Cost per unit, GST included" if gst_is_cost
                      else "Cost per unit before GST")
        rows = "".join(
            f'<div class="row {css}"><span>{label}</span>'
            f'<span>{inr(value)}</span></div>'
            for label, value, css in [
                ("Taxable value received", r.taxable_value, "credit"),
                (cost_label, r.cost_ex_gst_per_unit, ""),
                (f"Cost of {money(qty):,.0f} units", -r.total_cost, "debit"),
            ])
        rows += (f'<div class="row total"><span>'
                 f'{"Loss" if r.is_loss else "Net profit"}</span>'
                 f'<span>{signed_inr(r.net_profit)}</span></div>')
        rows += (f'<div class="row"><span>Per unit</span>'
                 f'<span>{signed_inr(r.profit_per_unit)}</span></div>')

        if gst_is_cost:
            note = ("GST paid on purchase is treated as a cost here, so no "
                    f"input credit is set off. You remit {inr(r.total_gst)} "
                    "in full.")
        else:
            note = (f"GST stays out of profit. You collect {inr(r.total_gst)} "
                    f"and claim {inr(r.input_gst_credit)} back as input "
                    f"credit, so {inr(r.net_gst_payable)} goes to the "
                    "government. None of it is earnings.")

        st.markdown(f'<div class="ledger"><h3>What you keep</h3>{rows}'
                    f'<p class="note">{note}</p></div>',
                    unsafe_allow_html=True)

    # ---- download ----
    lines = [
        ("Product", product),
        ("Rate per unit", inr(rate, symbol=False)),
        ("Quantity", f"{money(qty):,.0f}"),
        ("Discount %", f"{discount:g}"),
        ("CGST %", f"{cgst:g}"),
        ("SGST %", f"{sgst:g}"),
        ("Cost per unit entered", inr(cost, symbol=False)),
        ("Cost per unit used", inr(r.cost_ex_gst_per_unit, symbol=False)),
        ("Gross value", inr(r.gross, symbol=False)),
        ("Discount amount", inr(r.discount_amount, symbol=False)),
        ("Taxable value", inr(r.taxable_value, symbol=False)),
        ("CGST amount", inr(r.cgst_amount, symbol=False)),
        ("SGST amount", inr(r.sgst_amount, symbol=False)),
        ("Invoice total", inr(r.invoice_total, symbol=False)),
        ("Total cost", inr(r.total_cost, symbol=False)),
        ("Net profit on lot", inr(r.net_profit, symbol=False)),
        ("Net profit per unit", inr(r.profit_per_unit, symbol=False)),
        ("Margin %", str(r.margin_pct)),
        ("Markup %", str(r.markup_pct)),
        ("Input GST credit", inr(r.input_gst_credit, symbol=False)),
        ("Net GST payable", inr(r.net_gst_payable, symbol=False)),
        ("Breakeven rate per unit", inr(r.breakeven_rate, symbol=False)),
        ("Breakeven discount %", str(r.breakeven_discount_pct)),
    ]
    csv = "Item,Value\n" + "\n".join(f'"{k}","{v}"' for k, v in lines)
    st.download_button("Download this calculation", csv,
                       file_name=f"elegant-leaf-{product[:24].replace(' ', '-')}.csv",
                       mime="text/csv", use_container_width=True)

    st.caption("Figures follow standard GST invoicing: tax is charged on the "
               "rounded taxable value. Confirm rates with your accountant "
               "before filing.")
