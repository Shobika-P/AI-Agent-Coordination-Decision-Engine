import { useState, useRef, useEffect } from "react";
import API from "../services/api";
import WhatIfPanel from "./WhatIfPanel";

function safeParseJson(input) {
    if (input === null || input === undefined) return input;
    if (typeof input === "object") return input;
    if (typeof input !== "string") return input;

    const trimmed = input.trim();
    if (
        (trimmed.startsWith("{") && trimmed.endsWith("}")) ||
        (trimmed.startsWith("[") && trimmed.endsWith("]"))
    ) {
        try {
            return JSON.parse(trimmed);
        } catch {
            return input;
        }
    }
    return input;
}

function formatKeyLabel(key) {
    if (!key) return "";
    return String(key)
        .replace(/_/g, " ")
        .replace(/([a-z])([A-Z])/g, "$1 $2")
        .replace(/\b\w/g, (char) => char.toUpperCase());
}

function safeString(value, fallback = "") {
    if (value === null || value === undefined) return fallback;
    const parsed = safeParseJson(value);
    if (typeof parsed === "string") return parsed;
    if (typeof parsed === "number" || typeof parsed === "boolean") return String(parsed);
    if (Array.isArray(parsed)) {
        return parsed.map((item) => safeString(item)).join("\n");
    }
    if (typeof parsed === "object") {
        return toReadableText(parsed);
    }
    return fallback;
}

function toReadableText(value, level = 0) {
    if (value === null || value === undefined) return "";
    const parsed = safeParseJson(value);

    if (typeof parsed === "string") return parsed;
    if (typeof parsed === "number" || typeof parsed === "boolean") return String(parsed);

    const indent = "  ".repeat(level);

    if (Array.isArray(parsed)) {
        return parsed.map((item) => `${indent}• ${toReadableText(item, level + 1)}`).join("\n");
    }

    if (typeof parsed === "object") {
        return Object.entries(parsed)
            .map(([k, v]) => {
                const label = formatKeyLabel(k);
                const valText = toReadableText(v, level + 1);
                const parsedV = safeParseJson(v);
                if (typeof parsedV === "object" && parsedV !== null) {
                    return `${indent}${label}:\n${valText}`;
                }
                return `${indent}${label}: ${valText}`;
            })
            .join("\n");
    }

    return String(parsed);
}

function StructuredDataRenderer({ value, depth = 0 }) {
    if (value === null || value === undefined) return null;

    const parsed = safeParseJson(value);

    if (typeof parsed === "boolean" || typeof parsed === "number") {
        return <span className="summary-text">{String(parsed)}</span>;
    }

    if (typeof parsed === "string") {
        return <p className="summary-text">{parsed}</p>;
    }

    if (Array.isArray(parsed)) {
        if (parsed.length === 0) return null;
        return (
            <ul className="structured-list">
                {parsed.map((item, idx) => {
                    const parsedItem = safeParseJson(item);
                    return (
                        <li key={idx} className="structured-list-item">
                            {typeof parsedItem === "object" && parsedItem !== null ? (
                                <StructuredDataRenderer value={parsedItem} depth={depth + 1} />
                            ) : (
                                <span>{safeString(parsedItem)}</span>
                            )}
                        </li>
                    );
                })}
            </ul>
        );
    }

    if (typeof parsed === "object") {
        const entries = Object.entries(parsed);
        if (entries.length === 0) return null;

        return (
            <div className={`structured-object-card depth-${depth}`}>
                {entries.map(([key, val]) => {
                    const label = formatKeyLabel(key);
                    const parsedVal = safeParseJson(val);
                    const isPrimitive =
                        typeof parsedVal === "string" ||
                        typeof parsedVal === "number" ||
                        typeof parsedVal === "boolean";
                    const isRiskKey =
                        key.toLowerCase().includes("risk") &&
                        typeof parsedVal === "string" &&
                        ["low", "medium", "high"].includes(parsedVal.toLowerCase());

                    return (
                        <div key={key} className="structured-field-block">
                            <h5 className="field-label">{label}</h5>
                            {isRiskKey ? (
                                <span className={`risk-pill-badge risk-badge-${parsedVal.toLowerCase()}`}>
                                    {parsedVal.toUpperCase()} RISK
                                </span>
                            ) : isPrimitive ? (
                                <p className="field-value-text">{String(parsedVal)}</p>
                            ) : (
                                <StructuredDataRenderer value={parsedVal} depth={depth + 1} />
                            )}
                        </div>
                    );
                })}
            </div>
        );
    }

    return <span className="summary-text">{String(parsed)}</span>;
}

