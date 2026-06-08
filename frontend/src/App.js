import React, { useEffect, useMemo, useRef, useState } from "react";
import "./App.css";

const BASE_URL = process.env.REACT_APP_API_URL || "http://127.0.0.1:8000";
const API_KEY = process.env.REACT_APP_API_KEY || "";

function authHeaders(extra = {}) {
  return API_KEY ? { ...extra, "X-API-Key": API_KEY } : extra;
}
const EMPTY_FORM = {
  name: "",
  description: "",
  price: "",
  quantity: "",
  category: ""
};

function formatCurrency(value) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0
  }).format(value || 0);
}

function formatDate(value) {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "—";
  return date.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
}

function getStockStatus(quantity) {
  if (quantity === 0) return "Out of stock";
  if (quantity <= 5) return "Low stock";
  return "Healthy";
}

function escapeCsv(value) {
  return `"${String(value).replaceAll('"', '""')}"`;
}

function App() {
  const [products, setProducts] = useState([]);
  const [summary, setSummary] = useState(null);
  const [categories, setCategories] = useState([]);
  const [insights, setInsights] = useState({
    highest_value_product: null,
    reorder_recommendations: [],
    out_of_stock_products: []
  });
  const [form, setForm] = useState(EMPTY_FORM);
  const [editingProduct, setEditingProduct] = useState(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [importing, setImporting] = useState(false);
  const [toast, setToast] = useState("");
  const [search, setSearch] = useState("");
  const [stockFilter, setStockFilter] = useState("all");
  const [categoryFilter, setCategoryFilter] = useState("all");
  const [sortBy, setSortBy] = useState("name");
  const fileInputRef = useRef(null);

  const localMetrics = useMemo(() => {
    const totalProducts = products.length;
    const totalInventory = products.reduce((sum, product) => sum + product.quantity, 0);
    const catalogValue = products.reduce(
      (sum, product) => sum + product.price * product.quantity,
      0
    );
    const lowStock = products.filter((product) => product.quantity > 0 && product.quantity <= 5).length;
    const outOfStock = products.filter((product) => product.quantity === 0).length;
    const averagePrice = totalProducts
      ? products.reduce((sum, product) => sum + product.price, 0) / totalProducts
      : 0;

    return { totalProducts, totalInventory, catalogValue, lowStock, outOfStock, averagePrice };
  }, [products]);

  const metrics = {
    totalProducts: summary?.total_products ?? localMetrics.totalProducts,
    totalInventory: summary?.total_inventory ?? localMetrics.totalInventory,
    catalogValue: summary?.total_catalog_value ?? localMetrics.catalogValue,
    lowStock: summary?.low_stock_count ?? localMetrics.lowStock,
    outOfStock: summary?.out_of_stock_count ?? localMetrics.outOfStock,
    averagePrice: summary?.average_price ?? localMetrics.averagePrice
  };

  const categoryBreakdown = summary?.category_breakdown ?? [];

  useEffect(() => {
    fetchDashboardData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [search, stockFilter, categoryFilter, sortBy]);

  const showToast = (message) => {
    setToast(message);
    setTimeout(() => setToast(""), 2400);
  };

  const buildProductQuery = () => {
    const params = new URLSearchParams({
      limit: "500",
      sort_by: sortBy,
      stock_status: stockFilter
    });

    if (search.trim()) {
      params.set("search", search.trim());
    }

    if (categoryFilter !== "all") {
      params.set("category", categoryFilter);
    }

    return params.toString();
  };

  const fetchDashboardData = async () => {
    try {
      setLoading(true);
      const [productsRes, summaryRes, insightsRes, categoriesRes] = await Promise.all([
        fetch(`${BASE_URL}/products?${buildProductQuery()}`, { headers: authHeaders() }),
        fetch(`${BASE_URL}/products/summary`, { headers: authHeaders() }),
        fetch(`${BASE_URL}/products/insights`, { headers: authHeaders() }),
        fetch(`${BASE_URL}/products/categories`, { headers: authHeaders() })
      ]);

      if (!productsRes.ok || !summaryRes.ok || !insightsRes.ok || !categoriesRes.ok) {
        throw new Error("Failed to fetch dashboard data");
      }

      const [productsData, summaryData, insightsData, categoriesData] = await Promise.all([
        productsRes.json(),
        summaryRes.json(),
        insightsRes.json(),
        categoriesRes.json()
      ]);

      setProducts(productsData.items);
      setSummary(summaryData);
      setInsights(insightsData);
      setCategories(categoriesData);
    } catch (err) {
      console.error(err);
      showToast("Unable to load dashboard data");
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
      quantity: Number(form.quantity),
      category: form.category.trim() || "Uncategorized"
    };

    try {
      setSaving(true);
      const url = editingProduct
        ? `${BASE_URL}/products/${editingProduct.id}`
        : `${BASE_URL}/products`;
      const method = editingProduct ? "PUT" : "POST";

      const res = await fetch(url, {
        method,
        headers: authHeaders({ "Content-Type": "application/json" }),
        body: JSON.stringify(payload)
      });

      if (!res.ok) {
        const errorData = await res.json();
        throw new Error(errorData.detail || "Failed to save product");
      }

      showToast(editingProduct ? "Product updated" : "Product added");
      resetForm();
      fetchDashboardData();
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
        method: "DELETE",
        headers: authHeaders()
      });

      if (!res.ok) {
        throw new Error("Failed to delete product");
      }

      showToast("Product deleted");
      fetchDashboardData();
    } catch (err) {
      console.error(err);
      showToast("Unable to delete product");
    }
  };

  const adjustStock = async (product, delta) => {
    if (product.quantity + delta < 0) {
      showToast("Stock cannot go below zero");
      return;
    }

    try {
      const res = await fetch(`${BASE_URL}/products/${product.id}/stock`, {
        method: "PATCH",
        headers: authHeaders({ "Content-Type": "application/json" }),
        body: JSON.stringify({ delta })
      });

      if (!res.ok) {
        const errorData = await res.json();
        throw new Error(errorData.detail || "Failed to adjust stock");
      }

      fetchDashboardData();
    } catch (err) {
      console.error(err);
      showToast(err.message || "Unable to adjust stock");
    }
  };

  const startEditing = (product) => {
    setEditingProduct(product);
    setForm({
      name: product.name,
      description: product.description,
      price: product.price,
      quantity: product.quantity,
      category: product.category || ""
    });
  };

  const exportCsv = () => {
    if (products.length === 0) {
      showToast("No products to export");
      return;
    }

    const header = ["ID", "Name", "Description", "Category", "Price", "Quantity", "Status", "Catalog Value"];
    const rows = products.map((product) => [
      product.id,
      product.name,
      product.description,
      product.category || "Uncategorized",
      product.price,
      product.quantity,
      getStockStatus(product.quantity),
      product.price * product.quantity
    ]);
    const csv = [header, ...rows]
      .map((row) => row.map(escapeCsv).join(","))
      .join("\n");
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");

    link.href = url;
    link.download = "saas-products.csv";
    link.click();
    URL.revokeObjectURL(url);
    showToast("CSV exported");
  };

  const importCsv = async (event) => {
    const file = event.target.files?.[0];
    if (!file) return;

    const data = new FormData();
    data.append("file", file);

    try {
      setImporting(true);
      const res = await fetch(`${BASE_URL}/products/import`, {
        method: "POST",
        headers: authHeaders(),
        body: data
      });

      const result = await res.json();
      if (!res.ok) {
        throw new Error(result.detail || "Failed to import products");
      }

      const failedNote = result.failed ? `, ${result.failed} skipped` : "";
      showToast(`Imported ${result.created} product${result.created === 1 ? "" : "s"}${failedNote}`);
      fetchDashboardData();
    } catch (err) {
      console.error(err);
      showToast(err.message || "Unable to import products");
    } finally {
      setImporting(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    }
  };

  return (
    <main className="app-shell">
      {toast && <div className="toast">{toast}</div>}

      <section className="workspace-header">
        <div>
          <p className="eyebrow">SaaS operations</p>
          <h1>Product Management Dashboard</h1>
          <p className="header-copy">
            Track catalog health, inventory exposure and product updates from one focused workspace.
          </p>
        </div>
        <div className="header-actions">
          <input
            ref={fileInputRef}
            type="file"
            accept=".csv"
            onChange={importCsv}
            style={{ display: "none" }}
          />
          <button
            className="secondary-button"
            onClick={() => fileInputRef.current?.click()}
            disabled={importing}
          >
            {importing ? "Importing" : "Import CSV"}
          </button>
          <button className="secondary-button" onClick={exportCsv} disabled={loading}>
            Export CSV
          </button>
          <button className="refresh-button" onClick={fetchDashboardData} disabled={loading}>
            {loading ? "Syncing" : "Refresh"}
          </button>
        </div>
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
        <article className="metric-card">
          <span>Average price</span>
          <strong>{formatCurrency(metrics.averagePrice)}</strong>
        </article>
        <article className="metric-card alert">
          <span>Low stock</span>
          <strong>{metrics.lowStock}</strong>
        </article>
        <article className="metric-card danger">
          <span>Out of stock</span>
          <strong>{metrics.outOfStock}</strong>
        </article>
      </section>

      <section className="dashboard-grid">
        <aside className="sidebar-stack">
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

            <label>
              Category
              <input
                list="category-options"
                value={form.category}
                onChange={(e) => setForm({ ...form, category: e.target.value })}
                placeholder="Subscription"
              />
              <datalist id="category-options">
                {categories.map((name) => (
                  <option key={name} value={name} />
                ))}
              </datalist>
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

          <section className="insights-panel">
            <div className="section-heading">
              <p className="eyebrow">Insights</p>
              <h2>Ops focus</h2>
            </div>

            <div className="insight-block">
              <span>Highest value</span>
              <strong>{insights.highest_value_product?.name || "No product yet"}</strong>
              {insights.highest_value_product && (
                <p>{formatCurrency(insights.highest_value_product.price * insights.highest_value_product.quantity)}</p>
              )}
            </div>

            <div className="insight-block">
              <span>Reorder queue</span>
              {insights.reorder_recommendations.length === 0 ? (
                <p>No low-stock products</p>
              ) : (
                <ul>
                  {insights.reorder_recommendations.slice(0, 4).map((product) => (
                    <li key={product.id}>
                      <strong>{product.name}</strong>
                      <span>{product.quantity} left</span>
                    </li>
                  ))}
                </ul>
              )}
            </div>

            <div className="insight-block">
              <span>By category</span>
              {categoryBreakdown.length === 0 ? (
                <p>No categories yet</p>
              ) : (
                <ul>
                  {categoryBreakdown.map((stat) => (
                    <li key={stat.category}>
                      <strong>{stat.category}</strong>
                      <span className="neutral-pill">{stat.product_count}</span>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </section>
        </aside>

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
              <select value={categoryFilter} onChange={(e) => setCategoryFilter(e.target.value)}>
                <option value="all">All categories</option>
                {categories.map((name) => (
                  <option key={name} value={name}>
                    {name}
                  </option>
                ))}
              </select>
              <select value={stockFilter} onChange={(e) => setStockFilter(e.target.value)}>
                <option value="all">All stock</option>
                <option value="healthy">Healthy</option>
                <option value="low">Low stock</option>
                <option value="out">Out of stock</option>
              </select>
              <select value={sortBy} onChange={(e) => setSortBy(e.target.value)}>
                <option value="name">Name</option>
                <option value="stock">Lowest stock</option>
                <option value="value">Highest value</option>
                <option value="price">Highest price</option>
              </select>
            </div>
          </div>

          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Product</th>
                  <th>Category</th>
                  <th>Price</th>
                  <th>Stock</th>
                  <th>Status</th>
                  <th>Value</th>
                  <th>Updated</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {loading ? (
                  <tr>
                    <td colSpan="8" className="empty-state">
                      Loading product data
                    </td>
                  </tr>
                ) : products.length === 0 ? (
                  <tr>
                    <td colSpan="8" className="empty-state">
                      No products match this view
                    </td>
                  </tr>
                ) : (
                  products.map((product) => {
                    const status = getStockStatus(product.quantity);

                    return (
                      <tr key={product.id}>
                        <td>
                          <strong>{product.name}</strong>
                          <span>{product.description}</span>
                        </td>
                        <td>
                          <span className="category-tag">{product.category || "Uncategorized"}</span>
                        </td>
                        <td>{formatCurrency(product.price)}</td>
                        <td>
                          <div className="stock-stepper">
                            <button
                              type="button"
                              aria-label="Decrease stock"
                              onClick={() => adjustStock(product, -1)}
                              disabled={product.quantity === 0}
                            >
                              −
                            </button>
                            <span>{product.quantity}</span>
                            <button
                              type="button"
                              aria-label="Increase stock"
                              onClick={() => adjustStock(product, 1)}
                            >
                              +
                            </button>
                          </div>
                        </td>
                        <td>
                          <span className={`status-pill ${status.toLowerCase().replaceAll(" ", "-")}`}>
                            {status}
                          </span>
                        </td>
                        <td>{formatCurrency(product.price * product.quantity)}</td>
                        <td className="muted-cell">{formatDate(product.updated_at)}</td>
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
