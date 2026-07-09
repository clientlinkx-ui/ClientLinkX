import SwiftUI
import WebKit

struct RootView: View {
    @EnvironmentObject private var state: AppState
    @State private var selection: AppSection = .dashboard
    @State private var showingSettings = false
    @State private var showingLogin = false

    var body: some View {
        NavigationSplitView {
            Sidebar(selection: $selection, showingSettings: $showingSettings, showingLogin: $showingLogin)
        } detail: {
            ZStack {
                LiquidBackground()
                if state.nativeSession?.isWorkspaceReady == false {
                    SessionGateView(showingLogin: $showingLogin)
                        .padding(24)
                } else {
                    content
                        .padding(24)
                }
            }
            .toolbar {
                ToolbarItemGroup {
                    if state.isLoading { ProgressView().controlSize(.small) }
                    Button {
                        Task { await state.refreshAll() }
                    } label: {
                        Label("Refresh", systemImage: "arrow.clockwise")
                    }
                }
            }
        }
        .sheet(isPresented: $showingSettings) {
            SettingsView()
                .environmentObject(state)
        }
        .sheet(isPresented: $showingLogin, onDismiss: {
            Task { await state.syncWebCookies() }
        }) {
            LoginBridgeView(baseURLString: state.baseURLString, nextPath: state.nativeSession?.nextURL)
                .frame(minWidth: 880, minHeight: 640)
        }
        .alert(item: $state.error) { error in
            Alert(title: Text("Backend Message"), message: Text(error.message), dismissButton: .default(Text("OK")))
        }
    }

    @ViewBuilder
    private var content: some View {
        switch selection {
        case .dashboard:
            DashboardView()
        case .conversations:
            ConversationsView()
        case .assistant:
            AssistantView()
        }
    }
}

struct SessionGateView: View {
    @EnvironmentObject private var state: AppState
    @Binding var showingLogin: Bool

    var body: some View {
        VStack(spacing: 18) {
            Spacer()
            GlassPanel {
                VStack(spacing: 14) {
                    Image(systemName: icon)
                        .font(.system(size: 46))
                        .foregroundStyle(.teal)
                    Text(title)
                        .font(.title.bold())
                    Text(message)
                        .font(.callout)
                        .foregroundStyle(.secondary)
                        .multilineTextAlignment(.center)
                        .frame(maxWidth: 520)

                    HStack {
                        Button(primaryActionTitle) {
                            showingLogin = true
                        }
                        .buttonStyle(GlassButtonStyle(prominent: true))

                        Button("Retry") {
                            Task { await state.refreshAll() }
                        }
                        .buttonStyle(GlassButtonStyle())
                    }
                }
                .padding(18)
                .frame(maxWidth: 680)
            }
            Spacer()
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }

    private var title: String {
        guard let session = state.nativeSession else { return "Connect PingPilot" }
        if !session.authenticated { return "Sign In Required" }
        if !session.onboardingComplete { return "Finish Workspace Onboarding" }
        return "Dashboard Access Needed"
    }

    private var message: String {
        guard let session = state.nativeSession else {
            return "Connect to the Flask backend, then sign in with the existing web flow."
        }
        if !session.authenticated {
            return session.message ?? "Sign in to use the native dashboard."
        }
        if !session.onboardingComplete {
            return "Your account is signed in, but the backend is blocking workspace APIs until onboarding is complete."
        }
        if session.permissions?.dashboard == false {
            return "Your current role is signed in but does not have the dashboard permission required by this native view."
        }
        return session.message ?? "The workspace is not ready yet."
    }

    private var icon: String {
        if state.nativeSession?.authenticated == false { return "person.crop.circle.badge.exclamationmark" }
        if state.nativeSession?.onboardingComplete == false { return "checklist" }
        return "lock.shield"
    }

    private var primaryActionTitle: String {
        if state.nativeSession?.onboardingComplete == false { return "Continue Onboarding" }
        return "Sign In"
    }
}

enum AppSection: String, CaseIterable, Identifiable {
    case dashboard = "Dashboard"
    case conversations = "Conversations"
    case assistant = "Assistant"

