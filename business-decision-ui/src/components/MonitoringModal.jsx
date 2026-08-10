import { useState, useEffect } from "react";
import API from "../services/api";

function MonitoringModal({ isOpen, onClose }) {
    const [metrics, setMetrics] = useState(null);
    const [loading, setLoading] = useState(false);

    useEffect(() => {
        if (isOpen) {
            fetchMonitoring();
        }
    }, [isOpen]);

    const fetchMonitoring = async () => {
        setLoading(true);
        try {
            const response = await API.get("/monitoring");
            if (response.data.success) {
                setMetrics(response.data.metrics);
            }
        } catch (err) {
            console.error("MONITORING FETCH ERROR:", err);
        } finally {
            setLoading(false);
        }
    };

    if (!isOpen) return null;

    return (
        <div className="modal-overlay" onClick={onClose}>
            <div className="modal-content monitoring-modal" onClick={(e) => e.stopPropagation()}>
                <div className="modal-header">
                    <div>
                        <span className="modal-label">TELEMETRY & MONITORING</span>
                        <h2>Agent System Dashboard</h2>
                    </div>
                    <button className="modal-close" onClick={onClose}>×</button>
                </div>

                <div className="modal-body">
                    {loading && (
                        <div className="monitoring-loading">
                            Fetching system telemetry...
                        </div>
                    )}

                    {!loading && metrics && (
                        <div className="monitoring-grid">
                            <div className="telemetry-card">
                                <span className="telemetry-label">DECISIONS PROCESSED</span>
                                <span className="telemetry-value">{metrics.total_decisions}</span>
                            </div>

                            <div className="telemetry-card">
                                <span className="telemetry-label">COMPLETED WORKFLOWS</span>
                                <span className="telemetry-value green">{metrics.completed_workflows}</span>
                            </div>

                            <div className="telemetry-card">
                                <span className="telemetry-label">MODEL STATUS</span>
                                <span className="telemetry-value">{metrics.model_status.toUpperCase()}</span>
                            </div>

                            <div className="telemetry-card">
                                <span className="telemetry-label">API HEALTH</span>
                                <span className="telemetry-value green">{metrics.api_status.toUpperCase()}</span>
                            </div>

                            <div className="agent-status-panel">
                                <h3>Agent Health Matrix</h3>
                                <div className="agent-health-rows">
                                    {Object.entries(metrics.agent_statuses || {}).map(([name, status]) => (
                                        <div key={name} className="health-row">
                                            <span className="health-name">{name.replace("_", " ").toUpperCase()}</span>
                                            <span className="health-badge operational">● {status}</span>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}

export default MonitoringModal;
