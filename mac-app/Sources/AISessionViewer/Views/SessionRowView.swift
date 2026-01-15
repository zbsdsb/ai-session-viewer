import SwiftUI

struct SessionRowView: View {
    let session: Session

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            // 会话标题
            Text(session.firstMessage.isEmpty ? "(无标题)" : session.firstMessage)
                .lineLimit(2)
                .font(.headline)

            // 元数据行 - 使用 Label 和 SF Symbols 图标
            HStack(spacing: 12) {
                Label(session.toolDisplayName, systemImage: "hammer.fill")
                    .fixedSize(horizontal: true, vertical: false)
                    .lineLimit(1)
                Label(DateFormats.displayString(session.lastTime), systemImage: "clock")
                Label("\(session.messageCount) 条", systemImage: "bubble.left")
                Text(session.formattedFileSize)
            }
            .font(.caption)
            .foregroundColor(.secondary)

            // 项目路径 - 支持中间截断和 tooltip
            if !session.projectPath.isEmpty {
                Text(session.projectPath)
                    .font(.caption2)
                    .foregroundColor(.secondary.opacity(0.6))
                    .lineLimit(1)
                    .truncationMode(.middle)
                    .help(session.projectPath)
            }
        }
        .padding(.vertical, 6)
    }
}
