import Foundation

enum ToolFilter: String, CaseIterable, Identifiable {
    case all
    case claude
    case codex

    var id: String { rawValue }

    var displayName: String {
        switch self {
        case .all:
            return "全部工具"
        case .claude:
            return "Claude Code"
        case .codex:
            return "Codex"
        }
    }
}

struct SessionFilterInput: Equatable {
    var search: String = ""
    var project: String = ""
    var tool: ToolFilter = .all
    var since: Date? = nil
    var until: Date? = nil
    var limit: Int? = nil
}

struct Session: Identifiable, Equatable {
    let id: Int64
    let tool: String
    let sessionId: String
    let projectPath: String
    let startTime: String
    let lastTime: String
    let messageCount: Int
    let firstMessage: String
    let filePath: String
    let fileSize: Int
    let model: String
    let summary: String

    var toolDisplayName: String {
        switch tool.lowercased() {
        case "claude":
            return "Claude Code"
        case "codex":
            return "Codex"
        default:
            return tool
        }
    }

    var resumeCommand: String {
        switch tool.lowercased() {
        case "claude":
            return "claude -r \(sessionId)"
        case "codex":
            return "codex --resume \(sessionId)"
        default:
            return ""
        }
    }

    var formattedFileSize: String {
        if fileSize < 1024 {
            return "\(fileSize) B"
        }
        if fileSize < 1024 * 1024 {
            return String(format: "%.1f KB", Double(fileSize) / 1024.0)
        }
        return String(format: "%.1f MB", Double(fileSize) / 1024.0 / 1024.0)
    }
}

enum DateFormats {
    static let isoFormatter: DateFormatter = {
        let formatter = DateFormatter()
        formatter.locale = Locale(identifier: "en_US_POSIX")
        formatter.timeZone = TimeZone(secondsFromGMT: 0)
        formatter.dateFormat = "yyyy-MM-dd'T'HH:mm:ss"
        return formatter
    }()

    static let displayFormatter: DateFormatter = {
        let formatter = DateFormatter()
        formatter.locale = Locale.current
        formatter.dateFormat = "yyyy-MM-dd HH:mm"
        return formatter
    }()

    static func toIsoString(_ date: Date, endOfDay: Bool) -> String {
        if endOfDay {
            let calendar = Calendar.current
            let components = calendar.dateComponents([.year, .month, .day], from: date)
            if let base = calendar.date(from: components),
               let end = calendar.date(byAdding: DateComponents(hour: 23, minute: 59, second: 59), to: base) {
                return isoFormatter.string(from: end)
            }
        }
        return isoFormatter.string(from: date)
    }

    static func displayString(_ value: String) -> String {
        if value.isEmpty {
            return "未知"
        }

        // 处理带毫秒的 ISO 格式: "2026-01-15T01:26:23.217000"
        // 移除毫秒部分，只保留到秒
        let cleanValue = value.components(separatedBy: ".").first ?? value

        if let date = isoFormatter.date(from: cleanValue) {
            return displayFormatter.string(from: date)
        }
        return "未知"
    }
}
