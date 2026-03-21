import QtQuick 2.15
import QtQuick.Layouts 1.15

Rectangle {
    id: root

    property var shellWindow: null
    property string label: ""
    property string value: ""
    property string tone: "neutral"
    property bool prominent: false

    radius: shellWindow ? shellWindow.edgeRadius : 12
    color: shellWindow ? shellWindow.toneFill(tone) : "#152029"
    border.color: shellWindow ? shellWindow.toneColor(tone) : "#86c7d4"
    border.width: 1
    implicitWidth: content.implicitWidth + ((shellWindow ? shellWindow.scaled(prominent ? 13 : 11) : 11) * 2)
    implicitHeight: content.implicitHeight + ((shellWindow ? shellWindow.scaled(prominent ? 10 : 8) : 8) * 2)

    Rectangle {
        anchors.left: parent.left
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        width: shellWindow ? shellWindow.scaled(prominent ? 3 : 2) : (prominent ? 3 : 2)
        radius: width / 2
        color: shellWindow ? shellWindow.toneColor(root.tone) : "#86c7d4"
        opacity: 0.82
    }

    ColumnLayout {
        id: content
        anchors.centerIn: parent
        spacing: shellWindow ? shellWindow.scaled(1) : 1

        Text {
            visible: root.label.length > 0
            text: root.label
            color: shellWindow ? shellWindow.textMuted : "#6f7f8a"
            font.pixelSize: shellWindow ? shellWindow.captionSize : 10
            font.family: shellWindow ? shellWindow.monoFamily : "JetBrains Mono"
            horizontalAlignment: Text.AlignLeft
        }

        Text {
            text: root.value
            color: shellWindow ? shellWindow.textStrong : "#f5efe4"
            font.pixelSize: shellWindow ? shellWindow.bodyEmphasisSize : 14
            font.weight: Font.DemiBold
            font.family: shellWindow ? shellWindow.uiFamily : "Noto Sans CJK SC"
            horizontalAlignment: Text.AlignLeft
        }
    }
}
