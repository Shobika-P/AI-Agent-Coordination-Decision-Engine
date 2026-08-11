function Navbar({ onOpenLibrary, onOpenMonitoring, quotaStatus }) {
    return (
        <header className="navbar-container">
            <div className="navbar-left">
                <div className="brand-logo-icon">⚡</div>
                <div className="brand-text-group">
                    <h1 className="brand-title">DECISION ENGINE</h1>
                    <span className="brand-subtitle">Enterprise AI Business Decision Support Workspace</span>
                </div>
            </div>

            <div className="navbar-right">
                <span className={`status-pill ${quotaStatus === "demo" ? "orange" : "green"}`}>
                    <span className="pill-dot"></span>
                    {quotaStatus === "demo" ? "DEMO MODE (Quota Protected)" : "GEMINI API ONLINE"}
                </span>

                <button
                    type="button"
                    className="btn-nav-action"
                    onClick={onOpenLibrary}
                >
                    📁 Report Library
                </button>

                <button
                    type="button"
                    className="btn-nav-action secondary"
                    onClick={onOpenMonitoring}
                >
                    📊 System Status
                </button>
            </div>
        </header>
    );
}

export default Navbar;