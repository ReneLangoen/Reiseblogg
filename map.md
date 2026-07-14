---
layout: default
title: Reisekart
permalink: /map/
---

<section class="page-intro">
  <h1>Reisekart</h1>
  <p class="page-subtitle">Et visuelt kart over hvor vi har vært, og hvordan vi har reist mellom stedene.</p>
</section>

<div class="map-wrapper">
  <div class="map-legend">
    <div class="map-legend-title">Hvordan vi reiste</div>
    <div class="map-legend-items">
      <div class="map-legend-item" data-mode="Fly"><span class="map-legend-line" style="background:#1f78b4"></span>Fly</div>
      <div class="map-legend-item" data-mode="Bil"><span class="map-legend-line" style="background:#33a02c"></span>Bil</div>
      <div class="map-legend-item" data-mode="Buss"><span class="map-legend-line" style="background:#ff7f00"></span>Buss</div>
      <div class="map-legend-item" data-mode="Båt"><span class="map-legend-line" style="background:#6a3d9a"></span>Båt</div>
      <div class="map-legend-item" data-mode="Tog"><span class="map-legend-line" style="background:#e31a1c"></span>Tog</div>
    </div>
  </div>
  <div id="travel-map" class="travel-map"></div>
</div>

<script>
  window.mapData = {
    locations: {{ site.data.map.locations | jsonify }},
    routes: {{ site.data.map.routes | jsonify }}
  };
</script>

<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
<link href="https://unpkg.com/maplibre-gl/dist/maplibre-gl.css" rel="stylesheet" />
<script src="https://unpkg.com/maplibre-gl/dist/maplibre-gl.js"></script>
<script src="https://unpkg.com/@maplibre/maplibre-gl-leaflet/leaflet-maplibre-gl.js"></script>

