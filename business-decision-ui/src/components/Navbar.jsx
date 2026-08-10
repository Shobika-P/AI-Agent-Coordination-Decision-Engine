function Navbar({ activeTab, setActiveTab, onOpenHistory, onOpenMonitoring }) {
    return (
        <header className="navbar">
            <div className="navbar-container">
                <div className="navbar-brand">
                    <div className="navbar-logo-icon">
                        🤖
                    </div>
                    <div className="navbar-brand-text">
                        <span className="brand-title">AI Business Decision Engine</span>
                        <span className="brand-subtitle">Enterprise Strategic Platform</span>
                    </div>
                </div>

                <nav className="nav-menu">
                    <button
                        className={`nav-item ${activeTab === "engine" ? "active" : ""}`}
                        onClick={() => setActiveTab("engine")}
                    >
                        Decision Engine
                    </button>
                    <button
                        className="nav-item"
                        onClick={onOpenHistory}
                    >
                        Decision Log
                    </button>
                    <button
                        className="nav-item"
                        onClick={onOpenMonitoring}
                    >
                        Monitoring & Telemetry
                    </button>
                </nav>

                <div className="navbar-right">
                    <span className="system-status-badge">
                        <span className="status-indicator"></span>
                        System Operational
                    </span>

                    <button
                        className="navbar-monitoring-btn"
                        onClick={onOpenMonitoring}
                        title="View engine telemetry"
                    >
                        📊 Metrics
                    </button>
                </div>
            </div>
        </header>
    );
}

export default Navbar;