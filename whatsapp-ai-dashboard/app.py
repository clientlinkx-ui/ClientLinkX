from flask import Flask, render_template

app = Flask(__name__)


dashboard_data = {
    "page_title": "Customer Dashboard",
    "page_subtitle": "WhatsApp AI operations, service quality, and business outcomes.",
    "stats": [
        {
            "title": "Total Conversations",
            "value": "18,420",
            "change": "+12.8%",
            "trend": "up",
            "icon": "fa-solid fa-comments",
        },
        {
            "title": "Escalations",
            "value": "312",
            "change": "-7.4%",
            "trend": "down",
            "icon": "fa-solid fa-headset",
        },
        {
            "title": "Customer Satisfaction",
            "value": "94.2%",
            "change": "+3.1%",
            "trend": "up",
            "icon": "fa-solid fa-face-smile",
        },
        {
            "title": "Automation Rate",
            "value": "87.6%",
            "change": "+5.6%",
            "trend": "up",
            "icon": "fa-solid fa-bolt",
        },
    ],
    "conversations": [
        {
            "customer_name": "Priya Nair",
            "avatar": None,
            "time": "2m ago",
            "last_message": "Asked for delivery ETA on order #CLX-2918.",
            "handler": "AI",
            "status": "Active",
            "unread": 2,
        },
        {
            "customer_name": "Arjun Mehta",
            "avatar": None,
            "time": "8m ago",
            "last_message": "Requested course fee details and scholarship options.",
            "handler": "AI",
            "status": "Waiting",
            "unread": 1,
        },
        {
            "customer_name": "Maya Kapoor",
            "avatar": None,
            "time": "18m ago",
            "last_message": "Booking moved to Saturday at 4:30 PM.",
            "handler": "Human",
            "status": "Resolved",
            "unread": 0,
        },
        {
            "customer_name": "Rahul Shah",
            "avatar": None,
            "time": "31m ago",
            "last_message": "Lead qualified for enterprise pricing follow-up.",
            "handler": "AI",
            "status": "Active",
            "unread": 4,
        },
    ],
    "activities": [
        {
            "title": "Escalation assigned",
            "description": "High-intent lead routed to Sales Team A.",
            "activity_type": "Escalation",
            "icon": "fa-solid fa-arrow-up-right-dots",
            "time": "5m ago",
            "user": "Anita",
            "status": "Open",
        },
        {
            "title": "Knowledge base synced",
            "description": "18 product policy pages refreshed successfully.",
            "activity_type": "Sync",
            "icon": "fa-solid fa-arrows-rotate",
            "time": "22m ago",
            "user": "System",
            "status": "Done",
        },
        {
            "title": "Prompt version deployed",
            "description": "Admissions flow updated to version 3.4.",
            "activity_type": "AI",
            "icon": "fa-solid fa-robot",
            "time": "1h ago",
            "user": "Rohan",
            "status": "Live",
        },
    ],
    "performance": [
        {
            "title": "First Response Time",
            "subtitle": "Median across WhatsApp threads",
            "icon": "fa-solid fa-stopwatch",
            "value": "4.8",
            "unit": "sec",
            "progress": 92,
            "status": "excellent",
            "change": "1.7 sec faster",
        },
        {
            "title": "Resolution Rate",
            "subtitle": "Solved without human handoff",
            "icon": "fa-solid fa-circle-check",
            "value": "82.4",
            "unit": "%",
            "progress": 82,
            "status": "good",
            "change": "+4.2 this week",
        },
        {
            "title": "Fallback Rate",
            "subtitle": "Messages needing clarification",
            "icon": "fa-solid fa-triangle-exclamation",
            "value": "5.9",
            "unit": "%",
            "progress": 34,
            "status": "warning",
            "change": "Review top intents",
        },
    ],
    "modules": [
        {"name": "Sales", "value": "1,248", "label": "qualified leads", "progress": 78, "icon": "fa-solid fa-chart-line"},
        {"name": "Admissions", "value": "426", "label": "applications started", "progress": 64, "icon": "fa-solid fa-graduation-cap"},
        {"name": "Appointments", "value": "689", "label": "bookings created", "progress": 71, "icon": "fa-solid fa-calendar-check"},
        {"name": "Orders", "value": "2,914", "label": "order queries handled", "progress": 86, "icon": "fa-solid fa-box"},
    ],
    "escalations": [
        {"team": "Sales Team A", "count": 44, "sla": "12m", "tone": "warning"},
        {"team": "Support Desk", "count": 29, "sla": "8m", "tone": "good"},
        {"team": "Admissions", "count": 18, "sla": "15m", "tone": "warning"},
        {"team": "Billing", "count": 7, "sla": "5m", "tone": "good"},
    ],
}

