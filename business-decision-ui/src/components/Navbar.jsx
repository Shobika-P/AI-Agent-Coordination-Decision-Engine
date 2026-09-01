function Navbar({ onOpenLibrary, onOpenMonitoring, quotaStatus, currentUser, onLogout }) {
    let pillClass = "green";
    let pillText = "GEMINI API LIVE";

    if (quotaStatus === "TEMPORARILY_UNAVAILABLE" || quotaStatus === "temporary_ai_unavailable") {
        pillClass = "orange";
        pillText = "AI SERVICE BUSY";
    } else if (quotaStatus === "RATE_LIMITED" || quotaStatus === "rate_limited" || quotaStatus === "quota_exhausted") {
        pillClass = "orange";
        pillText = "RATE LIMITED";
    } else if (quotaStatus === "RECOVERING") {
        pillClass = "blue";
        pillText = "RECOVERING";
    } else if (quotaStatus === "CONFIGURATION_ERROR" || quotaStatus === "offline" || quotaStatus === "configuration_error") {
        pillClass = "red";
        pillText = "CONFIG ERROR";
    } else if (quotaStatus === "checking") {
        pillClass = "blue";
        pillText = "SYSTEM ONLINE";
    }

    return (
        <header className="navbar-container">
            <div className="navbar-left">
                <div className="brand-logo-icon">⚡</div>
                <div className="brand-text-group">
                    <h1 className="brand-title">DECISION ENGINE</h1>
                    <span className="brand-subtitle">Enterprise Workflow Platform & Decision Automation System</span>
                </div>
            </div>

            <div className="navbar-right">
                <span className={`status-pill ${pillClass}`}>
                    <span className="pill-dot"></span>
                    {pillText}
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

                {currentUser && (
                    <div className="nav-user-group">
                        <span className="nav-user-badge" title={currentUser.email}>
                            👤 <span className="nav-user-email">{currentUser.email}</span>
                        </span>
                        <button
                            type="button"
                            className="btn-nav-action logout-btn"
                            onClick={onLogout}
                            title="Sign out of your account"
                        >
                            Sign Out
                        </button>
                    </div>
                )}
            </div>
        </header>
    );
}

export default Navbar;