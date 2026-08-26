import { StrictMode, useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import "./styles.css";

function App() {
  const [apiStatus, setApiStatus] = useState("checking API");
  useEffect(() => {
    fetch("http://localhost:8000/health")
      .then((response) => (response.ok ? response.json() : Promise.reject()))
      .then(() => setApiStatus("API connected"))
      .catch(() => setApiStatus("API unavailable"));
  }, []);
  return (
    <main className="shell">
      <p className="eyebrow">MOSAIC / decision intelligence</p>
      <h1>See the supply chain as a connected system.</h1>
      <p className="lede">The platform foundation is ready for data ingestion, forecasting, risk analysis, and explainable decisions.</p>
      <span className="status">{apiStatus}</span>
    </main>
  );
}

createRoot(document.getElementById("root")!).render(<StrictMode><App /></StrictMode>);
