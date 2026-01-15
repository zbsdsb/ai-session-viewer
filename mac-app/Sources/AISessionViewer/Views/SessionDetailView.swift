import SwiftUI
import AppKit

struct SessionDetailView: View {
    let session: Session

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 12) {
                Text(session.firstMessage.isEmpty ? "(无标题)" : session.firstMessage)
                    .font(.title2)

                VStack(alignment: .leading, spacing: 6) {
                    DetailRow(title: "工具", value: session.toolDisplayName)
                    DetailRow(title: "开始时间", value: DateFormats.displayString(session.startTime))
                    DetailRow(title: "最后时间", value: DateFormats.displayString(session.lastTime))
                    DetailRow(title: "消息数量", value: "\(session.messageCount)")
                    DetailRow(title: "模型", value: session.model.isEmpty ? "未知" : session.model)
                    DetailRow(title: "文件大小", value: session.formattedFileSize)
                    DetailRow(title: "项目路径", value: session.projectPath.isEmpty ? "(无项目)" : session.projectPath)
                    DetailRow(title: "会话文件", value: session.filePath)
                }

                Divider()

                VStack(alignment: .leading, spacing: 8) {
                    Text("恢复命令")
                        .font(.headline)
                    HStack {
                        Text(session.resumeCommand)
                            .font(.system(.body, design: .monospaced))
                            .textSelection(.enabled)
                            .lineLimit(nil)
                            .layoutPriority(1)
                        Spacer()
                        Button("复制") {
                            NSPasteboard.general.clearContents()
                            NSPasteboard.general.setString(session.resumeCommand, forType: .string)
                        }
                    }
                }

                Divider()

                VStack(alignment: .leading, spacing: 8) {
                    Text("会话摘要")
                        .font(.headline)
                    Text(session.summary.isEmpty ? "(无摘要)" : session.summary)
                        .textSelection(.enabled)
                }
            }
            .padding(16)
        }
    }
}

private struct DetailRow: View {
    let title: String
    let value: String

    var body: some View {
        HStack(alignment: .top, spacing: 8) {
            Text(title)
                .frame(width: 90, alignment: .leading)
                .foregroundColor(.secondary)
            Text(value)
                .textSelection(.enabled)
                .lineLimit(nil)
                .fixedSize(horizontal: false, vertical: true)
            Spacer()
        }
    }
}
