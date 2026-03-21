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
    readonly property color topFill: shellWindow ? Qt.lighter(shellWindow.surfaceGlass, 1.02) : "#233240"
    readonly property color bottomFill: shellWindow ? Qt.darker(shellWindow.surfaceRaised, 1.02) : "#17222c"

    radius: shellWindow ? shellWindow.edgeRadius : 12
    gradient: Gradient {
        GradientStop { position: 0.0; color: Qt.rgba(root.topFill.r, root.topFill.g, root.topFill.b, prominent ? 0.84 : 0.74) }
        GradientStop { position: 0.42; color: shellWindow
            ? Qt.rgba(shellWindow.surfaceQuiet.r, shellWindow.surfaceQuiet.g, shellWindow.surfaceQuiet.b, prominent ? 0.78 : 0.66)
            : "#152029" }
        GradientStop { position: 1.0; color: Qt.rgba(root.bottomFill.r, root.bottomFill.g, root.bottomFill.b, prominent ? 0.88 : 0.78) }
    }
    border.color: shellWindow ? Qt.rgba(accentColor.r, accentColor.g, accentColor.b, prominent ? 0.62 : 0.34) : "#86c7d4"
    border.width: 1
    implicitWidth: content.implicitWidth + ((shellWindow ? shellWindow.scaled(prominent ? 13 : 10) : 10) * 2)
    implicitHeight: content.implicitHeight + ((shellWindow ? shellWindow.scaled(prominent ? 8 : 6) : 6) * 2)

    Rectangle {
        anchors.fill: parent
        radius: parent.radius
        gradient: Gradient {
            GradientStop { position: 0.0; color: "#12ffffff" }
            GradientStop { position: 0.36; color: "#04ffffff" }
            GradientStop { position: 1.0; color: "#00000000" }
        }
        opacity: prominent ? 0.22 : 0.12
    }

    Rectangle {
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.leftMargin: shellWindow ? shellWindow.scaled(8) : 8
        anchors.rightMargin: shellWindow ? shellWindow.scaled(8) : 8
        height: shellWindow ? shellWindow.scaled(1) : 1
        radius: height / 2
        gradient: Gradient {
            orientation: Gradient.Horizontal
            GradientStop { position: 0.0; color: "transparent" }
            GradientStop { position: 0.16; color: Qt.rgba(accentColor.r, accentColor.g, accentColor.b, 0.16) }
            GradientStop { position: 0.5; color: Qt.rgba(accentColor.r, accentColor.g, accentColor.b, 0.76) }
            GradientStop { position: 0.84; color: Qt.rgba(accentColor.r, accentColor.g, accentColor.b, 0.16) }
            GradientStop { position: 1.0; color: "transparent" }
        }
        opacity: prominent ? 0.74 : 0.52
    }

    Rectangle {
        anchors.left: parent.left
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        anchors.topMargin: shellWindow ? shellWindow.scaled(6) : 6
        anchors.bottomMargin: shellWindow ? shellWindow.scaled(6) : 6
        width: shellWindow ? shellWindow.scaled(prominent ? 2 : 1) : (prominent ? 2 : 1)
        radius: width / 2
        color: accentColor
        opacity: prominent ? 0.76 : 0.58
    }

    Rectangle {
        anchors.fill: parent
        anchors.margins: 1
        radius: parent.radius - 1
        color: "transparent"
        border.color: "#0effffff"
        border.width: 1
        opacity: 0.34
    }

    ColumnLayout {
        id: content
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.verticalCenter: parent.verticalCenter
        anchors.leftMargin: shellWindow ? shellWindow.scaled(prominent ? 13 : 11) : 11
        anchors.rightMargin: shellWindow ? shellWindow.scaled(prominent ? 13 : 11) : 11
        spacing: shellWindow ? shellWindow.scaled(prominent ? 2 : 1) : 1

        Text {
            visible: root.label.length > 0
            text: root.label
            color: shellWindow ? shellWindow.textSecondary : "#6f7f8a"
            font.pixelSize: shellWindow ? shellWindow.captionSize : 10
            font.family: shellWindow ? shellWindow.monoFamily : "JetBrains Mono"
            font.letterSpacing: shellWindow ? shellWindow.scaled(0.5) : 0.5
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
            font.letterSpacing: shellWindow ? shellWindow.scaled(prominent ? 0.18 : 0.08) : 0.1
            horizontalAlignment: Text.AlignLeft
        }
    }
}
