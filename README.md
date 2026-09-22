# Elegant Leaf — lot profit calculator

Price a tea lot and see what it earns: for the whole consignment, and for a
single packet.

Built for a distributor pricing wholesale lots. Enter the rate, quantity,
discount, GST and your cost, and it returns the net profit, the profit on one
unit, the full invoice breakdown, and the discount at which the lot stops
paying.

---

## Running it

```bash
git clone https://github.com/<you>/elegant-leaf.git
cd elegant-leaf
pip install -r requirements.txt
streamlit run app.py
```

Opens at http://localhost:8501.

**Windows:**
```cmd
py -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

## Putting it online

1. Push this repo to GitHub.
2. Go to [share.streamlit.io](https://share.streamlit.io) → **New app**.
3. Repo: yours · Branch: `main` · Main file: `app.py`
4. Deploy. The first build takes two or three minutes.

No API keys, no database, no secrets. One dependency.

---

## How the profit is worked out

```
Gross            = rate × quantity
Discount         = gross × discount %
Taxable value    = gross − discount

CGST             = taxable value × CGST %
SGST             = taxable value × SGST %
Invoice total    = taxable value + CGST + SGST     ← what the buyer pays

Cost             = cost per unit (before GST) × quantity
Net profit       = taxable value − cost            ← what you keep
Profit per unit  = net profit ÷ quantity
```

### GST is not profit

This is the part worth understanding, because it is the easiest thing to get
wrong and it changes the answer.

You collect CGST and SGST from the buyer and remit both to the government. You
claim input credit on the GST you paid your supplier. The money moves through
the business without ever belonging to it, so it does not belong in a profit
figure either.

So profit is computed on the **taxable value** against the **pre-GST cost**.
Raise the GST rate and the invoice total rises while the profit does not move
at all. There is a test asserting exactly that, because a plausible-looking
implementation gets it wrong.

What the app still shows you, because you need it: the CGST and SGST amounts,
the invoice total, the input credit you can claim, and the net GST actually
payable after that credit is set off.

### The exception

A dealer under the **composition scheme**, or one not registered for GST,
cannot claim input credit. For them the GST paid on purchase is genuinely
gone, and it is a real cost.

Tick *"Treat GST paid as a cost"* and the cost basis becomes GST-inclusive. On
the worked example below, profit falls from ₹5,000 to ₹1,200 — which is the
true picture for that dealer, and the reason the toggle exists rather than a
blanket assumption.

### Cost entered including GST

If you take the cost off a tax-inclusive purchase bill, tick *"This cost
includes GST"* and enter the rate you paid. ₹399 including 5% GST is stripped
back to ₹380 of actual cost. Entering ₹399 without ticking the box would
understate your profit by ₹19 a unit.

---

## A worked example

200 packets of Assam CTC at ₹450, 10% discount, 5% GST, costing ₹380 each.

| | |
|---|---|
| Gross value | ₹90,000.00 |
| Less discount at 10% | −₹9,000.00 |
| **Taxable value** | **₹81,000.00** |
| CGST at 2.5% | ₹2,025.00 |
| SGST at 2.5% | ₹2,025.00 |
| **Invoice total** | **₹85,050.00** |
| Cost of 200 units | −₹76,000.00 |
| **Net profit on the lot** | **₹5,000.00** |
| **Net profit per unit** | **₹25.00** |
| Margin on sale | 6.17% |
| Markup on cost | 6.58% |
| Breakeven discount | 15.56% |

That last line is the useful one. At ₹380 a unit against a ₹450 list price you
can discount to 15.56% and no further. At 10% you have 5.56 points of room.
The app draws that as a meter so you can see how close a deal is running.

---

## Money handling

Every figure is a `Decimal`, never a float. In floating point `0.1 + 0.2` is
already wrong in the seventeenth decimal, and small errors accumulate across a
lot — an invoice that disagrees with the buyer's by a paisa is an argument
nobody needs.

Rounding follows Indian invoicing practice: the taxable value is rounded to two
decimals first, then tax is charged on that rounded figure, half-up, the way
the GST portal does it. A test asserts the parts reconcile to the whole with no
residue, because the buyer will add them up.

Amounts are formatted in lakh-and-crore grouping — ₹12,34,567.89, not
₹1,234,567.89.

---

## Tests

```bash
python test_calc.py
```

Nine groups, covering the cases where a plausible implementation goes wrong:

- a straightforward lot, checked line by line
- **GST at 5% and at 18% producing identical profit** — the single most likely
  error
- a GST-inclusive cost being stripped back correctly
- the composition-scheme path, where GST genuinely is a cost
- breakeven discount, verified by re-running at that discount and asserting
  profit lands on zero
- a loss staying negative rather than being clamped at zero
- zero quantity and 100% discount not raising
- rounding reconciling exactly on awkward figures
- Indian number grouping

`.github/workflows/ci.yml` runs them on every push. The arithmetic is the
product — if it breaks, every invoice priced with this tool is wrong.

---

## Files

```
app.py              the Streamlit interface
calc.py             the arithmetic — pure functions, no Streamlit, testable
test_calc.py        nine test groups
requirements.txt    one dependency
.streamlit/         theme tokens matching the app's palette
.github/workflows/  tests on every push
```

`calc.py` has no Streamlit import on purpose. It can be called from a script,
a notebook, or a future batch job over a CSV of lots without dragging the UI
along.

---

## Worth adding later

- **Several lots at once.** Upload a CSV of products and price the whole
  consignment in one pass. `calc.compute()` already takes one `Lot` at a time,
  so this is a loop and a table.
- **Save what you priced.** Right now each calculation is downloadable but not
  kept. Appending to a CSV in the repo would build a record of what you quoted
  and at what margin.
- **IGST for interstate sales.** The app assumes an intrastate sale — CGST plus
  SGST. Interstate is a single IGST line at the combined rate. The arithmetic is
  the same; it needs one toggle and a relabelled row.
- **Slab and scheme discounts.** If you give different rates by volume, that is
  a lookup before the discount step rather than a change to the maths.

---

*A pricing tool, not accounting software. Confirm GST rates and treatment with
your accountant before filing.*
