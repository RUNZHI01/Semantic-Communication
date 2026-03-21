import QtQuick 2.15
import QtQuick.Layouts 1.15

Item {
    id: root

    property var shellWindow: null
    property string eyebrow: ""
    property string title: ""
    property string subtitle: ""
    property color fillColor: shellWindow ? shellWindow.surfaceRaised : "#18212a"
    property color borderColor: shellWindow ? shellWindow.borderSubtle : "#2a3944"
    property color accentColor: shellWindow ? shellWindow.accentGold : "#c6ab7d"
    property int padding: shellWindow ? shellWindow.panelPadding : 18
    property int radius: shellWindow ? shellWindow.panelRadius : 22
    property int contentSpacing: shellWindow ? shellWindow.compactGap : 8

    readonly property bool hasHeader: eyebrow.length > 0 || title.length > 0 || subtitle.length > 0

    default property alias contentData: contentLayout.data

    implicitHeight: chrome.implicitHeight + (padding * 2)

    Rectangle {
        anchors.fill: parent
        radius: root.radius
        color: root.fillColor
        border.color: root.borderColor
        border.width: 1
    }

    Rectangle {
        anchors.fill: parent
        radius: root.radius
        gradient: Gradient {
            GradientStop { position: 0.0; color: "#12ffffff" }
            GradientStop { position: 0.26; color: "#05ffffff" }
            GradientStop { position: 1.0; color: "#00000000" }
        }
        opacity: 0.52
    }

    Rectangle {
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.leftMargin: shellWindow ? shellWindow.scaled(5) : 5
        anchors.rightMargin: shellWindow ? shellWindow.scaled(5) : 5
        anchors.topMargin: shellWindow ? shellWindow.scaled(4) : 4
        height: shellWindow ? shellWindow.scaled(3) : 3
        radius: height / 2
        gradient: Gradient {
            orientation: Gradient.Horizontal
            GradientStop { position: 0.0; color: "transparent" }
            GradientStop { position: 0.18; color: Qt.rgba(root.accentColor.r, root.accentColor.g, root.accentColor.b, 0.22) }
            GradientStop { position: 0.52; color: Qt.rgba(root.accentColor.r, root.accentColor.g, root.accentColor.b, 0.88) }
            GradientStop { position: 0.84; color: Qt.rgba(root.accentColor.r, root.accentColor.g, root.accentColor.b, 0.22) }
            GradientStop { position: 1.0; color: "transparent" }
        }
    }

    Rectangle {
        width: parent.width * 0.46
        height: parent.height * 0.72
        radius: width / 2
        color: root.accentColor
        opacity: 0.05
        x: -width * 0.2
        y: -height * 0.34
    }

    Rectangle {
        anchors.fill: parent
        anchors.margins: 1
        radius: parent.radius - 1
        color: "transparent"
        border.color: "#10ffffff"
        border.width: 1
    }

    ColumnLayout {
        id: chrome
        anchors.fill: parent
        anchors.margins: root.padding
        spacing: root.contentSpacing

        Item {
            visible: root.hasHeader
            Layout.fillWidth: true
            implicitHeight: headerColumn.implicitHeight

            ColumnLayout {
                id: headerColumn
                anchors.fill: parent
                spacing: shellWindow ? shellWindow.scaled(2) : 2

                Text {
                    visible: root.eyebrow.length > 0
                    text: root.eyebrow
                    color: root.accentColor
                    font.pixelSize: shellWindow ? shellWindow.eyebrowSize : 10
                    font.family: shellWindow ? shellWindow.monoFamily : "JetBrains Mono"
                    font.letterSpacing: shellWindow ? shellWindow.scaled(1) : 1
                }

                Text {
                    visible: root.title.length > 0
                    Layout.fillWidth: true
                    text: root.title
                    color: shellWindow ? shellWindow.textStrong : "#f5efe4"
                    font.pixelSize: shellWindow ? shellWindow.sectionTitleSize : 22
                    font.weight: Font.DemiBold
                    font.family: shellWindow ? shellWindow.displayFamily : "Noto Serif CJK SC"
                    wrapMode: Text.WordWrap
                }

                Text {
                    visible: root.subtitle.length > 0
                    Layout.fillWidth: true
                    text: root.subtitle
                    color: shellWindow ? shellWindow.textSecondary : "#9aa8b1"
                    font.pixelSize: shellWindow ? shellWindow.bodySize : 13
                    font.family: shellWindow ? shellWindow.uiFamily : "Noto Sans CJK SC"
                    wrapMode: Text.WordWrap
                }
            }
        }

        Rectangle {
            visible: root.hasHeader && contentLayout.children.length > 0
            Layout.fillWidth: true
            Layout.preferredHeight: 1
            color: shellWindow ? shellWindow.dataLineStrong : "#33434f"
            opacity: 0.72
        }

        ColumnLayout {
            id: contentLayout
            Layout.fillWidth: true
            spacing: root.contentSpacing
        }
    }
}
