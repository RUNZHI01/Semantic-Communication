import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "DataUtils.js" as DataUtils

Item {
    id: root

    property var shellWindow: null

    readonly property var centerPanel: shellWindow ? DataUtils.objectOrEmpty(shellWindow.centerPanelData) : ({})
    readonly property var sampleData: DataUtils.objectOrEmpty(centerPanel["sample"])
    readonly property var feedContract: shellWindow ? DataUtils.objectOrEmpty(shellWindow.centerFeedContract) : ({})
    readonly property var statusRows: shellWindow ? DataUtils.arrayOrEmpty(shellWindow.statusRows) : []
    readonly property var scenarioList: shellWindow ? DataUtils.arrayOrEmpty(shellWindow.rightScenarios) : []
    readonly property var recommendedScenario: shellWindow ? DataUtils.objectOrEmpty(shellWindow.recommendedScenario) : ({})
    readonly property var recommendedComparison: shellWindow ? DataUtils.objectOrEmpty(shellWindow.recommendedComparison) : ({})
    readonly property var stageTimingList: DataUtils.arrayOrEmpty(recommendedScenario["stage_timings"])
    readonly property var evidenceList: DataUtils.arrayOrEmpty(recommendedScenario["evidence"])
    readonly property var actionList: shellWindow ? DataUtils.arrayOrEmpty(shellWindow.bottomActions) : []
    readonly property var trackData: shellWindow ? DataUtils.arrayOrEmpty(shellWindow.trackData) : []
    readonly property var currentPoint: shellWindow ? DataUtils.objectOrEmpty(shellWindow.currentPosition) : ({})
    readonly property real headingDeg: shellWindow ? Number(shellWindow.kinematics["heading_deg"] || 0) : 0
    readonly property string anchorValue: shellWindow ? String(shellWindow.liveAnchor["valid_instance"] || "--") : "--"
    readonly property string anchorStatus: shellWindow ? String(shellWindow.liveAnchor["board_status"] || "--") : "--"
    readonly property string anchorProbeSummary: shellWindow ? String(shellWindow.liveAnchor["probe_summary"] || "--") : "--"
    readonly property string recommendedScenarioLabel: String(
        recommendedScenario["label"] || recommendedScenario["scenario_id"] || "当前没有推荐弱网策略"
    )
    readonly property bool landingWide: shellWindow ? shellWindow.viewportWidth >= 1320 : width >= 1320
    readonly property bool landingShortHeight: shellWindow ? shellWindow.shortViewport : height < 780
    readonly property int railWidth: shellWindow ? shellWindow.scaled(landingWide ? 132 : 134) : 132
    readonly property int landingStageLedgerWidth: shellWindow ? shellWindow.scaled(landingWide ? 298 : 268) : 298
    readonly property int flightSidebarWidth: shellWindow ? shellWindow.scaled(shellWindow.wideLayout ? 316 : 292) : 316
    readonly property int flightStageHeight: shellWindow ? shellWindow.scaled(shellWindow.compactLayout ? 332 : 478) : 478
    readonly property int flightStackedStageHeight: shellWindow ? shellWindow.scaled(shellWindow.compactLayout ? 316 : 372) : 372
    readonly property var landingStatusList: shellWindow ? shellWindow.previewItems(statusRows, 2) : []
    readonly property var landingScenarioList: shellWindow ? shellWindow.previewItems(scenarioList, 1) : []
    readonly property var timingPreviewList: shellWindow ? shellWindow.previewItems(stageTimingList, shellWindow.compactLayout ? 3 : 4) : []
    readonly property var evidencePreviewList: shellWindow ? shellWindow.previewItems(evidenceList, 4) : []
    readonly property var scenarioDeckList: shellWindow ? shellWindow.previewItems(scenarioList, shellWindow.wideLayout ? 4 : 3) : []
    readonly property var landingJumpList: shellWindow ? DataUtils.arrayOrEmpty(shellWindow.landingJumpModel) : []
    readonly property var landingWeakMetricList: shellWindow
        ? shellWindow.previewItems(shellWindow.landingWeakMetricModel, landingWide ? 2 : 2)
        : []
    readonly property var landingStackedStatusModel: [
        {
            "label": "会话",
            "value": shellWindow ? shellWindow.systemSessionValue : "--",
            "detail": compact(
                "心跳 " + (shellWindow ? shellWindow.heartbeatValue : "--")
                    + "  ·  "
                    + (shellWindow ? shellWindow.recentEventValue : "--"),
                landingShortHeight ? 34 : 52
            ),
            "tone": shellWindow ? shellWindow.heartbeatTone : "neutral"
        }
    ]
    readonly property var landingStackedWeakModel: [
        {
            "label": "推荐档",
            "value": shellWindow ? shellWindow.recommendedScenarioId : "--",
            "detail": compact(
                formattedComparison(recommendedScenario, "pipeline_images_per_sec", 3, "img/s")
                    + "  ·  uplift "
                    + formattedComparison(recommendedScenario, "throughput_uplift_pct", 3, "%"),
                landingShortHeight ? 38 : 56
            ),
            "tone": "warning"
        }
    ]
    readonly property var landingTelemetryPreviewList: shellWindow
        ? shellWindow.previewItems(shellWindow.landingTelemetryModel, landingWide ? 3 : 2)
        : []
    readonly property var actionPreviewList: shellWindow ? shellWindow.previewItems(actionList, 2) : []
    readonly property var landingDockChipModel: shellWindow ? [
        {
            "label": "动作",
            "value": String(shellWindow.enabledBottomActions) + " / " + String(actionList.length),
            "tone": shellWindow.enabledBottomActions > 0 ? "online" : "warning"
        },
        {
            "label": "桥接",
            "value": shellWindow.bridgeAvailable ? "仓库在线" : "桥接缺失",
            "tone": shellWindow.bridgeAvailable ? "online" : "warning"
        },
        {
            "label": "渲染",
            "value": shellWindow.softwareRenderEnabled ? "软件安全" : "图形优先",
            "tone": shellWindow.softwareRenderEnabled ? "warning" : "online"
        }
    ] : []
    readonly property int landingTelemetryColumns: landingWide ? 3 : ((shellWindow ? shellWindow.viewportWidth : width) >= 720 ? 2 : 1)
    readonly property int landingJumpColumns: (shellWindow ? shellWindow.viewportWidth : width) >= 720 ? 2 : 1
    readonly property int landingActionColumns: landingWide ? 2 : ((shellWindow ? shellWindow.viewportWidth : width) >= 720 ? 2 : 1)
    readonly property int landingWideDockColumns: 4
    readonly property var landingStageBannerChips: shellWindow
        ? shellWindow.previewItems(shellWindow.landingStageChipModel, landingWide ? 3 : 2)
        : []
    readonly property var landingSystemRailModel: [
        {
            "label": "会话",
            "value": shellWindow ? shellWindow.systemSessionValue : "--",
            "detail": compact(
                (shellWindow ? shellWindow.recentEventValue : "--") + "  ·  " + (shellWindow ? shellWindow.eventTimeValue : "--"),
                landingShortHeight ? 38 : 58
            ),
            "tone": "neutral"
        },
        {
            "label": "心跳",
            "value": shellWindow ? shellWindow.heartbeatValue : "--",
            "detail": compact(
                "快照 " + (shellWindow ? shellWindow.snapshotReasonValue : "--"),
                landingShortHeight ? 36 : 54
            ),
            "tone": shellWindow ? shellWindow.heartbeatTone : "neutral"
        }
    ]
    readonly property var landingWeakRailModel: [
        {
            "label": "推荐档",
            "value": shellWindow ? shellWindow.recommendedScenarioId : "--",
            "detail": compact(
                formattedComparison(recommendedScenario, "pipeline_images_per_sec", 3, "img/s")
                    + "  ·  uplift "
                    + formattedComparison(recommendedScenario, "throughput_uplift_pct", 3, "%"),
                landingShortHeight ? 40 : 58
            ),
            "tone": "warning"
        },
        {
            "label": "在线锚点",
            "value": anchorValue,
            "detail": compact(anchorProbeSummary, landingShortHeight ? 40 : 62),
            "tone": shellWindow ? shellWindow.liveAnchorTone : "neutral"
        }
    ]
    readonly property var flightContractModel: [
        {
            "label": "源状态",
            "value": String(centerPanel["source_status"] || "--"),
            "detail": String(feedContract["active_source_kind"] || "--"),
            "tone": "online"
        },
        {
            "label": "接口",
            "value": String(centerPanel["source_api_path"] || "--"),
            "detail": String(feedContract["active_source_label"] || "--"),
            "tone": "neutral"
        },
        {
            "label": "采样时间",
            "value": String(sampleData["captured_at"] || "--"),
            "detail": String(sampleData["source"] || "contract sample"),
            "tone": "neutral"
        },
        {
            "label": "回退语义",
            "value": compact(centerPanel["fallback_note"] || "--", 54),
            "detail": String(centerPanel["ownership_note"] || "--"),
            "tone": "warning"
        }
    ]
    readonly property string landingBriefText: compact(shellWindow ? shellWindow.landingSummaryText : "", landingShortHeight ? 88 : 120)
    readonly property string landingTruthBrief: compact(shellWindow ? shellWindow.truthNoteValue : "", landingShortHeight ? 96 : 132)
    readonly property string landingLaunchBrief: shellWindow && shellWindow.softwareRenderEnabled
        ? "repo-backed 绑定继续走软件安全启动，字体、主题和当前地图资源路径保持一致。"
        : "图形优先路径已就绪，同时维持同一套 repo-backed 绑定和地图资源路径。"
    readonly property string anchorProbeBrief: compact(anchorProbeSummary, landingShortHeight ? 72 : 104)
    readonly property string recommendedScenarioBrief: compact(
        String(recommendedScenario["summary"] || recommendedScenario["operator_note"] || "延续仓库现有弱网推荐剧本。"),
        landingShortHeight ? 72 : 96
    )
    readonly property string landingStageLedgerText: compact(
        shellWindow ? shellWindow.landingSummaryText : "",
        landingShortHeight ? 100 : 148
    )
    readonly property string landingStageLedgerSupport: compact(
        (shellWindow ? shellWindow.activeSourceLabel : "--") + "  ·  " + anchorProbeSummary,
        landingShortHeight ? 88 : 120
    )
    readonly property string landingSystemRailLine: compact(
        (shellWindow ? shellWindow.eventTimeValue : "--") + "  ·  " + (shellWindow ? shellWindow.snapshotRelativePath : "--"),
        landingShortHeight ? 68 : 108
    )
    readonly property string landingWeakRailLine: compact(
        "锚点 " + anchorValue + "  ·  " + anchorProbeSummary,
        landingShortHeight ? 68 : 104
    )
    readonly property string landingDeckEyebrow: "全球态势 · 指挥主墙"
    readonly property string landingDeckSupportText: compact(
        landingStageSubtitle + "  ·  " + (shellWindow ? shellWindow.activeSourceLabel : "--"),
        landingShortHeight ? 76 : 132
    )
    readonly property int landingWideStageMinHeight: shellWindow ? shellWindow.scaled(landingShortHeight ? 276 : 340) : 340
    readonly property int landingStackedStageHeight: shellWindow ? shellWindow.scaled(landingShortHeight ? 320 : 392) : 392
    readonly property int landingDeckGap: shellWindow ? shellWindow.scaled(landingWide ? 8 : 10) : (landingWide ? 8 : 10)
    readonly property string landingStageSubtitle: "真实地理底图继续占据第一视觉层，系统与弱网压成两侧连续细轨，底部坞站收口为同一块甲板托盘。"
    readonly property string mapCtaLabel: landingShortHeight ? "飞行合同" : "进入飞行合同"
    readonly property string dockCtaLabel: landingShortHeight ? "执行页" : "展开执行页"
    readonly property color landingDeckPanelColor: shellWindow
        ? Qt.rgba(shellWindow.surfaceGlass.r, shellWindow.surfaceGlass.g, shellWindow.surfaceGlass.b, 0.16)
        : "#152333"
    readonly property color landingDeckBorderTone: shellWindow
        ? Qt.rgba(shellWindow.panelGlowStrong.r, shellWindow.panelGlowStrong.g, shellWindow.panelGlowStrong.b, 0.18)
        : "#5f88a6"
    readonly property color landingRailDivider: shellWindow
        ? Qt.rgba(shellWindow.borderSubtle.r, shellWindow.borderSubtle.g, shellWindow.borderSubtle.b, 0.32)
        : "#49657d"
    readonly property color landingRailFill: shellWindow
        ? Qt.rgba(shellWindow.surfaceGlass.r, shellWindow.surfaceGlass.g, shellWindow.surfaceGlass.b, 0.18)
        : "#8c0f1720"
    readonly property color landingRailBorder: shellWindow
        ? Qt.rgba(shellWindow.panelGlowStrong.r, shellWindow.panelGlowStrong.g, shellWindow.panelGlowStrong.b, 0.16)
        : "#49657d"
    readonly property color landingStageFill: shellWindow
        ? Qt.rgba(shellWindow.surfaceGlass.r, shellWindow.surfaceGlass.g, shellWindow.surfaceGlass.b, 0.08)
        : "#62081119"
    readonly property color landingStageBorder: shellWindow
        ? Qt.rgba(shellWindow.panelGlowStrong.r, shellWindow.panelGlowStrong.g, shellWindow.panelGlowStrong.b, 0.22)
        : "#58b2da"
    readonly property color landingDockFill: shellWindow
        ? Qt.rgba(shellWindow.surfaceGlass.r, shellWindow.surfaceGlass.g, shellWindow.surfaceGlass.b, 0.18)
        : "#7d0f1720"
    readonly property color landingDockBorder: shellWindow
        ? Qt.rgba(shellWindow.panelGlowStrong.r, shellWindow.panelGlowStrong.g, shellWindow.panelGlowStrong.b, 0.14)
        : "#58b2da"

    function compact(text, limit) {
        if (shellWindow)
            return shellWindow.compactMessage(text, limit)
        return String(text || "")
    }

    function comparisonOf(scenario) {
        return DataUtils.objectOrEmpty(DataUtils.objectOrEmpty(scenario)["comparison"])
    }

    function formattedComparison(scenario, key, decimals, suffix) {
        if (!shellWindow)
            return "--"
        return shellWindow.formattedMetric(comparisonOf(scenario)[key], decimals, suffix)
    }

    function scenarioTone(scenario) {
        return String(DataUtils.objectOrEmpty(scenario)["tone"] || "neutral")
    }

    function stageValue(stage) {
        var resolved = DataUtils.objectOrEmpty(stage)
        if (!shellWindow)
            return "--"
        return shellWindow.formattedMetric(resolved["mean_ms"], 1, "ms")
    }

    function stageDetail(stage) {
        var resolved = DataUtils.objectOrEmpty(stage)
        if (!shellWindow)
            return ""
        return "P50 "
            + shellWindow.formattedMetric(resolved["median_ms"], 1, "ms")
            + " / max "
            + shellWindow.formattedMetric(resolved["max_ms"], 1, "ms")
    }

    function actionTone(action) {
        var resolved = DataUtils.objectOrEmpty(action)
        if (!!resolved["enabled"])
            return String(resolved["tone"] || "online")
        return "neutral"
    }

    function jumpTone(jumpItem) {
        return String(DataUtils.objectOrEmpty(jumpItem)["tone"] || "neutral")
    }

    Component {
        id: landingJumpCardDelegate

        Rectangle {
            readonly property var jumpData: DataUtils.objectOrEmpty(modelData)
            readonly property string jumpToneValue: root.jumpTone(jumpData)
            readonly property color jumpAccent: shellWindow ? shellWindow.toneColor(jumpToneValue) : "#86c7d4"
            property bool jumpHovered: false
            Layout.fillWidth: true
            radius: shellWindow ? shellWindow.edgeRadius + shellWindow.scaled(1) : 13
            color: jumpHovered
                ? (shellWindow ? Qt.lighter(shellWindow.surfaceRaised, 1.14) : "#1c2a38")
                : (shellWindow ? shellWindow.surfaceRaised : "#15202a")
            border.color: Qt.rgba(jumpAccent.r, jumpAccent.g, jumpAccent.b, jumpHovered ? 0.92 : 0.72)
            border.width: 1
            scale: jumpHovered ? 1.015 : 1.0
            Behavior on color { ColorAnimation { duration: 140 } }
            Behavior on border.color { ColorAnimation { duration: 140 } }
            Behavior on scale { NumberAnimation { duration: 140 } }
            implicitHeight: jumpColumn.implicitHeight + ((shellWindow ? shellWindow.scaled(10) : 10) * 2)

            Rectangle {
                anchors.left: parent.left
                anchors.top: parent.top
                anchors.bottom: parent.bottom
                width: shellWindow ? shellWindow.scaled(3) : 3
                radius: width / 2
                color: jumpAccent
                opacity: 0.82
            }

            Rectangle {
                anchors.fill: parent
                anchors.margins: 1
                radius: parent.radius - 1
                color: "transparent"
                border.color: "#10ffffff"
                border.width: 1
            }

            ColumnLayout {
                id: jumpColumn
                anchors.fill: parent
                anchors.margins: shellWindow ? shellWindow.scaled(10) : 10
                spacing: shellWindow ? shellWindow.scaled(3) : 3

                RowLayout {
                    Layout.fillWidth: true
                    spacing: shellWindow ? shellWindow.compactGap : 8

                    Text {
                        Layout.fillWidth: true
                        text: String(jumpData["label"] || "--")
                        color: shellWindow ? shellWindow.textStrong : "#f5efe4"
                        font.pixelSize: shellWindow ? shellWindow.bodyEmphasisSize : 14
                        font.weight: Font.DemiBold
                        font.family: shellWindow ? shellWindow.uiFamily : "Noto Sans CJK SC"
                    }

                    Text {
                        text: String(jumpData["english"] || "")
                        color: shellWindow ? shellWindow.textMuted : "#6f7f8a"
                        font.pixelSize: shellWindow ? shellWindow.captionSize : 10
                        font.family: shellWindow ? shellWindow.monoFamily : "JetBrains Mono"
                    }
                }

                    Text {
                        Layout.fillWidth: true
                        text: String(jumpData["summary"] || "")
                        color: shellWindow ? shellWindow.textSecondary : "#9aa8b1"
                        font.pixelSize: shellWindow ? shellWindow.captionSize + 1 : 11
                        font.family: shellWindow ? shellWindow.uiFamily : "Noto Sans CJK SC"
                        wrapMode: Text.WordWrap
                        maximumLineCount: 2
                        elide: Text.ElideRight
                    }

                    Text {
                        Layout.fillWidth: true
                        text: "直达入口  ·  " + String(jumpData["value"] || "--")
                        color: jumpAccent
                        font.pixelSize: shellWindow ? shellWindow.captionSize + 1 : 11
                        font.weight: Font.DemiBold
                        font.family: shellWindow ? shellWindow.monoFamily : "JetBrains Mono"
                        wrapMode: Text.WrapAnywhere
                    }
            }

            MouseArea {
                anchors.fill: parent
                hoverEnabled: true
                cursorShape: Qt.PointingHandCursor
                onClicked: if (shellWindow) shellWindow.currentPage = Number(jumpData["index"] || 0)
                onEntered: parent.jumpHovered = true
                onExited: parent.jumpHovered = false
            }
        }
    }

    Component {
        id: landingActionPreviewDelegate

        Rectangle {
            readonly property var actionData: DataUtils.objectOrEmpty(modelData)
            readonly property string actionToneValue: root.actionTone(actionData)
            readonly property color actionAccent: shellWindow ? shellWindow.toneColor(actionToneValue) : "#86c7d4"
            readonly property bool actionEnabled: !!actionData["enabled"]
            Layout.fillWidth: true
            radius: shellWindow ? shellWindow.edgeRadius + shellWindow.scaled(1) : 13
            color: shellWindow ? shellWindow.surfaceRaised : "#15202a"
            border.color: Qt.rgba(actionAccent.r, actionAccent.g, actionAccent.b, 0.72)
            border.width: 1
            implicitHeight: actionColumn.implicitHeight + ((shellWindow ? shellWindow.scaled(10) : 10) * 2)

            Rectangle {
                anchors.left: parent.left
                anchors.top: parent.top
                anchors.bottom: parent.bottom
                width: shellWindow ? shellWindow.scaled(3) : 3
                radius: width / 2
                color: actionAccent
                opacity: 0.82
            }

            ColumnLayout {
                id: actionColumn
                anchors.fill: parent
                anchors.margins: shellWindow ? shellWindow.scaled(10) : 10
                spacing: shellWindow ? shellWindow.scaled(4) : 4

                RowLayout {
                    Layout.fillWidth: true
                    spacing: shellWindow ? shellWindow.compactGap : 8

                    Text {
                        Layout.fillWidth: true
                        text: String(actionData["label"] || "--")
                        color: shellWindow ? shellWindow.textStrong : "#f5efe4"
                        font.pixelSize: shellWindow ? shellWindow.bodyEmphasisSize : 14
                        font.weight: Font.DemiBold
                        font.family: shellWindow ? shellWindow.uiFamily : "Noto Sans CJK SC"
                    }

                    Rectangle {
                        radius: shellWindow ? shellWindow.edgeRadius : 12
                        color: shellWindow ? shellWindow.toneFill(actionToneValue) : "#152029"
                        border.color: actionAccent
                        border.width: 1
                        implicitWidth: actionStateText.implicitWidth + ((shellWindow ? shellWindow.scaled(8) : 8) * 2)
                        implicitHeight: actionStateText.implicitHeight + ((shellWindow ? shellWindow.scaled(4) : 4) * 2)

                        Text {
                            id: actionStateText
                            anchors.centerIn: parent
                            text: actionEnabled ? "可执行" : "只读"
                            color: shellWindow ? shellWindow.textStrong : "#f5efe4"
                            font.pixelSize: shellWindow ? shellWindow.captionSize + 1 : 11
                            font.weight: Font.DemiBold
                            font.family: shellWindow ? shellWindow.uiFamily : "Noto Sans CJK SC"
                        }
                    }
                }

                Text {
                    Layout.fillWidth: true
                    text: compact(actionData["note"] || "保持合同镜像", 76)
                    color: shellWindow ? shellWindow.textPrimary : "#d7dde2"
                    font.pixelSize: shellWindow ? shellWindow.bodySize : 13
                    font.family: shellWindow ? shellWindow.uiFamily : "Noto Sans CJK SC"
                    wrapMode: Text.WordWrap
                    maximumLineCount: 2
                    elide: Text.ElideRight
                }

                Text {
                    Layout.fillWidth: true
                    text: actionEnabled ? "仓库合同已接入 · 保持软件安全回退" : "仓库合同只读镜像 · 进入执行页查看"
                    color: shellWindow ? shellWindow.textMuted : "#6f7f8a"
                    font.pixelSize: shellWindow ? shellWindow.captionSize + 1 : 11
                    font.family: shellWindow ? shellWindow.monoFamily : "JetBrains Mono"
                    wrapMode: Text.WrapAnywhere
                }
            }
        }
    }

    Component {
        id: landingScenarioPreviewDelegate

        Rectangle {
            readonly property var scenarioData: DataUtils.objectOrEmpty(modelData)
            readonly property string scenarioToneValue: root.scenarioTone(scenarioData)
            readonly property color scenarioAccent: shellWindow ? shellWindow.toneColor(scenarioToneValue) : "#86c7d4"
            Layout.fillWidth: true
            radius: shellWindow ? shellWindow.edgeRadius + shellWindow.scaled(1) : 13
            color: shellWindow ? shellWindow.surfaceQuiet : "#0f161d"
            border.color: Qt.rgba(scenarioAccent.r, scenarioAccent.g, scenarioAccent.b, 0.68)
            border.width: 1
            implicitHeight: scenarioPreviewColumn.implicitHeight + ((shellWindow ? shellWindow.scaled(10) : 10) * 2)

            Rectangle {
                anchors.left: parent.left
                anchors.top: parent.top
                anchors.bottom: parent.bottom
                width: shellWindow ? shellWindow.scaled(3) : 3
                radius: width / 2
                color: scenarioAccent
                opacity: 0.78
            }

            ColumnLayout {
                id: scenarioPreviewColumn
                anchors.fill: parent
                anchors.margins: shellWindow ? shellWindow.scaled(10) : 10
                spacing: shellWindow ? shellWindow.scaled(3) : 3

                RowLayout {
                    Layout.fillWidth: true
                    spacing: shellWindow ? shellWindow.compactGap : 8

                    Text {
                        Layout.fillWidth: true
                        text: String(scenarioData["label"] || scenarioData["scenario_id"] || "--")
                        color: shellWindow ? shellWindow.textStrong : "#f5efe4"
                        font.pixelSize: shellWindow ? shellWindow.bodyEmphasisSize : 14
                        font.weight: Font.DemiBold
                        font.family: shellWindow ? shellWindow.uiFamily : "Noto Sans CJK SC"
                        elide: Text.ElideRight
                    }

                    Text {
                        text: String(scenarioData["scenario_id"] || "--")
                        color: scenarioAccent
                        font.pixelSize: shellWindow ? shellWindow.captionSize : 10
                        font.family: shellWindow ? shellWindow.monoFamily : "JetBrains Mono"
                    }
                }

                Text {
                    Layout.fillWidth: true
                    text: compact(scenarioData["summary"] || scenarioData["operator_note"] || "", 78)
                    color: shellWindow ? shellWindow.textSecondary : "#9aa8b1"
                    font.pixelSize: shellWindow ? shellWindow.captionSize + 1 : 11
                    font.family: shellWindow ? shellWindow.uiFamily : "Noto Sans CJK SC"
                    wrapMode: Text.WordWrap
                    maximumLineCount: 2
                    elide: Text.ElideRight
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: shellWindow ? shellWindow.compactGap : 8

                    Text {
                        Layout.fillWidth: true
                        text: "吞吐 " + root.formattedComparison(scenarioData, "pipeline_images_per_sec", 3, "img/s")
                        color: shellWindow ? shellWindow.textMuted : "#6f7f8a"
                        font.pixelSize: shellWindow ? shellWindow.captionSize + 1 : 11
                        font.family: shellWindow ? shellWindow.monoFamily : "JetBrains Mono"
                        elide: Text.ElideRight
                    }

                    Text {
                        text: "提升 " + root.formattedComparison(scenarioData, "throughput_uplift_pct", 3, "%")
                        color: scenarioAccent
                        font.pixelSize: shellWindow ? shellWindow.captionSize + 1 : 11
                        font.weight: Font.DemiBold
                        font.family: shellWindow ? shellWindow.monoFamily : "JetBrains Mono"
                        elide: Text.ElideRight
                    }
                }
            }
        }
    }

    Component {
        id: landingTelemetryReadoutDelegate

        Rectangle {
            readonly property var metricData: DataUtils.objectOrEmpty(modelData)
            readonly property string metricTone: String(metricData["tone"] || "neutral")
            readonly property color metricAccent: shellWindow ? shellWindow.toneColor(metricTone) : "#86c7d4"
            Layout.fillWidth: true
            radius: shellWindow ? shellWindow.edgeRadius + shellWindow.scaled(1) : 13
            color: shellWindow ? shellWindow.surfaceQuiet : "#0f161d"
            border.color: Qt.rgba(metricAccent.r, metricAccent.g, metricAccent.b, 0.68)
            border.width: 1
            implicitHeight: readoutColumn.implicitHeight + ((shellWindow ? shellWindow.scaled(8) : 8) * 2)

            Rectangle {
                anchors.left: parent.left
                anchors.top: parent.top
                anchors.bottom: parent.bottom
                anchors.topMargin: shellWindow ? shellWindow.scaled(7) : 7
                anchors.bottomMargin: shellWindow ? shellWindow.scaled(7) : 7
                width: shellWindow ? shellWindow.scaled(3) : 3
                radius: width / 2
                color: metricAccent
                opacity: 0.84
            }

            Rectangle {
                anchors.fill: parent
                radius: parent.radius
                gradient: Gradient {
                    GradientStop { position: 0.0; color: "#12ffffff" }
                    GradientStop { position: 0.36; color: "#04ffffff" }
                    GradientStop { position: 1.0; color: "#00000000" }
                }
                opacity: 0.34
            }

            ColumnLayout {
                id: readoutColumn
                anchors.fill: parent
                anchors.leftMargin: shellWindow ? shellWindow.scaled(14) : 14
                anchors.rightMargin: shellWindow ? shellWindow.scaled(8) : 8
                anchors.topMargin: shellWindow ? shellWindow.scaled(8) : 8
                anchors.bottomMargin: shellWindow ? shellWindow.scaled(8) : 8
                spacing: shellWindow ? shellWindow.scaled(1) : 1

                Text {
                    text: String(metricData["label"] || "--")
                    color: shellWindow ? shellWindow.textMuted : "#6f7f8a"
                    font.pixelSize: shellWindow ? shellWindow.captionSize : 10
                    font.family: shellWindow ? shellWindow.monoFamily : "JetBrains Mono"
                    font.letterSpacing: shellWindow ? shellWindow.scaled(0.5) : 0.5
                }

                Text {
                    Layout.fillWidth: true
                    text: String(metricData["value"] || "--")
                    color: shellWindow ? shellWindow.textStrong : "#f5efe4"
                    font.pixelSize: shellWindow ? shellWindow.bodyEmphasisSize : 14
                    font.weight: Font.DemiBold
                    font.family: shellWindow ? shellWindow.displayFamily : "Noto Serif CJK SC"
                    wrapMode: Text.WordWrap
                    maximumLineCount: 2
                    elide: Text.ElideRight
                }

                Text {
                    visible: text.length > 0
                    Layout.fillWidth: true
                    text: String(metricData["detail"] || "")
                    color: shellWindow ? shellWindow.textSecondary : "#9aa8b1"
                    font.pixelSize: shellWindow ? shellWindow.captionSize : 10
                    font.family: shellWindow ? shellWindow.uiFamily : "Noto Sans CJK SC"
                    wrapMode: Text.WordWrap
                    maximumLineCount: 1
                    elide: Text.ElideRight
                }
            }
        }
    }

    Component {
        id: landingRailReadoutDelegate

        Item {
            readonly property var readoutData: DataUtils.objectOrEmpty(modelData)
            readonly property string readoutTone: String(readoutData["tone"] || "neutral")
            readonly property color readoutAccent: shellWindow ? shellWindow.toneColor(readoutTone) : "#86c7d4"
            readonly property string readoutValue: String(readoutData["value"] || "--")
            readonly property bool structuredValue: /^[A-Za-z0-9_:\-./%°,+\s]+$/.test(readoutValue)
            Layout.fillWidth: true
            implicitHeight: railReadoutColumn.implicitHeight + ((shellWindow ? shellWindow.scaled(9) : 9) * 2)

            Rectangle {
                visible: index > 0
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                height: 1
                color: root.landingRailDivider
                opacity: 0.78
            }

            Rectangle {
                anchors.left: parent.left
                anchors.top: parent.top
                anchors.bottom: parent.bottom
                anchors.topMargin: shellWindow ? shellWindow.scaled(10) : 10
                anchors.bottomMargin: shellWindow ? shellWindow.scaled(10) : 10
                width: shellWindow ? shellWindow.scaled(2) : 2
                radius: width / 2
                color: readoutAccent
                opacity: 0.84
            }

            ColumnLayout {
                id: railReadoutColumn
                anchors.fill: parent
                anchors.leftMargin: shellWindow ? shellWindow.scaled(12) : 12
                anchors.rightMargin: shellWindow ? shellWindow.scaled(4) : 4
                anchors.topMargin: shellWindow ? shellWindow.scaled(9) : 9
                anchors.bottomMargin: shellWindow ? shellWindow.scaled(9) : 9
                spacing: shellWindow ? shellWindow.scaled(2) : 2

                Text {
                    text: String(readoutData["label"] || "--")
                    color: shellWindow ? shellWindow.textMuted : "#6f7f8a"
                    font.pixelSize: shellWindow ? shellWindow.captionSize : 10
                    font.family: shellWindow ? shellWindow.monoFamily : "JetBrains Mono"
                    font.letterSpacing: shellWindow ? shellWindow.scaled(0.6) : 0.6
                }

                Text {
                    Layout.fillWidth: true
                    text: readoutValue
                    color: shellWindow ? shellWindow.textStrong : "#f5efe4"
                    font.pixelSize: shellWindow ? shellWindow.bodyEmphasisSize + shellWindow.scaled(1) : 15
                    font.weight: Font.DemiBold
                    font.family: shellWindow
                        ? (structuredValue ? shellWindow.monoFamily : shellWindow.displayFamily)
                        : "Noto Sans CJK SC"
                    wrapMode: Text.WordWrap
                    maximumLineCount: 2
                    elide: Text.ElideRight
                }

                Text {
                    visible: text.length > 0
                    Layout.fillWidth: true
                    text: String(readoutData["detail"] || "")
                    color: shellWindow ? shellWindow.textSecondary : "#9aa8b1"
                    font.pixelSize: shellWindow ? shellWindow.captionSize + 1 : 11
                    font.family: shellWindow ? shellWindow.uiFamily : "Noto Sans CJK SC"
                    wrapMode: Text.WordWrap
                    maximumLineCount: 2
                    elide: Text.ElideRight
                }
            }
        }
    }

    Rectangle {
        id: shellSurface
        anchors.fill: parent
        anchors.leftMargin: (shellWindow ? shellWindow.safeLeft : 0) + (shellWindow ? shellWindow.outerPadding : 12)
        anchors.topMargin: (shellWindow ? shellWindow.safeTop : 0) + (shellWindow ? shellWindow.outerPadding : 12)
        anchors.rightMargin: (shellWindow ? shellWindow.safeRight : 0) + (shellWindow ? shellWindow.outerPadding : 12)
        anchors.bottomMargin: (shellWindow ? shellWindow.safeBottom : 0) + (shellWindow ? shellWindow.outerPadding : 12)
        radius: shellWindow ? shellWindow.panelRadius + shellWindow.scaled(10) : 30
        color: shellWindow ? Qt.rgba(shellWindow.shellExterior.r, shellWindow.shellExterior.g, shellWindow.shellExterior.b, 0.74) : "#0b1117"
        border.color: shellWindow ? Qt.rgba(shellWindow.borderSubtle.r, shellWindow.borderSubtle.g, shellWindow.borderSubtle.b, 0.42) : "#2a3944"
        border.width: 1
        clip: true
        opacity: 0

        NumberAnimation on opacity {
            from: 0; to: 1; duration: 500; easing.type: Easing.OutCubic
        }

        Rectangle {
            id: shellBreathGlow
            anchors.fill: parent
            radius: parent.radius
            color: "transparent"
            border.color: shellWindow ? shellWindow.accentIce : "#7cddff"
            border.width: 1
            opacity: 0.06
            z: 8

            SequentialAnimation on opacity {
                loops: Animation.Infinite
                NumberAnimation { from: 0.04; to: 0.12; duration: 2800; easing.type: Easing.InOutSine }
                NumberAnimation { from: 0.12; to: 0.04; duration: 2800; easing.type: Easing.InOutSine }
            }
        }

        Rectangle {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            anchors.leftMargin: shellWindow ? shellWindow.scaled(20) : 20
            anchors.rightMargin: shellWindow ? shellWindow.scaled(20) : 20
            height: shellWindow ? shellWindow.scaled(2) : 2
            radius: height / 2
            z: 10
            gradient: Gradient {
                orientation: Gradient.Horizontal
                GradientStop { position: 0.0; color: "transparent" }
                GradientStop { position: 0.15; color: Qt.rgba(shellWindow ? shellWindow.accentIce.r : 0.49, shellWindow ? shellWindow.accentIce.g : 0.87, shellWindow ? shellWindow.accentIce.b : 1.0, 0.06) }
                GradientStop { position: 0.45; color: Qt.rgba(shellWindow ? shellWindow.accentIce.r : 0.49, shellWindow ? shellWindow.accentIce.g : 0.87, shellWindow ? shellWindow.accentIce.b : 1.0, 0.48) }
                GradientStop { position: 0.55; color: Qt.rgba(shellWindow ? shellWindow.accentIce.r : 0.49, shellWindow ? shellWindow.accentIce.g : 0.87, shellWindow ? shellWindow.accentIce.b : 1.0, 0.42) }
                GradientStop { position: 0.85; color: Qt.rgba(shellWindow ? shellWindow.accentGold.r : 0.94, shellWindow ? shellWindow.accentGold.g : 0.69, shellWindow ? shellWindow.accentGold.b : 0.38, 0.12) }
                GradientStop { position: 1.0; color: "transparent" }
            }
            opacity: 0.72
        }

        Canvas {
            id: scanlineOverlay
            anchors.fill: parent
            z: 5
            opacity: 0.035
            onPaint: {
                var ctx = getContext("2d")
                ctx.clearRect(0, 0, width, height)
                ctx.strokeStyle = "rgba(180, 220, 255, 0.6)"
                ctx.lineWidth = 0.5
                for (var y = 0; y < height; y += 4) {
                    ctx.beginPath()
                    ctx.moveTo(0, y)
                    ctx.lineTo(width, y)
                    ctx.stroke()
                }
            }
            onWidthChanged: requestPaint()
            onHeightChanged: requestPaint()
        }

        Rectangle {
            anchors.fill: parent
            gradient: Gradient {
                GradientStop { position: 0.0; color: shellWindow ? shellWindow.canopyTop : "#1b252e" }
                GradientStop { position: 0.16; color: shellWindow ? shellWindow.shellInterior : "#11181f" }
                GradientStop { position: 1.0; color: shellWindow ? shellWindow.canopyBottom : "#0b1015" }
            }
            opacity: 0.86
        }

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: shellWindow ? shellWindow.shellPadding : 18
            spacing: shellWindow ? shellWindow.zoneGap : 14

            ShellHeader {
                Layout.fillWidth: true
                shellWindow: root.shellWindow
                currentIndex: shellWindow ? shellWindow.currentPage : 0
                onPageRequested: function(index) { if (shellWindow) shellWindow.currentPage = index }
            }

            StackLayout {
                id: mainStack
                Layout.fillWidth: true
                Layout.fillHeight: true
                currentIndex: shellWindow ? shellWindow.currentPage : 0

                Behavior on currentIndex {
                    enabled: false
                }

                Item {
                    Layout.fillWidth: true
                    Layout.fillHeight: true

                    Loader {
                        anchors.fill: parent
                        active: true
                        sourceComponent: landingWide ? landingWideComponent : landingStackedComponent
                    }
                }

                Item {
                    Layout.fillWidth: true
                    Layout.fillHeight: true

                    Loader {
                        anchors.fill: parent
                        active: mainStack.currentIndex === 1
                        sourceComponent: mainStack.currentIndex === 1 ? systemStatusPageComponent : null
                    }
                }

                Item {
                    Layout.fillWidth: true
                    Layout.fillHeight: true

                    Loader {
                        anchors.fill: parent
                        active: true
                        sourceComponent: shellWindow && shellWindow.wideLayout ? flightWideComponent : flightStackedComponent
                    }
                }

                Item {
                    Layout.fillWidth: true
                    Layout.fillHeight: true

                    Loader {
                        anchors.fill: parent
                        active: mainStack.currentIndex === 3
                        sourceComponent: mainStack.currentIndex === 3 ? weakNetworkPageComponent : null
                    }
                }

                Item {
                    Layout.fillWidth: true
                    Layout.fillHeight: true

                    Loader {
                        anchors.fill: parent
                        active: mainStack.currentIndex === 4
                        sourceComponent: mainStack.currentIndex === 4 ? actionDockPageComponent : null
                    }
                }
            }
        }
    }

    Component {
        id: systemStatusPageComponent

        Flickable {
            anchors.fill: parent
            contentWidth: width
            contentHeight: innerLayout0.implicitHeight
            clip: true
            boundsBehavior: Flickable.StopAtBounds
            flickableDirection: Flickable.VerticalFlick
            ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }

            GridLayout {
                id: innerLayout0
                width: parent.width
                columns: shellWindow && shellWindow.wideLayout ? 2 : 1
                columnSpacing: shellWindow ? shellWindow.zoneGap : 14
                rowSpacing: shellWindow ? shellWindow.zoneGap : 14

                ShellCard {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    shellWindow: root.shellWindow
                    accentColor: shellWindow ? shellWindow.accentGold : "#c6ab7d"
                    eyebrow: "系统板态总览"
                    title: "会话、心跳与快照轨迹"
                    subtitle: shellWindow ? shellWindow.landingSummaryText : ""

                    Flow {
                        Layout.fillWidth: true
                        spacing: shellWindow ? shellWindow.compactGap : 8

                        Repeater {
                            model: shellWindow ? shellWindow.systemPageChipModel : []

                            delegate: ToneChip {
                                shellWindow: root.shellWindow
                                label: modelData["label"]
                                value: modelData["value"]
                                tone: modelData["tone"]
                            }
                        }
                    }

                    GridLayout {
                        Layout.fillWidth: true
                        columns: shellWindow && shellWindow.compactLayout ? 1 : 2
                        columnSpacing: shellWindow ? shellWindow.compactGap : 8
                        rowSpacing: shellWindow ? shellWindow.compactGap : 8

                        Repeater {
                            model: root.statusRows

                            delegate: MetricTile {
                                shellWindow: root.shellWindow
                                Layout.fillWidth: true
                                label: String(modelData["label"] || "--")
                                value: String(modelData["value"] || "--")
                                detail: "状态语义: " + String(modelData["tone"] || "neutral")
                                tone: String(modelData["tone"] || "neutral")
                                entranceDelay: index * 60
                            }
                        }
                    }
                }

                ColumnLayout {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    spacing: shellWindow ? shellWindow.zoneGap : 14

                    ShellCard {
                        Layout.fillWidth: true
                        shellWindow: root.shellWindow
                        accentColor: shellWindow ? shellWindow.accentIce : "#86c7d4"
                        eyebrow: "事实边界"
                        title: "快照路径与仓库入口"
                        subtitle: "继续直接读取 repo-backed 合同，不绕过现有运行约束。"

                        ToneChip {
                            shellWindow: root.shellWindow
                            label: "快照时间"
                            value: shellWindow ? shellWindow.eventTimeValue : "--"
                            tone: shellWindow ? shellWindow.recentEventTone : "neutral"
                            prominent: true
                        }

                        Rectangle {
                            Layout.fillWidth: true
                            radius: shellWindow ? shellWindow.edgeRadius : 12
                            color: shellWindow ? shellWindow.surfaceQuiet : "#0f161d"
                            border.color: shellWindow ? shellWindow.borderSubtle : "#2a3944"
                            border.width: 1
                            implicitHeight: snapshotColumn.implicitHeight + ((shellWindow ? shellWindow.cardPadding : 14) * 2)

                            ColumnLayout {
                                id: snapshotColumn
                                anchors.fill: parent
                                anchors.margins: shellWindow ? shellWindow.cardPadding : 14
                                spacing: shellWindow ? shellWindow.compactGap : 8

                                Text {
                                    Layout.fillWidth: true
                                    text: shellWindow ? shellWindow.truthNoteValue : ""
                                    color: shellWindow ? shellWindow.textPrimary : "#d7dde2"
                                    font.pixelSize: shellWindow ? shellWindow.bodySize : 13
                                    font.family: shellWindow ? shellWindow.uiFamily : "Noto Sans CJK SC"
                                    wrapMode: Text.WordWrap
                                }

                                Text {
                                    Layout.fillWidth: true
                                    text: shellWindow ? shellWindow.snapshotRelativePath : "--"
                                    color: shellWindow ? shellWindow.accentIce : "#86c7d4"
                                    font.pixelSize: shellWindow ? shellWindow.captionSize + 1 : 11
                                    font.family: shellWindow ? shellWindow.monoFamily : "JetBrains Mono"
                                    wrapMode: Text.WrapAnywhere
                                }

                                Text {
                                    Layout.fillWidth: true
                                    text: shellWindow ? shellWindow.launchHint : "--"
                                    color: shellWindow ? shellWindow.textSecondary : "#9aa8b1"
                                    font.pixelSize: shellWindow ? shellWindow.captionSize + 1 : 11
                                    font.family: shellWindow ? shellWindow.monoFamily : "JetBrains Mono"
                                    wrapMode: Text.WrapAnywhere
                                }
                            }
                        }
                    }

                    ShellCard {
                        Layout.fillWidth: true
                        shellWindow: root.shellWindow
                        accentColor: shellWindow ? shellWindow.accentMint : "#93bea5"
                        eyebrow: "启动姿态"
                        title: "自适应原生命令壳"
                        subtitle: "保持软件渲染安全回退与仓库内 venv 启动路径。"

                        Flow {
                            Layout.fillWidth: true
                            spacing: shellWindow ? shellWindow.compactGap : 8

                            Repeater {
                                model: shellWindow ? shellWindow.actionPageChipModel : []

                                delegate: ToneChip {
                                    shellWindow: root.shellWindow
                                    label: modelData["label"]
                                    value: modelData["value"]
                                    tone: modelData["tone"]
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    Component {
        id: weakNetworkPageComponent

        Flickable {
            anchors.fill: parent
            contentWidth: width
            contentHeight: innerLayout1.implicitHeight
            clip: true
            boundsBehavior: Flickable.StopAtBounds
            flickableDirection: Flickable.VerticalFlick
            ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }

            ColumnLayout {
                id: innerLayout1
                width: parent.width
                spacing: shellWindow ? shellWindow.zoneGap : 14

                ShellCard {
                    Layout.fillWidth: true
                    shellWindow: root.shellWindow
                    accentColor: shellWindow ? shellWindow.accentGold : "#c6ab7d"
                    eyebrow: "弱网推荐策略"
                    title: root.recommendedScenarioLabel
                    subtitle: String(root.recommendedScenario["summary"] || "当前没有弱网摘要。")

                    Flow {
                        Layout.fillWidth: true
                        spacing: shellWindow ? shellWindow.compactGap : 8

                        Repeater {
                            model: shellWindow ? shellWindow.weakPageChipModel : []

                            delegate: ToneChip {
                                shellWindow: root.shellWindow
                                label: modelData["label"]
                                value: modelData["value"]
                                tone: modelData["tone"]
                                prominent: true
                            }
                        }
                    }

                    GridLayout {
                        Layout.fillWidth: true
                        columns: shellWindow && shellWindow.compactLayout ? 2 : 4
                        columnSpacing: shellWindow ? shellWindow.compactGap : 8
                        rowSpacing: shellWindow ? shellWindow.compactGap : 8

                        Repeater {
                            model: [
                                {
                                    "label": "Pipeline",
                                    "value": shellWindow ? shellWindow.formattedMetric(root.recommendedComparison["pipeline_images_per_sec"], 3, "img/s") : "--",
                                    "detail": "真机 pipeline 吞吐",
                                    "tone": "online"
                                },
                                {
                                    "label": "Uplift",
                                    "value": shellWindow ? shellWindow.formattedMetric(root.recommendedComparison["throughput_uplift_pct"], 3, "%") : "--",
                                    "detail": "相对 serial 提升",
                                    "tone": "warning"
                                },
                                {
                                    "label": "节省时长",
                                    "value": shellWindow ? shellWindow.formattedMetric(root.recommendedComparison["saved_seconds_per_batch"], 3, "s") : "--",
                                    "detail": "每批次节省",
                                    "tone": "online"
                                },
                                {
                                    "label": "在线锚点",
                                    "value": root.anchorValue,
                                    "detail": root.anchorStatus,
                                    "tone": shellWindow ? shellWindow.liveAnchorTone : "neutral"
                                }
                            ]

                            delegate: MetricTile {
                                shellWindow: root.shellWindow
                                Layout.fillWidth: true
                                label: modelData["label"]
                                value: modelData["value"]
                                detail: modelData["detail"]
                                tone: modelData["tone"]
                                prominent: true
                            }
                        }
                    }
                }

                GridLayout {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    columns: shellWindow && shellWindow.wideLayout ? 2 : 1
                    columnSpacing: shellWindow ? shellWindow.zoneGap : 14
                    rowSpacing: shellWindow ? shellWindow.zoneGap : 14

                    ShellCard {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        shellWindow: root.shellWindow
                        accentColor: shellWindow ? shellWindow.accentIce : "#86c7d4"
                        eyebrow: "对照剧本池"
                        title: String(root.scenarioList.length) + " 个剧本节点"
                        subtitle: "直接使用仓库弱网合同中的场景、吞吐与证据字段。"

                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: shellWindow ? shellWindow.compactGap : 8

                            Repeater {
                                model: root.scenarioDeckList

                                delegate: Rectangle {
                                    readonly property var scenarioData: DataUtils.objectOrEmpty(modelData)
                                    Layout.fillWidth: true
                                    radius: shellWindow ? shellWindow.edgeRadius : 12
                                    color: shellWindow ? shellWindow.surfaceQuiet : "#0f161d"
                                    border.color: shellWindow ? shellWindow.toneColor(root.scenarioTone(scenarioData)) : "#86c7d4"
                                    border.width: 1
                                    implicitHeight: scenarioColumn.implicitHeight + ((shellWindow ? shellWindow.cardPadding : 14) * 2)

                                    ColumnLayout {
                                        id: scenarioColumn
                                        anchors.fill: parent
                                        anchors.margins: shellWindow ? shellWindow.cardPadding : 14
                                        spacing: shellWindow ? shellWindow.scaled(4) : 4

                                        RowLayout {
                                            Layout.fillWidth: true
                                            spacing: shellWindow ? shellWindow.compactGap : 8

                                            Text {
                                                Layout.fillWidth: true
                                                text: String(scenarioData["label"] || scenarioData["scenario_id"] || "--")
                                                color: shellWindow ? shellWindow.textStrong : "#f5efe4"
                                                font.pixelSize: shellWindow ? shellWindow.bodyEmphasisSize : 14
                                                font.weight: Font.DemiBold
                                                font.family: shellWindow ? shellWindow.uiFamily : "Noto Sans CJK SC"
                                            }

                                            ToneChip {
                                                shellWindow: root.shellWindow
                                                label: "档位"
                                                value: String(scenarioData["scenario_id"] || "--")
                                                tone: root.scenarioTone(scenarioData)
                                            }
                                        }

                                        Text {
                                            Layout.fillWidth: true
                                            text: compact(scenarioData["summary"] || scenarioData["operator_note"] || "", 120)
                                            color: shellWindow ? shellWindow.textSecondary : "#9aa8b1"
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
                                                        "label": "吞吐",
                                                        "value": root.formattedComparison(scenarioData, "pipeline_images_per_sec", 3, "img/s"),
                                                        "tone": "online"
                                                    },
                                                    {
                                                        "label": "提升",
                                                        "value": root.formattedComparison(scenarioData, "throughput_uplift_pct", 3, "%"),
                                                        "tone": "warning"
                                                    },
                                                    {
                                                        "label": "批耗时",
                                                        "value": root.formattedComparison(scenarioData, "saved_seconds_per_batch", 3, "s"),
                                                        "tone": "neutral"
                                                    }
                                                ]

                                                delegate: ToneChip {
                                                    shellWindow: root.shellWindow
                                                    label: modelData["label"]
                                                    value: modelData["value"]
                                                    tone: modelData["tone"]
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }

                    ShellCard {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        shellWindow: root.shellWindow
                        accentColor: shellWindow ? shellWindow.accentMint : "#93bea5"
                        eyebrow: "证据摘要"
                        title: "阶段耗时与证据文件"
                        subtitle: "优先展示推荐剧本的 stage timings、报告路径与在线锚点。"

                        GridLayout {
                            Layout.fillWidth: true
                            columns: 1
                            rowSpacing: shellWindow ? shellWindow.compactGap : 8

                            Repeater {
                                model: root.timingPreviewList

                                delegate: MetricTile {
                                    shellWindow: root.shellWindow
                                    Layout.fillWidth: true
                                    label: String(modelData["label"] || "--")
                                    value: root.stageValue(modelData)
                                    detail: root.stageDetail(modelData)
                                    tone: String(modelData["tone"] || "neutral")
                                }
                            }
                        }

                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: shellWindow ? shellWindow.compactGap : 8

                            Repeater {
                                model: root.evidencePreviewList

                                delegate: Rectangle {
                                    Layout.fillWidth: true
                                    radius: shellWindow ? shellWindow.edgeRadius : 12
                                    color: shellWindow ? shellWindow.surfaceQuiet : "#0f161d"
                                    border.color: shellWindow ? shellWindow.borderSubtle : "#2a3944"
                                    border.width: 1
                                    implicitHeight: evidenceColumn.implicitHeight + ((shellWindow ? shellWindow.scaled(8) : 8) * 2)

                                    ColumnLayout {
                                        id: evidenceColumn
                                        anchors.fill: parent
                                        anchors.margins: shellWindow ? shellWindow.scaled(8) : 8
                                        spacing: shellWindow ? shellWindow.scaled(2) : 2

                                        Text {
                                            text: String(modelData["label"] || "--")
                                            color: shellWindow ? shellWindow.textStrong : "#f5efe4"
                                            font.pixelSize: shellWindow ? shellWindow.bodyEmphasisSize : 14
                                            font.family: shellWindow ? shellWindow.uiFamily : "Noto Sans CJK SC"
                                        }

                                        Text {
                                            Layout.fillWidth: true
                                            text: String(modelData["path"] || "--")
                                            color: shellWindow ? shellWindow.accentIce : "#86c7d4"
                                            font.pixelSize: shellWindow ? shellWindow.captionSize + 1 : 11
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
        }
    }

    Component {
        id: actionDockPageComponent

        Flickable {
            anchors.fill: parent
            contentWidth: width
            contentHeight: innerLayout2.implicitHeight
            clip: true
            boundsBehavior: Flickable.StopAtBounds
            flickableDirection: Flickable.VerticalFlick
            ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }

            GridLayout {
                id: innerLayout2
                width: parent.width
                columns: shellWindow && shellWindow.wideLayout ? 2 : 1
                columnSpacing: shellWindow ? shellWindow.zoneGap : 14
                rowSpacing: shellWindow ? shellWindow.zoneGap : 14

                ShellCard {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    shellWindow: root.shellWindow
                    accentColor: shellWindow ? shellWindow.accentGold : "#c6ab7d"
                    eyebrow: "ACTION DOCK / 合同动作"
                    title: "启停入口、动作门控与只读回显"
                    subtitle: shellWindow ? shellWindow.footerNote : ""

                    Flow {
                        Layout.fillWidth: true
                        spacing: shellWindow ? shellWindow.compactGap : 8

                        Repeater {
                            model: shellWindow ? shellWindow.actionPageChipModel : []

                            delegate: ToneChip {
                                shellWindow: root.shellWindow
                                label: modelData["label"]
                                value: modelData["value"]
                                tone: modelData["tone"]
                            }
                        }
                    }

                    GridLayout {
                        Layout.fillWidth: true
                        columns: shellWindow && shellWindow.compactLayout ? 1 : 2
                        columnSpacing: shellWindow ? shellWindow.compactGap : 8
                        rowSpacing: shellWindow ? shellWindow.compactGap : 8

                        Repeater {
                            model: root.actionList

                            delegate: MetricTile {
                                shellWindow: root.shellWindow
                                Layout.fillWidth: true
                                label: String(modelData["label"] || "--")
                                value: !!modelData["enabled"] ? "可执行" : "只读"
                                detail: String(modelData["note"] || "--")
                                tone: root.actionTone(modelData)
                            }
                        }
                    }
                }

                ColumnLayout {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    spacing: shellWindow ? shellWindow.zoneGap : 14

                    ShellCard {
                        Layout.fillWidth: true
                        shellWindow: root.shellWindow
                        accentColor: shellWindow ? shellWindow.accentIce : "#86c7d4"
                        eyebrow: "启动命令"
                        title: "软件渲染安全入口"
                        subtitle: "精确保留当前原生座舱的 launch plumbing。"

                        Rectangle {
                            Layout.fillWidth: true
                            radius: shellWindow ? shellWindow.edgeRadius : 12
                            color: shellWindow ? shellWindow.surfaceQuiet : "#0f161d"
                            border.color: shellWindow ? shellWindow.borderSubtle : "#2a3944"
                            border.width: 1
                            implicitHeight: launchColumn.implicitHeight + ((shellWindow ? shellWindow.cardPadding : 14) * 2)

                            ColumnLayout {
                                id: launchColumn
                                anchors.fill: parent
                                anchors.margins: shellWindow ? shellWindow.cardPadding : 14
                                spacing: shellWindow ? shellWindow.compactGap : 8

                                Text {
                                    Layout.fillWidth: true
                                    text: shellWindow ? shellWindow.launchHint : "--"
                                    color: shellWindow ? shellWindow.accentIce : "#86c7d4"
                                    font.pixelSize: shellWindow ? shellWindow.captionSize + 1 : 11
                                    font.family: shellWindow ? shellWindow.monoFamily : "JetBrains Mono"
                                    wrapMode: Text.WrapAnywhere
                                }

                                Text {
                                    Layout.fillWidth: true
                                    text: shellWindow ? shellWindow.footerNote : ""
                                    color: shellWindow ? shellWindow.textSecondary : "#9aa8b1"
                                    font.pixelSize: shellWindow ? shellWindow.bodySize : 13
                                    font.family: shellWindow ? shellWindow.uiFamily : "Noto Sans CJK SC"
                                    wrapMode: Text.WordWrap
                                }
                            }
                        }
                    }

                    ShellCard {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        shellWindow: root.shellWindow
                        accentColor: shellWindow ? shellWindow.accentMint : "#93bea5"
                        eyebrow: "ROUTES / 路径与上下文"
                        title: "快照、接口与推荐档位"
                        subtitle: "不改动仓库原始数据合同，只改 native shell 外形。"

                        GridLayout {
                            Layout.fillWidth: true
                            columns: 1
                            rowSpacing: shellWindow ? shellWindow.compactGap : 8

                            Repeater {
                                model: [
                                    {
                                        "label": "快照路径",
                                        "value": shellWindow ? shellWindow.snapshotRelativePath : "--",
                                        "detail": shellWindow ? shellWindow.eventTimeValue : "--",
                                        "tone": "neutral"
                                    },
                                    {
                                        "label": "推荐弱网档",
                                        "value": shellWindow ? shellWindow.recommendedScenarioId : "--",
                                        "detail": root.anchorProbeSummary,
                                        "tone": "warning"
                                    },
                                    {
                                        "label": "飞机合同 API",
                                        "value": String(root.centerPanel["source_api_path"] || "--"),
                                        "detail": String(root.centerPanel["source_status"] || "--"),
                                        "tone": "online"
                                    }
                                ]

                                delegate: MetricTile {
                                    shellWindow: root.shellWindow
                                    Layout.fillWidth: true
                                    label: modelData["label"]
                                    value: modelData["value"]
                                    detail: modelData["detail"]
                                    tone: modelData["tone"]
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    Component {
        id: flightWideComponent

        Item {
            anchors.fill: parent

            RowLayout {
                anchors.fill: parent
                spacing: shellWindow ? shellWindow.zoneGap : 14

                Flickable {
                    Layout.preferredWidth: root.flightSidebarWidth
                    Layout.minimumWidth: root.flightSidebarWidth
                    Layout.maximumWidth: root.flightSidebarWidth
                    Layout.fillHeight: true
                    contentWidth: width
                    contentHeight: flightSidebarCol.implicitHeight
                    clip: true
                    boundsBehavior: Flickable.StopAtBounds
                    flickableDirection: Flickable.VerticalFlick
                    ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }

                ColumnLayout {
                    id: flightSidebarCol
                    width: parent.width
                    spacing: shellWindow ? shellWindow.zoneGap : 14

                    ShellCard {
                        Layout.fillWidth: true
                        shellWindow: root.shellWindow
                        accentColor: shellWindow ? shellWindow.accentGold : "#c6ab7d"
                        eyebrow: "MAP SIDEBAR / 合同边栏"
                        title: "遥测、采样与任务摘要"
                        subtitle: "借用 QDashBoard 的边栏分区，让地图主视区保持整块可读。"

                        Flow {
                            Layout.fillWidth: true
                            spacing: shellWindow ? shellWindow.compactGap : 8

                            Repeater {
                                model: shellWindow ? shellWindow.landingStageChipModel : []

                                delegate: ToneChip {
                                    shellWindow: root.shellWindow
                                    label: modelData["label"]
                                    value: modelData["value"]
                                    tone: modelData["tone"]
                                }
                            }
                        }

                        GridLayout {
                            Layout.fillWidth: true
                            columns: 1
                            rowSpacing: shellWindow ? shellWindow.compactGap : 8

                            Repeater {
                                model: shellWindow ? shellWindow.landingTelemetryModel : []

                                delegate: MetricTile {
                                    shellWindow: root.shellWindow
                                    Layout.fillWidth: true
                                    label: modelData["label"]
                                    value: modelData["value"]
                                    detail: modelData["detail"]
                                    tone: modelData["tone"]
                                }
                            }
                        }
                    }

                    ShellCard {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        shellWindow: root.shellWindow
                        accentColor: shellWindow ? shellWindow.accentMint : "#93bea5"
                        eyebrow: "数据合同"
                        title: "来源状态、接口与回退说明"
                        subtitle: root.anchorProbeBrief

                        Rectangle {
                            Layout.fillWidth: true
                            radius: shellWindow ? shellWindow.edgeRadius : 12
                            color: shellWindow ? shellWindow.surfaceQuiet : "#0f161d"
                            border.color: shellWindow ? shellWindow.borderSubtle : "#2a3944"
                            border.width: 1
                            implicitHeight: flightSidebarSummary.implicitHeight + ((shellWindow ? shellWindow.scaled(10) : 10) * 2)

                            ColumnLayout {
                                id: flightSidebarSummary
                                anchors.fill: parent
                                anchors.margins: shellWindow ? shellWindow.scaled(10) : 10
                                spacing: shellWindow ? shellWindow.scaled(3) : 3

                                Text {
                                    text: "边栏摘要"
                                    color: shellWindow ? shellWindow.accentMint : "#93bea5"
                                    font.pixelSize: shellWindow ? shellWindow.captionSize : 10
                                    font.family: shellWindow ? shellWindow.monoFamily : "JetBrains Mono"
                                    font.letterSpacing: shellWindow ? shellWindow.scaled(0.6) : 0.6
                                }

                                Text {
                                    Layout.fillWidth: true
                                    text: root.landingTruthBrief
                                    color: shellWindow ? shellWindow.textPrimary : "#d7dde2"
                                    font.pixelSize: shellWindow ? shellWindow.bodySize : 13
                                    font.family: shellWindow ? shellWindow.uiFamily : "Noto Sans CJK SC"
                                    wrapMode: Text.WordWrap
                                    maximumLineCount: 3
                                    elide: Text.ElideRight
                                }
                            }
                        }

                        GridLayout {
                            Layout.fillWidth: true
                            columns: 1
                            rowSpacing: shellWindow ? shellWindow.compactGap : 8

                            Repeater {
                                model: root.flightContractModel

                                delegate: MetricTile {
                                    shellWindow: root.shellWindow
                                    Layout.fillWidth: true
                                    label: modelData["label"]
                                    value: modelData["value"]
                                    detail: modelData["detail"]
                                    tone: modelData["tone"]
                                }
                            }
                        }
                    }
                }
                }

                ShellCard {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    Layout.minimumWidth: shellWindow ? shellWindow.scaled(700) : 700
                    shellWindow: root.shellWindow
                    accentColor: shellWindow ? shellWindow.accentIce : "#86c7d4"
                    eyebrow: "飞行态势板"
                    title: shellWindow ? shellWindow.missionCallSignValue + " · " + shellWindow.aircraftIdValue : "飞行合同"
                    subtitle: shellWindow ? shellWindow.activeSourceLabel : ""

                    Item {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        implicitHeight: root.flightStageHeight

                        WorldMapStage {
                            anchors.fill: parent
                            shellWindow: root.shellWindow
                            stageActive: mainStack.currentIndex === 2
                            preloadAssets: true
                            trackData: root.trackData
                            currentPoint: root.currentPoint
                            headingDeg: root.headingDeg
                            currentLabel: shellWindow ? shellWindow.missionCallSignValue : ""
                            currentDetail: shellWindow ? shellWindow.activeSourceLabel : ""
                            anchorLabel: root.anchorValue
                            scenarioLabel: root.recommendedScenarioLabel
                            scenarioTone: shellWindow ? shellWindow.liveAnchorTone : "neutral"
                            landingMode: false
                            bannerEyebrow: "FLIGHT CONTRACT / LIVE TRACK"
                            bannerTitle: shellWindow ? shellWindow.landingMapBannerTitle : ""
                            bannerText: shellWindow ? shellWindow.landingMapBannerText : ""
                            bannerChips: shellWindow ? shellWindow.landingStageChipModel : []
                            showStageBadge: true
                            showScenarioBadge: true
                            showInfoPanels: false
                            preferBottomBannerDock: true
                        }
                    }
                }
            }
        }
    }

    Component {
        id: flightStackedComponent

        Item {
            anchors.fill: parent

            Flickable {
                id: flightStackedScroller
                anchors.fill: parent
                contentWidth: width
                contentHeight: flightStackedColumn.implicitHeight
                clip: true
                boundsBehavior: Flickable.StopAtBounds
                interactive: contentHeight > height

                ScrollBar.vertical: ScrollBar {
                    policy: flightStackedScroller.interactive ? ScrollBar.AsNeeded : ScrollBar.AlwaysOff
                }

                ColumnLayout {
                    id: flightStackedColumn
                    width: flightStackedScroller.width
                    spacing: shellWindow ? shellWindow.zoneGap : 14

                    ShellCard {
                        Layout.fillWidth: true
                        shellWindow: root.shellWindow
                        accentColor: shellWindow ? shellWindow.accentIce : "#86c7d4"
                        eyebrow: "飞行态势板"
                        title: shellWindow ? shellWindow.missionCallSignValue + " · " + shellWindow.aircraftIdValue : "飞行合同"
                        subtitle: shellWindow ? shellWindow.activeSourceLabel : ""

                        Item {
                            Layout.fillWidth: true
                            implicitHeight: root.flightStackedStageHeight

                            WorldMapStage {
                                anchors.fill: parent
                                shellWindow: root.shellWindow
                                stageActive: mainStack.currentIndex === 2
                                preloadAssets: true
                                trackData: root.trackData
                                currentPoint: root.currentPoint
                                headingDeg: root.headingDeg
                                currentLabel: shellWindow ? shellWindow.missionCallSignValue : ""
                                currentDetail: shellWindow ? shellWindow.activeSourceLabel : ""
                                anchorLabel: root.anchorValue
                                scenarioLabel: root.recommendedScenarioLabel
                                scenarioTone: shellWindow ? shellWindow.liveAnchorTone : "neutral"
                            landingMode: false
                            bannerEyebrow: "FLIGHT CONTRACT / LIVE TRACK"
                            bannerTitle: shellWindow ? shellWindow.landingMapBannerTitle : ""
                            bannerText: shellWindow ? shellWindow.landingMapBannerText : ""
                            bannerChips: shellWindow ? shellWindow.landingStageChipModel : []
                            showStageBadge: true
                            showScenarioBadge: true
                            showInfoPanels: false
                            preferBottomBannerDock: true
                        }
                    }
                }

                    ShellCard {
                        Layout.fillWidth: true
                        shellWindow: root.shellWindow
                        accentColor: shellWindow ? shellWindow.accentGold : "#c6ab7d"
                        eyebrow: "MAP SIDEBAR / 遥测边栏"
                        title: "遥测、采样与任务摘要"
                        subtitle: root.anchorProbeBrief

                        Flow {
                            Layout.fillWidth: true
                            spacing: shellWindow ? shellWindow.compactGap : 8

                            Repeater {
                                model: shellWindow ? shellWindow.landingStageChipModel : []

                                delegate: ToneChip {
                                    shellWindow: root.shellWindow
                                    label: modelData["label"]
                                    value: modelData["value"]
                                    tone: modelData["tone"]
                                }
                            }
                        }

                        GridLayout {
                            Layout.fillWidth: true
                            columns: shellWindow && shellWindow.compactLayout ? 1 : 2
                            columnSpacing: shellWindow ? shellWindow.compactGap : 8
                            rowSpacing: shellWindow ? shellWindow.compactGap : 8

                            Repeater {
                                model: shellWindow ? shellWindow.landingTelemetryModel : []

                                delegate: MetricTile {
                                    shellWindow: root.shellWindow
                                    Layout.fillWidth: true
                                    label: modelData["label"]
                                    value: modelData["value"]
                                    detail: modelData["detail"]
                                    tone: modelData["tone"]
                                }
                            }
                        }
                    }

                    ShellCard {
                        Layout.fillWidth: true
                        shellWindow: root.shellWindow
                        accentColor: shellWindow ? shellWindow.accentMint : "#93bea5"
                        eyebrow: "数据合同"
                        title: "来源状态、接口与回退说明"
                        subtitle: "边栏语义继续直连 repo-backed 字段。"

                        Rectangle {
                            Layout.fillWidth: true
                            radius: shellWindow ? shellWindow.edgeRadius : 12
                            color: shellWindow ? shellWindow.surfaceQuiet : "#0f161d"
                            border.color: shellWindow ? shellWindow.borderSubtle : "#2a3944"
                            border.width: 1
                            implicitHeight: flightStackedSummary.implicitHeight + ((shellWindow ? shellWindow.scaled(10) : 10) * 2)

                            ColumnLayout {
                                id: flightStackedSummary
                                anchors.fill: parent
                                anchors.margins: shellWindow ? shellWindow.scaled(10) : 10
                                spacing: shellWindow ? shellWindow.scaled(3) : 3

                                Text {
                                    text: root.landingTruthBrief
                                    color: shellWindow ? shellWindow.textPrimary : "#d7dde2"
                                    font.pixelSize: shellWindow ? shellWindow.bodySize : 13
                                    font.family: shellWindow ? shellWindow.uiFamily : "Noto Sans CJK SC"
                                    wrapMode: Text.WordWrap
                                    maximumLineCount: 3
                                    elide: Text.ElideRight
                                }

                                Text {
                                    Layout.fillWidth: true
                                    text: shellWindow ? shellWindow.launchHint : "--"
                                    color: shellWindow ? shellWindow.textSecondary : "#9aa8b1"
                                    font.pixelSize: shellWindow ? shellWindow.captionSize + 1 : 11
                                    font.family: shellWindow ? shellWindow.monoFamily : "JetBrains Mono"
                                    wrapMode: Text.WrapAnywhere
                                }
                            }
                        }

                        GridLayout {
                            Layout.fillWidth: true
                            columns: 1
                            rowSpacing: shellWindow ? shellWindow.compactGap : 8

                            Repeater {
                                model: root.flightContractModel

                                delegate: MetricTile {
                                    shellWindow: root.shellWindow
                                    Layout.fillWidth: true
                                    label: modelData["label"]
                                    value: modelData["value"]
                                    detail: modelData["detail"]
                                    tone: modelData["tone"]
                                }
                            }
                        }
                    }
                }
            }
        }

    }

    Component {
        id: landingWideComponent

        Item {
            anchors.fill: parent

            ColumnLayout {
                anchors.fill: parent
                spacing: shellWindow ? shellWindow.zoneGap : 10

                Item {
                    Layout.fillWidth: true
                    Layout.fillHeight: true

                    WorldMapStage {
                        anchors.fill: parent
                        shellWindow: root.shellWindow
                        stageActive: mainStack.currentIndex === 0
                        preloadAssets: true
                        trackData: root.trackData
                        currentPoint: root.currentPoint
                        headingDeg: root.headingDeg
                        currentLabel: ""
                        currentDetail: ""
                        anchorLabel: root.anchorValue
                        scenarioLabel: ""
                        scenarioTone: "neutral"
                        landingMode: true
                        bannerEyebrow: ""
                        bannerTitle: ""
                        bannerText: ""
                        bannerChips: []
                        showStageBadge: false
                        showScenarioBadge: false
                        showInfoPanels: false
                        preferBottomBannerDock: false
                    }

                    Rectangle {
                        id: heroKpiWide
                        anchors.left: parent.left
                        anchors.bottom: parent.bottom
                        anchors.leftMargin: shellWindow ? shellWindow.scaled(24) : 24
                        anchors.bottomMargin: shellWindow ? shellWindow.scaled(24) : 24
                        width: heroKpiWideCol.implicitWidth + (shellWindow ? shellWindow.scaled(28) : 28)
                        height: heroKpiWideCol.implicitHeight + (shellWindow ? shellWindow.scaled(22) : 22)
                        radius: shellWindow ? shellWindow.cardRadius : 16
                        color: shellWindow ? Qt.rgba(shellWindow.shellInterior.r, shellWindow.shellInterior.g, shellWindow.shellInterior.b, 0.82) : "#11181fD0"
                        border.color: shellWindow ? Qt.rgba(shellWindow.accentMint.r, shellWindow.accentMint.g, shellWindow.accentMint.b, 0.3) : "#50e8b04D"
                        border.width: 1
                        opacity: 0

                        NumberAnimation on opacity { from: 0; to: 1; duration: 600; easing.type: Easing.OutCubic }

                        Rectangle {
                            anchors.centerIn: parent
                            width: parent.width * 1.2
                            height: parent.height * 1.2
                            radius: parent.radius + 6
                            color: shellWindow ? shellWindow.accentMint : "#50e8b0"
                            opacity: 0.06
                            z: -1
                        }

                        Rectangle {
                            anchors.left: parent.left
                            anchors.right: parent.right
                            anchors.top: parent.top
                            anchors.leftMargin: shellWindow ? shellWindow.scaled(12) : 12
                            anchors.rightMargin: shellWindow ? shellWindow.scaled(12) : 12
                            height: 2
                            radius: 1
                            gradient: Gradient {
                                orientation: Gradient.Horizontal
                                GradientStop { position: 0.0; color: "transparent" }
                                GradientStop { position: 0.3; color: shellWindow ? Qt.rgba(shellWindow.accentMint.r, shellWindow.accentMint.g, shellWindow.accentMint.b, 0.5) : "#50e8b080" }
                                GradientStop { position: 0.7; color: shellWindow ? Qt.rgba(shellWindow.accentIce.r, shellWindow.accentIce.g, shellWindow.accentIce.b, 0.3) : "#64d4ff4D" }
                                GradientStop { position: 1.0; color: "transparent" }
                            }
                            opacity: 0.8
                        }

                        Column {
                            id: heroKpiWideCol
                            anchors.centerIn: parent
                            spacing: shellWindow ? shellWindow.scaled(4) : 4

                            property real animatedSpeedup: 0
                            property real animatedBefore: 0
                            property real animatedAfter: 0

                            NumberAnimation on animatedSpeedup { from: 0; to: 12; duration: 1200; easing.type: Easing.OutCubic }
                            NumberAnimation on animatedBefore { from: 0; to: 1844; duration: 1000; easing.type: Easing.OutQuad }
                            NumberAnimation on animatedAfter { from: 0; to: 153; duration: 1400; easing.type: Easing.OutCubic }

                            Text {
                                text: "TVM MetaSchedule 加速"
                                color: shellWindow ? shellWindow.accentIce : "#64d4ff"
                                font.pixelSize: shellWindow ? shellWindow.eyebrowSize : 13
                                font.family: shellWindow ? shellWindow.uiFamily : "Noto Sans CJK SC"
                                font.letterSpacing: shellWindow ? shellWindow.scaled(1.2) : 1.2
                            }

                            Text {
                                text: Math.round(heroKpiWideCol.animatedSpeedup) + "x 提速"
                                color: shellWindow ? shellWindow.textStrong : "#f0f6ff"
                                font.pixelSize: shellWindow ? shellWindow.headerTitleSize : 42
                                font.weight: Font.Bold
                                font.family: shellWindow ? shellWindow.displayFamily : "Noto Sans CJK SC"
                            }

                            Text {
                                text: Math.round(heroKpiWideCol.animatedBefore) + " ms → " + Math.round(heroKpiWideCol.animatedAfter) + " ms"
                                color: shellWindow ? shellWindow.textSecondary : "#88abc5"
                                font.pixelSize: shellWindow ? shellWindow.sectionTitleSize : 28
                                font.weight: Font.DemiBold
                                font.family: shellWindow ? shellWindow.monoFamily : "JetBrains Mono"
                            }

                            Rectangle {
                                width: parent.width
                                height: 2
                                radius: 1
                                gradient: Gradient {
                                    orientation: Gradient.Horizontal
                                    GradientStop { position: 0.0; color: shellWindow ? shellWindow.accentMint : "#50e8b0" }
                                    GradientStop { position: 1.0; color: "transparent" }
                                }
                                opacity: 0.7
                            }
                        }
                    }
                }

                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: landingBottomBar.implicitHeight + (shellWindow ? shellWindow.scaled(16) : 16)
                    radius: shellWindow ? shellWindow.cardRadius : 16
                    color: shellWindow ? Qt.rgba(shellWindow.surfaceRaised.r, shellWindow.surfaceRaised.g, shellWindow.surfaceRaised.b, 0.85) : "#152535"
                    border.color: shellWindow ? Qt.rgba(shellWindow.borderSubtle.r, shellWindow.borderSubtle.g, shellWindow.borderSubtle.b, 0.4) : "#2a4560"
                    border.width: 1

                    Rectangle {
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.top: parent.top
                        anchors.leftMargin: shellWindow ? shellWindow.scaled(14) : 14
                        anchors.rightMargin: shellWindow ? shellWindow.scaled(14) : 14
                        height: 1
                        radius: height / 2
                        gradient: Gradient {
                            orientation: Gradient.Horizontal
                            GradientStop { position: 0.0; color: "transparent" }
                            GradientStop { position: 0.2; color: Qt.rgba(shellWindow ? shellWindow.accentIce.r : 0.49, shellWindow ? shellWindow.accentIce.g : 0.87, shellWindow ? shellWindow.accentIce.b : 1.0, 0.08) }
                            GradientStop { position: 0.5; color: Qt.rgba(shellWindow ? shellWindow.accentIce.r : 0.49, shellWindow ? shellWindow.accentIce.g : 0.87, shellWindow ? shellWindow.accentIce.b : 1.0, 0.32) }
                            GradientStop { position: 0.8; color: Qt.rgba(shellWindow ? shellWindow.accentGold.r : 0.94, shellWindow ? shellWindow.accentGold.g : 0.69, shellWindow ? shellWindow.accentGold.b : 0.38, 0.12) }
                            GradientStop { position: 1.0; color: "transparent" }
                        }
                        opacity: 0.6
                    }

                    RowLayout {
                        id: landingBottomBar
                        anchors.fill: parent
                        anchors.margins: shellWindow ? shellWindow.scaled(12) : 12
                        spacing: shellWindow ? shellWindow.compactGap : 8

                        Text {
                            text: "演示控制台"
                            color: shellWindow ? shellWindow.accentIce : "#64d4ff"
                            font.pixelSize: shellWindow ? shellWindow.eyebrowSize : 13
                            font.family: shellWindow ? shellWindow.uiFamily : "Noto Sans CJK SC"
                        }

                        Text {
                            text: shellWindow ? (shellWindow.performanceHeadlineShort || "153.778 ms / +91.66%") : "153.778 ms / +91.66%"
                            color: shellWindow ? shellWindow.textStrong : "#f0f6ff"
                            font.pixelSize: shellWindow ? shellWindow.sectionTitleSize : 28
                            font.weight: Font.Bold
                            font.family: shellWindow ? shellWindow.displayFamily : "Noto Sans CJK SC"
                        }

                        Item { Layout.fillWidth: true }

                        Repeater {
                            model: root.landingControlActions

                            delegate: OperatorActionButton {
                                shellWindow: root.shellWindow
                                actionData: DataUtils.objectOrEmpty(modelData)
                                compact: true
                                width: shellWindow ? shellWindow.scaled(180) : 180
                            }
                        }

                        Rectangle {
                            radius: shellWindow ? shellWindow.edgeRadius : 12
                            color: shellWindow ? Qt.rgba(shellWindow.surfaceQuiet.r, shellWindow.surfaceQuiet.g, shellWindow.surfaceQuiet.b, 0.72) : "#0d1822"
                            border.color: shellWindow ? Qt.rgba(shellWindow.accentIce.r, shellWindow.accentIce.g, shellWindow.accentIce.b, 0.34) : "#64d4ff"
                            border.width: 1
                            implicitWidth: flightBtn.implicitWidth + (shellWindow ? shellWindow.scaled(20) : 20)
                            implicitHeight: flightBtn.implicitHeight + (shellWindow ? shellWindow.scaled(12) : 12)
                            Text { id: flightBtn; anchors.centerIn: parent; text: "飞行态势"; color: shellWindow ? shellWindow.textStrong : "#f0f6ff"; font.pixelSize: shellWindow ? shellWindow.bodySize : 16; font.family: shellWindow ? shellWindow.uiFamily : "Noto Sans CJK SC" }
                            MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: if (shellWindow) shellWindow.currentPage = 2 }
                        }

                        Rectangle {
                            radius: shellWindow ? shellWindow.edgeRadius : 12
                            color: shellWindow ? Qt.rgba(shellWindow.surfaceQuiet.r, shellWindow.surfaceQuiet.g, shellWindow.surfaceQuiet.b, 0.72) : "#0d1822"
                            border.color: shellWindow ? Qt.rgba(shellWindow.accentMint.r, shellWindow.accentMint.g, shellWindow.accentMint.b, 0.4) : "#50e8b0"
                            border.width: 1
                            implicitWidth: actionBtn.implicitWidth + (shellWindow ? shellWindow.scaled(20) : 20)
                            implicitHeight: actionBtn.implicitHeight + (shellWindow ? shellWindow.scaled(12) : 12)
                            Text { id: actionBtn; anchors.centerIn: parent; text: "执行操作"; color: shellWindow ? shellWindow.textStrong : "#f0f6ff"; font.pixelSize: shellWindow ? shellWindow.bodySize : 16; font.family: shellWindow ? shellWindow.uiFamily : "Noto Sans CJK SC" }
                            MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: if (shellWindow) shellWindow.currentPage = 4 }
                        }
                    }
                }
            }
        }
    }


    Component {
        id: landingStackedComponent

        Item {
            anchors.fill: parent

            ColumnLayout {
                anchors.fill: parent
                spacing: shellWindow ? shellWindow.zoneGap : 10

                Item {
                    Layout.fillWidth: true
                    Layout.fillHeight: true

                    WorldMapStage {
                        anchors.fill: parent
                        shellWindow: root.shellWindow
                        stageActive: mainStack.currentIndex === 0
                        preloadAssets: true
                        trackData: root.trackData
                        currentPoint: root.currentPoint
                        headingDeg: root.headingDeg
                        currentLabel: ""
                        currentDetail: ""
                        anchorLabel: root.anchorValue
                        landingMode: true
                        bannerEyebrow: ""
                        bannerTitle: ""
                        bannerText: ""
                        bannerChips: []
                        showStageBadge: false
                        showScenarioBadge: false
                        showInfoPanels: false
                        preferBottomBannerDock: false
                    }

                    Rectangle {
                        id: heroKpiStacked
                        anchors.left: parent.left
                        anchors.bottom: parent.bottom
                        anchors.leftMargin: shellWindow ? shellWindow.scaled(16) : 16
                        anchors.bottomMargin: shellWindow ? shellWindow.scaled(16) : 16
                        width: heroKpiStackedCol.implicitWidth + (shellWindow ? shellWindow.scaled(22) : 22)
                        height: heroKpiStackedCol.implicitHeight + (shellWindow ? shellWindow.scaled(18) : 18)
                        radius: shellWindow ? shellWindow.cardRadius : 16
                        color: shellWindow ? Qt.rgba(shellWindow.shellInterior.r, shellWindow.shellInterior.g, shellWindow.shellInterior.b, 0.82) : "#11181fD0"
                        border.color: shellWindow ? Qt.rgba(shellWindow.accentMint.r, shellWindow.accentMint.g, shellWindow.accentMint.b, 0.3) : "#50e8b04D"
                        border.width: 1
                        opacity: 0

                        NumberAnimation on opacity { from: 0; to: 1; duration: 600; easing.type: Easing.OutCubic }

                        Column {
                            id: heroKpiStackedCol
                            anchors.centerIn: parent
                            spacing: shellWindow ? shellWindow.scaled(3) : 3

                            Text {
                                text: "TVM MetaSchedule 加速"
                                color: shellWindow ? shellWindow.accentIce : "#64d4ff"
                                font.pixelSize: shellWindow ? shellWindow.eyebrowSize : 13
                                font.family: shellWindow ? shellWindow.uiFamily : "Noto Sans CJK SC"
                                font.letterSpacing: shellWindow ? shellWindow.scaled(1.0) : 1.0
                            }

                            Text {
                                text: "12x 提速"
                                color: shellWindow ? shellWindow.textStrong : "#f0f6ff"
                                font.pixelSize: shellWindow ? shellWindow.sectionTitleSize : 28
                                font.weight: Font.Bold
                                font.family: shellWindow ? shellWindow.displayFamily : "Noto Sans CJK SC"
                            }

                            Text {
                                text: "1844 ms → 153 ms"
                                color: shellWindow ? shellWindow.textSecondary : "#88abc5"
                                font.pixelSize: shellWindow ? shellWindow.bodyEmphasisSize : 14
                                font.weight: Font.DemiBold
                                font.family: shellWindow ? shellWindow.monoFamily : "JetBrains Mono"
                            }

                            Rectangle {
                                width: parent.width
                                height: 2
                                radius: 1
                                gradient: Gradient {
                                    orientation: Gradient.Horizontal
                                    GradientStop { position: 0.0; color: shellWindow ? shellWindow.accentMint : "#50e8b0" }
                                    GradientStop { position: 1.0; color: "transparent" }
                                }
                                opacity: 0.7
                            }
                        }
                    }
                }

                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: stackedBar.implicitHeight + (shellWindow ? shellWindow.scaled(14) : 14)
                    radius: shellWindow ? shellWindow.cardRadius : 16
                    color: shellWindow ? Qt.rgba(shellWindow.surfaceRaised.r, shellWindow.surfaceRaised.g, shellWindow.surfaceRaised.b, 0.85) : "#152535"
                    border.color: shellWindow ? Qt.rgba(shellWindow.borderSubtle.r, shellWindow.borderSubtle.g, shellWindow.borderSubtle.b, 0.4) : "#2a4560"
                    border.width: 1

                    ColumnLayout {
                        id: stackedBar
                        anchors.fill: parent
                        anchors.margins: shellWindow ? shellWindow.scaled(10) : 10
                        spacing: shellWindow ? shellWindow.scaled(6) : 6

                        Text {
                            text: shellWindow ? (shellWindow.performanceHeadlineShort || "153.778 ms / +91.66%") : "153.778 ms / +91.66%"
                            color: shellWindow ? shellWindow.textStrong : "#f0f6ff"
                            font.pixelSize: shellWindow ? shellWindow.sectionTitleSize : 28
                            font.weight: Font.Bold
                            font.family: shellWindow ? shellWindow.displayFamily : "Noto Sans CJK SC"
                        }
                    }
                }
            }
        }
    }
}
