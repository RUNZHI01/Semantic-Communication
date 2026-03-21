import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import QtQuick.Window 2.15
import "components"
import "components/DataUtils.js" as DataUtils

ApplicationWindow {
    id: root

    readonly property bool bridgeAvailable: (typeof cockpitBridgeAvailable !== "undefined") && !!cockpitBridgeAvailable
    readonly property var uiState: DataUtils.jsonObjectOrEmpty((typeof cockpitUiStateJson !== "undefined") ? cockpitUiStateJson : "{}")
    readonly property var zones: DataUtils.objectOrEmpty(uiState["zones"])
    readonly property var metrics: DataUtils.objectOrEmpty((typeof screenMetrics !== "undefined") ? screenMetrics : null)
    readonly property var insets: DataUtils.objectOrEmpty((typeof safeAreaInsets !== "undefined") ? safeAreaInsets : null)
    readonly property var options: DataUtils.objectOrEmpty((typeof launchOptions !== "undefined") ? launchOptions : null)

    readonly property var leftPanelData: DataUtils.objectOrEmpty(zones["left_status_panel"])
    readonly property var centerPanelData: DataUtils.objectOrEmpty(zones["center_tactical_view"])
    readonly property var rightPanelData: DataUtils.objectOrEmpty(zones["right_weak_network_panel"])
    readonly property var bottomPanelData: DataUtils.objectOrEmpty(zones["bottom_action_strip"])
    readonly property var bottomActions: DataUtils.arrayOrEmpty(bottomPanelData["actions"])
    readonly property var meta: DataUtils.objectOrEmpty(uiState["meta"])
    readonly property var statusRows: DataUtils.arrayOrEmpty(leftPanelData["rows"])
    readonly property var centerControlSummary: DataUtils.objectOrEmpty(centerPanelData["control_summary"])
    readonly property var centerFeedContract: DataUtils.objectOrEmpty(centerPanelData["feed_contract"])
    readonly property var centerSampleData: DataUtils.objectOrEmpty(centerPanelData["sample"])
    readonly property var trackData: DataUtils.arrayOrEmpty(centerPanelData["track"])
    readonly property var currentPosition: DataUtils.objectOrEmpty(centerPanelData["position"])
    readonly property var kinematics: DataUtils.objectOrEmpty(centerPanelData["kinematics"])
    readonly property var fix: DataUtils.objectOrEmpty(centerPanelData["fix"])
    readonly property var liveAnchor: DataUtils.objectOrEmpty(rightPanelData["live_anchor"])
    readonly property var rightScenarios: DataUtils.arrayOrEmpty(rightPanelData["scenarios"])
    readonly property var recommendedScenario: recommendedScenarioObject(rightScenarios)
    readonly property var recommendedComparison: DataUtils.objectOrEmpty(recommendedScenario["comparison"])
    readonly property var recommendedCommands: DataUtils.objectOrEmpty(recommendedScenario["commands"])
    readonly property var recommendedEvidence: DataUtils.arrayOrEmpty(recommendedScenario["evidence"])
    readonly property string recommendedScenarioId: String(rightPanelData["recommended_scenario_id"] || "--")
    readonly property int enabledBottomActions: enabledActionTotal(bottomActions)
    readonly property bool softwareRenderEnabled: !!options["softwareRender"]

    readonly property int designWidth: 1440
    readonly property int designHeight: 900

    readonly property string displayFamily: "Noto Sans CJK SC"
    readonly property string uiFamily: "Noto Sans CJK SC"
    readonly property string monoFamily: "JetBrains Mono"

    readonly property color bgColorTop: "#09111c"
    readonly property color bgColorMid: "#0b1522"
    readonly property color bgColorBottom: "#050910"
    readonly property color hazeBlue: "#153250"
    readonly property color hazeAmber: "#6a371a"
    readonly property color shellColor: "#0f1724"
    readonly property color shellColorRaised: "#131f31"
    readonly property color shellColorInset: "#0b1522"
    readonly property color shellColorGlass: "#182537"
    readonly property color panelColor: "#121d2d"
    readonly property color panelColorRaised: "#162336"
    readonly property color panelColorSoft: "#0d1624"
    readonly property color cardColor: "#172435"
    readonly property color cardColorSoft: "#101926"
    readonly property color borderSoft: "#31465f"
    readonly property color borderStrong: "#73b6ff"
    readonly property color accentBlue: "#73b6ff"
    readonly property color accentBlueSoft: "#4d86bc"
    readonly property color accentCyan: "#acecff"
    readonly property color accentGreen: "#79deb2"
    readonly property color accentAmber: "#f0b97c"
    readonly property color accentRed: "#ff8c95"
    readonly property color textStrong: "#f5f7fb"
    readonly property color textPrimary: "#dce6f2"
    readonly property color textSecondary: "#9aa9bd"
    readonly property color textMuted: "#76859a"
    readonly property color textTertiary: "#536277"
    readonly property color gridLine: "#162231"
    readonly property color gridLineStrong: "#26364c"
    readonly property color shellStageTop: "#22364b"
    readonly property color shellStageMid: "#141f2e"
    readonly property color shellStageBottom: "#0b1119"
    readonly property color shellDockTop: "#1b293b"
    readonly property color shellDockMid: "#121c2a"
    readonly property color shellDockBottom: "#0a1018"
    readonly property color panelGlowStrong: "#84bfff"
    readonly property color panelTraceStrong: "#3d5572"
    readonly property color panelTrace: "#1d2c40"
    readonly property color panelTraceSoft: "#121b28"
    readonly property color shellGlowOuter: "#71b0ff"
    readonly property color shellGlowSoft: "#1b2940"
    readonly property color shellFabricTop: "#182638"
    readonly property color shellFabricMid: "#0f1826"
    readonly property color shellFabricBottom: "#09111a"
    readonly property color shellCanopyTop: "#23374b"
    readonly property color shellCanopyMid: "#121d2b"
    readonly property color shellCanopyBottom: "#091019"
    readonly property color shellCanopyEdge: "#30465c"
    readonly property color shellDeckAura: "#233a52"

    readonly property real widthScale: Math.max(0.72, Math.min(1.16, Number(metrics["width"] || designWidth) / designWidth))
    readonly property real heightScale: Math.max(0.72, Math.min(1.16, Number(metrics["height"] || designHeight) / designHeight))
    readonly property real uiScale: Math.min(widthScale, heightScale)

    readonly property int safeLeft: Number(insets["left"] || 0)
    readonly property int safeTop: Number(insets["top"] || 0)
    readonly property int safeRight: Number(insets["right"] || 0)
    readonly property int safeBottom: Number(insets["bottom"] || 0)

    readonly property int viewportHeight: height > 0 ? height : Number(metrics["height"] || designHeight)
    readonly property real contentWidth: Math.max(1, width - safeLeft - safeRight - (outerPadding * 2))
    readonly property bool wideLayout: contentWidth >= scaled(1320)
    readonly property bool mediumLayout: !wideLayout && contentWidth >= scaled(980)
    readonly property bool compactLayout: !wideLayout && !mediumLayout
    readonly property bool shortViewport: viewportHeight < 780
    readonly property bool tallViewport: viewportHeight >= 960

    readonly property int outerPadding: scaled(compactLayout ? 14 : 18)
    readonly property int shellPadding: scaled(compactLayout ? 18 : 24)
    readonly property int zoneGap: scaled(compactLayout ? 12 : 16)
    readonly property int compactGap: scaled(8)
    readonly property int panelPadding: scaled(compactLayout ? 16 : 18)
    readonly property int cardPadding: scaled(compactLayout ? 12 : 14)
    readonly property int panelRadius: scaled(22)
    readonly property int cardRadius: scaled(16)
    readonly property int edgeRadius: scaled(12)
    readonly property int headerTitleSize: scaled(compactLayout ? 30 : 36)
    readonly property int sectionTitleSize: scaled(compactLayout ? 22 : 26)
    readonly property int bodyEmphasisSize: scaled(compactLayout ? 14 : 15)
    readonly property int bodySize: scaled(13)
    readonly property int captionSize: scaled(10)
    readonly property int eyebrowSize: scaled(10)

    readonly property string topTitle: primaryLabel(meta["title"] || "飞腾原生座舱 / Feiteng Native Cockpit")
    readonly property string topSubtitle: String(meta["subtitle"] || "Qt/QML 原生壳体继续读取仓库现有 TVM/OpenAMP 演示合同。")
    readonly property string activeSourceLabel: String(centerFeedContract["active_source_label"] || centerPanelData["source_label"] || "--")
    readonly property string systemSessionValue: String((statusRow("会话") || {})["value"] || "--")
    readonly property string recentEventValue: String((statusRow("最近事件") || {})["value"] || "--")
    readonly property string recentEventTone: recentEventValue.indexOf("REJECT") >= 0
        ? "warning"
        : String((statusRow("最近事件") || {})["tone"] || "neutral")
    readonly property string heartbeatValue: String((statusRow("心跳") || {})["value"] || "--")
    readonly property string heartbeatTone: String((statusRow("心跳") || {})["tone"] || "neutral")
    readonly property string linkProfileValue: String(centerControlSummary["link_profile"] || (statusRow("链路档位") || {})["value"] || "--")
    readonly property string snapshotReasonValue: String((statusRow("快照原因") || {})["value"] || "--")
    readonly property string truthNoteValue: String(leftPanelData["truth_note"] || rightPanelData["truth_note"] || "")
    readonly property string eventTimeValue: String((statusRow("事件时间") || {})["value"] || "--")
    readonly property string launchHint: String(meta["launch_hint"] || "bash ./session_bootstrap/scripts/run_cockpit_native.sh")
    readonly property string snapshotRelativePath: String(leftPanelData["snapshot_path"] || "--")

    property int currentPage: 0

    readonly property var navigationModel: [
        {
            "index": 0,
            "label": "总览",
            "english": "Landing",
            "detail": "中心墙板",
            "summary": "首屏只保留世界地图主墙板、精简摘要与跳转入口。"
        },
        {
            "index": 1,
            "label": "系统板态",
            "english": "System",
            "detail": "证据总线",
            "summary": "查看会话、心跳、快照原因与真值说明。"
        },
        {
            "index": 2,
            "label": "飞行合同",
            "english": "Flight",
            "detail": "地图与遥测",
            "summary": "聚焦飞机合同、世界地图与实时航迹镜像。"
        },
        {
            "index": 3,
            "label": "弱网策略",
            "english": "Weak-Link",
            "detail": "推荐档与锚点",
            "summary": "聚焦推荐弱网档、在线锚点与吞吐证据。"
        },
        {
            "index": 4,
            "label": "执行坞站",
            "english": "Action Dock",
            "detail": "动作与启动",
            "summary": "查看合同动作、软件渲染路径与启动命令。"
        }
    ]

    readonly property var landingBadgeModel: [
        {
            "label": "会话",
            "value": systemSessionValue,
            "tone": "neutral"
        },
        {
            "label": "最近事件",
            "value": recentEventValue,
            "tone": recentEventTone
        },
        {
            "label": "在线锚点",
            "value": String(liveAnchor["valid_instance"] || "--"),
            "tone": String(liveAnchor["tone"] || "neutral")
        },
        {
            "label": "链路档位",
            "value": linkProfileValue,
            "tone": heartbeatTone
        },
        {
            "label": "渲染路径",
            "value": softwareRenderEnabled ? "软件安全渲染" : "GPU 优先渲染",
            "tone": softwareRenderEnabled ? "warning" : "online"
        }
    ]

    readonly property var landingJumpModel: [
        {
            "index": 1,
            "label": "系统板态",
            "english": "System",
            "summary": "会话、心跳与快照原因",
            "value": heartbeatValue + " / " + snapshotReasonValue,
            "tone": heartbeatTone
        },
        {
            "index": 2,
            "label": "飞行合同",
            "english": "Flight",
            "summary": "地图、遥测与数据合同",
            "value": activeSourceLabel,
            "tone": "online"
        },
        {
            "index": 3,
            "label": "弱网策略",
            "english": "Weak-Link",
            "summary": "推荐档与在线锚点",
            "value": recommendedScenarioId,
            "tone": "warning"
        },
        {
            "index": 4,
            "label": "执行坞站",
            "english": "Action Dock",
            "summary": "合同动作与启动命令",
            "value": String(enabledBottomActions) + " / " + String(bottomActions.length) + " actions",
            "tone": enabledBottomActions > 0 ? "online" : "warning"
        }
    ]

    readonly property var landingTelemetryModel: [
        {
            "label": "当前位置",
            "value": coordinatePair(currentPosition),
            "detail": "经纬度 / WGS84",
            "tone": "neutral"
        },
        {
            "label": "飞行高度",
            "value": formattedMetric(kinematics["altitude_m"], 0, "m"),
            "detail": "垂直速度 " + formattedMetric(kinematics["vertical_speed_mps"], 1, "m/s"),
            "tone": "online"
        },
        {
            "label": "地速与航向",
            "value": formattedMetric(kinematics["ground_speed_kph"], 0, "km/h"),
            "detail": "航向 " + formattedMetric(kinematics["heading_deg"], 0, "°"),
            "tone": "neutral"
        },
        {
            "label": "定位质量",
            "value": String(fix["type"] || "--") + " / " + formattedMetric(fix["satellites"], 0, "sat"),
            "detail": "置信 " + formattedMetric(fix["confidence_m"], 1, "m"),
            "tone": "online"
        }
    ]

    readonly property string landingSummaryTitle: recentEventTone === "warning"
        ? "首屏改为问题导向的世界态势墙板"
        : "首屏改为地图主导的命令中心壳体"
    readonly property string landingSummaryText: String(centerControlSummary["last_event_message"] || rightPanelData["summary"] || topSubtitle)

    minimumWidth: 760
    minimumHeight: 600
    visible: true
    color: bgColorBottom
    title: topTitle

    function scaled(value) {
        return Math.max(1, Math.round(value * uiScale))
    }

    function primaryLabel(text) {
        var raw = String(text || "")
        var slash = raw.indexOf("/")
        return slash >= 0 ? raw.slice(0, slash).trim() : raw
    }

    function secondaryLabel(text) {
        var raw = String(text || "")
        var slash = raw.indexOf("/")
        return slash >= 0 ? raw.slice(slash + 1).trim() : ""
    }

    function statusRow(label) {
        for (var index = 0; index < statusRows.length; ++index) {
            var row = DataUtils.objectOrEmpty(statusRows[index])
            if (String(row["label"] || "") === label)
                return row
        }
        return ({})
    }

    function enabledActionTotal(actionsModel) {
        var actionList = DataUtils.arrayOrEmpty(actionsModel)
        var total = 0
        for (var index = 0; index < actionList.length; ++index) {
            var action = DataUtils.objectOrEmpty(actionList[index])
            if (!!action["enabled"])
                total += 1
        }
        return total
    }

    function toneColor(tone) {
        if (tone === "online")
            return accentGreen
        if (tone === "warning" || tone === "degraded")
            return accentAmber
        if (tone === "danger")
            return accentRed
        return accentBlue
    }

    function toneFill(tone) {
        if (tone === "online")
            return "#12211c"
        if (tone === "warning" || tone === "degraded")
            return "#281f17"
        if (tone === "danger")
            return "#29161a"
        return "#121b28"
    }

    function formattedMetric(value, decimals, suffix) {
        var resolved = Number(value)
        if (!isFinite(resolved))
            return "--"
        return resolved.toFixed(decimals) + (suffix ? (" " + suffix) : "")
    }

    function coordinatePair(point) {
        var resolved = DataUtils.objectOrEmpty(point)
        var latitude = Number(resolved["latitude"])
        var longitude = Number(resolved["longitude"])
        if (!isFinite(latitude) || !isFinite(longitude))
            return "--"
        return latitude.toFixed(3) + "°, " + longitude.toFixed(3) + "°"
    }

    function recommendedScenarioObject(scenariosModel) {
        var scenarioList = DataUtils.arrayOrEmpty(scenariosModel)
        for (var index = 0; index < scenarioList.length; ++index) {
            var scenario = DataUtils.objectOrEmpty(scenarioList[index])
            if (!!scenario["recommended"])
                return scenario
        }
        return scenarioList.length > 0 ? DataUtils.objectOrEmpty(scenarioList[0]) : ({})
    }

    Component.onCompleted: {
        var availableWidth = Math.max(minimumWidth, Number(metrics["width"] || designWidth))
        var availableHeight = Math.max(minimumHeight, Number(metrics["height"] || designHeight))
        width = Math.max(minimumWidth, Math.min(Math.round(availableWidth * 0.96), scaled(1720)))
        height = Math.max(minimumHeight, Math.min(Math.round(availableHeight * 0.96), scaled(980)))
    }

    Rectangle {
        anchors.fill: parent
        gradient: Gradient {
            GradientStop { position: 0.0; color: root.bgColorTop }
            GradientStop { position: 0.42; color: root.bgColorMid }
            GradientStop { position: 1.0; color: root.bgColorBottom }
        }
    }

    Rectangle {
        width: root.width * 0.72
        height: root.height * 0.68
        radius: width / 2
        color: root.hazeBlue
        opacity: 0.16
        x: -width * 0.24
        y: -height * 0.08
    }

    Rectangle {
        width: root.width * 0.46
        height: root.height * 0.4
        radius: width / 2
        color: root.hazeAmber
        opacity: 0.1
        x: root.width - (width * 0.76)
        y: -height * 0.18
    }

    Rectangle {
        width: root.width * 1.1
        height: root.scaled(180)
        rotation: -6
        color: "#17304b"
        opacity: 0.16
        x: -root.width * 0.05
        y: root.height * 0.32
    }

    Item {
        id: backdropGrid
        anchors.fill: parent
        opacity: 0.18

        Repeater {
            model: 12

            delegate: Rectangle {
                width: backdropGrid.width
                height: 1
                color: index % 3 === 0 ? root.gridLineStrong : root.gridLine
                y: index * (backdropGrid.height / 11)
            }
        }

        Repeater {
            model: 18

            delegate: Rectangle {
                width: 1
                height: backdropGrid.height
                color: index % 4 === 0 ? root.gridLineStrong : root.gridLine
                x: index * (backdropGrid.width / 17)
            }
        }
    }

    Rectangle {
        id: shellSurface
        anchors.fill: parent
        anchors.leftMargin: root.safeLeft + root.outerPadding
        anchors.topMargin: root.safeTop + root.outerPadding
        anchors.rightMargin: root.safeRight + root.outerPadding
        anchors.bottomMargin: root.safeBottom + root.outerPadding
        radius: root.panelRadius + root.scaled(6)
        color: root.shellColor
        border.color: "#31455d"
        border.width: 1
        clip: true

        Rectangle {
            anchors.fill: parent
            radius: parent.radius
            gradient: Gradient {
                GradientStop { position: 0.0; color: root.shellColorGlass }
                GradientStop { position: 0.28; color: root.shellColorRaised }
                GradientStop { position: 0.58; color: root.shellColorInset }
                GradientStop { position: 1.0; color: "#070c13" }
            }
        }

        Rectangle {
            anchors.fill: parent
            radius: parent.radius
            gradient: Gradient {
                GradientStop { position: 0.0; color: "#0affffff" }
                GradientStop { position: 0.2; color: "#04ffffff" }
                GradientStop { position: 0.5; color: "transparent" }
                GradientStop { position: 1.0; color: "#26000000" }
            }
        }

        Rectangle {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            height: root.scaled(3)
            gradient: Gradient {
                orientation: Gradient.Horizontal
                GradientStop { position: 0.0; color: "transparent" }
                GradientStop { position: 0.18; color: root.accentBlueSoft }
                GradientStop { position: 0.5; color: root.accentBlue }
                GradientStop { position: 0.82; color: root.accentCyan }
                GradientStop { position: 1.0; color: "transparent" }
            }
            opacity: 0.88
        }

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: root.shellPadding
            spacing: root.zoneGap

            PanelFrame {
                shellWindow: root
                panelColor: root.panelColorSoft
                borderTone: root.borderSoft
                accentTone: root.accentBlue
                Layout.fillWidth: true
                implicitHeight: headerContent.implicitHeight + (root.panelPadding * 2)

                GridLayout {
                    id: headerContent
                    anchors.fill: parent
                    anchors.margins: root.panelPadding
                    columns: root.compactLayout ? 1 : 2
                    columnSpacing: root.zoneGap
                    rowSpacing: root.compactGap

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: root.compactGap

                        Text {
                            text: "飞腾派命令中心 / Native Command Center"
                            color: root.accentBlue
                            font.pixelSize: root.eyebrowSize
                            font.family: root.monoFamily
                            font.letterSpacing: root.scaled(1)
                        }

                        Text {
                            text: root.topTitle
                            color: root.textStrong
                            font.pixelSize: root.headerTitleSize
                            font.bold: true
                            font.family: root.displayFamily
                        }

                        Text {
                            Layout.fillWidth: true
                            text: root.currentPage === 0
                                ? "首屏收敛为地图主墙板，系统板态、飞行合同、弱网策略和执行坞站全部转入独立页面。"
                                : String(DataUtils.objectOrEmpty(root.navigationModel[root.currentPage])["summary"] || "")
                            color: root.textSecondary
                            font.pixelSize: root.bodySize
                            font.family: root.uiFamily
                            wrapMode: Text.WordWrap
                        }

                        Item {
                            Layout.fillWidth: true
                            implicitHeight: badgeFlow.implicitHeight

                            Flow {
                                id: badgeFlow
                                width: parent.width
                                spacing: root.compactGap

                                Repeater {
                                    model: root.landingBadgeModel

                                    delegate: Rectangle {
                                        property var itemData: modelData
                                        radius: root.edgeRadius
                                        color: root.toneFill(String(itemData["tone"] || "neutral"))
                                        border.color: root.toneColor(String(itemData["tone"] || "neutral"))
                                        border.width: 1
                                        implicitWidth: badgeRow.implicitWidth + (root.scaled(12) * 2)
                                        implicitHeight: badgeRow.implicitHeight + (root.scaled(8) * 2)

                                        Row {
                                            id: badgeRow
                                            anchors.centerIn: parent
                                            spacing: root.scaled(10)

                                            Text {
                                                text: itemData["label"]
                                                color: root.textMuted
                                                font.pixelSize: root.captionSize
                                                font.family: root.monoFamily
                                            }

                                            Text {
                                                text: itemData["value"]
                                                color: root.textStrong
                                                font.pixelSize: root.captionSize
                                                font.bold: true
                                                font.family: root.uiFamily
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }

                    Item {
                        Layout.fillWidth: true
                        implicitHeight: navColumn.implicitHeight

                        Column {
                            id: navColumn
                            anchors.right: parent.right
                            anchors.left: root.compactLayout ? parent.left : undefined
                            spacing: root.compactGap

                            Text {
                                text: "页面导航"
                                color: root.textMuted
                                font.pixelSize: root.captionSize
                                font.family: root.monoFamily
                            }

                            Flow {
                                width: root.compactLayout ? parent.width : Math.max(root.scaled(420), implicitWidth)
                                spacing: root.compactGap

                                Repeater {
                                    model: root.navigationModel

                                    delegate: Rectangle {
                                        property var itemData: modelData
                                        readonly property bool active: root.currentPage === Number(itemData["index"])
                                        radius: root.edgeRadius
                                        color: active ? "#18283c" : "#0f1723"
                                        border.color: active
                                            ? root.accentBlue
                                            : "#2b3d54"
                                        border.width: 1
                                        implicitWidth: navButtonColumn.implicitWidth + (root.scaled(16) * 2)
                                        implicitHeight: navButtonColumn.implicitHeight + (root.scaled(10) * 2)

                                        Column {
                                            id: navButtonColumn
                                            anchors.centerIn: parent
                                            spacing: 1

                                            Text {
                                                text: itemData["label"]
                                                color: active ? root.textStrong : root.textPrimary
                                                font.pixelSize: root.bodySize
                                                font.bold: true
                                                font.family: root.uiFamily
                                            }

                                            Text {
                                                visible: !root.compactLayout
                                                text: itemData["detail"]
                                                color: active ? root.accentBlue : root.textMuted
                                                font.pixelSize: root.captionSize
                                                font.family: root.monoFamily
                                            }
                                        }

                                        MouseArea {
                                            anchors.fill: parent
                                            hoverEnabled: true
                                            cursorShape: Qt.PointingHandCursor
                                            onClicked: root.currentPage = Number(parent.itemData["index"])
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }

            StackLayout {
                id: pageStack
                Layout.fillWidth: true
                Layout.fillHeight: true
                currentIndex: root.currentPage

                Item {
                    Layout.fillWidth: true
                    Layout.fillHeight: true

                    GridLayout {
                        anchors.fill: parent
                        columns: root.wideLayout ? 12 : 1
                        columnSpacing: root.zoneGap
                        rowSpacing: root.zoneGap

                        PanelFrame {
                            shellWindow: root
                            panelColor: root.cardColor
                            borderTone: root.borderStrong
                            accentTone: root.accentBlue
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            Layout.columnSpan: root.wideLayout ? 8 : 1
                            Layout.minimumHeight: root.scaled(root.wideLayout ? 420 : (root.mediumLayout ? 340 : 260))
                            Layout.preferredHeight: root.scaled(root.wideLayout ? 560 : (root.mediumLayout ? 410 : 300))

                            Item {
                                anchors.fill: parent
                                anchors.margins: root.scaled(14)

                                WorldMapStage {
                                    anchors.fill: parent
                                    shellWindow: root
                                    trackData: root.trackData
                                    currentPoint: root.currentPosition
                                    headingDeg: Number(root.kinematics["heading_deg"] || 0)
                                    currentLabel: String(root.centerPanelData["mission_call_sign"] || "M9-DEMO") + " 实时航迹"
                                    currentDetail: root.activeSourceLabel + " / " + root.linkProfileValue
                                    anchorLabel: String(root.liveAnchor["valid_instance"] || "--")
                                    projectionLabel: "等经纬投影 / Equirectangular"
                                    scenarioLabel: root.recommendedScenarioId
                                    scenarioTone: String(root.liveAnchor["tone"] || "neutral")
                                }

                                Rectangle {
                                    anchors.right: parent.right
                                    anchors.top: parent.top
                                    anchors.margins: root.scaled(16)
                                    radius: root.edgeRadius
                                    color: "#e60d1522"
                                    border.color: root.accentBlue
                                    border.width: 1
                                    implicitWidth: mapActionRow.implicitWidth + (root.scaled(14) * 2)
                                    implicitHeight: mapActionRow.implicitHeight + (root.scaled(10) * 2)

                                    Row {
                                        id: mapActionRow
                                        anchors.centerIn: parent
                                        spacing: root.scaled(8)

                                        Text {
                                            text: "查看飞行合同"
                                            color: root.textStrong
                                            font.pixelSize: root.bodySize
                                            font.bold: true
                                            font.family: root.uiFamily
                                        }

                                        Text {
                                            text: ">"
                                            color: root.accentBlue
                                            font.pixelSize: root.bodyEmphasisSize
                                            font.bold: true
                                            font.family: root.monoFamily
                                        }
                                    }

                                    MouseArea {
                                        anchors.fill: parent
                                        hoverEnabled: true
                                        cursorShape: Qt.PointingHandCursor
                                        onClicked: root.currentPage = 2
                                    }
                                }

                                Flow {
                                    id: telemetryFlow
                                    width: parent.width - (root.scaled(32))
                                    anchors.left: parent.left
                                    anchors.bottom: parent.bottom
                                    anchors.leftMargin: root.scaled(16)
                                    anchors.bottomMargin: root.scaled(16)
                                    spacing: root.compactGap

                                    Repeater {
                                        model: root.landingTelemetryModel

                                        delegate: Rectangle {
                                            property var itemData: modelData
                                            width: root.wideLayout
                                                ? ((telemetryFlow.width - (root.compactGap * 3)) / 4)
                                                : ((telemetryFlow.width - root.compactGap) / 2)
                                            radius: root.edgeRadius
                                            color: "#dc0d1624"
                                            border.color: "#31455c"
                                            border.width: 1
                                            implicitHeight: telemetryColumn.implicitHeight + (root.scaled(12) * 2)

                                            Column {
                                                id: telemetryColumn
                                                anchors.fill: parent
                                                anchors.margins: root.scaled(12)
                                                spacing: root.scaled(2)

                                                Text {
                                                    text: itemData["label"]
                                                    color: root.textMuted
                                                    font.pixelSize: root.captionSize
                                                    font.family: root.monoFamily
                                                }

                                                Text {
                                                    width: parent.width
                                                    text: itemData["value"]
                                                    color: root.textStrong
                                                    font.pixelSize: root.bodyEmphasisSize
                                                    font.bold: true
                                                    font.family: root.uiFamily
                                                    elide: Text.ElideRight
                                                }

                                                Text {
                                                    width: parent.width
                                                    text: itemData["detail"]
                                                    color: root.textSecondary
                                                    font.pixelSize: root.captionSize
                                                    font.family: root.uiFamily
                                                    wrapMode: Text.WordWrap
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }

                        ColumnLayout {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            Layout.columnSpan: root.wideLayout ? 4 : 1
                            spacing: root.zoneGap

                            PanelFrame {
                                shellWindow: root
                                panelColor: root.panelColor
                                borderTone: root.borderSoft
                                accentTone: root.accentAmber
                                Layout.fillWidth: true
                                Layout.fillHeight: root.wideLayout
                                implicitHeight: landingCommandColumn.implicitHeight + (root.panelPadding * 2)

                                ColumnLayout {
                                    id: landingCommandColumn
                                    anchors.fill: parent
                                    anchors.margins: root.panelPadding
                                    spacing: root.compactGap

                                    Text {
                                        text: "命令摘要 / Command Brief"
                                        color: root.accentAmber
                                        font.pixelSize: root.eyebrowSize
                                        font.family: root.monoFamily
                                        font.letterSpacing: root.scaled(1)
                                    }

                                    Text {
                                        text: root.landingSummaryTitle
                                        color: root.textStrong
                                        font.pixelSize: root.sectionTitleSize
                                        font.bold: true
                                        font.family: root.displayFamily
                                        wrapMode: Text.WordWrap
                                    }

                                    Text {
                                        Layout.fillWidth: true
                                        text: root.landingSummaryText
                                        color: root.textSecondary
                                        font.pixelSize: root.bodySize
                                        font.family: root.uiFamily
                                        wrapMode: Text.WordWrap
                                    }

                                    Rectangle {
                                        Layout.fillWidth: true
                                        Layout.preferredHeight: 1
                                        color: "#28384d"
                                    }

                                    GridLayout {
                                        Layout.fillWidth: true
                                        columns: 2
                                        columnSpacing: root.compactGap
                                        rowSpacing: root.compactGap

                                        Repeater {
                                            model: [
                                                {
                                                    "label": "会话",
                                                    "value": root.systemSessionValue,
                                                    "tone": "neutral"
                                                },
                                                {
                                                    "label": "事件时间",
                                                    "value": root.eventTimeValue,
                                                    "tone": "neutral"
                                                },
                                                {
                                                    "label": "在线锚点",
                                                    "value": String(root.liveAnchor["board_status"] || "--"),
                                                    "tone": String(root.liveAnchor["tone"] || "neutral")
                                                },
                                                {
                                                    "label": "快照原因",
                                                    "value": root.snapshotReasonValue,
                                                    "tone": "warning"
                                                }
                                            ]

                                            delegate: Rectangle {
                                                property var itemData: modelData
                                                Layout.fillWidth: true
                                                radius: root.edgeRadius
                                                color: root.toneFill(String(itemData["tone"] || "neutral"))
                                                border.color: root.toneColor(String(itemData["tone"] || "neutral"))
                                                border.width: 1
                                                implicitHeight: summaryStat.implicitHeight + (root.scaled(10) * 2)

                                                Column {
                                                    id: summaryStat
                                                    anchors.fill: parent
                                                    anchors.margins: root.scaled(10)
                                                    spacing: root.scaled(2)

                                                    Text {
                                                        text: itemData["label"]
                                                        color: root.textMuted
                                                        font.pixelSize: root.captionSize
                                                        font.family: root.monoFamily
                                                    }

                                                    Text {
                                                        width: parent.width
                                                        text: itemData["value"]
                                                        color: root.textStrong
                                                        font.pixelSize: root.captionSize
                                                        font.bold: true
                                                        font.family: root.uiFamily
                                                        wrapMode: Text.WrapAnywhere
                                                    }
                                                }
                                            }
                                        }
                                    }

                                    Text {
                                        Layout.fillWidth: true
                                        text: "快照路径: " + root.snapshotRelativePath
                                        color: root.textMuted
                                        font.pixelSize: root.captionSize
                                        font.family: root.monoFamily
                                        wrapMode: Text.WrapAnywhere
                                    }

                                    Rectangle {
                                        Layout.fillWidth: true
                                        Layout.preferredHeight: 1
                                        color: "#28384d"
                                    }

                                    Text {
                                        text: "跳转二级页面 / Secondary Surfaces"
                                        color: root.accentBlue
                                        font.pixelSize: root.eyebrowSize
                                        font.family: root.monoFamily
                                        font.letterSpacing: root.scaled(1)
                                    }

                                    Text {
                                        Layout.fillWidth: true
                                        text: "把系统板态、飞行合同、弱网策略和执行坞站全部拆成独立页面，总览页只保留地图主墙板和必要摘要。"
                                        color: root.textSecondary
                                        font.pixelSize: root.bodySize
                                        font.family: root.uiFamily
                                        wrapMode: Text.WordWrap
                                    }

                                    GridLayout {
                                        Layout.fillWidth: true
                                        columns: root.wideLayout ? 1 : 2
                                        columnSpacing: root.compactGap
                                        rowSpacing: root.compactGap

                                        Repeater {
                                            model: root.landingJumpModel

                                            delegate: Rectangle {
                                                property var itemData: modelData
                                                Layout.fillWidth: true
                                                radius: root.edgeRadius
                                                color: "#0d1623"
                                                border.color: root.toneColor(String(itemData["tone"] || "neutral"))
                                                border.width: 1
                                                implicitHeight: jumpCardColumn.implicitHeight + (root.scaled(10) * 2)

                                                Column {
                                                    id: jumpCardColumn
                                                    anchors.fill: parent
                                                    anchors.margins: root.scaled(10)
                                                    spacing: root.scaled(2)

                                                    Row {
                                                        width: parent.width
                                                        spacing: root.scaled(6)

                                                        Text {
                                                            text: itemData["label"]
                                                            color: root.textStrong
                                                            font.pixelSize: root.bodySize
                                                            font.bold: true
                                                            font.family: root.uiFamily
                                                        }

                                                        Text {
                                                            text: itemData["english"]
                                                            color: root.textMuted
                                                            font.pixelSize: root.captionSize
                                                            font.family: root.monoFamily
                                                        }
                                                    }

                                                    Text {
                                                        width: parent.width
                                                        text: itemData["summary"]
                                                        visible: !root.compactLayout
                                                        color: root.textSecondary
                                                        font.pixelSize: root.captionSize
                                                        font.family: root.uiFamily
                                                        wrapMode: Text.WordWrap
                                                    }

                                                    Text {
                                                        width: parent.width
                                                        text: itemData["value"] + "  ·  进入 >"
                                                        color: root.toneColor(String(itemData["tone"] || "neutral"))
                                                        font.pixelSize: root.captionSize
                                                        font.bold: true
                                                        font.family: root.monoFamily
                                                        wrapMode: Text.WrapAnywhere
                                                    }
                                                }

                                                MouseArea {
                                                    anchors.fill: parent
                                                    hoverEnabled: true
                                                    cursorShape: Qt.PointingHandCursor
                                                    onClicked: root.currentPage = Number(parent.itemData["index"])
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }

                ScrollView {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    clip: true
                    ScrollBar.horizontal.policy: ScrollBar.AlwaysOff

                    Item {
                        width: parent.width
                        implicitHeight: systemPageContent.implicitHeight

                        ColumnLayout {
                            id: systemPageContent
                            width: parent.width
                            spacing: root.zoneGap

                            PanelFrame {
                                shellWindow: root
                                panelColor: root.panelColorSoft
                                borderTone: root.borderSoft
                                accentTone: root.accentBlue
                                Layout.fillWidth: true
                                implicitHeight: systemHeaderRow.implicitHeight + (root.panelPadding * 2)

                                RowLayout {
                                    id: systemHeaderRow
                                    anchors.fill: parent
                                    anchors.margins: root.panelPadding
                                    spacing: root.zoneGap

                                    Rectangle {
                                        radius: root.edgeRadius
                                        color: "#0d1623"
                                        border.color: root.accentBlue
                                        border.width: 1
                                        implicitWidth: systemBackRow.implicitWidth + (root.scaled(14) * 2)
                                        implicitHeight: systemBackRow.implicitHeight + (root.scaled(10) * 2)

                                        Row {
                                            id: systemBackRow
                                            anchors.centerIn: parent
                                            spacing: root.scaled(6)

                                            Text {
                                                text: "<"
                                                color: root.accentBlue
                                                font.pixelSize: root.bodySize
                                                font.bold: true
                                                font.family: root.monoFamily
                                            }

                                            Text {
                                                text: "返回总览"
                                                color: root.textStrong
                                                font.pixelSize: root.bodySize
                                                font.bold: true
                                                font.family: root.uiFamily
                                            }
                                        }

                                        MouseArea {
                                            anchors.fill: parent
                                            hoverEnabled: true
                                            cursorShape: Qt.PointingHandCursor
                                            onClicked: root.currentPage = 0
                                        }
                                    }

                                    ColumnLayout {
                                        Layout.fillWidth: true
                                        spacing: root.scaled(2)

                                        Text {
                                            text: "系统板态 / System Evidence"
                                            color: root.textStrong
                                            font.pixelSize: root.sectionTitleSize
                                            font.bold: true
                                            font.family: root.displayFamily
                                        }

                                        Text {
                                            Layout.fillWidth: true
                                            text: "集中查看会话、心跳、快照原因和模式边界说明。这个页面保留高密度证据视图，总览页不再同时展开。"
                                            color: root.textSecondary
                                            font.pixelSize: root.bodySize
                                            font.family: root.uiFamily
                                            wrapMode: Text.WordWrap
                                        }
                                    }
                                }
                            }

                            GridLayout {
                                Layout.fillWidth: true
                                columns: root.wideLayout ? 12 : 1
                                columnSpacing: root.zoneGap
                                rowSpacing: root.zoneGap

                                StatusPanel {
                                    shellWindow: root
                                    panelData: root.leftPanelData
                                    Layout.fillWidth: true
                                    Layout.columnSpan: root.wideLayout ? 8 : 1
                                }

                                ColumnLayout {
                                    Layout.fillWidth: true
                                    Layout.columnSpan: root.wideLayout ? 4 : 1
                                    spacing: root.zoneGap

                                    PanelFrame {
                                        shellWindow: root
                                        panelColor: root.panelColor
                                        borderTone: root.borderSoft
                                        accentTone: root.accentAmber
                                        Layout.fillWidth: true
                                        implicitHeight: systemNoteColumn.implicitHeight + (root.panelPadding * 2)

                                        ColumnLayout {
                                            id: systemNoteColumn
                                            anchors.fill: parent
                                            anchors.margins: root.panelPadding
                                            spacing: root.compactGap

                                            Text {
                                                text: "模式边界 / Truth Note"
                                                color: root.accentAmber
                                                font.pixelSize: root.eyebrowSize
                                                font.family: root.monoFamily
                                            }

                                            Text {
                                                text: "把真值说明和快照来源放到单独页面，避免首屏信息竞争。"
                                                color: root.textStrong
                                                font.pixelSize: root.bodyEmphasisSize
                                                font.bold: true
                                                font.family: root.uiFamily
                                                wrapMode: Text.WordWrap
                                            }

                                            Text {
                                                Layout.fillWidth: true
                                                text: root.truthNoteValue
                                                color: root.textSecondary
                                                font.pixelSize: root.bodySize
                                                font.family: root.uiFamily
                                                wrapMode: Text.WordWrap
                                            }

                                            Text {
                                                Layout.fillWidth: true
                                                text: "快照路径: " + root.snapshotRelativePath
                                                color: root.textMuted
                                                font.pixelSize: root.captionSize
                                                font.family: root.monoFamily
                                                wrapMode: Text.WrapAnywhere
                                            }
                                        }
                                    }

                                    PanelFrame {
                                        shellWindow: root
                                        panelColor: root.panelColor
                                        borderTone: root.borderSoft
                                        accentTone: root.accentBlue
                                        Layout.fillWidth: true
                                        implicitHeight: systemQuickGrid.implicitHeight + (root.panelPadding * 2)

                                        GridLayout {
                                            id: systemQuickGrid
                                            anchors.fill: parent
                                            anchors.margins: root.panelPadding
                                            columns: 2
                                            columnSpacing: root.compactGap
                                            rowSpacing: root.compactGap

                                            Repeater {
                                                model: [
                                                    {
                                                        "label": "会话",
                                                        "value": root.systemSessionValue,
                                                        "tone": "neutral"
                                                    },
                                                    {
                                                        "label": "心跳",
                                                        "value": root.heartbeatValue,
                                                        "tone": root.heartbeatTone
                                                    },
                                                    {
                                                        "label": "最近事件",
                                                        "value": root.recentEventValue,
                                                        "tone": root.recentEventTone
                                                    },
                                                    {
                                                        "label": "快照原因",
                                                        "value": root.snapshotReasonValue,
                                                        "tone": "warning"
                                                    }
                                                ]

                                                delegate: Rectangle {
                                                    property var itemData: modelData
                                                    Layout.fillWidth: true
                                                    radius: root.edgeRadius
                                                    color: root.toneFill(String(itemData["tone"] || "neutral"))
                                                    border.color: root.toneColor(String(itemData["tone"] || "neutral"))
                                                    border.width: 1
                                                    implicitHeight: systemQuickColumn.implicitHeight + (root.scaled(10) * 2)

                                                    Column {
                                                        id: systemQuickColumn
                                                        anchors.fill: parent
                                                        anchors.margins: root.scaled(10)
                                                        spacing: root.scaled(2)

                                                        Text {
                                                            text: itemData["label"]
                                                            color: root.textMuted
                                                            font.pixelSize: root.captionSize
                                                            font.family: root.monoFamily
                                                        }

                                                        Text {
                                                            width: parent.width
                                                            text: itemData["value"]
                                                            color: root.textStrong
                                                            font.pixelSize: root.captionSize
                                                            font.bold: true
                                                            font.family: root.uiFamily
                                                            wrapMode: Text.WrapAnywhere
                                                        }
                                                    }
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }

                ScrollView {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    clip: true
                    ScrollBar.horizontal.policy: ScrollBar.AlwaysOff

                    Item {
                        width: parent.width
                        implicitHeight: flightPageContent.implicitHeight

                        ColumnLayout {
                            id: flightPageContent
                            width: parent.width
                            spacing: root.zoneGap

                            PanelFrame {
                                shellWindow: root
                                panelColor: root.panelColorSoft
                                borderTone: root.borderSoft
                                accentTone: root.accentBlue
                                Layout.fillWidth: true
                                implicitHeight: flightHeaderRow.implicitHeight + (root.panelPadding * 2)

                                RowLayout {
                                    id: flightHeaderRow
                                    anchors.fill: parent
                                    anchors.margins: root.panelPadding
                                    spacing: root.zoneGap

                                    Rectangle {
                                        radius: root.edgeRadius
                                        color: "#0d1623"
                                        border.color: root.accentBlue
                                        border.width: 1
                                        implicitWidth: flightBackRow.implicitWidth + (root.scaled(14) * 2)
                                        implicitHeight: flightBackRow.implicitHeight + (root.scaled(10) * 2)

                                        Row {
                                            id: flightBackRow
                                            anchors.centerIn: parent
                                            spacing: root.scaled(6)

                                            Text {
                                                text: "<"
                                                color: root.accentBlue
                                                font.pixelSize: root.bodySize
                                                font.bold: true
                                                font.family: root.monoFamily
                                            }

                                            Text {
                                                text: "返回总览"
                                                color: root.textStrong
                                                font.pixelSize: root.bodySize
                                                font.bold: true
                                                font.family: root.uiFamily
                                            }
                                        }

                                        MouseArea {
                                            anchors.fill: parent
                                            hoverEnabled: true
                                            cursorShape: Qt.PointingHandCursor
                                            onClicked: root.currentPage = 0
                                        }
                                    }

                                    ColumnLayout {
                                        Layout.fillWidth: true
                                        spacing: root.scaled(2)

                                        Text {
                                            text: "飞行合同 / Flight Contract"
                                            color: root.textStrong
                                            font.pixelSize: root.sectionTitleSize
                                            font.bold: true
                                            font.family: root.displayFamily
                                        }

                                        Text {
                                            Layout.fillWidth: true
                                            text: "集中查看世界地图、航迹、遥测指标和数据合同说明，让中心地图真正承担主舞台。"
                                            color: root.textSecondary
                                            font.pixelSize: root.bodySize
                                            font.family: root.uiFamily
                                            wrapMode: Text.WordWrap
                                        }
                                    }
                                }
                            }

                            GridLayout {
                                Layout.fillWidth: true
                                columns: root.wideLayout ? 12 : 1
                                columnSpacing: root.zoneGap
                                rowSpacing: root.zoneGap

                                PanelFrame {
                                    shellWindow: root
                                    panelColor: root.cardColor
                                    borderTone: root.borderStrong
                                    accentTone: root.accentBlue
                                    Layout.fillWidth: true
                                    Layout.columnSpan: root.wideLayout ? 7 : 1
                                    Layout.minimumHeight: root.scaled(root.shortViewport ? 360 : 430)
                                    Layout.preferredHeight: root.scaled(root.wideLayout ? 520 : 460)

                                    Item {
                                        anchors.fill: parent
                                        anchors.margins: root.scaled(14)

                                        WorldMapStage {
                                            anchors.fill: parent
                                            shellWindow: root
                                            trackData: root.trackData
                                            currentPoint: root.currentPosition
                                            headingDeg: Number(root.kinematics["heading_deg"] || 0)
                                            currentLabel: String(root.centerPanelData["mission_call_sign"] || "M9-DEMO") + " 飞行合同"
                                            currentDetail: root.activeSourceLabel + " / " + root.linkProfileValue
                                            anchorLabel: String(root.liveAnchor["valid_instance"] || "--")
                                            projectionLabel: "世界地图合同 / Equirectangular"
                                            scenarioLabel: root.recommendedScenarioId
                                            scenarioTone: String(root.liveAnchor["tone"] || "neutral")
                                        }
                                    }
                                }

                                ColumnLayout {
                                    Layout.fillWidth: true
                                    Layout.columnSpan: root.wideLayout ? 5 : 1
                                    spacing: root.zoneGap

                                    PanelFrame {
                                        shellWindow: root
                                        panelColor: root.panelColor
                                        borderTone: root.borderSoft
                                        accentTone: root.accentBlue
                                        Layout.fillWidth: true
                                        implicitHeight: flightMetricGrid.implicitHeight + (root.panelPadding * 2)

                                        GridLayout {
                                            id: flightMetricGrid
                                            anchors.fill: parent
                                            anchors.margins: root.panelPadding
                                            columns: 2
                                            columnSpacing: root.compactGap
                                            rowSpacing: root.compactGap

                                            Repeater {
                                                model: [
                                                    {
                                                        "label": "任务代号",
                                                        "value": String(root.centerPanelData["mission_call_sign"] || "--"),
                                                        "tone": "neutral"
                                                    },
                                                    {
                                                        "label": "飞机编号",
                                                        "value": String(root.centerPanelData["aircraft_id"] || "--"),
                                                        "tone": "neutral"
                                                    },
                                                    {
                                                        "label": "当前坐标",
                                                        "value": root.coordinatePair(root.currentPosition),
                                                        "tone": "online"
                                                    },
                                                    {
                                                        "label": "飞行高度",
                                                        "value": root.formattedMetric(root.kinematics["altitude_m"], 0, "m"),
                                                        "tone": "online"
                                                    },
                                                    {
                                                        "label": "地速",
                                                        "value": root.formattedMetric(root.kinematics["ground_speed_kph"], 0, "km/h"),
                                                        "tone": "neutral"
                                                    },
                                                    {
                                                        "label": "航向",
                                                        "value": root.formattedMetric(root.kinematics["heading_deg"], 0, "°"),
                                                        "tone": "neutral"
                                                    }
                                                ]

                                                delegate: Rectangle {
                                                    property var itemData: modelData
                                                    Layout.fillWidth: true
                                                    radius: root.edgeRadius
                                                    color: root.toneFill(String(itemData["tone"] || "neutral"))
                                                    border.color: root.toneColor(String(itemData["tone"] || "neutral"))
                                                    border.width: 1
                                                    implicitHeight: flightMetricColumn.implicitHeight + (root.scaled(10) * 2)

                                                    Column {
                                                        id: flightMetricColumn
                                                        anchors.fill: parent
                                                        anchors.margins: root.scaled(10)
                                                        spacing: root.scaled(2)

                                                        Text {
                                                            text: itemData["label"]
                                                            color: root.textMuted
                                                            font.pixelSize: root.captionSize
                                                            font.family: root.monoFamily
                                                        }

                                                        Text {
                                                            width: parent.width
                                                            text: itemData["value"]
                                                            color: root.textStrong
                                                            font.pixelSize: root.captionSize
                                                            font.bold: true
                                                            font.family: root.uiFamily
                                                            wrapMode: Text.WrapAnywhere
                                                        }
                                                    }
                                                }
                                            }
                                        }
                                    }

                                    PanelFrame {
                                        shellWindow: root
                                        panelColor: root.panelColor
                                        borderTone: root.borderSoft
                                        accentTone: root.accentAmber
                                        Layout.fillWidth: true
                                        implicitHeight: flightContractColumn.implicitHeight + (root.panelPadding * 2)

                                        ColumnLayout {
                                            id: flightContractColumn
                                            anchors.fill: parent
                                            anchors.margins: root.panelPadding
                                            spacing: root.compactGap

                                            Text {
                                                text: "数据合同 / Contract Detail"
                                                color: root.accentAmber
                                                font.pixelSize: root.eyebrowSize
                                                font.family: root.monoFamily
                                            }

                                            Text {
                                                Layout.fillWidth: true
                                                text: String(root.centerFeedContract["summary"] || root.centerPanelData["fallback_note"] || "--")
                                                color: root.textStrong
                                                font.pixelSize: root.bodyEmphasisSize
                                                font.bold: true
                                                font.family: root.uiFamily
                                                wrapMode: Text.WordWrap
                                            }

                                            Text {
                                                Layout.fillWidth: true
                                                text: "API: " + String(root.centerFeedContract["api_path"] || root.centerPanelData["source_api_path"] || "--")
                                                color: root.textSecondary
                                                font.pixelSize: root.bodySize
                                                font.family: root.monoFamily
                                                wrapMode: Text.WrapAnywhere
                                            }

                                            Text {
                                                Layout.fillWidth: true
                                                text: "采样时间: " + String(root.centerSampleData["captured_at"] || "--")
                                                color: root.textSecondary
                                                font.pixelSize: root.bodySize
                                                font.family: root.uiFamily
                                                wrapMode: Text.WordWrap
                                            }

                                            Text {
                                                Layout.fillWidth: true
                                                text: String(root.centerPanelData["ownership_note"] || "")
                                                color: root.textMuted
                                                font.pixelSize: root.bodySize
                                                font.family: root.uiFamily
                                                wrapMode: Text.WordWrap
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }

                ScrollView {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    clip: true
                    ScrollBar.horizontal.policy: ScrollBar.AlwaysOff

                    Item {
                        width: parent.width
                        implicitHeight: weakPageContent.implicitHeight

                        ColumnLayout {
                            id: weakPageContent
                            width: parent.width
                            spacing: root.zoneGap

                            PanelFrame {
                                shellWindow: root
                                panelColor: root.panelColorSoft
                                borderTone: root.borderSoft
                                accentTone: root.accentAmber
                                Layout.fillWidth: true
                                implicitHeight: weakHeaderRow.implicitHeight + (root.panelPadding * 2)

                                RowLayout {
                                    id: weakHeaderRow
                                    anchors.fill: parent
                                    anchors.margins: root.panelPadding
                                    spacing: root.zoneGap

                                    Rectangle {
                                        radius: root.edgeRadius
                                        color: "#0d1623"
                                        border.color: root.accentAmber
                                        border.width: 1
                                        implicitWidth: weakBackRow.implicitWidth + (root.scaled(14) * 2)
                                        implicitHeight: weakBackRow.implicitHeight + (root.scaled(10) * 2)

                                        Row {
                                            id: weakBackRow
                                            anchors.centerIn: parent
                                            spacing: root.scaled(6)

                                            Text {
                                                text: "<"
                                                color: root.accentAmber
                                                font.pixelSize: root.bodySize
                                                font.bold: true
                                                font.family: root.monoFamily
                                            }

                                            Text {
                                                text: "返回总览"
                                                color: root.textStrong
                                                font.pixelSize: root.bodySize
                                                font.bold: true
                                                font.family: root.uiFamily
                                            }
                                        }

                                        MouseArea {
                                            anchors.fill: parent
                                            hoverEnabled: true
                                            cursorShape: Qt.PointingHandCursor
                                            onClicked: root.currentPage = 0
                                        }
                                    }

                                    ColumnLayout {
                                        Layout.fillWidth: true
                                        spacing: root.scaled(2)

                                        Text {
                                            text: "弱网策略 / Weak-Link Strategy"
                                            color: root.textStrong
                                            font.pixelSize: root.sectionTitleSize
                                            font.bold: true
                                            font.family: root.displayFamily
                                        }

                                        Text {
                                            Layout.fillWidth: true
                                            text: "这个页面专门承载推荐弱网档、在线锚点和吞吐证据，不再挤在首屏右侧。"
                                            color: root.textSecondary
                                            font.pixelSize: root.bodySize
                                            font.family: root.uiFamily
                                            wrapMode: Text.WordWrap
                                        }
                                    }
                                }
                            }

                            GridLayout {
                                Layout.fillWidth: true
                                columns: root.wideLayout ? 12 : 1
                                columnSpacing: root.zoneGap
                                rowSpacing: root.zoneGap

                                WeakNetworkPanel {
                                    shellWindow: root
                                    panelData: root.rightPanelData
                                    Layout.fillWidth: true
                                    Layout.columnSpan: root.wideLayout ? 8 : 1
                                }

                                ColumnLayout {
                                    Layout.fillWidth: true
                                    Layout.columnSpan: root.wideLayout ? 4 : 1
                                    spacing: root.zoneGap

                                    PanelFrame {
                                        shellWindow: root
                                        panelColor: root.panelColor
                                        borderTone: root.borderSoft
                                        accentTone: root.accentBlue
                                        Layout.fillWidth: true
                                        implicitHeight: anchorColumn.implicitHeight + (root.panelPadding * 2)

                                        ColumnLayout {
                                            id: anchorColumn
                                            anchors.fill: parent
                                            anchors.margins: root.panelPadding
                                            spacing: root.compactGap

                                            Text {
                                                text: "在线锚点 / Live Anchor"
                                                color: root.accentBlue
                                                font.pixelSize: root.eyebrowSize
                                                font.family: root.monoFamily
                                            }

                                            Text {
                                                Layout.fillWidth: true
                                                text: String(root.liveAnchor["board_status"] || "--")
                                                color: root.textStrong
                                                font.pixelSize: root.bodyEmphasisSize
                                                font.bold: true
                                                font.family: root.uiFamily
                                                wrapMode: Text.WordWrap
                                            }

                                            Text {
                                                Layout.fillWidth: true
                                                text: String(root.liveAnchor["probe_summary"] || "--")
                                                color: root.textSecondary
                                                font.pixelSize: root.bodySize
                                                font.family: root.uiFamily
                                                wrapMode: Text.WordWrap
                                            }

                                            Repeater {
                                                model: DataUtils.arrayOrEmpty(root.liveAnchor["links"])

                                                delegate: Rectangle {
                                                    property var itemData: modelData
                                                    Layout.fillWidth: true
                                                    radius: root.edgeRadius
                                                    color: "#0d1623"
                                                    border.color: "#30445c"
                                                    border.width: 1
                                                    implicitHeight: anchorLinkColumn.implicitHeight + (root.scaled(10) * 2)

                                                    Column {
                                                        id: anchorLinkColumn
                                                        anchors.fill: parent
                                                        anchors.margins: root.scaled(10)
                                                        spacing: root.scaled(2)

                                                        Text {
                                                            width: parent.width
                                                            text: itemData["label"]
                                                            color: root.textStrong
                                                            font.pixelSize: root.captionSize
                                                            font.bold: true
                                                            font.family: root.uiFamily
                                                            wrapMode: Text.WordWrap
                                                        }

                                                        Text {
                                                            width: parent.width
                                                            text: itemData["path"]
                                                            color: root.textMuted
                                                            font.pixelSize: root.captionSize
                                                            font.family: root.monoFamily
                                                            wrapMode: Text.WrapAnywhere
                                                        }
                                                    }
                                                }
                                            }
                                        }
                                    }

                                    PanelFrame {
                                        shellWindow: root
                                        panelColor: root.panelColor
                                        borderTone: root.borderSoft
                                        accentTone: root.accentAmber
                                        Layout.fillWidth: true
                                        implicitHeight: weakScenarioColumn.implicitHeight + (root.panelPadding * 2)

                                        ColumnLayout {
                                            id: weakScenarioColumn
                                            anchors.fill: parent
                                            anchors.margins: root.panelPadding
                                            spacing: root.compactGap

                                            Text {
                                                text: "推荐档 / Recommended Scenario"
                                                color: root.accentAmber
                                                font.pixelSize: root.eyebrowSize
                                                font.family: root.monoFamily
                                            }

                                            Text {
                                                text: String(root.recommendedScenario["label"] || root.recommendedScenarioId)
                                                color: root.textStrong
                                                font.pixelSize: root.bodyEmphasisSize
                                                font.bold: true
                                                font.family: root.uiFamily
                                                wrapMode: Text.WordWrap
                                            }

                                            Text {
                                                Layout.fillWidth: true
                                                text: String(root.recommendedScenario["summary"] || "--")
                                                color: root.textSecondary
                                                font.pixelSize: root.bodySize
                                                font.family: root.uiFamily
                                                wrapMode: Text.WordWrap
                                            }

                                            GridLayout {
                                                Layout.fillWidth: true
                                                columns: 2
                                                columnSpacing: root.compactGap
                                                rowSpacing: root.compactGap

                                                Repeater {
                                                    model: [
                                                        {
                                                            "label": "Pipeline",
                                                            "value": root.formattedMetric(root.recommendedComparison["pipeline_images_per_sec"], 3, "img/s"),
                                                            "tone": "online"
                                                        },
                                                        {
                                                            "label": "提升",
                                                            "value": root.formattedMetric(root.recommendedComparison["throughput_uplift_pct"], 3, "%"),
                                                            "tone": "warning"
                                                        },
                                                        {
                                                            "label": "批次节省",
                                                            "value": root.formattedMetric(root.recommendedComparison["saved_seconds_per_batch"], 3, "s"),
                                                            "tone": "warning"
                                                        },
                                                        {
                                                            "label": "推荐档",
                                                            "value": root.recommendedScenarioId,
                                                            "tone": "neutral"
                                                        }
                                                    ]

                                                    delegate: Rectangle {
                                                        property var itemData: modelData
                                                        Layout.fillWidth: true
                                                        radius: root.edgeRadius
                                                        color: root.toneFill(String(itemData["tone"] || "neutral"))
                                                        border.color: root.toneColor(String(itemData["tone"] || "neutral"))
                                                        border.width: 1
                                                        implicitHeight: weakStatColumn.implicitHeight + (root.scaled(10) * 2)

                                                        Column {
                                                            id: weakStatColumn
                                                            anchors.fill: parent
                                                            anchors.margins: root.scaled(10)
                                                            spacing: root.scaled(2)

                                                            Text {
                                                                text: itemData["label"]
                                                                color: root.textMuted
                                                                font.pixelSize: root.captionSize
                                                                font.family: root.monoFamily
                                                            }

                                                            Text {
                                                                width: parent.width
                                                                text: itemData["value"]
                                                                color: root.textStrong
                                                                font.pixelSize: root.captionSize
                                                                font.bold: true
                                                                font.family: root.uiFamily
                                                                wrapMode: Text.WrapAnywhere
                                                            }
                                                        }
                                                    }
                                                }
                                            }

                                            Text {
                                                Layout.fillWidth: true
                                                text: "Pipeline 命令: " + String(root.recommendedCommands["pipeline"] || "--")
                                                color: root.textMuted
                                                font.pixelSize: root.captionSize
                                                font.family: root.monoFamily
                                                wrapMode: Text.WrapAnywhere
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }

                ScrollView {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    clip: true
                    ScrollBar.horizontal.policy: ScrollBar.AlwaysOff

                    Item {
                        width: parent.width
                        implicitHeight: actionPageContent.implicitHeight

                        ColumnLayout {
                            id: actionPageContent
                            width: parent.width
                            spacing: root.zoneGap

                            PanelFrame {
                                shellWindow: root
                                panelColor: root.panelColorSoft
                                borderTone: root.borderSoft
                                accentTone: root.accentGreen
                                Layout.fillWidth: true
                                implicitHeight: actionHeaderRow.implicitHeight + (root.panelPadding * 2)

                                RowLayout {
                                    id: actionHeaderRow
                                    anchors.fill: parent
                                    anchors.margins: root.panelPadding
                                    spacing: root.zoneGap

                                    Rectangle {
                                        radius: root.edgeRadius
                                        color: "#0d1623"
                                        border.color: root.accentGreen
                                        border.width: 1
                                        implicitWidth: actionBackRow.implicitWidth + (root.scaled(14) * 2)
                                        implicitHeight: actionBackRow.implicitHeight + (root.scaled(10) * 2)

                                        Row {
                                            id: actionBackRow
                                            anchors.centerIn: parent
                                            spacing: root.scaled(6)

                                            Text {
                                                text: "<"
                                                color: root.accentGreen
                                                font.pixelSize: root.bodySize
                                                font.bold: true
                                                font.family: root.monoFamily
                                            }

                                            Text {
                                                text: "返回总览"
                                                color: root.textStrong
                                                font.pixelSize: root.bodySize
                                                font.bold: true
                                                font.family: root.uiFamily
                                            }
                                        }

                                        MouseArea {
                                            anchors.fill: parent
                                            hoverEnabled: true
                                            cursorShape: Qt.PointingHandCursor
                                            onClicked: root.currentPage = 0
                                        }
                                    }

                                    ColumnLayout {
                                        Layout.fillWidth: true
                                        spacing: root.scaled(2)

                                        Text {
                                            text: "执行坞站 / Action Dock"
                                            color: root.textStrong
                                            font.pixelSize: root.sectionTitleSize
                                            font.bold: true
                                            font.family: root.displayFamily
                                        }

                                        Text {
                                            Layout.fillWidth: true
                                            text: "把合同动作、软件渲染安全路径和启动命令集中在这个页面，首屏只保留跳转入口。"
                                            color: root.textSecondary
                                            font.pixelSize: root.bodySize
                                            font.family: root.uiFamily
                                            wrapMode: Text.WordWrap
                                        }
                                    }
                                }
                            }

                            GridLayout {
                                Layout.fillWidth: true
                                columns: root.wideLayout ? 12 : 1
                                columnSpacing: root.zoneGap
                                rowSpacing: root.zoneGap

                                ActionStrip {
                                    shellWindow: root
                                    panelData: root.bottomPanelData
                                    Layout.fillWidth: true
                                    Layout.columnSpan: root.wideLayout ? 8 : 1
                                }

                                ColumnLayout {
                                    Layout.fillWidth: true
                                    Layout.columnSpan: root.wideLayout ? 4 : 1
                                    spacing: root.zoneGap

                                    PanelFrame {
                                        shellWindow: root
                                        panelColor: root.panelColor
                                        borderTone: root.borderSoft
                                        accentTone: root.accentGreen
                                        Layout.fillWidth: true
                                        implicitHeight: actionLaunchColumn.implicitHeight + (root.panelPadding * 2)

                                        ColumnLayout {
                                            id: actionLaunchColumn
                                            anchors.fill: parent
                                            anchors.margins: root.panelPadding
                                            spacing: root.compactGap

                                            Text {
                                                text: "启动与渲染 / Launch Path"
                                                color: root.accentGreen
                                                font.pixelSize: root.eyebrowSize
                                                font.family: root.monoFamily
                                            }

                                            Text {
                                                Layout.fillWidth: true
                                                text: softwareRenderEnabled ? "当前窗口已走软件安全渲染路径。" : "当前窗口处于 GPU 优先模式。"
                                                color: root.textStrong
                                                font.pixelSize: root.bodyEmphasisSize
                                                font.bold: true
                                                font.family: root.uiFamily
                                                wrapMode: Text.WordWrap
                                            }

                                            Text {
                                                Layout.fillWidth: true
                                                text: "启动命令: " + root.launchHint
                                                color: root.textSecondary
                                                font.pixelSize: root.bodySize
                                                font.family: root.monoFamily
                                                wrapMode: Text.WrapAnywhere
                                            }

                                            Text {
                                                Layout.fillWidth: true
                                                text: "离屏截图: bash ./session_bootstrap/scripts/run_cockpit_native_capture.sh"
                                                color: root.textSecondary
                                                font.pixelSize: root.bodySize
                                                font.family: root.monoFamily
                                                wrapMode: Text.WrapAnywhere
                                            }

                                            Text {
                                                Layout.fillWidth: true
                                                text: String(root.bottomPanelData["footer_note"] || "")
                                                color: root.textMuted
                                                font.pixelSize: root.bodySize
                                                font.family: root.uiFamily
                                                wrapMode: Text.WordWrap
                                            }
                                        }
                                    }

                                    PanelFrame {
                                        shellWindow: root
                                        panelColor: root.panelColor
                                        borderTone: root.borderSoft
                                        accentTone: root.accentAmber
                                        Layout.fillWidth: true
                                        implicitHeight: actionStateGrid.implicitHeight + (root.panelPadding * 2)

                                        GridLayout {
                                            id: actionStateGrid
                                            anchors.fill: parent
                                            anchors.margins: root.panelPadding
                                            columns: 2
                                            columnSpacing: root.compactGap
                                            rowSpacing: root.compactGap

                                            Repeater {
                                                model: [
                                                    {
                                                        "label": "合同动作",
                                                        "value": String(root.bottomActions.length),
                                                        "tone": "neutral"
                                                    },
                                                    {
                                                        "label": "可执行",
                                                        "value": String(root.enabledBottomActions),
                                                        "tone": root.enabledBottomActions > 0 ? "online" : "warning"
                                                    },
                                                    {
                                                        "label": "只读",
                                                        "value": String(Math.max(0, root.bottomActions.length - root.enabledBottomActions)),
                                                        "tone": "warning"
                                                    },
                                                    {
                                                        "label": "推荐档",
                                                        "value": root.recommendedScenarioId,
                                                        "tone": "warning"
                                                    }
                                                ]

                                                delegate: Rectangle {
                                                    property var itemData: modelData
                                                    Layout.fillWidth: true
                                                    radius: root.edgeRadius
                                                    color: root.toneFill(String(itemData["tone"] || "neutral"))
                                                    border.color: root.toneColor(String(itemData["tone"] || "neutral"))
                                                    border.width: 1
                                                    implicitHeight: actionStateColumn.implicitHeight + (root.scaled(10) * 2)

                                                    Column {
                                                        id: actionStateColumn
                                                        anchors.fill: parent
                                                        anchors.margins: root.scaled(10)
                                                        spacing: root.scaled(2)

                                                        Text {
                                                            text: itemData["label"]
                                                            color: root.textMuted
                                                            font.pixelSize: root.captionSize
                                                            font.family: root.monoFamily
                                                        }

                                                        Text {
                                                            width: parent.width
                                                            text: itemData["value"]
                                                            color: root.textStrong
                                                            font.pixelSize: root.captionSize
                                                            font.bold: true
                                                            font.family: root.uiFamily
                                                            wrapMode: Text.WrapAnywhere
                                                        }
                                                    }
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
