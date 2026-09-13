"""
Meridian Goods — a simple multi-tier e-commerce product catalog.

Tier mapping for the case study:
  - Web/App tier : this Flask app, running on EC2 instances behind an ALB
  - Data tier    : MySQL on Amazon RDS

Configuration is pulled entirely from environment variables so the same
code runs unchanged whether you're pointing it at a local MySQL box or
at an RDS endpoint.
"""

import os
from decimal import Decimal

from flask import Flask, render_template, request, redirect, url_for, flash
import mysql.connector
from mysql.connector import pooling

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-change-me")

DB_CONFIG = {
    "host": os.environ.get("DB_HOST", "localhost"),
    "port": int(os.environ.get("DB_PORT", 3306)),
    "user": os.environ.get("DB_USER", "admin"),
    "password": os.environ.get("DB_PASSWORD", ""),
    "database": os.environ.get("DB_NAME", "meridian_goods"),
}

_pool = None


def get_pool():
    """Lazily create a small connection pool (created on first request,
    not at import time, so the app can still boot / show a health check
    even if RDS isn't reachable yet — handy while you're debugging
    connectivity)."""
    global _pool
    if _pool is None:
        _pool = pooling.MySQLConnectionPool(
            pool_name="meridian_pool",
            pool_size=5,
            **DB_CONFIG,
        )
    return _pool


def get_conn():
    return get_pool().get_connection()


SCHEMA = """
CREATE TABLE IF NOT EXISTS categories (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(80) NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS products (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(150) NOT NULL,
    description TEXT,
    price DECIMAL(10,2) NOT NULL,
    stock INT NOT NULL DEFAULT 0,
    category_id INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE SET NULL
);
"""

SEED_CATEGORIES = ["Home & Living", "Kitchen", "Stationery", "Electronics", "Outdoors"]

SEED_PRODUCTS = [
    ("Handwoven Cotton Throw", "Soft, breathable throw blanket, loom-woven in natural cotton.", 1499.00, 24, "Home & Living"),
    ("Cast Iron Skillet 10\"", "Pre-seasoned cast iron skillet, oven safe up to 500F.", 1899.00, 15, "Kitchen"),
    ("Brass Desk Lamp", "Adjustable brass desk lamp with a warm 2700K bulb.", 2299.00, 8, "Home & Living"),
    ("Refillable Fountain Pen", "Stainless steel nib, converts for bottled ink.", 649.00, 40, "Stationery"),
    ("Wireless Mechanical Keyboard", "Hot-swappable switches, USB-C, 75% layout.", 4599.00, 12, "Electronics"),
    ("Insulated Steel Bottle 1L", "Double-wall vacuum insulation, keeps drinks cold 24h.", 899.00, 33, "Outdoors"),
    ("Linen Notebook Set", "Set of 3 dot-grid notebooks, linen hardcover.", 799.00, 50, "Stationery"),
    ("Compact Camping Stove", "Foldable, wind-resistant, includes carry pouch.", 2199.00, 10, "Outdoors"),
]


def init_db():
    """Creates schema and seeds a handful of demo products. Safe to
    call repeatedly — uses CREATE TABLE IF NOT EXISTS and checks
    before seeding."""
    conn = get_conn()
    cur = conn.cursor()
    for statement in SCHEMA.strip().split(";"):
        statement = statement.strip()
        if statement:
            cur.execute(statement)
    conn.commit()

    cur.execute("SELECT COUNT(*) FROM categories")
    if cur.fetchone()[0] == 0:
        cur.executemany(
            "INSERT INTO categories (name) VALUES (%s)",
            [(c,) for c in SEED_CATEGORIES],
        )
        conn.commit()

    cur.execute("SELECT COUNT(*) FROM products")
    if cur.fetchone()[0] == 0:
        cur.execute("SELECT id, name FROM categories")
        cat_map = {name: cid for cid, name in cur.fetchall()}
        cur.executemany(
            "INSERT INTO products (name, description, price, stock, category_id) "
            "VALUES (%s, %s, %s, %s, %s)",
            [(n, d, p, s, cat_map[c]) for n, d, p, s, c in SEED_PRODUCTS],
        )
        conn.commit()

    cur.close()
    conn.close()


