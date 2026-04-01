/**
 * CountUp animation component for numbers
 * Animates from 0 to target value with easing
 */
import { useState, useEffect, useRef } from 'react'
import { T } from '../../theme/tokens'

interface CountUpProps {
  end: number
  duration?: number
  decimals?: number
  className?: string
  formatValue?: (value: number) => string
}

export function CountUp({
  end,
  duration = T.durationNormal,
  decimals = 0,
  className = '',
  formatValue,
}: CountUpProps) {
  const [current, setCurrent] = useState(0)
  const startTime = useRef<number>()
  const requestRef = useRef<number>()

  useEffect(() => {
    if (end === null || end === undefined || Number.isNaN(end)) {
      setCurrent(0)
      return
    }

    const animate = (timestamp: number) => {
      if (!startTime.current) startTime.current = timestamp
      const progress = timestamp - startTime.current
      const percent = Math.min(progress / duration, 1)

      // Easing: ease-out cubic
      const eased = 1 - Math.pow(1 - percent, 3)

      setCurrent(eased * end)

      if (percent < 1) {
        requestRef.current = requestAnimationFrame(animate)
      }
    }

    requestRef.current = requestAnimationFrame(animate)

    return () => {
      if (requestRef.current) {
        cancelAnimationFrame(requestRef.current)
      }
    }
  }, [end, duration])

  const displayValue = formatValue ? formatValue(current) : current.toFixed(decimals)

  return <span className={className}>{displayValue}</span>
}
