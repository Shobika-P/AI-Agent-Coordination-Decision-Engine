import { useState, useEffect } from "react";
import API from "../services/api";

function MonitoringModal({ isOpen, onClose }) {
    const [metrics, setMetrics] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    useEffect(() => {
        if (isOpen) {
            fetchMetrics();
        }
    }, [isOpen]);

    const fetchMetrics = async () => {
        setLoading(true);
        setError(null);
        try {
            const res = await API.get("/monitoring");
            if (res.data?.success) {
                setMetrics(res.data.metrics);
            }
        } catch {
            setError("Failed to load telemetry metrics.");
        } finally {
            setLoading(false);
        }
    };

    if (!isOpen) return null;

    const gemini = metrics?.gemini_telemetry || {};
    const tokens = gemini.token_usage || {};

    return (
        <div className="modal-backdrop-overlay" onClick={onClose}>
            <div className="modal-content-container monitoring-modal" onClick={(e) => e.stopPropagation()}>
                <div className="modal-header-bar">
                    <div>
                        <span className="modal-eyebrow">SYSTEM TELEMETRY</span>
                        <h2 className="modal-title-text">AI Usage & Engine Status</h2>
                    </div>
                    <button className="btn-modal-close" onClick={onClose}>✕</button>
                </div>

                <div className="monitoring-body">
                    {loading ? (
                        <div className="telemetry-loading">
                            <span className="spinner-dot"></span>
                            <span>Fetching metrics...</span>
                        </div>
                    ) : error ? (
                        <div className="telemetry-error">{error}</div>
                    ) : (
                        <>
                            {/* QUOTA MODE STATUS CARD */}
                            <div className={`status-banner-card ${gemini.status === "LIVE" ? "active" : (gemini.status === "RECOVERING" ? "info" : "warning")}`}>
                                <div className="banner-status-icon">
                                    {gemini.status === "LIVE" ? "🟢" : (gemini.status === "RECOVERING" ? "🔄" : "⚡")}
                                </div>
                                <div className="banner-status-text">
                                    <h4>{gemini.mode || "LIVE"}</h4>
                                    <p>
                                        Model Chain: <strong>{(gemini.model_chain || [gemini.primary_model || "gemini-3.7-flash"]).join(" → ")}</strong> | Circuit State: <strong>{gemini.circuit_state || "CLOSED"}</strong>
                                    </p>
                                </div>
                            </div>


                            {/* TELEMETRY METRICS GRID */}
                            <div className="telemetry-grid">
                                <div className="metric-card-box">
                                    <small>LIVE LLM CALLS</small>
                                    <h3>{gemini.gemini_requests || 0}</h3>
                                </div>

                                <div className="metric-card-box">
                                    <small>CACHED RESPONSES</small>
                                    <h3>{gemini.cached_responses || 0}</h3>
                                </div>

                                <div className="metric-card-box">
                                    <small>FALLBACK RESPONSES</small>
                                    <h3>{gemini.fallback_responses || 0}</h3>
                                </div>

                                <div className="metric-card-box">
                                    <small>AVG LATENCY</small>
                                    <h3>{gemini.average_response_sec || 0} s</h3>
                                </div>
                            </div>

                            {/* TOKEN USAGE & STORAGE INFORMATION */}
                            <div className="telemetry-details-block">
                                <h4>Token Usage Telemetry</h4>
                                <div className="token-metrics-row">
                                    <div>Prompt Tokens: <strong>{tokens.prompt_tokens?.toLocaleString() || 0}</strong></div>
                                    <div>Completion Tokens: <strong>{tokens.completion_tokens?.toLocaleString() || 0}</strong></div>
                                    <div>Total Tokens: <strong>{tokens.total_tokens?.toLocaleString() || 0}</strong></div>
                                </div>

                                <h4 style={{ marginTop: "16px" }}>Database & Storage Status</h4>
                                <p><strong>Source of Truth:</strong> SQLite Database (<code>memory/decision_engine.db</code>)</p>
                                <p><strong>Total Persistent Decisions Logged:</strong> {metrics?.total_decisions || 0}</p>
                            </div>
                        </>
                    )}
                </div>
            </div>
        </div>
    );
}

export default MonitoringModal;