function ReportViewer({
    report,
    task,
    loading,
    error,
    quotaNotice,
    followupMessages = [],
    onFollowup,
    onClearFollowup,
    onRetry
}) {
    const [localFollowupText, setLocalFollowupText] = useState("");
    const [showExportMenu, setShowExportMenu] = useState(false);
    const [exporting, setExporting] = useState(false);
    const [toastMsg, setToastMsg] = useState("");
    const [dynamicViability, setDynamicViability] = useState(null);
    const [dynamicRisk, setDynamicRisk] = useState(null);

    const threadEndRef = useRef(null);

    useEffect(() => {
        if (followupMessages.length > 0) {
            threadEndRef.current?.scrollIntoView({ behavior: "smooth" });
        }
    }, [followupMessages]);

    useEffect(() => {
        setDynamicViability(null);
        setDynamicRisk(null);
    }, [report]);

    const parsedReport = safeParseJson(report);

    const defaultChips = [
        "Why is the market risk medium?",
        "How can we lower customer acquisition cost?",
        "What happens if sales volume drops by 20%?",
        "What are our top 3 execution priorities?"
    ];

    const suggestedChips =
        Array.isArray(parsedReport?.suggested_followups) && parsedReport.suggested_followups.length > 0
            ? parsedReport.suggested_followups
            : defaultChips;

    const handleExport = async (format) => {
        setShowExportMenu(false);

        if (format === "copy") {
            const decisionText = toReadableText(parsedReport?.decision || parsedReport);
            const riskText = safeString(dynamicRisk || parsedReport?.risk_level || parsedReport?.tool_analysis?.risk_level, "Medium");
            const copyContent = `ENTERPRISE AI DECISION REPORT\nQuery: ${task}\nRisk Level: ${riskText}\nViability Score: ${dynamicViability || parsedReport?.viability_score || 78}/100\n\n${decisionText}`;
            navigator.clipboard.writeText(copyContent);
            setToastMsg("Report copied to clipboard!");
            setTimeout(() => setToastMsg(""), 3000);
            return;
        }

        if (format === "print") {
            window.print();
            return;
        }

        setExporting(true);
        try {
            const response = await API.post(
                "/export-report",
                {
                    task: task || "Business Decision Query",
                    report: parsedReport,
                    conversation_history: followupMessages.map((m) => ({ question: m.question, answer: toReadableText(m.answer) })),
                    format: format
                },
                { responseType: format === "pdf" ? "blob" : "text" }
            );

            if (format === "pdf") {
                const blob = new Blob([response.data], { type: "application/pdf" });
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement("a");
                a.href = url;
                a.download = `Decision_Report_${Date.now().toString().slice(-6)}.pdf`;
                document.body.appendChild(a);
                a.click();
                a.remove();
                window.URL.revokeObjectURL(url);
            } else if (format === "json") {
                const blob = new Blob(
                    [typeof response.data === "string" ? response.data : JSON.stringify(response.data, null, 2)],
                    { type: "application/json" }
                );
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement("a");
                a.href = url;
                a.download = `Decision_Report_${Date.now().toString().slice(-6)}.json`;
                document.body.appendChild(a);
                a.click();
                a.remove();
            } else if (format === "markdown") {
                const blob = new Blob([response.data], { type: "text/markdown" });
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement("a");
                a.href = url;
                a.download = `Decision_Report_${Date.now().toString().slice(-6)}.md`;
                document.body.appendChild(a);
                a.click();
                a.remove();
            }
            setToastMsg(`Exported report as ${format.toUpperCase()}`);
            setTimeout(() => setToastMsg(""), 3000);
        } catch (err) {
            console.error("EXPORT ERROR:", err);
            alert("Failed to export report document.");
        } finally {
            setExporting(false);
        }
    };

    if (loading) {
        return (
            <section className="report-container">
                <div className="empty-state-card">
                    <span className="spinner-dot" style={{ width: "24px", height: "24px", borderWidth: "3px" }}></span>
                    <h3 style={{ marginTop: "16px", color: "var(--text-main)", fontSize: "20px" }}>
                        Analyzing Business Decision...
                    </h3>
                    <p>
                        LangGraph multi-agent orchestration graph is running quantitative models, market research,
                        and decision intelligence synthesis.
                    </p>
                </div>
            </section>
        );
    }

    if (error && !parsedReport) {
        const errorTitle = typeof error === "object" && error.title ? error.title : "AI Service Temporarily Busy";
        const errorMsg =
            typeof error === "object" && error.message
                ? error.message
                : safeString(error, "We could not complete the live AI analysis at this moment. Please retry in a few seconds.");

        return (
            <section className="report-container">
                <div className="error-card" style={{ maxWidth: "600px", margin: "40px auto", textAlign: "center", padding: "36px 24px" }}>
                    <div className="error-icon" style={{ fontSize: "36px", marginBottom: "12px" }}>⚡</div>
                    <h3 style={{ fontSize: "20px", fontWeight: "700", color: "var(--text-main, #f3f4f6)", marginBottom: "8px" }}>
                        {errorTitle}
                    </h3>
                    <p style={{ fontSize: "14.5px", lineHeight: "1.6", color: "var(--text-secondary, #9ca3af)", margin: "0 auto 20px" }}>
                        {errorMsg}
                    </p>
                    {onRetry && (
                        <button className="btn-retry-action" onClick={onRetry} style={{ padding: "10px 22px", fontSize: "14px", fontWeight: "600", borderRadius: "6px", cursor: "pointer" }}>
                            🔄 Retry Analysis
                        </button>
                    )}
                </div>
            </section>
        );
    }


    if (!parsedReport) {
        return (
            <section className="report-container empty-state-card">
                <div className="empty-badge">ENTERPRISE DECISION WORKSPACE</div>
                <h2>Awaiting Business Query</h2>
                <p>
                    Submit a strategic business question above to initiate autonomous multi-agent analysis,
                    risk modeling, financial tool calculations, and decision intelligence.
                </p>
                <div className="empty-features-grid">
                    <div className="feature-item">
                        <span>🔍</span>
                        <strong>Research Agent</strong>
                        <p>Evaluates market demand and competitor positioning</p>
                    </div>
                    <div className="feature-item">
                        <span>📊</span>
                        <strong>Quantitative Tools</strong>
                        <p>Calculates profit, ROI, break-even & market risk</p>
                    </div>
                    <div className="feature-item">
                        <span>🚀</span>
                        <strong>Planning Agent</strong>
                        <p>Formulates phased strategic execution roadmap</p>
                    </div>
                    <div className="feature-item">
                        <span>⚖️</span>
                        <strong>Decision Agent</strong>
                        <p>Delivers Viability Score & actionable recommendation</p>
                    </div>
                </div>
            </section>
        );
    }

    const isObjReport = typeof parsedReport === "object" && parsedReport !== null;

    const viabilityScore = dynamicViability || (isObjReport ? parsedReport.viability_score : null) || 78;
    const confidenceScore = (isObjReport ? parsedReport.confidence : null) || 82;

    const riskLevelStr = safeString(
        dynamicRisk ||
            (isObjReport ? parsedReport.risk_level || parsedReport.tool_analysis?.risk_level : null),
        "Medium"
    );
    const normalizedRisk = riskLevelStr.toLowerCase();
    const riskBadgeClass =
        normalizedRisk === "low"
            ? "risk-badge-low"
            : normalizedRisk === "high"
            ? "risk-badge-high"
            : "risk-badge-medium";

    const decisionValue = isObjReport ? parsedReport.decision : parsedReport;
    const whyThisDecision = isObjReport && Array.isArray(parsedReport.why_this_decision) ? parsedReport.why_this_decision : [];
    const keyRisks = isObjReport && Array.isArray(parsedReport.key_risks) ? parsedReport.key_risks : [];
    const keyOpportunities = isObjReport && Array.isArray(parsedReport.key_opportunities) ? parsedReport.key_opportunities : [];
    const recommendedDecision = isObjReport ? (parsedReport.recommended_decision || parsedReport.recommendation_title) : "";
    const implementationRoadmap = isObjReport && Array.isArray(parsedReport.implementation_roadmap) ? parsedReport.implementation_roadmap : [];
    const successMetrics = isObjReport && Array.isArray(parsedReport.success_metrics) ? parsedReport.success_metrics : [];
    const conditionsAndAssumptions = isObjReport && Array.isArray(parsedReport.conditions_and_assumptions) ? parsedReport.conditions_and_assumptions : [];
    const conclusionText = isObjReport ? parsedReport.conclusion : "";
    const toolAnalysis = isObjReport ? parsedReport.tool_analysis : null;

    // Filter dynamic extra properties for custom AI outputs
    const knownKeys = new Set([
        "decision",
        "viability_score",
        "confidence",
        "risk_level",
        "why_this_decision",
        "key_risks",
        "key_opportunities",
        "tool_analysis",
        "recommended_decision",
        "recommendation_title",
        "implementation_roadmap",
        "success_metrics",
        "conditions_and_assumptions",
        "conclusion",
        "execution_metrics",
        "title",
        "task"
    ]);

    const isAnyFollowupLoading = followupMessages.some((msg) => msg.loading);

    const handleSendFollowup = (textToSend) => {
        const queryText = textToSend || localFollowupText;
        if (!queryText.trim() || isAnyFollowupLoading) return;
        onFollowup(queryText.trim());
        setLocalFollowupText("");
    };

    const analysisSource = isObjReport
        ? parsedReport.analysis_source || (parsedReport.is_demo ? "FALLBACK" : "LIVE_AI")
        : "LIVE_AI";

    return (
        <section className="report-container">
            {/* NOTICE BANNER */}
            {quotaNotice && (
                <div className="quota-notice-banner">
                    <span className="banner-icon">⚡</span>
                    <span>{quotaNotice}</span>
                </div>
            )}

            {/* EXECUTIVE REPORT CARD */}
            <div className="executive-report-card">
                {/* METADATA HEADER */}
                <div className="report-meta-header">
                    <div className="report-meta-left">
                        <span className="meta-eyebrow">AI DECISION INTELLIGENCE</span>
                        <h2 className="report-meta-title">Executive Strategic Assessment</h2>
                    </div>

                    <div className="report-meta-right">
                        <div className="export-dropdown-wrapper">
                            <button
                                className="btn-export-trigger"
                                onClick={() => setShowExportMenu(!showExportMenu)}
                                disabled={exporting}
                            >
                                <span>📥 Export Report</span>
                                <span className="dropdown-caret">▼</span>
                            </button>

                            {showExportMenu && (
                                <div className="export-menu-dropdown">
                                    <button onClick={() => handleExport("pdf")}>📄 Download PDF Report</button>
                                    <button onClick={() => handleExport("json")}>📊 Download JSON Data</button>
                                    <button onClick={() => handleExport("markdown")}>📝 Download Markdown</button>
                                    <button onClick={() => handleExport("copy")}>📋 Copy Report Text</button>
                                    <button onClick={() => handleExport("print")}>🖨️ Print Document</button>
                                </div>
                            )}
                        </div>

                        {toastMsg && (
                            <div className="toast-notification-inline">
                                <span>{toastMsg}</span>
                            </div>
                        )}

                        {analysisSource === "LIVE_AI" && (
                            <span className="status-pill green" title="Generated live by Gemini Multi-Agent Workflow">
                                <span className="pill-dot"></span>
                                Live AI Analysis
                            </span>
                        )}
                        {analysisSource === "LIVE_CACHE" && (
                            <span className="status-pill blue" title="Returned from in-memory query cache" style={{ background: "rgba(59, 130, 246, 0.15)", color: "#60a5fa", border: "1px solid rgba(59, 130, 246, 0.3)" }}>
                                <span className="pill-dot" style={{ background: "#3b82f6" }}></span>
                                Cached Analysis
                            </span>
                        )}
                        {analysisSource === "FALLBACK" && (
                            <span className="status-pill orange" title="Generated via offline structured fallback protection mode" style={{ background: "rgba(245, 158, 11, 0.15)", color: "#fbbf24", border: "1px solid rgba(245, 158, 11, 0.3)" }}>
                                <span className="pill-dot" style={{ background: "#f59e0b" }}></span>
                                Offline Fallback
                            </span>
                        )}
                    </div>
                </div>

                {/* DECISION INTELLIGENCE SCORECARDS */}
                <div className="intelligence-scorecard-grid">
                    <div className="scorecard-item">
                        <span className="scorecard-label">BUSINESS VIABILITY</span>
                        <div className="scorecard-value-group">
                            <span className="scorecard-number">{viabilityScore}</span>
                            <span className="scorecard-max">/ 100</span>
                        </div>
                        <div className="scorecard-bar-track">
                            <div className="scorecard-bar-fill blue" style={{ width: `${viabilityScore}%` }}></div>
                        </div>
                    </div>

                    <div className="scorecard-item">
                        <span className="scorecard-label">AI CONFIDENCE</span>
                        <div className="scorecard-value-group">
                            <span className="scorecard-number green">{confidenceScore}%</span>
                        </div>
                        <div className="scorecard-bar-track">
                            <div className="scorecard-bar-fill green" style={{ width: `${confidenceScore}%` }}></div>
                        </div>
                    </div>

                    <div className="scorecard-item">
                        <span className="scorecard-label">MARKET RISK LEVEL</span>
                        <div className="scorecard-value-group">
                            <span className={`risk-pill-badge ${riskBadgeClass}`}>
                                {riskLevelStr.toUpperCase()} RISK
                            </span>
                        </div>
                        <small className="scorecard-subtext">Quantified by Multi-Agent Engine</small>
                    </div>
                </div>

                {/* 01. EXECUTIVE SUMMARY BLOCK */}
                <div className="report-section-block">
                    <div className="section-header-title">
                        <span className="section-num">01</span>
                        <div>
                            <small className="section-tag">EXECUTIVE RECOMMENDATION</small>
                            <h3 className="section-heading">Executive Summary</h3>
                        </div>
                    </div>
                    <div className="summary-card-body">
                        <StructuredDataRenderer value={decisionValue} />
                    </div>
                </div>

                {/* 02. STRATEGIC DRIVERS / WHY THIS DECISION */}
                {whyThisDecision.length > 0 && (
                    <div className="report-section-block">
                        <h4 className="drivers-title">Strategic Drivers (Why This Decision?)</h4>
                        <div className="drivers-grid">
                            {whyThisDecision.map((driver, idx) => (
                                <div key={idx} className="driver-chip-item">
                                    <span className="driver-icon">✓</span>
                                    <span className="driver-text">{safeString(driver)}</span>
                                </div>
                            ))}
                        </div>
                    </div>
                )}

                {/* 03 & 04. RISKS & OPPORTUNITIES GRID */}
                {(keyRisks.length > 0 || keyOpportunities.length > 0) && (
                    <div className="risks-opportunities-grid">
                        {keyRisks.length > 0 && (
                            <div className="risk-box-card">
                                <h4 className="box-heading risk">⚠️ Key Risk Factors</h4>
                                <ul>
                                    {keyRisks.map((riskItem, idx) => (
                                        <li key={idx}>
                                            <StructuredDataRenderer value={riskItem} />
                                        </li>
                                    ))}
                                </ul>
                            </div>
                        )}

                        {keyOpportunities.length > 0 && (
                            <div className="opportunity-box-card">
                                <h4 className="box-heading opportunity">✦ Strategic Opportunities</h4>
                                <ul>
                                    {keyOpportunities.map((oppItem, idx) => (
                                        <li key={idx}>
                                            <StructuredDataRenderer value={oppItem} />
                                        </li>
                                    ))}
                                </ul>
                            </div>
                        )}
                    </div>
                )}

                {/* 05. RECOMMENDED DECISION STATEMENT */}
                {recommendedDecision && (
                    <div className="report-section-block">
                        <div className="recommended-decision-card" style={{ background: "rgba(37, 99, 235, 0.08)", border: "1px solid rgba(37, 99, 235, 0.25)", borderRadius: "8px", padding: "16px 20px" }}>
                            <small style={{ color: "var(--accent-color, #3b82f6)", fontSize: "11px", fontWeight: "700", letterSpacing: "1px", textTransform: "uppercase" }}>RECOMMENDED DECISION</small>
                            <h4 style={{ color: "var(--text-main, #f3f4f6)", fontSize: "16px", fontWeight: "700", marginTop: "4px", marginBottom: 0 }}>{safeString(recommendedDecision)}</h4>
                        </div>
                    </div>
                )}

                {/* 06. IMPLEMENTATION ROADMAP */}
                {Array.isArray(implementationRoadmap) && implementationRoadmap.length > 0 && (
                    <div className="report-section-block">
                        <div className="section-header-title">
                            <span className="section-num">02</span>
                            <div>
                                <small className="section-tag">EXECUTION ROADMAP</small>
                                <h3 className="section-heading">Implementation Roadmap</h3>
                            </div>
                        </div>
                        <div className="roadmap-phases-grid" style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "16px", marginTop: "12px" }}>
                            {implementationRoadmap.map((item, idx) => (
                                <div key={idx} className="roadmap-phase-card" style={{ background: "var(--bg-card, #111827)", border: "1px solid var(--border-color, #1f2937)", borderRadius: "8px", padding: "16px" }}>
                                    <h4 style={{ color: "var(--accent-color, #3b82f6)", fontSize: "14px", fontWeight: "700", marginBottom: "10px", borderBottom: "1px solid var(--border-color, #374151)", paddingBottom: "6px" }}>
                                        {safeString(item.phase || item.title || `Phase ${idx + 1}`)}
                                    </h4>
                                    {Array.isArray(item.steps) ? (
                                        <ul style={{ paddingLeft: "16px", margin: 0, fontSize: "13px", color: "var(--text-secondary, #9ca3af)", display: "flex", flexDirection: "column", gap: "6px" }}>
                                            {item.steps.map((step, sIdx) => (
                                                <li key={sIdx}>{safeString(step)}</li>
                                            ))}
                                        </ul>
                                    ) : (
                                        <p style={{ fontSize: "13px", color: "var(--text-secondary, #9ca3af)", margin: 0 }}>{safeString(item.steps || item.description)}</p>
                                    )}
                                </div>
                            ))}
                        </div>
                    </div>
                )}

                {/* 07. SUCCESS METRICS */}
                {Array.isArray(successMetrics) && successMetrics.length > 0 && (
                    <div className="report-section-block">
                        <div className="section-header-title">
                            <span className="section-num">03</span>
                            <div>
                                <small className="section-tag">TARGET BENCHMARKS</small>
                                <h3 className="section-heading">Success Metrics</h3>
                            </div>
                        </div>
                        <div className="success-metrics-grid" style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "12px", marginTop: "12px" }}>
                            {successMetrics.map((metric, idx) => (
                                <div key={idx} className="metric-chip-card" style={{ background: "rgba(16, 185, 129, 0.08)", border: "1px solid rgba(16, 185, 129, 0.2)", borderRadius: "8px", padding: "12px 16px", display: "flex", alignItems: "center", gap: "10px" }}>
                                    <span style={{ color: "#10b981", fontWeight: "bold" }}>🎯</span>
                                    <span style={{ fontSize: "13.5px", fontWeight: "600", color: "var(--text-main, #f3f4f6)" }}>{safeString(metric)}</span>
                                </div>
                            ))}
                        </div>
                    </div>
                )}

                {/* 08. CONDITIONS & ASSUMPTIONS */}
                {Array.isArray(conditionsAndAssumptions) && conditionsAndAssumptions.length > 0 && (
                    <div className="report-section-block">
                        <h4 className="drivers-title" style={{ color: "#eab308" }}>Conditions & Baseline Assumptions</h4>
                        <div className="drivers-grid">
                            {conditionsAndAssumptions.map((cond, idx) => (
                                <div key={idx} className="driver-chip-item" style={{ borderColor: "rgba(234, 179, 8, 0.3)", background: "rgba(234, 179, 8, 0.05)" }}>
                                    <span className="driver-icon" style={{ color: "#eab308" }}>📌</span>
                                    <span className="driver-text">{safeString(cond)}</span>
                                </div>
                            ))}
                        </div>
                    </div>
                )}

                {/* 09. CONCLUSION */}
                {conclusionText && (
                    <div className="report-section-block">
                        <div className="section-header-title">
                            <span className="section-num">✦</span>
                            <div>
                                <small className="section-tag">FINAL SYNTHESIS</small>
                                <h3 className="section-heading">Conclusion</h3>
                            </div>
                        </div>
                        <div className="summary-card-body">
                            <p className="summary-text">{safeString(conclusionText)}</p>
                        </div>
                    </div>
                )}

                {/* QUANTITATIVE TOOL ANALYSIS */}
                {toolAnalysis && (
                    <div className="report-section-block">
                        <div className="section-header-title">
                            <span className="section-num">04</span>
                            <div>
                                <small className="section-tag">QUANTITATIVE MODELING</small>
                                <h3 className="section-heading">Business Tool Analysis</h3>
                            </div>
                        </div>

                        <div className="tool-metric-cards-grid">
                            <div className="tool-metric-card">
                                <small>EXECUTED TOOL</small>
                                <h4>{safeString(toolAnalysis.tool_name || toolAnalysis.tool, "Market Risk Tool")}</h4>
                            </div>
                            <div className="tool-metric-card">
                                <small>TOOL RATING</small>
                                <h4 className={riskBadgeClass}>{safeString(toolAnalysis.risk_level, riskLevelStr)}</h4>
                            </div>
                        </div>

                        {Array.isArray(toolAnalysis.observations) &&
                            toolAnalysis.observations.length > 0 && (
                                <div className="observations-list-box">
                                    <h5 className="obs-title">Observations</h5>
                                    {toolAnalysis.observations.map((obs, idx) => (
                                        <div key={idx} className="obs-item">
                                            <StructuredDataRenderer value={obs} />
                                        </div>
                                    ))}
                                </div>
                            )}
                    </div>
                )}

                {/* SENSITIVITY WHAT-IF ANALYSIS ENGINE */}
                <WhatIfPanel
                    task={task}
                    onUpdateMetrics={({ viability_score, risk_level }) => {
                        if (viability_score) setDynamicViability(viability_score);
                        if (risk_level) setDynamicRisk(risk_level);
                    }}
                />
            </div>

            {/* DYNAMIC UNLIMITED FOLLOW-UP CONVERSATION */}
            <div className="followup-panel">
                <div className="followup-panel-header">
                    <div>
                        <span className="panel-eyebrow">CONTINUE THE ANALYSIS</span>
                        <h3 className="panel-title">Ask the Decision Engine</h3>
                        <p className="panel-subtitle">
                            Ask any strategic, financial, marketing, operational, or pricing follow-up question.
                        </p>
                    </div>
                    {followupMessages.length > 0 && onClearFollowup && (
                        <button
                            type="button"
                            className="btn-clear-discussion"
                            onClick={onClearFollowup}
                        >
                            🗑️ Clear Thread
                        </button>
                    )}
                </div>

                <div className="suggested-chips-container">
                    <span className="chips-hint">Suggested questions:</span>
                    <div className="chips-flex">
                        {suggestedChips.map((chipText, idx) => (
                            <button
                                key={idx}
                                type="button"
                                className="suggestion-chip-btn"
                                onClick={() => setLocalFollowupText(chipText)}
                                disabled={isAnyFollowupLoading}
                            >
                                {chipText}
                            </button>
                        ))}
                    </div>
                </div>

                <div className="followup-input-card">
                    <textarea
                        value={localFollowupText}
                        onChange={(e) => setLocalFollowupText(e.target.value)}
                        onKeyDown={(e) => {
                            if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) {
                                e.preventDefault();
                                handleSendFollowup();
                            }
                        }}
                        placeholder="Ask any follow-up question about this decision..."
                        rows={3}
                        disabled={isAnyFollowupLoading}
                    />

                    <div className="input-card-footer">
                        <span className="footer-keyboard-tip">Press Ctrl + Enter to submit</span>

                        <button
                            type="button"
                            className="btn-followup-submit"
                            onClick={() => handleSendFollowup()}
                            disabled={isAnyFollowupLoading || !localFollowupText.trim()}
                        >
                            {isAnyFollowupLoading ? (
                                <span>Analyzing...</span>
                            ) : (
                                <span>Ask Decision Engine →</span>
                            )}
                        </button>
                    </div>
                </div>

                {followupMessages.length > 0 && (
                    <div className="conversation-thread-list">
                        <h4 className="thread-section-title">Follow-up Conversation History</h4>

                        {followupMessages.map((msg) => (
                            <div className="conversation-item-block" key={msg.id}>
                                <div className="user-question-bubble">
                                    <span className="bubble-role">YOUR QUESTION</span>
                                    <p>{msg.question}</p>
                                </div>

                                <div className="ai-response-bubble">
                                    <span className="bubble-role ai">AI DECISION ENGINE ✦</span>

                                    {msg.loading && (
                                        <div className="ai-inline-loading">
                                            <span className="spinner-dot"></span>
                                            <span>Analyzing with decision context...</span>
                                        </div>
                                    )}

                                    {msg.error && (
                                        <div className="ai-inline-error">
                                            <span>⚠️ {safeString(msg.error)}</span>
                                        </div>
                                    )}

                                    {msg.answer && !msg.loading && (
                                        <div className="ai-answer-content">
                                            <StructuredDataRenderer value={msg.answer} />
                                            <button
                                                className="btn-copy-inline"
                                                onClick={() => navigator.clipboard.writeText(toReadableText(msg.answer))}
                                            >
                                                📋 Copy
                                            </button>
                                        </div>
                                    )}
                                </div>
                            </div>
                        ))}
                        <div ref={threadEndRef} />
                    </div>
                )}
            </div>
        </section>
    );
}

export default ReportViewer;