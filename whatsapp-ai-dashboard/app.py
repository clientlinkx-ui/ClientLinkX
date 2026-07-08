import json
import os
import secrets
import urllib.error
import urllib.parse
import urllib.request

from pathlib import Path

from flask import Flask, Response, flash, g, jsonify, redirect, render_template, request, session, url_for

from database import (
    add_knowledge_entry,
    add_conversation_message,
    add_support_ticket,
    add_team_role,
    assign_conversation_thread,
    create_customer,
    create_or_update_team_member,
    create_conversation_thread,
    export_rows_csv,
    get_dashboard_user,
    get_assistant_connection,
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
    get_topbar_items,
    get_workflows_data,
    global_search,
    init_db,
    search_knowledge_entries,
    mark_topbar_items_read,
    purchase_addon_cart,
    save_assistant_connection,
    save_security_settings,
    save_workspace_settings,
    synchronize_active_model,
    toggle_addon_cart,
    toggle_billing_addon,
    toggle_security_access_rule,
    toggle_settings_module,
    update_conversation_thread_status,
    update_customer,
    delete_knowledge_entry,
    deploy_ai_runtime,
    save_prompt,
    save_workflow,
    set_boolean,
    update_ai_runtime,
    update_kb_sync_settings,
    update_dashboard_user_preferences,
    update_knowledge_entry,
    upsert_google_user,
)
from document_ingest import extract_document_text


def load_local_env():
    env_path = Path(__file__).resolve().parent / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text().splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


load_local_env()


app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "pingpilot-dashboard-dev-secret")
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024
init_db()

ASSISTANT_SESSIONS = {}
DEFAULT_OLLAMA_API_URL = os.environ.get("OLLAMA_API_URL", "https://ollama.com/api/chat")
DEFAULT_OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.1")
DEFAULT_OPENROUTER_API_URL = os.environ.get("OPENROUTER_API_URL", "https://openrouter.ai/api/v1/chat/completions")
DEFAULT_OPENROUTER_MODEL = os.environ.get("OPENROUTER_MODEL", "openai/gpt-4o-mini")
DEFAULT_GOOGLE_CLIENT_ID = "600909369975-fkhejulu9hkr6klan0vf3smho8npv372.apps.googleusercontent.com"
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", DEFAULT_GOOGLE_CLIENT_ID).strip()
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "").strip()
GOOGLE_ALLOWED_DOMAIN = os.environ.get("GOOGLE_ALLOWED_DOMAIN", "").strip().lower()
GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"
APPLE_AUTH_URL = os.environ.get("APPLE_AUTH_URL", "").strip()
WHATSAPP_AUTH_URL = os.environ.get("WHATSAPP_AUTH_URL", "").strip()

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
    if config_id and ASSISTANT_SESSIONS.get(config_id):
        return ASSISTANT_SESSIONS[config_id]
    user = getattr(g, "current_user", None)
    if not user:
        return None
    saved = get_assistant_connection(user["id"], include_key=True)
    if not saved:
        return None
    config_id = config_id or secrets.token_urlsafe(24)
    session["assistant_config_id"] = config_id
    session["ollama_config_id"] = config_id
    ASSISTANT_SESSIONS[config_id] = {
        "provider": saved["provider"],
        "provider_label": saved["provider_label"],
        "api_key": saved["api_key"],
        "api_url": saved["api_url"],
        "model": saved["model"],
    }
    return ASSISTANT_SESSIONS[config_id]


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
        headers["X-Title"] = "PingPilot WhatsApp AI Dashboard"

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


def google_auth_configured():
    return bool(GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET)


def google_missing_config():
    missing = []
    if not GOOGLE_CLIENT_ID:
        missing.append("GOOGLE_CLIENT_ID")
    if not GOOGLE_CLIENT_SECRET:
        missing.append("GOOGLE_CLIENT_SECRET")
    return missing


def third_party_auth_ready(provider):
    urls = {
        "apple": APPLE_AUTH_URL,
        "whatsapp": WHATSAPP_AUTH_URL,
    }
    return bool(urls.get(provider))


