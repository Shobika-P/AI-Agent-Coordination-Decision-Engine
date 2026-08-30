import { useState, useEffect } from "react";
import API from "./services/api";

import Navbar from "./components/Navbar";
import BusinessForm from "./components/BusinessForm";
import WorkflowVisualizer from "./components/WorkflowVisualizer";
import ReportViewer from "./components/ReportViewer";
import ReportLibraryModal from "./components/ReportLibraryModal";
import MonitoringModal from "./components/MonitoringModal";

function App() {
    const [report, setReport] = useState(null);
    const [businessTask, setBusinessTask] = useState("");
    const [conversationId, setConversationId] = useState(null);
    const [loading, setLoading] = useState(false);
    const [reportError, setReportError] = useState(null);
    const [quotaNotice, setQuotaNotice] = useState(null);
    const [metrics, setMetrics] = useState({});
    const [apiStatus, setApiStatus] = useState("checking");

    // LangGraph Workflow Agent Statuses
    const [agentStatuses, setAgentStatuses] = useState({
        tool: "WAITING",
        research: "WAITING",
        planning: "WAITING",
        decision: "WAITING",
        report: "WAITING"
    });

    // Modals
    const [showLibrary, setShowLibrary] = useState(false);
    const [showMonitoring, setShowMonitoring] = useState(false);

    // Follow-up Thread
    const [followupMessages, setFollowupMessages] = useState([]);

    useEffect(() => {
        checkHealth();
    }, []);

    const checkHealth = async () => {
        try {
            const res = await API.get("/health");
            const status = res.data?.status || (res.data?.gemini_available ? "LIVE" : "CONFIGURATION_ERROR");
            setApiStatus(status);
        } catch {
            setApiStatus("CONFIGURATION_ERROR");
        }
    };

    const handleGenerate = async (task, forceRefresh = false) => {
        if (!task || !task.trim()) return;

        console.log("Launching LangGraph decision workflow for:", task, "forceRefresh:", forceRefresh);
        setLoading(true);
        setReportError(null);
        setQuotaNotice(null);
        setReport(null);
        setBusinessTask(task.trim());
        setFollowupMessages([]);
        setConversationId(null);
        setMetrics({});

        setAgentStatuses({
            tool: "RUNNING",
            research: "WAITING",
            planning: "WAITING",
            decision: "WAITING",
            report: "WAITING"
        });

        try {
            const response = await API.post("/generate-report", {
                task: task.trim(),
                force_refresh: forceRefresh
            });

            console.log("LANGGRAPH RESPONSE:", response?.data);

            if (response?.data?.success && response?.data?.report) {
                setReport(response.data.report);
                setConversationId(response.data.conversation_id);

                if (response.data.workflow?.agent_statuses) {
                    setAgentStatuses(response.data.workflow.agent_statuses);
                } else {
                    setAgentStatuses({
                        tool: "COMPLETED",
                        research: "COMPLETED",
                        planning: "COMPLETED",
                        decision: "COMPLETED",
                        report: "COMPLETED"
                    });
                }

                if (response.data.workflow?.metrics) {
                    setMetrics(response.data.workflow.metrics);
                }

                checkHealth();
            } else {
                const data = response?.data || {};
                let errObj = {
                    title: data.status === "rate_limited" ? "AI Rate Limit Reached" : "AI Service Temporarily Busy",
                    message: data.message || "We could not complete the live AI analysis at this moment. Please retry in a few seconds.",
                    isTemporary: true
                };
                setReportError(errObj);
            }
        } catch (error) {
            console.error("LANGGRAPH REPORT ERROR:", error);
            const data = error?.response?.data || {};
            const httpStatus = error?.response?.status;

            let errObj = null;
            if (data.status === "rate_limited" || httpStatus === 429) {
                errObj = {
                    title: "AI Rate Limit Reached",
                    message: data.message || "The AI request rate limit has been reached. Please wait a few seconds before retrying.",
                    isTemporary: true
                };
            } else if (data.status === "configuration_error" || (httpStatus === 500 && String(data.error || "").toLowerCase().includes("key"))) {
                errObj = {
                    title: "AI Configuration Error",
                    message: data.message || "Google Gemini API key is missing or invalid. Please check your environment configuration.",
                    isTemporary: false
                };
            } else {
                errObj = {
                    title: "AI Service Temporarily Busy",
                    message: data.message || "We could not complete the live AI analysis at this moment. Please retry in a few seconds.",
                    isTemporary: true
                };
            }
            setReportError(errObj);
            checkHealth();
        } finally {
            setLoading(false);
        }
    };


    const handleFollowup = async (userQuestion) => {
        const questionText = (typeof userQuestion === "string" ? userQuestion : "").trim();
        if (!questionText || !report) return;

        const messageId = Date.now().toString() + Math.random().toString(36).substr(2, 4);
        const newMessage = {
            id: messageId,
            question: questionText,
            answer: null,
            loading: true,
            error: null
        };

        setFollowupMessages((prev) => [...prev, newMessage]);

        try {
            const response = await API.post("/follow-up", {
                question: questionText,
                original_task: businessTask,
                conversation_id: conversationId,
                report: report
            });

            console.log("LANGGRAPH FOLLOW-UP RESPONSE:", response?.data);

            if (response?.data?.success && response?.data?.answer) {
                const rawAnswer = response.data.answer;
                const cleanAnswer =
                    typeof rawAnswer === "string"
                        ? rawAnswer
                        : JSON.stringify(rawAnswer, null, 2);

                if (response.data.conversation_id) {
                    setConversationId(response.data.conversation_id);
                }

                setFollowupMessages((prev) =>
                    prev.map((msg) =>
                        msg.id === messageId
                            ? { ...msg, answer: cleanAnswer, loading: false, error: null }
                            : msg
                    )
                );
            } else {
                const errMsg =
                    response?.data?.error || "Unable to answer follow-up question.";

                setFollowupMessages((prev) =>
                    prev.map((msg) =>
                        msg.id === messageId
                            ? { ...msg, loading: false, error: errMsg }
                            : msg
                    )
                );
            }
        } catch (error) {
            console.error("LANGGRAPH FOLLOW-UP ERROR:", error);
            const errMsg =
                error?.response?.data?.error ||
                "Unable to process follow-up question. Previous report remains active.";

            setFollowupMessages((prev) =>
                prev.map((msg) =>
                    msg.id === messageId
                        ? { ...msg, loading: false, error: errMsg }
                        : msg
                )
            );
        }
    };

    const handleSelectReportFromLibrary = ({ task, conversation_id, report, history }) => {
        setBusinessTask(task);
        setConversationId(conversation_id);
        setReport(report);
        setReportError(null);
        setAgentStatuses({
            tool: "COMPLETED",
            research: "COMPLETED",
            planning: "COMPLETED",
            decision: "COMPLETED",
            report: "COMPLETED"
        });

        if (Array.isArray(history)) {
            const formattedMessages = history.map((item, idx) => ({
                id: `history-${idx}`,
                question: item.question,
                answer: item.answer,
                loading: false,
                error: null
            }));
            setFollowupMessages(formattedMessages);
        } else {
            setFollowupMessages([]);
        }
    };

    return (
        <div className="app-shell">
            <Navbar
                onOpenLibrary={() => setShowLibrary(true)}
                onOpenMonitoring={() => setShowMonitoring(true)}
                quotaStatus={quotaNotice ? "demo" : apiStatus}
            />

            <main className="app-container">
                {/* HERO QUERY INPUT FORM */}
                <BusinessForm
                    onGenerate={handleGenerate}
                    loading={loading}
                    initialTask={businessTask}
                />

                {/* LANGGRAPH WORKFLOW VISUALIZER */}
                <WorkflowVisualizer
                    agentStatuses={agentStatuses}
                    metrics={metrics}
                    isVisible={loading || !!report}
                />

                {/* EXECUTIVE REPORT VIEWER & DYNAMIC FOLLOW-UP THREAD */}
                <ReportViewer
                    report={report}
                    task={businessTask}
                    loading={loading}
                    error={reportError}
                    quotaNotice={quotaNotice}
                    followupMessages={followupMessages}
                    onFollowup={handleFollowup}
                    onClearFollowup={() => setFollowupMessages([])}
                    onRetry={() => handleGenerate(businessTask, true)}
                />

                {/* PERSISTENT SQLITE REPORT LIBRARY MODAL */}
                <ReportLibraryModal
                    isOpen={showLibrary}
                    onClose={() => setShowLibrary(false)}
                    onSelectReport={handleSelectReportFromLibrary}
                />

                {/* AI SYSTEM MONITORING TELEMETRY MODAL */}
                <MonitoringModal
                    isOpen={showMonitoring}
                    onClose={() => setShowMonitoring(false)}
                />
            </main>
        </div>
    );
}

export default App;