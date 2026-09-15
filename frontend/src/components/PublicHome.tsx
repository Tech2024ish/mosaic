export function PublicHome() {
  return (
    <>
      <section className="hero" id="overview">
        <div className="hero-copy">
          <p className="eyebrow">Supply-chain decision intelligence</p>
          <h1>Complex supply-chain data made clear enough to act on.</h1>
          <p className="hero-text">
            Bring operational data into one place, validate inventory, and monitor performance
            with calm, actionable intelligence.
          </p>
          <div className="hero-actions">
            <a className="button button-gold" href="#access">Get started</a>
            <a className="button button-ghost" href="#network">Explore platform</a>
          </div>
        </div>
        <div className="hero-art" aria-label="MOSAIC platform preview">
          <div className="preview-window">
            <div className="preview-browser"><span /><span /><span /><b>MOSAIC</b></div>
            <div className="preview-shell">
              <aside><strong>M</strong><span>Overview</span><span>Inventory</span><span>Analytics</span><span>Reports</span></aside>
              <div className="preview-content">
                <div className="preview-title"><div><b>MOSAIC Overview</b><small>A single view of supply-chain performance</small></div><span>Live data</span></div>
                <div className="preview-metrics">
                  <div><small>Total revenue</small><b>$25,539</b><i>+8.4%</i></div>
                  <div><small>Units sold</small><b>1,051</b><i>+12.2%</i></div>
                  <div><small>Active products</small><b>433</b><i>+6.1%</i></div>
                </div>
                <div className="preview-chart"><div className="preview-chart-heading"><b>Daily revenue trend</b><small>Weekly</small></div><div className="preview-lines"><span /><span /><span /><span /><span /><span /></div></div>
                <div className="preview-bottom"><div><b>Warehouse performance</b><span /><span /><span /></div><div><b>Operational insights</b><small>Inventory levels remain stable</small><small>Top product demand increased</small></div></div>
              </div>
            </div>
          </div>
        </div>
      </section>
    </>
  );
}

export function PublicFeatures() {
  return (
    <section className="feature-strip" id="network">
      <div><span className="feature-number">01.</span><h3>Data intake</h3><p>Automated pipeline for ingestion and validation.</p></div>
      <div><span className="feature-number">02.</span><h3>Analytics</h3><p>Multi-criteria sales and performance trends.</p></div>
      <div><span className="feature-number">03.</span><h3>Operations</h3><p>Real-time SKU and inventory visibility.</p></div>
      <div><span className="feature-number">04.</span><h3>Insights</h3><p>Clear signals from the data you already have.</p></div>
    </section>
  );
}

export function PublicFooter({ apiStatus }: { apiStatus: string }) {
  return (
    <footer className="public-footer">
      <div className="public-footer-main">
        <div className="public-footer-brand">
          <a className="brand" href="#overview">MOSAIC<span>.</span></a>
          <p>Decision intelligence for resilient supply chains.</p>
        </div>
        <div>
          <h2>Platform</h2>
          <a href="#network">Data intake</a>
          <a href="#network">Analytics</a>
          <a href="#network">Operations</a>
          <a href="#inventory">Inventory</a>
        </div>
        <div>
          <h2>Workspace</h2>
          <a href="#access">Sign in</a>
          <a href="#access">Create account</a>
          <a href="#network">Product overview</a>
        </div>
        <div>
          <h2>Company</h2>
          <a href="mailto:hello@mosaic.local">Contact</a>
          <a href="#network">Privacy</a>
          <a href="#network">Terms</a>
        </div>
      </div>
      <div className="public-footer-bottom">
        <span>© {new Date().getFullYear()} MOSAIC</span>
        <span className="connection"><i /> {apiStatus}</span>
      </div>
    </footer>
  );
}
