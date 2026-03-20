import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "components"

ApplicationWindow {
    id: root
    readonly property var uiState: cockpitBridge ? cockpitBridge.state : ({})
    readonly property var zones: uiState["zones"] || ({})

    width: 1520
    height: 920
    visible: true
    color: "#09131d"
    title: ((uiState["meta"] || {})["title"] || "Feiteng Native Cockpit Prototype")

    Rectangle {
        anchors.fill: parent
        gradient: Gradient {
            GradientStop { position: 0.0; color: "#0f2031" }
            GradientStop { position: 0.48; color: "#09131d" }
            GradientStop { position: 1.0; color: "#05090d" }
        }
    }

    Rectangle {
        anchors.fill: parent
        color: "transparent"
        border.width: 1
        border.color: "#1f5164"
        radius: 12
        anchors.margins: 10
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 22
        spacing: 18

        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 84
            radius: 14
            color: "#102634"
            border.color: "#2ba6b6"
            border.width: 1

            RowLayout {
                anchors.fill: parent
                anchors.margins: 18
                spacing: 18

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 4

                    Text {
                        text: (uiState["meta"] || {})["title"] || "Native Cockpit Prototype"
                        color: "#d8f7ff"
                        font.pixelSize: 28
                        font.bold: true
                        font.family: "DejaVu Sans Mono"
                    }

                    Text {
                        text: (uiState["meta"] || {})["subtitle"] || ""
                        color: "#8fb8c6"
                        font.pixelSize: 14
                        font.family: "DejaVu Sans Mono"
                    }
                }

                Rectangle {
                    Layout.preferredWidth: 320
                    Layout.fillHeight: true
                    radius: 10
                    color: "#0b1822"
                    border.color: "#174051"
                    border.width: 1

                    Column {
                        anchors.fill: parent
                        anchors.margins: 12
                        spacing: 6

                        Text {
                            text: "Contract Source"
                            color: "#68d7e5"
                            font.pixelSize: 12
                            font.family: "DejaVu Sans Mono"
                        }

                        Text {
                            text: (uiState["meta"] || {})["snapshot_path"] || ""
                            color: "#c3ebf4"
                            wrapMode: Text.WrapAnywhere
                            font.pixelSize: 12
                            font.family: "DejaVu Sans Mono"
                        }
                    }
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 18

            StatusPanel {
                Layout.preferredWidth: 330
                Layout.fillHeight: true
                panelData: zones["left_status_panel"] || ({})
            }

            TacticalView {
                Layout.fillWidth: true
                Layout.fillHeight: true
                panelData: zones["center_tactical_view"] || ({})
            }

            WeakNetworkPanel {
                Layout.preferredWidth: 390
                Layout.fillHeight: true
                panelData: zones["right_weak_network_panel"] || ({})
            }
        }

        ActionStrip {
            Layout.fillWidth: true
            Layout.preferredHeight: 120
            panelData: zones["bottom_action_strip"] || ({})
        }
    }
}
