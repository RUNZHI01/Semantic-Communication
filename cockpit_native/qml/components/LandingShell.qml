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
    readonly property bool landingWide: shellWindow ? shellWindow.viewportWidth >= shellWindow.scaled(1320) : width >= 1320
    readonly property bool landingShortHeight: shellWindow ? shellWindow.shortViewport : height < 780
    readonly property int railWidth: shellWindow ? shellWindow.scaled(landingWide ? 222 : 212) : 222
    readonly property int landingStageLedgerWidth: shellWindow ? shellWindow.scaled(landingWide ? 298 : 268) : 298
    readonly property int flightSidebarWidth: shellWindow ? shellWindow.scaled(shellWindow.wideLayout ? 316 : 292) : 316
    readonly property int flightStageHeight: shellWindow ? shellWindow.scaled(shellWindow.compactLayout ? 332 : 478) : 478
    readonly property int flightStackedStageHeight: shellWindow ? shellWindow.scaled(shellWindow.compactLayout ? 316 : 372) : 372
    readonly property var landingStatusList: shellWindow ? shellWindow.previewItems(statusRows, landingWide ? 2 : 3) : []
    readonly property var landingScenarioList: shellWindow ? shellWindow.previewItems(scenarioList, 1) : []
    readonly property var timingPreviewList: shellWindow ? shellWindow.previewItems(stageTimingList, shellWindow.compactLayout ? 3 : 4) : []
    readonly property var evidencePreviewList: shellWindow ? shellWindow.previewItems(evidenceList, 4) : []
    readonly property var scenarioDeckList: shellWindow ? shellWindow.previewItems(scenarioList, shellWindow.wideLayout ? 4 : 3) : []
    readonly property var landingJumpList: shellWindow ? DataUtils.arrayOrEmpty(shellWindow.landingJumpModel) : []
    readonly property var landingWeakMetricList: shellWindow ? DataUtils.arrayOrEmpty(shellWindow.landingWeakMetricModel) : []
    readonly property var landingTelemetryPreviewList: shellWindow
        ? shellWindow.previewItems(shellWindow.landingTelemetryModel, landingWide ? 4 : 2)
        : []
    readonly property var actionPreviewList: shellWindow ? shellWindow.previewItems(actionList, 2) : []
    readonly property int landingTelemetryColumns: landingWide ? 4 : ((shellWindow ? shellWindow.viewportWidth : width) >= (shellWindow ? shellWindow.scaled(720) : 720) ? 2 : 1)
    readonly property int landingJumpColumns: (shellWindow ? shellWindow.viewportWidth : width) >= (shellWindow ? shellWindow.scaled(720) : 720) ? 2 : 1
    readonly property int landingActionColumns: landingWide ? 2 : ((shellWindow ? shellWindow.viewportWidth : width) >= (shellWindow ? shellWindow.scaled(720) : 720) ? 2 : 1)
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
    readonly property string landingLaunchBrief: compact(shellWindow ? shellWindow.launchHint : "--", landingShortHeight ? 40 : 56)
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
    readonly property int landingWideStageHeight: shellWindow ? shellWindow.scaled(landingShortHeight ? 320 : 362) : 362
    readonly property int landingStackedStageHeight: shellWindow ? shellWindow.scaled(landingShortHeight ? 276 : 316) : 316
    readonly property string landingStageSubtitle: "世界地图保持主墙位，系统回注、弱网策略与执行门控全部退到支撑轨。"
    readonly property string mapCtaLabel: landingShortHeight ? "飞行合同" : "进入飞行合同"
    readonly property string dockCtaLabel: landingShortHeight ? "执行坞站" : "进入执行坞站"

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
            Layout.fillWidth: true
            radius: shellWindow ? shellWindow.edgeRadius + shellWindow.scaled(1) : 13
            color: shellWindow ? shellWindow.surfaceRaised : "#15202a"
            border.color: Qt.rgba(jumpAccent.r, jumpAccent.g, jumpAccent.b, 0.72)
            border.width: 1
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

    Rectangle {
        id: shellSurface
        anchors.fill: parent
        anchors.leftMargin: (shellWindow ? shellWindow.safeLeft : 0) + (shellWindow ? shellWindow.outerPadding : 12)
        anchors.topMargin: (shellWindow ? shellWindow.safeTop : 0) + (shellWindow ? shellWindow.outerPadding : 12)
        anchors.rightMargin: (shellWindow ? shellWindow.safeRight : 0) + (shellWindow ? shellWindow.outerPadding : 12)
        anchors.bottomMargin: (shellWindow ? shellWindow.safeBottom : 0) + (shellWindow ? shellWindow.outerPadding : 12)
        radius: shellWindow ? shellWindow.panelRadius + shellWindow.scaled(10) : 30
        color: shellWindow ? shellWindow.shellExterior : "#0b1117"
        border.color: shellWindow ? shellWindow.borderSubtle : "#2a3944"
        border.width: 1
        clip: true

        Rectangle {
            anchors.fill: parent
            gradient: Gradient {
                GradientStop { position: 0.0; color: shellWindow ? shellWindow.canopyTop : "#1b252e" }
                GradientStop { position: 0.16; color: shellWindow ? shellWindow.shellInterior : "#11181f" }
                GradientStop { position: 1.0; color: shellWindow ? shellWindow.canopyBottom : "#0b1015" }
            }
        }

        Rectangle {
            width: parent.width * 0.5
            height: parent.height * 0.36
            radius: width / 2
            color: shellWindow ? shellWindow.accentGold : "#c6ab7d"
            opacity: 0.05
            x: -width * 0.16
            y: -height * 0.22
        }

        Rectangle {
            width: parent.width * 0.34
            height: parent.height * 0.28
            radius: width / 2
            color: shellWindow ? shellWindow.accentIce : "#86c7d4"
            opacity: 0.06
            x: parent.width - (width * 0.76)
            y: parent.height * 0.08
        }

        Rectangle {
            anchors.fill: parent
            anchors.margins: shellWindow ? shellWindow.scaled(5) : 5
            radius: parent.radius - (shellWindow ? shellWindow.scaled(5) : 5)
            color: "transparent"
            border.color: "#0dffffff"
            border.width: 1
        }

        Rectangle {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            height: shellWindow ? shellWindow.scaled(2) : 2
            gradient: Gradient {
                orientation: Gradient.Horizontal
                GradientStop { position: 0.0; color: "transparent" }
                GradientStop { position: 0.18; color: Qt.rgba(shellWindow.accentGold.r, shellWindow.accentGold.g, shellWindow.accentGold.b, 0.16) }
                GradientStop { position: 0.5; color: Qt.rgba(shellWindow.accentGold.r, shellWindow.accentGold.g, shellWindow.accentGold.b, 0.78) }
                GradientStop { position: 0.82; color: Qt.rgba(shellWindow.accentIce.r, shellWindow.accentIce.g, shellWindow.accentIce.b, 0.28) }
                GradientStop { position: 1.0; color: "transparent" }
            }
        }

        Rectangle {
            anchors.left: parent.left
            anchors.top: parent.top
            anchors.bottom: parent.bottom
            anchors.leftMargin: shellWindow ? shellWindow.scaled(6) : 6
            anchors.topMargin: shellWindow ? shellWindow.scaled(18) : 18
            anchors.bottomMargin: shellWindow ? shellWindow.scaled(18) : 18
            width: shellWindow ? shellWindow.scaled(3) : 3
            radius: width / 2
            gradient: Gradient {
                GradientStop { position: 0.0; color: "transparent" }
                GradientStop { position: 0.18; color: Qt.rgba(shellWindow.accentGold.r, shellWindow.accentGold.g, shellWindow.accentGold.b, 0.18) }
                GradientStop { position: 0.52; color: Qt.rgba(shellWindow.accentGold.r, shellWindow.accentGold.g, shellWindow.accentGold.b, 0.84) }
                GradientStop { position: 0.84; color: Qt.rgba(shellWindow.accentIce.r, shellWindow.accentIce.g, shellWindow.accentIce.b, 0.26) }
                GradientStop { position: 1.0; color: "transparent" }
            }
            opacity: 0.92
        }

        Rectangle {
            anchors.right: parent.right
            anchors.top: parent.top
            anchors.bottom: parent.bottom
            anchors.rightMargin: shellWindow ? shellWindow.scaled(6) : 6
            anchors.topMargin: shellWindow ? shellWindow.scaled(32) : 32
            anchors.bottomMargin: shellWindow ? shellWindow.scaled(32) : 32
            width: shellWindow ? shellWindow.scaled(2) : 2
            radius: width / 2
            gradient: Gradient {
                GradientStop { position: 0.0; color: "transparent" }
                GradientStop { position: 0.16; color: Qt.rgba(shellWindow.accentIce.r, shellWindow.accentIce.g, shellWindow.accentIce.b, 0.14) }
                GradientStop { position: 0.5; color: Qt.rgba(shellWindow.accentIce.r, shellWindow.accentIce.g, shellWindow.accentIce.b, 0.7) }
                GradientStop { position: 0.84; color: Qt.rgba(shellWindow.accentGold.r, shellWindow.accentGold.g, shellWindow.accentGold.b, 0.18) }
                GradientStop { position: 1.0; color: "transparent" }
            }
            opacity: 0.72
        }

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: shellWindow ? shellWindow.shellPadding : 18
            spacing: shellWindow ? shellWindow.zoneGap : 14

            ShellHeader {
                Layout.fillWidth: true
                shellWindow: root.shellWindow
                currentIndex: shellWindow ? shellWindow.currentPage : 0
                onPageRequested: if (shellWindow) shellWindow.currentPage = index
            }

            StackLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true
                currentIndex: shellWindow ? shellWindow.currentPage : 0

                Item {
                    Loader {
                        anchors.fill: parent
                        sourceComponent: landingWide ? landingWideComponent : landingStackedComponent
                    }
                }

                Item {
                    Layout.fillWidth: true
                    Layout.fillHeight: true

                    GridLayout {
                        anchors.fill: parent
                        columns: shellWindow && shellWindow.wideLayout ? 2 : 1
                        columnSpacing: shellWindow ? shellWindow.zoneGap : 14
                        rowSpacing: shellWindow ? shellWindow.zoneGap : 14

                        ShellCard {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            shellWindow: root.shellWindow
                            accentColor: shellWindow ? shellWindow.accentGold : "#c6ab7d"
                            eyebrow: "SYSTEM BOARD / 板态总览"
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
                                eyebrow: "EVIDENCE / 事实边界"
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
                                eyebrow: "META / 启动姿态"
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

                Item {
                    Layout.fillWidth: true
                    Layout.fillHeight: true

                    Loader {
                        anchors.fill: parent
                        sourceComponent: shellWindow && shellWindow.wideLayout ? flightWideComponent : flightStackedComponent
                    }
                }

                Item {
                    Layout.fillWidth: true
                    Layout.fillHeight: true

                    ColumnLayout {
                        anchors.fill: parent
                        spacing: shellWindow ? shellWindow.zoneGap : 14

                        ShellCard {
                            Layout.fillWidth: true
                            shellWindow: root.shellWindow
                            accentColor: shellWindow ? shellWindow.accentGold : "#c6ab7d"
                            eyebrow: "WEAK-LINK / 推荐策略"
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
                                eyebrow: "SCENARIOS / 对照池"
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
                                eyebrow: "TIMINGS / 证据摘要"
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

                Item {
                    Layout.fillWidth: true
                    Layout.fillHeight: true

                    GridLayout {
                        anchors.fill: parent
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
                                eyebrow: "LAUNCH / 启动命令"
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
        }
    }

    Component {
        id: flightWideComponent

        Item {
            anchors.fill: parent

            RowLayout {
                anchors.fill: parent
                spacing: shellWindow ? shellWindow.zoneGap : 14

                ColumnLayout {
                    Layout.preferredWidth: root.flightSidebarWidth
                    Layout.minimumWidth: root.flightSidebarWidth
                    Layout.maximumWidth: root.flightSidebarWidth
                    Layout.fillHeight: true
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
                        eyebrow: "CONTRACT / 数据合同"
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
                                    text: "边栏摘要 / SIDEBAR NOTE"
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

                ShellCard {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    Layout.minimumWidth: shellWindow ? shellWindow.scaled(700) : 700
                    shellWindow: root.shellWindow
                    accentColor: shellWindow ? shellWindow.accentIce : "#86c7d4"
                    eyebrow: "FLIGHT STAGE / 飞行合同"
                    title: shellWindow ? shellWindow.missionCallSignValue + " · " + shellWindow.aircraftIdValue : "飞行合同"
                    subtitle: shellWindow ? shellWindow.activeSourceLabel : ""

                    Item {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        implicitHeight: root.flightStageHeight

                        WorldMapStage {
                            anchors.fill: parent
                            shellWindow: root.shellWindow
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
                        }

                        InsetPanel {
                            anchors.left: parent.left
                            anchors.top: parent.top
                            anchors.leftMargin: shellWindow ? shellWindow.scaled(16) : 16
                            anchors.topMargin: shellWindow ? shellWindow.scaled(76) : 76
                            width: Math.min(
                                parent.width - ((shellWindow ? shellWindow.scaled(32) : 32) * 2),
                                root.landingStageLedgerWidth
                            )
                            shellWindow: root.shellWindow
                            accentColor: shellWindow ? shellWindow.accentGold : "#c6ab7d"
                            fillColor: "#d509121a"
                            prominent: true

                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: shellWindow ? shellWindow.scaled(3) : 3

                                Text {
                                    text: "MAP CONTEXT / 主视区摘要"
                                    color: shellWindow ? shellWindow.accentGold : "#c6ab7d"
                                    font.pixelSize: shellWindow ? shellWindow.captionSize : 10
                                    font.family: shellWindow ? shellWindow.monoFamily : "JetBrains Mono"
                                    font.letterSpacing: shellWindow ? shellWindow.scaled(0.7) : 0.7
                                }

                                Text {
                                    Layout.fillWidth: true
                                    text: root.landingStageLedgerText
                                    color: shellWindow ? shellWindow.textStrong : "#f5efe4"
                                    font.pixelSize: shellWindow ? shellWindow.bodySize : 13
                                    font.weight: Font.DemiBold
                                    font.family: shellWindow ? shellWindow.uiFamily : "Noto Sans CJK SC"
                                    wrapMode: Text.WordWrap
                                    maximumLineCount: 3
                                    elide: Text.ElideRight
                                }

                                Text {
                                    Layout.fillWidth: true
                                    text: root.landingStageLedgerSupport
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
                        eyebrow: "FLIGHT STAGE / 飞行合同"
                        title: shellWindow ? shellWindow.missionCallSignValue + " · " + shellWindow.aircraftIdValue : "飞行合同"
                        subtitle: shellWindow ? shellWindow.activeSourceLabel : ""

                        Item {
                            Layout.fillWidth: true
                            implicitHeight: root.flightStackedStageHeight

                            WorldMapStage {
                                anchors.fill: parent
                                shellWindow: root.shellWindow
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
                        eyebrow: "CONTRACT / 数据合同"
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

                Flickable {
                    id: wideScroller
                    anchors.fill: parent
                    contentWidth: width
                    contentHeight: wideColumn.implicitHeight
                    clip: true
                    boundsBehavior: Flickable.StopAtBounds
                    interactive: contentHeight > height

                    ScrollBar.vertical: ScrollBar {
                        policy: wideScroller.interactive ? ScrollBar.AsNeeded : ScrollBar.AlwaysOff
                    }

                ColumnLayout {
                    id: wideColumn
                    width: wideScroller.width
                    spacing: shellWindow ? shellWindow.zoneGap : 14

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: shellWindow ? shellWindow.zoneGap : 14

                        ColumnLayout {
                            Layout.preferredWidth: root.railWidth
                            Layout.minimumWidth: root.railWidth
                            Layout.maximumWidth: root.railWidth
                            Layout.alignment: Qt.AlignTop
                            spacing: shellWindow ? shellWindow.zoneGap : 14

                            ShellCard {
                                Layout.fillWidth: true
                                shellWindow: root.shellWindow
                                accentColor: shellWindow ? shellWindow.accentGold : "#c6ab7d"
                                eyebrow: "系统回注 / SYSTEM RAIL"
                                title: "板态摘要与事实边界"
                                subtitle: "继续呈现仓库快照、心跳、事件与事实边界。"

                                InsetPanel {
                                    Layout.fillWidth: true
                                    shellWindow: root.shellWindow
                                    accentColor: shellWindow ? shellWindow.accentGold : "#c6ab7d"

                                    ColumnLayout {
                                        id: systemBriefColumn
                                        Layout.fillWidth: true
                                        spacing: shellWindow ? shellWindow.scaled(3) : 3

                                        Text {
                                            text: "任务简报 / MISSION BRIEF"
                                            color: shellWindow ? shellWindow.accentGold : "#c6ab7d"
                                            font.pixelSize: shellWindow ? shellWindow.captionSize : 10
                                            font.family: shellWindow ? shellWindow.monoFamily : "JetBrains Mono"
                                            font.letterSpacing: shellWindow ? shellWindow.scaled(0.6) : 0.6
                                        }

                                        Text {
                                            Layout.fillWidth: true
                                            text: root.landingBriefText
                                            color: shellWindow ? shellWindow.textPrimary : "#d7dde2"
                                            font.pixelSize: shellWindow ? shellWindow.bodySize : 13
                                            font.family: shellWindow ? shellWindow.uiFamily : "Noto Sans CJK SC"
                                            wrapMode: Text.WordWrap
                                            maximumLineCount: 2
                                            elide: Text.ElideRight
                                        }

                                        Text {
                                            Layout.fillWidth: true
                                            text: (shellWindow ? shellWindow.activeSourceLabel : "--") + "  ·  " + root.anchorStatus
                                            color: shellWindow ? shellWindow.textMuted : "#6f7f8a"
                                            font.pixelSize: shellWindow ? shellWindow.captionSize + 1 : 11
                                            font.family: shellWindow ? shellWindow.uiFamily : "Noto Sans CJK SC"
                                            wrapMode: Text.WordWrap
                                        }
                                    }
                                }

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

                                ColumnLayout {
                                    Layout.fillWidth: true
                                    spacing: shellWindow ? shellWindow.compactGap : 8

                                    Repeater {
                                        model: root.landingStatusList

                                        delegate: MetricTile {
                                            readonly property var rowData: DataUtils.objectOrEmpty(modelData)
                                            shellWindow: root.shellWindow
                                            Layout.fillWidth: true
                                            label: String(rowData["label"] || "--")
                                            value: String(rowData["value"] || "--")
                                            detail: "状态语义: " + String(rowData["tone"] || "neutral")
                                            tone: String(rowData["tone"] || "neutral")
                                        }
                                    }
                                }
                            }

                            ShellCard {
                                Layout.fillWidth: true
                                shellWindow: root.shellWindow
                                accentColor: shellWindow ? shellWindow.accentIce : "#86c7d4"
                                eyebrow: "事实边界 / BOUNDARY"
                                title: "仓库路径与软件安全"
                                subtitle: "继续直接读取 repo-backed 合同，并保留软件渲染安全入口。"

                                MetricTile {
                                    shellWindow: root.shellWindow
                                    Layout.fillWidth: true
                                    label: "快照路径"
                                    value: shellWindow ? shellWindow.snapshotRelativePath : "--"
                                    detail: shellWindow ? shellWindow.eventTimeValue : "--"
                                    tone: shellWindow ? shellWindow.recentEventTone : "neutral"
                                }

                                MetricTile {
                                    shellWindow: root.shellWindow
                                    Layout.fillWidth: true
                                    label: "启动入口"
                                    value: compact(shellWindow ? shellWindow.launchHint : "--", 52)
                                    detail: shellWindow ? shellWindow.footerNote : ""
                                    tone: shellWindow && shellWindow.softwareRenderEnabled ? "warning" : "online"
                                }
                            }
                        }

                        ShellCard {
                            Layout.fillWidth: true
                            Layout.minimumWidth: shellWindow ? shellWindow.scaled(620) : 620
                            Layout.alignment: Qt.AlignTop
                            shellWindow: root.shellWindow
                            accentColor: shellWindow ? shellWindow.accentIce : "#86c7d4"
                            eyebrow: "全球主墙板 / GLOBAL STAGE"
                            title: shellWindow ? shellWindow.landingSummaryTitle : "地图优先的原生命令壳"
                            subtitle: root.landingStageSubtitle

                            Item {
                                Layout.fillWidth: true
                                implicitHeight: root.landingWideStageHeight

                                WorldMapStage {
                                    anchors.fill: parent
                                    shellWindow: root.shellWindow
                                    trackData: root.trackData
                                    currentPoint: root.currentPoint
                                    headingDeg: root.headingDeg
                                    currentLabel: shellWindow ? shellWindow.landingMapBannerTitle : ""
                                    currentDetail: shellWindow ? shellWindow.activeSourceLabel : ""
                                    anchorLabel: root.anchorValue
                                    scenarioLabel: root.recommendedScenarioLabel
                                    scenarioTone: shellWindow ? shellWindow.liveAnchorTone : "neutral"
                                    landingMode: true
                                    bannerEyebrow: "全球指挥主舞台 / GLOBAL COMMAND STAGE"
                                    bannerTitle: shellWindow ? shellWindow.landingMapBannerTitle : ""
                                    bannerText: shellWindow ? shellWindow.landingMapBannerText : ""
                                    bannerChips: shellWindow ? shellWindow.landingStageChipModel : []
                                }

                                Rectangle {
                                    anchors.right: parent.right
                                    anchors.bottom: parent.bottom
                                    anchors.margins: shellWindow ? shellWindow.scaled(14) : 14
                                    radius: shellWindow ? shellWindow.edgeRadius + shellWindow.scaled(1) : 13
                                    color: "#da09131f"
                                    border.color: shellWindow ? shellWindow.accentIce : "#86c7d4"
                                    border.width: 1
                                    implicitWidth: mapCtaColumn.implicitWidth + ((shellWindow ? shellWindow.scaled(13) : 13) * 2)
                                    implicitHeight: mapCtaColumn.implicitHeight + ((shellWindow ? shellWindow.scaled(7) : 7) * 2)

                                    Column {
                                        id: mapCtaColumn
                                        anchors.centerIn: parent
                                        spacing: shellWindow ? shellWindow.scaled(1) : 1

                                        Text {
                                            text: "直达"
                                            color: shellWindow ? shellWindow.accentIce : "#86c7d4"
                                            font.pixelSize: shellWindow ? shellWindow.captionSize : 10
                                            font.family: shellWindow ? shellWindow.monoFamily : "JetBrains Mono"
                                            horizontalAlignment: Text.AlignHCenter
                                        }

                                        Row {
                                            spacing: shellWindow ? shellWindow.compactGap : 8

                                            Text {
                                                text: root.mapCtaLabel
                                                color: shellWindow ? shellWindow.textStrong : "#f5efe4"
                                                font.pixelSize: shellWindow ? shellWindow.bodySize : 13
                                                font.weight: Font.DemiBold
                                                font.family: shellWindow ? shellWindow.uiFamily : "Noto Sans CJK SC"
                                            }

                                            Text {
                                                text: ">"
                                                color: shellWindow ? shellWindow.accentIce : "#86c7d4"
                                                font.pixelSize: shellWindow ? shellWindow.bodyEmphasisSize : 14
                                                font.weight: Font.DemiBold
                                                font.family: shellWindow ? shellWindow.monoFamily : "JetBrains Mono"
                                            }
                                        }
                                    }

                                    MouseArea {
                                        anchors.fill: parent
                                        hoverEnabled: true
                                        cursorShape: Qt.PointingHandCursor
                                        onClicked: if (shellWindow) shellWindow.currentPage = 2
                                    }
                                }
                            }

                            RowLayout {
                                Layout.fillWidth: true
                                spacing: shellWindow ? shellWindow.zoneGap : 12

                                GridLayout {
                                    Layout.fillWidth: true
                                    Layout.alignment: Qt.AlignTop
                                    columns: 2
                                    columnSpacing: shellWindow ? shellWindow.compactGap : 8
                                    rowSpacing: shellWindow ? shellWindow.compactGap : 8

                                    Repeater {
                                        model: root.landingTelemetryPreviewList
                                        delegate: landingTelemetryReadoutDelegate
                                    }
                                }

                                InsetPanel {
                                    Layout.preferredWidth: shellWindow ? shellWindow.scaled(240) : 240
                                    Layout.maximumWidth: shellWindow ? shellWindow.scaled(260) : 260
                                    Layout.alignment: Qt.AlignTop
                                    shellWindow: root.shellWindow
                                    accentColor: shellWindow ? shellWindow.accentIce : "#86c7d4"
                                    prominent: true

                                    Text {
                                        Layout.fillWidth: true
                                        text: "STAGE LEDGER / 主墙摘记"
                                        color: shellWindow ? shellWindow.accentIce : "#86c7d4"
                                        font.pixelSize: shellWindow ? shellWindow.captionSize : 10
                                        font.family: shellWindow ? shellWindow.monoFamily : "JetBrains Mono"
                                        font.letterSpacing: shellWindow ? shellWindow.scaled(0.7) : 0.7
                                    }

                                    Text {
                                        Layout.fillWidth: true
                                        text: root.landingStageLedgerText
                                        color: shellWindow ? shellWindow.textStrong : "#f5efe4"
                                        font.pixelSize: shellWindow ? shellWindow.bodySize : 13
                                        font.family: shellWindow ? shellWindow.uiFamily : "Noto Sans CJK SC"
                                        wrapMode: Text.WordWrap
                                        maximumLineCount: 4
                                        elide: Text.ElideRight
                                    }

                                    Text {
                                        Layout.fillWidth: true
                                        text: root.landingStageLedgerSupport
                                        color: shellWindow ? shellWindow.textSecondary : "#9aa8b1"
                                        font.pixelSize: shellWindow ? shellWindow.captionSize + 1 : 11
                                        font.family: shellWindow ? shellWindow.uiFamily : "Noto Sans CJK SC"
                                        wrapMode: Text.WordWrap
                                        maximumLineCount: 3
                                        elide: Text.ElideRight
                                    }

                                    RowLayout {
                                        Layout.fillWidth: true
                                        spacing: shellWindow ? shellWindow.compactGap : 8

                                        Rectangle {
                                            Layout.fillWidth: true
                                            radius: shellWindow ? shellWindow.edgeRadius : 12
                                            color: shellWindow ? shellWindow.toneFill("online") : "#102033"
                                            border.color: shellWindow ? shellWindow.accentIce : "#86c7d4"
                                            border.width: 1
                                            implicitHeight: shellWindow ? shellWindow.scaled(38) : 38

                                            Text {
                                                anchors.centerIn: parent
                                                text: "飞行合同 / Flight"
                                                color: shellWindow ? shellWindow.textStrong : "#f5efe4"
                                                font.pixelSize: shellWindow ? shellWindow.captionSize + 1 : 11
                                                font.weight: Font.DemiBold
                                                font.family: shellWindow ? shellWindow.uiFamily : "Noto Sans CJK SC"
                                            }

                                            MouseArea {
                                                anchors.fill: parent
                                                hoverEnabled: true
                                                cursorShape: Qt.PointingHandCursor
                                                onClicked: if (shellWindow) shellWindow.currentPage = 2
                                            }
                                        }

                                        Rectangle {
                                            Layout.fillWidth: true
                                            radius: shellWindow ? shellWindow.edgeRadius : 12
                                            color: shellWindow ? shellWindow.toneFill("warning") : "#251f18"
                                            border.color: shellWindow ? shellWindow.accentGold : "#c6ab7d"
                                            border.width: 1
                                            implicitHeight: shellWindow ? shellWindow.scaled(38) : 38

                                            Text {
                                                anchors.centerIn: parent
                                                text: "执行坞站 / Dock"
                                                color: shellWindow ? shellWindow.textStrong : "#f5efe4"
                                                font.pixelSize: shellWindow ? shellWindow.captionSize + 1 : 11
                                                font.weight: Font.DemiBold
                                                font.family: shellWindow ? shellWindow.uiFamily : "Noto Sans CJK SC"
                                            }

                                            MouseArea {
                                                anchors.fill: parent
                                                hoverEnabled: true
                                                cursorShape: Qt.PointingHandCursor
                                                onClicked: if (shellWindow) shellWindow.currentPage = 4
                                            }
                                        }
                                    }
                                }
                            }
                        }

                        ColumnLayout {
                            Layout.preferredWidth: root.railWidth
                            Layout.minimumWidth: root.railWidth
                            Layout.maximumWidth: root.railWidth
                            Layout.alignment: Qt.AlignTop
                            spacing: shellWindow ? shellWindow.zoneGap : 14

                            ShellCard {
                                Layout.fillWidth: true
                                shellWindow: root.shellWindow
                                accentColor: shellWindow ? shellWindow.accentMint : "#93bea5"
                                eyebrow: "弱网摘要 / WEAK-LINK"
                                title: root.recommendedScenarioLabel
                                subtitle: "在线锚点 " + root.anchorValue + "  ·  " + root.anchorStatus

                                InsetPanel {
                                    Layout.fillWidth: true
                                    shellWindow: root.shellWindow
                                    accentColor: shellWindow ? shellWindow.accentMint : "#93bea5"

                                    ColumnLayout {
                                        id: weakSummaryColumn
                                        Layout.fillWidth: true
                                        spacing: shellWindow ? shellWindow.scaled(3) : 3

                                        Text {
                                            text: "推荐剧本 / RECOMMENDED"
                                            color: shellWindow ? shellWindow.accentMint : "#93bea5"
                                            font.pixelSize: shellWindow ? shellWindow.captionSize : 10
                                            font.family: shellWindow ? shellWindow.monoFamily : "JetBrains Mono"
                                            font.letterSpacing: shellWindow ? shellWindow.scaled(0.6) : 0.6
                                        }

                                        Text {
                                            Layout.fillWidth: true
                                            text: root.recommendedScenarioBrief
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
                                        model: root.landingWeakMetricList
                                        delegate: landingTelemetryReadoutDelegate
                                    }
                                }

                                ColumnLayout {
                                    Layout.fillWidth: true
                                    visible: root.landingScenarioList.length > 0
                                    spacing: shellWindow ? shellWindow.compactGap : 8

                                    Repeater {
                                        model: root.landingScenarioList
                                        delegate: landingScenarioPreviewDelegate
                                    }
                                }
                            }

                            ShellCard {
                                Layout.fillWidth: true
                                shellWindow: root.shellWindow
                                accentColor: shellWindow ? shellWindow.accentGold : "#c6ab7d"
                                eyebrow: "页面直达 / JUMP RAIL"
                                title: "页面入口与轻量跳转"
                                subtitle: "让地图留在主位，系统、飞行、弱网与执行页保持显式进入。"

                                ColumnLayout {
                                    Layout.fillWidth: true
                                    spacing: shellWindow ? shellWindow.compactGap : 8

                                    Repeater {
                                        model: root.landingJumpList
                                        delegate: landingJumpCardDelegate
                                    }
                                }
                            }
                        }
                    }

                    ShellCard {
                        Layout.fillWidth: true
                        shellWindow: root.shellWindow
                        accentColor: shellWindow ? shellWindow.accentGold : "#c6ab7d"
                        eyebrow: "执行坞站 / ACTION DOCK"
                        title: "轻量动作预览与软件安全启动"
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
                            columns: root.landingActionColumns
                            columnSpacing: shellWindow ? shellWindow.compactGap : 8
                            rowSpacing: shellWindow ? shellWindow.compactGap : 8

                            Repeater {
                                model: root.actionPreviewList
                                delegate: landingActionPreviewDelegate
                            }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: shellWindow ? shellWindow.zoneGap : 12

                            InsetPanel {
                                Layout.fillWidth: true
                                shellWindow: root.shellWindow
                                accentColor: shellWindow ? shellWindow.accentIce : "#86c7d4"

                                Text {
                                    Layout.fillWidth: true
                                    text: "LAUNCH / 安全启动"
                                    color: shellWindow ? shellWindow.accentIce : "#86c7d4"
                                    font.pixelSize: shellWindow ? shellWindow.captionSize : 10
                                    font.family: shellWindow ? shellWindow.monoFamily : "JetBrains Mono"
                                    font.letterSpacing: shellWindow ? shellWindow.scaled(0.7) : 0.7
                                }

                                Text {
                                    Layout.fillWidth: true
                                    text: shellWindow ? shellWindow.launchHint : "--"
                                    color: shellWindow ? shellWindow.textPrimary : "#d7dde2"
                                    font.pixelSize: shellWindow ? shellWindow.captionSize + 1 : 11
                                    font.family: shellWindow ? shellWindow.monoFamily : "JetBrains Mono"
                                    wrapMode: Text.WrapAnywhere
                                }

                                Text {
                                    Layout.fillWidth: true
                                    text: root.anchorProbeBrief
                                    color: shellWindow ? shellWindow.textSecondary : "#9aa8b1"
                                    font.pixelSize: shellWindow ? shellWindow.captionSize + 1 : 11
                                    font.family: shellWindow ? shellWindow.uiFamily : "Noto Sans CJK SC"
                                    wrapMode: Text.WordWrap
                                    maximumLineCount: 2
                                    elide: Text.ElideRight
                                }
                            }

                            Rectangle {
                                radius: shellWindow ? shellWindow.edgeRadius + shellWindow.scaled(1) : 13
                                color: "#da09131f"
                                border.color: shellWindow ? shellWindow.accentGold : "#c6ab7d"
                                border.width: 1
                                implicitWidth: dockCtaColumn.implicitWidth + ((shellWindow ? shellWindow.scaled(13) : 13) * 2)
                                implicitHeight: dockCtaColumn.implicitHeight + ((shellWindow ? shellWindow.scaled(7) : 7) * 2)

                                Column {
                                    id: dockCtaColumn
                                    anchors.centerIn: parent
                                    spacing: shellWindow ? shellWindow.scaled(1) : 1

                                    Text {
                                        text: "直达"
                                        color: shellWindow ? shellWindow.accentGold : "#c6ab7d"
                                        font.pixelSize: shellWindow ? shellWindow.captionSize : 10
                                        font.family: shellWindow ? shellWindow.monoFamily : "JetBrains Mono"
                                        horizontalAlignment: Text.AlignHCenter
                                    }

                                    Row {
                                        spacing: shellWindow ? shellWindow.compactGap : 8

                                        Text {
                                            text: root.dockCtaLabel
                                            color: shellWindow ? shellWindow.textStrong : "#f5efe4"
                                            font.pixelSize: shellWindow ? shellWindow.bodySize : 13
                                            font.weight: Font.DemiBold
                                            font.family: shellWindow ? shellWindow.uiFamily : "Noto Sans CJK SC"
                                        }

                                        Text {
                                            text: ">"
                                            color: shellWindow ? shellWindow.accentGold : "#c6ab7d"
                                            font.pixelSize: shellWindow ? shellWindow.bodyEmphasisSize : 14
                                            font.weight: Font.DemiBold
                                            font.family: shellWindow ? shellWindow.monoFamily : "JetBrains Mono"
                                        }
                                    }
                                }

                                MouseArea {
                                    anchors.fill: parent
                                    hoverEnabled: true
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: if (shellWindow) shellWindow.currentPage = 4
                                }
                            }
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

                Flickable {
                    id: stackedScroller
                    anchors.fill: parent
                    contentWidth: width
                    contentHeight: stackedColumn.implicitHeight
                    clip: true
                    boundsBehavior: Flickable.StopAtBounds
                    interactive: contentHeight > height

                    ScrollBar.vertical: ScrollBar {
                        policy: stackedScroller.interactive ? ScrollBar.AsNeeded : ScrollBar.AlwaysOff
                    }

                ColumnLayout {
                    id: stackedColumn
                    width: stackedScroller.width
                    spacing: shellWindow ? shellWindow.zoneGap : 14

                    ShellCard {
                        Layout.fillWidth: true
                        shellWindow: root.shellWindow
                        accentColor: shellWindow ? shellWindow.accentIce : "#86c7d4"
                        eyebrow: "全球主墙板 / GLOBAL STAGE"
                        title: shellWindow ? shellWindow.landingSummaryTitle : "地图优先的原生命令壳"
                        subtitle: root.landingStageSubtitle

                        Item {
                            Layout.fillWidth: true
                            implicitHeight: root.landingStackedStageHeight

                            WorldMapStage {
                                anchors.fill: parent
                                shellWindow: root.shellWindow
                                trackData: root.trackData
                                currentPoint: root.currentPoint
                                headingDeg: root.headingDeg
                                currentLabel: shellWindow ? shellWindow.landingMapBannerTitle : ""
                                currentDetail: shellWindow ? shellWindow.activeSourceLabel : ""
                                anchorLabel: root.anchorValue
                                scenarioLabel: root.recommendedScenarioLabel
                                scenarioTone: shellWindow ? shellWindow.liveAnchorTone : "neutral"
                                landingMode: true
                                bannerEyebrow: "全球指挥主舞台 / GLOBAL COMMAND STAGE"
                                bannerTitle: shellWindow ? shellWindow.landingMapBannerTitle : ""
                                bannerText: shellWindow ? shellWindow.landingMapBannerText : ""
                                bannerChips: shellWindow ? shellWindow.landingStageChipModel : []
                            }

                            Rectangle {
                                anchors.right: parent.right
                                anchors.bottom: parent.bottom
                                anchors.margins: shellWindow ? shellWindow.scaled(12) : 12
                                radius: shellWindow ? shellWindow.edgeRadius + shellWindow.scaled(1) : 13
                                color: "#da09131f"
                                border.color: shellWindow ? shellWindow.accentIce : "#86c7d4"
                                border.width: 1
                                implicitWidth: stackedMapCtaColumn.implicitWidth + ((shellWindow ? shellWindow.scaled(12) : 12) * 2)
                                implicitHeight: stackedMapCtaColumn.implicitHeight + ((shellWindow ? shellWindow.scaled(7) : 7) * 2)

                                Column {
                                    id: stackedMapCtaColumn
                                    anchors.centerIn: parent
                                    spacing: shellWindow ? shellWindow.scaled(1) : 1

                                    Text {
                                        text: "直达"
                                        color: shellWindow ? shellWindow.accentIce : "#86c7d4"
                                        font.pixelSize: shellWindow ? shellWindow.captionSize : 10
                                        font.family: shellWindow ? shellWindow.monoFamily : "JetBrains Mono"
                                        horizontalAlignment: Text.AlignHCenter
                                    }

                                    Row {
                                        spacing: shellWindow ? shellWindow.compactGap : 8

                                        Text {
                                            text: root.mapCtaLabel
                                            color: shellWindow ? shellWindow.textStrong : "#f5efe4"
                                            font.pixelSize: shellWindow ? shellWindow.bodySize : 13
                                            font.weight: Font.DemiBold
                                            font.family: shellWindow ? shellWindow.uiFamily : "Noto Sans CJK SC"
                                        }

                                        Text {
                                            text: ">"
                                            color: shellWindow ? shellWindow.accentIce : "#86c7d4"
                                            font.pixelSize: shellWindow ? shellWindow.bodyEmphasisSize : 14
                                            font.weight: Font.DemiBold
                                            font.family: shellWindow ? shellWindow.monoFamily : "JetBrains Mono"
                                        }
                                    }
                                }

                                MouseArea {
                                    anchors.fill: parent
                                    hoverEnabled: true
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: if (shellWindow) shellWindow.currentPage = 2
                                }
                            }
                        }

                        GridLayout {
                            Layout.fillWidth: true
                            columns: root.landingTelemetryColumns
                            columnSpacing: shellWindow ? shellWindow.compactGap : 8
                            rowSpacing: shellWindow ? shellWindow.compactGap : 8

                            Repeater {
                                model: root.landingTelemetryPreviewList
                                delegate: landingTelemetryReadoutDelegate
                            }
                        }

                        InsetPanel {
                            Layout.fillWidth: true
                            shellWindow: root.shellWindow
                            accentColor: shellWindow ? shellWindow.accentIce : "#86c7d4"
                            prominent: true

                            Text {
                                Layout.fillWidth: true
                                text: "STAGE LEDGER / 主墙摘记"
                                color: shellWindow ? shellWindow.accentIce : "#86c7d4"
                                font.pixelSize: shellWindow ? shellWindow.captionSize : 10
                                font.family: shellWindow ? shellWindow.monoFamily : "JetBrains Mono"
                                font.letterSpacing: shellWindow ? shellWindow.scaled(0.7) : 0.7
                            }

                            Text {
                                Layout.fillWidth: true
                                text: root.landingStageLedgerText
                                color: shellWindow ? shellWindow.textStrong : "#f5efe4"
                                font.pixelSize: shellWindow ? shellWindow.bodySize : 13
                                font.family: shellWindow ? shellWindow.uiFamily : "Noto Sans CJK SC"
                                wrapMode: Text.WordWrap
                                maximumLineCount: 4
                                elide: Text.ElideRight
                            }

                            Text {
                                Layout.fillWidth: true
                                text: root.landingStageLedgerSupport
                                color: shellWindow ? shellWindow.textSecondary : "#9aa8b1"
                                font.pixelSize: shellWindow ? shellWindow.captionSize + 1 : 11
                                font.family: shellWindow ? shellWindow.uiFamily : "Noto Sans CJK SC"
                                wrapMode: Text.WordWrap
                                maximumLineCount: 3
                                elide: Text.ElideRight
                            }

                            GridLayout {
                                Layout.fillWidth: true
                                columns: root.landingJumpColumns
                                columnSpacing: shellWindow ? shellWindow.compactGap : 8
                                rowSpacing: shellWindow ? shellWindow.compactGap : 8

                                Rectangle {
                                    Layout.fillWidth: true
                                    radius: shellWindow ? shellWindow.edgeRadius : 12
                                    color: shellWindow ? shellWindow.toneFill("online") : "#102033"
                                    border.color: shellWindow ? shellWindow.accentIce : "#86c7d4"
                                    border.width: 1
                                    implicitHeight: shellWindow ? shellWindow.scaled(38) : 38

                                    Text {
                                        anchors.centerIn: parent
                                        text: "飞行合同 / Flight"
                                        color: shellWindow ? shellWindow.textStrong : "#f5efe4"
                                        font.pixelSize: shellWindow ? shellWindow.captionSize + 1 : 11
                                        font.weight: Font.DemiBold
                                        font.family: shellWindow ? shellWindow.uiFamily : "Noto Sans CJK SC"
                                    }

                                    MouseArea {
                                        anchors.fill: parent
                                        hoverEnabled: true
                                        cursorShape: Qt.PointingHandCursor
                                        onClicked: if (shellWindow) shellWindow.currentPage = 2
                                    }
                                }

                                Rectangle {
                                    Layout.fillWidth: true
                                    radius: shellWindow ? shellWindow.edgeRadius : 12
                                    color: shellWindow ? shellWindow.toneFill("warning") : "#251f18"
                                    border.color: shellWindow ? shellWindow.accentGold : "#c6ab7d"
                                    border.width: 1
                                    implicitHeight: shellWindow ? shellWindow.scaled(38) : 38

                                    Text {
                                        anchors.centerIn: parent
                                        text: "执行坞站 / Dock"
                                        color: shellWindow ? shellWindow.textStrong : "#f5efe4"
                                        font.pixelSize: shellWindow ? shellWindow.captionSize + 1 : 11
                                        font.weight: Font.DemiBold
                                        font.family: shellWindow ? shellWindow.uiFamily : "Noto Sans CJK SC"
                                    }

                                    MouseArea {
                                        anchors.fill: parent
                                        hoverEnabled: true
                                        cursorShape: Qt.PointingHandCursor
                                        onClicked: if (shellWindow) shellWindow.currentPage = 4
                                    }
                                }
                            }
                        }
                    }

                    GridLayout {
                        Layout.fillWidth: true
                        columns: root.landingJumpColumns
                        columnSpacing: shellWindow ? shellWindow.zoneGap : 14
                        rowSpacing: shellWindow ? shellWindow.zoneGap : 14

                        ShellCard {
                            Layout.fillWidth: true
                            shellWindow: root.shellWindow
                            accentColor: shellWindow ? shellWindow.accentGold : "#c6ab7d"
                            eyebrow: "系统回注 / SYSTEM"
                            title: "会话、事件与快照"
                            subtitle: "继续呈现仓库快照、心跳、事件与事实边界。"

                            InsetPanel {
                                Layout.fillWidth: true
                                shellWindow: root.shellWindow
                                accentColor: shellWindow ? shellWindow.accentGold : "#c6ab7d"

                                ColumnLayout {
                                    id: stackedSystemBriefColumn
                                    Layout.fillWidth: true
                                    spacing: shellWindow ? shellWindow.scaled(3) : 3

                                    Text {
                                        text: "任务简报 / MISSION BRIEF"
                                        color: shellWindow ? shellWindow.accentGold : "#c6ab7d"
                                        font.pixelSize: shellWindow ? shellWindow.captionSize : 10
                                        font.family: shellWindow ? shellWindow.monoFamily : "JetBrains Mono"
                                        font.letterSpacing: shellWindow ? shellWindow.scaled(0.6) : 0.6
                                    }

                                    Text {
                                        Layout.fillWidth: true
                                        text: root.landingBriefText
                                        color: shellWindow ? shellWindow.textPrimary : "#d7dde2"
                                        font.pixelSize: shellWindow ? shellWindow.bodySize : 13
                                        font.family: shellWindow ? shellWindow.uiFamily : "Noto Sans CJK SC"
                                        wrapMode: Text.WordWrap
                                        maximumLineCount: 2
                                        elide: Text.ElideRight
                                    }
                                }
                            }

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
                                columns: 1
                                rowSpacing: shellWindow ? shellWindow.compactGap : 8

                                Repeater {
                                    model: root.landingStatusList

                                    delegate: MetricTile {
                                        shellWindow: root.shellWindow
                                        Layout.fillWidth: true
                                        label: String(modelData["label"] || "--")
                                        value: String(modelData["value"] || "--")
                                        detail: shellWindow ? shellWindow.snapshotRelativePath : "--"
                                        tone: String(modelData["tone"] || "neutral")
                                    }
                                }
                            }
                        }

                        ShellCard {
                            Layout.fillWidth: true
                            shellWindow: root.shellWindow
                            accentColor: shellWindow ? shellWindow.accentMint : "#93bea5"
                            eyebrow: "弱网摘要 / WEAK-LINK"
                            title: root.recommendedScenarioLabel
                            subtitle: "在线锚点 " + root.anchorValue + "  ·  " + root.anchorStatus

                            InsetPanel {
                                Layout.fillWidth: true
                                shellWindow: root.shellWindow
                                accentColor: shellWindow ? shellWindow.accentMint : "#93bea5"

                                ColumnLayout {
                                    id: stackedWeakBriefColumn
                                    Layout.fillWidth: true
                                    spacing: shellWindow ? shellWindow.scaled(3) : 3

                                    Text {
                                        text: "推荐剧本 / RECOMMENDED"
                                        color: shellWindow ? shellWindow.accentMint : "#93bea5"
                                        font.pixelSize: shellWindow ? shellWindow.captionSize : 10
                                        font.family: shellWindow ? shellWindow.monoFamily : "JetBrains Mono"
                                        font.letterSpacing: shellWindow ? shellWindow.scaled(0.6) : 0.6
                                    }

                                    Text {
                                        Layout.fillWidth: true
                                        text: root.recommendedScenarioBrief
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
                                        model: root.landingWeakMetricList
                                        delegate: landingTelemetryReadoutDelegate
                                    }
                                }

                                ColumnLayout {
                                    Layout.fillWidth: true
                                    visible: root.landingScenarioList.length > 0 && !root.landingShortHeight
                                    spacing: shellWindow ? shellWindow.compactGap : 8

                                    Repeater {
                                        model: root.landingScenarioList
                                        delegate: landingScenarioPreviewDelegate
                                    }
                                }
                        }
                    }

                    ShellCard {
                        Layout.fillWidth: true
                        shellWindow: root.shellWindow
                        accentColor: shellWindow ? shellWindow.accentGold : "#c6ab7d"
                        eyebrow: "页面直达 / JUMP RAIL"
                        title: "页面入口与轻量跳转"
                        subtitle: "系统、飞行、弱网和执行页保持明确入口，但不再压过地图主位。"

                        GridLayout {
                            Layout.fillWidth: true
                            columns: root.landingJumpColumns
                            columnSpacing: shellWindow ? shellWindow.compactGap : 8
                            rowSpacing: shellWindow ? shellWindow.compactGap : 8

                            Repeater {
                                model: root.landingJumpList
                                delegate: landingJumpCardDelegate
                            }
                        }
                    }

                    ShellCard {
                        Layout.fillWidth: true
                        shellWindow: root.shellWindow
                        accentColor: shellWindow ? shellWindow.accentGold : "#c6ab7d"
                        eyebrow: "执行坞站 / ACTION DOCK"
                        title: "轻量动作预览与启动入口"
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
                            columns: root.landingActionColumns
                            columnSpacing: shellWindow ? shellWindow.compactGap : 8
                            rowSpacing: shellWindow ? shellWindow.compactGap : 8

                            Repeater {
                                model: root.actionPreviewList
                                delegate: landingActionPreviewDelegate
                            }
                        }

                        InsetPanel {
                            Layout.fillWidth: true
                            shellWindow: root.shellWindow
                            accentColor: shellWindow ? shellWindow.accentIce : "#86c7d4"

                            ColumnLayout {
                                id: stackedLaunchColumn
                                Layout.fillWidth: true
                                spacing: shellWindow ? shellWindow.compactGap : 8

                                Text {
                                    Layout.fillWidth: true
                                    text: "LAUNCH / 安全启动"
                                    color: shellWindow ? shellWindow.accentIce : "#86c7d4"
                                    font.pixelSize: shellWindow ? shellWindow.captionSize : 10
                                    font.family: shellWindow ? shellWindow.monoFamily : "JetBrains Mono"
                                    font.letterSpacing: shellWindow ? shellWindow.scaled(0.7) : 0.7
                                }

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
                                    text: root.anchorProbeBrief
                                    color: shellWindow ? shellWindow.textSecondary : "#9aa8b1"
                                    font.pixelSize: shellWindow ? shellWindow.captionSize + 1 : 11
                                    font.family: shellWindow ? shellWindow.uiFamily : "Noto Sans CJK SC"
                                    wrapMode: Text.WordWrap
                                    maximumLineCount: 2
                                    elide: Text.ElideRight
                                }

                                Rectangle {
                                    Layout.alignment: Qt.AlignRight
                                    radius: shellWindow ? shellWindow.edgeRadius + shellWindow.scaled(1) : 13
                                    color: "#da09131f"
                                    border.color: shellWindow ? shellWindow.accentGold : "#c6ab7d"
                                    border.width: 1
                                    implicitWidth: stackedDockCtaColumn.implicitWidth + ((shellWindow ? shellWindow.scaled(12) : 12) * 2)
                                    implicitHeight: stackedDockCtaColumn.implicitHeight + ((shellWindow ? shellWindow.scaled(7) : 7) * 2)

                                    Column {
                                        id: stackedDockCtaColumn
                                        anchors.centerIn: parent
                                        spacing: shellWindow ? shellWindow.scaled(1) : 1

                                        Text {
                                            text: "直达"
                                            color: shellWindow ? shellWindow.accentGold : "#c6ab7d"
                                            font.pixelSize: shellWindow ? shellWindow.captionSize : 10
                                            font.family: shellWindow ? shellWindow.monoFamily : "JetBrains Mono"
                                            horizontalAlignment: Text.AlignHCenter
                                        }

                                        Row {
                                            spacing: shellWindow ? shellWindow.compactGap : 8

                                            Text {
                                                text: root.dockCtaLabel
                                                color: shellWindow ? shellWindow.textStrong : "#f5efe4"
                                                font.pixelSize: shellWindow ? shellWindow.bodySize : 13
                                                font.weight: Font.DemiBold
                                                font.family: shellWindow ? shellWindow.uiFamily : "Noto Sans CJK SC"
                                            }

                                            Text {
                                                text: ">"
                                                color: shellWindow ? shellWindow.accentGold : "#c6ab7d"
                                                font.pixelSize: shellWindow ? shellWindow.bodyEmphasisSize : 14
                                                font.weight: Font.DemiBold
                                                font.family: shellWindow ? shellWindow.monoFamily : "JetBrains Mono"
                                            }
                                        }
                                    }

                                    MouseArea {
                                        anchors.fill: parent
                                        hoverEnabled: true
                                        cursorShape: Qt.PointingHandCursor
                                        onClicked: if (shellWindow) shellWindow.currentPage = 4
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
