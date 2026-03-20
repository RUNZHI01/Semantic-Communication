import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

PanelFrame {
    id: root
    property var panelData: ({})
    panelColor: "#0c1720"

    readonly property var positionData: panelData["position"] || ({})
    readonly property var kinematicsData: panelData["kinematics"] || ({})
    readonly property var fixData: panelData["fix"] || ({})
    readonly property var trackData: panelData["track"] || []
    readonly property real headingDeg: Number(kinematicsData["heading_deg"] || 0)

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 18
        spacing: 14

        RowLayout {
            Layout.fillWidth: true

            ColumnLayout {
                Layout.fillWidth: true
                spacing: 4

                Text {
                    text: panelData["title"] || "Tactical / Aircraft View"
                    color: "#d8f7ff"
                    font.pixelSize: 24
                    font.bold: true
                    font.family: "DejaVu Sans Mono"
                }

                Text {
                    text: (panelData["mission_call_sign"] || "M9-DEMO") + " / " + (panelData["aircraft_id"] || "FT-AIR-01")
                    color: "#68d7e5"
                    font.pixelSize: 14
                    font.family: "DejaVu Sans Mono"
                }
            }

            Rectangle {
                Layout.preferredWidth: 220
                Layout.preferredHeight: 54
                radius: 10
                color: "#102634"
                border.color: "#29576b"
                border.width: 1

                Column {
                    anchors.fill: parent
                    anchors.margins: 10
                    spacing: 2

                    Text {
                        text: panelData["source_label"] || ""
                        color: "#c3ebf4"
                        font.pixelSize: 13
                        font.family: "DejaVu Sans Mono"
                    }

                    Text {
                        text: "status: " + (panelData["source_status"] || "")
                        color: "#76b5c7"
                        font.pixelSize: 11
                        font.family: "DejaVu Sans Mono"
                    }
                }
            }
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            radius: 14
            color: "#07121a"
            border.color: "#1b4f61"
            border.width: 1

            Item {
                anchors.fill: parent
                anchors.margins: 20

                Repeater {
                    model: 4

                    delegate: Rectangle {
                        anchors.centerIn: parent
                        width: parent.width * (0.28 + index * 0.18)
                        height: width
                        radius: width / 2
                        color: "transparent"
                        border.color: index === 3 ? "#2ba6b6" : "#143949"
                        border.width: 1
                    }
                }

                Repeater {
                    model: trackData

                    delegate: Rectangle {
                        width: 10
                        height: 10
                        radius: 5
                        color: "#f2b84a"
                        x: parent.width / 2 + (index - (trackData.length / 2)) * 34 - width / 2
                        y: parent.height / 2 + (trackData.length - index) * 26 - height / 2
                        opacity: 0.25 + (index / Math.max(trackData.length, 1)) * 0.65
                    }
                }

                Text {
                    anchors.centerIn: parent
                    text: "▲"
                    rotation: headingDeg
                    color: "#d8f7ff"
                    font.pixelSize: 46
                    font.family: "DejaVu Sans Mono"
                }

                Rectangle {
                    anchors.left: parent.left
                    anchors.top: parent.top
                    width: 240
                    height: 132
                    radius: 12
                    color: "#102634"
                    border.color: "#29576b"
                    border.width: 1

                    Column {
                        anchors.fill: parent
                        anchors.margins: 12
                        spacing: 6

                        Text {
                            text: "Position"
                            color: "#68d7e5"
                            font.pixelSize: 12
                            font.family: "DejaVu Sans Mono"
                        }

                        Text {
                            text: "lat  " + Number(positionData["latitude"] || 0).toFixed(6)
                            color: "#edfaff"
                            font.pixelSize: 14
                            font.family: "DejaVu Sans Mono"
                        }

                        Text {
                            text: "lon  " + Number(positionData["longitude"] || 0).toFixed(6)
                            color: "#edfaff"
                            font.pixelSize: 14
                            font.family: "DejaVu Sans Mono"
                        }

                        Text {
                            text: "fix  " + (fixData["type"] || "") + " / ±" + Number(fixData["confidence_m"] || 0).toFixed(1) + " m"
                            color: "#c3ebf4"
                            font.pixelSize: 12
                            font.family: "DejaVu Sans Mono"
                        }
                    }
                }

                Rectangle {
                    anchors.right: parent.right
                    anchors.top: parent.top
                    width: 240
                    height: 152
                    radius: 12
                    color: "#102634"
                    border.color: "#29576b"
                    border.width: 1

                    Column {
                        anchors.fill: parent
                        anchors.margins: 12
                        spacing: 6

                        Text {
                            text: "Kinematics"
                            color: "#68d7e5"
                            font.pixelSize: 12
                            font.family: "DejaVu Sans Mono"
                        }

                        Text {
                            text: "ALT " + Number(kinematicsData["altitude_m"] || 0).toFixed(1) + " m"
                            color: "#edfaff"
                            font.pixelSize: 16
                            font.family: "DejaVu Sans Mono"
                        }

                        Text {
                            text: "GS  " + Number(kinematicsData["ground_speed_kph"] || 0).toFixed(1) + " kph"
                            color: "#edfaff"
                            font.pixelSize: 16
                            font.family: "DejaVu Sans Mono"
                        }

                        Text {
                            text: "VS  " + Number(kinematicsData["vertical_speed_mps"] || 0).toFixed(1) + " m/s"
                            color: "#edfaff"
                            font.pixelSize: 16
                            font.family: "DejaVu Sans Mono"
                        }

                        Text {
                            text: "HDG " + Number(kinematicsData["heading_deg"] || 0).toFixed(1) + "°"
                            color: "#f2b84a"
                            font.pixelSize: 16
                            font.family: "DejaVu Sans Mono"
                        }
                    }
                }

                Rectangle {
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.bottom: parent.bottom
                    height: 96
                    radius: 12
                    color: "#0b1822"
                    border.color: "#173645"
                    border.width: 1

                    Column {
                        anchors.fill: parent
                        anchors.margins: 12
                        spacing: 6

                        Text {
                            text: "Control Summary"
                            color: "#68d7e5"
                            font.pixelSize: 12
                            font.family: "DejaVu Sans Mono"
                        }

                        Text {
                            text: "link profile: " + ((panelData["control_summary"] || {})["link_profile"] || "")
                            color: "#edfaff"
                            font.pixelSize: 13
                            font.family: "DejaVu Sans Mono"
                        }

                        Text {
                            text: (panelData["control_summary"] || {})["last_event_message"] || ""
                            color: "#c3ebf4"
                            wrapMode: Text.WordWrap
                            font.pixelSize: 12
                            font.family: "DejaVu Sans Mono"
                        }
                    }
                }
            }
        }
    }
}
