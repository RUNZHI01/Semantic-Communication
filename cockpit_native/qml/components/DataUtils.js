.pragma library

function isArray(value) {
    if (Array.isArray)
        return Array.isArray(value)
    return Object.prototype.toString.call(value) === "[object Array]"
}

function isObject(value) {
    return value !== null && typeof value === "object" && !isArray(value)
}

function objectOrEmpty(value) {
    return isObject(value) ? value : ({})
}

function arrayOrEmpty(value) {
    return isArray(value) ? value : []
}

function objectOrFallback(value, fallback) {
    return isObject(value) ? value : objectOrEmpty(fallback)
}
