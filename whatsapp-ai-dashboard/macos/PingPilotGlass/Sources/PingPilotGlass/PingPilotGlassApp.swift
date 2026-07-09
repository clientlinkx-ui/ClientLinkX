import SwiftUI

@main
struct PingPilotGlassApp: App {
    @StateObject private var state = AppState()

    var body: some Scene {
        WindowGroup {
            RootView()
                .environmentObject(state)
                .frame(minWidth: 1180, minHeight: 760)
                .task { await state.refreshAll() }
        }
        .windowStyle(.hiddenTitleBar)
        .commands {
            CommandGroup(after: .appInfo) {
                Button("Refresh Backend Data") {
                    Task { await state.refreshAll() }
                }
                .keyboardShortcut("r", modifiers: [.command])
            }
        }
    }
}