    var id: String { rawValue }
    var icon: String {
        switch self {
        case .dashboard: "gauge.with.dots.needle.67percent"
        case .conversations: "bubble.left.and.bubble.right.fill"
        case .assistant: "sparkles"
        }
    }
}

struct Sidebar: View {
    @Binding var selection: AppSection
    @Binding var showingSettings: Bool
    @Binding var showingLogin: Bool

    var body: some View {
        ZStack {
            LiquidBackground()
            VStack(alignment: .leading, spacing: 18) {
                HStack(spacing: 12) {
                    Image(systemName: "message.badge.waveform.fill")
                        .font(.system(size: 30))
                        .foregroundStyle(.teal)
                    VStack(alignment: .leading, spacing: 2) {
                        Text("PingPilot")
                            .font(.title2.bold())
                        Text("Liquid command deck")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    }
                }
                .padding(.bottom, 8)

                ForEach(AppSection.allCases) { section in
                    Button {
                        selection = section
                    } label: {
                        Label(section.rawValue, systemImage: section.icon)
                            .frame(maxWidth: .infinity, alignment: .leading)
                    }
                    .buttonStyle(SidebarButtonStyle(isSelected: selection == section))
                }

                Spacer()

                Button {
                    showingLogin = true
                } label: {
                    Label("Sign In", systemImage: "person.crop.circle.badge.checkmark")
                        .frame(maxWidth: .infinity, alignment: .leading)
                }
                .buttonStyle(GlassButtonStyle())

                Button {
                    showingSettings = true
                } label: {
                    Label("Settings", systemImage: "slider.horizontal.3")
                        .frame(maxWidth: .infinity, alignment: .leading)
                }
                .buttonStyle(GlassButtonStyle())
            }
            .padding(18)
        }
        .navigationSplitViewColumnWidth(min: 240, ideal: 260)
    }
}

struct DashboardView: View {
    @EnvironmentObject private var state: AppState

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 18) {
                Header(title: "Live WhatsApp Operations", subtitle: state.dashboardUpdatedAt.map { "Updated \($0)" } ?? "Connected to the Flask backend")

                LazyVGrid(columns: Array(repeating: GridItem(.flexible(), spacing: 14), count: 4), spacing: 14) {
                    ForEach(state.dashboard?.stats ?? []) { stat in
                        StatGlassCard(stat: stat)
                    }
                }

                HStack(alignment: .top, spacing: 14) {
                    TrafficPanel(traffic: state.dashboard?.traffic)
                    StatusPanel(status: state.dashboard?.statusBreakdown)
                }

                HStack(alignment: .top, spacing: 14) {
                    ModulesPanel(modules: state.dashboard?.modules ?? [])
                    RuntimePanel(runtime: state.dashboard?.runtimeStatus)
                    ActivityPanel(items: state.dashboard?.recentActivity ?? [])
                }
            }
        }
    }
}

struct ConversationsView: View {
    @EnvironmentObject private var state: AppState
    @State private var draft = ""

    var body: some View {
        VStack(alignment: .leading, spacing: 14) {
            Header(title: "Conversation Glassboard", subtitle: "\(state.counts?.total ?? state.conversations.count) threads in the current queue")

            HStack {
                TextField("Search customer, phone, intent, or message", text: $state.searchText)
                    .textFieldStyle(.roundedBorder)
                    .onSubmit { Task { await state.loadConversations() } }
                Picker("Status", selection: $state.selectedStatus) {
                    ForEach(["All", "Active", "Waiting", "Escalated", "Resolved"], id: \.self) { Text($0) }
                }
                .pickerStyle(.segmented)
                Button("Apply") { Task { await state.loadConversations() } }
                    .buttonStyle(GlassButtonStyle(prominent: true))
            }

            HStack(alignment: .top, spacing: 14) {
                GlassPanel {
                    List(state.conversations, selection: Binding(get: {
                        state.selectedThread?.id
                    }, set: { id in
                        if let id { Task { await state.selectThread(id) } }
                    })) { item in
                        ConversationRow(item: item)
                            .tag(item.id)
                    }
                    .scrollContentBackground(.hidden)
                }
                .frame(width: 360)

                ThreadDetail(thread: state.selectedThread, draft: $draft)
            }
        }
    }
}

