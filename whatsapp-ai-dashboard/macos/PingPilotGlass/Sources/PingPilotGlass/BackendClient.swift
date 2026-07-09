import Foundation
import WebKit

@MainActor
final class AppState: ObservableObject {
    @Published var baseURLString: String {
        didSet { UserDefaults.standard.set(baseURLString, forKey: "baseURLString") }
    }
    @Published var dashboard: DashboardSnapshot?
    @Published var dashboardUpdatedAt: String?
    @Published var conversations: [ConversationSummary] = []
    @Published var selectedThread: ConversationThread?
    @Published var counts: ConversationCounts?
    @Published var assistantConfig: AssistantConfigEnvelope?
    @Published var nativeSession: NativeSession?
    @Published var isLoading = false
    @Published var error: APIError?
    @Published var searchText = ""
    @Published var selectedStatus = "All"

    let client = BackendClient()

    init() {
        baseURLString = UserDefaults.standard.string(forKey: "baseURLString") ?? "http://127.0.0.1:5000"
        client.baseURLString = baseURLString
    }

    func refreshAll() async {
        client.baseURLString = baseURLString
        isLoading = true
        defer { isLoading = false }
        do {
            nativeSession = try await client.nativeSession()
            guard nativeSession?.isWorkspaceReady == true else {
                dashboard = nil
                conversations = []
                selectedThread = nil
                counts = nil
                assistantConfig = nil
                return
            }
            let dashboardEnvelope = try await client.dashboard()
            dashboard = dashboardEnvelope.data
            dashboardUpdatedAt = dashboardEnvelope.updatedAt
            let conversationEnvelope = try await client.conversations(status: selectedStatus, query: searchText)
            conversations = conversationEnvelope.threads ?? []
            selectedThread = conversationEnvelope.selectedThread
            counts = conversationEnvelope.summaryCounts
            assistantConfig = try? await client.assistantConfig()
        } catch {
            self.error = APIError(message: error.localizedDescription)
        }
    }

    func checkSession() async {
        client.baseURLString = baseURLString
        do {
            nativeSession = try await client.nativeSession()
        } catch {
            self.error = APIError(message: error.localizedDescription)
        }
    }

    func loadConversations() async {
        client.baseURLString = baseURLString
        do {
            let envelope = try await client.conversations(status: selectedStatus, query: searchText)
            conversations = envelope.threads ?? []
            selectedThread = envelope.selectedThread
            counts = envelope.summaryCounts
        } catch {
            self.error = APIError(message: error.localizedDescription)
        }
    }

    func selectThread(_ id: Int) async {
        do {
            selectedThread = try await client.thread(id)
        } catch {
            self.error = APIError(message: error.localizedDescription)
        }
    }

    func sendReply(_ body: String) async {
        guard let id = selectedThread?.id else { return }
        do {
            selectedThread = try await client.sendReply(threadID: id, body: body)
            await loadConversations()
        } catch {
            self.error = APIError(message: error.localizedDescription)
        }
    }

    func runDecision() async {
        guard let id = selectedThread?.id else { return }
        do {
            selectedThread = try await client.analyze(threadID: id)
        } catch {
            self.error = APIError(message: error.localizedDescription)
        }
    }

    func setThreadStatus(_ action: String) async {
        guard let id = selectedThread?.id else { return }
        do {
            selectedThread = try await client.statusAction(threadID: id, action: action)
            await loadConversations()
        } catch {
            self.error = APIError(message: error.localizedDescription)
        }
    }

    func assistantChat(_ message: String) async -> String {
        do {
            let response = try await client.assistantChat(message)
            return response.reply ?? "No reply returned."
        } catch {
            self.error = APIError(message: error.localizedDescription)
            return error.localizedDescription
        }
    }

    func syncWebCookies() async {
        let cookies = await WKWebsiteDataStore.default().httpCookieStore.allCookies()
        for cookie in cookies {
            HTTPCookieStorage.shared.setCookie(cookie)
        }
        await refreshAll()
    }
}

@MainActor
final class BackendClient {
    var baseURLString = "http://127.0.0.1:5000"
    private let decoder = JSONDecoder()

    private var baseURL: URL {
        URL(string: baseURLString.trimmingCharacters(in: .whitespacesAndNewlines)) ?? URL(string: "http://127.0.0.1:5000")!
    }

    func dashboard() async throws -> DashboardEnvelope {
        try await request("/api/dashboard/refresh", method: "POST", body: EmptyBody())
    }

