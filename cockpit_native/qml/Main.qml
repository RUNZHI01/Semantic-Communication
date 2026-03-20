import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import QtQuick.Window 2.15
import "components"
import "components/DataUtils.js" as DataUtils

ApplicationWindow {
    id: root
    readonly property var bridge: (typeof cockpitBridge !== "undefined" && cockpitBridge) ? cockpitBridge : null
    readonly property var uiState: DataUtils.objectOrEmpty(bridge ? bridge.state : null)
    readonly property var zones: DataUtils.objectOrEmpty(uiState["zones"])
    readonly property var metrics: DataUtils.objectOrEmpty((typeof screenMetrics !== "undefined") ? screenMetrics : null)
    readonly property var insets: DataUtils.objectOrEmpty((typeof safeAreaInsets !== "undefined") ? safeAreaInsets : null)
    readonly property var options: DataUtils.objectOrEmpty((typeof launchOptions !== "undefined") ? launchOptions : null)

    readonly property var leftPanelData: DataUtils.objectOrEmpty(zones["left_status_panel"])
    readonly property var centerPanelData: DataUtils.objectOrEmpty(zones["center_tactical_view"])
    readonly property var rightPanelData: DataUtils.objectOrEmpty(zones["right_weak_network_panel"])
    readonly property var bottomPanelData: DataUtils.objectOrEmpty(zones["bottom_action_strip"])
    readonly property var meta: DataUtils.objectOrEmpty(uiState["meta"])
    readonly property var statusRows: DataUtils.arrayOrEmpty(leftPanelData["rows"])
    readonly property var centerControlSummary: DataUtils.objectOrEmpty(centerPanelData["control_summary"])
    readonly property var centerFeedContract: DataUtils.objectOrEmpty(centerPanelData["feed_contract"])
    readonly property var centerSampleData: DataUtils.objectOrEmpty(centerPanelData["sample"])
    readonly property bool softwareRenderEnabled: !!options["softwareRender"]

    readonly property int designWidth: 1440
    readonly property int designHeight: 900

    readonly property string displayFamily: "Noto Sans CJK SC"
    readonly property string uiFamily: "Noto Sans CJK SC"
    readonly property string monoFamily: "JetBrains Mono"

    readonly property color bgColorDeep: "#020710"
    readonly property color bgColorMid: "#071629"
    readonly property color bgColorLight: "#0f3359"
    readonly property color bgColorHaze: "#173f67"
    readonly property color shellColor: "#07101d"
    readonly property color shellColorRaised: "#0b1727"
    readonly property color shellColorInset: "#071522"
    readonly property color shellColorGlass: "#0d2031"
    readonly property color panelColor: "#0a1523"
    readonly property color panelColorRaised: "#102239"
    readonly property color panelColorSoft: "#0c1a2b"
    readonly property color cardColor: "#112743"
    readonly property color cardColorSoft: "#0c1829"
    readonly property color borderSoft: "#214666"
    readonly property color borderStrong: "#5ac7ff"
    readonly property color accentBlue: "#4ebcff"
    readonly property color accentBlueSoft: "#2f86be"
    readonly property color accentCyan: "#9ff1ff"
    readonly property color accentGreen: "#42f0bc"
    readonly property color accentAmber: "#ffbf52"
    readonly property color accentRed: "#ff7b7b"
    readonly property color textStrong: "#f6fbff"
    readonly property color textPrimary: "#d7efff"
    readonly property color textSecondary: "#8db2cc"
    readonly property color textMuted: "#5a778e"
    readonly property color textTertiary: "#4b667d"
    readonly property color gridLine: "#132b42"
    readonly property color gridLineStrong: "#24567d"
    readonly property color shellStageTop: "#153f67"
    readonly property color shellStageMid: "#0a1d31"
    readonly property color shellStageBottom: "#05101a"
    readonly property color shellDockTop: "#112c47"
    readonly property color shellDockMid: "#0a1828"
    readonly property color shellDockBottom: "#06101a"
    readonly property color panelGlowStrong: "#6fdcff"
    readonly property color panelTraceStrong: "#1f5b86"
    readonly property color panelTrace: "#143754"
    readonly property color panelTraceSoft: "#0d2940"

    readonly property real widthScale: Math.max(0.78, Math.min(1.18, Number(metrics["width"] || designWidth) / designWidth))
    readonly property real heightScale: Math.max(0.78, Math.min(1.18, Number(metrics["height"] || designHeight) / designHeight))
    readonly property real uiScale: Math.min(widthScale, heightScale)

    readonly property int safeLeft: Number(insets["left"] || 0)
    readonly property int safeTop: Number(insets["top"] || 0)
    readonly property int safeRight: Number(insets["right"] || 0)
    readonly property int safeBottom: Number(insets["bottom"] || 0)

    readonly property int outerPadding: scaled(20)
    readonly property int shellPadding: scaled(26)
    readonly property int zoneGap: scaled(18)
    readonly property int compactGap: scaled(10)
    readonly property int panelPadding: scaled(18)
    readonly property int cardPadding: scaled(16)
    readonly property int panelRadius: scaled(24)
    readonly property int cardRadius: scaled(16)
    readonly property int edgeRadius: scaled(12)
    readonly property int headerTitleSize: scaled(36)
    readonly property int sectionTitleSize: scaled(24)
    readonly property int bodyEmphasisSize: scaled(14)
    readonly property int bodySize: scaled(13)
    readonly property int captionSize: scaled(10)
    readonly property int eyebrowSize: scaled(10)
    readonly property int headerPad: scaled(wideLayout ? 18 : 24)
    readonly property int headerChipWidth: scaled(wideLayout ? 142 : 154)
    readonly property int headerMirrorWidth: scaled(wideLayout ? 448 : 0)

    readonly property real contentWidth: Math.max(1, width - safeLeft - safeRight - (outerPadding * 2))
    readonly property bool wideLayout: contentWidth >= scaled(1380)
    readonly property bool mediumLayout: !wideLayout && contentWidth >= scaled(980)
    readonly property bool compactLayout: !wideLayout && !mediumLayout
    readonly property bool splitHeaderLayout: !compactLayout && contentWidth >= scaled(1500)
    readonly property int dashboardColumns: wideLayout ? 16 : (mediumLayout ? 2 : 1)
    readonly property int wideLeftSpan: 3
    readonly property int wideCenterSpan: 10
    readonly property int wideRightSpan: 3

    readonly property string topTitle: primaryLabel(meta["title"] || "飞腾原生座舱 / Feiteng Native Cockpit")
    readonly property string topSubtitle: secondaryLabel(meta["title"] || "飞腾原生座舱 / Feiteng Native Cockpit")
    readonly property var liveAnchor: DataUtils.objectOrEmpty(rightPanelData["live_anchor"])
    readonly property string recommendedScenarioId: String(rightPanelData["recommended_scenario_id"] || "--")

    readonly property var headerChipModel: [
        {
            "label": "会话",
            "value": String((statusRow("会话") || {})["value"] || "--"),
            "tone": String((statusRow("会话") || {})["tone"] || "online")
        },
        {
            "label": "事件",
            "value": String((statusRow("最近事件") || {})["value"] || "--"),
            "tone": String((statusRow("最近事件") || {})["tone"] || "online")
        },
        {
            "label": "链路",
            "value": String(centerControlSummary["link_profile"] || "--"),
            "tone": "neutral"
        },
        {
            "label": "锚点",
            "value": String(liveAnchor["valid_instance"] || "--"),
            "tone": String(liveAnchor["tone"] || "online")
        },
        {
            "label": "渲染",
            "value": softwareRenderEnabled ? "软件回退" : "图形加速",
            "tone": softwareRenderEnabled ? "warning" : "online"
        }
    ]
    readonly property var headerMirrorModel: [
        {
            "label": "采样时钟",
            "value": String(centerSampleData["captured_at"] || "--"),
            "tone": "neutral"
        },
        {
            "label": "链路档位",
            "value": String(centerControlSummary["link_profile"] || "--"),
            "tone": "warning"
        },
        {
            "label": "弱网策略",
            "value": recommendedScenarioId,
            "tone": "warning"
        },
        {
            "label": "板端锚点",
            "value": String(liveAnchor["board_status"] || "--"),
            "tone": String(liveAnchor["tone"] || "neutral")
        }
    ]
    readonly property var shellFooterModel: [
        {
            "label": "会话",
            "value": String((statusRow("会话") || {})["value"] || "--"),
            "detail": "当前证据会话",
            "tone": "neutral"
        },
        {
            "label": "布局策略",
            "value": String(meta["layout_strategy"] || "--"),
            "detail": "自适应壳体布局",
            "tone": "neutral"
        },
        {
            "label": "主舞台",
            "value": String(centerPanelData["mission_call_sign"] || "--"),
            "detail": String(centerControlSummary["link_profile"] || "global wallboard"),
            "tone": String(liveAnchor["tone"] || "neutral")
        },
        {
            "label": "数据源",
            "value": String(centerFeedContract["active_source_label"] || centerPanelData["source_label"] || "--"),
            "detail": String(centerControlSummary["link_profile"] || "--"),
            "tone": "neutral"
        },
        {
            "label": "弱网策略",
            "value": recommendedScenarioId,
            "detail": String((statusRow("快照原因") || {})["value"] || "archive mirror"),
            "tone": "warning"
        },
        {
            "label": "渲染路径",
            "value": softwareRenderEnabled ? "软件回退" : "图形加速",
            "detail": softwareRenderEnabled ? "software-safe launch" : "gpu primary launch",
            "tone": softwareRenderEnabled ? "warning" : "online"
        }
    ]

    minimumWidth: 920
    minimumHeight: 680
    visible: true
    color: bgColorDeep
    title: meta["title"] || "飞腾原生座舱"

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

    function toneColor(tone) {
        if (tone === "online")
            return accentGreen
        if (tone === "warning")
            return accentAmber
        if (tone === "danger")
            return accentRed
        return accentBlue
    }

    function toneFill(tone) {
        if (tone === "online")
            return "#0d2c29"
        if (tone === "warning")
            return "#302311"
        if (tone === "danger")
            return "#321518"
        return "#0d2234"
    }

    Component.onCompleted: {
        var availableWidth = Math.max(minimumWidth, Number(metrics["width"] || designWidth))
        var availableHeight = Math.max(minimumHeight, Number(metrics["height"] || designHeight))
        width = Math.max(minimumWidth, Math.min(Math.round(availableWidth * 0.95), scaled(1820)))
        height = Math.max(minimumHeight, Math.min(Math.round(availableHeight * 0.92), scaled(1060)))
    }

    Rectangle {
        anchors.fill: parent
        color: root.bgColorDeep
    }

    Rectangle {
        width: root.scaled(620)
        height: width
        radius: width / 2
        color: "#14487b"
        opacity: 0.16
        x: root.width - (width * 0.56)
        y: -height * 0.34
    }

    Rectangle {
        width: root.scaled(520)
        height: width
        radius: width / 2
        color: "#0c2b50"
        opacity: 0.2
        x: -width * 0.28
        y: root.height - (height * 0.72)
    }

    Rectangle {
        width: root.width * 1.18
        height: root.scaled(240)
        rotation: -8
        color: root.bgColorHaze
        opacity: 0.08
        x: -root.width * 0.06
        y: root.height * 0.16
    }

    Rectangle {
        anchors.fill: parent
        gradient: Gradient {
            GradientStop { position: 0.0; color: root.bgColorLight }
            GradientStop { position: 0.38; color: root.bgColorMid }
            GradientStop { position: 1.0; color: root.bgColorDeep }
        }
        opacity: 0.78
    }

    Item {
        id: backdropGrid
        anchors.fill: parent
        opacity: 0.36

        Repeater {
            model: 14

            delegate: Rectangle {
                width: backdropGrid.width
                height: 1
                color: index % 4 === 0 ? root.gridLineStrong : root.gridLine
                y: index * (backdropGrid.height / 13)
            }
        }

        Repeater {
            model: 18

            delegate: Rectangle {
                width: 1
                height: backdropGrid.height
                color: index % 5 === 0 ? root.gridLineStrong : root.gridLine
                x: index * (backdropGrid.width / 17)
            }
        }
    }

    Item {
        id: shellSurface
        anchors.fill: parent
        anchors.leftMargin: root.outerPadding
        anchors.topMargin: root.outerPadding
        anchors.rightMargin: root.outerPadding
        anchors.bottomMargin: root.outerPadding

        Rectangle {
            anchors.fill: parent
            radius: root.panelRadius + root.scaled(4)
            color: "#0f3557"
            opacity: 0.14
        }

        Rectangle {
            anchors.fill: parent
            radius: root.panelRadius
            gradient: Gradient {
                GradientStop { position: 0.0; color: root.shellColorRaised }
                GradientStop { position: 0.24; color: root.shellColorGlass }
                GradientStop { position: 0.48; color: root.shellColorInset }
                GradientStop { position: 0.68; color: root.shellColor }
                GradientStop { position: 1.0; color: "#040b16" }
            }
            border.color: "#2c77aa"
            border.width: 1
        }

        Rectangle {
            anchors.fill: parent
            radius: root.panelRadius
            gradient: Gradient {
                GradientStop { position: 0.0; color: "#1f5a8600" }
                GradientStop { position: 0.16; color: "#184a7022" }
                GradientStop { position: 0.48; color: "transparent" }
                GradientStop { position: 1.0; color: "#02060c88" }
            }
            opacity: 0.88
        }

        Rectangle {
            anchors.fill: parent
            anchors.margins: 1
            radius: root.panelRadius - 1
            color: "transparent"
            border.color: "#0c2640"
            border.width: 1
            opacity: 0.9
        }

        Rectangle {
            anchors.fill: parent
            anchors.margins: root.scaled(12)
            radius: root.panelRadius - root.scaled(12)
            color: "transparent"
            border.color: "#102d47"
            border.width: 1
            opacity: 0.54
        }

        Rectangle {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            height: root.scaled(3)
            gradient: Gradient {
                GradientStop { position: 0.0; color: "transparent" }
                GradientStop { position: 0.22; color: root.accentBlue }
                GradientStop { position: 0.75; color: root.accentCyan }
                GradientStop { position: 1.0; color: "transparent" }
            }
            opacity: 0.68
        }

        Rectangle {
            id: leftRailBerth
            visible: root.wideLayout
            anchors.left: parent.left
            anchors.top: parent.top
            anchors.bottom: parent.bottom
            anchors.margins: root.scaled(20)
            width: Math.max(root.scaled(212), parent.width * 0.17)
            radius: root.cardRadius
            gradient: Gradient {
                orientation: Gradient.Horizontal
                GradientStop { position: 0.0; color: "#1e5f8d00" }
                GradientStop { position: 0.2; color: "#174c741a" }
                GradientStop { position: 0.54; color: "#10263d7a" }
                GradientStop { position: 1.0; color: "#09142100" }
            }
            border.color: "#163f61"
            border.width: 1
            opacity: 0.78
        }

        Rectangle {
            anchors.fill: leftRailBerth
            visible: leftRailBerth.visible
            anchors.margins: 1
            radius: Math.max(2, leftRailBerth.radius - 1)
            color: "transparent"
            border.color: "#102d45"
            border.width: 1
            opacity: 0.82
        }

        Rectangle {
            id: rightRailBerth
            visible: root.wideLayout
            anchors.right: parent.right
            anchors.top: parent.top
            anchors.bottom: parent.bottom
            anchors.margins: root.scaled(20)
            width: Math.max(root.scaled(212), parent.width * 0.17)
            radius: root.cardRadius
            gradient: Gradient {
                orientation: Gradient.Horizontal
                GradientStop { position: 0.0; color: "#09142100" }
                GradientStop { position: 0.46; color: "#10263d7a" }
                GradientStop { position: 0.8; color: "#174c741a" }
                GradientStop { position: 1.0; color: "#1e5f8d00" }
            }
            border.color: "#163f61"
            border.width: 1
            opacity: 0.78
        }

        Rectangle {
            anchors.fill: rightRailBerth
            visible: rightRailBerth.visible
            anchors.margins: 1
            radius: Math.max(2, rightRailBerth.radius - 1)
            color: "transparent"
            border.color: "#102d45"
            border.width: 1
            opacity: 0.82
        }

        Rectangle {
            id: centerStageBerth
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.top: parent.top
            anchors.bottom: parent.bottom
            anchors.topMargin: root.scaled(130)
            anchors.bottomMargin: root.scaled(root.wideLayout ? 116 : 92)
            width: Math.max(
                root.scaled(root.wideLayout ? 588 : (root.mediumLayout ? 540 : 320)),
                parent.width * (root.wideLayout ? 0.39 : (root.mediumLayout ? 0.58 : 0.78))
            )
            radius: root.panelRadius
            gradient: Gradient {
                GradientStop { position: 0.0; color: "#18486f22" }
                GradientStop { position: 0.2; color: "#14375782" }
                GradientStop { position: 0.52; color: "#0a17264c" }
                GradientStop { position: 1.0; color: "#07111b00" }
            }
            border.color: "#17486e"
            border.width: 1
            opacity: 0.72
        }

        Rectangle {
            anchors.fill: centerStageBerth
            anchors.margins: root.scaled(12)
            radius: Math.max(2, centerStageBerth.radius - root.scaled(12))
            color: "transparent"
            border.color: "#11334e"
            border.width: 1
            opacity: 0.58
        }

        Rectangle {
            anchors.horizontalCenter: centerStageBerth.horizontalCenter
            anchors.top: centerStageBerth.top
            anchors.bottom: centerStageBerth.bottom
            width: 1
            color: "#17476b"
            opacity: 0.18
        }

        Rectangle {
            id: bottomActionBerth
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.bottom: parent.bottom
            anchors.leftMargin: root.scaled(20)
            anchors.rightMargin: root.scaled(20)
            anchors.bottomMargin: root.scaled(18)
            radius: root.cardRadius
            gradient: Gradient {
                GradientStop { position: 0.0; color: "#153a5a16" }
                GradientStop { position: 0.28; color: "#10253c82" }
                GradientStop { position: 1.0; color: "#07111c00" }
            }
            border.color: "#163f61"
            border.width: 1
            height: root.scaled(root.wideLayout ? 148 : 124)
            opacity: 0.78
        }

        Rectangle {
            anchors.fill: bottomActionBerth
            anchors.margins: 1
            radius: Math.max(2, bottomActionBerth.radius - 1)
            color: "transparent"
            border.color: "#102d45"
            border.width: 1
            opacity: 0.82
        }

        Rectangle {
            anchors.horizontalCenter: centerStageBerth.horizontalCenter
            anchors.top: parent.top
            anchors.bottom: parent.bottom
            width: Math.max(root.scaled(120), centerStageBerth.width * 0.18)
            radius: width / 2
            gradient: Gradient {
                GradientStop { position: 0.0; color: "#1b5a8600" }
                GradientStop { position: 0.18; color: "#1a4c7420" }
                GradientStop { position: 0.42; color: "#153a592e" }
                GradientStop { position: 0.7; color: "#0c233848" }
                GradientStop { position: 1.0; color: "#06101a00" }
            }
            opacity: 0.74
        }

        Rectangle {
            visible: root.wideLayout
            anchors.left: leftRailBerth.right
            anchors.right: rightRailBerth.left
            anchors.top: centerStageBerth.top
            anchors.leftMargin: root.scaled(28)
            anchors.rightMargin: root.scaled(28)
            anchors.topMargin: root.scaled(38)
            height: root.scaled(2)
            gradient: Gradient {
                orientation: Gradient.Horizontal
                GradientStop { position: 0.0; color: "transparent" }
                GradientStop { position: 0.16; color: root.accentBlueSoft }
                GradientStop { position: 0.5; color: root.accentCyan }
                GradientStop { position: 0.84; color: root.accentBlueSoft }
                GradientStop { position: 1.0; color: "transparent" }
            }
            opacity: 0.42
        }

        Rectangle {
            anchors.horizontalCenter: centerStageBerth.horizontalCenter
            anchors.top: centerStageBerth.top
            anchors.bottom: bottomActionBerth.top
            anchors.topMargin: root.scaled(26)
            anchors.bottomMargin: root.scaled(14)
            width: root.scaled(2)
            gradient: Gradient {
                GradientStop { position: 0.0; color: root.accentCyan }
                GradientStop { position: 0.16; color: root.accentBlue }
                GradientStop { position: 0.58; color: "#194b72" }
                GradientStop { position: 1.0; color: "transparent" }
            }
            opacity: 0.34
        }

        Rectangle {
            anchors.horizontalCenter: centerStageBerth.horizontalCenter
            anchors.top: centerStageBerth.top
            anchors.topMargin: root.scaled(30)
            width: root.scaled(8)
            height: width
            radius: width / 2
            color: root.accentCyan
            border.color: "#ffffff"
            border.width: 1
            opacity: 0.92
        }

        Rectangle {
            anchors.horizontalCenter: centerStageBerth.horizontalCenter
            anchors.bottom: bottomActionBerth.top
            anchors.bottomMargin: root.scaled(10)
            width: root.scaled(8)
            height: width
            radius: width / 2
            color: root.accentBlue
            border.color: "#ffffff"
            border.width: 1
            opacity: 0.88
        }

        Item {
            anchors.fill: parent
            opacity: 0.24

            Repeater {
                model: 13

                delegate: Rectangle {
                    width: parent.width - root.shellPadding
                    height: 1
                    x: root.shellPadding / 2
                    y: root.shellPadding + index * ((parent.height - (root.shellPadding * 2)) / 12)
                    color: index % 3 === 0 ? root.gridLineStrong : root.gridLine
                }
            }
        }

        Rectangle {
            width: root.scaled(48)
            height: 2
            color: root.accentBlue
            anchors.left: parent.left
            anchors.top: parent.top
            anchors.leftMargin: root.scaled(18)
            anchors.topMargin: root.scaled(18)
        }

        Rectangle {
            width: 2
            height: root.scaled(48)
            color: root.accentBlue
            anchors.left: parent.left
            anchors.top: parent.top
            anchors.leftMargin: root.scaled(18)
            anchors.topMargin: root.scaled(18)
        }

        Rectangle {
            width: root.scaled(48)
            height: 2
            color: root.accentCyan
            anchors.right: parent.right
            anchors.top: parent.top
            anchors.rightMargin: root.scaled(18)
            anchors.topMargin: root.scaled(18)
        }

        Rectangle {
            width: 2
            height: root.scaled(48)
            color: root.accentCyan
            anchors.right: parent.right
            anchors.top: parent.top
            anchors.rightMargin: root.scaled(18)
            anchors.topMargin: root.scaled(18)
        }

        Rectangle {
            width: root.scaled(48)
            height: 2
            color: root.accentBlue
            anchors.left: parent.left
            anchors.bottom: parent.bottom
            anchors.leftMargin: root.scaled(18)
            anchors.bottomMargin: root.scaled(18)
        }

        Rectangle {
            width: 2
            height: root.scaled(48)
            color: root.accentBlue
            anchors.left: parent.left
            anchors.bottom: parent.bottom
            anchors.leftMargin: root.scaled(18)
            anchors.bottomMargin: root.scaled(18)
        }

        Rectangle {
            width: root.scaled(48)
            height: 2
            color: root.accentCyan
            anchors.right: parent.right
            anchors.bottom: parent.bottom
            anchors.rightMargin: root.scaled(18)
            anchors.bottomMargin: root.scaled(18)
        }

        Rectangle {
            width: 2
            height: root.scaled(48)
            color: root.accentCyan
            anchors.right: parent.right
            anchors.bottom: parent.bottom
            anchors.rightMargin: root.scaled(18)
            anchors.bottomMargin: root.scaled(18)
        }

        ColumnLayout {
            anchors.fill: parent
            anchors.leftMargin: root.shellPadding + root.safeLeft
            anchors.topMargin: root.shellPadding + root.safeTop
            anchors.rightMargin: root.shellPadding + root.safeRight
            anchors.bottomMargin: root.shellPadding + root.safeBottom
            spacing: root.zoneGap

            Rectangle {
                Layout.fillWidth: true
                radius: root.panelRadius
                gradient: Gradient {
                    GradientStop { position: 0.0; color: "#0f2841" }
                    GradientStop { position: 0.7; color: "#0a1827" }
                    GradientStop { position: 1.0; color: "#08121f" }
                }
                border.color: "#2d8bca"
                border.width: 1
                implicitHeight: headerLayout.implicitHeight + (root.headerPad * 2)

                Rectangle {
                    anchors.fill: parent
                    radius: parent.radius
                    color: "transparent"
                    border.color: "#143754"
                    border.width: 1
                    opacity: 0.7
                }

                Rectangle {
                    width: parent.width * 0.44
                    height: parent.height * 0.78
                    radius: width / 2
                    color: "#1171b1"
                    opacity: 0.11
                    x: -width * 0.24
                    y: -height * 0.18
                }

                GridLayout {
                    id: headerLayout
                    anchors.fill: parent
                    anchors.margins: root.headerPad
                    columns: root.splitHeaderLayout ? 2 : 1
                    columnSpacing: root.zoneGap
                    rowSpacing: root.compactGap

                    ColumnLayout {
                        Layout.fillWidth: true
                        Layout.minimumWidth: 0
                        Layout.preferredWidth: root.splitHeaderLayout
                            ? Math.max(root.scaled(540), headerLayout.width - root.headerMirrorWidth - root.zoneGap)
                            : headerLayout.width
                        spacing: root.compactGap

                        Text {
                            text: "安全态势总控 / Native Security-Ops Shell"
                            color: root.accentCyan
                            font.pixelSize: root.eyebrowSize
                            font.family: root.monoFamily
                            font.letterSpacing: root.scaled(2)
                        }

                        Text {
                            text: root.topTitle || "飞腾原生座舱"
                            color: root.textStrong
                            font.pixelSize: root.headerTitleSize
                            font.bold: true
                            font.family: root.displayFamily
                            wrapMode: Text.WordWrap
                        }

                        Text {
                            text: root.topSubtitle
                            visible: text.length > 0
                            color: "#8ec5ea"
                            font.pixelSize: root.bodySize
                            font.family: root.monoFamily
                            font.letterSpacing: root.scaled(1)
                            wrapMode: Text.WordWrap
                        }

                        Text {
                            text: meta["subtitle"] || "Qt/QML 原生壳体继续沿用既有 TVM/OpenAMP 合同，以安全运营中台风格整合飞行、链路、弱网与锚点观测。"
                            color: root.textSecondary
                            font.pixelSize: root.bodySize
                            font.family: root.uiFamily
                            wrapMode: Text.WordWrap
                        }

                        Flow {
                            Layout.fillWidth: true
                            width: parent.width
                            spacing: root.compactGap

                            Repeater {
                                model: root.headerChipModel.length

                                delegate: Rectangle {
                                    readonly property var chip: root.headerChipModel[index]
                                    radius: root.edgeRadius
                                    gradient: Gradient {
                                        GradientStop { position: 0.0; color: Qt.lighter(root.toneFill(chip["tone"]), 1.16) }
                                        GradientStop { position: 1.0; color: root.toneFill(chip["tone"]) }
                                    }
                                    border.color: root.toneColor(chip["tone"])
                                    border.width: 1
                                    height: chipText.implicitHeight + chipValue.implicitHeight + root.scaled(20)
                                    width: Math.max(root.headerChipWidth, chipText.implicitWidth + chipValue.implicitWidth + root.scaled(30))

                                    Rectangle {
                                        anchors.left: parent.left
                                        anchors.right: parent.right
                                        anchors.top: parent.top
                                        height: root.scaled(2)
                                        gradient: Gradient {
                                            GradientStop { position: 0.0; color: "transparent" }
                                            GradientStop { position: 0.28; color: root.toneColor(chip["tone"]) }
                                            GradientStop { position: 0.74; color: Qt.lighter(root.toneColor(chip["tone"]), 1.18) }
                                            GradientStop { position: 1.0; color: "transparent" }
                                        }
                                        opacity: 0.76
                                    }

                                    Column {
                                        anchors.fill: parent
                                        anchors.margins: root.scaled(10)
                                        spacing: root.scaled(3)

                                        Text {
                                            id: chipText
                                            text: chip["label"]
                                            color: root.textMuted
                                            font.pixelSize: root.captionSize
                                            font.family: root.monoFamily
                                            font.letterSpacing: root.scaled(1)
                                        }

                                        Text {
                                            id: chipValue
                                            text: chip["value"]
                                            color: root.textStrong
                                            font.pixelSize: root.bodySize
                                            font.bold: true
                                            font.family: root.monoFamily
                                        }
                                    }
                                }
                            }
                        }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        Layout.minimumWidth: 0
                        Layout.alignment: Qt.AlignTop
                        Layout.preferredWidth: root.splitHeaderLayout ? root.headerMirrorWidth : headerLayout.width
                        Layout.maximumWidth: root.splitHeaderLayout ? root.headerMirrorWidth : Number.MAX_VALUE
                        radius: root.cardRadius
                        gradient: Gradient {
                            GradientStop { position: 0.0; color: "#11253b" }
                            GradientStop { position: 0.46; color: "#0b1828" }
                            GradientStop { position: 1.0; color: "#081321" }
                        }
                        border.color: "#2b78ab"
                        border.width: 1
                        implicitHeight: summaryColumn.implicitHeight + (root.cardPadding * 2)

                        Rectangle {
                            anchors.fill: parent
                            radius: parent.radius
                            color: "transparent"
                            border.color: "#143754"
                            border.width: 1
                            opacity: 0.78
                        }

                        Rectangle {
                            anchors.left: parent.left
                            anchors.right: parent.right
                            anchors.top: parent.top
                            height: root.scaled(3)
                            gradient: Gradient {
                                GradientStop { position: 0.0; color: "transparent" }
                                GradientStop { position: 0.24; color: root.accentBlue }
                                GradientStop { position: 0.72; color: root.accentCyan }
                                GradientStop { position: 1.0; color: "transparent" }
                            }
                            opacity: 0.82
                        }

                        Column {
                            id: summaryColumn
                            anchors.fill: parent
                            anchors.margins: root.cardPadding
                            spacing: root.compactGap

                            Text {
                                text: "态势镜像 / Mission Control Mirror"
                                color: root.accentCyan
                                font.pixelSize: root.eyebrowSize
                                font.family: root.monoFamily
                                font.letterSpacing: root.scaled(2)
                            }

                            Text {
                                width: parent.width
                                text: root.liveAnchor["label"] || "实时锚点未挂接"
                                color: root.textStrong
                                font.pixelSize: root.bodyEmphasisSize
                                font.bold: true
                                font.family: root.uiFamily
                                wrapMode: Text.WordWrap
                            }

                            Text {
                                width: parent.width
                                text: root.liveAnchor["probe_summary"] || "中心总控右舷维持合同镜像与归档锚点，只展示已知板端事实，不虚构实时链路。"
                                color: root.textSecondary
                                font.pixelSize: root.bodySize
                                font.family: root.uiFamily
                                wrapMode: Text.WordWrap
                            }

                            GridLayout {
                                width: parent.width
                                columns: root.compactLayout ? 1 : 2
                                columnSpacing: root.compactGap
                                rowSpacing: root.compactGap

                                Repeater {
                                    model: root.headerMirrorModel.length

                                    delegate: Rectangle {
                                        readonly property var metric: root.headerMirrorModel[index]
                                        Layout.fillWidth: true
                                        radius: root.edgeRadius
                                        gradient: Gradient {
                                            GradientStop { position: 0.0; color: Qt.lighter(root.toneFill(metric["tone"]), 1.1) }
                                            GradientStop { position: 1.0; color: root.toneFill(metric["tone"]) }
                                        }
                                        border.color: root.toneColor(metric["tone"])
                                        border.width: 1
                                        implicitHeight: metricColumn.implicitHeight + (root.scaled(10) * 2)

                                        Column {
                                            id: metricColumn
                                            anchors.fill: parent
                                            anchors.margins: root.scaled(10)
                                            spacing: root.scaled(3)

                                            Text {
                                                text: metric["label"]
                                                color: root.textMuted
                                                font.pixelSize: root.captionSize
                                                font.family: root.monoFamily
                                                font.letterSpacing: root.scaled(1)
                                            }

                                            Text {
                                                width: parent.width
                                                text: metric["value"]
                                                color: root.textStrong
                                                font.pixelSize: root.bodySize
                                                font.bold: true
                                                font.family: root.monoFamily
                                                wrapMode: Text.WrapAnywhere
                                            }
                                        }
                                    }
                                }
                            }

                            Rectangle {
                                width: parent.width
                                radius: root.edgeRadius
                                gradient: Gradient {
                                    GradientStop { position: 0.0; color: "#0a1727" }
                                    GradientStop { position: 1.0; color: "#081321" }
                                }
                                border.color: "#1a486a"
                                border.width: 1
                                implicitHeight: snapshotColumn.implicitHeight + (root.scaled(12) * 2)

                                Column {
                                    id: snapshotColumn
                                    anchors.fill: parent
                                    anchors.margins: root.scaled(12)
                                    spacing: root.scaled(4)

                                    Text {
                                        text: "快照路径 / Snapshot Path"
                                        color: root.accentBlue
                                        font.pixelSize: root.captionSize
                                        font.family: root.monoFamily
                                    }

                                    Text {
                                        width: parent.width
                                        text: meta["snapshot_path"] || ""
                                        color: root.textPrimary
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

            GridLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true
                columns: root.dashboardColumns
                columnSpacing: root.zoneGap
                rowSpacing: root.zoneGap

                TacticalView {
                    Layout.row: 0
                    Layout.column: root.wideLayout ? root.wideLeftSpan : 0
                    Layout.columnSpan: root.wideLayout ? root.wideCenterSpan : (root.mediumLayout ? 2 : 1)
                    Layout.fillWidth: true
                    Layout.fillHeight: root.wideLayout
                    Layout.minimumHeight: root.scaled(root.wideLayout ? 520 : 400)
                    shellWindow: root
                    panelData: root.centerPanelData
                }

                StatusPanel {
                    Layout.row: root.wideLayout ? 0 : 1
                    Layout.column: 0
                    Layout.columnSpan: root.wideLayout ? root.wideLeftSpan : 1
                    Layout.fillWidth: true
                    Layout.fillHeight: root.wideLayout
                    Layout.minimumHeight: root.scaled(root.wideLayout ? 500 : 300)
                    shellWindow: root
                    panelData: root.leftPanelData
                }

                WeakNetworkPanel {
                    Layout.row: root.wideLayout ? 0 : (root.mediumLayout ? 1 : 2)
                    Layout.column: root.wideLayout ? (root.wideLeftSpan + root.wideCenterSpan) : (root.mediumLayout ? 1 : 0)
                    Layout.columnSpan: root.wideLayout ? root.wideRightSpan : 1
                    Layout.fillWidth: true
                    Layout.fillHeight: root.wideLayout
                    Layout.minimumHeight: root.scaled(root.wideLayout ? 500 : 340)
                    shellWindow: root
                    panelData: root.rightPanelData
                }

                ActionStrip {
                    Layout.row: root.wideLayout ? 1 : (root.mediumLayout ? 2 : 3)
                    Layout.column: 0
                    Layout.columnSpan: root.wideLayout ? root.dashboardColumns : (root.mediumLayout ? 2 : 1)
                    Layout.fillWidth: true
                    shellWindow: root
                    panelData: root.bottomPanelData
                }
            }

            Rectangle {
                Layout.fillWidth: true
                radius: root.cardRadius
                gradient: Gradient {
                    GradientStop { position: 0.0; color: "#0f2236" }
                    GradientStop { position: 0.46; color: "#0a1828" }
                    GradientStop { position: 1.0; color: "#08121f" }
                }
                border.color: "#2a79ae"
                border.width: 1
                implicitHeight: shellFooterLayout.implicitHeight + (root.scaled(12) * 2)

                Rectangle {
                    anchors.fill: parent
                    anchors.margins: 1
                    radius: parent.radius - 1
                    color: "transparent"
                    border.color: "#133754"
                    border.width: 1
                    opacity: 0.82
                }

                Rectangle {
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.top: parent.top
                    height: root.scaled(3)
                    gradient: Gradient {
                        GradientStop { position: 0.0; color: "transparent" }
                        GradientStop { position: 0.22; color: root.accentBlue }
                        GradientStop { position: 0.72; color: root.accentCyan }
                        GradientStop { position: 1.0; color: "transparent" }
                    }
                    opacity: 0.8
                }

                ColumnLayout {
                    id: shellFooterLayout
                    anchors.fill: parent
                    anchors.margins: root.scaled(12)
                    spacing: root.compactGap

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: root.compactGap

                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: root.scaled(2)

                            Text {
                                text: "壳体总线 / SHELL BUS"
                                color: root.accentBlue
                                font.pixelSize: root.captionSize
                                font.family: root.monoFamily
                                font.letterSpacing: root.scaled(1)
                            }

                            Text {
                                text: "统一显示当前会话、布局策略、源状态与安全渲染路径，让整个原生 cockpit 收口成一条完成态总线。"
                                color: root.textSecondary
                                font.pixelSize: root.captionSize
                                font.family: root.uiFamily
                                wrapMode: Text.WordWrap
                            }
                        }

                        Rectangle {
                            Layout.alignment: Qt.AlignTop
                            radius: root.edgeRadius
                            color: "#091726"
                            border.color: "#1c547c"
                            border.width: 1
                            implicitWidth: shellStamp.implicitWidth + (root.scaled(12) * 2)
                            implicitHeight: shellStamp.implicitHeight + (root.scaled(5) * 2)

                            Text {
                                id: shellStamp
                                anchors.centerIn: parent
                                text: "ADAPTIVE ZONES"
                                color: root.textPrimary
                                font.pixelSize: root.captionSize
                                font.family: root.monoFamily
                            }
                        }
                    }

                    GridLayout {
                        Layout.fillWidth: true
                        columns: root.compactLayout ? 1 : (root.mediumLayout ? 2 : root.shellFooterModel.length)
                        columnSpacing: root.compactGap
                        rowSpacing: root.compactGap

                        Repeater {
                            model: root.shellFooterModel.length

                            delegate: Rectangle {
                                readonly property var itemData: root.shellFooterModel[index]
                                Layout.fillWidth: true
                                radius: root.edgeRadius
                                gradient: Gradient {
                                    GradientStop { position: 0.0; color: Qt.lighter(root.toneFill(itemData["tone"]), 1.12) }
                                    GradientStop { position: 1.0; color: root.toneFill(itemData["tone"]) }
                                }
                                border.color: root.toneColor(itemData["tone"])
                                border.width: 1
                                implicitHeight: footerMetricColumn.implicitHeight + (root.scaled(9) * 2)

                                Rectangle {
                                    anchors.left: parent.left
                                    anchors.right: parent.right
                                    anchors.top: parent.top
                                    height: root.scaled(2)
                                    gradient: Gradient {
                                        GradientStop { position: 0.0; color: "transparent" }
                                        GradientStop { position: 0.28; color: root.toneColor(itemData["tone"]) }
                                        GradientStop { position: 0.74; color: Qt.lighter(root.toneColor(itemData["tone"]), 1.16) }
                                        GradientStop { position: 1.0; color: "transparent" }
                                    }
                                    opacity: 0.74
                                }

                                Column {
                                    id: footerMetricColumn
                                    anchors.fill: parent
                                    anchors.margins: root.scaled(9)
                                    spacing: root.scaled(2)

                                    Text {
                                        text: itemData["label"]
                                        color: root.textMuted
                                        font.pixelSize: root.captionSize
                                        font.family: root.monoFamily
                                        font.letterSpacing: root.scaled(1)
                                    }

                                    Text {
                                        width: parent.width
                                        text: itemData["value"]
                                        color: root.textStrong
                                        font.pixelSize: root.bodySize
                                        font.bold: true
                                        font.family: root.monoFamily
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

        Rectangle {
            visible: leftRailBerth.visible
            anchors.left: leftRailBerth.left
            anchors.top: centerStageBerth.top
            anchors.leftMargin: root.scaled(14)
            anchors.topMargin: root.scaled(10)
            radius: root.edgeRadius
            gradient: Gradient {
                GradientStop { position: 0.0; color: "#12304a" }
                GradientStop { position: 1.0; color: "#0b1726" }
            }
            border.color: "#1c5c86"
            border.width: 1
            implicitWidth: leftBerthColumn.implicitWidth + (root.scaled(12) * 2)
            implicitHeight: leftBerthColumn.implicitHeight + (root.scaled(8) * 2)

            Column {
                id: leftBerthColumn
                anchors.centerIn: parent
                spacing: 1

                Text {
                    text: "LEFT SYSTEM RAIL"
                    color: root.accentBlue
                    font.pixelSize: root.captionSize
                    font.family: root.monoFamily
                    font.letterSpacing: root.scaled(1)
                }

                Text {
                    text: "BOARD HEALTH BUS"
                    color: root.textMuted
                    font.pixelSize: root.captionSize
                    font.family: root.uiFamily
                }
            }
        }

        Rectangle {
            anchors.horizontalCenter: centerStageBerth.horizontalCenter
            anchors.top: centerStageBerth.top
            anchors.topMargin: root.scaled(10)
            radius: root.edgeRadius
            gradient: Gradient {
                GradientStop { position: 0.0; color: "#143553" }
                GradientStop { position: 1.0; color: "#0b1726" }
            }
            border.color: "#1f668f"
            border.width: 1
            implicitWidth: centerBerthColumn.implicitWidth + (root.scaled(14) * 2)
            implicitHeight: centerBerthColumn.implicitHeight + (root.scaled(8) * 2)

            Column {
                id: centerBerthColumn
                anchors.centerIn: parent
                spacing: 1

                Text {
                    text: "CENTER THEATER"
                    color: root.accentCyan
                    font.pixelSize: root.captionSize
                    font.family: root.monoFamily
                    font.letterSpacing: root.scaled(1)
                }

                Text {
                    text: "GLOBAL WALLBOARD"
                    color: root.textMuted
                    font.pixelSize: root.captionSize
                    font.family: root.uiFamily
                }
            }
        }

        Rectangle {
            visible: rightRailBerth.visible
            anchors.right: rightRailBerth.right
            anchors.top: centerStageBerth.top
            anchors.rightMargin: root.scaled(14)
            anchors.topMargin: root.scaled(10)
            radius: root.edgeRadius
            gradient: Gradient {
                GradientStop { position: 0.0; color: "#12304a" }
                GradientStop { position: 1.0; color: "#0b1726" }
            }
            border.color: "#1c5c86"
            border.width: 1
            implicitWidth: rightBerthColumn.implicitWidth + (root.scaled(12) * 2)
            implicitHeight: rightBerthColumn.implicitHeight + (root.scaled(8) * 2)

            Column {
                id: rightBerthColumn
                anchors.centerIn: parent
                spacing: 1

                Text {
                    text: "RIGHT WEAK-LINK RAIL"
                    color: root.accentCyan
                    font.pixelSize: root.captionSize
                    font.family: root.monoFamily
                    font.letterSpacing: root.scaled(1)
                }

                Text {
                    text: "PLAYBOOK + LIVE WATCH"
                    color: root.textMuted
                    font.pixelSize: root.captionSize
                    font.family: root.uiFamily
                }
            }
        }

    }
}
