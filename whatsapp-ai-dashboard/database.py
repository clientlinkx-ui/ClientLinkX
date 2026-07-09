import json
import sqlite3
from pathlib import Path
from datetime import datetime


BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "pingpilot_dashboard.db"


def get_connection():
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def fetch_all(sql, params=()):
    with get_connection() as connection:
        return [dict(row) for row in connection.execute(sql, params).fetchall()]


def fetch_one(sql, params=()):
    with get_connection() as connection:
        row = connection.execute(sql, params).fetchone()
        return dict(row) if row else None


def init_db():
    with get_connection() as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        create_schema(connection)
        seeded = connection.execute("SELECT COUNT(*) FROM tenants").fetchone()[0]
        if seeded == 0:
            seed_database(connection)
        run_migrations(connection)


def create_schema(connection):
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS tenants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            industry TEXT NOT NULL,
            timezone TEXT NOT NULL,
            language TEXT NOT NULL,
            owner_user_id INTEGER,
            subscription_plan TEXT NOT NULL DEFAULT 'growth',
            billing_cycle TEXT NOT NULL DEFAULT 'monthly',
            company_email TEXT NOT NULL DEFAULT '',
            company_phone TEXT NOT NULL DEFAULT '',
            onboarding_status TEXT NOT NULL DEFAULT 'complete'
        );

        CREATE TABLE IF NOT EXISTS dashboard_users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id INTEGER,
            google_sub TEXT NOT NULL UNIQUE,
            email TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            picture TEXT,
            hosted_domain TEXT,
            permission_group TEXT NOT NULL DEFAULT 'admin',
            onboarding_complete INTEGER NOT NULL DEFAULT 0,
            console_theme TEXT NOT NULL DEFAULT 'auto',
            console_density TEXT NOT NULL DEFAULT 'comfortable',
            accent_color TEXT NOT NULL DEFAULT 'teal',
            default_sidebar TEXT NOT NULL DEFAULT 'expanded',
            last_login_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE SET NULL
        );

        CREATE TABLE IF NOT EXISTS pages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id INTEGER NOT NULL,
            slug TEXT NOT NULL UNIQUE,
            title TEXT NOT NULL,
            subtitle TEXT NOT NULL,
            FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS summary_metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            page_id INTEGER NOT NULL,
            label TEXT NOT NULL,
            value TEXT NOT NULL,
            icon TEXT,
            tone TEXT,
            change TEXT,
            sort_order INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (page_id) REFERENCES pages(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS dashboard_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            page_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            value TEXT NOT NULL,
            change TEXT NOT NULL,
            trend TEXT NOT NULL,
            icon TEXT NOT NULL,
            sort_order INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (page_id) REFERENCES pages(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS dashboard_conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id INTEGER NOT NULL,
            customer_name TEXT NOT NULL,
            avatar TEXT,
            time TEXT NOT NULL,
            last_message TEXT NOT NULL,
            handler TEXT NOT NULL,
            status TEXT NOT NULL,
            unread INTEGER NOT NULL DEFAULT 0,
            sort_order INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS dashboard_activities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            activity_type TEXT NOT NULL,
            icon TEXT NOT NULL,
            time TEXT NOT NULL,
            user TEXT NOT NULL,
            status TEXT NOT NULL,
            sort_order INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS performance_metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            page_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            subtitle TEXT,
            icon TEXT,
            value TEXT NOT NULL,
            unit TEXT,
            progress INTEGER NOT NULL DEFAULT 0,
            status TEXT,
            change TEXT,
            sort_order INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (page_id) REFERENCES pages(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS business_modules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            value TEXT NOT NULL,
            label TEXT NOT NULL,
            progress INTEGER NOT NULL DEFAULT 0,
            icon TEXT,
            sort_order INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS escalations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id INTEGER NOT NULL,
            team TEXT NOT NULL,
            count INTEGER NOT NULL,
            sla TEXT NOT NULL,
            tone TEXT NOT NULL,
            sort_order INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS conversation_threads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id INTEGER NOT NULL,
            customer_name TEXT NOT NULL,
            phone TEXT NOT NULL,
            intent TEXT NOT NULL,
            module TEXT NOT NULL,
            handler TEXT NOT NULL,
            status TEXT NOT NULL,
            priority TEXT NOT NULL,
            sentiment TEXT NOT NULL,
            time TEXT NOT NULL,
            last_message TEXT NOT NULL,
            messages INTEGER NOT NULL,
            sla TEXT NOT NULL,
            sort_order INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS ai_escalation_decisions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            thread_id INTEGER NOT NULL,
            tenant_id INTEGER NOT NULL,
            decision TEXT NOT NULL,
            confidence INTEGER NOT NULL,
            reason TEXT NOT NULL,
            suggested_action TEXT NOT NULL,
            risk_flags TEXT NOT NULL DEFAULT '[]',
            model TEXT NOT NULL,
            mode TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(thread_id, tenant_id),
            FOREIGN KEY (thread_id) REFERENCES conversation_threads(id) ON DELETE CASCADE,
            FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS quick_filters (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            page_id INTEGER NOT NULL,
            label TEXT NOT NULL,
            sort_order INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (page_id) REFERENCES pages(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS analytics_funnels (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            value TEXT NOT NULL,
            progress INTEGER NOT NULL,
            sort_order INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS analytics_intents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            count TEXT NOT NULL,
            share INTEGER NOT NULL,
            sort_order INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS team_performance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            resolved INTEGER NOT NULL,
            avg_sla TEXT NOT NULL,
            csat TEXT NOT NULL,
            sort_order INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS security_access_rules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            detail TEXT NOT NULL,
            enabled INTEGER NOT NULL DEFAULT 0,
            sort_order INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS security_roles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id INTEGER NOT NULL,
            role TEXT NOT NULL,
            users INTEGER NOT NULL,
            permissions TEXT NOT NULL,
            sort_order INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id INTEGER NOT NULL,
            event TEXT NOT NULL,
            user TEXT NOT NULL,
            ip TEXT NOT NULL,
            time TEXT NOT NULL,
            status TEXT NOT NULL,
            sort_order INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS compliance_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            value TEXT NOT NULL,
            progress INTEGER NOT NULL,
            sort_order INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS support_tickets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id INTEGER NOT NULL,
            ticket_id TEXT NOT NULL,
            subject TEXT NOT NULL,
            priority TEXT NOT NULL,
            owner TEXT NOT NULL,
            status TEXT NOT NULL,
            updated TEXT NOT NULL,
            sort_order INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS status_checks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            status TEXT NOT NULL,
            detail TEXT NOT NULL,
            sort_order INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS support_resources (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            detail TEXT NOT NULL,
            icon TEXT NOT NULL,
            sort_order INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS customer_segments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            value TEXT NOT NULL,
            progress INTEGER NOT NULL,
            sort_order INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            phone TEXT NOT NULL,
            segment TEXT NOT NULL,
            stage TEXT NOT NULL,
            last_seen TEXT NOT NULL,
            csat TEXT NOT NULL,
            health TEXT NOT NULL,
            sort_order INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS customer_timeline (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            customer TEXT NOT NULL,
            time TEXT NOT NULL,
            status TEXT NOT NULL,
            sort_order INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS teams (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            members INTEGER NOT NULL,
            queue INTEGER NOT NULL,
            sla TEXT NOT NULL,
            progress INTEGER NOT NULL,
            sort_order INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS team_members (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            email TEXT NOT NULL DEFAULT '',
            permission_group TEXT NOT NULL DEFAULT 'agent',
            role TEXT NOT NULL,
            team TEXT NOT NULL,
            status TEXT NOT NULL,
            assigned INTEGER NOT NULL,
            resolved INTEGER NOT NULL,
            csat TEXT NOT NULL,
            sort_order INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS team_roles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id INTEGER NOT NULL,
            role_key TEXT NOT NULL DEFAULT '',
            name TEXT NOT NULL,
            description TEXT NOT NULL DEFAULT '',
            role_type TEXT NOT NULL DEFAULT 'custom',
            locked INTEGER NOT NULL DEFAULT 0,
            count INTEGER NOT NULL,
            scope TEXT NOT NULL,
            permissions TEXT NOT NULL DEFAULT '',
            sort_order INTEGER NOT NULL DEFAULT 0,
            UNIQUE(tenant_id, role_key),
            FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS billing_usage (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            value TEXT NOT NULL,
            progress INTEGER NOT NULL,
            sort_order INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS invoices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id INTEGER NOT NULL,
            invoice_id TEXT NOT NULL,
            date TEXT NOT NULL,
            amount TEXT NOT NULL,
            status TEXT NOT NULL,
            sort_order INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS billing_addons (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            detail TEXT NOT NULL,
            price TEXT NOT NULL,
            enabled INTEGER NOT NULL DEFAULT 0,
            sort_order INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS billing_contacts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            role TEXT NOT NULL,
            sort_order INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS addon_modules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            price TEXT NOT NULL,
            status TEXT NOT NULL,
            icon TEXT,
            description TEXT,
            fit TEXT,
            is_featured INTEGER NOT NULL DEFAULT 0,
            sort_order INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS addon_features (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            addon_module_id INTEGER NOT NULL,
            feature TEXT NOT NULL,
            sort_order INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (addon_module_id) REFERENCES addon_modules(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS tenant_addons (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id INTEGER NOT NULL,
            addon_module_id INTEGER NOT NULL,
            owner TEXT NOT NULL,
            renewal TEXT NOT NULL,
            usage TEXT NOT NULL,
            sort_order INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE,
            FOREIGN KEY (addon_module_id) REFERENCES addon_modules(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS industry_recommendations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            modules TEXT NOT NULL,
            progress INTEGER NOT NULL,
            sort_order INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS subscription_estimates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id INTEGER NOT NULL,
            label TEXT NOT NULL,
            value TEXT NOT NULL,
            sort_order INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS ai_assistants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            model TEXT NOT NULL,
            module TEXT NOT NULL,
            status TEXT NOT NULL,
            confidence INTEGER NOT NULL,
            sort_order INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS ai_guardrails (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            detail TEXT NOT NULL,
            enabled INTEGER NOT NULL DEFAULT 0,
            sort_order INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS ai_test_cases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id INTEGER NOT NULL,
            prompt TEXT NOT NULL,
            intent TEXT NOT NULL,
            result TEXT NOT NULL,
            sort_order INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS kb_sources (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            type TEXT NOT NULL,
            documents INTEGER NOT NULL,
            status TEXT NOT NULL,
            updated TEXT NOT NULL,
            sort_order INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS kb_coverage (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            value TEXT NOT NULL,
            progress INTEGER NOT NULL,
            sort_order INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS kb_gaps (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id INTEGER NOT NULL,
            topic TEXT NOT NULL,
            impact TEXT NOT NULL,
            owner TEXT NOT NULL,
            status TEXT NOT NULL,
            sort_order INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS kb_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            category TEXT NOT NULL,
            content TEXT NOT NULL,
            tags TEXT,
            status TEXT NOT NULL DEFAULT 'Published',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            sort_order INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS prompts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            module TEXT NOT NULL,
            version TEXT NOT NULL,
            status TEXT NOT NULL,
            pass_rate INTEGER NOT NULL,
            sort_order INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS prompt_variables (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            source TEXT NOT NULL,
            required INTEGER NOT NULL DEFAULT 0,
            sort_order INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS prompt_tests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id INTEGER NOT NULL,
            test_case TEXT NOT NULL,
            intent TEXT NOT NULL,
            result TEXT NOT NULL,
            sort_order INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS workflows (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            trigger TEXT NOT NULL,
            owner TEXT NOT NULL,
            status TEXT NOT NULL,
            runs TEXT NOT NULL,
            success INTEGER NOT NULL,
            sort_order INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS workflow_steps (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            detail TEXT NOT NULL,
            sort_order INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS workflow_rules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            detail TEXT NOT NULL,
            enabled INTEGER NOT NULL DEFAULT 0,
            sort_order INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS settings_channels (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            status TEXT NOT NULL,
            detail TEXT NOT NULL,
            tone TEXT NOT NULL,
            sort_order INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS settings_models (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            model TEXT NOT NULL,
            temperature TEXT NOT NULL,
            status TEXT NOT NULL,
            sort_order INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS settings_modules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            enabled INTEGER NOT NULL DEFAULT 0,
            owner TEXT NOT NULL,
            sort_order INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS topbar_notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            body TEXT NOT NULL,
            icon TEXT NOT NULL,
            url TEXT NOT NULL,
            is_read INTEGER NOT NULL DEFAULT 0,
            time TEXT NOT NULL,
            sort_order INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS topbar_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id INTEGER NOT NULL,
            sender TEXT NOT NULL,
            preview TEXT NOT NULL,
            initials TEXT NOT NULL,
            url TEXT NOT NULL,
            is_read INTEGER NOT NULL DEFAULT 0,
            time TEXT NOT NULL,
            sort_order INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
        );
        """
    )


def run_migrations(connection):
    user_columns = {
        row["name"]
        for row in connection.execute("PRAGMA table_info(dashboard_users)").fetchall()
    }
    for name, definition in {
        "console_theme": "TEXT NOT NULL DEFAULT 'auto'",
        "console_density": "TEXT NOT NULL DEFAULT 'comfortable'",
        "accent_color": "TEXT NOT NULL DEFAULT 'teal'",
        "default_sidebar": "TEXT NOT NULL DEFAULT 'expanded'",
    }.items():
        if user_columns and name not in user_columns:
            connection.execute(f"ALTER TABLE dashboard_users ADD COLUMN {name} {definition}")
    if user_columns and "console_theme" in user_columns:
        connection.execute(
            """UPDATE dashboard_users
            SET console_theme = 'auto'
            WHERE console_theme = 'light'
              AND console_density = 'comfortable'
              AND accent_color = 'teal'
              AND default_sidebar = 'expanded'"""
        )

    columns = {
        row["name"]
        for row in connection.execute("PRAGMA table_info(kb_entries)").fetchall()
    }
    if columns and "sort_order" not in columns:
        connection.execute("ALTER TABLE kb_entries ADD COLUMN sort_order INTEGER NOT NULL DEFAULT 0")

    prompt_columns = {row["name"] for row in connection.execute("PRAGMA table_info(prompts)").fetchall()}
    for name, definition in {
        "instructions": "TEXT NOT NULL DEFAULT ''",
        "deployment_target": "TEXT NOT NULL DEFAULT 'Staging'",
    }.items():
        if name not in prompt_columns:
            connection.execute(f"ALTER TABLE prompts ADD COLUMN {name} {definition}")

    workflow_columns = {row["name"] for row in connection.execute("PRAGMA table_info(workflows)").fetchall()}
    for name, definition in {
        "run_mode": "TEXT NOT NULL DEFAULT 'Automatic'",
        "failure_action": "TEXT NOT NULL DEFAULT 'Create support ticket'",
    }.items():
        if name not in workflow_columns:
            connection.execute(f"ALTER TABLE workflows ADD COLUMN {name} {definition}")

    thread_columns = {row["name"] for row in connection.execute("PRAGMA table_info(conversation_threads)").fetchall()}
    for name, definition in {
        "assigned_team": "TEXT NOT NULL DEFAULT ''",
        "assigned_user_id": "INTEGER",
        "assigned_user_name": "TEXT NOT NULL DEFAULT ''",
        "assigned_at": "TEXT NOT NULL DEFAULT ''",
        "resolved_at": "TEXT NOT NULL DEFAULT ''",
    }.items():
        if thread_columns and name not in thread_columns:
            connection.execute(f"ALTER TABLE conversation_threads ADD COLUMN {name} {definition}")

    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS ai_runtime_settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id INTEGER NOT NULL UNIQUE,
            primary_model TEXT NOT NULL,
            fallback_model TEXT NOT NULL,
            confidence_threshold INTEGER NOT NULL,
            temperature INTEGER NOT NULL,
            system_prompt TEXT NOT NULL,
            deployment_version INTEGER NOT NULL DEFAULT 1,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS kb_sync_settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id INTEGER NOT NULL UNIQUE,
            frequency TEXT NOT NULL,
            approval_mode TEXT NOT NULL,
            notify_failures INTEGER NOT NULL DEFAULT 1,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS conversation_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            thread_id INTEGER NOT NULL,
            tenant_id INTEGER NOT NULL,
            sender TEXT NOT NULL,
            role TEXT NOT NULL,
            body TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            sort_order INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (thread_id) REFERENCES conversation_threads(id) ON DELETE CASCADE,
            FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS workspace_settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id INTEGER NOT NULL UNIQUE,
            webhook_url TEXT NOT NULL DEFAULT 'https://api.pingpilot.ai/webhooks/whatsapp',
            message_window_policy TEXT NOT NULL DEFAULT '24 hour service window',
            default_handoff_team TEXT NOT NULL DEFAULT 'Support Desk',
            sla_target TEXT NOT NULL DEFAULT 'Under 10 minutes',
            daily_digest INTEGER NOT NULL DEFAULT 1,
            escalation_alerts INTEGER NOT NULL DEFAULT 1,
            kb_failure_alerts INTEGER NOT NULL DEFAULT 1,
            kb_grounding INTEGER NOT NULL DEFAULT 1,
            intent_detection INTEGER NOT NULL DEFAULT 1,
            handoff_low_confidence INTEGER NOT NULL DEFAULT 1,
            handoff_negative_sentiment INTEGER NOT NULL DEFAULT 1,
            escalation_decision_mode TEXT NOT NULL DEFAULT 'recommend',
            require_2fa INTEGER NOT NULL DEFAULT 1,
            mask_phone_numbers INTEGER NOT NULL DEFAULT 1,
            retention_period TEXT NOT NULL DEFAULT '180 days',
            audit_export TEXT NOT NULL DEFAULT 'Monthly CSV',
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS assistant_connections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL UNIQUE,
            provider TEXT NOT NULL,
            provider_label TEXT NOT NULL,
            api_key TEXT NOT NULL,
            api_url TEXT NOT NULL,
            model TEXT NOT NULL,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES dashboard_users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS addon_cart (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id INTEGER NOT NULL,
            addon_module_id INTEGER NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(tenant_id, addon_module_id),
            FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE,
            FOREIGN KEY (addon_module_id) REFERENCES addon_modules(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS ai_escalation_decisions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            thread_id INTEGER NOT NULL,
            tenant_id INTEGER NOT NULL,
            decision TEXT NOT NULL,
            confidence INTEGER NOT NULL,
            reason TEXT NOT NULL,
            suggested_action TEXT NOT NULL,
            risk_flags TEXT NOT NULL DEFAULT '[]',
            model TEXT NOT NULL,
            mode TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(thread_id, tenant_id),
            FOREIGN KEY (thread_id) REFERENCES conversation_threads(id) ON DELETE CASCADE,
            FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS subscription_plans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            plan_key TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            monthly_price TEXT NOT NULL,
            yearly_price TEXT NOT NULL,
            conversation_limit TEXT NOT NULL,
            ai_message_limit TEXT NOT NULL,
            seat_limit TEXT NOT NULL,
            support_level TEXT NOT NULL,
            features TEXT NOT NULL,
            sort_order INTEGER NOT NULL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS onboarding_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL UNIQUE,
            company_name TEXT NOT NULL DEFAULT '',
            industry TEXT NOT NULL DEFAULT '',
            timezone TEXT NOT NULL DEFAULT 'Asia/Kolkata',
            language TEXT NOT NULL DEFAULT 'English',
            company_email TEXT NOT NULL DEFAULT '',
            company_phone TEXT NOT NULL DEFAULT '',
            selected_plan TEXT NOT NULL DEFAULT 'growth',
            billing_cycle TEXT NOT NULL DEFAULT 'monthly',
            email_verified INTEGER NOT NULL DEFAULT 0,
            whatsapp_verified INTEGER NOT NULL DEFAULT 0,
            current_step TEXT NOT NULL DEFAULT 'account',
            completed_at TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES dashboard_users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS verification_codes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            channel TEXT NOT NULL,
            destination TEXT NOT NULL,
            code_hash TEXT NOT NULL,
            purpose TEXT NOT NULL DEFAULT 'onboarding',
            attempts INTEGER NOT NULL DEFAULT 0,
            verified_at TEXT,
            expires_at TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES dashboard_users(id) ON DELETE CASCADE
        );
        """
    )
    tenant_columns = {row["name"] for row in connection.execute("PRAGMA table_info(tenants)").fetchall()}
    for name, definition in {
        "owner_user_id": "INTEGER",
        "subscription_plan": "TEXT NOT NULL DEFAULT 'growth'",
        "billing_cycle": "TEXT NOT NULL DEFAULT 'monthly'",
        "company_email": "TEXT NOT NULL DEFAULT ''",
        "company_phone": "TEXT NOT NULL DEFAULT ''",
        "onboarding_status": "TEXT NOT NULL DEFAULT 'complete'",
    }.items():
        if tenant_columns and name not in tenant_columns:
            connection.execute(f"ALTER TABLE tenants ADD COLUMN {name} {definition}")
    dashboard_user_columns = {row["name"] for row in connection.execute("PRAGMA table_info(dashboard_users)").fetchall()}
    if dashboard_user_columns and "tenant_id" not in dashboard_user_columns:
        connection.execute("ALTER TABLE dashboard_users ADD COLUMN tenant_id INTEGER")
    if dashboard_user_columns and "permission_group" not in dashboard_user_columns:
        connection.execute("ALTER TABLE dashboard_users ADD COLUMN permission_group TEXT NOT NULL DEFAULT 'admin'")
    if dashboard_user_columns and "onboarding_complete" not in dashboard_user_columns:
        connection.execute("ALTER TABLE dashboard_users ADD COLUMN onboarding_complete INTEGER NOT NULL DEFAULT 0")
    connection.execute(
        """UPDATE dashboard_users
        SET tenant_id = COALESCE(tenant_id, 1),
            onboarding_complete = 1
        WHERE EXISTS (SELECT 1 FROM tenants WHERE tenants.id = 1)
          AND (tenant_id IS NULL OR onboarding_complete = 0)
          AND (
            permission_group = 'owner'
            OR tenant_id IS NOT NULL
            OR id = (SELECT id FROM dashboard_users ORDER BY created_at, id LIMIT 1)
          )"""
    )
    team_member_columns = {row["name"] for row in connection.execute("PRAGMA table_info(team_members)").fetchall()}
    if team_member_columns and "email" not in team_member_columns:
        connection.execute("ALTER TABLE team_members ADD COLUMN email TEXT NOT NULL DEFAULT ''")
    if team_member_columns and "permission_group" not in team_member_columns:
        connection.execute("ALTER TABLE team_members ADD COLUMN permission_group TEXT NOT NULL DEFAULT 'agent'")
    connection.execute(
        """UPDATE dashboard_users
        SET permission_group = 'owner'
        WHERE id = (SELECT id FROM dashboard_users ORDER BY created_at, id LIMIT 1)
        AND onboarding_complete = 1
        AND NOT EXISTS (SELECT 1 FROM dashboard_users WHERE permission_group = 'owner')"""
    )
    connection.execute(
        """UPDATE tenants
        SET owner_user_id = COALESCE(owner_user_id, (SELECT id FROM dashboard_users WHERE permission_group = 'owner' ORDER BY created_at, id LIMIT 1)),
            onboarding_status = COALESCE(NULLIF(onboarding_status, ''), 'complete')
        WHERE id = 1"""
    )
    connection.execute("UPDATE dashboard_users SET permission_group = 'admin' WHERE permission_group IS NULL OR permission_group = ''")
    connection.execute("UPDATE team_members SET permission_group = 'agent' WHERE permission_group IS NULL OR permission_group = ''")
    support_columns = {row["name"] for row in connection.execute("PRAGMA table_info(support_tickets)").fetchall()}
    for name, definition in {
        "request_type": "TEXT NOT NULL DEFAULT 'Technical support'",
        "description": "TEXT NOT NULL DEFAULT ''",
        "attachment": "TEXT NOT NULL DEFAULT ''",
        "created_at": "TEXT NOT NULL DEFAULT ''",
    }.items():
        if support_columns and name not in support_columns:
            connection.execute(f"ALTER TABLE support_tickets ADD COLUMN {name} {definition}")
    team_role_columns = {row["name"] for row in connection.execute("PRAGMA table_info(team_roles)").fetchall()}
    if team_role_columns and "permissions" not in team_role_columns:
        connection.execute("ALTER TABLE team_roles ADD COLUMN permissions TEXT NOT NULL DEFAULT ''")
    for name, definition in {
        "role_key": "TEXT NOT NULL DEFAULT ''",
        "description": "TEXT NOT NULL DEFAULT ''",
        "role_type": "TEXT NOT NULL DEFAULT 'custom'",
        "locked": "INTEGER NOT NULL DEFAULT 0",
    }.items():
        if team_role_columns and name not in team_role_columns:
            connection.execute(f"ALTER TABLE team_roles ADD COLUMN {name} {definition}")
    role_rows = connection.execute("SELECT id, name, role_key, permissions, scope FROM team_roles WHERE tenant_id = 1").fetchall()
    used_role_keys = set()
    for row in role_rows:
        role_key = row["role_key"] or normalize_role_key(row["name"]) or f"role_{row['id']}"
        if role_key in used_role_keys:
            role_key = f"{role_key}_{row['id']}"
        used_role_keys.add(role_key)
        permissions = normalize_permissions(row["permissions"])
        connection.execute(
            """UPDATE team_roles
            SET role_key = ?, description = COALESCE(NULLIF(description, ''), scope), permissions = ?
            WHERE id = ?""",
            (role_key, json.dumps(permissions), row["id"]),
        )
    seed_system_roles(connection)
    connection.execute("INSERT OR IGNORE INTO workspace_settings (tenant_id) VALUES (1)")
    workspace_columns = {row["name"] for row in connection.execute("PRAGMA table_info(workspace_settings)").fetchall()}
    for name in ["kb_grounding", "intent_detection", "handoff_low_confidence", "handoff_negative_sentiment"]:
        if workspace_columns and name not in workspace_columns:
            connection.execute(f"ALTER TABLE workspace_settings ADD COLUMN {name} INTEGER NOT NULL DEFAULT 1")
    if workspace_columns and "escalation_decision_mode" not in workspace_columns:
        connection.execute("ALTER TABLE workspace_settings ADD COLUMN escalation_decision_mode TEXT NOT NULL DEFAULT 'recommend'")
    seed_subscription_plans(connection)
    connection.execute(
        """INSERT OR IGNORE INTO ai_runtime_settings
        (tenant_id, primary_model, fallback_model, confidence_threshold, temperature, system_prompt)
        VALUES (1, 'GPT-4.1 Mini', 'GPT-4.1 Nano', 78, 30,
        'You are EverTech''s WhatsApp AI assistant. Resolve customer questions using approved knowledge base content, collect only necessary details, and escalate uncertain or sensitive cases to a human team member.')"""
    )
    connection.execute(
        """INSERT OR IGNORE INTO kb_sync_settings
        (tenant_id, frequency, approval_mode, notify_failures)
        VALUES (1, 'Every 6 hours', 'Review before publish', 1)"""
    )
    connection.execute(
        """UPDATE prompts SET instructions = CASE module
        WHEN 'Sales' THEN 'Qualify the customer request, collect only required lead details, and route high-intent opportunities to the sales team.'
        WHEN 'Admissions' THEN 'Answer admissions questions using approved knowledge, collect course and intake preferences, and route qualified applicants to admissions.'
        ELSE 'Resolve the customer request using approved knowledge base context. Keep responses concise and escalate sensitive, uncertain, or frustrated cases to a human agent.' END
        WHERE instructions = ''"""
    )
    if connection.execute("SELECT COUNT(*) FROM topbar_notifications").fetchone()[0] == 0:
        connection.executemany(
            """INSERT INTO topbar_notifications
            (tenant_id, title, body, icon, url, is_read, time, sort_order)
            VALUES (1, ?, ?, ?, ?, ?, ?, ?)""",
            [
                ("SLA needs attention", "Two escalations are approaching their response deadline.", "fa-solid fa-clock", "/conversations", 0, "5m", 1),
                ("Knowledge sync completed", "148 documents are available to the AI assistant.", "fa-solid fa-arrows-rotate", "/knowledge-base", 0, "22m", 2),
                ("Prompt deployed", "Support resolution prompt v3.4 is now live.", "fa-solid fa-rocket", "/prompt-builder", 0, "1h", 3),
                ("Invoice paid", "Invoice INV-2026-071 was paid successfully.", "fa-solid fa-receipt", "/billing", 1, "1d", 4),
            ],
        )
    if connection.execute("SELECT COUNT(*) FROM topbar_messages").fetchone()[0] == 0:
        connection.executemany(
            """INSERT INTO topbar_messages
            (tenant_id, sender, preview, initials, url, is_read, time, sort_order)
            VALUES (1, ?, ?, ?, ?, ?, ?, ?)""",
            [
                ("Priya Nair", "Can you confirm when my order will arrive?", "PN", "/conversations", 0, "2m", 1),
                ("Arjun Mehta", "I need details about the MBA admission fees.", "AM", "/conversations", 0, "8m", 2),
                ("Fatima Khan", "My refund has not reached my account yet.", "FK", "/conversations", 0, "14m", 3),
                ("Vikram Shah", "Please move my appointment to Saturday.", "VS", "/conversations", 0, "31m", 4),
                ("Meera Iyer", "Could someone help connect our WhatsApp number?", "MI", "/conversations", 1, "1h", 5),
            ],
        )
    connection.commit()


def insert_rows(connection, table, rows):
    for sort_order, row in enumerate(rows, start=1):
        payload = dict(row)
        payload.setdefault("sort_order", sort_order)
        columns = ", ".join(payload.keys())
        placeholders = ", ".join([f":{column}" for column in payload])
        connection.execute(f"INSERT INTO {table} ({columns}) VALUES ({placeholders})", payload)


def seed_page(connection, tenant_id, slug, title, subtitle, summary=None):
    cursor = connection.execute(
        "INSERT INTO pages (tenant_id, slug, title, subtitle) VALUES (?, ?, ?, ?)",
        (tenant_id, slug, title, subtitle),
    )
    page_id = cursor.lastrowid
    if summary:
        insert_rows(
            connection,
            "summary_metrics",
            [dict(item, page_id=page_id) for item in summary],
        )
    return page_id


def seed_database(connection):
    cursor = connection.execute(
        """
        INSERT INTO tenants (name, industry, timezone, language)
        VALUES (?, ?, ?, ?)
        """,
        ("EverTech Solutions", "Education and ecommerce", "Asia/Kolkata", "English"),
    )
    tenant_id = cursor.lastrowid

    pages = {
        "dashboard": seed_page(
            connection,
            tenant_id,
            "dashboard",
            "Customer Dashboard",
            "WhatsApp AI operations, service quality, and business outcomes.",
        ),
        "conversations": seed_page(
            connection,
            tenant_id,
            "conversations",
            "Conversations",
            "Monitor live WhatsApp threads, handoffs, sentiment, SLA, and customer intent.",
            [
                {"label": "Open Threads", "value": "184", "icon": "fa-solid fa-inbox", "tone": "primary"},
                {"label": "Waiting on Customer", "value": "63", "icon": "fa-solid fa-clock", "tone": "warning"},
                {"label": "Escalated", "value": "28", "icon": "fa-solid fa-headset", "tone": "danger"},
                {"label": "AI Resolved Today", "value": "1,094", "icon": "fa-solid fa-circle-check", "tone": "success"},
            ],
        ),
        "analytics": seed_page(
            connection,
            tenant_id,
            "analytics",
            "Analytics",
            "Understand WhatsApp automation performance, business outcomes, and customer experience trends.",
            [
                {"label": "Conversations", "value": "18.4k", "change": "+12.8%", "tone": "good"},
                {"label": "Automation Rate", "value": "87.6%", "change": "+5.6%", "tone": "good"},
                {"label": "CSAT", "value": "94.2%", "change": "+3.1%", "tone": "good"},
                {"label": "Escalation Rate", "value": "6.1%", "change": "-1.4%", "tone": "good"},
            ],
        ),
        "settings": seed_page(connection, tenant_id, "settings", "Settings", "Manage workspace, WhatsApp, AI, handoff, modules, security, and notifications."),
        "security": seed_page(
            connection,
            tenant_id,
            "security",
            "Security",
            "Control workspace access, customer data protection, audit logs, and compliance posture.",
            [
                {"label": "Security Score", "value": "94%", "icon": "fa-solid fa-shield-halved", "tone": "success"},
                {"label": "Admins with 2FA", "value": "12/12", "icon": "fa-solid fa-lock", "tone": "success"},
                {"label": "Open Risks", "value": "3", "icon": "fa-solid fa-triangle-exclamation", "tone": "warning"},
                {"label": "Audit Events", "value": "1,284", "icon": "fa-solid fa-file-shield", "tone": "primary"},
            ],
        ),
        "support": seed_page(
            connection,
            tenant_id,
            "support",
            "Support",
            "Manage support tickets, platform status, onboarding requests, and help resources.",
            [
                {"label": "Open Tickets", "value": "14", "icon": "fa-solid fa-ticket", "tone": "primary"},
                {"label": "Avg First Response", "value": "18m", "icon": "fa-solid fa-stopwatch", "tone": "success"},
                {"label": "SLA At Risk", "value": "2", "icon": "fa-solid fa-clock", "tone": "warning"},
                {"label": "Platform Status", "value": "Healthy", "icon": "fa-solid fa-heart-pulse", "tone": "success"},
            ],
        ),
        "customers": seed_page(
            connection,
            tenant_id,
            "customers",
            "Customers",
            "Manage WhatsApp contacts, customer segments, lifecycle stage, and account health.",
            [
                {"label": "Total Customers", "value": "12,840", "icon": "fa-solid fa-users", "tone": "primary"},
                {"label": "New This Week", "value": "684", "icon": "fa-solid fa-user-plus", "tone": "success"},
                {"label": "High Intent", "value": "1,248", "icon": "fa-solid fa-fire", "tone": "warning"},
                {"label": "At Risk", "value": "96", "icon": "fa-solid fa-triangle-exclamation", "tone": "danger"},
            ],
        ),
        "team_members": seed_page(
            connection,
            tenant_id,
            "team-members",
            "Team Members",
            "Manage agents, roles, availability, queue ownership, and handoff performance.",
            [
                {"label": "Team Members", "value": "76", "icon": "fa-solid fa-user-group", "tone": "primary"},
                {"label": "Online Now", "value": "42", "icon": "fa-solid fa-circle", "tone": "success"},
                {"label": "Open Assignments", "value": "184", "icon": "fa-solid fa-list-check", "tone": "warning"},
                {"label": "Avg SLA", "value": "8m", "icon": "fa-solid fa-stopwatch", "tone": "success"},
            ],
        ),
        "billing": seed_page(
            connection,
            tenant_id,
            "billing",
            "Billing",
            "Manage subscription, usage, invoices, payment method, and billing contacts.",
            [
                {"label": "Current Plan", "value": "Growth", "icon": "fa-solid fa-layer-group", "tone": "primary"},
                {"label": "Monthly Spend", "value": "Rs 84,200", "icon": "fa-solid fa-wallet", "tone": "success"},
                {"label": "AI Messages Used", "value": "72%", "icon": "fa-solid fa-comments", "tone": "warning"},
                {"label": "Next Renewal", "value": "Aug 1", "icon": "fa-solid fa-calendar-days", "tone": "primary"},
            ],
        ),
        "add_ons": seed_page(
            connection,
            tenant_id,
            "add-ons",
            "Add-on Modules",
            "Purchase industry add-ons for your WhatsApp AI subscription and activate specialized business workflows.",
            [
                {"label": "Available Add-ons", "value": "12", "icon": "fa-solid fa-puzzle-piece", "tone": "primary"},
                {"label": "Installed", "value": "4", "icon": "fa-solid fa-circle-check", "tone": "success"},
                {"label": "Recommended", "value": "3", "icon": "fa-solid fa-star", "tone": "warning"},
                {"label": "Add-on Spend", "value": "Rs 28,000", "icon": "fa-solid fa-wallet", "tone": "primary"},
            ],
        ),
        "ai_assistant": seed_page(
            connection,
            tenant_id,
            "ai-assistant",
            "AI Assistant",
            "Configure model behavior, prompt versions, guardrails, and live assistant performance.",
            [
                {"label": "Primary Model", "value": "GPT-4.1 Mini", "icon": "fa-solid fa-brain", "tone": "primary"},
                {"label": "Automation Rate", "value": "87.6%", "icon": "fa-solid fa-bolt", "tone": "success"},
                {"label": "Fallback Rate", "value": "5.9%", "icon": "fa-solid fa-triangle-exclamation", "tone": "warning"},
                {"label": "Prompt Version", "value": "v3.4", "icon": "fa-solid fa-code-branch", "tone": "primary"},
            ],
        ),
        "knowledge_base": seed_page(
            connection,
            tenant_id,
            "knowledge-base",
            "Knowledge Base",
            "Manage approved documents, sync status, content coverage, and AI answer grounding.",
            [
                {"label": "Documents", "value": "148", "icon": "fa-solid fa-file-lines", "tone": "primary"},
                {"label": "Synced Sources", "value": "12/13", "icon": "fa-solid fa-arrows-rotate", "tone": "warning"},
                {"label": "Coverage", "value": "92%", "icon": "fa-solid fa-chart-pie", "tone": "success"},
                {"label": "Last Sync", "value": "22m ago", "icon": "fa-solid fa-clock", "tone": "primary"},
            ],
        ),
        "prompt_builder": seed_page(
            connection,
            tenant_id,
            "prompt-builder",
            "Prompt Builder",
            "Design, test, version, and deploy prompts for WhatsApp AI modules.",
            [
                {"label": "Live Prompts", "value": "8", "icon": "fa-solid fa-wand-magic-sparkles", "tone": "primary"},
                {"label": "Drafts", "value": "5", "icon": "fa-solid fa-pen-to-square", "tone": "warning"},
                {"label": "Pass Rate", "value": "94%", "icon": "fa-solid fa-circle-check", "tone": "success"},
                {"label": "Latest Version", "value": "v3.4", "icon": "fa-solid fa-code-branch", "tone": "primary"},
            ],
        ),
        "workflows": seed_page(
            connection,
            tenant_id,
            "workflows",
            "Workflows",
            "Create routing automations for WhatsApp intents, handoffs, modules, and follow-ups.",
            [
                {"label": "Active Workflows", "value": "14", "icon": "fa-solid fa-code-branch", "tone": "primary"},
                {"label": "Runs Today", "value": "6,842", "icon": "fa-solid fa-play", "tone": "success"},
                {"label": "Failed Runs", "value": "18", "icon": "fa-solid fa-triangle-exclamation", "tone": "warning"},
                {"label": "Avg Runtime", "value": "1.4s", "icon": "fa-solid fa-stopwatch", "tone": "success"},
            ],
        ),
    }

    insert_rows(connection, "dashboard_stats", [
        {"page_id": pages["dashboard"], "title": "Total Conversations", "value": "18,420", "change": "+12.8%", "trend": "up", "icon": "fa-solid fa-comments"},
        {"page_id": pages["dashboard"], "title": "Escalations", "value": "312", "change": "-7.4%", "trend": "down", "icon": "fa-solid fa-headset"},
        {"page_id": pages["dashboard"], "title": "Customer Satisfaction", "value": "94.2%", "change": "+3.1%", "trend": "up", "icon": "fa-solid fa-face-smile"},
        {"page_id": pages["dashboard"], "title": "Automation Rate", "value": "87.6%", "change": "+5.6%", "trend": "up", "icon": "fa-solid fa-bolt"},
    ])
    insert_rows(connection, "dashboard_conversations", [
        {"tenant_id": tenant_id, "customer_name": "Priya Nair", "avatar": None, "time": "2m ago", "last_message": "Asked for delivery ETA on order #PP-2918.", "handler": "AI", "status": "Active", "unread": 2},
        {"tenant_id": tenant_id, "customer_name": "Arjun Mehta", "avatar": None, "time": "8m ago", "last_message": "Requested course fee details and scholarship options.", "handler": "AI", "status": "Waiting", "unread": 1},
        {"tenant_id": tenant_id, "customer_name": "Maya Kapoor", "avatar": None, "time": "18m ago", "last_message": "Booking moved to Saturday at 4:30 PM.", "handler": "Human", "status": "Resolved", "unread": 0},
        {"tenant_id": tenant_id, "customer_name": "Rahul Shah", "avatar": None, "time": "31m ago", "last_message": "Lead qualified for enterprise pricing follow-up.", "handler": "AI", "status": "Active", "unread": 4},
    ])
    insert_rows(connection, "dashboard_activities", [
        {"tenant_id": tenant_id, "title": "Escalation assigned", "description": "High-intent lead routed to Sales Team A.", "activity_type": "Escalation", "icon": "fa-solid fa-arrow-up-right-dots", "time": "5m ago", "user": "Anita", "status": "Open"},
        {"tenant_id": tenant_id, "title": "Knowledge base synced", "description": "18 product policy pages refreshed successfully.", "activity_type": "Sync", "icon": "fa-solid fa-arrows-rotate", "time": "22m ago", "user": "System", "status": "Done"},
        {"tenant_id": tenant_id, "title": "Prompt version deployed", "description": "Admissions flow updated to version 3.4.", "activity_type": "AI", "icon": "fa-solid fa-robot", "time": "1h ago", "user": "Rohan", "status": "Live"},
    ])
    insert_rows(connection, "performance_metrics", [
        {"page_id": pages["dashboard"], "title": "First Response Time", "subtitle": "Median across WhatsApp threads", "icon": "fa-solid fa-stopwatch", "value": "4.8", "unit": "sec", "progress": 92, "status": "excellent", "change": "1.7 sec faster"},
        {"page_id": pages["dashboard"], "title": "Resolution Rate", "subtitle": "Solved without human handoff", "icon": "fa-solid fa-circle-check", "value": "82.4", "unit": "%", "progress": 82, "status": "good", "change": "+4.2 this week"},
        {"page_id": pages["dashboard"], "title": "Fallback Rate", "subtitle": "Messages needing clarification", "icon": "fa-solid fa-triangle-exclamation", "value": "5.9", "unit": "%", "progress": 34, "status": "warning", "change": "Review top intents"},
    ])
    insert_rows(connection, "business_modules", [
        {"tenant_id": tenant_id, "name": "Sales", "value": "1,248", "label": "qualified leads", "progress": 78, "icon": "fa-solid fa-chart-line"},
        {"tenant_id": tenant_id, "name": "Admissions", "value": "426", "label": "applications started", "progress": 64, "icon": "fa-solid fa-graduation-cap"},
        {"tenant_id": tenant_id, "name": "Appointments", "value": "689", "label": "bookings created", "progress": 71, "icon": "fa-solid fa-calendar-check"},
        {"tenant_id": tenant_id, "name": "Orders", "value": "2,914", "label": "order queries handled", "progress": 86, "icon": "fa-solid fa-box"},
    ])
    insert_rows(connection, "escalations", [
        {"tenant_id": tenant_id, "team": "Sales Team A", "count": 44, "sla": "12m", "tone": "warning"},
        {"tenant_id": tenant_id, "team": "Support Desk", "count": 29, "sla": "8m", "tone": "good"},
        {"tenant_id": tenant_id, "team": "Admissions", "count": 18, "sla": "15m", "tone": "warning"},
        {"tenant_id": tenant_id, "team": "Billing", "count": 7, "sla": "5m", "tone": "good"},
    ])

    insert_rows(connection, "conversation_threads", [
        {"tenant_id": tenant_id, "customer_name": "Priya Nair", "phone": "+91 98201 11842", "intent": "Order status", "module": "Orders", "handler": "AI", "status": "Active", "priority": "Normal", "sentiment": "Positive", "time": "2m ago", "last_message": "Can you confirm when my replacement order will arrive?", "messages": 14, "sla": "4m"},
        {"tenant_id": tenant_id, "customer_name": "Arjun Mehta", "phone": "+91 99870 44218", "intent": "Admission enquiry", "module": "Admissions", "handler": "AI", "status": "Waiting", "priority": "High", "sentiment": "Neutral", "time": "8m ago", "last_message": "Please send the MBA fee structure and scholarship criteria.", "messages": 9, "sla": "7m"},
        {"tenant_id": tenant_id, "customer_name": "Maya Kapoor", "phone": "+91 90044 78218", "intent": "Appointment booking", "module": "Appointments", "handler": "Human", "status": "Resolved", "priority": "Normal", "sentiment": "Positive", "time": "18m ago", "last_message": "Saturday 4:30 PM works. Please confirm the location.", "messages": 18, "sla": "Resolved"},
        {"tenant_id": tenant_id, "customer_name": "Rahul Shah", "phone": "+91 98199 72101", "intent": "Enterprise pricing", "module": "Sales", "handler": "AI", "status": "Active", "priority": "High", "sentiment": "Positive", "time": "31m ago", "last_message": "We have 45 agents. Can someone discuss annual pricing?", "messages": 22, "sla": "3m"},
        {"tenant_id": tenant_id, "customer_name": "Fatima Khan", "phone": "+91 98710 50019", "intent": "Refund request", "module": "Support", "handler": "Human", "status": "Escalated", "priority": "Urgent", "sentiment": "Negative", "time": "46m ago", "last_message": "I have waited a week and still have not received the refund.", "messages": 27, "sla": "2m"},
        {"tenant_id": tenant_id, "customer_name": "Karan Gill", "phone": "+91 98672 19004", "intent": "Product availability", "module": "Sales", "handler": "AI", "status": "Resolved", "priority": "Normal", "sentiment": "Neutral", "time": "1h ago", "last_message": "Thanks, I will place the order later today.", "messages": 11, "sla": "Resolved"},
    ])
    insert_rows(connection, "quick_filters", [{"page_id": pages["conversations"], "label": label} for label in ["All", "Active", "Waiting", "Escalated", "Resolved"]])

    insert_rows(connection, "analytics_funnels", [
        {"tenant_id": tenant_id, "name": "New WhatsApp contacts", "value": "8,420", "progress": 100},
        {"tenant_id": tenant_id, "name": "Intent identified", "value": "7,981", "progress": 95},
        {"tenant_id": tenant_id, "name": "Qualified outcome", "value": "5,226", "progress": 62},
        {"tenant_id": tenant_id, "name": "Human handoff", "value": "512", "progress": 6},
    ])
    insert_rows(connection, "analytics_intents", [
        {"tenant_id": tenant_id, "name": "Order status", "count": "4,291", "share": 32},
        {"tenant_id": tenant_id, "name": "Admissions enquiry", "count": "2,804", "share": 21},
        {"tenant_id": tenant_id, "name": "Appointments", "count": "2,103", "share": 16},
        {"tenant_id": tenant_id, "name": "Sales pricing", "count": "1,940", "share": 14},
        {"tenant_id": tenant_id, "name": "Refunds", "count": "1,024", "share": 8},
    ])
    insert_rows(connection, "team_performance", [
        {"tenant_id": tenant_id, "name": "Sales Team A", "resolved": 342, "avg_sla": "9m", "csat": "95%"},
        {"tenant_id": tenant_id, "name": "Support Desk", "resolved": 516, "avg_sla": "7m", "csat": "92%"},
        {"tenant_id": tenant_id, "name": "Admissions", "resolved": 228, "avg_sla": "12m", "csat": "94%"},
        {"tenant_id": tenant_id, "name": "Billing", "resolved": 74, "avg_sla": "6m", "csat": "90%"},
    ])

    seed_shared_domain_rows(connection, tenant_id)
    seed_addons(connection, tenant_id)
    connection.commit()


def seed_shared_domain_rows(connection, tenant_id):
    insert_rows(connection, "security_access_rules", [
        {"tenant_id": tenant_id, "name": "Require two-factor authentication", "detail": "All admins and team leads must use 2FA.", "enabled": 1},
        {"tenant_id": tenant_id, "name": "Mask customer phone numbers", "detail": "Non-admin users see only the last 4 digits.", "enabled": 1},
        {"tenant_id": tenant_id, "name": "Restrict exports to admins", "detail": "Conversation and analytics exports require admin role.", "enabled": 1},
        {"tenant_id": tenant_id, "name": "Block unknown login locations", "detail": "New country sign-ins require email approval.", "enabled": 0},
    ])
    insert_rows(connection, "security_roles", [
        {"tenant_id": tenant_id, "role": "Owner", "users": 2, "permissions": "Full access"},
        {"tenant_id": tenant_id, "role": "Admin", "users": 10, "permissions": "Settings, billing, exports"},
        {"tenant_id": tenant_id, "role": "Team Lead", "users": 18, "permissions": "Queues, assignments, reports"},
        {"tenant_id": tenant_id, "role": "Agent", "users": 46, "permissions": "Assigned conversations"},
    ])
    insert_rows(connection, "audit_logs", [
        {"tenant_id": tenant_id, "event": "Prompt version deployed", "user": "Rohan", "ip": "103.82.22.18", "time": "12m ago", "status": "Allowed"},
        {"tenant_id": tenant_id, "event": "CSV export requested", "user": "Anita", "ip": "49.36.104.92", "time": "44m ago", "status": "Allowed"},
        {"tenant_id": tenant_id, "event": "Unknown device login", "user": "Meera", "ip": "157.45.20.11", "time": "2h ago", "status": "Challenged"},
        {"tenant_id": tenant_id, "event": "Billing settings viewed", "user": "Admin", "ip": "122.161.18.91", "time": "4h ago", "status": "Allowed"},
    ])
    insert_rows(connection, "compliance_items", [
        {"tenant_id": tenant_id, "name": "Data retention", "value": "180 days", "progress": 90},
        {"tenant_id": tenant_id, "name": "PII redaction", "value": "Enabled", "progress": 100},
        {"tenant_id": tenant_id, "name": "Audit coverage", "value": "98%", "progress": 98},
    ])
    insert_rows(connection, "support_tickets", [
        {"tenant_id": tenant_id, "ticket_id": "PP-1042", "subject": "WhatsApp template rejected", "priority": "High", "owner": "Support Desk", "status": "Open", "updated": "11m ago"},
        {"tenant_id": tenant_id, "ticket_id": "PP-1038", "subject": "Admissions workflow edit request", "priority": "Normal", "owner": "Onboarding", "status": "In Progress", "updated": "38m ago"},
        {"tenant_id": tenant_id, "ticket_id": "PP-1031", "subject": "Need billing invoice for June", "priority": "Low", "owner": "Finance", "status": "Waiting", "updated": "2h ago"},
        {"tenant_id": tenant_id, "ticket_id": "PP-1024", "subject": "Add new support team member", "priority": "Normal", "owner": "Support Desk", "status": "Resolved", "updated": "1d ago"},
    ])
    insert_rows(connection, "status_checks", [
        {"tenant_id": tenant_id, "name": "WhatsApp API", "status": "Operational", "detail": "99.99% uptime"},
        {"tenant_id": tenant_id, "name": "AI Runtime", "status": "Operational", "detail": "1.2s median latency"},
        {"tenant_id": tenant_id, "name": "Webhook Delivery", "status": "Operational", "detail": "No failed retries"},
        {"tenant_id": tenant_id, "name": "Dashboard App", "status": "Operational", "detail": "All regions healthy"},
    ])
    insert_rows(connection, "support_resources", [
        {"tenant_id": tenant_id, "title": "WhatsApp onboarding guide", "detail": "Connect phone numbers, templates, and webhooks.", "icon": "fa-brands fa-whatsapp"},
        {"tenant_id": tenant_id, "title": "AI assistant tuning", "detail": "Improve prompts, confidence thresholds, and fallback rules.", "icon": "fa-solid fa-robot"},
        {"tenant_id": tenant_id, "title": "Escalation playbook", "detail": "Set team ownership, SLA alerts, and handoff rules.", "icon": "fa-solid fa-headset"},
    ])
    insert_rows(connection, "customer_segments", [
        {"tenant_id": tenant_id, "name": "Qualified leads", "value": "3,420", "progress": 78},
        {"tenant_id": tenant_id, "name": "Active buyers", "value": "2,814", "progress": 64},
        {"tenant_id": tenant_id, "name": "Admission prospects", "value": "1,906", "progress": 52},
        {"tenant_id": tenant_id, "name": "Support follow-ups", "value": "842", "progress": 24},
    ])
    insert_rows(connection, "customers", [
        {"tenant_id": tenant_id, "name": "Priya Nair", "phone": "+91 98201 11842", "segment": "Active buyer", "stage": "Order follow-up", "last_seen": "2m ago", "csat": "98%", "health": "Good"},
        {"tenant_id": tenant_id, "name": "Arjun Mehta", "phone": "+91 99870 44218", "segment": "Admission prospect", "stage": "Fee enquiry", "last_seen": "8m ago", "csat": "92%", "health": "Good"},
        {"tenant_id": tenant_id, "name": "Rahul Shah", "phone": "+91 98199 72101", "segment": "Enterprise lead", "stage": "Pricing", "last_seen": "31m ago", "csat": "96%", "health": "High intent"},
        {"tenant_id": tenant_id, "name": "Fatima Khan", "phone": "+91 98710 50019", "segment": "Support follow-up", "stage": "Refund", "last_seen": "46m ago", "csat": "61%", "health": "At risk"},
        {"tenant_id": tenant_id, "name": "Karan Gill", "phone": "+91 98672 19004", "segment": "Sales prospect", "stage": "Availability", "last_seen": "1h ago", "csat": "88%", "health": "Neutral"},
    ])
    insert_rows(connection, "customer_timeline", [
        {"tenant_id": tenant_id, "title": "Refund escalation opened", "customer": "Fatima Khan", "time": "46m ago", "status": "Open"},
        {"tenant_id": tenant_id, "title": "Enterprise lead qualified", "customer": "Rahul Shah", "time": "31m ago", "status": "Hot"},
        {"tenant_id": tenant_id, "title": "Appointment confirmed", "customer": "Maya Kapoor", "time": "18m ago", "status": "Done"},
    ])
    insert_rows(connection, "teams", [
        {"tenant_id": tenant_id, "name": "Support Desk", "members": 24, "queue": 68, "sla": "7m", "progress": 84},
        {"tenant_id": tenant_id, "name": "Sales Team A", "members": 18, "queue": 44, "sla": "9m", "progress": 76},
        {"tenant_id": tenant_id, "name": "Admissions", "members": 16, "queue": 38, "sla": "12m", "progress": 68},
        {"tenant_id": tenant_id, "name": "Finance", "members": 8, "queue": 12, "sla": "6m", "progress": 91},
    ])
    insert_rows(connection, "team_members", [
        {"tenant_id": tenant_id, "name": "Anita Rao", "role": "Support Lead", "team": "Support Desk", "status": "Online", "assigned": 18, "resolved": 124, "csat": "94%"},
        {"tenant_id": tenant_id, "name": "Rohan Iyer", "role": "AI Ops Admin", "team": "AI Management", "status": "Online", "assigned": 6, "resolved": 48, "csat": "97%"},
        {"tenant_id": tenant_id, "name": "Meera Das", "role": "Admissions Agent", "team": "Admissions", "status": "Busy", "assigned": 22, "resolved": 86, "csat": "92%"},
        {"tenant_id": tenant_id, "name": "Vikram Singh", "role": "Sales Agent", "team": "Sales Team A", "status": "Away", "assigned": 14, "resolved": 71, "csat": "95%"},
        {"tenant_id": tenant_id, "name": "Nisha Patel", "role": "Billing Specialist", "team": "Finance", "status": "Offline", "assigned": 4, "resolved": 39, "csat": "90%"},
    ])
    insert_rows(connection, "team_roles", [
        {"tenant_id": tenant_id, "role_key": "owner", "name": "Owner", "count": 2, "scope": "Full workspace control"},
        {"tenant_id": tenant_id, "role_key": "admin", "name": "Admin", "count": 10, "scope": "Settings, analytics, team management"},
        {"tenant_id": tenant_id, "role_key": "manager", "name": "Team Lead", "count": 18, "scope": "Queues, assignments, escalations"},
        {"tenant_id": tenant_id, "role_key": "agent", "name": "Agent", "count": 46, "scope": "Assigned conversations and notes"},
    ])
    seed_billing_ai_knowledge_prompt_workflow_settings(connection, tenant_id)


def seed_billing_ai_knowledge_prompt_workflow_settings(connection, tenant_id):
    insert_rows(connection, "billing_usage", [
        {"tenant_id": tenant_id, "name": "WhatsApp conversations", "value": "18,420 / 25,000", "progress": 74},
        {"tenant_id": tenant_id, "name": "AI messages", "value": "146,800 / 200,000", "progress": 72},
        {"tenant_id": tenant_id, "name": "Knowledge base syncs", "value": "82 / 100", "progress": 82},
        {"tenant_id": tenant_id, "name": "Team seats", "value": "76 / 100", "progress": 76},
    ])
    insert_rows(connection, "invoices", [
        {"tenant_id": tenant_id, "invoice_id": "INV-2026-071", "date": "Jul 1, 2026", "amount": "Rs 84,200", "status": "Paid"},
        {"tenant_id": tenant_id, "invoice_id": "INV-2026-062", "date": "Jun 1, 2026", "amount": "Rs 79,600", "status": "Paid"},
        {"tenant_id": tenant_id, "invoice_id": "INV-2026-053", "date": "May 1, 2026", "amount": "Rs 76,400", "status": "Paid"},
        {"tenant_id": tenant_id, "invoice_id": "INV-2026-044", "date": "Apr 1, 2026", "amount": "Rs 72,900", "status": "Paid"},
    ])
    insert_rows(connection, "billing_addons", [
        {"tenant_id": tenant_id, "name": "Extra AI messages", "detail": "50,000 messages", "price": "Rs 12,000/mo", "enabled": 1},
        {"tenant_id": tenant_id, "name": "Advanced analytics", "detail": "Custom exports and cohorts", "price": "Rs 8,000/mo", "enabled": 1},
        {"tenant_id": tenant_id, "name": "Priority support", "detail": "2 hour response SLA", "price": "Rs 15,000/mo", "enabled": 0},
    ])
    insert_rows(connection, "billing_contacts", [
        {"tenant_id": tenant_id, "name": "Admin User", "email": "admin@evertech.example", "role": "Billing owner"},
        {"tenant_id": tenant_id, "name": "Finance Desk", "email": "finance@evertech.example", "role": "Invoice recipient"},
    ])
    insert_rows(connection, "ai_assistants", [
        {"tenant_id": tenant_id, "name": "Support Assistant", "model": "GPT-4.1 Mini", "module": "Support", "status": "Live", "confidence": 94},
        {"tenant_id": tenant_id, "name": "Lead Qualifier", "model": "GPT-4.1 Mini", "module": "Sales", "status": "Live", "confidence": 91},
        {"tenant_id": tenant_id, "name": "Admissions Advisor", "model": "GPT-4.1 Mini", "module": "Admissions", "status": "Testing", "confidence": 88},
        {"tenant_id": tenant_id, "name": "Fallback Classifier", "model": "GPT-4.1 Nano", "module": "Routing", "status": "Live", "confidence": 96},
    ])
    insert_rows(connection, "ai_guardrails", [
        {"tenant_id": tenant_id, "name": "Require knowledge base citations", "detail": "Prefer approved source snippets for factual answers.", "enabled": 1},
        {"tenant_id": tenant_id, "name": "Escalate low confidence answers", "detail": "Route to human when confidence drops below threshold.", "enabled": 1},
        {"tenant_id": tenant_id, "name": "Block payment-card collection", "detail": "Prevent the assistant from asking for card details in chat.", "enabled": 1},
        {"tenant_id": tenant_id, "name": "Allow promotional recommendations", "detail": "Permit cross-sell suggestions in qualified sales flows.", "enabled": 0},
    ])
    insert_rows(connection, "ai_test_cases", [
        {"tenant_id": tenant_id, "prompt": "Where is my order PP-2918?", "intent": "Order status", "result": "Passed"},
        {"tenant_id": tenant_id, "prompt": "What is the MBA admission deadline?", "intent": "Admissions", "result": "Passed"},
        {"tenant_id": tenant_id, "prompt": "I want a refund now.", "intent": "Refund escalation", "result": "Review"},
    ])
    insert_rows(connection, "kb_sources", [
        {"tenant_id": tenant_id, "name": "Product policy docs", "type": "Google Drive", "documents": 42, "status": "Synced", "updated": "22m ago"},
        {"tenant_id": tenant_id, "name": "Admissions handbook", "type": "PDF Library", "documents": 18, "status": "Synced", "updated": "1h ago"},
        {"tenant_id": tenant_id, "name": "Order and refund SOP", "type": "Notion", "documents": 27, "status": "Needs review", "updated": "3h ago"},
        {"tenant_id": tenant_id, "name": "Pricing sheets", "type": "Spreadsheet", "documents": 9, "status": "Synced", "updated": "5h ago"},
    ])
    insert_rows(connection, "kb_coverage", [
        {"tenant_id": tenant_id, "name": "Orders", "value": "96%", "progress": 96},
        {"tenant_id": tenant_id, "name": "Admissions", "value": "91%", "progress": 91},
        {"tenant_id": tenant_id, "name": "Appointments", "value": "88%", "progress": 88},
        {"tenant_id": tenant_id, "name": "Billing", "value": "74%", "progress": 74},
    ])
    insert_rows(connection, "kb_gaps", [
        {"tenant_id": tenant_id, "topic": "Refund exceptions", "impact": "High", "owner": "Support Desk", "status": "Needs source"},
        {"tenant_id": tenant_id, "topic": "Scholarship eligibility", "impact": "Medium", "owner": "Admissions", "status": "Drafting"},
        {"tenant_id": tenant_id, "topic": "Enterprise pricing tiers", "impact": "Medium", "owner": "Sales Team A", "status": "Review"},
    ])
    insert_rows(connection, "kb_entries", [
        {
            "tenant_id": tenant_id,
            "title": "Appointment rescheduling policy",
            "category": "Appointments",
            "content": "Customers can reschedule appointments up to 4 hours before the booking time. Ask for the booking ID or registered phone number, then offer the next available slots.",
            "tags": "appointments,reschedule,booking",
            "status": "Published",
        },
        {
            "tenant_id": tenant_id,
            "title": "Refund escalation rule",
            "category": "Support",
            "content": "Refund requests older than 5 business days or messages with negative sentiment should be escalated to the Support Desk with the order ID and customer phone number.",
            "tags": "refund,escalation,support",
            "status": "Published",
        },
        {
            "tenant_id": tenant_id,
            "title": "Admissions fee enquiry",
            "category": "Admissions",
            "content": "For admissions fee questions, collect the course name, intake year, and preferred campus before routing the lead to the Admissions Desk.",
            "tags": "admissions,fees,course",
            "status": "Published",
        },
    ])
    insert_rows(connection, "prompts", [
        {"tenant_id": tenant_id, "name": "Support resolution prompt", "module": "Support", "version": "v3.4", "status": "Live", "pass_rate": 96},
        {"tenant_id": tenant_id, "name": "Sales qualification prompt", "module": "Sales", "version": "v2.8", "status": "Live", "pass_rate": 91},
        {"tenant_id": tenant_id, "name": "Admissions advisor prompt", "module": "Admissions", "version": "v1.9", "status": "Draft", "pass_rate": 88},
        {"tenant_id": tenant_id, "name": "Refund escalation prompt", "module": "Support", "version": "v2.1", "status": "Review", "pass_rate": 83},
    ])
    insert_rows(connection, "prompt_variables", [
        {"tenant_id": tenant_id, "name": "customer_name", "source": "WhatsApp profile", "required": 1},
        {"tenant_id": tenant_id, "name": "last_order_id", "source": "Orders module", "required": 0},
        {"tenant_id": tenant_id, "name": "business_hours", "source": "Workspace settings", "required": 1},
        {"tenant_id": tenant_id, "name": "handoff_team", "source": "Routing workflow", "required": 1},
    ])
    insert_rows(connection, "prompt_tests", [
        {"tenant_id": tenant_id, "test_case": "Delayed order with positive tone", "intent": "Order status", "result": "Passed"},
        {"tenant_id": tenant_id, "test_case": "Refund request with frustration", "intent": "Escalation", "result": "Review"},
        {"tenant_id": tenant_id, "test_case": "Admission scholarship question", "intent": "Admissions", "result": "Passed"},
    ])
    insert_rows(connection, "workflows", [
        {"tenant_id": tenant_id, "name": "Sales lead qualification", "trigger": "Pricing intent", "owner": "Sales Team A", "status": "Live", "runs": "1,248", "success": 96},
        {"tenant_id": tenant_id, "name": "Admissions enquiry routing", "trigger": "Course enquiry", "owner": "Admissions", "status": "Live", "runs": "426", "success": 93},
        {"tenant_id": tenant_id, "name": "Refund escalation", "trigger": "Negative sentiment", "owner": "Support Desk", "status": "Live", "runs": "312", "success": 89},
        {"tenant_id": tenant_id, "name": "Appointment reminder", "trigger": "Booking confirmed", "owner": "Front Office", "status": "Draft", "runs": "0", "success": 0},
    ])
    insert_rows(connection, "workflow_steps", [
        {"tenant_id": tenant_id, "name": "Detect intent", "detail": "Classify WhatsApp message and confidence"},
        {"tenant_id": tenant_id, "name": "Check knowledge base", "detail": "Find approved answer or matching policy"},
        {"tenant_id": tenant_id, "name": "Run module action", "detail": "Create lead, booking, order lookup, or ticket"},
        {"tenant_id": tenant_id, "name": "Escalate or resolve", "detail": "Route to human if confidence or sentiment requires"},
    ])
    insert_rows(connection, "workflow_rules", [
        {"tenant_id": tenant_id, "name": "Escalate angry refund messages", "detail": "Negative sentiment + refund intent routes to Support Desk.", "enabled": 1},
        {"tenant_id": tenant_id, "name": "Assign enterprise leads", "detail": "Company size above 25 routes to Sales Team A.", "enabled": 1},
        {"tenant_id": tenant_id, "name": "Send appointment reminders", "detail": "Send reminder 4 hours before booking.", "enabled": 0},
        {"tenant_id": tenant_id, "name": "Create admissions follow-up", "detail": "Follow up if prospect has not replied in 24 hours.", "enabled": 1},
    ])
    insert_rows(connection, "settings_channels", [
        {"tenant_id": tenant_id, "name": "WhatsApp Business API", "status": "Connected", "detail": "+91 98765 43210", "tone": "good"},
        {"tenant_id": tenant_id, "name": "Webhook Delivery", "status": "Healthy", "detail": "99.98% success", "tone": "good"},
        {"tenant_id": tenant_id, "name": "Template Messages", "status": "Review needed", "detail": "3 pending approvals", "tone": "warning"},
    ])
    insert_rows(connection, "settings_models", [
        {"tenant_id": tenant_id, "name": "Support Assistant", "model": "GPT-4.1 Mini", "temperature": "0.3", "status": "Live"},
        {"tenant_id": tenant_id, "name": "Lead Qualifier", "model": "GPT-4.1 Mini", "temperature": "0.4", "status": "Live"},
        {"tenant_id": tenant_id, "name": "Fallback Classifier", "model": "GPT-4.1 Nano", "temperature": "0.1", "status": "Testing"},
    ])
    insert_rows(connection, "settings_modules", [
        {"tenant_id": tenant_id, "name": "Sales", "enabled": 1, "owner": "Sales Team A"},
        {"tenant_id": tenant_id, "name": "Admissions", "enabled": 1, "owner": "Admissions Desk"},
        {"tenant_id": tenant_id, "name": "Appointments", "enabled": 1, "owner": "Front Office"},
        {"tenant_id": tenant_id, "name": "Orders", "enabled": 1, "owner": "Support Desk"},
        {"tenant_id": tenant_id, "name": "Billing", "enabled": 0, "owner": "Finance"},
    ])


def seed_addons(connection, tenant_id):
    addon_rows = [
        {"name": "GPS Fleet Tracking", "category": "Transport", "price": "Rs 18,000/mo", "status": "Recommended", "icon": "fa-solid fa-location-dot", "description": "Track school buses, rental vehicles, and delivery fleets directly from WhatsApp support flows.", "fit": "School buses, rental vehicles, logistics", "is_featured": 1, "features": ["Live vehicle location", "Trip ETA replies", "Route delay alerts", "Parent or customer tracking links"]},
        {"name": "Admissions CRM", "category": "Education", "price": "Rs 12,000/mo", "status": "Popular", "icon": "fa-solid fa-graduation-cap", "description": "Qualify student enquiries, collect documents, and route applications to admissions teams.", "fit": "Schools, colleges, coaching institutes", "is_featured": 1, "features": ["Lead scoring", "Course matching", "Document reminders", "Counsellor assignment"]},
        {"name": "Orders Plus", "category": "Commerce", "price": "Rs 10,000/mo", "status": "Fast setup", "icon": "fa-solid fa-box-open", "description": "Connect order lookup, refund checks, delivery updates, and product follow-ups to WhatsApp.", "fit": "Retail, D2C, distributors", "is_featured": 1, "features": ["Order status lookup", "Refund routing", "Delivery notifications", "Repeat purchase prompts"]},
        {"name": "Appointment Scheduling", "category": "Services", "price": "Rs 8,000/mo", "status": "Available", "icon": "fa-solid fa-calendar-check", "description": "Book and reschedule appointments from chat.", "fit": "Clinics, salons, consultants", "is_featured": 0, "features": []},
        {"name": "Field Agent Dispatch", "category": "Operations", "price": "Rs 14,000/mo", "status": "Available", "icon": "fa-solid fa-route", "description": "Assign service visits and field tasks.", "fit": "Repairs, inspections, home services", "is_featured": 0, "features": []},
        {"name": "Payment Reminders", "category": "Finance", "price": "Rs 6,000/mo", "status": "Installed", "icon": "fa-solid fa-receipt", "description": "Automate fee and installment reminders.", "fit": "Subscriptions, fees, installments", "is_featured": 0, "features": []},
        {"name": "Advanced Analytics", "category": "Reporting", "price": "Rs 8,000/mo", "status": "Installed", "icon": "fa-solid fa-chart-pie", "description": "Custom exports and cohorts.", "fit": "Management reporting", "is_featured": 0, "features": []},
        {"name": "Priority Support", "category": "Support", "price": "Rs 15,000/mo", "status": "Installed", "icon": "fa-solid fa-headset", "description": "2 hour response SLA.", "fit": "High-volume teams", "is_featured": 0, "features": []},
        {"name": "Extra AI Messages", "category": "AI Usage", "price": "Rs 12,000/mo", "status": "Installed", "icon": "fa-solid fa-comments", "description": "50,000 additional AI messages.", "fit": "Growing automation volume", "is_featured": 0, "features": []},
    ]
    addon_ids = {}
    for sort_order, addon in enumerate(addon_rows, start=1):
        features = addon.pop("features")
        cursor = connection.execute(
            """
            INSERT INTO addon_modules
            (tenant_id, name, category, price, status, icon, description, fit, is_featured, sort_order)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (tenant_id, addon["name"], addon["category"], addon["price"], addon["status"], addon["icon"], addon["description"], addon["fit"], addon["is_featured"], sort_order),
        )
        addon_id = cursor.lastrowid
        addon_ids[addon["name"]] = addon_id
        insert_rows(connection, "addon_features", [{"addon_module_id": addon_id, "feature": feature} for feature in features])

    insert_rows(connection, "tenant_addons", [
        {"tenant_id": tenant_id, "addon_module_id": addon_ids["Advanced Analytics"], "owner": "Admin User", "renewal": "Aug 1, 2026", "usage": "Active"},
        {"tenant_id": tenant_id, "addon_module_id": addon_ids["Payment Reminders"], "owner": "Finance Desk", "renewal": "Aug 1, 2026", "usage": "Active"},
        {"tenant_id": tenant_id, "addon_module_id": addon_ids["Priority Support"], "owner": "Admin User", "renewal": "Aug 1, 2026", "usage": "Active"},
        {"tenant_id": tenant_id, "addon_module_id": addon_ids["Extra AI Messages"], "owner": "Admin User", "renewal": "Aug 1, 2026", "usage": "72% used"},
    ])
    insert_rows(connection, "industry_recommendations", [
        {"tenant_id": tenant_id, "name": "Education", "modules": "Admissions CRM, GPS Fleet Tracking, Payment Reminders", "progress": 86},
        {"tenant_id": tenant_id, "name": "Vehicle Rental", "modules": "GPS Fleet Tracking, Field Agent Dispatch, Damage Reports", "progress": 82},
        {"tenant_id": tenant_id, "name": "Healthcare", "modules": "Appointment Scheduling, Patient Follow-ups, Intake Forms", "progress": 74},
        {"tenant_id": tenant_id, "name": "Commerce", "modules": "Orders Plus, Returns Assistant, Loyalty Campaigns", "progress": 68},
    ])
    insert_rows(connection, "subscription_estimates", [
        {"tenant_id": tenant_id, "label": "Current Growth plan", "value": "Rs 84,200/mo"},
        {"tenant_id": tenant_id, "label": "Selected add-ons", "value": "Rs 30,000/mo"},
        {"tenant_id": tenant_id, "label": "Estimated new total", "value": "Rs 114,200/mo"},
    ])


def page_meta(slug):
    page = fetch_one("SELECT id, title AS page_title, subtitle AS page_subtitle FROM pages WHERE slug = ?", (slug,))
    if not page:
        return {"page_title": "", "page_subtitle": ""}
    return page


def summary(slug):
    page = page_meta(slug)
    if not page.get("id"):
        return []
    return fetch_all(
        "SELECT label, value, icon, tone, change FROM summary_metrics WHERE page_id = ? ORDER BY sort_order",
        (page["id"],),
    )


def ordered(table, tenant_id=1, columns="*"):
    return fetch_all(f"SELECT {columns} FROM {table} WHERE tenant_id = ? ORDER BY sort_order", (tenant_id,))


def page_ordered(table, slug, columns="*"):
    page = page_meta(slug)
    return fetch_all(f"SELECT {columns} FROM {table} WHERE page_id = ? ORDER BY sort_order", (page["id"],))


def with_page(slug, payload):
    page = page_meta(slug)
    page.pop("id", None)
    return {**page, **payload}


def dashboard_updated_at():
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def format_metric(value):
    try:
        return f"{int(value):,}"
    except (TypeError, ValueError):
        return str(value or "0")


def clamp_percent(value):
    return max(0, min(100, int(round(value or 0))))


def parse_percent(value):
    if value is None:
        return None
    try:
        return float(str(value).replace("%", "").strip())
    except ValueError:
        return None


def dashboard_thread_counts(tenant_id=1):
    return fetch_one(
        """
        SELECT
            COUNT(*) AS total,
            SUM(CASE WHEN handler = 'AI' THEN 1 ELSE 0 END) AS ai_handled,
            SUM(CASE WHEN handler = 'Human' OR status = 'Escalated' THEN 1 ELSE 0 END) AS escalated,
            SUM(CASE WHEN status = 'Resolved' THEN 1 ELSE 0 END) AS resolved,
            SUM(CASE WHEN status = 'Waiting' THEN 1 ELSE 0 END) AS waiting,
            SUM(CASE WHEN status = 'Active' THEN 1 ELSE 0 END) AS active,
            SUM(CASE WHEN sentiment = 'Negative' THEN 1 ELSE 0 END) AS negative
        FROM conversation_threads
        WHERE tenant_id = ?
        """,
        (tenant_id,),
    ) or {}


def get_dashboard_summary(tenant_id=1):
    counts = dashboard_thread_counts(tenant_id)
    total = counts.get("total") or 0
    if not total:
        return page_ordered("dashboard_stats", "dashboard", "title, value, change, trend, icon")

    csat_rows = fetch_all("SELECT csat FROM customers WHERE tenant_id = ?", (tenant_id,))
    csat_values = [value for value in (parse_percent(row.get("csat")) for row in csat_rows) if value is not None]
    csat = sum(csat_values) / len(csat_values) if csat_values else 92.0
    automation = ((counts.get("ai_handled") or 0) / total) * 100
    escalation_rate = ((counts.get("escalated") or 0) / total) * 100

    return [
        {
            "title": "Total Conversations",
            "value": format_metric(total),
            "raw_value": total,
            "change": f"{format_metric(counts.get('active') or 0)} active",
            "trend": "up" if counts.get("active") else "neutral",
            "icon": "fa-solid fa-comments",
            "url": "/conversations",
            "help": "Total live WhatsApp threads currently stored in PingPilot. Open it to drill into every conversation timeline and routing state.",
        },
        {
            "title": "Escalations",
            "value": format_metric(counts.get("escalated") or 0),
            "raw_value": counts.get("escalated") or 0,
            "change": f"{escalation_rate:.1f}% of volume",
            "trend": "down" if escalation_rate < 20 else "up",
            "icon": "fa-solid fa-headset",
            "url": "/conversations?status=Escalated",
            "help": "Threads currently owned by humans or marked escalated. Use this to inspect where AI routing has handed work to your team.",
        },
        {
            "title": "Customer Satisfaction",
            "value": f"{csat:.1f}%",
            "raw_value": csat,
            "change": f"{format_metric(counts.get('resolved') or 0)} resolved",
            "trend": "up" if csat >= 90 else "down",
            "icon": "fa-solid fa-face-smile",
            "url": "/analytics?metric=csat",
            "help": "Average customer satisfaction from stored customer records, paired with current resolution volume.",
        },
        {
            "title": "Automation Rate",
            "value": f"{automation:.1f}%",
            "raw_value": automation,
            "change": f"{format_metric(counts.get('ai_handled') or 0)} AI handled",
            "trend": "up" if automation >= 70 else "down",
            "icon": "fa-solid fa-bolt",
            "url": "/analytics?metric=automation",
            "help": "Share of stored conversations currently handled by AI rather than a human queue.",
        },
    ]


def get_dashboard_recent_conversations(tenant_id=1, limit=4):
    rows = fetch_all(
        """
        SELECT id, customer_name, time, last_message, handler, status, messages
        FROM conversation_threads
        WHERE tenant_id = ?
        ORDER BY sort_order, id
        LIMIT ?
        """,
        (tenant_id, limit),
    )
    if not rows:
        return ordered("dashboard_conversations", tenant_id=tenant_id, columns="customer_name, avatar, time, last_message, handler, status, unread")
    conversations = []
    for row in rows:
        status = row.get("status") or "Active"
        conversations.append({
            "id": row.get("id"),
            "customer_name": row.get("customer_name"),
            "avatar": None,
            "time": row.get("time") or "Recently",
            "last_message": row.get("last_message"),
            "handler": row.get("handler") or "AI",
            "status": status,
            "unread": 0 if status == "Resolved" else min(row.get("messages") or 0, 9),
            "url": f"/conversations?thread={row.get('id')}",
        })
    return conversations


def dashboard_module_icon(module_name):
    icons = {
        "sales": "fa-solid fa-chart-line",
        "admissions": "fa-solid fa-graduation-cap",
        "appointments": "fa-solid fa-calendar-check",
        "orders": "fa-solid fa-box",
        "support": "fa-solid fa-life-ring",
        "billing": "fa-solid fa-credit-card",
    }
    return icons.get((module_name or "").lower(), "fa-solid fa-layer-group")


def get_dashboard_modules(tenant_id=1):
    rows = fetch_all(
        """
        SELECT
            module AS name,
            COUNT(*) AS total,
            SUM(CASE WHEN status = 'Resolved' THEN 1 ELSE 0 END) AS resolved
        FROM conversation_threads
        WHERE tenant_id = ?
        GROUP BY module
        ORDER BY total DESC, module
        LIMIT 6
        """,
        (tenant_id,),
    )
    if not rows:
        return ordered("business_modules", tenant_id=tenant_id, columns="name, value, label, progress, icon")
    return [
        {
            "name": row["name"],
            "value": format_metric(row["total"]),
            "raw_value": row["total"],
            "label": "threads handled",
            "progress": clamp_percent(((row["resolved"] or 0) / row["total"]) * 100 if row["total"] else 0),
            "icon": dashboard_module_icon(row["name"]),
            "url": f"/analytics?module={row['name']}",
        }
        for row in rows
    ]


def get_dashboard_handoffs(tenant_id=1):
    rows = fetch_all(
        """
        SELECT module AS team, COUNT(*) AS count
        FROM conversation_threads
        WHERE tenant_id = ?
          AND (handler = 'Human' OR status = 'Escalated')
          AND status != 'Resolved'
        GROUP BY module
        ORDER BY count DESC, module
        LIMIT 5
        """,
        (tenant_id,),
    )
    if not rows:
        return ordered("escalations", tenant_id=tenant_id, columns="team, count, sla, tone")
    return [
        {
            "team": f"{row['team']} Team",
            "count": row["count"],
            "sla": "Live queue",
            "tone": "warning" if row["count"] >= 3 else "good",
            "url": f"/conversations?status=Escalated&module={row['team']}",
        }
        for row in rows
    ]


def get_dashboard_status_breakdown(tenant_id=1):
    rows = fetch_all(
        """
        SELECT status, COUNT(*) AS count
        FROM conversation_threads
        WHERE tenant_id = ?
        GROUP BY status
        ORDER BY count DESC
        """,
        (tenant_id,),
    )
    if not rows:
        return {
            "labels": ["Resolved by AI", "Waiting", "Escalated", "Abandoned"],
            "values": [68, 14, 12, 6],
        }
    labels = [row["status"] for row in rows]
    values = [row["count"] for row in rows]
    return {"labels": labels, "values": values}


def get_dashboard_traffic(range_key="7d", tenant_id=1):
    range_key = range_key if range_key in {"7d", "30d", "90d"} else "7d"
    counts = dashboard_thread_counts(tenant_id)
    total = counts.get("total") or 0
    ai_total = counts.get("ai_handled") or 0
    human_total = counts.get("escalated") or 0
    fallback = {
        "7d": {"labels": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"], "ai": [1840, 2140, 2380, 2210, 2690, 2860, 3120], "human": [210, 248, 224, 276, 240, 196, 178]},
        "30d": {"labels": ["W1", "W2", "W3", "W4", "Now"], "ai": [8420, 9210, 10480, 11340, 12620], "human": [940, 880, 802, 724, 690]},
        "90d": {"labels": ["Apr", "May", "Jun", "Jul"], "ai": [28400, 34600, 41200, 46300], "human": [3820, 3440, 2960, 2510]},
    }
    if not total:
        return fallback[range_key]

    labels = fallback[range_key]["labels"]
    weight_sets = {
        "7d": [0.78, 0.86, 0.93, 0.88, 1.0, 1.07, 1.16],
        "30d": [0.72, 0.86, 0.98, 1.08, 1.18],
        "90d": [0.68, 0.86, 1.0, 1.14],
    }
    weights = weight_sets[range_key]
    scale = max(total, len(weights) * 3)
    ai_base = max(1, round((ai_total or total) / len(weights)))
    human_base = max(1 if human_total else 0, round(human_total / len(weights)))
    return {
        "labels": labels,
        "ai": [max(0, round(ai_base * weight * scale / max(total, 1))) for weight in weights],
        "human": [max(0, round(human_base * weight * scale / max(total, 1))) for weight in weights],
    }


def get_dashboard_recent_activity(tenant_id=1, limit=5):
    audit_rows = fetch_all(
        """
        SELECT event, user, time, status
        FROM audit_logs
        WHERE tenant_id = ?
        ORDER BY sort_order, id
        LIMIT ?
        """,
        (tenant_id, limit),
    )
    if audit_rows:
        return [
            {
                "title": row["event"],
                "description": f"Workspace event recorded for {row['user']}.",
                "activity_type": "Audit",
                "icon": "fa-solid fa-shield-halved",
                "time": row["time"],
                "user": row["user"],
                "status": row["status"],
            }
            for row in audit_rows
        ]
    return ordered("dashboard_activities", tenant_id=tenant_id, columns="title, description, activity_type, icon, time, user, status")


def get_dashboard_performance(tenant_id=1):
    counts = dashboard_thread_counts(tenant_id)
    total = counts.get("total") or 0
    if not total:
        return page_ordered("performance_metrics", "dashboard", "title, subtitle, icon, value, unit, progress, status, change")
    resolution = ((counts.get("resolved") or 0) / total) * 100
    fallback = ((counts.get("negative") or 0) / total) * 100
    ai_decisions = fetch_one("SELECT AVG(confidence) AS confidence FROM ai_escalation_decisions WHERE tenant_id = ?", (tenant_id,)) or {}
    confidence = ai_decisions.get("confidence") or 88
    return [
        {
            "title": "Routing Confidence",
            "subtitle": "Average AI escalation confidence",
            "icon": "fa-solid fa-route",
            "value": f"{confidence:.1f}",
            "unit": "%",
            "progress": clamp_percent(confidence),
            "status": "excellent" if confidence >= 90 else "good",
            "change": "Live from AI decisions",
        },
        {
            "title": "Resolution Rate",
            "subtitle": "Threads marked resolved",
            "icon": "fa-solid fa-circle-check",
            "value": f"{resolution:.1f}",
            "unit": "%",
            "progress": clamp_percent(resolution),
            "status": "good" if resolution >= 50 else "warning",
            "change": f"{format_metric(counts.get('resolved') or 0)} resolved",
        },
        {
            "title": "Fallback Risk",
            "subtitle": "Negative sentiment share",
            "icon": "fa-solid fa-triangle-exclamation",
            "value": f"{fallback:.1f}",
            "unit": "%",
            "progress": clamp_percent(100 - fallback),
            "status": "warning" if fallback >= 20 else "good",
            "change": f"{format_metric(counts.get('negative') or 0)} flagged threads",
        },
    ]


def get_dashboard_runtime_status(tenant_id=1):
    runtime = get_ai_runtime()
    connection = fetch_one(
        """
        SELECT provider_label, model, updated_at
        FROM assistant_connections
        ORDER BY updated_at DESC, id DESC
        LIMIT 1
        """
    )
    kb_count = fetch_one("SELECT COUNT(*) AS count FROM kb_entries WHERE tenant_id = ?", (tenant_id,)) or {}
    handoffs = get_dashboard_handoffs(tenant_id)
    configured = bool(connection)
    return {
        "provider": connection["provider_label"] if connection else "No provider configured",
        "model": connection["model"] if connection else runtime["primary_model"],
        "description": "Active provider and model used by simulator, prompts, and routing decisions." if configured else "Connect Ollama or OpenRouter before relying on live AI responses.",
        "configured": configured,
        "status_label": "Online" if configured else "Setup needed",
        "status_tone": "online" if configured else "warning",
        "confidence": runtime.get("confidence_threshold", 82),
        "latency": "Live",
        "deployment_version": runtime.get("deployment_version", 1),
        "whatsapp_status": "Test harness",
        "kb_status": f"{kb_count.get('count') or 0} entries",
        "handoff_status": f"{sum(item.get('count') or 0 for item in handoffs)} open",
    }


def get_dashboard_data():
    tenant = fetch_one("SELECT name AS company_name, industry FROM tenants WHERE id = 1") or {"company_name": "PingPilot Workspace"}
    handoffs = get_dashboard_handoffs()
    return with_page("dashboard", {
        "workspace": tenant,
        "updated_at": dashboard_updated_at(),
        "ai_runtime": get_ai_runtime(),
        "runtime_status": get_dashboard_runtime_status(),
        "stats": get_dashboard_summary(),
        "conversations": get_dashboard_recent_conversations(),
        "activities": get_dashboard_recent_activity(),
        "performance": get_dashboard_performance(),
        "modules": get_dashboard_modules(),
        "escalations": handoffs,
        "handoff_total": sum(item.get("count") or 0 for item in handoffs),
        "traffic": get_dashboard_traffic(),
        "status_breakdown": get_dashboard_status_breakdown(),
    })


def conversation_select_columns():
    return """id, customer_name, phone, intent, module, handler, status, priority, sentiment,
        time, last_message, messages, sla, assigned_team, assigned_user_id, assigned_user_name,
        assigned_at, resolved_at"""


def conversation_row_decorated(row):
    if not row:
        return row
    row["assignee"] = row.get("assigned_user_name") or row.get("assigned_team") or "Unassigned"
    row["is_assigned"] = bool(row.get("assigned_user_name") or row.get("assigned_team"))
    return row


def conversation_filters_sql(filters, tenant_id=1, permitted_user_id=None):
    where = ["tenant_id = ?"]
    params = [tenant_id]
    status = (filters.get("status") or "").strip()
    if status and status != "All":
        where.append("status = ?")
        params.append(status)
    for key in ["module", "priority", "handler", "sentiment"]:
        value = (filters.get(key) or "").strip()
        if value:
            where.append(f"{key} = ?")
            params.append(value)
    assignee = (filters.get("assignee") or "").strip()
    if assignee:
        where.append("(assigned_team LIKE ? OR assigned_user_name LIKE ?)")
        params.extend([f"%{assignee}%", f"%{assignee}%"])
    query = (filters.get("q") or "").strip()
    if query:
        like = f"%{query}%"
        where.append("(customer_name LIKE ? OR phone LIKE ? OR intent LIKE ? OR module LIKE ? OR last_message LIKE ?)")
        params.extend([like, like, like, like, like])
    if permitted_user_id is not None:
        where.append("assigned_user_id = ?")
        params.append(permitted_user_id)
    return " AND ".join(where), params


def get_conversation_summary_counts(tenant_id=1, permitted_user_id=None):
    where = "tenant_id = ?"
    params = [tenant_id]
    if permitted_user_id is not None:
        where += " AND assigned_user_id = ?"
        params.append(permitted_user_id)
    rows = fetch_all(
        f"""SELECT status, COUNT(*) AS count
        FROM conversation_threads
        WHERE {where}
        GROUP BY status""",
        params,
    )
    counts = {row["status"]: row["count"] for row in rows}
    total = sum(counts.values())
    return {
        "total": total,
        "active": counts.get("Active", 0),
        "waiting": counts.get("Waiting", 0),
        "escalated": counts.get("Escalated", 0),
        "resolved": counts.get("Resolved", 0),
    }


def get_conversation_threads(filters=None, tenant_id=1, permitted_user_id=None, limit=100):
    filters = filters or {}
    where, params = conversation_filters_sql(filters, tenant_id, permitted_user_id)
    rows = fetch_all(
        f"""SELECT {conversation_select_columns()}
        FROM conversation_threads
        WHERE {where}
        ORDER BY CASE status WHEN 'Escalated' THEN 0 WHEN 'Waiting' THEN 1 WHEN 'Active' THEN 2 ELSE 3 END,
                 sort_order, id
        LIMIT ?""",
        (*params, limit),
    )
    return [conversation_row_decorated(row) for row in rows]


def get_conversation_filter_options(tenant_id=1):
    def values(column):
        return [
            row[column]
            for row in fetch_all(
                f"SELECT DISTINCT {column} FROM conversation_threads WHERE tenant_id = ? AND {column} != '' ORDER BY {column}",
                (tenant_id,),
            )
        ]

    assignees = fetch_all(
        """SELECT DISTINCT assigned_team AS value FROM conversation_threads
        WHERE tenant_id = ? AND assigned_team != ''
        UNION
        SELECT DISTINCT assigned_user_name AS value FROM conversation_threads
        WHERE tenant_id = ? AND assigned_user_name != ''
        ORDER BY value""",
        (tenant_id, tenant_id),
    )
    return {
        "modules": values("module"),
        "priorities": values("priority"),
        "handlers": values("handler"),
        "sentiments": values("sentiment"),
        "assignees": [row["value"] for row in assignees],
    }


def get_conversation_assignees(tenant_id=1):
    teams = ordered("teams", tenant_id=tenant_id, columns="name")
    members = ordered("team_members", tenant_id=tenant_id, columns="id, name, email, team, status")
    return {"teams": teams, "members": members}


def get_conversations_data():
    threads = get_conversation_threads()
    return with_page("conversations", {
        "summary": summary("conversations"),
        "summary_counts": get_conversation_summary_counts(),
        "threads": threads,
        "quick_filters": [item["label"] for item in page_ordered("quick_filters", "conversations", "label")],
        "filter_options": get_conversation_filter_options(),
        "assignees": get_conversation_assignees(),
    })


def get_analytics_data():
    return with_page("analytics", {
        "summary": summary("analytics"),
        "funnels": ordered("analytics_funnels", columns="name, value, progress"),
        "intents": ordered("analytics_intents", columns="name, count, share"),
        "teams": ordered("team_performance", columns="name, resolved, avg_sla, csat"),
    })


def get_settings_data():
    tenant = fetch_one("SELECT name AS company_name, industry, timezone, language FROM tenants WHERE id = 1")
    runtime = get_ai_runtime()
    models = ordered("settings_models", columns="name, model, temperature, status")
    for model in models:
        model["model"] = runtime["fallback_model"] if "Fallback" in model["name"] else runtime["primary_model"]
    return with_page("settings", {
        "workspace": tenant,
        "workspace_settings": fetch_one("SELECT * FROM workspace_settings WHERE tenant_id = 1"),
        "ai_runtime": runtime,
        "channels": ordered("settings_channels", columns="name, status, detail, tone"),
        "models": models,
        "modules": ordered("settings_modules", columns="id, name, enabled, owner"),
    })


def get_security_data():
    return with_page("security", {
        "summary": summary("security"),
        "access_rules": ordered("security_access_rules", columns="id, name, detail, enabled"),
        "roles": ordered("security_roles", columns="id, role, users, permissions"),
        "permission_groups": get_permission_groups(),
        "dashboard_users": get_dashboard_users(),
        "audit_logs": ordered("audit_logs", columns="event, user, ip, time, status"),
        "compliance": ordered("compliance_items", columns="name, value, progress"),
        "security_settings": fetch_one("SELECT * FROM workspace_settings WHERE tenant_id = 1"),
    })


def get_support_data():
    return with_page("support", {
        "summary": summary("support"),
        "tickets": ordered("support_tickets", columns="id, ticket_id, subject, priority, owner, status, updated, request_type, description, attachment, created_at"),
        "status_checks": ordered("status_checks", columns="name, status, detail"),
        "resources": ordered("support_resources", columns="title, detail, icon"),
    })


def get_customers_data():
    return with_page("customers", {
        "summary": summary("customers"),
        "segments": ordered("customer_segments", columns="name, value, progress"),
        "customers": ordered("customers", columns="id, name, phone, segment, stage, last_seen, csat, health"),
        "timeline": ordered("customer_timeline", columns="title, customer, time, status"),
    })


def get_team_data():
    members = ordered("team_members", columns="id, name, email, permission_group, role, team, status, assigned, resolved, csat")
    for member in members:
        member["permission_label"] = permission_group_label(member.get("permission_group"))
        member["is_owner"] = member.get("permission_group") == "owner"
    return with_page("team-members", {
        "summary": summary("team-members"),
        "members": members,
        "teams": ordered("teams", columns="name, members, queue, sla, progress"),
        "roles": ordered("team_roles", columns="id, name, count, scope, permissions"),
        "permission_groups": get_permission_groups(),
        "dashboard_users": get_dashboard_users(),
    })


def get_billing_data():
    tenant = fetch_one(
        """SELECT subscription_plan, billing_cycle FROM tenants WHERE id = 1"""
    ) or {"subscription_plan": "growth", "billing_cycle": "monthly"}
    plan = get_subscription_plan(tenant.get("subscription_plan") or "growth") or get_subscription_plan("growth")
    plan["billing_cycle"] = tenant.get("billing_cycle") or "monthly"
    plan["current_price"] = plan["yearly_price"] if plan["billing_cycle"] == "yearly" else plan["monthly_price"]
    return with_page("billing", {
        "summary": summary("billing"),
        "plan": plan,
        "usage": ordered("billing_usage", columns="name, value, progress"),
        "invoices": ordered("invoices", columns="id, invoice_id, date, amount, status"),
        "add_ons": ordered("billing_addons", columns="id, name, detail, price, enabled"),
        "contacts": ordered("billing_contacts", columns="name, email, role"),
    })


def get_add_ons_data():
    featured = fetch_all(
        """
        SELECT id, name, category, price, status, icon, description
        FROM addon_modules
        WHERE tenant_id = 1 AND is_featured = 1
        ORDER BY sort_order
        """
    )
    for module in featured:
        module["features"] = [
            item["feature"]
            for item in fetch_all("SELECT feature FROM addon_features WHERE addon_module_id = ? ORDER BY sort_order", (module["id"],))
        ]
    installed = fetch_all(
        """
        SELECT addon_modules.name, tenant_addons.owner, tenant_addons.renewal, tenant_addons.usage
        FROM tenant_addons
        JOIN addon_modules ON addon_modules.id = tenant_addons.addon_module_id
        WHERE tenant_addons.tenant_id = 1
        ORDER BY tenant_addons.sort_order
        """
    )
    return with_page("add-ons", {
        "summary": summary("add-ons"),
        "featured": featured,
        "marketplace": ordered("addon_modules", columns="id, name, category, fit, price, status"),
        "installed": installed,
        "industries": ordered("industry_recommendations", columns="name, modules, progress"),
        "estimate": ordered("subscription_estimates", columns="label, value"),
    })


def get_ai_assistant_data():
    runtime = get_ai_runtime()
    assistants = ordered("ai_assistants", columns="id, name, model, module, status, confidence")
    for assistant in assistants:
        assistant["model"] = runtime["fallback_model"] if "Fallback" in assistant["name"] else runtime["primary_model"]
    page_data = with_page("ai-assistant", {
        "summary": summary("ai-assistant"),
        "runtime": runtime,
        "assistants": assistants,
        "guardrails": ordered("ai_guardrails", columns="id, name, detail, enabled"),
        "test_cases": ordered("ai_test_cases", columns="id, prompt, intent, result"),
    })
    for item in page_data["summary"]:
        if item["label"] == "Primary Model":
            item["value"] = runtime["primary_model"]
    return page_data


def get_ai_runtime(tenant_id=1):
    return fetch_one("SELECT * FROM ai_runtime_settings WHERE tenant_id = ?", (tenant_id,))


def get_knowledge_base_data():
    return with_page("knowledge-base", {
        "summary": summary("knowledge-base"),
        "sources": ordered("kb_sources", columns="name, type, documents, status, updated"),
        "coverage": ordered("kb_coverage", columns="name, value, progress"),
        "gaps": ordered("kb_gaps", columns="topic, impact, owner, status"),
        "sync_settings": fetch_one("SELECT * FROM kb_sync_settings WHERE tenant_id = 1"),
        "entries": fetch_all(
            """
            SELECT id, title, category, content, tags, status, created_at
            FROM kb_entries
            WHERE tenant_id = 1
            ORDER BY created_at DESC, id DESC
            """
        ),
    })


def add_knowledge_entry(title, category, content, tags="", tenant_id=1):
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO kb_entries (tenant_id, title, category, content, tags, status)
            VALUES (?, ?, ?, ?, ?, 'Published')
            """,
            (tenant_id, title, category, content, tags),
        )
        connection.commit()


def knowledge_excerpt(row, terms, max_chars=1800):
    content = row["content"] or ""
    if len(content) <= max_chars:
        excerpt = content
    else:
        lowered = content.lower()
        first_match = next((lowered.find(term) for term in terms if lowered.find(term) >= 0), -1)
        if first_match < 0:
            first_match = 0
        start = max(0, first_match - max_chars // 3)
        end = min(len(content), start + max_chars)
        excerpt = content[start:end].strip()
        if start > 0:
            excerpt = f"...{excerpt}"
        if end < len(content):
            excerpt = f"{excerpt}..."

    result = dict(row)
    result["content"] = excerpt
    return result


def search_knowledge_entries(query, tenant_id=1, limit=5):
    terms = [term.strip().lower() for term in query.split() if len(term.strip()) > 2]
    if not terms:
        rows = fetch_all(
            """
            SELECT title, category, content, tags
            FROM kb_entries
            WHERE tenant_id = ? AND status = 'Published'
            ORDER BY updated_at DESC, id DESC
            LIMIT ?
            """,
            (tenant_id, limit),
        )
        return [knowledge_excerpt(row, terms) for row in rows]

    rows = fetch_all(
        """
        SELECT title, category, content, tags
        FROM kb_entries
        WHERE tenant_id = ? AND status = 'Published'
        ORDER BY updated_at DESC, id DESC
        LIMIT 50
        """,
        (tenant_id,),
    )

    def score(row):
        haystack = f"{row['title']} {row['category']} {row['content']} {row.get('tags') or ''}".lower()
        return sum(1 for term in terms if term in haystack)

    ranked = sorted(
        ((score(row), row) for row in rows),
        key=lambda item: item[0],
        reverse=True,
    )
    matches = [row for row_score, row in ranked if row_score > 0]
    selected = matches[:limit] or rows[: min(limit, len(rows))]
    return [knowledge_excerpt(row, terms) for row in selected]


def global_search(query, tenant_id=1, limit=18):
    term = f"%{query.strip()}%"
    searches = [
        (
            "Conversation", "conversations", "fa-regular fa-comments",
            """SELECT customer_name AS title, intent || ' - ' || last_message AS detail
            FROM conversation_threads WHERE tenant_id = ? AND
            (customer_name LIKE ? OR phone LIKE ? OR intent LIKE ? OR last_message LIKE ?)
            ORDER BY sort_order LIMIT 4""",
            (tenant_id, term, term, term, term),
        ),
        (
            "Customer", "customers", "fa-regular fa-user",
            """SELECT name AS title, phone || ' - ' || segment || ' - ' || stage AS detail
            FROM customers WHERE tenant_id = ? AND
            (name LIKE ? OR phone LIKE ? OR segment LIKE ? OR stage LIKE ?)
            ORDER BY sort_order LIMIT 4""",
            (tenant_id, term, term, term, term),
        ),
        (
            "Knowledge", "knowledge_base", "fa-solid fa-book-open",
            """SELECT title, category || ' - ' || substr(content, 1, 120) AS detail
            FROM kb_entries WHERE tenant_id = ? AND
            (title LIKE ? OR category LIKE ? OR content LIKE ? OR COALESCE(tags, '') LIKE ?)
            ORDER BY updated_at DESC LIMIT 4""",
            (tenant_id, term, term, term, term),
        ),
        (
            "Prompt", "prompt_builder", "fa-solid fa-wand-magic-sparkles",
            """SELECT name AS title, module || ' - ' || version || ' - ' || status AS detail
            FROM prompts WHERE tenant_id = ? AND
            (name LIKE ? OR module LIKE ? OR version LIKE ? OR instructions LIKE ?)
            ORDER BY sort_order LIMIT 4""",
            (tenant_id, term, term, term, term),
        ),
        (
            "Workflow", "workflows", "fa-solid fa-code-branch",
            """SELECT name AS title, trigger || ' - ' || owner || ' - ' || status AS detail
            FROM workflows WHERE tenant_id = ? AND
            (name LIKE ? OR trigger LIKE ? OR owner LIKE ? OR status LIKE ?)
            ORDER BY sort_order LIMIT 4""",
            (tenant_id, term, term, term, term),
        ),
        (
            "Team member", "team_members", "fa-solid fa-user-group",
            """SELECT name AS title, role || ' - ' || team || ' - ' || status AS detail
            FROM team_members WHERE tenant_id = ? AND
            (name LIKE ? OR role LIKE ? OR team LIKE ? OR status LIKE ?)
            ORDER BY sort_order LIMIT 4""",
            (tenant_id, term, term, term, term),
        ),
        (
            "Help resource", "support", "fa-regular fa-circle-question",
            """SELECT title, detail FROM support_resources WHERE tenant_id = ? AND
            (title LIKE ? OR detail LIKE ?) ORDER BY sort_order LIMIT 5""",
            (tenant_id, term, term),
        ),
        (
            "Support ticket", "support", "fa-solid fa-ticket",
            """SELECT ticket_id || ' - ' || subject AS title,
            priority || ' - ' || owner || ' - ' || status AS detail
            FROM support_tickets WHERE tenant_id = ? AND
            (ticket_id LIKE ? OR subject LIKE ? OR priority LIKE ? OR owner LIKE ? OR status LIKE ?)
            ORDER BY sort_order LIMIT 4""",
            (tenant_id, term, term, term, term, term),
        ),
        (
            "Platform service", "support", "fa-solid fa-heart-pulse",
            """SELECT name AS title, status || ' - ' || detail AS detail
            FROM status_checks WHERE tenant_id = ? AND
            (name LIKE ? OR status LIKE ? OR detail LIKE ?) ORDER BY sort_order LIMIT 4""",
            (tenant_id, term, term, term),
        ),
        (
            "Add-on", "add_ons", "fa-solid fa-puzzle-piece",
            """SELECT name AS title, category || ' - ' || price || ' - ' || COALESCE(description, '') AS detail
            FROM addon_modules WHERE tenant_id = ? AND
            (name LIKE ? OR category LIKE ? OR description LIKE ? OR fit LIKE ?) ORDER BY sort_order LIMIT 4""",
            (tenant_id, term, term, term, term),
        ),
        (
            "Module setting", "settings", "fa-solid fa-sliders",
            """SELECT name AS title, owner || CASE WHEN enabled = 1 THEN ' - Enabled' ELSE ' - Disabled' END AS detail
            FROM settings_modules WHERE tenant_id = ? AND
            (name LIKE ? OR owner LIKE ?) ORDER BY sort_order LIMIT 4""",
            (tenant_id, term, term),
        ),
    ]
    results = []
    endpoint_by_slug = {
        "dashboard": "dashboard",
        "conversations": "conversations",
        "analytics": "analytics",
        "settings": "settings",
        "security": "security",
        "support": "support",
        "customers": "customers",
        "team-members": "team_members",
        "billing": "billing",
        "add-ons": "add_ons",
        "ai-assistant": "ai_assistant",
        "knowledge-base": "knowledge_base",
        "prompt-builder": "prompt_builder",
        "workflows": "workflows",
    }
    with get_connection() as connection:
        account_text = query.strip().lower()
        if any(word in account_text for word in ["account", "profile", "personalization", "theme", "preferences"]):
            results.append({
                "type": "Page",
                "page": "account_settings",
                "icon": "fa-regular fa-user",
                "title": "Account Settings",
                "detail": "Manage your profile, notifications, sessions, and console personalization.",
                "priority": 0,
            })
        page_rows = connection.execute(
            """SELECT slug, title, subtitle FROM pages WHERE tenant_id = ? AND
            (title LIKE ? OR subtitle LIKE ? OR slug LIKE ?) ORDER BY title""",
            (tenant_id, term, term, term),
        ).fetchall()
        for row in page_rows:
            endpoint = endpoint_by_slug.get(row["slug"])
            if endpoint:
                results.append({
                    "type": "Page",
                    "page": endpoint,
                    "icon": "fa-solid fa-arrow-up-right-from-square",
                    "title": row["title"],
                    "detail": row["subtitle"],
                    "priority": 0,
                })
        for result_type, page, icon, sql, params in searches:
            for row in connection.execute(sql, params).fetchall():
                results.append({
                    "type": result_type,
                    "page": page,
                    "icon": icon,
                    "title": row["title"],
                    "detail": row["detail"],
                    "fragment": {
                        "Help resource": "help-center",
                        "Support ticket": "support-tickets",
                        "Platform service": "platform-health",
                    }.get(result_type),
                    "priority": 1 if result_type.startswith("Help") else 2,
                })
    lowered = query.strip().lower()
    results.sort(key=lambda item: (item["priority"], not item["title"].lower().startswith(lowered), item["type"], item["title"]))
    return results[:limit]


def get_prompt_builder_data():
    return with_page("prompt-builder", {
        "summary": summary("prompt-builder"),
        "prompts": ordered("prompts", columns="id, name, module, version, status, pass_rate, instructions, deployment_target"),
        "variables": ordered("prompt_variables", columns="id, name, source, required"),
        "tests": ordered("prompt_tests", columns='id, test_case AS "case", intent, result'),
    })


def get_workflows_data():
    return with_page("workflows", {
        "summary": summary("workflows"),
        "workflows": ordered("workflows", columns="id, name, trigger, owner, status, runs, success, run_mode, failure_action"),
        "steps": ordered("workflow_steps", columns="id, name, detail"),
        "rules": ordered("workflow_rules", columns="id, name, detail, enabled"),
    })


def update_ai_runtime(data, tenant_id=1):
    with get_connection() as connection:
        connection.execute(
            """UPDATE ai_runtime_settings SET primary_model = ?, fallback_model = ?,
            confidence_threshold = ?, temperature = ?, system_prompt = ?, updated_at = CURRENT_TIMESTAMP
            WHERE tenant_id = ?""",
            (data["primary_model"], data["fallback_model"], data["confidence_threshold"],
             data["temperature"], data["system_prompt"], tenant_id),
        )
        connection.execute(
            "UPDATE ai_assistants SET model = ? WHERE tenant_id = ? AND name NOT LIKE 'Fallback%'",
            (data["primary_model"], tenant_id),
        )
        connection.execute(
            "UPDATE ai_assistants SET model = ? WHERE tenant_id = ? AND name LIKE 'Fallback%'",
            (data["fallback_model"], tenant_id),
        )
        connection.execute(
            "UPDATE settings_models SET model = ? WHERE tenant_id = ? AND name NOT LIKE 'Fallback%'",
            (data["primary_model"], tenant_id),
        )
        connection.execute(
            "UPDATE settings_models SET model = ? WHERE tenant_id = ? AND name LIKE 'Fallback%'",
            (data["fallback_model"], tenant_id),
        )
        connection.commit()


def synchronize_active_model(model, tenant_id=1):
    with get_connection() as connection:
        connection.execute(
            "UPDATE ai_runtime_settings SET primary_model = ?, updated_at = CURRENT_TIMESTAMP WHERE tenant_id = ?",
            (model, tenant_id),
        )
        connection.execute(
            "UPDATE ai_assistants SET model = ? WHERE tenant_id = ? AND name NOT LIKE 'Fallback%'",
            (model, tenant_id),
        )
        connection.execute(
            "UPDATE settings_models SET model = ? WHERE tenant_id = ? AND name NOT LIKE 'Fallback%'",
            (model, tenant_id),
        )
        connection.commit()


def deploy_ai_runtime(tenant_id=1):
    with get_connection() as connection:
        connection.execute(
            "UPDATE ai_runtime_settings SET deployment_version = deployment_version + 1, updated_at = CURRENT_TIMESTAMP WHERE tenant_id = ?",
            (tenant_id,),
        )
        connection.execute("UPDATE ai_assistants SET status = 'Live' WHERE tenant_id = ?", (tenant_id,))
        connection.commit()
        return connection.execute("SELECT deployment_version FROM ai_runtime_settings WHERE tenant_id = ?", (tenant_id,)).fetchone()[0]


def set_boolean(table, row_id, enabled, tenant_id=1):
    allowed = {"ai_guardrails", "workflow_rules"}
    if table not in allowed:
        raise ValueError("Unsupported setting")
    with get_connection() as connection:
        cursor = connection.execute(
            f"UPDATE {table} SET enabled = ? WHERE id = ? AND tenant_id = ?",
            (int(bool(enabled)), row_id, tenant_id),
        )
        connection.commit()
        return cursor.rowcount > 0


def update_knowledge_entry(entry_id, status, tenant_id=1):
    with get_connection() as connection:
        cursor = connection.execute(
            "UPDATE kb_entries SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ? AND tenant_id = ?",
            (status, entry_id, tenant_id),
        )
        connection.commit()
        return cursor.rowcount > 0


def delete_knowledge_entry(entry_id, tenant_id=1):
    with get_connection() as connection:
        cursor = connection.execute("DELETE FROM kb_entries WHERE id = ? AND tenant_id = ?", (entry_id, tenant_id))
        connection.commit()
        return cursor.rowcount > 0


def update_kb_sync_settings(frequency, approval_mode, notify_failures, tenant_id=1):
    with get_connection() as connection:
        connection.execute(
            """UPDATE kb_sync_settings SET frequency = ?, approval_mode = ?, notify_failures = ?,
            updated_at = CURRENT_TIMESTAMP WHERE tenant_id = ?""",
            (frequency, approval_mode, int(bool(notify_failures)), tenant_id),
        )
        connection.execute("UPDATE kb_sources SET updated = 'Just now', status = 'Synced' WHERE tenant_id = ?", (tenant_id,))
        connection.commit()


def save_prompt(data, tenant_id=1):
    with get_connection() as connection:
        prompt_id = data.get("id")
        if prompt_id:
            connection.execute(
                """UPDATE prompts SET name = ?, module = ?, version = ?, status = ?, instructions = ?,
                deployment_target = ? WHERE id = ? AND tenant_id = ?""",
                (data["name"], data["module"], data["version"], data["status"], data["instructions"],
                 data["deployment_target"], prompt_id, tenant_id),
            )
        else:
            cursor = connection.execute(
                """INSERT INTO prompts (tenant_id, name, module, version, status, pass_rate, instructions, deployment_target, sort_order)
                VALUES (?, ?, ?, ?, ?, 0, ?, ?, (SELECT COALESCE(MAX(sort_order), 0) + 1 FROM prompts WHERE tenant_id = ?))""",
                (tenant_id, data["name"], data["module"], data["version"], data["status"], data["instructions"],
                 data["deployment_target"], tenant_id),
            )
            prompt_id = cursor.lastrowid
        connection.commit()
        return fetch_one("SELECT * FROM prompts WHERE id = ?", (prompt_id,))


def save_workflow(data, tenant_id=1):
    with get_connection() as connection:
        workflow_id = data.get("id")
        if workflow_id:
            connection.execute(
                """UPDATE workflows SET name = ?, trigger = ?, owner = ?, status = ?, run_mode = ?, failure_action = ?
                WHERE id = ? AND tenant_id = ?""",
                (data["name"], data["trigger"], data["owner"], data["status"], data["run_mode"],
                 data["failure_action"], workflow_id, tenant_id),
            )
        else:
            cursor = connection.execute(
                """INSERT INTO workflows (tenant_id, name, trigger, owner, status, runs, success, run_mode, failure_action, sort_order)
                VALUES (?, ?, ?, ?, ?, '0', 0, ?, ?, (SELECT COALESCE(MAX(sort_order), 0) + 1 FROM workflows WHERE tenant_id = ?))""",
                (tenant_id, data["name"], data["trigger"], data["owner"], data["status"], data["run_mode"],
                 data["failure_action"], tenant_id),
            )
            workflow_id = cursor.lastrowid
        connection.commit()
        return fetch_one("SELECT * FROM workflows WHERE id = ?", (workflow_id,))


def get_topbar_items(kind, tenant_id=1):
    tables = {
        "notifications": ("topbar_notifications", "id, title, body, icon, url, is_read, time"),
        "messages": ("topbar_messages", "id, sender, preview, initials, url, is_read, time"),
    }
    if kind not in tables:
        raise ValueError("Unsupported inbox type")
    table, columns = tables[kind]
    items = fetch_all(
        f"SELECT {columns} FROM {table} WHERE tenant_id = ? ORDER BY is_read, sort_order LIMIT 12",
        (tenant_id,),
    )
    unread = fetch_one(f"SELECT COUNT(*) AS count FROM {table} WHERE tenant_id = ? AND is_read = 0", (tenant_id,))["count"]
    return {"items": items, "unread": unread}


def mark_topbar_items_read(kind, item_id=None, tenant_id=1):
    tables = {"notifications": "topbar_notifications", "messages": "topbar_messages"}
    if kind not in tables:
        raise ValueError("Unsupported inbox type")
    table = tables[kind]
    with get_connection() as connection:
        if item_id is None:
            cursor = connection.execute(f"UPDATE {table} SET is_read = 1 WHERE tenant_id = ?", (tenant_id,))
        else:
            cursor = connection.execute(
                f"UPDATE {table} SET is_read = 1 WHERE tenant_id = ? AND id = ?",
                (tenant_id, item_id),
            )
        connection.commit()
        return cursor.rowcount


PERMISSION_CATALOG = [
    {"key": "page_dashboard", "label": "Dashboard", "group": "Pages"},
    {"key": "page_conversations", "label": "Conversations", "group": "Pages"},
    {"key": "page_whatsapp_test_client", "label": "Test WhatsApp Client", "group": "Pages"},
    {"key": "page_analytics", "label": "Analytics", "group": "Pages"},
    {"key": "page_ai_assistant", "label": "AI Assistant", "group": "AI Management"},
    {"key": "page_knowledge_base", "label": "Knowledge Base", "group": "AI Management"},
    {"key": "page_prompt_builder", "label": "Prompt Builder", "group": "AI Management"},
    {"key": "page_workflows", "label": "Workflows", "group": "AI Management"},
    {"key": "page_customers", "label": "Customers", "group": "Business"},
    {"key": "page_team_members", "label": "Team Members", "group": "Business"},
    {"key": "page_billing", "label": "Billing", "group": "Business"},
    {"key": "page_add_ons", "label": "Add-ons", "group": "Business"},
    {"key": "page_settings", "label": "Settings", "group": "System"},
    {"key": "page_security", "label": "Security", "group": "System"},
    {"key": "page_support", "label": "Support", "group": "System"},
    {"key": "manage_team_invites", "label": "Invite team members", "group": "Actions"},
    {"key": "assign_roles", "label": "Assign roles", "group": "Actions"},
    {"key": "manage_roles", "label": "Manage roles and permissions", "group": "Actions"},
    {"key": "export_data", "label": "Export data", "group": "Actions"},
    {"key": "manage_security", "label": "Manage security controls", "group": "Actions"},
    {"key": "manage_settings", "label": "Manage workspace settings", "group": "Actions"},
    {"key": "manage_billing", "label": "Manage billing and add-ons", "group": "Actions"},
    {"key": "manage_ai", "label": "Manage AI runtime and prompts", "group": "Actions"},
]


ALL_PERMISSION_KEYS = [item["key"] for item in PERMISSION_CATALOG]


SYSTEM_ROLES = [
    {
        "role_key": "owner",
        "name": "Owner",
        "description": "Full workspace access. Protected and cannot be changed.",
        "scope": "Full protected workspace access",
        "permissions": ALL_PERMISSION_KEYS,
        "role_type": "system",
        "locked": 1,
        "sort_order": 1,
    },
    {
        "role_key": "admin",
        "name": "Admin",
        "description": "Full administrative access except owner protection changes.",
        "scope": "Full workspace administration",
        "permissions": ALL_PERMISSION_KEYS,
        "role_type": "system",
        "locked": 1,
        "sort_order": 2,
    },
    {
        "role_key": "manager",
        "name": "Manager",
        "description": "Team lead access for operations, analytics, and customer work.",
        "scope": "Operational management",
        "permissions": [
            "page_dashboard", "page_conversations", "page_whatsapp_test_client", "page_analytics",
            "page_customers", "page_team_members", "page_support", "export_data",
        ],
        "role_type": "system",
        "locked": 1,
        "sort_order": 3,
    },
    {
        "role_key": "agent",
        "name": "Agent",
        "description": "Frontline access for assigned conversations and customer context.",
        "scope": "Conversation handling",
        "permissions": ["page_dashboard", "page_conversations", "page_customers", "page_support"],
        "role_type": "system",
        "locked": 1,
        "sort_order": 4,
    },
    {
        "role_key": "viewer",
        "name": "Viewer",
        "description": "Read-only dashboard and analytics visibility.",
        "scope": "Read-only visibility",
        "permissions": ["page_dashboard", "page_analytics", "page_support"],
        "role_type": "system",
        "locked": 1,
        "sort_order": 5,
    },
]


def normalize_role_key(name):
    key = "".join(char.lower() if char.isalnum() else "_" for char in (name or "").strip())
    key = "_".join(part for part in key.split("_") if part)
    return key[:48]


def normalize_permissions(permissions):
    if isinstance(permissions, str):
        try:
            permissions = json.loads(permissions)
        except json.JSONDecodeError:
            permissions = [item.strip() for item in permissions.split(",")]
    clean = []
    allowed = set(ALL_PERMISSION_KEYS)
    for item in permissions or []:
        value = str(item).strip()
        if value in allowed and value not in clean:
            clean.append(value)
    return clean


def seed_system_roles(connection, tenant_id=1):
    for role in SYSTEM_ROLES:
        existing = connection.execute(
            "SELECT id FROM team_roles WHERE tenant_id = ? AND role_key = ?",
            (tenant_id, role["role_key"]),
        ).fetchone()
        values = (
            role["name"],
            role["description"],
            role["role_type"],
            role["locked"],
            role["scope"],
            json.dumps(role["permissions"]),
            role["sort_order"],
        )
        if existing:
            connection.execute(
                """UPDATE team_roles
                SET name = ?, description = ?, role_type = ?, locked = ?, scope = ?, permissions = ?, sort_order = ?
                WHERE id = ?""",
                (*values, existing["id"]),
            )
        else:
            connection.execute(
                """INSERT INTO team_roles
                (tenant_id, role_key, name, description, role_type, locked, count, scope, permissions, sort_order)
                VALUES (?, ?, ?, ?, ?, ?, 0, ?, ?, ?)""",
                (tenant_id, role["role_key"], *values),
            )


SUBSCRIPTION_PLANS = [
    {
        "plan_key": "starter",
        "name": "Starter",
        "monthly_price": "Rs 24,900",
        "yearly_price": "Rs 249,000",
        "conversation_limit": "5,000 conversations",
        "ai_message_limit": "40,000 AI messages",
        "seat_limit": "15 team seats",
        "support_level": "Email support",
        "features": "WhatsApp inbox, AI assistant, knowledge base, basic analytics",
        "sort_order": 1,
    },
    {
        "plan_key": "growth",
        "name": "Growth",
        "monthly_price": "Rs 84,200",
        "yearly_price": "Rs 842,000",
        "conversation_limit": "25,000 conversations",
        "ai_message_limit": "200,000 AI messages",
        "seat_limit": "100 team seats",
        "support_level": "Priority support",
        "features": "Advanced routing, workflows, analytics, add-on marketplace, team roles",
        "sort_order": 2,
    },
    {
        "plan_key": "enterprise",
        "name": "Enterprise",
        "monthly_price": "Custom",
        "yearly_price": "Custom",
        "conversation_limit": "Custom conversations",
        "ai_message_limit": "Custom AI messages",
        "seat_limit": "Unlimited team seats",
        "support_level": "Dedicated success manager",
        "features": "Custom modules, SSO-ready controls, premium support, implementation review",
        "sort_order": 3,
    },
]


def seed_subscription_plans(connection):
    connection.executemany(
        """INSERT INTO subscription_plans
        (plan_key, name, monthly_price, yearly_price, conversation_limit, ai_message_limit, seat_limit, support_level, features, sort_order)
        VALUES (:plan_key, :name, :monthly_price, :yearly_price, :conversation_limit, :ai_message_limit, :seat_limit, :support_level, :features, :sort_order)
        ON CONFLICT(plan_key) DO UPDATE SET
            name = excluded.name,
            monthly_price = excluded.monthly_price,
            yearly_price = excluded.yearly_price,
            conversation_limit = excluded.conversation_limit,
            ai_message_limit = excluded.ai_message_limit,
            seat_limit = excluded.seat_limit,
            support_level = excluded.support_level,
            features = excluded.features,
            sort_order = excluded.sort_order""",
        SUBSCRIPTION_PLANS,
    )


def upsert_google_user(profile):
    google_sub = profile["sub"]
    email = profile["email"]
    name = profile.get("name") or email
    picture = profile.get("picture")
    hosted_domain = profile.get("hd")
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO dashboard_users (
                google_sub, email, name, picture, hosted_domain, console_theme, last_login_at
            )
            VALUES (?, ?, ?, ?, ?, 'auto', CURRENT_TIMESTAMP)
            ON CONFLICT(google_sub) DO UPDATE SET
                email = excluded.email,
                name = excluded.name,
                picture = excluded.picture,
                hosted_domain = excluded.hosted_domain,
                last_login_at = CURRENT_TIMESTAMP
            """,
            (google_sub, email, name, picture, hosted_domain),
        )
        connection.commit()
    return fetch_one(
        """SELECT id, tenant_id, google_sub, email, name, picture, hosted_domain, permission_group,
        onboarding_complete, console_theme,
        console_density, accent_color, default_sidebar
        FROM dashboard_users WHERE google_sub = ?""",
        (google_sub,),
    )


def get_dashboard_user(user_id):
    if not user_id:
        return None
    return fetch_one(
        """SELECT id, tenant_id, google_sub, email, name, picture, hosted_domain, permission_group,
        onboarding_complete, console_theme,
        console_density, accent_color, default_sidebar
        FROM dashboard_users WHERE id = ?""",
        (user_id,),
    )


def permission_group_label(group_key):
    role = get_role(group_key or "viewer")
    return role["name"] if role else "Viewer"


def get_permission_groups():
    users_by_group = {
        row["permission_group"]: row["count"]
        for row in fetch_all("SELECT permission_group, COUNT(*) AS count FROM dashboard_users GROUP BY permission_group")
    }
    members_by_group = {
        row["permission_group"]: row["count"]
        for row in fetch_all("SELECT permission_group, COUNT(*) AS count FROM team_members GROUP BY permission_group")
    }
    roles = get_roles()
    for role in roles:
        role["users"] = int(users_by_group.get(role["key"], 0)) + int(members_by_group.get(role["key"], 0))
    return roles


def permission_catalog_grouped():
    groups = {}
    for permission in PERMISSION_CATALOG:
        groups.setdefault(permission["group"], []).append(permission)
    return [{"name": name, "permissions": permissions} for name, permissions in groups.items()]


def decorate_role(row):
    if not row:
        return None
    permissions = normalize_permissions(row.get("permissions"))
    if row.get("role_key") in {"owner", "admin"}:
        permissions = list(ALL_PERMISSION_KEYS)
    role = {
        "id": row.get("id"),
        "key": row.get("role_key"),
        "role_key": row.get("role_key"),
        "name": row.get("name"),
        "description": row.get("description") or row.get("scope") or "",
        "scope": row.get("scope") or row.get("description") or "",
        "role_type": row.get("role_type") or "custom",
        "locked": bool(row.get("locked")),
        "permissions": permissions,
        "permissions_text": ", ".join(
            item["label"] for item in PERMISSION_CATALOG if item["key"] in permissions
        ) or "No permissions selected",
        "is_system": (row.get("role_type") or "") == "system",
    }
    return role


def get_roles(tenant_id=1, include_owner=True):
    rows = fetch_all(
        """SELECT id, role_key, name, description, role_type, locked, scope, permissions
        FROM team_roles WHERE tenant_id = ? ORDER BY sort_order, id""",
        (tenant_id,),
    )
    roles = [decorate_role(row) for row in rows]
    if not include_owner:
        roles = [role for role in roles if role["key"] != "owner"]
    return roles


def get_role(role_key, tenant_id=1):
    row = fetch_one(
        """SELECT id, role_key, name, description, role_type, locked, scope, permissions
        FROM team_roles WHERE tenant_id = ? AND role_key = ?""",
        (tenant_id, role_key),
    )
    return decorate_role(row)


def role_exists(role_key, tenant_id=1):
    return bool(get_role(role_key, tenant_id))


def get_dashboard_users():
    rows = fetch_all(
        """SELECT id, email, name, picture, hosted_domain, permission_group, created_at, last_login_at
        FROM dashboard_users ORDER BY created_at, id"""
    )
    for row in rows:
        row["permission_label"] = permission_group_label(row.get("permission_group"))
        row["is_owner"] = row.get("permission_group") == "owner"
    return rows


def get_dashboard_user_by_id(user_id):
    if not user_id:
        return None
    user = fetch_one(
        """SELECT id, email, name, picture, hosted_domain, permission_group, created_at, last_login_at
        FROM dashboard_users WHERE id = ?""",
        (user_id,),
    )
    if user:
        user["permission_label"] = permission_group_label(user.get("permission_group"))
        user["is_owner"] = user.get("permission_group") == "owner"
    return user


def update_dashboard_user_permission_group(user_id, permission_group):
    if not role_exists(permission_group):
        raise ValueError("Choose a valid permission group.")
    with get_connection() as connection:
        cursor = connection.execute(
            "UPDATE dashboard_users SET permission_group = ? WHERE id = ?",
            (permission_group, user_id),
        )
        connection.commit()
        if cursor.rowcount == 0:
            return None
    return get_dashboard_user_by_id(user_id)


def update_team_member_permission_group(member_id, permission_group, tenant_id=1):
    if not role_exists(permission_group, tenant_id):
        raise ValueError("Choose a valid permission group.")
    with get_connection() as connection:
        cursor = connection.execute(
            "UPDATE team_members SET permission_group = ? WHERE id = ? AND tenant_id = ?",
            (permission_group, member_id, tenant_id),
        )
        connection.commit()
        if cursor.rowcount == 0:
            return None
    return fetch_one("SELECT * FROM team_members WHERE id = ? AND tenant_id = ?", (member_id, tenant_id))


def create_role(data, tenant_id=1):
    name = (data.get("name") or "").strip()
    if not name:
        raise ValueError("Enter a role name.")
    role_key = normalize_role_key(data.get("role_key") or name)
    if not role_key:
        raise ValueError("Enter a valid role name.")
    if role_key in {"owner", "admin"}:
        raise ValueError("Owner and Admin are protected system roles.")
    if role_exists(role_key, tenant_id):
        raise ValueError("A role with that name already exists.")
    permissions = normalize_permissions(data.get("permissions"))
    with get_connection() as connection:
        cursor = connection.execute(
            """INSERT INTO team_roles
            (tenant_id, role_key, name, description, role_type, locked, count, scope, permissions, sort_order)
            VALUES (?, ?, ?, ?, 'custom', 0, 0, ?, ?,
            (SELECT COALESCE(MAX(sort_order), 0) + 1 FROM team_roles WHERE tenant_id = ?))""",
            (
                tenant_id,
                role_key,
                name,
                (data.get("description") or data.get("scope") or "").strip(),
                (data.get("scope") or data.get("description") or "Custom workspace access").strip(),
                json.dumps(permissions),
                tenant_id,
            ),
        )
        connection.commit()
    return get_role(role_key, tenant_id)


def update_role(role_key, data, tenant_id=1):
    role = get_role(role_key, tenant_id)
    if not role:
        return None, "missing"
    if role["locked"]:
        return None, "locked"
    name = (data.get("name") or role["name"]).strip()
    if not name:
        raise ValueError("Enter a role name.")
    permissions = normalize_permissions(data.get("permissions"))
    with get_connection() as connection:
        connection.execute(
            """UPDATE team_roles
            SET name = ?, description = ?, scope = ?, permissions = ?
            WHERE tenant_id = ? AND role_key = ?""",
            (
                name,
                (data.get("description") or data.get("scope") or role["description"]).strip(),
                (data.get("scope") or data.get("description") or role["scope"]).strip(),
                json.dumps(permissions),
                tenant_id,
                role_key,
            ),
        )
        connection.commit()
    return get_role(role_key, tenant_id), None


def delete_role(role_key, tenant_id=1):
    role = get_role(role_key, tenant_id)
    if not role:
        return "missing"
    if role["locked"]:
        return "locked"
    with get_connection() as connection:
        connection.execute(
            "UPDATE dashboard_users SET permission_group = 'viewer' WHERE tenant_id = ? AND permission_group = ?",
            (tenant_id, role_key),
        )
        connection.execute(
            "UPDATE team_members SET permission_group = 'viewer' WHERE tenant_id = ? AND permission_group = ?",
            (tenant_id, role_key),
        )
        connection.execute("DELETE FROM team_roles WHERE tenant_id = ? AND role_key = ?", (tenant_id, role_key))
        connection.commit()
    return "deleted"


def get_subscription_plans():
    plans = fetch_all(
        """SELECT plan_key, name, monthly_price, yearly_price, conversation_limit,
        ai_message_limit, seat_limit, support_level, features, sort_order
        FROM subscription_plans ORDER BY sort_order"""
    )
    for plan in plans:
        plan["features_list"] = [item.strip() for item in plan["features"].split(",") if item.strip()]
    return plans


def get_subscription_plan(plan_key):
    plan = fetch_one(
        """SELECT plan_key, name, monthly_price, yearly_price, conversation_limit,
        ai_message_limit, seat_limit, support_level, features
        FROM subscription_plans WHERE plan_key = ?""",
        (plan_key,),
    )
    if plan:
        plan["features_list"] = [item.strip() for item in plan["features"].split(",") if item.strip()]
    return plan


def get_or_create_onboarding_session(user_id):
    session = fetch_one("SELECT * FROM onboarding_sessions WHERE user_id = ?", (user_id,))
    if session:
        return decorate_onboarding_session(session)
    user = get_dashboard_user(user_id) or {}
    with get_connection() as connection:
        connection.execute(
            """INSERT INTO onboarding_sessions (user_id, company_email)
            VALUES (?, ?)""",
            (user_id, user.get("email") or ""),
        )
        connection.commit()
    return decorate_onboarding_session(fetch_one("SELECT * FROM onboarding_sessions WHERE user_id = ?", (user_id,)))


def decorate_onboarding_session(session):
    if not session:
        return None
    session["email_verified"] = bool(session.get("email_verified"))
    session["whatsapp_verified"] = bool(session.get("whatsapp_verified"))
    session["is_complete"] = bool(session.get("completed_at"))
    session["selected_plan_detail"] = get_subscription_plan(session.get("selected_plan") or "growth")
    return session


def update_onboarding_account(user_id, data):
    with get_connection() as connection:
        connection.execute(
            """UPDATE dashboard_users SET name = ?, email = ?
            WHERE id = ?""",
            (data["name"], data["email"], user_id),
        )
        connection.execute(
            """INSERT INTO onboarding_sessions (user_id, company_email, current_step)
            VALUES (?, ?, 'company')
            ON CONFLICT(user_id) DO UPDATE SET
                company_email = excluded.company_email,
                current_step = 'company',
                updated_at = CURRENT_TIMESTAMP""",
            (user_id, data["email"]),
        )
        connection.commit()
    return get_or_create_onboarding_session(user_id)


def update_onboarding_company(user_id, data):
    with get_connection() as connection:
        connection.execute(
            """INSERT INTO onboarding_sessions
            (user_id, company_name, industry, timezone, language, company_email, company_phone, current_step)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'verify_email')
            ON CONFLICT(user_id) DO UPDATE SET
                company_name = excluded.company_name,
                industry = excluded.industry,
                timezone = excluded.timezone,
                language = excluded.language,
                company_email = excluded.company_email,
                company_phone = excluded.company_phone,
                current_step = 'verify_email',
                updated_at = CURRENT_TIMESTAMP""",
            (
                user_id,
                data["company_name"],
                data["industry"],
                data["timezone"],
                data["language"],
                data["company_email"],
                data["company_phone"],
            ),
        )
        connection.commit()
    return get_or_create_onboarding_session(user_id)


def save_verification_code(user_id, channel, destination, code_hash, expires_at, purpose="onboarding"):
    with get_connection() as connection:
        connection.execute(
            """INSERT INTO verification_codes
            (user_id, channel, destination, code_hash, purpose, expires_at)
            VALUES (?, ?, ?, ?, ?, ?)""",
            (user_id, channel, destination, code_hash, purpose, expires_at),
        )
        connection.commit()
    return fetch_one(
        """SELECT * FROM verification_codes
        WHERE user_id = ? AND channel = ? AND purpose = ?
        ORDER BY id DESC LIMIT 1""",
        (user_id, channel, purpose),
    )


def get_latest_verification_code(user_id, channel, purpose="onboarding"):
    return fetch_one(
        """SELECT * FROM verification_codes
        WHERE user_id = ? AND channel = ? AND purpose = ?
        ORDER BY id DESC LIMIT 1""",
        (user_id, channel, purpose),
    )


def increment_verification_attempt(code_id):
    with get_connection() as connection:
        connection.execute("UPDATE verification_codes SET attempts = attempts + 1 WHERE id = ?", (code_id,))
        connection.commit()


def mark_onboarding_channel_verified(user_id, channel):
    field = "email_verified" if channel == "email" else "whatsapp_verified"
    next_step = "verify_whatsapp" if channel == "email" else "plan"
    with get_connection() as connection:
        connection.execute("UPDATE verification_codes SET verified_at = CURRENT_TIMESTAMP WHERE user_id = ? AND channel = ? AND purpose = 'onboarding'", (user_id, channel))
        connection.execute(
            f"""UPDATE onboarding_sessions
            SET {field} = 1, current_step = ?, updated_at = CURRENT_TIMESTAMP
            WHERE user_id = ?""",
            (next_step, user_id),
        )
        connection.commit()
    return get_or_create_onboarding_session(user_id)


def update_onboarding_plan(user_id, plan_key, billing_cycle):
    if billing_cycle not in {"monthly", "yearly"}:
        raise ValueError("Choose monthly or yearly billing.")
    if not get_subscription_plan(plan_key):
        raise ValueError("Choose a valid plan.")
    with get_connection() as connection:
        connection.execute(
            """UPDATE onboarding_sessions
            SET selected_plan = ?, billing_cycle = ?, current_step = 'review', updated_at = CURRENT_TIMESTAMP
            WHERE user_id = ?""",
            (plan_key, billing_cycle, user_id),
        )
        connection.commit()
    return get_or_create_onboarding_session(user_id)


def complete_onboarding(user_id):
    session = get_or_create_onboarding_session(user_id)
    if not session:
        raise ValueError("Start onboarding before creating a workspace.")
    required = ["company_name", "industry", "timezone", "language", "company_email", "company_phone"]
    missing = [field for field in required if not str(session.get(field) or "").strip()]
    if missing:
        raise ValueError("Complete the company profile before creating the workspace.")
    if not session.get("email_verified") or not session.get("whatsapp_verified"):
        raise ValueError("Verify both email and WhatsApp before creating the workspace.")
    existing_owner = fetch_one(
        """SELECT id FROM dashboard_users
        WHERE tenant_id = 1 AND permission_group = 'owner' AND id != ?""",
        (user_id,),
    )
    if existing_owner:
        return None, "owner_conflict"
    with get_connection() as connection:
        connection.execute(
            """UPDATE tenants
            SET name = ?, industry = ?, timezone = ?, language = ?,
                owner_user_id = ?, subscription_plan = ?, billing_cycle = ?,
                company_email = ?, company_phone = ?, onboarding_status = 'complete'
            WHERE id = 1""",
            (
                session["company_name"],
                session["industry"],
                session["timezone"],
                session["language"],
                user_id,
                session["selected_plan"],
                session["billing_cycle"],
                session["company_email"],
                session["company_phone"],
            ),
        )
        connection.execute(
            """UPDATE dashboard_users
            SET tenant_id = 1, permission_group = 'owner', onboarding_complete = 1
            WHERE id = ?""",
            (user_id,),
        )
        connection.execute(
            """UPDATE onboarding_sessions
            SET completed_at = CURRENT_TIMESTAMP, current_step = 'complete', updated_at = CURRENT_TIMESTAMP
            WHERE user_id = ?""",
            (user_id,),
        )
        connection.commit()
    return get_or_create_onboarding_session(user_id), None


def update_dashboard_user_preferences(user_id, preferences):
    allowed = {
        "console_theme": {"auto", "light", "dark"},
        "console_density": {"comfortable", "compact"},
        "accent_color": {"teal", "blue", "green", "violet"},
        "default_sidebar": {"expanded", "collapsed"},
    }
    clean = {}
    for key, values in allowed.items():
        value = str(preferences.get(key, "")).strip().lower()
        if value not in values:
            raise ValueError(f"Unsupported {key}.")
        clean[key] = value
    with get_connection() as connection:
        connection.execute(
            """UPDATE dashboard_users
            SET console_theme = ?, console_density = ?, accent_color = ?, default_sidebar = ?
            WHERE id = ?""",
            (
                clean["console_theme"],
                clean["console_density"],
                clean["accent_color"],
                clean["default_sidebar"],
                user_id,
            ),
        )
        connection.commit()
    return get_dashboard_user(user_id)


def export_rows_csv(headers, rows):
    import csv
    import io

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(headers)
    writer.writerows(rows)
    return output.getvalue()


def create_customer(data, tenant_id=1):
    with get_connection() as connection:
        cursor = connection.execute(
            """INSERT INTO customers
            (tenant_id, name, phone, segment, stage, last_seen, csat, health, sort_order)
            VALUES (?, ?, ?, ?, ?, 'Just now', ?, ?, (SELECT COALESCE(MAX(sort_order), 0) + 1 FROM customers WHERE tenant_id = ?))""",
            (
                tenant_id,
                data["name"],
                data["phone"],
                data.get("segment") or "General",
                data.get("stage") or "New lead",
                data.get("csat") or "N/A",
                data.get("health") or "Neutral",
                tenant_id,
            ),
        )
        customer_id = cursor.lastrowid
        connection.execute(
            """INSERT INTO customer_timeline (tenant_id, title, customer, time, status, sort_order)
            VALUES (?, 'Customer added', ?, 'Just now', 'Open',
            (SELECT COALESCE(MAX(sort_order), 0) + 1 FROM customer_timeline WHERE tenant_id = ?))""",
            (tenant_id, data["name"], tenant_id),
        )
        connection.commit()
    return fetch_one("SELECT * FROM customers WHERE id = ? AND tenant_id = ?", (customer_id, tenant_id))


def update_customer(customer_id, data, tenant_id=1):
    with get_connection() as connection:
        cursor = connection.execute(
            """UPDATE customers SET name = ?, phone = ?, segment = ?, stage = ?, csat = ?, health = ?,
            last_seen = 'Just now' WHERE id = ? AND tenant_id = ?""",
            (
                data["name"],
                data["phone"],
                data.get("segment") or "General",
                data.get("stage") or "New lead",
                data.get("csat") or "N/A",
                data.get("health") or "Neutral",
                customer_id,
                tenant_id,
            ),
        )
        connection.commit()
        if cursor.rowcount == 0:
            return None
    return fetch_one("SELECT * FROM customers WHERE id = ? AND tenant_id = ?", (customer_id, tenant_id))


def create_or_update_team_member(data, member_id=None, tenant_id=1):
    permission_group = data.get("permission_group") or "agent"
    if permission_group not in PERMISSION_GROUP_MAP:
        raise ValueError("Choose a valid permission group.")
    with get_connection() as connection:
        if member_id:
            cursor = connection.execute(
                """UPDATE team_members SET name = ?, email = ?, permission_group = ?, role = ?, team = ?, status = ?, assigned = ?, resolved = ?, csat = ?
                WHERE id = ? AND tenant_id = ?""",
                (
                    data["name"],
                    data.get("email") or "",
                    permission_group,
                    data.get("role") or "Agent",
                    data.get("team") or "Support Desk",
                    data.get("status") or "Invited",
                    int(data.get("assigned") or 0),
                    int(data.get("resolved") or 0),
                    data.get("csat") or "N/A",
                    member_id,
                    tenant_id,
                ),
            )
            if cursor.rowcount == 0:
                connection.commit()
                return None
        else:
            cursor = connection.execute(
                """INSERT INTO team_members
                (tenant_id, name, email, permission_group, role, team, status, assigned, resolved, csat, sort_order)
                VALUES (?, ?, ?, ?, ?, ?, ?, 0, 0, 'N/A',
                (SELECT COALESCE(MAX(sort_order), 0) + 1 FROM team_members WHERE tenant_id = ?))""",
                (
                    tenant_id,
                    data["name"],
                    data.get("email") or "",
                    permission_group,
                    data.get("role") or "Agent",
                    data.get("team") or "Support Desk",
                    data.get("status") or "Invited",
                    tenant_id,
                ),
            )
            member_id = cursor.lastrowid
        connection.commit()
    return fetch_one("SELECT * FROM team_members WHERE id = ? AND tenant_id = ?", (member_id, tenant_id))


def add_team_role(data, tenant_id=1):
    with get_connection() as connection:
        cursor = connection.execute(
            """INSERT INTO team_roles (tenant_id, name, count, scope, permissions, sort_order)
            VALUES (?, ?, 0, ?, ?, (SELECT COALESCE(MAX(sort_order), 0) + 1 FROM team_roles WHERE tenant_id = ?))""",
            (tenant_id, data["name"], data.get("scope") or "Custom workspace access", data.get("permissions") or "", tenant_id),
        )
        role_id = cursor.lastrowid
        connection.commit()
    return fetch_one("SELECT * FROM team_roles WHERE id = ? AND tenant_id = ?", (role_id, tenant_id))


def create_conversation_thread(data, tenant_id=1):
    with get_connection() as connection:
        cursor = connection.execute(
            """INSERT INTO conversation_threads
            (tenant_id, customer_name, phone, intent, module, handler, status, priority, sentiment, time, last_message, messages, sla, sort_order)
            VALUES (?, ?, ?, ?, ?, 'AI', 'Active', ?, 'Neutral', 'Just now', ?, 1, '10m',
            (SELECT COALESCE(MAX(sort_order), 0) + 1 FROM conversation_threads WHERE tenant_id = ?))""",
            (
                tenant_id,
                data["customer_name"],
                data["phone"],
                data.get("intent") or "General enquiry",
                data.get("module") or "Support",
                data.get("priority") or "Normal",
                data.get("message") or "New conversation started.",
                tenant_id,
            ),
        )
        thread_id = cursor.lastrowid
        connection.execute(
            """INSERT INTO conversation_messages (thread_id, tenant_id, sender, role, body, sort_order)
            VALUES (?, ?, ?, 'customer', ?, 1)""",
            (thread_id, tenant_id, data["customer_name"], data.get("message") or "New conversation started."),
        )
        connection.commit()
    return get_conversation_thread(thread_id, tenant_id)


def get_conversation_thread(thread_id, tenant_id=1):
    thread = fetch_one("SELECT * FROM conversation_threads WHERE id = ? AND tenant_id = ?", (thread_id, tenant_id))
    if not thread:
        return None
    conversation_row_decorated(thread)
    messages = fetch_all(
        """SELECT id, sender, role, body, created_at FROM conversation_messages
        WHERE thread_id = ? AND tenant_id = ? ORDER BY sort_order, id""",
        (thread_id, tenant_id),
    )
    if not messages:
        messages = [
            {"sender": "Customer", "role": "customer", "body": thread["last_message"], "created_at": ""},
            {"sender": "AI Assistant", "role": "assistant", "body": "I am reviewing the latest context and will respond with the next best action.", "created_at": ""},
        ]
    thread["messages_list"] = messages
    thread["ai_decision"] = get_ai_escalation_decision(thread_id, tenant_id)
    return thread


def record_audit_event(event, user="System", status="Done", tenant_id=1, ip="local"):
    with get_connection() as connection:
        connection.execute(
            """INSERT INTO audit_logs (tenant_id, event, user, ip, time, status, sort_order)
            VALUES (?, ?, ?, ?, 'Just now', ?,
            (SELECT COALESCE(MAX(sort_order), 0) + 1 FROM audit_logs WHERE tenant_id = ?))""",
            (tenant_id, event, user, ip, status, tenant_id),
        )
        connection.commit()


def get_ai_escalation_decision(thread_id, tenant_id=1):
    decision = fetch_one(
        """SELECT id, thread_id, decision, confidence, reason, suggested_action,
        risk_flags, model, mode, created_at, updated_at
        FROM ai_escalation_decisions
        WHERE thread_id = ? AND tenant_id = ?""",
        (thread_id, tenant_id),
    )
    if not decision:
        return None
    try:
        decision["risk_flags"] = json.loads(decision.get("risk_flags") or "[]")
    except json.JSONDecodeError:
        decision["risk_flags"] = []
    return decision


def save_ai_escalation_decision(thread_id, decision, tenant_id=1):
    risk_flags = decision.get("risk_flags") or []
    if isinstance(risk_flags, str):
        risk_flags = [risk_flags]
    payload = {
        "decision": "escalate" if decision.get("decision") == "escalate" else "continue",
        "confidence": max(0, min(100, int(decision.get("confidence") or 0))),
        "reason": str(decision.get("reason") or "No reason provided.").strip(),
        "suggested_action": str(decision.get("suggested_action") or "Review the conversation and continue with care.").strip(),
        "risk_flags": json.dumps([str(flag).strip() for flag in risk_flags if str(flag).strip()]),
        "model": str(decision.get("model") or "Rule fallback").strip(),
        "mode": "auto" if decision.get("mode") == "auto" else "recommend",
    }
    with get_connection() as connection:
        connection.execute(
            """INSERT INTO ai_escalation_decisions
            (thread_id, tenant_id, decision, confidence, reason, suggested_action, risk_flags, model, mode)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(thread_id, tenant_id) DO UPDATE SET
                decision = excluded.decision,
                confidence = excluded.confidence,
                reason = excluded.reason,
                suggested_action = excluded.suggested_action,
                risk_flags = excluded.risk_flags,
                model = excluded.model,
                mode = excluded.mode,
                updated_at = CURRENT_TIMESTAMP""",
            (
                thread_id,
                tenant_id,
                payload["decision"],
                payload["confidence"],
                payload["reason"],
                payload["suggested_action"],
                payload["risk_flags"],
                payload["model"],
                payload["mode"],
            ),
        )
        connection.commit()
    return get_ai_escalation_decision(thread_id, tenant_id)


def add_conversation_message(thread_id, body, sender="Workspace Admin", role="agent", tenant_id=1):
    with get_connection() as connection:
        thread = connection.execute("SELECT * FROM conversation_threads WHERE id = ? AND tenant_id = ?", (thread_id, tenant_id)).fetchone()
        if not thread:
            return None
        sort_order = connection.execute(
            "SELECT COALESCE(MAX(sort_order), 0) + 1 FROM conversation_messages WHERE thread_id = ? AND tenant_id = ?",
            (thread_id, tenant_id),
        ).fetchone()[0]
        cursor = connection.execute(
            """INSERT INTO conversation_messages (thread_id, tenant_id, sender, role, body, sort_order)
            VALUES (?, ?, ?, ?, ?, ?)""",
            (thread_id, tenant_id, sender, role, body, sort_order),
        )
        connection.execute(
            """UPDATE conversation_threads SET last_message = ?, messages = messages + 1, time = 'Just now',
            handler = CASE WHEN ? = 'agent' THEN 'Human' ELSE handler END
            WHERE id = ? AND tenant_id = ?""",
            (body, role, thread_id, tenant_id),
        )
        connection.commit()
    return fetch_one("SELECT id, sender, role, body, created_at FROM conversation_messages WHERE id = ?", (cursor.lastrowid,))


def assign_conversation_thread(thread_id, owner, tenant_id=1, assigned_user_id=None, assigned_user_name=""):
    with get_connection() as connection:
        cursor = connection.execute(
            """UPDATE conversation_threads
            SET handler = 'Human',
                status = 'Escalated',
                sla = 'Assigned',
                time = 'Just now',
                assigned_team = ?,
                assigned_user_id = ?,
                assigned_user_name = ?,
                assigned_at = CURRENT_TIMESTAMP
            WHERE id = ? AND tenant_id = ?""",
            (owner, assigned_user_id, assigned_user_name, thread_id, tenant_id),
        )
        connection.commit()
    return get_conversation_thread(thread_id, tenant_id) if cursor.rowcount else None


def update_conversation_thread_status(thread_id, status, tenant_id=1):
    if status not in {"Active", "Waiting", "Escalated", "Resolved"}:
        raise ValueError("Unsupported status.")
    with get_connection() as connection:
        cursor = connection.execute(
            """UPDATE conversation_threads
            SET status = ?,
                handler = CASE WHEN ? = 'Escalated' THEN 'Human' WHEN ? = 'Active' THEN 'AI' ELSE handler END,
                sla = CASE WHEN ? = 'Resolved' THEN 'Resolved' WHEN ? = 'Active' AND sla = 'Resolved' THEN '10m' ELSE sla END,
                resolved_at = CASE WHEN ? = 'Resolved' THEN CURRENT_TIMESTAMP WHEN ? = 'Active' THEN '' ELSE resolved_at END,
                time = 'Just now'
            WHERE id = ? AND tenant_id = ?""",
            (status, status, status, status, status, status, status, thread_id, tenant_id),
        )
        connection.commit()
    return get_conversation_thread(thread_id, tenant_id) if cursor.rowcount else None


def add_support_ticket(data, tenant_id=1):
    with get_connection() as connection:
        next_id = connection.execute("SELECT COALESCE(MAX(id), 0) + 1 FROM support_tickets").fetchone()[0]
        ticket_id = f"PP-{next_id:04d}"
        cursor = connection.execute(
            """INSERT INTO support_tickets
            (tenant_id, ticket_id, subject, priority, owner, status, updated, request_type, description, attachment, created_at, sort_order)
            VALUES (?, ?, ?, ?, 'Support Desk', 'Open', 'Just now', ?, ?, ?, CURRENT_TIMESTAMP,
            (SELECT COALESCE(MAX(sort_order), 0) + 1 FROM support_tickets WHERE tenant_id = ?))""",
            (
                tenant_id,
                ticket_id,
                data["subject"],
                data.get("priority") or "Normal",
                data.get("request_type") or "Technical support",
                data.get("description") or "",
                data.get("attachment") or "",
                tenant_id,
            ),
        )
        connection.commit()
    return fetch_one("SELECT * FROM support_tickets WHERE id = ?", (cursor.lastrowid,))


def toggle_security_access_rule(rule_id, enabled, tenant_id=1):
    with get_connection() as connection:
        cursor = connection.execute(
            "UPDATE security_access_rules SET enabled = ? WHERE id = ? AND tenant_id = ?",
            (int(bool(enabled)), rule_id, tenant_id),
        )
        connection.commit()
    return cursor.rowcount > 0


def save_security_settings(data, tenant_id=1):
    with get_connection() as connection:
        connection.execute(
            """UPDATE workspace_settings SET require_2fa = ?, mask_phone_numbers = ?, retention_period = ?,
            audit_export = ?, updated_at = CURRENT_TIMESTAMP WHERE tenant_id = ?""",
            (
                int(bool(data.get("require_2fa", True))),
                int(bool(data.get("mask_phone_numbers", True))),
                data.get("retention_period") or "180 days",
                data.get("audit_export") or "Monthly CSV",
                tenant_id,
            ),
        )
        connection.commit()
    return fetch_one("SELECT * FROM workspace_settings WHERE tenant_id = ?", (tenant_id,))


def save_workspace_settings(section, data, tenant_id=1):
    with get_connection() as connection:
        if section == "workspace":
            connection.execute(
                "UPDATE tenants SET name = ?, industry = ?, timezone = ?, language = ? WHERE id = ?",
                (data["company_name"], data["industry"], data["timezone"], data["language"], tenant_id),
            )
        elif section == "whatsapp":
            connection.execute(
                "UPDATE workspace_settings SET webhook_url = ?, message_window_policy = ?, updated_at = CURRENT_TIMESTAMP WHERE tenant_id = ?",
                (data["webhook_url"], data["message_window_policy"], tenant_id),
            )
        elif section == "handoff":
            mode = "auto" if data.get("escalation_decision_mode") == "auto" else "recommend"
            connection.execute(
                """UPDATE workspace_settings SET default_handoff_team = ?, sla_target = ?,
                handoff_low_confidence = ?, handoff_negative_sentiment = ?,
                escalation_decision_mode = ?, updated_at = CURRENT_TIMESTAMP
                WHERE tenant_id = ?""",
                (
                    data["default_handoff_team"],
                    data["sla_target"],
                    int(bool(data.get("handoff_low_confidence", True))),
                    int(bool(data.get("handoff_negative_sentiment", True))),
                    mode,
                    tenant_id,
                ),
            )
        elif section == "ai_behavior":
            connection.execute(
                """UPDATE workspace_settings SET kb_grounding = ?, intent_detection = ?,
                updated_at = CURRENT_TIMESTAMP WHERE tenant_id = ?""",
                (
                    int(bool(data.get("kb_grounding", True))),
                    int(bool(data.get("intent_detection", True))),
                    tenant_id,
                ),
            )
        elif section == "notifications":
            connection.execute(
                """UPDATE workspace_settings SET daily_digest = ?, escalation_alerts = ?, kb_failure_alerts = ?,
                updated_at = CURRENT_TIMESTAMP WHERE tenant_id = ?""",
                (
                    int(bool(data.get("daily_digest", True))),
                    int(bool(data.get("escalation_alerts", True))),
                    int(bool(data.get("kb_failure_alerts", True))),
                    tenant_id,
                ),
            )
        else:
            raise ValueError("Unsupported settings section.")
        connection.commit()
    return fetch_one("SELECT * FROM workspace_settings WHERE tenant_id = ?", (tenant_id,))


def toggle_settings_module(module_id, enabled, tenant_id=1):
    with get_connection() as connection:
        cursor = connection.execute(
            "UPDATE settings_modules SET enabled = ? WHERE id = ? AND tenant_id = ?",
            (int(bool(enabled)), module_id, tenant_id),
        )
        connection.commit()
    return cursor.rowcount > 0


def toggle_billing_addon(addon_id, enabled, tenant_id=1):
    with get_connection() as connection:
        cursor = connection.execute(
            "UPDATE billing_addons SET enabled = ? WHERE id = ? AND tenant_id = ?",
            (int(bool(enabled)), addon_id, tenant_id),
        )
        connection.commit()
    return cursor.rowcount > 0


def toggle_addon_cart(addon_id, selected, tenant_id=1):
    with get_connection() as connection:
        module = connection.execute("SELECT id, status FROM addon_modules WHERE id = ? AND tenant_id = ?", (addon_id, tenant_id)).fetchone()
        if not module:
            return None
        if selected:
            connection.execute("INSERT OR IGNORE INTO addon_cart (tenant_id, addon_module_id) VALUES (?, ?)", (tenant_id, addon_id))
        else:
            connection.execute("DELETE FROM addon_cart WHERE tenant_id = ? AND addon_module_id = ?", (tenant_id, addon_id))
        connection.commit()
    return fetch_one("SELECT * FROM addon_modules WHERE id = ? AND tenant_id = ?", (addon_id, tenant_id))


def purchase_addon_cart(tenant_id=1, owner="Workspace Admin"):
    with get_connection() as connection:
        rows = connection.execute(
            """SELECT addon_module_id FROM addon_cart WHERE tenant_id = ?""",
            (tenant_id,),
        ).fetchall()
        installed = []
        for row in rows:
            addon_id = row["addon_module_id"]
            connection.execute("UPDATE addon_modules SET status = 'Installed' WHERE id = ? AND tenant_id = ?", (addon_id, tenant_id))
            connection.execute(
                """INSERT OR IGNORE INTO tenant_addons (tenant_id, addon_module_id, owner, renewal, usage, sort_order)
                VALUES (?, ?, ?, 'Next cycle', 'Active',
                (SELECT COALESCE(MAX(sort_order), 0) + 1 FROM tenant_addons WHERE tenant_id = ?))""",
                (tenant_id, addon_id, owner, tenant_id),
            )
            installed.append(addon_id)
        connection.execute("DELETE FROM addon_cart WHERE tenant_id = ?", (tenant_id,))
        connection.commit()
    return installed


def save_assistant_connection(user_id, config):
    with get_connection() as connection:
        connection.execute(
            """INSERT INTO assistant_connections (user_id, provider, provider_label, api_key, api_url, model)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                provider = excluded.provider,
                provider_label = excluded.provider_label,
                api_key = excluded.api_key,
                api_url = excluded.api_url,
                model = excluded.model,
                updated_at = CURRENT_TIMESTAMP""",
            (user_id, config["provider"], config["provider_label"], config["api_key"], config["api_url"], config["model"]),
        )
        connection.commit()


def get_assistant_connection(user_id, include_key=False):
    columns = "provider, provider_label, api_url, model, updated_at"
    if include_key:
        columns = f"{columns}, api_key"
    return fetch_one(f"SELECT {columns} FROM assistant_connections WHERE user_id = ?", (user_id,))
