import QtQuick 2.15

Rectangle {
    id: frame
    property var shellWindow: null
    property color panelColor: shellWindow ? shellWindow.panelColor : "#091422"
    property color borderTone: shellWindow ? shellWindow.borderSoft : "#1a3f61"
    property color accentTone: shellWindow ? shellWindow.accentBlue : "#38b6ff"
    readonly property int chromeInset: shellWindow ? shellWindow.scaled(16) : 16
    readonly property color glowTone: Qt.lighter(frame.accentTone, 1.32)

    radius: shellWindow ? shellWindow.panelRadius : 18
    color: "transparent"
    border.width: 0
    clip: true

    Rectangle {
        anchors.fill: parent
        radius: parent.radius
        gradient: Gradient {
            GradientStop { position: 0.0; color: Qt.lighter(frame.panelColor, 1.2) }
            GradientStop { position: 0.12; color: Qt.lighter(frame.panelColor, 1.09) }
            GradientStop { position: 0.56; color: frame.panelColor }
            GradientStop { position: 1.0; color: Qt.darker(frame.panelColor, 1.18) }
        }
    }

    Rectangle {
        width: parent.width * 0.68
        height: parent.height * 0.72
        radius: width / 2
        color: frame.glowTone
        opacity: 0.12
        x: -width * 0.24
        y: -height * 0.28
    }

    Rectangle {
        width: parent.width * 0.58
        height: parent.height * 0.6
        radius: width / 2
        color: frame.glowTone
        opacity: 0.08
        x: parent.width - (width * 0.7)
        y: parent.height - (height * 0.62)
    }

    Rectangle {
        width: parent.width * 1.12
        height: parent.height * 0.42
        rotation: -8
        color: "#15476f"
        opacity: 0.08
        x: -parent.width * 0.08
        y: parent.height * 0.06
    }

    Rectangle {
        anchors.fill: parent
        radius: parent.radius
        gradient: Gradient {
            GradientStop { position: 0.0; color: "#17456b" }
            GradientStop { position: 0.08; color: "transparent" }
            GradientStop { position: 0.74; color: "transparent" }
            GradientStop { position: 1.0; color: "#050d17" }
        }
        opacity: 0.38
    }

    Rectangle {
        anchors.fill: parent
        radius: parent.radius
        gradient: Gradient {
            orientation: Gradient.Vertical
            GradientStop { position: 0.0; color: "#0a1422" }
            GradientStop { position: 0.18; color: "transparent" }
            GradientStop { position: 0.82; color: "transparent" }
            GradientStop { position: 1.0; color: "#02060d" }
        }
        opacity: 0.72
    }

    Rectangle {
        anchors.fill: parent
        radius: parent.radius
        color: "transparent"
        border.color: frame.borderTone
        border.width: 1
    }

    Rectangle {
        anchors.fill: parent
        anchors.margins: 1
        radius: parent.radius - 1
        color: "transparent"
        border.color: "#0c2237"
        border.width: 1
        opacity: 0.9
    }

    Rectangle {
        anchors.fill: parent
        anchors.margins: shellWindow ? shellWindow.scaled(10) : 10
        radius: Math.max(2, parent.radius - (shellWindow ? shellWindow.scaled(10) : 10))
        color: "transparent"
        border.color: "#11314d"
        border.width: 1
        opacity: 0.48
    }

    Item {
        anchors.fill: parent
        opacity: 0.16

        Repeater {
            model: 7

            delegate: Rectangle {
                width: parent.width - (frame.chromeInset * 2)
                height: 1
                x: frame.chromeInset
                y: frame.chromeInset + index * ((parent.height - (frame.chromeInset * 2)) / Math.max(1, model - 1))
                color: index === 0 || index === model - 1 ? Qt.lighter(frame.borderTone, 1.2) : frame.borderTone
                opacity: index === 0 || index === model - 1 ? 0.52 : 0.28
            }
        }

        Repeater {
            model: 9

            delegate: Rectangle {
                width: 1
                height: parent.height - (frame.chromeInset * 2)
                x: frame.chromeInset + index * ((parent.width - (frame.chromeInset * 2)) / Math.max(1, model - 1))
                y: frame.chromeInset
                color: index === 0 || index === model - 1 ? Qt.lighter(frame.borderTone, 1.2) : frame.borderTone
                opacity: index === 0 || index === model - 1 ? 0.42 : 0.24
            }
        }
    }

    Rectangle {
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        height: shellWindow ? shellWindow.scaled(4) : 4
        gradient: Gradient {
            GradientStop { position: 0.0; color: "transparent" }
            GradientStop { position: 0.14; color: frame.accentTone }
            GradientStop { position: 0.5; color: Qt.lighter(frame.glowTone, 1.08) }
            GradientStop { position: 0.86; color: frame.accentTone }
            GradientStop { position: 1.0; color: "transparent" }
        }
        opacity: 0.9
    }

    Rectangle {
        anchors.left: parent.left
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        anchors.margins: 1
        width: shellWindow ? shellWindow.scaled(6) : 6
        radius: width / 2
        gradient: Gradient {
            GradientStop { position: 0.0; color: "transparent" }
            GradientStop { position: 0.16; color: Qt.lighter(frame.accentTone, 1.18) }
            GradientStop { position: 0.62; color: frame.accentTone }
            GradientStop { position: 1.0; color: "transparent" }
        }
        opacity: 0.2
    }

    Rectangle {
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        anchors.margins: shellWindow ? shellWindow.scaled(8) : 8
        width: 1
        color: frame.glowTone
        opacity: 0.12
    }

    Rectangle {
        anchors.left: parent.left
        anchors.bottom: parent.bottom
        width: parent.width * 0.36
        height: 1
        color: frame.accentTone
        opacity: 0.18
    }

    Rectangle {
        width: shellWindow ? shellWindow.scaled(52) : 52
        height: 2
        color: frame.accentTone
        anchors.left: parent.left
        anchors.top: parent.top
        anchors.leftMargin: frame.chromeInset
        anchors.topMargin: frame.chromeInset
    }

    Rectangle {
        width: 2
        height: shellWindow ? shellWindow.scaled(52) : 52
        color: frame.accentTone
        anchors.left: parent.left
        anchors.top: parent.top
        anchors.leftMargin: frame.chromeInset
        anchors.topMargin: frame.chromeInset
    }

    Rectangle {
        width: shellWindow ? shellWindow.scaled(40) : 40
        height: 2
        color: frame.glowTone
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        anchors.rightMargin: frame.chromeInset
        anchors.bottomMargin: frame.chromeInset
        opacity: 0.92
    }

    Rectangle {
        width: 2
        height: shellWindow ? shellWindow.scaled(40) : 40
        color: frame.glowTone
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        anchors.rightMargin: frame.chromeInset
        anchors.bottomMargin: frame.chromeInset
        opacity: 0.92
    }

    Rectangle {
        width: shellWindow ? shellWindow.scaled(64) : 64
        height: shellWindow ? shellWindow.scaled(6) : 6
        radius: height / 2
        color: frame.glowTone
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.rightMargin: frame.chromeInset
        anchors.topMargin: frame.chromeInset
        opacity: 0.34
    }

    Repeater {
        model: [
            { "x": frame.chromeInset - 2, "y": frame.chromeInset - 2 },
            { "x": frame.width - frame.chromeInset - (shellWindow ? shellWindow.scaled(8) : 8), "y": frame.chromeInset - 2 },
            { "x": frame.chromeInset - 2, "y": frame.height - frame.chromeInset - (shellWindow ? shellWindow.scaled(8) : 8) },
            { "x": frame.width - frame.chromeInset - (shellWindow ? shellWindow.scaled(8) : 8), "y": frame.height - frame.chromeInset - (shellWindow ? shellWindow.scaled(8) : 8) }
        ]

        delegate: Rectangle {
            width: shellWindow ? shellWindow.scaled(8) : 8
            height: width
            radius: 2
            x: modelData["x"]
            y: modelData["y"]
            color: frame.glowTone
            opacity: 0.44
        }
    }
}
