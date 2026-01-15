import SwiftUI

struct ContentView: View {
    @ObservedObject var store: SessionStore

    @State private var searchText: String = ""
    @State private var selectedTool: ToolFilter = .all
    @State private var selectedProject: ProjectSelection? = .all
    @State private var sinceEnabled: Bool = false
    @State private var untilEnabled: Bool = false
    @State private var sinceDate: Date = Date()
    @State private var untilDate: Date = Date()
    @State private var selectedSessionId: Int64?

    var body: some View {
        NavigationSplitView {
            projectSidebar
        } content: {
            sessionsList
        } detail: {
            sessionDetail
                .navigationSplitViewColumnWidth(min: 320, ideal: 420, max: 520)
        }
        .navigationSplitViewStyle(.balanced)
        .frame(minWidth: 1100, minHeight: 700)
        .onAppear {
            applyFilters(debounce: false)
        }
    }

    private var projectSidebar: some View {
        List(selection: $selectedProject) {
            Text("全部项目")
                .tag(ProjectSelection.all)
            ForEach(store.projects, id: \.self) { project in
                Text(project)
                    .tag(ProjectSelection.project(project))
            }
        }
        .listStyle(.sidebar)
        .navigationSplitViewColumnWidth(min: 200, ideal: 240, max: 320)
        .onChange(of: selectedProject) { _ in
            applyFilters()
        }
    }

    private var sessionsList: some View {
        VStack(spacing: 0) {
            filterBar
            if !store.statusMessage.isEmpty {
                Text(store.statusMessage)
                    .foregroundColor(.secondary)
                    .padding(.vertical, 8)
            }
            List(store.sessions, selection: $selectedSessionId) { session in
                SessionRowView(session: session)
                    .tag(session.id)
            }
        }
        .navigationSplitViewColumnWidth(min: 420, ideal: 520, max: 720)
    }

    @ViewBuilder
    private var sessionDetail: some View {
        if let selectedId = selectedSessionId,
           let session = store.sessions.first(where: { $0.id == selectedId }) {
            SessionDetailView(session: session)
        } else {
            VStack {
                Text("请选择会话查看详情")
                    .foregroundColor(.secondary)
            }
            .frame(maxWidth: .infinity, maxHeight: .infinity)
        }
    }

    private var filterBar: some View {
        VStack(spacing: 8) {
            HStack(spacing: 12) {
                TextField("搜索关键词", text: $searchText)
                    .textFieldStyle(.roundedBorder)
                    .frame(minWidth: 200)
                    .onChange(of: searchText) { _ in
                        applyFilters()
                    }

                Picker("工具", selection: $selectedTool) {
                    ForEach(ToolFilter.allCases) { tool in
                        Text(tool.displayName).tag(tool)
                    }
                }
                .pickerStyle(.segmented)
                .frame(width: 240)
                .onChange(of: selectedTool) { _ in
                    applyFilters()
                }

                Toggle("开始日期", isOn: $sinceEnabled)
                    .toggleStyle(.switch)
                    .onChange(of: sinceEnabled) { _ in
                        applyFilters()
                    }
                DatePicker("", selection: $sinceDate, displayedComponents: .date)
                    .labelsHidden()
                    .disabled(!sinceEnabled)
                    .onChange(of: sinceDate) { _ in
                        applyFilters()
                    }

                Toggle("结束日期", isOn: $untilEnabled)
                    .toggleStyle(.switch)
                    .onChange(of: untilEnabled) { _ in
                        applyFilters()
                    }
                DatePicker("", selection: $untilDate, displayedComponents: .date)
                    .labelsHidden()
                    .disabled(!untilEnabled)
                    .onChange(of: untilDate) { _ in
                        applyFilters()
                    }

                if store.isLoading {
                    ProgressView()
                        .controlSize(.small)
                }

                Button("刷新") {
                    store.refresh()
                }
            }
            .padding(.horizontal, 12)
            .padding(.vertical, 8)
        }
        .background(Color(nsColor: .windowBackgroundColor))
    }

    private func applyFilters(debounce: Bool = true) {
        let project = selectedProject?.projectValue ?? ""
        let filter = SessionFilterInput(
            search: searchText,
            project: project,
            tool: selectedTool,
            since: sinceEnabled ? sinceDate : nil,
            until: untilEnabled ? untilDate : nil,
            limit: nil
        )
        store.applyFilter(filter, debounce: debounce)
    }
}

private enum ProjectSelection: Hashable {
    case all
    case project(String)

    var projectValue: String {
        switch self {
        case .all:
            return ""
        case .project(let value):
            return value
        }
    }
}
