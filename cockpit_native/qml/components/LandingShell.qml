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
    readonly property int railWidth: shellWindow ? shellWindow.scaled(landingWide ? 308 : 296) : 308
    readonly property var landingStatusList: shellWindow ? shellWindow.previewItems(statusRows, landingWide ? 4 : 3) : []
    readonly property var landingScenarioList: shellWindow ? shellWindow.previewItems(scenarioList, landingWide ? 3 : 2) : []
    readonly property var timingPreviewList: shellWindow ? shellWindow.previewItems(stageTimingList, shellWindow.compactLayout ? 3 : 4) : []
    readonly property var evidencePreviewList: shellWindow ? shellWindow.previewItems(evidenceList, 4) : []
    readonly property var scenarioDeckList: shellWindow ? shellWindow.previewItems(scenarioList, shellWindow.wideLayout ? 4 : 3) : []
    readonly property var landingJumpList: shellWindow ? DataUtils.arrayOrEmpty(shellWindow.landingJumpModel) : []
    readonly property var landingWeakMetricList: shellWindow ? DataUtils.arrayOrEmpty(shellWindow.landingWeakMetricModel) : []
    readonly property var actionPreviewList: shellWindow ? shellWindow.previewItems(actionList, landingWide ? 3 : 2) : []

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
            Layout.fillWidth: true
            radius: shellWindow ? shellWindow.edgeRadius : 12
            color: shellWindow ? shellWindow.surfaceQuiet : "#0f161d"
            border.color: shellWindow ? shellWindow.toneColor(root.jumpTone(jumpData)) : "#86c7d4"
            border.width: 1
            implicitHeight: jumpColumn.implicitHeight + ((shellWindow ? shellWindow.scaled(10) : 10) * 2)

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
                }

                Text {
                    Layout.fillWidth: true
                    text: String(jumpData["value"] || "--") + "  ·  进入 >"
                    color: shellWindow ? shellWindow.toneColor(root.jumpTone(jumpData)) : "#86c7d4"
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

        MetricTile {
            shellWindow: root.shellWindow
            Layout.fillWidth: true
            label: String(modelData["label"] || "--")
            value: !!modelData["enabled"] ? "可执行" : "只读"
            detail: compact(modelData["note"] || "保持合同镜像", 72)
            tone: root.actionTone(modelData)
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

                    GridLayout {
                        anchors.fill: parent
                        columns: shellWindow && shellWindow.wideLayout ? 2 : 1
                        columnSpacing: shellWindow ? shellWindow.zoneGap : 14
                        rowSpacing: shellWindow ? shellWindow.zoneGap : 14

                        ShellCard {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            shellWindow: root.shellWindow
                            accentColor: shellWindow ? shellWindow.accentIce : "#86c7d4"
                            eyebrow: "FLIGHT STAGE / 飞行合同"
                            title: shellWindow ? shellWindow.missionCallSignValue + " · " + shellWindow.aircraftIdValue : "飞行合同"
                            subtitle: shellWindow ? shellWindow.activeSourceLabel : ""

                            Item {
                                Layout.fillWidth: true
                                Layout.fillHeight: true
                                implicitHeight: shellWindow ? shellWindow.scaled(shellWindow.compactLayout ? 300 : 420) : 420

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

                        ColumnLayout {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            spacing: shellWindow ? shellWindow.zoneGap : 14

                            ShellCard {
                                Layout.fillWidth: true
                                shellWindow: root.shellWindow
                                accentColor: shellWindow ? shellWindow.accentGold : "#c6ab7d"
                                eyebrow: "TELEMETRY / 遥测摘要"
                                title: "高度、航向、定位与采样"
                                subtitle: "Flight contract 继续从仓库合同对象回填。"

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
                                Layout.fillHeight: true
                                shellWindow: root.shellWindow
                                accentColor: shellWindow ? shellWindow.accentMint : "#93bea5"
                                eyebrow: "CONTRACT / 数据合同"
                                title: "来源状态、接口与回退说明"
                                subtitle: "保留中国语义优先的合同描述，同时直连 repo 字段。"

                                GridLayout {
                                    Layout.fillWidth: true
                                    columns: 1
                                    rowSpacing: shellWindow ? shellWindow.compactGap : 8

                                    Repeater {
                                        model: [
                                            {
                                                "label": "源状态",
                                                "value": String(root.centerPanel["source_status"] || "--"),
                                                "detail": String(feedContract["active_source_kind"] || "--"),
                                                "tone": "online"
                                            },
                                            {
                                                "label": "接口",
                                                "value": String(root.centerPanel["source_api_path"] || "--"),
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
                                                "value": compact(root.centerPanel["fallback_note"] || "--", 54),
                                                "detail": String(root.centerPanel["ownership_note"] || "--"),
                                                "tone": "warning"
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
        id: landingWideComponent

        Item {
            anchors.fill: parent

            ColumnLayout {
                anchors.fill: parent
                spacing: shellWindow ? shellWindow.zoneGap : 14

                RowLayout {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    spacing: shellWindow ? shellWindow.zoneGap : 14

                    ColumnLayout {
                        Layout.preferredWidth: root.railWidth
                        Layout.fillHeight: true
                        spacing: shellWindow ? shellWindow.zoneGap : 14

                        ShellCard {
                            Layout.fillHeight: true
                            Layout.fillWidth: true
                            shellWindow: root.shellWindow
                            accentColor: shellWindow ? shellWindow.accentGold : "#c6ab7d"
                            eyebrow: "SYSTEM RAIL / 系统回注"
                            title: "板态摘要与事实边界"
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
                            eyebrow: "BOUNDARY / 事实边界"
                            title: "仓库路径与软件安全"
                            subtitle: shellWindow ? shellWindow.truthNoteValue : "继续直接读取仓库合同。"

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
                        Layout.fillHeight: true
                        shellWindow: root.shellWindow
                        accentColor: shellWindow ? shellWindow.accentIce : "#86c7d4"
                        eyebrow: "GLOBAL STAGE / 总览主屏"
                        title: shellWindow ? shellWindow.landingSummaryTitle : "地图优先的原生命令壳"
                        subtitle: shellWindow ? shellWindow.landingSummaryText : ""

                        Item {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            implicitHeight: shellWindow ? shellWindow.scaled(420) : 420

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
                                bannerEyebrow: "GLOBAL COMMAND STAGE"
                                bannerTitle: shellWindow ? shellWindow.landingMapBannerTitle : ""
                                bannerText: shellWindow ? shellWindow.landingMapBannerText : ""
                                bannerChips: shellWindow ? shellWindow.landingStageChipModel : []
                            }

                            Rectangle {
                                anchors.right: parent.right
                                anchors.bottom: parent.bottom
                                anchors.margins: shellWindow ? shellWindow.scaled(14) : 14
                                radius: shellWindow ? shellWindow.edgeRadius : 12
                                color: "#de09131f"
                                border.color: shellWindow ? shellWindow.accentIce : "#86c7d4"
                                border.width: 1
                                implicitWidth: mapCtaRow.implicitWidth + ((shellWindow ? shellWindow.scaled(14) : 14) * 2)
                                implicitHeight: mapCtaRow.implicitHeight + ((shellWindow ? shellWindow.scaled(8) : 8) * 2)

                                Row {
                                    id: mapCtaRow
                                    anchors.centerIn: parent
                                    spacing: shellWindow ? shellWindow.compactGap : 8

                                    Text {
                                        text: "进入飞行合同"
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
                            columns: 4
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

                    ColumnLayout {
                        Layout.preferredWidth: root.railWidth
                        Layout.fillHeight: true
                        spacing: shellWindow ? shellWindow.zoneGap : 14

                        ShellCard {
                            Layout.fillHeight: true
                            Layout.fillWidth: true
                            shellWindow: root.shellWindow
                            accentColor: shellWindow ? shellWindow.accentGold : "#c6ab7d"
                            eyebrow: "JUMP RAIL / 显式跳转"
                            title: "页面跳转与任务入口"
                            subtitle: "首屏保持地图居中，系统、飞行、弱网与执行页都能直接进入。"

                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: shellWindow ? shellWindow.compactGap : 8

                                Repeater {
                                    model: root.landingJumpList
                                    delegate: landingJumpCardDelegate
                                }
                            }
                        }

                        ShellCard {
                            Layout.fillWidth: true
                            shellWindow: root.shellWindow
                            accentColor: shellWindow ? shellWindow.accentMint : "#93bea5"
                            eyebrow: "WEAK-LINK / 弱网摘要"
                            title: root.recommendedScenarioLabel
                            subtitle: root.anchorStatus

                            GridLayout {
                                Layout.fillWidth: true
                                columns: 1
                                rowSpacing: shellWindow ? shellWindow.compactGap : 8

                                Repeater {
                                    model: root.landingWeakMetricList

                                    delegate: MetricTile {
                                        readonly property var metricData: DataUtils.objectOrEmpty(modelData)
                                        shellWindow: root.shellWindow
                                        Layout.fillWidth: true
                                        label: String(metricData["label"] || "--")
                                        value: String(metricData["value"] || "--")
                                        detail: String(metricData["detail"] || "")
                                        tone: String(metricData["tone"] || "neutral")
                                    }
                                }
                            }
                        }
                    }
                }

                ShellCard {
                    Layout.fillWidth: true
                    shellWindow: root.shellWindow
                    accentColor: shellWindow ? shellWindow.accentGold : "#c6ab7d"
                    eyebrow: "ACTION DOCK / 执行预览"
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
                        columns: 3
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

                        Rectangle {
                            Layout.fillWidth: true
                            radius: shellWindow ? shellWindow.edgeRadius : 12
                            color: shellWindow ? shellWindow.surfaceQuiet : "#0f161d"
                            border.color: shellWindow ? shellWindow.borderSubtle : "#2a3944"
                            border.width: 1
                            implicitHeight: launchHintText.implicitHeight + ((shellWindow ? shellWindow.scaled(8) : 8) * 2)

                            Text {
                                id: launchHintText
                                anchors.left: parent.left
                                anchors.right: parent.right
                                anchors.verticalCenter: parent.verticalCenter
                                anchors.leftMargin: shellWindow ? shellWindow.scaled(10) : 10
                                anchors.rightMargin: shellWindow ? shellWindow.scaled(10) : 10
                                text: shellWindow ? shellWindow.launchHint : "--"
                                color: shellWindow ? shellWindow.textPrimary : "#d7dde2"
                                font.pixelSize: shellWindow ? shellWindow.captionSize + 1 : 11
                                font.family: shellWindow ? shellWindow.monoFamily : "JetBrains Mono"
                                elide: Text.ElideMiddle
                            }
                        }

                        Rectangle {
                            radius: shellWindow ? shellWindow.edgeRadius : 12
                            color: "#de09131f"
                            border.color: shellWindow ? shellWindow.accentGold : "#c6ab7d"
                            border.width: 1
                            implicitWidth: dockCtaRow.implicitWidth + ((shellWindow ? shellWindow.scaled(14) : 14) * 2)
                            implicitHeight: dockCtaRow.implicitHeight + ((shellWindow ? shellWindow.scaled(9) : 9) * 2)

                            Row {
                                id: dockCtaRow
                                anchors.centerIn: parent
                                spacing: shellWindow ? shellWindow.compactGap : 8

                                Text {
                                    text: "进入执行坞站"
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

    Component {
        id: landingStackedComponent

        Item {
            anchors.fill: parent

            ColumnLayout {
                anchors.fill: parent
                spacing: shellWindow ? shellWindow.zoneGap : 14

                ShellCard {
                    Layout.fillWidth: true
                    shellWindow: root.shellWindow
                    accentColor: shellWindow ? shellWindow.accentIce : "#86c7d4"
                    eyebrow: "GLOBAL STAGE / 总览主屏"
                    title: shellWindow ? shellWindow.landingSummaryTitle : "地图优先的原生命令壳"
                    subtitle: shellWindow ? shellWindow.landingSummaryText : ""

                    Item {
                        Layout.fillWidth: true
                        implicitHeight: shellWindow ? shellWindow.scaled(340) : 340

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
                            bannerEyebrow: "GLOBAL COMMAND STAGE"
                            bannerTitle: shellWindow ? shellWindow.landingMapBannerTitle : ""
                            bannerText: shellWindow ? shellWindow.landingMapBannerText : ""
                            bannerChips: shellWindow ? shellWindow.landingStageChipModel : []
                        }

                        Rectangle {
                            anchors.right: parent.right
                            anchors.bottom: parent.bottom
                            anchors.margins: shellWindow ? shellWindow.scaled(12) : 12
                            radius: shellWindow ? shellWindow.edgeRadius : 12
                            color: "#de09131f"
                            border.color: shellWindow ? shellWindow.accentIce : "#86c7d4"
                            border.width: 1
                            implicitWidth: stackedMapCtaRow.implicitWidth + ((shellWindow ? shellWindow.scaled(14) : 14) * 2)
                            implicitHeight: stackedMapCtaRow.implicitHeight + ((shellWindow ? shellWindow.scaled(8) : 8) * 2)

                            Row {
                                id: stackedMapCtaRow
                                anchors.centerIn: parent
                                spacing: shellWindow ? shellWindow.compactGap : 8

                                Text {
                                    text: "进入飞行合同"
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
                        columns: 2
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
                    accentColor: shellWindow ? shellWindow.accentGold : "#c6ab7d"
                    eyebrow: "JUMP RAIL / 显式跳转"
                    title: "页面入口与轻量跳转"
                    subtitle: "系统、飞行、弱网和执行页都保留明确入口。"

                    GridLayout {
                        Layout.fillWidth: true
                        columns: shellWindow && shellWindow.mediumLayout ? 2 : 1
                        columnSpacing: shellWindow ? shellWindow.compactGap : 8
                        rowSpacing: shellWindow ? shellWindow.compactGap : 8

                        Repeater {
                            model: root.landingJumpList
                            delegate: landingJumpCardDelegate
                        }
                    }
                }

                GridLayout {
                    Layout.fillWidth: true
                    columns: shellWindow && shellWindow.mediumLayout ? 2 : 1
                    columnSpacing: shellWindow ? shellWindow.zoneGap : 14
                    rowSpacing: shellWindow ? shellWindow.zoneGap : 14

                    ShellCard {
                        Layout.fillWidth: true
                        shellWindow: root.shellWindow
                        accentColor: shellWindow ? shellWindow.accentGold : "#c6ab7d"
                        eyebrow: "SYSTEM / 板态"
                        title: "会话、事件与快照"
                        subtitle: shellWindow ? shellWindow.truthNoteValue : ""

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
                        eyebrow: "WEAK-LINK / 弱网摘要"
                        title: root.recommendedScenarioLabel
                        subtitle: root.anchorStatus

                        GridLayout {
                            Layout.fillWidth: true
                            columns: 1
                            rowSpacing: shellWindow ? shellWindow.compactGap : 8

                            Repeater {
                                model: root.landingWeakMetricList

                                delegate: MetricTile {
                                    shellWindow: root.shellWindow
                                    Layout.fillWidth: true
                                    label: String(modelData["label"] || "--")
                                    value: String(modelData["value"] || "--")
                                    detail: String(modelData["detail"] || "")
                                    tone: String(modelData["tone"] || "neutral")
                                }
                            }
                        }
                    }
                }

                ShellCard {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    shellWindow: root.shellWindow
                    accentColor: shellWindow ? shellWindow.accentGold : "#c6ab7d"
                    eyebrow: "ACTION DOCK / 执行预览"
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
                        columns: 1
                        rowSpacing: shellWindow ? shellWindow.compactGap : 8

                        Repeater {
                            model: root.actionPreviewList
                            delegate: landingActionPreviewDelegate
                        }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        radius: shellWindow ? shellWindow.edgeRadius : 12
                        color: shellWindow ? shellWindow.surfaceQuiet : "#0f161d"
                        border.color: shellWindow ? shellWindow.borderSubtle : "#2a3944"
                        border.width: 1
                        implicitHeight: stackedLaunchColumn.implicitHeight + ((shellWindow ? shellWindow.cardPadding : 14) * 2)

                        ColumnLayout {
                            id: stackedLaunchColumn
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

                            Rectangle {
                                Layout.alignment: Qt.AlignRight
                                radius: shellWindow ? shellWindow.edgeRadius : 12
                                color: "#de09131f"
                                border.color: shellWindow ? shellWindow.accentGold : "#c6ab7d"
                                border.width: 1
                                implicitWidth: stackedDockCtaRow.implicitWidth + ((shellWindow ? shellWindow.scaled(14) : 14) * 2)
                                implicitHeight: stackedDockCtaRow.implicitHeight + ((shellWindow ? shellWindow.scaled(9) : 9) * 2)

                                Row {
                                    id: stackedDockCtaRow
                                    anchors.centerIn: parent
                                    spacing: shellWindow ? shellWindow.compactGap : 8

                                    Text {
                                        text: "进入执行坞站"
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