<script>
  document.addEventListener("DOMContentLoaded", function () {
    const map = L.map('travel-map', {
      minZoom: 2,
      scrollWheelZoom: false
    }).setView([50, 10], 4);

    const modeColors = {
      Fly: '#1f78b4',
      Tog: '#e31a1c',
      Bil: '#33a02c',
      Buss: '#ff7f00',
      Båt: '#6a3d9a'
    };

    const openFreeMapLayer = L.maplibreGL({
      style: 'https://tiles.openfreemap.org/styles/liberty'
    }).addTo(map);

    openFreeMapLayer.getMaplibreMap().on('load', () => {
      const glMap = openFreeMapLayer.getMaplibreMap();
      glMap.getStyle().layers.forEach((layer) => {
        if (layer.type === 'symbol' && layer.layout && layer.layout['text-field']) {
          glMap.setLayoutProperty(layer.id, 'text-field', [
            'coalesce',
            ['get', 'name:no'],
            ['get', 'name:nb'],
            ['get', 'name:en'],
            ['get', 'name:latin'],
            ['get', 'name']
          ]);
        }
      });
    });

    // Build a map of preferred location objects by id, preferring any non-ghost
    // occurrence when a location appears multiple times. Preserve the original
    // ordering based on first appearance in `mapData.locations`.
    const allLocations = mapData.locations || [];
    const preferredById = {};
    for (const loc of allLocations) {
      if (!loc || !loc.id) continue;
      if (!preferredById[loc.id]) {
        preferredById[loc.id] = loc;
      } else if (preferredById[loc.id].ghost && !loc.ghost) {
        // replace a previously-seen ghost with a later non-ghost
        preferredById[loc.id] = loc;
      }
    }
    const locationById = preferredById;

    // visibleLocations: iterate original list order, include each id once and
    // use the preferred (non-ghost when available) instance for visibility.
    const seenIds = new Set();
    const visibleLocations = [];
    for (const loc of allLocations) {
      if (!loc || !loc.id) continue;
      if (seenIds.has(loc.id)) continue;
      seenIds.add(loc.id);
      const preferred = preferredById[loc.id] || loc;
      if (!preferred.ghost) visibleLocations.push(preferred);
    }

    // Norwegian number formatter used for tooltips and stats
    const nbFmt = new Intl.NumberFormat('nb-NO', { maximumFractionDigits: 0 });
    const nf = v => (typeof v === 'number' && isFinite(v)) ? nbFmt.format(Math.round(v)) : v;
    const markerColor = '#4f7d76';

    const mapContainer = map.getContainer();
    mapContainer.addEventListener('mouseenter', () => map.scrollWheelZoom.enable());
    mapContainer.addEventListener('mouseleave', () => map.scrollWheelZoom.disable());
    L.DomEvent.disableScrollPropagation(mapContainer);
    mapContainer.addEventListener('wheel', event => {
      if (map.scrollWheelZoom.enabled()) {
        event.preventDefault();
      }
    }, { passive: false });

    // Great-circle interpolation for geodesic routes
    function interpolateGreatCircle(lat1, lon1, lat2, lon2, segments) {
      const toRad = v => v * Math.PI / 180;
      const toDeg = v => v * 180 / Math.PI;
      const φ1 = toRad(lat1), λ1 = toRad(lon1);
      const φ2 = toRad(lat2), λ2 = toRad(lon2);
      const Δφ = φ2 - φ1;
      const Δλ = λ2 - λ1;
      const a = Math.sin(Δφ/2)*Math.sin(Δφ/2) + Math.cos(φ1)*Math.cos(φ2)*Math.sin(Δλ/2)*Math.sin(Δλ/2);
      const δ = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a)); // angular distance in radians
      if (δ === 0) return [[lat1, lon1]];
      const R = 6371; // km
      // choose segments based on distance (approx 50 km per segment)
      const approxKm = δ * R;
      const segs = segments || Math.min(128, Math.max(2, Math.ceil(approxKm / 50)));
      const points = [];
      for (let i = 0; i <= segs; i++) {
        const f = i / segs;
        const A = Math.sin((1 - f) * δ) / Math.sin(δ);
        const B = Math.sin(f * δ) / Math.sin(δ);
        const x = A * Math.cos(φ1) * Math.cos(λ1) + B * Math.cos(φ2) * Math.cos(λ2);
        const y = A * Math.cos(φ1) * Math.sin(λ1) + B * Math.cos(φ2) * Math.sin(λ2);
        const z = A * Math.sin(φ1) + B * Math.sin(φ2);
        const φ = Math.atan2(z, Math.sqrt(x * x + y * y));
        const λ = Math.atan2(y, x);
        points.push([toDeg(φ), toDeg(λ)]);
      }
      return points;
    }

    // helper: haversine distance (km)
    function haversine(lat1, lon1, lat2, lon2) {
      const R = 6371; // km
      const toRad = v => v * Math.PI / 180;
      const dLat = toRad(lat2 - lat1);
      const dLon = toRad(lon2 - lon1);
      const a = Math.sin(dLat/2) * Math.sin(dLat/2) + Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) * Math.sin(dLon/2) * Math.sin(dLon/2);
      const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
      return R * c;
    }

    // render routes; for car routes without explicit points we fetch a driving route from OSRM
    async function renderRoute(route) {
      const from = locationById[route.from];
      const to = locationById[route.to];
      if (!from || !to) return;
      // render routes even when endpoints are ghost; ghost locations are hidden
      // as markers but should still be part of route sequences

      let linePoints = null;
      let routeDist = 0;

      // Special case: Bergen -> Bangkok should be drawn as two geodesic legs via Munich
      if (route.from === 'bergen' && route.to === 'bangkok') {
        const munich = { lat: 48.1351, lng: 11.5820 };
        const part1 = interpolateGreatCircle(from.lat, from.lng, munich.lat, munich.lng);
        const part2 = interpolateGreatCircle(munich.lat, munich.lng, to.lat, to.lng);
        linePoints = part1.concat(part2.slice(1));
      }

      // prefer explicit points if provided
      if (!linePoints && route.points && Array.isArray(route.points) && route.points.length) {
        linePoints = route.points.map(p => Array.isArray(p) ? [p[0], p[1]] : [p.lat, p.lng]);
      } else if (!linePoints && route.mode && (String(route.mode).toLowerCase().includes('bil') || String(route.mode).toLowerCase().includes('car'))) {
        // fetch driving route from OSRM between from and to
        try {
          const url = `https://router.project-osrm.org/route/v1/driving/${from.lng},${from.lat};${to.lng},${to.lat}?overview=full&geometries=geojson`;
          const resp = await fetch(url);
          if (resp.ok) {
            const data = await resp.json();
            if (data && data.routes && data.routes.length) {
              const geom = data.routes[0].geometry;
              if (geom && Array.isArray(geom.coordinates) && geom.coordinates.length) {
                linePoints = geom.coordinates.map(c => [c[1], c[0]]); // convert [lon,lat] to [lat,lon]
                // OSRM returns distance in meters
                routeDist = (typeof route.distance_km === 'number' && isFinite(route.distance_km)) ? route.distance_km : (data.routes[0].distance / 1000);
              }
            }
          }
        } catch (e) {
          console.warn('OSRM routing failed, falling back to great-circle', e);
        }
      }

      // fallback: geodesic interpolation
      if (!linePoints) {
        linePoints = interpolateGreatCircle(from.lat, from.lng, to.lat, to.lng);
      }

      // if routeDist still zero and there are points, compute along-polyline distance
      if (!routeDist) {
        for (let i = 1; i < linePoints.length; i++) {
          const a = linePoints[i-1];
          const b = linePoints[i];
          routeDist += haversine(a[0], a[1], b[0], b[1]);
        }
      }

      const poly = L.polyline(linePoints, {
        color: route.color || modeColors[route.mode] || '#4f7d76',
        weight: 3,
        opacity: 0.8
      }).addTo(map);

      const displayDist = (typeof route.distance_km === 'number' && isFinite(route.distance_km)) ? route.distance_km : routeDist;

        poly.bindTooltip(`${nf(displayDist)} km`, {
        permanent: false,
        direction: 'center',
        className: 'route-tooltip'
      });
      poly.on('mouseover', function(e) { this.openTooltip(e.latlng); });
      poly.on('mousemove', function(e) { this.setTooltipLatLng(e.latlng); });
      poly.on('mouseout', function() { this.closeTooltip(); });
          // add a small directional arrow along the route
          try {
            if (linePoints && linePoints.length >= 2) {
              const midIndex = Math.max(1, Math.floor(linePoints.length * 0.5));
              const pA = linePoints[midIndex - 1];
              const pB = linePoints[midIndex];
              const angle = Math.atan2(pB[1] - pA[1], pB[0] - pA[0]) * 180 / Math.PI;
              const arrowColor = route.color || modeColors[route.mode] || '#4f7d76';
              const arrowHtml = `<div style="width:0;height:0;border-left:6px solid transparent;border-right:6px solid transparent;border-bottom:8px solid ${arrowColor};transform:rotate(${angle}deg);"></div>`;
              const arrowIcon = L.divIcon({ className: 'route-arrow-icon', html: arrowHtml, iconSize: [12, 12], iconAnchor: [6, 6] });
              L.marker([(pA[0] + pB[0]) / 2, (pA[1] + pB[1]) / 2], { icon: arrowIcon, interactive: false }).addTo(map);
            }
          } catch (e) {
            console.warn('Failed to render route arrow', e);
          }
    }

    // fire off rendering for all routes
    for (const route of mapData.routes) {
      renderRoute(route);
    }

    visibleLocations.forEach((loc, vindex) => {
      // find index among all locations (for home detection) and among visible (for week numbering)
      const indexAll = allLocations.findIndex(l => l.id === loc.id);
      // Week label: prefer an explicit `weeks` array (may contain multiple weeks),
      // fall back to a singular `week` property, else use the visible index.
      let weekLabel;
      if (Array.isArray(loc.weeks) && loc.weeks.length) {
        weekLabel = loc.weeks.join(', ');
      } else if (loc.week) {
        weekLabel = (String(loc.week).match(/\d+/) || [loc.week])[0];
      } else {
        weekLabel = String(vindex);
      }
      const labelText = loc.label || loc.name || loc.id.replace(/[-_]/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
      // consider home the very first entry in the full locations list
      const isHome = indexAll === 0 || weekLabel === '0';
      const markerIcon = L.divIcon({
          html: `
              <div class="map-marker">
                <span class="map-marker-dot${isHome ? ' zero' : ''}" ${isHome ? '' : `style="background:${markerColor}"`}>${weekLabel}</span>
              </div>
            `,
          className: 'map-marker-wrapper',
          iconSize: [24, 24],
          iconAnchor: [12, 12]
        });

      const marker = L.marker([loc.lat, loc.lng], {
        icon: markerIcon,
        riseOnHover: true
      }).addTo(map);

      marker.bindTooltip(`${labelText}<br>Uke ${weekLabel}`, {
        direction: 'top',
        offset: [0, -8]
      });
      marker.bindPopup(`<strong>${labelText}</strong><br>Uke ${weekLabel}`);
    });

    const bounds = L.latLngBounds(visibleLocations.map(loc => [loc.lat, loc.lng]));
    if (visibleLocations.length) map.fitBounds(bounds.pad(0.2));
  });
