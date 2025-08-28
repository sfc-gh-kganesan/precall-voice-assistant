import sqlite3
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("--db", type=str, required=True)
args = parser.parse_args()

db = sqlite3.connect(args.db)
cursor = db.cursor()


def to_set(result):
    return set([row[0] for row in result])


def get_invoices_without_purchase_order_headers():
    cursor.execute(
        """
    SELECT INVOICE_ID FROM invoice_data id
    LEFT JOIN purchase_order_header poh ON id.PURCHASE_ORDER_NUMBER = poh.PO_HEADER_NUMBER
    WHERE poh.PO_HEADER_NUMBER IS NULL
    """
    )
    return to_set(cursor.fetchall())


def get_invoices_without_purchase_order_lines():
    cursor.execute(
        """
    SELECT INVOICE_ID FROM invoice_data id
    JOIN purchase_order_header poh ON id.PURCHASE_ORDER_NUMBER = poh.PO_HEADER_NUMBER
    LEFT JOIN purchase_order_line pol ON id.PURCHASE_ORDER_NUMBER = pol.PO_HEADER_NUMBER
    WHERE pol.PO_LINE_WD_ID IS NULL
    """
    )
    return to_set(cursor.fetchall())


def get_invoices_with_zero_total_amount():
    cursor.execute(
        """
        SELECT INVOICE_ID FROM invoice_data id
        WHERE id.TOTAL_AMOUNT = 0 or id.TOTAL_AMOUNT is null
    """
    )
    return to_set(cursor.fetchall())


def get_invoices_with_too_large_total_amount():
    cursor.execute(
        """
        SELECT id.INVOICE_ID FROM invoice_data id
        JOIN purchase_order_header poh ON id.PURCHASE_ORDER_NUMBER = poh.PO_HEADER_NUMBER
        JOIN purchase_order_line pol ON id.PURCHASE_ORDER_NUMBER = pol.PO_HEADER_NUMBER
        WHERE id.TOTAL_AMOUNT + poh.PRIOR_VERSION_PO_AMOUNT_USD > poh.TOTAL_PO_AMOUNT_LOCAL
        """
    )
    return to_set(cursor.fetchall())


def get_all_invoice_ids():
    cursor.execute(
        """
        SELECT INVOICE_ID FROM invoice_data
        """
    )
    return to_set(cursor.fetchall())


def set_state(invoice_ids: set[int], state):
    sql = f"""
        UPDATE invoice_data SET STATE = ? WHERE INVOICE_ID IN ({','.join(map(str, invoice_ids))})
        """
    print(f"{state} =>{sql}")
    cursor = db.execute(sql, (state,))
    print(f"Rows affected: {cursor.rowcount}")
    db.commit()


def validate(rule, candidates, subtractand):
    failures = candidates & subtractand
    if failures:
        set_state(failures, rule)
    return candidates - subtractand


candidates = get_all_invoice_ids()
candidates = validate(
    "NO_MATCHING_PO_HEADER",
    candidates,
    get_invoices_without_purchase_order_headers(),
)

candidates = validate(
    "NO_MATCHING_PO_LINE",
    candidates,
    get_invoices_without_purchase_order_lines(),
)

candidates = validate(
    "ZERO_TOTAL_AMOUNT",
    candidates,
    get_invoices_with_zero_total_amount(),
)

candidates = validate(
    "TOO_LARGE_TOTAL_AMOUNT",
    candidates,
    get_invoices_with_too_large_total_amount(),
)

set_state(candidates, "VALID")

db.close()