struct ThreadDetail: View {
    @EnvironmentObject private var state: AppState
    let thread: ConversationThread?
    @Binding var draft: String

    var body: some View {
        GlassPanel {
            if let thread {
                VStack(alignment: .leading, spacing: 14) {
                    HStack {
                        VStack(alignment: .leading, spacing: 4) {
                            Text(thread.customerName)
                                .font(.title2.bold())
                            Text("\(thread.phone)  \(thread.module ?? "General")  SLA \(thread.sla ?? "Live")")
                                .font(.callout)
                                .foregroundStyle(.secondary)
                        }
                        Spacer()
                        StatusPill(text: thread.status ?? "Active")
                    }

                    if let decision = thread.aiDecision {
                        DecisionCard(decision: decision)
                    }

                    ScrollView {
                        LazyVStack(spacing: 10) {
                            ForEach(thread.messagesList ?? [], id: \.stableID) { message in
                                MessageBubble(message: message)
                            }
                        }
                    }

                    HStack {
                        TextField("Reply as workspace agent", text: $draft, axis: .vertical)
                            .textFieldStyle(.roundedBorder)
                        Button("Send") {
                            let body = draft
                            draft = ""
                            Task { await state.sendReply(body) }
                        }
                        .buttonStyle(GlassButtonStyle(prominent: true))
                        .disabled(draft.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
                    }

                    HStack {
                        Button("Analyze") { Task { await state.runDecision() } }
                        Button("Escalate") { Task { await state.setThreadStatus("escalate") } }
                        Button("Resolve") { Task { await state.setThreadStatus("resolve") } }
                        Button("Continue") { Task { await state.setThreadStatus("continue") } }
                    }
                    .buttonStyle(GlassButtonStyle())
                }
            } else {
                ContentUnavailableView("No Conversation Selected", systemImage: "bubble.left", description: Text("Choose a thread from the queue to inspect the live timeline."))
            }
        }
    }
}

struct AssistantView: View {
    @EnvironmentObject private var state: AppState
    @State private var message = "Summarize today's WhatsApp queue and note any risks."
    @State private var transcript: [(String, String)] = []
    @State private var isSending = false

    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            Header(title: "Assistant Test Bench", subtitle: state.assistantConfig?.configured == true ? "\(state.assistantConfig?.providerLabel ?? "Provider") / \(state.assistantConfig?.model ?? "model")" : "Configure the assistant in the web dashboard first")
            GlassPanel {
                VStack(alignment: .leading, spacing: 12) {
                    ScrollView {
                        LazyVStack(alignment: .leading, spacing: 12) {
                            ForEach(Array(transcript.enumerated()), id: \.offset) { _, item in
                                VStack(alignment: .leading, spacing: 4) {
                                    Text(item.0).font(.caption.bold()).foregroundStyle(.secondary)
                                    Text(item.1).textSelection(.enabled)
                                }
                                .padding(12)
                                .frame(maxWidth: .infinity, alignment: .leading)
                                .background(.thinMaterial, in: RoundedRectangle(cornerRadius: 14))
                            }
                        }
                    }
                    TextField("Ask the connected backend assistant", text: $message, axis: .vertical)
                        .textFieldStyle(.roundedBorder)
                    Button(isSending ? "Sending..." : "Send to Backend Assistant") {
                        Task {
                            isSending = true
                            let prompt = message
                            transcript.append(("You", prompt))
                            message = ""
                            let reply = await state.assistantChat(prompt)
                            transcript.append(("Assistant", reply))
                            isSending = false
                        }
                    }
                    .buttonStyle(GlassButtonStyle(prominent: true))
                    .disabled(isSending || message.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
                }
            }
        }
    }
}

