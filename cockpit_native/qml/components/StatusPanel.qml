import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

PanelFrame {
    id: root
    property var panelData: ({})
    panelColor: "#0b151f"

    implicitHeight: contentLayout.implicitHeight + ((shellWindow ? shellWindow.panelPadding : 18) * 2)

    ColumnLayout {
        id: contentLayout
        anchors.fill: parent
        anchors.margins: shellWindow ? shellWindow.panelPadding : 18
        spacing: shellWindow ? shellWindow.zoneGap : 12

        Text {
            text: panelData["title"] || "系统 / 板态"
            color: "#d8f7ff"
            font.pixelSize: shellWindow ? shellWindow.sectionTitleSize : 22
            font.bold: true
            font.family: shellWindow ? shellWindow.monoFamily : "DejaVu Sans Mono"
        }

        Text {
            Layout.fillWidth: true
            text: panelData["summary"] || ""
            color: "#8fb8c6"
            wrapMode: Text.WordWrap
            font.pixelSize: shellWindow ? shellWindow.bodySize : 13
            font.family: shellWindow ? shellWindow.monoFamily : "DejaVu Sans Mono"
        }

        Repeater {
            model: panelData["rows"] || []

            delegate: Rectangle {
                Layout.fillWidth: true
                radius: shellWindow ? shellWindow.cardRadius : 10
                color: "#101e2a"
                border.width: 1
                border.color: {
                    const tone = modelData["tone"];
                    if (tone === "online")
                        return "#21b573";
                    if (tone === "warning")
                        return "#f2b84a";
                    return "#29576b";
                }
                implicitHeight: rowLayout.implicitHeight + ((shellWindow ? shellWindow.cardPadding : 12) * 2)

                RowLayout {
                    id: rowLayout
                    anchors.fill: parent
                    anchors.margins: shellWindow ? shellWindow.cardPadding : 12
                    spacing: shellWindow ? shellWindow.compactGap : 8

                    Rectangle {
                        Layout.preferredWidth: shellWindow ? shellWindow.scaled(10) : 10
                        Layout.preferredHeight: shellWindow ? shellWindow.scaled(10) : 10
                        radius: width / 2
                        color: parent.parent.border.color
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 2

                        Text {
                            text: modelData["label"] || ""
                            color: "#70d9ef"
                            font.pixelSize: shellWindow ? shellWindow.captionSize : 11
                            font.family: shellWindow ? shellWindow.monoFamily : "DejaVu Sans Mono"
                        }

                        Text {
                            Layout.fillWidth: true
                            text: modelData["value"] || ""
                            color: "#edfaff"
                            wrapMode: Text.WordWrap
                            font.pixelSize: shellWindow ? shellWindow.bodyEmphasisSize : 14
                            font.family: shellWindow ? shellWindow.monoFamily : "DejaVu Sans Mono"
                        }
                    }
                }
            }
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            radius: shellWindow ? shellWindow.cardRadius : 12
            color: "#09131d"
            border.color: "#173645"
            border.width: 1

            Column {
                anchors.fill: parent
                anchors.margins: shellWindow ? shellWindow.cardPadding : 12
                spacing: shellWindow ? shellWindow.compactGap : 8

                Text {
                    text: "边界说明"
                    color: "#68d7e5"
                    font.pixelSize: shellWindow ? shellWindow.captionSize : 11
                    font.family: shellWindow ? shellWindow.monoFamily : "DejaVu Sans Mono"
                }

                Text {
                    width: parent.width
                    text: panelData["truth_note"] || ""
                    color: "#c3ebf4"
                    wrapMode: Text.WordWrap
                    font.pixelSize: shellWindow ? shellWindow.captionSize : 11
                    font.family: shellWindow ? shellWindow.monoFamily : "DejaVu Sans Mono"
                }
            }
        }
    }
}
