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
            text: panelData["title"] || "弱网对照 / Weak-Network"
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

        Rectangle {
            Layout.fillWidth: true
            radius: shellWindow ? shellWindow.cardRadius : 12
            color: "#102638"
            border.color: "#29576b"
            border.width: 1
            implicitHeight: anchorColumn.implicitHeight + ((shellWindow ? shellWindow.cardPadding : 12) * 2)

            Column {
                id: anchorColumn
                anchors.fill: parent
                anchors.margins: shellWindow ? shellWindow.cardPadding : 12
                spacing: shellWindow ? shellWindow.compactGap : 6

                Text {
                    text: "实时锚点"
                    color: "#68d7e5"
                    font.pixelSize: shellWindow ? shellWindow.captionSize : 11
                    font.family: shellWindow ? shellWindow.monoFamily : "DejaVu Sans Mono"
                }

                Text {
                    width: parent.width
                    text: ((panelData["live_anchor"] || {})["label"] || "") + " / " + ((panelData["live_anchor"] || {})["board_status"] || "")
                    color: "#edfaff"
                    font.pixelSize: shellWindow ? shellWindow.bodyEmphasisSize : 14
                    font.family: shellWindow ? shellWindow.monoFamily : "DejaVu Sans Mono"
                    wrapMode: Text.WordWrap
                }

                Text {
                    width: parent.width
                    text: (panelData["live_anchor"] || {})["probe_summary"] || ""
                    color: "#c3ebf4"
                    wrapMode: Text.WordWrap
                    font.pixelSize: shellWindow ? shellWindow.captionSize : 11
                    font.family: shellWindow ? shellWindow.monoFamily : "DejaVu Sans Mono"
                }
            }
        }

        ScrollView {
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true

            Column {
                width: root.width - ((shellWindow ? shellWindow.panelPadding : 18) * 2)
                spacing: shellWindow ? shellWindow.compactGap : 8

                Repeater {
                    model: panelData["scenarios"] || []

                    delegate: Rectangle {
                        width: parent.width
                        radius: shellWindow ? shellWindow.cardRadius : 12
                        color: modelData["scenario_id"] === panelData["recommended_scenario_id"] ? "#123247" : "#101e2a"
                        border.width: 1
                        border.color: modelData["recommended"] ? "#21b573" : "#29576b"
                        implicitHeight: cardColumn.implicitHeight + ((shellWindow ? shellWindow.cardPadding : 12) * 2)

                        Column {
                            id: cardColumn
                            anchors.left: parent.left
                            anchors.right: parent.right
                            anchors.top: parent.top
                            anchors.margins: shellWindow ? shellWindow.cardPadding : 12
                            spacing: shellWindow ? shellWindow.compactGap : 6

                            Row {
                                spacing: shellWindow ? shellWindow.compactGap : 8

                                Text {
                                    text: modelData["label"] || ""
                                    color: "#edfaff"
                                    font.pixelSize: shellWindow ? shellWindow.bodyEmphasisSize : 14
                                    font.bold: true
                                    font.family: shellWindow ? shellWindow.monoFamily : "DejaVu Sans Mono"
                                }

                                Rectangle {
                                    width: shellWindow ? shellWindow.scaled(72) : 72
                                    height: shellWindow ? shellWindow.scaled(20) : 20
                                    radius: height / 2
                                    color: modelData["recommended"] ? "#1f7a58" : "#5f4b18"

                                    Text {
                                        anchors.centerIn: parent
                                        text: modelData["recommended"] ? "推荐" : "对照"
                                        color: "#edfaff"
                                        font.pixelSize: shellWindow ? shellWindow.captionSize : 10
                                        font.family: shellWindow ? shellWindow.monoFamily : "DejaVu Sans Mono"
                                    }
                                }
                            }

                            Text {
                                width: parent.width
                                text: modelData["summary"] || ""
                                color: "#c3ebf4"
                                wrapMode: Text.WordWrap
                                font.pixelSize: shellWindow ? shellWindow.bodySize : 12
                                font.family: shellWindow ? shellWindow.monoFamily : "DejaVu Sans Mono"
                            }

                            Text {
                                width: parent.width
                                text: "处理 " + Number(modelData["processed_count"] || 0).toFixed(0) +
                                      " / 提升 " + Number(((modelData["comparison"] || {})["throughput_uplift_pct"] || 0)).toFixed(3) + "%"
                                color: "#68d7e5"
                                font.pixelSize: shellWindow ? shellWindow.captionSize : 11
                                font.family: shellWindow ? shellWindow.monoFamily : "DejaVu Sans Mono"
                                wrapMode: Text.WordWrap
                            }
                        }
                    }
                }
            }
        }

        Text {
            Layout.fillWidth: true
            text: panelData["truth_note"] || ""
            color: "#76b5c7"
            wrapMode: Text.WordWrap
            font.pixelSize: shellWindow ? shellWindow.captionSize : 11
            font.family: shellWindow ? shellWindow.monoFamily : "DejaVu Sans Mono"
        }
    }
}
