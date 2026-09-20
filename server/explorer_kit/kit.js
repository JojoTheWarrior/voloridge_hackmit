/* Kingdom explorer kit: optional helpers. Loads Leaflet on demand; exposes one global, `Kingdom`.
   Load it in <head> (it is tiny) so the theme is set before the first paint.
   Everything here is a convenience: read it, use what helps, replace what does not. */
(function () {
  'use strict'

  // Leaflet draws with <img> tiles and a 2D canvas. WebGL map libraries need web workers, which do not survive the sandboxed frame.
  const LEAFLET = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet'
  const LEAFLET_HASH = { css: 'sha256-p4NxAoJBhIIN+hmNHrzRCf9tD/miZyoHS5obTRR9BMY=', js: 'sha256-20nQCchB9co0qIjJZRGuk2/Z9VM+kNiyxNV1lvTlZBo=' }
  // Esri's raster tiles, all free and keyless: the gray canvas (base and place names apart, light and dark) and World Imagery.
  const ESRI = 'https://server.arcgisonline.com/ArcGIS/rest/services/{service}/MapServer/tile/{z}/{y}/{x}'
  const ESRI_LINK = '<a href="https://www.esri.com">Esri</a>'
  const BASEMAP_CREDIT = `© ${ESRI_LINK}, HERE, Garmin, © <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors`
  const IMAGERY_CREDIT = `Imagery © ${ESRI_LINK}, Maxar, Earthstar Geographics, and the GIS User Community`

  /* ---- Theme ------------------------------------------------------------------------------
     ?theme=light|dark wins, then the host page's postMessage, then the system preference. */
  const themeListeners = new Set()
  const systemDark = matchMedia('(prefers-color-scheme: dark)')
  const requested = new URLSearchParams(location.search).get('theme')
  let followSystem = requested !== 'light' && requested !== 'dark'

  const theme = {
    current: 'light',
    set(next) {
      if (next !== 'light' && next !== 'dark') return
      theme.current = next
      document.documentElement.dataset.theme = next
      themeListeners.forEach((listener) => listener(next))
    },
    /** Calls `listener(theme)` on every change; returns a function that unsubscribes. */
    onChange(listener) {
      themeListeners.add(listener)
      return () => themeListeners.delete(listener)
    },
    /** The current value of a design token, e.g. token('ink') → '#0a0a0a'. For canvas and map paint. */
    token: (name) => getComputedStyle(document.documentElement).getPropertyValue(`--color-${name}`).trim(),
  }
  theme.set(followSystem ? (systemDark.matches ? 'dark' : 'light') : requested)
  systemDark.addEventListener('change', (event) => followSystem && theme.set(event.matches ? 'dark' : 'light'))
  // The frame has an opaque origin, so the sender cannot be checked; the only thing a message can do is pick a theme.
  addEventListener('message', (event) => {
    if (!event.data || event.data.type !== 'kingdom:theme') return
    followSystem = false
    theme.set(event.data.theme)
  })

  // The explorer lives in a frame, so a link that leaves it must open a new tab. This covers map attributions too.
  addEventListener('click', (event) => {
    const link = event.target.closest?.('a[href]')
    if (link && link.host !== location.host) Object.assign(link, { target: '_blank', rel: 'noopener' })
  }, true)

  /* ---- DOM --------------------------------------------------------------------------------
     el('div', { class: 'k-card', onclick: fn }, 'text', child, …). Text goes in as text nodes,
     so data can never inject markup. Prefer this to innerHTML. */
  function el(tag, props, ...children) {
    const node = document.createElement(tag)
    for (const [key, value] of Object.entries(props || {})) {
      if (value == null || value === false) continue
      if (key.startsWith('on')) node.addEventListener(key.slice(2), value)
      else node.setAttribute(key, value === true ? '' : value)
    }
    node.append(...children.flat().filter((child) => child != null && child !== false))
    return node
  }

  /** Replaces `target`'s content with an empty, loading or error state. `action` is an optional element, usually one .k-btn. */
  function state(target, { kind = 'empty', title, text, action } = {}) {
    const busy = kind === 'loading'
    target.replaceChildren(
      el('div', { class: 'k-state k-fade-in', role: kind === 'error' ? 'alert' : 'status' },
        busy && el('div', { class: 'k-spinner' }), title && el('h2', null, title), text && el('p', null, text), action),
    )
  }

  /** Fetches a JSON file that sits next to index.html. On failure shows an error state in `target` (if given) and rethrows. */
  async function loadData(path, { target } = {}) {
    try {
      const response = await fetch(path)
      if (!response.ok) throw new Error(`${path}: HTTP ${response.status}`)
      return await response.json()
    } catch (error) {
      if (target) state(target, { kind: 'error', title: 'The data did not load', text: `${path} could not be read. Reload to try again.` })
      throw error
    }
  }

  /** An evidence frame: fades the image in, and says so when it cannot load. */
  function evidence(src, alt, caption) {
    const frame = el('div')
    const image = el('img', { src, alt, onload: () => image.classList.add('k-loaded'), onerror: () => frame.replaceChildren('Image unavailable') })
    frame.append(image)
    return el('figure', { class: 'k-evidence' }, frame, caption && el('figcaption', null, caption))
  }

  /** Renders ranked rows into an <ol class="k-list">. `title`, `sub` and `value` map an item to text.
      Keeps keyboard focus on the same row across re-renders; arrow keys move between rows. */
  function rankedList(list, items, { title, sub, value, selectedId, onSelect }) {
    const active = document.activeElement
    const focusedId = active && list.contains(active) ? active.dataset.id : null
    list.replaceChildren(...items.map((item, index) =>
      el('li', null,
        el('button', { type: 'button', class: 'k-rank', 'data-id': item.id, 'aria-current': String(item.id) === String(selectedId) ? 'true' : null, onclick: () => onSelect(item) },
          el('span', null, String(index + 1)),
          el('span', null, title(item), sub && el('small', null, sub(item))),
          el('span', null, value(item))))))
    if (focusedId != null) list.querySelector(`[data-id="${CSS.escape(focusedId)}"]`)?.focus()
    list.onkeydown = (event) => {
      const step = { ArrowDown: 'nextElementSibling', ArrowUp: 'previousElementSibling' }[event.key]
      const row = step && event.target.closest('li')?.[step]
      if (row) { event.preventDefault(); row.firstElementChild.focus() }
    }
  }

  // Sliders and meters fill with ink up to --k-pos.
  const syncRange = (input) => input.style.setProperty('--k-pos', `${((input.value - input.min) / (input.max - input.min || 1)) * 100}%`)
  addEventListener('input', (event) => event.target.matches?.('.k-range') && syncRange(event.target))
  addEventListener('DOMContentLoaded', () => document.querySelectorAll('.k-range').forEach(syncRange))

  /* ---- Formatters ------------------------------------------------------------------------- */
  const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
  const fmt = {
    /** 0.873 → "87%"; pct(0.873, 1) → "87.3%" */
    pct: (share, digits = 0) => (Number.isFinite(share) ? `${(share * 100).toFixed(digits)}%` : '—'),
    /** 12840.5 → "12,841"; a true minus sign so negatives align in mono. */
    num: (value, digits = 0) => (Number.isFinite(value) ? value.toLocaleString('en-US', { minimumFractionDigits: digits, maximumFractionDigits: digits }).replace('-', '−') : '—'),
    /** "2026-09-20" → "20 Sep 2026". A bare date is read as local, so it never slips a day. */
    date(value) {
      const date = new Date(/^\d{4}-\d{2}-\d{2}$/.test(value) ? `${value}T00:00` : value)
      return Number.isNaN(date.getTime()) ? '—' : `${date.getDate()} ${MONTHS[date.getMonth()]} ${date.getFullYear()}`
    },
  }

  /* ---- Map --------------------------------------------------------------------------------
     A Leaflet map with a gray basemap that follows the theme (Esri's light or dark gray canvas, place names
     drawn above the marks) and Esri World Imagery as the 'satellite' basemap. Neither needs a key. */
  let leafletLoading
  function loadLeaflet() {
    const load = (node, place) => new Promise((resolve, reject) => {
      Object.assign(node, { crossOrigin: '', onload: resolve, onerror: () => reject(new Error('Leaflet did not load')) })
      document.head[place](node)
    })
    // The stylesheet goes first in <head>, so kit.css comes after it and its restyling of Leaflet's chrome wins.
    leafletLoading ??= Promise.all([
      load(el('link', { rel: 'stylesheet', href: `${LEAFLET}.css`, integrity: LEAFLET_HASH.css }), 'prepend'),
      load(el('script', { src: `${LEAFLET}.js`, integrity: LEAFLET_HASH.js }), 'append'),
    ]).then(() => window.L)
    return leafletLoading
  }

  const rgba = (hex, alpha) => `rgba(${[1, 3, 5].map((at) => parseInt(hex.slice(at, at + 2), 16)).join(',')},${alpha})`
  const latLng = (item) => [item.lat, item.lon ?? item.lng]
  const accessor = (score) => (typeof score === 'function' ? score : (item) => Number(item[score]) || 0)

  /** Resolves to a small wrapper; `wrapper.leaflet` is the real Leaflet map for anything not covered here.
      opts: { center: [lon, lat], zoom, basemap: 'map' | 'satellite', ...any Leaflet map option }
      Items carry `lat` and `lon`. Raw Leaflet calls take [lat, lon], the other way round from `center`. */
  async function map(container, { basemap = 'map', center = [0, 20], zoom = 2, ...options } = {}) {
    let lib, leaflet
    try {
      lib = await loadLeaflet()
      leaflet = lib.map(container, {
        center: [center[1], center[0]], zoom, minZoom: 2, maxZoom: 18, zoomControl: false, attributionControl: false,
        preferCanvas: true, renderer: lib.canvas({ padding: 0.5, tolerance: 3 }), ...options,
      })
    } catch (error) {
      state(container, { kind: 'error', title: 'The map could not start', text: 'It needs a network connection.' })
      throw error
    }
    lib.control.zoom({ position: 'topright' }).addTo(leaflet)
    // A bottom sheet can resize the stage without resizing the browser window.
    const resize = new ResizeObserver(() => leaflet.invalidateSize({ pan: false }))
    resize.observe(container)
    leaflet.on('unload', () => resize.disconnect())
    const credits = lib.control.attribution({ prefix: '<a href="https://leafletjs.com">Leaflet</a>' }).addTo(leaflet).getContainer()
    // Under 640px the credits would cover the legend, so kit.css folds them behind this button.
    const creditsToggle = el('button', { type: 'button', class: 'leaflet-control k-credits-toggle', 'aria-label': 'Map credits', 'aria-expanded': 'false',
      onclick: () => creditsToggle.setAttribute('aria-expanded', String(credits.classList.toggle('k-open'))) }, 'i')
    credits.after(creditsToggle)
    lib.DomEvent.disableClickPropagation(creditsToggle)

    const pane = (name, zIndex) => {
      Object.assign(leaflet.createPane(name).style, { zIndex, pointerEvents: 'none' })
      return name
    }
    // The gray canvas stops at zoom 16 and the imagery at 18; beyond that Leaflet enlarges the last tiles.
    const tiles = (rest) => lib.tileLayer(ESRI, { maxNativeZoom: 16, maxZoom: 20, className: 'k-gray', ...rest })
    const base = tiles({ attribution: BASEMAP_CREDIT })
    const labels = tiles({ pane: pane('k-labels', 450) })
    const imagery = tiles({ service: 'World_Imagery', maxNativeZoom: 18, className: '', attribution: IMAGERY_CREDIT })
    const heatPane = pane('k-heat', 300)

    const tooltip = el('div', { class: 'k-tooltip', hidden: true })
    container.append(tooltip)
    const restylers = []
    // On imagery, marks are white with a dark edge in both themes; on the basemap they are the theme's ink.
    const inks = () => (basemap === 'satellite' ? { ink: '#ffffff', paper: '#0a0a0a' } : { ink: theme.token('ink'), paper: theme.token('paper') })

    function restyle() {
      const satellite = basemap === 'satellite'
      const canvas = `Canvas/World_${theme.current === 'dark' ? 'Dark' : 'Light'}_Gray_`
      base.options.service = `${canvas}Base`
      labels.options.service = `${canvas}Reference`
      for (const layer of [base, labels]) satellite ? layer.remove() : layer.addTo(leaflet).redraw()
      satellite ? imagery.addTo(leaflet) : imagery.remove()
      restylers.forEach((apply) => apply())
    }
    theme.onChange(restyle)
    restyle()

    const wrapper = {
      leaflet,
      get basemap() { return basemap },
      /** 'map' (gray, follows the theme) or 'satellite' (Esri World Imagery). */
      setBasemap(next) {
        if (next === basemap) return
        basemap = next
        restyle()
      },

      /** Scored points on one canvas: radius and opacity grow with the score (0..1); ink from the theme; a ring marks the selection.
          opts: { score: key | fn, tooltip: item => text, onSelect: item => void }
          Returns { setData(items), setVisible(bool), select(id | null) }. */
      points(items, { score = 'score', tooltip: label, onSelect } = {}) {
        const value = accessor(score)
        const group = lib.featureGroup().addTo(leaflet)
        const ring = lib.circleMarker([0, 0], { interactive: false, fill: false, weight: 1.5 })
        const chosen = lib.circleMarker([0, 0], { interactive: false, fillOpacity: 1, weight: 2 })
        let byId = new Map()
        let selectedId = null
        // Marks shrink when zoomed out so a city of them still reads as a pattern.
        const radius = (item, extra = 0) => Math.min(1, Math.max(0.45, 0.45 + (leaflet.getZoom() - 11) * 0.1375)) * (3 + extra + 7 * value(item))

        function restylePoints() {
          const { ink, paper } = inks()
          group.setStyle({ color: paper, fillColor: ink })
          chosen.setStyle({ color: paper, fillColor: ink })
          ring.setStyle({ color: ink })
        }
        restylers.push(restylePoints)
        restylePoints()
        leaflet.on('zoomend', () => {
          group.eachLayer((marker) => marker.setRadius(radius(marker.item)))
          layer.select(selectedId)
        })

        group.on('click', (event) => onSelect?.(event.propagatedFrom.item))
        group.on('mouseover mousemove', (event) => {
          if (!label) return
          tooltip.textContent = label(event.propagatedFrom.item)
          tooltip.hidden = false
          // Beside the pointer, flipped to its left when it would run off the stage.
          const { x, y } = event.containerPoint
          const flip = x + tooltip.offsetWidth + 24 > container.clientWidth
          tooltip.style.transform = `translate(${x + (flip ? -12 - tooltip.offsetWidth : 12)}px, ${y + 12}px)`
        })
        group.on('mouseout', () => { tooltip.hidden = true })

        const layer = {
          setData(next) {
            tooltip.hidden = true
            group.clearLayers()
            byId = new Map(next.map((item) => [String(item.id), item]))
            const { ink, paper } = inks()
            // Drawn in score order, so the likeliest marks sit on top and win the hover.
            for (const item of [...next].sort((a, b) => value(a) - value(b))) {
              const marker = lib.circleMarker(latLng(item), { radius: radius(item), weight: 1, opacity: 0.9, color: paper, fillColor: ink, fillOpacity: 0.14 + 0.76 * value(item) })
              group.addLayer(Object.assign(marker, { item }))
            }
            layer.select(selectedId)
          },
          setVisible(visible) {
            visible ? group.addTo(leaflet) : group.remove()
            layer.select(selectedId)
          },
          select(id) {
            selectedId = id
            const item = byId.get(String(id))
            const shown = item && leaflet.hasLayer(group)
            for (const [mark, extra] of [[ring, 6], [chosen, 0]]) {
              if (shown) mark.setLatLng(latLng(item)).setRadius(radius(item, extra)).addTo(leaflet).bringToFront()
              else mark.remove()
            }
          },
        }
        layer.setData(items)
        return layer
      },

      /** Density of score in ink tones: faint where little, solid where a lot. Returns { setData, setVisible }.
          A plain canvas of soft ink spots that pile up; redrawn after every move and theme change. */
      heat(items, { score = 'score', radius = 1 } = {}) {
        const value = accessor(score)
        const canvas = el('canvas', { class: 'leaflet-zoom-animated' })
        const spot = el('canvas', { width: 64, height: 64 })
        let data = items
        let corner

        function draw() {
          if (!canvas.isConnected) return
          // Twice the view, so a pan does not run off its edge, at half resolution: it is a blur anyway.
          const size = leaflet.getSize()
          const origin = leaflet.containerPointToLayerPoint(size.multiplyBy(-0.5))
          corner = leaflet.layerPointToLatLng(origin)
          lib.DomUtil.setPosition(canvas, origin)
          Object.assign(canvas, { width: size.x, height: size.y })
          Object.assign(canvas.style, { width: `${size.x * 2}px`, height: `${size.y * 2}px` })

          const ink = inks().ink
          const paint = spot.getContext('2d')
          const fade = paint.createRadialGradient(32, 32, 0, 32, 32, 32)
          for (const [at, alpha] of [[0, 1], [0.2, 0.85], [0.4, 0.55], [0.6, 0.27], [0.8, 0.08], [1, 0]]) fade.addColorStop(at, rgba(ink, alpha))
          paint.clearRect(0, 0, 64, 64)
          paint.fillStyle = fade
          paint.fillRect(0, 0, 64, 64)

          const context = canvas.getContext('2d')
          const zoom = leaflet.getZoom()
          const reach = 8 * radius * 1.285 ** (zoom - 10)
          const strength = Math.min(0.5, 0.2 + 0.04 * (zoom - 10))
          for (const item of data) {
            const at = leaflet.latLngToLayerPoint(latLng(item)).subtract(origin).divideBy(2)
            context.globalAlpha = value(item) * strength
            context.drawImage(spot, at.x - reach, at.y - reach, reach * 2, reach * 2)
          }
        }
        restylers.push(draw)
        leaflet.on('moveend resize', draw)
        leaflet.on('zoomanim', (event) => corner && lib.DomUtil.setTransform(canvas, leaflet._latLngToNewLayerPoint(corner, event.zoom, event.center), leaflet.getZoomScale(event.zoom)))

        const layer = {
          setData(next) { data = next; draw() },
          setVisible(visible) {
            if (visible) leaflet.getPane(heatPane).append(canvas)
            else canvas.remove()
            draw()
          },
        }
        layer.setVisible(true)
        return layer
      },

      /** Frames the items. Call once after loading data. */
      fit(items, { padding = 56, animate = false } = {}) {
        if (!items.length) return
        // Zoom moves in whole levels, so a small stage gives up some padding rather than a level.
        const size = leaflet.getSize()
        const pad = Math.min(padding, Math.min(size.x, size.y) / 16)
        leaflet.fitBounds(items.map(latLng), { padding: [pad, pad], animate, maxZoom: 16 })
      },
      /** Flies to one item, zooming in if needed but never out. `animate: false` jumps. */
      flyTo(item, zoom = 16, { animate = true } = {}) {
        const still = !animate || matchMedia('(prefers-reduced-motion: reduce)').matches
        leaflet.flyTo(latLng(item), Math.max(leaflet.getZoom(), zoom), { animate: !still, duration: 0.8 })
      },
      /** The items inside the current view. */
      inView(items) {
        const bounds = leaflet.getBounds()
        return items.filter((item) => bounds.contains(latLng(item)))
      },
      /** Calls `listener` after every pan or zoom settles. */
      onMove: (listener) => leaflet.on('moveend', listener),
    }
    return wrapper
  }

  window.Kingdom = { theme, el, state, loadData, evidence, rankedList, fmt, map }
})()
