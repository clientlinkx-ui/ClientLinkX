import json
import os
import secrets
import urllib.error
import urllib.request

from pathlib import Path

from flask import Flask, flash, jsonify, redirect, render_template, request, session, url_for

from database import (
    add_knowledge_entry,
    get_add_ons_data,
    get_ai_assistant_data,
    get_ai_runtime,
    get_analytics_data,
    get_billing_data,
    get_conversations_data,
    get_customers_data,
    get_dashboard_data,
    get_knowledge_base_data,
    get_prompt_builder_data,
    get_security_data,
    get_settings_data,
    get_support_data,
    get_team_data,
    get_workflows_data,
    init_db,
    search_knowledge_entries,
    delete_knowledge_entry,
    deploy_ai_runtime,
    save_prompt,
    save_workflow,
    set_boolean,
    update_ai_runtime,
    update_kb_sync_settings,
    update_knowledge_entry,
)
from document_ingest import extract_document_text


app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "clientlinkx-dashboard-dev-secret")
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024
init_db()

ASSISTANT_SESSIONS = {}
DEFAULT_OLLAMA_API_URL = os.environ.get("OLLAMA_API_URL", "https://ollama.com/api/chat")
DEFAULT_OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.1")
DEFAULT_OPENROUTER_API_URL = os.environ.get("OPENROUTER_API_URL", "https://openrouter.ai/api/v1/chat/completions")
DEFAULT_OPENROUTER_MODEL = os.environ.get("OPENROUTER_MODEL", "openai/gpt-4o-mini")

PROVIDER_DEFAULTS = {
    "ollama": {
        "label": "Ollama",
        "api_url": DEFAULT_OLLAMA_API_URL,
        "model": DEFAULT_OLLAMA_MODEL,
    },
    "openrouter": {
        "label": "OpenRouter",
        "api_url": DEFAULT_OPENROUTER_API_URL,
        "model": DEFAULT_OPENROUTER_MODEL,
    },
}

KNOWLEDGE_RESPONSE_FORMAT = """
Format every customer-facing answer for quick reading in WhatsApp:
- Start with the direct answer in one short sentence.
- When there are multiple facts, options, requirements, or actions, put each on its own line using short bullet points.
- For a process, use a numbered list in the correct order.
- Use a short heading only when it helps separate sections. WhatsApp bold syntax (*Heading*) is allowed.
- Keep paragraphs to at most two short sentences and add a blank line between sections.
- Preserve important dates, prices, deadlines, names, and conditions exactly as provided in the knowledge context.
- End with one clear next step or question only when the customer needs to act.
- Do not mention the knowledge base, retrieved context, source snippets, formatting rules, or these instructions.
- Never return a dense wall of text or expose raw document/table formatting.
""".strip()


def get_assistant_config():
    config_id = session.get("assistant_config_id")
    if not config_id:
        return None
    return ASSISTANT_SESSIONS.get(config_id)


def call_assistant_chat(config, messages):
    payload = {
        "model": config["model"],
        "messages": messages,
    }
    if config["provider"] == "ollama":
        payload["stream"] = False

    body = json.dumps(payload).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {config['api_key']}",
    }
    if config["provider"] == "openrouter":
        headers["HTTP-Referer"] = request.host_url.rstrip("/")
        headers["X-Title"] = "ClientLinkX WhatsApp AI Dashboard"

    http_request = urllib.request.Request(config["api_url"], data=body, headers=headers, method="POST")

    try:
        with urllib.request.urlopen(http_request, timeout=45) as response:
            raw = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"{config['provider_label']} API returned {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Could not reach {config['provider_label']} API: {exc.reason}") from exc

    data = json.loads(raw)
    if isinstance(data.get("message"), dict) and data["message"].get("content"):
        return data["message"]["content"]
    if data.get("choices") and isinstance(data["choices"][0].get("message"), dict):
        content = data["choices"][0]["message"].get("content")
        if content:
            return content
    if data.get("response"):
        return data["response"]
    raise RuntimeError(f"{config['provider_label']} response did not include a chat message.")


