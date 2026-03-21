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

    readonly property color accentColor: shellWindow ? shellWindow.toneColor(tone) : "#86c7d4"
    readonly property color topFill: shellWindow ? Qt.lighter(shellWindow.surfaceRaised, 1.04) : "#1a2430"
    readonly property color bottomFill: shellWindow ? Qt.darker(shellWindow.surfaceQuiet, 1.08) : "#0c151d"

    radius: shellWindow ? shellWindow.cardRadius : 16
    gradient: Gradient {
        GradientStop { position: 0.0; color: Qt.rgba(root.topFill.r, root.topFill.g, root.topFill.b, prominent ? 0.97 : 0.94) }
        GradientStop { position: 0.38; color: shellWindow
            ? Qt.rgba(shellWindow.surfaceQuiet.r, shellWindow.surfaceQuiet.g, shellWindow.surfaceQuiet.b, prominent ? 0.95 : 0.9)
            : "#0f161d" }
        GradientStop { position: 1.0; color: Qt.rgba(root.bottomFill.r, root.bottomFill.g, root.bottomFill.b, 0.98) }
    }
    border.color: shellWindow ? Qt.rgba(accentColor.r, accentColor.g, accentColor.b, prominent ? 0.76 : 0.54) : "#86c7d4"
    border.width: 1
    implicitHeight: body.implicitHeight + ((shellWindow ? shellWindow.cardPadding : 14) * 2)

    Rectangle {
        anchors.fill: parent
        radius: parent.radius
        gradient: Gradient {
            GradientStop { position: 0.0; color: "#12ffffff" }
            GradientStop { position: 0.28; color: "#05ffffff" }
            GradientStop { position: 1.0; color: "#00000000" }
        }
        opacity: prominent ? 0.38 : 0.28
    }

    Rectangle {
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.leftMargin: shellWindow ? shellWindow.scaled(10) : 10
        anchors.rightMargin: shellWindow ? shellWindow.scaled(10) : 10
        height: shellWindow ? shellWindow.scaled(2) : 2
        radius: height / 2
        gradient: Gradient {
            orientation: Gradient.Horizontal
            GradientStop { position: 0.0; color: "transparent" }
            GradientStop { position: 0.16; color: Qt.rgba(accentColor.r, accentColor.g, accentColor.b, 0.14) }
            GradientStop { position: 0.5; color: Qt.rgba(accentColor.r, accentColor.g, accentColor.b, 0.74) }
            GradientStop { position: 0.84; color: Qt.rgba(accentColor.r, accentColor.g, accentColor.b, 0.14) }
            GradientStop { position: 1.0; color: "transparent" }
        }
        opacity: 0.88
    }

    Rectangle {
        anchors.left: parent.left
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        anchors.leftMargin: shellWindow ? shellWindow.scaled(6) : 6
        anchors.topMargin: shellWindow ? shellWindow.scaled(8) : 8
        anchors.bottomMargin: shellWindow ? shellWindow.scaled(8) : 8
        width: shellWindow ? shellWindow.scaled(prominent ? 3 : 2) : (prominent ? 3 : 2)
        radius: width / 2
        color: accentColor
        opacity: 0.84
    }

    Rectangle {
        width: parent.width * 0.34
        height: parent.height * 0.64
        radius: width / 2
        color: accentColor
        opacity: prominent ? 0.08 : 0.05
        x: parent.width - (width * 0.74)
        y: -height * 0.16
    }

    Rectangle {
        anchors.fill: parent
        anchors.margins: 1
        radius: parent.radius - 1
        color: "transparent"
        border.color: "#0affffff"
        border.width: 1
        opacity: 0.66
    }

    ColumnLayout {
        id: body
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        anchors.leftMargin: shellWindow ? shellWindow.cardPadding + shellWindow.scaled(4) : 18
        anchors.rightMargin: shellWindow ? shellWindow.cardPadding : 14
        anchors.topMargin: shellWindow ? shellWindow.cardPadding : 14
        anchors.bottomMargin: shellWindow ? shellWindow.cardPadding : 14
        spacing: shellWindow ? shellWindow.scaled(3) : 3

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
                ? shellWindow.bodyEmphasisSize + (root.prominent ? shellWindow.scaled(2) : shellWindow.scaled(1))
                : (root.prominent ? 16 : 14)
            font.weight: Font.DemiBold
            font.family: shellWindow ? shellWindow.displayFamily : "Noto Serif CJK SC"
            font.letterSpacing: shellWindow ? shellWindow.scaled(0.16) : 0.16
            wrapMode: Text.WordWrap
            maximumLineCount: prominent ? 3 : 2
            elide: Text.ElideRight
        }

        Text {
            visible: root.detail.length > 0
            Layout.fillWidth: true
            text: root.detail
            color: shellWindow ? shellWindow.textSecondary : "#9aa8b1"
            font.pixelSize: shellWindow ? shellWindow.captionSize + 1 : 12
            font.family: shellWindow ? shellWindow.uiFamily : "Noto Sans CJK SC"
            wrapMode: Text.WordWrap
            maximumLineCount: 2
            elide: Text.ElideRight
        }
    }
}
