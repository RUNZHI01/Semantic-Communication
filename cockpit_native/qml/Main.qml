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
    readonly property var trackData: DataUtils.arrayOrEmpty(centerPanelData["track"])
    readonly property var currentPosition: DataUtils.objectOrEmpty(centerPanelData["position"])
    readonly property var kinematics: DataUtils.objectOrEmpty(centerPanelData["kinematics"])
    readonly property var fix: DataUtils.objectOrEmpty(centerPanelData["fix"])
    readonly property var liveAnchor: DataUtils.objectOrEmpty(rightPanelData["live_anchor"])
    readonly property var rightScenarios: DataUtils.arrayOrEmpty(rightPanelData["scenarios"])
    readonly property var recommendedScenario: recommendedScenarioObject(rightScenarios)
    readonly property var recommendedComparison: DataUtils.objectOrEmpty(recommendedScenario["comparison"])
    readonly property string recommendedScenarioId: String(rightPanelData["recommended_scenario_id"] || "--")
    readonly property int enabledBottomActions: enabledActionTotal(bottomActions)
    readonly property bool softwareRenderEnabled: !!options["softwareRender"]

    readonly property int designWidth: 1440
    readonly property int designHeight: 900

    readonly property string displayFamily: "Noto Sans CJK SC"
    readonly property string uiFamily: "Noto Sans CJK SC"
    readonly property string monoFamily: "JetBrains Mono"

    readonly property color bgColorTop: "#070d16"
    readonly property color bgColorMid: "#0a111c"
    readonly property color bgColorBottom: "#05080f"
    readonly property color hazeBlue: "#14365c"
    readonly property color hazeAmber: "#65401c"
    readonly property color shellColor: "#0c131d"
    readonly property color shellCanopyTop: "#23374b"
    readonly property color shellCanopyMid: "#111b29"
    readonly property color shellCanopyBottom: "#081018"
    readonly property color shellCanopyEdge: "#3b566f"
    readonly property color panelColor: "#101928"
    readonly property color panelColorRaised: "#132032"
    readonly property color panelColorSoft: "#0b131e"
    readonly property color cardColor: "#141f30"
    readonly property color borderSoft: "#2c4058"
    readonly property color borderStrong: "#72b6ff"
    readonly property color accentBlue: "#72b6ff"
    readonly property color accentCyan: "#aeeaff"
    readonly property color accentGreen: "#75dbb0"
    readonly property color accentAmber: "#efb97d"
    readonly property color accentRed: "#ff8b94"
    readonly property color textStrong: "#f5f7fb"
    readonly property color textPrimary: "#dbe5f1"
    readonly property color textSecondary: "#97a8bc"
    readonly property color textMuted: "#718296"
    readonly property color gridLine: "#162230"
    readonly property color gridLineStrong: "#263648"
    readonly property color shellDockTop: "#1b2a3c"
    readonly property color shellDockMid: "#101a28"
    readonly property color shellDockBottom: "#081018"
    readonly property color panelGlowStrong: "#85c0ff"
    readonly property color panelTraceStrong: "#38516d"

    readonly property real widthScale: Math.max(0.72, Math.min(1.16, Number(metrics["width"] || designWidth) / designWidth))
    readonly property real heightScale: Math.max(0.72, Math.min(1.16, Number(metrics["height"] || designHeight) / designHeight))
    readonly property real uiScale: Math.min(widthScale, heightScale)

    readonly property int safeLeft: Number(insets["left"] || 0)
    readonly property int safeTop: Number(insets["top"] || 0)
    readonly property int safeRight: Number(insets["right"] || 0)
    readonly property int safeBottom: Number(insets["bottom"] || 0)

    readonly property int viewportHeight: height > 0 ? height : Number(metrics["height"] || designHeight)
    readonly property real viewportWidth: width > 0 ? width : Number(metrics["width"] || designWidth)
    readonly property real contentWidth: Math.max(1, viewportWidth - safeLeft - safeRight)
    readonly property bool wideLayout: viewportWidth >= 1320
    readonly property bool mediumLayout: !wideLayout && viewportWidth >= 980
    readonly property bool compactLayout: !wideLayout && !mediumLayout
    readonly property bool shortViewport: viewportHeight < 780

    readonly property int outerPadding: scaled(compactLayout ? 14 : 18)
    readonly property int shellPadding: scaled(compactLayout ? 16 : 22)
    readonly property int zoneGap: scaled(compactLayout ? 12 : 16)
    readonly property int compactGap: scaled(8)
    readonly property int panelPadding: scaled(compactLayout ? 14 : 18)
    readonly property int cardPadding: scaled(compactLayout ? 11 : 14)
    readonly property int panelRadius: scaled(22)
    readonly property int cardRadius: scaled(16)
    readonly property int edgeRadius: scaled(12)
    readonly property int headerTitleSize: scaled(compactLayout ? 28 : 34)
    readonly property int sectionTitleSize: scaled(compactLayout ? 22 : 26)
    readonly property int bodyEmphasisSize: scaled(compactLayout ? 14 : 15)
    readonly property int bodySize: scaled(13)
    readonly property int captionSize: scaled(10)
    readonly property int eyebrowSize: scaled(10)

    readonly property string topTitle: primaryLabel(meta["title"] || "飞腾原生座舱 / Feiteng Native Cockpit")
    readonly property string topSubtitle: String(meta["subtitle"] || "Qt/QML 原生命令壳体，直接读取仓库内 TVM/OpenAMP 演示合同与板端态势。")
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
    readonly property string aircraftIdValue: String(centerPanelData["aircraft_id"] || "FT-AIR-01")
    readonly property string missionCallSignValue: String(centerPanelData["mission_call_sign"] || "M9-DEMO")
    readonly property string liveAnchorTone: String(liveAnchor["tone"] || "neutral")
    readonly property string currentPageSummary: currentPage === 0
        ? "首屏将全球地图、链路状态与执行入口收口到同一张命令墙板，默认落在真实航迹与仓库合同证据上。"
        : String(DataUtils.objectOrEmpty(navigationModel[currentPage])["summary"] || "")
    readonly property string landingSummaryTitle: recentEventTone === "warning"
        ? "问题聚焦的全球态势墙板"
        : "地图优先的全球态势墙板"
    readonly property string landingSummaryText: String(centerControlSummary["last_event_message"] || rightPanelData["summary"] || topSubtitle)
    readonly property string landingStageTitle: "全球态势主屏"
    readonly property string landingMapBannerTitle: missionCallSignValue + " · " + aircraftIdValue
    readonly property string landingMapBannerText: coordinatePair(currentPosition) + " · "
        + formattedMetric(kinematics["ground_speed_kph"], 0, "km/h")
    readonly property string dockFooterSummary: compactMessage(footerNote, compactLayout ? 46 : 78)
    readonly property string dockLaunchLabel: compactMessage(launchHint, compactLayout ? 34 : 62)
    readonly property string footerNote: String(bottomPanelData["footer_note"] || "默认执行仓库内软件渲染安全启动路径。")

    property int currentPage: 0

    readonly property var navigationModel: [
        {
            "index": 0,
            "label": "总览",
            "english": "Landing",
            "detail": "地图主墙板",
            "summary": "全球地图、链路态势与执行入口。"
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

    readonly property var topStatusModel: [
        {
            "label": "会话",
            "value": systemSessionValue,
            "tone": "neutral"
        },
        {
            "label": "心跳",
            "value": heartbeatValue,
            "tone": heartbeatTone
        },
        {
            "label": "在线锚点",
            "value": String(liveAnchor["valid_instance"] || "--"),
            "tone": liveAnchorTone
        },
        {
            "label": "渲染",
            "value": softwareRenderEnabled ? "软件安全" : "图形优先",
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

    readonly property var landingWeakMetricModel: [
        {
            "label": "推荐档",
            "value": recommendedScenarioId,
            "detail": compactMessage(String(recommendedScenario["summary"] || "延续仓库现有弱网推荐剧本。"), compactLayout ? 24 : 44),
            "tone": "warning"
        },
        {
            "label": "吞吐",
            "value": formattedMetric(recommendedComparison["pipeline_images_per_sec"], 3, "img/s"),
            "detail": "pipeline 对照",
            "tone": "online"
        },
        {
            "label": "提升",
            "value": formattedMetric(recommendedComparison["throughput_uplift_pct"], 3, "%"),
            "detail": "弱网 uplift",
            "tone": "warning"
        },
        {
            "label": "锚点",
            "value": String(liveAnchor["valid_instance"] || "--"),
            "detail": String(liveAnchor["board_status"] || "等待在线锚点"),
            "tone": liveAnchorTone
        }
    ]
    readonly property var landingStageChipModel: [
        {
            "label": "数据源",
            "value": compactMessage(activeSourceLabel, compactLayout ? 16 : 22),
            "tone": "online"
        },
        {
            "label": "锚点",
            "value": String(liveAnchor["valid_instance"] || "--"),
            "tone": liveAnchorTone
        },
        {
            "label": "链路",
            "value": compactMessage(linkProfileValue, compactLayout ? 14 : 20),
            "tone": "neutral"
        }
    ]

    readonly property var systemPageChipModel: [
        { "label": "会话", "value": systemSessionValue, "tone": "neutral" },
        { "label": "心跳", "value": heartbeatValue, "tone": heartbeatTone },
        { "label": "最近事件", "value": recentEventValue, "tone": recentEventTone },
        { "label": "链路", "value": linkProfileValue, "tone": "neutral" }
    ]

    readonly property var flightPageChipModel: [
        { "label": "任务", "value": missionCallSignValue, "tone": "neutral" },
        { "label": "机号", "value": aircraftIdValue, "tone": "neutral" },
        { "label": "源", "value": activeSourceLabel, "tone": "online" },
        { "label": "航迹", "value": String(trackData.length) + " 节点", "tone": trackData.length > 1 ? "online" : "neutral" }
    ]

    readonly property var weakPageChipModel: [
        { "label": "推荐档", "value": recommendedScenarioId, "tone": "warning" },
        { "label": "吞吐", "value": formattedMetric(recommendedComparison["pipeline_images_per_sec"], 3, "img/s"), "tone": "online" },
        { "label": "提升", "value": formattedMetric(recommendedComparison["throughput_uplift_pct"], 3, "%"), "tone": "warning" },
        { "label": "锚点", "value": String(liveAnchor["valid_instance"] || "--"), "tone": liveAnchorTone }
    ]

    readonly property var actionPageChipModel: [
        { "label": "动作", "value": String(bottomActions.length), "tone": "neutral" },
        { "label": "可执行", "value": String(enabledBottomActions), "tone": enabledBottomActions > 0 ? "online" : "warning" },
        { "label": "桥接", "value": bridgeAvailable ? "仓库在线" : "桥接缺失", "tone": bridgeAvailable ? "online" : "warning" },
        { "label": "渲染", "value": softwareRenderEnabled ? "软件安全" : "图形优先", "tone": softwareRenderEnabled ? "warning" : "online" }
    ]

    readonly property var dockPreviewActions: previewActions(bottomActions)

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
        return "#111a27"
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

    function compactMessage(text, limit) {
        var resolved = String(text || "")
        var maxLength = Math.max(8, Number(limit || 40))
        if (resolved.length <= maxLength)
            return resolved
        return resolved.slice(0, maxLength - 1) + "…"
    }

    function previewActions(actionsModel) {
        var resolved = DataUtils.arrayOrEmpty(actionsModel)
        if (resolved.length <= 2)
            return resolved
        return resolved.slice(0, 2)
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
            GradientStop { position: 0.48; color: root.bgColorMid }
            GradientStop { position: 1.0; color: root.bgColorBottom }
        }
    }

    Rectangle {
        width: root.width * 0.72
        height: root.height * 0.7
        radius: width / 2
        color: root.hazeBlue
        opacity: 0.18
        x: -width * 0.22
        y: -height * 0.12
    }

    Rectangle {
        width: root.width * 0.44
        height: root.height * 0.42
        radius: width / 2
        color: root.hazeAmber
        opacity: 0.1
        x: root.width - (width * 0.78)
        y: root.height * 0.08
    }

    Item {
        id: backdropGrid
        anchors.fill: parent
        opacity: 0.14

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
        radius: root.panelRadius + root.scaled(8)
        color: root.shellColor
        border.color: root.shellCanopyEdge
        border.width: 1
        clip: true

        Rectangle {
            anchors.fill: parent
            radius: parent.radius
            gradient: Gradient {
                GradientStop { position: 0.0; color: root.shellCanopyTop }
                GradientStop { position: 0.18; color: root.shellCanopyMid }
                GradientStop { position: 0.42; color: root.shellColor }
                GradientStop { position: 1.0; color: root.shellCanopyBottom }
            }
        }

        Rectangle {
            anchors.left: parent.left
            anchors.top: parent.top
            width: parent.width * 0.26
            height: root.scaled(108)
            radius: root.edgeRadius
            rotation: -9
            color: "#081018"
            opacity: 0.92
            x: -width * 0.12
            y: -height * 0.38
        }

        Rectangle {
            anchors.right: parent.right
            anchors.top: parent.top
            width: parent.width * 0.26
            height: root.scaled(108)
            radius: root.edgeRadius
            rotation: 9
            color: "#081018"
            opacity: 0.92
            x: parent.width - (width * 0.88)
            y: -height * 0.38
        }

        Rectangle {
            anchors.top: parent.top
            anchors.horizontalCenter: parent.horizontalCenter
            width: Math.min(parent.width * 0.46, root.scaled(560))
            height: root.scaled(30)
            radius: height / 2
            gradient: Gradient {
                orientation: Gradient.Horizontal
                GradientStop { position: 0.0; color: "transparent" }
                GradientStop { position: 0.2; color: "#10ffffff" }
                GradientStop { position: 0.5; color: "#24ffffff" }
                GradientStop { position: 0.8; color: "#10ffffff" }
                GradientStop { position: 1.0; color: "transparent" }
            }
            opacity: 0.82
        }

        Rectangle {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            height: root.scaled(3)
            gradient: Gradient {
                orientation: Gradient.Horizontal
                GradientStop { position: 0.0; color: "transparent" }
                GradientStop { position: 0.2; color: root.accentBlue }
                GradientStop { position: 0.5; color: root.accentCyan }
                GradientStop { position: 0.8; color: root.accentBlue }
                GradientStop { position: 1.0; color: "transparent" }
            }
            opacity: 0.88
        }

        Rectangle {
            anchors.left: parent.left
            anchors.bottom: parent.bottom
            width: parent.width * 0.2
            height: parent.height * 0.56
            color: root.accentBlue
            opacity: 0.035
            radius: width / 2
            x: -width * 0.22
            y: parent.height - (height * 0.72)
        }

        Rectangle {
            anchors.right: parent.right
            anchors.bottom: parent.bottom
            width: parent.width * 0.2
            height: parent.height * 0.56
            color: root.accentCyan
            opacity: 0.03
            radius: width / 2
            x: parent.width - (width * 0.78)
            y: parent.height - (height * 0.72)
        }

        Rectangle {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.bottom: parent.bottom
            height: parent.height * 0.18
            radius: parent.radius
            gradient: Gradient {
                GradientStop { position: 0.0; color: "#00000000" }
                GradientStop { position: 0.42; color: "#16000000" }
                GradientStop { position: 1.0; color: "#42060d15" }
            }
        }

        Rectangle {
            anchors.fill: parent
            anchors.margins: 3
            radius: parent.radius - 3
            color: "transparent"
            border.color: "#385069"
            border.width: 1
            opacity: 0.88
        }

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: root.shellPadding
            spacing: root.zoneGap

            PanelFrame {
                shellWindow: root
                panelColor: root.panelColorSoft
                borderTone: root.borderStrong
                accentTone: root.accentBlue
                Layout.fillWidth: true
                implicitHeight: canopyLayout.implicitHeight + (root.panelPadding * 2)

                GridLayout {
                    id: canopyLayout
                    anchors.fill: parent
                    anchors.margins: root.panelPadding
                    columns: root.compactLayout ? 1 : 5
                    columnSpacing: root.zoneGap
                    rowSpacing: root.compactGap

                    Rectangle {
                        Layout.columnSpan: root.compactLayout ? 1 : 2
                        Layout.fillWidth: true
                        radius: root.cardRadius
                        gradient: Gradient {
                            GradientStop { position: 0.0; color: "#18314e" }
                            GradientStop { position: 0.5; color: "#0f1d2d" }
                            GradientStop { position: 1.0; color: "#09111a" }
                        }
                        border.color: root.accentBlue
                        border.width: 1
                        implicitHeight: brandColumn.implicitHeight + (root.cardPadding * 2)

                        ColumnLayout {
                            id: brandColumn
                            anchors.fill: parent
                            anchors.margins: root.cardPadding
                            spacing: root.scaled(3)

                            Text {
                                text: "飞腾派原生座舱 / Native Cockpit"
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
                                wrapMode: Text.WordWrap
                            }

                            Text {
                                Layout.fillWidth: true
                                text: root.topSubtitle
                                color: root.textSecondary
                                font.pixelSize: root.bodySize
                                font.family: root.uiFamily
                                wrapMode: Text.WordWrap
                                maximumLineCount: root.compactLayout ? 4 : 2
                                elide: Text.ElideRight
                            }
                        }
                    }

                    Rectangle {
                        Layout.columnSpan: root.compactLayout ? 1 : 2
                        Layout.fillWidth: true
                        radius: root.cardRadius
                        color: "#0c1520"
                        border.color: "#2f4460"
                        border.width: 1
                        implicitHeight: navColumn.implicitHeight + (root.cardPadding * 2)

                        ColumnLayout {
                            id: navColumn
                            anchors.fill: parent
                            anchors.margins: root.cardPadding
                            spacing: root.compactGap

                            RowLayout {
                                Layout.fillWidth: true
                                spacing: root.compactGap

                                Text {
                                    text: "导航甲板 / Zone Deck"
                                    color: root.accentCyan
                                    font.pixelSize: root.eyebrowSize
                                    font.family: root.monoFamily
                                    font.letterSpacing: root.scaled(1)
                                }

                                Item {
                                    Layout.fillWidth: true
                                }

                                Text {
                                    text: root.currentPage === 0 ? "页 1 / 5" : "页 " + String(root.currentPage + 1) + " / 5"
                                    color: root.textMuted
                                    font.pixelSize: root.captionSize
                                    font.family: root.monoFamily
                                }
                            }

                            Flow {
                                Layout.fillWidth: true
                                width: parent.width
                                spacing: root.compactGap

                                Repeater {
                                    model: root.navigationModel

                                    delegate: Rectangle {
                                        property var itemData: modelData
                                        readonly property bool active: root.currentPage === Number(itemData["index"])
                                        radius: root.edgeRadius
                                        color: active ? "#18283b" : "#0d1520"
                                        border.color: active ? root.accentBlue : "#29405a"
                                        border.width: 1
                                        implicitWidth: navTabColumn.implicitWidth + (root.scaled(14) * 2)
                                        implicitHeight: navTabColumn.implicitHeight + (root.scaled(9) * 2)

                                        Column {
                                            id: navTabColumn
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
                                                text: itemData["english"] + " / " + itemData["detail"]
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

                    PanelFrame {
                        shellWindow: root
                        panelColor: "#111b29"
                        borderTone: root.recentEventTone === "warning" ? root.accentAmber : root.borderSoft
                        accentTone: root.recentEventTone === "warning" ? root.accentAmber : root.accentCyan
                        Layout.fillWidth: true
                        implicitHeight: statusColumn.implicitHeight + (root.cardPadding * 2)

                        ColumnLayout {
                            id: statusColumn
                            anchors.fill: parent
                            anchors.margins: root.cardPadding
                            spacing: root.compactGap

                            RowLayout {
                                Layout.fillWidth: true
                                spacing: root.zoneGap

                                ColumnLayout {
                                    Layout.fillWidth: true
                                    spacing: root.scaled(2)

                                    Text {
                                        text: "任务简报 / Mission Brief"
                                        color: root.currentPage === 0 ? root.accentCyan : root.accentAmber
                                        font.pixelSize: root.eyebrowSize
                                        font.family: root.monoFamily
                                        font.letterSpacing: root.scaled(1)
                                    }

                                    Text {
                                        Layout.fillWidth: true
                                        text: root.currentPage === 0 ? root.landingSummaryTitle : DataUtils.objectOrEmpty(root.navigationModel[root.currentPage])["label"]
                                        color: root.textStrong
                                        font.pixelSize: root.sectionTitleSize
                                        font.bold: true
                                        font.family: root.displayFamily
                                        wrapMode: Text.WordWrap
                                    }

                                    Text {
                                        Layout.fillWidth: true
                                        text: root.currentPageSummary
                                        color: root.textSecondary
                                        font.pixelSize: root.bodySize
                                        font.family: root.uiFamily
                                        wrapMode: Text.WordWrap
                                        maximumLineCount: root.compactLayout ? 4 : 2
                                        elide: Text.ElideRight
                                    }
                                }

                                Rectangle {
                                    Layout.alignment: Qt.AlignTop
                                    radius: root.edgeRadius
                                    color: root.toneFill(root.currentPage === 0
                                        ? (root.trackData.length > 1 ? "online" : "neutral")
                                        : "neutral")
                                    border.color: root.toneColor(root.currentPage === 0
                                        ? (root.trackData.length > 1 ? "online" : "neutral")
                                        : "neutral")
                                    border.width: 1
                                    implicitWidth: currentZoneStamp.implicitWidth + (root.scaled(12) * 2)
                                    implicitHeight: currentZoneStamp.implicitHeight + (root.scaled(8) * 2)

                                    Column {
                                        id: currentZoneStamp
                                        anchors.centerIn: parent
                                        spacing: 1

                                        Text {
                                            text: root.currentPage === 0 ? "LANDING SHELL" : "ZONE VIEW"
                                            color: root.textMuted
                                            font.pixelSize: root.captionSize
                                            font.family: root.monoFamily
                                        }

                                        Text {
                                            text: root.currentPage === 0
                                                ? (root.trackData.length > 1 ? "LIVE TRACK" : "CONTRACT MIRROR")
                                                : String(DataUtils.objectOrEmpty(root.navigationModel[root.currentPage])["english"] || "ZONE")
                                            color: root.toneColor(root.currentPage === 0
                                                ? (root.trackData.length > 1 ? "online" : "neutral")
                                                : "neutral")
                                            font.pixelSize: root.captionSize + 1
                                            font.bold: true
                                            font.family: root.monoFamily
                                        }
                                    }
                                }
                            }

                            Rectangle {
                                Layout.fillWidth: true
                                radius: root.edgeRadius
                                gradient: Gradient {
                                    GradientStop { position: 0.0; color: "#142131" }
                                    GradientStop { position: 1.0; color: "#0b141e" }
                                }
                                border.color: root.recentEventTone === "warning" ? "#7a5a34" : "#2d4661"
                                border.width: 1
                                implicitHeight: liveBriefColumn.implicitHeight + (root.scaled(8) * 2)

                                Column {
                                    id: liveBriefColumn
                                    anchors.fill: parent
                                    anchors.margins: root.scaled(8)
                                    spacing: root.scaled(2)

                                    Text {
                                        text: "实时摘要 / Live Brief"
                                        color: root.textMuted
                                        font.pixelSize: root.captionSize
                                        font.family: root.monoFamily
                                    }

                                    Text {
                                        width: parent.width
                                        text: root.currentPage === 0 ? root.landingSummaryText : root.currentPageSummary
                                        color: root.textPrimary
                                        font.pixelSize: root.bodySize
                                        font.family: root.uiFamily
                                        wrapMode: Text.WordWrap
                                        maximumLineCount: root.compactLayout ? 3 : 2
                                        elide: Text.ElideRight
                                    }
                                }
                            }

                            Flow {
                                Layout.fillWidth: true
                                width: parent.width
                                spacing: root.compactGap

                                Repeater {
                                    model: root.topStatusModel

                                    delegate: Rectangle {
                                        property var itemData: modelData
                                        radius: root.edgeRadius
                                        color: root.toneFill(String(itemData["tone"] || "neutral"))
                                        border.color: root.toneColor(String(itemData["tone"] || "neutral"))
                                        border.width: 1
                                        implicitWidth: statusPillRow.implicitWidth + (root.scaled(10) * 2)
                                        implicitHeight: statusPillRow.implicitHeight + (root.scaled(7) * 2)

                                        Row {
                                            id: statusPillRow
                                            anchors.centerIn: parent
                                            spacing: root.scaled(8)

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
                }
            }

            StackLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true
                currentIndex: root.currentPage

                Item {
                    Layout.fillWidth: true
                    Layout.fillHeight: true

                    GridLayout {
                        anchors.fill: parent
                        columns: root.wideLayout ? 12 : (root.mediumLayout ? 2 : 1)
                        columnSpacing: root.zoneGap
                        rowSpacing: root.zoneGap

                        PanelFrame {
                            shellWindow: root
                            panelColor: root.panelColor
                            borderTone: root.borderSoft
                            accentTone: root.accentBlue
                            Layout.row: root.wideLayout ? 0 : 1
                            Layout.column: 0
                            Layout.columnSpan: 1
                            Layout.fillWidth: true
                            Layout.fillHeight: root.wideLayout
                            Layout.minimumWidth: root.scaled(root.wideLayout ? 196 : 214)
                            implicitHeight: leftRailColumn.implicitHeight + (root.panelPadding * 2)

                            ColumnLayout {
                                id: leftRailColumn
                                anchors.fill: parent
                                anchors.margins: root.panelPadding
                                spacing: root.compactGap

                                Text {
                                    text: "左导轨 / Mission Rail"
                                    color: root.accentBlue
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
                                    color: "#243548"
                                }

                                Repeater {
                                    model: root.landingTelemetryModel

                                    delegate: Rectangle {
                                        property var itemData: modelData
                                        Layout.fillWidth: true
                                        radius: root.edgeRadius
                                        color: "#0d1520"
                                        border.color: root.toneColor(String(itemData["tone"] || "neutral"))
                                        border.width: 1
                                        implicitHeight: telemetryColumn.implicitHeight + (root.scaled(9) * 2)

                                        Column {
                                            id: telemetryColumn
                                            anchors.fill: parent
                                            anchors.margins: root.scaled(9)
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
                                                wrapMode: Text.WrapAnywhere
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

                        PanelFrame {
                            shellWindow: root
                            panelColor: root.cardColor
                            borderTone: root.borderStrong
                            accentTone: root.accentCyan
                            Layout.row: 0
                            Layout.column: root.wideLayout ? 1 : 0
                            Layout.columnSpan: root.wideLayout ? 10 : (root.mediumLayout ? 2 : 1)
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            Layout.minimumHeight: root.scaled(root.wideLayout ? 480 : (root.mediumLayout ? 410 : 320))

                            Item {
                                anchors.fill: parent
                                anchors.margins: root.scaled(12)

                                ColumnLayout {
                                    anchors.fill: parent
                                    spacing: root.compactGap

                                    RowLayout {
                                        Layout.fillWidth: true
                                        spacing: root.zoneGap

                                        ColumnLayout {
                                            Layout.fillWidth: true
                                            spacing: root.scaled(1)

                                            Text {
                                                text: "中心主舞台 / Command Wall"
                                                color: root.accentCyan
                                                font.pixelSize: root.eyebrowSize
                                                font.family: root.monoFamily
                                                font.letterSpacing: root.scaled(1)
                                            }

                                            Text {
                                                text: root.landingStageTitle
                                                color: root.textStrong
                                                font.pixelSize: root.bodyEmphasisSize + (root.wideLayout ? root.scaled(3) : root.scaled(1))
                                                font.bold: true
                                                font.family: root.displayFamily
                                                maximumLineCount: 1
                                                elide: Text.ElideRight
                                            }

                                            Text {
                                                Layout.fillWidth: true
                                                text: root.landingSummaryTitle
                                                color: root.textSecondary
                                                font.pixelSize: root.captionSize + 1
                                                font.family: root.uiFamily
                                                wrapMode: Text.WordWrap
                                                maximumLineCount: 2
                                                elide: Text.ElideRight
                                            }
                                        }

                                        Rectangle {
                                            Layout.alignment: Qt.AlignTop
                                            radius: root.edgeRadius
                                            color: root.toneFill(root.liveAnchorTone)
                                            border.color: root.toneColor(root.liveAnchorTone)
                                            border.width: 1
                                            implicitWidth: mapStatusStamp.implicitWidth + (root.scaled(12) * 2)
                                            implicitHeight: mapStatusStamp.implicitHeight + (root.scaled(8) * 2)

                                            Column {
                                                id: mapStatusStamp
                                                anchors.centerIn: parent
                                                spacing: 1

                                                Text {
                                                    text: "MAP STAGE"
                                                    color: root.textMuted
                                                    font.pixelSize: root.captionSize
                                                    font.family: root.monoFamily
                                                }

                                                Text {
                                                    text: root.trackData.length > 1 ? "LIVE TRACK" : "CONTRACT MIRROR"
                                                    color: root.toneColor(root.trackData.length > 1 ? "online" : "neutral")
                                                    font.pixelSize: root.captionSize + 1
                                                    font.bold: true
                                                    font.family: root.monoFamily
                                                }
                                            }
                                        }
                                    }

                                    Rectangle {
                                        id: landingMapViewport
                                        Layout.fillWidth: true
                                        Layout.fillHeight: true
                                        radius: root.cardRadius
                                        clip: true
                                        gradient: Gradient {
                                            GradientStop { position: 0.0; color: "#10263b" }
                                            GradientStop { position: 0.34; color: "#0b1827" }
                                            GradientStop { position: 1.0; color: "#071018" }
                                        }
                                        border.color: "#355674"
                                        border.width: 1

                                        WorldMapStage {
                                            anchors.fill: parent
                                            anchors.margins: 2
                                            shellWindow: root
                                            landingMode: true
                                            trackData: root.trackData
                                            currentPoint: root.currentPosition
                                            headingDeg: Number(root.kinematics["heading_deg"] || 0)
                                            currentLabel: root.missionCallSignValue + " 实时航迹"
                                            currentDetail: root.coordinatePair(root.currentPosition) + " / " + root.formattedMetric(root.kinematics["ground_speed_kph"], 0, "km/h")
                                            anchorLabel: String(root.liveAnchor["valid_instance"] || "--")
                                            projectionLabel: "等经纬投影 / Equirectangular"
                                            scenarioLabel: root.recommendedScenarioId
                                            scenarioTone: root.liveAnchorTone
                                            bannerEyebrow: "LIVE COMMAND BRIEF / GLOBAL WALLBOARD"
                                            bannerTitle: root.landingMapBannerTitle
                                            bannerText: root.landingMapBannerText
                                            bannerChips: root.landingStageChipModel
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
                            Layout.row: root.wideLayout ? 0 : (root.mediumLayout ? 1 : 2)
                            Layout.column: root.wideLayout ? 11 : (root.mediumLayout ? 1 : 0)
                            Layout.columnSpan: 1
                            Layout.fillWidth: true
                            Layout.fillHeight: root.wideLayout
                            Layout.minimumWidth: root.scaled(root.wideLayout ? 216 : 236)
                            implicitHeight: rightRailColumn.implicitHeight + (root.panelPadding * 2)

                            ColumnLayout {
                                id: rightRailColumn
                                anchors.fill: parent
                                anchors.margins: root.panelPadding
                                spacing: root.compactGap

                                Text {
                                    text: "右导轨 / Jump Rail"
                                    color: root.accentAmber
                                    font.pixelSize: root.eyebrowSize
                                    font.family: root.monoFamily
                                    font.letterSpacing: root.scaled(1)
                                }

                                Text {
                                    text: "显式跳转与弱网摘要"
                                    color: root.textStrong
                                    font.pixelSize: root.sectionTitleSize
                                    font.bold: true
                                    font.family: root.displayFamily
                                    wrapMode: Text.WordWrap
                                }

                                Text {
                                    Layout.fillWidth: true
                                    text: "把系统、飞行、弱网和执行收口为显式跳转轨，首屏保持地图主舞台。"
                                    color: root.textSecondary
                                    font.pixelSize: root.bodySize
                                    font.family: root.uiFamily
                                    wrapMode: Text.WordWrap
                                }

                                Repeater {
                                    model: root.landingJumpModel

                                    delegate: Rectangle {
                                        property var itemData: modelData
                                        radius: root.edgeRadius
                                        color: "#0d1520"
                                        border.color: root.toneColor(String(itemData["tone"] || "neutral"))
                                        border.width: 1
                                        implicitHeight: jumpColumn.implicitHeight + (root.scaled(9) * 2)

                                        Column {
                                            id: jumpColumn
                                            anchors.fill: parent
                                            anchors.margins: root.scaled(9)
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

                                Rectangle {
                                    Layout.fillWidth: true
                                    Layout.preferredHeight: 1
                                    color: "#243548"
                                }

                                Repeater {
                                    model: root.landingWeakMetricModel

                                    delegate: Rectangle {
                                        property var itemData: modelData
                                        radius: root.edgeRadius
                                        color: root.toneFill(String(itemData["tone"] || "neutral"))
                                        border.color: root.toneColor(String(itemData["tone"] || "neutral"))
                                        border.width: 1
                                        implicitHeight: weakColumn.implicitHeight + (root.scaled(9) * 2)

                                        Column {
                                            id: weakColumn
                                            anchors.fill: parent
                                            anchors.margins: root.scaled(9)
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
                                                wrapMode: Text.WrapAnywhere
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
                                implicitHeight: systemHeader.implicitHeight + (root.panelPadding * 2)

                                ColumnLayout {
                                    id: systemHeader
                                    anchors.fill: parent
                                    anchors.margins: root.panelPadding
                                    spacing: root.compactGap

                                    RowLayout {
                                        Layout.fillWidth: true
                                        spacing: root.zoneGap

                                        Rectangle {
                                            radius: root.edgeRadius
                                            color: "#0d1520"
                                            border.color: root.accentBlue
                                            border.width: 1
                                            implicitWidth: systemBackRow.implicitWidth + (root.scaled(12) * 2)
                                            implicitHeight: systemBackRow.implicitHeight + (root.scaled(8) * 2)

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
                                                text: "集中查看会话、心跳、快照原因和模式边界说明。首屏不再把这些高密度证据与世界地图抢同一块空间。"
                                                color: root.textSecondary
                                                font.pixelSize: root.bodySize
                                                font.family: root.uiFamily
                                                wrapMode: Text.WordWrap
                                            }
                                        }
                                    }

                                    Flow {
                                        Layout.fillWidth: true
                                        width: parent.width
                                        spacing: root.compactGap

                                        Repeater {
                                            model: root.systemPageChipModel

                                            delegate: Rectangle {
                                                property var itemData: modelData
                                                radius: root.edgeRadius
                                                color: root.toneFill(String(itemData["tone"] || "neutral"))
                                                border.color: root.toneColor(String(itemData["tone"] || "neutral"))
                                                border.width: 1
                                                implicitWidth: pageChipRow.implicitWidth + (root.scaled(10) * 2)
                                                implicitHeight: pageChipRow.implicitHeight + (root.scaled(7) * 2)

                                                Row {
                                                    id: pageChipRow
                                                    anchors.centerIn: parent
                                                    spacing: root.scaled(8)

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
                                        implicitHeight: truthColumn.implicitHeight + (root.panelPadding * 2)

                                        ColumnLayout {
                                            id: truthColumn
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
                                                text: "真值说明与快照来源"
                                                color: root.textStrong
                                                font.pixelSize: root.bodyEmphasisSize
                                                font.bold: true
                                                font.family: root.uiFamily
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
                                        implicitHeight: systemFactsColumn.implicitHeight + (root.panelPadding * 2)

                                        ColumnLayout {
                                            id: systemFactsColumn
                                            anchors.fill: parent
                                            anchors.margins: root.panelPadding
                                            spacing: root.compactGap

                                            Text {
                                                text: "系统摘要 / Snapshot Facts"
                                                color: root.accentBlue
                                                font.pixelSize: root.eyebrowSize
                                                font.family: root.monoFamily
                                            }

                                            Repeater {
                                                model: [
                                                    { "label": "事件时间", "value": root.eventTimeValue, "tone": "neutral" },
                                                    { "label": "快照原因", "value": root.snapshotReasonValue, "tone": "warning" },
                                                    { "label": "板端锚点", "value": String(root.liveAnchor["board_status"] || "--"), "tone": root.liveAnchorTone }
                                                ]

                                                delegate: Rectangle {
                                                    property var itemData: modelData
                                                    radius: root.edgeRadius
                                                    color: root.toneFill(String(itemData["tone"] || "neutral"))
                                                    border.color: root.toneColor(String(itemData["tone"] || "neutral"))
                                                    border.width: 1
                                                    implicitHeight: factColumn.implicitHeight + (root.scaled(8) * 2)

                                                    Column {
                                                        id: factColumn
                                                        anchors.fill: parent
                                                        anchors.margins: root.scaled(8)
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
                                implicitHeight: flightHeader.implicitHeight + (root.panelPadding * 2)

                                ColumnLayout {
                                    id: flightHeader
                                    anchors.fill: parent
                                    anchors.margins: root.panelPadding
                                    spacing: root.compactGap

                                    RowLayout {
                                        Layout.fillWidth: true
                                        spacing: root.zoneGap

                                        Rectangle {
                                            radius: root.edgeRadius
                                            color: "#0d1520"
                                            border.color: root.accentBlue
                                            border.width: 1
                                            implicitWidth: flightBackRow.implicitWidth + (root.scaled(12) * 2)
                                            implicitHeight: flightBackRow.implicitHeight + (root.scaled(8) * 2)

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
                                                text: "保留完整飞行遥测、世界地图与板端联动细节。Landing 页只借用其世界地图主舞台，不再把整页内容全部塞回首屏。"
                                                color: root.textSecondary
                                                font.pixelSize: root.bodySize
                                                font.family: root.uiFamily
                                                wrapMode: Text.WordWrap
                                            }
                                        }
                                    }

                                    Flow {
                                        Layout.fillWidth: true
                                        width: parent.width
                                        spacing: root.compactGap

                                        Repeater {
                                            model: root.flightPageChipModel

                                            delegate: Rectangle {
                                                property var itemData: modelData
                                                radius: root.edgeRadius
                                                color: root.toneFill(String(itemData["tone"] || "neutral"))
                                                border.color: root.toneColor(String(itemData["tone"] || "neutral"))
                                                border.width: 1
                                                implicitWidth: flightChipRow.implicitWidth + (root.scaled(10) * 2)
                                                implicitHeight: flightChipRow.implicitHeight + (root.scaled(7) * 2)

                                                Row {
                                                    id: flightChipRow
                                                    anchors.centerIn: parent
                                                    spacing: root.scaled(8)

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

                            TacticalView {
                                shellWindow: root
                                panelData: root.centerPanelData
                                Layout.fillWidth: true
                                Layout.preferredHeight: root.scaled(root.wideLayout ? 940 : 780)
                            }

                            PanelFrame {
                                shellWindow: root
                                panelColor: root.panelColor
                                borderTone: root.borderSoft
                                accentTone: root.accentAmber
                                Layout.fillWidth: true
                                implicitHeight: flightNoteColumn.implicitHeight + (root.panelPadding * 2)

                                ColumnLayout {
                                    id: flightNoteColumn
                                    anchors.fill: parent
                                    anchors.margins: root.panelPadding
                                    spacing: root.compactGap

                                    Text {
                                        text: "源与回退 / Feed Routing"
                                        color: root.accentAmber
                                        font.pixelSize: root.eyebrowSize
                                        font.family: root.monoFamily
                                    }

                                    Text {
                                        Layout.fillWidth: true
                                        text: "数据源: " + root.activeSourceLabel
                                        color: root.textStrong
                                        font.pixelSize: root.bodyEmphasisSize
                                        font.bold: true
                                        font.family: root.uiFamily
                                        wrapMode: Text.WordWrap
                                    }

                                    Text {
                                        Layout.fillWidth: true
                                        text: compactMessage(String(root.centerPanelData["fallback_note"] || root.centerPanelData["ownership_note"] || "继续沿用仓库合同给出的 feed routing 说明。"), root.compactLayout ? 88 : 180)
                                        color: root.textSecondary
                                        font.pixelSize: root.bodySize
                                        font.family: root.uiFamily
                                        wrapMode: Text.WordWrap
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
                                implicitHeight: weakHeader.implicitHeight + (root.panelPadding * 2)

                                ColumnLayout {
                                    id: weakHeader
                                    anchors.fill: parent
                                    anchors.margins: root.panelPadding
                                    spacing: root.compactGap

                                    RowLayout {
                                        Layout.fillWidth: true
                                        spacing: root.zoneGap

                                        Rectangle {
                                            radius: root.edgeRadius
                                            color: "#0d1520"
                                            border.color: root.accentAmber
                                            border.width: 1
                                            implicitWidth: weakBackRow.implicitWidth + (root.scaled(12) * 2)
                                            implicitHeight: weakBackRow.implicitHeight + (root.scaled(8) * 2)

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
                                                text: "完整保留后端驱动的弱网 compare、在线锚点与推荐剧本。Landing 页只露出跳转轨与缩略指标，不稀释这里的对照细节。"
                                                color: root.textSecondary
                                                font.pixelSize: root.bodySize
                                                font.family: root.uiFamily
                                                wrapMode: Text.WordWrap
                                            }
                                        }
                                    }

                                    Flow {
                                        Layout.fillWidth: true
                                        width: parent.width
                                        spacing: root.compactGap

                                        Repeater {
                                            model: root.weakPageChipModel

                                            delegate: Rectangle {
                                                property var itemData: modelData
                                                radius: root.edgeRadius
                                                color: root.toneFill(String(itemData["tone"] || "neutral"))
                                                border.color: root.toneColor(String(itemData["tone"] || "neutral"))
                                                border.width: 1
                                                implicitWidth: weakChipRow.implicitWidth + (root.scaled(10) * 2)
                                                implicitHeight: weakChipRow.implicitHeight + (root.scaled(7) * 2)

                                                Row {
                                                    id: weakChipRow
                                                    anchors.centerIn: parent
                                                    spacing: root.scaled(8)

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

                            WeakNetworkPanel {
                                shellWindow: root
                                panelData: root.rightPanelData
                                Layout.fillWidth: true
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
                                accentTone: root.accentCyan
                                Layout.fillWidth: true
                                implicitHeight: actionHeader.implicitHeight + (root.panelPadding * 2)

                                ColumnLayout {
                                    id: actionHeader
                                    anchors.fill: parent
                                    anchors.margins: root.panelPadding
                                    spacing: root.compactGap

                                    RowLayout {
                                        Layout.fillWidth: true
                                        spacing: root.zoneGap

                                        Rectangle {
                                            radius: root.edgeRadius
                                            color: "#0d1520"
                                            border.color: root.accentCyan
                                            border.width: 1
                                            implicitWidth: actionBackRow.implicitWidth + (root.scaled(12) * 2)
                                            implicitHeight: actionBackRow.implicitHeight + (root.scaled(8) * 2)

                                            Row {
                                                id: actionBackRow
                                                anchors.centerIn: parent
                                                spacing: root.scaled(6)

                                                Text {
                                                    text: "<"
                                                    color: root.accentCyan
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
                                                text: "保持与首屏底部坞站一致的合同动作语义，但这里展开完整门控与说明。软件渲染安全启动入口继续保留。"
                                                color: root.textSecondary
                                                font.pixelSize: root.bodySize
                                                font.family: root.uiFamily
                                                wrapMode: Text.WordWrap
                                            }
                                        }
                                    }

                                    Flow {
                                        Layout.fillWidth: true
                                        width: parent.width
                                        spacing: root.compactGap

                                        Repeater {
                                            model: root.actionPageChipModel

                                            delegate: Rectangle {
                                                property var itemData: modelData
                                                radius: root.edgeRadius
                                                color: root.toneFill(String(itemData["tone"] || "neutral"))
                                                border.color: root.toneColor(String(itemData["tone"] || "neutral"))
                                                border.width: 1
                                                implicitWidth: actionChipRow.implicitWidth + (root.scaled(10) * 2)
                                                implicitHeight: actionChipRow.implicitHeight + (root.scaled(7) * 2)

                                                Row {
                                                    id: actionChipRow
                                                    anchors.centerIn: parent
                                                    spacing: root.scaled(8)

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

                            ActionStrip {
                                shellWindow: root
                                panelData: root.bottomPanelData
                                Layout.fillWidth: true
                            }
                        }
                    }
                }
            }

            PanelFrame {
                shellWindow: root
                panelColor: root.panelColorSoft
                borderTone: root.borderSoft
                accentTone: root.accentAmber
                Layout.fillWidth: true
                implicitHeight: dockLayout.implicitHeight + (root.panelPadding * 2)

                GridLayout {
                    id: dockLayout
                    anchors.fill: parent
                    anchors.margins: root.panelPadding
                    columns: root.compactLayout ? 1 : (root.mediumLayout ? 2 : 3)
                    columnSpacing: root.zoneGap
                    rowSpacing: root.compactGap

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: root.compactGap

                        Text {
                            text: "底部坞站 / Compact Action Dock"
                            color: root.accentAmber
                            font.pixelSize: root.eyebrowSize
                            font.family: root.monoFamily
                            font.letterSpacing: root.scaled(1)
                        }

                        Text {
                            text: "随时可调用的执行坞站"
                            color: root.textStrong
                            font.pixelSize: root.bodyEmphasisSize
                            font.bold: true
                            font.family: root.uiFamily
                        }

                        Text {
                            Layout.fillWidth: true
                            text: root.dockFooterSummary
                            color: root.textSecondary
                            font.pixelSize: root.bodySize
                            font.family: root.uiFamily
                            wrapMode: Text.WordWrap
                            maximumLineCount: 2
                            elide: Text.ElideRight
                        }

                        Rectangle {
                            Layout.fillWidth: true
                            radius: root.edgeRadius
                            color: "#0d1520"
                            border.color: "#29405a"
                            border.width: 1
                            implicitHeight: dockLaunchText.implicitHeight + (root.scaled(7) * 2)

                            Text {
                                id: dockLaunchText
                                anchors.left: parent.left
                                anchors.right: parent.right
                                anchors.verticalCenter: parent.verticalCenter
                                anchors.leftMargin: root.scaled(10)
                                anchors.rightMargin: root.scaled(10)
                                text: root.dockLaunchLabel
                                color: root.textPrimary
                                font.pixelSize: root.captionSize
                                font.family: root.monoFamily
                                elide: Text.ElideMiddle
                            }
                        }
                    }

                    Item {
                        Layout.fillWidth: true
                        implicitHeight: dockActionFlow.implicitHeight

                        Flow {
                            id: dockActionFlow
                            width: parent.width
                            spacing: root.compactGap

                            Repeater {
                                model: root.dockPreviewActions

                                delegate: Rectangle {
                                    property var itemData: modelData
                                    radius: root.edgeRadius
                                    color: itemData["enabled"] ? root.toneFill(String(itemData["tone"] || "neutral")) : "#0d1520"
                                    border.color: itemData["enabled"]
                                        ? root.toneColor(String(itemData["tone"] || "neutral"))
                                        : "#2c3c50"
                                    border.width: 1
                                    width: Math.max(root.scaled(142), dockActionRow.implicitWidth + (root.scaled(16) * 2))
                                    height: dockActionRow.implicitHeight + (root.scaled(8) * 2)

                                    Row {
                                        id: dockActionRow
                                        anchors.centerIn: parent
                                        spacing: root.scaled(8)

                                        Text {
                                            width: root.scaled(92)
                                            text: itemData["label"]
                                            color: root.textStrong
                                            font.pixelSize: root.bodySize
                                            font.bold: true
                                            font.family: root.uiFamily
                                            elide: Text.ElideRight
                                        }

                                        Text {
                                            text: itemData["enabled"] ? "live" : compactMessage(String(itemData["note"] || "只读合同"), 14)
                                            color: itemData["enabled"] ? root.toneColor(String(itemData["tone"] || "neutral")) : root.textMuted
                                            font.pixelSize: root.captionSize
                                            font.family: root.monoFamily
                                            font.bold: itemData["enabled"]
                                        }
                                    }
                                }
                            }
                        }
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: root.compactGap

                        Flow {
                            Layout.fillWidth: true
                            width: parent.width
                            spacing: root.compactGap

                            Repeater {
                                model: [
                                    { "label": "页面", "value": DataUtils.objectOrEmpty(root.navigationModel[root.currentPage])["label"], "tone": "neutral" },
                                    { "label": "动作", "value": String(root.enabledBottomActions) + " live", "tone": root.enabledBottomActions > 0 ? "online" : "warning" },
                                    { "label": "桥接", "value": root.bridgeAvailable ? "online" : "offline", "tone": root.bridgeAvailable ? "online" : "warning" }
                                ]

                                delegate: Rectangle {
                                    property var itemData: modelData
                                    radius: root.edgeRadius
                                    color: root.toneFill(String(itemData["tone"] || "neutral"))
                                    border.color: root.toneColor(String(itemData["tone"] || "neutral"))
                                    border.width: 1
                                    implicitWidth: dockStatRow.implicitWidth + (root.scaled(10) * 2)
                                    implicitHeight: dockStatRow.implicitHeight + (root.scaled(7) * 2)

                                    Row {
                                        id: dockStatRow
                                        anchors.centerIn: parent
                                        spacing: root.scaled(8)

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

                        Item {
                            Layout.fillWidth: true
                            implicitHeight: dockCtaButton.implicitHeight

                            Rectangle {
                                id: dockCtaButton
                                anchors.right: parent.right
                                radius: root.edgeRadius
                                color: "#0d1520"
                                border.color: root.accentCyan
                                border.width: 1
                                implicitWidth: dockCtaRow.implicitWidth + (root.scaled(14) * 2)
                                implicitHeight: dockCtaRow.implicitHeight + (root.scaled(9) * 2)

                                Row {
                                    id: dockCtaRow
                                    anchors.centerIn: parent
                                    spacing: root.scaled(8)

                                    Text {
                                        text: "进入执行坞站"
                                        color: root.textStrong
                                        font.pixelSize: root.bodySize
                                        font.bold: true
                                        font.family: root.uiFamily
                                    }

                                    Text {
                                        text: ">"
                                        color: root.accentCyan
                                        font.pixelSize: root.bodyEmphasisSize
                                        font.bold: true
                                        font.family: root.monoFamily
                                    }
                                }

                                MouseArea {
                                    anchors.fill: parent
                                    hoverEnabled: true
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: root.currentPage = 4
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
