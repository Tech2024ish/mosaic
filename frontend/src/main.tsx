import { type ChangeEvent, type FormEvent, StrictMode, useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import "./styles.css";

const API_URL = "http://localhost:8000";
type AuthMode = "login" | "register";
type Job = { id: string; status: string; total_rows: number; successful_rows: number; failed_rows: number };
type ImportError = { row_number: number; message: string; field_name: string | null };

function App() {
  const [apiStatus, setApiStatus] = useState("checking connection");
  const [authMode, setAuthMode] = useState<AuthMode>("login");
  const [email, setEmail] = useState("");
  const [name, setName] = useState("");
  const [password, setPassword] = useState("");
  const [token, setToken] = useState(() => window.localStorage.getItem("mosaic_access_token") ?? "");
  const [authMessage, setAuthMessage] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [job, setJob] = useState<Job | null>(null);
  const [errors, setErrors] = useState<ImportError[]>([]);
  const [message, setMessage] = useState("");

  const apiFetch = (url: string, init: RequestInit = {}) => fetch(url, {
    ...init,
    headers: { ...(init.headers ?? {}), ...(token ? { Authorization: `Bearer ${token}` } : {}) },
  });

  useEffect(() => {
    fetch(`${API_URL}/health`).then((response) => (response.ok ? response.json() : Promise.reject()))
      .then(() => setApiStatus("API connected")).catch(() => setApiStatus("API unavailable"));
  }, []);

  useEffect(() => {
    if (!job || ["completed", "failed"].includes(job.status)) return;
    const timer = window.setInterval(async () => {
      const response = await apiFetch(`${API_URL}/api/v1/imports/${job.id}`);
      if (response.ok) setJob(await response.json());
    }, 1000);
    return () => window.clearInterval(timer);
  }, [job]);

  useEffect(() => {
    if (!job || !["completed", "failed"].includes(job.status)) return;
    apiFetch(`${API_URL}/api/v1/imports/${job.id}/errors`).then((response) => response.ok ? response.json() : []).then(setErrors);
  }, [job?.status, job?.id]);

  const authenticate = async (event: FormEvent) => {
    event.preventDefault(); setAuthMessage("");
    if (authMode === "register") {
      const registration = await fetch(`${API_URL}/api/v1/auth/register`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ email, name, password }) });
      if (!registration.ok) { const result = await registration.json(); setAuthMessage(result.detail ?? "Registration could not be completed."); return; }
    }
    const response = await fetch(`${API_URL}/api/v1/auth/login`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ email, password }) });
    if (!response.ok) { setAuthMessage("Check your email and password, then try again."); return; }
    const result = await response.json(); window.localStorage.setItem("mosaic_access_token", result.access_token); setToken(result.access_token);
    setAuthMessage(authMode === "register" ? "Workspace created" : "Signed in successfully");
  };

  const submitImport = async (event: FormEvent) => {
    event.preventDefault(); if (!file || !token) return; setMessage(""); setErrors([]);
    const body = new FormData(); body.append("file", file); body.append("dataset_type", "sales_history");
    const response = await apiFetch(`${API_URL}/api/v1/imports`, { method: "POST", body });
    if (!response.ok) { setMessage("Upload failed. Check the file and your session."); return; }
    setJob(await response.json());
  };

  const signOut = () => { window.localStorage.removeItem("mosaic_access_token"); setToken(""); setJob(null); };
  const switchMode = (mode: AuthMode) => { setAuthMode(mode); setAuthMessage(""); };

  return <div className="app-shell">
    <header className="topbar"><a className="brand" href="/">MOSAIC<span>.</span></a><nav><a className="active" href="#overview">Overview</a><a href="#ingestion">Data intake</a><a href="#network">Supply network</a></nav><div className="topbar-actions"><span className="connection"><i /> {apiStatus}</span>{token ? <button className="button button-ghost" onClick={signOut}>Sign out</button> : <a className="button button-gold" href="#access">Get started</a>}</div></header>
    <main>
      <section className="hero" id="overview"><div className="hero-copy"><p className="eyebrow">Supply-chain decision intelligence</p><h1>Make every supply decision <em>clearer.</em></h1><p className="hero-text">MOSAIC connects the signals across your supply chain so your team can see what is happening, understand why, and act with confidence.</p><div className="hero-actions"><a className="button button-gold" href="#access">Enter your workspace <span>→</span></a><a className="text-link" href="#ingestion">Explore data intake <span>↗</span></a></div></div><div className="hero-art" aria-hidden="true"><div className="art-grid" /><div className="art-orbit orbit-one" /><div className="art-orbit orbit-two" /><div className="art-node node-one" /><div className="art-node node-two" /><div className="art-node node-three" /><div className="art-label label-one">DEMAND</div><div className="art-label label-two">SUPPLY</div><div className="art-label label-three">ACTION</div></div></section>
      <section className="access-section" id="access"><div className="section-intro"><p className="eyebrow">Your operating picture</p><h2>Start with a clearer view.</h2><p>Securely connect your operational data and turn it into decisions your business can explain.</p></div>{!token ? <form className="auth-card" onSubmit={authenticate}><div className="card-heading"><span className="card-mark">✦</span><div><p className="eyebrow">MOSAIC workspace</p><h2>{authMode === "login" ? "Welcome back" : "Create your workspace"}</h2></div></div><div className="tabs"><button type="button" className={authMode === "login" ? "selected" : ""} onClick={() => switchMode("login")}>Sign in</button><button type="button" className={authMode === "register" ? "selected" : ""} onClick={() => switchMode("register")}>Register</button></div>{authMode === "register" && <label>Name<input value={name} onChange={(event) => setName(event.target.value)} placeholder="Your name" required /></label>}<label>Email<input type="email" value={email} onChange={(event) => setEmail(event.target.value)} placeholder="you@company.com" required /></label><label>Password<input type="password" value={password} onChange={(event) => setPassword(event.target.value)} placeholder="At least 12 characters" minLength={12} required /></label><button className="button button-dark submit-button" type="submit">{authMode === "login" ? "Sign in to MOSAIC" : "Create workspace"}<span>→</span></button>{authMessage && <p className={authMessage === "Workspace created" || authMessage === "Signed in successfully" ? "success-message" : "error-message"}>{authMessage}</p>}<p className="privacy-note">Your workspace is tenant-isolated and protected.</p></form> : <form className="auth-card import-form" id="ingestion" onSubmit={submitImport}><div className="card-heading"><span className="card-mark">↗</span><div><p className="eyebrow">Data intake</p><h2>Import sales history</h2></div></div><p className="card-description">Upload a CSV and MOSAIC will validate, normalize, and stage it safely.</p><label className="file-drop"><input type="file" accept=".csv,text/csv" onChange={(event: ChangeEvent<HTMLInputElement>) => setFile(event.target.files?.[0] ?? null)} /><span className="upload-icon">↑</span><strong>{file ? file.name : "Choose a CSV file"}</strong><small>{file ? `${(file.size / 1024).toFixed(1)} KB selected` : "Maximum file size: 25 MB"}</small></label><button className="button button-dark submit-button" type="submit" disabled={!file}>Start secure import <span>→</span></button>{job && <p className="summary">Job {job.id.slice(0, 8)} · {job.status} · {job.successful_rows}/{job.total_rows} rows accepted{job.failed_rows ? ` · ${job.failed_rows} rejected` : ""}</p>}{message && <p className="error-message">{message}</p>}{errors.length > 0 && <ul className="error-list">{errors.map((error) => <li key={`${error.row_number}-${error.message}`}>Row {error.row_number}{error.field_name ? ` (${error.field_name})` : ""}: {error.message}</li>)}</ul>}</form>}</section>
      <section className="feature-strip" id="network"><div><span className="feature-number">01</span><h3>Connect the signals</h3><p>Bring sales, inventory, suppliers, and warehouses into one decision picture.</p></div><div><span className="feature-number">02</span><h3>Understand the risk</h3><p>Separate the noise from the operational conditions that need attention.</p></div><div><span className="feature-number">03</span><h3>Choose with confidence</h3><p>Make explainable decisions today and learn from their outcomes tomorrow.</p></div></section>
    </main><footer><span className="brand">MOSAIC<span>.</span></span><span>Decision intelligence for resilient supply chains.</span><span className="connection"><i /> {apiStatus}</span></footer>
  </div>;
}

createRoot(document.getElementById("root")!).render(<StrictMode><App /></StrictMode>);
