import { useState, useEffect } from "react";
import API from "../services/api";

function ReportLibraryModal({ isOpen, onClose, onSelectReport }) {
    const [reports, setReports] = useState([]);
    const [loading, setLoading] = useState(false);
    const [search, setSearch] = useState("");
    const [riskFilter, setRiskFilter] = useState("ALL");
    const [deletingId, setDeletingId] = useState(null);

    useEffect(() => {
        if (isOpen) {
            fetchReports();
        }
    }, [isOpen, search, riskFilter]);

    const fetchReports = async () => {
        setLoading(true);
        try {
            const res = await API.get(`/reports?search=${encodeURIComponent(search)}&risk=${encodeURIComponent(riskFilter)}`);
            if (res.data?.success) {
                setReports(res.data.reports || []);
            }
        } catch (err) {
            console.error("Error fetching report library:", err);
        } finally {
            setLoading(false);
        }
    };

    const handleDelete = async (e, reportId) => {
        e.stopPropagation();
        if (!window.confirm("Are you sure you want to delete this report from the library?")) return;

        setDeletingId(reportId);
        try {
            await API.delete(`/reports/${reportId}`);
            setReports((prev) => prev.filter((r) => r.report_id !== reportId));
        } catch (err) {
            alert("Failed to delete report.");
        } finally {
            setDeletingId(null);
        }
    };

    const handleSelect = async (reportId) => {
        try {
            const res = await API.get(`/reports/${reportId}`);
            if (res.data?.success && res.data?.report) {
                const rData = res.data.report;
                onSelectReport({
                    task: rData.original_question,
                    conversation_id: rData.report_id,
                    report: rData.report_data,
                    history: rData.conversation_history
                });
                onClose();
            }
        } catch (err) {
            alert("Failed to load selected report.");
        }
    };

    if (!isOpen) return null;

    return (
        <div className="modal-backdrop-overlay" onClick={onClose}>
            <div className="modal-content-container library-modal" onClick={(e) => e.stopPropagation()}>
                <div className="modal-header-bar">
                    <div>
                        <span className="modal-eyebrow">PERSISTENT DB STORAGE</span>
                        <h2 className="modal-title-text">Enterprise Report Library</h2>
                    </div>
                    <button className="btn-modal-close" onClick={onClose}>✕</button>
                </div>

                <div className="library-toolbar">
                    <div className="search-input-wrapper">
                        <span className="search-icon">🔍</span>
                        <input
                            type="text"
                            placeholder="Search reports by title, query, or decision..."
                            value={search}
                            onChange={(e) => setSearch(e.target.value)}
                        />
                    </div>

                    <div className="risk-filter-pills">
                        {["ALL", "LOW", "MEDIUM", "HIGH"].map((risk) => (
                            <button
                                key={risk}
                                className={`btn-filter-pill ${riskFilter === risk ? "active" : ""}`}
                                onClick={() => setRiskFilter(risk)}
                            >
                                {risk} RISK
                            </button>
                        ))}
                    </div>
                </div>

                <div className="library-grid-scroll">
                    {loading ? (
                        <div className="library-loading-state">
                            <span className="mini-spinner"></span>
                            <span>Loading reports from SQLite database...</span>
                        </div>
                    ) : reports.length === 0 ? (
                        <div className="library-empty-state">
                            <span className="empty-icon">📁</span>
                            <p>No saved reports found matching your criteria.</p>
                        </div>
                    ) : (
                        <div className="reports-cards-grid">
                            {reports.map((item) => {
                                const riskClass =
                                    item.risk_level?.toLowerCase() === "low"
                                        ? "badge-low"
                                        : item.risk_level?.toLowerCase() === "high"
                                        ? "badge-high"
                                        : "badge-medium";

                                const formattedDate = new Date(item.created_at).toLocaleDateString("en-US", {
                                    month: "short",
                                    day: "numeric",
                                    year: "numeric",
                                    hour: "2-digit",
                                    minute: "2-digit"
                                });

                                return (
                                    <div
                                        key={item.report_id}
                                        className="library-report-card"
                                        onClick={() => handleSelect(item.report_id)}
                                    >
                                        <div className="card-top-header">
                                            <span className={`risk-badge ${riskClass}`}>
                                                {item.risk_level?.toUpperCase() || "MEDIUM"} RISK
                                            </span>
                                            <span className="viability-chip">
                                                Viability: {item.viability_score || 78}/100
                                            </span>
                                        </div>

                                        <h3 className="card-report-title">{item.title}</h3>
                                        <p className="card-original-query">"{item.original_question}"</p>

                                        <div className="card-footer-bar">
                                            <span className="card-date">{formattedDate}</span>

                                            <div className="card-actions">
                                                <button
                                                    type="button"
                                                    className="btn-card-open"
                                                    onClick={() => handleSelect(item.report_id)}
                                                >
                                                    Open Report →
                                                </button>
                                                <button
                                                    type="button"
                                                    className="btn-card-delete"
                                                    disabled={deletingId === item.report_id}
                                                    onClick={(e) => handleDelete(e, item.report_id)}
                                                    title="Delete Report"
                                                >
                                                    🗑️
                                                </button>
                                            </div>
                                        </div>
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

export default ReportLibraryModal;
