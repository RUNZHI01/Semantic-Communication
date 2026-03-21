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
    property bool minimalChrome: false

    readonly property bool hasHeader: eyebrow.length > 0 || title.length > 0 || subtitle.length > 0
    readonly property color topFill: Qt.lighter(root.fillColor, root.minimalChrome ? 1.03 : 1.08)
    readonly property color bottomFill: Qt.darker(root.fillColor, root.minimalChrome ? 1.02 : 1.08)
    readonly property color rimTone: Qt.lighter(root.borderColor, 1.06)

    default property alias contentData: contentLayout.data

    implicitHeight: chrome.implicitHeight + (padding * 2)

    Rectangle {
        anchors.fill: parent
        radius: root.radius
        gradient: Gradient {
            GradientStop { position: 0.0; color: Qt.rgba(root.topFill.r, root.topFill.g, root.topFill.b, root.minimalChrome ? 0.84 : 0.98) }
            GradientStop { position: 0.2; color: Qt.rgba(root.fillColor.r, root.fillColor.g, root.fillColor.b, root.minimalChrome ? 0.8 : 0.98) }
            GradientStop { position: 1.0; color: Qt.rgba(root.bottomFill.r, root.bottomFill.g, root.bottomFill.b, root.minimalChrome ? 0.86 : 0.99) }
        }
    }

    Rectangle {
        width: parent.width * 0.34
        height: parent.height * 0.48
        radius: width / 2
        color: root.accentColor
        opacity: root.minimalChrome ? 0.024 : 0.055
        x: parent.width - (width * 0.68)
        y: -height * 0.18
    }

    Rectangle {
        anchors.fill: parent
        radius: parent.radius
        gradient: Gradient {
            GradientStop { position: 0.0; color: "#18ffffff" }
            GradientStop { position: 0.16; color: "#08ffffff" }
            GradientStop { position: 0.52; color: "#00000000" }
            GradientStop { position: 1.0; color: "#12000000" }
        }
        opacity: root.minimalChrome ? 0.18 : 0.42
    }

    Rectangle {
        visible: !root.minimalChrome
        anchors.left: parent.left
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        anchors.leftMargin: shellWindow ? shellWindow.scaled(5) : 5
        anchors.topMargin: shellWindow ? shellWindow.scaled(10) : 10
        anchors.bottomMargin: shellWindow ? shellWindow.scaled(10) : 10
        width: shellWindow ? shellWindow.scaled(3) : 3
        radius: width / 2
        gradient: Gradient {
            orientation: Gradient.Vertical
            GradientStop { position: 0.0; color: "transparent" }
            GradientStop { position: 0.18; color: Qt.rgba(root.accentColor.r, root.accentColor.g, root.accentColor.b, 0.18) }
            GradientStop { position: 0.5; color: Qt.rgba(root.accentColor.r, root.accentColor.g, root.accentColor.b, 0.96) }
            GradientStop { position: 0.82; color: Qt.rgba(root.accentColor.r, root.accentColor.g, root.accentColor.b, 0.22) }
            GradientStop { position: 1.0; color: "transparent" }
        }
    }

    Rectangle {
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        height: shellWindow ? shellWindow.scaled(root.minimalChrome ? 1 : 2) : (root.minimalChrome ? 1 : 2)
        anchors.leftMargin: shellWindow ? shellWindow.scaled(10) : 10
        anchors.rightMargin: shellWindow ? shellWindow.scaled(10) : 10
        radius: height / 2
        gradient: Gradient {
            orientation: Gradient.Horizontal
            GradientStop { position: 0.0; color: "transparent" }
            GradientStop { position: 0.18; color: Qt.rgba(root.accentColor.r, root.accentColor.g, root.accentColor.b, root.minimalChrome ? 0.08 : 0.14) }
            GradientStop { position: 0.5; color: Qt.rgba(root.accentColor.r, root.accentColor.g, root.accentColor.b, root.minimalChrome ? 0.46 : 0.84) }
            GradientStop { position: 0.82; color: Qt.rgba(root.accentColor.r, root.accentColor.g, root.accentColor.b, root.minimalChrome ? 0.08 : 0.14) }
            GradientStop { position: 1.0; color: "transparent" }
        }
        opacity: root.minimalChrome ? 0.56 : 0.94
    }

    Rectangle {
        anchors.fill: parent
        radius: parent.radius
        color: "transparent"
        border.color: root.rimTone
        border.width: 1
    }

    Rectangle {
        anchors.fill: parent
        anchors.margins: 1
        radius: parent.radius - 1
        color: "transparent"
        border.color: Qt.rgba(root.borderColor.r, root.borderColor.g, root.borderColor.b, 0.44)
        border.width: 1
        opacity: root.minimalChrome ? 0.58 : 1.0
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
                    font.letterSpacing: shellWindow ? shellWindow.scaled(0.9) : 0.9
                }

                Text {
                    visible: root.title.length > 0
                    Layout.fillWidth: true
                    text: root.title
                    color: shellWindow ? shellWindow.textStrong : "#f5efe4"
                    font.pixelSize: shellWindow ? shellWindow.sectionTitleSize : 22
                    font.weight: Font.DemiBold
                    font.family: shellWindow ? shellWindow.displayFamily : "Noto Serif CJK SC"
                    font.letterSpacing: shellWindow ? shellWindow.scaled(0.2) : 0.2
                    wrapMode: Text.WordWrap
                }

                Text {
                    visible: root.subtitle.length > 0
                    Layout.fillWidth: true
                    text: root.subtitle
                    color: shellWindow ? shellWindow.textSecondary : "#9aa8b1"
                    font.pixelSize: shellWindow ? shellWindow.captionSize + 2 : 12
                    font.family: shellWindow ? shellWindow.uiFamily : "Noto Sans CJK SC"
                    wrapMode: Text.WordWrap
                    maximumLineCount: 3
                    elide: Text.ElideRight
                }
            }
        }

        Rectangle {
            visible: root.hasHeader && contentLayout.children.length > 0
            Layout.fillWidth: true
            Layout.preferredHeight: 1
            gradient: Gradient {
                orientation: Gradient.Horizontal
                GradientStop { position: 0.0; color: "transparent" }
                GradientStop { position: 0.18; color: Qt.rgba(root.accentColor.r, root.accentColor.g, root.accentColor.b, 0.2) }
                GradientStop { position: 0.5; color: shellWindow ? shellWindow.dataLineStrong : "#33434f" }
                GradientStop { position: 0.82; color: Qt.rgba(root.borderColor.r, root.borderColor.g, root.borderColor.b, 0.22) }
                GradientStop { position: 1.0; color: "transparent" }
            }
            opacity: 0.82
        }

        ColumnLayout {
            id: contentLayout
            Layout.fillWidth: true
            spacing: root.contentSpacing
        }
    }
}