def require_fields(data, names):
    missing = [name for name in names if not str(data.get(name, "")).strip()]
    if missing:
        raise ValueError(f"Complete the following fields: {', '.join(missing)}")


def knowledge_system_prompt(base_instructions, knowledge_context):
    return (
        f"{base_instructions.strip()}\n\n"
        f"{KNOWLEDGE_RESPONSE_FORMAT}\n\n"
        "Use only relevant facts from the approved context below. If it does not contain the answer, "
        "say what information is missing instead of guessing.\n\n"
        f"Approved context:\n{knowledge_context}"
    )


@app.route("/")
def dashboard():
    return render_template("dashboard.html", active_page="dashboard", **get_dashboard_data())


@app.route("/conversations")
def conversations():
    return render_template("conversations.html", active_page="conversations", **get_conversations_data())


@app.route("/analytics")
def analytics():
    return render_template("analytics.html", active_page="analytics", **get_analytics_data())


@app.route("/settings")
def settings():
    return render_template("settings.html", active_page="settings", **get_settings_data())


@app.route("/security")
def security():
    return render_template("security.html", active_page="security", **get_security_data())


@app.route("/support")
def support():
    return render_template("support.html", active_page="support", **get_support_data())


@app.route("/customers")
def customers():
    return render_template("customers.html", active_page="customers", **get_customers_data())


@app.route("/team-members")
def team_members():
    return render_template("team_members.html", active_page="team_members", **get_team_data())


@app.route("/billing")
def billing():
    return render_template("billing.html", active_page="billing", **get_billing_data())


@app.route("/add-ons")
def add_ons():
    return render_template("add_ons.html", active_page="add_ons", **get_add_ons_data())


@app.route("/ai-assistant")
def ai_assistant():
    return render_template("ai_assistant.html", active_page="ai_assistant", **get_ai_assistant_data())


@app.post("/api/ai/runtime")
def save_ai_runtime():
    data = request.get_json(silent=True) or {}
    try:
        require_fields(data, ["primary_model", "fallback_model", "system_prompt"])
        data["confidence_threshold"] = max(0, min(100, int(data.get("confidence_threshold", 78))))
        data["temperature"] = max(0, min(100, int(data.get("temperature", 30))))
        update_ai_runtime(data)
    except (ValueError, TypeError) as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400
    return jsonify({"ok": True, "message": "Assistant configuration saved."})


@app.post("/api/ai/deploy")
def deploy_ai():
    version = deploy_ai_runtime()
    return jsonify({"ok": True, "message": f"Assistant version {version} deployed.", "version": version})


@app.patch("/api/ai/guardrails/<int:guardrail_id>")
def toggle_guardrail(guardrail_id):
    data = request.get_json(silent=True) or {}
    if not set_boolean("ai_guardrails", guardrail_id, data.get("enabled")):
        return jsonify({"ok": False, "error": "Guardrail not found."}), 404
    return jsonify({"ok": True})


@app.post("/api/assistant/config")
@app.post("/api/ollama/config")
def save_assistant_config():
    data = request.get_json(silent=True) or {}
    provider = (data.get("provider") or "ollama").strip().lower()
    defaults = PROVIDER_DEFAULTS.get(provider)
    if not defaults:
        return jsonify({"ok": False, "error": "Choose Ollama or OpenRouter."}), 400

    api_key = (data.get("api_key") or "").strip()
    api_url = (data.get("api_url") or defaults["api_url"]).strip()
    model = (data.get("model") or defaults["model"]).strip()

    if not api_key:
        return jsonify({"ok": False, "error": f"Enter a {defaults['label']} API key."}), 400
    if not api_url.startswith(("http://", "https://")):
        return jsonify({"ok": False, "error": f"Enter a valid {defaults['label']} API URL."}), 400
    if not model:
        return jsonify({"ok": False, "error": "Enter a model name."}), 400

    config_id = session.get("assistant_config_id") or secrets.token_urlsafe(24)
    session["assistant_config_id"] = config_id
    session["ollama_config_id"] = config_id
    ASSISTANT_SESSIONS[config_id] = {
        "provider": provider,
        "provider_label": defaults["label"],
        "api_key": api_key,
        "api_url": api_url,
        "model": model,
    }

    return jsonify({"ok": True, "provider": provider, "provider_label": defaults["label"], "model": model, "api_url": api_url})