conversation_rows = [
    {
        "customer_name": "Priya Nair",
        "phone": "+91 98201 11842",
        "intent": "Order status",
        "module": "Orders",
        "handler": "AI",
        "status": "Active",
        "priority": "Normal",
        "sentiment": "Positive",
        "time": "2m ago",
        "last_message": "Can you confirm when my replacement order will arrive?",
        "messages": 14,
        "sla": "4m",
    },
    {
        "customer_name": "Arjun Mehta",
        "phone": "+91 99870 44218",
        "intent": "Admission enquiry",
        "module": "Admissions",
        "handler": "AI",
        "status": "Waiting",
        "priority": "High",
        "sentiment": "Neutral",
        "time": "8m ago",
        "last_message": "Please send the MBA fee structure and scholarship criteria.",
        "messages": 9,
        "sla": "7m",
    },
    {
        "customer_name": "Maya Kapoor",
        "phone": "+91 90044 78218",
        "intent": "Appointment booking",
        "module": "Appointments",
        "handler": "Human",
        "status": "Resolved",
        "priority": "Normal",
        "sentiment": "Positive",
        "time": "18m ago",
        "last_message": "Saturday 4:30 PM works. Please confirm the location.",
        "messages": 18,
        "sla": "Resolved",
    },
    {
        "customer_name": "Rahul Shah",
        "phone": "+91 98199 72101",
        "intent": "Enterprise pricing",
        "module": "Sales",
        "handler": "AI",
        "status": "Active",
        "priority": "High",
        "sentiment": "Positive",
        "time": "31m ago",
        "last_message": "We have 45 agents. Can someone discuss annual pricing?",
        "messages": 22,
        "sla": "3m",
    },
    {
        "customer_name": "Fatima Khan",
        "phone": "+91 98710 50019",
        "intent": "Refund request",
        "module": "Support",
        "handler": "Human",
        "status": "Escalated",
        "priority": "Urgent",
        "sentiment": "Negative",
        "time": "46m ago",
        "last_message": "I have waited a week and still have not received the refund.",
        "messages": 27,
        "sla": "2m",
    },
    {
        "customer_name": "Karan Gill",
        "phone": "+91 98672 19004",
        "intent": "Product availability",
        "module": "Sales",
        "handler": "AI",
        "status": "Resolved",
        "priority": "Normal",
        "sentiment": "Neutral",
        "time": "1h ago",
        "last_message": "Thanks, I will place the order later today.",
        "messages": 11,
        "sla": "Resolved",
    },
]

conversations_data = {
    "page_title": "Conversations",
    "page_subtitle": "Monitor live WhatsApp threads, handoffs, sentiment, SLA, and customer intent.",
    "summary": [
        {"label": "Open Threads", "value": "184", "icon": "fa-solid fa-inbox", "tone": "primary"},
        {"label": "Waiting on Customer", "value": "63", "icon": "fa-solid fa-clock", "tone": "warning"},
        {"label": "Escalated", "value": "28", "icon": "fa-solid fa-headset", "tone": "danger"},
        {"label": "AI Resolved Today", "value": "1,094", "icon": "fa-solid fa-circle-check", "tone": "success"},
    ],
    "threads": conversation_rows,
    "quick_filters": ["All", "Active", "Waiting", "Escalated", "Resolved"],
}

