import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

PanelFrame {
    id: root
    property var panelData: ({})
    panelColor: "#09131d"

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 16
        spacing: 10

        Text {
            text: panelData["title"] || "Action Strip"
            color: "#d8f7ff"
            font.pixelSize: 18
            font.bold: true
            font.family: "DejaVu Sans Mono"
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 10

            Repeater {
                model: panelData["actions"] || []

                delegate: Rectangle {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    radius: 12
                    color: modelData["enabled"] ? "#102634" : "#0f1d28"
                    border.width: 1
                    border.color: {
                        const tone = modelData["tone"];
                        if (tone === "online")
                            return "#21b573";
                        if (tone === "warning")
                            return "#f2b84a";
                        return "#29576b";
                    }

                    MouseArea {
                        anchors.fill: parent
                        enabled: modelData["enabled"]
                        onClicked: {
                            if (modelData["action_id"] === "reload_contracts" && cockpitBridge) {
                                cockpitBridge.reload();
                            }
                        }
                    }

                    Column {
                        anchors.fill: parent
                        anchors.margins: 12
                        spacing: 6

                        Text {
                            text: modelData["label"] || ""
                            color: "#edfaff"
                            font.pixelSize: 14
                            font.bold: true
                            font.family: "DejaVu Sans Mono"
                        }

                        Text {
                            text: modelData["note"] || ""
                            color: "#c3ebf4"
                            wrapMode: Text.WordWrap
                            font.pixelSize: 11
                            font.family: "DejaVu Sans Mono"
                        }
                    }
                }
            }
        }
    }
}
