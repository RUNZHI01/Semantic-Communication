import QtQuick 2.15
import QtQuick.Layouts 1.15

Item {
    id: root

    property var shellWindow: null
    property int currentIndex: 0

    signal pageRequested(int index)

    implicitHeight: headerColumn.implicitHeight

    ColumnLayout {
        id: headerColumn
        anchors.fill: parent
        spacing: shellWindow ? shellWindow.zoneGap : 14

        Rectangle {
            Layout.fillWidth: true
            radius: shellWindow ? shellWindow.panelRadius + shellWindow.scaled(2) : 24
            color: shellWindow ? shellWindow.surfaceGlass : "#1c2731"
            border.color: shellWindow ? shellWindow.borderStrong : "#b4946c"
            border.width: 1
            implicitHeight: heroGrid.implicitHeight + ((shellWindow ? shellWindow.panelPadding : 18) * 2)

            Rectangle {
                width: parent.width * 0.36
                height: parent.height * 0.8
                radius: width / 2
                color: shellWindow ? shellWindow.accentGold : "#c6ab7d"
                opacity: 0.07
                x: -width * 0.18
                y: -height * 0.2
            }

            GridLayout {
                id: heroGrid
                anchors.fill: parent
                anchors.margins: shellWindow ? shellWindow.panelPadding : 18
                columns: shellWindow && shellWindow.compactLayout ? 1 : 2
                columnSpacing: shellWindow ? shellWindow.zoneGap : 12
                rowSpacing: shellWindow ? shellWindow.compactGap : 8

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: shellWindow ? shellWindow.compactGap : 8

                    Text {
                        text: "TVM-飞腾派项目 / PHASE 6 DEMO"
                        color: shellWindow ? shellWindow.accentGold : "#c6ab7d"
                        font.pixelSize: shellWindow ? shellWindow.eyebrowSize : 10
                        font.family: shellWindow ? shellWindow.monoFamily : "JetBrains Mono"
                        font.letterSpacing: shellWindow ? shellWindow.scaled(1) : 1
                    }

                    Text {
                        Layout.fillWidth: true
                        text: shellWindow ? shellWindow.topTitle : "飞腾原生座舱"
                        color: shellWindow ? shellWindow.textStrong : "#f5efe4"
                        font.pixelSize: shellWindow ? shellWindow.headerTitleSize : 32
                        font.weight: Font.DemiBold
                        font.family: shellWindow ? shellWindow.displayFamily : "Noto Serif CJK SC"
                        wrapMode: Text.WordWrap
                    }

                    Text {
                        Layout.fillWidth: true
                        text: shellWindow
                            ? shellWindow.currentPageSummary + "\n" + shellWindow.topSubtitle
                            : ""
                        color: shellWindow ? shellWindow.textSecondary : "#9aa8b1"
                        font.pixelSize: shellWindow ? shellWindow.bodySize : 13
                        font.family: shellWindow ? shellWindow.uiFamily : "Noto Sans CJK SC"
                        wrapMode: Text.WordWrap
                    }
                }

                Flow {
                    Layout.fillWidth: true
                    spacing: shellWindow ? shellWindow.compactGap : 8

                    Repeater {
                        model: shellWindow ? shellWindow.topStatusModel : []

                        delegate: ToneChip {
                            shellWindow: root.shellWindow
                            label: modelData["label"]
                            value: modelData["value"]
                            tone: modelData["tone"]
                            prominent: true
                        }
                    }
                }
            }
        }

        Rectangle {
            Layout.fillWidth: true
            radius: shellWindow ? shellWindow.cardRadius : 16
            color: shellWindow ? shellWindow.surfaceQuiet : "#0f161d"
            border.color: shellWindow ? shellWindow.borderSubtle : "#2a3944"
            border.width: 1
            implicitHeight: navFlow.implicitHeight + ((shellWindow ? shellWindow.cardPadding : 14) * 2)

            Flow {
                id: navFlow
                anchors.fill: parent
                anchors.margins: shellWindow ? shellWindow.cardPadding : 14
                spacing: shellWindow ? shellWindow.compactGap : 8

                Repeater {
                    model: shellWindow ? shellWindow.navigationModel : []

                    delegate: Rectangle {
                        readonly property bool selected: Number(modelData["index"]) === root.currentIndex

                        radius: shellWindow ? shellWindow.edgeRadius : 12
                        color: selected
                            ? Qt.rgba(
                                shellWindow.accentGold.r,
                                shellWindow.accentGold.g,
                                shellWindow.accentGold.b,
                                0.14
                            )
                            : shellWindow.surfaceRaised
                        border.color: selected ? shellWindow.accentGold : shellWindow.borderSubtle
                        border.width: 1
                        implicitWidth: navColumn.implicitWidth + ((shellWindow ? shellWindow.scaled(12) : 12) * 2)
                        implicitHeight: navColumn.implicitHeight + ((shellWindow ? shellWindow.scaled(9) : 9) * 2)

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