</script>

<!-- Statistics panel (always visible) -->
<style>
  .map-stats { margin-top:1rem; display:block }
  .map-stats table { width:100%; border-collapse:collapse }
  .map-stats th, .map-stats td { text-align:left; padding:6px 8px; border-bottom:1px solid rgba(0,0,0,0.04) }
  .route-arrow-icon { pointer-events: none; }
  .route-arrow-icon div { transform-origin: center; }
</style>

<div class="map-stats" id="mapStats">
  <h3>Statistikk</h3>
  <div id="statsSummary">Laster statistikk…</div>
  <div id="statsList">Laster steder…</div>
</div>

<script>
  (function () {
    // compute stats once DOM and data available
    document.addEventListener('DOMContentLoaded', async () => {
      try {
        const locations = window.mapData && window.mapData.locations ? window.mapData.locations : [];
        const routes = window.mapData && window.mapData.routes ? window.mapData.routes : [];

        function haversine(lat1, lon1, lat2, lon2) {
          const R = 6371; // km
          const toRad = v => v * Math.PI / 180;
          const dLat = toRad(lat2 - lat1);
          const dLon = toRad(lon2 - lon1);
          const a = Math.sin(dLat/2) * Math.sin(dLat/2) + Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) * Math.sin(dLon/2) * Math.sin(dLon/2);
          const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
          return R * c;
        }

        async function fetchOsrmDistance(from, to) {
          try {
            const url = `https://router.project-osrm.org/route/v1/driving/${from.lng},${from.lat};${to.lng},${to.lat}?overview=false`;
            const resp = await fetch(url);
            if (!resp.ok) return null;
            const data = await resp.json();
            if (data && data.routes && data.routes.length) {
              return data.routes[0].distance / 1000;
            }
          } catch (e) {
            console.warn('OSRM distance fetch failed', e);
          }
          return null;
        }

        const summary = {};
        // Exclude the first location (home) from city/country counts
        const countedLocations = locations.slice(1);
        summary.cities = Math.max(0, countedLocations.length);
        summary.routes = routes.length;

        // distance metrics over routes — we may need to asynchronously fetch OSRM distances for driving legs
        const distances = [];
        const pending = [];
        routes.forEach(r => {
          const from = locations.find(l => l.id === r.from);
          const to = locations.find(l => l.id === r.to);
          if (!from || !to) return;
          // prefer explicit override
          if (typeof r.distance_km === 'number' && isFinite(r.distance_km)) {
            distances.push({ d: r.distance_km, from: r.from, to: r.to, mode: r.mode });
            return;
          }
          // special-case Bergen -> Bangkok to route via Munich geodesics
          if (r.from === 'bergen' && r.to === 'bangkok') {
            const munich = { lat: 48.1351, lng: 11.5820 };
            const d1 = haversine(from.lat, from.lng, munich.lat, munich.lng);
            const d2 = haversine(munich.lat, munich.lng, to.lat, to.lng);
            distances.push({ d: d1 + d2, from: r.from, to: r.to, mode: r.mode });
            return;
          }
          // if route.points exist, sum along them
          if (r.points && Array.isArray(r.points) && r.points.length) {
            const pts = r.points.map(p => Array.isArray(p) ? [p[0], p[1]] : [p.lat, p.lng]);
            let s = 0;
            for (let i = 1; i < pts.length; i++) s += haversine(pts[i-1][0], pts[i-1][1], pts[i][0], pts[i][1]);
            distances.push({ d: s, from: r.from, to: r.to, mode: r.mode });
            return;
          }
          // For driving modes without explicit distance, fetch OSRM distance asynchronously
          if (r.mode && (String(r.mode).toLowerCase().includes('bil') || String(r.mode).toLowerCase().includes('car'))) {
            const p = fetchOsrmDistance(from, to).then(d => {
              const val = (d !== null) ? d : haversine(from.lat, from.lng, to.lat, to.lng);
              distances.push({ d: val, from: r.from, to: r.to, mode: r.mode });
            });
            pending.push(p);
            return;
          }
          // fallback: straight haversine between endpoints
          const d = haversine(from.lat, from.lng, to.lat, to.lng);
          distances.push({ d, from: r.from, to: r.to, mode: r.mode });
        });

        // wait for any pending OSRM fetches
        if (pending.length) await Promise.all(pending);

        const totalDistance = distances.reduce((s, x) => s + x.d, 0);
        summary.totalDistanceKm = totalDistance;

        // bounding box and centroid
        if (locations.length) {
          const lats = locations.map(l=>l.lat);
          const lngs = locations.map(l=>l.lng);
          summary.bounds = { minLat: Math.min(...lats), maxLat: Math.max(...lats), minLng: Math.min(...lngs), maxLng: Math.max(...lngs) };
          summary.centroid = { lat: lats.reduce((a,b)=>a+b,0)/lats.length, lng: lngs.reduce((a,b)=>a+b,0)/lngs.length };
        }

        // estimate countries primarily from `country` field in map.yml, else fall back to parsing `label`
        const countries = new Set();
        let unknownCountries = 0;
        countedLocations.forEach(l => {
          if (l.country && String(l.country).trim()) {
            countries.add(String(l.country).trim());
            return;
          }
          if (l.label && l.label.includes(',')) {
            const parts = l.label.split(',').map(s=>s.trim()).filter(Boolean);
            if (parts.length) {
              const country = parts[parts.length-1];
              countries.add(country);
            } else {
              unknownCountries++;
            }
            return;
          }
          unknownCountries++;
        });
        summary.estimatedCountries = countries.size;
        summary.unknownCountryLabels = unknownCountries;

        // distances from home (first location)
        const home = locations[0];
        if (home) {
          const distFromHome = locations.map(l => ({ id: l.id, label: l.label, d: haversine(home.lat, home.lng, l.lat, l.lng) }));
          distFromHome.sort((a,b)=>b.d-a.d);
          summary.farthest = distFromHome.slice(0,5);
        }

        // render simplified summary HTML (user requested only three labels)
        const el = document.getElementById('statsSummary');
        const nbFmt = new Intl.NumberFormat('nb-NO', { maximumFractionDigits: 0 });
        const nf = v => typeof v === 'number' ? nbFmt.format(Math.round(v)) : v;
        const antalLand = summary.estimatedCountries;
        const antalByer = summary.cities;
        const distanseReist = summary.totalDistanceKm;

        // compute per-mode distances
        const modeSums = {};
        distances.forEach(x => {
          const m = x.mode ? String(x.mode).trim() : 'Annet';
          modeSums[m] = (modeSums[m] || 0) + (Number(x.d) || 0);
        });

        // preferred display order
        const order = ['Fly', 'Bil', 'Tog', 'Buss', 'Båt'];
        const modesToShow = [];
        // add known modes from order if present
        order.forEach(m => { if (modeSums[m]) modesToShow.push(m); });
        // add any other modes
        Object.keys(modeSums).forEach(m => { if (!modesToShow.includes(m)) modesToShow.push(m); });

        // build list of key/value pairs then render into table with two pairs per row
        const pairs = [];
        pairs.push(['Antall land', String(antalLand)]);
        pairs.push(['Antall byer', String(antalByer)]);
        modesToShow.forEach(m => pairs.push([`Distanse ${m}`, `${nf(modeSums[m])} km`]));
        pairs.push(['Total distanse', `${nf(distanseReist)} km`]);

        let html = `<table>`;
        for (let i = 0; i < pairs.length; i += 2) {
          const a = pairs[i];
          const b = pairs[i+1];
          html += '<tr>';
          html += `<th>${a[0]}</th><td>${a[1]}</td>`;
          if (b) html += `<th>${b[0]}</th><td>${b[1]}</td>`;
          else html += `<th></th><td></td>`;
          html += '</tr>';
        }
        html += `</table>`;
        el.innerHTML = html;
        // hide legend items for modes with zero distance
        const legendItems = document.querySelectorAll('.map-legend-item[data-mode]');
        legendItems.forEach(elm => {
          const m = elm.getAttribute('data-mode');
          if (!m) return;
          if (!modeSums[m] || modeSums[m] === 0) elm.style.display = 'none';
          else elm.style.display = '';
        });
        // Render full grouped list of countries -> cities (excluding first/home)
        try {
          const listEl = document.getElementById('statsList');
          const groups = {};
          countedLocations.forEach(l => {
            const country = (l.country && String(l.country).trim()) || (l.label && l.label.split(',').pop().trim()) || 'Ukjent';
            if (!groups[country]) groups[country] = new Set();
            const cityLabel = l.label || l.id;
            groups[country].add(cityLabel);
          });
          // Convert to sorted arrays
          const countryNames = Object.keys(groups).sort((a,b)=>a.localeCompare(b, 'nb') );
          let listHtml = '<h4>Steder etter land</h4>';
          listHtml += '<div class="places-list">';
          countryNames.forEach(cn => {
            const cities = Array.from(groups[cn]).sort((a,b)=>a.localeCompare(b, 'nb'));
            listHtml += `<div class="country-group"><strong>${cn}</strong><ul>`;
            cities.forEach(ct => { listHtml += `<li>${ct}</li>`; });
            listHtml += '</ul></div>';
          });
          listHtml += '</div>';
          listEl.innerHTML = listHtml;
        } catch (e) {
          console.warn('Failed to render places list', e);
        }
      } catch (e) {
        const el = document.getElementById('statsSummary');
        el.textContent = 'Kunne ikke beregne statistikk: ' + e.message;
      }
    });
  })();
</script>
