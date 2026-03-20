import QtQuick 2.15
import QtQuick.Controls 2.15

Rectangle {
    id: frame
    property var shellWindow: null
    property string title: ""
    property color panelColor: "#0c1720"
    property color borderTone: "#1b4f61"
    property color accentTone: "#2aa6c1"

    radius: shellWindow ? shellWindow.panelRadius : 16
    color: panelColor
    border.color: borderTone
    border.width: 1
    clip: true

    Rectangle {
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        height: 1
        color: accentTone
        opacity: 0.34
    }

    Rectangle {
        anchors.fill: parent
        radius: parent.radius
        color: "transparent"
        border.width: 1
        border.color: "#0d2a38"
        opacity: 0.7
    }
}
