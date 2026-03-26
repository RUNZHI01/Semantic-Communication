import QtQuick 2.15

Rectangle {
    id: frame

    property var shellWindow: null
    property color panelColor: shellWindow ? shellWindow.panelColor : "#1c1c26"
    property color borderTone: shellWindow ? shellWindow.borderSoft : "#2c2c3a"
    property color accentTone: shellWindow ? shellWindow.accentBlue : "#5080ff"

    radius: shellWindow ? shellWindow.panelRadius : 16
    color: panelColor
    border.color: Qt.rgba(borderTone.r, borderTone.g, borderTone.b, 0.5)
    border.width: 1
    clip: true

    Rectangle {
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.leftMargin: shellWindow ? shellWindow.scaled(12) : 12
        anchors.rightMargin: shellWindow ? shellWindow.scaled(12) : 12
        height: shellWindow ? shellWindow.scaled(2) : 2
        radius: height / 2
        gradient: Gradient {
            orientation: Gradient.Horizontal
            GradientStop { position: 0.0; color: "transparent" }
            GradientStop { position: 0.2; color: Qt.rgba(accentTone.r, accentTone.g, accentTone.b, 0.06) }
            GradientStop { position: 0.5; color: Qt.rgba(accentTone.r, accentTone.g, accentTone.b, 0.32) }
            GradientStop { position: 0.8; color: Qt.rgba(accentTone.r, accentTone.g, accentTone.b, 0.08) }
            GradientStop { position: 1.0; color: "transparent" }
        }
        opacity: 0.6
    }
}
