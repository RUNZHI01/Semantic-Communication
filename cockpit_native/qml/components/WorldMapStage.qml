import QtQuick 2.15

Item {
    id: root

    property var shellWindow: null
    property var trackData: []
    property var currentPoint: ({})
    property real headingDeg: 0
    property string currentLabel: "实时航迹"
    property string currentDetail: ""
    property string anchorLabel: "--"
    property string projectionLabel: "经纬投影 / EQUIRECTANGULAR"
    property string scenarioLabel: ""
    property string scenarioTone: "neutral"
    property bool landingMode: false
    property string bannerEyebrow: landingMode ? "全球指挥主舞台 / GLOBAL COMMAND STAGE" : "实时指挥舞台 / LIVE COMMAND STAGE"
    property string bannerTitle: currentLabel && currentLabel.length > 0
        ? currentLabel
        : (landingMode ? "世界主墙板" : "实时航迹")
    property string bannerText: currentDetail && currentDetail.length > 0
        ? currentDetail
        : "世界地图主墙板"
    property var bannerChips: []

    readonly property var launchOptions: shellWindow && shellWindow.options ? shellWindow.options : ({})
    readonly property string requestedMapBackend: normalizeBackend(String(launchOptions["mapBackend"] || "auto"))
    readonly property string worldMapBackdropSource: String(launchOptions["worldMapBackdropSource"] || "")
    readonly property bool localBackdropReady: worldMapBackdropSource.length > 0
    readonly property string activeMapBackend: useSvgBackdrop() ? "svg" : "canvas"

    function normalizeBackend(value) {
        if (value === "canvas" || value === "svg" || value === "qtlocation")
            return value
        return "auto"
    }

    function useSvgBackdrop() {
        if (!localBackdropReady)
            return false
        return requestedMapBackend === "auto" || requestedMapBackend === "svg"
    }

    // Centralize backend selection here so future SVG or QtLocation transplants
    // do not require edits across every cockpit page that embeds the map stage.
    WorldMapStageCanvas {
        anchors.fill: parent
        shellWindow: root.shellWindow
        trackData: root.trackData
        currentPoint: root.currentPoint
        headingDeg: root.headingDeg
        backdropMode: root.activeMapBackend === "svg" ? "asset" : "canvas"
        backdropSource: root.activeMapBackend === "svg" ? root.worldMapBackdropSource : ""
        currentLabel: root.currentLabel
        currentDetail: root.currentDetail
        anchorLabel: root.anchorLabel
        projectionLabel: root.projectionLabel
        scenarioLabel: root.scenarioLabel
        scenarioTone: root.scenarioTone
        landingMode: root.landingMode
        bannerEyebrow: root.bannerEyebrow
        bannerTitle: root.bannerTitle
        bannerText: root.bannerText
        bannerChips: root.bannerChips
    }
}
