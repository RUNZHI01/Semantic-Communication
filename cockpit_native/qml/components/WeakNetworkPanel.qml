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
            text: panelData["title"] || "Weak-Network Comparison"
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

        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 118
            radius: 12
            color: "#102634"
            border.color: "#29576b"
            border.width: 1

            Column {
                anchors.fill: parent
                anchors.margins: 12
                spacing: 5

                Text {
                    text: "Live Anchor"
                    color: "#68d7e5"
                    font.pixelSize: 12
                    font.family: "DejaVu Sans Mono"
                }

                Text {
                    text: ((panelData["live_anchor"] || {})["label"] || "") + " / " + ((panelData["live_anchor"] || {})["board_status"] || "")
                    color: "#edfaff"
                    font.pixelSize: 14
                    font.family: "DejaVu Sans Mono"
                }

                Text {
                    text: (panelData["live_anchor"] || {})["probe_summary"] || ""
                    color: "#c3ebf4"
                    wrapMode: Text.WordWrap
                    font.pixelSize: 12
                    font.family: "DejaVu Sans Mono"
                }
            }
        }

        ScrollView {
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true

            Column {
                width: root.width - 36
                spacing: 10

                Repeater {
                    model: panelData["scenarios"] || []

                    delegate: Rectangle {
                        width: parent.width
                        radius: 12
                        color: modelData["scenario_id"] === panelData["recommended_scenario_id"] ? "#123042" : "#101f2b"
                        border.width: 1
                        border.color: modelData["recommended"] ? "#21b573" : "#29576b"
                        implicitHeight: cardColumn.implicitHeight + 20

                        Column {
                            id: cardColumn
                            anchors.left: parent.left
                            anchors.right: parent.right
                            anchors.top: parent.top
                            anchors.margins: 12
                            spacing: 6

                            Row {
                                spacing: 8

                                Text {
                                    text: modelData["label"] || ""
                                    color: "#edfaff"
                                    font.pixelSize: 15
                                    font.bold: true
                                    font.family: "DejaVu Sans Mono"
                                }

                                Rectangle {
                                    width: 88
                                    height: 20
                                    radius: 10
                                    color: modelData["recommended"] ? "#1f7a58" : "#634d15"

                                    Text {
                                        anchors.centerIn: parent
                                        text: modelData["recommended"] ? "recommended" : "compare"
                                        color: "#edfaff"
                                        font.pixelSize: 10
                                        font.family: "DejaVu Sans Mono"
                                    }
                                }
                            }

                            Text {
                                text: modelData["summary"] || ""
                                color: "#c3ebf4"
                                wrapMode: Text.WordWrap
                                font.pixelSize: 12
                                font.family: "DejaVu Sans Mono"
                            }

                            Text {
                                text: "processed " + Number(modelData["processed_count"] || 0).toFixed(0) +
                                      " / uplift " + Number(((modelData["comparison"] || {})["throughput_uplift_pct"] || 0)).toFixed(3) + "%"
                                color: "#68d7e5"
                                font.pixelSize: 11
                                font.family: "DejaVu Sans Mono"
                            }
                        }
                    }
                }
            }
        }

        Text {
            text: panelData["truth_note"] || ""
            color: "#76b5c7"
            wrapMode: Text.WordWrap
            font.pixelSize: 11
            font.family: "DejaVu Sans Mono"
        }
    }
}
