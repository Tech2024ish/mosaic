import { type ChangeEvent, type FormEvent, StrictMode, useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import "./styles.css";

const API_URL = (import.meta.env.VITE_API_URL ?? "http://localhost:8000").replace(/\/$/, "");
type AuthMode = "login" | "register";
type Job = { id: string; original_filename?: string; status: string; total_rows: number; successful_rows: number; failed_rows: number };
type ImportError = { row_number: number; message: string; field_name: string | null };
type CurrentUser = { id: string; email: string; name: string; organization_id: string; is_active: boolean };
type ImportStats = { total_imports: number; successful_imports: number; failed_imports: number; cancelled_imports: number; retry_count: number; total_rows: number; successful_rows: number; failed_rows: number };
type ImportEvent = { id: string; event_type: string; actor_id: string | null; created_at: string };
type DatasetType = "sales_history" | "products" | "warehouses" | "suppliers" | "inventory_snapshots";
type MasterItem = Record<string, string | number | boolean | null>;
type AnalyticsValue = number | string;
type AnalyticsSummary = { sales_count: number; total_quantity: AnalyticsValue; total_revenue: AnalyticsValue; average_sale_value: AnalyticsValue; product_count: number; warehouse_count: number; supplier_count: number; inventory_quantity: AnalyticsValue; inventory_record_count: number };
type TrendItem = { period: string; sales_count: number; total_quantity: AnalyticsValue; revenue: AnalyticsValue };
type SalesGroup = { key: string; label: string | null; sales_count: number; total_quantity: AnalyticsValue; total_revenue: AnalyticsValue; average_sale_value: AnalyticsValue };
type AnalyticsGroupBy = "date" | "product" | "warehouse";
type AnalyticsPeriod = "day" | "week" | "month";
type RankedItem = { rank: number; product_code?: string; product_name?: string | null; warehouse_code?: string; warehouse_name?: string | null; sales_count: number; quantity_sold: AnalyticsValue; revenue: AnalyticsValue };
type ReportType = "sales" | "products" | "inventory" | "warehouses";
type ReportItem = RankedItem & { snapshot_date?: string; quantity_on_hand?: AnalyticsValue; unit_cost?: AnalyticsValue | null };
type ReportResult = { report_type: ReportType; summary?: Partial<AnalyticsSummary> & { total_quantity?: AnalyticsValue; inventory_record_count?: number }; trend?: TrendItem[]; top_products?: RankedItem[]; warehouse_performance?: RankedItem[]; items?: ReportItem[] };
type InventorySummary = { total_inventory_units: AnalyticsValue; products_with_inventory: number; warehouses_with_inventory: number; out_of_stock_products: number };
type InventoryWarehouse = { warehouse_id: string; warehouse_code: string; warehouse_name: string; total_quantity: AnalyticsValue; product_count: number; status: "in_stock" | "out_of_stock" };
type InventoryProduct = { product_id: string; product_code: string; product_name: string; total_quantity: AnalyticsValue; warehouse_count: number; status: "in_stock" | "out_of_stock" };

function App() {
  const [apiStatus, setApiStatus] = useState("checking connection");
  const [authMode, setAuthMode] = useState<AuthMode>("login");
  const [email, setEmail] = useState("");
  const [name, setName] = useState("");
  const [password, setPassword] = useState("");
  const [token, setToken] = useState(() => window.localStorage.getItem("mosaic_access_token") ?? "");
  const [showAccess, setShowAccess] = useState(() => window.location.hash === "#access");
  const [currentUser, setCurrentUser] = useState<CurrentUser | null>(null);
  const [authMessage, setAuthMessage] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [job, setJob] = useState<Job | null>(null);
  const [errors, setErrors] = useState<ImportError[]>([]);
  const [events, setEvents] = useState<ImportEvent[]>([]);
  const [message, setMessage] = useState("");
  const [history, setHistory] = useState<Job[]>([]);
  const [stats, setStats] = useState<ImportStats | null>(null);
  const [datasetType, setDatasetType] = useState<DatasetType>("sales_history");
  const [masterType, setMasterType] = useState<DatasetType>("products");
  const [masterItems, setMasterItems] = useState<MasterItem[]>([]);
  const [masterMessage, setMasterMessage] = useState("");
  const [analyticsSummary, setAnalyticsSummary] = useState<AnalyticsSummary | null>(null);
  const [analyticsTrend, setAnalyticsTrend] = useState<TrendItem[]>([]);
  const [topProducts, setTopProducts] = useState<RankedItem[]>([]);
  const [warehousePerformance, setWarehousePerformance] = useState<RankedItem[]>([]);
  const [analyticsMessage, setAnalyticsMessage] = useState("");
  const [analyticsDateFrom, setAnalyticsDateFrom] = useState("");
  const [analyticsDateTo, setAnalyticsDateTo] = useState("");
  const [appliedDateFrom, setAppliedDateFrom] = useState("");
  const [appliedDateTo, setAppliedDateTo] = useState("");
  const [analyticsGroupBy, setAnalyticsGroupBy] = useState<AnalyticsGroupBy>("product");
  const [analyticsPeriod, setAnalyticsPeriod] = useState<AnalyticsPeriod>("month");
  const [salesGroups, setSalesGroups] = useState<SalesGroup[]>([]);
  const [analyticsLoading, setAnalyticsLoading] = useState(false);
  const [reportType, setReportType] = useState<ReportType>("sales");
  const [reportDateFrom, setReportDateFrom] = useState("");
  const [reportDateTo, setReportDateTo] = useState("");
  const [report, setReport] = useState<ReportResult | null>(null);
  const [reportMessage, setReportMessage] = useState("");
  const [, setReportLoading] = useState(false);
  const [inventorySummary, setInventorySummary] = useState<InventorySummary | null>(null);
  const [inventoryWarehouses, setInventoryWarehouses] = useState<InventoryWarehouse[]>([]);
  const [inventoryProducts, setInventoryProducts] = useState<InventoryProduct[]>([]);
  const [inventoryOutOfStock, setInventoryOutOfStock] = useState<InventoryProduct[]>([]);
  const [inventoryLoading, setInventoryLoading] = useState(false);
  const [inventoryMessage, setInventoryMessage] = useState("");

  const apiFetch = (url: string, init: RequestInit = {}) => fetch(url, {
    ...init, headers: { ...(init.headers ?? {}), ...(token ? { Authorization: `Bearer ${token}` } : {}) },
  });

  useEffect(() => {
    fetch(`${API_URL}/health`).then((response) => response.ok ? response.json() : Promise.reject())
      .then(() => setApiStatus("API connected")).catch(() => setApiStatus("API unavailable"));
  }, []);

  useEffect(() => {
    const handleHashChange = () => setShowAccess(window.location.hash === "#access");
    window.addEventListener("hashchange", handleHashChange);
    return () => window.removeEventListener("hashchange", handleHashChange);
  }, []);

  useEffect(() => {
    if (token) setShowAccess(true);
  }, [token]);

  useEffect(() => {
    if (!token) { setCurrentUser(null); setHistory([]); setStats(null); setMasterItems([]); return; }
    apiFetch(`${API_URL}/api/v1/auth/me`).then(async (response) => {
      if (!response.ok) throw new Error("Authentication expired");
      setCurrentUser(await response.json());
    }).catch(() => { window.localStorage.removeItem("mosaic_access_token"); setToken(""); });
  }, [token]);

  const refreshOperations = async () => {
    if (!token) return;
    const [historyResponse, statsResponse] = await Promise.all([
      apiFetch(`${API_URL}/api/v1/imports?limit=50`), apiFetch(`${API_URL}/api/v1/imports/stats`),
    ]);
    if (historyResponse.ok) setHistory(await historyResponse.json());
    if (statsResponse.ok) setStats(await statsResponse.json());
  };

  useEffect(() => { refreshOperations(); }, [token]);

  const refreshMasterData = async () => {
    if (!token) return;
    const endpoint = masterType === "sales_history" ? "sales" : masterType;
    const response = await apiFetch(`${API_URL}/api/v1/${endpoint}?limit=50`);
    if (response.ok) { setMasterItems(await response.json()); setMasterMessage(""); }
    else setMasterMessage("Master data could not be loaded.");
  };

  const refreshInventory = async () => {
    if (!token) return;
    setInventoryLoading(true);
    setInventoryMessage("");
    setInventorySummary(null);
    setInventoryWarehouses([]);
    setInventoryProducts([]);
    setInventoryOutOfStock([]);
    try {
      const [summaryResponse, warehouseResponse, productResponse, outOfStockResponse] = await Promise.all([
        apiFetch(`${API_URL}/api/v1/inventory/summary`),
        apiFetch(`${API_URL}/api/v1/inventory/by-warehouse?limit=5`),
        apiFetch(`${API_URL}/api/v1/inventory/by-product?limit=50&sort=quantity&order=desc`),
        apiFetch(`${API_URL}/api/v1/inventory/by-product?limit=10&status=out_of_stock&sort=code&order=asc`),
      ]);
      if (!summaryResponse.ok || !warehouseResponse.ok || !productResponse.ok || !outOfStockResponse.ok) throw new Error("Inventory unavailable");
      setInventorySummary(await summaryResponse.json());
      setInventoryWarehouses(await warehouseResponse.json());
      setInventoryProducts(await productResponse.json());
      setInventoryOutOfStock(await outOfStockResponse.json());
    } catch {
      setInventoryMessage("Inventory intelligence could not be loaded. Please retry.");
    } finally {
      setInventoryLoading(false);
    }
  };

  const refreshAnalytics = async () => {
    if (!token) return;
    setAnalyticsLoading(true);
    setAnalyticsMessage("");
    setAnalyticsSummary(null);
    setAnalyticsTrend([]);
    setTopProducts([]);
    setWarehousePerformance([]);
    setSalesGroups([]);
    const analyticsParams = new URLSearchParams();
    const groupParams = new URLSearchParams({ group_by: analyticsGroupBy, period: analyticsPeriod, limit: "20" });
    if (appliedDateFrom) {
      analyticsParams.set("date_from", appliedDateFrom);
      groupParams.set("date_from", appliedDateFrom);
    }
    if (appliedDateTo) {
      analyticsParams.set("date_to", appliedDateTo);
      groupParams.set("date_to", appliedDateTo);
    }
    const query = analyticsParams.toString();
    const trendParams = new URLSearchParams({ period: analyticsPeriod });
    if (appliedDateFrom) trendParams.set("date_from", appliedDateFrom);
    if (appliedDateTo) trendParams.set("date_to", appliedDateTo);
    const responses = await Promise.all([
      apiFetch(`${API_URL}/api/v1/analytics/summary${query ? `?${query}` : ""}`),
      apiFetch(`${API_URL}/api/v1/analytics/sales/trend?${trendParams.toString()}`),
      apiFetch(`${API_URL}/api/v1/analytics/products/top?limit=5${query ? `&${query}` : ""}`),
      apiFetch(`${API_URL}/api/v1/analytics/warehouses/performance?limit=5${query ? `&${query}` : ""}`),
      apiFetch(`${API_URL}/api/v1/analytics/sales?${groupParams.toString()}`),
    ]).catch(() => null);
    if (!responses) {
      setAnalyticsMessage("Analytics could not be loaded. Please retry.");
      setAnalyticsLoading(false);
      return;
    }
    const [summaryResponse, trendResponse, productsResponse, warehousesResponse, groupedResponse] = responses;
    if (summaryResponse.ok && trendResponse.ok && productsResponse.ok && warehousesResponse.ok && groupedResponse.ok) {
      setAnalyticsSummary(await summaryResponse.json());
      setAnalyticsTrend((await trendResponse.json()).data);
      setTopProducts((await productsResponse.json()).items);
      setWarehousePerformance((await warehousesResponse.json()).items);
      setSalesGroups((await groupedResponse.json()).groups);
      setAnalyticsMessage("");
    } else setAnalyticsMessage("Analytics could not be loaded. Please retry.");
    setAnalyticsLoading(false);
  };

  const reportQuery = () => {
    const params = new URLSearchParams();
    if (reportDateFrom) params.set("date_from", reportDateFrom);
    if (reportDateTo) params.set("date_to", reportDateTo);
    return params.toString();
  };

  const generateReport = async () => {
    if (!token) return;
    setReportMessage("");
    setReportLoading(true);
    const query = reportQuery();
    try {
      const response = await apiFetch(`${API_URL}/api/v1/reports/${reportType}${query ? `?${query}` : ""}`);
      if (response.ok) { setReport(await response.json()); setReportMessage(""); }
      else setReportMessage("Report could not be generated. Check the selected dates.");
    } catch {
      setReportMessage("Report could not be generated because the API is unavailable.");
    } finally {
      setReportLoading(false);
    }
  };

  const exportReport = async () => {
    if (!token) return;
    setReportMessage("");
    setReportLoading(true);
    const query = reportQuery();
    try {
      const response = await apiFetch(`${API_URL}/api/v1/reports/${reportType}/export?format=csv${query ? `&${query}` : ""}`);
      if (!response.ok) { setReportMessage("Report export could not be downloaded."); return; }
      const link = document.createElement("a"); link.href = URL.createObjectURL(await response.blob()); link.download = `mosaic-${reportType}-report.csv`; link.click(); URL.revokeObjectURL(link.href);
    } catch {
      setReportMessage("Report export could not be downloaded because the API is unavailable.");
    } finally {
      setReportLoading(false);
    }
  };

  useEffect(() => { refreshMasterData(); }, [token, masterType]);
  useEffect(() => { refreshInventory(); }, [token]);
  const applyAnalyticsFilters = () => {
    setAppliedDateFrom(analyticsDateFrom);
    setAppliedDateTo(analyticsDateTo);
  };

  useEffect(() => { refreshAnalytics(); }, [token, analyticsGroupBy, analyticsPeriod, appliedDateFrom, appliedDateTo]);

  useEffect(() => {
    if (!job || ["completed", "failed", "cancelled"].includes(job.status)) return;
    const timer = window.setInterval(async () => {
      const response = await apiFetch(`${API_URL}/api/v1/imports/${job.id}`);
      if (response.ok) setJob(await response.json());
    }, 1000);
    return () => window.clearInterval(timer);
  }, [job]);

  const authenticate = async (event: FormEvent) => {
    event.preventDefault(); setAuthMessage("");
    if (authMode === "register") {
      const registration = await fetch(`${API_URL}/api/v1/auth/register`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ email, name, password }) });
      if (!registration.ok) { setAuthMessage("Registration could not be completed."); return; }
    }
    const response = await fetch(`${API_URL}/api/v1/auth/login`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ email, password }) });
    if (!response.ok) { setAuthMessage("Check your email and password, then try again."); return; }
    const result = await response.json(); window.localStorage.setItem("mosaic_access_token", result.access_token); setToken(result.access_token);
    setAuthMessage(authMode === "register" ? "Workspace created" : "Signed in successfully");
  };

  const submitImport = async (event: FormEvent) => {
    event.preventDefault(); if (!file || !token) return; setMessage(""); setErrors([]);
    const body = new FormData(); body.append("file", file); body.append("dataset_type", datasetType);
    const response = await apiFetch(`${API_URL}/api/v1/imports`, { method: "POST", body });
    if (!response.ok) { setMessage("Upload failed. Check the file and your session."); return; }
    setJob(await response.json()); await refreshOperations();
  };

  const inspectImport = async (selected: Job) => {
    setJob(selected);
    const [errorsResponse, eventsResponse] = await Promise.all([
      apiFetch(`${API_URL}/api/v1/imports/${selected.id}/errors`), apiFetch(`${API_URL}/api/v1/imports/${selected.id}/events`),
    ]);
    setErrors(errorsResponse.ok ? await errorsResponse.json() : []);
    setEvents(eventsResponse.ok ? await eventsResponse.json() : []);
  };

  const retryImport = async (selected: Job) => {
    const response = await apiFetch(`${API_URL}/api/v1/imports/${selected.id}/retry`, { method: "POST" });
    if (response.ok) { setMessage("Import queued for retry."); await refreshOperations(); } else setMessage("This import cannot be retried in its current state.");
  };

  const cancelImport = async (selected: Job) => {
    if (!window.confirm("Cancel this import?")) return;
    const response = await apiFetch(`${API_URL}/api/v1/imports/${selected.id}/cancel`, { method: "POST" });
    if (response.ok) { setMessage("Import cancelled."); setJob(await response.json()); await refreshOperations(); } else setMessage("This import cannot be cancelled in its current state.");
  };

  const downloadReport = async (selected: Job) => {
    const response = await apiFetch(`${API_URL}/api/v1/imports/${selected.id}/errors/report`);
    if (!response.ok) { setMessage("Validation report could not be downloaded."); return; }
    const link = document.createElement("a"); link.href = URL.createObjectURL(await response.blob()); link.download = `mosaic-import-${selected.id}-errors.csv`; link.click(); URL.revokeObjectURL(link.href);
  };

  const signOut = async () => {
    if (token) await apiFetch(`${API_URL}/api/v1/auth/logout`, { method: "POST" });
    window.localStorage.removeItem("mosaic_access_token"); setToken(""); setCurrentUser(null); setJob(null); setShowAccess(false); window.history.replaceState(null, "", window.location.pathname);
  };
  const maxTrendRevenue = Math.max(1, ...analyticsTrend.map((item) => Number(item.revenue)));
  const inventoryDashboard = token && (
    <section className="inventory-dashboard" id="inventory" aria-labelledby="inventory-title">
      <div className="dashboard-heading">
        <div><p className="eyebrow">Inventory intelligence</p><h1 id="inventory-title">Current inventory position</h1><p className="dashboard-subtitle">See what is available, where it is held, and which products need attention.</p></div>
        <button className="button button-gold" type="button" onClick={refreshInventory} disabled={inventoryLoading}>{inventoryLoading ? "Refreshing..." : "Refresh inventory"}</button>
      </div>
      {inventoryMessage && <div className="dashboard-alert" role="alert">{inventoryMessage}<button className="text-link" type="button" onClick={refreshInventory}>Retry</button></div>}
      {inventoryLoading ? <div className="dashboard-loading-card" role="status">Loading inventory intelligence...</div> : inventorySummary && <>
        <div className="dashboard-kpis inventory-kpis">
          <article className="dashboard-kpi"><span>Total inventory units</span><strong>{String(inventorySummary.total_inventory_units)}</strong><small>Latest position by product and warehouse</small></article>
          <article className="dashboard-kpi"><span>Products with inventory</span><strong>{inventorySummary.products_with_inventory}</strong><small>Products with units available</small></article>
          <article className="dashboard-kpi"><span>Warehouses with inventory</span><strong>{inventorySummary.warehouses_with_inventory}</strong><small>Locations holding available units</small></article>
          <article className="dashboard-kpi inventory-attention"><span>Out of stock products</span><strong>{inventorySummary.out_of_stock_products}</strong><small>Products with no available units</small></article>
        </div>
        {Number(inventorySummary.total_inventory_units) === 0 && inventorySummary.out_of_stock_products === 0 ? <div className="dashboard-empty" role="status"><strong>No inventory data available</strong><span>Import inventory snapshots from Data intake to build this position.</span><a className="button button-dark" href="#ingestion">Go to data intake</a></div> : <div className="inventory-grid">
          <section className="dashboard-panel" aria-labelledby="inventory-warehouse-title"><div className="panel-heading"><div><p className="eyebrow">Distribution</p><h2 id="inventory-warehouse-title">Inventory by warehouse</h2></div><span className="panel-meta">Current</span></div>{inventoryWarehouses.length === 0 ? <p className="panel-empty">No warehouse inventory is available.</p> : <div className="inventory-ranking">{inventoryWarehouses.map((item) => <div className="inventory-ranking-row" key={item.warehouse_id}><div className="inventory-row-label"><strong>{item.warehouse_name}</strong><small>{item.warehouse_code} · {item.product_count} products</small></div><div className="inventory-bar"><span style={{ width: `${Math.max(4, Number(item.total_quantity) / Math.max(1, ...inventoryWarehouses.map((warehouse) => Number(warehouse.total_quantity))) * 100)}%` }} /></div><b>{String(item.total_quantity)}</b><span className={`inventory-status ${item.status}`}>{item.status === "in_stock" ? "In stock" : "Out of stock"}</span></div>)}</div>}</section>
          <section className="dashboard-panel" aria-labelledby="out-of-stock-title"><div className="panel-heading"><div><p className="eyebrow">Attention</p><h2 id="out-of-stock-title">Out of stock</h2></div><span className="panel-meta">{inventoryOutOfStock.length}</span></div>{inventoryOutOfStock.length === 0 ? <p className="panel-empty inventory-healthy">Inventory position looks healthy.</p> : <div className="dashboard-table">{inventoryOutOfStock.map((item) => <div className="dashboard-table-row" key={item.product_id}><span className="inventory-status-icon" aria-hidden="true">!</span><div><strong>{item.product_name}</strong><small>{item.product_code} · {item.warehouse_count} warehouses</small></div><span className="inventory-status out_of_stock">Out of stock</span></div>)}</div>}</section>
        </div>}
        <section className="dashboard-panel inventory-products-panel" aria-labelledby="inventory-products-title"><div className="panel-heading"><div><p className="eyebrow">Product position</p><h2 id="inventory-products-title">Inventory by product</h2></div><span className="panel-meta">Top 50</span></div>{inventoryProducts.length === 0 ? <p className="panel-empty">No products match the current inventory position.</p> : <div className="dashboard-table inventory-product-table"><div className="inventory-table-header"><span>Product</span><span>Quantity</span><span>Warehouses</span><span>Status</span></div>{inventoryProducts.map((item) => <div className="inventory-product-row" key={item.product_id}><div><strong>{item.product_name}</strong><small>{item.product_code}</small></div><b>{String(item.total_quantity)}</b><span>{item.warehouse_count}</span><span className={`inventory-status ${item.status}`}>{item.status === "in_stock" ? "In stock" : "Out of stock"}</span></div>)}</div>}</section>
      </>}
    </section>
  );
  const decisionDashboard = token && (
    <section className="decision-dashboard" id="decision-overview" aria-labelledby="decision-overview-title">
      <div className="dashboard-heading">
        <div>
          <p className="eyebrow">Decision intelligence</p>
          <h1 id="decision-overview-title">Overview</h1>
          <p className="dashboard-subtitle">A clear view of what is happening across your business.</p>
        </div>
        <button className="button button-gold" type="button" onClick={refreshAnalytics} disabled={analyticsLoading}>
          {analyticsLoading ? "Refreshing..." : "Refresh data"}
        </button>
      </div>
      <div className="dashboard-filters" aria-label="Dashboard filters">
        <label>From<input type="date" value={analyticsDateFrom} onChange={(event) => setAnalyticsDateFrom(event.target.value)} /></label>
        <label>To<input type="date" value={analyticsDateTo} onChange={(event) => setAnalyticsDateTo(event.target.value)} /></label>
        <label>Trend<select value={analyticsPeriod} onChange={(event) => setAnalyticsPeriod(event.target.value as AnalyticsPeriod)}><option value="day">Daily</option><option value="week">Weekly</option><option value="month">Monthly</option></select></label>
        <button className="button button-dark filter-apply" type="button" onClick={applyAnalyticsFilters} disabled={analyticsLoading}>Apply</button>
      </div>
      {analyticsMessage && <div className="dashboard-alert" role="alert">{analyticsMessage}<button className="text-link" type="button" onClick={refreshAnalytics}>Retry</button></div>}
      {analyticsLoading ? <div className="dashboard-loading-card" role="status">Loading your decision data...</div> : !analyticsSummary ? <div className="dashboard-empty" role="status"><strong>No sales data available</strong><span>Upload a sales-history CSV from Data intake to populate this overview.</span><a className="button button-dark" href="#ingestion">Go to data intake</a></div> : <>
        <div className="dashboard-kpis">
          <article className="dashboard-kpi"><span>Total revenue</span><strong>{String(analyticsSummary.total_revenue)}</strong><small>Selected period</small></article>
          <article className="dashboard-kpi"><span>Transactions</span><strong>{analyticsSummary.sales_count}</strong><small>Completed sales records</small></article>
          <article className="dashboard-kpi"><span>Units sold</span><strong>{String(analyticsSummary.total_quantity)}</strong><small>Quantity across sales</small></article>
          <article className="dashboard-kpi"><span>Average sale value</span><strong>{String(analyticsSummary.average_sale_value)}</strong><small>Revenue per transaction</small></article>
        </div>
        <div className="dashboard-main-grid">
          <section className="dashboard-panel dashboard-trend-panel" aria-labelledby="revenue-trend-title">
            <div className="panel-heading"><div><p className="eyebrow">Performance</p><h2 id="revenue-trend-title">Revenue trend</h2></div><span className="panel-meta">{analyticsPeriod}</span></div>
            {analyticsTrend.length === 0 ? <p className="panel-empty">No revenue recorded for this period.</p> : <div className="dashboard-chart" role="img" aria-label="Revenue by period">{analyticsTrend.map((item) => <div className="chart-column" key={item.period}><div className="chart-value">{String(item.revenue)}</div><div className="chart-track"><span style={{ height: `${Math.max(6, Number(item.revenue) / maxTrendRevenue * 100)}%` }} /></div><small>{item.period}</small></div>)}</div>}
          </section>
          <section className="dashboard-panel insight-panel" aria-labelledby="insights-title"><div className="panel-heading"><div><p className="eyebrow">Signals</p><h2 id="insights-title">At a glance</h2></div></div><div className="insight-row"><span className="status-dot green" /><div><strong>{topProducts[0]?.product_name ?? topProducts[0]?.product_code ?? "No product data"}</strong><small>Top product by revenue</small></div></div><div className="insight-row"><span className="status-dot yellow" /><div><strong>{warehousePerformance[0]?.warehouse_name ?? warehousePerformance[0]?.warehouse_code ?? "No warehouse data"}</strong><small>Leading warehouse by revenue</small></div></div><div className="insight-row"><span className="status-dot blue" /><div><strong>{String(analyticsSummary.inventory_quantity)}</strong><small>Current inventory quantity</small></div></div></section>
        </div>
        <div className="dashboard-main-grid dashboard-tables-grid">
          <section className="dashboard-panel" aria-labelledby="top-products-title"><div className="panel-heading"><div><p className="eyebrow">Product performance</p><h2 id="top-products-title">Top products</h2></div><span className="panel-meta">Top 5</span></div>{topProducts.length === 0 ? <p className="panel-empty">No products match this period.</p> : <div className="dashboard-table">{topProducts.map((item) => <div className="dashboard-table-row" key={item.product_code}><span className="rank">{item.rank}</span><div><strong>{item.product_name ?? item.product_code}</strong><small>{String(item.quantity_sold)} units · {item.sales_count} transactions</small></div><b>{String(item.revenue)}</b></div>)}</div>}</section>
          <section className="dashboard-panel" aria-labelledby="warehouse-performance-title"><div className="panel-heading"><div><p className="eyebrow">Distribution performance</p><h2 id="warehouse-performance-title">Warehouses</h2></div><span className="panel-meta">Top 5</span></div>{warehousePerformance.length === 0 ? <p className="panel-empty">No warehouses match this period.</p> : <div className="dashboard-table">{warehousePerformance.map((item) => <div className="dashboard-table-row" key={item.warehouse_code}><span className="rank">{item.rank}</span><div><strong>{item.warehouse_name ?? item.warehouse_code}</strong><small>{String(item.quantity_sold)} units · {item.sales_count} transactions</small></div><b>{String(item.revenue)}</b></div>)}</div>}</section>
        </div>
      </>}
    </section>
  );

  return <div className={`${token ? "app-shell workspace-shell" : "app-shell"}${showAccess ? " access-open" : ""}`}>
    {token && <aside className="workspace-sidebar" aria-label="Workspace navigation"><a className="sidebar-brand" href="#overview">MOSAIC<span>.</span></a><p className="sidebar-label">Workspace</p><nav className="sidebar-nav"><a className="sidebar-active" href="#overview"><span>⌂</span>Overview</a><a href="#inventory"><span>▧</span>Inventory</a><a href="#ingestion"><span>↥</span>Data intake</a><a href="#operations"><span>▦</span>Operations</a><a href="#analytics"><span>◒</span>Analytics</a><a href="#reports"><span>▤</span>Reports</a></nav><div className="sidebar-footer"><span className="sidebar-avatar">{currentUser?.name?.slice(0, 1).toUpperCase() ?? "M"}</span><div><strong>{currentUser?.name ?? "Workspace"}</strong><small>{currentUser?.email ?? "Tenant workspace"}</small></div><button className="sidebar-signout" type="button" onClick={signOut} aria-label="Sign out">↗</button></div></aside>}
    <header className="topbar"><a className="brand" href="/">MOSAIC<span>.</span></a><nav><a className="active" href="#overview">Overview</a><a href="#ingestion">Data intake</a><a href="#operations">Operations</a>{token && <><a href="#analytics">Analytics</a><a href="#reports">Reports</a></>}</nav><div className="topbar-actions"><span className="connection"><i /> {apiStatus}</span>{token ? <><span className="user-label">{currentUser?.name ?? "Workspace"}</span><button className="button button-ghost" onClick={signOut}>Sign out</button></> : <a className="button button-gold" href="#access">Get started</a>}</div></header>
    <main>
      {decisionDashboard}
      {inventoryDashboard}
      {token && <div className="dashboard-toolbar" aria-live="polite"><label>Trend period<select value={analyticsPeriod} onChange={(event) => setAnalyticsPeriod(event.target.value as AnalyticsPeriod)}><option value="day">Daily</option><option value="week">Weekly</option><option value="month">Monthly</option></select></label>{analyticsLoading && <span className="dashboard-loading">Refreshing decision data…</span>}</div>}
      {token && <section className="operations-section analytics-query" id="sales-query"><div className="operations-heading"><div><p className="eyebrow">Sales query</p><h2>Explore grouped performance</h2></div><button className="button button-ghost" type="button" onClick={refreshAnalytics}>Refresh</button></div><div className="report-filters"><label>Group by<select value={analyticsGroupBy} onChange={(event) => setAnalyticsGroupBy(event.target.value as AnalyticsGroupBy)}><option value="product">Product</option><option value="warehouse">Warehouse</option><option value="date">Date</option></select></label><label>From<input type="date" value={analyticsDateFrom} onChange={(event) => setAnalyticsDateFrom(event.target.value)} /></label><label>To<input type="date" value={analyticsDateTo} onChange={(event) => setAnalyticsDateTo(event.target.value)} /></label></div>{salesGroups.length === 0 ? <p className="empty-state">No grouped sales match these filters.</p> : <div className="history-list">{salesGroups.map((item) => <article className="history-row" key={item.key}><div><strong>{item.label ?? item.key}</strong><small>{item.sales_count} transactions · {String(item.total_quantity)} units</small></div><span>{String(item.total_revenue)}</span></article>)}</div>}</section>}
      <section className="hero" id="overview"><div className="hero-copy"><p className="eyebrow">Supply-chain decision intelligence</p><h1>Make every supply decision <em>clearer.</em></h1><p className="hero-text">MOSAIC connects the signals across your supply chain so your team can see what is happening, understand why, and act with confidence.</p><div className="hero-actions"><a className="button button-gold" href="#access">Enter your workspace <span>→</span></a><a className="text-link" href="#ingestion">Explore data intake <span>↗</span></a></div></div><div className="hero-art" aria-hidden="true"><div className="art-grid" /><div className="art-orbit orbit-one" /><div className="art-orbit orbit-two" /><div className="art-node node-one" /><div className="art-node node-two" /><div className="art-node node-three" /><div className="art-label label-one">DEMAND</div><div className="art-label label-two">SUPPLY</div><div className="art-label label-three">ACTION</div></div></section>
      <section className="access-section" id="access"><div className="section-intro"><p className="eyebrow">Your operating picture</p><h2>Start with a clearer view.</h2><p>Securely connect your operational data and turn it into decisions your business can explain.</p></div>{!token ? <form className="auth-card" onSubmit={authenticate}><div className="card-heading"><span className="card-mark">✦</span><div><p className="eyebrow">MOSAIC workspace</p><h2>{authMode === "login" ? "Welcome back" : "Create your workspace"}</h2></div></div><div className="tabs"><button type="button" className={authMode === "login" ? "selected" : ""} onClick={() => setAuthMode("login")}>Sign in</button><button type="button" className={authMode === "register" ? "selected" : ""} onClick={() => setAuthMode("register")}>Register</button></div>{authMode === "register" && <label>Name<input value={name} onChange={(event) => setName(event.target.value)} placeholder="Your name" required /></label>}<label>Email<input type="email" value={email} onChange={(event) => setEmail(event.target.value)} placeholder="you@company.com" required /></label><label>Password<input type="password" value={password} onChange={(event) => setPassword(event.target.value)} placeholder="At least 12 characters" minLength={12} required /></label><button className="button button-dark submit-button" type="submit">{authMode === "login" ? "Sign in to MOSAIC" : "Create workspace"}<span>→</span></button>{authMessage && <p className="success-message">{authMessage}</p>}<p className="privacy-note">Your workspace is tenant-isolated and protected.</p></form> : <form className="auth-card import-form" id="ingestion" onSubmit={submitImport}><div className="card-heading"><span className="card-mark">↗</span><div><p className="eyebrow">Data intake</p><h2>Import operational data</h2></div></div><p className="card-description">Upload a CSV and MOSAIC will validate, normalize, and stage it safely.</p><label>Dataset<select value={datasetType} onChange={(event) => setDatasetType(event.target.value as DatasetType)}><option value="sales_history">Sales history</option><option value="products">Products</option><option value="warehouses">Warehouses</option><option value="suppliers">Suppliers</option><option value="inventory_snapshots">Inventory snapshots</option></select></label><label className="file-drop"><input type="file" accept=".csv,text/csv" onChange={(event: ChangeEvent<HTMLInputElement>) => setFile(event.target.files?.[0] ?? null)} /><span className="upload-icon">↑</span><strong>{file ? file.name : "Choose a CSV file"}</strong><small>{file ? `${(file.size / 1024).toFixed(1)} KB selected` : "Maximum file size: 25 MB"}</small></label><button className="button button-dark submit-button" type="submit" disabled={!file}>Start secure import <span>→</span></button>{job && <p className="summary">Job {job.id.slice(0, 8)} · {job.status} · {job.successful_rows}/{job.total_rows} rows accepted{job.failed_rows ? ` · ${job.failed_rows} rejected` : ""}</p>}{message && <p className="error-message">{message}</p>}</form>}</section>
      {token && <section className="operations-section" id="operations"><div className="operations-heading"><div><p className="eyebrow">Operations</p><h2>Import history</h2></div><button className="button button-ghost" onClick={refreshOperations}>Refresh</button></div>{stats && <div className="stats-grid"><div><strong>{stats.total_imports}</strong><span>Imports</span></div><div><strong>{stats.successful_rows}</strong><span>Rows accepted</span></div><div><strong>{stats.failed_rows}</strong><span>Rows rejected</span></div></div>}<div className="history-list">{history.length === 0 ? <p className="empty-state">No imports yet. Upload your first sales-history CSV above.</p> : history.map((item) => <article className="history-row" key={item.id}><div><strong>{item.original_filename}</strong><small>{item.id.slice(0, 8)} · {item.status}</small></div><span>{item.successful_rows}/{item.total_rows} rows</span><button className="text-link" onClick={() => inspectImport(item)}>Inspect</button>{item.status === "failed" && <button className="text-link" onClick={() => retryImport(item)}>Retry</button>}{["pending", "processing"].includes(item.status) && <button className="text-link" onClick={() => cancelImport(item)}>Cancel</button>}</article>)}</div>{job && <div className="detail-card"><p className="eyebrow">Selected import</p><h3>{job.id}</h3><p>{job.status} · {job.failed_rows} validation errors</p>{job.failed_rows > 0 && <button className="text-link" onClick={() => downloadReport(job)}>Download validation report</button>}{events.length > 0 && <div className="event-list"><p className="eyebrow">Activity</p>{events.map((event) => <small key={event.id}>{event.event_type.replaceAll("_", " ")} · {new Date(event.created_at).toLocaleString()}</small>)}</div>}{errors.length > 0 && <ul className="error-list">{errors.map((error) => <li key={`${error.row_number}-${error.message}`}>Row {error.row_number}{error.field_name ? ` (${error.field_name})` : ""}: {error.message}</li>)}</ul>}</div>}</section>}
      {token && <section className="operations-section"><div className="operations-heading"><div><p className="eyebrow">Business data</p><h2>Explore your tenant data</h2></div><button className="button button-ghost" onClick={refreshMasterData}>Refresh</button></div><label>Dataset<select value={masterType} onChange={(event) => setMasterType(event.target.value as DatasetType)}><option value="products">Products</option><option value="warehouses">Warehouses</option><option value="suppliers">Suppliers</option><option value="inventory">Inventory snapshots</option><option value="sales_history">Sales history</option></select></label>{masterMessage && <p className="error-message">{masterMessage}</p>}<div className="history-list">{masterItems.length === 0 ? <p className="empty-state">No {masterType} loaded yet.</p> : masterItems.slice(0, 50).map((item, index) => <article className="history-row" key={String(item.id ?? index)}><div><strong>{String(item.product_code ?? item.warehouse_code ?? item.supplier_code ?? item.name ?? "Record")}</strong><small>{String(item.name ?? item.snapshot_date ?? item.sale_date ?? item.location ?? "")}</small></div><span>{String(item.is_active ?? item.quantity_on_hand ?? item.quantity ?? "")}</span></article>)}</div></section>}
      {token && <section className="operations-section" id="analytics"><div className="operations-heading"><div><p className="eyebrow">Decision signals</p><h2>Analytics overview</h2></div><button className="button button-ghost" onClick={refreshAnalytics}>Refresh</button></div>{analyticsMessage && <p className="error-message">{analyticsMessage}</p>}{analyticsSummary && <div className="stats-grid"><div><strong>{String(analyticsSummary.total_revenue)}</strong><span>Revenue</span></div><div><strong>{analyticsSummary.sales_count}</strong><span>Transactions</span></div><div><strong>{String(analyticsSummary.average_sale_value)}</strong><span>Average sale</span></div><div><strong>{String(analyticsSummary.inventory_quantity)}</strong><span>Current inventory</span></div></div>}<div className="history-list">{analyticsTrend.length === 0 ? <p className="empty-state">No sales trend data for this workspace.</p> : analyticsTrend.map((item) => <article className="history-row trend-row" key={item.period}><div><strong>{item.period}</strong><small>{item.sales_count} transactions</small></div><div className="trend-bar"><span style={{ width: `${Math.max(5, Number(item.revenue) / maxTrendRevenue * 100)}%` }} /></div><span>{String(item.revenue)} revenue</span></article>)}</div><div className="history-list">{topProducts.length > 0 && <><p className="eyebrow">Top products</p>{topProducts.map((item) => <article className="history-row" key={`product-${item.product_code}`}><div><strong>#{item.rank} {item.product_name ?? item.product_code}</strong><small>{item.product_code} · {item.sales_count} transactions</small></div><span>{String(item.revenue)}</span></article>)}</>}{warehousePerformance.length > 0 && <><p className="eyebrow">Warehouse performance</p>{warehousePerformance.map((item) => <article className="history-row" key={`warehouse-${item.warehouse_code}`}><div><strong>#{item.rank} {item.warehouse_name ?? item.warehouse_code}</strong><small>{item.warehouse_code} · {item.sales_count} transactions</small></div><span>{String(item.revenue)}</span></article>)}</>}</div></section>}
      {token && <section className="operations-section" id="reports"><div className="operations-heading"><div><p className="eyebrow">Reusable business output</p><h2>Reports & exports</h2></div><div className="report-actions"><button className="button button-ghost" type="button" onClick={generateReport}>Generate</button><button className="button button-gold" type="button" onClick={exportReport}>Download CSV</button></div></div><div className="report-filters"><label>Report<select value={reportType} onChange={(event) => setReportType(event.target.value as ReportType)}><option value="sales">Sales report</option><option value="products">Product performance</option><option value="inventory">Inventory report</option><option value="warehouses">Warehouse report</option></select></label><label>From<input type="date" value={reportDateFrom} onChange={(event) => setReportDateFrom(event.target.value)} /></label><label>To<input type="date" value={reportDateTo} onChange={(event) => setReportDateTo(event.target.value)} /></label></div>{reportMessage && <p className="error-message">{reportMessage}</p>}{report?.summary && <div className="stats-grid"><div><strong>{String(report.summary.total_revenue ?? report.summary.total_quantity ?? "0")}</strong><span>{reportType === "inventory" ? "Inventory quantity" : "Revenue"}</span></div><div><strong>{String(report.summary.sales_count ?? report.summary.inventory_record_count ?? 0)}</strong><span>{reportType === "inventory" ? "Inventory records" : "Transactions"}</span></div><div><strong>{String(report.summary.average_sale_value ?? "—")}</strong><span>Average sale</span></div></div>}{report?.trend && <div className="history-list"><p className="eyebrow">Sales trend</p>{report.trend.map((item) => <article className="history-row" key={item.period}><div><strong>{item.period}</strong><small>{item.sales_count} transactions</small></div><span>{String(item.revenue)}</span></article>)}</div>}{report?.items && <div className="history-list">{report.items.length === 0 ? <p className="empty-state">No rows match this report.</p> : report.items.map((item) => <article className="history-row" key={`${item.product_code ?? item.warehouse_code}-${item.snapshot_date ?? item.rank}`}><div><strong>{item.product_name ?? item.warehouse_name ?? item.product_code ?? item.warehouse_code}</strong><small>{item.snapshot_date ?? `${item.sales_count} transactions`}</small></div><span>{String(item.revenue ?? item.quantity_on_hand ?? "")}</span></article>)}</div>}{report?.top_products && <div className="history-list"><p className="eyebrow">Top products</p>{report.top_products.map((item) => <article className="history-row" key={`report-product-${item.product_code}`}><div><strong>#{item.rank} {item.product_name ?? item.product_code}</strong><small>{item.sales_count} transactions</small></div><span>{String(item.revenue)}</span></article>)}</div>}{report?.warehouse_performance && <div className="history-list"><p className="eyebrow">Warehouse performance</p>{report.warehouse_performance.map((item) => <article className="history-row" key={`report-warehouse-${item.warehouse_code}`}><div><strong>#{item.rank} {item.warehouse_name ?? item.warehouse_code}</strong><small>{item.sales_count} transactions</small></div><span>{String(item.revenue)}</span></article>)}</div>}</section>}
      <section className="feature-strip" id="network"><div><span className="feature-number">01</span><h3>Connect the signals</h3><p>Bring sales, inventory, suppliers, and warehouses into one decision picture.</p></div><div><span className="feature-number">02</span><h3>Understand the risk</h3><p>Separate the noise from the operational conditions that need attention.</p></div><div><span className="feature-number">03</span><h3>Choose with confidence</h3><p>Make explainable decisions today and learn from their outcomes tomorrow.</p></div></section>
    </main><footer><span className="brand">MOSAIC<span>.</span></span><span>Decision intelligence for resilient supply chains.</span><span className="connection"><i /> {apiStatus}</span></footer>
  </div>;
}

createRoot(document.getElementById("root")!).render(<StrictMode><App /></StrictMode>);