struct SettingsView: View {
    @EnvironmentObject private var state: AppState
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            Header(title: "Backend Settings", subtitle: "Point the native app at the same Flask server used by the web dashboard.")
            TextField("Backend URL", text: $state.baseURLString)
                .textFieldStyle(.roundedBorder)
            HStack {
                Button("Cancel") { dismiss() }
                Spacer()
                Button("Save and Refresh") {
                    Task {
                        await state.refreshAll()
                        dismiss()
                    }
                }
                .buttonStyle(GlassButtonStyle(prominent: true))
            }
        }
        .padding(24)
        .frame(width: 520)
        .background(LiquidBackground())
    }
}

struct LoginBridgeView: NSViewRepresentable {
    let baseURLString: String
    let nextPath: String?

    func makeNSView(context: Context) -> WKWebView {
        let configuration = WKWebViewConfiguration()
        configuration.websiteDataStore = .default()
        let webView = WKWebView(frame: .zero, configuration: configuration)
        webView.navigationDelegate = context.coordinator
        let baseURL = URL(string: baseURLString) ?? URL(string: "http://127.0.0.1:5000")!
        let rawPath = nextPath?.isEmpty == false ? nextPath! : "/login"
        let path = rawPath.trimmingCharacters(in: CharacterSet(charactersIn: "/"))
        let url = baseURL.appending(path: path)
        webView.load(URLRequest(url: url))
        return webView
    }

    func updateNSView(_ nsView: WKWebView, context: Context) {}

    func makeCoordinator() -> Coordinator { Coordinator() }

    final class Coordinator: NSObject, WKNavigationDelegate {}
}

struct Header: View {
    let title: String
    let subtitle: String

    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(title)
                .font(.system(size: 34, weight: .bold, design: .rounded))
            Text(subtitle)
                .font(.callout)
                .foregroundStyle(.secondary)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }
}

struct GlassPanel<Content: View>: View {
    @ViewBuilder let content: Content

    var body: some View {
        content
            .padding(16)
            .background(.ultraThinMaterial, in: RoundedRectangle(cornerRadius: 22, style: .continuous))
            .overlay {
                RoundedRectangle(cornerRadius: 22, style: .continuous)
                    .stroke(.white.opacity(0.22), lineWidth: 1)
            }
            .shadow(color: .black.opacity(0.12), radius: 24, x: 0, y: 12)
    }
}

struct StatGlassCard: View {
    let stat: StatCard

    var body: some View {
        GlassPanel {
            VStack(alignment: .leading, spacing: 10) {
                Image(systemName: iconName(for: stat.title))
                    .font(.title2)
                    .foregroundStyle(.teal)
                Text(stat.value)
                    .font(.system(size: 30, weight: .bold, design: .rounded))
                Text(stat.title)
                    .font(.headline)
                Text(stat.change ?? "")
                    .font(.caption)
                    .foregroundStyle(stat.trend == "down" ? .orange : .secondary)
            }
            .frame(maxWidth: .infinity, alignment: .leading)
        }
    }

    private func iconName(for title: String) -> String {
        if title.contains("Escalation") { return "headphones.circle.fill" }
        if title.contains("Satisfaction") { return "face.smiling.fill" }
        if title.contains("Automation") { return "bolt.circle.fill" }
        return "bubble.left.and.bubble.right.fill"
    }
}

struct TrafficPanel: View {
    let traffic: TrafficData?

    var body: some View {
        GlassPanel {
            VStack(alignment: .leading, spacing: 14) {
                Text("AI vs Human Traffic").font(.headline)
                if let traffic {
                    ChartBars(labels: traffic.labels, primary: traffic.ai, secondary: traffic.human)
                } else {
                    ProgressView()
                }
            }
        }
    }
}

struct ChartBars: View {
    let labels: [String]
    let primary: [Int]
    let secondary: [Int]

