from fastmcp import FastMCP
import os
import json
import sqlite3
import tempfile

# Use temporary directory which is writable in cloud
DB_PATH = os.path.join(tempfile.gettempdir(), "expenses.db")

mcp = FastMCP("ExpenseTracker")

def init_db():
    with sqlite3.connect(DB_PATH) as c:
        c.execute("PRAGMA journal_mode=WAL")
        c.execute("""
            CREATE TABLE IF NOT EXISTS expenses(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                amount REAL NOT NULL,
                category TEXT NOT NULL,
                subcategory TEXT DEFAULT '',
                note TEXT DEFAULT ''
            )
        """)
        c.commit()

init_db()

DEFAULT_CATEGORIES = [
    "Food & Dining",
    "Transportation",
    "Shopping",
    "Entertainment",
    "Bills & Utilities",
    "Healthcare",
    "Travel",
    "Education",
    "Business",
    "Other"
]

@mcp.tool()
def add_expense(date: str, amount: float, category: str, subcategory: str = "", note: str = "") -> dict:
    """Add a new expense entry to the database."""
    try:
        with sqlite3.connect(DB_PATH) as c:
            cur = c.execute(
                "INSERT INTO expenses(date, amount, category, subcategory, note) VALUES (?,?,?,?,?)",
                (date, amount, category, subcategory, note)
            )
            expense_id = cur.lastrowid
            c.commit()
            return {"status": "success", "id": expense_id, "message": "Expense added successfully"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@mcp.tool()
def list_expenses(start_date: str, end_date: str) -> list:
    """List expense entries within an inclusive date range."""
    try:
        with sqlite3.connect(DB_PATH) as c:
            cur = c.execute(
                """
                SELECT id, date, amount, category, subcategory, note
                FROM expenses
                WHERE date BETWEEN ? AND ?
                ORDER BY date DESC, id DESC
                """,
                (start_date, end_date)
            )
            cols = [d[0] for d in cur.description]
            return [dict(zip(cols, r)) for r in cur.fetchall()]
    except Exception as e:
        return {"status": "error", "message": str(e)}

@mcp.tool()
def summarize(start_date: str, end_date: str, category: str = None) -> list:
    """Summarize expenses by category within an inclusive date range."""
    try:
        with sqlite3.connect(DB_PATH) as c:
            query = """
                SELECT category, SUM(amount) AS total_amount, COUNT(*) as count
                FROM expenses
                WHERE date BETWEEN ? AND ?
            """
            params = [start_date, end_date]

            if category:
                query += " AND category = ?"
                params.append(category)

            query += " GROUP BY category ORDER BY total_amount DESC"

            cur = c.execute(query, params)
            cols = [d[0] for d in cur.description]
            return [dict(zip(cols, r)) for r in cur.fetchall()]
    except Exception as e:
        return {"status": "error", "message": str(e)}

@mcp.resource("expense:///categories", mime_type="application/json")
def categories() -> str:
    """Return available expense categories."""
    # Try loading from file first, fall back to defaults
    categories_path = os.path.join(os.path.dirname(__file__), "categories.json")
    try:
        with open(categories_path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return json.dumps({"categories": DEFAULT_CATEGORIES}, indent=2)

if __name__ == "__main__":
    mcp.run(transport="http", host="0.0.0.0", port=8000)