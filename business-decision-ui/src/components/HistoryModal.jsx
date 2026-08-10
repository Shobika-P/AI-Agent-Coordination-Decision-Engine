import { useState, useEffect } from "react";
import API from "../services/api";

function HistoryModal({ isOpen, onClose, onSelectTask }) {
    const [history, setHistory] = useState([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState("");

    useEffect(() => {
        if (isOpen) {
            fetchHistory();
        }
    }, [isOpen]);

    const fetchHistory = async () => {
        setLoading(true);
        setError("");
        try {
            const response = await API.get("/history");
            if (response.data.success) {
                setHistory(response.data.history || []);
            } else {
                setError(response.data.error || "Failed to load history.");
            }
        } catch (err) {
            console.error("HISTORY FETCH ERROR:", err);
            setError("Unable to connect to server to fetch history.");
        } finally {
            setLoading(false);
        }
    };

    if (!isOpen) return null;

    return (
        <div className="modal-overlay" onClick={onClose}>
            <div className="modal-content" onClick={(e) => e.stopPropagation()}>
                <div className="modal-header">
                    <div>
                        <span className="modal-label">DECISION LOG</span>
                        <h2>Past Business Decisions</h2>
                    </div>
                    <button className="modal-close" onClick={onClose}>×</button>
                </div>

                <div className="modal-body">
                    {loading && (
                        <div className="history-loading">
                            🤖 Loading decision history...
                        </div>
                    )}

                    {error && (
                        <div className="history-error">
                            ⚠️ {error}
                        </div>
                    )}

                    {!loading && !error && history.length === 0 && (
                        <div className="history-empty">
                            No past decisions recorded yet.
                        </div>
                    )}

                    {!loading && !error && history.length > 0 && (
                        <div className="history-grid">
                            {history.slice().reverse().map((item, index) => {
                                const dateStr = item.timestamp
                                    ? new Date(item.timestamp).toLocaleString()
                                    : "Prior Run";
                                const risk = item.risk_level || "Medium";
                                const riskClass =
                                    risk.toLowerCase() === "low"
                                        ? "risk-low"
                                        : risk.toLowerCase() === "high"
                                            ? "risk-high"
                                            : "risk-medium";

                                // Extract short decision text
                                let decisionText = "";
                                if (typeof item.decision === "string") {
                                    decisionText = item.decision;
                                } else if (Array.isArray(item.decision)) {
                                    decisionText = item.decision.map(d => typeof d === 'string' ? d : d.text || '').join('\n');
                                } else {
                                    decisionText = JSON.stringify(item.decision);
                                }

                                const recommendationMatch = decisionText.match(/RECOMMEND[^\n\.\:]+/i);
                                const recBadge = recommendationMatch ? recommendationMatch[0] : "Decision Report";

                                return (
                                    <div key={index} className="history-card">
                                        <div className="history-card-header">
                                            <span className="history-date">{dateStr}</span>
                                            <span className={`history-risk-badge ${riskClass}`}>
                                                {risk} Risk
                                            </span>
                                        </div>

                                        <h4>{item.task}</h4>

                                        <div className="history-rec-tag">
                                            {recBadge}
                                        </div>

                                        <p className="history-preview">
                                            {decisionText.substring(0, 180)}...
                                        </p>

                                        {onSelectTask && (
                                            <button
                                                className="history-re-run-btn"
                                                onClick={() => {
                                                    onSelectTask(item.task);
                                                    onClose();
                                                }}
                                            >
                                                Rerun Analysis →
                                            </button>
                                        )}
                                    </div>
                                );
                            })}
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}

export default HistoryModal;
