import React, { useEffect, useMemo, useState } from "react";
import "./App.css";

const BASE_URL = process.env.REACT_APP_API_URL || "http://127.0.0.1:8000";
const EMPTY_FORM = {
  name: "",
  description: "",
  price: "",
  quantity: ""
};

function formatCurrency(value) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0
  }).format(value || 0);
}

function getStockStatus(quantity) {
  if (quantity === 0) return "Out of stock";
  if (quantity <= 5) return "Low stock";
  return "Healthy";
}

function App() {
  const [products, setProducts] = useState([]);
  const [form, setForm] = useState(EMPTY_FORM);
  const [editingProduct, setEditingProduct] = useState(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [toast, setToast] = useState("");
  const [search, setSearch] = useState("");
  const [stockFilter, setStockFilter] = useState("all");
  const [sortBy, setSortBy] = useState("name");

  useEffect(() => {
    fetchProducts();
  }, []);

  const metrics = useMemo(() => {
    const totalProducts = products.length;
    const totalInventory = products.reduce((sum, product) => sum + product.quantity, 0);
    const catalogValue = products.reduce(
      (sum, product) => sum + product.price * product.quantity,
      0
    );
    const lowStock = products.filter((product) => product.quantity <= 5).length;

    return { totalProducts, totalInventory, catalogValue, lowStock };
  }, [products]);

  const filteredProducts = useMemo(() => {
    const query = search.trim().toLowerCase();

    return [...products]
      .filter((product) => {
        const matchesSearch =
          product.name.toLowerCase().includes(query) ||
          product.description.toLowerCase().includes(query);
        const status = getStockStatus(product.quantity);
        const matchesStock = stockFilter === "all" || status === stockFilter;

        return matchesSearch && matchesStock;
      })
      .sort((a, b) => {
        if (sortBy === "value") {
          return b.price * b.quantity - a.price * a.quantity;
        }

        if (sortBy === "stock") {
          return a.quantity - b.quantity;
        }

        return a.name.localeCompare(b.name);
      });
  }, [products, search, stockFilter, sortBy]);

  const showToast = (message) => {
    setToast(message);
    setTimeout(() => setToast(""), 2400);
  };

  const fetchProducts = async () => {
    try {
      setLoading(true);
      const res = await fetch(`${BASE_URL}/products?limit=500`);

      if (!res.ok) {
        throw new Error("Failed to fetch products");
      }

      const data = await res.json();
      setProducts(data);
    } catch (err) {
      console.error(err);
      showToast("Unable to load products");
    } finally {
      setLoading(false);
    }
  };

  const validateForm = () => {
    if (!form.name.trim() || !form.description.trim()) {
      return "Name and description are required";
    }

    if (Number(form.price) <= 0) {
      return "Price must be greater than 0";
    }

    if (Number(form.quantity) < 0) {
      return "Quantity cannot be negative";
    }

    return "";
  };

  const resetForm = () => {
    setForm(EMPTY_FORM);
    setEditingProduct(null);
  };

  const saveProduct = async (event) => {
    event.preventDefault();

    const validationError = validateForm();
    if (validationError) {
      showToast(validationError);
      return;
    }

    const payload = {
      name: form.name.trim(),
      description: form.description.trim(),
      price: Number(form.price),
      quantity: Number(form.quantity)
    };

    try {
      setSaving(true);
      const url = editingProduct
        ? `${BASE_URL}/products/${editingProduct.id}`
        : `${BASE_URL}/products`;
      const method = editingProduct ? "PUT" : "POST";

      const res = await fetch(url, {
        method,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });

      if (!res.ok) {
        const errorData = await res.json();
        throw new Error(errorData.detail || "Failed to save product");
      }

      showToast(editingProduct ? "Product updated" : "Product added");
      resetForm();
      fetchProducts();
    } catch (err) {
      console.error(err);
      showToast(err.message || "Unable to save product");
    } finally {
      setSaving(false);
    }
  };

  const deleteProduct = async (id) => {
    try {
      const res = await fetch(`${BASE_URL}/products/${id}`, {
        method: "DELETE"
      });

      if (!res.ok) {
        throw new Error("Failed to delete product");
      }

      showToast("Product deleted");
      fetchProducts();
    } catch (err) {
      console.error(err);
      showToast("Unable to delete product");
    }
  };

  const startEditing = (product) => {
    setEditingProduct(product);
    setForm({
      name: product.name,
      description: product.description,
      price: product.price,
      quantity: product.quantity
    });
  };

  return (
    <main className="app-shell">
      {toast && <div className="toast">{toast}</div>}

      <section className="workspace-header">
        <div>
          <p className="eyebrow">SaaS operations</p>
          <h1>Product Management Dashboard</h1>
          <p className="header-copy">
            Track catalog health, inventory exposure, and product updates from one focused workspace.
          </p>
        </div>
        <button className="refresh-button" onClick={fetchProducts} disabled={loading}>
          {loading ? "Syncing" : "Refresh"}
        </button>
      </section>

      <section className="metric-grid" aria-label="Product performance metrics">
        <article className="metric-card">
          <span>Total products</span>
          <strong>{metrics.totalProducts}</strong>
        </article>
        <article className="metric-card">
          <span>Inventory units</span>
          <strong>{metrics.totalInventory}</strong>
        </article>
        <article className="metric-card">
          <span>Catalog value</span>
          <strong>{formatCurrency(metrics.catalogValue)}</strong>
        </article>
        <article className="metric-card alert">
          <span>Needs attention</span>
          <strong>{metrics.lowStock}</strong>
        </article>
      </section>

      <section className="dashboard-grid">
        <form className="product-form" onSubmit={saveProduct}>
          <div className="section-heading">
            <p className="eyebrow">Catalog control</p>
            <h2>{editingProduct ? "Edit product" : "Add product"}</h2>
          </div>

          <label>
            Product name
            <input
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              placeholder="Starter plan"
            />
          </label>

          <label>
            Description
            <textarea
              value={form.description}
              onChange={(e) => setForm({ ...form, description: e.target.value })}
              placeholder="Self-serve subscription plan for small teams"
              rows="4"
            />
          </label>

          <div className="field-row">
            <label>
              Price
              <input
                type="number"
                min="0"
                step="0.01"
                value={form.price}
                onChange={(e) => setForm({ ...form, price: e.target.value })}
                placeholder="49"
              />
            </label>
            <label>
              Quantity
              <input
                type="number"
                min="0"
                value={form.quantity}
                onChange={(e) => setForm({ ...form, quantity: e.target.value })}
                placeholder="25"
              />
            </label>
          </div>

          <div className="form-actions">
            <button type="submit" disabled={saving}>
              {saving ? "Saving" : editingProduct ? "Update product" : "Add product"}
            </button>
            {editingProduct && (
              <button type="button" className="secondary-button" onClick={resetForm}>
                Cancel
              </button>
            )}
          </div>
        </form>

        <section className="product-panel">
          <div className="table-toolbar">
            <div className="section-heading">
              <p className="eyebrow">Live catalog</p>
              <h2>Products</h2>
            </div>
            <div className="toolbar-controls">
              <input
                className="search-input"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search products"
              />
              <select value={stockFilter} onChange={(e) => setStockFilter(e.target.value)}>
                <option value="all">All stock</option>
                <option value="Healthy">Healthy</option>
                <option value="Low stock">Low stock</option>
                <option value="Out of stock">Out of stock</option>
              </select>
              <select value={sortBy} onChange={(e) => setSortBy(e.target.value)}>
                <option value="name">Name</option>
                <option value="stock">Lowest stock</option>
                <option value="value">Highest value</option>
              </select>
            </div>
          </div>

          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Product</th>
                  <th>Price</th>
                  <th>Stock</th>
                  <th>Status</th>
                  <th>Value</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {loading ? (
                  <tr>
                    <td colSpan="6" className="empty-state">
                      Loading product data
                    </td>
                  </tr>
                ) : filteredProducts.length === 0 ? (
                  <tr>
                    <td colSpan="6" className="empty-state">
                      No products match this view
                    </td>
                  </tr>
                ) : (
                  filteredProducts.map((product) => {
                    const status = getStockStatus(product.quantity);

                    return (
                      <tr key={product.id}>
                        <td>
                          <strong>{product.name}</strong>
                          <span>{product.description}</span>
                        </td>
                        <td>{formatCurrency(product.price)}</td>
                        <td>{product.quantity}</td>
                        <td>
                          <span className={`status-pill ${status.toLowerCase().replaceAll(" ", "-")}`}>
                            {status}
                          </span>
                        </td>
                        <td>{formatCurrency(product.price * product.quantity)}</td>
                        <td>
                          <div className="row-actions">
                            <button type="button" onClick={() => startEditing(product)}>
                              Edit
                            </button>
                            <button
                              type="button"
                              className="danger-button"
                              onClick={() => deleteProduct(product.id)}
                            >
                              Delete
                            </button>
                          </div>
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        </section>
      </section>
    </main>
  );
}

export default App;
