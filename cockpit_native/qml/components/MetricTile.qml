import QtQuick 2.15
import QtQuick.Layouts 1.15

Rectangle {
    id: root

    property var shellWindow: null
    property string label: ""
    property string value: ""
    property string detail: ""
    property string tone: "neutral"
    property bool prominent: false

    radius: shellWindow ? shellWindow.cardRadius : 16
    color: shellWindow ? shellWindow.surfaceQuiet : "#0f161d"
    border.color: shellWindow ? shellWindow.toneColor(tone) : "#86c7d4"
    border.width: 1
    implicitHeight: body.implicitHeight + ((shellWindow ? shellWindow.cardPadding : 14) * 2)

    Rectangle {
        anchors.fill: parent
        radius: parent.radius
        gradient: Gradient {
            GradientStop { position: 0.0; color: "#12ffffff" }
            GradientStop { position: 0.4; color: "#04ffffff" }
            GradientStop { position: 1.0; color: "#00000000" }
        }
        opacity: 0.3
    }

    ColumnLayout {
        id: body
        anchors.fill: parent
        anchors.margins: shellWindow ? shellWindow.cardPadding : 14
        spacing: shellWindow ? shellWindow.scaled(4) : 4

        Text {
            text: root.label
            color: shellWindow ? shellWindow.textMuted : "#6f7f8a"
            font.pixelSize: shellWindow ? shellWindow.captionSize : 10
            font.family: shellWindow ? shellWindow.monoFamily : "JetBrains Mono"
            font.letterSpacing: shellWindow ? shellWindow.scaled(0.6) : 0.6
        }

        Text {
            Layout.fillWidth: true
            text: root.value
            color: shellWindow ? shellWindow.textStrong : "#f5efe4"
            font.pixelSize: shellWindow
                ? shellWindow.bodyEmphasisSize + (root.prominent ? shellWindow.scaled(2) : 0)
                : (root.prominent ? 16 : 14)
            font.weight: Font.DemiBold
            font.family: shellWindow ? shellWindow.displayFamily : "Noto Serif CJK SC"
            wrapMode: Text.WordWrap
        }

        Text {
            visible: root.detail.length > 0
            Layout.fillWidth: true
            text: root.detail
            color: shellWindow ? shellWindow.textSecondary : "#9aa8b1"
            font.pixelSize: shellWindow ? shellWindow.bodySize : 13
            font.family: shellWindow ? shellWindow.uiFamily : "Noto Sans CJK SC"
            wrapMode: Text.WordWrap
        }
    }
}
