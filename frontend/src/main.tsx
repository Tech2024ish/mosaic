import { type ChangeEvent, type FormEvent, StrictMode, useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import "./styles.css";

const API_URL = "http://localhost:8000";
type AuthMode = "login" | "register";
type Job = { id: string; original_filename?: string; status: string; total_rows: number; successful_rows: number; failed_rows: number };
type ImportError = { row_number: number; message: string; field_name: string | null };
type CurrentUser = { id: string; email: string; name: string; organization_id: string; is_active: boolean };
type ImportStats = { total_imports: number; successful_imports: number; failed_imports: number; cancelled_imports: number; retry_count: number; total_rows: number; successful_rows: number; failed_rows: number };
type ImportEvent = { id: string; event_type: string; actor_id: string | null; created_at: string };
type DatasetType = "sales_history" | "products" | "warehouses" | "suppliers" | "inventory_snapshots";
type MasterItem = Record<string, string | number | boolean | null>;

function App() {
  const [apiStatus, setApiStatus] = useState("checking connection");
  const [authMode, setAuthMode] = useState<AuthMode>("login");
  const [email, setEmail] = useState("");
  const [name, setName] = useState("");
  const [password, setPassword] = useState("");
  const [token, setToken] = useState(() => window.localStorage.getItem("mosaic_access_token") ?? "");
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
  const [masterType, setMasterType] = useState<Exclude<DatasetType, "sales_history">>("products");
  const [masterItems, setMasterItems] = useState<MasterItem[]>([]);
  const [masterMessage, setMasterMessage] = useState("");

  const apiFetch = (url: string, init: RequestInit = {}) => fetch(url, {
    ...init, headers: { ...(init.headers ?? {}), ...(token ? { Authorization: `Bearer ${token}` } : {}) },
  });

  useEffect(() => {
    fetch(`${API_URL}/health`).then((response) => response.ok ? response.json() : Promise.reject())
      .then(() => setApiStatus("API connected")).catch(() => setApiStatus("API unavailable"));
  }, []);

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
    const response = await apiFetch(`${API_URL}/api/v1/${masterType}`);
    if (response.ok) { setMasterItems(await response.json()); setMasterMessage(""); }
    else setMasterMessage("Master data could not be loaded.");
  };

  useEffect(() => { refreshMasterData(); }, [token, masterType]);

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
    window.localStorage.removeItem("mosaic_access_token"); setToken(""); setCurrentUser(null); setJob(null);
  };

  return <div className="app-shell">
    <header className="topbar"><a className="brand" href="/">MOSAIC<span>.</span></a><nav><a className="active" href="#overview">Overview</a><a href="#ingestion">Data intake</a><a href="#operations">Operations</a></nav><div className="topbar-actions"><span className="connection"><i /> {apiStatus}</span>{token ? <><span className="user-label">{currentUser?.name ?? "Workspace"}</span><button className="button button-ghost" onClick={signOut}>Sign out</button></> : <a className="button button-gold" href="#access">Get started</a>}</div></header>
    <main>
      <section className="hero" id="overview"><div className="hero-copy"><p className="eyebrow">Supply-chain decision intelligence</p><h1>Make every supply decision <em>clearer.</em></h1><p className="hero-text">MOSAIC connects the signals across your supply chain so your team can see what is happening, understand why, and act with confidence.</p><div className="hero-actions"><a className="button button-gold" href="#access">Enter your workspace <span>→</span></a><a className="text-link" href="#ingestion">Explore data intake <span>↗</span></a></div></div><div className="hero-art" aria-hidden="true"><div className="art-grid" /><div className="art-orbit orbit-one" /><div className="art-orbit orbit-two" /><div className="art-node node-one" /><div className="art-node node-two" /><div className="art-node node-three" /><div className="art-label label-one">DEMAND</div><div className="art-label label-two">SUPPLY</div><div className="art-label label-three">ACTION</div></div></section>
      <section className="access-section" id="access"><div className="section-intro"><p className="eyebrow">Your operating picture</p><h2>Start with a clearer view.</h2><p>Securely connect your operational data and turn it into decisions your business can explain.</p></div>{!token ? <form className="auth-card" onSubmit={authenticate}><div className="card-heading"><span className="card-mark">✦</span><div><p className="eyebrow">MOSAIC workspace</p><h2>{authMode === "login" ? "Welcome back" : "Create your workspace"}</h2></div></div><div className="tabs"><button type="button" className={authMode === "login" ? "selected" : ""} onClick={() => setAuthMode("login")}>Sign in</button><button type="button" className={authMode === "register" ? "selected" : ""} onClick={() => setAuthMode("register")}>Register</button></div>{authMode === "register" && <label>Name<input value={name} onChange={(event) => setName(event.target.value)} placeholder="Your name" required /></label>}<label>Email<input type="email" value={email} onChange={(event) => setEmail(event.target.value)} placeholder="you@company.com" required /></label><label>Password<input type="password" value={password} onChange={(event) => setPassword(event.target.value)} placeholder="At least 12 characters" minLength={12} required /></label><button className="button button-dark submit-button" type="submit">{authMode === "login" ? "Sign in to MOSAIC" : "Create workspace"}<span>→</span></button>{authMessage && <p className="success-message">{authMessage}</p>}<p className="privacy-note">Your workspace is tenant-isolated and protected.</p></form> : <form className="auth-card import-form" id="ingestion" onSubmit={submitImport}><div className="card-heading"><span className="card-mark">↗</span><div><p className="eyebrow">Data intake</p><h2>Import operational data</h2></div></div><p className="card-description">Upload a CSV and MOSAIC will validate, normalize, and stage it safely.</p><label>Dataset<select value={datasetType} onChange={(event) => setDatasetType(event.target.value as DatasetType)}><option value="sales_history">Sales history</option><option value="products">Products</option><option value="warehouses">Warehouses</option><option value="suppliers">Suppliers</option><option value="inventory_snapshots">Inventory snapshots</option></select></label><label className="file-drop"><input type="file" accept=".csv,text/csv" onChange={(event: ChangeEvent<HTMLInputElement>) => setFile(event.target.files?.[0] ?? null)} /><span className="upload-icon">↑</span><strong>{file ? file.name : "Choose a CSV file"}</strong><small>{file ? `${(file.size / 1024).toFixed(1)} KB selected` : "Maximum file size: 25 MB"}</small></label><button className="button button-dark submit-button" type="submit" disabled={!file}>Start secure import <span>→</span></button>{job && <p className="summary">Job {job.id.slice(0, 8)} · {job.status} · {job.successful_rows}/{job.total_rows} rows accepted{job.failed_rows ? ` · ${job.failed_rows} rejected` : ""}</p>}{message && <p className="error-message">{message}</p>}</form>}</section>
      {token && <section className="operations-section" id="operations"><div className="operations-heading"><div><p className="eyebrow">Operations</p><h2>Import history</h2></div><button className="button button-ghost" onClick={refreshOperations}>Refresh</button></div>{stats && <div className="stats-grid"><div><strong>{stats.total_imports}</strong><span>Imports</span></div><div><strong>{stats.successful_rows}</strong><span>Rows accepted</span></div><div><strong>{stats.failed_rows}</strong><span>Rows rejected</span></div></div>}<div className="history-list">{history.length === 0 ? <p className="empty-state">No imports yet. Upload your first sales-history CSV above.</p> : history.map((item) => <article className="history-row" key={item.id}><div><strong>{item.original_filename}</strong><small>{item.id.slice(0, 8)} · {item.status}</small></div><span>{item.successful_rows}/{item.total_rows} rows</span><button className="text-link" onClick={() => inspectImport(item)}>Inspect</button>{item.status === "failed" && <button className="text-link" onClick={() => retryImport(item)}>Retry</button>}{["pending", "processing"].includes(item.status) && <button className="text-link" onClick={() => cancelImport(item)}>Cancel</button>}</article>)}</div>{job && <div className="detail-card"><p className="eyebrow">Selected import</p><h3>{job.id}</h3><p>{job.status} · {job.failed_rows} validation errors</p>{job.failed_rows > 0 && <button className="text-link" onClick={() => downloadReport(job)}>Download validation report</button>}{events.length > 0 && <div className="event-list"><p className="eyebrow">Activity</p>{events.map((event) => <small key={event.id}>{event.event_type.replaceAll("_", " ")} · {new Date(event.created_at).toLocaleString()}</small>)}</div>}{errors.length > 0 && <ul className="error-list">{errors.map((error) => <li key={`${error.row_number}-${error.message}`}>Row {error.row_number}{error.field_name ? ` (${error.field_name})` : ""}: {error.message}</li>)}</ul>}</div>}</section>}
      {token && <section className="operations-section"><div className="operations-heading"><div><p className="eyebrow">Master data</p><h2>Operational reference data</h2></div><button className="button button-ghost" onClick={refreshMasterData}>Refresh</button></div><label>Browse<select value={masterType} onChange={(event) => setMasterType(event.target.value as typeof masterType)}><option value="products">Products</option><option value="warehouses">Warehouses</option><option value="suppliers">Suppliers</option><option value="inventory">Inventory snapshots</option></select></label>{masterMessage && <p className="error-message">{masterMessage}</p>}<div className="history-list">{masterItems.length === 0 ? <p className="empty-state">No {masterType} loaded yet.</p> : masterItems.slice(0, 50).map((item, index) => <article className="history-row" key={String(item.id ?? index)}><div><strong>{String(item.product_code ?? item.warehouse_code ?? item.supplier_code ?? item.name ?? "Record")}</strong><small>{String(item.name ?? item.snapshot_date ?? item.location ?? "")}</small></div><span>{String(item.is_active ?? item.quantity_on_hand ?? "")}</span></article>)}</div></section>}
      <section className="feature-strip" id="network"><div><span className="feature-number">01</span><h3>Connect the signals</h3><p>Bring sales, inventory, suppliers, and warehouses into one decision picture.</p></div><div><span className="feature-number">02</span><h3>Understand the risk</h3><p>Separate the noise from the operational conditions that need attention.</p></div><div><span className="feature-number">03</span><h3>Choose with confidence</h3><p>Make explainable decisions today and learn from their outcomes tomorrow.</p></div></section>
    </main><footer><span className="brand">MOSAIC<span>.</span></span><span>Decision intelligence for resilient supply chains.</span><span className="connection"><i /> {apiStatus}</span></footer>
  </div>;
}

createRoot(document.getElementById("root")!).render(<StrictMode><App /></StrictMode>);
