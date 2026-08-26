import { ChangeEvent, FormEvent, StrictMode, useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import "./styles.css";

function App() {
  const [apiStatus, setApiStatus] = useState("checking API");
  const [file, setFile] = useState<File | null>(null);
  const [job, setJob] = useState<{ id: string; status: string; total_rows: number; successful_rows: number; failed_rows: number } | null>(null);
  const [errors, setErrors] = useState<Array<{ row_number: number; message: string; field_name: string | null }>>([]);
  const [message, setMessage] = useState("");
  useEffect(() => {
    fetch("http://localhost:8000/health")
      .then((response) => (response.ok ? response.json() : Promise.reject()))
      .then(() => setApiStatus("API connected"))
      .catch(() => setApiStatus("API unavailable"));
  }, []);
  useEffect(() => {
    if (!job || ["completed", "failed"].includes(job.status)) return;
    const timer = window.setInterval(async () => {
      const response = await fetch(`http://localhost:8000/api/v1/imports/${job.id}`);
      if (response.ok) setJob(await response.json());
    }, 1000);
    return () => window.clearInterval(timer);
  }, [job]);
  useEffect(() => {
    if (job?.status !== "completed" && job?.status !== "failed") return;
    fetch(`http://localhost:8000/api/v1/imports/${job.id}/errors`)
      .then((response) => response.ok ? response.json() : [])
      .then(setErrors);
  }, [job?.status, job?.id]);
  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (!file) return;
    setMessage(""); setErrors([]);
    const body = new FormData(); body.append("file", file); body.append("dataset_type", "sales_history");
    const response = await fetch("http://localhost:8000/api/v1/imports", { method: "POST", body });
    if (!response.ok) { setMessage((await response.json()).detail ?? "Upload failed"); return; }
    setJob(await response.json());
  };
  return (
    <main className="shell">
      <p className="eyebrow">MOSAIC / decision intelligence</p>
      <h1>See the supply chain as a connected system.</h1>
      <p className="lede">The platform foundation is ready for data ingestion, forecasting, risk analysis, and explainable decisions.</p>
      <span className="status">{apiStatus}</span>
      <form className="import-card" onSubmit={submit}>
        <h2>Import sales history</h2>
        <input type="file" accept=".csv,text/csv" onChange={(event: ChangeEvent<HTMLInputElement>) => setFile(event.target.files?.[0] ?? null)} />
        <button type="submit" disabled={!file}>Start import</button>
        {message && <p className="error">{message}</p>}
        {job && <p className="summary">Job {job.id.slice(0, 8)} · {job.status} · {job.successful_rows}/{job.total_rows} rows accepted{job.failed_rows ? ` · ${job.failed_rows} rejected` : ""}</p>}
        {errors.length > 0 && <ul>{errors.map((error) => <li key={`${error.row_number}-${error.message}`}>Row {error.row_number}{error.field_name ? ` (${error.field_name})` : ""}: {error.message}</li>)}</ul>}
      </form>
    </main>
  );
}

createRoot(document.getElementById("root")!).render(<StrictMode><App /></StrictMode>);
