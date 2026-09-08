"use client";

import { useEffect, useRef } from "react";
import mapboxgl from "mapbox-gl";
import "mapbox-gl/dist/mapbox-gl.css";

export default function MapView({ collection, onSelect }) {
  const container = useRef(null);
  const map = useRef(null);
  const collectionRef = useRef(collection);
  const onSelectRef = useRef(onSelect);
  const token = process.env.NEXT_PUBLIC_MAPBOX_TOKEN;
  collectionRef.current = collection;
  onSelectRef.current = onSelect;

  useEffect(() => {
    if (!token || map.current) return;
    mapboxgl.accessToken = token;
    
    // Using a dark satellite-like style
    map.current = new mapboxgl.Map({ 
      container: container.current, 
      style: "mapbox://styles/mapbox/dark-v11", 
      center: [78.2, 20.5], 
      zoom: 4,
      attributionControl: false
    });
    
    map.current.addControl(new mapboxgl.NavigationControl({ showCompass: false }), "bottom-left");
    
    map.current.on("load", () => {
      map.current.addSource("events", { type: "geojson", data: collectionRef.current, cluster: true, clusterRadius: 50 });
      
      // Cluster layer
      map.current.addLayer({ 
        id: "clusters", 
        type: "circle", 
        source: "events", 
        filter: ["has", "point_count"], 
        paint: { 
          "circle-color": "rgba(38, 52, 46, 0.8)", 
          "circle-radius": ["step", ["get", "point_count"], 20, 100, 30, 750, 40],
          "circle-stroke-width": 1,
          "circle-stroke-color": "#a5afa9"
        } 
      });

      // Cluster count label
      map.current.addLayer({
        id: "cluster-count",
        type: "symbol",
        source: "events",
        filter: ["has", "point_count"],
        layout: {
          "text-field": "{point_count_abbreviated}",
          "text-font": ["DIN Offc Pro Medium", "Arial Unicode MS Bold"],
          "text-size": 12
        },
        paint: {
          "text-color": "#ffffff"
        }
      });

      // Individual events layer
      map.current.addLayer({ 
        id: "events", 
        type: "circle", 
        source: "events", 
        filter: ["!", ["has", "point_count"]], 
        paint: { 
          "circle-radius": [
            "case",
            ["==", ["get", "severity"], "high"], 8,
            6
          ], 
          "circle-stroke-width": [
            "case",
            ["==", ["get", "severity"], "high"], 3,
            2
          ], 
          "circle-stroke-color": "#ffffff", 
          "circle-color": [
            "match", 
            ["get", "classification"], 
            "wildfire", "#f59e0b", 
            "industrial", "#3b82f6", 
            "#71717a"
          ] 
        } 
      });

      // Critical pulsing effect (represented by a larger, fainter ring)
      map.current.addLayer({
        id: "events-critical-pulse",
        type: "circle",
        source: "events",
        filter: ["all", ["!", ["has", "point_count"]], ["==", ["get", "severity"], "high"]],
        paint: {
          "circle-radius": 18,
          "circle-color": "rgba(239, 68, 68, 0.3)",
          "circle-stroke-width": 0
        }
      });

      // Hover Tooltips
      const popup = new mapboxgl.Popup({
        closeButton: false,
        closeOnClick: false,
        className: 'premium-tooltip'
      });

      map.current.on('mouseenter', 'events', (e) => {
        map.current.getCanvas().style.cursor = 'pointer';
        const coordinates = e.features[0].geometry.coordinates.slice();
        const props = e.features[0].properties;
        const isCritical = props.severity === 'high';
        
        while (Math.abs(e.lngLat.lng - coordinates[0]) > 180) {
          coordinates[0] += e.lngLat.lng > coordinates[0] ? 360 : -360;
        }
        
        const html = `
          <div style="background: var(--bg-secondary); padding: 12px; border-radius: 8px; border: 1px solid var(--border-subtle); color: white; min-width: 180px;">
            <div style="display: flex; align-items: center; gap: 6px; margin-bottom: 8px;">
              <div style="width: 8px; height: 8px; border-radius: 50%; background: ${isCritical ? 'var(--accent-critical)' : 'var(--accent-warning)'}"></div>
              <strong style="font-size: 12px; text-transform: uppercase;">${props.classification} (${props.source || 'VIIRS'})</strong>
            </div>
            <div style="display: grid; grid-template-columns: auto 1fr; gap: 4px 12px; font-size: 11px;">
              <span style="color: var(--text-secondary)">FRP</span> <strong style="text-align: right">${props.frp || 0} MW</strong>
              <span style="color: var(--text-secondary)">CONFIDENCE</span> <strong style="text-align: right">${Math.round(props.confidence * 100)}%</strong>
              <span style="color: var(--text-secondary)">DETECTED</span> <strong style="text-align: right">${new Date(props.detectedAt).toLocaleTimeString()}</strong>
            </div>
            <div style="margin-top: 8px; font-size: 10px; color: var(--text-tertiary); text-align: center; text-transform: uppercase;">Click for full intel →</div>
          </div>
        `;

        popup.setLngLat(coordinates).setHTML(html).addTo(map.current);
      });

      map.current.on('mouseleave', 'events', () => {
        map.current.getCanvas().style.cursor = '';
        popup.remove();
      });

      map.current.on("click", "events", (click) => {
        popup.remove();
        onSelectRef.current(click.features[0].properties.id);
      });
      
      map.current.on("click", "clusters", async (click) => {
        const feature = map.current.queryRenderedFeatures(click.point, { layers: ["clusters"] })[0];
        const zoom = await map.current.getSource("events").getClusterExpansionZoom(feature.properties.cluster_id);
        map.current.easeTo({ center: feature.geometry.coordinates, zoom });
      });
    });
    
    return () => { map.current?.remove(); map.current = null; };
  }, [token]);

  useEffect(() => {
    const source = map.current?.getSource("events");
    if (source) source.setData(collection);
  }, [collection]);

  if (!token) return <div className="map-fallback"><p>Mapbox token unavailable. Event list remains interactive.</p>{collection.features.map(({ properties }) => <button key={properties.id} onClick={() => onSelect(properties.id)}><span className={`dot ${properties.classification}`} />{properties.classification} · {properties.frp ?? "—"} MW</button>)}</div>;
  return (
    <div className="map-container">
      <div ref={container} style={{ width: '100%', height: '100%' }} aria-label="Interactive thermal event map" />
      {/* Custom CSS for mapbox popups to remove default white background */}
      <style dangerouslySetInnerHTML={{__html: `
        .premium-tooltip .mapboxgl-popup-content { background: transparent; padding: 0; border-radius: 0; box-shadow: 0 10px 25px rgba(0,0,0,0.5); }
        .premium-tooltip .mapboxgl-popup-tip { display: none; }
      `}} />
    </div>
  );
}
