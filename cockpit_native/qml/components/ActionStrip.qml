import QtQuick 2.15
import QtQuick.Layouts 1.15
import "DataUtils.js" as DataUtils

PanelFrame {
    id: root
    property var panelData: ({})
    readonly property var panel: DataUtils.objectOrEmpty(panelData)
    readonly property var actions: DataUtils.arrayOrEmpty(panel["actions"])
    readonly property var launchConfig: DataUtils.objectOrEmpty((typeof launchOptions !== "undefined") ? launchOptions : null)
    readonly property bool softwareRenderEnabled: !!launchConfig["softwareRender"]
    readonly property var bridge: (typeof cockpitBridge !== "undefined" && cockpitBridge) ? cockpitBridge : null

    panelColor: shellWindow ? shellWindow.cardColorSoft : "#08131b"
    borderTone: shellWindow ? shellWindow.borderSoft : "#1a3f61"
    accentTone: shellWindow ? shellWindow.accentBlue : "#38b6ff"

    implicitHeight: contentLayout.implicitHeight + ((shellWindow ? shellWindow.panelPadding : 16) * 2)

    function toneColor(tone) {
        if (shellWindow)
            return shellWindow.toneColor(tone)
        if (tone === "online")
            return "#42f0bc"
        if (tone === "warning")
            return "#ffbf52"
        return "#38b6ff"
    }

    function toneFill(tone) {
        if (shellWindow)
            return shellWindow.toneFill(tone)
        if (tone === "online")
            return "#0d2c29"
        if (tone === "warning")
            return "#302311"
        return "#0d2234"
    }

    ColumnLayout {
        id: contentLayout
        anchors.fill: parent
        anchors.margins: shellWindow ? shellWindow.panelPadding : 16
        spacing: shellWindow ? shellWindow.zoneGap : 10

        Rectangle {
            Layout.fillWidth: true
            radius: shellWindow ? shellWindow.cardRadius : 14
            gradient: Gradient {
                GradientStop { position: 0.0; color: "#0f2c47" }
                GradientStop { position: 0.5; color: "#091a2a" }
                GradientStop { position: 1.0; color: "#06101a" }
            }
            border.color: "#2b7eaf"
            border.width: 1
            implicitHeight: heroLayout.implicitHeight + ((shellWindow ? shellWindow.cardPadding : 12) * 2)

            GridLayout {
                id: heroLayout
                anchors.fill: parent
                anchors.margins: shellWindow ? shellWindow.cardPadding : 12
                columns: root.width >= (shellWindow ? shellWindow.scaled(980) : 980) ? 2 : 1
                columnSpacing: shellWindow ? shellWindow.zoneGap : 12
                rowSpacing: shellWindow ? shellWindow.compactGap : 8

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: shellWindow ? shellWindow.compactGap : 8

                    Text {
                        text: panel["title"] || "操作条 / Action Strip"
                        color: shellWindow ? shellWindow.accentBlue : "#38b6ff"
                        font.pixelSize: shellWindow ? shellWindow.eyebrowSize : 10
                        font.family: shellWindow ? shellWindow.monoFamily : "JetBrains Mono"
                        font.letterSpacing: shellWindow ? shellWindow.scaled(1) : 1
                    }

                    Text {
                        text: "执行控制"
                        color: shellWindow ? shellWindow.textStrong : "#f4fbff"
                        font.pixelSize: shellWindow ? shellWindow.sectionTitleSize : 20
                        font.bold: true
                        font.family: shellWindow ? shellWindow.displayFamily : "Noto Sans CJK SC"
                    }

                    Text {
                        Layout.fillWidth: true
                        text: "保持原生壳体自适应布局，只暴露真实可执行的合同动作，其余项作为只读指示。"
                        color: shellWindow ? shellWindow.textSecondary : "#83acc8"
                        wrapMode: Text.WordWrap
                        font.pixelSize: shellWindow ? shellWindow.bodySize : 12
                        font.family: shellWindow ? shellWindow.uiFamily : "Noto Sans CJK SC"
                    }
                }

                Flow {
                    Layout.fillWidth: true
                    spacing: shellWindow ? shellWindow.compactGap : 8

                    Repeater {
                        model: [
                            {
                                "label": "动作数",
                                "value": String(actions.length),
                                "tone": "neutral"
                            },
                            {
                                "label": "重载",
                                "value": "合同刷新",
                                "tone": "online"
                            },
                            {
                                "label": "渲染",
                                "value": softwareRenderEnabled ? "软件回退" : "图形加速",
                                "tone": softwareRenderEnabled ? "warning" : "online"
                            }
                        ]

                        delegate: Rectangle {
                            readonly property var chip: modelData
                            radius: shellWindow ? shellWindow.edgeRadius : 10
                            color: root.toneFill(chip["tone"])
                            border.color: root.toneColor(chip["tone"])
                            border.width: 1
                            height: chipColumn.implicitHeight + ((shellWindow ? shellWindow.scaled(8) : 8) * 2)
                            width: Math.max(shellWindow ? shellWindow.scaled(140) : 140, chipColumn.implicitWidth + (shellWindow ? shellWindow.scaled(20) : 20))

                            Column {
                                id: chipColumn
                                anchors.centerIn: parent
                                spacing: 2

                                Text {
                                    text: chip["label"]
                                    color: shellWindow ? shellWindow.textMuted : "#4e7392"
                                    font.pixelSize: shellWindow ? shellWindow.captionSize : 11
                                    font.family: shellWindow ? shellWindow.uiFamily : "Noto Sans CJK SC"
                                }

                                Text {
                                    text: chip["value"]
                                    color: shellWindow ? shellWindow.textStrong : "#f4fbff"
                                    font.pixelSize: shellWindow ? shellWindow.captionSize : 11
                                    font.bold: true
                                    font.family: shellWindow ? shellWindow.monoFamily : "JetBrains Mono"
                                }
                            }
                        }
                    }
                }
            }
        }

        Item {
            Layout.fillWidth: true
            implicitHeight: actionFlow.implicitHeight

            Flow {
                id: actionFlow
                width: parent.width
                spacing: shellWindow ? shellWindow.zoneGap : 10
                readonly property int columns: width >= (shellWindow ? shellWindow.scaled(1260) : 1260)
                    ? 4
                    : width >= (shellWindow ? shellWindow.scaled(760) : 760)
                        ? 2
                        : 1

                Repeater {
                    model: actions

                    delegate: Rectangle {
                        id: actionCard
                        readonly property bool enabledAction: !!modelData["enabled"]
                        readonly property bool hovered: actionArea.containsMouse
                        width: Math.max(
                            shellWindow ? shellWindow.scaled(220) : 220,
                            Math.floor((actionFlow.width - ((actionFlow.columns - 1) * actionFlow.spacing)) / actionFlow.columns)
                        )
                        radius: shellWindow ? shellWindow.cardRadius : 12
                        gradient: Gradient {
                            GradientStop {
                                position: 0.0
                                color: actionCard.enabledAction
                                    ? (actionCard.hovered ? "#143a57" : "#102a40")
                                    : "#0b1822"
                            }
                            GradientStop {
                                position: 1.0
                                color: actionCard.enabledAction
                                    ? (actionCard.hovered ? "#0b1e2d" : "#081624")
                                    : "#071018"
                            }
                        }
                        border.width: 1
                        border.color: root.toneColor(modelData["tone"])
                        implicitHeight: actionColumn.implicitHeight + ((shellWindow ? shellWindow.cardPadding : 12) * 2)
                        scale: actionCard.hovered ? 1.015 : 1.0

                        Behavior on scale {
                            NumberAnimation { duration: 120 }
                        }

                        Rectangle {
                            width: parent.width * 0.44
                            height: parent.height * 0.92
                            radius: width / 2
                            color: root.toneColor(modelData["tone"])
                            opacity: actionCard.enabledAction ? 0.09 : 0.04
                            x: -width * 0.22
                            y: -height * 0.18
                        }

                        Rectangle {
                            anchors.left: parent.left
                            anchors.right: parent.right
                            anchors.top: parent.top
                            height: shellWindow ? shellWindow.scaled(3) : 3
                            gradient: Gradient {
                                GradientStop { position: 0.0; color: "transparent" }
                                GradientStop { position: 0.28; color: root.toneColor(modelData["tone"]) }
                                GradientStop { position: 0.72; color: Qt.lighter(root.toneColor(modelData["tone"]), 1.18) }
                                GradientStop { position: 1.0; color: "transparent" }
                            }
                            opacity: 0.78
                        }

                        Rectangle {
                            anchors.left: parent.left
                            anchors.top: parent.top
                            anchors.bottom: parent.bottom
                            anchors.margins: shellWindow ? shellWindow.scaled(10) : 10
                            width: shellWindow ? shellWindow.scaled(4) : 4
                            radius: width / 2
                            color: root.toneColor(modelData["tone"])
                            opacity: actionCard.enabledAction ? 0.92 : 0.42
                        }

                        MouseArea {
                            id: actionArea
                            anchors.fill: parent
                            enabled: actionCard.enabledAction
                            hoverEnabled: actionCard.enabledAction
                            cursorShape: actionCard.enabledAction ? Qt.PointingHandCursor : Qt.ArrowCursor
                            onClicked: {
                                if (modelData["action_id"] === "reload_contracts" && bridge)
                                    bridge.reload()
                            }
                        }

                        Column {
                            id: actionColumn
                            anchors.fill: parent
                            anchors.margins: shellWindow ? shellWindow.cardPadding : 12
                            anchors.leftMargin: (shellWindow ? shellWindow.cardPadding : 12) + (shellWindow ? shellWindow.scaled(8) : 8)
                            spacing: shellWindow ? shellWindow.compactGap : 6

                            RowLayout {
                                width: parent.width
                                spacing: shellWindow ? shellWindow.compactGap : 8

                                Rectangle {
                                    radius: shellWindow ? shellWindow.edgeRadius : 10
                                    color: root.toneFill(modelData["tone"])
                                    border.color: root.toneColor(modelData["tone"])
                                    border.width: 1
                                    implicitWidth: actionIdText.implicitWidth + ((shellWindow ? shellWindow.scaled(12) : 12) * 2)
                                    implicitHeight: actionIdText.implicitHeight + ((shellWindow ? shellWindow.scaled(6) : 6) * 2)

                                    Text {
                                        id: actionIdText
                                        anchors.centerIn: parent
                                        text: modelData["action_id"] || ""
                                        color: shellWindow ? shellWindow.textPrimary : "#d5eeff"
                                        font.pixelSize: shellWindow ? shellWindow.captionSize : 10
                                        font.family: shellWindow ? shellWindow.monoFamily : "JetBrains Mono"
                                    }
                                }

                                Item {
                                    Layout.fillWidth: true
                                }

                                Rectangle {
                                    radius: height / 2
                                    color: actionCard.enabledAction ? "#163a2c" : "#1b2530"
                                    border.color: actionCard.enabledAction ? "#42f0bc" : "#35516b"
                                    border.width: 1
                                    implicitWidth: statusText.implicitWidth + ((shellWindow ? shellWindow.scaled(12) : 12) * 2)
                                    implicitHeight: statusText.implicitHeight + ((shellWindow ? shellWindow.scaled(6) : 6) * 2)

                                    Text {
                                        id: statusText
                                        anchors.centerIn: parent
                                        text: actionCard.enabledAction ? "可执行" : "只读"
                                        color: shellWindow ? shellWindow.textStrong : "#f4fbff"
                                        font.pixelSize: shellWindow ? shellWindow.captionSize : 10
                                        font.family: shellWindow ? shellWindow.uiFamily : "Noto Sans CJK SC"
                                    }
                                }
                            }

                            Text {
                                text: actionCard.enabledAction ? "ACTION WINDOW" : "READ ONLY CONTRACT"
                                color: shellWindow ? shellWindow.textMuted : "#4e7392"
                                font.pixelSize: shellWindow ? shellWindow.captionSize : 10
                                font.family: shellWindow ? shellWindow.monoFamily : "JetBrains Mono"
                                font.letterSpacing: shellWindow ? shellWindow.scaled(1) : 1
                            }

                            Text {
                                text: modelData["label"] || ""
                                color: shellWindow ? shellWindow.textStrong : "#f4fbff"
                                font.pixelSize: shellWindow ? shellWindow.bodyEmphasisSize : 14
                                font.bold: true
                                font.family: shellWindow ? shellWindow.uiFamily : "Noto Sans CJK SC"
                            }

                            Text {
                                width: parent.width
                                text: modelData["note"] || ""
                                color: shellWindow ? shellWindow.textSecondary : "#83acc8"
                                wrapMode: Text.WordWrap
                                font.pixelSize: shellWindow ? shellWindow.captionSize : 11
                                font.family: shellWindow ? shellWindow.uiFamily : "Noto Sans CJK SC"
                            }

                            Rectangle {
                                width: parent.width
                                radius: shellWindow ? shellWindow.edgeRadius : 10
                                gradient: Gradient {
                                    GradientStop { position: 0.0; color: actionCard.enabledAction ? "#10283a" : "#0a1620" }
                                    GradientStop { position: 1.0; color: actionCard.enabledAction ? "#0a1824" : "#09121a" }
                                }
                                border.color: actionCard.enabledAction ? root.toneColor(modelData["tone"]) : "#27445c"
                                border.width: 1
                                implicitHeight: actionHintColumn.implicitHeight + ((shellWindow ? shellWindow.scaled(8) : 8) * 2)

                                Column {
                                    id: actionHintColumn
                                    anchors.centerIn: parent
                                    spacing: shellWindow ? shellWindow.scaled(2) : 2

                                    Text {
                                        text: actionCard.enabledAction ? "操作提示" : "只读提示"
                                        color: shellWindow ? shellWindow.textMuted : "#4e7392"
                                        font.pixelSize: shellWindow ? shellWindow.captionSize : 10
                                        font.family: shellWindow ? shellWindow.uiFamily : "Noto Sans CJK SC"
                                    }

                                    Text {
                                        text: actionCard.enabledAction ? "点击执行" : "展示当前合同值"
                                        color: shellWindow ? shellWindow.textPrimary : "#d5eeff"
                                        font.pixelSize: shellWindow ? shellWindow.captionSize : 11
                                        font.family: shellWindow ? shellWindow.uiFamily : "Noto Sans CJK SC"
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }

        Rectangle {
            Layout.fillWidth: true
            radius: shellWindow ? shellWindow.edgeRadius : 10
            color: "#081321"
            border.color: "#1f557c"
            border.width: 1
            implicitHeight: footerText.implicitHeight + ((shellWindow ? shellWindow.scaled(10) : 10) * 2)

            Text {
                id: footerText
                anchors.fill: parent
                anchors.margins: shellWindow ? shellWindow.scaled(10) : 10
                text: panel["footer_note"] || ""
                color: shellWindow ? shellWindow.textMuted : "#4e7392"
                wrapMode: Text.WordWrap
                font.pixelSize: shellWindow ? shellWindow.captionSize : 11
                font.family: shellWindow ? shellWindow.uiFamily : "Noto Sans CJK SC"
                visible: text.length > 0
            }
        }
    }
}