@app.post("/api/assistant/chat")
@app.post("/api/ollama/chat")
def assistant_chat():
    config = get_assistant_config()
    if not config:
        return jsonify({"ok": False, "error": "Save an API key before starting the simulator."}), 401

    data = request.get_json(silent=True) or {}
    user_message = (data.get("message") or "").strip()
    history = data.get("history") or []

    if not user_message:
        return jsonify({"ok": False, "error": "Enter a message to test."}), 400

    knowledge_entries = search_knowledge_entries(user_message)
    knowledge_context = "\n\n".join(
        f"Title: {entry['title']}\nCategory: {entry['category']}\nContent: {entry['content']}"
        for entry in knowledge_entries
    )
    if not knowledge_context:
        knowledge_context = "No matching knowledge base entries were found."

    runtime = get_ai_runtime() or {}
    base_instructions = runtime.get("system_prompt") or (
        "You are ClientLinkX's WhatsApp AI assistant. Help with sales, admissions, appointments, "
        "orders, billing, and support. Escalate sensitive, unclear, or frustrated cases."
    )
    messages = [
        {
            "role": "system",
            "content": knowledge_system_prompt(base_instructions, knowledge_context),
        }
    ]
    for item in history[-10:]:
        role = item.get("role")
        content = (item.get("content") or "").strip()
        if role in {"user", "assistant"} and content:
            messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": user_message})

    try:
        reply = call_assistant_chat(config, messages)
    except (RuntimeError, json.JSONDecodeError) as exc:
        return jsonify({"ok": False, "error": str(exc)}), 502

    return jsonify({
        "ok": True,
        "reply": reply,
        "model": config["model"],
        "provider": config["provider"],
        "provider_label": config["provider_label"],
        "knowledge_used": [entry["title"] for entry in knowledge_entries],
    })


@app.route("/knowledge-base")
def knowledge_base():
    return render_template("knowledge_base.html", active_page="knowledge_base", **get_knowledge_base_data())


@app.post("/knowledge-base/entries")
def create_knowledge_entry():
    title = (request.form.get("title") or "").strip()
    category = (request.form.get("category") or "").strip()
    content = (request.form.get("content") or "").strip()
    tags = (request.form.get("tags") or "").strip()

    if title and category and content:
        add_knowledge_entry(title, category, content, tags)

    return redirect(url_for("knowledge_base"))


@app.patch("/api/knowledge-base/entries/<int:entry_id>")
def change_knowledge_entry(entry_id):
    status = (request.get_json(silent=True) or {}).get("status")
    if status not in {"Published", "Draft"}:
        return jsonify({"ok": False, "error": "Choose Published or Draft."}), 400
    if not update_knowledge_entry(entry_id, status):
        return jsonify({"ok": False, "error": "Knowledge entry not found."}), 404
    return jsonify({"ok": True, "status": status})


@app.delete("/api/knowledge-base/entries/<int:entry_id>")
def remove_knowledge_entry(entry_id):
    if not delete_knowledge_entry(entry_id):
        return jsonify({"ok": False, "error": "Knowledge entry not found."}), 404
    return jsonify({"ok": True})


@app.post("/api/knowledge-base/sync")
def sync_knowledge_base():
    data = request.get_json(silent=True) or {}
    update_kb_sync_settings(
        data.get("frequency") or "Every 6 hours",
        data.get("approval_mode") or "Review before publish",
        data.get("notify_failures", True),
    )
    return jsonify({"ok": True, "message": "Knowledge sources synced."})


