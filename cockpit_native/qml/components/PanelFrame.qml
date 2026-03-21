import QtQuick 2.15

Rectangle {
    id: frame

    property var shellWindow: null
    property color panelColor: shellWindow ? shellWindow.panelColor : "#121d2d"
    property color borderTone: shellWindow ? shellWindow.borderSoft : "#334961"
    property color accentTone: shellWindow ? shellWindow.accentBlue : "#73b6ff"
    readonly property int innerInset: shellWindow ? shellWindow.scaled(10) : 10
    readonly property int chromeInset: shellWindow ? shellWindow.scaled(4) : 4
    readonly property int accentBandHeight: shellWindow ? shellWindow.scaled(3) : 3
    readonly property int cornerCapWidth: shellWindow ? shellWindow.scaled(132) : 132
    readonly property int cornerCapHeight: shellWindow ? shellWindow.scaled(58) : 58
    readonly property color topWash: Qt.lighter(frame.panelColor, 1.08)
    readonly property color bottomWash: Qt.darker(frame.panelColor, 1.18)
    readonly property color deepTone: Qt.darker(frame.panelColor, 1.32)
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
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        height: Math.max(parent.height * 0.42, frame.radius * 2.2)
        radius: parent.radius
        gradient: Gradient {
            GradientStop { position: 0.0; color: "#00000000" }
            GradientStop { position: 0.4; color: "#0d000000" }
            GradientStop { position: 1.0; color: frame.deepTone }
        }
        opacity: 0.84
    }

    Rectangle {
        anchors.fill: parent
        radius: parent.radius
        gradient: Gradient {
            GradientStop { position: 0.0; color: "#14ffffff" }
            GradientStop { position: 0.18; color: "#09ffffff" }
            GradientStop { position: 0.48; color: "transparent" }
            GradientStop { position: 1.0; color: "#34000000" }
        }
        opacity: 0.62
    }

    Rectangle {
        width: frame.cornerCapWidth
        height: frame.cornerCapHeight
        radius: shellWindow ? shellWindow.edgeRadius : 12
        color: frame.deepTone
        opacity: 0.86
        rotation: -12
        x: -width * 0.16
        y: -height * 0.44
    }

    Rectangle {
        width: frame.cornerCapWidth
        height: frame.cornerCapHeight
        radius: shellWindow ? shellWindow.edgeRadius : 12
        color: frame.deepTone
        opacity: 0.86
        rotation: 12
        x: parent.width - (width * 0.84)
        y: -height * 0.44
    }

    Rectangle {
        anchors.top: parent.top
        anchors.horizontalCenter: parent.horizontalCenter
        width: Math.min(parent.width * 0.4, shellWindow ? shellWindow.scaled(520) : 520)
        height: shellWindow ? shellWindow.scaled(24) : 24
        radius: height / 2
        gradient: Gradient {
            orientation: Gradient.Horizontal
            GradientStop { position: 0.0; color: "#00000000" }
            GradientStop { position: 0.2; color: "#12ffffff" }
            GradientStop { position: 0.5; color: "#22ffffff" }
            GradientStop { position: 0.8; color: "#12ffffff" }
            GradientStop { position: 1.0; color: "#00000000" }
        }
        opacity: 0.7
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
            GradientStop { position: 0.0; color: "#0dffffff" }
            GradientStop { position: 0.34; color: "#04ffffff" }
            GradientStop { position: 1.0; color: "#00ffffff" }
        }
        opacity: 0.74
    }

    Rectangle {
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.leftMargin: frame.chromeInset
        anchors.rightMargin: frame.chromeInset
        height: frame.accentBandHeight
        radius: frame.accentBandHeight / 2
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
        border.color: "#08ffffff"
        border.width: 1
    }

    Rectangle {
        anchors.fill: parent
        anchors.margins: frame.chromeInset
        radius: Math.max(2, parent.radius - frame.chromeInset)
        color: "transparent"
        border.color: Qt.rgba(frame.borderTone.r, frame.borderTone.g, frame.borderTone.b, 0.28)
        border.width: 1
    }

    Rectangle {
        anchors.fill: parent
        anchors.margins: frame.innerInset
        radius: Math.max(2, parent.radius - frame.innerInset)
        color: "transparent"
        border.color: "#09ffffff"
        border.width: 1
        opacity: 0.72
    }
}
