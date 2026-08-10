import { useState } from "react";
import API from "./services/api";

import Navbar from "./components/Navbar";
import BusinessForm from "./components/BusinessForm";
import WorkflowVisualizer from "./components/WorkflowVisualizer";
import ReportViewer from "./components/ReportViewer";
import HistoryModal from "./components/HistoryModal";
import MonitoringModal from "./components/MonitoringModal";

function App() {
    const [report, setReport] = useState(null);
    const [businessTask, setBusinessTask] = useState("");
    const [conversationId, setConversationId] = useState(null);
    const [loading, setLoading] = useState(false);
    const [reportError, setReportError] = useState(null);

    // LangGraph Workflow Agent Statuses
    const [agentStatuses, setAgentStatuses] = useState({
        tool: "QUEUED",
        research: "QUEUED",
        planning: "QUEUED",
        decision: "QUEUED",
        report: "QUEUED"
    });

    // Modals & Active Tab
    const [activeTab, setActiveTab] = useState("engine");
    const [showHistory, setShowHistory] = useState(false);
    const [showMonitoring, setShowMonitoring] = useState(false);

    // Sequential Follow-up Thread
    const [followupMessages, setFollowupMessages] = useState([]);

    const handleGenerate = async (task) => {
        if (!task || !task.trim()) return;

        console.log("Launching LangGraph decision workflow for:", task);
        setLoading(true);
        setReportError(null);
        setReport(null);
        setBusinessTask(task.trim());
        setFollowupMessages([]);
        setConversationId(null);

        setAgentStatuses({
            tool: "RUNNING",
            research: "QUEUED",
            planning: "QUEUED",
            decision: "QUEUED",
            report: "QUEUED"
        });

        try {
            const response = await API.post("/generate-report", {
                task: task.trim()
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
            } else {
                const errMsg = response?.data?.error || "Failed to generate business report.";
                setReportError(errMsg);
            }
        } catch (error) {
            console.error("LANGGRAPH REPORT ERROR:", error);
            const errMsg =
                error?.response?.data?.error ||
                "Failed to generate the business report. Please check server connectivity or Gemini quota limits.";
            setReportError(errMsg);
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
                    response?.data?.error || "The AI Engine could not answer this question.";

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
                "Unable to process follow-up question. Please check server connectivity or quota limits.";

            setFollowupMessages((prev) =>
                prev.map((msg) =>
                    msg.id === messageId
                        ? { ...msg, loading: false, error: errMsg }
                        : msg
                )
            );
        }
    };

    return (
        <div className="app-shell">
            <Navbar
                activeTab={activeTab}
                setActiveTab={setActiveTab}
                onOpenHistory={() => setShowHistory(true)}
                onOpenMonitoring={() => setShowMonitoring(true)}
            />

            <main className="app-container">
                {/* HERO & QUERY FORM */}
                <BusinessForm
                    onGenerate={handleGenerate}
                    loading={loading}
                    initialTask={businessTask}
                />

                {/* LANGGRAPH WORKFLOW VISUALIZER */}
                <WorkflowVisualizer
                    agentStatuses={agentStatuses}
                    isVisible={loading || !!report}
                />

                {/* EXECUTIVE REPORT & FOLLOW-UP CONVERSATION */}
                <ReportViewer
                    report={report}
                    task={businessTask}
                    loading={loading}
                    error={reportError}
                    followupMessages={followupMessages}
                    onFollowup={handleFollowup}
                    onClearFollowup={() => setFollowupMessages([])}
                    onRetry={() => handleGenerate(businessTask)}
                />

                {/* DECISION LOG HISTORY MODAL */}
                <HistoryModal
                    isOpen={showHistory}
                    onClose={() => setShowHistory(false)}
                    onSelectTask={(selectedTask) => {
                        handleGenerate(selectedTask);
                    }}
                />

                {/* MONITORING & TELEMETRY MODAL */}
                <MonitoringModal
                    isOpen={showMonitoring}
                    onClose={() => setShowMonitoring(false)}
                />
            </main>
        </div>
    );
}

export default App;