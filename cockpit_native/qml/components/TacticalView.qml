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
    readonly property var controlSummary: panelData["control_summary"] || ({})
    readonly property real headingDeg: Number(kinematicsData["heading_deg"] || 0)
    readonly property bool compactCardLayout: shellWindow ? shellWindow.compactLayout : width < 900

    implicitHeight: contentLayout.implicitHeight + ((shellWindow ? shellWindow.panelPadding : 18) * 2)

    ColumnLayout {
        id: contentLayout
        anchors.fill: parent
        anchors.margins: shellWindow ? shellWindow.panelPadding : 18
        spacing: shellWindow ? shellWindow.zoneGap : 12

        GridLayout {
            Layout.fillWidth: true
            columns: compactCardLayout ? 1 : 2
            columnSpacing: shellWindow ? shellWindow.zoneGap : 12
            rowSpacing: shellWindow ? shellWindow.compactGap : 8

            ColumnLayout {
                Layout.fillWidth: true
                spacing: shellWindow ? shellWindow.compactGap : 6

                Text {
                    text: panelData["title"] || "航迹 / 飞机合同"
                    color: "#d8f7ff"
                    font.pixelSize: shellWindow ? shellWindow.sectionTitleSize : 22
                    font.bold: true
                    font.family: shellWindow ? shellWindow.monoFamily : "DejaVu Sans Mono"
                }

                Text {
                    text: (panelData["mission_call_sign"] || "M9-DEMO") + " / " + (panelData["aircraft_id"] || "FT-AIR-01")
                    color: "#68d7e5"
                    font.pixelSize: shellWindow ? shellWindow.bodySize : 13
                    font.family: shellWindow ? shellWindow.monoFamily : "DejaVu Sans Mono"
                }
            }

            Rectangle {
                Layout.fillWidth: true
                radius: shellWindow ? shellWindow.cardRadius : 12
                color: "#102638"
                border.color: "#29576b"
                border.width: 1
                implicitHeight: sourceColumn.implicitHeight + ((shellWindow ? shellWindow.cardPadding : 12) * 2)

                Column {
                    id: sourceColumn
                    anchors.fill: parent
                    anchors.margins: shellWindow ? shellWindow.cardPadding : 12
                    spacing: shellWindow ? shellWindow.compactGap : 6

                    Text {
                        text: "数据来源"
                        color: "#68d7e5"
                        font.pixelSize: shellWindow ? shellWindow.captionSize : 11
                        font.family: shellWindow ? shellWindow.monoFamily : "DejaVu Sans Mono"
                    }

                    Text {
                        width: parent.width
                        text: (panelData["source_label"] || "") + " / " + (panelData["source_status"] || "")
                        color: "#edfaff"
                        wrapMode: Text.WordWrap
                        font.pixelSize: shellWindow ? shellWindow.bodyEmphasisSize : 14
                        font.family: shellWindow ? shellWindow.monoFamily : "DejaVu Sans Mono"
                    }

                    Text {
                        width: parent.width
                        text: panelData["source_api_path"] || ""
                        color: "#93c6d6"
                        wrapMode: Text.WrapAnywhere
                        font.pixelSize: shellWindow ? shellWindow.captionSize : 11
                        font.family: shellWindow ? shellWindow.monoFamily : "DejaVu Sans Mono"
                    }
                }
            }
        }

        Rectangle {
            Layout.fillWidth: true
            radius: shellWindow ? shellWindow.cardRadius : 12
            color: "#091825"
            border.color: "#18475a"
            border.width: 1
            implicitHeight: routeColumn.implicitHeight + ((shellWindow ? shellWindow.cardPadding : 12) * 2)

            ColumnLayout {
                id: routeColumn
                anchors.fill: parent
                anchors.margins: shellWindow ? shellWindow.cardPadding : 12
                spacing: shellWindow ? shellWindow.compactGap : 8

                RowLayout {
                    Layout.fillWidth: true

                    Text {
                        text: "航迹摘要"
                        color: "#68d7e5"
                        font.pixelSize: shellWindow ? shellWindow.captionSize : 11
                        font.family: shellWindow ? shellWindow.monoFamily : "DejaVu Sans Mono"
                    }

                    Item {
                        Layout.fillWidth: true
                    }

                    Text {
                        text: "HDG " + headingDeg.toFixed(1) + "°"
                        color: "#f2b84a"
                        font.pixelSize: shellWindow ? shellWindow.bodySize : 13
                        font.family: shellWindow ? shellWindow.monoFamily : "DejaVu Sans Mono"
                    }
                }

                Item {
                    Layout.fillWidth: true
                    implicitHeight: shellWindow ? shellWindow.scaled(78) : 78

                    Rectangle {
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.verticalCenter: parent.verticalCenter
                        height: 2
                        radius: 1
                        color: "#174253"
                    }

                    Repeater {
                        model: Math.max(root.trackData.length, 1)

                        delegate: Rectangle {
                            readonly property int pointCount: Math.max(root.trackData.length, 1)
                            readonly property real progress: pointCount <= 1 ? 0.5 : index / (pointCount - 1)
                            readonly property bool currentPoint: index === (pointCount - 1)
                            width: currentPoint ? (shellWindow ? shellWindow.scaled(14) : 14) : (shellWindow ? shellWindow.scaled(8) : 8)
                            height: width
                            radius: width / 2
                            color: currentPoint ? "#2db6e2" : "#7eb8ca"
                            opacity: currentPoint ? 1.0 : 0.55
                            x: (parent.width - width) * progress
                            y: (parent.height / 2) - (height / 2) + ((index % 2 === 0) ? -(height * 0.8) : (height * 0.8))
                        }
                    }

                    Text {
                        anchors.left: parent.left
                        anchors.bottom: parent.bottom
                        text: "起点"
                        color: "#76b5c7"
                        font.pixelSize: shellWindow ? shellWindow.captionSize : 11
                        font.family: shellWindow ? shellWindow.monoFamily : "DejaVu Sans Mono"
                    }

                    Text {
                        anchors.right: parent.right
                        anchors.bottom: parent.bottom
                        text: "当前"
                        color: "#76b5c7"
                        font.pixelSize: shellWindow ? shellWindow.captionSize : 11
                        font.family: shellWindow ? shellWindow.monoFamily : "DejaVu Sans Mono"
                    }
                }

                Text {
                    Layout.fillWidth: true
                    text: "采样 " + Number(trackData.length || 0).toFixed(0) + " 点，使用时间序列摘要展示航迹变化，不伪装成地图或地球视图。"
                    color: "#93c6d6"
                    wrapMode: Text.WordWrap
                    font.pixelSize: shellWindow ? shellWindow.captionSize : 11
                    font.family: shellWindow ? shellWindow.monoFamily : "DejaVu Sans Mono"
                }
            }
        }

        GridLayout {
            Layout.fillWidth: true
            columns: compactCardLayout ? 1 : 2
            columnSpacing: shellWindow ? shellWindow.zoneGap : 12
            rowSpacing: shellWindow ? shellWindow.zoneGap : 12

            Rectangle {
                Layout.fillWidth: true
                radius: shellWindow ? shellWindow.cardRadius : 12
                color: "#102638"
                border.color: "#29576b"
                border.width: 1
                implicitHeight: positionColumn.implicitHeight + ((shellWindow ? shellWindow.cardPadding : 12) * 2)

                Column {
                    id: positionColumn
                    anchors.fill: parent
                    anchors.margins: shellWindow ? shellWindow.cardPadding : 12
                    spacing: shellWindow ? shellWindow.compactGap : 6

                    Text {
                        text: "位置"
                        color: "#68d7e5"
                        font.pixelSize: shellWindow ? shellWindow.captionSize : 11
                        font.family: shellWindow ? shellWindow.monoFamily : "DejaVu Sans Mono"
                    }

                    Text {
                        text: "lat  " + Number(positionData["latitude"] || 0).toFixed(6)
                        color: "#edfaff"
                        font.pixelSize: shellWindow ? shellWindow.bodyEmphasisSize : 14
                        font.family: shellWindow ? shellWindow.monoFamily : "DejaVu Sans Mono"
                    }

                    Text {
                        text: "lon  " + Number(positionData["longitude"] || 0).toFixed(6)
                        color: "#edfaff"
                        font.pixelSize: shellWindow ? shellWindow.bodyEmphasisSize : 14
                        font.family: shellWindow ? shellWindow.monoFamily : "DejaVu Sans Mono"
                    }

                    Text {
                        width: parent.width
                        text: "fix  " + (fixData["type"] || "") + " / ±" + Number(fixData["confidence_m"] || 0).toFixed(1) + " m"
                        color: "#c3ebf4"
                        font.pixelSize: shellWindow ? shellWindow.captionSize : 11
                        font.family: shellWindow ? shellWindow.monoFamily : "DejaVu Sans Mono"
                        wrapMode: Text.WordWrap
                    }
                }
            }

            Rectangle {
                Layout.fillWidth: true
                radius: shellWindow ? shellWindow.cardRadius : 12
                color: "#102638"
                border.color: "#29576b"
                border.width: 1
                implicitHeight: kinematicsColumn.implicitHeight + ((shellWindow ? shellWindow.cardPadding : 12) * 2)

                Column {
                    id: kinematicsColumn
                    anchors.fill: parent
                    anchors.margins: shellWindow ? shellWindow.cardPadding : 12
                    spacing: shellWindow ? shellWindow.compactGap : 6

                    Text {
                        text: "机动参数"
                        color: "#68d7e5"
                        font.pixelSize: shellWindow ? shellWindow.captionSize : 11
                        font.family: shellWindow ? shellWindow.monoFamily : "DejaVu Sans Mono"
                    }

                    Text {
                        text: "ALT " + Number(kinematicsData["altitude_m"] || 0).toFixed(1) + " m"
                        color: "#edfaff"
                        font.pixelSize: shellWindow ? shellWindow.bodyEmphasisSize : 14
                        font.family: shellWindow ? shellWindow.monoFamily : "DejaVu Sans Mono"
                    }

                    Text {
                        text: "GS  " + Number(kinematicsData["ground_speed_kph"] || 0).toFixed(1) + " kph"
                        color: "#edfaff"
                        font.pixelSize: shellWindow ? shellWindow.bodyEmphasisSize : 14
                        font.family: shellWindow ? shellWindow.monoFamily : "DejaVu Sans Mono"
                    }

                    Text {
                        text: "VS  " + Number(kinematicsData["vertical_speed_mps"] || 0).toFixed(1) + " m/s"
                        color: "#edfaff"
                        font.pixelSize: shellWindow ? shellWindow.bodyEmphasisSize : 14
                        font.family: shellWindow ? shellWindow.monoFamily : "DejaVu Sans Mono"
                    }
                }
            }
        }

        Rectangle {
            Layout.fillWidth: true
            radius: shellWindow ? shellWindow.cardRadius : 12
            color: "#0b1822"
            border.color: "#173645"
            border.width: 1
            implicitHeight: summaryColumn.implicitHeight + ((shellWindow ? shellWindow.cardPadding : 12) * 2)

            Column {
                id: summaryColumn
                anchors.fill: parent
                anchors.margins: shellWindow ? shellWindow.cardPadding : 12
                spacing: shellWindow ? shellWindow.compactGap : 6

                Text {
                    text: "控制摘要"
                    color: "#68d7e5"
                    font.pixelSize: shellWindow ? shellWindow.captionSize : 11
                    font.family: shellWindow ? shellWindow.monoFamily : "DejaVu Sans Mono"
                }

                Text {
                    width: parent.width
                    text: "链路档位: " + (controlSummary["link_profile"] || "")
                    color: "#edfaff"
                    font.pixelSize: shellWindow ? shellWindow.bodySize : 13
                    font.family: shellWindow ? shellWindow.monoFamily : "DejaVu Sans Mono"
                    wrapMode: Text.WordWrap
                }

                Text {
                    width: parent.width
                    text: (controlSummary["last_event_message"] || "")
                    color: "#c3ebf4"
                    font.pixelSize: shellWindow ? shellWindow.bodySize : 12
                    font.family: shellWindow ? shellWindow.monoFamily : "DejaVu Sans Mono"
                    wrapMode: Text.WordWrap
                }

                Text {
                    width: parent.width
                    text: panelData["ownership_note"] || panelData["fallback_note"] || ""
                    visible: text.length > 0
                    color: "#8fb8c6"
                    font.pixelSize: shellWindow ? shellWindow.captionSize : 11
                    font.family: shellWindow ? shellWindow.monoFamily : "DejaVu Sans Mono"
                    wrapMode: Text.WordWrap
                }
            }
        }
    }
}
