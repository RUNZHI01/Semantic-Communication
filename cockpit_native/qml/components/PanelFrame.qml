import QtQuick 2.15

Rectangle {
    id: frame

    property var shellWindow: null
    property color panelColor: shellWindow ? shellWindow.panelColor : "#121d2d"
    property color borderTone: shellWindow ? shellWindow.borderSoft : "#334961"
    property color accentTone: shellWindow ? shellWindow.accentBlue : "#73b6ff"
    readonly property int innerInset: shellWindow ? shellWindow.scaled(10) : 10
    readonly property int accentBandHeight: shellWindow ? shellWindow.scaled(3) : 3
    readonly property color topWash: Qt.lighter(frame.panelColor, 1.08)
    readonly property color bottomWash: Qt.darker(frame.panelColor, 1.18)
    readonly property color rimTone: Qt.lighter(frame.borderTone, 1.04)
    readonly property color glowTone: Qt.lighter(frame.accentTone, 1.08)

    radius: shellWindow ? shellWindow.panelRadius : 22
    color: "transparent"
    border.width: 0
    clip: true

    Rectangle {
        anchors.fill: parent
        radius: parent.radius
        gradient: Gradient {
            GradientStop { position: 0.0; color: frame.topWash }
            GradientStop { position: 0.28; color: Qt.lighter(frame.panelColor, 1.03) }
            GradientStop { position: 0.64; color: frame.panelColor }
            GradientStop { position: 1.0; color: frame.bottomWash }
        }
    }

    Rectangle {
        anchors.fill: parent
        radius: parent.radius
        gradient: Gradient {
            GradientStop { position: 0.0; color: "#ffffff14" }
            GradientStop { position: 0.18; color: "#ffffff09" }
            GradientStop { position: 0.48; color: "transparent" }
            GradientStop { position: 1.0; color: "#00000034" }
        }
        opacity: 0.62
    }

    Rectangle {
        width: parent.width * 0.86
        height: parent.height * 0.5
        radius: width / 2
        color: frame.accentTone
        opacity: 0.075
        x: -width * 0.18
        y: -height * 0.18
    }

    Rectangle {
        width: parent.width * 0.58
        height: parent.height * 0.42
        radius: width / 2
        color: frame.glowTone
        opacity: 0.045
        x: parent.width - (width * 0.8)
        y: parent.height - (height * 0.74)
    }

    Rectangle {
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        height: parent.height * 0.32
        radius: parent.radius
        gradient: Gradient {
            GradientStop { position: 0.0; color: "#ffffff0d" }
            GradientStop { position: 0.34; color: "#ffffff04" }
            GradientStop { position: 1.0; color: "#ffffff00" }
        }
        opacity: 0.74
    }

    Rectangle {
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        height: frame.accentBandHeight
        gradient: Gradient {
            orientation: Gradient.Horizontal
            GradientStop { position: 0.0; color: "transparent" }
            GradientStop { position: 0.2; color: Qt.rgba(frame.accentTone.r, frame.accentTone.g, frame.accentTone.b, 0.34) }
            GradientStop { position: 0.5; color: Qt.rgba(frame.accentTone.r, frame.accentTone.g, frame.accentTone.b, 0.86) }
            GradientStop { position: 0.8; color: Qt.rgba(frame.accentTone.r, frame.accentTone.g, frame.accentTone.b, 0.34) }
            GradientStop { position: 1.0; color: "transparent" }
        }
        opacity: 0.92
    }

    Rectangle {
        anchors.fill: parent
        radius: parent.radius
        color: "transparent"
        border.color: frame.rimTone
        border.width: 1
    }

    Rectangle {
        anchors.fill: parent
        anchors.margins: 1
        radius: parent.radius - 1
        color: "transparent"
        border.color: "#ffffff08"
        border.width: 1
    }

    Rectangle {
        anchors.fill: parent
        anchors.margins: frame.innerInset
        radius: Math.max(2, parent.radius - frame.innerInset)
        color: "transparent"
        border.color: "#ffffff09"
        border.width: 1
        opacity: 0.72
    }
}
