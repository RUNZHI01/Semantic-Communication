import QtQuick 2.15

Rectangle {
    id: frame
    property var shellWindow: null
    property color panelColor: shellWindow ? shellWindow.panelColor : "#091422"
    property color borderTone: shellWindow ? shellWindow.borderSoft : "#1a3f61"
    property color accentTone: shellWindow ? shellWindow.accentBlue : "#38b6ff"
    readonly property int chromeInset: shellWindow ? shellWindow.scaled(16) : 16
    readonly property int innerInset: shellWindow ? shellWindow.scaled(9) : 9
    readonly property int headerBandHeight: shellWindow ? shellWindow.scaled(34) : 34
    readonly property int rimInset: shellWindow ? shellWindow.scaled(20) : 20
    readonly property int traceInset: shellWindow ? shellWindow.scaled(26) : 26
    readonly property color glowTone: Qt.lighter(frame.accentTone, 1.28)
    readonly property color shadowTone: Qt.darker(frame.panelColor, 1.22)
    readonly property color ambientTone: Qt.lighter(frame.borderTone, 1.12)

    radius: shellWindow ? shellWindow.panelRadius : 18
    color: "transparent"
    border.width: 0
    clip: true

    Rectangle {
        anchors.fill: parent
        radius: parent.radius
        gradient: Gradient {
            GradientStop { position: 0.0; color: Qt.lighter(frame.panelColor, 1.18) }
            GradientStop { position: 0.18; color: Qt.lighter(frame.panelColor, 1.08) }
            GradientStop { position: 0.42; color: Qt.lighter(frame.panelColor, 1.02) }
            GradientStop { position: 0.62; color: frame.panelColor }
            GradientStop { position: 1.0; color: frame.shadowTone }
        }
    }

    Rectangle {
        anchors.fill: parent
        radius: parent.radius
        gradient: Gradient {
            GradientStop { position: 0.0; color: "#214c7100" }
            GradientStop { position: 0.18; color: "#1a4b7224" }
            GradientStop { position: 0.52; color: "transparent" }
            GradientStop { position: 1.0; color: "#010409aa" }
        }
    }

    Rectangle {
        anchors.left: parent.left
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        width: frame.rimInset
        gradient: Gradient {
            orientation: Gradient.Horizontal
            GradientStop { position: 0.0; color: "#050d1600" }
            GradientStop { position: 0.4; color: "#0c203120" }
            GradientStop { position: 1.0; color: "#173a5518" }
        }
        opacity: 0.74
    }

    Rectangle {
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        width: frame.rimInset
        gradient: Gradient {
            orientation: Gradient.Horizontal
            GradientStop { position: 0.0; color: "#173a5516" }
            GradientStop { position: 0.6; color: "#09162414" }
            GradientStop { position: 1.0; color: "#040a1200" }
        }
        opacity: 0.68
    }

    Rectangle {
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        height: frame.headerBandHeight
        gradient: Gradient {
            GradientStop { position: 0.0; color: "#1a446620" }
            GradientStop { position: 0.58; color: "#0b172400" }
            GradientStop { position: 1.0; color: "#03070c00" }
        }
        opacity: 0.9
    }

    Rectangle {
        width: parent.width * 0.84
        height: parent.height * 0.64
        radius: width / 2
        color: frame.glowTone
        opacity: 0.11
        x: -width * 0.18
        y: -height * 0.26
    }

    Rectangle {
        width: parent.width * 0.62
        height: parent.height * 0.54
        radius: width / 2
        color: frame.glowTone
        opacity: 0.06
        x: parent.width - (width * 0.72)
        y: parent.height - (height * 0.62)
    }

    Rectangle {
        width: parent.width * 1.16
        height: parent.height * 0.34
        rotation: -7
        color: "#17446a"
        opacity: 0.08
        x: -parent.width * 0.08
        y: parent.height * 0.08
    }

    Rectangle {
        width: parent.width * 1.08
        height: parent.height * 0.22
        rotation: 5
        color: "#0f3552"
        opacity: 0.08
        x: -parent.width * 0.04
        y: parent.height * 0.58
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
        border.color: "#0b2236"
        border.width: 1
        opacity: 0.94
    }

    Rectangle {
        anchors.fill: parent
        anchors.margins: frame.traceInset
        radius: Math.max(2, parent.radius - frame.traceInset)
        color: "transparent"
        border.color: "#153a58"
        border.width: 1
        opacity: 0.32
    }

    Rectangle {
        anchors.fill: parent
        anchors.margins: frame.innerInset
        radius: Math.max(2, parent.radius - frame.innerInset)
        color: "transparent"
        border.color: "#12324b"
        border.width: 1
        opacity: 0.54
    }

    Rectangle {
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.leftMargin: frame.traceInset
        anchors.rightMargin: frame.traceInset
        anchors.topMargin: frame.traceInset - (shellWindow ? shellWindow.scaled(8) : 8)
        height: 1
        color: frame.glowTone
        opacity: 0.16
    }

    Row {
        anchors.left: parent.left
        anchors.top: parent.top
        anchors.leftMargin: frame.chromeInset
        anchors.topMargin: frame.chromeInset - 1
        spacing: shellWindow ? shellWindow.scaled(6) : 6

        Repeater {
            model: 3

            delegate: Rectangle {
                width: shellWindow ? shellWindow.scaled(7) : 7
                height: width
                radius: width / 2
                color: index === 0 ? frame.accentTone : frame.ambientTone
                opacity: index === 0 ? 0.92 : (0.36 - (index * 0.06))
            }
        }
    }

    Row {
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.rightMargin: frame.chromeInset
        anchors.topMargin: frame.chromeInset - 1
        spacing: shellWindow ? shellWindow.scaled(6) : 6

        Repeater {
            model: 4

            delegate: Rectangle {
                width: (shellWindow ? shellWindow.scaled(20) : 20) - (index * (shellWindow ? shellWindow.scaled(2) : 2))
                height: shellWindow ? shellWindow.scaled(2) : 2
                radius: height / 2
                color: index === 0 ? frame.glowTone : frame.ambientTone
                opacity: index === 0 ? 0.92 : (0.42 - (index * 0.06))
            }
        }
    }

    Item {
        anchors.fill: parent
        opacity: 0.12

        Repeater {
            model: 9

            delegate: Rectangle {
                width: parent.width - (frame.chromeInset * 2)
                height: 1
                x: frame.chromeInset
                y: frame.chromeInset + index * ((parent.height - (frame.chromeInset * 2)) / Math.max(1, model - 1))
                color: index === 0 || index === model - 1 ? Qt.lighter(frame.borderTone, 1.18) : frame.borderTone
                opacity: index === 0 || index === model - 1 ? 0.44 : 0.18
            }
        }

        Repeater {
            model: 11

            delegate: Rectangle {
                width: 1
                height: parent.height - (frame.chromeInset * 2)
                x: frame.chromeInset + index * ((parent.width - (frame.chromeInset * 2)) / Math.max(1, model - 1))
                y: frame.chromeInset
                color: index === 0 || index === model - 1 ? Qt.lighter(frame.borderTone, 1.16) : frame.borderTone
                opacity: index === 0 || index === model - 1 ? 0.4 : 0.16
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
            GradientStop { position: 0.5; color: Qt.lighter(frame.glowTone, 1.06) }
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
            GradientStop { position: 0.14; color: Qt.lighter(frame.accentTone, 1.12) }
            GradientStop { position: 0.58; color: frame.accentTone }
            GradientStop { position: 1.0; color: "transparent" }
        }
        opacity: 0.28
    }

    Rectangle {
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        anchors.margins: shellWindow ? shellWindow.scaled(10) : 10
        width: 1
        color: frame.glowTone
        opacity: 0.14
    }

    Rectangle {
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        anchors.leftMargin: frame.chromeInset
        anchors.rightMargin: frame.chromeInset
        height: 1
        color: frame.accentTone
        opacity: 0.14
    }

    Rectangle {
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        anchors.rightMargin: frame.traceInset
        anchors.topMargin: frame.traceInset
        anchors.bottomMargin: frame.traceInset
        width: 1
        color: frame.ambientTone
        opacity: 0.14
    }

    Rectangle {
        width: shellWindow ? shellWindow.scaled(62) : 62
        height: 2
        color: frame.accentTone
        anchors.left: parent.left
        anchors.top: parent.top
        anchors.leftMargin: frame.chromeInset
        anchors.topMargin: frame.chromeInset
        opacity: 0.96
    }

    Rectangle {
        width: 2
        height: shellWindow ? shellWindow.scaled(52) : 52
        color: frame.accentTone
        anchors.left: parent.left
        anchors.top: parent.top
        anchors.leftMargin: frame.chromeInset
        anchors.topMargin: frame.chromeInset
        opacity: 0.96
    }

    Rectangle {
        width: shellWindow ? shellWindow.scaled(42) : 42
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
        height: shellWindow ? shellWindow.scaled(42) : 42
        color: frame.glowTone
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        anchors.rightMargin: frame.chromeInset
        anchors.bottomMargin: frame.chromeInset
        opacity: 0.92
    }

    Rectangle {
        width: shellWindow ? shellWindow.scaled(74) : 74
        height: shellWindow ? shellWindow.scaled(6) : 6
        radius: height / 2
        color: frame.glowTone
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.rightMargin: frame.chromeInset
        anchors.topMargin: frame.chromeInset
        opacity: 0.28
    }

    Rectangle {
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        anchors.leftMargin: frame.chromeInset
        anchors.rightMargin: frame.chromeInset
        anchors.bottomMargin: frame.chromeInset - 1
        height: shellWindow ? shellWindow.scaled(8) : 8
        radius: height / 2
        gradient: Gradient {
            orientation: Gradient.Horizontal
            GradientStop { position: 0.0; color: "#00000000" }
            GradientStop { position: 0.2; color: "#13314a30" }
            GradientStop { position: 0.5; color: "#1a4a6e46" }
            GradientStop { position: 0.8; color: "#13314a30" }
            GradientStop { position: 1.0; color: "#00000000" }
        }
        opacity: 0.58
    }

    Rectangle {
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        height: frame.headerBandHeight
        gradient: Gradient {
            GradientStop { position: 0.0; color: "#02060b00" }
            GradientStop { position: 0.34; color: "#0b1b2a18" }
            GradientStop { position: 0.72; color: "#14334b24" }
            GradientStop { position: 1.0; color: "#11273810" }
        }
        opacity: 0.82
    }

    Rectangle {
        anchors.left: parent.left
        anchors.top: parent.verticalCenter
        anchors.topMargin: -(shellWindow ? shellWindow.scaled(20) : 20)
        width: shellWindow ? shellWindow.scaled(28) : 28
        height: shellWindow ? shellWindow.scaled(2) : 2
        color: frame.glowTone
        opacity: 0.28
    }

    Rectangle {
        anchors.right: parent.right
        anchors.top: parent.verticalCenter
        anchors.topMargin: shellWindow ? shellWindow.scaled(20) : 20
        width: shellWindow ? shellWindow.scaled(28) : 28
        height: shellWindow ? shellWindow.scaled(2) : 2
        color: frame.glowTone
        opacity: 0.22
    }

    Row {
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: parent.bottom
        anchors.bottomMargin: frame.chromeInset - 1
        spacing: shellWindow ? shellWindow.scaled(7) : 7

        Repeater {
            model: 5

            delegate: Rectangle {
                width: (shellWindow ? shellWindow.scaled(18) : 18) - (index * (shellWindow ? shellWindow.scaled(2) : 2))
                height: shellWindow ? shellWindow.scaled(2) : 2
                radius: height / 2
                color: index === 2 ? frame.glowTone : frame.ambientTone
                opacity: index === 2 ? 0.82 : (0.42 - (index * 0.04))
            }
        }
    }

    Repeater {
        model: 4

        delegate: Rectangle {
            width: shellWindow ? shellWindow.scaled(8) : 8
            height: width
            radius: 2
            x: index % 2 === 0
                ? frame.chromeInset - 2
                : frame.width - frame.chromeInset - width + 2
            y: index < 2
                ? frame.chromeInset - 2
                : frame.height - frame.chromeInset - height + 2
            color: frame.glowTone
            opacity: 0.42
        }
    }
}
