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

    readonly property int mapInset: shellWindow ? shellWindow.scaled(24) : 24
    readonly property color oceanTop: "#113a5c"
    readonly property color oceanBottom: "#06111a"
    readonly property color landFill: "#1a4a67"
    readonly property color landFillBright: "#285f82"
    readonly property color coastlineColor: shellWindow ? Qt.lighter(shellWindow.accentCyan, 1.04) : "#8fe6ff"
    readonly property color gridMinor: shellWindow ? shellWindow.gridLine : "#123147"
    readonly property color gridMajor: shellWindow ? shellWindow.gridLineStrong : "#245b80"
    readonly property color labelColor: shellWindow ? shellWindow.textMuted : "#68859d"
    readonly property color mapGlow: shellWindow ? shellWindow.panelGlowStrong : "#78d8ff"
    readonly property color markerColor: shellWindow ? shellWindow.accentCyan : "#8fe6ff"
    readonly property color emphasisColor: shellWindow ? shellWindow.accentAmber : "#ffbf55"
    readonly property bool hasCurrentPoint: isFinite(Number(currentPoint["longitude"])) && isFinite(Number(currentPoint["latitude"]))
    readonly property real markerX: hasCurrentPoint ? projectX(Number(currentPoint["longitude"])) : width * 0.5
    readonly property real markerY: hasCurrentPoint ? projectY(Number(currentPoint["latitude"])) : height * 0.5
    readonly property bool leftCallout: markerX > width * 0.64
    readonly property real plotWidth: Math.max(1, width - (mapInset * 2))
    readonly property real plotHeight: Math.max(1, height - (mapInset * 2))
    readonly property string anchorDetailText: anchorLabel && anchorLabel !== "--"
        ? "锚点 " + anchorLabel
        : "锚点待命"
    readonly property string currentDetailText: currentDetail && currentDetail.length > 0
        ? currentDetail
        : "世界地图主舞台"
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
            ctx.strokeStyle = "rgba(143,230,255,0.92)"
            ctx.lineWidth = 2.4
            ctx.stroke()

            ctx.beginPath()
            for (var midIndex = 0; midIndex < trackData.length; ++midIndex) {
                var midPoint = trackData[midIndex]
                var mx = projectX(midPoint["longitude"])
                var my = projectY(midPoint["latitude"])
                ctx.moveTo(mx + 3.4, my)
                ctx.arc(mx, my, midIndex === trackData.length - 1 ? 4.6 : 2.8, 0, Math.PI * 2)
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
        }
        ctx.restore()
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
            ctx.lineWidth = 1.15
            ctx.fill()
            ctx.stroke()
        }

        onPaint: {
            var ctx = getContext("2d")
            ctx.reset()
            ctx.clearRect(0, 0, width, height)

            var ocean = ctx.createLinearGradient(0, 0, 0, height)
            ocean.addColorStop(0.0, root.oceanTop)
            ocean.addColorStop(0.58, "#0a1f31")
            ocean.addColorStop(1.0, root.oceanBottom)
            ctx.fillStyle = ocean
            ctx.fillRect(0, 0, width, height)

            var beam = ctx.createRadialGradient(width * 0.72, height * 0.32, 0, width * 0.72, height * 0.32, width * 0.55)
            beam.addColorStop(0.0, "rgba(120,216,255,0.17)")
            beam.addColorStop(0.52, "rgba(120,216,255,0.06)")
            beam.addColorStop(1.0, "rgba(120,216,255,0.0)")
            ctx.fillStyle = beam
            ctx.fillRect(0, 0, width, height)

            ctx.save()
            ctx.beginPath()
            ctx.rect(root.mapInset, root.mapInset, root.plotWidth, root.plotHeight)
            ctx.clip()

            for (var latitude = -60; latitude <= 60; latitude += 30) {
                var latitudeY = root.projectY(latitude)
                ctx.beginPath()
                ctx.moveTo(root.mapInset, latitudeY)
                ctx.lineTo(width - root.mapInset, latitudeY)
                ctx.strokeStyle = latitude === 0 ? "rgba(111,191,255,0.34)" : "rgba(36,91,128,0.28)"
                ctx.lineWidth = latitude === 0 ? 1.4 : 1.0
                ctx.stroke()
            }

            for (var longitude = -180; longitude <= 180; longitude += 30) {
                var longitudeX = root.projectX(longitude)
                ctx.beginPath()
                ctx.moveTo(longitudeX, root.mapInset)
                ctx.lineTo(longitudeX, height - root.mapInset)
                ctx.strokeStyle = longitude === 0 ? "rgba(111,191,255,0.34)" : "rgba(18,49,71,0.38)"
                ctx.lineWidth = longitude === 0 ? 1.4 : 1.0
                ctx.stroke()
            }

            for (var polygonIndex = 0; polygonIndex < root.continentPolygons.length; ++polygonIndex) {
                var polygon = root.continentPolygons[polygonIndex]
                var shadowPolygon = root.continentPolygons[polygonIndex]
                ctx.save()
                ctx.translate(0, 3)
                drawPolygon(ctx, shadowPolygon, "rgba(5,13,22,0.42)", "rgba(0,0,0,0)")
                ctx.restore()

                var fillColor = polygonIndex % 2 === 0 ? root.landFill : root.landFillBright
                drawPolygon(ctx, polygon, fillColor, "rgba(143,230,255,0.46)")
            }

            ctx.beginPath()
            ctx.rect(root.mapInset, root.mapInset, root.plotWidth, root.plotHeight)
            ctx.strokeStyle = "rgba(143,230,255,0.32)"
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

    Repeater {
        model: root.continentLabels

        delegate: Text {
            text: modelData["label"]
            color: root.labelColor
            font.pixelSize: shellWindow ? shellWindow.captionSize : 10
            font.family: shellWindow ? shellWindow.uiFamily : "Ubuntu Sans"
            font.weight: Font.DemiBold
            x: root.projectX(modelData["lon"]) - (width / 2)
            y: root.projectY(modelData["lat"]) - (height / 2)
            opacity: 0.9
        }
    }

    Repeater {
        model: root.latitudeTicks

        delegate: Text {
            text: String(modelData) + "°"
            color: root.labelColor
            font.pixelSize: shellWindow ? shellWindow.captionSize : 10
            font.family: shellWindow ? shellWindow.monoFamily : "Ubuntu Sans Mono"
            x: root.mapInset + (shellWindow ? shellWindow.scaled(8) : 8)
            y: root.projectY(modelData) - (height / 2)
            opacity: 0.76
        }
    }

    Repeater {
        model: root.longitudeTicks

        delegate: Text {
            text: (modelData > 0 ? "+" : "") + String(modelData) + "°"
            color: root.labelColor
            font.pixelSize: shellWindow ? shellWindow.captionSize : 10
            font.family: shellWindow ? shellWindow.monoFamily : "Ubuntu Sans Mono"
            x: root.projectX(modelData) - (width / 2)
            y: height - root.mapInset + (shellWindow ? shellWindow.scaled(6) : 6)
            opacity: 0.76
        }
    }

    Rectangle {
        anchors.left: parent.left
        anchors.top: parent.top
        anchors.margins: shellWindow ? shellWindow.scaled(16) : 16
        radius: shellWindow ? shellWindow.edgeRadius : 12
        color: "#071522d6"
        border.color: "#578fe6ff"
        border.width: 1
        implicitWidth: stageLabelColumn.implicitWidth + ((shellWindow ? shellWindow.scaled(14) : 14) * 2)
        implicitHeight: stageLabelColumn.implicitHeight + ((shellWindow ? shellWindow.scaled(10) : 10) * 2)

        Column {
            id: stageLabelColumn
            anchors.centerIn: parent
            spacing: shellWindow ? shellWindow.scaled(2) : 2

            Text {
                text: "世界态势地图 / WORLD MAP"
                color: root.mapGlow
                font.pixelSize: shellWindow ? shellWindow.captionSize : 10
                font.family: shellWindow ? shellWindow.monoFamily : "Ubuntu Sans Mono"
                font.letterSpacing: shellWindow ? shellWindow.scaled(1) : 1
            }

            Text {
                text: root.projectionLabel
                color: shellWindow ? shellWindow.textSecondary : "#88abc5"
                font.pixelSize: shellWindow ? shellWindow.captionSize : 10
                font.family: shellWindow ? shellWindow.uiFamily : "Ubuntu Sans"
            }
        }
    }

    Rectangle {
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.margins: shellWindow ? shellWindow.scaled(16) : 16
        radius: shellWindow ? shellWindow.edgeRadius : 12
        color: "#071522d6"
        border.color: toneColor(scenarioTone)
        border.width: 1
        implicitWidth: scenarioColumn.implicitWidth + ((shellWindow ? shellWindow.scaled(14) : 14) * 2)
        implicitHeight: scenarioColumn.implicitHeight + ((shellWindow ? shellWindow.scaled(10) : 10) * 2)

        Column {
            id: scenarioColumn
            anchors.centerIn: parent
            spacing: shellWindow ? shellWindow.scaled(2) : 2

            Text {
                text: "主舞台关注"
                color: shellWindow ? shellWindow.textMuted : "#68859d"
                font.pixelSize: shellWindow ? shellWindow.captionSize : 10
                font.family: shellWindow ? shellWindow.uiFamily : "Ubuntu Sans"
            }

            Text {
                text: scenarioLabel && scenarioLabel.length > 0 ? scenarioLabel : "全球链路稳态"
                color: toneColor(scenarioTone)
                font.pixelSize: shellWindow ? shellWindow.bodyEmphasisSize : 14
                font.bold: true
                font.family: shellWindow ? shellWindow.displayFamily : "Ubuntu Sans"
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
        visible: root.hasCurrentPoint
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
        color: "#071522e6"
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
                font.family: shellWindow ? shellWindow.monoFamily : "Ubuntu Sans Mono"
                font.letterSpacing: shellWindow ? shellWindow.scaled(1) : 1
            }

            Text {
                text: root.currentDetailText
                color: shellWindow ? shellWindow.textStrong : "#f1f7ff"
                font.pixelSize: shellWindow ? shellWindow.bodyEmphasisSize : 14
                font.bold: true
                font.family: shellWindow ? shellWindow.displayFamily : "Ubuntu Sans"
            }

            Text {
                text: root.anchorDetailText
                color: shellWindow ? shellWindow.textSecondary : "#88abc5"
                font.pixelSize: shellWindow ? shellWindow.captionSize : 10
                font.family: shellWindow ? shellWindow.uiFamily : "Ubuntu Sans"
            }
        }
    }
}
