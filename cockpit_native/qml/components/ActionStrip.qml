import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

PanelFrame {
    id: root
    property var panelData: ({})
    panelColor: "#08131b"

    function toneColor(tone) {
        if (tone === "online")
            return "#24b67b";
        if (tone === "warning")
            return "#f2b84a";
        return "#2b6f88";
    }

    implicitHeight: contentLayout.implicitHeight + ((shellWindow ? shellWindow.panelPadding : 16) * 2)

    ColumnLayout {
        id: contentLayout
        anchors.fill: parent
        anchors.margins: shellWindow ? shellWindow.panelPadding : 16
        spacing: shellWindow ? shellWindow.zoneGap : 10

        Text {
            text: panelData["title"] || "操作条 / Action Strip"
            color: "#d8f7ff"
            font.pixelSize: shellWindow ? shellWindow.sectionTitleSize : 18
            font.bold: true
            font.family: shellWindow ? shellWindow.monoFamily : "DejaVu Sans Mono"
        }

        Text {
            Layout.fillWidth: true
            text: "保留仓库既有后端合同，不把原生壳体做成固定 1920x1080 画布。"
            color: "#8fb8c6"
            wrapMode: Text.WordWrap
            font.pixelSize: shellWindow ? shellWindow.bodySize : 12
            font.family: shellWindow ? shellWindow.monoFamily : "DejaVu Sans Mono"
        }

        Item {
            Layout.fillWidth: true
            implicitHeight: actionFlow.implicitHeight

            Flow {
                id: actionFlow
                width: parent.width
                spacing: shellWindow ? shellWindow.zoneGap : 10
                readonly property int columns: width >= (shellWindow ? shellWindow.scaled(1180) : 1180)
                    ? 4
                    : width >= (shellWindow ? shellWindow.scaled(680) : 680)
                        ? 2
                        : 1

                Repeater {
                    model: panelData["actions"] || []

                    delegate: Rectangle {
                        width: Math.max(
                            shellWindow ? shellWindow.scaled(200) : 200,
                            Math.floor((actionFlow.width - ((actionFlow.columns - 1) * actionFlow.spacing)) / actionFlow.columns)
                        )
                        radius: shellWindow ? shellWindow.cardRadius : 12
                        color: modelData["enabled"] ? "#0f2534" : "#0d1a24"
                        border.width: 1
                        border.color: toneColor(modelData["tone"])
                        implicitHeight: actionColumn.implicitHeight + ((shellWindow ? shellWindow.cardPadding : 12) * 2)

                        MouseArea {
                            anchors.fill: parent
                            enabled: modelData["enabled"]
                            cursorShape: modelData["enabled"] ? Qt.PointingHandCursor : Qt.ArrowCursor
                            onClicked: {
                                if (modelData["action_id"] === "reload_contracts" && cockpitBridge) {
                                    cockpitBridge.reload();
                                }
                            }
                        }

                        Column {
                            id: actionColumn
                            anchors.fill: parent
                            anchors.margins: shellWindow ? shellWindow.cardPadding : 12
                            spacing: shellWindow ? shellWindow.compactGap : 6

                            Text {
                                text: modelData["label"] || ""
                                color: "#edfaff"
                                font.pixelSize: shellWindow ? shellWindow.bodyEmphasisSize : 14
                                font.bold: true
                                font.family: shellWindow ? shellWindow.monoFamily : "DejaVu Sans Mono"
                            }

                            Text {
                                text: modelData["note"] || ""
                                color: "#c3ebf4"
                                wrapMode: Text.WordWrap
                                font.pixelSize: shellWindow ? shellWindow.captionSize : 11
                                font.family: shellWindow ? shellWindow.monoFamily : "DejaVu Sans Mono"
                            }
                        }
                    }
                }
            }
        }

        Text {
            Layout.fillWidth: true
            text: panelData["footer_note"] || ""
            color: "#76b5c7"
            wrapMode: Text.WordWrap
            font.pixelSize: shellWindow ? shellWindow.captionSize : 11
            font.family: shellWindow ? shellWindow.monoFamily : "DejaVu Sans Mono"
        }
    }
}
