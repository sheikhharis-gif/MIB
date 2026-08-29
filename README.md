# Fleet Manager

Vehicle Fleet Management System — vehicles, vendors (Broker/Self), trip &amp; route
assignment, load assessment, oil/diesel expenses, sales tax invoicing (individual +
total vendor with SRB 15%), SRB cheque receipt tracking, and income/vendor-tax reports.

## Run it

```
venv\Scripts\python.exe app.py
```

This starts the server and opens `http://127.0.0.1:5000/` in your browser automatically.
The SQLite database (`fleet.db`) and a default admin user are created automatically on
first run.

**Default login:** `admin` / `admin123`

## Notes

- All data is stored locally in `fleet.db` (SQLite) — no internet connection needed to run.
- The dependencies are isolated in the `venv/` folder so they don't affect any other
  Python project on this machine.
- Net Income = Account Receivable − Account Payable − Expense (shown in Reports ›
  Income/Balance Sheet).
- SRB cheque math (Reports › SRB Cheque Receipt): Cheque 1 = Total Freight;
  Cheque 2 = (SRB 15% × 80%) − (SRB 15% × 20% income tax).
