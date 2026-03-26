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
    readonly property bool bridgeAvailable: (typeof cockpitBridgeAvailable !== "undefined") && !!cockpitBridgeAvailable
    readonly property int enabledActionCount: enabledActions()
    readonly property int readonlyActionCount: Math.max(0, actions.length - enabledActionCount)
    readonly property string heroStampLabel: String(enabledActionCount) + " LIVE"
    readonly property var centerStagePanel: shellWindow ? DataUtils.objectOrEmpty(shellWindow.centerPanelData) : ({})
    readonly property var centerStageControl: shellWindow ? DataUtils.objectOrEmpty(shellWindow.centerControlSummary) : ({})
    readonly property var rightRailPanel: shellWindow ? DataUtils.objectOrEmpty(shellWindow.rightPanelData) : ({})
    readonly property var rightRailAnchor: DataUtils.objectOrEmpty(rightRailPanel["live_anchor"])
    readonly property var shellMeta: shellWindow ? DataUtils.objectOrEmpty(shellWindow.meta) : ({})
    readonly property string dockHandoffLabel: enabledActionCount > 0
        ? "执行坞站已经接上主舞台门控"
        : "执行坞站保持只读镜像门控"
    readonly property string dockHandoffDetail: enabledActionCount > 0
        ? "可执行动作继续沿用中心墙板与右舷剧本给出的事实边界，坞站不再像原型按钮区。"
        : "当前没有开放动作，但坞站仍保持与中心主舞台相同的合同语义和只读审计视图。"
    readonly property var dockHandoffModel: [
        {
            "label": "主舞台",
            "value": String(centerStagePanel["mission_call_sign"] || "--"),
            "detail": String(centerStageControl["link_profile"] || "GLOBAL WALLBOARD"),
            "tone": "neutral"
        },
        {
            "label": "弱网策略",
            "value": String(rightRailPanel["recommended_scenario_id"] || "--"),
            "detail": String(rightRailAnchor["valid_instance"] || rightRailAnchor["board_status"] || "--"),
            "tone": "warning"
        },
        {
            "label": "门控",
            "value": String(enabledActionCount) + " LIVE",
            "detail": String(readonlyActionCount) + " READ ONLY",
            "tone": enabledActionCount > 0 ? "online" : "warning"
        },
        {
            "label": "渲染",
            "value": softwareRenderEnabled ? "软件回退" : "图形加速",
            "detail": String(shellMeta["layout_strategy"] || "--"),
            "tone": softwareRenderEnabled ? "warning" : "online"
        }
    ]

    panelColor: shellWindow ? shellWindow.panelColorRaised : "#08131b"
    borderTone: shellWindow ? shellWindow.panelTraceStrong : "#1a3f61"
    accentTone: shellWindow ? shellWindow.accentCyan : "#38b6ff"

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

    function enabledActions() {
        var total = 0
        for (var index = 0; index < actions.length; ++index) {
            var action = DataUtils.objectOrEmpty(actions[index])
            if (!!action["enabled"])
                total += 1
        }
        return total
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
                GradientStop { position: 0.0; color: shellWindow ? shellWindow.shellDockTop : "#123554" }
                GradientStop { position: 0.5; color: shellWindow ? shellWindow.shellDockMid : "#0a1d2e" }
                GradientStop { position: 1.0; color: shellWindow ? shellWindow.shellDockBottom : "#06101a" }
            }
            border.color: shellWindow ? shellWindow.panelGlowStrong : "#3190cb"
            border.width: 1
            implicitHeight: heroLayout.implicitHeight + ((shellWindow ? shellWindow.cardPadding : 12) * 2)

            Rectangle {
                width: parent.width * 0.38
                height: parent.height * 0.9
                radius: width / 2
                color: "#4abfff"
                opacity: 0.1
                x: -width * 0.2
                y: -height * 0.2
            }

            Rectangle {
                anchors.fill: parent
                anchors.margins: 1
                radius: parent.radius - 1
                color: "transparent"
                border.color: "#143551"
                border.width: 1
                opacity: 0.82
            }

            Rectangle {
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                anchors.leftMargin: shellWindow ? shellWindow.scaled(14) : 14
                anchors.rightMargin: shellWindow ? shellWindow.scaled(14) : 14
                height: shellWindow ? shellWindow.scaled(2) : 2
                radius: height / 2
                gradient: Gradient {
                    orientation: Gradient.Horizontal
                    GradientStop { position: 0.0; color: "transparent" }
                    GradientStop { position: 0.15; color: "rgba(78,190,255,0.06)" }
                    GradientStop { position: 0.45; color: "rgba(78,190,255,0.52)" }
                    GradientStop { position: 0.55; color: "rgba(78,190,255,0.44)" }
                    GradientStop { position: 0.85; color: "rgba(78,190,255,0.08)" }
                    GradientStop { position: 1.0; color: "transparent" }
                }
                opacity: 0.74
            }

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

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: shellWindow ? shellWindow.compactGap : 8

                        Text {
                            Layout.fillWidth: true
                            text: panel["title"] || "操作窗 · 执行坞站"
                            color: shellWindow ? shellWindow.accentBlue : "#38b6ff"
                            font.pixelSize: shellWindow ? shellWindow.eyebrowSize : 10
                            font.family: shellWindow ? shellWindow.monoFamily : "JetBrains Mono"
                            font.letterSpacing: shellWindow ? shellWindow.scaled(1) : 1
                        }

                        Rectangle {
                            radius: shellWindow ? shellWindow.edgeRadius : 10
                            color: "#091726"
                            border.color: "#1d547c"
                            border.width: 1
                            implicitWidth: heroStamp.implicitWidth + ((shellWindow ? shellWindow.scaled(10) : 10) * 2)
                            implicitHeight: heroStamp.implicitHeight + ((shellWindow ? shellWindow.scaled(5) : 5) * 2)

                            Text {
                                id: heroStamp
                                anchors.centerIn: parent
                                text: root.heroStampLabel
                                color: shellWindow ? shellWindow.textPrimary : "#d5eeff"
                                font.pixelSize: shellWindow ? shellWindow.captionSize : 9
                                font.family: shellWindow ? shellWindow.monoFamily : "JetBrains Mono"
                            }
                        }
                    }

                    Text {
                        text: "执行指令坞站"
                        color: shellWindow ? shellWindow.textStrong : "#f4fbff"
                        font.pixelSize: shellWindow ? shellWindow.sectionTitleSize : 20
                        font.bold: true
                        font.family: shellWindow ? shellWindow.displayFamily : "Noto Sans CJK SC"
                    }

                    Text {
                        text: "执行链路已接线"
                        color: shellWindow ? shellWindow.textSecondary : "#83acc8"
                        font.pixelSize: shellWindow ? shellWindow.captionSize : 11
                        font.family: shellWindow ? shellWindow.monoFamily : "JetBrains Mono"
                        font.letterSpacing: shellWindow ? shellWindow.scaled(1) : 1
                    }

                    Text {
                        Layout.fillWidth: true
                        text: "延续主舞台的蓝色技术壳体语义，把真实可执行的合同动作收口为下方指令坞站，其余项继续保持只读显示。"
                        color: shellWindow ? shellWindow.textSecondary : "#83acc8"
                        wrapMode: Text.WordWrap
                        font.pixelSize: shellWindow ? shellWindow.bodySize : 12
                        font.family: shellWindow ? shellWindow.uiFamily : "Noto Sans CJK SC"
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        radius: shellWindow ? shellWindow.edgeRadius : 10
                        gradient: Gradient {
                            GradientStop { position: 0.0; color: "#0b1b2d" }
                            GradientStop { position: 1.0; color: "#091522" }
                        }
                        border.color: "#1f5a83"
                        border.width: 1
                        implicitHeight: doctrineColumn.implicitHeight + ((shellWindow ? shellWindow.scaled(9) : 9) * 2)

                        Column {
                            id: doctrineColumn
                            anchors.fill: parent
                            anchors.margins: shellWindow ? shellWindow.scaled(9) : 9
                            spacing: 2

                            Text {
                                text: "坞站门控 / ACTION GATE"
                                color: shellWindow ? shellWindow.accentCyan : "#72f3ff"
                                font.pixelSize: shellWindow ? shellWindow.captionSize : 10
                                font.family: shellWindow ? shellWindow.monoFamily : "JetBrains Mono"
                                font.letterSpacing: shellWindow ? shellWindow.scaled(1) : 1
                            }

                            Text {
                                width: parent.width
                                text: enabledActionCount > 0
                                    ? "可执行合同动作 " + String(enabledActionCount) + " 项，未开放动作保持只读。"
                                    : "当前没有开放执行动作，动作区全部作为只读合同镜像。"
                                color: shellWindow ? shellWindow.textSecondary : "#83acc8"
                                font.pixelSize: shellWindow ? shellWindow.captionSize : 11
                                font.family: shellWindow ? shellWindow.uiFamily : "Noto Sans CJK SC"
                                wrapMode: Text.WordWrap
                            }
                        }
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
                                "label": "可执行",
                                "value": String(enabledActionCount),
                                "tone": enabledActionCount > 0 ? "online" : "warning"
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
                            gradient: Gradient {
                                GradientStop { position: 0.0; color: Qt.lighter(root.toneFill(chip["tone"]), 1.14) }
                                GradientStop { position: 1.0; color: root.toneFill(chip["tone"]) }
                            }
                            border.color: root.toneColor(chip["tone"])
                            border.width: 1
                            height: chipColumn.implicitHeight + ((shellWindow ? shellWindow.scaled(8) : 8) * 2)
                            width: Math.max(shellWindow ? shellWindow.scaled(140) : 140, chipColumn.implicitWidth + (shellWindow ? shellWindow.scaled(20) : 20))

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
                                    font.pixelSize: shellWindow ? shellWindow.captionSize : 11
                                    font.bold: true
                                    font.family: shellWindow ? shellWindow.monoFamily : "JetBrains Mono"
                                }
                            }
                        }
                    }
                }

                Rectangle {
                    Layout.fillWidth: true
                    Layout.columnSpan: heroLayout.columns
                    radius: shellWindow ? shellWindow.edgeRadius : 10
                    gradient: Gradient {
                        GradientStop { position: 0.0; color: "#10253a" }
                        GradientStop { position: 0.5; color: "#0b1828" }
                        GradientStop { position: 1.0; color: "#081321" }
                    }
                    border.color: root.toneColor(enabledActionCount > 0 ? "online" : "warning")
                    border.width: 1
                    implicitHeight: handoffColumn.implicitHeight + ((shellWindow ? shellWindow.scaled(10) : 10) * 2)

                    Rectangle {
                        anchors.fill: parent
                        anchors.margins: 1
                        radius: parent.radius - 1
                        color: "transparent"
                        border.color: "#13344f"
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
                            GradientStop { position: 0.22; color: root.toneColor(enabledActionCount > 0 ? "online" : "warning") }
                            GradientStop { position: 0.72; color: Qt.lighter(root.toneColor(enabledActionCount > 0 ? "online" : "warning"), 1.16) }
                            GradientStop { position: 1.0; color: "transparent" }
                        }
                        opacity: 0.78
                    }

                    ColumnLayout {
                        id: handoffColumn
                        anchors.fill: parent
                        anchors.margins: shellWindow ? shellWindow.scaled(10) : 10
                        spacing: shellWindow ? shellWindow.compactGap : 8

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: shellWindow ? shellWindow.compactGap : 8

                            Text {
                                Layout.fillWidth: true
                                text: "执行联动 / COMMAND HANDOFF BUS"
                                color: shellWindow ? shellWindow.accentCyan : "#72f3ff"
                                font.pixelSize: shellWindow ? shellWindow.captionSize : 11
                                font.family: shellWindow ? shellWindow.monoFamily : "JetBrains Mono"
                                font.letterSpacing: shellWindow ? shellWindow.scaled(1) : 1
                            }

                            Rectangle {
                                radius: shellWindow ? shellWindow.edgeRadius : 10
                                color: "#091726"
                                border.color: "#1d547c"
                                border.width: 1
                                implicitWidth: handoffStamp.implicitWidth + ((shellWindow ? shellWindow.scaled(10) : 10) * 2)
                                implicitHeight: handoffStamp.implicitHeight + ((shellWindow ? shellWindow.scaled(5) : 5) * 2)

                                Text {
                                    id: handoffStamp
                                    anchors.centerIn: parent
                                    text: "CENTER -> DOCK"
                                    color: shellWindow ? shellWindow.textPrimary : "#d5eeff"
                                    font.pixelSize: shellWindow ? shellWindow.captionSize : 9
                                    font.family: shellWindow ? shellWindow.monoFamily : "JetBrains Mono"
                                }
                            }
                        }

                        Text {
                            Layout.fillWidth: true
                            text: root.dockHandoffLabel
                            color: shellWindow ? shellWindow.textStrong : "#f4fbff"
                            font.pixelSize: shellWindow ? shellWindow.bodyEmphasisSize : 14
                            font.bold: true
                            font.family: shellWindow ? shellWindow.uiFamily : "Noto Sans CJK SC"
                            wrapMode: Text.WordWrap
                        }

                        Text {
                            Layout.fillWidth: true
                            text: root.dockHandoffDetail
                            color: shellWindow ? shellWindow.textSecondary : "#83acc8"
                            font.pixelSize: shellWindow ? shellWindow.captionSize : 11
                            font.family: shellWindow ? shellWindow.uiFamily : "Noto Sans CJK SC"
                            wrapMode: Text.WordWrap
                        }

                        GridLayout {
                            Layout.fillWidth: true
                            columns: actionFlow.columns >= 4 ? 4 : 2
                            columnSpacing: shellWindow ? shellWindow.compactGap : 8
                            rowSpacing: shellWindow ? shellWindow.compactGap : 8

                            Repeater {
                                model: root.dockHandoffModel.length

                                delegate: Rectangle {
                                    readonly property var handoffData: root.dockHandoffModel[index]
                                    Layout.fillWidth: true
                                    radius: shellWindow ? shellWindow.edgeRadius : 10
                                    gradient: Gradient {
                                        GradientStop { position: 0.0; color: Qt.lighter(root.toneFill(handoffData["tone"]), 1.14) }
                                        GradientStop { position: 1.0; color: root.toneFill(handoffData["tone"]) }
                                    }
                                    border.color: root.toneColor(handoffData["tone"])
                                    border.width: 1
                                    implicitHeight: handoffMetricColumn.implicitHeight + ((shellWindow ? shellWindow.scaled(8) : 8) * 2)

                                    Column {
                                        id: handoffMetricColumn
                                        anchors.fill: parent
                                        anchors.margins: shellWindow ? shellWindow.scaled(8) : 8
                                        spacing: 2

                                        Text {
                                            text: handoffData["label"]
                                            color: shellWindow ? shellWindow.textMuted : "#4e7392"
                                            font.pixelSize: shellWindow ? shellWindow.captionSize : 11
                                            font.family: shellWindow ? shellWindow.monoFamily : "JetBrains Mono"
                                        }

                                        Text {
                                            width: parent.width
                                            text: handoffData["value"]
                                            color: shellWindow ? shellWindow.textStrong : "#f4fbff"
                                            font.pixelSize: shellWindow ? shellWindow.captionSize : 11
                                            font.bold: true
                                            font.family: shellWindow ? shellWindow.monoFamily : "JetBrains Mono"
                                            wrapMode: Text.WrapAnywhere
                                        }

                                        Text {
                                            width: parent.width
                                            text: handoffData["detail"]
                                            color: shellWindow ? shellWindow.textSecondary : "#83acc8"
                                            font.pixelSize: shellWindow ? shellWindow.captionSize : 10
                                            font.family: shellWindow ? shellWindow.uiFamily : "Noto Sans CJK SC"
                                            wrapMode: Text.WordWrap
                                            maximumLineCount: 2
                                            elide: Text.ElideRight
                                        }
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
                text: "动作窗口 / COMMAND WINDOWS"
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
                implicitWidth: actionCountText.implicitWidth + ((shellWindow ? shellWindow.scaled(12) : 12) * 2)
                implicitHeight: actionCountText.implicitHeight + ((shellWindow ? shellWindow.scaled(5) : 5) * 2)

                Text {
                    id: actionCountText
                    anchors.centerIn: parent
                    text: String(actions.length) + " ACTIONS"
                    color: shellWindow ? shellWindow.textPrimary : "#d5eeff"
                    font.pixelSize: shellWindow ? shellWindow.captionSize : 10
                    font.family: shellWindow ? shellWindow.monoFamily : "JetBrains Mono"
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

                        Rectangle {
                            anchors.fill: parent
                            anchors.margins: 1
                            radius: parent.radius - 1
                            color: "transparent"
                            border.color: actionCard.enabledAction ? "#143654" : "#112334"
                            border.width: 1
                            opacity: 0.74
                        }

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

                        Rectangle {
                            anchors.right: parent.right
                            anchors.top: parent.top
                            anchors.margins: shellWindow ? shellWindow.scaled(10) : 10
                            radius: shellWindow ? shellWindow.edgeRadius : 10
                            color: root.toneFill(modelData["tone"])
                            border.color: root.toneColor(modelData["tone"])
                            border.width: 1
                            implicitWidth: toneBadgeText.implicitWidth + ((shellWindow ? shellWindow.scaled(10) : 10) * 2)
                            implicitHeight: toneBadgeText.implicitHeight + ((shellWindow ? shellWindow.scaled(5) : 5) * 2)

                            Text {
                                id: toneBadgeText
                                anchors.centerIn: parent
                                text: String(modelData["tone"] || "neutral").toUpperCase()
                                color: shellWindow ? shellWindow.textPrimary : "#d5eeff"
                                font.pixelSize: shellWindow ? shellWindow.captionSize : 9
                                font.family: shellWindow ? shellWindow.monoFamily : "JetBrains Mono"
                            }
                        }

                        MouseArea {
                            id: actionArea
                            anchors.fill: parent
                            enabled: actionCard.enabledAction
                            hoverEnabled: actionCard.enabledAction
                            cursorShape: actionCard.enabledAction ? Qt.PointingHandCursor : Qt.ArrowCursor
                            onClicked: {
                                if (modelData["action_id"] === "reload_contracts" && bridgeAvailable)
                                    cockpitBridge.reload()
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
            gradient: Gradient {
                GradientStop { position: 0.0; color: "#0b1b2d" }
                GradientStop { position: 1.0; color: "#091421" }
            }
            border.color: "#1f557c"
            border.width: 1
            implicitHeight: footerColumn.implicitHeight + ((shellWindow ? shellWindow.scaled(10) : 10) * 2)

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
                opacity: 0.76
            }

            RowLayout {
                id: footerColumn
                anchors.fill: parent
                anchors.margins: shellWindow ? shellWindow.scaled(10) : 10
                spacing: shellWindow ? shellWindow.compactGap : 8

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 2

                    Text {
                        text: "审计回路 / AUDIT LOOP"
                        color: shellWindow ? shellWindow.accentBlue : "#38b6ff"
                        font.pixelSize: shellWindow ? shellWindow.captionSize : 11
                        font.family: shellWindow ? shellWindow.monoFamily : "JetBrains Mono"
                        font.letterSpacing: shellWindow ? shellWindow.scaled(1) : 1
                    }

                    Text {
                        Layout.fillWidth: true
                        text: panel["footer_note"] || "执行舱保持合同边界，只对已接线动作开放人工触发入口。"
                        color: shellWindow ? shellWindow.textMuted : "#4e7392"
                        wrapMode: Text.WordWrap
                        font.pixelSize: shellWindow ? shellWindow.captionSize : 11
                        font.family: shellWindow ? shellWindow.uiFamily : "Noto Sans CJK SC"
                    }
                }

                Rectangle {
                    Layout.alignment: Qt.AlignTop
                    radius: shellWindow ? shellWindow.edgeRadius : 10
                    color: "#091726"
                    border.color: "#1c547c"
                    border.width: 1
                    implicitWidth: footerStampColumn.implicitWidth + ((shellWindow ? shellWindow.scaled(10) : 10) * 2)
                    implicitHeight: footerStampColumn.implicitHeight + ((shellWindow ? shellWindow.scaled(6) : 6) * 2)

                    Column {
                        id: footerStampColumn
                        anchors.centerIn: parent
                        spacing: 1

                        Text {
                            text: "READ ONLY"
                            color: shellWindow ? shellWindow.textMuted : "#4e7392"
                            font.pixelSize: shellWindow ? shellWindow.captionSize : 9
                            font.family: shellWindow ? shellWindow.monoFamily : "JetBrains Mono"
                        }

                        Text {
                            text: String(readonlyActionCount)
                            color: shellWindow ? shellWindow.textPrimary : "#d5eeff"
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
