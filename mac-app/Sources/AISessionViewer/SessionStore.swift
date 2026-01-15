import Foundation

final class SessionStore: ObservableObject {
    @Published var sessions: [Session] = []
    @Published var projects: [String] = []
    @Published var statusMessage: String = ""
    @Published var isLoading: Bool = false

    private let database: Database
    private let workQueue = DispatchQueue(label: "ai.session.viewer.db", qos: .userInitiated)
    private var pendingWork: DispatchWorkItem?
    private var currentFilter = SessionFilterInput()

    init(databasePath: String = SessionStore.defaultIndexPath()) {
        self.database = Database(path: databasePath)
        reloadProjects()
        applyFilter(currentFilter, debounce: false)
    }

    static func defaultIndexPath() -> String {
        let home = FileManager.default.homeDirectoryForCurrentUser
        return home.appendingPathComponent(".cache/ai-session-viewer/index.db").path
    }

    func reloadProjects() {
        guard database.fileExists() else {
            statusMessage = "索引数据库不存在，请先运行 aisv --build-index"
            projects = []
            return
        }
        statusMessage = ""
        workQueue.async {
            let items = self.database.fetchProjects()
            DispatchQueue.main.async {
                self.projects = items
            }
        }
    }

    func applyFilter(_ filter: SessionFilterInput, debounce: Bool = true) {
        currentFilter = filter
        let work = DispatchWorkItem { [weak self] in
            self?.loadSessions()
        }
        pendingWork?.cancel()
        pendingWork = work
        let delay: TimeInterval = debounce ? 0.2 : 0.0
        DispatchQueue.main.asyncAfter(deadline: .now() + delay, execute: work)
    }

    func refresh() {
        reloadProjects()
        applyFilter(currentFilter, debounce: false)
    }

    private func loadSessions() {
        guard database.fileExists() else {
            DispatchQueue.main.async {
                self.statusMessage = "索引数据库不存在，请先运行 aisv --build-index"
                self.sessions = []
                self.isLoading = false
            }
            return
        }
        DispatchQueue.main.async {
            self.statusMessage = ""
            self.isLoading = true
        }
        let filter = currentFilter
        workQueue.async {
            let items = self.database.fetchSessions(filter: filter)
            DispatchQueue.main.async {
                self.sessions = items
                self.isLoading = false
            }
        }
    }
}
