import QtQuick 2.15
import QtQuick.Layouts 1.15
import "DataUtils.js" as DataUtils

Rectangle {
    id: root

    property var shellWindow: null
    property var actionData: ({})
    property bool compact: false

    readonly property var action: DataUtils.objectOrEmpty(actionData)
    readonly property bool interactiveAction: !!action["interactive"]
    readonly property bool readyAction: interactiveAction && !!action["enabled"]
    readonly property string toneValue: String(action["runtime_tone"] || action["tone"] || "neutral")
    readonly property color accentColor: shellWindow ? shellWindow.toneColor(toneValue) : "#86c7d4"
    readonly property bool hovered: actionArea.containsMouse
    readonly property bool pressed: actionArea.pressed
    readonly property string actionId: String(action["action_id"] || "")
    readonly property string statusLabel: readyAction ? "LIVE 就绪" : (interactiveAction ? "受限可点" : "只读")
    readonly property string stateLabel: String(
        action["runtime_state"] || (readyAction ? "LIVE 可执行" : (interactiveAction ? "点击查看限制说明" : "只读合同"))
    )
    readonly property string detailLabel: String(
        action["runtime_detail"] || action["limitation"] || action["note"] || action["cta_label"] || ""
    )
    readonly property string ctaLabel: String(action["cta_label"] || (interactiveAction ? "点击执行" : "只读"))
    readonly property int localPadding: shellWindow ? shellWindow.scaled(compact ? 9 : 10) : (compact ? 9 : 10)
    readonly property int localGap: shellWindow ? shellWindow.scaled(compact ? 3 : 5) : (compact ? 3 : 5)

    radius: shellWindow ? shellWindow.edgeRadius : 12
    color: compact
        ? (interactiveAction
            ? (pressed
                ? Qt.rgba(accentColor.r, accentColor.g, accentColor.b, 0.24)
                : (hovered
                    ? Qt.rgba(accentColor.r, accentColor.g, accentColor.b, 0.18)
                    : Qt.rgba(accentColor.r, accentColor.g, accentColor.b, 0.12)))
            : "#0b1620")
        : (interactiveAction
            ? (pressed ? "#0c2231" : (hovered ? "#123247" : "#10283a"))
            : "#0b1620")
    border.color: Qt.rgba(accentColor.r, accentColor.g, accentColor.b, interactiveAction ? (compact ? 0.58 : 0.72) : 0.28)
    border.width: 1
    implicitHeight: contentColumn.implicitHeight + (localPadding * 2)
    scale: interactiveAction && hovered ? (compact ? 1.008 : 1.01) : 1.0

    Behavior on scale {
        NumberAnimation { duration: 90 }
    }

    Behavior on color {
        ColorAnimation { duration: 120 }
    }

    Behavior on border.color {
        ColorAnimation { duration: 120 }
    }

    Rectangle {
        anchors.fill: parent
        anchors.margins: 1
        radius: parent.radius - 1
        color: "transparent"
        border.color: "#10ffffff"
        border.width: 1
    }

    Rectangle {
        anchors.left: parent.left
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        anchors.margins: shellWindow ? shellWindow.scaled(8) : 8
        width: shellWindow ? shellWindow.scaled(compact ? 2 : 3) : (compact ? 2 : 3)
        radius: width / 2
        color: accentColor
        opacity: interactiveAction ? (compact ? 0.76 : 0.9) : 0.42
    }

    Rectangle {
        visible: compact
        anchors.fill: parent
        anchors.margins: 1
        radius: parent.radius - 1
        gradient: Gradient {
            GradientStop { position: 0.0; color: Qt.rgba(1, 1, 1, hovered ? 0.1 : 0.05) }
            GradientStop { position: 0.18; color: "#00000000" }
            GradientStop { position: 0.72; color: "#00000000" }
            GradientStop { position: 1.0; color: Qt.rgba(0, 0, 0, pressed ? 0.18 : 0.1) }
        }
        opacity: 0.92
    }

    Rectangle {
        visible: compact
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.leftMargin: shellWindow ? shellWindow.scaled(8) : 8
        anchors.rightMargin: shellWindow ? shellWindow.scaled(8) : 8
        anchors.topMargin: shellWindow ? shellWindow.scaled(4) : 4
        height: shellWindow ? shellWindow.scaled(2) : 2
        radius: height / 2
        gradient: Gradient {
            orientation: Gradient.Horizontal
            GradientStop { position: 0.0; color: "transparent" }
            GradientStop { position: 0.18; color: Qt.rgba(accentColor.r, accentColor.g, accentColor.b, 0.08) }
            GradientStop { position: 0.5; color: Qt.rgba(accentColor.r, accentColor.g, accentColor.b, hovered ? 0.8 : 0.6) }
            GradientStop { position: 0.82; color: Qt.rgba(accentColor.r, accentColor.g, accentColor.b, 0.08) }
            GradientStop { position: 1.0; color: "transparent" }
        }
        opacity: 0.92
    }

    Rectangle {
        visible: compact
        width: parent.width * 0.46
        height: parent.height * 0.86
        radius: width / 2
        color: accentColor
        opacity: hovered ? 0.14 : 0.09
        x: -width * 0.14
        y: -height * 0.12
    }

    Rectangle {
        visible: compact
        width: parent.width * 0.38
        height: parent.height * 0.78
        radius: width / 2
        color: "#000000"
        opacity: pressed ? 0.16 : 0.08
        x: parent.width - (width * 0.82)
        y: parent.height - (height * 0.76)
    }

    Rectangle {
        visible: compact
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        anchors.leftMargin: shellWindow ? shellWindow.scaled(8) : 8
        anchors.rightMargin: shellWindow ? shellWindow.scaled(8) : 8
        anchors.bottomMargin: shellWindow ? shellWindow.scaled(4) : 4
        height: shellWindow ? shellWindow.scaled(1) : 1
        radius: height / 2
        color: Qt.rgba(1, 1, 1, pressed ? 0.0 : 0.08)
    }

    Item {
        visible: compact && (hovered || pressed)
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.rightMargin: shellWindow ? shellWindow.scaled(8) : 8
        anchors.topMargin: shellWindow ? shellWindow.scaled(6) : 6
        width: shellWindow ? shellWindow.scaled(14) : 14
        height: width

        Rectangle {
            anchors.right: parent.right
            width: parent.width
            height: shellWindow ? shellWindow.scaled(1) : 1
            color: Qt.rgba(accentColor.r, accentColor.g, accentColor.b, pressed ? 0.78 : 0.52)
        }

        Rectangle {
            anchors.right: parent.right
            width: shellWindow ? shellWindow.scaled(1) : 1
            height: parent.height
            color: Qt.rgba(accentColor.r, accentColor.g, accentColor.b, pressed ? 0.78 : 0.52)
        }
    }

    Item {
        visible: compact && (hovered || pressed)
        anchors.left: parent.left
        anchors.bottom: parent.bottom
        anchors.leftMargin: shellWindow ? shellWindow.scaled(8) : 8
        anchors.bottomMargin: shellWindow ? shellWindow.scaled(6) : 6
        width: shellWindow ? shellWindow.scaled(12) : 12
        height: width

        Rectangle {
            anchors.left: parent.left
            anchors.bottom: parent.bottom
            width: parent.width
            height: shellWindow ? shellWindow.scaled(1) : 1
            color: Qt.rgba(accentColor.r, accentColor.g, accentColor.b, pressed ? 0.74 : 0.44)
        }

        Rectangle {
            anchors.left: parent.left
            anchors.bottom: parent.bottom
            width: shellWindow ? shellWindow.scaled(1) : 1
            height: parent.height
            color: Qt.rgba(accentColor.r, accentColor.g, accentColor.b, pressed ? 0.74 : 0.44)
        }
    }

    MouseArea {
        id: actionArea
        anchors.fill: parent
        enabled: interactiveAction
        hoverEnabled: interactiveAction
        cursorShape: interactiveAction ? Qt.PointingHandCursor : Qt.ArrowCursor
        onClicked: {
            if (shellWindow && shellWindow.invokeOperatorAction && actionId.length > 0)
                shellWindow.invokeOperatorAction(actionId)
        }
    }

    ColumnLayout {
        id: contentColumn
        anchors.fill: parent
        anchors.leftMargin: localPadding + (shellWindow ? shellWindow.scaled(8) : 8)
        anchors.rightMargin: localPadding
        anchors.topMargin: localPadding
        anchors.bottomMargin: localPadding
        spacing: localGap

        RowLayout {
            visible: !compact
            Layout.fillWidth: true
            spacing: shellWindow ? shellWindow.compactGap : 8

            Rectangle {
                radius: shellWindow ? shellWindow.edgeRadius : 10
                color: shellWindow ? shellWindow.toneFill(toneValue) : "#102033"
                border.color: accentColor
                border.width: 1
                implicitWidth: actionIdText.implicitWidth + ((shellWindow ? shellWindow.scaled(10) : 10) * 2)
                implicitHeight: actionIdText.implicitHeight + ((shellWindow ? shellWindow.scaled(5) : 5) * 2)

                Text {
                    id: actionIdText
                    anchors.centerIn: parent
                    text: actionId
                    color: shellWindow ? shellWindow.textPrimary : "#d5eeff"
                    font.pixelSize: shellWindow ? shellWindow.captionSize : 9
                    font.family: shellWindow ? shellWindow.monoFamily : "JetBrains Mono"
                }
            }

            Item {
                Layout.fillWidth: true
            }

            Rectangle {
                radius: height / 2
                color: readyAction ? "#17392c" : (interactiveAction ? "#352614" : "#1b2530")
                border.color: readyAction ? "#42f0bc" : (interactiveAction ? "#ffbf52" : "#35516b")
                border.width: 1
                implicitWidth: statusText.implicitWidth + ((shellWindow ? shellWindow.scaled(10) : 10) * 2)
                implicitHeight: statusText.implicitHeight + ((shellWindow ? shellWindow.scaled(5) : 5) * 2)

                Text {
                    id: statusText
                    anchors.centerIn: parent
                    text: root.statusLabel
                    color: shellWindow ? shellWindow.textStrong : "#f4fbff"
                    font.pixelSize: shellWindow ? shellWindow.captionSize : 10
                    font.family: shellWindow ? shellWindow.uiFamily : "Noto Sans CJK SC"
                }
            }
        }

        Text {
            Layout.fillWidth: true
            text: String(action["label"] || "--")
            color: shellWindow ? shellWindow.textStrong : "#f4fbff"
            font.pixelSize: shellWindow ? shellWindow.bodyEmphasisSize : 14
            font.weight: Font.DemiBold
            font.family: shellWindow ? (compact ? shellWindow.displayFamily : shellWindow.uiFamily) : "Noto Sans CJK SC"
            wrapMode: compact ? Text.NoWrap : Text.WordWrap
            maximumLineCount: compact ? 1 : 2
            elide: Text.ElideRight
        }

        Text {
            Layout.fillWidth: true
            visible: !compact || statusLabel.length > 0
            text: compact ? statusLabel : stateLabel
            color: readyAction
                ? (shellWindow ? shellWindow.accentMint : "#42f0bc")
                : (interactiveAction ? (shellWindow ? shellWindow.accentAmber : "#ffbf52") : (shellWindow ? shellWindow.textMuted : "#6f7f8a"))
            font.pixelSize: shellWindow ? shellWindow.captionSize + 1 : 11
            font.family: shellWindow ? (compact ? shellWindow.monoFamily : shellWindow.uiFamily) : "Noto Sans CJK SC"
            font.weight: Font.DemiBold
            wrapMode: compact ? Text.NoWrap : Text.WordWrap
            maximumLineCount: 1
            elide: Text.ElideRight
        }

        Text {
            Layout.fillWidth: true
            visible: !compact && detailLabel.length > 0
            text: detailLabel
            color: shellWindow ? shellWindow.textSecondary : "#9aa8b1"
            font.pixelSize: shellWindow ? shellWindow.captionSize + 1 : 11
            font.family: shellWindow ? shellWindow.uiFamily : "Noto Sans CJK SC"
            wrapMode: Text.WordWrap
            maximumLineCount: 2
            elide: Text.ElideRight
        }

        Text {
            Layout.fillWidth: true
            visible: !compact
            text: interactiveAction ? ctaLabel : "只读合同镜像"
            color: accentColor
            font.pixelSize: shellWindow ? shellWindow.captionSize : 10
            font.family: shellWindow ? shellWindow.monoFamily : "JetBrains Mono"
            font.letterSpacing: shellWindow ? shellWindow.scaled(0.6) : 0.6
            wrapMode: Text.WrapAnywhere
            elide: Text.ElideRight
        }
    }
}
