import QtQuick 2.15
import QtQuick.Layouts 1.15
import "DataUtils.js" as DataUtils

PanelFrame {
    id: root
    property var panelData: ({})
    readonly property var panel: DataUtils.objectOrEmpty(panelData)

    panelColor: shellWindow ? shellWindow.panelColorRaised : "#091422"
    borderTone: shellWindow ? shellWindow.panelTraceStrong : "#1a3f61"
    accentTone: shellWindow ? shellWindow.accentBlue : "#38b6ff"

    readonly property var rows: DataUtils.arrayOrEmpty(panel["rows"])
    readonly property bool dualColumn: width >= (shellWindow ? shellWindow.scaled(520) : 520)

    implicitHeight: contentLayout.implicitHeight + ((shellWindow ? shellWindow.panelPadding : 18) * 2)

    function toneColor(tone) {
        return shellWindow ? shellWindow.toneColor(tone) : "#38b6ff"
    }

    function toneFill(tone) {
        return shellWindow ? shellWindow.toneFill(tone) : "#0d2234"
    }

    function rowObject(label) {
        for (var index = 0; index < rows.length; ++index) {
            var row = DataUtils.objectOrEmpty(rows[index])
            if (String(row["label"] || "") === label)
                return row
        }
        return ({})
    }

    function rowValue(label) {
        return String(rowObject(label)["value"] || "")
    }

    function rowTone(label) {
        return String(rowObject(label)["tone"] || "neutral")
    }

    ColumnLayout {
        id: contentLayout
        anchors.fill: parent
        anchors.margins: shellWindow ? shellWindow.panelPadding : 18
        spacing: shellWindow ? shellWindow.zoneGap : 12

        Rectangle {
            Layout.fillWidth: true
            radius: shellWindow ? shellWindow.cardRadius : 14
            gradient: Gradient {
                GradientStop { position: 0.0; color: shellWindow ? shellWindow.shellDockTop : "#14385c" }
                GradientStop { position: 0.48; color: shellWindow ? shellWindow.shellDockMid : "#0b1d31" }
                GradientStop { position: 1.0; color: shellWindow ? shellWindow.shellDockBottom : "#07111c" }
            }
            border.color: shellWindow ? shellWindow.panelGlowStrong : "#3292cf"
            border.width: 1
            implicitHeight: heroLayout.implicitHeight + ((shellWindow ? shellWindow.cardPadding : 14) * 2)

            Rectangle {
                width: parent.width * 0.34
                height: parent.height * 0.8
                radius: width / 2
                color: "#3eb4ff"
                opacity: 0.12
                x: -width * 0.22
                y: -height * 0.2
            }

            GridLayout {
                id: heroLayout
                anchors.fill: parent
                anchors.margins: shellWindow ? shellWindow.cardPadding : 14
                columns: dualColumn ? 2 : 1
                columnSpacing: shellWindow ? shellWindow.zoneGap : 12
                rowSpacing: shellWindow ? shellWindow.compactGap : 8

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: shellWindow ? shellWindow.compactGap : 8

                    Text {
                        text: panel["title"] || "左舷系统轨 / Left System Rail"
                        color: shellWindow ? shellWindow.accentBlue : "#38b6ff"
                        font.pixelSize: shellWindow ? shellWindow.eyebrowSize : 10
                        font.family: shellWindow ? shellWindow.monoFamily : "JetBrains Mono"
                        font.letterSpacing: shellWindow ? shellWindow.scaled(1) : 1
                    }

                    Text {
                        text: "左舷系统轨"
                        color: shellWindow ? shellWindow.textStrong : "#f4fbff"
                        font.pixelSize: shellWindow ? shellWindow.sectionTitleSize : 24
                        font.bold: true
                        font.family: shellWindow ? shellWindow.displayFamily : "Noto Sans CJK SC"
                    }

                    Text {
                        text: "LEFT SYSTEM RAIL / BOARD HEALTH"
                        color: shellWindow ? shellWindow.textSecondary : "#83acc8"
                        font.pixelSize: shellWindow ? shellWindow.captionSize : 11
                        font.family: shellWindow ? shellWindow.monoFamily : "JetBrains Mono"
                        font.letterSpacing: shellWindow ? shellWindow.scaled(1) : 1
                    }

                    Text {
                        Layout.fillWidth: true
                        text: panel["summary"] || ""
                        color: shellWindow ? shellWindow.textSecondary : "#83acc8"
                        font.pixelSize: shellWindow ? shellWindow.bodySize : 13
                        font.family: shellWindow ? shellWindow.uiFamily : "Noto Sans CJK SC"
                        wrapMode: Text.WordWrap
                    }

                    Flow {
                        Layout.fillWidth: true
                        spacing: shellWindow ? shellWindow.compactGap : 8

                        Repeater {
                            model: [
                                {
                                    "label": "会话",
                                    "value": root.rowValue("会话"),
                                    "tone": root.rowTone("会话")
                                },
                                {
                                    "label": "最近事件",
                                    "value": root.rowValue("最近事件"),
                                    "tone": root.rowTone("最近事件")
                                },
                                {
                                    "label": "心跳",
                                    "value": root.rowValue("心跳"),
                                    "tone": root.rowTone("心跳")
                                }
                            ]

                            delegate: Rectangle {
                                readonly property var chip: modelData
                                radius: shellWindow ? shellWindow.edgeRadius : 10
                                gradient: Gradient {
                                    GradientStop { position: 0.0; color: Qt.lighter(root.toneFill(chip["tone"]), 1.14) }
                                    GradientStop { position: 1.0; color: root.toneFill(chip["tone"]) }
                                }
                                border.color: root.toneColor(chip["tone"])
                                border.width: 1
                                height: chipColumn.implicitHeight + ((shellWindow ? shellWindow.scaled(8) : 8) * 2)
                                width: Math.max(shellWindow ? shellWindow.scaled(136) : 136, chipColumn.implicitWidth + (shellWindow ? shellWindow.scaled(22) : 22))

                                Rectangle {
                                    anchors.left: parent.left
                                    anchors.right: parent.right
                                    anchors.top: parent.top
                                    height: shellWindow ? shellWindow.scaled(2) : 2
                                    gradient: Gradient {
                                        GradientStop { position: 0.0; color: "transparent" }
                                        GradientStop { position: 0.28; color: root.toneColor(chip["tone"]) }
                                        GradientStop { position: 0.72; color: Qt.lighter(root.toneColor(chip["tone"]), 1.16) }
                                        GradientStop { position: 1.0; color: "transparent" }
                                    }
                                    opacity: 0.74
                                }

                                Column {
                                    id: chipColumn
                                    anchors.centerIn: parent
                                    spacing: 2

                                    Text {
                                        text: chip["label"]
                                        color: shellWindow ? shellWindow.textMuted : "#4e7392"
                                        font.pixelSize: shellWindow ? shellWindow.captionSize : 11
                                        font.family: shellWindow ? shellWindow.monoFamily : "JetBrains Mono"
                                    }

                                    Text {
                                        text: chip["value"]
                                        color: shellWindow ? shellWindow.textStrong : "#f4fbff"
                                        font.pixelSize: shellWindow ? shellWindow.bodySize : 13
                                        font.bold: true
                                        font.family: shellWindow ? shellWindow.monoFamily : "JetBrains Mono"
                                    }
                                }
                            }
                        }
                    }
                }

                Rectangle {
                    Layout.fillWidth: true
                    radius: shellWindow ? shellWindow.cardRadius : 14
                    gradient: Gradient {
                        GradientStop { position: 0.0; color: "#102539" }
                        GradientStop { position: 1.0; color: "#081321" }
                    }
                    border.color: "#235b84"
                    border.width: 1
                    implicitHeight: monitorColumn.implicitHeight + ((shellWindow ? shellWindow.cardPadding : 14) * 2)

                    Rectangle {
                        anchors.fill: parent
                        anchors.margins: 1
                        radius: parent.radius - 1
                        color: "transparent"
                        border.color: "#133450"
                        border.width: 1
                        opacity: 0.8
                    }

                    Rectangle {
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.top: parent.top
                        height: shellWindow ? shellWindow.scaled(3) : 3
                        gradient: Gradient {
                            GradientStop { position: 0.0; color: "transparent" }
                            GradientStop { position: 0.22; color: shellWindow ? shellWindow.accentBlue : "#38b6ff" }
                            GradientStop { position: 0.72; color: shellWindow ? shellWindow.accentCyan : "#72f3ff" }
                            GradientStop { position: 1.0; color: "transparent" }
                        }
                        opacity: 0.78
                    }

                    Column {
                        id: monitorColumn
                        anchors.fill: parent
                        anchors.margins: shellWindow ? shellWindow.cardPadding : 14
                        spacing: shellWindow ? shellWindow.scaled(6) : 6

                        RowLayout {
                            width: parent.width
                            spacing: shellWindow ? shellWindow.compactGap : 8

                            Text {
                                Layout.fillWidth: true
                                text: "板端监视 / Left Monitor Rail"
                                color: shellWindow ? shellWindow.accentCyan : "#72f3ff"
                                font.pixelSize: shellWindow ? shellWindow.captionSize : 11
                                font.family: shellWindow ? shellWindow.monoFamily : "JetBrains Mono"
                            }

                            Rectangle {
                                radius: shellWindow ? shellWindow.edgeRadius : 10
                                color: "#091726"
                                border.color: "#1d547c"
                                border.width: 1
                                implicitWidth: monitorStamp.implicitWidth + ((shellWindow ? shellWindow.scaled(10) : 10) * 2)
                                implicitHeight: monitorStamp.implicitHeight + ((shellWindow ? shellWindow.scaled(5) : 5) * 2)

                                Text {
                                    id: monitorStamp
                                    anchors.centerIn: parent
                                    text: "3 NODES"
                                    color: shellWindow ? shellWindow.textPrimary : "#d5eeff"
                                    font.pixelSize: shellWindow ? shellWindow.captionSize : 9
                                    font.family: shellWindow ? shellWindow.monoFamily : "JetBrains Mono"
                                }
                            }
                        }

                        Repeater {
                            model: [
                                {
                                    "label": "作业统计",
                                    "value": root.rowValue("作业统计"),
                                    "tone": root.rowTone("作业统计")
                                },
                                {
                                    "label": "链路档位",
                                    "value": root.rowValue("链路档位"),
                                    "tone": root.rowTone("链路档位")
                                },
                                {
                                    "label": "事件时间",
                                    "value": root.rowValue("事件时间"),
                                    "tone": root.rowTone("事件时间")
                                }
                            ]

                            delegate: Rectangle {
                                readonly property var metric: modelData
                                width: parent.width
                                radius: shellWindow ? shellWindow.edgeRadius : 10
                                gradient: Gradient {
                                    GradientStop { position: 0.0; color: "#102133" }
                                    GradientStop { position: 1.0; color: "#091a2a" }
                                }
                                border.color: root.toneColor(metric["tone"])
                                border.width: 1
                                implicitHeight: metricColumn.implicitHeight + ((shellWindow ? shellWindow.scaled(8) : 8) * 2)

                                Rectangle {
                                    anchors.left: parent.left
                                    anchors.right: parent.right
                                    anchors.top: parent.top
                                    height: shellWindow ? shellWindow.scaled(2) : 2
                                    gradient: Gradient {
                                        GradientStop { position: 0.0; color: "transparent" }
                                        GradientStop { position: 0.28; color: root.toneColor(metric["tone"]) }
                                        GradientStop { position: 0.72; color: Qt.lighter(root.toneColor(metric["tone"]), 1.16) }
                                        GradientStop { position: 1.0; color: "transparent" }
                                    }
                                    opacity: 0.74
                                }

                                Column {
                                    id: metricColumn
                                    anchors.fill: parent
                                    anchors.margins: shellWindow ? shellWindow.scaled(8) : 8
                                    spacing: 2

                                    Text {
                                        text: metric["label"]
                                        color: shellWindow ? shellWindow.textMuted : "#4e7392"
                                        font.pixelSize: shellWindow ? shellWindow.captionSize : 11
                                        font.family: shellWindow ? shellWindow.uiFamily : "Noto Sans CJK SC"
                                    }

                                    Text {
                                        width: parent.width
                                        text: metric["value"]
                                        color: shellWindow ? shellWindow.textStrong : "#f4fbff"
                                        font.pixelSize: shellWindow ? shellWindow.captionSize : 11
                                        font.bold: true
                                        font.family: shellWindow ? shellWindow.monoFamily : "JetBrains Mono"
                                        wrapMode: Text.WrapAnywhere
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: shellWindow ? shellWindow.compactGap : 8

            Text {
                text: "状态矩阵 / STATUS MATRIX"
                color: shellWindow ? shellWindow.accentBlue : "#38b6ff"
                font.pixelSize: shellWindow ? shellWindow.captionSize : 11
                font.family: shellWindow ? shellWindow.monoFamily : "JetBrains Mono"
                font.letterSpacing: shellWindow ? shellWindow.scaled(1) : 1
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 1
                color: "#18405f"
                opacity: 0.92
            }

            Rectangle {
                radius: shellWindow ? shellWindow.edgeRadius : 10
                color: "#081625"
                border.color: "#20577f"
                border.width: 1
                implicitWidth: rowCountText.implicitWidth + ((shellWindow ? shellWindow.scaled(12) : 12) * 2)
                implicitHeight: rowCountText.implicitHeight + ((shellWindow ? shellWindow.scaled(5) : 5) * 2)

                Text {
                    id: rowCountText
                    anchors.centerIn: parent
                    text: String(rows.length) + " ROWS"
                    color: shellWindow ? shellWindow.textPrimary : "#d5eeff"
                    font.pixelSize: shellWindow ? shellWindow.captionSize : 10
                    font.family: shellWindow ? shellWindow.monoFamily : "JetBrains Mono"
                }
            }
        }

        GridLayout {
            Layout.fillWidth: true
            columns: dualColumn ? 2 : 1
            columnSpacing: shellWindow ? shellWindow.zoneGap : 12
            rowSpacing: shellWindow ? shellWindow.zoneGap : 12

            Repeater {
                model: rows

                delegate: Rectangle {
                    readonly property var rowData: modelData
                    readonly property bool wideCard: dualColumn && (String(rowData["label"] || "") === "作业统计" || String(rowData["label"] || "") === "快照原因")
                    Layout.fillWidth: true
                    Layout.columnSpan: wideCard ? 2 : 1
                    radius: shellWindow ? shellWindow.cardRadius : 14
                    gradient: Gradient {
                        GradientStop { position: 0.0; color: "#0f2235" }
                        GradientStop { position: 1.0; color: "#0a1727" }
                    }
                    border.color: root.toneColor(rowData["tone"])
                    border.width: 1
                    implicitHeight: rowColumn.implicitHeight + ((shellWindow ? shellWindow.cardPadding : 14) * 2)

                    Rectangle {
                        anchors.fill: parent
                        anchors.margins: 1
                        radius: parent.radius - 1
                        color: "transparent"
                        border.color: "#112f49"
                        border.width: 1
                        opacity: 0.74
                    }

                    Rectangle {
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.top: parent.top
                        height: shellWindow ? shellWindow.scaled(3) : 3
                        gradient: Gradient {
                            GradientStop { position: 0.0; color: "transparent" }
                            GradientStop { position: 0.24; color: root.toneColor(rowData["tone"]) }
                            GradientStop { position: 0.72; color: Qt.lighter(root.toneColor(rowData["tone"]), 1.18) }
                            GradientStop { position: 1.0; color: "transparent" }
                        }
                        opacity: 0.74
                    }

                    Rectangle {
                        anchors.left: parent.left
                        anchors.top: parent.top
                        anchors.bottom: parent.bottom
                        anchors.margins: shellWindow ? shellWindow.scaled(10) : 10
                        width: shellWindow ? shellWindow.scaled(4) : 4
                        radius: width / 2
                        color: root.toneColor(rowData["tone"])
                        opacity: 0.95
                    }

                    Rectangle {
                        anchors.right: parent.right
                        anchors.top: parent.top
                        anchors.margins: shellWindow ? shellWindow.scaled(10) : 10
                        radius: shellWindow ? shellWindow.edgeRadius : 10
                        color: root.toneFill(rowData["tone"])
                        border.color: root.toneColor(rowData["tone"])
                        border.width: 1
                        implicitWidth: rowToneText.implicitWidth + ((shellWindow ? shellWindow.scaled(10) : 10) * 2)
                        implicitHeight: rowToneText.implicitHeight + ((shellWindow ? shellWindow.scaled(5) : 5) * 2)

                        Text {
                            id: rowToneText
                            anchors.centerIn: parent
                            text: String(rowData["tone"] || "neutral").toUpperCase()
                            color: shellWindow ? shellWindow.textPrimary : "#d5eeff"
                            font.pixelSize: shellWindow ? shellWindow.captionSize : 9
                            font.family: shellWindow ? shellWindow.monoFamily : "JetBrains Mono"
                        }
                    }

                    Column {
                        id: rowColumn
                        anchors.fill: parent
                        anchors.margins: shellWindow ? shellWindow.cardPadding : 14
                        anchors.leftMargin: (shellWindow ? shellWindow.cardPadding : 14) + (shellWindow ? shellWindow.scaled(8) : 8)
                        spacing: shellWindow ? shellWindow.scaled(4) : 4

                        Text {
                            text: rowData["label"] || ""
                            color: shellWindow ? shellWindow.textMuted : "#4e7392"
                            font.pixelSize: shellWindow ? shellWindow.captionSize : 11
                            font.family: shellWindow ? shellWindow.uiFamily : "Noto Sans CJK SC"
                        }

                        Text {
                            width: parent.width
                            text: rowData["value"] || ""
                            color: shellWindow ? shellWindow.textStrong : "#f4fbff"
                            font.pixelSize: shellWindow ? shellWindow.bodySize : 13
                            font.bold: true
                            font.family: shellWindow ? shellWindow.monoFamily : "JetBrains Mono"
                            wrapMode: Text.WrapAnywhere
                        }
                    }
                }
            }
        }

        Rectangle {
            Layout.fillWidth: true
            radius: shellWindow ? shellWindow.cardRadius : 14
            color: "#081321"
            border.color: "#1f557c"
            border.width: 1
            implicitHeight: footerColumn.implicitHeight + ((shellWindow ? shellWindow.cardPadding : 14) * 2)

            Column {
                id: footerColumn
                anchors.fill: parent
                anchors.margins: shellWindow ? shellWindow.cardPadding : 14
                spacing: shellWindow ? shellWindow.scaled(4) : 4

                Text {
                    text: "真实性边界 / EVIDENCE BOUNDARY"
                    color: shellWindow ? shellWindow.accentBlue : "#38b6ff"
                    font.pixelSize: shellWindow ? shellWindow.captionSize : 11
                    font.family: shellWindow ? shellWindow.monoFamily : "JetBrains Mono"
                }

                Text {
                    width: parent.width
                    text: panel["truth_note"] || ""
                    visible: text.length > 0
                    color: shellWindow ? shellWindow.textSecondary : "#83acc8"
                    font.pixelSize: shellWindow ? shellWindow.captionSize : 11
                    font.family: shellWindow ? shellWindow.uiFamily : "Noto Sans CJK SC"
                    wrapMode: Text.WordWrap
                }

                Text {
                    width: parent.width
                    text: panel["snapshot_path"] || ""
                    visible: text.length > 0
                    color: shellWindow ? shellWindow.textMuted : "#4e7392"
                    font.pixelSize: shellWindow ? shellWindow.captionSize : 11
                    font.family: shellWindow ? shellWindow.monoFamily : "JetBrains Mono"
                    wrapMode: Text.WrapAnywhere
                }
            }
        }
    }
}
