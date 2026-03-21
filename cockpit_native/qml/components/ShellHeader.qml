import QtQuick 2.15
import QtQuick.Layouts 1.15

Item {
    id: root

    property var shellWindow: null
    property int currentIndex: 0

    readonly property bool landingPage: currentIndex === 0
    readonly property var currentPageEntry: shellWindow ? shellWindow.navigationModel[currentIndex] : ({})
    readonly property bool compactTopRail: shellWindow ? shellWindow.viewportWidth < 1260 : width < 1260
    readonly property bool stackNav: shellWindow ? shellWindow.viewportWidth < 1120 : width < 1120
    readonly property bool stackStatusRail: shellWindow ? shellWindow.viewportWidth < 940 : width < 940
    readonly property int topRailPadding: shellWindow ? shellWindow.scaled(landingPage ? 10 : 13) : (landingPage ? 10 : 13)
    readonly property int navPadding: shellWindow ? shellWindow.scaled(landingPage ? 7 : 8) : (landingPage ? 7 : 8)
    readonly property color goldAccent: shellWindow ? shellWindow.accentGold : "#c6ab7d"
    readonly property color iceAccent: shellWindow ? shellWindow.accentIce : "#86c7d4"
    readonly property string leadText: shellWindow
        ? (landingPage
            ? shellWindow.currentPageSummary
            : (String(currentPageEntry["label"] || shellWindow.topTitle) + " / " + shellWindow.currentPageSummary))
        : ""
    readonly property string heroEyebrow: landingPage
        ? "TVM-FEITENG PI / PHASE 6 NATIVE COCKPIT"
        : (String(currentPageEntry["english"] || "COCKPIT PAGE") + " / ACTIVE PAGE")
    readonly property string heroTitle: shellWindow
        ? (landingPage ? shellWindow.topTitle : String(currentPageEntry["label"] || shellWindow.topTitle))
        : "飞腾原生座舱"
    readonly property string heroSubtitle: shellWindow
        ? (landingPage
            ? shellWindow.topSubtitle
            : shellWindow.currentPageSummary + " · 保持仓库回注字段与软件安全回退。")
        : ""
    readonly property string pageIndicator: shellWindow
        ? ("0" + String(currentIndex + 1)).slice(-2) + " / " + ("0" + String(shellWindow.navigationModel.length)).slice(-2)
        : "01 / 05"
    readonly property var commandRailModel: shellWindow ? shellWindow.topStatusModel : []

    signal pageRequested(int index)

    implicitHeight: headerColumn.implicitHeight

    ColumnLayout {
        id: headerColumn
        anchors.fill: parent
        spacing: shellWindow ? shellWindow.compactGap : 8

        Rectangle {
            Layout.fillWidth: true
            radius: shellWindow ? shellWindow.cardRadius + shellWindow.scaled(2) : 18
            color: shellWindow ? Qt.rgba(shellWindow.surfaceGlass.r, shellWindow.surfaceGlass.g, shellWindow.surfaceGlass.b, 0.98) : "#1d2832"
            border.color: shellWindow ? Qt.rgba(goldAccent.r, goldAccent.g, goldAccent.b, 0.84) : "#b4946c"
            border.width: 1
            implicitHeight: topRailGrid.implicitHeight + (root.topRailPadding * 2)

            Rectangle {
                anchors.fill: parent
                radius: parent.radius
                gradient: Gradient {
                    GradientStop { position: 0.0; color: shellWindow ? shellWindow.shellDockTop : "#22323d" }
                    GradientStop { position: 0.24; color: shellWindow ? shellWindow.shellDockMid : "#15202a" }
                    GradientStop { position: 1.0; color: shellWindow ? shellWindow.shellDockBottom : "#0a1118" }
                }
                opacity: 0.96
            }

            Rectangle {
                width: parent.width * 0.26
                height: parent.height * 1.08
                radius: width / 2
                color: goldAccent
                opacity: 0.08
                x: -width * 0.18
                y: -height * 0.18
            }

            Rectangle {
                width: parent.width * 0.18
                height: parent.height * 0.86
                radius: width / 2
                color: iceAccent
                opacity: 0.06
                x: parent.width - (width * 0.68)
                y: -height * 0.16
            }

            Rectangle {
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                anchors.leftMargin: shellWindow ? shellWindow.scaled(10) : 10
                anchors.rightMargin: shellWindow ? shellWindow.scaled(10) : 10
                height: shellWindow ? shellWindow.scaled(2) : 2
                gradient: Gradient {
                    orientation: Gradient.Horizontal
                    GradientStop { position: 0.0; color: "transparent" }
                    GradientStop { position: 0.18; color: Qt.rgba(goldAccent.r, goldAccent.g, goldAccent.b, 0.18) }
                    GradientStop { position: 0.48; color: Qt.rgba(goldAccent.r, goldAccent.g, goldAccent.b, 0.84) }
                    GradientStop { position: 0.82; color: Qt.rgba(iceAccent.r, iceAccent.g, iceAccent.b, 0.28) }
                    GradientStop { position: 1.0; color: "transparent" }
                }
                opacity: 0.9
            }

            GridLayout {
                id: topRailGrid
                anchors.fill: parent
                anchors.margins: root.topRailPadding
                columns: root.landingPage ? 1 : (root.compactTopRail ? 1 : 3)
                columnSpacing: shellWindow ? shellWindow.zoneGap : 12
                rowSpacing: shellWindow ? shellWindow.compactGap : 8

                Rectangle {
                    Layout.fillWidth: true
                    radius: shellWindow ? shellWindow.edgeRadius + shellWindow.scaled(1) : 13
                    color: shellWindow ? Qt.rgba(shellWindow.surfaceQuiet.r, shellWindow.surfaceQuiet.g, shellWindow.surfaceQuiet.b, 0.88) : "#101820"
                    border.color: shellWindow ? Qt.rgba(goldAccent.r, goldAccent.g, goldAccent.b, 0.72) : "#c6ab7d"
                    border.width: 1
                    implicitHeight: badgeRow.implicitHeight + ((shellWindow ? shellWindow.scaled(10) : 10) * 2)

                    RowLayout {
                        id: badgeRow
                        anchors.fill: parent
                        anchors.margins: shellWindow ? shellWindow.scaled(10) : 10
                        spacing: shellWindow ? shellWindow.compactGap : 8

                        Rectangle {
                            radius: shellWindow ? shellWindow.edgeRadius : 12
                            Layout.preferredWidth: shellWindow ? shellWindow.scaled(48) : 48
                            Layout.preferredHeight: shellWindow ? shellWindow.scaled(48) : 48
                            gradient: Gradient {
                                GradientStop { position: 0.0; color: goldAccent }
                                GradientStop { position: 1.0; color: iceAccent }
                            }

                            Rectangle {
                                anchors.fill: parent
                                anchors.margins: 1
                                radius: parent.radius - 1
                                color: shellWindow ? shellWindow.surfaceRaised : "#152029"
                            }

                            Text {
                                anchors.centerIn: parent
                                text: "FP"
                                color: shellWindow ? shellWindow.textStrong : "#f5efe4"
                                font.pixelSize: shellWindow ? shellWindow.bodyEmphasisSize + shellWindow.scaled(2) : 16
                                font.weight: Font.DemiBold
                                font.family: shellWindow ? shellWindow.displayFamily : "Noto Serif CJK SC"
                            }
                        }

                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: shellWindow ? shellWindow.scaled(2) : 2

                            RowLayout {
                                Layout.fillWidth: true
                                spacing: shellWindow ? shellWindow.compactGap : 8

                                Text {
                                    Layout.fillWidth: true
                                    text: root.heroEyebrow
                                    color: goldAccent
                                    font.pixelSize: shellWindow ? shellWindow.captionSize : 10
                                    font.family: shellWindow ? shellWindow.monoFamily : "JetBrains Mono"
                                    font.letterSpacing: shellWindow ? shellWindow.scaled(0.8) : 0.8
                                    elide: Text.ElideRight
                                }

                                Text {
                                    text: root.pageIndicator
                                    color: shellWindow ? shellWindow.textStrong : "#f5efe4"
                                    font.pixelSize: shellWindow ? shellWindow.captionSize : 10
                                    font.family: shellWindow ? shellWindow.monoFamily : "JetBrains Mono"
                                    font.letterSpacing: shellWindow ? shellWindow.scaled(0.7) : 0.7
                                }
                            }

                            Text {
                                Layout.fillWidth: true
                                text: root.heroTitle
                                color: shellWindow ? shellWindow.textStrong : "#f5efe4"
                                font.pixelSize: shellWindow
                                    ? (root.landingPage ? shellWindow.sectionTitleSize + shellWindow.scaled(2) : shellWindow.sectionTitleSize)
                                    : 24
                                font.weight: Font.DemiBold
                                font.family: shellWindow ? shellWindow.displayFamily : "Noto Serif CJK SC"
                                elide: Text.ElideRight
                            }

                            Text {
                                Layout.fillWidth: true
                                text: root.heroSubtitle
                                color: shellWindow ? shellWindow.textSecondary : "#9aa8b1"
                                font.pixelSize: shellWindow ? shellWindow.captionSize + 1 : 11
                                font.family: shellWindow ? shellWindow.uiFamily : "Noto Sans CJK SC"
                                maximumLineCount: root.landingPage ? 1 : 2
                                elide: Text.ElideRight
                            }

                            Text {
                                visible: root.landingPage && root.leadText.length > 0
                                Layout.fillWidth: true
                                text: root.leadText
                                color: shellWindow ? shellWindow.textStrong : "#f5efe4"
                                font.pixelSize: shellWindow ? shellWindow.bodySize : 13
                                font.weight: Font.DemiBold
                                font.family: shellWindow ? shellWindow.uiFamily : "Noto Sans CJK SC"
                                wrapMode: Text.WordWrap
                                maximumLineCount: 2
                                elide: Text.ElideRight
                            }

                            Flow {
                                visible: root.landingPage && root.commandRailModel.length > 0
                                Layout.fillWidth: true
                                spacing: shellWindow ? shellWindow.compactGap : 8

                                Repeater {
                                    model: root.commandRailModel

                                    delegate: ToneChip {
                                        shellWindow: root.shellWindow
                                        label: String(modelData["label"] || "--")
                                        value: String(modelData["value"] || "--")
                                        tone: String(modelData["tone"] || "neutral")
                                    }
                                }
                            }
                        }
                    }
                }

                Rectangle {
                    visible: !root.landingPage
                    Layout.fillWidth: true
                    radius: shellWindow ? shellWindow.edgeRadius + shellWindow.scaled(1) : 13
                    color: shellWindow ? Qt.rgba(shellWindow.surfaceQuiet.r, shellWindow.surfaceQuiet.g, shellWindow.surfaceQuiet.b, 0.78) : "#101820"
                    border.color: shellWindow ? Qt.rgba(shellWindow.borderSubtle.r, shellWindow.borderSubtle.g, shellWindow.borderSubtle.b, 0.84) : "#2a3944"
                    border.width: 1
                    implicitHeight: summaryColumn.implicitHeight + ((shellWindow ? shellWindow.scaled(10) : 10) * 2)

                    ColumnLayout {
                        id: summaryColumn
                        anchors.fill: parent
                        anchors.margins: shellWindow ? shellWindow.scaled(10) : 10
                        spacing: shellWindow ? shellWindow.scaled(4) : 4

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: shellWindow ? shellWindow.compactGap : 8

                            Text {
                                text: root.landingPage ? "PRIMARY COMMAND SHELL" : "ACTIVE PAGE SUMMARY"
                                color: iceAccent
                                font.pixelSize: shellWindow ? shellWindow.captionSize : 10
                                font.family: shellWindow ? shellWindow.monoFamily : "JetBrains Mono"
                                font.letterSpacing: shellWindow ? shellWindow.scaled(0.7) : 0.7
                            }

                            Rectangle {
                                Layout.alignment: Qt.AlignVCenter
                                radius: shellWindow ? shellWindow.edgeRadius : 12
                                color: shellWindow ? shellWindow.toneFill(root.landingPage ? "online" : "neutral") : "#102033"
                                border.color: shellWindow ? shellWindow.toneColor(root.landingPage ? "online" : "neutral") : "#86c7d4"
                                border.width: 1
                                implicitWidth: summaryPill.implicitWidth + ((shellWindow ? shellWindow.scaled(8) : 8) * 2)
                                implicitHeight: summaryPill.implicitHeight + ((shellWindow ? shellWindow.scaled(4) : 4) * 2)

                                Text {
                                    id: summaryPill
                                    anchors.centerIn: parent
                                    text: root.landingPage ? "MAP-FIRST" : "UNIFIED NAV"
                                    color: shellWindow ? shellWindow.textStrong : "#f5efe4"
                                    font.pixelSize: shellWindow ? shellWindow.captionSize : 10
                                    font.family: shellWindow ? shellWindow.monoFamily : "JetBrains Mono"
                                }
                            }
                        }

                        Text {
                            Layout.fillWidth: true
                            text: root.leadText
                            color: shellWindow ? shellWindow.textStrong : "#f5efe4"
                            font.pixelSize: shellWindow ? shellWindow.bodyEmphasisSize : 14
                            font.weight: Font.DemiBold
                            font.family: shellWindow ? shellWindow.uiFamily : "Noto Sans CJK SC"
                            wrapMode: Text.WordWrap
                            maximumLineCount: root.landingPage ? 2 : 3
                            elide: Text.ElideRight
                        }

                        Text {
                            Layout.fillWidth: true
                            text: root.landingPage
                                ? "借用 cluster 的壳体比例和 QDashBoard 的顶部命令带，让地图主舞台重新成为第一视觉层。"
                                : "延续相同的命令带与导航逻辑，页面切换仍保持同一个原生壳体语言。"
                            color: shellWindow ? shellWindow.textSecondary : "#9aa8b1"
                            font.pixelSize: shellWindow ? shellWindow.captionSize + 1 : 11
                            font.family: shellWindow ? shellWindow.uiFamily : "Noto Sans CJK SC"
                            wrapMode: Text.WordWrap
                            maximumLineCount: 2
                            elide: Text.ElideRight
                        }
                    }
                }

                GridLayout {
                    visible: !root.landingPage
                    Layout.fillWidth: true
                    columns: root.stackStatusRail ? 1 : 2
                    columnSpacing: shellWindow ? shellWindow.compactGap : 8
                    rowSpacing: shellWindow ? shellWindow.compactGap : 8

                    Repeater {
                        model: root.commandRailModel

                        delegate: Rectangle {
                            readonly property string tone: String(modelData["tone"] || "neutral")
                            readonly property color accent: shellWindow ? shellWindow.toneColor(tone) : "#86c7d4"

                            Layout.fillWidth: true
                            radius: shellWindow ? shellWindow.edgeRadius : 12
                            color: shellWindow ? Qt.rgba(shellWindow.surfaceRaised.r, shellWindow.surfaceRaised.g, shellWindow.surfaceRaised.b, 0.86) : "#152029"
                            border.color: Qt.rgba(accent.r, accent.g, accent.b, 0.58)
                            border.width: 1
                            implicitHeight: statusColumn.implicitHeight + ((shellWindow ? shellWindow.scaled(8) : 8) * 2)

                            Rectangle {
                                anchors.left: parent.left
                                anchors.top: parent.top
                                anchors.bottom: parent.bottom
                                anchors.leftMargin: shellWindow ? shellWindow.scaled(6) : 6
                                anchors.topMargin: shellWindow ? shellWindow.scaled(7) : 7
                                anchors.bottomMargin: shellWindow ? shellWindow.scaled(7) : 7
                                width: shellWindow ? shellWindow.scaled(2) : 2
                                radius: width / 2
                                color: accent
                                opacity: 0.84
                            }

                            ColumnLayout {
                                id: statusColumn
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
                color: "#14ffffff"
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

                        radius: shellWindow ? shellWindow.edgeRadius + shellWindow.scaled(1) : 13
                        color: selected
                            ? Qt.rgba(shellWindow.surfaceRaised.r, shellWindow.surfaceRaised.g, shellWindow.surfaceRaised.b, 0.98)
                            : Qt.rgba(shellWindow.surfaceRaised.r, shellWindow.surfaceRaised.g, shellWindow.surfaceRaised.b, 0.74)
                        border.color: selected
                            ? Qt.rgba(goldAccent.r, goldAccent.g, goldAccent.b, 0.92)
                            : Qt.rgba(shellWindow.borderSubtle.r, shellWindow.borderSubtle.g, shellWindow.borderSubtle.b, 0.9)
                        border.width: 1
                        implicitWidth: root.stackNav
                            ? Math.max(shellWindow ? shellWindow.scaled(146) : 146, navColumn.implicitWidth + ((shellWindow ? shellWindow.scaled(18) : 18) * 2))
                            : navColumn.implicitWidth + ((shellWindow ? shellWindow.scaled(18) : 18) * 2)
                        implicitHeight: navColumn.implicitHeight + ((shellWindow ? shellWindow.scaled(9) : 9) * 2)

                        Rectangle {
                            visible: selected
                            anchors.fill: parent
                            radius: parent.radius
                            gradient: Gradient {
                                orientation: Gradient.Horizontal
                                GradientStop { position: 0.0; color: Qt.rgba(goldAccent.r, goldAccent.g, goldAccent.b, 0.14) }
                                GradientStop { position: 0.5; color: "#0cffffff" }
                                GradientStop { position: 1.0; color: Qt.rgba(iceAccent.r, iceAccent.g, iceAccent.b, 0.12) }
                            }
                            opacity: 0.8
                        }

                        Rectangle {
                            anchors.left: parent.left
                            anchors.top: parent.top
                            anchors.bottom: parent.bottom
                            anchors.leftMargin: shellWindow ? shellWindow.scaled(6) : 6
                            anchors.topMargin: shellWindow ? shellWindow.scaled(8) : 8
                            anchors.bottomMargin: shellWindow ? shellWindow.scaled(8) : 8
                            width: shellWindow ? shellWindow.scaled(selected ? 3 : 2) : (selected ? 3 : 2)
                            radius: width / 2
                            color: selected ? goldAccent : shellWindow ? shellWindow.borderSubtle : "#2a3944"
                            opacity: selected ? 0.94 : 0.68
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
                                color: selected ? goldAccent : shellWindow.textMuted
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
