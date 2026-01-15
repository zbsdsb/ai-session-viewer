import Foundation
import SQLite3

final class Database {
    private let path: String

    init(path: String) {
        self.path = path
    }

    func fileExists() -> Bool {
        FileManager.default.fileExists(atPath: path)
    }

    func fetchProjects() -> [String] {
        guard let db = openDatabase() else {
            return []
        }
        defer { sqlite3_close(db) }

        let sql = """
        SELECT DISTINCT project_path
        FROM sessions
        WHERE project_path IS NOT NULL AND project_path <> ''
        ORDER BY project_path
        """

        guard let statement = prepareStatement(db, sql: sql) else {
            return []
        }
        defer { sqlite3_finalize(statement) }

        var projects: [String] = []
        while sqlite3_step(statement) == SQLITE_ROW {
            if let text = sqlite3_column_text(statement, 0) {
                projects.append(String(cString: text))
            }
        }
        return projects
    }

    func fetchSessions(filter: SessionFilterInput) -> [Session] {
        guard let db = openDatabase() else {
            return []
        }
        defer { sqlite3_close(db) }

        var clauses: [String] = []
        var bindValues: [BindValue] = []
        var joinFts = false

        let searchQuery = buildFtsQuery(filter.search)
        if !searchQuery.isEmpty {
            joinFts = true
            clauses.append("f MATCH ?")
            bindValues.append(.text(searchQuery))
        }

        if !filter.project.isEmpty {
            clauses.append("s.project_path LIKE ?")
            bindValues.append(.text("%\(filter.project)%"))
        }

        if let since = filter.since {
            clauses.append("s.start_time >= ?")
            bindValues.append(.text(DateFormats.toIsoString(since, endOfDay: false)))
        }

        if let until = filter.until {
            clauses.append("s.start_time <= ?")
            bindValues.append(.text(DateFormats.toIsoString(until, endOfDay: true)))
        }

        if filter.tool != .all {
            clauses.append("s.tool = ?")
            bindValues.append(.text(filter.tool.rawValue))
        }

        let whereClause = clauses.isEmpty ? "" : "WHERE " + clauses.joined(separator: " AND ")
        let joinClause = joinFts ? "JOIN sessions_fts f ON f.rowid = s.id" : ""
        let limitClause = filter.limit == nil ? "" : "LIMIT ?"
        if let limit = filter.limit {
            bindValues.append(.int(limit))
        }

        let sql = """
        SELECT s.*
        FROM sessions s
        \(joinClause)
        \(whereClause)
        ORDER BY COALESCE(s.last_time, s.start_time) DESC
        \(limitClause)
        """

        guard let statement = prepareStatement(db, sql: sql) else {
            return []
        }
        defer { sqlite3_finalize(statement) }

        bind(statement, values: bindValues)

        var sessions: [Session] = []
        while sqlite3_step(statement) == SQLITE_ROW {
            let session = Session(
                id: sqlite3_column_int64(statement, 0),
                tool: readText(statement, index: 1),
                sessionId: readText(statement, index: 2),
                projectPath: readText(statement, index: 3),
                startTime: readText(statement, index: 4),
                lastTime: readText(statement, index: 5),
                messageCount: Int(sqlite3_column_int(statement, 6)),
                firstMessage: readText(statement, index: 7),
                filePath: readText(statement, index: 9),
                fileSize: Int(sqlite3_column_int(statement, 10)),
                model: readText(statement, index: 11),
                summary: readText(statement, index: 8)
            )
            sessions.append(session)
        }

        return sessions
    }

    private func buildFtsQuery(_ text: String) -> String {
        let tokens = text.split { $0.isWhitespace }.map { token -> String in
            let cleaned = token.trimmingCharacters(in: .whitespacesAndNewlines)
            return cleaned.replacingOccurrences(of: "\"", with: "\"\"")
        }
        if tokens.isEmpty {
            return ""
        }
        return tokens.map { "\"\($0)\"" }.joined(separator: " AND ")
    }

    private func openDatabase() -> OpaquePointer? {
        var db: OpaquePointer?
        if sqlite3_open(path, &db) == SQLITE_OK {
            return db
        }
        if db != nil {
            sqlite3_close(db)
        }
        return nil
    }

    private func prepareStatement(_ db: OpaquePointer, sql: String) -> OpaquePointer? {
        var statement: OpaquePointer?
        if sqlite3_prepare_v2(db, sql, -1, &statement, nil) == SQLITE_OK {
            return statement
        }
        return nil
    }

    private func readText(_ statement: OpaquePointer, index: Int32) -> String {
        guard let text = sqlite3_column_text(statement, index) else {
            return ""
        }
        return String(cString: text)
    }

    private func bind(_ statement: OpaquePointer, values: [BindValue]) {
        for (index, value) in values.enumerated() {
            let position = Int32(index + 1)
            switch value {
            case .text(let text):
                sqlite3_bind_text(statement, position, text, -1, SQLITE_TRANSIENT)
            case .int(let number):
                sqlite3_bind_int(statement, position, Int32(number))
            }
        }
    }
}

private enum BindValue {
    case text(String)
    case int(Int)
}

private let SQLITE_TRANSIENT = unsafeBitCast(-1, to: sqlite3_destructor_type.self)