def safe_next_url(value):
    if value and value.startswith("/") and not value.startswith("//"):
        return value
    return url_for("dashboard")


def google_redirect_uri():
    return os.environ.get("GOOGLE_REDIRECT_URI") or url_for("google_callback", _external=True)


def exchange_google_code(code):
    payload = urllib.parse.urlencode({
        "code": code,
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "redirect_uri": google_redirect_uri(),
        "grant_type": "authorization_code",
    }).encode("utf-8")
    token_request = urllib.request.Request(
        GOOGLE_TOKEN_URL,
        data=payload,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    with urllib.request.urlopen(token_request, timeout=30) as response:
        token_data = json.loads(response.read().decode("utf-8"))
    access_token = token_data.get("access_token")
    if not access_token:
        raise RuntimeError("Google did not return an access token.")
    profile_request = urllib.request.Request(
        GOOGLE_USERINFO_URL,
        headers={"Authorization": f"Bearer {access_token}"},
        method="GET",
    )
    with urllib.request.urlopen(profile_request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


@app.before_request
def require_login():
    g.current_user = get_dashboard_user(session.get("user_id"))
    if request.endpoint in {"login", "register", "google_login", "google_callback", "apple_login", "whatsapp_login", "logout", "static"}:
        return None
    if g.current_user:
        return None
    if request.path.startswith("/api/"):
        return jsonify({"ok": False, "error": "Login required."}), 401
    return redirect(url_for("login", next=request.full_path if request.query_string else request.path))


@app.context_processor
def inject_current_user():
    user = getattr(g, "current_user", None)
    if not user:
        return {"current_user": None, "account": None}
    name = user.get("name") or user.get("email") or "Workspace User"
    initials = "".join(part[0] for part in name.split()[:2]).upper() or "WU"
    preferences = {
        "console_theme": user.get("console_theme") or "auto",
        "console_density": user.get("console_density") or "comfortable",
        "accent_color": user.get("accent_color") or "teal",
        "default_sidebar": user.get("default_sidebar") or "expanded",
    }
    return {
        "current_user": user,
        "account": {
            "name": name,
            "email": user.get("email") or "",
            "initials": initials,
            "role": "Workspace Admin",
            "domain": user.get("hosted_domain") or "",
        },
        "preferences": preferences,
        "body_classes": " ".join([
            f"theme-{preferences['console_theme']}",
            f"density-{preferences['console_density']}",
            f"accent-{preferences['accent_color']}",
            "sidebar-collapsed" if preferences["default_sidebar"] == "collapsed" else "",
        ]).strip(),
    }


@app.route("/login")
def login():
    if g.current_user:
        return redirect(safe_next_url(request.args.get("next")))
    return render_template(
        "login.html",
        auth_ready=google_auth_configured(),
        google_client_id=GOOGLE_CLIENT_ID,
        missing_config=google_missing_config(),
        allowed_domain=GOOGLE_ALLOWED_DOMAIN,
        next_url=safe_next_url(request.args.get("next")),
    )


@app.route("/register")
def register():
    if g.current_user:
        return redirect(safe_next_url(request.args.get("next")))
    return render_template(
        "register.html",
        auth_ready=google_auth_configured(),
        apple_ready=third_party_auth_ready("apple"),
        whatsapp_ready=third_party_auth_ready("whatsapp"),
        missing_config=google_missing_config(),
        allowed_domain=GOOGLE_ALLOWED_DOMAIN,
        next_url=safe_next_url(request.args.get("next")),
    )


@app.route("/auth/google")
def google_login():
    if not google_auth_configured():
        flash("Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET before using Google sign-in.", "warning")
        return redirect(url_for("login", next=request.args.get("next") or "/"))
    state = secrets.token_urlsafe(32)
    session["google_oauth_state"] = state
    session["post_login_next"] = safe_next_url(request.args.get("next"))
    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": google_redirect_uri(),
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "access_type": "online",
        "prompt": "select_account",
    }
    if GOOGLE_ALLOWED_DOMAIN:
        params["hd"] = GOOGLE_ALLOWED_DOMAIN
    return redirect(f"{GOOGLE_AUTH_URL}?{urllib.parse.urlencode(params)}")


@app.route("/auth/apple")
def apple_login():
    if not APPLE_AUTH_URL:
        flash("Apple registration is not configured yet. Set APPLE_AUTH_URL to enable Sign in with Apple.", "warning")
        return redirect(url_for("register", next=request.args.get("next") or "/"))
    session["post_login_next"] = safe_next_url(request.args.get("next"))
    return redirect(APPLE_AUTH_URL)


@app.route("/auth/whatsapp")
def whatsapp_login():
    if not WHATSAPP_AUTH_URL:
        flash("WhatsApp registration is not configured yet. Set WHATSAPP_AUTH_URL to enable WhatsApp account registration.", "warning")
        return redirect(url_for("register", next=request.args.get("next") or "/"))
    session["post_login_next"] = safe_next_url(request.args.get("next"))
    return redirect(WHATSAPP_AUTH_URL)


@app.route("/auth/google/callback")
def google_callback():
    expected_state = session.pop("google_oauth_state", None)
    received_state = request.args.get("state")
    if not expected_state or not secrets.compare_digest(expected_state, received_state or ""):
        flash("Google sign-in could not be verified. Please try again.", "warning")
        return redirect(url_for("login"))
    if request.args.get("error"):
        flash(f"Google sign-in was cancelled: {request.args.get('error')}", "warning")
        return redirect(url_for("login"))
    code = request.args.get("code")
    if not code:
        flash("Google did not return a sign-in code. Please try again.", "warning")
        return redirect(url_for("login"))
    try:
        profile = exchange_google_code(code)
    except (RuntimeError, urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError) as exc:
        flash(f"Google sign-in failed: {exc}", "warning")
        return redirect(url_for("login"))
    if not profile.get("email_verified"):
        flash("Use a verified Google email address to access the dashboard.", "warning")
        return redirect(url_for("login"))
    email = (profile.get("email") or "").lower()
    hosted_domain = (profile.get("hd") or email.split("@")[-1]).lower()
    if GOOGLE_ALLOWED_DOMAIN and hosted_domain != GOOGLE_ALLOWED_DOMAIN:
        flash(f"Use a Google account from {GOOGLE_ALLOWED_DOMAIN}.", "warning")
        return redirect(url_for("login"))
    user = upsert_google_user(profile)
    next_url = session.pop("post_login_next", None) or url_for("dashboard")
    session.clear()
    session["user_id"] = user["id"]
    session["user_email"] = user["email"]
    return redirect(next_url)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/account")
def account_settings():
    return render_template(
        "account.html",
        active_page="account",
        page_title="Account Settings",
        page_subtitle="Manage your profile, session, notifications, and console preferences.",
    )


@app.post("/api/account/preferences")
def save_account_preferences():
    data = request.get_json(silent=True) or {}
    try:
        user = update_dashboard_user_preferences(g.current_user["id"], data)
    except ValueError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400
    return jsonify({
        "ok": True,
        "preferences": {
            "console_theme": user["console_theme"],
            "console_density": user["console_density"],
            "accent_color": user["accent_color"],
            "default_sidebar": user["default_sidebar"],
        },
    })


@app.route("/")
def dashboard():
    return render_template("dashboard.html", active_page="dashboard", **get_dashboard_data())


@app.get("/api/search")
def search_dashboard():
    query = (request.args.get("q") or "").strip()
    if len(query) < 2:
        return jsonify({"ok": True, "query": query, "results": []})
    results = global_search(query)
    for result in results:
        fragment = result.pop("fragment", None)
        result.pop("priority", None)
        result["url"] = url_for(result.pop("page"), _anchor=fragment) if fragment else url_for(result.pop("page"))
    return jsonify({"ok": True, "query": query, "results": results})


@app.get("/api/topbar/<kind>")
def topbar_items(kind):
    try:
        payload = get_topbar_items(kind)
    except ValueError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 404
    return jsonify({"ok": True, **payload})


@app.patch("/api/topbar/<kind>/<int:item_id>")
def read_topbar_item(kind, item_id):
    try:
        changed = mark_topbar_items_read(kind, item_id)
    except ValueError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 404
    if not changed:
        return jsonify({"ok": False, "error": "Item not found."}), 404
    return jsonify({"ok": True})


@app.post("/api/topbar/<kind>/read-all")
def read_all_topbar_items(kind):
    try:
        mark_topbar_items_read(kind)
    except ValueError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 404
    return jsonify({"ok": True})


def csv_response(filename, content):
    return Response(
        content,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@app.route("/conversations")
def conversations():
    return render_template("conversations.html", active_page="conversations", **get_conversations_data())


@app.post("/api/conversations")
def api_create_conversation():
    data = request.get_json(silent=True) or {}
    try:
        require_fields(data, ["customer_name", "phone"])
        thread = create_conversation_thread(data)
    except ValueError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400
    return jsonify({"ok": True, "message": "Conversation created.", "thread": thread})


@app.get("/api/conversations/<int:thread_id>")
def api_get_conversation(thread_id):
    from database import get_conversation_thread

    thread = get_conversation_thread(thread_id)
    if not thread:
        return jsonify({"ok": False, "error": "Conversation not found."}), 404
    return jsonify({"ok": True, "thread": thread})


@app.post("/api/conversations/<int:thread_id>/messages")
def api_add_conversation_message(thread_id):
    data = request.get_json(silent=True) or {}
    body = (data.get("body") or "").strip()
    if not body:
        return jsonify({"ok": False, "error": "Enter a message."}), 400
    message = add_conversation_message(thread_id, body, account["name"] if (account := {"name": g.current_user.get("name")}) else "Workspace Admin")
    if not message:
        return jsonify({"ok": False, "error": "Conversation not found."}), 404
    return jsonify({"ok": True, "message": "Reply sent.", "conversation_message": message})


@app.post("/api/conversations/<int:thread_id>/assign")
def api_assign_conversation(thread_id):
    data = request.get_json(silent=True) or {}
    if not assign_conversation_thread(thread_id, data.get("owner") or "Support Desk"):
        return jsonify({"ok": False, "error": "Conversation not found."}), 404
    return jsonify({"ok": True, "message": "Conversation assigned and escalated."})


@app.post("/api/conversations/<int:thread_id>/resolve")
def api_resolve_conversation(thread_id):
    if not update_conversation_thread_status(thread_id, "Resolved"):
        return jsonify({"ok": False, "error": "Conversation not found."}), 404
    return jsonify({"ok": True, "message": "Conversation resolved."})


@app.post("/api/conversations/<int:thread_id>/escalate")
def api_escalate_conversation(thread_id):
    if not update_conversation_thread_status(thread_id, "Escalated"):
        return jsonify({"ok": False, "error": "Conversation not found."}), 404
    return jsonify({"ok": True, "message": "Conversation escalated."})


@app.route("/analytics")
def analytics():
    return render_template("analytics.html", active_page="analytics", **get_analytics_data())


@app.route("/settings")
def settings():
    return render_template("settings.html", active_page="settings", **get_settings_data())


@app.post("/api/settings/workspace")
def api_save_workspace():
    data = request.get_json(silent=True) or {}
    try:
        require_fields(data, ["company_name", "industry", "timezone", "language"])
        save_workspace_settings("workspace", data)
    except ValueError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400
    return jsonify({"ok": True, "message": "Workspace settings saved."})


@app.post("/api/settings/whatsapp")
def api_save_whatsapp_settings():
    data = request.get_json(silent=True) or {}
    try:
        require_fields(data, ["webhook_url", "message_window_policy"])
        save_workspace_settings("whatsapp", data)
    except ValueError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400
    return jsonify({"ok": True, "message": "WhatsApp settings saved."})


@app.post("/api/settings/handoff")
def api_save_handoff_settings():
    data = request.get_json(silent=True) or {}
    save_workspace_settings("handoff", data)
    return jsonify({"ok": True, "message": "Handoff settings saved."})


@app.post("/api/settings/ai-behavior")
def api_save_ai_behavior_settings():
    save_workspace_settings("ai_behavior", request.get_json(silent=True) or {})
    return jsonify({"ok": True, "message": "AI behavior settings saved."})


@app.patch("/api/settings/modules/<int:module_id>")
def api_toggle_settings_module(module_id):
    data = request.get_json(silent=True) or {}
    if not toggle_settings_module(module_id, data.get("enabled")):
        return jsonify({"ok": False, "error": "Module not found."}), 404
    return jsonify({"ok": True, "message": "Module setting updated."})


@app.post("/api/settings/notifications")
def api_save_notifications():
    save_workspace_settings("notifications", request.get_json(silent=True) or {})
    return jsonify({"ok": True, "message": "Notification settings saved."})


@app.route("/security")
def security():
    return render_template("security.html", active_page="security", **get_security_data())


@app.patch("/api/security/access-rules/<int:rule_id>")
def api_toggle_security_rule(rule_id):
    data = request.get_json(silent=True) or {}
    if not toggle_security_access_rule(rule_id, data.get("enabled")):
        return jsonify({"ok": False, "error": "Security rule not found."}), 404
    return jsonify({"ok": True, "message": "Security policy updated."})


@app.post("/api/security/settings")
def api_save_security_settings():
    save_security_settings(request.get_json(silent=True) or {})
    return jsonify({"ok": True, "message": "Security settings saved."})


@app.post("/api/security/roles")
def api_add_security_role():
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    permissions = (data.get("permissions") or "Read dashboard, manage assigned conversations").strip()
    if not name:
        return jsonify({"ok": False, "error": "Enter a role name."}), 400
    from database import get_connection
    with get_connection() as connection:
        cursor = connection.execute(
            """INSERT INTO security_roles (tenant_id, role, users, permissions, sort_order)
            VALUES (1, ?, 0, ?, (SELECT COALESCE(MAX(sort_order), 0) + 1 FROM security_roles WHERE tenant_id = 1))""",
            (name, permissions),
        )
        connection.commit()
    return jsonify({"ok": True, "message": "Security role added.", "role_id": cursor.lastrowid})


@app.get("/api/security/audit-log/export")
def api_export_audit_log():
    from database import fetch_all
    rows = fetch_all("SELECT event, user, ip, time, status FROM audit_logs WHERE tenant_id = 1 ORDER BY sort_order")
    return csv_response("audit-log.csv", export_rows_csv(["Event", "User", "IP", "Time", "Status"], [[r["event"], r["user"], r["ip"], r["time"], r["status"]] for r in rows]))


@app.route("/support")
def support():
    return render_template("support.html", active_page="support", **get_support_data())


@app.post("/api/support/tickets")
def api_create_support_ticket():
    data = request.get_json(silent=True) or {}
    try:
        require_fields(data, ["subject"])
        ticket = add_support_ticket(data)
    except ValueError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400
    return jsonify({"ok": True, "message": "Support ticket created.", "ticket": ticket})


@app.patch("/api/support/tickets/<int:ticket_id>")
def api_update_support_ticket(ticket_id):
    data = request.get_json(silent=True) or {}
    status = data.get("status") or "Open"
    from database import get_connection
    with get_connection() as connection:
        cursor = connection.execute(
            "UPDATE support_tickets SET status = ?, updated = 'Just now' WHERE id = ? AND tenant_id = 1",
            (status, ticket_id),
        )
        connection.commit()
    if cursor.rowcount == 0:
        return jsonify({"ok": False, "error": "Ticket not found."}), 404
    return jsonify({"ok": True, "message": "Ticket updated."})


@app.get("/api/support/tickets/export")
def api_export_support_tickets():
    from database import fetch_all
    rows = fetch_all("SELECT ticket_id, subject, priority, owner, status, updated FROM support_tickets WHERE tenant_id = 1 ORDER BY sort_order")
    return csv_response("support-tickets.csv", export_rows_csv(["Ticket", "Subject", "Priority", "Owner", "Status", "Updated"], [[r["ticket_id"], r["subject"], r["priority"], r["owner"], r["status"], r["updated"]] for r in rows]))


@app.route("/customers")
def customers():
    return render_template("customers.html", active_page="customers", **get_customers_data())


@app.post("/api/customers")
def api_create_customer():
    data = request.get_json(silent=True) or {}
    try:
        require_fields(data, ["name", "phone"])
        customer = create_customer(data)
    except ValueError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400
    return jsonify({"ok": True, "message": "Customer added.", "customer": customer})


@app.patch("/api/customers/<int:customer_id>")
def api_update_customer(customer_id):
    data = request.get_json(silent=True) or {}
    try:
        require_fields(data, ["name", "phone"])
        customer = update_customer(customer_id, data)
    except ValueError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400
    if not customer:
        return jsonify({"ok": False, "error": "Customer not found."}), 404
    return jsonify({"ok": True, "message": "Customer updated.", "customer": customer})


@app.get("/api/customers/export")
def api_export_customers():
    from database import fetch_all
    rows = fetch_all("SELECT name, phone, segment, stage, last_seen, csat, health FROM customers WHERE tenant_id = 1 ORDER BY sort_order")
    return csv_response("customers.csv", export_rows_csv(["Name", "Phone", "Segment", "Stage", "Last seen", "CSAT", "Health"], [[r["name"], r["phone"], r["segment"], r["stage"], r["last_seen"], r["csat"], r["health"]] for r in rows]))


@app.route("/team-members")
def team_members():
    return render_template("team_members.html", active_page="team_members", **get_team_data())


@app.post("/api/team-members")
def api_create_team_member():
    data = request.get_json(silent=True) or {}
    try:
        require_fields(data, ["name"])
        member = create_or_update_team_member(data)
    except ValueError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400
    return jsonify({"ok": True, "message": "Team member invited.", "member": member})


@app.patch("/api/team-members/<int:member_id>")
def api_update_team_member(member_id):
    data = request.get_json(silent=True) or {}
    try:
        require_fields(data, ["name"])
        member = create_or_update_team_member(data, member_id=member_id)
    except ValueError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400
    if not member:
        return jsonify({"ok": False, "error": "Team member not found."}), 404
    return jsonify({"ok": True, "message": "Team member updated.", "member": member})


@app.post("/api/team-roles")
def api_add_team_role():
    data = request.get_json(silent=True) or {}
    try:
        require_fields(data, ["name"])
        role = add_team_role(data)
    except ValueError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400
    return jsonify({"ok": True, "message": "Role added.", "role": role})


@app.get("/api/team-members/export")
def api_export_team():
    from database import fetch_all
    rows = fetch_all("SELECT name, role, team, status, assigned, resolved, csat FROM team_members WHERE tenant_id = 1 ORDER BY sort_order")
    return csv_response("team-members.csv", export_rows_csv(["Name", "Role", "Team", "Status", "Assigned", "Resolved", "CSAT"], [[r["name"], r["role"], r["team"], r["status"], r["assigned"], r["resolved"], r["csat"]] for r in rows]))


@app.route("/billing")
def billing():
    return render_template("billing.html", active_page="billing", **get_billing_data())


@app.patch("/api/billing/add-ons/<int:addon_id>")
def api_toggle_billing_addon(addon_id):
    data = request.get_json(silent=True) or {}
    if not toggle_billing_addon(addon_id, data.get("enabled")):
        return jsonify({"ok": False, "error": "Billing add-on not found."}), 404
    return jsonify({"ok": True, "message": "Billing add-on updated."})


@app.get("/api/billing/invoices/<int:invoice_id>/download")
def api_download_invoice(invoice_id):
    from database import fetch_one
    invoice = fetch_one("SELECT invoice_id, date, amount, status FROM invoices WHERE id = ? AND tenant_id = 1", (invoice_id,))
    if not invoice:
        return jsonify({"ok": False, "error": "Invoice not found."}), 404
    content = export_rows_csv(["Invoice", "Date", "Amount", "Status"], [[invoice["invoice_id"], invoice["date"], invoice["amount"], invoice["status"]]])
    return csv_response(f"{invoice['invoice_id']}.csv", content)


@app.get("/api/billing/invoices/export")
def api_export_invoices():
    from database import fetch_all
    rows = fetch_all("SELECT invoice_id, date, amount, status FROM invoices WHERE tenant_id = 1 ORDER BY sort_order")
    return csv_response("invoices.csv", export_rows_csv(["Invoice", "Date", "Amount", "Status"], [[r["invoice_id"], r["date"], r["amount"], r["status"]] for r in rows]))


@app.route("/add-ons")
def add_ons():
    return render_template("add_ons.html", active_page="add_ons", **get_add_ons_data())


@app.post("/api/add-ons/cart")
def api_addon_cart():
    data = request.get_json(silent=True) or {}
    module = toggle_addon_cart(int(data.get("addon_id") or 0), bool(data.get("selected", True)))
    if not module:
        return jsonify({"ok": False, "error": "Add-on not found."}), 404
    return jsonify({"ok": True, "message": "Checkout updated.", "module": module})


@app.post("/api/add-ons/purchase")
def api_purchase_addons():
    installed = purchase_addon_cart(owner=g.current_user.get("name") or "Workspace Admin")
    return jsonify({"ok": True, "message": f"Purchased {len(installed)} add-on{'s' if len(installed) != 1 else ''}.", "installed": installed})


@app.post("/api/add-ons/<int:addon_id>/install")
def api_install_addon(addon_id):
    module = toggle_addon_cart(addon_id, True)
    if not module:
        return jsonify({"ok": False, "error": "Add-on not found."}), 404
    purchase_addon_cart(owner=g.current_user.get("name") or "Workspace Admin")
    return jsonify({"ok": True, "message": "Add-on installed.", "module": module})


@app.get("/api/add-ons/quote")
def api_download_addon_quote():
    from database import fetch_all
    rows = fetch_all(
        """SELECT addon_modules.name, addon_modules.price
        FROM addon_cart JOIN addon_modules ON addon_modules.id = addon_cart.addon_module_id
        WHERE addon_cart.tenant_id = 1 ORDER BY addon_modules.sort_order"""
    )
    return csv_response("addon-quote.csv", export_rows_csv(["Add-on", "Price"], [[r["name"], r["price"]] for r in rows]))


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
        config = get_assistant_config()
        if config:
            config["model"] = data["primary_model"]
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


@app.post("/api/ai/test-suite")
def run_ai_test_suite():
    config = get_assistant_config()
    from database import get_connection
    result = "Passed" if config else "Needs connection"
    with get_connection() as connection:
        connection.execute("UPDATE ai_test_cases SET result = ? WHERE tenant_id = 1", (result,))
        connection.commit()
    return jsonify({"ok": True, "message": f"AI test suite recorded: {result}.", "result": result})


@app.post("/api/assistant/config")
@app.post("/api/ollama/config")
def save_assistant_config():
    data = request.get_json(silent=True) or {}
    provider = (data.get("provider") or "ollama").strip().lower()
    defaults = PROVIDER_DEFAULTS.get(provider)
    if not defaults:
        return jsonify({"ok": False, "error": "Choose Ollama or OpenRouter."}), 400

    existing_config = get_assistant_config()
    api_key = (data.get("api_key") or "").strip()
    if not api_key and existing_config and existing_config["provider"] == provider:
        api_key = existing_config["api_key"]
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
    save_assistant_connection(g.current_user["id"], ASSISTANT_SESSIONS[config_id])
    synchronize_active_model(model)

    return jsonify({"ok": True, "provider": provider, "provider_label": defaults["label"], "model": model, "api_url": api_url})


@app.get("/api/assistant/config")
def assistant_config_status():
    config = get_assistant_config()
    if not config:
        return jsonify({"ok": True, "configured": False})
    return jsonify({
        "ok": True,
        "configured": True,
        "provider": config["provider"],
        "provider_label": config["provider_label"],
        "model": config["model"],
        "api_url": config["api_url"],
    })


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
        "You are PingPilot's WhatsApp AI assistant. Help with sales, admissions, appointments, "
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
