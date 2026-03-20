import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

PanelFrame {
    id: root
    property var panelData: ({})
    panelColor: "#0b151e"

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 18
        spacing: 12

        Text {
            text: panelData["title"] || "System / Board"
            color: "#d8f7ff"
            font.pixelSize: 22
            font.bold: true
            font.family: "DejaVu Sans Mono"
        }

        Text {
            text: panelData["summary"] || ""
            color: "#8fb8c6"
            wrapMode: Text.WordWrap
            font.pixelSize: 13
            font.family: "DejaVu Sans Mono"
        }

        Repeater {
            model: panelData["rows"] || []

            delegate: Rectangle {
                Layout.fillWidth: true
                implicitHeight: 58
                radius: 10
                color: "#101f2b"
                border.width: 1
                border.color: {
                    const tone = modelData["tone"];
                    if (tone === "online")
                        return "#21b573";
                    if (tone === "warning")
                        return "#f2b84a";
                    return "#29576b";
                }

                RowLayout {
                    anchors.fill: parent
                    anchors.margins: 12
                    spacing: 12

                    Rectangle {
                        Layout.preferredWidth: 10
                        Layout.preferredHeight: 10
                        radius: 5
                        color: parent.parent.border.color
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 2

                        Text {
                            text: modelData["label"] || ""
                            color: "#67d7e4"
                            font.pixelSize: 12
                            font.family: "DejaVu Sans Mono"
                        }

                        Text {
                            text: modelData["value"] || ""
                            color: "#edfaff"
                            wrapMode: Text.WordWrap
                            font.pixelSize: 14
                            font.family: "DejaVu Sans Mono"
                        }
                    }
                }
            }
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            radius: 12
            color: "#09131d"
            border.color: "#173645"
            border.width: 1

            Column {
                anchors.fill: parent
                anchors.margins: 12
                spacing: 8

                Text {
                    text: "Boundary Note"
                    color: "#68d7e5"
                    font.pixelSize: 12
                    font.family: "DejaVu Sans Mono"
                }

                Text {
                    text: panelData["truth_note"] || ""
                    color: "#c3ebf4"
                    wrapMode: Text.WordWrap
                    font.pixelSize: 12
                    font.family: "DejaVu Sans Mono"
                }
            }
        }
    }
}
