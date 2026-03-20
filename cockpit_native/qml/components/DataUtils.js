.pragma library

function isArray(value) {
    if (Array.isArray && Array.isArray(value))
        return true
    if (value === null || value === undefined)
        return false
    if (typeof value === "string" || typeof value === "function")
        return false
    if (Object.prototype.toString.call(value) === "[object Array]")
        return true
    return typeof value === "object" && typeof value.length === "number" && value.length >= 0
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
