import Foundation

struct APIError: LocalizedError, Identifiable {
    let id = UUID()
    let message: String

    var errorDescription: String? { message }
}

struct NativeSession: Decodable {
    let ok: Bool
    let authenticated: Bool
    let onboardingComplete: Bool
    let message: String?
    let nextURL: String?
    let user: NativeUser?
    let permissions: NativePermissions?

    var isWorkspaceReady: Bool {
        authenticated && onboardingComplete && (permissions?.dashboard ?? false)
    }

    enum CodingKeys: String, CodingKey {
        case ok, authenticated, message, user, permissions
        case onboardingComplete = "onboarding_complete"
        case nextURL = "next_url"
    }
}

struct NativeUser: Decodable {
    let id: Int?
    let name: String
    let email: String
    let permissionGroup: String?

    enum CodingKeys: String, CodingKey {
        case id, name, email
        case permissionGroup = "permission_group"
    }
}

struct NativePermissions: Decodable {
    let dashboard: Bool
    let conversations: Bool
    let assistant: Bool
}

struct DashboardEnvelope: Decodable {
    let ok: Bool
    let data: DashboardSnapshot?
    let updatedAt: String?
    let error: String?

    enum CodingKeys: String, CodingKey {
        case ok, data, error
        case updatedAt = "updated_at"
    }
}

struct DashboardSnapshot: Decodable {
    var stats: [StatCard] = []
    var traffic: TrafficData?
    var statusBreakdown: StatusBreakdown?
    var modules: [BusinessModule] = []
    var handoffs: [HandoffQueue] = []
    var recentConversations: [ConversationSummary] = []
    var recentActivity: [ActivityItem] = []
    var runtimeStatus: RuntimeStatus?

    enum CodingKeys: String, CodingKey {
        case stats, traffic, modules, handoffs
        case statusBreakdown = "status_breakdown"
        case recentConversations = "recent_conversations"
        case recentActivity = "recent_activity"
        case runtimeStatus = "runtime_status"
    }
}

struct StatCard: Decodable, Identifiable {
    var id: String { title }
    let title: String
    let value: String
    let change: String?
    let trend: String?
    let icon: String?
}

struct TrafficData: Decodable {
    let labels: [String]
    let ai: [Int]
    let human: [Int]
}

struct StatusBreakdown: Decodable {
    let labels: [String]
    let values: [Int]
}

struct BusinessModule: Decodable, Identifiable {
    var id: String { name }
    let name: String
    let value: String
    let label: String?
    let progress: Double?
}

struct HandoffQueue: Decodable, Identifiable {
    var id: String { team }
    let team: String
    let count: Int
    let sla: String?
    let tone: String?
}

struct RuntimeStatus: Decodable {
    let provider: String
    let model: String
    let description: String?
    let configured: Bool?
    let statusLabel: String?
    let confidence: Int?
    let latency: String?
    let whatsappStatus: String?
    let kbStatus: String?
    let handoffStatus: String?

    enum CodingKeys: String, CodingKey {
        case provider, model, description, configured, confidence, latency
        case statusLabel = "status_label"
        case whatsappStatus = "whatsapp_status"
        case kbStatus = "kb_status"
        case handoffStatus = "handoff_status"
    }
}

struct ActivityItem: Decodable, Identifiable {
    var id: String { "\(title)-\(time ?? "")" }
    let title: String
    let description: String?
    let time: String?
    let user: String?
    let status: String?
}

struct ConversationListEnvelope: Decodable {
    let ok: Bool
    let threads: [ConversationSummary]?
    let selectedThread: ConversationThread?
    let summaryCounts: ConversationCounts?
    let assignees: AssigneePayload?
    let error: String?

    enum CodingKeys: String, CodingKey {
        case ok, threads, assignees, error
        case selectedThread = "selected_thread"
        case summaryCounts = "summary_counts"
    }
}

struct ConversationThreadEnvelope: Decodable {
    let ok: Bool
    let message: String?
    let thread: ConversationThread?
    let decision: AIDecision?
    let error: String?
}

struct ConversationSummary: Decodable, Identifiable {
    let id: Int
    let customerName: String
    let phone: String?
    let intent: String?
    let module: String?
    let handler: String?
    let status: String?
    let priority: String?
    let sentiment: String?
    let time: String?
    let lastMessage: String?
    let messages: Int?
    let sla: String?
    let assignee: String?

    enum CodingKeys: String, CodingKey {
        case id, phone, intent, module, handler, status, priority, sentiment, time, messages, sla, assignee
        case customerName = "customer_name"
        case lastMessage = "last_message"
    }
}

struct ConversationThread: Decodable, Identifiable {
    let id: Int
    let customerName: String
    let phone: String
    let intent: String?
    let module: String?
    let handler: String?
    let status: String?
    let priority: String?
    let sentiment: String?
    let time: String?
    let lastMessage: String?
    let messages: Int?
    let sla: String?
    let assignee: String?
    let messagesList: [ConversationMessage]?
    let aiDecision: AIDecision?

    enum CodingKeys: String, CodingKey {
        case id, phone, intent, module, handler, status, priority, sentiment, time, messages, sla, assignee
        case customerName = "customer_name"
        case lastMessage = "last_message"
        case messagesList = "messages_list"
        case aiDecision = "ai_decision"
    }
}

struct ConversationMessage: Decodable, Identifiable {
    let id: Int?
    let sender: String
    let role: String
    let body: String
    let createdAt: String?

    var stableID: String { "\(id ?? body.hashValue)-\(createdAt ?? "")" }
    var isInbound: Bool { role == "customer" }

    enum CodingKeys: String, CodingKey {
        case id, sender, role, body
        case createdAt = "created_at"
    }
}

struct AIDecision: Decodable {
    let decision: String
    let confidence: Int
    let reason: String
    let suggestedAction: String?
    let riskFlags: [String]?
    let model: String?
    let mode: String?
    let updatedAt: String?
    let createdAt: String?

    enum CodingKeys: String, CodingKey {
        case decision, confidence, reason, model, mode
        case suggestedAction = "suggested_action"
        case riskFlags = "risk_flags"
        case updatedAt = "updated_at"
        case createdAt = "created_at"
    }
}

struct ConversationCounts: Decodable {
    let total: Int
    let active: Int?
    let waiting: Int?
    let escalated: Int?
    let resolved: Int?
}

struct AssigneePayload: Decodable {
    let teams: [TeamAssignee]?
    let members: [MemberAssignee]?
}

struct TeamAssignee: Decodable, Identifiable {
    var id: String { name }
    let name: String
}

struct MemberAssignee: Decodable, Identifiable {
    let id: Int
    let name: String
    let team: String?
}

struct AssistantConfigEnvelope: Decodable {
    let ok: Bool
    let configured: Bool?
    let provider: String?
    let providerLabel: String?
    let apiURL: String?
    let model: String?
    let error: String?

    enum CodingKeys: String, CodingKey {
        case ok, configured, provider, model, error
        case providerLabel = "provider_label"
        case apiURL = "api_url"
    }
}

struct AssistantChatEnvelope: Decodable {
    let ok: Bool
    let reply: String?
    let providerLabel: String?
    let model: String?
    let error: String?

    enum CodingKeys: String, CodingKey {
        case ok, reply, model, error
        case providerLabel = "provider_label"
    }
}
