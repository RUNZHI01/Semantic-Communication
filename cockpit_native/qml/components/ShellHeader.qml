import QtQuick 2.15
import QtQuick.Layouts 1.15

Item {
    id: root

    property var shellWindow: null
    property int currentIndex: 0

    readonly property bool landingPage: currentIndex === 0
    readonly property var currentPageEntry: shellWindow ? shellWindow.navigationModel[currentIndex] : ({})
    readonly property int heroPadding: shellWindow
        ? shellWindow.scaled(landingPage ? (shellWindow.compactLayout ? 10 : 12) : (shellWindow.compactLayout ? 12 : 14))
        : 14
    readonly property int navPadding: shellWindow ? shellWindow.scaled(landingPage ? 7 : 9) : 9
    readonly property string leadText: shellWindow
        ? (landingPage
            ? shellWindow.currentPageSummary
            : (String(currentPageEntry["label"] || "") + " / " + shellWindow.currentPageSummary))
        : ""
    readonly property string heroEyebrow: landingPage
        ? "TVM-FEITENG PI / PHASE 6 NATIVE COCKPIT"
        : (String(currentPageEntry["english"] || "COCKPIT PAGE") + " / ACTIVE PAGE")
    readonly property string heroTitle: shellWindow
        ? (landingPage ? shellWindow.topTitle : (String(currentPageEntry["label"] || shellWindow.topTitle)))
        : "飞腾原生座舱"
    readonly property string heroSubtitle: shellWindow
        ? (landingPage
            ? shellWindow.topSubtitle
            : shellWindow.currentPageSummary + " · 继续使用仓库回注字段与安全渲染入口。")
        : ""
    readonly property string consoleTitle: landingPage ? "PRIMARY STAGE / LIVE POSTURE" : "MAP-FIRST SHELL / NAV CONTEXT"
    readonly property string consoleSummary: landingPage
        ? "压缩顶部壳体，让全球地图回到第一视觉层；系统、弱网与执行入口收束成同一条命令轨。"
        : "保持相同的壳体语言与回退策略，让每个页面仍像同一个原生产品。"
    readonly property var landingHeroModel: shellWindow ? [
        { "label": "任务代号", "value": shellWindow.missionCallSignValue, "tone": "neutral" },
        { "label": "数据源", "value": shellWindow.activeSourceLabel, "tone": "online" },
        { "label": "推荐剧本", "value": shellWindow.recommendedScenarioId, "tone": "warning" }
    ] : []
    readonly property var heroChipModel: landingPage ? landingHeroModel : (shellWindow ? shellWindow.topStatusModel : [])
    readonly property var consoleModel: landingPage ? (shellWindow ? shellWindow.topStatusModel : []) : landingHeroModel

    signal pageRequested(int index)

    implicitHeight: headerColumn.implicitHeight

    ColumnLayout {
        id: headerColumn
        anchors.fill: parent
        spacing: shellWindow ? shellWindow.compactGap : 8

        Rectangle {
            Layout.fillWidth: true
            radius: shellWindow ? shellWindow.panelRadius + shellWindow.scaled(2) : 24
            color: shellWindow ? Qt.rgba(shellWindow.surfaceGlass.r, shellWindow.surfaceGlass.g, shellWindow.surfaceGlass.b, 0.98) : "#1c2731"
            border.color: shellWindow ? Qt.rgba(shellWindow.borderStrong.r, shellWindow.borderStrong.g, shellWindow.borderStrong.b, 0.86) : "#b4946c"
            border.width: 1
            implicitHeight: heroGrid.implicitHeight + (root.heroPadding * 2)

            Rectangle {
                anchors.fill: parent
                radius: parent.radius
                gradient: Gradient {
                    GradientStop { position: 0.0; color: "#12ffffff" }
                    GradientStop { position: 0.24; color: "#05ffffff" }
                    GradientStop { position: 1.0; color: "#00000000" }
                }
                opacity: 0.46
            }

            Rectangle {
                width: parent.width * 0.32
                height: parent.height * 0.9
                radius: width / 2
                color: shellWindow ? shellWindow.accentGold : "#c6ab7d"
                opacity: 0.08
                x: -width * 0.16
                y: -height * 0.2
            }

            Rectangle {
                width: parent.width * 0.26
                height: parent.height * 0.84
                radius: width / 2
                color: shellWindow ? shellWindow.accentIce : "#86c7d4"
                opacity: 0.06
                x: parent.width - (width * 0.72)
                y: -height * 0.22
            }

            Rectangle {
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                anchors.leftMargin: shellWindow ? shellWindow.scaled(12) : 12
                anchors.rightMargin: shellWindow ? shellWindow.scaled(12) : 12
                height: shellWindow ? shellWindow.scaled(2) : 2
                radius: height / 2
                gradient: Gradient {
                    orientation: Gradient.Horizontal
                    GradientStop { position: 0.0; color: "transparent" }
                    GradientStop { position: 0.18; color: Qt.rgba(shellWindow.accentGold.r, shellWindow.accentGold.g, shellWindow.accentGold.b, 0.16) }
                    GradientStop { position: 0.48; color: Qt.rgba(shellWindow.accentGold.r, shellWindow.accentGold.g, shellWindow.accentGold.b, 0.82) }
                    GradientStop { position: 0.78; color: Qt.rgba(shellWindow.accentIce.r, shellWindow.accentIce.g, shellWindow.accentIce.b, 0.22) }
                    GradientStop { position: 1.0; color: "transparent" }
                }
            }

            GridLayout {
                id: heroGrid
                anchors.fill: parent
                anchors.margins: root.heroPadding
                columns: shellWindow && shellWindow.viewportWidth < shellWindow.scaled(1120) ? 1 : 2
                columnSpacing: shellWindow ? shellWindow.zoneGap : 12
                rowSpacing: shellWindow ? shellWindow.compactGap : 8

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: shellWindow ? shellWindow.scaled(5) : 5

                    Text {
                        text: root.heroEyebrow
                        color: shellWindow ? shellWindow.accentGold : "#c6ab7d"
                        font.pixelSize: shellWindow ? shellWindow.eyebrowSize : 10
                        font.family: shellWindow ? shellWindow.monoFamily : "JetBrains Mono"
                        font.letterSpacing: shellWindow ? shellWindow.scaled(0.9) : 0.9
                    }

                    Text {
                        Layout.fillWidth: true
                        text: root.heroTitle
                        color: shellWindow ? shellWindow.textStrong : "#f5efe4"
                        font.pixelSize: shellWindow
                            ? (root.landingPage
                                ? shellWindow.sectionTitleSize + shellWindow.scaled(shellWindow.compactLayout ? 3 : 5)
                                : shellWindow.headerTitleSize)
                            : 32
                        font.weight: Font.DemiBold
                        font.family: shellWindow ? shellWindow.displayFamily : "Noto Serif CJK SC"
                        wrapMode: Text.WordWrap
                    }

                    Text {
                        Layout.fillWidth: true
                        text: root.heroSubtitle
                        color: shellWindow ? shellWindow.textSecondary : "#9aa8b1"
                        font.pixelSize: shellWindow ? shellWindow.captionSize + 2 : 12
                        font.family: shellWindow ? shellWindow.uiFamily : "Noto Sans CJK SC"
                        wrapMode: Text.WordWrap
                        maximumLineCount: root.landingPage ? 1 : 2
                        elide: Text.ElideRight
                    }

                    Flow {
                        Layout.fillWidth: true
                        spacing: shellWindow ? shellWindow.compactGap : 8

                        Repeater {
                            model: root.heroChipModel

                            delegate: ToneChip {
                                shellWindow: root.shellWindow
                                label: modelData["label"]
                                value: modelData["value"]
                                tone: modelData["tone"]
                                prominent: root.landingPage
                            }
                        }
                    }
                }

                Rectangle {
                    Layout.fillWidth: true
                    radius: shellWindow ? shellWindow.cardRadius : 16
                    color: shellWindow ? Qt.rgba(shellWindow.surfaceQuiet.r, shellWindow.surfaceQuiet.g, shellWindow.surfaceQuiet.b, 0.86) : "#101820"
                    border.color: shellWindow ? Qt.rgba(shellWindow.borderSubtle.r, shellWindow.borderSubtle.g, shellWindow.borderSubtle.b, 0.9) : "#2a3944"
                    border.width: 1
                    implicitHeight: consoleColumn.implicitHeight + ((shellWindow ? shellWindow.cardPadding : 12) * 2)

                    Rectangle {
                        anchors.fill: parent
                        anchors.margins: 1
                        radius: parent.radius - 1
                        color: "transparent"
                        border.color: "#0dffffff"
                        border.width: 1
                    }

                    ColumnLayout {
                        id: consoleColumn
                        anchors.fill: parent
                        anchors.margins: shellWindow ? shellWindow.cardPadding : 12
                        spacing: shellWindow ? shellWindow.compactGap : 8

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: shellWindow ? shellWindow.compactGap : 8

                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: shellWindow ? shellWindow.scaled(1) : 1

                                Text {
                                    text: root.consoleTitle
                                    color: shellWindow ? shellWindow.accentIce : "#86c7d4"
                                    font.pixelSize: shellWindow ? shellWindow.captionSize : 10
                                    font.family: shellWindow ? shellWindow.monoFamily : "JetBrains Mono"
                                    font.letterSpacing: shellWindow ? shellWindow.scaled(0.8) : 0.8
                                }

                                Text {
                                    Layout.fillWidth: true
                                    text: root.leadText
                                    color: shellWindow ? shellWindow.textStrong : "#f5efe4"
                                    font.pixelSize: shellWindow ? shellWindow.bodyEmphasisSize : 14
                                    font.weight: Font.DemiBold
                                    font.family: shellWindow ? shellWindow.uiFamily : "Noto Sans CJK SC"
                                    wrapMode: Text.WordWrap
                                    maximumLineCount: 2
                                    elide: Text.ElideRight
                                }
                            }

                            Rectangle {
                                radius: shellWindow ? shellWindow.edgeRadius : 12
                                color: shellWindow ? Qt.rgba(shellWindow.surfaceRaised.r, shellWindow.surfaceRaised.g, shellWindow.surfaceRaised.b, 0.9) : "#152029"
                                border.color: shellWindow ? Qt.rgba(shellWindow.accentGold.r, shellWindow.accentGold.g, shellWindow.accentGold.b, 0.76) : "#c6ab7d"
                                border.width: 1
                                implicitWidth: consolePillText.implicitWidth + ((shellWindow ? shellWindow.scaled(10) : 10) * 2)
                                implicitHeight: consolePillText.implicitHeight + ((shellWindow ? shellWindow.scaled(6) : 6) * 2)

                                Text {
                                    id: consolePillText
                                    anchors.centerIn: parent
                                    text: root.landingPage ? "MAP FIRST" : "UNIFIED SHELL"
                                    color: shellWindow ? shellWindow.textStrong : "#f5efe4"
                                    font.pixelSize: shellWindow ? shellWindow.captionSize : 10
                                    font.family: shellWindow ? shellWindow.monoFamily : "JetBrains Mono"
                                    font.letterSpacing: shellWindow ? shellWindow.scaled(0.7) : 0.7
                                }
                            }
                        }

                        Text {
                            Layout.fillWidth: true
                            text: root.consoleSummary
                            color: shellWindow ? shellWindow.textSecondary : "#9aa8b1"
                            font.pixelSize: shellWindow ? shellWindow.captionSize + 1 : 11
                            font.family: shellWindow ? shellWindow.uiFamily : "Noto Sans CJK SC"
                            wrapMode: Text.WordWrap
                            maximumLineCount: root.landingPage ? 1 : 2
                            elide: Text.ElideRight
                        }

                        GridLayout {
                            Layout.fillWidth: true
                            columns: root.consoleModel.length >= 4 ? 2 : Math.max(1, root.consoleModel.length)
                            columnSpacing: shellWindow ? shellWindow.compactGap : 8
                            rowSpacing: shellWindow ? shellWindow.compactGap : 8

                            Repeater {
                                model: root.consoleModel

                                delegate: Rectangle {
                                    readonly property string itemTone: String(modelData["tone"] || "neutral")
                                    readonly property color itemAccent: shellWindow ? shellWindow.toneColor(itemTone) : "#86c7d4"

                                    Layout.fillWidth: true
                                    radius: shellWindow ? shellWindow.edgeRadius : 12
                                    color: shellWindow ? Qt.rgba(shellWindow.surfaceRaised.r, shellWindow.surfaceRaised.g, shellWindow.surfaceRaised.b, 0.88) : "#152029"
                                    border.color: Qt.rgba(itemAccent.r, itemAccent.g, itemAccent.b, 0.56)
                                    border.width: 1
                                    implicitHeight: consoleCellColumn.implicitHeight + ((shellWindow ? shellWindow.scaled(8) : 8) * 2)

                                    Rectangle {
                                        anchors.left: parent.left
                                        anchors.top: parent.top
                                        anchors.bottom: parent.bottom
                                        anchors.leftMargin: shellWindow ? shellWindow.scaled(6) : 6
                                        anchors.topMargin: shellWindow ? shellWindow.scaled(7) : 7
                                        anchors.bottomMargin: shellWindow ? shellWindow.scaled(7) : 7
                                        width: shellWindow ? shellWindow.scaled(2) : 2
                                        radius: width / 2
                                        color: itemAccent
                                        opacity: 0.84
                                    }

                                    ColumnLayout {
                                        id: consoleCellColumn
                                        anchors.left: parent.left
                                        anchors.right: parent.right
                                        anchors.verticalCenter: parent.verticalCenter
                                        anchors.leftMargin: shellWindow ? shellWindow.scaled(14) : 14
                                        anchors.rightMargin: shellWindow ? shellWindow.scaled(10) : 10
                                        spacing: shellWindow ? shellWindow.scaled(1) : 1

                                        Text {
                                            Layout.fillWidth: true
                                            text: String(modelData["label"] || "--")
                                            color: shellWindow ? shellWindow.textMuted : "#6f7f8a"
                                            font.pixelSize: shellWindow ? shellWindow.captionSize : 10
                                            font.family: shellWindow ? shellWindow.monoFamily : "JetBrains Mono"
                                            elide: Text.ElideRight
                                        }

                                        Text {
                                            Layout.fillWidth: true
                                            text: String(modelData["value"] || "--")
                                            color: shellWindow ? shellWindow.textStrong : "#f5efe4"
                                            font.pixelSize: shellWindow ? shellWindow.bodyEmphasisSize : 14
                                            font.weight: Font.DemiBold
                                            font.family: shellWindow ? shellWindow.uiFamily : "Noto Sans CJK SC"
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

        Rectangle {
            Layout.fillWidth: true
            radius: shellWindow ? shellWindow.cardRadius : 16
            color: shellWindow ? Qt.rgba(shellWindow.surfaceQuiet.r, shellWindow.surfaceQuiet.g, shellWindow.surfaceQuiet.b, 0.94) : "#0f161d"
            border.color: shellWindow ? Qt.rgba(shellWindow.borderSubtle.r, shellWindow.borderSubtle.g, shellWindow.borderSubtle.b, 0.88) : "#2a3944"
            border.width: 1
            implicitHeight: navFlow.implicitHeight + (root.navPadding * 2)

            Rectangle {
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                anchors.leftMargin: shellWindow ? shellWindow.scaled(10) : 10
                anchors.rightMargin: shellWindow ? shellWindow.scaled(10) : 10
                height: shellWindow ? shellWindow.scaled(1) : 1
                color: "#12ffffff"
            }

            Flow {
                id: navFlow
                anchors.fill: parent
                anchors.margins: root.navPadding
                spacing: shellWindow ? shellWindow.compactGap : 8

                Repeater {
                    model: shellWindow ? shellWindow.navigationModel : []

                    delegate: Rectangle {
                        readonly property bool selected: Number(modelData["index"]) === root.currentIndex

                        radius: shellWindow ? shellWindow.edgeRadius : 12
                        color: selected
                            ? Qt.rgba(shellWindow.surfaceRaised.r, shellWindow.surfaceRaised.g, shellWindow.surfaceRaised.b, 0.98)
                            : Qt.rgba(shellWindow.surfaceRaised.r, shellWindow.surfaceRaised.g, shellWindow.surfaceRaised.b, 0.72)
                        border.color: selected
                            ? Qt.rgba(shellWindow.accentGold.r, shellWindow.accentGold.g, shellWindow.accentGold.b, 0.9)
                            : Qt.rgba(shellWindow.borderSubtle.r, shellWindow.borderSubtle.g, shellWindow.borderSubtle.b, 0.88)
                        border.width: 1
                        implicitWidth: navColumn.implicitWidth + ((shellWindow ? shellWindow.scaled(12) : 12) * 2)
                        implicitHeight: navColumn.implicitHeight + ((shellWindow ? shellWindow.scaled(root.landingPage ? 7 : 8) : 8) * 2)

                        Rectangle {
                            anchors.left: parent.left
                            anchors.top: parent.top
                            anchors.bottom: parent.bottom
                            anchors.leftMargin: shellWindow ? shellWindow.scaled(6) : 6
                            anchors.topMargin: shellWindow ? shellWindow.scaled(7) : 7
                            anchors.bottomMargin: shellWindow ? shellWindow.scaled(7) : 7
                            width: shellWindow ? shellWindow.scaled(selected ? 3 : 2) : (selected ? 3 : 2)
                            radius: width / 2
                            color: selected ? shellWindow.accentGold : shellWindow.borderSubtle
                            opacity: selected ? 0.94 : 0.7
                        }

                        Rectangle {
                            visible: selected
                            anchors.left: parent.left
                            anchors.right: parent.right
                            anchors.top: parent.top
                            anchors.leftMargin: shellWindow ? shellWindow.scaled(10) : 10
                            anchors.rightMargin: shellWindow ? shellWindow.scaled(10) : 10
                            anchors.topMargin: shellWindow ? shellWindow.scaled(4) : 4
                            height: shellWindow ? shellWindow.scaled(2) : 2
                            radius: height / 2
                            gradient: Gradient {
                                orientation: Gradient.Horizontal
                                GradientStop { position: 0.0; color: "transparent" }
                                GradientStop { position: 0.24; color: shellWindow.accentGold }
                                GradientStop { position: 0.78; color: Qt.lighter(shellWindow.accentIce, 1.08) }
                                GradientStop { position: 1.0; color: "transparent" }
                            }
                            opacity: 0.92
                        }

                        ColumnLayout {
                            id: navColumn
                            anchors.centerIn: parent
                            spacing: shellWindow ? shellWindow.scaled(1) : 1

                            Text {
                                text: modelData["label"]
                                color: selected ? shellWindow.textStrong : shellWindow.textPrimary
                                font.pixelSize: shellWindow ? shellWindow.bodyEmphasisSize : 14
                                font.weight: selected ? Font.DemiBold : Font.Medium
                                font.family: shellWindow ? shellWindow.uiFamily : "Noto Sans CJK SC"
                            }

                            Text {
                                text: modelData["english"]
                                color: selected ? shellWindow.accentGold : shellWindow.textMuted
                                font.pixelSize: shellWindow ? shellWindow.captionSize : 10
                                font.family: shellWindow ? shellWindow.monoFamily : "JetBrains Mono"
                            }
                        }

                        MouseArea {
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: root.pageRequested(Number(modelData["index"]))
                        }
                    }
                }
            }
        }
    }
}
