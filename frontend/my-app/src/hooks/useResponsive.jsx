

// src/hooks/useResponsive.js
import { useState, useEffect } from 'react'

// Tailwind CSS breakpoints
const breakpoints = {
  sm: 640,
  md: 768,
  lg: 1024,
  xl: 1280,
  '2xl': 1536,
}

export function useResponsive() {
  const [screenSize, setScreenSize] = useState({
    width: typeof window !== 'undefined' ? window.innerWidth : 0,
    height: typeof window !== 'undefined' ? window.innerHeight : 0,
  })

  useEffect(() => {
    const handleResize = () => {
      setScreenSize({
        width: window.innerWidth,
        height: window.innerHeight,
      })
    }

    window.addEventListener('resize', handleResize)
    
    // Set initial size
    handleResize()

    return () => window.removeEventListener('resize', handleResize)
  }, [])

  const isMobile = screenSize.width < breakpoints.md
  const isTablet = screenSize.width >= breakpoints.md && screenSize.width < breakpoints.lg
  const isDesktop = screenSize.width >= breakpoints.lg

  return {
    ...screenSize,
    isMobile,
    isTablet,
    isDesktop,
    breakpoints,
  }
}

export function useBreakpoint(breakpoint) {
  const { width } = useResponsive()
  return width >= breakpoints[breakpoint]
}

export function useMediaQuery(query) {
  const [matches, setMatches] = useState(false)

  useEffect(() => {
    const media = window.matchMedia(query)
    if (media.matches !== matches) {
      setMatches(media.matches)
    }
    
    const listener = () => setMatches(media.matches)
    media.addEventListener('change', listener)
    
    return () => media.removeEventListener('change', listener)
  }, [matches, query])

  return matches
}