    func nativeSession() async throws -> NativeSession {
        try await request("/api/native/session")
    }

    func conversations(status: String, query: String) async throws -> ConversationListEnvelope {
        var components = URLComponents(url: baseURL.appending(path: "/api/conversations"), resolvingAgainstBaseURL: false)!
        var items: [URLQueryItem] = []
        if status != "All" { items.append(URLQueryItem(name: "status", value: status)) }
        if !query.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
            items.append(URLQueryItem(name: "q", value: query))
        }
        components.queryItems = items.isEmpty ? nil : items
        return try await request(components.url!)
    }

    func thread(_ id: Int) async throws -> ConversationThread {
        let envelope: ConversationThreadEnvelope = try await request("/api/conversations/\(id)")
        guard let thread = envelope.thread else { throw APIError(message: envelope.error ?? "Conversation not found.") }
        return thread
    }

    func sendReply(threadID: Int, body: String) async throws -> ConversationThread {
        let envelope: ConversationThreadEnvelope = try await request("/api/conversations/\(threadID)/messages", method: "POST", body: ["body": body])
        guard let thread = envelope.thread else { throw APIError(message: envelope.error ?? "Reply failed.") }
        return thread
    }

    func analyze(threadID: Int) async throws -> ConversationThread {
        let envelope: ConversationThreadEnvelope = try await request("/api/conversations/\(threadID)/ai-decision", method: "POST")
        guard let thread = envelope.thread else { throw APIError(message: envelope.error ?? "Analysis failed.") }
        return thread
    }

    func statusAction(threadID: Int, action: String) async throws -> ConversationThread {
        let envelope: ConversationThreadEnvelope = try await request("/api/conversations/\(threadID)/\(action)", method: "POST")
        guard let thread = envelope.thread else { throw APIError(message: envelope.error ?? "Action failed.") }
        return thread
    }

    func assistantConfig() async throws -> AssistantConfigEnvelope {
        try await request("/api/assistant/config")
    }

    func assistantChat(_ message: String) async throws -> AssistantChatEnvelope {
        try await request("/api/assistant/chat", method: "POST", body: ["message": message])
    }

    private func request<T: Decodable>(_ path: String, method: String = "GET", body: Encodable? = nil) async throws -> T {
        try await request(baseURL.appending(path: path), method: method, body: body)
    }

    private func request<T: Decodable>(_ url: URL, method: String = "GET", body: Encodable? = nil) async throws -> T {
        var request = URLRequest(url: url)
        request.httpMethod = method
        request.setValue("application/json", forHTTPHeaderField: "Accept")
        if let cookies = HTTPCookieStorage.shared.cookies(for: url), !cookies.isEmpty {
            request.setValue(HTTPCookie.requestHeaderFields(with: cookies)["Cookie"], forHTTPHeaderField: "Cookie")
        }
        if let body {
            request.setValue("application/json", forHTTPHeaderField: "Content-Type")
            request.httpBody = try JSONEncoder().encode(AnyEncodable(body))
        }

        let (data, response) = try await URLSession.shared.data(for: request)
        guard let http = response as? HTTPURLResponse else {
            throw APIError(message: "Backend did not return an HTTP response.")
        }
        if !(200..<300).contains(http.statusCode) {
            if let backendError = try? decoder.decode(ErrorEnvelope.self, from: data), let message = backendError.error {
                throw APIError(message: message)
            }
            let body = String(data: data, encoding: .utf8)?
                .replacingOccurrences(of: "\n", with: " ")
                .trimmingCharacters(in: .whitespacesAndNewlines)
            let detail = body?.isEmpty == false ? " \(body!.prefix(180))" : ""
            throw APIError(message: "Backend returned HTTP \(http.statusCode).\(detail)")
        }
        let decoded = try decoder.decode(T.self, from: data)
        return decoded
    }
}

struct ErrorEnvelope: Decodable {
    let ok: Bool?
    let error: String?
}

struct EmptyBody: Encodable {}

struct AnyEncodable: Encodable {
    private let encodeClosure: (Encoder) throws -> Void

    init(_ wrapped: Encodable) {
        encodeClosure = wrapped.encode
    }

    func encode(to encoder: Encoder) throws {
        try encodeClosure(encoder)
    }
}

extension WKHTTPCookieStore {
    func allCookies() async -> [HTTPCookie] {
        await withCheckedContinuation { continuation in
            getAllCookies { continuation.resume(returning: $0) }
        }
    }
}
