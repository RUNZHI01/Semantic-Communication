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
    readonly property var currentPoint: trackPoint(Math.max(trackData.length - 1, 0))
    readonly property var originPoint: trackPoint(0)
    readonly property string sampleTimestamp: String(sampleData["captured_at"] || "采样时间未知")
    readonly property string latitudeLabel: coordinateLabel(positionData["latitude"], "lat")
    readonly property string longitudeLabel: coordinateLabel(positionData["longitude"], "lon")
    readonly property string altitudeLabel: Number(kinematicsData["altitude_m"] || 0).toFixed(0) + " m"
    readonly property string speedLabel: Number(kinematicsData["ground_speed_kph"] || 0).toFixed(0) + " km/h"
    readonly property string climbLabel: signedMetric(kinematicsData["vertical_speed_mps"], 1, "m/s")
    readonly property string headingLabel: headingDeg.toFixed(1) + "°"
    readonly property string fixLabel: String(fixData["type"] || "--") + " / ±" + Number(fixData["confidence_m"] || 0).toFixed(1) + "m"
    readonly property var mapHudMetrics: [
        { "label": "Fix", "value": fixLabel, "tone": "neutral" },
        { "label": "航向", "value": headingLabel, "tone": "warning" },
        { "label": "高度", "value": altitudeLabel, "tone": "online" },
        { "label": "航迹", "value": String(Number(trackData.length || 0).toFixed(0)) + " 节点", "tone": hasRealTrack() ? "online" : "neutral" }
    ]
    readonly property var railMetrics: [
        { "label": "ALT", "value": altitudeLabel, "detail": "高度层", "tone": "online" },
        { "label": "GS", "value": speedLabel, "detail": "地速", "tone": "neutral" },
        { "label": "VS", "value": climbLabel, "detail": "爬升率", "tone": "warning" },
        { "label": "SAT", "value": String(Number(fixData["satellites"] || 0).toFixed(0)), "detail": "卫星数", "tone": "neutral" }
    ]
    readonly property var missionRibbonModel: [
        {
            "label": "SOURCE",
            "value": root.sourceStatusLabel(),
            "tone": "neutral"
        },
        {
            "label": "ANCHOR",
            "value": String(liveAnchorData["valid_instance"] || "--"),
            "tone": String(liveAnchorData["tone"] || "neutral")
        },
        {
            "label": "LINK",
            "value": String(controlSummary["link_profile"] || "--"),
            "tone": "warning"
        },
        {
            "label": "HEARTBEAT",
            "value": heartbeatValue,
            "tone": heartbeatTone
        }
    ]
    readonly property var watchlistModel: [
        {
            "label": "CONTROL EVENT",
            "value": latestEventValue,
            "detail": compactMessage(controlSummary["last_event_message"], "当前没有额外控制消息。", 78),
            "tone": latestEventTone
        },
        {
            "label": "WEAK-LINK PROFILE",
            "value": recommendedScenarioId,
            "detail": compactMessage(scenarioSummary(recommendedScenarioId), "弱网对照摘要暂不可用。", 78),
            "tone": "warning"
        },
        {
            "label": "LIVE ANCHOR",
            "value": String(liveAnchorData["board_status"] || "--"),
            "detail": compactMessage(liveAnchorData["probe_summary"], "在线探板信息暂不可用。", 78),
            "tone": String(liveAnchorData["tone"] || "neutral")
        }
    ]
    readonly property var footerModel: [
        {
            "title": "GEO / POSITION",
            "value": "LAT " + Number(positionData["latitude"] || 0).toFixed(6) + "  LON " + Number(positionData["longitude"] || 0).toFixed(6),
            "detail": "航迹 " + String(Number(trackData.length || 0).toFixed(0)) + " 点 / 航向 " + headingLabel,
            "tone": "neutral"
        },
        {
            "title": "CONTRACT / SOURCE",
            "value": root.sourceLabel(),
            "detail": root.sourceStatusLabel() + " / " + sampleTimestamp,
            "tone": "neutral"
        },
        {
            "title": "LIVE / ANCHOR",
            "value": String(liveAnchorData["label"] || "实时锚点未挂接"),
            "detail": String(liveAnchorData["board_status"] || "尚无在线锚点状态"),
            "tone": String(liveAnchorData["tone"] || "neutral")
        },
        {
            "title": "WEAK / NETWORK",
            "value": recommendedScenarioId,
            "detail": compactMessage(scenarioSummary(recommendedScenarioId), "沿用归档弱网报告中的真实对照结果。", 88),
            "tone": "warning"
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

                Column {
                    id: heroColumn
                    anchors.fill: parent
                    anchors.margins: shellWindow ? shellWindow.cardPadding : 14
                    spacing: shellWindow ? shellWindow.compactGap : 8

                    Text {
                        text: panel["title"] || "航迹 / 飞机合同"
                        color: shellWindow ? shellWindow.accentBlue : "#38b6ff"
                        font.pixelSize: shellWindow ? shellWindow.eyebrowSize : 10
                        font.family: shellWindow ? shellWindow.monoFamily : "JetBrains Mono"
                        font.letterSpacing: shellWindow ? shellWindow.scaled(1) : 1
                    }

                    Text {
                        text: "全域态势墙"
                        color: shellWindow ? shellWindow.textStrong : "#f4fbff"
                        font.pixelSize: shellWindow ? shellWindow.sectionTitleSize : 24
                        font.bold: true
                        font.family: shellWindow ? shellWindow.displayFamily : "Noto Sans CJK SC"
                    }

                    Text {
                        text: "GLOBAL OPS WALLBOARD"
                        color: shellWindow ? shellWindow.textSecondary : "#83acc8"
                        font.pixelSize: shellWindow ? shellWindow.captionSize : 11
                        font.family: shellWindow ? shellWindow.monoFamily : "JetBrains Mono"
                        font.letterSpacing: shellWindow ? shellWindow.scaled(1) : 1
                    }

                    Text {
                        width: parent.width
                        text: "以既有飞机合同为主数据源，中心区改为全球态势墙式投影，保留真实机位、链路档位与采样时间。"
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
                                    "label": "航班",
                                    "value": String(panel["mission_call_sign"] || "M9-DEMO"),
                                    "tone": "online"
                                },
                                {
                                    "label": "机号",
                                    "value": String(panel["aircraft_id"] || "FT-AIR-01"),
                                    "tone": "neutral"
                                },
                                {
                                    "label": "链路",
                                    "value": String(controlSummary["link_profile"] || "--"),
                                    "tone": "warning"
                                },
                                {
                                    "label": "航迹",
                                    "value": String(Number(trackData.length || 0).toFixed(0)) + " 点",
                                    "tone": hasRealTrack() ? "online" : "neutral"
                                }
                            ]

                            delegate: Rectangle {
                                readonly property var chip: modelData
                                radius: shellWindow ? shellWindow.edgeRadius : 10
                                color: root.toneFill(chip["tone"])
                                border.color: root.toneColor(chip["tone"])
                                border.width: 1
                                height: chipColumn.implicitHeight + ((shellWindow ? shellWindow.scaled(8) : 8) * 2)
                                width: Math.max(shellWindow ? shellWindow.scaled(136) : 136, chipColumn.implicitWidth + (shellWindow ? shellWindow.scaled(22) : 22))

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

                Column {
                    id: feedColumn
                    anchors.fill: parent
                    anchors.margins: shellWindow ? shellWindow.cardPadding : 14
                    spacing: shellWindow ? shellWindow.scaled(5) : 5

                    Text {
                        text: "合同源 / Feed Contract"
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
                                text: "API PATH"
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
                            text: "GLOBAL OPERATIONS MESH"
                            color: shellWindow ? shellWindow.accentBlue : "#38b6ff"
                            font.pixelSize: shellWindow ? shellWindow.captionSize : 11
                            font.family: shellWindow ? shellWindow.monoFamily : "JetBrains Mono"
                            font.letterSpacing: shellWindow ? shellWindow.scaled(1) : 1
                        }

                        Text {
                            text: "全球态势墙"
                            color: shellWindow ? shellWindow.textStrong : "#f4fbff"
                            font.pixelSize: shellWindow ? shellWindow.sectionTitleSize : 24
                            font.bold: true
                            font.family: shellWindow ? shellWindow.displayFamily : "Noto Sans CJK SC"
                        }

                        Text {
                            text: "借鉴 mission-control 与安全态势墙的主舞台做法，把真实机位、弱网档位、在线锚点与采样时钟汇入同一中心投影。"
                            color: shellWindow ? shellWindow.textSecondary : "#83acc8"
                            font.pixelSize: shellWindow ? shellWindow.bodySize : 13
                            font.family: shellWindow ? shellWindow.uiFamily : "Noto Sans CJK SC"
                            wrapMode: Text.WordWrap
                        }
                    }

                    Rectangle {
                        radius: shellWindow ? shellWindow.edgeRadius : 10
                        color: root.toneFill(hasRealTrack() ? "online" : "neutral")
                        border.color: root.toneColor(hasRealTrack() ? "online" : "neutral")
                        border.width: 1
                        implicitWidth: statusColumn.implicitWidth + ((shellWindow ? shellWindow.scaled(16) : 16) * 2)
                        implicitHeight: statusColumn.implicitHeight + ((shellWindow ? shellWindow.scaled(10) : 10) * 2)

                        Column {
                            id: statusColumn
                            anchors.centerIn: parent
                            spacing: shellWindow ? shellWindow.scaled(3) : 3

                            Text {
                                text: "采样 / SAMPLE"
                                color: shellWindow ? shellWindow.textMuted : "#4e7392"
                                font.pixelSize: shellWindow ? shellWindow.captionSize : 11
                                font.family: shellWindow ? shellWindow.monoFamily : "JetBrains Mono"
                            }

                            Text {
                                text: root.sampleTimestamp
                                color: shellWindow ? shellWindow.textStrong : "#f4fbff"
                                font.pixelSize: shellWindow ? shellWindow.captionSize : 11
                                font.bold: true
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
                                color: root.toneFill(chip["tone"])
                                border.color: root.toneColor(chip["tone"])
                                border.width: 1
                                height: hudChipColumn.implicitHeight + ((shellWindow ? shellWindow.scaled(9) : 9) * 2)
                                width: Math.max(shellWindow ? shellWindow.scaled(148) : 148, hudChipColumn.implicitWidth + (shellWindow ? shellWindow.scaled(22) : 22))

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

                Flow {
                    Layout.fillWidth: true
                    spacing: shellWindow ? shellWindow.compactGap : 8

                    Repeater {
                        model: root.missionRibbonModel

                        delegate: Rectangle {
                            readonly property var itemData: modelData
                            radius: shellWindow ? shellWindow.edgeRadius : 10
                            color: "#0a1a29"
                            border.color: root.toneColor(itemData["tone"])
                            border.width: 1
                            height: ribbonColumn.implicitHeight + ((shellWindow ? shellWindow.scaled(8) : 8) * 2)
                            width: Math.max(shellWindow ? shellWindow.scaled(156) : 156, ribbonColumn.implicitWidth + (shellWindow ? shellWindow.scaled(24) : 24))

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

                        RowLayout {
                            id: theatreRow
                            anchors.fill: parent
                            anchors.margins: shellWindow ? shellWindow.scaled(8) : 8
                            spacing: shellWindow ? shellWindow.compactGap : 8

                            Text {
                                text: "THEATRE GRID"
                                color: shellWindow ? shellWindow.accentBlue : "#38b6ff"
                                font.pixelSize: shellWindow ? shellWindow.captionSize : 11
                                font.family: shellWindow ? shellWindow.monoFamily : "JetBrains Mono"
                            }

                            Rectangle {
                                Layout.fillWidth: true
                                Layout.preferredHeight: 1
                                color: "#123b5b"
                                opacity: 0.92
                            }

                            Repeater {
                                model: [
                                    {
                                        "label": "ANCHOR",
                                        "value": String(liveAnchorData["valid_instance"] || "--"),
                                        "tone": String(liveAnchorData["tone"] || "neutral")
                                    },
                                    {
                                        "label": "WEAK-LINK",
                                        "value": recommendedScenarioId,
                                        "tone": "warning"
                                    },
                                    {
                                        "label": "STAMP",
                                        "value": root.compactMessage(root.sampleTimestamp, "采样时间未知", 24),
                                        "tone": "neutral"
                                    }
                                ]

                                delegate: Rectangle {
                                    readonly property var ribbonData: modelData
                                    radius: shellWindow ? shellWindow.edgeRadius : 10
                                    color: root.toneFill(ribbonData["tone"])
                                    border.color: root.toneColor(ribbonData["tone"])
                                    border.width: 1
                                    implicitWidth: theatreBadgeColumn.implicitWidth + ((shellWindow ? shellWindow.scaled(12) : 12) * 2)
                                    implicitHeight: theatreBadgeColumn.implicitHeight + ((shellWindow ? shellWindow.scaled(5) : 5) * 2)

                                    Column {
                                        id: theatreBadgeColumn
                                        anchors.centerIn: parent
                                        spacing: 1

                                        Text {
                                            text: ribbonData["label"]
                                            color: shellWindow ? shellWindow.textMuted : "#4e7392"
                                            font.pixelSize: shellWindow ? shellWindow.captionSize : 9
                                            font.family: shellWindow ? shellWindow.monoFamily : "JetBrains Mono"
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
                        width: shellWindow ? shellWindow.scaled(compactCardLayout ? 204 : 232) : 232
                        radius: shellWindow ? shellWindow.cardRadius : 14
                        gradient: Gradient {
                            GradientStop { position: 0.0; color: "#0d1f31" }
                            GradientStop { position: 1.0; color: "#081321" }
                        }
                        border.color: "#245c88"
                        border.width: 1
                        anchors.left: parent.left
                        anchors.top: parent.top
                        anchors.leftMargin: shellWindow ? shellWindow.scaled(14) : 14
                        anchors.topMargin: shellWindow ? shellWindow.scaled(66) : 66
                        implicitHeight: missionColumn.implicitHeight + ((shellWindow ? shellWindow.scaled(12) : 12) * 2)

                        Column {
                            id: missionColumn
                            anchors.fill: parent
                            anchors.margins: shellWindow ? shellWindow.scaled(12) : 12
                            spacing: shellWindow ? shellWindow.scaled(4) : 4

                            Text {
                                text: "MISSION / TRACK HUD"
                                color: shellWindow ? shellWindow.accentBlue : "#38b6ff"
                                font.pixelSize: shellWindow ? shellWindow.captionSize : 11
                                font.family: shellWindow ? shellWindow.monoFamily : "JetBrains Mono"
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

                            Rectangle {
                                width: parent.width
                                height: 1
                                color: "#18405f"
                            }

                            Text {
                                width: parent.width
                                text: "链路 " + String(root.controlSummary["link_profile"] || "--")
                                color: shellWindow ? shellWindow.textSecondary : "#83acc8"
                                font.pixelSize: shellWindow ? shellWindow.captionSize : 11
                                font.family: shellWindow ? shellWindow.uiFamily : "Noto Sans CJK SC"
                                wrapMode: Text.WordWrap
                            }

                            Text {
                                width: parent.width
                                text: "源 " + root.sourceLabel()
                                color: shellWindow ? shellWindow.textSecondary : "#83acc8"
                                font.pixelSize: shellWindow ? shellWindow.captionSize : 11
                                font.family: shellWindow ? shellWindow.uiFamily : "Noto Sans CJK SC"
                                wrapMode: Text.WordWrap
                            }

                            Text {
                                width: parent.width
                                text: "弱网 " + recommendedScenarioId
                                color: shellWindow ? shellWindow.textSecondary : "#83acc8"
                                font.pixelSize: shellWindow ? shellWindow.captionSize : 11
                                font.family: shellWindow ? shellWindow.uiFamily : "Noto Sans CJK SC"
                                wrapMode: Text.WordWrap
                            }

                            Text {
                                width: parent.width
                                text: compactMessage(liveAnchorData["board_status"], "在线锚点状态未知。", 48)
                                color: shellWindow ? shellWindow.textMuted : "#4e7392"
                                font.pixelSize: shellWindow ? shellWindow.captionSize : 10
                                font.family: shellWindow ? shellWindow.monoFamily : "JetBrains Mono"
                                wrapMode: Text.WordWrap
                            }
                        }
                    }

                    Rectangle {
                        visible: !compactCardLayout
                        width: shellWindow ? shellWindow.scaled(224) : 224
                        radius: shellWindow ? shellWindow.cardRadius : 14
                        gradient: Gradient {
                            GradientStop { position: 0.0; color: "#0b1c2e" }
                            GradientStop { position: 1.0; color: "#081321" }
                        }
                        border.color: "#245c88"
                        border.width: 1
                        anchors.right: parent.right
                        anchors.top: parent.top
                        anchors.rightMargin: shellWindow ? shellWindow.scaled(14) : 14
                        anchors.topMargin: shellWindow ? shellWindow.scaled(66) : 66
                        implicitHeight: railColumn.implicitHeight + ((shellWindow ? shellWindow.scaled(12) : 12) * 2)

                        Column {
                            id: railColumn
                            anchors.fill: parent
                            anchors.margins: shellWindow ? shellWindow.scaled(12) : 12
                            spacing: shellWindow ? shellWindow.scaled(6) : 6

                            Text {
                                text: "FLIGHT TELEMETRY"
                                color: shellWindow ? shellWindow.accentBlue : "#38b6ff"
                                font.pixelSize: shellWindow ? shellWindow.captionSize : 11
                                font.family: shellWindow ? shellWindow.monoFamily : "JetBrains Mono"
                            }

                            Repeater {
                                model: root.railMetrics

                                delegate: Rectangle {
                                    readonly property var metric: modelData
                                    width: parent.width
                                    radius: shellWindow ? shellWindow.edgeRadius : 10
                                    color: root.toneFill(metric["tone"])
                                    border.color: root.toneColor(metric["tone"])
                                    border.width: 1
                                    implicitHeight: railMetricColumn.implicitHeight + ((shellWindow ? shellWindow.scaled(8) : 8) * 2)

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
                                text: "OPS WATCHLIST"
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
                                    color: "#0a1826"
                                    border.color: root.toneColor(watch["tone"])
                                    border.width: 1
                                    implicitHeight: watchColumn.implicitHeight + ((shellWindow ? shellWindow.scaled(8) : 8) * 2)

                                    Column {
                                        id: watchColumn
                                        anchors.fill: parent
                                        anchors.margins: shellWindow ? shellWindow.scaled(8) : 8
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
                    }

                    Rectangle {
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.bottom: parent.bottom
                        anchors.leftMargin: shellWindow ? shellWindow.scaled(14) : 14
                        anchors.rightMargin: shellWindow ? shellWindow.scaled(14) : 14
                        anchors.bottomMargin: shellWindow ? shellWindow.scaled(14) : 14
                        radius: shellWindow ? shellWindow.edgeRadius : 10
                        gradient: Gradient {
                            GradientStop { position: 0.0; color: "#07111d" }
                            GradientStop { position: 1.0; color: "#081726" }
                        }
                        border.color: "#1b4b72"
                        border.width: 1
                        implicitHeight: footerGrid.implicitHeight + ((shellWindow ? shellWindow.scaled(10) : 10) * 2)

                        GridLayout {
                            id: footerGrid
                            anchors.fill: parent
                            anchors.margins: shellWindow ? shellWindow.scaled(10) : 10
                            columns: compactCardLayout ? 1 : 4
                            columnSpacing: shellWindow ? shellWindow.compactGap : 8
                            rowSpacing: shellWindow ? shellWindow.compactGap : 8

                            Repeater {
                                model: root.footerModel

                                delegate: Rectangle {
                                    readonly property var footerItem: modelData
                                    Layout.fillWidth: true
                                    radius: shellWindow ? shellWindow.edgeRadius : 10
                                    color: "#091321"
                                    border.color: root.toneColor(footerItem["tone"])
                                    border.width: 1
                                    implicitHeight: footerColumn.implicitHeight + ((shellWindow ? shellWindow.scaled(8) : 8) * 2)

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
}