    var body: some View {
        HStack(alignment: .bottom, spacing: 10) {
            ForEach(labels.indices, id: \.self) { index in
                let ai = primary.indices.contains(index) ? primary[index] : 0
                let human = secondary.indices.contains(index) ? secondary[index] : 0
                let maxValue = max((primary + secondary).max() ?? 1, 1)
                VStack(spacing: 6) {
                    RoundedRectangle(cornerRadius: 7)
                        .fill(.teal.gradient)
                        .frame(height: CGFloat(ai) / CGFloat(maxValue) * 170 + 12)
                    RoundedRectangle(cornerRadius: 7)
                        .fill(.orange.gradient)
                        .frame(height: CGFloat(human) / CGFloat(maxValue) * 90 + 8)
                    Text(labels[index]).font(.caption2).foregroundStyle(.secondary)
                }
            }
        }
        .frame(maxWidth: .infinity, minHeight: 230)
    }
}

struct StatusPanel: View {
    let status: StatusBreakdown?

    var body: some View {
        GlassPanel {
            VStack(alignment: .leading, spacing: 12) {
                Text("Status Mix").font(.headline)
                ForEach(status?.labels.indices ?? 0..<0, id: \.self) { index in
                    let value = status?.values[index] ?? 0
                    HStack {
                        Text(status?.labels[index] ?? "")
                        Spacer()
                        Text("\(value)")
                            .bold()
                    }
                    ProgressView(value: Double(value), total: Double(max(status?.values.max() ?? 1, 1)))
                        .tint(index == 0 ? .teal : .orange)
                }
            }
            .frame(width: 300)
        }
    }
}

struct ModulesPanel: View {
    let modules: [BusinessModule]

    var body: some View {
        GlassPanel {
            VStack(alignment: .leading, spacing: 12) {
                Text("Modules").font(.headline)
                ForEach(modules) { module in
                    VStack(alignment: .leading, spacing: 4) {
                        HStack {
                            Text(module.name).bold()
                            Spacer()
                            Text(module.value)
                        }
                        ProgressView(value: (module.progress ?? 0) / 100)
                            .tint(.teal)
                    }
                }
            }
        }
    }
}

struct RuntimePanel: View {
    let runtime: RuntimeStatus?

    var body: some View {
        GlassPanel {
            VStack(alignment: .leading, spacing: 12) {
                Text("Runtime").font(.headline)
                Text(runtime?.provider ?? "No provider").font(.title3.bold())
                Text(runtime?.model ?? "No model")
                Text(runtime?.description ?? "Connect the backend assistant to unlock live AI actions.")
                    .font(.callout)
                    .foregroundStyle(.secondary)
                StatusPill(text: runtime?.statusLabel ?? "Setup needed")
            }
            .frame(width: 260, alignment: .leading)
        }
    }
}

struct ActivityPanel: View {
    let items: [ActivityItem]

    var body: some View {
        GlassPanel {
            VStack(alignment: .leading, spacing: 12) {
                Text("Activity").font(.headline)
                ForEach(items) { item in
                    VStack(alignment: .leading, spacing: 2) {
                        Text(item.title).bold()
                        Text(item.time ?? "")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    }
                }
            }
        }
    }
}

struct ConversationRow: View {
    let item: ConversationSummary

    var body: some View {
        VStack(alignment: .leading, spacing: 5) {
            HStack {
                Text(item.customerName).bold()
                Spacer()
                Text(item.time ?? "")
                    .font(.caption2)
                    .foregroundStyle(.secondary)
            }
            Text(item.lastMessage ?? item.intent ?? "No preview")
                .font(.callout)
                .foregroundStyle(.secondary)
                .lineLimit(2)
            HStack {
                StatusPill(text: item.status ?? "Active")
                Text(item.assignee ?? "Unassigned")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
        }
        .padding(.vertical, 5)
    }
}

struct DecisionCard: View {
    let decision: AIDecision

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack {
                Label(decision.decision == "escalate" ? "Escalate to human" : "Continue chat", systemImage: "wand.and.sparkles")
                    .font(.headline)
                Spacer()
                Text("\(decision.confidence)%")
                    .font(.headline)
            }
            ProgressView(value: Double(decision.confidence), total: 100)
                .tint(decision.decision == "escalate" ? .orange : .teal)
            Text(decision.reason)
                .font(.callout)
                .foregroundStyle(.secondary)
            if let action = decision.suggestedAction {
                Text(action).font(.callout)
            }
        }
        .padding(12)
        .background(.thinMaterial, in: RoundedRectangle(cornerRadius: 16))
    }
}

