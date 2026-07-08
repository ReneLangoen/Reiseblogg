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
      <div class="map-legend-item"><span class="map-legend-line" style="background:#1f78b4"></span>Fly</div>
      <div class="map-legend-item"><span class="map-legend-line" style="background:#33a02c"></span>Bil</div>
      <div class="map-legend-item"><span class="map-legend-line" style="background:#ff7f00"></span>Buss</div>
      <div class="map-legend-item"><span class="map-legend-line" style="background:#6a3d9a"></span>Båt</div>
      <div class="map-legend-item"><span class="map-legend-line" style="background:#e31a1c"></span>Tog</div>
    </div>
  </div>
  <div id="travel-map" class="travel-map"></div>
</div>

<script>
  const mapData = {
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

    const locationById = Object.fromEntries(mapData.locations.map(loc => [loc.id, loc]));
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

    mapData.routes.forEach(route => {
      const from = locationById[route.from];
      const to = locationById[route.to];
      if (!from || !to) return;

      L.polyline([[from.lat, from.lng], [to.lat, to.lng]], {
        color: route.color || modeColors[route.mode] || '#4f7d76',
        weight: 3,
        opacity: 0.8
      }).addTo(map);
    });

    mapData.locations.forEach((loc, index) => {
      const weekLabel = loc.week ? (String(loc.week).match(/\d+/) || [loc.week])[0] : String(index + 1);
      const labelText = loc.label || loc.name || loc.id.replace(/[-_]/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
      const markerIcon = L.divIcon({
        html: `
          <div class="map-marker">
            <span class="map-marker-dot" style="background:${markerColor}">${weekLabel}</span>
          </div>
        `,
        className: 'map-marker-wrapper',
        iconSize: [26, 26],
        iconAnchor: [13, 13]
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

    const bounds = L.latLngBounds(mapData.locations.map(loc => [loc.lat, loc.lng]));
    map.fitBounds(bounds.pad(0.2));
  });
</script>
