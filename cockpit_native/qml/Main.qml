import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import QtQuick.Window 2.15
import "components"

ApplicationWindow {
    id: root
    readonly property var uiState: cockpitBridge ? cockpitBridge.state : ({})
    readonly property var zones: uiState["zones"] || ({})
    readonly property var metrics: screenMetrics || ({})
    readonly property var insets: safeAreaInsets || ({})

    readonly property int designWidth: 1440
    readonly property int designHeight: 900
    readonly property string monoFamily: "DejaVu Sans Mono"

    readonly property real widthScale: Math.max(0.78, Math.min(1.18, Number(metrics["width"] || designWidth) / designWidth))
    readonly property real heightScale: Math.max(0.78, Math.min(1.18, Number(metrics["height"] || designHeight) / designHeight))
    readonly property real uiScale: Math.min(widthScale, heightScale)

    readonly property int safeLeft: Number(insets["left"] || 0)
    readonly property int safeTop: Number(insets["top"] || 0)
    readonly property int safeRight: Number(insets["right"] || 0)
    readonly property int safeBottom: Number(insets["bottom"] || 0)

    readonly property int outerPadding: scaled(18)
    readonly property int shellPadding: scaled(20)
    readonly property int zoneGap: scaled(16)
    readonly property int compactGap: scaled(8)
    readonly property int panelPadding: scaled(18)
    readonly property int cardPadding: scaled(12)
    readonly property int panelRadius: scaled(18)
    readonly property int cardRadius: scaled(12)
    readonly property int headerTitleSize: scaled(30)
    readonly property int sectionTitleSize: scaled(22)
    readonly property int bodyEmphasisSize: scaled(14)
    readonly property int bodySize: scaled(13)
    readonly property int captionSize: scaled(11)

    readonly property real contentWidth: Math.max(1, width - safeLeft - safeRight - (outerPadding * 2))
    readonly property bool wideLayout: contentWidth >= scaled(1380)
    readonly property bool mediumLayout: !wideLayout && contentWidth >= scaled(980)
    readonly property bool compactLayout: !wideLayout && !mediumLayout
    readonly property int dashboardColumns: wideLayout ? 12 : (mediumLayout ? 2 : 1)

    minimumWidth: 920
    minimumHeight: 680
    visible: true
    color: "#07111a"
    title: ((uiState["meta"] || {})["title"] || "飞腾原生座舱")

    function scaled(value) {
        return Math.max(1, Math.round(value * uiScale))
    }

    Component.onCompleted: {
        const availableWidth = Math.max(minimumWidth, Number(metrics["width"] || designWidth))
        const availableHeight = Math.max(minimumHeight, Number(metrics["height"] || designHeight))
        width = Math.max(minimumWidth, Math.min(Math.round(availableWidth * 0.94), scaled(1720)))
        height = Math.max(minimumHeight, Math.min(Math.round(availableHeight * 0.92), scaled(1060)))
    }

    Rectangle {
        anchors.fill: parent
        gradient: Gradient {
            GradientStop { position: 0.0; color: "#14314a" }
            GradientStop { position: 0.46; color: "#0a1723" }
            GradientStop { position: 1.0; color: "#050b12" }
        }
    }

    Rectangle {
        anchors.fill: parent
        color: "transparent"
        border.width: 1
        border.color: "#1b5670"
        radius: root.panelRadius
        anchors.leftMargin: root.outerPadding
        anchors.topMargin: root.outerPadding
        anchors.rightMargin: root.outerPadding
        anchors.bottomMargin: root.outerPadding
        opacity: 0.9
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.leftMargin: root.outerPadding + root.safeLeft
        anchors.topMargin: root.outerPadding + root.safeTop
        anchors.rightMargin: root.outerPadding + root.safeRight
        anchors.bottomMargin: root.outerPadding + root.safeBottom
        spacing: root.zoneGap

        Rectangle {
            Layout.fillWidth: true
            implicitHeight: headerGrid.implicitHeight + (root.shellPadding * 2)
            radius: root.panelRadius
            color: "#102638"
            border.color: "#2aa3c9"
            border.width: 1

            GridLayout {
                id: headerGrid
                anchors.fill: parent
                anchors.margins: root.shellPadding
                columns: root.compactLayout ? 1 : 2
                columnSpacing: root.zoneGap
                rowSpacing: root.compactGap

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: root.compactGap

                    Text {
                        text: (uiState["meta"] || {})["title"] || "飞腾原生座舱 / Feiteng Native Cockpit"
                        color: "#e4f9ff"
                        font.pixelSize: root.headerTitleSize
                        font.bold: true
                        font.family: root.monoFamily
                        wrapMode: Text.WordWrap
                    }

                    Text {
                        text: (uiState["meta"] || {})["subtitle"] || ""
                        color: "#93c6d6"
                        font.pixelSize: root.bodySize
                        font.family: root.monoFamily
                        wrapMode: Text.WordWrap
                    }
                }

                Rectangle {
                    Layout.fillWidth: true
                    implicitHeight: sourceColumn.implicitHeight + (root.cardPadding * 2)
                    radius: root.cardRadius
                    color: "#0a1824"
                    border.color: "#18475a"
                    border.width: 1

                    Column {
                        id: sourceColumn
                        anchors.fill: parent
                        anchors.margins: root.cardPadding
                        spacing: root.compactGap

                        Text {
                            text: "合同来源"
                            color: "#70d9ef"
                            font.pixelSize: root.captionSize
                            font.family: root.monoFamily
                        }

                        Text {
                            text: (uiState["meta"] || {})["snapshot_path"] || ""
                            color: "#d0eef8"
                            wrapMode: Text.WrapAnywhere
                            font.pixelSize: root.captionSize
                            font.family: root.monoFamily
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
                Layout.column: root.wideLayout ? 3 : 0
                Layout.columnSpan: root.wideLayout ? 5 : (root.mediumLayout ? 2 : 1)
                Layout.fillWidth: true
                Layout.fillHeight: root.wideLayout
                Layout.minimumHeight: root.scaled(root.wideLayout ? 440 : 360)
                shellWindow: root
                panelData: zones["center_tactical_view"] || ({})
            }

            StatusPanel {
                Layout.row: root.wideLayout ? 0 : 1
                Layout.column: 0
                Layout.columnSpan: root.wideLayout ? 3 : 1
                Layout.fillWidth: true
                Layout.fillHeight: root.wideLayout
                Layout.minimumHeight: root.scaled(root.wideLayout ? 440 : 260)
                shellWindow: root
                panelData: zones["left_status_panel"] || ({})
            }

            WeakNetworkPanel {
                Layout.row: root.wideLayout ? 0 : (root.mediumLayout ? 1 : 2)
                Layout.column: root.wideLayout ? 8 : (root.mediumLayout ? 1 : 0)
                Layout.columnSpan: root.wideLayout ? 4 : 1
                Layout.fillWidth: true
                Layout.fillHeight: root.wideLayout
                Layout.minimumHeight: root.scaled(root.wideLayout ? 440 : 300)
                shellWindow: root
                panelData: zones["right_weak_network_panel"] || ({})
            }

            ActionStrip {
                Layout.row: root.wideLayout ? 1 : (root.mediumLayout ? 2 : 3)
                Layout.column: 0
                Layout.columnSpan: root.wideLayout ? 12 : (root.mediumLayout ? 2 : 1)
                Layout.fillWidth: true
                shellWindow: root
                panelData: zones["bottom_action_strip"] || ({})
            }
        }
    }
}
