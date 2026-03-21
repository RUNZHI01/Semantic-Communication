import QtQuick 2.15
import QtQuick.Layouts 1.15

Item {
    id: root

    property var shellWindow: null
    property var trackData: []
    property var currentPoint: ({})
    property real headingDeg: 0
    property string backdropMode: "canvas"
    property string backdropSource: ""
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
    property string bannerText: currentDetailText
    property var bannerChips: []

    readonly property int mapInset: shellWindow ? shellWindow.scaled(landingMode ? 16 : 20) : (landingMode ? 16 : 20)
    readonly property int overlayMargin: shellWindow ? shellWindow.scaled(landingMode ? 14 : 16) : (landingMode ? 14 : 16)
    readonly property int bannerPadding: shellWindow ? shellWindow.scaled(landingMode ? 12 : 11) : (landingMode ? 12 : 11)
    readonly property int bannerGap: shellWindow ? shellWindow.scaled(landingMode ? 7 : 6) : (landingMode ? 7 : 6)
    readonly property color oceanTop: landingMode ? "#234c69" : "#17304b"
    readonly property color oceanBottom: landingMode ? "#09131c" : "#050d15"
    readonly property color landFill: landingMode ? "#6f96ae" : "#53758f"
    readonly property color landFillBright: landingMode ? "#99bece" : "#7598ae"
    readonly property color coastlineColor: shellWindow ? Qt.lighter(shellWindow.accentCyan, 1.04) : "#8fe6ff"
    readonly property color gridMinor: shellWindow ? shellWindow.gridLine : "#123147"
    readonly property color gridMajor: shellWindow ? shellWindow.gridLineStrong : "#245b80"
    readonly property color labelColor: shellWindow ? Qt.lighter(shellWindow.textMuted, 1.2) : "#8fa7bb"
    readonly property color mapGlow: shellWindow ? shellWindow.panelGlowStrong : "#78d8ff"
    readonly property color markerColor: shellWindow ? shellWindow.accentCyan : "#8fe6ff"
    readonly property color emphasisColor: shellWindow ? shellWindow.accentAmber : "#ffbf55"
    readonly property color overlayCardColor: landingMode ? "#d70c1721" : "#d90a1320"
    readonly property color overlayCardColorSoft: landingMode ? "#9b07111a" : "#aa081119"
    readonly property bool hasCurrentPoint: isFinite(Number(currentPoint["longitude"])) && isFinite(Number(currentPoint["latitude"]))
    readonly property bool compactStage: width < (shellWindow ? shellWindow.scaled(620) : 620)
    readonly property bool useExternalBackdrop: backdropMode === "asset" && backdropSource.length > 0
    readonly property bool externalBackdropActive: useExternalBackdrop && externalBackdropImage.status === Image.Ready
    readonly property real markerX: hasCurrentPoint ? projectX(Number(currentPoint["longitude"])) : width * 0.5
    readonly property real markerY: hasCurrentPoint ? projectY(Number(currentPoint["latitude"])) : height * 0.5
    readonly property bool leftCallout: markerX > width * 0.64
    readonly property bool showCurrentCallout: hasCurrentPoint && !landingMode
    readonly property real plotWidth: Math.max(1, width - (mapInset * 2))
    readonly property real plotHeight: Math.max(1, height - (mapInset * 2))
    readonly property string anchorDetailText: anchorLabel && anchorLabel !== "--"
        ? "锚点 " + anchorLabel
        : "锚点待命"
    readonly property string currentDetailText: currentDetail && currentDetail.length > 0
        ? currentDetail
        : "世界地图主墙板"
    readonly property string infoRailHeadingText: shellWindow
        ? shellWindow.formattedMetric(headingDeg, 0, "°")
        : (Math.round(headingDeg) + "°")
    readonly property string infoRailPositionText: hasCurrentPoint
        ? (Number(currentPoint["latitude"]).toFixed(2) + "°, " + Number(currentPoint["longitude"]).toFixed(2) + "°")
        : "--"
    readonly property string infoRailAnchorText: anchorLabel && anchorLabel.length > 0 && anchorLabel !== "--"
        ? anchorLabel
        : "待命"
    readonly property bool stackedBanner: width < (shellWindow
        ? shellWindow.scaled(landingMode ? 720 : 980)
        : (landingMode ? 720 : 980))
    readonly property bool dockBannerBottomLeft: landingMode && !stackedBanner
    readonly property real bannerMaxWidth: Math.max(
        shellWindow ? shellWindow.scaled(landingMode ? 280 : 260) : (landingMode ? 280 : 260),
        Math.min(
            width - (overlayMargin * 2),
            shellWindow ? shellWindow.scaled(landingMode ? 360 : 560) : (landingMode ? 360 : 560)
        )
    )
    readonly property real scenarioPlateMaxWidth: Math.max(
        shellWindow ? shellWindow.scaled(landingMode ? 148 : 176) : (landingMode ? 148 : 176),
        Math.min(
            width * (landingMode ? 0.32 : 0.42),
            shellWindow ? shellWindow.scaled(landingMode ? 210 : 250) : (landingMode ? 210 : 250)
        )
    )
    readonly property int topOverlayHeight: Math.max(
        stageLabelPlate.visible ? stageLabelPlate.height : 0,
        scenarioPlate.visible ? scenarioPlate.height : 0
    )
    readonly property real infoRailMaxWidth: Math.max(
        shellWindow ? shellWindow.scaled(260) : 260,
        Math.min(
            width - (overlayMargin * 2),
            shellWindow ? shellWindow.scaled(390) : 390
        )
    )
    readonly property string trackNodeLabel: trackData && trackData.length > 0
        ? String(trackData.length) + " 节点"
        : "等待航迹"
    readonly property var continentPolygons: [
        [
            [-168, 72], [-156, 67], [-149, 60], [-141, 58], [-132, 52], [-124, 48],
            [-122, 40], [-117, 32], [-110, 24], [-102, 20], [-94, 18], [-86, 19],
            [-80, 24], [-79, 31], [-76, 40], [-71, 46], [-63, 52], [-58, 60],
            [-66, 67], [-82, 72], [-102, 76], [-124, 75], [-146, 74]
        ],
        [
            [-56, 82], [-34, 78], [-24, 72], [-28, 64], [-42, 60], [-56, 62],
            [-64, 70], [-60, 78]
        ],
        [
            [-81, 12], [-74, 7], [-69, 0], [-64, -10], [-61, -22], [-60, -34],
            [-64, -47], [-72, -55], [-78, -52], [-80, -38], [-79, -22], [-77, -8]
        ],
        [
            [-11, 36], [-6, 43], [2, 48], [14, 54], [30, 60], [48, 64], [66, 67],
            [88, 69], [110, 70], [128, 67], [144, 61], [158, 56], [170, 47],
            [170, 40], [160, 33], [149, 27], [136, 21], [124, 23], [112, 18],
            [102, 10], [95, 6], [88, 9], [82, 18], [74, 22], [64, 27], [54, 31],
            [44, 31], [34, 37], [26, 44], [16, 46], [8, 44], [0, 40]
        ],
        [
            [67, 24], [77, 28], [87, 22], [83, 10], [76, 7], [70, 12]
        ],
        [
            [95, 8], [106, 5], [116, 0], [124, -5], [128, 2], [122, 12], [112, 15], [100, 13]
        ],
        [
            [128, 31], [139, 35], [145, 42], [141, 46], [132, 42]
        ],
        [
            [-17, 37], [2, 36], [18, 34], [32, 31], [42, 20], [48, 9], [45, -7],
            [40, -22], [33, -34], [20, -35], [10, -25], [2, -10], [-5, 7], [-10, 22]
        ],
        [
            [112, -11], [132, -10], [152, -18], [154, -30], [146, -39], [132, -42],
            [118, -36], [112, -24]
        ],
        [
            [-180, -70], [-150, -74], [-120, -78], [-90, -80], [-60, -82], [-30, -80],
            [0, -79], [30, -80], [60, -82], [90, -80], [120, -78], [150, -75],
            [180, -72], [180, -86], [-180, -86]
        ]
    ]
    readonly property var continentLabels: [
        { "label": "北美", "lon": -108, "lat": 50 },
        { "label": "南美", "lon": -60, "lat": -18 },
        { "label": "欧洲", "lon": 18, "lat": 52 },
        { "label": "非洲", "lon": 18, "lat": 5 },
        { "label": "亚洲", "lon": 94, "lat": 46 },
        { "label": "大洋洲", "lon": 134, "lat": -25 }
    ]
    readonly property var latitudeTicks: [-60, -30, 0, 30, 60]
    readonly property var longitudeTicks: [-120, -60, 0, 60, 120]

    function toneColor(tone) {
        if (shellWindow) {
            if (tone === "warning")
                return shellWindow.accentAmber
            if (tone === "online")
                return shellWindow.accentCyan
            if (tone === "degraded")
                return Qt.lighter(shellWindow.accentAmber, 1.06)
            if (tone === "neutral")
                return shellWindow.accentBlue
            return shellWindow.textSecondary
        }
        if (tone === "warning")
            return "#ffbf55"
        if (tone === "online")
            return "#8fe6ff"
        if (tone === "degraded")
            return "#f7ca72"
        if (tone === "neutral")
            return "#5ab7ff"
        return "#88abc5"
    }

    function toneFill(tone) {
        if (shellWindow) {
            if (tone === "warning" || tone === "degraded")
                return "#251d10"
            if (tone === "online")
                return "#0b2432"
            if (tone === "neutral")
                return "#102033"
            return "#0a1724"
        }
        if (tone === "warning" || tone === "degraded")
            return "#251d10"
        if (tone === "online")
            return "#0b2432"
        if (tone === "neutral")
            return "#102033"
        return "#0a1724"
    }

    function projectX(longitude) {
        return mapInset + ((Number(longitude) + 180) / 360) * plotWidth
    }

    function projectY(latitude) {
        return mapInset + ((90 - Number(latitude)) / 180) * plotHeight
    }

    function drawTrack(ctx) {
        if (!trackData || trackData.length < 1)
            return

        ctx.save()
        ctx.lineJoin = "round"
        ctx.lineCap = "round"
        if (trackData.length > 1) {
            var shadowWidth = landingMode ? 8.4 : 7.2
            var washWidth = landingMode ? 4.8 : 4.2
            var trackWidth = landingMode ? 3.1 : 2.6
            ctx.beginPath()
            for (var index = 0; index < trackData.length; ++index) {
                var point = trackData[index]
                var x = projectX(point["longitude"])
                var y = projectY(point["latitude"])
                if (index === 0)
                    ctx.moveTo(x, y)
                else
                    ctx.lineTo(x, y)
            }
            ctx.strokeStyle = "rgba(4,11,18,0.78)"
            ctx.lineWidth = shadowWidth
            ctx.stroke()

            ctx.strokeStyle = "rgba(255,255,255,0.18)"
            ctx.lineWidth = washWidth
            ctx.stroke()

            ctx.strokeStyle = "rgba(143,230,255,0.94)"
            ctx.lineWidth = trackWidth
            ctx.stroke()

            ctx.beginPath()
            for (var midIndex = 0; midIndex < trackData.length; ++midIndex) {
                var midPoint = trackData[midIndex]
                var mx = projectX(midPoint["longitude"])
                var my = projectY(midPoint["latitude"])
                ctx.moveTo(mx + 3.4, my)
                ctx.arc(mx, my, midIndex === trackData.length - 1 ? (landingMode ? 5.2 : 4.6) : (landingMode ? 3.2 : 2.8), 0, Math.PI * 2)
            }
            ctx.fillStyle = "rgba(143,230,255,0.88)"
            ctx.fill()
        }

        if (hasCurrentPoint) {
            var cx = markerX
            var cy = markerY
            var headingRadians = (headingDeg - 90) * Math.PI / 180

            ctx.beginPath()
            ctx.arc(cx, cy, 22, 0, Math.PI * 2)
            ctx.strokeStyle = "rgba(143,230,255,0.26)"
            ctx.lineWidth = 1.4
            ctx.stroke()

            ctx.beginPath()
            ctx.arc(cx, cy, 56, 0, Math.PI * 2)
            ctx.strokeStyle = "rgba(143,230,255,0.12)"
            ctx.lineWidth = 1.2
            ctx.stroke()

            ctx.beginPath()
            ctx.arc(cx, cy, 38, (-140 * Math.PI) / 180, (40 * Math.PI) / 180)
            ctx.strokeStyle = "rgba(255,191,85,0.34)"
            ctx.lineWidth = 1.2
            ctx.stroke()

            ctx.beginPath()
            ctx.moveTo(cx, cy)
            ctx.lineTo(cx + (Math.cos(headingRadians) * 74), cy + (Math.sin(headingRadians) * 74))
            ctx.strokeStyle = "rgba(255,255,255,0.62)"
            ctx.lineWidth = 1.4
            ctx.stroke()

            ctx.beginPath()
            ctx.arc(cx, cy, 6.5, 0, Math.PI * 2)
            ctx.fillStyle = "rgba(255,255,255,0.92)"
            ctx.fill()
        }
        ctx.restore()
    }

    Image {
        id: externalBackdropImage
        anchors.fill: parent
        anchors.margins: root.mapInset
        visible: root.externalBackdropActive
        source: root.useExternalBackdrop ? root.backdropSource : ""
        fillMode: Image.Stretch
        smooth: true
        asynchronous: true
        mipmap: true
        opacity: root.landingMode ? 0.78 : 0.72
        onStatusChanged: mapCanvas.requestPaint()
    }

    Rectangle {
        anchors.fill: externalBackdropImage
        visible: externalBackdropImage.visible
        color: root.landingMode ? "#50111b27" : "#64091118"
    }

    Canvas {
        id: mapCanvas
        anchors.fill: parent
        antialiasing: true

        function drawPolygon(ctx, polygon, fillColor, strokeColor) {
            if (!polygon || polygon.length < 2)
                return

            ctx.beginPath()
            for (var pointIndex = 0; pointIndex < polygon.length; ++pointIndex) {
                var point = polygon[pointIndex]
                var px = root.projectX(point[0])
                var py = root.projectY(point[1])
                if (pointIndex === 0)
                    ctx.moveTo(px, py)
                else
                    ctx.lineTo(px, py)
            }
            ctx.closePath()
            ctx.fillStyle = fillColor
            ctx.strokeStyle = strokeColor
            ctx.lineWidth = 1.25
            ctx.fill()
            ctx.stroke()
        }

        onPaint: {
            var ctx = getContext("2d")
            var canvasWidth = Math.max(1, root.width)
            var canvasHeight = Math.max(1, root.height)
            ctx.reset()
            ctx.clearRect(0, 0, canvasWidth, canvasHeight)

            var ocean = ctx.createLinearGradient(0, 0, 0, canvasHeight)
            ocean.addColorStop(0.0, root.oceanTop)
            ocean.addColorStop(0.34, root.landingMode ? "#1a3852" : "#11253a")
            ocean.addColorStop(0.62, root.landingMode ? "#10263a" : "#0d1d2d")
            ocean.addColorStop(1.0, root.oceanBottom)
            ctx.fillStyle = ocean
            ctx.fillRect(0, 0, canvasWidth, canvasHeight)

            var beamCenterX = canvasWidth * 0.72
            var beamCenterY = canvasHeight * 0.32
            var beamRadius = Math.max(1, canvasWidth * 0.55)
            var beam = ctx.createRadialGradient(beamCenterX, beamCenterY, 0, beamCenterX, beamCenterY, beamRadius)
            beam.addColorStop(0.0, root.landingMode ? "rgba(120,216,255,0.22)" : "rgba(120,216,255,0.18)")
            beam.addColorStop(0.52, root.landingMode ? "rgba(120,216,255,0.09)" : "rgba(120,216,255,0.07)")
            beam.addColorStop(1.0, "rgba(120,216,255,0.0)")
            ctx.fillStyle = beam
            ctx.fillRect(0, 0, canvasWidth, canvasHeight)

            var hazeCenterX = canvasWidth * 0.22
            var hazeCenterY = canvasHeight * 0.78
            var hazeRadius = Math.max(1, canvasWidth * 0.42)
            var haze = ctx.createRadialGradient(hazeCenterX, hazeCenterY, 0, hazeCenterX, hazeCenterY, hazeRadius)
            haze.addColorStop(0.0, "rgba(240,185,124,0.12)")
            haze.addColorStop(0.5, "rgba(240,185,124,0.04)")
            haze.addColorStop(1.0, "rgba(240,185,124,0.0)")
            ctx.fillStyle = haze
            ctx.fillRect(0, 0, canvasWidth, canvasHeight)

            if (root.hasCurrentPoint) {
                var spotlightRadius = Math.max(1, Math.min(canvasWidth, canvasHeight) * 0.38)
                var spotlight = ctx.createRadialGradient(root.markerX, root.markerY, 0, root.markerX, root.markerY, spotlightRadius)
                spotlight.addColorStop(0.0, "rgba(255,255,255,0.04)")
                spotlight.addColorStop(0.3, "rgba(172,236,255,0.09)")
                spotlight.addColorStop(1.0, "rgba(172,236,255,0.0)")
                ctx.fillStyle = spotlight
                ctx.fillRect(0, 0, canvasWidth, canvasHeight)
            }

            ctx.save()
            ctx.beginPath()
            ctx.rect(root.mapInset, root.mapInset, root.plotWidth, root.plotHeight)
            ctx.clip()

            for (var latitude = -60; latitude <= 60; latitude += 30) {
                var latitudeY = root.projectY(latitude)
                ctx.beginPath()
                ctx.moveTo(root.mapInset, latitudeY)
                ctx.lineTo(width - root.mapInset, latitudeY)
                ctx.strokeStyle = latitude === 0
                    ? (root.landingMode ? "rgba(156,210,255,0.44)" : "rgba(132,191,255,0.36)")
                    : (root.landingMode ? "rgba(78,110,139,0.28)" : "rgba(68,98,126,0.24)")
                ctx.lineWidth = latitude === 0 ? 1.4 : 1.0
                ctx.stroke()
            }

            for (var longitude = -180; longitude <= 180; longitude += 30) {
                var longitudeX = root.projectX(longitude)
                ctx.beginPath()
                ctx.moveTo(longitudeX, root.mapInset)
                ctx.lineTo(longitudeX, height - root.mapInset)
                ctx.strokeStyle = longitude === 0
                    ? (root.landingMode ? "rgba(156,210,255,0.44)" : "rgba(132,191,255,0.36)")
                    : (root.landingMode ? "rgba(40,63,88,0.34)" : "rgba(31,49,69,0.32)")
                ctx.lineWidth = longitude === 0 ? 1.4 : 1.0
                ctx.stroke()
            }

            if (!root.externalBackdropActive) {
                for (var polygonIndex = 0; polygonIndex < root.continentPolygons.length; ++polygonIndex) {
                    var polygon = root.continentPolygons[polygonIndex]
                    var shadowPolygon = root.continentPolygons[polygonIndex]
                    ctx.save()
                    ctx.translate(0, 3)
                    drawPolygon(ctx, shadowPolygon, "rgba(5,13,22,0.36)", "rgba(0,0,0,0)")
                    ctx.restore()

                    var fillColor = polygonIndex % 3 === 0
                        ? root.landFillBright
                        : (polygonIndex % 2 === 0 ? root.landFill : Qt.darker(root.landFill, 1.04))
                    drawPolygon(ctx, polygon, fillColor, Qt.rgba(root.coastlineColor.r, root.coastlineColor.g, root.coastlineColor.b, root.landingMode ? 0.62 : 0.5))
                }
            }

            ctx.beginPath()
            ctx.rect(root.mapInset, root.mapInset, root.plotWidth, root.plotHeight)
            ctx.strokeStyle = root.landingMode ? "rgba(188,233,255,0.34)" : "rgba(172,236,255,0.28)"
            ctx.lineWidth = 1
            ctx.stroke()

            root.drawTrack(ctx)
            ctx.restore()
        }

        onWidthChanged: requestPaint()
        onHeightChanged: requestPaint()
        Component.onCompleted: requestPaint()
    }

    onTrackDataChanged: mapCanvas.requestPaint()
    onCurrentPointChanged: mapCanvas.requestPaint()
    onHeadingDegChanged: mapCanvas.requestPaint()
    onBackdropModeChanged: mapCanvas.requestPaint()
    onBackdropSourceChanged: mapCanvas.requestPaint()
    onWidthChanged: mapCanvas.requestPaint()
    onHeightChanged: mapCanvas.requestPaint()

    Rectangle {
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        height: shellWindow ? shellWindow.scaled(2) : 2
        gradient: Gradient {
            orientation: Gradient.Horizontal
            GradientStop { position: 0.0; color: "transparent" }
            GradientStop { position: 0.22; color: root.mapGlow }
            GradientStop { position: 0.5; color: Qt.lighter(root.mapGlow, 1.1) }
            GradientStop { position: 0.78; color: root.mapGlow }
            GradientStop { position: 1.0; color: "transparent" }
        }
        opacity: 0.62
    }

    Rectangle {
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        height: parent.height * 0.2
        gradient: Gradient {
            GradientStop { position: 0.0; color: "#7a07111c" }
            GradientStop { position: 0.4; color: "#3207111c" }
            GradientStop { position: 1.0; color: "#0007111c" }
        }
    }

    Rectangle {
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        height: parent.height * 0.26
        gradient: Gradient {
            GradientStop { position: 0.0; color: "#0007111c" }
            GradientStop { position: 0.4; color: "#2407111c" }
            GradientStop { position: 1.0; color: "#98061018" }
        }
    }

    Item {
        x: root.mapInset - 1
        y: root.mapInset - 1
        width: shellWindow ? shellWindow.scaled(root.landingMode ? 20 : 18) : (root.landingMode ? 20 : 18)
        height: width

        Rectangle {
            width: parent.width
            height: 1
            color: Qt.rgba(root.mapGlow.r, root.mapGlow.g, root.mapGlow.b, root.landingMode ? 0.82 : 0.62)
        }

        Rectangle {
            width: 1
            height: parent.height
            color: Qt.rgba(root.mapGlow.r, root.mapGlow.g, root.mapGlow.b, root.landingMode ? 0.82 : 0.62)
        }
    }

    Item {
        width: shellWindow ? shellWindow.scaled(root.landingMode ? 20 : 18) : (root.landingMode ? 20 : 18)
        height: width
        x: root.mapInset + root.plotWidth - width + 1
        y: root.mapInset - 1

        Rectangle {
            anchors.right: parent.right
            width: parent.width
            height: 1
            color: Qt.rgba(root.mapGlow.r, root.mapGlow.g, root.mapGlow.b, root.landingMode ? 0.82 : 0.62)
        }

        Rectangle {
            anchors.right: parent.right
            width: 1
            height: parent.height
            color: Qt.rgba(root.mapGlow.r, root.mapGlow.g, root.mapGlow.b, root.landingMode ? 0.82 : 0.62)
        }
    }

    Item {
        width: shellWindow ? shellWindow.scaled(root.landingMode ? 20 : 18) : (root.landingMode ? 20 : 18)
        height: width
        x: root.mapInset - 1
        y: root.mapInset + root.plotHeight - height + 1

        Rectangle {
            anchors.bottom: parent.bottom
            width: parent.width
            height: 1
            color: Qt.rgba(root.mapGlow.r, root.mapGlow.g, root.mapGlow.b, root.landingMode ? 0.82 : 0.62)
        }

        Rectangle {
            anchors.bottom: parent.bottom
            width: 1
            height: parent.height
            color: Qt.rgba(root.mapGlow.r, root.mapGlow.g, root.mapGlow.b, root.landingMode ? 0.82 : 0.62)
        }
    }

    Item {
        width: shellWindow ? shellWindow.scaled(root.landingMode ? 20 : 18) : (root.landingMode ? 20 : 18)
        height: width
        x: root.mapInset + root.plotWidth - width + 1
        y: root.mapInset + root.plotHeight - height + 1

        Rectangle {
            anchors.right: parent.right
            anchors.bottom: parent.bottom
            width: parent.width
            height: 1
            color: Qt.rgba(root.mapGlow.r, root.mapGlow.g, root.mapGlow.b, root.landingMode ? 0.82 : 0.62)
        }

        Rectangle {
            anchors.right: parent.right
            anchors.bottom: parent.bottom
            width: 1
            height: parent.height
            color: Qt.rgba(root.mapGlow.r, root.mapGlow.g, root.mapGlow.b, root.landingMode ? 0.82 : 0.62)
        }
    }

    Repeater {
        model: root.continentLabels

        delegate: Text {
            text: modelData["label"]
            color: root.labelColor
            font.pixelSize: shellWindow ? shellWindow.captionSize + 1 : 11
            font.family: shellWindow ? shellWindow.uiFamily : "Noto Sans CJK SC"
            font.weight: Font.DemiBold
            x: root.projectX(modelData["lon"]) - (width / 2)
            y: root.projectY(modelData["lat"]) - (height / 2)
            opacity: 0.94
        }
    }

    Repeater {
        model: root.latitudeTicks

        delegate: Text {
            text: String(modelData) + "°"
            color: root.labelColor
            font.pixelSize: shellWindow ? shellWindow.captionSize : 10
            font.family: shellWindow ? shellWindow.monoFamily : "JetBrains Mono"
            x: root.mapInset + (shellWindow ? shellWindow.scaled(8) : 8)
            y: root.projectY(modelData) - (height / 2)
            opacity: 0.7
        }
    }

    Repeater {
        model: root.longitudeTicks

        delegate: Text {
            text: (modelData > 0 ? "+" : "") + String(modelData) + "°"
            color: root.labelColor
            font.pixelSize: shellWindow ? shellWindow.captionSize : 10
            font.family: shellWindow ? shellWindow.monoFamily : "JetBrains Mono"
            x: root.projectX(modelData) - (width / 2)
            y: height - root.mapInset + (shellWindow ? shellWindow.scaled(6) : 6)
            opacity: 0.7
        }
    }

    Rectangle {
        id: stageLabelPlate
        visible: true
        anchors.left: parent.left
        anchors.top: parent.top
        anchors.margins: root.overlayMargin
        radius: shellWindow ? shellWindow.edgeRadius : 12
        gradient: Gradient {
            GradientStop { position: 0.0; color: root.overlayCardColor }
            GradientStop { position: 1.0; color: root.overlayCardColorSoft }
        }
        border.color: root.landingMode
            ? Qt.rgba(root.mapGlow.r, root.mapGlow.g, root.mapGlow.b, 0.82)
            : root.mapGlow
        border.width: 1
        implicitWidth: stageLabelColumn.implicitWidth + ((shellWindow ? shellWindow.scaled(12) : 12) * 2)
        implicitHeight: stageLabelColumn.implicitHeight + ((shellWindow ? shellWindow.scaled(9) : 9) * 2)

        Column {
            id: stageLabelColumn
            anchors.centerIn: parent
            spacing: shellWindow ? shellWindow.scaled(2) : 2

            Text {
                text: root.landingMode ? "全球主墙板 / GLOBAL WALLBOARD" : "世界态势地图 / WORLD MAP"
                color: root.mapGlow
                font.pixelSize: shellWindow ? shellWindow.captionSize + 1 : 11
                font.family: shellWindow ? shellWindow.monoFamily : "JetBrains Mono"
                font.letterSpacing: shellWindow ? shellWindow.scaled(1) : 1
                opacity: root.landingMode ? 0.94 : 1.0
            }

            Text {
                text: root.externalBackdropActive
                    ? root.projectionLabel + " / LOCAL ASSET"
                    : root.projectionLabel
                color: shellWindow ? shellWindow.textSecondary : "#88abc5"
                font.pixelSize: shellWindow ? shellWindow.captionSize : 10
                font.family: shellWindow ? shellWindow.uiFamily : "Noto Sans CJK SC"
            }

            Text {
                text: root.trackNodeLabel + "  ·  锚点 " + root.infoRailAnchorText
                color: shellWindow ? shellWindow.textMuted : "#68859d"
                font.pixelSize: shellWindow ? shellWindow.captionSize : 10
                font.family: shellWindow ? shellWindow.uiFamily : "Noto Sans CJK SC"
            }
        }
    }

    Rectangle {
        id: scenarioPlate
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.margins: root.overlayMargin
        width: Math.min(implicitWidth, root.scenarioPlateMaxWidth)
        radius: shellWindow ? shellWindow.edgeRadius : 12
        gradient: Gradient {
            GradientStop { position: 0.0; color: root.overlayCardColor }
            GradientStop { position: 1.0; color: root.overlayCardColorSoft }
        }
        border.color: toneColor(scenarioTone)
        border.width: 1
        implicitWidth: scenarioColumn.implicitWidth + ((shellWindow ? shellWindow.scaled(12) : 12) * 2)
        implicitHeight: scenarioColumn.implicitHeight + ((shellWindow ? shellWindow.scaled(9) : 9) * 2)

        Column {
            id: scenarioColumn
            anchors.fill: parent
            anchors.margins: shellWindow ? shellWindow.scaled(9) : 9
            spacing: shellWindow ? shellWindow.scaled(2) : 2

            Text {
                width: parent.width
                text: root.compactStage
                    ? (root.landingMode ? "场景焦点" : "当前关注")
                    : (root.landingMode ? "场景焦点 / Focus" : "当前关注 / Focus")
                color: shellWindow ? shellWindow.textMuted : "#68859d"
                font.pixelSize: shellWindow ? shellWindow.captionSize : 10
                font.family: shellWindow ? shellWindow.uiFamily : "Noto Sans CJK SC"
                elide: Text.ElideRight
            }

            Text {
                width: parent.width
                text: scenarioLabel && scenarioLabel.length > 0 ? scenarioLabel : "全球链路稳态"
                color: toneColor(scenarioTone)
                font.pixelSize: shellWindow ? shellWindow.bodyEmphasisSize : 14
                font.bold: true
                font.family: shellWindow ? shellWindow.displayFamily : "Noto Sans CJK SC"
                elide: Text.ElideRight
            }

            Text {
                width: parent.width
                text: root.currentDetailText
                color: shellWindow ? shellWindow.textSecondary : "#88abc5"
                font.pixelSize: shellWindow ? shellWindow.captionSize : 10
                font.family: shellWindow ? shellWindow.uiFamily : "Noto Sans CJK SC"
                elide: Text.ElideRight
            }
        }
    }

    Rectangle {
        id: commandBanner
        visible: root.bannerTitle.length > 0 || root.bannerText.length > 0 || root.bannerChips.length > 0
        width: root.bannerMaxWidth
        x: root.dockBannerBottomLeft
            ? root.overlayMargin
            : Math.max(root.overlayMargin, (root.width - width) / 2)
        y: root.dockBannerBottomLeft
            ? root.height - height - root.overlayMargin
            : (root.stackedBanner
                ? root.overlayMargin + root.topOverlayHeight + (shellWindow ? shellWindow.scaled(10) : 10)
                : root.overlayMargin + (shellWindow ? shellWindow.scaled(root.landingMode ? 8 : 6) : (root.landingMode ? 8 : 6)))
        radius: shellWindow ? shellWindow.scaled(root.landingMode ? 14 : 13) : (root.landingMode ? 14 : 13)
        gradient: Gradient {
            GradientStop { position: 0.0; color: root.landingMode ? "#d212202b" : "#d40b1621" }
            GradientStop { position: 0.54; color: root.landingMode ? "#b80a1220" : "#bb09111a" }
            GradientStop { position: 1.0; color: root.landingMode ? "#86081018" : "#8d071018" }
        }
        border.color: root.landingMode ? Qt.lighter(root.mapGlow, 1.06) : Qt.rgba(root.mapGlow.r, root.mapGlow.g, root.mapGlow.b, 0.72)
        border.width: 1

        Rectangle {
            visible: root.landingMode
            width: shellWindow ? shellWindow.scaled(3) : 3
            anchors.left: parent.left
            anchors.top: parent.top
            anchors.bottom: parent.bottom
            anchors.leftMargin: root.bannerPadding
            anchors.topMargin: root.bannerPadding
            anchors.bottomMargin: root.bannerPadding
            radius: width / 2
            gradient: Gradient {
                GradientStop { position: 0.0; color: "transparent" }
                GradientStop { position: 0.24; color: root.mapGlow }
                GradientStop { position: 0.76; color: Qt.lighter(root.mapGlow, 1.12) }
                GradientStop { position: 1.0; color: "transparent" }
            }
            opacity: 0.82
        }

        Rectangle {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            height: shellWindow ? shellWindow.scaled(2) : 2
            radius: height / 2
            gradient: Gradient {
                orientation: Gradient.Horizontal
                GradientStop { position: 0.0; color: "transparent" }
                GradientStop { position: 0.16; color: root.mapGlow }
                GradientStop { position: 0.54; color: Qt.lighter(root.mapGlow, 1.12) }
                GradientStop { position: 0.84; color: root.mapGlow }
                GradientStop { position: 1.0; color: "transparent" }
            }
            opacity: root.landingMode ? 0.92 : 0.76
        }

        Rectangle {
            width: parent.width * 0.32
            height: parent.height * 0.8
            radius: width / 2
            color: root.mapGlow
            opacity: root.landingMode ? 0.05 : 0.04
            x: -width * 0.16
            y: -height * 0.26
        }

        Column {
            id: bannerColumn
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            anchors.leftMargin: root.bannerPadding + (root.landingMode ? (shellWindow ? shellWindow.scaled(10) : 10) : 0)
            anchors.rightMargin: root.bannerPadding
            anchors.topMargin: root.bannerPadding
            anchors.bottomMargin: root.bannerPadding
            spacing: root.bannerGap

            Text {
                width: parent.width
                text: root.bannerEyebrow
                color: root.mapGlow
                font.pixelSize: shellWindow ? shellWindow.captionSize : 10
                font.family: shellWindow ? shellWindow.monoFamily : "JetBrains Mono"
                font.letterSpacing: shellWindow ? shellWindow.scaled(1) : 1
                elide: Text.ElideRight
            }

            Text {
                width: parent.width
                text: root.bannerTitle
                color: shellWindow ? shellWindow.textStrong : "#f5f9ff"
                font.pixelSize: shellWindow
                    ? shellWindow.bodyEmphasisSize + (root.landingMode ? shellWindow.scaled(2) : shellWindow.scaled(2))
                    : (root.landingMode ? 18 : 18)
                font.weight: Font.DemiBold
                font.family: shellWindow ? shellWindow.displayFamily : "Noto Sans CJK SC"
                wrapMode: Text.WordWrap
                maximumLineCount: root.stackedBanner ? 2 : 1
                elide: Text.ElideRight
            }

            Text {
                visible: text.length > 0
                width: parent.width
                text: root.bannerText
                color: shellWindow ? shellWindow.textSecondary : "#8fa9be"
                font.pixelSize: shellWindow ? shellWindow.captionSize + 1 : 12
                font.family: shellWindow ? shellWindow.uiFamily : "Noto Sans CJK SC"
                wrapMode: Text.WordWrap
                maximumLineCount: root.landingMode ? 2 : (root.stackedBanner ? 2 : 1)
                elide: Text.ElideRight
            }

            Flow {
                visible: root.bannerChips.length > 0
                width: parent.width
                spacing: root.bannerGap

                Repeater {
                    model: root.bannerChips

                    delegate: Rectangle {
                        readonly property var chipData: modelData
                        radius: shellWindow ? shellWindow.edgeRadius : 12
                        color: root.toneFill(String(chipData["tone"] || "neutral"))
                        border.color: root.toneColor(String(chipData["tone"] || "neutral"))
                        border.width: 1
                        implicitWidth: bannerChipColumn.implicitWidth + ((shellWindow ? shellWindow.scaled(8) : 8) * 2)
                        implicitHeight: bannerChipColumn.implicitHeight + ((shellWindow ? shellWindow.scaled(5) : 5) * 2)

                        Column {
                            id: bannerChipColumn
                            anchors.centerIn: parent
                            spacing: 1

                            Text {
                                text: chipData["label"]
                                color: shellWindow ? shellWindow.textMuted : "#68859d"
                                font.pixelSize: shellWindow ? shellWindow.captionSize : 10
                                font.family: shellWindow ? shellWindow.monoFamily : "JetBrains Mono"
                            }

                            Text {
                                text: chipData["value"]
                                color: shellWindow ? shellWindow.textStrong : "#f5f9ff"
                                font.pixelSize: shellWindow ? shellWindow.captionSize + 1 : 11
                                font.bold: true
                                font.family: shellWindow ? shellWindow.uiFamily : "Noto Sans CJK SC"
                            }
                        }
                    }
                }
            }
        }
    }

    Rectangle {
        visible: width >= (shellWindow ? shellWindow.scaled(520) : 520)
        width: root.infoRailMaxWidth
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: parent.bottom
        anchors.bottomMargin: root.overlayMargin + (shellWindow ? shellWindow.scaled(10) : 10)
        radius: shellWindow ? shellWindow.edgeRadius : 12
        gradient: Gradient {
            GradientStop { position: 0.0; color: "#d20b1520" }
            GradientStop { position: 0.54; color: "#af09111a" }
            GradientStop { position: 1.0; color: "#82060d15" }
        }
        border.color: Qt.rgba(root.mapGlow.r, root.mapGlow.g, root.mapGlow.b, root.landingMode ? 0.72 : 0.58)
        border.width: 1
        opacity: 0.96

        Rectangle {
            anchors.fill: parent
            anchors.margins: 1
            radius: parent.radius - 1
            color: "transparent"
            border.color: "#0dffffff"
            border.width: 1
        }

        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: shellWindow ? shellWindow.scaled(12) : 12
            anchors.rightMargin: shellWindow ? shellWindow.scaled(12) : 12
            anchors.topMargin: shellWindow ? shellWindow.scaled(8) : 8
            anchors.bottomMargin: shellWindow ? shellWindow.scaled(8) : 8
            spacing: shellWindow ? shellWindow.compactGap : 8

            ColumnLayout {
                Layout.fillWidth: true
                spacing: 1

                Text {
                    text: "TRACK"
                    color: root.mapGlow
                    font.pixelSize: shellWindow ? shellWindow.captionSize : 10
                    font.family: shellWindow ? shellWindow.monoFamily : "JetBrains Mono"
                    font.letterSpacing: shellWindow ? shellWindow.scaled(0.7) : 0.7
                }

                Text {
                    text: root.trackNodeLabel
                    color: shellWindow ? shellWindow.textStrong : "#f5f9ff"
                    font.pixelSize: shellWindow ? shellWindow.bodyEmphasisSize : 14
                    font.weight: Font.DemiBold
                    font.family: shellWindow ? shellWindow.displayFamily : "Noto Serif CJK SC"
                }
            }

            Rectangle {
                width: 1
                Layout.fillHeight: true
                color: "#14ffffff"
            }

            ColumnLayout {
                Layout.fillWidth: true
                spacing: 1

                Text {
                    text: "ANCHOR"
                    color: root.mapGlow
                    font.pixelSize: shellWindow ? shellWindow.captionSize : 10
                    font.family: shellWindow ? shellWindow.monoFamily : "JetBrains Mono"
                    font.letterSpacing: shellWindow ? shellWindow.scaled(0.7) : 0.7
                }

                Text {
                    text: root.infoRailAnchorText
                    color: shellWindow ? shellWindow.textStrong : "#f5f9ff"
                    font.pixelSize: shellWindow ? shellWindow.bodyEmphasisSize : 14
                    font.weight: Font.DemiBold
                    font.family: shellWindow ? shellWindow.uiFamily : "Noto Sans CJK SC"
                    elide: Text.ElideRight
                }
            }

            Rectangle {
                width: 1
                Layout.fillHeight: true
                color: "#14ffffff"
            }

            ColumnLayout {
                Layout.fillWidth: true
                spacing: 1

                Text {
                    text: "HEADING / FIX"
                    color: root.mapGlow
                    font.pixelSize: shellWindow ? shellWindow.captionSize : 10
                    font.family: shellWindow ? shellWindow.monoFamily : "JetBrains Mono"
                    font.letterSpacing: shellWindow ? shellWindow.scaled(0.7) : 0.7
                }

                Text {
                    text: root.infoRailHeadingText + "  ·  " + root.infoRailPositionText
                    color: shellWindow ? shellWindow.textStrong : "#f5f9ff"
                    font.pixelSize: shellWindow ? shellWindow.captionSize + 1 : 11
                    font.weight: Font.DemiBold
                    font.family: shellWindow ? shellWindow.uiFamily : "Noto Sans CJK SC"
                    elide: Text.ElideRight
                }
            }
        }
    }

    Item {
        visible: root.hasCurrentPoint
        x: root.markerX - (width / 2)
        y: root.markerY - (height / 2)
        width: shellWindow ? shellWindow.scaled(38) : 38
        height: width

        Rectangle {
            anchors.centerIn: parent
            width: parent.width * 1.85
            height: width
            radius: width / 2
            color: root.markerColor
            opacity: 0.12

            SequentialAnimation on scale {
                loops: Animation.Infinite
                NumberAnimation { from: 0.78; to: 1.18; duration: 1600 }
                NumberAnimation { from: 1.18; to: 0.78; duration: 1600 }
            }
        }

        Item {
            anchors.fill: parent
            rotation: root.headingDeg
            transformOrigin: Item.Center

            Rectangle {
                width: parent.width * 0.16
                height: parent.height * 0.8
                radius: width / 2
                color: root.markerColor
                border.color: "#ffffff"
                border.width: 1
                anchors.centerIn: parent
            }

            Rectangle {
                width: parent.width * 0.82
                height: parent.height * 0.14
                radius: height / 2
                color: root.markerColor
                border.color: "#ffffff"
                border.width: 1
                anchors.centerIn: parent
            }

            Rectangle {
                width: parent.width * 0.26
                height: parent.height * 0.2
                rotation: 45
                radius: height / 2
                color: root.emphasisColor
                anchors.horizontalCenter: parent.horizontalCenter
                anchors.top: parent.top
                anchors.topMargin: shellWindow ? shellWindow.scaled(1) : 1
            }
        }
    }

    Rectangle {
        visible: root.showCurrentCallout
        readonly property real preferredY: Math.max(
            shellWindow ? shellWindow.scaled(68) : 68,
            Math.min(
                root.height - implicitHeight - (shellWindow ? shellWindow.scaled(24) : 24),
                root.markerY - (implicitHeight / 2)
            )
        )
        x: root.leftCallout
            ? Math.max(shellWindow ? shellWindow.scaled(16) : 16, root.markerX - width - (shellWindow ? shellWindow.scaled(22) : 22))
            : Math.min(root.width - width - (shellWindow ? shellWindow.scaled(16) : 16), root.markerX + (shellWindow ? shellWindow.scaled(22) : 22))
        y: preferredY
        radius: shellWindow ? shellWindow.edgeRadius : 12
        gradient: Gradient {
            GradientStop { position: 0.0; color: root.overlayCardColor }
            GradientStop { position: 1.0; color: root.overlayCardColorSoft }
        }
        border.color: root.markerColor
        border.width: 1
        implicitWidth: currentCalloutColumn.implicitWidth + ((shellWindow ? shellWindow.scaled(16) : 16) * 2)
        implicitHeight: currentCalloutColumn.implicitHeight + ((shellWindow ? shellWindow.scaled(12) : 12) * 2)

        Rectangle {
            y: (parent.height / 2) - 1
            x: root.leftCallout ? parent.width : -((shellWindow ? shellWindow.scaled(18) : 18))
            width: shellWindow ? shellWindow.scaled(18) : 18
            height: 2
            color: root.markerColor
            opacity: 0.8
        }

        Column {
            id: currentCalloutColumn
            anchors.centerIn: parent
            spacing: shellWindow ? shellWindow.scaled(2) : 2

            Text {
                text: root.currentLabel
                color: root.markerColor
                font.pixelSize: shellWindow ? shellWindow.captionSize : 10
                font.family: shellWindow ? shellWindow.monoFamily : "JetBrains Mono"
                font.letterSpacing: shellWindow ? shellWindow.scaled(1) : 1
            }

            Text {
                text: root.currentDetailText
                color: shellWindow ? shellWindow.textStrong : "#f1f7ff"
                font.pixelSize: shellWindow ? shellWindow.bodyEmphasisSize : 14
                font.bold: true
                font.family: shellWindow ? shellWindow.displayFamily : "Noto Sans CJK SC"
            }

            Text {
                text: root.anchorDetailText
                color: shellWindow ? shellWindow.textSecondary : "#88abc5"
                font.pixelSize: shellWindow ? shellWindow.captionSize : 10
                font.family: shellWindow ? shellWindow.uiFamily : "Noto Sans CJK SC"
            }
        }
    }
}