struct MessageBubble: View {
    let message: ConversationMessage

    var body: some View {
        HStack {
            if !message.isInbound { Spacer(minLength: 80) }
            VStack(alignment: .leading, spacing: 4) {
                Text(message.sender)
                    .font(.caption.bold())
                    .foregroundStyle(.secondary)
                Text(message.body)
                    .textSelection(.enabled)
            }
            .padding(12)
            .background(message.isInbound ? .regularMaterial : .thinMaterial, in: RoundedRectangle(cornerRadius: 16))
            if message.isInbound { Spacer(minLength: 80) }
        }
    }
}

struct StatusPill: View {
    let text: String

    var body: some View {
        Text(text)
            .font(.caption.bold())
            .padding(.horizontal, 9)
            .padding(.vertical, 5)
            .background(color.opacity(0.16), in: Capsule())
            .foregroundStyle(color)
    }

    private var color: Color {
        switch text.lowercased() {
        case "resolved", "online": .teal
        case "escalated", "setup needed": .orange
        case "waiting": .yellow
        default: .blue
        }
    }
}

struct LiquidBackground: View {
    var body: some View {
        ZStack {
            LinearGradient(colors: [Color(nsColor: .windowBackgroundColor), Color.teal.opacity(0.12), Color.cyan.opacity(0.08)], startPoint: .topLeading, endPoint: .bottomTrailing)
            Circle()
                .fill(.teal.opacity(0.16))
                .blur(radius: 50)
                .frame(width: 360, height: 360)
                .offset(x: -260, y: -180)
            Circle()
                .fill(.cyan.opacity(0.12))
                .blur(radius: 64)
                .frame(width: 420, height: 420)
                .offset(x: 360, y: 260)
        }
        .ignoresSafeArea()
    }
}

struct SidebarButtonStyle: ButtonStyle {
    let isSelected: Bool

    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .padding(.horizontal, 12)
            .padding(.vertical, 10)
            .background {
                RoundedRectangle(cornerRadius: 14)
                    .fill(isSelected ? AnyShapeStyle(.ultraThinMaterial) : AnyShapeStyle(.clear))
            }
            .overlay {
                RoundedRectangle(cornerRadius: 14)
                    .stroke(isSelected ? .white.opacity(0.24) : .clear, lineWidth: 1)
            }
            .foregroundStyle(isSelected ? .primary : .secondary)
            .scaleEffect(configuration.isPressed ? 0.98 : 1)
    }
}

struct GlassButtonStyle: ButtonStyle {
    var prominent = false

    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .fontWeight(prominent ? .semibold : .regular)
            .padding(.horizontal, 12)
            .padding(.vertical, 8)
            .background {
                RoundedRectangle(cornerRadius: 12, style: .continuous)
                    .fill(prominent ? AnyShapeStyle(.teal.gradient) : AnyShapeStyle(.thinMaterial))
            }
            .overlay {
                RoundedRectangle(cornerRadius: 12, style: .continuous)
                    .stroke(.white.opacity(0.24), lineWidth: 1)
            }
            .foregroundStyle(prominent ? .white : .primary)
            .shadow(color: .black.opacity(configuration.isPressed ? 0.06 : 0.14), radius: configuration.isPressed ? 4 : 12, y: configuration.isPressed ? 2 : 6)
            .scaleEffect(configuration.isPressed ? 0.98 : 1)
    }
}