@app.route("/healthz")
def healthz():
    """Target group health check endpoint for the ALB."""
    try:
        conn = get_conn()
        conn.ping(reconnect=False)
        conn.close()
        return {"status": "ok", "db": "reachable"}, 200
    except Exception as exc:
        return {"status": "degraded", "db": "unreachable", "error": str(exc)}, 200


@app.route("/")
def index():
    category = request.args.get("category", "").strip()
    search = request.args.get("q", "").strip()

    conn = get_conn()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT id, name FROM categories ORDER BY name")
    categories = cur.fetchall()

    query = """
        SELECT p.id, p.name, p.description, p.price, p.stock, c.name AS category
        FROM products p
        LEFT JOIN categories c ON p.category_id = c.id
        WHERE 1=1
    """
    params = []
    if category:
        query += " AND c.name = %s"
        params.append(category)
    if search:
        query += " AND p.name LIKE %s"
        params.append(f"%{search}%")
    query += " ORDER BY p.created_at DESC"

    cur.execute(query, params)
    products = cur.fetchall()
    cur.close()
    conn.close()

    return render_template(
        "index.html",
        products=products,
        categories=categories,
        active_category=category,
        search=search,
    )


@app.route("/product/<int:product_id>")
def product_detail(product_id):
    conn = get_conn()
    cur = conn.cursor(dictionary=True)
    cur.execute(
        """SELECT p.*, c.name AS category FROM products p
           LEFT JOIN categories c ON p.category_id = c.id
           WHERE p.id = %s""",
        (product_id,),
    )
    product = cur.fetchone()
    cur.close()
    conn.close()
    if not product:
        flash("That product doesn't exist anymore.", "error")
        return redirect(url_for("index"))
    return render_template("product_detail.html", product=product)


@app.route("/product/new", methods=["GET", "POST"])
def product_new():
    conn = get_conn()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT id, name FROM categories ORDER BY name")
    categories = cur.fetchall()

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip()
        price = request.form.get("price", "0")
        stock = request.form.get("stock", "0")
        category_id = request.form.get("category_id") or None

        if not name or Decimal(price) <= 0:
            flash("Give the product a name and a price above zero.", "error")
        else:
            cur.execute(
                "INSERT INTO products (name, description, price, stock, category_id) "
                "VALUES (%s, %s, %s, %s, %s)",
                (name, description, price, stock, category_id),
            )
            conn.commit()
            cur.close()
            conn.close()
            flash(f'"{name}" was added to the catalog.', "success")
            return redirect(url_for("index"))

    cur.close()
    conn.close()
    return render_template("product_form.html", categories=categories, product=None)


@app.route("/product/<int:product_id>/edit", methods=["GET", "POST"])
def product_edit(product_id):
    conn = get_conn()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT id, name FROM categories ORDER BY name")
    categories = cur.fetchall()

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip()
        price = request.form.get("price", "0")
        stock = request.form.get("stock", "0")
        category_id = request.form.get("category_id") or None

        cur.execute(
            "UPDATE products SET name=%s, description=%s, price=%s, stock=%s, category_id=%s "
            "WHERE id=%s",
            (name, description, price, stock, category_id, product_id),
        )
        conn.commit()
        cur.close()
        conn.close()
        flash(f'"{name}" was updated.', "success")
        return redirect(url_for("product_detail", product_id=product_id))

    cur.execute("SELECT * FROM products WHERE id = %s", (product_id,))
    product = cur.fetchone()
    cur.close()
    conn.close()
    if not product:
        flash("That product doesn't exist anymore.", "error")
        return redirect(url_for("index"))
    return render_template("product_form.html", categories=categories, product=product)


@app.route("/product/<int:product_id>/delete", methods=["POST"])
def product_delete(product_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT name FROM products WHERE id = %s", (product_id,))
    row = cur.fetchone()
    cur.execute("DELETE FROM products WHERE id = %s", (product_id,))
    conn.commit()
    cur.close()
    conn.close()
    if row:
        flash(f'"{row[0]}" was removed from the catalog.', "success")
    return redirect(url_for("index"))


if __name__ == "__main__":
    with app.app_context():
        try:
            init_db()
        except Exception as exc:
            print(f"[startup] could not reach DB yet: {exc}")
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 80)), debug=False)
