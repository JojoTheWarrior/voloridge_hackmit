/* Kingdom explorer kit: optional helpers. No dependencies; exposes one global, `Kingdom`.
   Load it in <head> (it is tiny) so the theme is set before the first paint.
   Everything here is a convenience: read it, use what helps, replace what does not. */
(function () {
  'use strict'

  // 5.x on purpose: MapLibre 4 drops its own worker messages inside a sandboxed frame (opaque origin), so nothing draws.
  const MAPLIBRE = 'https://unpkg.com/maplibre-gl@5.24.0/dist/maplibre-gl'
  const BASE_TILES = 'https://tiles.openfreemap.org/planet' // OpenStreetMap data in the OpenMapTiles schema; free, no key
  const GLYPHS = 'https://tiles.openfreemap.org/fonts/{fontstack}/{range}.pbf'
  const LABEL_FONT = ['Noto Sans Regular'] // the font to use if you add your own symbol layers
  const IMAGERY = {
    type: 'raster', tileSize: 256, maxzoom: 18,
    tiles: ['https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}'],
    attribution: 'Imagery © <a href="https://www.esri.com">Esri</a>, Maxar, Earthstar Geographics, and the GIS User Community',
  }

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
     A MapLibre GL map whose basemap is drawn by us: OpenFreeMap vector tiles painted with the kit's
     own tokens, so it matches the product in light and dark and repaints when the theme changes.
     Esri World Imagery sits above it as the 'satellite' basemap. Neither needs a key. */
  function basemapLayers() {
    const c = theme.token
    const width = (...stops) => ['interpolate', ['exponential', 1.5], ['zoom'], ...stops]
    const base = (id, type, sourceLayer, rest) => ({ id: `k-${id}`, type, source: 'k-base', 'source-layer': sourceLayer, ...rest })
    const road = (id, classes, minzoom, color, stops) => base(id, 'line', 'transportation', {
      minzoom, filter: ['all', ['==', ['geometry-type'], 'LineString'], ['in', ['get', 'class'], ['literal', classes]]],
      layout: { 'line-cap': 'round', 'line-join': 'round' }, paint: { 'line-color': color, 'line-width': width(...stops) },
    })
    const name = ['coalesce', ['get', 'name_en'], ['get', 'name:latin'], ['get', 'name']]
    const label = (id, sourceLayer, rest, layout, color) => base(id, 'symbol', sourceLayer, {
      ...rest, layout: { 'text-field': name, 'text-font': LABEL_FONT, 'text-max-width': 8, ...layout },
      paint: { 'text-color': color, 'text-halo-color': c('side'), 'text-halo-width': 1.25 },
    })
    const places = (classes) => ['in', ['get', 'class'], ['literal', classes]]
    return [
      { id: 'k-land', type: 'background', paint: { 'background-color': c('side') } },
      base('green', 'fill', 'landcover', { paint: { 'fill-color': c('fill') } }),
      base('park', 'fill', 'park', { paint: { 'fill-color': c('fill') } }),
      base('water', 'fill', 'water', { paint: { 'fill-color': c('line') } }),
      base('river', 'line', 'waterway', { paint: { 'line-color': c('line'), 'line-width': width(10, 0.5, 16, 3) } }),
      base('building', 'fill', 'building', { minzoom: 14, paint: { 'fill-color': c('hover'), 'fill-outline-color': c('line') } }),
      road('road-minor', ['minor', 'service', 'track'], 12.5, c('series-4'), [13, 0.5, 16, 2.5, 19, 10]),
      road('rail', ['rail', 'transit'], 11, c('series-3'), [11, 0.5, 16, 1]),
      road('road-major', ['motorway', 'trunk', 'primary', 'secondary', 'tertiary'], 6, c('series-3'), [8, 0.4, 12, 1.2, 16, 5, 19, 16]),
      label('label-road', 'transportation_name', { minzoom: 14.5 }, { 'symbol-placement': 'line', 'text-size': 10, 'text-letter-spacing': 0.02 }, c('muted')),
      label('label-area', 'place', { minzoom: 12.5, filter: places(['suburb', 'quarter', 'neighbourhood', 'village', 'hamlet']) }, { 'text-size': 10.5, 'text-padding': 12, 'text-transform': 'uppercase', 'text-letter-spacing': 0.08 }, c('faint')),
      label('label-city', 'place', { filter: places(['city', 'town']) }, { 'text-size': ['interpolate', ['linear'], ['zoom'], 6, 11, 12, 15], 'text-letter-spacing': -0.01 }, c('muted')),
      { id: 'k-satellite', type: 'raster', source: 'k-satellite', layout: { visibility: 'none' } },
    ]
  }

  let mapLibre
  function loadMapLibre() {
    if (window.maplibregl) return Promise.resolve(window.maplibregl)
    mapLibre ??= new Promise((resolve, reject) => {
      document.head.append(
        el('link', { rel: 'stylesheet', href: `${MAPLIBRE}.css` }),
        el('script', { src: `${MAPLIBRE}.js`, onload: () => resolve(window.maplibregl), onerror: () => reject(new Error('MapLibre did not load')) }))
    })
    return mapLibre
  }

  const rgba = (hex, alpha) => `rgba(${[1, 3, 5].map((at) => parseInt(hex.slice(at, at + 2), 16)).join(',')},${alpha})`
  const position = (item) => [item.lon ?? item.lng, item.lat]

  /** Resolves to a small wrapper; `wrapper.gl` is the real MapLibre map for anything not covered here.
      opts: { center: [lon, lat], zoom, basemap: 'map' | 'satellite', ...any MapLibre option } */
  async function map(container, { basemap = 'map', ...options } = {}) {
    let gl
    try {
      const lib = await loadMapLibre()
      gl = new lib.Map({
        container, center: [0, 20], zoom: 1.5, maxZoom: 19, dragRotate: false, pitchWithRotate: false, attributionControl: false,
        style: {
          version: 8,
          glyphs: GLYPHS,
          sources: { 'k-base': { type: 'vector', url: BASE_TILES }, 'k-satellite': IMAGERY },
          layers: basemapLayers(),
        },
        ...options,
      })
      gl.touchZoomRotate.disableRotation()
      gl.addControl(new lib.NavigationControl({ showCompass: false }), 'top-right')
      gl.addControl(new lib.AttributionControl({ compact: true }), 'bottom-right')
      await new Promise((resolve) => gl.once('load', resolve))
      // MapLibre opens the credits by default; on a narrow stage they would cover the legend, so start them folded.
      if (container.clientWidth < 640) {
        const credits = container.querySelector('.maplibregl-ctrl-attrib')
        credits?.classList.remove('maplibregl-compact-show')
        credits?.removeAttribute('open')
      }
    } catch (error) {
      state(container, { kind: 'error', title: 'The map could not start', text: 'It needs WebGL and a network connection.' })
      throw error
    }

    const tooltip = el('div', { class: 'k-tooltip', hidden: true })
    container.append(tooltip)
    const restylers = []
    // On imagery, marks are white with a dark edge in both themes; on the basemap they are the theme's ink.
    const inks = () => (basemap === 'satellite' ? { ink: '#ffffff', paper: '#0a0a0a' } : { ink: theme.token('ink'), paper: theme.token('paper') })

    function restyle() {
      for (const layer of basemapLayers()) for (const [property, value] of Object.entries(layer.paint || {})) gl.setPaintProperty(layer.id, property, value)
      gl.setLayoutProperty('k-satellite', 'visibility', basemap === 'satellite' ? 'visible' : 'none')
      restylers.forEach((apply) => apply())
    }
    theme.onChange(restyle)
    restyle()

    function geojson(items, score) {
      return { type: 'FeatureCollection', features: items.map((item) => ({ type: 'Feature', geometry: { type: 'Point', coordinates: position(item) }, properties: { id: item.id, score: score(item) } })) }
    }
    const accessor = (score) => (typeof score === 'function' ? score : (item) => Number(item[score]) || 0)
    const setVisible = (ids, visible) => ids.forEach((id) => gl.setLayoutProperty(id, 'visibility', visible ? 'visible' : 'none'))

    const wrapper = {
      gl,
      get basemap() { return basemap },
      /** 'map' (ours, follows the theme) or 'satellite' (Esri World Imagery). */
      setBasemap(next) { basemap = next; restyle() },

      /** Scored points: radius and opacity grow with the score (0..1); ink from the theme; a ring marks the selection.
          opts: { id, score: key | fn, tooltip: item => text, onSelect: item => void }
          Returns { setData(items), setVisible(bool), select(id | null) }. */
      points(items, { id = 'k-points', score = 'score', tooltip: label, onSelect } = {}) {
        const byId = new Map()
        const value = accessor(score)
        // Marks shrink when zoomed out so a city of them still reads as a pattern.
        const radius = (extra) => ['interpolate', ['linear'], ['zoom'], 11, ['*', 0.45, ['+', 3 + extra, ['*', 7, ['get', 'score']]]], 15, ['+', 3 + extra, ['*', 7, ['get', 'score']]]]
        const none = ['==', ['get', 'id'], '']
        gl.addSource(id, { type: 'geojson', data: geojson([], value) })
        gl.addLayer({ id, type: 'circle', source: id, layout: { 'circle-sort-key': ['get', 'score'] }, paint: { 'circle-radius': radius(0), 'circle-opacity': ['+', 0.14, ['*', 0.76, ['get', 'score']]], 'circle-stroke-width': 1, 'circle-stroke-opacity': 0.9 } })
        gl.addLayer({ id: `${id}-ring`, type: 'circle', source: id, filter: none, paint: { 'circle-radius': radius(6), 'circle-opacity': 0, 'circle-stroke-width': 1.5 } })
        gl.addLayer({ id: `${id}-selected`, type: 'circle', source: id, filter: none, paint: { 'circle-radius': radius(0), 'circle-stroke-width': 2 } })
        const layers = [id, `${id}-ring`, `${id}-selected`]

        restylers.push(() => {
          const { ink, paper } = inks()
          for (const layer of [id, `${id}-selected`]) {
            gl.setPaintProperty(layer, 'circle-color', ink)
            gl.setPaintProperty(layer, 'circle-stroke-color', paper)
          }
          gl.setPaintProperty(`${id}-ring`, 'circle-stroke-color', ink)
        })
        restylers.at(-1)()

        gl.on('click', id, (event) => onSelect?.(byId.get(String(event.features[0].properties.id))))
        gl.on('mousemove', id, (event) => {
          gl.getCanvas().style.cursor = 'pointer'
          const item = byId.get(String(event.features[0].properties.id))
          if (!label || !item) return
          tooltip.textContent = label(item)
          tooltip.hidden = false
          // Beside the pointer, flipped to its left when it would run off the stage.
          const flip = event.point.x + tooltip.offsetWidth + 24 > container.clientWidth
          tooltip.style.transform = `translate(${event.point.x + (flip ? -12 - tooltip.offsetWidth : 12)}px, ${event.point.y + 12}px)`
        })
        gl.on('mouseleave', id, () => { gl.getCanvas().style.cursor = ''; tooltip.hidden = true })

        const layer = {
          setData(next) {
            byId.clear()
            next.forEach((item) => byId.set(String(item.id), item))
            gl.getSource(id).setData(geojson(next, value))
          },
          setVisible: (visible) => setVisible(layers, visible),
          select(selectedId) {
            const filter = ['==', ['to-string', ['get', 'id']], selectedId == null ? '' : String(selectedId)]
            gl.setFilter(`${id}-ring`, filter)
            gl.setFilter(`${id}-selected`, filter)
          },
        }
        layer.setData(items)
        return layer
      },

      /** Density of score in ink tones: faint where little, solid where a lot. Returns { setData, setVisible }. */
      heat(items, { id = 'k-heat', score = 'score', radius = 1 } = {}) {
        const value = accessor(score)
        gl.addSource(id, { type: 'geojson', data: geojson(items, value) })
        gl.addLayer({ id, type: 'heatmap', source: id, paint: {
          'heatmap-weight': ['get', 'score'],
          'heatmap-radius': ['interpolate', ['exponential', 1.4], ['zoom'], 10, 16 * radius, 16, 72 * radius],
          'heatmap-intensity': ['interpolate', ['linear'], ['zoom'], 10, 0.8, 16, 1.6],
        } })
        restylers.push(() => {
          const ink = inks().ink
          gl.setPaintProperty(id, 'heatmap-color', ['interpolate', ['linear'], ['heatmap-density'], 0, rgba(ink, 0), 0.15, rgba(ink, 0.1), 0.45, rgba(ink, 0.32), 0.75, rgba(ink, 0.58), 1, rgba(ink, 0.82)])
        })
        restylers.at(-1)()
        return { setData: (next) => gl.getSource(id).setData(geojson(next, value)), setVisible: (visible) => setVisible([id], visible) }
      },

      /** Frames the items. Call once after loading data. */
      fit(items, { padding = 56, animate = false } = {}) {
        if (!items.length) return
        const lons = items.map((item) => position(item)[0])
        const lats = items.map((item) => item.lat)
        gl.fitBounds([[Math.min(...lons), Math.min(...lats)], [Math.max(...lons), Math.max(...lats)]], { padding, animate, maxZoom: 16 })
      },
      /** Flies to one item, zooming in if needed but never out. */
      flyTo(item, zoom = 16) {
        const reduced = matchMedia('(prefers-reduced-motion: reduce)').matches
        gl.flyTo({ center: position(item), zoom: Math.max(gl.getZoom(), zoom), speed: 1.4, animate: !reduced })
      },
      /** The items inside the current view. */
      inView(items) {
        const bounds = gl.getBounds()
        return items.filter((item) => bounds.contains(position(item)))
      },
      /** Calls `listener` after every pan or zoom settles. */
      onMove: (listener) => gl.on('moveend', listener),
    }
    return wrapper
  }

  window.Kingdom = { theme, el, state, loadData, evidence, rankedList, fmt, map }
})()
