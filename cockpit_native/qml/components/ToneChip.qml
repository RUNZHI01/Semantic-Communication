import QtQuick 2.15
import QtQuick.Layouts 1.15

Rectangle {
    id: root

    property var shellWindow: null
    property string label: ""
    property string value: ""
    property string tone: "neutral"
    property bool prominent: false

    readonly property color accentColor: shellWindow ? shellWindow.toneColor(tone) : "#86c7d4"

    radius: shellWindow ? shellWindow.edgeRadius + (prominent ? shellWindow.scaled(1) : 0) : 12
    color: shellWindow
        ? Qt.rgba(shellWindow.surfaceQuiet.r, shellWindow.surfaceQuiet.g, shellWindow.surfaceQuiet.b, prominent ? 0.92 : 0.82)
        : "#152029"
    border.color: shellWindow ? Qt.rgba(accentColor.r, accentColor.g, accentColor.b, prominent ? 0.82 : 0.54) : "#86c7d4"
    border.width: 1
    implicitWidth: content.implicitWidth + ((shellWindow ? shellWindow.scaled(prominent ? 14 : 11) : 11) * 2)
    implicitHeight: content.implicitHeight + ((shellWindow ? shellWindow.scaled(prominent ? 9 : 7) : 7) * 2)

    Rectangle {
        anchors.fill: parent
        radius: parent.radius
        gradient: Gradient {
            GradientStop { position: 0.0; color: "#12ffffff" }
            GradientStop { position: 0.36; color: "#04ffffff" }
            GradientStop { position: 1.0; color: "#00000000" }
        }
        opacity: prominent ? 0.42 : 0.28
    }

    Rectangle {
        anchors.left: parent.left
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        anchors.topMargin: shellWindow ? shellWindow.scaled(6) : 6
        anchors.bottomMargin: shellWindow ? shellWindow.scaled(6) : 6
        width: shellWindow ? shellWindow.scaled(prominent ? 3 : 2) : (prominent ? 3 : 2)
        radius: width / 2
        color: accentColor
        opacity: 0.82
    }

    ColumnLayout {
        id: content
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.verticalCenter: parent.verticalCenter
        anchors.leftMargin: shellWindow ? shellWindow.scaled(prominent ? 14 : 12) : 12
        anchors.rightMargin: shellWindow ? shellWindow.scaled(prominent ? 14 : 12) : 12
        spacing: shellWindow ? shellWindow.scaled(prominent ? 2 : 1) : 1

        Text {
            visible: root.label.length > 0
            text: root.label
            color: shellWindow ? Qt.lighter(shellWindow.textMuted, prominent ? 1.04 : 1.0) : "#6f7f8a"
            font.pixelSize: shellWindow ? shellWindow.captionSize : 10
            font.family: shellWindow ? shellWindow.monoFamily : "JetBrains Mono"
            font.letterSpacing: shellWindow ? shellWindow.scaled(0.6) : 0.6
            horizontalAlignment: Text.AlignLeft
        }

        Text {
            text: root.value
            color: shellWindow ? shellWindow.textStrong : "#f5efe4"
            font.pixelSize: shellWindow
                ? shellWindow.bodyEmphasisSize + (prominent ? shellWindow.scaled(1) : 0)
                : 14
            font.weight: Font.DemiBold
            font.family: shellWindow ? (prominent ? shellWindow.displayFamily : shellWindow.uiFamily) : "Noto Sans CJK SC"
            horizontalAlignment: Text.AlignLeft
        }
    }
}
