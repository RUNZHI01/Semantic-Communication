import QtQuick 2.15

Rectangle {
    id: frame

    property var shellWindow: null
    property color panelColor: shellWindow ? shellWindow.panelColor : "#121d2d"
    property color borderTone: shellWindow ? shellWindow.borderSoft : "#334961"
    property color accentTone: shellWindow ? shellWindow.accentBlue : "#73b6ff"
    readonly property int innerInset: shellWindow ? shellWindow.scaled(8) : 8
    readonly property int chromeInset: shellWindow ? shellWindow.scaled(4) : 4
    readonly property int accentBandHeight: shellWindow ? shellWindow.scaled(2) : 2
    readonly property color topWash: Qt.lighter(frame.panelColor, 1.1)
    readonly property color bottomWash: Qt.darker(frame.panelColor, 1.2)
    readonly property color deepTone: Qt.darker(frame.panelColor, 1.34)
    readonly property color rimTone: Qt.lighter(frame.borderTone, 1.03)
    readonly property color glowTone: Qt.lighter(frame.accentTone, 1.06)

    radius: shellWindow ? shellWindow.panelRadius : 22
    color: "transparent"
    border.width: 0
    clip: true

    Rectangle {
        anchors.fill: parent
        radius: parent.radius
        gradient: Gradient {
            GradientStop { position: 0.0; color: frame.topWash }
            GradientStop { position: 0.18; color: Qt.lighter(frame.panelColor, 1.05) }
            GradientStop { position: 0.62; color: frame.panelColor }
            GradientStop { position: 1.0; color: frame.bottomWash }
        }
    }

    Rectangle {
        width: parent.width * 0.72
        height: parent.height * 0.64
        radius: width / 2
        color: frame.accentTone
        opacity: 0.08
        x: -width * 0.2
        y: -height * 0.18
    }

    Rectangle {
        width: parent.width * 0.48
        height: parent.height * 0.44
        radius: width / 2
        color: frame.glowTone
        opacity: 0.05
        x: parent.width - (width * 0.84)
        y: parent.height - (height * 0.76)
    }

    Rectangle {
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        height: Math.max(parent.height * 0.4, frame.radius * 2.1)
        radius: parent.radius
        gradient: Gradient {
            GradientStop { position: 0.0; color: "#00000000" }
            GradientStop { position: 0.38; color: "#0b000000" }
            GradientStop { position: 1.0; color: frame.deepTone }
        }
        opacity: 0.8
    }

    Rectangle {
        anchors.fill: parent
        radius: parent.radius
        gradient: Gradient {
            GradientStop { position: 0.0; color: "#14ffffff" }
            GradientStop { position: 0.22; color: "#08ffffff" }
            GradientStop { position: 0.52; color: "transparent" }
            GradientStop { position: 1.0; color: "#2a000000" }
        }
        opacity: 0.58
    }

    Rectangle {
        width: parent.width * 0.28
        height: parent.height * 0.16
        radius: shellWindow ? shellWindow.edgeRadius : 12
        color: "#18000000"
        opacity: 1.0
        rotation: -10
        x: -width * 0.28
        y: -height * 0.32
    }

    Rectangle {
        width: parent.width * 0.22
        height: parent.height * 0.14
        radius: shellWindow ? shellWindow.edgeRadius : 12
        color: "#11000000"
        opacity: 1.0
        rotation: 12
        x: parent.width - (width * 0.72)
        y: -height * 0.26
    }

    Rectangle {
        anchors.top: parent.top
        anchors.horizontalCenter: parent.horizontalCenter
        width: Math.min(parent.width * 0.44, shellWindow ? shellWindow.scaled(520) : 520)
        height: shellWindow ? shellWindow.scaled(28) : 28
        radius: height / 2
        gradient: Gradient {
            orientation: Gradient.Horizontal
            GradientStop { position: 0.0; color: "#00000000" }
            GradientStop { position: 0.18; color: "#0dffffff" }
            GradientStop { position: 0.5; color: "#24ffffff" }
            GradientStop { position: 0.82; color: "#0dffffff" }
            GradientStop { position: 1.0; color: "#00000000" }
        }
        opacity: 0.54
    }

    Rectangle {
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        height: parent.height * 0.26
        radius: parent.radius
        gradient: Gradient {
            GradientStop { position: 0.0; color: "#0cffffff" }
            GradientStop { position: 0.34; color: "#03ffffff" }
            GradientStop { position: 1.0; color: "#00ffffff" }
        }
        opacity: 0.66
    }

    Rectangle {
        anchors.left: parent.left
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        anchors.leftMargin: frame.chromeInset
        anchors.topMargin: frame.chromeInset
        anchors.bottomMargin: frame.chromeInset
        width: shellWindow ? shellWindow.scaled(3) : 3
        radius: width / 2
        gradient: Gradient {
            orientation: Gradient.Vertical
            GradientStop { position: 0.0; color: "transparent" }
            GradientStop { position: 0.16; color: Qt.rgba(frame.accentTone.r, frame.accentTone.g, frame.accentTone.b, 0.22) }
            GradientStop { position: 0.46; color: Qt.rgba(frame.accentTone.r, frame.accentTone.g, frame.accentTone.b, 0.86) }
            GradientStop { position: 0.82; color: Qt.rgba(frame.accentTone.r, frame.accentTone.g, frame.accentTone.b, 0.28) }
            GradientStop { position: 1.0; color: "transparent" }
        }
        opacity: 0.92
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
            GradientStop { position: 0.18; color: Qt.rgba(frame.accentTone.r, frame.accentTone.g, frame.accentTone.b, 0.2) }
            GradientStop { position: 0.5; color: Qt.rgba(frame.accentTone.r, frame.accentTone.g, frame.accentTone.b, 0.82) }
            GradientStop { position: 0.82; color: Qt.rgba(frame.accentTone.r, frame.accentTone.g, frame.accentTone.b, 0.2) }
            GradientStop { position: 1.0; color: "transparent" }
        }
        opacity: 0.9
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
        border.color: Qt.rgba(frame.borderTone.r, frame.borderTone.g, frame.borderTone.b, 0.26)
        border.width: 1
    }

    Rectangle {
        anchors.fill: parent
        anchors.margins: frame.innerInset
        radius: Math.max(2, parent.radius - frame.innerInset)
        color: "transparent"
        border.color: "#08ffffff"
        border.width: 1
        opacity: 0.64
    }
}