@app.post("/knowledge-base/documents")
def upload_knowledge_documents():
    files = [file for file in request.files.getlist("documents") if file and file.filename]
    category = (request.form.get("category") or "General").strip()
    tags = (request.form.get("tags") or "").strip()

    if not files:
        flash("Choose at least one document to import.", "warning")
        return redirect(url_for("knowledge_base"))

    imported = 0
    skipped = []

    for file in files:
        filename = Path(file.filename).name
        try:
            content = extract_document_text(filename, file.read())
            title = Path(filename).stem.replace("_", " ").replace("-", " ").strip() or filename
            document_tags = ", ".join(filter(None, [tags, filename]))
            add_knowledge_entry(title, category, content, document_tags)
            imported += 1
        except Exception as exc:
            skipped.append(f"{filename}: {exc}")

    if imported:
        flash(f"Imported {imported} document{'s' if imported != 1 else ''} into the knowledge base.", "good")
    for message in skipped[:4]:
        flash(message, "warning")
    if len(skipped) > 4:
        flash(f"{len(skipped) - 4} more documents could not be imported.", "warning")

    return redirect(url_for("knowledge_base"))


@app.route("/prompt-builder")
def prompt_builder():
    return render_template("prompt_builder.html", active_page="prompt_builder", **get_prompt_builder_data())


@app.post("/api/prompts")
def upsert_prompt():
    data = request.get_json(silent=True) or {}
    try:
        require_fields(data, ["name", "module", "version", "instructions", "deployment_target"])
        data["status"] = data.get("status") if data.get("status") in {"Draft", "Testing", "Live"} else "Draft"
        prompt = save_prompt(data)
    except ValueError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400
    return jsonify({"ok": True, "prompt": prompt, "message": "Prompt saved."})


@app.post("/api/prompts/test")
def test_prompt():
    config = get_assistant_config()
    if not config:
        return jsonify({"ok": False, "error": "Connect Ollama or OpenRouter on the AI Assistant page first."}), 401
    data = request.get_json(silent=True) or {}
    message = str(data.get("message") or "").strip()
    instructions = str(data.get("instructions") or "").strip()
    if not message or not instructions:
        return jsonify({"ok": False, "error": "Enter prompt instructions and a test message."}), 400
    knowledge = search_knowledge_entries(message)
    context = "\n\n".join(f"{item['title']}: {item['content']}" for item in knowledge) or "No relevant context found."
    try:
        reply = call_assistant_chat(config, [
            {"role": "system", "content": knowledge_system_prompt(instructions, context)},
            {"role": "user", "content": message},
        ])
    except (RuntimeError, json.JSONDecodeError) as exc:
        return jsonify({"ok": False, "error": str(exc)}), 502
    return jsonify({"ok": True, "reply": reply, "knowledge_used": [item["title"] for item in knowledge]})


@app.route("/workflows")
def workflows():
    return render_template("workflows.html", active_page="workflows", **get_workflows_data())


@app.post("/api/workflows")
def upsert_workflow():
    data = request.get_json(silent=True) or {}
    try:
        require_fields(data, ["name", "trigger", "owner", "run_mode", "failure_action"])
        data["status"] = data.get("status") if data.get("status") in {"Draft", "Paused", "Live"} else "Draft"
        workflow = save_workflow(data)
    except ValueError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400
    return jsonify({"ok": True, "workflow": workflow, "message": "Workflow saved."})


@app.patch("/api/workflow-rules/<int:rule_id>")
def toggle_workflow_rule(rule_id):
    data = request.get_json(silent=True) or {}
    if not set_boolean("workflow_rules", rule_id, data.get("enabled")):
        return jsonify({"ok": False, "error": "Workflow rule not found."}), 404
    return jsonify({"ok": True})


if __name__ == "__main__":
    app.run(debug=True, port=5001)