analytics_data = {
    "page_title": "Analytics",
    "page_subtitle": "Understand WhatsApp automation performance, business outcomes, and customer experience trends.",
    "summary": [
        {"label": "Conversations", "value": "18.4k", "change": "+12.8%", "tone": "good"},
        {"label": "Automation Rate", "value": "87.6%", "change": "+5.6%", "tone": "good"},
        {"label": "CSAT", "value": "94.2%", "change": "+3.1%", "tone": "good"},
        {"label": "Escalation Rate", "value": "6.1%", "change": "-1.4%", "tone": "good"},
    ],
    "funnels": [
        {"name": "New WhatsApp contacts", "value": "8,420", "progress": 100},
        {"name": "Intent identified", "value": "7,981", "progress": 95},
        {"name": "Qualified outcome", "value": "5,226", "progress": 62},
        {"name": "Human handoff", "value": "512", "progress": 6},
    ],
    "intents": [
        {"name": "Order status", "count": "4,291", "share": 32},
        {"name": "Admissions enquiry", "count": "2,804", "share": 21},
        {"name": "Appointments", "count": "2,103", "share": 16},
        {"name": "Sales pricing", "count": "1,940", "share": 14},
        {"name": "Refunds", "count": "1,024", "share": 8},
    ],
    "teams": [
        {"name": "Sales Team A", "resolved": 342, "avg_sla": "9m", "csat": "95%"},
        {"name": "Support Desk", "resolved": 516, "avg_sla": "7m", "csat": "92%"},
        {"name": "Admissions", "resolved": 228, "avg_sla": "12m", "csat": "94%"},
        {"name": "Billing", "resolved": 74, "avg_sla": "6m", "csat": "90%"},
    ],
}

settings_data = {
    "page_title": "Settings",
    "page_subtitle": "Manage workspace, WhatsApp, AI, handoff, modules, security, and notifications.",
    "workspace": {
        "company_name": "EverTech Solutions",
        "industry": "Education and ecommerce",
        "timezone": "Asia/Kolkata",
        "language": "English",
    },
    "channels": [
        {"name": "WhatsApp Business API", "status": "Connected", "detail": "+91 98765 43210", "tone": "good"},
        {"name": "Webhook Delivery", "status": "Healthy", "detail": "99.98% success", "tone": "good"},
        {"name": "Template Messages", "status": "Review needed", "detail": "3 pending approvals", "tone": "warning"},
    ],
    "models": [
        {"name": "Support Assistant", "model": "GPT-4.1 Mini", "temperature": "0.3", "status": "Live"},
        {"name": "Lead Qualifier", "model": "GPT-4.1 Mini", "temperature": "0.4", "status": "Live"},
        {"name": "Fallback Classifier", "model": "GPT-4.1 Nano", "temperature": "0.1", "status": "Testing"},
    ],
    "modules": [
        {"name": "Sales", "enabled": True, "owner": "Sales Team A"},
        {"name": "Admissions", "enabled": True, "owner": "Admissions Desk"},
        {"name": "Appointments", "enabled": True, "owner": "Front Office"},
        {"name": "Orders", "enabled": True, "owner": "Support Desk"},
        {"name": "Billing", "enabled": False, "owner": "Finance"},
    ],
}


@app.route('/')
def dashboard():
    return render_template('dashboard.html', active_page='dashboard', **dashboard_data)


@app.route('/conversations')
def conversations():
    return render_template('conversations.html', active_page='conversations', **conversations_data)


@app.route('/analytics')
def analytics():
    return render_template('analytics.html', active_page='analytics', **analytics_data)


@app.route('/settings')
def settings():
    return render_template('settings.html', active_page='settings', **settings_data)

if __name__ == '__main__':
    app.run(debug=True, port=5001)
