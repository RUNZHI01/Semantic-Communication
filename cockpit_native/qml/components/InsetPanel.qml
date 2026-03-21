import QtQuick 2.15
import QtQuick.Layouts 1.15

Rectangle {
    id: root

    property var shellWindow: null
    property color accentColor: shellWindow ? shellWindow.accentIce : "#86c7d4"
    property color fillColor: shellWindow ? shellWindow.surfaceQuiet : "#0f161d"
    property int padding: shellWindow ? shellWindow.cardPadding : 14
    property bool prominent: false
    property bool showAccentRail: true

    default property alias contentData: content.data

    readonly property int accentWidth: shellWindow ? shellWindow.scaled(prominent ? 3 : 2) : (prominent ? 3 : 2)
    readonly property int contentLeftPadding: padding + (showAccentRail ? accentWidth + (shellWindow ? shellWindow.scaled(6) : 6) : 0)

    radius: shellWindow ? shellWindow.edgeRadius + shellWindow.scaled(1) : 13
    color: shellWindow
        ? Qt.rgba(fillColor.r, fillColor.g, fillColor.b, prominent ? 0.94 : 0.9)
        : fillColor
    border.color: shellWindow ? Qt.rgba(accentColor.r, accentColor.g, accentColor.b, prominent ? 0.62 : 0.44) : accentColor
    border.width: 1
    implicitHeight: content.implicitHeight + (padding * 2)

    Rectangle {
        anchors.fill: parent
        radius: parent.radius
        gradient: Gradient {
            GradientStop { position: 0.0; color: "#16ffffff" }
            GradientStop { position: 0.28; color: "#08ffffff" }
            GradientStop { position: 1.0; color: "#00000000" }
        }
        opacity: root.prominent ? 0.44 : 0.32
    }

    Rectangle {
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        height: Math.max(parent.height * 0.38, root.radius * 1.5)
        radius: parent.radius
        gradient: Gradient {
            GradientStop { position: 0.0; color: "#00000000" }
            GradientStop { position: 0.44; color: "#12000000" }
            GradientStop { position: 1.0; color: "#2b000000" }
        }
        opacity: 0.84
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
            GradientStop { position: 0.18; color: Qt.rgba(root.accentColor.r, root.accentColor.g, root.accentColor.b, 0.16) }
            GradientStop { position: 0.5; color: Qt.rgba(root.accentColor.r, root.accentColor.g, root.accentColor.b, 0.84) }
            GradientStop { position: 0.82; color: Qt.rgba(root.accentColor.r, root.accentColor.g, root.accentColor.b, 0.16) }
            GradientStop { position: 1.0; color: "transparent" }
        }
        opacity: 0.9
    }

    Rectangle {
        visible: root.showAccentRail
        anchors.left: parent.left
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        anchors.leftMargin: shellWindow ? shellWindow.scaled(7) : 7
        anchors.topMargin: shellWindow ? shellWindow.scaled(9) : 9
        anchors.bottomMargin: shellWindow ? shellWindow.scaled(9) : 9
        width: root.accentWidth
        radius: width / 2
        gradient: Gradient {
            GradientStop { position: 0.0; color: "transparent" }
            GradientStop { position: 0.16; color: Qt.rgba(root.accentColor.r, root.accentColor.g, root.accentColor.b, 0.2) }
            GradientStop { position: 0.48; color: Qt.rgba(root.accentColor.r, root.accentColor.g, root.accentColor.b, 0.9) }
            GradientStop { position: 0.82; color: Qt.rgba(root.accentColor.r, root.accentColor.g, root.accentColor.b, 0.24) }
            GradientStop { position: 1.0; color: "transparent" }
        }
    }

    Rectangle {
        width: parent.width * 0.44
        height: parent.height * 0.7
        radius: width / 2
        color: root.accentColor
        opacity: root.prominent ? 0.08 : 0.05
        x: -width * 0.16
        y: -height * 0.24
    }

    Rectangle {
        anchors.fill: parent
        anchors.margins: 1
        radius: parent.radius - 1
        color: "transparent"
        border.color: "#0effffff"
        border.width: 1
        opacity: 0.7
    }

    ColumnLayout {
        id: content
        anchors.fill: parent
        anchors.leftMargin: root.contentLeftPadding
        anchors.rightMargin: root.padding
        anchors.topMargin: root.padding
        anchors.bottomMargin: root.padding
        spacing: shellWindow ? shellWindow.compactGap : 8
    }
}
