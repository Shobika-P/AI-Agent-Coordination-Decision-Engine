import { useState } from "react";
import FollowUp from "./components/FollowUp";
import API from "./services/api";

import Navbar from "./components/Navbar";
import BusinessForm from "./components/BusinessForm";
import ReportViewer from "./components/ReportViewer";

function App() {
  const [task, setTask] = useState("");
  const [report, setReport] = useState("");
  const [loading, setLoading] = useState(false);
  const [conversation, setConversation] = useState([]);
  const [followUpLoading, setFollowUpLoading] = useState(false);

  const handleGenerate = async (businessTask) => {

  setTask(businessTask);

  setLoading(true);
  setReport("");
  setConversation([]);
  setFollowUpAnswer("");

  try {

    const response = await API.post("/generate-report", {
      task: businessTask
    });

    setReport(response.data.report);

  } catch (error) {

    console.error(error);

    setReport(
      "Unable to generate the business report. Please try again."
    );

  } finally {

    setLoading(false);

  }
};
const handleFollowUp = async (question) => {

  setFollowUpLoading(true);

  try {

    const response = await API.post("/follow-up", {
      task: task,
      report: report,
      question: question
    });

    const newMessage = {
      question: question,
      answer: response.data.answer
    };

    setConversation((previous) => [
      ...previous,
      newMessage
    ]);

  } catch (error) {

    console.error(error);

    const newMessage = {
      question: question,
      answer: "Unable to answer this question. Please try again."
    };

    setConversation((previous) => [
      ...previous,
      newMessage
    ]);

  } finally {

    setFollowUpLoading(false);

  }
};
 return (
  <div className="app">

    <Navbar />

    <BusinessForm
      onGenerate={handleGenerate}
      loading={loading}
    />

    <ReportViewer
      report={report}
      loading={loading}
    />

    {report && !loading && (
      <FollowUp
        onAsk={handleFollowUp}
        loading={followUpLoading}
        disabled={!report}
      />
    )}

    {conversation.length > 0 && (
  <div className="conversation-container">

    {conversation.map((item, index) => (

      <div
        className="conversation-item"
        key={index}
      >

        <div className="user-question">

          <div className="message-label">
            You
          </div>

          <div className="question-bubble">
            {item.question}
          </div>

        </div>

        <div className="ai-answer">

          <div className="message-label ai-label">
            🤖 AI Decision Support
          </div>

          <div className="answer-bubble">
            {item.answer}
          </div>

        </div>

      </div>

    ))}

  </div>
)}

  </div>
);
}

export default App;