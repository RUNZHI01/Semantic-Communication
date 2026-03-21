import QtQuick 2.15
import QtQuick.Controls 2.15
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
    readonly property string recommendedScenarioId: String(
        rightPanelData["recommended_scenario_id"] || recommendedScenario["scenario_id"] || "--"
    )
    readonly property int enabledBottomActions: enabledActionTotal(bottomActions)
    readonly property bool softwareRenderEnabled: !!options["softwareRender"]

    readonly property int designWidth: 1440
    readonly property int designHeight: 900

    readonly property string displayFamily: "Noto Serif CJK SC"
    readonly property string uiFamily: "Noto Sans CJK SC"
    readonly property string monoFamily: "JetBrains Mono"

    readonly property color sceneTop: "#050608"
    readonly property color sceneMid: "#0a0f14"
    readonly property color sceneBottom: "#12181f"
    readonly property color haloCool: "#18303a"
    readonly property color haloWarm: "#4f3d29"
    readonly property color shellExterior: "#0b1117"
    readonly property color shellInterior: "#11181f"
    readonly property color surfaceRaised: "#18212a"
    readonly property color surfaceQuiet: "#0f161d"
    readonly property color surfaceGlass: "#1c2731"
    readonly property color borderSubtle: "#2a3944"
    readonly property color borderStrong: "#b4946c"
    readonly property color accentIce: "#86c7d4"
    readonly property color accentGold: "#c6ab7d"
    readonly property color accentMint: "#93bea5"
    readonly property color accentRose: "#c88478"
    readonly property color textStrong: "#f5efe4"
    readonly property color textPrimary: "#d7dde2"
    readonly property color textSecondary: "#9aa8b1"
    readonly property color textMuted: "#6f7f8a"
    readonly property color dataLine: "#1b2730"
    readonly property color dataLineStrong: "#33434f"
    readonly property color panelHighlight: "#22303b"
    readonly property color panelGlowSoft: "#86c7d4"
    readonly property color canopyTop: "#1b252e"
    readonly property color canopyBottom: "#0b1015"

    readonly property color panelColor: surfaceRaised
    readonly property color panelColorRaised: surfaceGlass
    readonly property color panelColorSoft: surfaceQuiet
    readonly property color cardColor: surfaceRaised
    readonly property color borderSoft: borderSubtle
    readonly property color accentBlue: "#9cb4c1"
    readonly property color accentCyan: accentIce
    readonly property color accentAmber: accentGold
    readonly property color accentGreen: accentMint
    readonly property color accentRed: accentRose
    readonly property color gridLine: dataLine
    readonly property color gridLineStrong: dataLineStrong
    readonly property color shellDockTop: "#202d37"
    readonly property color shellDockMid: "#141d25"
    readonly property color shellDockBottom: "#0b1117"
    readonly property color panelGlowStrong: panelGlowSoft
    readonly property color panelTraceStrong: borderStrong

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
    readonly property bool wideLayout: viewportWidth >= 1360
    readonly property bool mediumLayout: !wideLayout && viewportWidth >= 1040
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
    readonly property int sectionTitleSize: scaled(compactLayout ? 20 : 26)
    readonly property int bodyEmphasisSize: scaled(compactLayout ? 14 : 15)
    readonly property int bodySize: scaled(13)
    readonly property int captionSize: scaled(10)
    readonly property int eyebrowSize: scaled(10)

    readonly property string topTitle: primaryLabel(meta["title"] || "飞腾原生座舱")
    readonly property string topSubtitle: String(
        meta["subtitle"] || "Qt/QML 原生壳体继续读取仓库现有 TVM/OpenAMP 演示合同，并保持软件渲染安全启动。"
    )
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
    readonly property string landingSummaryTitle: recentEventTone === "warning"
        ? "异常事件已回注到主壳体"
        : "地图优先的原生命令壳"
    readonly property string landingSummaryText: String(centerControlSummary["last_event_message"] || rightPanelData["summary"] || topSubtitle)
    readonly property string landingMapBannerTitle: missionCallSignValue + " · " + aircraftIdValue
    readonly property string landingMapBannerText: coordinatePair(currentPosition) + " · "
        + formattedMetric(kinematics["ground_speed_kph"], 0, "km/h")
    readonly property string footerNote: String(
        bottomPanelData["footer_note"] || "默认执行仓库内软件渲染安全启动路径。"
    )
    readonly property string currentPageSummary: String(
        DataUtils.objectOrEmpty(navigationModel[currentPage])["summary"] || topSubtitle
    )

    property int currentPage: 0

    readonly property var navigationModel: [
        {
            "index": 0,
            "label": "总览",
            "english": "Landing",
            "summary": "地图主舞台、左舷系统轨、右舷弱网策略与执行坞站。"
        },
        {
            "index": 1,
            "label": "系统板态",
            "english": "System",
            "summary": "会话、心跳、最近事件、快照原因与事实边界。"
        },
        {
            "index": 2,
            "label": "飞行合同",
            "english": "Flight",
            "summary": "全球地图、飞机合同、实时遥测与采样元数据。"
        },
        {
            "index": 3,
            "label": "弱网策略",
            "english": "Weak-Link",
            "summary": "推荐档、吞吐 uplift、在线锚点与对照证据。"
        },
        {
            "index": 4,
            "label": "执行坞站",
            "english": "Action Dock",
            "summary": "合同动作、启动入口、渲染模式与只读门控。"
        }
    ]

    readonly property var topStatusModel: [
        { "label": "会话", "value": systemSessionValue, "tone": "neutral" },
        { "label": "心跳", "value": heartbeatValue, "tone": heartbeatTone },
        { "label": "在线锚点", "value": String(liveAnchor["valid_instance"] || "--"), "tone": liveAnchorTone },
        { "label": "渲染", "value": softwareRenderEnabled ? "软件安全" : "图形优先", "tone": softwareRenderEnabled ? "warning" : "online" }
    ]

    readonly property var landingJumpModel: [
        {
            "index": 1,
            "label": "系统板态",
            "english": "System",
            "summary": "会话、心跳与快照原因",
            "value": compactMessage(heartbeatValue + " / " + snapshotReasonValue, compactLayout ? 20 : 30),
            "tone": heartbeatTone
        },
        {
            "index": 2,
            "label": "飞行合同",
            "english": "Flight",
            "summary": "地图、遥测与数据合同",
            "value": compactMessage(activeSourceLabel, compactLayout ? 16 : 22),
            "tone": "online"
        },
        {
            "index": 3,
            "label": "弱网策略",
            "english": "Weak-Link",
            "summary": "推荐档与在线锚点",
            "value": compactMessage(recommendedScenarioId, compactLayout ? 12 : 18),
            "tone": "warning"
        },
        {
            "index": 4,
            "label": "执行坞站",
            "english": "Action Dock",
            "summary": "合同动作与启动命令",
            "value": String(enabledBottomActions) + " / " + String(bottomActions.length) + " 动作",
            "tone": enabledBottomActions > 0 ? "online" : "warning"
        }
    ]

    readonly property var landingTelemetryModel: [
        {
            "label": "当前位置",
            "value": coordinatePair(currentPosition),
            "detail": "WGS84 / 实时位置",
            "tone": "neutral"
        },
        {
            "label": "飞行高度",
            "value": formattedMetric(kinematics["altitude_m"], 0, "m"),
            "detail": "垂速 " + formattedMetric(kinematics["vertical_speed_mps"], 1, "m/s"),
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
            "detail": compactMessage(
                String(recommendedScenario["summary"] || "延续仓库现有弱网推荐剧本。"),
                compactLayout ? 26 : 44
            ),
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
            "detail": compactMessage(String(liveAnchor["board_status"] || "等待在线锚点"), compactLayout ? 16 : 28),
            "tone": liveAnchorTone
        }
    ]

    readonly property var landingStageChipModel: [
        { "label": "数据源", "value": compactMessage(activeSourceLabel, compactLayout ? 18 : 24), "tone": "online" },
        { "label": "锚点", "value": String(liveAnchor["valid_instance"] || "--"), "tone": liveAnchorTone },
        { "label": "链路", "value": compactMessage(linkProfileValue, compactLayout ? 14 : 20), "tone": "neutral" }
    ]

    readonly property var systemPageChipModel: [
        { "label": "会话", "value": systemSessionValue, "tone": "neutral" },
        { "label": "心跳", "value": heartbeatValue, "tone": heartbeatTone },
        { "label": "最近事件", "value": compactMessage(recentEventValue, compactLayout ? 12 : 18), "tone": recentEventTone },
        { "label": "链路", "value": compactMessage(linkProfileValue, compactLayout ? 12 : 18), "tone": "neutral" }
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

    minimumWidth: 760
    minimumHeight: 600
    visible: true
    color: sceneBottom
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
            return accentMint
        if (tone === "warning" || tone === "degraded")
            return accentGold
        if (tone === "danger")
            return accentRose
        return accentIce
    }

    function toneFill(tone) {
        if (tone === "online")
            return "#18231d"
        if (tone === "warning" || tone === "degraded")
            return "#251f18"
        if (tone === "danger")
            return "#26191a"
        return "#152029"
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
        var preferredScenarioId = String(rightPanelData["recommended_scenario_id"] || "")
        for (var index = 0; index < scenarioList.length; ++index) {
            var scenario = DataUtils.objectOrEmpty(scenarioList[index])
            if (!!scenario["recommended"] || String(scenario["scenario_id"] || "") === preferredScenarioId)
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

    function previewItems(itemsModel, limit) {
        var resolved = DataUtils.arrayOrEmpty(itemsModel)
        if (resolved.length <= limit)
            return resolved
        return resolved.slice(0, limit)
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
            GradientStop { position: 0.0; color: root.sceneTop }
            GradientStop { position: 0.46; color: root.sceneMid }
            GradientStop { position: 1.0; color: root.sceneBottom }
        }
    }

    Rectangle {
        width: root.width * 0.62
        height: root.height * 0.68
        radius: width / 2
        color: root.haloCool
        opacity: 0.16
        x: -width * 0.18
        y: -height * 0.12
    }

    Rectangle {
        width: root.width * 0.38
        height: root.height * 0.46
        radius: width / 2
        color: root.haloWarm
        opacity: 0.11
        x: root.width - (width * 0.8)
        y: root.height * 0.1
    }

    Item {
        anchors.fill: parent
        opacity: 0.13

        Repeater {
            model: 10

            delegate: Rectangle {
                width: parent ? parent.width : 0
                height: 1
                color: index % 2 === 0 ? root.dataLineStrong : root.dataLine
                y: index * ((parent ? parent.height : 0) / 9)
            }
        }

        Repeater {
            model: 18

            delegate: Rectangle {
                width: 1
                height: parent ? parent.height : 0
                color: index % 3 === 0 ? root.dataLineStrong : root.dataLine
                x: index * ((parent ? parent.width : 0) / 17)
            }
        }
    }

    LandingShell {
        anchors.fill: parent
        shellWindow: root
    }
}
