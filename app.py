from flask import Flask, request, jsonify
from flask_cors import CORS

from agents.business_decision_engine import business_decision_engine

app = Flask(__name__)
CORS(app)


@app.route("/")
def home():
    return "AI Business Decision Engine API is Running!"


@app.route("/generate-report", methods=["POST"])
def generate_report():

    data = request.get_json()

    task = data.get("task")

    if not task:
        return jsonify({
            "error": "Task is required."
        }), 400

    report = business_decision_engine(task)

    return jsonify({
        "report": report
    })

@app.route("/follow-up", methods=["POST"])
def follow_up():

    data = request.get_json()

    task = data.get("task")
    report = data.get("report")
    question = data.get("question")

    if not task or not report or not question:
        return jsonify({
            "error": "Task, report and question are required."
        }), 400

    prompt = f"""
You are an AI Business Decision Support Assistant.

The user previously asked this business decision question:

BUSINESS QUESTION:
{task}

The AI generated the following business decision report:

BUSINESS REPORT:
{report}

The user now has a follow-up question:

FOLLOW-UP QUESTION:
{question}

Answer the follow-up question using the business report as the primary context.

Rules:
- Stay focused on the user's business decision.
- Do not generate an entirely new report unless specifically requested.
- Use information from the existing report.
- Give practical and clear business advice.
- If the question asks for clarification, explain the relevant part of the report.
- If the question asks for recommendations, provide actionable recommendations.
"""

    try:

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )

        answer = response.text

        return jsonify({
            "answer": answer
        })

    except Exception as e:

        return jsonify({
            "error": str(e)
        }), 500


if __name__ == "__main__":
    app.run(debug=True)
    