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
    readonly property bool softwareRenderEnabled: !!options["softwareRender"]

    readonly property int designWidth: 1440
    readonly property int designHeight: 900

    readonly property string displayFamily: "Noto Sans CJK SC"
    readonly property string uiFamily: "Noto Sans CJK SC"
    readonly property string monoFamily: "JetBrains Mono"

    readonly property color bgColorDeep: "#020710"
    readonly property color bgColorMid: "#071629"
    readonly property color bgColorLight: "#0f3359"
    readonly property color shellColor: "#07101d"
    readonly property color shellColorRaised: "#0b1727"
    readonly property color panelColor: "#0a1523"
    readonly property color panelColorRaised: "#102239"
    readonly property color cardColor: "#112743"
    readonly property color cardColorSoft: "#0c1829"
    readonly property color borderSoft: "#214666"
    readonly property color borderStrong: "#5ac7ff"
    readonly property color accentBlue: "#4ebcff"
    readonly property color accentCyan: "#9ff1ff"
    readonly property color accentGreen: "#42f0bc"
    readonly property color accentAmber: "#ffbf52"
    readonly property color accentRed: "#ff7b7b"
    readonly property color textStrong: "#f6fbff"
    readonly property color textPrimary: "#d7efff"
    readonly property color textSecondary: "#8db2cc"
    readonly property color textMuted: "#5a778e"
    readonly property color gridLine: "#132b42"
    readonly property color gridLineStrong: "#24567d"

    readonly property real widthScale: Math.max(0.78, Math.min(1.18, Number(metrics["width"] || designWidth) / designWidth))
    readonly property real heightScale: Math.max(0.78, Math.min(1.18, Number(metrics["height"] || designHeight) / designHeight))
    readonly property real uiScale: Math.min(widthScale, heightScale)

    readonly property int safeLeft: Number(insets["left"] || 0)
    readonly property int safeTop: Number(insets["top"] || 0)
    readonly property int safeRight: Number(insets["right"] || 0)
    readonly property int safeBottom: Number(insets["bottom"] || 0)

    readonly property int outerPadding: scaled(20)
    readonly property int shellPadding: scaled(24)
    readonly property int zoneGap: scaled(18)
    readonly property int compactGap: scaled(8)
    readonly property int panelPadding: scaled(18)
    readonly property int cardPadding: scaled(14)
    readonly property int panelRadius: scaled(22)
    readonly property int cardRadius: scaled(14)
    readonly property int edgeRadius: scaled(10)
    readonly property int headerTitleSize: scaled(38)
    readonly property int sectionTitleSize: scaled(24)
    readonly property int bodyEmphasisSize: scaled(15)
    readonly property int bodySize: scaled(13)
    readonly property int captionSize: scaled(11)
    readonly property int eyebrowSize: scaled(10)

    readonly property real contentWidth: Math.max(1, width - safeLeft - safeRight - (outerPadding * 2))
    readonly property bool wideLayout: contentWidth >= scaled(1380)
    readonly property bool mediumLayout: !wideLayout && contentWidth >= scaled(980)
    readonly property bool compactLayout: !wideLayout && !mediumLayout
    readonly property int dashboardColumns: wideLayout ? 16 : (mediumLayout ? 2 : 1)
    readonly property int wideLeftSpan: 3
    readonly property int wideCenterSpan: 10
    readonly property int wideRightSpan: 3

    readonly property string topTitle: primaryLabel(meta["title"] || "飞腾原生座舱 / Feiteng Native Cockpit")
    readonly property string topSubtitle: secondaryLabel(meta["title"] || "飞腾原生座舱 / Feiteng Native Cockpit")
    readonly property var liveAnchor: DataUtils.objectOrEmpty(rightPanelData["live_anchor"])

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
        anchors.fill: parent
        gradient: Gradient {
            GradientStop { position: 0.0; color: root.bgColorLight }
            GradientStop { position: 0.38; color: root.bgColorMid }
            GradientStop { position: 1.0; color: root.bgColorDeep }
        }
        opacity: 0.72
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
            color: "#0b2d4e"
            opacity: 0.12
        }

        Rectangle {
            anchors.fill: parent
            radius: root.panelRadius
            gradient: Gradient {
                GradientStop { position: 0.0; color: root.shellColorRaised }
                GradientStop { position: 0.48; color: root.shellColor }
                GradientStop { position: 1.0; color: "#040b16" }
            }
            border.color: "#2c77aa"
            border.width: 1
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
                implicitHeight: headerLayout.implicitHeight + (root.shellPadding * 2)

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
                    opacity: 0.09
                    x: -width * 0.24
                    y: -height * 0.18
                }

                GridLayout {
                    id: headerLayout
                    anchors.fill: parent
                    anchors.margins: root.shellPadding
                    columns: root.compactLayout ? 1 : 2
                    columnSpacing: root.zoneGap
                    rowSpacing: root.compactGap

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: root.compactGap

                        Text {
                            text: "飞行态势总控 / Native Operations Shell"
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
                            text: meta["subtitle"] || "Qt/QML 原生壳体读取既有 TVM/OpenAMP 合同，保持自适应布局与安全区处理。"
                            color: root.textSecondary
                            font.pixelSize: root.bodySize
                            font.family: root.uiFamily
                            wrapMode: Text.WordWrap
                        }

                        Flow {
                            Layout.fillWidth: true
                            spacing: root.compactGap

                            Repeater {
                                model: root.headerChipModel.length

                                delegate: Rectangle {
                                    readonly property var chip: root.headerChipModel[index]
                                    radius: root.edgeRadius
                                    color: root.toneFill(chip["tone"])
                                    border.color: root.toneColor(chip["tone"])
                                    border.width: 1
                                    height: chipText.implicitHeight + chipValue.implicitHeight + root.scaled(18)
                                    width: Math.max(root.scaled(150), chipText.implicitWidth + chipValue.implicitWidth + root.scaled(28))

                                    Column {
                                        anchors.fill: parent
                                        anchors.margins: root.scaled(9)
                                        spacing: root.scaled(2)

                                        Text {
                                            id: chipText
                                            text: chip["label"]
                                            color: root.textSecondary
                                            font.pixelSize: root.captionSize
                                            font.family: root.uiFamily
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
                        radius: root.cardRadius
                        gradient: Gradient {
                            GradientStop { position: 0.0; color: "#0d1f31" }
                            GradientStop { position: 1.0; color: "#091625" }
                        }
                        border.color: "#21537d"
                        border.width: 1
                        implicitHeight: summaryColumn.implicitHeight + (root.cardPadding * 2)

                        Column {
                            id: summaryColumn
                            anchors.fill: parent
                            anchors.margins: root.cardPadding
                            spacing: root.compactGap

                            Text {
                                text: "合同快照 / Live Contract Mirror"
                                color: root.accentBlue
                                font.pixelSize: root.eyebrowSize
                                font.family: root.monoFamily
                                font.letterSpacing: root.scaled(1)
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
                                text: root.liveAnchor["probe_summary"] || "显示的是仓库合同与归档快照，不推断不存在的实时链路。"
                                color: root.textSecondary
                                font.pixelSize: root.bodySize
                                font.family: root.uiFamily
                                wrapMode: Text.WordWrap
                            }

                            Rectangle {
                                width: parent.width
                                radius: root.edgeRadius
                                color: "#081321"
                                border.color: "#143654"
                                border.width: 1
                                implicitHeight: snapshotColumn.implicitHeight + (root.scaled(12) * 2)

                                Column {
                                    id: snapshotColumn
                                    anchors.fill: parent
                                    anchors.margins: root.scaled(12)
                                    spacing: root.scaled(4)

                                    Text {
                                        text: "Snapshot Path"
                                        color: root.textMuted
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
        }
    }
}
