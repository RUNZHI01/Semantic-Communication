import QtQuick 2.15
import QtQuick.Layouts 1.15
import "DataUtils.js" as DataUtils

PanelFrame {
    id: root
    property var panelData: ({})
    readonly property var panel: DataUtils.objectOrEmpty(panelData)

    panelColor: shellWindow ? shellWindow.panelColorRaised : "#0d2034"
    borderTone: shellWindow ? shellWindow.borderStrong : "#42bcff"
    accentTone: shellWindow ? shellWindow.accentCyan : "#72f3ff"
    readonly property color accentBlue: shellWindow ? shellWindow.accentBlue : "#38b6ff"
    readonly property color accentCyan: shellWindow ? shellWindow.accentCyan : "#72f3ff"

    readonly property var positionData: DataUtils.objectOrEmpty(panel["position"])
    readonly property var kinematicsData: DataUtils.objectOrEmpty(panel["kinematics"])
    readonly property var fixData: DataUtils.objectOrEmpty(panel["fix"])
    readonly property var trackData: DataUtils.arrayOrEmpty(panel["track"])
    readonly property var controlSummary: DataUtils.objectOrEmpty(panel["control_summary"])
    readonly property var feedContractData: DataUtils.objectOrEmpty(panel["feed_contract"])
    readonly property var sampleData: DataUtils.objectOrEmpty(panel["sample"])
    readonly property var shellRightPanelData: shellWindow ? DataUtils.objectOrEmpty(shellWindow.rightPanelData) : ({})
    readonly property var liveAnchorData: DataUtils.objectOrEmpty(shellRightPanelData["live_anchor"])
    readonly property var weakNetworkScenarios: DataUtils.arrayOrEmpty(shellRightPanelData["scenarios"])
    readonly property string recommendedScenarioId: shellWindow ? String(shellRightPanelData["recommended_scenario_id"] || "--") : "--"
    readonly property var latestEventRow: shellWindow && shellWindow.statusRow ? DataUtils.objectOrEmpty(shellWindow.statusRow("最近事件")) : ({})
    readonly property string latestEventValue: String(latestEventRow["value"] || "--")
    readonly property string latestEventTone: String(latestEventRow["tone"] || "neutral")
    readonly property var heartbeatRow: shellWindow && shellWindow.statusRow ? DataUtils.objectOrEmpty(shellWindow.statusRow("心跳")) : ({})
    readonly property string heartbeatValue: String(heartbeatRow["value"] || "--")
    readonly property string heartbeatTone: String(heartbeatRow["tone"] || "neutral")
    readonly property real headingDeg: Number(kinematicsData["heading_deg"] || 0)
    readonly property bool compactCardLayout: shellWindow ? shellWindow.compactLayout : width < 920
    readonly property int metricColumns: compactCardLayout ? 1 : 4
    readonly property int mapInset: shellWindow ? shellWindow.scaled(24) : 24
    readonly property int stageDockMargin: shellWindow ? shellWindow.scaled(14) : 14
    readonly property int stageOverlayTopMargin: shellWindow ? shellWindow.scaled(66) : 66
    readonly property int stageProjectionBottomMargin: shellWindow ? shellWindow.scaled(86) : 86
    readonly property int stageConnectorSpan: shellWindow ? shellWindow.scaled(34) : 34
    readonly property int missionDeckWidth: shellWindow ? shellWindow.scaled(compactCardLayout ? 214 : 248) : 248
    readonly property int telemetryRailWidth: shellWindow ? shellWindow.scaled(236) : 236
    readonly property var currentPoint: trackPoint(Math.max(trackData.length - 1, 0))
    readonly property var originPoint: trackPoint(0)
    readonly property string sampleTimestamp: String(sampleData["captured_at"] || "采样时间未知")
    readonly property string sampleSequenceLabel: "SEQ " + String(sampleData["sequence"] || 0)
    readonly property string sampleTransportLabel: String(sampleData["transport"] || "--")
    readonly property string sampleProducerLabel: String(sampleData["producer_id"] || "--")
    readonly property real currentTrackAgeSec: Number(currentPoint["age_sec"] || 0)
    readonly property string trackAgeLabel: currentTrackAgeSec.toFixed(0) + " s"
    readonly property string lastJobLabel: String(controlSummary["last_job_id"] || "--")
    readonly property string missionModeLabel: hasRealTrack() ? "实时融合投影" : "合同镜像投影"
    readonly property string missionModeEnglish: hasRealTrack() ? "LIVE TRACK FUSION" : "CONTRACT MIRROR"
    readonly property string missionFocusLabel: wallboardStatusTone === "warning"
        ? "弱网、锚点与控制事件进入优先观测"
        : "航迹、热点和板端锚点保持统一主舞台"
    readonly property string stagePriorityLabel: wallboardStatusTone === "warning" ? "LINK WATCH" : "TRACK WATCH"
    readonly property string stagePriorityDetail: wallboardStatusTone === "warning"
        ? "弱网策略、在线锚点与控制事件进入前置监看。"
        : "航迹链、Fix 与采样心跳维持稳定主舞台。"
    readonly property string latitudeLabel: coordinateLabel(positionData["latitude"], "lat")
    readonly property string longitudeLabel: coordinateLabel(positionData["longitude"], "lon")
    readonly property string altitudeLabel: Number(kinematicsData["altitude_m"] || 0).toFixed(0) + " m"
    readonly property string speedLabel: Number(kinematicsData["ground_speed_kph"] || 0).toFixed(0) + " km/h"
    readonly property string climbLabel: signedMetric(kinematicsData["vertical_speed_mps"], 1, "m/s")
    readonly property string headingLabel: headingDeg.toFixed(1) + "°"
    readonly property string fixLabel: String(fixData["type"] || "--") + " / ±" + Number(fixData["confidence_m"] || 0).toFixed(1) + "m"
    readonly property string wallboardStatusTone: String(liveAnchorData["tone"] || (hasRealTrack() ? "online" : "neutral"))
    readonly property string wallboardStatusLabel: wallboardStatusTone === "warning"
        ? "链路重点监视"
        : (hasRealTrack() ? "投影稳定锁定" : "合同镜像模式")
    readonly property string wallboardStatusDetail: wallboardStatusTone === "warning"
        ? "弱网策略、在线锚点与控制事件已进入重点监看。"
        : (hasRealTrack()
            ? "真实航迹、热点弧线与采样心跳已经并入同一主舞台。"
            : "当前以前端合同镜像维持中心舞台，不推断不存在的实时链路。")
    readonly property var mapHudMetrics: [
        { "label": "定位 Fix", "value": fixLabel, "tone": "neutral" },
        { "label": "航向 Heading", "value": headingLabel, "tone": "warning" },
        { "label": "高度层", "value": altitudeLabel, "tone": "online" },
        { "label": "航迹链", "value": String(Number(trackData.length || 0).toFixed(0)) + " 节点", "tone": hasRealTrack() ? "online" : "neutral" }
    ]
    readonly property var railMetrics: [
        { "label": "ALT", "value": altitudeLabel, "detail": "高度层", "tone": "online" },
        { "label": "GS", "value": speedLabel, "detail": "地速", "tone": "neutral" },
        { "label": "VS", "value": climbLabel, "detail": "爬升率", "tone": "warning" },
        { "label": "SAT", "value": String(Number(fixData["satellites"] || 0).toFixed(0)), "detail": "卫星数", "tone": "neutral" }
    ]
    readonly property var missionRibbonModel: [
        {
            "label": "源",
            "value": root.sourceStatusLabel(),
            "tone": "neutral"
        },
        {
            "label": "锚点",
            "value": String(liveAnchorData["valid_instance"] || "--"),
            "tone": String(liveAnchorData["tone"] || "neutral")
        },
        {
            "label": "链路",
            "value": String(controlSummary["link_profile"] || "--"),
            "tone": "warning"
        },
        {
            "label": "心跳",
            "value": heartbeatValue,
            "tone": heartbeatTone
        }
    ]
    readonly property bool stageCommandShelfVisible: !compactCardLayout
        && width >= (missionDeckWidth + telemetryRailWidth + (shellWindow ? shellWindow.scaled(560) : 560))
    readonly property var theatreRibbonModel: [
        {
            "label": "锚点",
            "value": String(liveAnchorData["valid_instance"] || "--"),
            "tone": String(liveAnchorData["tone"] || "neutral")
        },
        {
            "label": "弱网",
            "value": recommendedScenarioId,
            "tone": "warning"
        },
        {
            "label": "采样",
            "value": sampleTimestamp.length > 22 ? sampleTimestamp.slice(0, 22) + "…" : sampleTimestamp,
            "tone": "neutral"
        },
        {
            "label": "事件",
            "value": latestEventValue,
            "tone": latestEventTone
        }
    ]
    readonly property var stageCommandShelfModel: [
        {
            "label": "SEQUENCE",
            "value": sampleSequenceLabel,
            "detail": "采样序列",
            "tone": "neutral"
        },
        {
            "label": "TRANSPORT",
            "value": compactMessage(sampleTransportLabel, "--", 18),
            "detail": "采样通道",
            "tone": "neutral"
        },
        {
            "label": "LAST JOB",
            "value": lastJobLabel,
            "detail": compactMessage(latestEventValue, "--", 18),
            "tone": latestEventTone
        },
        {
            "label": "FIX",
            "value": String(fixData["type"] || "--"),
            "detail": "±" + Number(fixData["confidence_m"] || 0).toFixed(1) + " m",
            "tone": currentTrackAgeSec <= 8 ? "online" : "warning"
        }
    ]
    readonly property var stageBannerModel: [
        {
            "label": "MODE",
            "value": missionModeEnglish,
            "detail": missionModeLabel,
            "tone": hasRealTrack() ? "online" : "neutral"
        },
        {
            "label": "TRACK AGE",
            "value": trackAgeLabel,
            "detail": "当前点年龄",
            "tone": currentTrackAgeSec <= 8 ? "online" : "warning"
        },
        {
            "label": "FIX RMS",
            "value": "±" + Number(fixData["confidence_m"] || 0).toFixed(1) + " m",
            "detail": String(fixData["type"] || "--"),
            "tone": "neutral"
        },
        {
            "label": "EVENT",
            "value": latestEventValue,
            "detail": compactMessage(controlSummary["last_event_message"], "当前没有额外控制消息。", 42),
            "tone": latestEventTone
        }
    ]
    readonly property var stageFloorModel: [
        {
            "label": "SOURCE",
            "value": compactMessage(root.sourceStatusLabel(), "--", 18),
            "detail": compactMessage(root.sourceLabel(), "合同镜像", 26),
            "tone": "neutral"
        },
        {
            "label": "PRIORITY",
            "value": stagePriorityLabel,
            "detail": compactMessage(stagePriorityDetail, "主舞台稳态", 28),
            "tone": wallboardStatusTone
        },
        {
            "label": "PRODUCER",
            "value": compactMessage(sampleProducerLabel, "--", 20),
            "detail": compactMessage(liveAnchorData["board_status"], sampleTimestamp, 26),
            "tone": String(liveAnchorData["tone"] || "neutral")
        }
    ]
    readonly property var watchlistModel: [
        {
            "label": "控制事件 / CONTROL EVENT",
            "value": latestEventValue,
            "detail": compactMessage(controlSummary["last_event_message"], "当前没有额外控制消息。", 78),
            "tone": latestEventTone
        },
        {
            "label": "弱网档位 / WEAK-LINK",
            "value": recommendedScenarioId,
            "detail": compactMessage(scenarioSummary(recommendedScenarioId), "弱网对照摘要暂不可用。", 78),
            "tone": "warning"
        },
        {
            "label": "板端锚点 / LIVE ANCHOR",
            "value": String(liveAnchorData["board_status"] || "--"),
            "detail": compactMessage(liveAnchorData["probe_summary"], "在线探板信息暂不可用。", 78),
            "tone": String(liveAnchorData["tone"] || "neutral")
        }
    ]
    readonly property var footerModel: [
        {
            "title": "坐标 / GEO POSITION",
            "value": "LAT " + Number(positionData["latitude"] || 0).toFixed(6) + "  LON " + Number(positionData["longitude"] || 0).toFixed(6),
            "detail": "航迹 " + String(Number(trackData.length || 0).toFixed(0)) + " 点 / 航向 " + headingLabel,
            "tone": "neutral"
        },
        {
            "title": "合同 / SOURCE",
            "value": root.sourceLabel(),
            "detail": root.sourceStatusLabel() + " / " + sampleTimestamp,
            "tone": "neutral"
        },
        {
            "title": "锚点 / LIVE",
            "value": String(liveAnchorData["label"] || "实时锚点未挂接"),
            "detail": String(liveAnchorData["board_status"] || "尚无在线锚点状态"),
            "tone": String(liveAnchorData["tone"] || "neutral")
        },
        {
            "title": "弱网 / NETWORK",
            "value": recommendedScenarioId,
            "detail": compactMessage(scenarioSummary(recommendedScenarioId), "沿用归档弱网报告中的真实对照结果。", 88),
            "tone": "warning"
        }
    ]
    readonly property int warningHotspotCount: hotspotCountByTone("warning")
    readonly property int onlineHotspotCount: hotspotCountByTone("online")
    readonly property string stageEnvelopeLabel: compactCardLayout ? "STACKED WALLBOARD BUS" : "TRIPLE RAIL WALLBOARD BUS"
    readonly property string stageEnvelopeStamp: "GRID " + String(sampleData["sequence"] || 0)
    readonly property var stageEnvelopeModel: [
        {
            "label": "WING-L",
            "value": "MISSION DECK",
            "detail": compactMessage(String(panel["mission_call_sign"] || "M9-DEMO"), "M9-DEMO", 18),
            "tone": "neutral"
        },
        {
            "label": "CORE",
            "value": stagePriorityLabel,
            "detail": compactMessage(stagePriorityDetail, "主舞台稳态", 24),
            "tone": wallboardStatusTone
        },
        {
            "label": "WING-R",
            "value": "TELEMETRY RAIL",
            "detail": compactMessage(String(liveAnchorData["board_status"] || sampleTimestamp), sampleTimestamp, 22),
            "tone": String(liveAnchorData["tone"] || "neutral")
        },
        {
            "label": "HOTSPOTS",
            "value": String(warningHotspotCount) + " WARN / " + String(wallboardHotspots.length) + " TOTAL",
            "detail": String(onlineHotspotCount) + " stable meshes",
            "tone": warningHotspotCount > 0 ? "warning" : "online"
        }
    ]
    readonly property var longitudeTicks: [-150, -90, -30, 30, 90, 150]
    readonly property var latitudeTicks: [60, 30, 0, -30, -60]
    readonly property var wallboardHotspots: [
        { "label": "北太平洋", "latitude": 35.0, "longitude": -150.0, "tone": "neutral", "intensity": 0.48 },
        { "label": "欧陆骨干", "latitude": 50.0, "longitude": 9.0, "tone": "online", "intensity": 0.72 },
        { "label": "阿拉伯海", "latitude": 23.0, "longitude": 64.0, "tone": "warning", "intensity": 0.58 },
        { "label": "华中汇聚", "latitude": 31.0, "longitude": 112.0, "tone": "online", "intensity": 1.0 },
        { "label": "南洋链路", "latitude": 3.0, "longitude": 104.0, "tone": "neutral", "intensity": 0.56 },
        { "label": "北大西洋", "latitude": 43.0, "longitude": -35.0, "tone": "warning", "intensity": 0.5 }
    ]

    implicitHeight: contentLayout.implicitHeight + ((shellWindow ? shellWindow.panelPadding : 18) * 2)

    function trackPoint(index) {
        var fallbackPoint = {
            "latitude": Number(positionData["latitude"] || 0),
            "longitude": Number(positionData["longitude"] || 0),
            "age_sec": 0
        }
        if (trackData.length === 0)
            return fallbackPoint
        return DataUtils.objectOrFallback(trackData[Math.max(0, Math.min(index, trackData.length - 1))], fallbackPoint)
    }

    function worldX(longitude, plotWidth) {
        var usableWidth = Math.max(1, plotWidth - (mapInset * 2))
        return mapInset + (((Number(longitude || 0) + 180) / 360) * usableWidth)
    }

    function worldY(latitude, plotHeight) {
        var usableHeight = Math.max(1, plotHeight - (mapInset * 2))
        return mapInset + (((90 - Number(latitude || 0)) / 180) * usableHeight)
    }

    function toneColor(tone) {
        if (shellWindow)
            return shellWindow.toneColor(tone)
        if (tone === "online")
            return "#42f0bc"
        if (tone === "warning")
            return "#ffbf52"
        if (tone === "danger")
            return "#ff7b7b"
        return "#38b6ff"
    }

    function toneFill(tone) {
        if (shellWindow)
            return shellWindow.toneFill(tone)
        if (tone === "online")
            return "#0d2c29"
        if (tone === "warning")
            return "#302311"
        if (tone === "danger")
            return "#321518"
        return "#0d2234"
    }

    function sourceLabel() {
        return String(feedContractData["active_source_label"] || panel["source_label"] || "Backend Stub Contract")
    }

    function sourceStatusLabel() {
        return String(panel["source_status"] || feedContractData["active_source_kind"] || "stub active")
    }

    function scenarioById(scenarioId) {
        for (var index = 0; index < weakNetworkScenarios.length; ++index) {
            var scenario = DataUtils.objectOrEmpty(weakNetworkScenarios[index])
            if (String(scenario["scenario_id"] || "") === String(scenarioId || ""))
                return scenario
        }
        return ({})
    }

    function scenarioSummary(scenarioId) {
        var scenario = scenarioById(scenarioId)
        return String(scenario["summary"] || scenario["operator_note"] || "")
    }

    function hotspotCountByTone(tone) {
        var total = 0
        for (var index = 0; index < wallboardHotspots.length; ++index) {
            var hotspot = DataUtils.objectOrEmpty(wallboardHotspots[index])
            if (String(hotspot["tone"] || "") === String(tone || ""))
                total += 1
        }
        return total
    }

    function hasRealTrack() {
        return trackData.length > 1
    }

    function compactMessage(text, fallback, limit) {
        var value = String(text || fallback || "")
        var maxLength = Math.max(18, Number(limit || 80))
        if (value.length <= maxLength)
            return value
        return value.slice(0, maxLength - 1) + "…"
    }

    function coordinateLabel(value, axis) {
        var amount = Number(value || 0)
        var suffix = axis === "lat"
            ? (amount >= 0 ? "N" : "S")
            : (amount >= 0 ? "E" : "W")
        return Math.abs(amount).toFixed(3) + "°" + suffix
    }

    function gridLatitudeLabel(value) {
        if (Number(value) === 0)
            return "EQ"
        return Math.abs(Number(value)).toFixed(0) + "°" + (Number(value) > 0 ? "N" : "S")
    }

    function gridLongitudeLabel(value) {
        return Math.abs(Number(value)).toFixed(0) + "°" + (Number(value) > 0 ? "E" : "W")
    }

    function signedMetric(value, precision, unit) {
        var amount = Number(value || 0)
        return (amount >= 0 ? "+" : "") + amount.toFixed(precision) + " " + unit
    }

    onTrackDataChanged: if (mapCanvas) mapCanvas.requestPaint()
    onHeadingDegChanged: if (mapCanvas) mapCanvas.requestPaint()
    onWidthChanged: if (mapCanvas) mapCanvas.requestPaint()
    onHeightChanged: if (mapCanvas) mapCanvas.requestPaint()

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

            Rectangle {
                Layout.fillWidth: true
                radius: shellWindow ? shellWindow.cardRadius : 14
                gradient: Gradient {
                    GradientStop { position: 0.0; color: "#123458" }
                    GradientStop { position: 0.55; color: "#0a1829" }
                    GradientStop { position: 1.0; color: "#07111d" }
                }
                border.color: "#2f8dcc"
                border.width: 1
                implicitHeight: heroColumn.implicitHeight + ((shellWindow ? shellWindow.cardPadding : 14) * 2)

                Rectangle {
                    width: parent.width * 0.38
                    height: parent.height * 0.9
                    radius: width / 2
                    color: "#49bbff"
                    opacity: 0.12
                    x: -width * 0.22
                    y: -height * 0.28
                }

                Rectangle {
                    anchors.fill: parent
                    anchors.margins: 1
                    radius: parent.radius - 1
                    color: "transparent"
                    border.color: "#133652"
                    border.width: 1
                    opacity: 0.82
                }

                Rectangle {
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.top: parent.top
                    height: shellWindow ? shellWindow.scaled(3) : 3
                    gradient: Gradient {
                        GradientStop { position: 0.0; color: "transparent" }
                        GradientStop { position: 0.22; color: root.accentBlue }
                        GradientStop { position: 0.72; color: root.accentCyan }
                        GradientStop { position: 1.0; color: "transparent" }
                    }
                    opacity: 0.78
                }

                Column {
                    id: heroColumn
                    anchors.fill: parent
                    anchors.margins: shellWindow ? shellWindow.cardPadding : 14
                    spacing: shellWindow ? shellWindow.compactGap : 8

                    Text {
                        text: panel["title"] || "航迹合同 / Aircraft Feed"
                        color: shellWindow ? shellWindow.accentBlue : "#38b6ff"
                        font.pixelSize: shellWindow ? shellWindow.eyebrowSize : 10
                        font.family: shellWindow ? shellWindow.monoFamily : "JetBrains Mono"
                        font.letterSpacing: shellWindow ? shellWindow.scaled(1) : 1
                    }

                    Text {
                        text: "全域防护态势墙"
                        color: shellWindow ? shellWindow.textStrong : "#f4fbff"
                        font.pixelSize: shellWindow ? shellWindow.sectionTitleSize : 24
                        font.bold: true
                        font.family: shellWindow ? shellWindow.displayFamily : "Noto Sans CJK SC"
                    }

                    Text {
                        text: "GLOBAL DEFENSE WALLBOARD"
                        color: shellWindow ? shellWindow.textSecondary : "#83acc8"
                        font.pixelSize: shellWindow ? shellWindow.captionSize : 11
                        font.family: shellWindow ? shellWindow.monoFamily : "JetBrains Mono"
                        font.letterSpacing: shellWindow ? shellWindow.scaled(1) : 1
                    }

                    Text {
                        width: parent.width
                        text: "沿用既有飞机合同作为唯一事实源，把中心区推向安全运营主舞台风格，集中呈现机位、链路、热点弧线与采样心跳。"
                        color: shellWindow ? shellWindow.textSecondary : "#83acc8"
                        font.pixelSize: shellWindow ? shellWindow.bodySize : 13
                        font.family: shellWindow ? shellWindow.uiFamily : "Noto Sans CJK SC"
                        wrapMode: Text.WordWrap
                    }

                    Flow {
                        width: parent.width
                        spacing: shellWindow ? shellWindow.compactGap : 8

                        Repeater {
                            model: [
                                {
                                    "label": "任务呼号",
                                    "value": String(panel["mission_call_sign"] || "M9-DEMO"),
                                    "tone": "online"
                                },
                                {
                                    "label": "机体编号",
                                    "value": String(panel["aircraft_id"] || "FT-AIR-01"),
                                    "tone": "neutral"
                                },
                                {
                                    "label": "链路档位",
                                    "value": String(controlSummary["link_profile"] || "--"),
                                    "tone": "warning"
                                },
                                {
                                    "label": "航迹留痕",
                                    "value": String(Number(trackData.length || 0).toFixed(0)) + " 点",
                                    "tone": hasRealTrack() ? "online" : "neutral"
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
                                width: Math.max(shellWindow ? shellWindow.scaled(152) : 152, chipColumn.implicitWidth + (shellWindow ? shellWindow.scaled(24) : 24))

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
                                        font.family: shellWindow ? shellWindow.uiFamily : "Noto Sans CJK SC"
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
            }

            Rectangle {
                Layout.fillWidth: true
                radius: shellWindow ? shellWindow.cardRadius : 14
                gradient: Gradient {
                    GradientStop { position: 0.0; color: "#0d2237" }
                    GradientStop { position: 1.0; color: "#07131f" }
                }
                border.color: "#2f78aa"
                border.width: 1
                implicitHeight: feedColumn.implicitHeight + ((shellWindow ? shellWindow.cardPadding : 14) * 2)

                Rectangle {
                    anchors.fill: parent
                    anchors.margins: 1
                    radius: parent.radius - 1
                    color: "transparent"
                    border.color: "#133550"
                    border.width: 1
                    opacity: 0.82
                }

                Rectangle {
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.top: parent.top
                    height: shellWindow ? shellWindow.scaled(3) : 3
                    gradient: Gradient {
                        GradientStop { position: 0.0; color: "transparent" }
                        GradientStop { position: 0.22; color: root.accentBlue }
                        GradientStop { position: 0.72; color: root.accentCyan }
                        GradientStop { position: 1.0; color: "transparent" }
                    }
                    opacity: 0.74
                }

                Column {
                    id: feedColumn
                    anchors.fill: parent
                    anchors.margins: shellWindow ? shellWindow.cardPadding : 14
                    spacing: shellWindow ? shellWindow.scaled(5) : 5

                    Text {
                        text: "数据源镜像 / Source Mirror"
                        color: shellWindow ? shellWindow.accentCyan : "#72f3ff"
                        font.pixelSize: shellWindow ? shellWindow.captionSize : 11
                        font.family: shellWindow ? shellWindow.monoFamily : "JetBrains Mono"
                    }

                    Text {
                        width: parent.width
                        text: root.sourceLabel()
                        color: shellWindow ? shellWindow.textStrong : "#f4fbff"
                        font.pixelSize: shellWindow ? shellWindow.bodyEmphasisSize : 15
                        font.bold: true
                        font.family: shellWindow ? shellWindow.uiFamily : "Noto Sans CJK SC"
                        wrapMode: Text.WordWrap
                    }

                    Text {
                        width: parent.width
                        text: "状态 " + root.sourceStatusLabel()
                        color: shellWindow ? shellWindow.textPrimary : "#d5eeff"
                        font.pixelSize: shellWindow ? shellWindow.captionSize : 11
                        font.family: shellWindow ? shellWindow.monoFamily : "JetBrains Mono"
                        wrapMode: Text.WordWrap
                    }

                    Text {
                        width: parent.width
                        text: String(feedContractData["summary"] || panel["ownership_note"] || "")
                        color: shellWindow ? shellWindow.textSecondary : "#83acc8"
                        font.pixelSize: shellWindow ? shellWindow.bodySize : 13
                        font.family: shellWindow ? shellWindow.uiFamily : "Noto Sans CJK SC"
                        wrapMode: Text.WordWrap
                    }

                    Rectangle {
                        width: parent.width
                        radius: shellWindow ? shellWindow.edgeRadius : 10
                        color: "#081320"
                        border.color: "#18486d"
                        border.width: 1
                        implicitHeight: apiColumn.implicitHeight + ((shellWindow ? shellWindow.scaled(10) : 10) * 2)

                        Column {
                            id: apiColumn
                            anchors.fill: parent
                            anchors.margins: shellWindow ? shellWindow.scaled(10) : 10
                            spacing: shellWindow ? shellWindow.scaled(3) : 3

                            Text {
                                text: "API PATH / 合同入口"
                                color: shellWindow ? shellWindow.textMuted : "#4e7392"
                                font.pixelSize: shellWindow ? shellWindow.captionSize : 11
                                font.family: shellWindow ? shellWindow.monoFamily : "JetBrains Mono"
                            }

                            Text {
                                width: parent.width
                                text: String(panel["source_api_path"] || feedContractData["api_path"] || "")
                                color: shellWindow ? shellWindow.textPrimary : "#d5eeff"
                                font.pixelSize: shellWindow ? shellWindow.captionSize : 11
                                font.family: shellWindow ? shellWindow.monoFamily : "JetBrains Mono"
                                wrapMode: Text.WrapAnywhere
                            }
                        }
                    }
                }
            }
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.minimumHeight: shellWindow ? shellWindow.scaled(compactCardLayout ? 388 : 492) : 492
            radius: shellWindow ? shellWindow.cardRadius : 14
            gradient: Gradient {
                GradientStop { position: 0.0; color: "#0d2840" }
                GradientStop { position: 0.36; color: "#081523" }
                GradientStop { position: 1.0; color: "#040a13" }
            }
            border.color: "#3295d6"
            border.width: 1

            Rectangle {
                anchors.fill: parent
                anchors.margins: 1
                radius: parent.radius - 1
                color: "transparent"
                border.color: "#143753"
                border.width: 1
                opacity: 0.86
            }

            Rectangle {
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                height: shellWindow ? shellWindow.scaled(3) : 3
                gradient: Gradient {
                    GradientStop { position: 0.0; color: "transparent" }
                    GradientStop { position: 0.22; color: root.accentBlue }
                    GradientStop { position: 0.72; color: root.accentCyan }
                    GradientStop { position: 1.0; color: "transparent" }
                }
                opacity: 0.8
            }

            Rectangle {
                width: parent.width * 0.44
                height: parent.height * 0.9
                radius: width / 2
                color: "#37a9f2"
                opacity: 0.08
                x: -width * 0.2
                y: -height * 0.12
            }

            Rectangle {
                width: parent.width * 0.48
                height: parent.height * 0.72
                radius: width / 2
                color: "#72f3ff"
                opacity: 0.06
                x: parent.width - (width * 0.8)
                y: parent.height * 0.18
            }

            ColumnLayout {
                id: mapLayout
                anchors.fill: parent
                anchors.margins: shellWindow ? shellWindow.cardPadding : 14
                spacing: shellWindow ? shellWindow.compactGap : 8

                RowLayout {
                    Layout.fillWidth: true
                    spacing: shellWindow ? shellWindow.zoneGap : 12

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: shellWindow ? shellWindow.scaled(2) : 2

                        Text {
                            text: "GLOBAL SECURITY WALLBOARD"
                            color: shellWindow ? shellWindow.accentBlue : "#38b6ff"
                            font.pixelSize: shellWindow ? shellWindow.captionSize : 11
                            font.family: shellWindow ? shellWindow.monoFamily : "JetBrains Mono"
                            font.letterSpacing: shellWindow ? shellWindow.scaled(1) : 1
                        }

                        Text {
                            text: "全球防护网投影"
                            color: shellWindow ? shellWindow.textStrong : "#f4fbff"
                            font.pixelSize: shellWindow ? shellWindow.sectionTitleSize : 24
                            font.bold: true
                            font.family: shellWindow ? shellWindow.displayFamily : "Noto Sans CJK SC"
                        }

                        Text {
                            text: "以 DDoS / 安全运营主舞台的层次组织中心视野，把真实机位、弱网档位、在线锚点、控制事件与采样时钟收敛到同一投影。"
                            color: shellWindow ? shellWindow.textSecondary : "#83acc8"
                            font.pixelSize: shellWindow ? shellWindow.bodySize : 13
                            font.family: shellWindow ? shellWindow.uiFamily : "Noto Sans CJK SC"
                            wrapMode: Text.WordWrap
                        }
                    }

                    Rectangle {
                        radius: shellWindow ? shellWindow.edgeRadius : 10
                        gradient: Gradient {
                            GradientStop { position: 0.0; color: Qt.lighter(root.toneFill(root.wallboardStatusTone), 1.12) }
                            GradientStop { position: 1.0; color: root.toneFill(root.wallboardStatusTone) }
                        }
                        border.color: root.toneColor(root.wallboardStatusTone)
                        border.width: 1
                        implicitWidth: statusColumn.implicitWidth + ((shellWindow ? shellWindow.scaled(16) : 16) * 2)
                        implicitHeight: statusColumn.implicitHeight + ((shellWindow ? shellWindow.scaled(10) : 10) * 2)

                        Column {
                            id: statusColumn
                            anchors.centerIn: parent
                            spacing: shellWindow ? shellWindow.scaled(3) : 3

                            Text {
                                text: "态势状态 / WALLBOARD STATUS"
                                color: shellWindow ? shellWindow.textMuted : "#4e7392"
                                font.pixelSize: shellWindow ? shellWindow.captionSize : 11
                                font.family: shellWindow ? shellWindow.monoFamily : "JetBrains Mono"
                            }

                            Text {
                                text: root.wallboardStatusLabel
                                color: shellWindow ? shellWindow.textStrong : "#f4fbff"
                                font.pixelSize: shellWindow ? shellWindow.bodySize : 13
                                font.bold: true
                                font.family: shellWindow ? shellWindow.uiFamily : "Noto Sans CJK SC"
                            }

                            Text {
                                text: root.wallboardStatusDetail
                                color: shellWindow ? shellWindow.textSecondary : "#83acc8"
                                font.pixelSize: shellWindow ? shellWindow.captionSize : 11
                                font.family: shellWindow ? shellWindow.uiFamily : "Noto Sans CJK SC"
                                wrapMode: Text.WordWrap
                            }

                            Text {
                                text: "SAMPLE  " + root.sampleTimestamp
                                color: shellWindow ? shellWindow.textPrimary : "#d5eeff"
                                font.pixelSize: shellWindow ? shellWindow.captionSize : 11
                                font.family: shellWindow ? shellWindow.monoFamily : "JetBrains Mono"
                            }
                        }
                    }
                }

                Flow {
                    Layout.fillWidth: true
                    spacing: shellWindow ? shellWindow.compactGap : 8

                    Repeater {
                        model: root.mapHudMetrics

                            delegate: Rectangle {
                                readonly property var chip: modelData
                                radius: shellWindow ? shellWindow.edgeRadius : 10
                                gradient: Gradient {
                                    GradientStop { position: 0.0; color: Qt.lighter(root.toneFill(chip["tone"]), 1.14) }
                                    GradientStop { position: 1.0; color: root.toneFill(chip["tone"]) }
                                }
                                border.color: root.toneColor(chip["tone"])
                                border.width: 1
                                height: hudChipColumn.implicitHeight + ((shellWindow ? shellWindow.scaled(9) : 9) * 2)
                                width: Math.max(shellWindow ? shellWindow.scaled(148) : 148, hudChipColumn.implicitWidth + (shellWindow ? shellWindow.scaled(22) : 22))

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
                                    opacity: 0.72
                                }

                                Column {
                                    id: hudChipColumn
                                    anchors.centerIn: parent
                                    spacing: shellWindow ? shellWindow.scaled(2) : 2

                                    Text {
                                        text: chip["label"]
                                        color: shellWindow ? shellWindow.textMuted : "#4e7392"
                                        font.pixelSize: shellWindow ? shellWindow.captionSize : 11
                                        font.family: shellWindow ? shellWindow.uiFamily : "Noto Sans CJK SC"
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

                Flow {
                    Layout.fillWidth: true
                    spacing: shellWindow ? shellWindow.compactGap : 8

                    Repeater {
                        model: root.missionRibbonModel

                        delegate: Rectangle {
                            readonly property var itemData: modelData
                            radius: shellWindow ? shellWindow.edgeRadius : 10
                            gradient: Gradient {
                                GradientStop { position: 0.0; color: "#0f2335" }
                                GradientStop { position: 1.0; color: "#091522" }
                            }
                            border.color: root.toneColor(itemData["tone"])
                            border.width: 1
                            height: ribbonColumn.implicitHeight + ((shellWindow ? shellWindow.scaled(8) : 8) * 2)
                            width: Math.max(shellWindow ? shellWindow.scaled(156) : 156, ribbonColumn.implicitWidth + (shellWindow ? shellWindow.scaled(24) : 24))

                            Rectangle {
                                anchors.left: parent.left
                                anchors.right: parent.right
                                anchors.top: parent.top
                                height: shellWindow ? shellWindow.scaled(2) : 2
                                gradient: Gradient {
                                    GradientStop { position: 0.0; color: "transparent" }
                                    GradientStop { position: 0.28; color: root.toneColor(itemData["tone"]) }
                                    GradientStop { position: 0.72; color: Qt.lighter(root.toneColor(itemData["tone"]), 1.16) }
                                    GradientStop { position: 1.0; color: "transparent" }
                                }
                                opacity: 0.74
                            }

                            Column {
                                id: ribbonColumn
                                anchors.centerIn: parent
                                spacing: shellWindow ? shellWindow.scaled(2) : 2

                                Text {
                                    text: itemData["label"]
                                    color: shellWindow ? shellWindow.textMuted : "#4e7392"
                                    font.pixelSize: shellWindow ? shellWindow.captionSize : 10
                                    font.family: shellWindow ? shellWindow.monoFamily : "JetBrains Mono"
                                    font.letterSpacing: shellWindow ? shellWindow.scaled(1) : 1
                                }

                                Text {
                                    text: itemData["value"]
                                    color: shellWindow ? shellWindow.textPrimary : "#d5eeff"
                                    font.pixelSize: shellWindow ? shellWindow.captionSize : 11
                                    font.bold: true
                                    font.family: shellWindow ? shellWindow.monoFamily : "JetBrains Mono"
                                }
                            }
                        }
                    }
                }

                Item {
                    id: mapStage
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    implicitHeight: shellWindow ? shellWindow.scaled(compactCardLayout ? 338 : 410) : 410
                    clip: true

                    Rectangle {
                        anchors.fill: parent
                        radius: shellWindow ? shellWindow.cardRadius : 14
                        gradient: Gradient {
                            GradientStop { position: 0.0; color: "#030912" }
                            GradientStop { position: 0.42; color: "#05111d" }
                            GradientStop { position: 1.0; color: "#02070e" }
                        }
                    }

                    Rectangle {
                        anchors.fill: parent
                        radius: shellWindow ? shellWindow.cardRadius : 14
                        color: "transparent"
                        border.color: "#1b4c75"
                        border.width: 1
                    }

                    Rectangle {
                        anchors.fill: parent
                        anchors.margins: shellWindow ? shellWindow.scaled(8) : 8
                        radius: Math.max(2, (shellWindow ? shellWindow.cardRadius : 14) - (shellWindow ? shellWindow.scaled(8) : 8))
                        color: "transparent"
                        border.color: "#0d304d"
                        border.width: 1
                        opacity: 0.82
                    }

                    Rectangle {
                        anchors.fill: parent
                        anchors.margins: shellWindow ? shellWindow.scaled(18) : 18
                        radius: Math.max(2, (shellWindow ? shellWindow.cardRadius : 14) - (shellWindow ? shellWindow.scaled(18) : 18))
                        color: "transparent"
                        border.color: "#123551"
                        border.width: 1
                        opacity: 0.38
                    }

                    Rectangle {
                        width: parent.width * 0.7
                        height: width
                        radius: width / 2
                        color: "#0f446d"
                        opacity: 0.16
                        anchors.centerIn: parent
                    }

                    Rectangle {
                        width: parent.width * 0.4
                        height: parent.height * 0.68
                        radius: width / 2
                        color: "#31b2ff"
                        opacity: 0.08
                        x: -width * 0.12
                        y: parent.height * 0.12
                    }

                    Rectangle {
                        width: parent.width * 1.08
                        height: parent.height * 0.18
                        rotation: -6
                        color: "#123957"
                        opacity: 0.1
                        x: -parent.width * 0.04
                        y: parent.height * 0.46
                    }

                    Rectangle {
                        anchors.left: parent.left
                        anchors.top: parent.top
                        anchors.bottom: parent.bottom
                        anchors.margins: shellWindow ? shellWindow.scaled(14) : 14
                        width: shellWindow ? shellWindow.scaled(4) : 4
                        radius: width / 2
                        gradient: Gradient {
                            GradientStop { position: 0.0; color: "transparent" }
                            GradientStop { position: 0.2; color: "#2fa2e6" }
                            GradientStop { position: 0.82; color: "#164b6f" }
                            GradientStop { position: 1.0; color: "transparent" }
                        }
                        opacity: 0.22
                    }

                    Rectangle {
                        anchors.right: parent.right
                        anchors.top: parent.top
                        anchors.bottom: parent.bottom
                        anchors.margins: shellWindow ? shellWindow.scaled(14) : 14
                        width: 1
                        color: "#67d6ff"
                        opacity: 0.16
                    }

                    Rectangle {
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.top: parent.top
                        height: shellWindow ? shellWindow.scaled(72) : 72
                        gradient: Gradient {
                            GradientStop { position: 0.0; color: "#11294366" }
                            GradientStop { position: 0.58; color: "#08152220" }
                            GradientStop { position: 1.0; color: "#04080d00" }
                        }
                        opacity: 0.94
                    }

                    Rectangle {
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.bottom: parent.bottom
                        height: shellWindow ? shellWindow.scaled(96) : 96
                        gradient: Gradient {
                            GradientStop { position: 0.0; color: "#04080d00" }
                            GradientStop { position: 0.46; color: "#08142140" }
                            GradientStop { position: 1.0; color: "#0815227a" }
                        }
                        opacity: 0.96
                    }

                    Rectangle {
                        id: leftDockLane
                        visible: !compactCardLayout
                        anchors.left: parent.left
                        anchors.top: parent.top
                        anchors.bottom: footerAuditRail.top
                        anchors.leftMargin: root.stageDockMargin
                        anchors.topMargin: root.stageOverlayTopMargin - (shellWindow ? shellWindow.scaled(18) : 18)
                        anchors.bottomMargin: shellWindow ? shellWindow.scaled(18) : 18
                        width: missionDeckCard.width + (shellWindow ? shellWindow.scaled(28) : 28)
                        radius: shellWindow ? shellWindow.cardRadius : 14
                        gradient: Gradient {
                            GradientStop { position: 0.0; color: "#11273b" }
                            GradientStop { position: 0.48; color: "#0b1725" }
                            GradientStop { position: 1.0; color: "#07111d" }
                        }
                        border.color: "#143754"
                        border.width: 1
                        opacity: 0.72

                        Rectangle {
                            anchors.fill: parent
                            anchors.margins: 1
                            radius: parent.radius - 1
                            color: "transparent"
                            border.color: "#102b42"
                            border.width: 1
                            opacity: 0.84
                        }

                        Rectangle {
                            anchors.left: parent.left
                            anchors.top: parent.top
                            anchors.bottom: parent.bottom
                            width: shellWindow ? shellWindow.scaled(4) : 4
                            radius: width / 2
                            gradient: Gradient {
                                GradientStop { position: 0.0; color: "transparent" }
                                GradientStop { position: 0.18; color: root.accentBlue }
                                GradientStop { position: 0.76; color: root.accentCyan }
                                GradientStop { position: 1.0; color: "transparent" }
                            }
                            opacity: 0.58
                        }

                        Rectangle {
                            anchors.left: parent.left
                            anchors.right: parent.right
                            anchors.top: parent.top
                            height: shellWindow ? shellWindow.scaled(3) : 3
                            gradient: Gradient {
                                GradientStop { position: 0.0; color: "transparent" }
                                GradientStop { position: 0.22; color: root.accentBlue }
                                GradientStop { position: 0.68; color: root.accentCyan }
                                GradientStop { position: 1.0; color: "transparent" }
                            }
                            opacity: 0.52
                        }

                        Column {
                            anchors.left: parent.left
                            anchors.top: parent.top
                            anchors.leftMargin: shellWindow ? shellWindow.scaled(12) : 12
                            anchors.topMargin: shellWindow ? shellWindow.scaled(12) : 12
                            spacing: 1

                            Text {
                                text: "LEFT COMMAND RAIL"
                                color: shellWindow ? shellWindow.accentBlue : "#38b6ff"
                                font.pixelSize: shellWindow ? shellWindow.captionSize : 10
                                font.family: shellWindow ? shellWindow.monoFamily : "JetBrains Mono"
                                font.letterSpacing: shellWindow ? shellWindow.scaled(1) : 1
                            }

                            Text {
                                text: "Deck / control bus"
                                color: shellWindow ? shellWindow.textMuted : "#4e7392"
                                font.pixelSize: shellWindow ? shellWindow.captionSize : 10
                                font.family: shellWindow ? shellWindow.uiFamily : "Noto Sans CJK SC"
                            }
                        }

                        Column {
                            anchors.left: parent.left
                            anchors.bottom: leftLaneBadge.top
                            anchors.leftMargin: shellWindow ? shellWindow.scaled(12) : 12
                            anchors.bottomMargin: shellWindow ? shellWindow.scaled(8) : 8
                            spacing: shellWindow ? shellWindow.scaled(6) : 6

                            Repeater {
                                model: 4

                                delegate: Rectangle {
                                    width: shellWindow ? shellWindow.scaled(index === 0 ? 8 : 6) : (index === 0 ? 8 : 6)
                                    height: width
                                    radius: width / 2
                                    color: index === 0 ? root.accentBlue : "#1d547c"
                                    border.color: index === 0 ? "#ffffff" : "transparent"
                                    border.width: index === 0 ? 1 : 0
                                    opacity: index === 0 ? 0.92 : (0.52 - (index * 0.08))
                                }
                            }
                        }

                        Rectangle {
                            id: leftLaneBadge
                            anchors.left: parent.left
                            anchors.bottom: parent.bottom
                            anchors.leftMargin: shellWindow ? shellWindow.scaled(12) : 12
                            anchors.bottomMargin: shellWindow ? shellWindow.scaled(12) : 12
                            radius: shellWindow ? shellWindow.edgeRadius : 10
                            color: "#091726"
                            border.color: "#1d547c"
                            border.width: 1
                            implicitWidth: leftLaneStamp.implicitWidth + ((shellWindow ? shellWindow.scaled(10) : 10) * 2)
                            implicitHeight: leftLaneStamp.implicitHeight + ((shellWindow ? shellWindow.scaled(5) : 5) * 2)

                            Text {
                                id: leftLaneStamp
                                anchors.centerIn: parent
                                text: "BUS-L / MISSION"
                                color: shellWindow ? shellWindow.textPrimary : "#d5eeff"
                                font.pixelSize: shellWindow ? shellWindow.captionSize : 9
                                font.family: shellWindow ? shellWindow.monoFamily : "JetBrains Mono"
                            }
                        }

                        Repeater {
                            model: 6

                            delegate: Rectangle {
                                width: leftDockLane.width - ((shellWindow ? shellWindow.scaled(18) : 18) * 2)
                                height: 1
                                x: shellWindow ? shellWindow.scaled(14) : 14
                                y: (shellWindow ? shellWindow.scaled(60) : 60) + index * ((leftDockLane.height - (shellWindow ? shellWindow.scaled(110) : 110)) / Math.max(1, model - 1))
                                color: index % 2 === 0 ? "#1a496d" : "#10304a"
                                opacity: index === 0 || index === model - 1 ? 0.4 : 0.22
                            }
                        }
                    }

                    Rectangle {
                        id: rightDockLane
                        visible: !compactCardLayout
                        anchors.right: parent.right
                        anchors.top: parent.top
                        anchors.bottom: footerAuditRail.top
                        anchors.rightMargin: root.stageDockMargin
                        anchors.topMargin: root.stageOverlayTopMargin - (shellWindow ? shellWindow.scaled(18) : 18)
                        anchors.bottomMargin: shellWindow ? shellWindow.scaled(18) : 18
                        width: telemetryRailCard.width + (shellWindow ? shellWindow.scaled(28) : 28)
                        radius: shellWindow ? shellWindow.cardRadius : 14
                        gradient: Gradient {
                            GradientStop { position: 0.0; color: "#102538" }
                            GradientStop { position: 0.5; color: "#0a1725" }
                            GradientStop { position: 1.0; color: "#07111d" }
                        }
                        border.color: "#143754"
                        border.width: 1
                        opacity: 0.72

                        Rectangle {
                            anchors.fill: parent
                            anchors.margins: 1
                            radius: parent.radius - 1
                            color: "transparent"
                            border.color: "#102b42"
                            border.width: 1
                            opacity: 0.84
                        }

                        Rectangle {
                            anchors.right: parent.right
                            anchors.top: parent.top
                            anchors.bottom: parent.bottom
                            width: shellWindow ? shellWindow.scaled(4) : 4
                            radius: width / 2
                            gradient: Gradient {
                                GradientStop { position: 0.0; color: "transparent" }
                                GradientStop { position: 0.18; color: root.accentBlue }
                                GradientStop { position: 0.76; color: root.accentCyan }
                                GradientStop { position: 1.0; color: "transparent" }
                            }
                            opacity: 0.58
                        }

                        Rectangle {
                            anchors.left: parent.left
                            anchors.right: parent.right
                            anchors.top: parent.top
                            height: shellWindow ? shellWindow.scaled(3) : 3
                            gradient: Gradient {
                                GradientStop { position: 0.0; color: "transparent" }
                                GradientStop { position: 0.22; color: root.accentBlue }
                                GradientStop { position: 0.68; color: root.accentCyan }
                                GradientStop { position: 1.0; color: "transparent" }
                            }
                            opacity: 0.52
                        }

                        Column {
                            anchors.right: parent.right
                            anchors.top: parent.top
                            anchors.rightMargin: shellWindow ? shellWindow.scaled(12) : 12
                            anchors.topMargin: shellWindow ? shellWindow.scaled(12) : 12
                            spacing: 1

                            Text {
                                text: "RIGHT TELEMETRY RAIL"
                                color: shellWindow ? shellWindow.accentCyan : "#72f3ff"
                                font.pixelSize: shellWindow ? shellWindow.captionSize : 10
                                font.family: shellWindow ? shellWindow.monoFamily : "JetBrains Mono"
                                font.letterSpacing: shellWindow ? shellWindow.scaled(1) : 1
                            }

                            Text {
                                text: "Telemetry / watchlist"
                                color: shellWindow ? shellWindow.textMuted : "#4e7392"
                                font.pixelSize: shellWindow ? shellWindow.captionSize : 10
                                font.family: shellWindow ? shellWindow.uiFamily : "Noto Sans CJK SC"
                                horizontalAlignment: Text.AlignRight
                            }
                        }

                        Column {
                            anchors.right: parent.right
                            anchors.bottom: rightLaneBadge.top
                            anchors.rightMargin: shellWindow ? shellWindow.scaled(12) : 12
                            anchors.bottomMargin: shellWindow ? shellWindow.scaled(8) : 8
                            spacing: shellWindow ? shellWindow.scaled(6) : 6

                            Repeater {
                                model: 4

                                delegate: Rectangle {
                                    width: shellWindow ? shellWindow.scaled(index === 0 ? 8 : 6) : (index === 0 ? 8 : 6)
                                    height: width
                                    radius: width / 2
                                    color: index === 0 ? root.accentCyan : "#1d547c"
                                    border.color: index === 0 ? "#ffffff" : "transparent"
                                    border.width: index === 0 ? 1 : 0
                                    opacity: index === 0 ? 0.92 : (0.52 - (index * 0.08))
                                }
                            }
                        }

                        Rectangle {
                            id: rightLaneBadge
                            anchors.right: parent.right
                            anchors.bottom: parent.bottom
                            anchors.rightMargin: shellWindow ? shellWindow.scaled(12) : 12
                            anchors.bottomMargin: shellWindow ? shellWindow.scaled(12) : 12
                            radius: shellWindow ? shellWindow.edgeRadius : 10
                            color: "#091726"
                            border.color: "#1d547c"
                            border.width: 1
                            implicitWidth: rightLaneStamp.implicitWidth + ((shellWindow ? shellWindow.scaled(10) : 10) * 2)
                            implicitHeight: rightLaneStamp.implicitHeight + ((shellWindow ? shellWindow.scaled(5) : 5) * 2)

                            Text {
                                id: rightLaneStamp
                                anchors.centerIn: parent
                                text: "BUS-R / WATCH"
                                color: shellWindow ? shellWindow.textPrimary : "#d5eeff"
                                font.pixelSize: shellWindow ? shellWindow.captionSize : 9
                                font.family: shellWindow ? shellWindow.monoFamily : "JetBrains Mono"
                            }
                        }

                        Repeater {
                            model: 6

                            delegate: Rectangle {
                                width: rightDockLane.width - ((shellWindow ? shellWindow.scaled(18) : 18) * 2)
                                height: 1
                                x: shellWindow ? shellWindow.scaled(14) : 14
                                y: (shellWindow ? shellWindow.scaled(60) : 60) + index * ((rightDockLane.height - (shellWindow ? shellWindow.scaled(110) : 110)) / Math.max(1, model - 1))
                                color: index % 2 === 0 ? "#1a496d" : "#10304a"
                                opacity: index === 0 || index === model - 1 ? 0.4 : 0.22
                            }
                        }
                    }

                    Rectangle {
                        id: lowerDockLane
                        visible: !compactCardLayout
                        anchors.left: leftDockLane.right
                        anchors.right: rightDockLane.left
                        anchors.leftMargin: shellWindow ? shellWindow.scaled(18) : 18
                        anchors.rightMargin: shellWindow ? shellWindow.scaled(18) : 18
                        anchors.bottom: parent.bottom
                        anchors.bottomMargin: root.stageDockMargin
                        height: shellWindow ? shellWindow.scaled(176) : 176
                        radius: shellWindow ? shellWindow.cardRadius : 14
                        gradient: Gradient {
                            GradientStop { position: 0.0; color: "#0e2234" }
                            GradientStop { position: 0.46; color: "#091421" }
                            GradientStop { position: 1.0; color: "#071019" }
                        }
                        border.color: "#123451"
                        border.width: 1
                        opacity: 0.66

                        Rectangle {
                            anchors.fill: parent
                            anchors.margins: 1
                            radius: parent.radius - 1
                            color: "transparent"
                            border.color: "#0f2a41"
                            border.width: 1
                            opacity: 0.82
                        }

                        Rectangle {
                            anchors.left: parent.left
                            anchors.right: parent.right
                            anchors.top: parent.top
                            height: shellWindow ? shellWindow.scaled(3) : 3
                            gradient: Gradient {
                                GradientStop { position: 0.0; color: "transparent" }
                                GradientStop { position: 0.24; color: root.accentBlue }
                                GradientStop { position: 0.74; color: root.accentCyan }
                                GradientStop { position: 1.0; color: "transparent" }
                            }
                            opacity: 0.5
                        }

                        RowLayout {
                            anchors.left: parent.left
                            anchors.right: parent.right
                            anchors.top: parent.top
                            anchors.margins: shellWindow ? shellWindow.scaled(12) : 12
                            spacing: shellWindow ? shellWindow.compactGap : 8

                            Text {
                                Layout.fillWidth: true
                                text: "FLOOR BUS / SOURCE + ALERT"
                                color: shellWindow ? shellWindow.accentBlue : "#38b6ff"
                                font.pixelSize: shellWindow ? shellWindow.captionSize : 10
                                font.family: shellWindow ? shellWindow.monoFamily : "JetBrains Mono"
                                font.letterSpacing: shellWindow ? shellWindow.scaled(1) : 1
                            }

                            Text {
                                text: String(Number(root.trackData.length || 0).toFixed(0)) + " nodes"
                                color: shellWindow ? shellWindow.textMuted : "#4e7392"
                                font.pixelSize: shellWindow ? shellWindow.captionSize : 10
                                font.family: shellWindow ? shellWindow.monoFamily : "JetBrains Mono"
                            }
                        }

                        Flow {
                            id: floorBusFlow
                            z: 1
                            property real cardWidth: Math.max(
                                shellWindow ? shellWindow.scaled(88) : 88,
                                (width - ((root.stageFloorModel.length - 1) * (shellWindow ? shellWindow.compactGap : 8))) / Math.max(1, root.stageFloorModel.length)
                            )
                            anchors.left: parent.left
                            anchors.right: parent.right
                            anchors.top: parent.top
                            anchors.leftMargin: shellWindow ? shellWindow.scaled(12) : 12
                            anchors.rightMargin: shellWindow ? shellWindow.scaled(12) : 12
                            anchors.topMargin: shellWindow ? shellWindow.scaled(48) : 48
                            spacing: shellWindow ? shellWindow.compactGap : 8

                            Repeater {
                                model: root.stageFloorModel

                                delegate: Rectangle {
                                    readonly property var busItem: modelData
                                    width: floorBusFlow.cardWidth
                                    radius: shellWindow ? shellWindow.edgeRadius : 10
                                    gradient: Gradient {
                                        GradientStop { position: 0.0; color: Qt.lighter(root.toneFill(busItem["tone"]), 1.14) }
                                        GradientStop { position: 1.0; color: root.toneFill(busItem["tone"]) }
                                    }
                                    border.color: root.toneColor(busItem["tone"])
                                    border.width: 1
                                    implicitHeight: busColumn.implicitHeight + ((shellWindow ? shellWindow.scaled(7) : 7) * 2)

                                    Column {
                                        id: busColumn
                                        anchors.fill: parent
                                        anchors.margins: shellWindow ? shellWindow.scaled(7) : 7
                                        spacing: 1

                                        Text {
                                            text: busItem["label"]
                                            color: shellWindow ? shellWindow.textMuted : "#4e7392"
                                            font.pixelSize: shellWindow ? shellWindow.captionSize : 9
                                            font.family: shellWindow ? shellWindow.monoFamily : "JetBrains Mono"
                                            font.letterSpacing: shellWindow ? shellWindow.scaled(1) : 1
                                        }

                                        Text {
                                            width: parent.width
                                            text: busItem["value"]
                                            color: shellWindow ? shellWindow.textStrong : "#f4fbff"
                                            font.pixelSize: shellWindow ? shellWindow.captionSize : 10
                                            font.bold: true
                                            font.family: shellWindow ? shellWindow.monoFamily : "JetBrains Mono"
                                            wrapMode: Text.WrapAnywhere
                                        }

                                        Text {
                                            width: parent.width
                                            text: busItem["detail"]
                                            color: shellWindow ? shellWindow.textSecondary : "#83acc8"
                                            font.pixelSize: shellWindow ? shellWindow.captionSize : 9
                                            font.family: shellWindow ? shellWindow.uiFamily : "Noto Sans CJK SC"
                                            wrapMode: Text.WordWrap
                                            maximumLineCount: 2
                                            elide: Text.ElideRight
                                        }
                                    }
                                }
                            }
                        }

                        Repeater {
                            model: 10

                            delegate: Rectangle {
                                width: 1
                                height: lowerDockLane.height - (shellWindow ? shellWindow.scaled(36) : 36)
                                x: (shellWindow ? shellWindow.scaled(18) : 18) + index * ((lowerDockLane.width - (shellWindow ? shellWindow.scaled(36) : 36)) / Math.max(1, model - 1))
                                y: shellWindow ? shellWindow.scaled(24) : 24
                                color: index % 3 === 0 ? "#184769" : "#0f304a"
                                opacity: index % 3 === 0 ? 0.18 : 0.1
                            }
                        }
                    }

                    Rectangle {
                        visible: !compactCardLayout
                        id: stageEnvelopeFrame
                        anchors.left: leftDockLane.right
                        anchors.right: rightDockLane.left
                        anchors.top: root.stageCommandShelfVisible ? stageCommandShelf.bottom : stageTag.bottom
                        anchors.bottom: projectionRailCard.top
                        anchors.leftMargin: shellWindow ? shellWindow.scaled(18) : 18
                        anchors.rightMargin: shellWindow ? shellWindow.scaled(18) : 18
                        anchors.topMargin: shellWindow ? shellWindow.scaled(14) : 14
                        anchors.bottomMargin: shellWindow ? shellWindow.scaled(14) : 14
                        radius: shellWindow ? shellWindow.cardRadius : 14
                        color: "transparent"
                        border.color: "#174567"
                        border.width: 1
                        opacity: 0.92

                        Rectangle {
                            anchors.fill: parent
                            anchors.margins: 1
                            radius: parent.radius - 1
                            color: "transparent"
                            border.color: "#0f3049"
                            border.width: 1
                            opacity: 0.82
                        }

                        Rectangle {
                            anchors.fill: parent
                            anchors.margins: shellWindow ? shellWindow.scaled(12) : 12
                            radius: Math.max(2, parent.radius - (shellWindow ? shellWindow.scaled(12) : 12))
                            color: "transparent"
                            border.color: "#123752"
                            border.width: 1
                            opacity: 0.42
                        }

                        Rectangle {
                            width: parent.width * 0.52
                            height: parent.height * 0.72
                            radius: width / 2
                            color: root.accentBlue
                            opacity: 0.05
                            anchors.horizontalCenter: parent.horizontalCenter
                            y: parent.height * 0.08
                        }

                        Rectangle {
                            anchors.left: parent.left
                            anchors.top: parent.top
                            anchors.bottom: parent.bottom
                            anchors.margins: shellWindow ? shellWindow.scaled(10) : 10
                            width: shellWindow ? shellWindow.scaled(3) : 3
                            radius: width / 2
                            gradient: Gradient {
                                GradientStop { position: 0.0; color: "transparent" }
                                GradientStop { position: 0.18; color: root.accentBlue }
                                GradientStop { position: 0.82; color: root.accentCyan }
                                GradientStop { position: 1.0; color: "transparent" }
                            }
                            opacity: 0.28
                        }

                        Rectangle {
                            anchors.right: parent.right
                            anchors.top: parent.top
                            anchors.bottom: parent.bottom
                            anchors.margins: shellWindow ? shellWindow.scaled(10) : 10
                            width: shellWindow ? shellWindow.scaled(3) : 3
                            radius: width / 2
                            gradient: Gradient {
                                GradientStop { position: 0.0; color: "transparent" }
                                GradientStop { position: 0.18; color: root.accentCyan }
                                GradientStop { position: 0.82; color: root.accentBlue }
                                GradientStop { position: 1.0; color: "transparent" }
                            }
                            opacity: 0.28
                        }

                        Rectangle {
                            anchors.horizontalCenter: parent.horizontalCenter
                            anchors.top: parent.top
                            anchors.bottom: parent.bottom
                            width: 1
                            color: "#1b4b72"
                            opacity: 0.22
                        }

                        Rectangle {
                            anchors.left: parent.left
                            anchors.right: parent.right
                            anchors.verticalCenter: parent.verticalCenter
                            height: 1
                            color: "#1b4b72"
                            opacity: 0.16
                        }

                        RowLayout {
                            anchors.left: parent.left
                            anchors.right: parent.right
                            anchors.top: parent.top
                            anchors.leftMargin: shellWindow ? shellWindow.scaled(14) : 14
                            anchors.rightMargin: shellWindow ? shellWindow.scaled(14) : 14
                            anchors.topMargin: shellWindow ? shellWindow.scaled(12) : 12
                            spacing: shellWindow ? shellWindow.compactGap : 8

                            Text {
                                Layout.fillWidth: true
                                text: "SYSTEM ENCLOSURE / " + root.stageEnvelopeLabel
                                color: shellWindow ? shellWindow.accentBlue : "#38b6ff"
                                font.pixelSize: shellWindow ? shellWindow.captionSize : 10
                                font.family: shellWindow ? shellWindow.monoFamily : "JetBrains Mono"
                                font.letterSpacing: shellWindow ? shellWindow.scaled(1) : 1
                            }

                            Rectangle {
                                Layout.alignment: Qt.AlignTop
                                radius: shellWindow ? shellWindow.edgeRadius : 10
                                color: "#091726"
                                border.color: "#1d547c"
                                border.width: 1
                                implicitWidth: stageEnvelopeStampText.implicitWidth + ((shellWindow ? shellWindow.scaled(10) : 10) * 2)
                                implicitHeight: stageEnvelopeStampText.implicitHeight + ((shellWindow ? shellWindow.scaled(5) : 5) * 2)

                                Text {
                                    id: stageEnvelopeStampText
                                    anchors.centerIn: parent
                                    text: root.stageEnvelopeStamp
                                    color: shellWindow ? shellWindow.textPrimary : "#d5eeff"
                                    font.pixelSize: shellWindow ? shellWindow.captionSize : 9
                                    font.family: shellWindow ? shellWindow.monoFamily : "JetBrains Mono"
                                }
                            }
                        }

                        GridLayout {
                            anchors.left: parent.left
                            anchors.right: parent.right
                            anchors.bottom: parent.bottom
                            anchors.leftMargin: shellWindow ? shellWindow.scaled(14) : 14
                            anchors.rightMargin: shellWindow ? shellWindow.scaled(14) : 14
                            anchors.bottomMargin: shellWindow ? shellWindow.scaled(12) : 12
                            columns: root.stageEnvelopeModel.length
                            columnSpacing: shellWindow ? shellWindow.compactGap : 8
                            rowSpacing: shellWindow ? shellWindow.compactGap : 8

                            Repeater {
                                model: root.stageEnvelopeModel

                                delegate: Rectangle {
                                    readonly property var envelopeItem: modelData
                                    Layout.fillWidth: true
                                    radius: shellWindow ? shellWindow.edgeRadius : 10
                                    gradient: Gradient {
                                        GradientStop { position: 0.0; color: Qt.lighter(root.toneFill(envelopeItem["tone"]), 1.12) }
                                        GradientStop { position: 1.0; color: root.toneFill(envelopeItem["tone"]) }
                                    }
                                    border.color: root.toneColor(envelopeItem["tone"])
                                    border.width: 1
                                    implicitHeight: envelopeColumn.implicitHeight + ((shellWindow ? shellWindow.scaled(7) : 7) * 2)

                                    Rectangle {
                                        anchors.left: parent.left
                                        anchors.right: parent.right
                                        anchors.top: parent.top
                                        height: shellWindow ? shellWindow.scaled(2) : 2
                                        gradient: Gradient {
                                            GradientStop { position: 0.0; color: "transparent" }
                                            GradientStop { position: 0.28; color: root.toneColor(envelopeItem["tone"]) }
                                            GradientStop { position: 0.74; color: Qt.lighter(root.toneColor(envelopeItem["tone"]), 1.16) }
                                            GradientStop { position: 1.0; color: "transparent" }
                                        }
                                        opacity: 0.76
                                    }

                                    Column {
                                        id: envelopeColumn
                                        anchors.fill: parent
                                        anchors.margins: shellWindow ? shellWindow.scaled(7) : 7
                                        spacing: 1

                                        Text {
                                            text: envelopeItem["label"]
                                            color: shellWindow ? shellWindow.textMuted : "#4e7392"
                                            font.pixelSize: shellWindow ? shellWindow.captionSize : 9
                                            font.family: shellWindow ? shellWindow.monoFamily : "JetBrains Mono"
                                            font.letterSpacing: shellWindow ? shellWindow.scaled(1) : 1
                                        }

                                        Text {
                                            width: parent.width
                                            text: envelopeItem["value"]
                                            color: shellWindow ? shellWindow.textStrong : "#f4fbff"
                                            font.pixelSize: shellWindow ? shellWindow.captionSize : 10
                                            font.bold: true
                                            font.family: shellWindow ? shellWindow.monoFamily : "JetBrains Mono"
                                            wrapMode: Text.WrapAnywhere
                                        }

                                        Text {
                                            width: parent.width
                                            text: envelopeItem["detail"]
                                            color: shellWindow ? shellWindow.textSecondary : "#83acc8"
                                            font.pixelSize: shellWindow ? shellWindow.captionSize : 9
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

                    Rectangle {
                        id: stageTag
                        anchors.horizontalCenter: parent.horizontalCenter
                        anchors.top: parent.top
                        anchors.topMargin: root.stageDockMargin
                        radius: shellWindow ? shellWindow.edgeRadius : 10
                        gradient: Gradient {
                            GradientStop { position: 0.0; color: "#0b1c2d" }
                            GradientStop { position: 1.0; color: "#091522" }
                        }
                        border.color: "#2b6f9d"
                        border.width: 1
                        implicitWidth: stageTagRow.implicitWidth + ((shellWindow ? shellWindow.scaled(14) : 14) * 2)
                        implicitHeight: stageTagRow.implicitHeight + ((shellWindow ? shellWindow.scaled(7) : 7) * 2)

                        RowLayout {
                            id: stageTagRow
                            anchors.centerIn: parent
                            spacing: shellWindow ? shellWindow.compactGap : 8

                            Text {
                                text: "TACTICAL THEATER"
                                color: shellWindow ? shellWindow.accentBlue : "#38b6ff"
                                font.pixelSize: shellWindow ? shellWindow.captionSize : 10
                                font.family: shellWindow ? shellWindow.monoFamily : "JetBrains Mono"
                                font.letterSpacing: shellWindow ? shellWindow.scaled(1) : 1
                            }

                            Rectangle {
                                width: 1
                                height: shellWindow ? shellWindow.scaled(14) : 14
                                color: "#20567e"
                            }

                            Text {
                                text: root.missionModeEnglish
                                color: shellWindow ? shellWindow.textPrimary : "#d5eeff"
                                font.pixelSize: shellWindow ? shellWindow.captionSize : 10
                                font.family: shellWindow ? shellWindow.monoFamily : "JetBrains Mono"
                            }
                        }
                    }

                    Rectangle {
                        visible: root.stageCommandShelfVisible
                        id: stageCommandShelf
                        z: 1
                        anchors.horizontalCenter: parent.horizontalCenter
                        anchors.top: parent.top
                        anchors.topMargin: root.stageOverlayTopMargin
                        width: Math.min(
                            shellWindow ? shellWindow.scaled(520) : 520,
                            parent.width - ((root.stageDockMargin * 4) + root.missionDeckWidth + root.telemetryRailWidth + (root.stageConnectorSpan * 2))
                        )
                        radius: shellWindow ? shellWindow.edgeRadius : 10
                        gradient: Gradient {
                            GradientStop { position: 0.0; color: "#0b1d30" }
                            GradientStop { position: 0.56; color: "#091524" }
                            GradientStop { position: 1.0; color: "#08111c" }
                        }
                        border.color: "#2a6f9d"
                        border.width: 1
                        implicitHeight: stageCommandShelfLayout.implicitHeight + ((shellWindow ? shellWindow.scaled(10) : 10) * 2)

                        Rectangle {
                            anchors.fill: parent
                            anchors.margins: 1
                            radius: parent.radius - 1
                            color: "transparent"
                            border.color: "#123450"
                            border.width: 1
                            opacity: 0.82
                        }

                        Rectangle {
                            anchors.left: parent.left
                            anchors.right: parent.right
                            anchors.top: parent.top
                            height: shellWindow ? shellWindow.scaled(3) : 3
                            gradient: Gradient {
                                GradientStop { position: 0.0; color: "transparent" }
                                GradientStop { position: 0.22; color: root.accentBlue }
                                GradientStop { position: 0.72; color: root.accentCyan }
                                GradientStop { position: 1.0; color: "transparent" }
                            }
                            opacity: 0.78
                        }

                        RowLayout {
                            id: stageCommandShelfLayout
                            anchors.fill: parent
                            anchors.margins: shellWindow ? shellWindow.scaled(10) : 10
                            spacing: shellWindow ? shellWindow.compactGap : 8

                            Repeater {
                                model: root.stageCommandShelfModel

                                delegate: Rectangle {
                                    readonly property var shelfMetric: modelData
                                    Layout.fillWidth: true
                                    radius: shellWindow ? shellWindow.edgeRadius : 10
                                    gradient: Gradient {
                                        GradientStop { position: 0.0; color: Qt.lighter(root.toneFill(shelfMetric["tone"]), 1.14) }
                                        GradientStop { position: 1.0; color: root.toneFill(shelfMetric["tone"]) }
                                    }
                                    border.color: root.toneColor(shelfMetric["tone"])
                                    border.width: 1
                                    implicitHeight: shelfMetricColumn.implicitHeight + ((shellWindow ? shellWindow.scaled(7) : 7) * 2)

                                    Column {
                                        id: shelfMetricColumn
                                        anchors.fill: parent
                                        anchors.margins: shellWindow ? shellWindow.scaled(7) : 7
                                        spacing: 1

                                        Text {
                                            text: shelfMetric["label"]
                                            color: shellWindow ? shellWindow.textMuted : "#4e7392"
                                            font.pixelSize: shellWindow ? shellWindow.captionSize : 9
                                            font.family: shellWindow ? shellWindow.monoFamily : "JetBrains Mono"
                                            font.letterSpacing: shellWindow ? shellWindow.scaled(1) : 1
                                        }

                                        Text {
                                            width: parent.width
                                            text: shelfMetric["value"]
                                            color: shellWindow ? shellWindow.textStrong : "#f4fbff"
                                            font.pixelSize: shellWindow ? shellWindow.captionSize : 11
                                            font.bold: true
                                            font.family: shellWindow ? shellWindow.monoFamily : "JetBrains Mono"
                                            wrapMode: Text.WrapAnywhere
                                        }

                                        Text {
                                            width: parent.width
                                            text: shelfMetric["detail"]
                                            color: shellWindow ? shellWindow.textSecondary : "#83acc8"
                                            font.pixelSize: shellWindow ? shellWindow.captionSize : 9
                                            font.family: shellWindow ? shellWindow.uiFamily : "Noto Sans CJK SC"
                                            wrapMode: Text.WordWrap
                                        }
                                    }
                                }
                            }
                        }
                    }

                    Rectangle {
                        visible: root.stageCommandShelfVisible
                        anchors.right: stageCommandShelf.left
                        anchors.rightMargin: shellWindow ? shellWindow.scaled(8) : 8
                        anchors.verticalCenter: stageCommandShelf.verticalCenter
                        width: root.stageConnectorSpan
                        height: shellWindow ? shellWindow.scaled(2) : 2
                        gradient: Gradient {
                            orientation: Gradient.Horizontal
                            GradientStop { position: 0.0; color: root.accentBlue }
                            GradientStop { position: 0.72; color: root.accentCyan }
                            GradientStop { position: 1.0; color: "transparent" }
                        }
                        opacity: 0.82
                    }

                    Rectangle {
                        visible: root.stageCommandShelfVisible
                        anchors.left: stageCommandShelf.right
                        anchors.leftMargin: shellWindow ? shellWindow.scaled(8) : 8
                        anchors.verticalCenter: stageCommandShelf.verticalCenter
                        width: root.stageConnectorSpan
                        height: shellWindow ? shellWindow.scaled(2) : 2
                        gradient: Gradient {
                            orientation: Gradient.Horizontal
                            GradientStop { position: 0.0; color: "transparent" }
                            GradientStop { position: 0.28; color: root.accentBlue }
                            GradientStop { position: 1.0; color: root.accentCyan }
                        }
                        opacity: 0.82
                    }

                    Rectangle {
                        width: shellWindow ? shellWindow.scaled(42) : 42
                        height: 2
                        color: root.accentBlue
                        anchors.left: parent.left
                        anchors.top: parent.top
                        anchors.leftMargin: shellWindow ? shellWindow.scaled(14) : 14
                        anchors.topMargin: shellWindow ? shellWindow.scaled(14) : 14
                        opacity: 0.94
                    }

                    Rectangle {
                        width: 2
                        height: shellWindow ? shellWindow.scaled(42) : 42
                        color: root.accentBlue
                        anchors.left: parent.left
                        anchors.top: parent.top
                        anchors.leftMargin: shellWindow ? shellWindow.scaled(14) : 14
                        anchors.topMargin: shellWindow ? shellWindow.scaled(14) : 14
                        opacity: 0.94
                    }

                    Rectangle {
                        width: shellWindow ? shellWindow.scaled(42) : 42
                        height: 2
                        color: root.accentCyan
                        anchors.right: parent.right
                        anchors.top: parent.top
                        anchors.rightMargin: shellWindow ? shellWindow.scaled(14) : 14
                        anchors.topMargin: shellWindow ? shellWindow.scaled(14) : 14
                        opacity: 0.9
                    }

                    Rectangle {
                        width: 2
                        height: shellWindow ? shellWindow.scaled(42) : 42
                        color: root.accentCyan
                        anchors.right: parent.right
                        anchors.top: parent.top
                        anchors.rightMargin: shellWindow ? shellWindow.scaled(14) : 14
                        anchors.topMargin: shellWindow ? shellWindow.scaled(14) : 14
                        opacity: 0.9
                    }

                    Rectangle {
                        width: shellWindow ? shellWindow.scaled(42) : 42
                        height: 2
                        color: "#1d5f8d"
                        anchors.left: parent.left
                        anchors.bottom: parent.bottom
                        anchors.leftMargin: shellWindow ? shellWindow.scaled(14) : 14
                        anchors.bottomMargin: shellWindow ? shellWindow.scaled(14) : 14
                        opacity: 0.84
                    }

                    Rectangle {
                        width: 2
                        height: shellWindow ? shellWindow.scaled(42) : 42
                        color: "#1d5f8d"
                        anchors.left: parent.left
                        anchors.bottom: parent.bottom
                        anchors.leftMargin: shellWindow ? shellWindow.scaled(14) : 14
                        anchors.bottomMargin: shellWindow ? shellWindow.scaled(14) : 14
                        opacity: 0.84
                    }

                    Rectangle {
                        width: shellWindow ? shellWindow.scaled(42) : 42
                        height: 2
                        color: "#5ecfff"
                        anchors.right: parent.right
                        anchors.bottom: parent.bottom
                        anchors.rightMargin: shellWindow ? shellWindow.scaled(14) : 14
                        anchors.bottomMargin: shellWindow ? shellWindow.scaled(14) : 14
                        opacity: 0.84
                    }

                    Rectangle {
                        width: 2
                        height: shellWindow ? shellWindow.scaled(42) : 42
                        color: "#5ecfff"
                        anchors.right: parent.right
                        anchors.bottom: parent.bottom
                        anchors.rightMargin: shellWindow ? shellWindow.scaled(14) : 14
                        anchors.bottomMargin: shellWindow ? shellWindow.scaled(14) : 14
                        opacity: 0.84
                    }

                    Rectangle {
                        id: scanSweep
                        width: shellWindow ? shellWindow.scaled(88) : 88
                        height: mapStage.height - (root.mapInset * 2)
                        y: root.mapInset
                        x: -width
                        gradient: Gradient {
                            orientation: Gradient.Horizontal
                            GradientStop { position: 0.0; color: "#2fd1ff00" }
                            GradientStop { position: 0.45; color: "#2daeff18" }
                            GradientStop { position: 0.52; color: "#9ff1ff5c" }
                            GradientStop { position: 0.65; color: "#2daeff16" }
                            GradientStop { position: 1.0; color: "#2fd1ff00" }
                        }
                        opacity: 0.34

                        SequentialAnimation on x {
                            loops: Animation.Infinite
                            running: mapStage.visible && mapStage.width > 0
                            NumberAnimation {
                                from: -scanSweep.width
                                to: mapStage.width
                                duration: 7600
                                easing.type: Easing.InOutSine
                            }
                            PauseAnimation { duration: 900 }
                        }
                    }

                    Repeater {
                        model: 4

                        delegate: Rectangle {
                            width: (mapStage.width - (root.mapInset * 2)) / 4
                            height: mapStage.height - (root.mapInset * 2)
                            x: root.mapInset + (index * width)
                            y: root.mapInset
                            gradient: Gradient {
                                GradientStop {
                                    position: 0.0
                                    color: index % 2 === 0 ? "#07111d00" : "#08203526"
                                }
                                GradientStop {
                                    position: 1.0
                                    color: index % 2 === 0 ? "#08203520" : "#07111d00"
                                }
                            }
                            opacity: 0.42
                        }
                    }

                    Rectangle {
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.top: parent.top
                        anchors.leftMargin: shellWindow ? shellWindow.scaled(14) : 14
                        anchors.rightMargin: shellWindow ? shellWindow.scaled(14) : 14
                        anchors.topMargin: shellWindow ? shellWindow.scaled(14) : 14
                        radius: shellWindow ? shellWindow.edgeRadius : 10
                        gradient: Gradient {
                            GradientStop { position: 0.0; color: "#0b1b2f" }
                            GradientStop { position: 1.0; color: "#081320" }
                        }
                        border.color: "#1a4e78"
                        border.width: 1
                        implicitHeight: theatreRow.implicitHeight + ((shellWindow ? shellWindow.scaled(8) : 8) * 2)

                        ColumnLayout {
                            id: theatreRow
                            anchors.fill: parent
                            anchors.margins: shellWindow ? shellWindow.scaled(8) : 8
                            spacing: shellWindow ? shellWindow.compactGap : 8

                            RowLayout {
                                Layout.fillWidth: true
                                spacing: shellWindow ? shellWindow.zoneGap : 12

                                ColumnLayout {
                                    Layout.fillWidth: true
                                    spacing: shellWindow ? shellWindow.scaled(2) : 2

                                    Text {
                                        text: "主舞台网格 / COMMAND MESH"
                                        color: shellWindow ? shellWindow.accentBlue : "#38b6ff"
                                        font.pixelSize: shellWindow ? shellWindow.captionSize : 11
                                        font.family: shellWindow ? shellWindow.monoFamily : "JetBrains Mono"
                                        font.letterSpacing: shellWindow ? shellWindow.scaled(1) : 1
                                    }

                                    Text {
                                        text: root.missionFocusLabel
                                        color: shellWindow ? shellWindow.textSecondary : "#83acc8"
                                        font.pixelSize: shellWindow ? shellWindow.captionSize : 11
                                        font.family: shellWindow ? shellWindow.uiFamily : "Noto Sans CJK SC"
                                        wrapMode: Text.WordWrap
                                    }
                                }

                                Rectangle {
                                    radius: shellWindow ? shellWindow.edgeRadius : 10
                                    gradient: Gradient {
                                        GradientStop { position: 0.0; color: Qt.lighter(root.toneFill(root.wallboardStatusTone), 1.14) }
                                        GradientStop { position: 1.0; color: root.toneFill(root.wallboardStatusTone) }
                                    }
                                    border.color: root.toneColor(root.wallboardStatusTone)
                                    border.width: 1
                                    implicitWidth: theatreStatusColumn.implicitWidth + ((shellWindow ? shellWindow.scaled(14) : 14) * 2)
                                    implicitHeight: theatreStatusColumn.implicitHeight + ((shellWindow ? shellWindow.scaled(8) : 8) * 2)

                                    Column {
                                        id: theatreStatusColumn
                                        anchors.centerIn: parent
                                        spacing: 1

                                        Text {
                                            text: root.missionModeEnglish
                                            color: shellWindow ? shellWindow.textMuted : "#4e7392"
                                            font.pixelSize: shellWindow ? shellWindow.captionSize : 9
                                            font.family: shellWindow ? shellWindow.monoFamily : "JetBrains Mono"
                                            font.letterSpacing: shellWindow ? shellWindow.scaled(1) : 1
                                        }

                                        Text {
                                            text: root.wallboardStatusLabel
                                            color: shellWindow ? shellWindow.textStrong : "#f4fbff"
                                            font.pixelSize: shellWindow ? shellWindow.captionSize : 11
                                            font.bold: true
                                            font.family: shellWindow ? shellWindow.uiFamily : "Noto Sans CJK SC"
                                        }
                                    }
                                }
                            }

                            Rectangle {
                                Layout.fillWidth: true
                                Layout.preferredHeight: 1
                                color: "#123b5b"
                                opacity: 0.92
                            }

                            Flow {
                                Layout.fillWidth: true
                                spacing: shellWindow ? shellWindow.compactGap : 8

                                Repeater {
                                    model: root.theatreRibbonModel

                                    delegate: Rectangle {
                                        readonly property var ribbonData: modelData
                                        radius: shellWindow ? shellWindow.edgeRadius : 10
                                        gradient: Gradient {
                                            GradientStop { position: 0.0; color: Qt.lighter(root.toneFill(ribbonData["tone"]), 1.14) }
                                            GradientStop { position: 1.0; color: root.toneFill(ribbonData["tone"]) }
                                        }
                                        border.color: root.toneColor(ribbonData["tone"])
                                        border.width: 1
                                        implicitWidth: theatreBadgeColumn.implicitWidth + ((shellWindow ? shellWindow.scaled(12) : 12) * 2)
                                        implicitHeight: theatreBadgeColumn.implicitHeight + ((shellWindow ? shellWindow.scaled(5) : 5) * 2)

                                        Rectangle {
                                            anchors.left: parent.left
                                            anchors.right: parent.right
                                            anchors.top: parent.top
                                            height: shellWindow ? shellWindow.scaled(2) : 2
                                            gradient: Gradient {
                                                GradientStop { position: 0.0; color: "transparent" }
                                                GradientStop { position: 0.28; color: root.toneColor(ribbonData["tone"]) }
                                                GradientStop { position: 0.72; color: Qt.lighter(root.toneColor(ribbonData["tone"]), 1.16) }
                                                GradientStop { position: 1.0; color: "transparent" }
                                            }
                                            opacity: 0.74
                                        }

                                        Column {
                                            id: theatreBadgeColumn
                                            anchors.centerIn: parent
                                            spacing: 1

                                            Text {
                                                text: ribbonData["label"]
                                                color: shellWindow ? shellWindow.textMuted : "#4e7392"
                                                font.pixelSize: shellWindow ? shellWindow.captionSize : 9
                                                font.family: shellWindow ? shellWindow.monoFamily : "JetBrains Mono"
                                                font.letterSpacing: shellWindow ? shellWindow.scaled(1) : 1
                                            }

                                            Text {
                                                text: ribbonData["value"]
                                                color: shellWindow ? shellWindow.textStrong : "#f4fbff"
                                                font.pixelSize: shellWindow ? shellWindow.captionSize : 10
                                                font.bold: true
                                                font.family: shellWindow ? shellWindow.monoFamily : "JetBrains Mono"
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }

                    Repeater {
                        model: 9

                        delegate: Rectangle {
                            width: mapStage.width - (root.mapInset * 2)
                            height: 1
                            x: root.mapInset
                            y: root.mapInset + index * ((mapStage.height - (root.mapInset * 2)) / Math.max(1, model - 1))
                            color: index === 4 ? "#2a6f9f" : "#123248"
                            opacity: index === 4 ? 0.76 : 0.38
                        }
                    }

                    Repeater {
                        model: 13

                        delegate: Rectangle {
                            width: 1
                            height: mapStage.height - (root.mapInset * 2)
                            x: root.mapInset + index * ((mapStage.width - (root.mapInset * 2)) / Math.max(1, model - 1))
                            y: root.mapInset
                            color: index === 6 ? "#2a6f9f" : "#123248"
                            opacity: index === 6 ? 0.72 : 0.34
                        }
                    }

                    Repeater {
                        model: root.latitudeTicks

                        delegate: Text {
                            text: root.gridLatitudeLabel(modelData)
                            color: shellWindow ? shellWindow.textMuted : "#4e7392"
                            font.pixelSize: shellWindow ? shellWindow.captionSize : 10
                            font.family: shellWindow ? shellWindow.monoFamily : "JetBrains Mono"
                            x: shellWindow ? shellWindow.scaled(10) : 10
                            y: root.worldY(modelData, mapStage.height) - (height / 2)
                        }
                    }

                    Repeater {
                        model: root.longitudeTicks

                        delegate: Text {
                            text: root.gridLongitudeLabel(modelData)
                            color: shellWindow ? shellWindow.textMuted : "#4e7392"
                            font.pixelSize: shellWindow ? shellWindow.captionSize : 10
                            font.family: shellWindow ? shellWindow.monoFamily : "JetBrains Mono"
                            x: root.worldX(modelData, mapStage.width) - (width / 2)
                            y: mapStage.height - (shellWindow ? shellWindow.scaled(28) : 28)
                        }
                    }

                    Rectangle {
                        anchors.left: parent.left
                        anchors.right: parent.right
                        height: 1
                        y: root.worldY(root.currentPoint["latitude"], mapStage.height)
                        color: "#2f8fca"
                        opacity: 0.18
                    }

                    Rectangle {
                        width: 1
                        anchors.top: parent.top
                        anchors.bottom: parent.bottom
                        x: root.worldX(root.currentPoint["longitude"], mapStage.width)
                        color: "#2f8fca"
                        opacity: 0.18
                    }

                    Repeater {
                        model: 5

                        delegate: Rectangle {
                            width: mapStage.width * (0.18 + (index * 0.11))
                            height: width
                            radius: width / 2
                            anchors.centerIn: parent
                            color: "transparent"
                            border.color: index === 1 ? "#3caef9" : "#19486c"
                            border.width: 1
                            opacity: 0.24 - (index * 0.03)
                        }
                    }

                    Item {
                        anchors.centerIn: parent
                        width: Math.min(parent.width * 0.88, parent.height * 1.7)
                        height: width

                        Item {
                            anchors.fill: parent
                            transformOrigin: Item.Center

                            NumberAnimation on rotation {
                                from: 0
                                to: 360
                                duration: 8800
                                loops: Animation.Infinite
                            }

                            Rectangle {
                                x: parent.width / 2
                                y: (parent.height - height) / 2
                                width: parent.width * 0.42
                                height: shellWindow ? shellWindow.scaled(92) : 92
                                gradient: Gradient {
                                    orientation: Gradient.Horizontal
                                    GradientStop { position: 0.0; color: "#2590d800" }
                                    GradientStop { position: 0.18; color: "#1c7bb822" }
                                    GradientStop { position: 0.65; color: "#2db4ff44" }
                                    GradientStop { position: 1.0; color: "#5ef0ff00" }
                                }
                                opacity: 0.24
                            }

                            Rectangle {
                                x: parent.width / 2
                                y: (parent.height - height) / 2
                                width: parent.width * 0.38
                                height: 2
                                gradient: Gradient {
                                    orientation: Gradient.Horizontal
                                    GradientStop { position: 0.0; color: "#39a8ef55" }
                                    GradientStop { position: 0.7; color: "#7cf5ff" }
                                    GradientStop { position: 1.0; color: "transparent" }
                                }
                                opacity: 0.86
                            }
                        }
                    }

                    Canvas {
                        id: mapCanvas
                        anchors.fill: parent
                        antialiasing: true

                        onPaint: {
                            var ctx = getContext("2d")
                            ctx.clearRect(0, 0, mapCanvas.width, mapCanvas.height)
                            ctx.lineCap = "round"
                            ctx.lineJoin = "round"

                            function px(longitude) {
                                return root.worldX(longitude, mapCanvas.width)
                            }

                            function py(latitude) {
                                return root.worldY(latitude, mapCanvas.height)
                            }

                            function drawLandmass(points, fillColor, strokeColor) {
                                if (!points || points.length === 0)
                                    return
                                ctx.beginPath()
                                ctx.moveTo(px(points[0][0]), py(points[0][1]))
                                for (var i = 1; i < points.length; ++i)
                                    ctx.lineTo(px(points[i][0]), py(points[i][1]))
                                ctx.closePath()
                                ctx.fillStyle = fillColor
                                ctx.fill()
                                ctx.strokeStyle = strokeColor
                                ctx.lineWidth = 1
                                ctx.stroke()
                            }

                            function drawArc(lon1, lat1, lon2, lat2, color, width, rise, glowColor) {
                                var x1 = px(lon1)
                                var y1 = py(lat1)
                                var x2 = px(lon2)
                                var y2 = py(lat2)
                                var midX = (x1 + x2) / 2
                                var midY = (y1 + y2) / 2 - rise

                                ctx.save()
                                ctx.beginPath()
                                ctx.moveTo(x1, y1)
                                ctx.quadraticCurveTo(midX, midY, x2, y2)
                                ctx.lineWidth = width + 2.2
                                ctx.strokeStyle = glowColor
                                ctx.globalAlpha = 0.24
                                ctx.stroke()
                                ctx.restore()

                                ctx.beginPath()
                                ctx.moveTo(x1, y1)
                                ctx.quadraticCurveTo(midX, midY, x2, y2)
                                ctx.lineWidth = width
                                ctx.strokeStyle = color
                                ctx.globalAlpha = 1.0
                                ctx.stroke()
                            }

                            function drawPoint(lon, lat, fillColor, strokeColor, size) {
                                ctx.beginPath()
                                ctx.arc(px(lon), py(lat), size, 0, Math.PI * 2)
                                ctx.fillStyle = fillColor
                                ctx.fill()
                                ctx.strokeStyle = strokeColor
                                ctx.lineWidth = 1.2
                                ctx.stroke()
                            }

                            var wash = ctx.createRadialGradient(
                                mapCanvas.width * 0.52,
                                mapCanvas.height * 0.48,
                                22,
                                mapCanvas.width * 0.52,
                                mapCanvas.height * 0.48,
                                mapCanvas.width * 0.42
                            )
                            wash.addColorStop(0.0, "rgba(33,122,184,0.12)")
                            wash.addColorStop(0.55, "rgba(10,42,68,0.04)")
                            wash.addColorStop(1.0, "rgba(0,0,0,0)")
                            ctx.fillStyle = wash
                            ctx.fillRect(0, 0, mapCanvas.width, mapCanvas.height)

                            var landFill = "rgba(17,63,97,0.34)"
                            var landStroke = "rgba(109,202,255,0.14)"
                            drawLandmass([[-165, 12], [-155, 55], [-126, 73], [-95, 67], [-64, 50], [-77, 18], [-110, 7]], landFill, landStroke)
                            drawLandmass([[-82, 12], [-72, 3], [-61, -16], [-56, -34], [-63, -55], [-76, -50], [-81, -20]], landFill, landStroke)
                            drawLandmass([[-12, 36], [2, 58], [34, 71], [78, 66], [120, 56], [151, 40], [131, 9], [90, 20], [66, 8], [35, 28], [9, 30]], landFill, landStroke)
                            drawLandmass([[-18, 31], [6, 33], [28, 19], [34, -8], [24, -31], [14, -34], [-2, -20], [-12, 6]], "rgba(19,71,93,0.32)", landStroke)
                            drawLandmass([[111, -13], [126, -11], [145, -24], [154, -38], [136, -43], [117, -33]], "rgba(17,70,96,0.3)", landStroke)
                            drawLandmass([[-54, 58], [-42, 74], [-18, 80], [-20, 61]], "rgba(18,78,118,0.24)", "rgba(114,243,255,0.12)")

                            for (var hotspotIndex = 0; hotspotIndex < root.wallboardHotspots.length; ++hotspotIndex) {
                                var hotspot = root.wallboardHotspots[hotspotIndex]
                                var meshColor = hotspot["tone"] === "warning" ? "rgba(255,191,82,0.62)" : "rgba(57,182,255,0.58)"
                                var meshGlow = hotspot["tone"] === "warning" ? "rgba(255,191,82,0.38)" : "rgba(114,243,255,0.34)"
                                drawArc(
                                    root.currentPoint["longitude"],
                                    root.currentPoint["latitude"],
                                    hotspot["longitude"],
                                    hotspot["latitude"],
                                    meshColor,
                                    hotspot["tone"] === "warning" ? 2.0 : 1.8,
                                    28 + (hotspotIndex * 6),
                                    meshGlow
                                )
                            }

                            if (root.trackData.length > 1) {
                                for (var trackIndex = 0; trackIndex < root.trackData.length - 1; ++trackIndex) {
                                    var pointA = root.trackData[trackIndex]
                                    var pointB = root.trackData[trackIndex + 1]
                                    var currentSegment = trackIndex === root.trackData.length - 2
                                    drawArc(
                                        pointA["longitude"],
                                        pointA["latitude"],
                                        pointB["longitude"],
                                        pointB["latitude"],
                                        currentSegment ? "rgba(114,243,255,0.98)" : "rgba(57,182,255,0.66)",
                                        currentSegment ? 3.2 : 2.0,
                                        12 + (trackIndex * 2),
                                        currentSegment ? "rgba(114,243,255,0.42)" : "rgba(57,182,255,0.22)"
                                    )
                                }
                            }

                            for (var pointIndex = 0; pointIndex < Math.max(root.trackData.length, 1); ++pointIndex) {
                                var point = root.trackPoint(pointIndex)
                                var current = pointIndex === Math.max(root.trackData.length - 1, 0)
                                drawPoint(
                                    point["longitude"],
                                    point["latitude"],
                                    current ? "rgba(114,243,255,0.96)" : "rgba(90,177,230,0.62)",
                                    current ? "rgba(255,255,255,0.92)" : "rgba(57,123,171,0.72)",
                                    current ? 5.2 : 3.2
                                )
                            }

                            drawPoint(
                                root.originPoint["longitude"],
                                root.originPoint["latitude"],
                                "rgba(0,0,0,0)",
                                "rgba(156,211,248,0.8)",
                                7.0
                            )

                            var aircraftX = px(root.currentPoint["longitude"])
                            var aircraftY = py(root.currentPoint["latitude"])
                            ctx.beginPath()
                            ctx.arc(aircraftX, aircraftY, 18, 0, Math.PI * 2)
                            ctx.strokeStyle = "rgba(114,243,255,0.34)"
                            ctx.lineWidth = 1.4
                            ctx.stroke()

                            ctx.save()
                            ctx.translate(aircraftX, aircraftY)
                            ctx.rotate((root.headingDeg - 90) * Math.PI / 180)
                            ctx.beginPath()
                            ctx.moveTo(0, -18)
                            ctx.lineTo(8, 14)
                            ctx.lineTo(0, 8)
                            ctx.lineTo(-8, 14)
                            ctx.closePath()
                            ctx.fillStyle = "rgba(114,243,255,0.92)"
                            ctx.strokeStyle = "rgba(255,255,255,0.9)"
                            ctx.lineWidth = 1
                            ctx.fill()
                            ctx.stroke()
                            ctx.restore()
                        }

                        onWidthChanged: requestPaint()
                        onHeightChanged: requestPaint()
                        Component.onCompleted: requestPaint()
                    }

                    Repeater {
                        model: root.wallboardHotspots

                        delegate: Item {
                            readonly property var hotspot: modelData
                            readonly property real pulseSize: (shellWindow ? shellWindow.scaled(22) : 22) + (hotspot["intensity"] * (shellWindow ? shellWindow.scaled(20) : 20))
                            readonly property real anchorX: root.worldX(hotspot["longitude"], mapStage.width)
                            readonly property real anchorY: root.worldY(hotspot["latitude"], mapStage.height)
                            readonly property bool leftLabel: anchorX > mapStage.width * 0.64
                            x: anchorX - (pulseSize / 2)
                            y: anchorY - (pulseSize / 2)
                            width: pulseSize
                            height: pulseSize

                            Rectangle {
                                anchors.centerIn: parent
                                width: parent.width
                                height: width
                                radius: width / 2
                                color: "transparent"
                                border.color: root.toneColor(hotspot["tone"])
                                border.width: 1
                                opacity: 0.34

                                SequentialAnimation on scale {
                                    loops: Animation.Infinite
                                    NumberAnimation { from: 0.78; to: 1.22; duration: 1700 }
                                    NumberAnimation { from: 1.22; to: 0.78; duration: 1700 }
                                }
                            }

                            Rectangle {
                                anchors.centerIn: parent
                                width: parent.width * 0.42
                                height: width
                                radius: width / 2
                                color: root.toneColor(hotspot["tone"])
                                border.color: "#ffffff"
                                border.width: 1
                            }

                            Rectangle {
                                id: labelPlate
                                y: (parent.height - height) / 2
                                x: leftLabel
                                    ? -width - (shellWindow ? shellWindow.scaled(8) : 8)
                                    : parent.width + (shellWindow ? shellWindow.scaled(8) : 8)
                                radius: shellWindow ? shellWindow.edgeRadius : 10
                                gradient: Gradient {
                                    GradientStop { position: 0.0; color: "#0a1a2a" }
                                    GradientStop { position: 1.0; color: "#081321" }
                                }
                                border.color: root.toneColor(hotspot["tone"])
                                border.width: 1
                                implicitWidth: labelColumn.implicitWidth + ((shellWindow ? shellWindow.scaled(14) : 14) * 2)
                                implicitHeight: labelColumn.implicitHeight + ((shellWindow ? shellWindow.scaled(8) : 8) * 2)

                                Column {
                                    id: labelColumn
                                    anchors.centerIn: parent
                                    spacing: shellWindow ? shellWindow.scaled(1) : 1

                                    Text {
                                        text: hotspot["label"]
                                        color: shellWindow ? shellWindow.textPrimary : "#d5eeff"
                                        font.pixelSize: shellWindow ? shellWindow.captionSize : 11
                                        font.family: shellWindow ? shellWindow.uiFamily : "Noto Sans CJK SC"
                                    }

                                    Text {
                                        text: hotspot["tone"] === "warning" ? "告警热点" : "网格节点"
                                        color: shellWindow ? shellWindow.textMuted : "#4e7392"
                                        font.pixelSize: shellWindow ? shellWindow.captionSize : 10
                                        font.family: shellWindow ? shellWindow.uiFamily : "Noto Sans CJK SC"
                                    }
                                }
                            }
                        }
                    }

                    Item {
                        id: aircraftMarker
                        readonly property bool leftTag: x > mapStage.width * 0.56
                        width: shellWindow ? shellWindow.scaled(38) : 38
                        height: width
                        x: root.worldX(root.currentPoint["longitude"], mapStage.width) - (width / 2)
                        y: root.worldY(root.currentPoint["latitude"], mapStage.height) - (height / 2)

                        Rectangle {
                            anchors.centerIn: parent
                            width: parent.width * 1.9
                            height: width
                            radius: width / 2
                            color: shellWindow ? shellWindow.accentCyan : "#72f3ff"
                            opacity: 0.12

                            SequentialAnimation on scale {
                                loops: Animation.Infinite
                                NumberAnimation { from: 0.82; to: 1.16; duration: 1400 }
                                NumberAnimation { from: 1.16; to: 0.82; duration: 1400 }
                            }
                        }

                        Item {
                            anchors.fill: parent
                            rotation: root.headingDeg
                            transformOrigin: Item.Center

                            Rectangle {
                                width: parent.width * 0.16
                                height: parent.height * 0.82
                                radius: width / 2
                                color: shellWindow ? shellWindow.accentCyan : "#72f3ff"
                                anchors.horizontalCenter: parent.horizontalCenter
                                anchors.verticalCenter: parent.verticalCenter
                                border.color: "#ffffff"
                                border.width: 1
                            }

                            Rectangle {
                                width: parent.width * 0.84
                                height: parent.height * 0.14
                                radius: height / 2
                                color: shellWindow ? shellWindow.accentCyan : "#72f3ff"
                                anchors.centerIn: parent
                                border.color: "#ffffff"
                                border.width: 1
                            }

                            Rectangle {
                                width: parent.width * 0.3
                                height: parent.height * 0.2
                                rotation: 45
                                radius: height / 2
                                color: shellWindow ? shellWindow.accentAmber : "#ffbf52"
                                anchors.horizontalCenter: parent.horizontalCenter
                                anchors.top: parent.top
                                anchors.topMargin: shellWindow ? shellWindow.scaled(2) : 2
                            }
                        }
                    }

                    Item {
                        anchors.centerIn: aircraftMarker
                        width: shellWindow ? shellWindow.scaled(118) : 118
                        height: width

                        Rectangle {
                            anchors.centerIn: parent
                            width: parent.width
                            height: 1
                            color: "#2f8fca"
                            opacity: 0.24
                        }

                        Rectangle {
                            anchors.centerIn: parent
                            width: 1
                            height: parent.height
                            color: "#2f8fca"
                            opacity: 0.24
                        }

                        Rectangle {
                            anchors.centerIn: parent
                            width: parent.width * 0.44
                            height: width
                            radius: width / 2
                            color: "transparent"
                            border.color: "#5ecfff"
                            border.width: 1
                            opacity: 0.48
                        }

                        Rectangle {
                            anchors.horizontalCenter: parent.horizontalCenter
                            anchors.top: parent.top
                            width: 1
                            height: parent.height * 0.16
                            color: "#5ecfff"
                            opacity: 0.6
                        }

                        Rectangle {
                            anchors.horizontalCenter: parent.horizontalCenter
                            anchors.bottom: parent.bottom
                            width: 1
                            height: parent.height * 0.16
                            color: "#5ecfff"
                            opacity: 0.6
                        }

                        Rectangle {
                            anchors.left: parent.left
                            anchors.verticalCenter: parent.verticalCenter
                            width: parent.width * 0.16
                            height: 1
                            color: "#5ecfff"
                            opacity: 0.6
                        }

                        Rectangle {
                            anchors.right: parent.right
                            anchors.verticalCenter: parent.verticalCenter
                            width: parent.width * 0.16
                            height: 1
                            color: "#5ecfff"
                            opacity: 0.6
                        }
                    }

                    Rectangle {
                        radius: shellWindow ? shellWindow.edgeRadius : 10
                        color: "#081321"
                        border.color: shellWindow ? shellWindow.accentCyan : "#72f3ff"
                        border.width: 1
                        x: aircraftMarker.leftTag
                            ? aircraftMarker.x - width - (shellWindow ? shellWindow.scaled(10) : 10)
                            : aircraftMarker.x + aircraftMarker.width + (shellWindow ? shellWindow.scaled(10) : 10)
                        y: aircraftMarker.y + (aircraftMarker.height / 2) - (height / 2)
                        implicitWidth: aircraftColumn.implicitWidth + ((shellWindow ? shellWindow.scaled(14) : 14) * 2)
                        implicitHeight: aircraftColumn.implicitHeight + ((shellWindow ? shellWindow.scaled(8) : 8) * 2)

                        Column {
                            id: aircraftColumn
                            anchors.centerIn: parent
                            spacing: shellWindow ? shellWindow.scaled(1) : 1

                            Text {
                                text: String(panel["mission_call_sign"] || "M9-DEMO") + " / 当前机位"
                                color: shellWindow ? shellWindow.textStrong : "#f4fbff"
                                font.pixelSize: shellWindow ? shellWindow.captionSize : 11
                                font.bold: true
                                font.family: shellWindow ? shellWindow.uiFamily : "Noto Sans CJK SC"
                            }

                            Text {
                                text: root.latitudeLabel + "  " + root.longitudeLabel
                                color: shellWindow ? shellWindow.textPrimary : "#d5eeff"
                                font.pixelSize: shellWindow ? shellWindow.captionSize : 10
                                font.family: shellWindow ? shellWindow.monoFamily : "JetBrains Mono"
                            }
                        }
                    }

                    Rectangle {
                        id: missionDeckCard
                        width: root.missionDeckWidth
                        radius: shellWindow ? shellWindow.cardRadius : 14
                        gradient: Gradient {
                            GradientStop { position: 0.0; color: "#10273d" }
                            GradientStop { position: 0.46; color: "#0b1827" }
                            GradientStop { position: 1.0; color: "#081321" }
                        }
                        border.color: "#2b6f9d"
                        border.width: 1
                        anchors.left: parent.left
                        anchors.top: parent.top
                        anchors.leftMargin: root.stageDockMargin
                        anchors.topMargin: root.stageOverlayTopMargin
                        implicitHeight: missionColumn.implicitHeight + ((shellWindow ? shellWindow.scaled(12) : 12) * 2)

                        Rectangle {
                            width: parent.width * 0.58
                            height: parent.height * 0.74
                            radius: width / 2
                            color: root.accentBlue
                            opacity: 0.09
                            x: -width * 0.28
                            y: -height * 0.08
                        }

                        Rectangle {
                            width: parent.width * 0.44
                            height: parent.height * 0.42
                            radius: width / 2
                            color: root.accentCyan
                            opacity: 0.06
                            x: parent.width - (width * 0.72)
                            y: parent.height * 0.52
                        }

                        Rectangle {
                            anchors.fill: parent
                            anchors.margins: 1
                            radius: parent.radius - 1
                            color: "transparent"
                            border.color: "#123450"
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
                                GradientStop { position: 0.22; color: root.accentBlue }
                                GradientStop { position: 0.72; color: root.accentCyan }
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
                            gradient: Gradient {
                                GradientStop { position: 0.0; color: "transparent" }
                                GradientStop { position: 0.2; color: root.accentBlue }
                                GradientStop { position: 0.76; color: root.accentCyan }
                                GradientStop { position: 1.0; color: "transparent" }
                            }
                            opacity: 0.9
                        }

                        Column {
                            id: missionColumn
                            anchors.fill: parent
                            anchors.margins: shellWindow ? shellWindow.scaled(12) : 12
                            spacing: shellWindow ? shellWindow.scaled(4) : 4

                            Text {
                                text: "任务牌 / MISSION DECK"
                                color: shellWindow ? shellWindow.accentBlue : "#38b6ff"
                                font.pixelSize: shellWindow ? shellWindow.captionSize : 11
                                font.family: shellWindow ? shellWindow.monoFamily : "JetBrains Mono"
                                font.letterSpacing: shellWindow ? shellWindow.scaled(1) : 1
                            }

                            RowLayout {
                                width: parent.width
                                spacing: shellWindow ? shellWindow.compactGap : 8

                                Rectangle {
                                    radius: shellWindow ? shellWindow.edgeRadius : 10
                                    color: "#091726"
                                    border.color: "#1d547c"
                                    border.width: 1
                                    implicitWidth: missionDeckStamp.implicitWidth + ((shellWindow ? shellWindow.scaled(10) : 10) * 2)
                                    implicitHeight: missionDeckStamp.implicitHeight + ((shellWindow ? shellWindow.scaled(5) : 5) * 2)

                                    Text {
                                        id: missionDeckStamp
                                        anchors.centerIn: parent
                                        text: "DECK-L / CONTROL"
                                        color: shellWindow ? shellWindow.textPrimary : "#d5eeff"
                                        font.pixelSize: shellWindow ? shellWindow.captionSize : 9
                                        font.family: shellWindow ? shellWindow.monoFamily : "JetBrains Mono"
                                    }
                                }

                                Text {
                                    Layout.fillWidth: true
                                    text: root.sampleTimestamp
                                    color: shellWindow ? shellWindow.textMuted : "#4e7392"
                                    font.pixelSize: shellWindow ? shellWindow.captionSize : 10
                                    font.family: shellWindow ? shellWindow.monoFamily : "JetBrains Mono"
                                    horizontalAlignment: Text.AlignRight
                                    elide: Text.ElideRight
                                }
                            }

                            Text {
                                width: parent.width
                                text: String(panel["mission_call_sign"] || "M9-DEMO") + " / " + String(panel["aircraft_id"] || "FT-AIR-01")
                                color: shellWindow ? shellWindow.textStrong : "#f4fbff"
                                font.pixelSize: shellWindow ? shellWindow.bodyEmphasisSize : 15
                                font.bold: true
                                font.family: shellWindow ? shellWindow.uiFamily : "Noto Sans CJK SC"
                                wrapMode: Text.WordWrap
                            }

                            Text {
                                width: parent.width
                                text: "当前位置 " + root.latitudeLabel + "  " + root.longitudeLabel
                                color: shellWindow ? shellWindow.textPrimary : "#d5eeff"
                                font.pixelSize: shellWindow ? shellWindow.captionSize : 11
                                font.family: shellWindow ? shellWindow.monoFamily : "JetBrains Mono"
                                wrapMode: Text.WordWrap
                            }

                            Flow {
                                width: parent.width
                                spacing: shellWindow ? shellWindow.compactGap : 8

                                Repeater {
                                    model: [
                                        {
                                            "label": "LINK",
                                            "value": String(root.controlSummary["link_profile"] || "--"),
                                            "tone": "warning"
                                        },
                                        {
                                            "label": "PLAYBOOK",
                                            "value": recommendedScenarioId,
                                            "tone": "warning"
                                        }
                                    ]

                                    delegate: Rectangle {
                                        readonly property var deckBadge: modelData
                                        radius: shellWindow ? shellWindow.edgeRadius : 10
                                        gradient: Gradient {
                                            GradientStop { position: 0.0; color: Qt.lighter(root.toneFill(deckBadge["tone"]), 1.14) }
                                            GradientStop { position: 1.0; color: root.toneFill(deckBadge["tone"]) }
                                        }
                                        border.color: root.toneColor(deckBadge["tone"])
                                        border.width: 1
                                        height: deckBadgeColumn.implicitHeight + ((shellWindow ? shellWindow.scaled(6) : 6) * 2)
                                        width: Math.max(shellWindow ? shellWindow.scaled(96) : 96, deckBadgeColumn.implicitWidth + (shellWindow ? shellWindow.scaled(18) : 18))

                                        Column {
                                            id: deckBadgeColumn
                                            anchors.centerIn: parent
                                            spacing: 1

                                            Text {
                                                text: deckBadge["label"]
                                                color: shellWindow ? shellWindow.textMuted : "#4e7392"
                                                font.pixelSize: shellWindow ? shellWindow.captionSize : 9
                                                font.family: shellWindow ? shellWindow.monoFamily : "JetBrains Mono"
                                            }

                                            Text {
                                                text: deckBadge["value"]
                                                color: shellWindow ? shellWindow.textStrong : "#f4fbff"
                                                font.pixelSize: shellWindow ? shellWindow.captionSize : 10
                                                font.bold: true
                                                font.family: shellWindow ? shellWindow.monoFamily : "JetBrains Mono"
                                            }
                                        }
                                    }
                                }
                            }

                            Rectangle {
                                width: parent.width
                                radius: shellWindow ? shellWindow.edgeRadius : 10
                                gradient: Gradient {
                                    GradientStop { position: 0.0; color: Qt.lighter(root.toneFill(root.wallboardStatusTone), 1.16) }
                                    GradientStop { position: 1.0; color: root.toneFill(root.wallboardStatusTone) }
                                }
                                border.color: root.toneColor(root.wallboardStatusTone)
                                border.width: 1
                                implicitHeight: missionModeRow.implicitHeight + ((shellWindow ? shellWindow.scaled(8) : 8) * 2)

                                RowLayout {
                                    id: missionModeRow
                                    anchors.fill: parent
                                    anchors.margins: shellWindow ? shellWindow.scaled(8) : 8
                                    spacing: shellWindow ? shellWindow.compactGap : 8

                                    ColumnLayout {
                                        Layout.fillWidth: true
                                        spacing: 1

                                        Text {
                                            text: root.missionModeEnglish
                                            color: shellWindow ? shellWindow.textMuted : "#4e7392"
                                            font.pixelSize: shellWindow ? shellWindow.captionSize : 9
                                            font.family: shellWindow ? shellWindow.monoFamily : "JetBrains Mono"
                                            font.letterSpacing: shellWindow ? shellWindow.scaled(1) : 1
                                        }

                                        Text {
                                            text: root.missionModeLabel
                                            color: shellWindow ? shellWindow.textStrong : "#f4fbff"
                                            font.pixelSize: shellWindow ? shellWindow.captionSize : 11
                                            font.bold: true
                                            font.family: shellWindow ? shellWindow.uiFamily : "Noto Sans CJK SC"
                                            wrapMode: Text.WordWrap
                                        }
                                    }

                                    ColumnLayout {
                                        Layout.alignment: Qt.AlignTop
                                        spacing: 1

                                        Text {
                                            text: "TRACK AGE"
                                            color: shellWindow ? shellWindow.textMuted : "#4e7392"
                                            font.pixelSize: shellWindow ? shellWindow.captionSize : 9
                                            font.family: shellWindow ? shellWindow.monoFamily : "JetBrains Mono"
                                        }

                                        Text {
                                            text: root.trackAgeLabel
                                            color: shellWindow ? shellWindow.textPrimary : "#d5eeff"
                                            font.pixelSize: shellWindow ? shellWindow.captionSize : 11
                                            font.bold: true
                                            font.family: shellWindow ? shellWindow.monoFamily : "JetBrains Mono"
                                        }
                                    }
                                }
                            }

                            Rectangle {
                                width: parent.width
                                height: 1
                                color: "#18405f"
                            }

                            Rectangle {
                                width: parent.width
                                radius: shellWindow ? shellWindow.edgeRadius : 10
                                gradient: Gradient {
                                    GradientStop { position: 0.0; color: "#0b1a2a" }
                                    GradientStop { position: 1.0; color: "#091321" }
                                }
                                border.color: "#1b4f76"
                                border.width: 1
                                implicitHeight: missionNoteColumn.implicitHeight + ((shellWindow ? shellWindow.scaled(8) : 8) * 2)

                                Rectangle {
                                    anchors.left: parent.left
                                    anchors.top: parent.top
                                    anchors.bottom: parent.bottom
                                    anchors.margins: shellWindow ? shellWindow.scaled(8) : 8
                                    width: shellWindow ? shellWindow.scaled(3) : 3
                                    radius: width / 2
                                    color: root.toneColor(root.latestEventTone)
                                    opacity: 0.92
                                }

                                Column {
                                    id: missionNoteColumn
                                    anchors.fill: parent
                                    anchors.margins: shellWindow ? shellWindow.scaled(8) : 8
                                    anchors.leftMargin: (shellWindow ? shellWindow.scaled(8) : 8) + (shellWindow ? shellWindow.scaled(7) : 7)
                                    spacing: shellWindow ? shellWindow.scaled(2) : 2

                                    Text {
                                        text: "事件摘记 / EVENT NOTE"
                                        color: shellWindow ? shellWindow.textMuted : "#4e7392"
                                        font.pixelSize: shellWindow ? shellWindow.captionSize : 10
                                        font.family: shellWindow ? shellWindow.monoFamily : "JetBrains Mono"
                                    }

                                    Text {
                                        width: parent.width
                                        text: compactMessage(controlSummary["last_event_message"], root.wallboardStatusDetail, 96)
                                        color: shellWindow ? shellWindow.textSecondary : "#83acc8"
                                        font.pixelSize: shellWindow ? shellWindow.captionSize : 11
                                        font.family: shellWindow ? shellWindow.uiFamily : "Noto Sans CJK SC"
                                        wrapMode: Text.WordWrap
                                    }
                                }
                            }

                            GridLayout {
                                width: parent.width
                                columns: compactCardLayout ? 1 : 2
                                columnSpacing: shellWindow ? shellWindow.compactGap : 8
                                rowSpacing: shellWindow ? shellWindow.compactGap : 8

                                Repeater {
                                    model: [
                                        {
                                            "label": "链路",
                                            "value": String(root.controlSummary["link_profile"] || "--"),
                                            "tone": "warning"
                                        },
                                        {
                                            "label": "弱网",
                                            "value": recommendedScenarioId,
                                            "tone": "warning"
                                        },
                                        {
                                            "label": "源状态",
                                            "value": root.sourceStatusLabel(),
                                            "tone": "neutral"
                                        },
                                        {
                                            "label": "锚点",
                                            "value": compactMessage(liveAnchorData["board_status"], "状态未知", 18),
                                            "tone": String(liveAnchorData["tone"] || "neutral")
                                        }
                                    ]

                                    delegate: Rectangle {
                                        readonly property var deckMetric: modelData
                                        Layout.fillWidth: true
                                        radius: shellWindow ? shellWindow.edgeRadius : 10
                                        gradient: Gradient {
                                            GradientStop { position: 0.0; color: Qt.lighter(root.toneFill(deckMetric["tone"]), 1.12) }
                                            GradientStop { position: 1.0; color: root.toneFill(deckMetric["tone"]) }
                                        }
                                        border.color: root.toneColor(deckMetric["tone"])
                                        border.width: 1
                                        implicitHeight: deckColumn.implicitHeight + ((shellWindow ? shellWindow.scaled(8) : 8) * 2)

                                        Column {
                                            id: deckColumn
                                            anchors.fill: parent
                                            anchors.margins: shellWindow ? shellWindow.scaled(8) : 8
                                            spacing: shellWindow ? shellWindow.scaled(2) : 2

                                            Text {
                                                text: deckMetric["label"]
                                                color: shellWindow ? shellWindow.textMuted : "#4e7392"
                                                font.pixelSize: shellWindow ? shellWindow.captionSize : 10
                                                font.family: shellWindow ? shellWindow.monoFamily : "JetBrains Mono"
                                            }

                                            Text {
                                                width: parent.width
                                                text: deckMetric["value"]
                                                color: shellWindow ? shellWindow.textStrong : "#f4fbff"
                                                font.pixelSize: shellWindow ? shellWindow.captionSize : 11
                                                font.bold: true
                                                font.family: shellWindow ? shellWindow.monoFamily : "JetBrains Mono"
                                                wrapMode: Text.WordWrap
                                            }
                                        }
                                    }
                                }
                            }
                        }

                        Rectangle {
                            visible: !compactCardLayout
                            anchors.left: parent.right
                            anchors.verticalCenter: parent.verticalCenter
                            width: root.stageConnectorSpan
                            height: shellWindow ? shellWindow.scaled(2) : 2
                            gradient: Gradient {
                                orientation: Gradient.Horizontal
                                GradientStop { position: 0.0; color: root.accentBlue }
                                GradientStop { position: 0.72; color: root.accentCyan }
                                GradientStop { position: 1.0; color: "transparent" }
                            }
                            opacity: 0.82
                        }

                        Rectangle {
                            visible: !compactCardLayout
                            width: shellWindow ? shellWindow.scaled(8) : 8
                            height: width
                            radius: width / 2
                            color: root.accentCyan
                            border.color: "#ffffff"
                            border.width: 1
                            anchors.left: parent.right
                            anchors.leftMargin: root.stageConnectorSpan - (width / 2)
                            anchors.verticalCenter: parent.verticalCenter
                        }
                    }

                    Rectangle {
                        visible: !compactCardLayout
                        width: shellWindow ? shellWindow.scaled(2) : 2
                        anchors.horizontalCenter: missionDeckCard.horizontalCenter
                        anchors.top: missionDeckCard.bottom
                        anchors.bottom: footerAuditRail.top
                        anchors.topMargin: shellWindow ? shellWindow.scaled(8) : 8
                        anchors.bottomMargin: shellWindow ? shellWindow.scaled(10) : 10
                        gradient: Gradient {
                            GradientStop { position: 0.0; color: root.accentBlue }
                            GradientStop { position: 0.76; color: root.accentCyan }
                            GradientStop { position: 1.0; color: "transparent" }
                        }
                        opacity: 0.74
                    }

                    Rectangle {
                        visible: !compactCardLayout
                        width: shellWindow ? shellWindow.scaled(8) : 8
                        height: width
                        radius: width / 2
                        color: root.accentBlue
                        border.color: "#ffffff"
                        border.width: 1
                        anchors.horizontalCenter: missionDeckCard.horizontalCenter
                        anchors.bottom: footerAuditRail.top
                        anchors.bottomMargin: shellWindow ? shellWindow.scaled(6) : 6
                    }

                    Rectangle {
                        visible: !compactCardLayout
                        id: telemetryRailCard
                        width: root.telemetryRailWidth
                        radius: shellWindow ? shellWindow.cardRadius : 14
                        gradient: Gradient {
                            GradientStop { position: 0.0; color: "#10273d" }
                            GradientStop { position: 0.42; color: "#0c1a28" }
                            GradientStop { position: 1.0; color: "#081321" }
                        }
                        border.color: "#2b6f9d"
                        border.width: 1
                        anchors.right: parent.right
                        anchors.top: parent.top
                        anchors.rightMargin: root.stageDockMargin
                        anchors.topMargin: root.stageOverlayTopMargin
                        implicitHeight: railColumn.implicitHeight + ((shellWindow ? shellWindow.scaled(12) : 12) * 2)

                        Rectangle {
                            width: parent.width * 0.52
                            height: parent.height * 0.66
                            radius: width / 2
                            color: root.accentCyan
                            opacity: 0.07
                            x: parent.width - (width * 0.72)
                            y: -height * 0.1
                        }

                        Rectangle {
                            anchors.fill: parent
                            anchors.margins: 1
                            radius: parent.radius - 1
                            color: "transparent"
                            border.color: "#123450"
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
                                GradientStop { position: 0.22; color: root.accentBlue }
                                GradientStop { position: 0.72; color: root.accentCyan }
                                GradientStop { position: 1.0; color: "transparent" }
                            }
                            opacity: 0.78
                        }

                        Rectangle {
                            anchors.right: parent.right
                            anchors.top: parent.top
                            anchors.bottom: parent.bottom
                            anchors.margins: shellWindow ? shellWindow.scaled(10) : 10
                            width: shellWindow ? shellWindow.scaled(4) : 4
                            radius: width / 2
                            gradient: Gradient {
                                GradientStop { position: 0.0; color: "transparent" }
                                GradientStop { position: 0.2; color: root.accentBlue }
                                GradientStop { position: 0.76; color: root.accentCyan }
                                GradientStop { position: 1.0; color: "transparent" }
                            }
                            opacity: 0.88
                        }

                        Column {
                            id: railColumn
                            anchors.fill: parent
                            anchors.margins: shellWindow ? shellWindow.scaled(12) : 12
                            spacing: shellWindow ? shellWindow.scaled(6) : 6

                            RowLayout {
                                width: parent.width
                                spacing: shellWindow ? shellWindow.compactGap : 8

                                Text {
                                    Layout.fillWidth: true
                                    text: "飞行遥测 / TELEMETRY RAIL"
                                    color: shellWindow ? shellWindow.accentBlue : "#38b6ff"
                                    font.pixelSize: shellWindow ? shellWindow.captionSize : 11
                                    font.family: shellWindow ? shellWindow.monoFamily : "JetBrains Mono"
                                    font.letterSpacing: shellWindow ? shellWindow.scaled(1) : 1
                                }

                                Rectangle {
                                    radius: shellWindow ? shellWindow.edgeRadius : 10
                                    color: "#091726"
                                    border.color: "#1d547c"
                                    border.width: 1
                                    implicitWidth: telemetryStamp.implicitWidth + ((shellWindow ? shellWindow.scaled(10) : 10) * 2)
                                    implicitHeight: telemetryStamp.implicitHeight + ((shellWindow ? shellWindow.scaled(5) : 5) * 2)

                                    Text {
                                        id: telemetryStamp
                                        anchors.centerIn: parent
                                        text: String(root.railMetrics.length) + " FEEDS"
                                        color: shellWindow ? shellWindow.textPrimary : "#d5eeff"
                                        font.pixelSize: shellWindow ? shellWindow.captionSize : 9
                                        font.family: shellWindow ? shellWindow.monoFamily : "JetBrains Mono"
                                    }
                                }
                            }

                            RowLayout {
                                width: parent.width
                                spacing: shellWindow ? shellWindow.compactGap : 8

                                Rectangle {
                                    radius: shellWindow ? shellWindow.edgeRadius : 10
                                    color: "#091726"
                                    border.color: "#1d547c"
                                    border.width: 1
                                    implicitWidth: telemetryBusStamp.implicitWidth + ((shellWindow ? shellWindow.scaled(10) : 10) * 2)
                                    implicitHeight: telemetryBusStamp.implicitHeight + ((shellWindow ? shellWindow.scaled(5) : 5) * 2)

                                    Text {
                                        id: telemetryBusStamp
                                        anchors.centerIn: parent
                                        text: "RAIL-R / LIVE"
                                        color: shellWindow ? shellWindow.textPrimary : "#d5eeff"
                                        font.pixelSize: shellWindow ? shellWindow.captionSize : 9
                                        font.family: shellWindow ? shellWindow.monoFamily : "JetBrains Mono"
                                    }
                                }

                                Text {
                                    Layout.fillWidth: true
                                    text: compactMessage(String(liveAnchorData["board_status"] || root.sampleTimestamp), root.sampleTimestamp, 34)
                                    color: shellWindow ? shellWindow.textMuted : "#4e7392"
                                    font.pixelSize: shellWindow ? shellWindow.captionSize : 10
                                    font.family: shellWindow ? shellWindow.monoFamily : "JetBrains Mono"
                                    horizontalAlignment: Text.AlignRight
                                    elide: Text.ElideRight
                                }
                            }

                            Repeater {
                                model: root.railMetrics

                                delegate: Rectangle {
                                    readonly property var metric: modelData
                                    width: parent.width
                                    radius: shellWindow ? shellWindow.edgeRadius : 10
                                    gradient: Gradient {
                                        GradientStop { position: 0.0; color: Qt.lighter(root.toneFill(metric["tone"]), 1.12) }
                                        GradientStop { position: 1.0; color: root.toneFill(metric["tone"]) }
                                    }
                                    border.color: root.toneColor(metric["tone"])
                                    border.width: 1
                                    implicitHeight: railMetricColumn.implicitHeight + ((shellWindow ? shellWindow.scaled(8) : 8) * 2)

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
                                        opacity: 0.76
                                    }

                                    Column {
                                        id: railMetricColumn
                                        anchors.fill: parent
                                        anchors.margins: shellWindow ? shellWindow.scaled(8) : 8
                                        spacing: shellWindow ? shellWindow.scaled(2) : 2

                                        Text {
                                            text: metric["label"]
                                            color: shellWindow ? shellWindow.textMuted : "#4e7392"
                                            font.pixelSize: shellWindow ? shellWindow.captionSize : 10
                                            font.family: shellWindow ? shellWindow.monoFamily : "JetBrains Mono"
                                        }

                                        Text {
                                            text: metric["value"]
                                            color: shellWindow ? shellWindow.textStrong : "#f4fbff"
                                            font.pixelSize: shellWindow ? shellWindow.bodyEmphasisSize : 15
                                            font.bold: true
                                            font.family: shellWindow ? shellWindow.monoFamily : "JetBrains Mono"
                                        }

                                        Text {
                                            text: metric["detail"]
                                            color: shellWindow ? shellWindow.textSecondary : "#83acc8"
                                            font.pixelSize: shellWindow ? shellWindow.captionSize : 10
                                            font.family: shellWindow ? shellWindow.uiFamily : "Noto Sans CJK SC"
                                        }
                                    }
                                }
                            }

                            Rectangle {
                                width: parent.width
                                height: 1
                                color: "#123b5b"
                                opacity: 0.92
                            }

                            Text {
                                text: "事件哨兵 / WATCHLIST"
                                color: shellWindow ? shellWindow.accentCyan : "#72f3ff"
                                font.pixelSize: shellWindow ? shellWindow.captionSize : 11
                                font.family: shellWindow ? shellWindow.monoFamily : "JetBrains Mono"
                            }

                            Repeater {
                                model: root.watchlistModel

                                delegate: Rectangle {
                                    readonly property var watch: modelData
                                    width: parent.width
                                    radius: shellWindow ? shellWindow.edgeRadius : 10
                                    gradient: Gradient {
                                        GradientStop { position: 0.0; color: "#102133" }
                                        GradientStop { position: 1.0; color: "#091421" }
                                    }
                                    border.color: root.toneColor(watch["tone"])
                                    border.width: 1
                                    implicitHeight: watchColumn.implicitHeight + ((shellWindow ? shellWindow.scaled(8) : 8) * 2)

                                    Rectangle {
                                        anchors.left: parent.left
                                        anchors.top: parent.top
                                        anchors.bottom: parent.bottom
                                        anchors.margins: shellWindow ? shellWindow.scaled(8) : 8
                                        width: shellWindow ? shellWindow.scaled(3) : 3
                                        radius: width / 2
                                        color: root.toneColor(watch["tone"])
                                        opacity: 0.9
                                    }

                                    Column {
                                        id: watchColumn
                                        anchors.fill: parent
                                        anchors.margins: shellWindow ? shellWindow.scaled(8) : 8
                                        anchors.leftMargin: (shellWindow ? shellWindow.scaled(8) : 8) + (shellWindow ? shellWindow.scaled(7) : 7)
                                        spacing: shellWindow ? shellWindow.scaled(2) : 2

                                        Text {
                                            text: watch["label"]
                                            color: shellWindow ? shellWindow.textMuted : "#4e7392"
                                            font.pixelSize: shellWindow ? shellWindow.captionSize : 9
                                            font.family: shellWindow ? shellWindow.monoFamily : "JetBrains Mono"
                                        }

                                        Text {
                                            text: watch["value"]
                                            color: shellWindow ? shellWindow.textStrong : "#f4fbff"
                                            font.pixelSize: shellWindow ? shellWindow.captionSize : 11
                                            font.bold: true
                                            font.family: shellWindow ? shellWindow.monoFamily : "JetBrains Mono"
                                            wrapMode: Text.WordWrap
                                        }

                                        Text {
                                            width: parent.width
                                            text: watch["detail"]
                                            color: shellWindow ? shellWindow.textSecondary : "#83acc8"
                                            font.pixelSize: shellWindow ? shellWindow.captionSize : 10
                                            font.family: shellWindow ? shellWindow.uiFamily : "Noto Sans CJK SC"
                                            wrapMode: Text.WordWrap
                                        }
                                    }
                                }
                            }
                        }

                        Rectangle {
                            visible: !compactCardLayout
                            anchors.right: parent.left
                            anchors.verticalCenter: parent.verticalCenter
                            width: root.stageConnectorSpan
                            height: shellWindow ? shellWindow.scaled(2) : 2
                            gradient: Gradient {
                                orientation: Gradient.Horizontal
                                GradientStop { position: 0.0; color: "transparent" }
                                GradientStop { position: 0.28; color: root.accentBlue }
                                GradientStop { position: 1.0; color: root.accentCyan }
                            }
                            opacity: 0.82
                        }

                        Rectangle {
                            visible: !compactCardLayout
                            width: shellWindow ? shellWindow.scaled(8) : 8
                            height: width
                            radius: width / 2
                            color: root.accentCyan
                            border.color: "#ffffff"
                            border.width: 1
                            anchors.right: parent.left
                            anchors.rightMargin: root.stageConnectorSpan - (width / 2)
                            anchors.verticalCenter: parent.verticalCenter
                        }
                    }

                    Rectangle {
                        visible: !compactCardLayout
                        width: shellWindow ? shellWindow.scaled(2) : 2
                        anchors.horizontalCenter: telemetryRailCard.horizontalCenter
                        anchors.top: telemetryRailCard.bottom
                        anchors.bottom: footerAuditRail.top
                        anchors.topMargin: shellWindow ? shellWindow.scaled(8) : 8
                        anchors.bottomMargin: shellWindow ? shellWindow.scaled(10) : 10
                        gradient: Gradient {
                            GradientStop { position: 0.0; color: root.accentCyan }
                            GradientStop { position: 0.76; color: root.accentBlue }
                            GradientStop { position: 1.0; color: "transparent" }
                        }
                        opacity: 0.74
                    }

                    Rectangle {
                        visible: !compactCardLayout
                        width: shellWindow ? shellWindow.scaled(8) : 8
                        height: width
                        radius: width / 2
                        color: root.accentCyan
                        border.color: "#ffffff"
                        border.width: 1
                        anchors.horizontalCenter: telemetryRailCard.horizontalCenter
                        anchors.bottom: footerAuditRail.top
                        anchors.bottomMargin: shellWindow ? shellWindow.scaled(6) : 6
                    }

                    Rectangle {
                        visible: !compactCardLayout
                        id: projectionRailCard
                        anchors.horizontalCenter: parent.horizontalCenter
                        anchors.bottom: parent.bottom
                        anchors.bottomMargin: root.stageProjectionBottomMargin
                        width: Math.min(parent.width - ((shellWindow ? shellWindow.scaled(180) : 180) * 2), shellWindow ? shellWindow.scaled(720) : 720)
                        radius: shellWindow ? shellWindow.cardRadius : 14
                        gradient: Gradient {
                            GradientStop { position: 0.0; color: "#0d2032" }
                            GradientStop { position: 0.55; color: "#081321" }
                            GradientStop { position: 1.0; color: "#071018" }
                        }
                        border.color: "#2a6e9e"
                        border.width: 1
                        implicitHeight: projectionColumn.implicitHeight + ((shellWindow ? shellWindow.scaled(12) : 12) * 2)

                        Rectangle {
                            width: parent.width * 0.48
                            height: parent.height * 0.92
                            radius: width / 2
                            color: root.accentBlue
                            opacity: 0.08
                            anchors.horizontalCenter: parent.horizontalCenter
                            y: -height * 0.28
                        }

                        Rectangle {
                            anchors.fill: parent
                            anchors.margins: 1
                            radius: parent.radius - 1
                            color: "transparent"
                            border.color: "#123450"
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
                                GradientStop { position: 0.22; color: root.accentBlue }
                                GradientStop { position: 0.72; color: root.accentCyan }
                                GradientStop { position: 1.0; color: "transparent" }
                            }
                            opacity: 0.78
                        }

                        Rectangle {
                            visible: !compactCardLayout
                            width: shellWindow ? shellWindow.scaled(2) : 2
                            height: shellWindow ? shellWindow.scaled(34) : 34
                            anchors.horizontalCenter: parent.horizontalCenter
                            anchors.bottom: parent.top
                            gradient: Gradient {
                                GradientStop { position: 0.0; color: root.accentCyan }
                                GradientStop { position: 0.62; color: root.accentBlue }
                                GradientStop { position: 1.0; color: "transparent" }
                            }
                            opacity: 0.82
                        }

                        Rectangle {
                            visible: !compactCardLayout
                            width: shellWindow ? shellWindow.scaled(8) : 8
                            height: width
                            radius: width / 2
                            color: root.accentCyan
                            border.color: "#ffffff"
                            border.width: 1
                            anchors.horizontalCenter: parent.horizontalCenter
                            anchors.bottom: parent.top
                        }

                        ColumnLayout {
                            id: projectionColumn
                            anchors.fill: parent
                            anchors.margins: shellWindow ? shellWindow.scaled(12) : 12
                            spacing: shellWindow ? shellWindow.compactGap : 8

                            RowLayout {
                                Layout.fillWidth: true
                                spacing: shellWindow ? shellWindow.compactGap : 8

                                ColumnLayout {
                                    Layout.fillWidth: true
                                    spacing: 1

                                    Text {
                                        text: "投影遥测 / PROJECTION TELEMETRY"
                                        color: shellWindow ? shellWindow.accentBlue : "#38b6ff"
                                        font.pixelSize: shellWindow ? shellWindow.captionSize : 11
                                        font.family: shellWindow ? shellWindow.monoFamily : "JetBrains Mono"
                                        font.letterSpacing: shellWindow ? shellWindow.scaled(1) : 1
                                    }

                                    Text {
                                        text: root.missionFocusLabel
                                        color: shellWindow ? shellWindow.textSecondary : "#83acc8"
                                        font.pixelSize: shellWindow ? shellWindow.captionSize : 11
                                        font.family: shellWindow ? shellWindow.uiFamily : "Noto Sans CJK SC"
                                        wrapMode: Text.WordWrap
                                    }
                                }

                                Rectangle {
                                    Layout.alignment: Qt.AlignTop
                                    radius: shellWindow ? shellWindow.edgeRadius : 10
                                    color: "#091726"
                                    border.color: "#1c547c"
                                    border.width: 1
                                    implicitWidth: projectionStamp.implicitWidth + ((shellWindow ? shellWindow.scaled(12) : 12) * 2)
                                    implicitHeight: projectionStamp.implicitHeight + ((shellWindow ? shellWindow.scaled(6) : 6) * 2)

                                    Text {
                                        id: projectionStamp
                                        anchors.centerIn: parent
                                        text: String(Number(root.trackData.length || 0).toFixed(0)) + " TRACK NODES"
                                        color: shellWindow ? shellWindow.textPrimary : "#d5eeff"
                                        font.pixelSize: shellWindow ? shellWindow.captionSize : 10
                                        font.family: shellWindow ? shellWindow.monoFamily : "JetBrains Mono"
                                    }
                                }
                            }

                            Flow {
                                Layout.fillWidth: true
                                spacing: shellWindow ? shellWindow.compactGap : 8

                                Repeater {
                                    model: root.stageBannerModel

                                    delegate: Rectangle {
                                        readonly property var banner: modelData
                                        radius: shellWindow ? shellWindow.edgeRadius : 10
                                        gradient: Gradient {
                                            GradientStop { position: 0.0; color: Qt.lighter(root.toneFill(banner["tone"]), 1.12) }
                                            GradientStop { position: 1.0; color: root.toneFill(banner["tone"]) }
                                        }
                                        border.color: root.toneColor(banner["tone"])
                                        border.width: 1
                                        height: bannerColumn.implicitHeight + ((shellWindow ? shellWindow.scaled(8) : 8) * 2)
                                        width: Math.max(shellWindow ? shellWindow.scaled(148) : 148, bannerColumn.implicitWidth + (shellWindow ? shellWindow.scaled(22) : 22))

                                        Rectangle {
                                            anchors.fill: parent
                                            anchors.margins: 1
                                            radius: parent.radius - 1
                                            color: "transparent"
                                            border.color: "#102f48"
                                            border.width: 1
                                            opacity: 0.82
                                        }

                                        Rectangle {
                                            anchors.left: parent.left
                                            anchors.right: parent.right
                                            anchors.top: parent.top
                                            height: shellWindow ? shellWindow.scaled(2) : 2
                                            gradient: Gradient {
                                                GradientStop { position: 0.0; color: "transparent" }
                                                GradientStop { position: 0.28; color: root.toneColor(banner["tone"]) }
                                                GradientStop { position: 0.72; color: Qt.lighter(root.toneColor(banner["tone"]), 1.16) }
                                                GradientStop { position: 1.0; color: "transparent" }
                                            }
                                            opacity: 0.76
                                        }

                                        Column {
                                            id: bannerColumn
                                            anchors.centerIn: parent
                                            spacing: 2

                                            Text {
                                                text: banner["label"]
                                                color: shellWindow ? shellWindow.textMuted : "#4e7392"
                                                font.pixelSize: shellWindow ? shellWindow.captionSize : 9
                                                font.family: shellWindow ? shellWindow.monoFamily : "JetBrains Mono"
                                                font.letterSpacing: shellWindow ? shellWindow.scaled(1) : 1
                                            }

                                            Text {
                                                text: banner["value"]
                                                color: shellWindow ? shellWindow.textStrong : "#f4fbff"
                                                font.pixelSize: shellWindow ? shellWindow.captionSize : 11
                                                font.bold: true
                                                font.family: shellWindow ? shellWindow.monoFamily : "JetBrains Mono"
                                                wrapMode: Text.WrapAnywhere
                                            }

                                            Text {
                                                text: banner["detail"]
                                                color: shellWindow ? shellWindow.textSecondary : "#83acc8"
                                                font.pixelSize: shellWindow ? shellWindow.captionSize : 10
                                                font.family: shellWindow ? shellWindow.uiFamily : "Noto Sans CJK SC"
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }

                    Rectangle {
                        visible: !compactCardLayout
                        width: shellWindow ? shellWindow.scaled(2) : 2
                        anchors.horizontalCenter: projectionRailCard.horizontalCenter
                        anchors.top: projectionRailCard.bottom
                        anchors.bottom: footerAuditRail.top
                        anchors.topMargin: shellWindow ? shellWindow.scaled(8) : 8
                        anchors.bottomMargin: shellWindow ? shellWindow.scaled(10) : 10
                        gradient: Gradient {
                            GradientStop { position: 0.0; color: root.accentCyan }
                            GradientStop { position: 0.72; color: root.accentBlue }
                            GradientStop { position: 1.0; color: "transparent" }
                        }
                        opacity: 0.72
                    }

                    Rectangle {
                        visible: !compactCardLayout
                        width: shellWindow ? shellWindow.scaled(8) : 8
                        height: width
                        radius: width / 2
                        color: root.accentCyan
                        border.color: "#ffffff"
                        border.width: 1
                        anchors.horizontalCenter: projectionRailCard.horizontalCenter
                        anchors.bottom: footerAuditRail.top
                        anchors.bottomMargin: shellWindow ? shellWindow.scaled(6) : 6
                    }

                    Rectangle {
                        id: footerAuditRail
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.bottom: parent.bottom
                        anchors.leftMargin: root.stageDockMargin
                        anchors.rightMargin: root.stageDockMargin
                        anchors.bottomMargin: root.stageDockMargin
                        radius: shellWindow ? shellWindow.edgeRadius : 10
                        gradient: Gradient {
                            GradientStop { position: 0.0; color: "#081524" }
                            GradientStop { position: 1.0; color: "#0a1928" }
                        }
                        border.color: "#265f89"
                        border.width: 1
                        implicitHeight: footerRailColumn.implicitHeight + ((shellWindow ? shellWindow.scaled(10) : 10) * 2)

                        Rectangle {
                            width: parent.width * 0.42
                            height: parent.height * 0.9
                            radius: width / 2
                            color: root.accentBlue
                            opacity: 0.06
                            x: -width * 0.24
                            y: -height * 0.18
                        }

                        Rectangle {
                            anchors.fill: parent
                            anchors.margins: 1
                            radius: parent.radius - 1
                            color: "transparent"
                            border.color: "#133450"
                            border.width: 1
                            opacity: 0.8
                        }

                        Column {
                            id: footerRailColumn
                            anchors.fill: parent
                            anchors.margins: shellWindow ? shellWindow.scaled(10) : 10
                            spacing: shellWindow ? shellWindow.scaled(8) : 8

                            RowLayout {
                                width: parent.width
                                spacing: shellWindow ? shellWindow.compactGap : 8

                                Text {
                                    Layout.fillWidth: true
                                    text: "审计底栏 / AUDIT RAIL"
                                    color: shellWindow ? shellWindow.accentBlue : "#38b6ff"
                                    font.pixelSize: shellWindow ? shellWindow.captionSize : 11
                                    font.family: shellWindow ? shellWindow.monoFamily : "JetBrains Mono"
                                    font.letterSpacing: shellWindow ? shellWindow.scaled(1) : 1
                                }

                                Rectangle {
                                    Layout.alignment: Qt.AlignTop
                                    radius: shellWindow ? shellWindow.edgeRadius : 10
                                    color: "#091726"
                                    border.color: "#1d547c"
                                    border.width: 1
                                    implicitWidth: auditStamp.implicitWidth + ((shellWindow ? shellWindow.scaled(10) : 10) * 2)
                                    implicitHeight: auditStamp.implicitHeight + ((shellWindow ? shellWindow.scaled(5) : 5) * 2)

                                    Text {
                                        id: auditStamp
                                        anchors.centerIn: parent
                                        text: root.stageEnvelopeStamp
                                        color: shellWindow ? shellWindow.textPrimary : "#d5eeff"
                                        font.pixelSize: shellWindow ? shellWindow.captionSize : 9
                                        font.family: shellWindow ? shellWindow.monoFamily : "JetBrains Mono"
                                    }
                                }
                            }

                            GridLayout {
                                id: footerGrid
                                width: parent.width
                                columns: compactCardLayout ? 1 : 4
                                columnSpacing: shellWindow ? shellWindow.compactGap : 8
                                rowSpacing: shellWindow ? shellWindow.compactGap : 8

                                Repeater {
                                    model: root.footerModel

                                    delegate: Rectangle {
                                        readonly property var footerItem: modelData
                                        Layout.fillWidth: true
                                        radius: shellWindow ? shellWindow.edgeRadius : 10
                                        gradient: Gradient {
                                            GradientStop { position: 0.0; color: "#0a1625" }
                                            GradientStop { position: 1.0; color: "#091321" }
                                        }
                                        border.color: root.toneColor(footerItem["tone"])
                                        border.width: 1
                                        implicitHeight: footerColumn.implicitHeight + ((shellWindow ? shellWindow.scaled(8) : 8) * 2)

                                        Rectangle {
                                            anchors.fill: parent
                                            anchors.margins: 1
                                            radius: parent.radius - 1
                                            color: "transparent"
                                            border.color: "#102f48"
                                            border.width: 1
                                            opacity: 0.82
                                        }

                                        Rectangle {
                                            anchors.left: parent.left
                                            anchors.right: parent.right
                                            anchors.top: parent.top
                                            height: shellWindow ? shellWindow.scaled(2) : 2
                                            gradient: Gradient {
                                                GradientStop { position: 0.0; color: "transparent" }
                                                GradientStop { position: 0.28; color: root.toneColor(footerItem["tone"]) }
                                                GradientStop { position: 0.72; color: Qt.lighter(root.toneColor(footerItem["tone"]), 1.16) }
                                                GradientStop { position: 1.0; color: "transparent" }
                                            }
                                            opacity: 0.74
                                        }

                                        Column {
                                            id: footerColumn
                                            anchors.fill: parent
                                            anchors.margins: shellWindow ? shellWindow.scaled(8) : 8
                                            spacing: shellWindow ? shellWindow.scaled(2) : 2

                                            Text {
                                                text: footerItem["title"]
                                                color: shellWindow ? shellWindow.textMuted : "#4e7392"
                                                font.pixelSize: shellWindow ? shellWindow.captionSize : 10
                                                font.family: shellWindow ? shellWindow.monoFamily : "JetBrains Mono"
                                            }

                                            Text {
                                                width: parent.width
                                                text: footerItem["value"]
                                                color: shellWindow ? shellWindow.textPrimary : "#d5eeff"
                                                font.pixelSize: shellWindow ? shellWindow.captionSize : 11
                                                font.bold: true
                                                font.family: shellWindow ? shellWindow.monoFamily : "JetBrains Mono"
                                                wrapMode: Text.WordWrap
                                            }

                                            Text {
                                                width: parent.width
                                                text: footerItem["detail"]
                                                color: shellWindow ? shellWindow.textSecondary : "#83acc8"
                                                font.pixelSize: shellWindow ? shellWindow.captionSize : 10
                                                font.family: shellWindow ? shellWindow.uiFamily : "Noto Sans CJK SC"
                                                wrapMode: Text.WordWrap
                                                maximumLineCount: compactCardLayout ? 3 : 2
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
        }

        GridLayout {
            Layout.fillWidth: true
            columns: root.metricColumns
            columnSpacing: shellWindow ? shellWindow.zoneGap : 12
            rowSpacing: shellWindow ? shellWindow.zoneGap : 12

            Repeater {
                model: [
                    {
                        "eyebrow": "定位基准",
                        "title": "机位",
                        "value": "LAT " + Number(positionData["latitude"] || 0).toFixed(6),
                        "detail": "LON " + Number(positionData["longitude"] || 0).toFixed(6),
                        "note": "FIX " + String(fixData["type"] || "") + " / ±" + Number(fixData["confidence_m"] || 0).toFixed(1) + " m / SAT " + Number(fixData["satellites"] || 0).toFixed(0),
                        "tone": "neutral"
                    },
                    {
                        "eyebrow": "飞行动力",
                        "title": "机动",
                        "value": "ALT " + Number(kinematicsData["altitude_m"] || 0).toFixed(1) + " m",
                        "detail": "GS  " + Number(kinematicsData["ground_speed_kph"] || 0).toFixed(1) + " kph",
                        "note": "VS  " + Number(kinematicsData["vertical_speed_mps"] || 0).toFixed(1) + " m/s",
                        "tone": "warning"
                    },
                    {
                        "eyebrow": "控制摘要",
                        "title": "链路",
                        "value": String(controlSummary["link_profile"] || "--"),
                        "detail": "Last Job " + String(controlSummary["last_job_id"] || "--"),
                        "note": String(controlSummary["last_event_message"] || ""),
                        "tone": "online"
                    },
                    {
                        "eyebrow": "数据合同",
                        "title": "来源",
                        "value": root.sourceLabel(),
                        "detail": "API " + String(panel["source_api_path"] || feedContractData["api_path"] || ""),
                        "note": String(feedContractData["summary"] || panel["ownership_note"] || ""),
                        "tone": "neutral"
                    }
                ]

                delegate: Rectangle {
                    readonly property var card: modelData
                    Layout.fillWidth: true
                    radius: shellWindow ? shellWindow.cardRadius : 14
                    gradient: Gradient {
                        GradientStop { position: 0.0; color: "#0d2032" }
                        GradientStop { position: 1.0; color: "#081321" }
                    }
                    border.color: root.toneColor(card["tone"])
                    border.width: 1
                    implicitHeight: metricColumn.implicitHeight + ((shellWindow ? shellWindow.cardPadding : 14) * 2)

                    Rectangle {
                        width: parent.width * 0.46
                        height: parent.height * 0.92
                        radius: width / 2
                        color: root.toneColor(card["tone"])
                        opacity: 0.08
                        x: -width * 0.24
                        y: -height * 0.24
                    }

                    Rectangle {
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.top: parent.top
                        height: shellWindow ? shellWindow.scaled(3) : 3
                        gradient: Gradient {
                            GradientStop { position: 0.0; color: "transparent" }
                            GradientStop { position: 0.28; color: root.toneColor(card["tone"]) }
                            GradientStop { position: 0.74; color: Qt.lighter(root.toneColor(card["tone"]), 1.18) }
                            GradientStop { position: 1.0; color: "transparent" }
                        }
                        opacity: 0.72
                    }

                    Rectangle {
                        anchors.left: parent.left
                        anchors.top: parent.top
                        anchors.bottom: parent.bottom
                        anchors.margins: shellWindow ? shellWindow.scaled(10) : 10
                        width: shellWindow ? shellWindow.scaled(4) : 4
                        radius: width / 2
                        color: root.toneColor(card["tone"])
                        opacity: 0.9
                    }

                    Column {
                        id: metricColumn
                        anchors.fill: parent
                        anchors.margins: shellWindow ? shellWindow.cardPadding : 14
                        anchors.leftMargin: (shellWindow ? shellWindow.cardPadding : 14) + (shellWindow ? shellWindow.scaled(8) : 8)
                        spacing: shellWindow ? shellWindow.scaled(4) : 4

                        Text {
                            text: card["eyebrow"]
                            color: shellWindow ? shellWindow.textMuted : "#4e7392"
                            font.pixelSize: shellWindow ? shellWindow.captionSize : 11
                            font.family: shellWindow ? shellWindow.uiFamily : "Noto Sans CJK SC"
                        }

                        Text {
                            text: card["title"]
                            color: root.toneColor(card["tone"])
                            font.pixelSize: shellWindow ? shellWindow.bodySize : 13
                            font.bold: true
                            font.family: shellWindow ? shellWindow.uiFamily : "Noto Sans CJK SC"
                        }

                        Text {
                            width: parent.width
                            text: card["value"]
                            color: shellWindow ? shellWindow.textStrong : "#f4fbff"
                            font.pixelSize: shellWindow ? shellWindow.bodyEmphasisSize : 15
                            font.bold: true
                            font.family: shellWindow ? shellWindow.monoFamily : "JetBrains Mono"
                            wrapMode: Text.WordWrap
                        }

                        Text {
                            width: parent.width
                            text: card["detail"]
                            color: shellWindow ? shellWindow.textPrimary : "#d5eeff"
                            font.pixelSize: shellWindow ? shellWindow.captionSize : 11
                            font.family: shellWindow ? shellWindow.monoFamily : "JetBrains Mono"
                            wrapMode: Text.WrapAnywhere
                        }

                        Text {
                            width: parent.width
                            text: card["note"]
                            color: shellWindow ? shellWindow.textSecondary : "#83acc8"
                            font.pixelSize: shellWindow ? shellWindow.captionSize : 11
                            font.family: shellWindow ? shellWindow.uiFamily : "Noto Sans CJK SC"
                            wrapMode: Text.WordWrap
                        }
                    }
                }
            }
        }
    }
